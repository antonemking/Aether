# Benchmarks

Performance experiments, comparison harnesses, and reporting utilities live here.

## Quick Start

Run the baseline comparison between the Zig executor and Python `ThreadPoolExecutor`:

```bash
python benchmarks/zig_vs_python.py --calls 32 --payload 20 --iterations 5 --mode sleep
```

The script will:

- Rebuild the Zig shared library (`zig build`).
- Execute a batch of mock sleep tools via the Aether runtime.
- Execute the same workload using a pure-Python thread pool.
- Report aggregate wall-clock times, per-call latencies, and the observed speedup.

Adjust `--calls`, `--payload`, `--mode`, and `--iterations` to explore different workload shapes as you iterate on the runtime. Use `--mode cpu` with `--payload <iterations>` to stress the runtime with CPU-bound work.

## Recorded Runs

| Mode  | Calls | Payload | Iterations | Zig total (ms) | Python total (ms) | Speedup |
|-------|-------|---------|------------|----------------|-------------------|---------|
| sleep | 32    | 20 ms   | 5          | 25.63          | 28.50             | 1.11×   |
| cpu   | 32    | 50 000  | 5          | 0.79           | 262.70            | 332.97× |

Notes:

- Sleep mode focuses on orchestration overhead; the per-call work is dominated by the OS wait, so the gap is modest.
- CPU mode exercises the native spin tool and highlights the advantage of running the heavy work in Zig rather than under the Python GIL.
