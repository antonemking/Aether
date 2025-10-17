"""Helpers for the binary envelope shared with the Zig core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping

import ctypes
import struct


# Layout mirrors `zig/src/ffi/exports.zig`.
_HEADER = struct.Struct("<II")
_CALL = struct.Struct("<HHxxxxQ")


class PythonCall(ctypes.Structure):
    _fields_ = [
        ("tool_id", ctypes.c_uint16),
        ("reserved", ctypes.c_uint16),
        ("payload", ctypes.c_uint64),
    ]


class PythonResult(ctypes.Structure):
    _fields_ = [
        ("status", ctypes.c_uint16),
        ("reserved", ctypes.c_uint16),
        ("output", ctypes.c_uint64),
        ("error_code", ctypes.c_int32),
    ]


ToolCallback = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.POINTER(PythonCall),
    ctypes.POINTER(PythonResult),
)


class ResultBuffer(ctypes.Structure):
    _fields_ = [
        ("ptr", ctypes.POINTER(ctypes.c_uint8)),
        ("len", ctypes.c_size_t),
        ("count", ctypes.c_size_t),
    ]


class FfiToolResult(ctypes.Structure):
    _fields_ = [
        ("tool_id", ctypes.c_uint16),
        ("status", ctypes.c_uint16),
        ("output", ctypes.c_uint64),
        ("elapsed_ns", ctypes.c_uint64),
        ("error_code", ctypes.c_int32),
        ("reserved", ctypes.c_int32),
    ]


@dataclass
class EncodedBatch:
    buffer: ctypes.Array[ctypes.c_char]
    pointer: ctypes.c_void_p
    length: int
    count: int


@dataclass
class ToolExecution:
    tool_id: int
    status: int
    output: int
    elapsed_ns: int
    error_code: int


def encode_calls(calls: Iterable[Mapping[str, int]]) -> EncodedBatch:
    """Convert Python call descriptors into a native buffer pointer and length."""

    call_list = list(calls)
    count = len(call_list)
    total_size = _HEADER.size + count * _CALL.size
    buf = ctypes.create_string_buffer(total_size)

    _HEADER.pack_into(buf, 0, count, 0)

    offset = _HEADER.size
    for call in call_list:
        try:
            tool_id = int(call["tool_id"])
            payload = int(call.get("payload", 0))
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Each call must include integer 'tool_id' and numeric 'payload'") from exc

        _CALL.pack_into(buf, offset, tool_id, 0, payload)
        offset += _CALL.size

    pointer = ctypes.c_void_p(ctypes.addressof(buf))
    return EncodedBatch(buffer=buf, pointer=pointer, length=total_size, count=count)


def decode_results(buffer: ResultBuffer) -> List[ToolExecution]:
    """Convert a native buffer pointer back into Python objects."""

    if not buffer.ptr or buffer.count == 0:
        return []

    array_type = FfiToolResult * buffer.count
    results_array = ctypes.cast(buffer.ptr, ctypes.POINTER(array_type)).contents

    executions: List[ToolExecution] = []
    for entry in results_array:
        executions.append(
            ToolExecution(
                tool_id=int(entry.tool_id),
                status=int(entry.status),
                output=int(entry.output),
                elapsed_ns=int(entry.elapsed_ns),
                error_code=int(entry.error_code),
            )
        )

    return executions


__all__ = [
    "PythonCall",
    "PythonResult",
    "ToolCallback",
    "EncodedBatch",
    "ResultBuffer",
    "ToolExecution",
    "encode_calls",
    "decode_results",
]
