# Repository Overview

This repo is a remix of Stanford's [CS146S: The Modern Software Developer](https://themodernsoftware.dev).
The course's assignments are in Python and centered on using coding agents. This remix keeps the assignments,
but threads one project through them: **a coding-agent harness written in Rust**.

## The question

> How much paid-token spend can tiny local models remove from a Claude coding workflow
> without hurting task success?

Every experiment reports three numbers: **Claude cost per task**, **task success rate**, and **wall time**.
Offloading only counts as a win when cost drops *and* success holds. The baseline is an *optimized*
Claude-only setup (prompt caching, truncated tool output, cheaper models for small calls), not a naive one.

## Architecture (target)

```
harness (Rust binary)
  ├── Claude API ............ main reasoning; prompt caching on; every call written to a usage ledger
  └── sidecar provider ...... llama-server (llama.cpp), OpenAI-compatible, localhost + API key
        small jobs, short outputs:
        • compress large tool output (logs, test failures) before Claude sees it
        • filter files/search hits for relevance
        • commit messages, titles, request classification
```

- **Local-first:** developed and measured on a MacBook (M4 Pro). The same repo and scripts later deploy to a
  4-vCPU, no-GPU VPS. Mac CPU-only runs with 4 threads (`cpu4`) approximate it, as a best case.
- **Security-first:** no agent gets a remote shell. Models are pinned by revision and sha256.
  The harness's bash tool will run in a container.
- **Reference harness:** [pi](https://github.com/badlogic/pi-mono), read and traced for comparison.

## Layout

| Path | What | Status |
|---|---|---|
| `course/` | Course assignments (git submodule; `git submodule update --remote` pulls new weeks) | weeks 1–5 |
| `harness/` | The Rust harness (cargo crate) | scaffold only |
| `vps/models.lock` | Model pins: `repo revision file sha256` per line | 3 models |
| `vps/fetch-models.sh` | Download + verify models (macOS/Linux, resumable, retries) | ✅ |
| `vps/bench.sh` | `llama-bench` in `gpu` / `cpu4` modes → `evals/bench/*.jsonl` | ✅ |
| `evals/` | Benchmark results; later the task suite, A/B results, and cost ledger | benchmarks |
| `notes/mN.md` | Working notes per milestone (raw material for blog posts) | M0 |
| `docs/` | This overview, the Rust learning log, Rust vs Python | living docs |
| `models/` | Downloaded GGUF files (gitignored) | — |

## Milestones

| # | Course base | Remix | Status |
|---|---|---|---|
| M0 | setup | toolchain, local inference, pinned models, benchmarks | ✅ ([notes](../notes/m0.md)) |
| M1 | W1: trace dissection | where do Claude Code's and pi's tokens go? (mitmproxy) | next |
| M2 | n/a | harness v0: agent loop, streaming, tools, prompt caching, ledger | |
| M3 | n/a | sidecar v1: router + 2 offload jobs, A/B vs M2 | |
| M4 | W2: MCP server | course MCP server in Rust (`rmcp`); expose the sidecar to Claude Code | |
| M5 | W3/W4: skills, AGENTS.md | context as a budget: measure what skills and AGENTS.md cost and save | |
| M6 | n/a | inference tuning lab + eval runner (quants, threads, KV cache) | |
| M7 | W5: readiness | do agent-ready repos cost fewer tokens? | |
| M8+ | new weeks + final project | fold in new course weeks; open-source results | |

## Docs

- [Rust learning log](rust-learning-log.md): Rust concepts as I hit them, per milestone, from a beginner's view.
- [Rust vs Python](rust-vs-python.md): what Rust buys (and costs) compared to doing the course in Python,
  as hypotheses checked against evidence as the course goes on.

## Quick start

```bash
git clone --recurse-submodules https://github.com/arosenfeld2003/cs146s-frugal-harness
cd cs146s-frugal-harness
brew install llama.cpp          # or build from source on Linux (see notes/m0.md)
vps/fetch-models.sh             # ~9GB, verified against vps/models.lock
vps/bench.sh                    # MODES="gpu cpu4" by default; ONLY=<regex> to filter models
cd harness && cargo run
```
