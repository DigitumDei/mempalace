# Phase 1 Plan: Workspace and Core Foundations

## Objective

Create the Rust workspace, define the core domain model, and lock the base schemas and embedding profile constants that later phases rely on.

## Dependencies

- Phase 0 fixture and parity decisions are complete.
- Acceptance criteria for config, ids, and path handling are written.

## Implementation Workstreams

### 1. Workspace Scaffolding

- Create the Rust workspace and crate layout from the migration plan.
- Define crate ownership boundaries early so storage, ingest, search, graph, MCP, and CLI work do not collapse into one crate.
- Add baseline lint, test, and formatting configuration.

### 2. Core Domain Types

- Define stable IDs and core structs:
  - `WingId`
  - `RoomId`
  - `DrawerId`
  - `DrawerRecord`
  - `SearchQuery`
  - `SearchResult`
  - `EmbeddingProfile`
- Ensure serialization rules are explicit and versionable.

### 3. Error and Observability Foundations

- Define shared error types and error conversion boundaries.
- Establish `tracing` conventions for library crates and binaries.
- Decide which failures should be typed versus opaque infrastructure errors.

### 4. Config and Path Rules

- Define versioned config schema.
- Implement path expansion, profile resolution, and local data directory rules.
- Make platform and profile behavior deterministic.

### 5. Embedding Profile Constants

- Lock the `balanced` and `low_cpu` profile names, model ids, and dimensions.
- Prevent storage schema work from guessing vector dimensions later.

## Deliverables

- Rust workspace with crate skeletons
- Shared core types crate
- Shared error and tracing setup
- Versioned config schema
- Path resolution implementation
- Embedding profile constants committed in code

## To-Do Checklist

- [ ] Create workspace root and crate directories.
- [ ] Add cargo workspace configuration.
- [ ] Add baseline linting and formatting config.
- [ ] Add shared test support crate or module if needed.
- [ ] Define `WingId`, `RoomId`, and `DrawerId`.
- [ ] Define `DrawerRecord`, `SearchQuery`, and `SearchResult`.
- [ ] Define `EmbeddingProfile` and profile metadata types.
- [ ] Implement serialization and deserialization for core types.
- [ ] Implement shared error enums and conversion boundaries.
- [ ] Configure `tracing` initialization strategy.
- [ ] Define versioned config file schema.
- [ ] Implement config loading and validation.
- [ ] Implement path expansion and home-directory handling.
- [ ] Implement local palace data directory resolution.
- [ ] Lock `balanced` profile model id and dimension.
- [ ] Lock `low_cpu` profile model id and dimension.
- [ ] Write config round-trip tests.
- [ ] Write profile selection tests.
- [ ] Write path resolution tests.
- [ ] Write ID serialization tests.

## Exit Gates

- Workspace builds successfully.
- Foundational unit tests pass.
- Core types and config schema are stable enough for storage and embeddings work.
- Embedding dimensions are locked and available to downstream crates.

## Risks To Watch

- Letting convenience shortcuts leak dynamic metadata into the core model.
- Deferring embedding profile constants until storage schema work starts.
- Blurry crate boundaries that make later parallel work harder.
