"""Demonstrate mixing native Zig tools with Python-defined callbacks."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SRC = REPO_ROOT / "python" / "src"

if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from aether.runtime import AgentRuntime


def resolve_library() -> str:
    target = {
        "darwin": "libaether.dylib",
        "win32": "aether.dll",
    }.get(sys.platform, "libaether.so")
    return str(REPO_ROOT / "zig" / "zig-out" / "lib" / target)


def main() -> None:
    runtime = AgentRuntime(resolve_library())

    @runtime.tool("py_double")
    def py_double(value: int) -> int:
        return value * 2

    @runtime.tool("py_concat")
    def py_concat(prefix: str, suffix: str) -> str:
        return f"{prefix}{suffix}"

    calls = [
        {"name": "cpu_spin", "payload": 50_000},
        {"name": "py_double", "payload": 21},
        {"name": "py_concat", "payload": {"args": ["Hello, ", "Aether!"]}},
    ]

    results = runtime.execute(calls)
    for result in results:
        status = "ok" if result.status == 0 else f"error ({result.error_code})"
        print(f"{result.name:<10} -> {result.output!r} [{status}]")


if __name__ == "__main__":
    main()
