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

## Scope Decisions

### Onboarding-Derived Setup

Retained in release scope as a typed registry seeding path only.

- Rust Phase 6 keeps onboarding-derived people, project, alias, and relationship data when it is
  provided explicitly by the user or higher layers.
- Phase 6 does not implement an interactive onboarding flow in the Rust crate surface yet.
- Registry seeding is deterministic and local, so later CLI or MCP layers can call it without
  reintroducing hidden Python dependencies.

### Non-Networked Entity Rules

Automatic Wikipedia lookup and all other network-based enrichment are explicitly out of scope for
Rust v1.

- Entity detection runs only on local text supplied to the crate.
- Registry lookup and graph writes use local storage only.
- Tests must prove that detection and lookup succeed without any network dependency.

## To-Do Checklist

- [x] Port entity detection heuristics.
- [x] Define entity identity and persistence schema.
- [x] Implement entity registry reads and writes.
- [x] Port hall derivation logic.
- [x] Port room derivation logic.
- [x] Port tunnel derivation logic.
- [x] Implement duplicate relation handling.
- [x] Implement traversal queries.
- [x] Define traversal ordering rules.
- [x] Port onboarding-derived setup behavior if retained.
- [x] Document non-support for automatic Wikipedia enrichment.
- [x] Add entity detection fixture tests.
- [x] Add registry persistence tests.
- [x] Add graph edge creation tests.
- [x] Add palace graph tunnel parity tests.
- [x] Add duplicate relation tests.
- [x] Add traversal query tests.
- [x] Add negative tests proving no network lookups occur.

## Exit Gates

- Entity and graph suites pass on the fixture corpus.
- Palace graph derivation is stable and deterministic.
- Non-networked entity policy is documented and enforced by tests.

## Validation Scope

Phase 6 Rust coverage is centered on:

- typed entity registry persistence over SQLite
- deterministic entity detection heuristics with no network path
- duplicate-safe palace graph derivation and traversal
- temporal knowledge graph add, invalidate, query, timeline, and stats behavior
- GitHub Actions execution through the Rust storage workflow rather than local build validation

## Risks To Watch

- Letting graph semantics drift because fixtures only cover search behavior.
- Hidden Python dependence on external lookup artifacts.
- Weak duplicate handling causing graph explosion over repeated ingest runs.
