# cs146s-frugal-harness

A remix of Stanford's [CS146S: The Modern Software Developer](https://themodernsoftware.dev):
a Rust coding-agent harness for frontier models (Claude) that tries to get the most out of every paid token
by offloading small jobs to tiny local models (llama.cpp), built local-first and security-first.

Progress is written up per milestone on [my blog](https://arosenfeld2003.github.io/blog/).

| Path | What |
|---|---|
| `course/` | Course assignments (git submodule of [mihail911/modern-software-dev-assignments](https://github.com/mihail911/modern-software-dev-assignments)) |
| `harness/` | The Rust harness (early days) |
| `vps/` | Cross-platform scripts: pinned model downloads (`models.lock`, sha256-verified), `llama-bench` runner |
| `evals/` | Benchmark results (JSONL), later the eval suite and cost ledger |
| `notes/` | Per-milestone notes |
| `docs/` | [Repo overview](docs/README.md), [Rust learning log](docs/rust-learning-log.md), [Rust vs Python](docs/rust-vs-python.md) |

```bash
git clone --recurse-submodules https://github.com/arosenfeld2003/cs146s-frugal-harness
vps/fetch-models.sh   # ~9GB of GGUF models, verified against models.lock
vps/bench.sh          # requires llama.cpp (llama-bench) on PATH
```

## How this is built

All code in this repo is written with [Claude Code](https://claude.com/claude-code), with me directing,
reviewing, and deciding. Each commit's `Co-Authored-By` trailer records the model that wrote it.
Model changes are logged below so results and code can be traced to the model that produced them.

| From | Model | Notes |
|---|---|---|
| 2026-11-09 (M0) | Claude Opus 5.5 (`claude-opus-5-5`) | Initial setup, scripts, benchmarks |
