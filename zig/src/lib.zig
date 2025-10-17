const std = @import("std");

pub const ToolId = enum(u16) {
    mock_sleep = 0,
    cpu_spin = 1,
};

pub const ToolCall = struct {
    tool_id: ToolId,
    payload: u64, // milliseconds for the mock sleep tool
};

pub const ToolResult = struct {
    tool_id: ToolId,
    output: u64,
    elapsed_ns: u64,
};

const ToolFn = *const fn (*Runtime, ToolCall) anyerror!ToolResult;
const ToolRegistry = std.EnumArray(ToolId, ?ToolFn);

pub const Runtime = struct {
    allocator: std.mem.Allocator,
    tools: ToolRegistry,

    pub fn init(allocator: std.mem.Allocator) !*Runtime {
        var runtime = try allocator.create(Runtime);
        runtime.* = .{
            .allocator = allocator,
            .tools = ToolRegistry.initFill(null),
        };

        runtime.registerBuiltins();
        return runtime;
    }

    pub fn deinit(self: *Runtime) void {
        self.tools = ToolRegistry.initFill(null);
        self.allocator.destroy(self);
    }

    pub fn registerTool(self: *Runtime, id: ToolId, func: ToolFn) void {
        self.tools.set(id, @as(?ToolFn, func));
    }

    pub fn executeBatch(self: *Runtime, calls: []const ToolCall) ![]ToolResult {
        if (calls.len == 0) {
            return self.allocator.alloc(ToolResult, 0);
        }

        var results = try self.allocator.alloc(ToolResult, calls.len);
        errdefer self.allocator.free(results);

        var errors = try self.allocator.alloc(?anyerror, calls.len);
        defer self.allocator.free(errors);
        for (errors) |*err_slot| err_slot.* = null;

        var threads = try self.allocator.alloc(std.Thread, calls.len);
        defer self.allocator.free(threads);

        for (calls, 0..) |call, idx| {
            threads[idx] = try std.Thread.spawn(.{}, threadRunner, .{ThreadData{
                .runtime = self,
                .call = call,
                .result_ptr = &results[idx],
                .error_ptr = &errors[idx],
            }});
        }

        for (threads) |*handle| {
            handle.join();
        }

        for (errors) |maybe_err| {
            if (maybe_err) |err| {
                return err;
            }
        }

        return results;
    }

    fn dispatch(self: *Runtime, call: ToolCall) !ToolResult {
        const maybe_tool = self.tools.get(call.tool_id);
        if (maybe_tool) |tool_fn| {
            return tool_fn(self, call);
        }
        return error.ToolNotRegistered;
    }

    fn registerBuiltins(self: *Runtime) void {
        self.registerTool(.mock_sleep, mockSleepTool);
        self.registerTool(.cpu_spin, cpuSpinTool);
    }
};

const ThreadData = struct {
    runtime: *Runtime,
    call: ToolCall,
    result_ptr: *ToolResult,
    error_ptr: *?anyerror,
};

fn threadRunner(data: ThreadData) void {
    const res = data.runtime.dispatch(data.call);
    if (res) |value| {
        data.result_ptr.* = value;
    } else |err| {
        data.error_ptr.* = err;
    }
}

fn mockSleepTool(_: *Runtime, call: ToolCall) anyerror!ToolResult {
    var timer = try std.time.Timer.start();
    // Convert payload (ms) to nanoseconds, guard against overflow.
    const ns = std.math.mul(u64, call.payload, std.time.ns_per_ms) catch return error.InvalidPayload;
    std.time.sleep(ns);
    const elapsed = timer.read();
    return ToolResult{
        .tool_id = call.tool_id,
        .output = call.payload,
        .elapsed_ns = elapsed,
    };
}

fn cpuSpinTool(_: *Runtime, call: ToolCall) anyerror!ToolResult {
    var timer = try std.time.Timer.start();
    var acc: u64 = 1469598103934665603; // FNV offset basis for mixing
    var i: u64 = 0;
    const iterations = call.payload;
    while (i < iterations) : (i += 1) {
        acc = std.math.rotl(u64, acc ^ i, 5) *% 1099511628211;
    }
    const elapsed = timer.read();
    return ToolResult{
        .tool_id = call.tool_id,
        .output = acc,
        .elapsed_ns = elapsed,
    };
}

pub fn initRuntime(allocator: std.mem.Allocator) !*Runtime {
    return Runtime.init(allocator);
}

pub fn deinitRuntime(runtime: *Runtime) void {
    runtime.deinit();
}
