"""Thin wrapper around the Zig runtime FFI."""

from __future__ import annotations

from ctypes import CDLL, c_size_t, c_void_p

from . import binary
from .binary import EncodedBatch, ResultBuffer, ToolExecution


class AgentRuntime:
    """Facade for registering tools and executing them via the Zig engine."""

    def __init__(self, lib_path: str = "./libaether.so") -> None:
        self._lib = CDLL(lib_path)
        self._tools = {}
        self._configure_ffi()
        runtime_ptr = self._lib.aether_create_runtime()
        if not runtime_ptr:
            raise RuntimeError("Failed to initialize Aether runtime")
        self._runtime = c_void_p(runtime_ptr)

    def tool(self, name: str):
        """Decorator to register a tool implementation."""

        def decorator(func):
            self._tools[name] = func
            return func

        return decorator

    def execute(self, calls):
        """Encode calls, forward them across the FFI boundary, and decode results."""
        batch: EncodedBatch = binary.encode_calls(calls)
        buffer = self._lib.aether_execute(self._runtime, batch.pointer, c_size_t(batch.length))
        try:
            results = binary.decode_results(buffer)
        finally:
            self._lib.aether_free_buffer(self._runtime, buffer)

        for execution in results:
            if execution.status != 0:
                raise RuntimeError(
                    f"Tool {execution.tool_id} failed with code {execution.error_code}"
                )

        return results

    def _configure_ffi(self) -> None:
        self._lib.aether_create_runtime.restype = c_void_p
        self._lib.aether_create_runtime.argtypes = []

        self._lib.aether_destroy_runtime.restype = None
        self._lib.aether_destroy_runtime.argtypes = [c_void_p]

        self._lib.aether_execute.restype = ResultBuffer
        self._lib.aether_execute.argtypes = [c_void_p, c_void_p, c_size_t]

        self._lib.aether_free_buffer.restype = None
        self._lib.aether_free_buffer.argtypes = [c_void_p, ResultBuffer]

    def __del__(self):
        runtime_ptr = getattr(self, "_runtime", None)
        if runtime_ptr:
            self._lib.aether_destroy_runtime(runtime_ptr)
