# Phase 6 Plan: Knowledge Graph and Entity Workflow

## Objective

Preserve palace structure, entity workflows, and cross-room relationships while making graph persistence and traversal explicit in Rust.

## Dependencies

- Phase 2 graph-capable storage is ready.
- Phase 4 ingest emits the metadata required for graph derivation.
- Phase 5 search and layered memory can consume graph context.

## Implementation Workstreams

### 1. Entity Detection

- Port entity detection heuristics from Python.
- Keep deterministic behavior on fixtures.
- Define false-positive and false-negative tradeoffs where exact parity is not practical.

### 2. Entity Registry Persistence

- Port entity registry reads and writes.
- Define schema-backed storage instead of loose metadata blobs.

### 3. Palace Graph Derivation

- Port hall, room, and tunnel derivation.
- Preserve meaningful parity with the Python palace graph on fixture inputs.

### 4. Graph Traversal and Query APIs

- Implement traversal APIs used by search, wake-up, and MCP layers.
- Keep traversal order and duplicate handling deterministic.

### 5. Onboarding and Scope Boundaries

- Port onboarding-derived setup behavior only if it remains in release scope.
- Explicitly document that automatic Wikipedia or network-based enrichment is not part of Rust v1.

## Deliverables

- Entity detection module
- Entity registry persistence layer
- Graph derivation module
- Graph traversal APIs
- Scope note for onboarding-derived behavior and non-networked entity rules

## To-Do Checklist

- [ ] Port entity detection heuristics.
- [ ] Define entity identity and persistence schema.
- [ ] Implement entity registry reads and writes.
- [ ] Port hall derivation logic.
- [ ] Port room derivation logic.
- [ ] Port tunnel derivation logic.
- [ ] Implement duplicate relation handling.
- [ ] Implement traversal queries.
- [ ] Define traversal ordering rules.
- [ ] Port onboarding-derived setup behavior if retained.
- [ ] Document non-support for automatic Wikipedia enrichment.
- [ ] Add entity detection fixture tests.
- [ ] Add registry persistence tests.
- [ ] Add graph edge creation tests.
- [ ] Add palace graph tunnel parity tests.
- [ ] Add duplicate relation tests.
- [ ] Add traversal query tests.
- [ ] Add negative tests proving no network lookups occur.

## Exit Gates

- Entity and graph suites pass on the fixture corpus.
- Palace graph derivation is stable and deterministic.
- Non-networked entity policy is documented and enforced by tests.

## Risks To Watch

- Letting graph semantics drift because fixtures only cover search behavior.
- Hidden Python dependence on external lookup artifacts.
- Weak duplicate handling causing graph explosion over repeated ingest runs.
