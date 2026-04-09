# Phase 8 Plan: MCP Server

## Objective

Provide a Rust MCP server that is contract-compatible with MemPalace clients and stable under real stdio lifecycle conditions.

## Dependencies

- Phase 0 MCP contract goldens are available.
- Phase 5 search and wake-up flows are implemented.
- Phase 6 graph APIs are available for graph-related tools.
- Phase 7 AAAK support is available for AAAK-related tools.

## Implementation Workstreams

### 1. Server and Tool Registration

- Implement MCP server bootstrapping and tool registration.
- Match the documented tool surface exactly unless an intentional scope change has been approved.

### 2. Tool Porting

- Port status and taxonomy tools.
- Port search, wake-up, and layer tools.
- Port graph and knowledge-graph tools.
- Port diary tools.
- Port write and delete tools if they remain in scope.

### 3. Error Mapping

- Define structured error mapping so invalid input and internal failures are distinguishable.
- Keep response shapes contract-testable.

### 4. Lifecycle and Concurrency

- Prove stdio startup, steady-state operation, and shutdown behavior with a real harness.
- Validate behavior under concurrent writes, ingest, and reads where supported.

## Deliverables

- Rust MCP server crate
- Tool registration implementation
- Ported tool handlers
- Structured error mapping
- Client harness-based integration tests

## To-Do Checklist

- [ ] Implement MCP server bootstrap.
- [ ] Implement tool registration.
- [ ] Match registered tool names to the approved contract.
- [ ] Port status and taxonomy tools.
- [ ] Port search tool.
- [ ] Port wake-up and layer tools.
- [ ] Port graph and knowledge-graph tools.
- [ ] Port diary tools.
- [ ] Decide whether write/delete tools remain in scope.
- [ ] Port write/delete tools if retained.
- [ ] Implement request decoding.
- [ ] Implement response encoding.
- [ ] Implement structured error mapping.
- [ ] Implement invalid input handling.
- [ ] Add MCP contract tests.
- [ ] Add invalid input tests.
- [ ] Add tool output shape tests.
- [ ] Add tool-surface completeness tests.
- [ ] Add startup and shutdown tests.
- [ ] Add concurrent MCP write-versus-ingest tests.

## Exit Gates

- MCP integration suite passes against a real client harness.
- Tool surface matches the approved contract.
- Lifecycle behavior is stable under stdio execution.

## Risks To Watch

- Passing shape tests while silently dropping tool coverage.
- Weak lifecycle testing that misses real stdio shutdown bugs.
- Scope drift around write/delete tools without explicit documentation.
