# Week 1 Write-up

## Part I: Capture

**Setup** (enough for a reader to reproduce your capture):
```
claude --version:  2.1.311 (Claude Code), interactive CLI, model claude-opus-5-5 (effort medium, auto permission mode)
mitmproxy version: Mitmproxy 11.0.2 (Python 3.11.9, OpenSSL 3.4.1)
proxy command:     tracer/run.sh cc-task-v2 claude      # run from experiments/m1-tokenledger
                   # which starts, in the background:
                   mitmdump --listen-host 127.0.0.1 -p 18080 -s tracer/capture.py --set flow_detail=0
                   # and launches claude with, for that one process only:
                   HTTPS_PROXY=http://127.0.0.1:18080 HTTP_PROXY=http://127.0.0.1:18080
                   NO_PROXY=localhost,127.0.0.1 NODE_USE_ENV_PROXY=1
                   NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem
settings file:     none. No .claude/settings.json, no ANTHROPIC_BASE_URL.
```
This differs from the assignment's reverse-proxy setup on purpose. A forward proxy captures **every** host the client
talks to, not only `api.anthropic.com`: this session reached 6 hosts in 52 flows (34 api.anthropic.com, 8 Datadog log
intake, 4 api.github.com, 4 mcp-proxy.anthropic.com, 1 formulae.brew.sh, 1 downloads.claude.ai). The mitmproxy CA is
trusted only by the child process through `NODE_EXTRA_CA_CERTS`; it is never installed in the system keychain. Because
nothing is written to a settings file, there is nothing to remove afterwards, and no other Claude Code session can
end up in the capture. `tracer/capture.py` writes one JSON line per flow with auth headers (`authorization`,
`x-api-key`, cookies) replaced at capture time, and reassembles streamed SSE responses into a single JSON message.
Source: [`tracer/`](../../tracer/) in this repo.

**The session.** What task, against what repo, and how many `POST /v1/messages` requests did it produce?
> The repo is [`m1-tokenledger`](https://github.com/arosenfeld2003/m1-tokenledger), a small Python package (3 modules,
> 21 tests at the start) that prices Anthropic `usage` blocks in dollars. At tag `v2-start` it contains `ISSUE.md`:
> switch to real per-model prices looked up by exact model ID (`PRICING.md`), add `Ledger.breakdown()`, add a CLI
> `--by-model` flag, and update the old tests without deleting any. Prompt: *"Implement ISSUE.md. Start by making a task
> list, then work through it and keep going until the full test suite passes."* Result: branch `cc-v2-result`,
> 21/21 tests passing, 218 s wall time.
>
> The session produced **11 `POST /v1/messages` requests**:
> - **8 main-loop requests** to `claude-opus-5-5` (seq 27, 28, 31, 33, 36, 39, 40, 42). Seq 27 sends the full request
>   with `thread: {type: "create"}`; the other 7 send `thread: {type: "continue", previous_message_id}` and carry only
>   the new tool results.
> - **1 suggestion-mode request** to `claude-opus-5-5` (seq 44) after the final answer: no thread, the whole 18-message
>   conversation replayed, ending in `[SUGGESTION MODE: Suggest what the user might naturally type next into Claude
>   Code.]`. It returned "commit this" (5 output tokens).
> - **2 helper requests:** seq 15 to `claude-haiku-4-5-20251001` with `max_tokens: 1` and the single user word
>   `quota`; seq 26 to `claude-haiku-5-5` with a `json_schema` output format of `{"title": string}`, which named the
>   session `"ISSUE.md"`.

