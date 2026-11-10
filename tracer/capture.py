"""mitmproxy addon: write every flow as one redacted JSON line.

Run via tracer/run.sh. Output path comes from $TRACE_OUT.

- Credentials are redacted before anything touches disk (headers + token-ish JSON keys).
- SSE responses are streamed through (the client sees tokens live) and teed;
  at the end the events are parsed and the final message is reassembled.
"""

import json
import os
import re
import time

from mitmproxy import http
from mitmproxy.net.encoding import decode

OUT = os.environ.get("TRACE_OUT", "traces/capture.jsonl")
MAX_OTHER_BODY = 64 * 1024  # non-Anthropic-API bodies (telemetry etc.) are clipped

SECRET_HEADERS = re.compile(r"^(authorization|proxy-authorization|x-api-key|cookie|set-cookie)$|token|secret", re.I)
SECRET_KEYS = re.compile(r"^(access_token|refresh_token|id_token|code|code_verifier|state)$|secret|password|api_?key", re.I)


def redact_headers(headers) -> dict:
    out = {}
    for k, v in headers.items(multi=True):
        out[k] = "<redacted>" if SECRET_HEADERS.search(k) else v
    return out


def redact_json(obj):
    if isinstance(obj, dict):
        return {k: "<redacted>" if SECRET_KEYS.search(k) and isinstance(v, str) else redact_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_json(x) for x in obj]
    return obj


def body(raw: bytes | None, ctype: str, clip: bool):
    if not raw:
        return None
    if "json" in ctype:
        try:
            return redact_json(json.loads(raw))
        except ValueError:
            pass
    text = raw.decode("utf-8", "replace")
    if clip and len(text) > MAX_OTHER_BODY:
        return text[:MAX_OTHER_BODY] + f"... <clipped {len(text) - MAX_OTHER_BODY} chars>"
    return text


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        data = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
        if not data:
            continue
        try:
            events.append(json.loads("\n".join(data)))
        except ValueError:
            events.append({"unparsed": "\n".join(data)})
    return events


def assemble(events: list[dict]) -> dict | None:
    """Rebuild a Messages API response from its stream events."""
    msg = None
    partial_json: dict[int, str] = {}
    for ev in events:
        t = ev.get("type")
        if t == "message_start":
            msg = ev["message"]
            msg["content"] = []
        elif msg is None:
            continue
        elif t == "content_block_start":
            msg["content"].append(ev["content_block"])
        elif t == "content_block_delta":
            i, d = ev["index"], ev["delta"]
            block = msg["content"][i]
            kind = d.get("type")
            if kind == "text_delta":
                block["text"] = block.get("text", "") + d["text"]
            elif kind == "thinking_delta":
                block["thinking"] = block.get("thinking", "") + d["thinking"]
            elif kind == "signature_delta":
                block["signature"] = "<signature %d chars>" % len(d["signature"])
            elif kind == "input_json_delta":
                partial_json[i] = partial_json.get(i, "") + d["partial_json"]
            else:
                block.setdefault("other_deltas", []).append(d)
        elif t == "content_block_stop":
            i = ev["index"]
            if i in partial_json:
                try:
                    msg["content"][i]["input"] = json.loads(partial_json.pop(i) or "{}")
                except ValueError:
                    msg["content"][i]["input_raw"] = partial_json.pop(i, "")
        elif t == "message_delta":
            msg.update({k: v for k, v in ev.get("delta", {}).items()})
            msg["usage"] = {**msg.get("usage", {}), **ev.get("usage", {})}
    return msg


class Capture:
    def __init__(self):
        os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
        self.f = open(OUT, "a", buffering=1)
        self.seq = 0

    def responseheaders(self, flow: http.HTTPFlow):
        if "text/event-stream" in flow.response.headers.get("content-type", ""):
            chunks: list[bytes] = []
            flow.metadata["sse_chunks"] = chunks

            def tee(data: bytes) -> bytes:
                chunks.append(data)
                return data

            flow.response.stream = tee

    def response(self, flow: http.HTTPFlow):
        self.write(flow)

    def error(self, flow: http.HTTPFlow):
        self.write(flow)

    def write(self, flow: http.HTTPFlow):
        req, resp = flow.request, flow.response
        is_api = req.pretty_host.endswith("anthropic.com") and req.path.startswith("/v1/messages")
        rec = {
            "seq": self.seq,
            "t_start": req.timestamp_start,
            "t_end": (resp.timestamp_end if resp else None) or time.time(),
            "method": req.method,
            "host": req.pretty_host,
            "path": req.path,
            "req_headers": redact_headers(req.headers),
            "req_body": body(req.get_content(strict=False), req.headers.get("content-type", ""), clip=not is_api),
        }
        self.seq += 1
        if resp:
            rec["status"] = resp.status_code
            rec["resp_headers"] = redact_headers(resp.headers)
            if "sse_chunks" in flow.metadata:
                raw = b"".join(flow.metadata["sse_chunks"])
                enc = resp.headers.get("content-encoding")
                if enc:
                    raw = decode(raw, enc)
                events = parse_sse(raw.decode("utf-8", "replace"))
                rec["sse_event_count"] = len(events)
                rec["resp_body"] = assemble(events)
            else:
                rec["resp_body"] = body(resp.get_content(strict=False), resp.headers.get("content-type", ""), clip=not is_api)
        if flow.error:
            rec["error"] = str(flow.error)
        self.f.write(json.dumps(rec) + "\n")


addons = [Capture()]
