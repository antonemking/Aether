const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const lib = b.addSharedLibrary(.{
        .name = "aether",
        .root_source_file = b.path("src/ffi/exports.zig"),
        .target = target,
        .optimize = optimize,
    });

    const core_module = b.addModule("core", .{
        .root_source_file = b.path("src/lib.zig"),
    });

    lib.root_module.addImport("core", core_module);

    b.installArtifact(lib);
}