| Requirement | Evidence |
|---|---|
| Touched ≥ 2 files | `git diff --stat v2-start cc-v2-result`: 5 files, +59/−35 (`tokenledger/pricing.py`, `ledger.py`, `cli.py`, `tests/test_pricing.py`, `tests/test_ledger.py`). In the trace: `Write` pricing.py and two `Edit`s of ledger.py in the seq 33 response; Python-heredoc edits of cli.py (seq 36 response) and both test files (seq 39 response). |
| Failed at least once | The seq 31 response runs `python3 -m pytest -q 2>&1 \| tail -15`. Its result (in the seq 33 request) ends `9 failed, 12 passed in 0.04s`, e.g. `TypeError: summarize() got an unexpected keyword argument 'by_model'`. Then it fixes code and tests over 3 responses (seq 33, 36, 39) and seq 40's result reads `21 passed in 0.03s`. **Disclosure:** these failures were planted. The 9 acceptance tests in `tests/test_issue.py` fail by design at `v2-start`. The agent never failed on its own work in this session. The one unplanned failure I captured is in an earlier, simpler session on the same repo (`traces/2026-11-21/cc-task.jsonl`, request seq 31): zsh rejected a glob, `(eval):1: no matches found: --include=*.py`, `is_error: true`, and the next command dropped the flag. Part IV covers both. |
| Long enough to plan | The seq 31 response opens with a `thinking` block (the request sets `thinking: {type: "adaptive", display: "updates"}`, which returns short progress notes instead of reasoning): *"I'm working through a five-step plan: exact-ID pricing with cache-read prices, a new `Ledger.breakdown()`, a `--by-model` CLI flag, updated tests, and a full suite run."* Later responses advance it in text: seq 33 "Task 1 is the pricing rewrite", seq 36 "Tasks 1 and 2 are done. Next is task 3", seq 39 "Task 4…", seq 40 "Task 5: all 21 tests pass". No task tool was used; none was offered (Part III). |
| Your own repo | `github.com/arosenfeld2003/m1-tokenledger`, my own public scratch repo, created for this capture and pinned in this repo as the submodule `experiments/m1-tokenledger`. Not the course repo. |

**What you redacted** from the excerpts quoted below, and why:
> No headers are quoted anywhere, and auth headers were already masked at capture time. Inside request bodies I
> replaced, with visible markers: my email (`[REDACTED: email]`, from the first `<system-reminder>`); the
> `metadata.user_id` values `device_id`, `account_uuid` and `session_id` (`[REDACTED: device id]`, etc.); my claude.ai
> organization UUID in OAuth paths (`[REDACTED: org id]`); and the MCP server IDs in `mcp-proxy.anthropic.com/v1/mcp/…`
> paths (`[REDACTED: mcp server id]`). Absolute paths under my home directory are shortened to `~/`. They are not secret,
> since the repo is public, but they add nothing. The raw captures stay in `traces/`, which is gitignored.


## Part II: System Prompt Annotation

**a. Structure.** Major sections in order, one line each on what it does, and why this order.
> TODO

**b. Tone and verbosity.** Quote the controlling instructions, then say what failure mode they defend against.
```
TODO
```
> TODO

**c. When not to act.** Quote the destructive-operation gates, scope limits, or refusal conditions, and what each buys.
```
TODO
```
> TODO

**d. Environment context.** What the agent is told about machine/repo/session, and where it lives in the request (`system` field or a `role: "system"` message).
> TODO

**e. `<system-reminder>`.** Where they appear (cite an example), two distinct purposes you can evidence, and why they are injected mid-conversation rather than stated once.
```
TODO
```
> TODO


## Part III: Tool Design Annotation

**Inventory.** Did the set change across requests? If so, what triggered it?

Counted from the first main request (seq 27). `tools[]` has 15 entries: 13 callable built-ins, the server-side
`advisor` tool, and a `DeferredToolPlaceholder` stub. Three MCP tools arrive outside `tools[]`, as `tool_addition`
entries in a `role: "system"` message. 46 more tools are listed by name only and must be loaded through `ToolSearch`.

