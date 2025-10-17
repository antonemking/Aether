const std = @import("std");
const c = std.c;

pub const ToolId = u16;

pub const ToolCall = struct {
    tool_id: ToolId,
    payload: u64,
};

pub const ToolResult = struct {
    tool_id: ToolId,
    status: u16 = 0,
    error_code: i32 = 0,
    output: u64 = 0,
    elapsed_ns: u64 = 0,
};

pub const PythonCall = extern struct {
    tool_id: ToolId,
    reserved: u16 = 0,
    payload: u64,
};

pub const PythonResult = extern struct {
    status: u16,
    reserved: u16 = 0,
    output: u64,
    error_code: i32,
};

pub const PythonCallback = ?*const fn (?*anyopaque, *const PythonCall, *PythonResult) callconv(.C) c_int;

const ToolFn = *const fn (*Runtime, ToolCall) anyerror!ToolResult;
const ToolMap = std.AutoHashMap(ToolId, ToolFn);

pub const TOOL_ID_SLEEP: ToolId = 0;
pub const TOOL_ID_CPU_SPIN: ToolId = 1;
pub const PYTHON_TOOL_BASE: ToolId = 1000;

pub const Runtime = struct {
    allocator: std.mem.Allocator,
    native_tools: ToolMap,
    python_callback: PythonCallback,
    python_context: ?*anyopaque,

    pub fn init(
        allocator: std.mem.Allocator,
        python_callback: PythonCallback,
        python_context: ?*anyopaque,
    ) !*Runtime {
        var native_tools = ToolMap.init(allocator);
        errdefer native_tools.deinit();

        var runtime = try allocator.create(Runtime);
        runtime.* = .{
            .allocator = allocator,
            .native_tools = native_tools,
            .python_callback = python_callback,
            .python_context = python_context,
        };

        try runtime.registerBuiltins();
        return runtime;
    }

    pub fn deinit(self: *Runtime) void {
        self.native_tools.deinit();
        self.allocator.destroy(self);
    }

    fn registerBuiltins(self: *Runtime) !void {
        try self.registerNative(TOOL_ID_SLEEP, mockSleepTool);
        try self.registerNative(TOOL_ID_CPU_SPIN, cpuSpinTool);
    }

    pub fn registerNative(self: *Runtime, id: ToolId, func: ToolFn) !void {
        try self.native_tools.put(id, func);
    }

    pub fn executeBatch(self: *Runtime, calls: []const ToolCall) ![]ToolResult {
        var results = try self.allocator.alloc(ToolResult, calls.len);
        errdefer self.allocator.free(results);

        if (calls.len == 0) {
            return results;
        }

        var threads = try self.allocator.alloc(std.Thread, calls.len);
        defer self.allocator.free(threads);

        for (calls, 0..) |call, idx| {
            threads[idx] = try std.Thread.spawn(.{}, threadRunner, .{ThreadData{
                .runtime = self,
                .call = call,
                .result_ptr = &results[idx],
            }});
        }

        for (threads) |*handle| {
            handle.join();
        }

        return results;
    }

    fn threadRunner(data: ThreadData) void {
        const runtime = data.runtime;
        const call = data.call;

        const result = runtime.dispatch(call) catch |err| runtime.errorResult(call.tool_id, err);
        data.result_ptr.* = result;
    }

    fn dispatch(self: *Runtime, call: ToolCall) anyerror!ToolResult {
        if (self.native_tools.get(call.tool_id)) |tool_fn| {
            return tool_fn(self, call);
        }

        if (call.tool_id >= PYTHON_TOOL_BASE) {
            return self.invokePython(call);
        }

        return error.ToolNotRegistered;
    }

    fn invokePython(self: *Runtime, call: ToolCall) ToolResult {
        if (self.python_callback == null) {
            return self.errorResult(call.tool_id, error.ToolNotRegistered);
        }

        var timer = std.time.Timer.start() catch {
            return self.errorResult(call.tool_id, error.TimerFailure);
        };

        var py_call = PythonCall{
            .tool_id = call.tool_id,
            .payload = call.payload,
        };
        var py_result = PythonResult{
            .status = 1,
            .output = 0,
            .error_code = 0,
        };

        const rc = self.python_callback.?(self.python_context, &py_call, &py_result);
        const elapsed = timer.read();

        if (rc != 0) {
            return ToolResult{
                .tool_id = call.tool_id,
                .status = 1,
                .error_code = rc,
                .output = py_result.output,
                .elapsed_ns = elapsed,
            };
        }

        return ToolResult{
            .tool_id = call.tool_id,
            .status = py_result.status,
            .error_code = py_result.error_code,
            .output = py_result.output,
            .elapsed_ns = elapsed,
        };
    }

    fn errorResult(self: *Runtime, tool_id: ToolId, err: anyerror) ToolResult {
        _ = self;
        return ToolResult{
            .tool_id = tool_id,
            .status = 1,
            .error_code = errorToCode(err),
            .output = 0,
            .elapsed_ns = 0,
        };
    }
};

const ThreadData = struct {
    runtime: *Runtime,
    call: ToolCall,
    result_ptr: *ToolResult,
};

fn mockSleepTool(_: *Runtime, call: ToolCall) anyerror!ToolResult {
    var timer = try std.time.Timer.start();
    const ns = std.math.mul(u64, call.payload, std.time.ns_per_ms) catch return error.InvalidPayload;
    std.time.sleep(ns);
    const elapsed = timer.read();
    return ToolResult{
        .tool_id = call.tool_id,
        .status = 0,
        .error_code = 0,
        .output = call.payload,
        .elapsed_ns = elapsed,
    };
}

fn cpuSpinTool(_: *Runtime, call: ToolCall) anyerror!ToolResult {
    var timer = try std.time.Timer.start();
    var acc: u64 = 1469598103934665603;
    var i: u64 = 0;
    const iterations = call.payload;
    while (i < iterations) : (i += 1) {
        acc = std.math.rotl(u64, acc ^ i, 5) *% 1099511628211;
    }
    const elapsed = timer.read();
    return ToolResult{
        .tool_id = call.tool_id,
        .status = 0,
        .error_code = 0,
        .output = acc,
        .elapsed_ns = elapsed,
    };
}

pub fn initRuntime(
    allocator: std.mem.Allocator,
    python_callback: PythonCallback,
    python_context: ?*anyopaque,
) !*Runtime {
    return Runtime.init(allocator, python_callback, python_context);
}

pub fn deinitRuntime(runtime: *Runtime) void {
    runtime.deinit();
}

pub fn errorToCode(err: anyerror) i32 {
    return switch (err) {
        error.InvalidPayload => 2001,
        error.ToolNotRegistered => 2002,
        error.TimerFailure => 2003,
        else => 2999,
    };
}
