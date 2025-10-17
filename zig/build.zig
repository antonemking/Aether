const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const lib = b.addStaticLibrary(.{
        .name = "aether",
        .target = target,
        .optimize = optimize,
    });

    lib.addIncludePath(.{ .path = "src" });
    lib.addModule("core", .{ .source_file = .{ .path = "src/lib.zig" } });

    b.installArtifact(lib);
}
