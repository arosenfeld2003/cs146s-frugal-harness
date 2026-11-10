# Rust vs Python for an Agent Harness

CS146S is a Python course (Python 3.12, Poetry, FastMCP). This remix builds the harness in Rust instead.
This doc tracks **what that choice actually buys and costs**, as claims checked against evidence
from this repo, not as language-war opinions.

## The honest prior

A coding agent spends most of its wall time **waiting on a model**: seconds per Claude call, and
tens of seconds for a CPU model reading a long prompt (see [M0 benchmarks](../notes/m0.md#benchmarks)).
Rust being "fast" barely matters for that loop. If Rust wins here, it should be for other reasons:
correctness, deployment, resource use, and safety. Those are the hypotheses below.

## Hypotheses

Status: 🔲 untested · 🟡 partial evidence · ✅ supported · ❌ refuted

| # | Claim | How we'll measure it | Milestone | Status |
|---|---|---|---|---|
| H1 | **Types catch protocol bugs early.** Modeling API messages as Rust `enum`s + `serde` turns malformed requests (wrong content-block shape, missing `tool_use_id`) into compile or parse errors instead of 400s at runtime. | Count bugs caught by the compiler/serde vs found at runtime; compare with a small Python equivalent | M2 | 🔲 |
| H2 | **One static binary simplifies VPS deploy.** `cargo build --release` → copy one file, vs conda + Poetry + venv on the server. | Steps and time to deploy on the VPS; binary size | M2 → VPS | 🔲 |
| H3 | **Low idle footprint for an always-on router.** On a 16GB VPS also running llama-server, every MB counts. | Resident memory (RSS) of the idle harness vs an equivalent Python process | M3 | 🔲 |
| H4 | **Fast startup** matters for CLI- and hook-style invocations (e.g. an MCP server spawned per session). | `hyperfine` cold start: Rust binary vs Python | M4 | 🔲 |
| H5 | **Concurrency without the GIL.** Parallel tool calls and parallel sidecar chunks (summarizing a long log in pieces) are natural with `tokio`. | Wall time for N parallel chunk summaries; code complexity | M3 / M6 | 🔲 |
| H6 | **Safer tool execution.** Memory safety and explicit error handling make the bash/file tools harder to misuse. | Qualitative; review of the tool-execution code paths | M2 / M5 | 🔲 |
| H7 | **Eval runner throughput.** Running a {harness × model × task} matrix with tight bookkeeping is easy to make correct and fast. | Matrix runtime; ledger correctness | M6 | 🔲 |

## Expected costs (also tracked)

| # | Cost | How we'll notice | Status |
|---|---|---|---|
| C1 | **Slower iteration**, especially as a Rust beginner (borrow checker, compile times) | Time-to-first-working-version per milestone; `cargo build` times | 🔲 |
| C2 | **Thinner LLM ecosystem.** Python has official SDKs and FastMCP; Rust may mean community crates or plain HTTP + `serde`. Check what's current at M2 before deciding. | What we had to hand-roll that Python gives for free | 🔲 |
| C3 | **Course materials assume Python** (FastMCP in W2, Poetry setup) | Translation effort per assignment | 🔲 |
| C4 | **Supply chain isn't free in Rust either.** Crates have dependency trees too. | `cargo tree` size; consider `cargo audit` / `cargo deny` | 🔲 |
| C5 | **Prototyping evals/analysis** (plots, quick stats) is easier in Python | Whether analysis scripts end up in Python anyway (that's fine) | 🔲 |

## Pragmatic rule

Rust for the **harness, sidecar router, MCP servers, and eval runner**: the long-running, deployed, correctness-critical parts.
Python (or plain shell) is fine for **one-off analysis and plotting**. The goal is to learn what each is good at,
not to be dogmatic.

## Evidence log

Append dated entries as hypotheses gain or lose support.

<!--
### YYYY-MM-DD · H# · ✅/❌/🟡
What happened, numbers, links to commits.
-->

_No entries yet. The first evidence arrives with harness v0 (M2)._
