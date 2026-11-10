#!/usr/bin/env python3
"""Summarize a tracer JSONL capture.

  tracer/report.py summary traces/DATE/label.jsonl     # all flows + per-request token breakdown
  tracer/report.py dump traces/DATE/label.jsonl SEQ    # write SEQ's request/response as markdown

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


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["-h"]
    {"summary": summary, "dump": dump}.get(cmd, lambda *_: print(__doc__))(*args)
