"""Thin wrapper around the Zig runtime FFI."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

from ctypes import CDLL, POINTER, c_size_t, c_void_p

from . import binary

PYTHON_TOOL_BASE = 1000


_RUNTIME_REGISTRY: Dict[int, "AgentRuntime"] = {}


@dataclass
class ExecutionResult:
    name: str
    tool_id: int
    status: int
    output: Any
    elapsed_ns: int
    error_code: int


class AgentRuntime:
    """Facade for registering tools and executing them via the Zig engine."""

    def __init__(self, lib_path: str = "./libaether.so") -> None:
        self._lib = CDLL(lib_path)
        self._configure_ffi()

        self._tool_ids: Dict[str, int] = {
            "sleep_ms": 0,
            "cpu_spin": 1,
        }
        self._tool_names: Dict[int, str] = {0: "sleep_ms", 1: "cpu_spin"}
        self._python_tools: Dict[int, Callable[..., Any]] = {}
        self._next_tool_id = PYTHON_TOOL_BASE

        self._active_payloads: Optional[List[Tuple[List[Any], Dict[str, Any]]]] = None
        self._active_results: Optional[List[Any]] = None
        self._active_lock = threading.Lock()

        self._callback_fn = binary.ToolCallback(_python_callback_trampoline)
        self._context_token = id(self)
        _RUNTIME_REGISTRY[self._context_token] = self
        runtime_ptr = self._lib.aether_create_runtime(
            self._callback_fn,
            c_void_p(self._context_token),
        )
        if not runtime_ptr:
            raise RuntimeError("Failed to initialize Aether runtime")
        self._runtime = c_void_p(runtime_ptr)

    def tool(self, name: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a Python tool."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or func.__name__
            tool_id = self._next_tool_id
            self._next_tool_id += 1

            self._tool_ids[tool_name] = tool_id
            self._tool_names[tool_id] = tool_name
            self._python_tools[tool_id] = func
            return func

        return decorator

    def execute(self, calls: Iterable[Mapping[str, Any]]) -> List[ExecutionResult]:
        """Encode calls, forward them across the FFI boundary, and decode results."""

        prepared_calls, payloads = self._prepare_calls(calls)
        batch = binary.encode_calls(prepared_calls)

        with self._active_lock:
            self._active_payloads = payloads
            self._active_results = []

        buffer = self._lib.aether_execute(self._runtime, batch.pointer, c_size_t(batch.length))
        try:
            raw_results = binary.decode_results(buffer)
        finally:
            self._lib.aether_free_buffer(self._runtime, buffer)

        with self._active_lock:
            results_store = self._active_results or []
            self._active_payloads = None
            self._active_results = None

        final_results: List[ExecutionResult] = []
        for entry in raw_results:
            name = self._tool_names.get(entry.tool_id, f"tool:{entry.tool_id}")
            if entry.status == 0:
                if entry.tool_id >= PYTHON_TOOL_BASE:
                    output = results_store[entry.output] if entry.output < len(results_store) else None
                else:
                    output = entry.output
            else:
                if entry.tool_id >= PYTHON_TOOL_BASE and entry.output < len(results_store):
                    output = results_store[entry.output]
                else:
                    output = None
            final_results.append(
                ExecutionResult(
                    name=name,
                    tool_id=entry.tool_id,
                    status=entry.status,
                    output=output,
                    elapsed_ns=entry.elapsed_ns,
                    error_code=entry.error_code,
                )
            )

        errors = [res for res in final_results if res.status != 0]
        if errors:
            first = errors[0]
            raise RuntimeError(
                f"Tool '{first.name}' ({first.tool_id}) failed with code {first.error_code}"
            )

        return final_results

    def _prepare_calls(
        self, calls: Iterable[Mapping[str, Any]]
    ) -> Tuple[List[Dict[str, int]], List[Tuple[List[Any], Dict[str, Any]]]]:
        prepared: List[Dict[str, int]] = []
        payloads: List[Tuple[List[Any], Dict[str, Any]]] = []

        for call in calls:
            tool_id = self._resolve_tool_id(call)
            payload = call.get("payload")

            if tool_id >= PYTHON_TOOL_BASE:
                args, kwargs = _normalize_python_payload(payload)
                index = len(payloads)
                payloads.append((args, kwargs))
                prepared.append({"tool_id": tool_id, "payload": index})
            else:
                prepared.append({"tool_id": tool_id, "payload": int(payload or 0)})

        return prepared, payloads

    def _resolve_tool_id(self, call: Mapping[str, Any]) -> int:
        if "tool_id" in call:
            return int(call["tool_id"])
        name = call.get("name")
        if not isinstance(name, str):
            raise ValueError("Call must include 'name' or 'tool_id'")
        if name not in self._tool_ids:
            raise KeyError(f"Unknown tool '{name}'")
        return self._tool_ids[name]

    def _handle_python_call(
        self,
        call: binary.PythonCall,
        result_ptr: POINTER(binary.PythonResult),
    ) -> int:
        tool_id = int(call.tool_id)
        payload_index = int(call.payload)

        try:
            func = self._python_tools[tool_id]
        except KeyError:
            result_ptr.contents.status = 1
            result_ptr.contents.error_code = -404
            result_ptr.contents.output = 0
            return -1

        with self._active_lock:
            if (
                self._active_payloads is None
                or payload_index < 0
                or payload_index >= len(self._active_payloads)
            ):
                result_ptr.contents.status = 1
                result_ptr.contents.error_code = -400
                result_ptr.contents.output = 0
                return -1
            args, kwargs = self._active_payloads[payload_index]

        try:
            output = func(*args, **kwargs)
            with self._active_lock:
                if self._active_results is None:
                    self._active_results = []
                self._active_results.append(output)
                result_index = len(self._active_results) - 1
            result_ptr.contents.status = 0
            result_ptr.contents.error_code = 0
            result_ptr.contents.output = result_index
            return 0
        except Exception as exc:  # pylint: disable=broad-except
            with self._active_lock:
                if self._active_results is None:
                    self._active_results = []
                self._active_results.append(exc)
                result_index = len(self._active_results) - 1
            result_ptr.contents.status = 1
            result_ptr.contents.error_code = -500
            result_ptr.contents.output = result_index
            return -1

    def _configure_ffi(self) -> None:
        self._lib.aether_create_runtime.restype = c_void_p
        self._lib.aether_create_runtime.argtypes = [binary.ToolCallback, c_void_p]

        self._lib.aether_destroy_runtime.restype = None
        self._lib.aether_destroy_runtime.argtypes = [c_void_p]

        self._lib.aether_execute.restype = binary.ResultBuffer
        self._lib.aether_execute.argtypes = [c_void_p, c_void_p, c_size_t]

        self._lib.aether_free_buffer.restype = None
        self._lib.aether_free_buffer.argtypes = [c_void_p, binary.ResultBuffer]

    def __del__(self) -> None:
        runtime_ptr = getattr(self, "_runtime", None)
        if runtime_ptr:
            self._lib.aether_destroy_runtime(runtime_ptr)
        token = getattr(self, "_context_token", None)
        if token is not None:
            _RUNTIME_REGISTRY.pop(token, None)


def _normalize_python_payload(payload: Any) -> Tuple[List[Any], Dict[str, Any]]:
    if payload is None:
        return [], {}
    if isinstance(payload, dict) and ("args" in payload or "kwargs" in payload):
        args = list(payload.get("args", []))
        kwargs = dict(payload.get("kwargs", {}))
        return args, kwargs
    if isinstance(payload, (list, tuple)):
        return list(payload), {}
    return [payload], {}


def _python_callback_trampoline(
    context: c_void_p,
    call_ptr: POINTER(binary.PythonCall),
    result_ptr: POINTER(binary.PythonResult),
) -> int:
    token = int(context)
    runtime = _RUNTIME_REGISTRY.get(token)
    if runtime is None:
        result_ptr.contents.status = 1
        result_ptr.contents.error_code = -410
        result_ptr.contents.output = 0
        return -1
    return runtime._handle_python_call(call_ptr.contents, result_ptr)
