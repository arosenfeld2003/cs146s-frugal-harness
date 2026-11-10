# Rust Learning Log

I'm learning Rust by building this harness. This log records concepts as I actually run into them,
with the code that taught them. It's not a tutorial; it's a trail.

**Format per entry:** concept → where it came up → what clicked → open questions.

**Resources:** [The Rust Book](https://doc.rust-lang.org/book/) · [Rust by Example](https://doc.rust-lang.org/rust-by-example/) ·
[Tokio tutorial](https://tokio.rs/tokio/tutorial) · `rustc --explain E0382` (every error code has a built-in explanation)

---

## M0: Setup

### Cargo: the build tool and package manager in one
- **Where:** `cargo new harness`, `cargo run`
- **What clicked:**
  - `Cargo.toml` declares dependencies (like `pyproject.toml`).
  - `Cargo.lock` pins exact versions (like `poetry.lock`). Commit it for binaries.
  - `target/` holds build output (gitignored).
  - Python needed conda + Poetry + a virtualenv. Rust needs only `cargo`.
- **Versions:** rustc / cargo 1.94.1

### Ownership, a first look (E0382)
- **Where:** the sidecar smoke test happened to summarize this compiler error:
  `error[E0382]: borrow of moved value: cfg`, where the value had been moved into a closure on line 38.
- **What it means:** every value has exactly one owner. Passing `cfg` into a closure (or a function) by
  value *moves* it, and the original name can't be used afterwards. The fixes are:
  - borrow instead (`&cfg`)
  - `cfg.clone()`
  - share it with `Arc<Config>` when several async tasks need it
- **Why it matters here:** the harness will pass config, HTTP clients, and the message history into async
  tasks. Deciding who *owns* the conversation history is a real design question, not just a compiler complaint.
- **Open question:** when should the history live in an `Arc<Mutex<…>>`, and when should it be passed by `&mut`?

---

## M2 preview: concepts the harness v0 will need

| Concept | Where it shows up | Python equivalent |
|---|---|---|
| `enum` with data + `match` | Message content blocks: `Text`, `ToolUse`, `ToolResult` | dict with a `"type"` key + if/elif |
| `serde` derive (`Serialize`/`Deserialize`) | Anthropic / OpenAI JSON ↔ Rust types | `json.loads` + Pydantic |
| `Result<T, E>` + `?` | Every HTTP call, file read, tool run | exceptions |
| `anyhow` / `thiserror` | App-level vs library-level errors | `Exception` subclasses |
| `async`/`await` + `tokio` | Streaming responses, parallel tool calls | `asyncio` |
| traits (`trait Provider`) | Claude vs llama-server behind one interface | ABC / Protocol |
| `Box<dyn Trait>` vs generics | Choosing a provider at runtime from config | duck typing |
| lifetimes (`&'a str`) | Probably avoidable at first: own `String`s, clone freely, optimize later | n/a |

**Beginner strategy (deliberate):** clone freely, use `String` over `&str` in structs, and use `anyhow`
everywhere at first. Get it working, then let the compiler and `cargo clippy` teach the tighter version.

---

## Entry template

```markdown
### <concept>
- **Where:** <file:line or milestone task>
- **What clicked:** <one or two sentences, in my own words>
- **Code:** <smallest snippet that shows it>
- **Python comparison:** <how I'd have done it in Python, and what's different>
- **Open questions:** <what I still don't get>
```