| Built-in | MCP | Deferred | **Total** | Changed mid-session? |
|---|---|---|---|---|
| 14 loaded: 13 client tools (`Agent`, `Artifact`, `AskUserQuestion`, `Bash`, `Edit`, `ListAgents`, `Read`, `ReportFindings`, `ScheduleWakeup`, `SendFeedback`, `Skill`, `ToolSearch`, `Write`) + 1 server tool (`advisor`, type `advisor_20260301`, `model: claude-opus-5-5`, `defer_loading: true`) | 3 loaded (`mcp__claude_ai_Claude_Docs__batch`, `__guide`, `__update`, as `tool_addition`) + 24 deferred, from 4 claude.ai connectors: Google Drive 15, Claude Docs 5+3, Gmail 2, Google Calendar 2 | 46 by name only: 22 built-in (e.g. `EnterPlanMode`, `WebSearch`, `CronCreate`, `NotebookEdit`, `TaskStop`) + 24 MCP | **63** distinct tools (17 with a schema in the first request, 46 deferred). `DeferredToolPlaceholder` is not counted: its description says "never call this tool" | **No.** `tools[]` is identical in seq 27 and seq 44, the only two requests that send it; the 7 thread-continue requests send no `tools` at all. What looks like a change is a delivery channel: the 3 Claude Docs tools come as `tool_addition` in seq 27's system message, under the text *"The following tools just became available and are ready to use"*, instead of being appended to `tools[]`. |

What triggered the `tool_addition` [INFERRED]: the claude.ai connectors connect after startup. The capture shows
`mcp-registry` and `/v1/mcp_servers` lookups (seq 1–14) and four `mcp-proxy.anthropic.com` calls (seq 17–20) before
the first model request (seq 27). Tools that finish loading late are announced in the message stream, so the cached
`tools[]` prefix stays byte-identical. The request carries the `mid-conversation-tool-changes-2026-07-01` and
`inline-tools-2026-09-15` beta flags, which fits that reading. No tool from the deferred list was loaded in this session:
there are 0 `ToolSearch` calls. The 9 tool calls were `Bash` ×6, `Write` ×1, `Edit` ×2 [OBSERVED].

Also observed: there is no task/todo tool anywhere in the inventory, loaded or deferred. That is why the plan in Part I
lives in prose.

**Two tools.** Pick tools that differ from each other.

| | Tool 1 | Tool 2 |
|---|---|---|
| Name | `Bash` (execution; in this session it also did reads and some edits) | `ToolSearch` (meta-tool: loads other tools) |
| Key schema fields | `command` (string); `timeout` (number, ms, "max 600000 for a foreground command"); `description` (string, 5–10 words for the user); `run_in_background` (boolean); `dangerouslyDisableSandbox` (boolean). `additionalProperties: false`, `eager_input_streaming: true`. | `query` (string: `"select:Read,Edit"`, keywords, or `"+slack send"`); `max_results` (number, `default: 5`). `additionalProperties: false`. |
| Required vs. optional vs. not exposed, and why | Required: `command` only. Everything else is optional with harness-side defaults (timeout 120000 ms). Not exposed: working directory, environment variables, stdin, and shell choice. The harness owns the cwd ("`cd` carries to the next call only in the main session, if the command succeeds and ends inside the working directories") and the shell ("initialized from the user's profile"). Sandboxing is on by default, and leaving it takes an explicit, alarmingly named flag. | Required: **both** `query` and `max_results`, even though `max_results` declares `default: 5`. Requiring it forces the model to choose a result budget on every call [INFERRED]. Not exposed: any way to list all tools, which isn't needed because the names are already in a system message, or to call the loaded tool. The result is text, a `<functions>` block in a `tool_result`, not a change to `tools[]`. |
| Description is defending against… (quote + the wrong behavior) | *"GitHub notifies the owner of any `@name` written in a PR, issue, or comment. Write a bare `@name` only for a real login you mean to notify. Put roles, placeholders, and code (`@human`, `@reviewer`, `@types/node`) in backticks or drop the `@`."* Wrong behavior: the model wrote placeholder or package names like `@reviewer` and `@types/node` into PR bodies, and GitHub pinged real people with those logins. Also: *"You will be notified when it exits — do not poll its output file while waiting. Foreground `sleep` is blocked"*: the model kept running `sleep`/`cat` loops on background jobs, burning turns. In the `description` param: *"do not echo the command's text, its flags, or file paths"*: descriptions that only restated the command, which is useless to a user reading the permission prompt. | The listing in the system message: *"Their schemas are NOT loaded — calling them directly will fail with InputValidationError. Use ToolSearch with query "select:<name>[,<name>...]" … before calling them."* Wrong behavior: the model saw a tool's name, guessed its parameters, and called it directly. The stub's own description, *"Reserved placeholder that keeps deferred tool loading active; never call this tool"*, defends against the model calling an empty-schema tool just because it is in `tools[]`. |
| Deliberately does *not* do… and what that implies | No interactive programs (*"Interactive flags (`-i`, e.g. `git rebase -i`, `git add -i`) are not supported"*), no persistent shell state (*"Shell state (env vars, functions) does not persist"*), no guarantee the user sees output (*"displayed to you, not reliably to the user"*), and no committing unless asked (*"Commit or push only when the user asks"*). Implies the safety layer sits **outside** the tool: each call is judged on its own. The request has a `safeguards: [{type: "dangerous_tool_use", classifier_context: {permission_mode: "auto", …}}]` field, and `cd` in a compound command "can trigger a permission prompt". Every call must be self-contained so that judgment is possible [INFERRED]. | Doesn't execute anything, and doesn't add the tool to `tools[]`. Implies the harness treats `tools[]` as a cache prefix that must stay byte-stable for the whole session. Rarely used capabilities (46 tools, including all of Drive) are paid for as one name per line and loaded into the message stream only when needed. That is also why the 3 late MCP tools arrive as `tool_addition` [INFERRED]. |

