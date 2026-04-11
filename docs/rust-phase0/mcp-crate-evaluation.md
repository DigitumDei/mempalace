# MCP Crate Evaluation

## Initial Choice

Use `rmcp` as the initial Rust MCP server implementation.

## Why `rmcp`

- Rust-native implementation rather than a thin wrapper around a foreign runtime
- Suitable for explicit tool registration and request/response schema control
- Good fit for stdio server transport, which matches the current Python server shape
- Easier to test as a crate-level component during Phase 8

## Contract Expectations

The chosen crate must support:

- stdio transport
- deterministic tool registration
- JSON-schema-like argument definitions
- structured error responses
- startup/shutdown behavior that can be exercised in integration tests

## Fallback Criteria

Switch away from `rmcp` if any of these fail during contract testing:

- cannot represent the full current tool set without custom protocol shims
- cannot preserve current request field names and response envelope shape closely enough
- cannot run reliably over stdio in CI integration tests
- requires unstable dependencies or a maintenance posture that makes release risk unacceptable

## Fallback Options

- another actively maintained Rust MCP crate with stdio support
- a small internal MCP adapter crate if third-party crates fail protocol and test requirements

The fallback decision is implementation-time operational, not product-time semantic. Tool names and payload shapes stay governed by the parity matrix.
