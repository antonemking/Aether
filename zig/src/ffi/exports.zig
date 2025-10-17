const std = @import("std");
const meta = std.meta;
const mem = std.mem;

const core = @import("core");

const ERR_INVALID_ENVELOPE: i32 = 1001;
const ERR_UNKNOWN_TOOL: i32 = 1002;
const ERR_INVALID_PAYLOAD: i32 = 1003;
const ERR_EXECUTION: i32 = 1004;
const ERR_ALLOC_FAILURE: i32 = 1005;

pub const BatchHeader = extern struct {
    call_count: u32,
    reserved: u32 = 0,
};

pub const FfiToolCall = extern struct {
    tool_id: u16,
    reserved: u16 = 0,
    payload: u64,
};

pub const FfiToolResult = extern struct {
    tool_id: u16,
    status: u16, // 0 = ok, 1 = error
    output: u64,
    elapsed_ns: u64,
    error_code: i32,
    reserved: i32 = 0,
};

pub const ResultBuffer = extern struct {
    ptr: ?[*]u8,
    len: usize, // number of bytes in the buffer
    count: usize, // number of FfiToolResult entries encoded in ptr
};

fn makeErrorBuffer(runtime: *core.Runtime, code: i32) ResultBuffer {
    const byte_len = @sizeOf(FfiToolResult);
    const allocator = runtime.allocator;

    const bytes = allocator.alloc(u8, byte_len) catch {
        return .{ .ptr = null, .len = 0, .count = 0 };
    };

    const slice = mem.bytesAsSlice(FfiToolResult, bytes);
    slice[0] = .{
        .tool_id = 0,
        .status = 1,
        .output = 0,
        .elapsed_ns = 0,
        .error_code = code,
        .reserved = 0,
    };

    return .{ .ptr = bytes.ptr, .len = byte_len, .count = 1 };
}

fn successBuffer(runtime: *core.Runtime, results: []core.ToolResult) !ResultBuffer {
    defer runtime.allocator.free(results);

    if (results.len == 0) {
        return .{ .ptr = null, .len = 0, .count = 0 };
    }

    const byte_len: usize = @sizeOf(FfiToolResult) * results.len;
    const bytes = try runtime.allocator.alloc(u8, byte_len);
    const slice = mem.bytesAsSlice(FfiToolResult, bytes);

    for (results, slice) |result, *dest| {
        dest.* = .{
            .tool_id = @intFromEnum(result.tool_id),
            .status = 0,
            .output = result.output,
            .elapsed_ns = result.elapsed_ns,
            .error_code = 0,
            .reserved = 0,
        };
    }

    return .{ .ptr = bytes.ptr, .len = byte_len, .count = results.len };
}

fn mapExecutionError(err: anyerror) i32 {
    return switch (err) {
        error.ToolNotRegistered => ERR_UNKNOWN_TOOL,
        error.InvalidPayload => ERR_INVALID_PAYLOAD,
        else => ERR_EXECUTION,
    };
}

export fn aether_create_runtime() callconv(.C) ?*core.Runtime {
    return core.initRuntime(std.heap.c_allocator) catch null;
}

export fn aether_destroy_runtime(runtime: ?*core.Runtime) callconv(.C) void {
    if (runtime) |rt| {
        core.deinitRuntime(rt);
    }
}

export fn aether_execute(
    runtime_ptr: ?*core.Runtime,
    payload_ptr: ?*const u8,
    payload_len: usize,
) callconv(.C) ResultBuffer {
    if (runtime_ptr == null or payload_ptr == null or payload_len < @sizeOf(BatchHeader)) {
        return .{ .ptr = null, .len = 0, .count = 0 };
    }

    const runtime = runtime_ptr.?;
    const base_ptr: [*]const u8 = @ptrCast(payload_ptr.?);
    const payload = base_ptr[0..payload_len];

    const call_count = @as(usize, mem.readInt(u32, payload[0..4], .little));
    const calls_bytes_len = @sizeOf(FfiToolCall) * call_count;
    const required_len = @sizeOf(BatchHeader) + calls_bytes_len;

    if (payload_len < required_len) {
        return makeErrorBuffer(runtime, ERR_INVALID_ENVELOPE);
    }

    const call_bytes = payload[@sizeOf(BatchHeader)..required_len];
    const ffi_calls = mem.bytesAsSlice(FfiToolCall, call_bytes);

    const tool_calls = runtime.allocator.alloc(core.ToolCall, call_count) catch {
        return makeErrorBuffer(runtime, ERR_ALLOC_FAILURE);
    };
    defer runtime.allocator.free(tool_calls);

    for (ffi_calls, tool_calls) |ffi_call, *tool_call| {
        const tool_id = meta.intToEnum(core.ToolId, ffi_call.tool_id) catch {
            return makeErrorBuffer(runtime, ERR_UNKNOWN_TOOL);
        };

        tool_call.* = .{
            .tool_id = tool_id,
            .payload = ffi_call.payload,
        };
    }

    const results = runtime.executeBatch(tool_calls) catch |err| {
        return makeErrorBuffer(runtime, mapExecutionError(err));
    };

    return successBuffer(runtime, results) catch {
        return makeErrorBuffer(runtime, ERR_ALLOC_FAILURE);
    };
}

export fn aether_free_buffer(
    runtime_ptr: ?*core.Runtime,
    buffer: ResultBuffer,
) callconv(.C) void {
    if (runtime_ptr) |runtime| {
        if (buffer.ptr) |ptr| {
            const bytes = ptr[0..buffer.len];
            runtime.allocator.free(bytes);
        }
    }
}
