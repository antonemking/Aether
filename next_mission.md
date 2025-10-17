# Next Mission

Enable Python-defined tools to execute through the Zig runtime so we can power real agent workflows (LangGraph, Autogen, etc.) without rewriting everything in Zig.

## Success Criteria

- Python tools registered via `@runtime.tool` run when the executor dispatches them, using the same scheduling and binary envelope as native tools.
- Zig can call back into Python safely (bounded queue + callback pointer), with clear ownership of memory and error propagation.
- Provide a toy example that mixes native tools and Python tools and demonstrates concurrency gains over a pure-Python baseline.
- Document the integration flow and usage in `docs/usage/` or README so early adopters can try it.

## Immediate Actions

1. Extend the FFI to accept a Python callback pointer/context during `aether_create_runtime`.
2. Wire Zig's `dispatch` to call back into Python via a registered callback (initially synchronous; introduce a queue/worker pool in a follow-up).
3. Update `python/src/aether/runtime.py` so the decorator registers tools and supplies the callback; handle marshaling to/from the binary envelope for Python functions.
4. Build a small example script (e.g., fetch URL + parse JSON) that runs under the runtime and compare to a Python-only implementation.
