const std = @import("std");

pub const Runtime = struct {
    // TODO: wire up tool registry, executor, cache, and FFI-safe API surface.
};

pub fn initRuntime(allocator: std.mem.Allocator) !*Runtime {
    _ = allocator;
    return error.NotImplemented;
}
