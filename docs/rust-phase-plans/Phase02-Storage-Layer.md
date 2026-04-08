# Phase 2 Plan: Storage Layer

## Objective

Replace Python's Chroma-centric storage with explicit `LanceDB` plus `SQLite`, including deterministic schemas, migrations, and crash-safe ingest bookkeeping.

## Dependencies

- Phase 1 core types, config, and embedding dimensions are locked.
- Phase 0 fixture corpus includes storage-relevant parity cases.

## Implementation Workstreams

### 1. SQLite Operational Schema

- Define migrations for config, manifests, entity registry, graph state, and tool state.
- Make migration application and schema version checks explicit.
- Define rollback or recovery expectations for partially applied migrations.

### 2. LanceDB Drawer Schema

- Create the drawers table with stable field definitions and embedding dimensions tied to profile configuration.
- Decide how compressed drawers are represented if retained.
- Define indexing and filtering strategy for wing, room, date, and source metadata.

### 3. Repository Interfaces

- Define repository traits for:
  - drawer storage
  - ingest manifests
  - entity registry
  - graph persistence
- Keep interface boundaries clean enough that higher layers do not know storage internals.

### 4. CRUD and Search Primitives

- Implement add, get, delete, update, and search primitives.
- Support deterministic metadata filtering and idempotent writes.
- Make duplicate handling explicit rather than incidental.

### 5. Cross-Store Consistency and Recovery

- Implement the pending-to-committed ingest contract described in the migration plan.
- Detect stale pending runs.
- Reconcile orphaned LanceDB rows.
- Mark interrupted ingest runs failed and retryable.

## Deliverables

- SQLite migrations
- LanceDB schema setup
- Storage repository traits and implementations
- CRUD and filter operations
- Cross-store reconciliation logic
- Storage integration test harness

## To-Do Checklist

- [ ] Define SQLite migration files or migration module.
- [ ] Create tables for config, migrations, ingest files, entities, graph state, and tool state.
- [ ] Implement migration runner.
- [ ] Implement migration version checks.
- [ ] Implement migration failure behavior.
- [ ] Define LanceDB drawer schema from `DrawerRecord`.
- [ ] Bind embedding dimensions to profile constants.
- [ ] Create table initialization flow.
- [ ] Decide compressed drawer storage handling.
- [ ] Define drawer store trait.
- [ ] Define ingest manifest store trait.
- [ ] Define entity registry store trait.
- [ ] Define graph store trait.
- [ ] Implement drawer insert/get/delete/update primitives.
- [ ] Implement metadata filter compilation for wing and room.
- [ ] Implement duplicate write handling.
- [ ] Implement ingest run creation and pending state.
- [ ] Implement manifest predeclaration of chunk ids.
- [ ] Implement LanceDB upsert flow.
- [ ] Implement commit transition after successful write.
- [ ] Implement stale pending run scan on startup.
- [ ] Implement orphaned LanceDB row pruning.
- [ ] Implement retryable failure marking for incomplete runs.
- [ ] Write migration application tests.
- [ ] Write migration rollback or failure recovery tests.
- [ ] Write drawer CRUD integration tests.
- [ ] Write duplicate insert tests.
- [ ] Write metadata filter tests.
- [ ] Write concurrent read tests.
- [ ] Write dual-write crash recovery tests.

## Exit Gates

- Real local storage integration tests pass.
- Cross-store reconciliation is deterministic under simulated interruption.
- Storage interfaces are stable enough for ingest and search layers.

## Risks To Watch

- Allowing LanceDB and SQLite to drift without a clear source-of-truth contract.
- Hiding dimension mismatches until runtime data is already written.
- Reintroducing dynamic metadata blobs in place of stable schemas.
