#!/usr/bin/env python3
"""Summarize a tracer JSONL capture.

  tracer/report.py summary traces/DATE/label.jsonl     # all flows + per-request token breakdown
  tracer/report.py dump traces/DATE/label.jsonl SEQ    # write SEQ's request/response as markdown
  tracer/report.py diff A.jsonl B.jsonl                # diff the main /v1/messages request of two captures

Token sizes per component are estimates (chars / 4); the totals in `usage` are exact.
"""

import json
import sys
from collections import Counter
from pathlib import Path


def load(path):
    return [json.loads(line) for line in open(path)]


def est(obj) -> int:
    s = obj if isinstance(obj, str) else json.dumps(obj)
    return len(s) // 4


def is_messages(r):
    return r["path"].startswith("/v1/messages") and isinstance(r.get("req_body"), dict) and "messages" in r["req_body"]


def block_text(b) -> str:
    if isinstance(b, str):
        return b
    return b.get("text") or b.get("thinking") or json.dumps(b.get("input") or b.get("content") or b)


def summary(path):
    rows = load(path)
    print(f"## {path}: {len(rows)} flows\n")
    hosts = Counter()
    for r in rows:
        hosts[(r["host"], r["path"].split("?")[0][:50])] += 1
    print("| count | host | path |\n|---|---|---|")
    for (h, p), n in hosts.most_common():
        print(f"| {n} | {h} | {p} |")

    for r in filter(is_messages, rows):
        b = r["req_body"]
        system = b.get("system") or []
        system = [{"type": "text", "text": system}] if isinstance(system, str) else system
        roles = Counter()
        for m in b["messages"]:
            content = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
            for blk in content:
                roles[f'{m["role"]}:{blk.get("type", "text")}'] += est(block_text(blk))
        u = (r.get("resp_body") or {}).get("usage", {})
        cls = r["req_headers"].get("x-claude-code-request-class", "")
        print(f"\n### seq {r['seq']} {b.get('model')} {cls} ({r['t_end'] - r['t_start']:.1f}s)\n")
        print("| component | est. tokens | detail |\n|---|---|---|")
        for i, s in enumerate(system):
            cc = s.get("cache_control")
            print(f"| system[{i}] | {est(s.get('text', ''))} | {('cache ' + json.dumps(cc)) if cc else ''} |")
        tools = b.get("tools") or []
        print(f"| tools ({len(tools)}) | {est(tools)} | largest: "
              + ", ".join(f"{t.get('name', t.get('type'))}={est(t)}" for t in sorted(tools, key=est, reverse=True)[:5]) + " |")
        for k, v in roles.most_common():
            print(f"| messages {k} | {v} | |")
        print(f"\nusage: input={u.get('input_tokens')} cache_write={u.get('cache_creation_input_tokens')} "
              f"cache_read={u.get('cache_read_input_tokens')} output={u.get('output_tokens')} "
              f"{json.dumps(u.get('cache_creation', {}))}")
        extra = {k: v for k, v in b.items() if k not in ("model", "messages", "system", "tools", "stream")}
        print(f"\nother fields: `{json.dumps(extra)[:600]}`")


def dump(path, seq):
    r = next(x for x in load(path) if x["seq"] == int(seq))
    b = r["req_body"]
    out = Path(path).with_name(f"{Path(path).stem}.seq{seq}.md")
    with open(out, "w") as f:
        f.write(f"# seq {seq}: {r['method']} {r['host']}{r['path']}\n\n## Request headers\n\n```json\n"
                f"{json.dumps(r['req_headers'], indent=2)}\n```\n")
        if not is_messages(r):
            f.write(f"\n## Request body\n\n```json\n{json.dumps(b, indent=2)}\n```\n")
        else:
            system = b.get("system") or []
            system = [{"type": "text", "text": system}] if isinstance(system, str) else system
            for i, s in enumerate(system):
                f.write(f"\n## system[{i}] {json.dumps(s.get('cache_control') or {})}\n\n{s.get('text', '')}\n")
            f.write("\n## Tools\n")
            for t in b.get("tools") or []:
                f.write(f"\n### {t.get('name', t.get('type'))}\n\n{t.get('description', '')}\n\n```json\n"
                        f"{json.dumps({k: v for k, v in t.items() if k != 'description'}, indent=2)}\n```\n")
            f.write("\n## Messages\n")
            for i, m in enumerate(b["messages"]):
                content = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
                for blk in content:
                    f.write(f"\n### [{i}] {m['role']} / {blk.get('type')} {json.dumps(blk.get('cache_control') or {})}\n\n"
                            f"{block_text(blk)}\n")
            rest = {k: v for k, v in b.items() if k not in ("messages", "system", "tools")}
            f.write(f"\n## Other request fields\n\n```json\n{json.dumps(rest, indent=2)}\n```\n")
        f.write(f"\n## Response ({r.get('status')})\n\n```json\n{json.dumps(r.get('resp_body'), indent=2)}\n```\n")
    print(out)


def main_request(path):
    """The last main-loop /v1/messages request in a capture."""
    reqs = [r for r in load(path) if is_messages(r)]
    main = [r for r in reqs if r["req_headers"].get("x-claude-code-request-class", "main") == "main"]
    return (main or reqs)[-1]


def diff(path_a, path_b):
    import difflib

    a, b = main_request(path_a)["req_body"], main_request(path_b)["req_body"]
    ha, hb = main_request(path_a)["req_headers"], main_request(path_b)["req_headers"]

    def text_diff(name, x, y):
        lines = list(difflib.unified_diff(x.splitlines(), y.splitlines(), "a", "b", lineterm="", n=1))
        if lines:
            print(f"\n### {name}\n\n```diff\n" + "\n".join(lines[2:]) + "\n```")

    def sys_text(body):
        s = body.get("system") or []
        return [s] if isinstance(s, str) else [x.get("text", "") for x in s]

    def sys_msgs(body):
        return "\n".join(block_text(c) for m in body["messages"] if m["role"] == "system"
                         for c in (m["content"] if isinstance(m["content"], list) else [m["content"]]))

    betas = lambda h: set(h.get("anthropic-beta", "").split(","))
    print(f"## diff: {path_a} → {path_b}\n")
    print(f"- beta flags added: {sorted(betas(hb) - betas(ha))}\n- beta flags removed: {sorted(betas(ha) - betas(hb))}")
    print(f"- request fields added: {sorted(set(b) - set(a))}, removed: {sorted(set(a) - set(b))}")
    ta = {t.get("name", t.get("type")): t for t in a.get("tools") or []}
    tb = {t.get("name", t.get("type")): t for t in b.get("tools") or []}
    print(f"- tools added: {sorted(set(tb) - set(ta))}, removed: {sorted(set(ta) - set(tb))}")
    for name in sorted(set(ta) & set(tb)):
        if ta[name] != tb[name]:
            print(f"- tool changed: {name} ({est(ta[name])} → {est(tb[name])} est. tokens)")
    sa, sb = sys_text(a), sys_text(b)
    for i in range(max(len(sa), len(sb))):
        text_diff(f"system[{i}]", sa[i] if i < len(sa) else "", sb[i] if i < len(sb) else "")
    text_diff("system-role messages", sys_msgs(a), sys_msgs(b))
    for name in sorted(set(ta) & set(tb)):
        if ta[name] != tb[name]:
            text_diff(f"tool {name}", json.dumps(ta[name], indent=1), json.dumps(tb[name], indent=1))


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["-h"]
    {"summary": summary, "dump": dump, "diff": diff}.get(cmd, lambda *_: print(__doc__))(*args)