Why these two?
> They show two different contracts. `Bash` is the general-purpose actuator: it can do almost anything, so its
> description is mostly prohibitions and output-handling rules. In this session it handled 6 of 9 tool calls,
> including file reads and test edits that `Read`/`Edit` could have done. `ToolSearch` does nothing in the world. It
> exists to keep the 15-entry `tools[]` prefix small and stable while 46 more tools stay reachable. Its failure
> contract is unusual: a call is invalid not because of bad arguments but because a schema hasn't been fetched yet.
> Together they show the main tension in the design: the agent needs broad power, but a large, stable, cached context
> is expensive. The `Artifact` tool alone has a 21,842-character description, the largest in `tools[]`.


## Part IV: Behavioral Analysis

**Every answer must be labeled `[OBSERVED]` or `[INFERRED]` and cite its evidence. Unlabeled answers earn no credit.**

**a. Error recovery**: `TODO: label` · evidence: `TODO`

What the agent saw, verbatim:
```
TODO
```
What it tried next, and turns to recover:
> TODO

**b. Planning**: `TODO: label` · evidence: `TODO`
> TODO

**c. Plans and task state**: `TODO: label` · evidence: `TODO` \
How does one get created and advanced? What does the model see about task state each turn, and where does it live in the request:
> TODO

**d. Subagents**: `TODO: label` · evidence: `TODO` \
When the agent delegates, what the subagent is told, and what comes back:
> TODO

**e. Context management**: `TODO: label` · evidence: `TODO` \
What changed in the payloads as the session grew:
> TODO


## Part V: Reflection

**Two decisions you would copy**, and the problem each solves:
1. TODO
2. TODO

**One you would make differently** (engage with why it might be there):
> TODO

**One thing the trace changed** about how you will steer a coding agent:
> TODO


## Submission
1. `Command (⌘) + F` for `TODO`. No results means you're done.
2. Confirm no credentials or `x-api-key` headers made it into your quoted excerpts.
3. Push all changes to your remote repository and submit via Gradescope.
4. Don't forget to remove `ANTHROPIC_BASE_URL` from your repo's `.claude/settings.json`!
