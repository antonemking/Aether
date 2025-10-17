"""Compare the Zig executor against a Python ThreadPool baseline."""

from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SRC = REPO_ROOT / "python" / "src"
ZIG_DIR = REPO_ROOT / "zig"

if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from aether.runtime import AgentRuntime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls", type=int, default=32, help="Number of tool calls to issue")
    parser.add_argument(
        "--payload",
        type=int,
        default=20,
        help="Payload value: milliseconds for sleep, iterations for CPU spin",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Repetitions for each benchmark to smooth out noise",
    )
    parser.add_argument(
        "--mode",
        choices=("sleep", "cpu"),
        default="sleep",
        help="Select the mock workload to run",
    )
    return parser.parse_args()


def ensure_library_path() -> Path:
    target = {
        "darwin": "libaether.dylib",
        "win32": "aether.dll",
    }.get(sys.platform, "libaether.so")

    subprocess.run(["zig", "build"], check=True, cwd=ZIG_DIR)

    lib_path = ZIG_DIR / "zig-out" / "lib" / target
    if not lib_path.exists():
        raise FileNotFoundError(f"Expected Zig library at {lib_path}")
    return lib_path


def build_calls(count: int, payload: int, mode: str) -> List[dict]:
    tool_id = 0 if mode == "sleep" else 1
    return [{"tool_id": tool_id, "payload": payload} for _ in range(count)]


def run_zig(runtime: AgentRuntime, calls: List[dict]) -> Tuple[float, List[int]]:
    start = time.perf_counter()
    results = runtime.execute(calls)
    total = time.perf_counter() - start
    elapsed = [res.elapsed_ns / 1_000_000 for res in results]
    return total, elapsed


def run_python_baseline(calls: List[dict], mode: str) -> Tuple[float, List[float]]:
    if mode == "sleep":
        def worker(payload_ms: int) -> float:
            start = time.perf_counter()
            time.sleep(payload_ms / 1000.0)
            return (time.perf_counter() - start) * 1000.0
    else:
        def worker(iterations: int) -> float:
            start = time.perf_counter()
            acc = 1469598103934665603
            for i in range(iterations):
                acc = ((acc ^ i) << 5 | (acc ^ i) >> (64 - 5)) & 0xFFFFFFFFFFFFFFFF
                acc = (acc * 1099511628211) & 0xFFFFFFFFFFFFFFFF
            _ = acc
            return (time.perf_counter() - start) * 1000.0

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(calls)) as executor:
        futures = [executor.submit(worker, call["payload"]) for call in calls]
        durations = [future.result() for future in futures]
    total = time.perf_counter() - start
    return total, durations


def summarize(name: str, totals: Iterable[float], per_call_ms: Iterable[float]) -> None:
    totals_ms = [t * 1000.0 for t in totals]
    print(f"{name} total   : {statistics.mean(totals_ms):8.2f} ms (σ={statistics.pstdev(totals_ms):.2f})")
    print(f"{name} per-call: {statistics.mean(per_call_ms):8.2f} ms")


def main() -> None:
    args = parse_args()
    calls = build_calls(args.calls, args.payload, args.mode)
    lib_path = ensure_library_path()

    runtime = AgentRuntime(str(lib_path))

    zig_totals: List[float] = []
    zig_per_call: List[float] = []
    py_totals: List[float] = []
    py_per_call: List[float] = []

    for _ in range(args.iterations):
        total, per_call = run_zig(runtime, calls)
        zig_totals.append(total)
        zig_per_call.extend(per_call)

        total_py, per_call_py = run_python_baseline(calls, args.mode)
        py_totals.append(total_py)
        py_per_call.extend(per_call_py)

    print(f"\n--- Benchmark Results ({args.mode}) ---")
    summarize("Zig", zig_totals, zig_per_call)
    summarize("Python", py_totals, py_per_call)

    speedup = statistics.mean(py_totals) / statistics.mean(zig_totals)
    print(f"Speedup (Python / Zig): {speedup:.2f}x")


if __name__ == "__main__":
    main()
