"""Helpers for the binary envelope shared with the Zig core."""

from __future__ import annotations


def encode_calls(calls) -> tuple[int, int]:
    """Convert Python call descriptors into a native buffer pointer and length."""
    _ = calls
    raise NotImplementedError("Binary envelope encoder not yet implemented.")


def decode_results(buffer_ptr: int):
    """Convert a native buffer pointer back into Python objects."""
    _ = buffer_ptr
    raise NotImplementedError("Binary envelope decoder not yet implemented.")
