# Packaging And Validation

This document captures the practical release path for the current Rust workspace and separates code-frozen surfaces from environment-dependent signoff.

## Release Artifacts

Current artifact set:

- `mempalace-cli` release binary
- `mempalace-mcp` release binary

Build command:

```bash
cargo build --release -p mempalace-cli -p mempalace-mcp
```

Artifact paths:

- `mempalace-rs/target/release/mempalace-cli`
- `mempalace-rs/target/release/mempalace-mcp`

## Install Validation

Minimum install validation for a candidate release:

1. Build both release binaries.
2. Run `mempalace-cli --help`.
3. Run `mempalace-cli init <fixture-dir>`.
4. Run `mempalace-cli mine <fixture-dir>`.
5. Run `mempalace-cli search <query>`.
6. Run `mempalace-cli status`.
7. Run `mempalace-cli wake-up`.
8. Start `mempalace-mcp` and confirm MCP `initialize` plus `tools/list`.

## Validation Matrix

### Expected on a normal development VM

- unit tests
- integration tests that do not rely on special hardware or benchmark hosts
- debug and release builds
- basic install-flow checks

### Expected on the reference environment

- full regression suite
- benchmark suite
- low-CPU suite
- final signoff on warm-cache behavior and resource ceilings
- optional Python interop validation only if that feature is explicitly shipped

## Current Phase 12 Status

Completed in this branch:

- CLI surface freeze documented
- config schema freeze documented
- release scope and known limitations documented
- standard deployment operator guidance written
- low-CPU operator guidance written
- packaging artifact definition documented

Still environment-dependent:

- full benchmark signoff
- full low-CPU signoff
- any optional Python interop validation
- final release-candidate install checks on supported targets

## Release Decision Rule

Do not mark Rust v1 release-ready from this document alone.

Use this directory to freeze the release promise, then attach the actual regression, benchmark, and low-CPU evidence from the reference environment before publishing a release tag.
