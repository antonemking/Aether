"""Thin wrapper around the Zig runtime FFI."""

from __future__ import annotations

from ctypes import CDLL

from . import binary


class AgentRuntime:
    """Facade for registering tools and executing them via the Zig engine."""

    def __init__(self, lib_path: str = "./libaether.so") -> None:
        self._lib = CDLL(lib_path)
        self._tools = {}
        # TODO: load symbols and initialize runtime pointer.

    def tool(self, name: str):
        """Decorator to register a tool implementation."""

        def decorator(func):
            self._tools[name] = func
            return func

        return decorator

    def execute(self, calls):
        """Encode calls, forward them across the FFI boundary, and decode results."""
        payload_ptr, payload_len = binary.encode_calls(calls)
        _ = payload_ptr
        _ = payload_len
        raise NotImplementedError("FFI bridge not wired up yet.")
