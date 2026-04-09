# Phase 0 Plan: Spec Lock and Fixture Harvest

## Objective

Freeze the Python reference behavior, define where Rust must match it exactly, and build the reproducible fixture baseline that every later phase depends on.

## Preconditions

- `docs/RustMigration.md` and `docs/RustMigrationTasks.md` are treated as source documents.
- The current Python implementation is runnable in a pinned environment.
- The team agrees that fixture reproducibility is a release-critical requirement, not optional tooling.

## Implementation Workstreams

### 1. User-Facing Surface Inventory

- Enumerate CLI commands, flags, exit codes, and output formats.
- Enumerate MCP tools, request fields, response fields, and error shapes.
- Enumerate storage behaviors that are externally meaningful:
  - drawer id semantics
  - metadata filter semantics
  - wake-up output structure
  - AAAK rendering shape

### 2. Rust Parity Policy

- Produce a parity matrix with three statuses:
  - exact parity required
  - tolerant parity required
  - intentional divergence
- Record explicit reasons for every divergence so later implementation does not relitigate them informally.
- Decide the initial Rust MCP crate selection and define fallback criteria if the first choice fails contract testing.

### 3. Fixture Corpus Harvest

- Collect representative project fixtures.
- Collect representative conversation export fixtures.
- Collect mixed memory fixtures that exercise wings, rooms, halls, tunnels, and graph behavior.
- Sanitize or synthesize any sensitive inputs while preserving structural realism.

### 4. Golden Output Capture

- Generate golden outputs from Python for:
  - search results
  - wake-up output
  - AAAK output
  - graph output
  - MCP tool registration and payload shapes
- Save goldens as stable JSON or text snapshots with clear fixture naming.

### 5. Pinned Regeneration Environment

- Pin Python version, dependency versions, embedding model id, and model checksum.
- Document cache warm-up and zero-network regeneration.
- Add fixture drift detection so regenerated outputs cannot silently replace baseline behavior.

### 6. Acceptance Criteria Definition

- Write measurable acceptance criteria for every subsystem before Phase 1 starts.
- Link each later phase to the fixtures and gates it must satisfy.

## Deliverables

- Fixture corpus under `tests/fixtures/`
- Golden outputs and fixture lock manifest
- Parity vs divergence decision log
- MCP crate evaluation note
- Acceptance criteria file or section references for each subsystem
- Fixture regeneration and drift-check workflow

## To-Do Checklist

- [ ] Inventory all current CLI commands and flags.
- [ ] Inventory all MCP tools and payload shapes.
- [ ] Inventory search, wake-up, AAAK, and graph output surfaces.
- [ ] Write parity matrix with exact, tolerant, and divergence categories.
- [ ] Choose initial Rust MCP crate and record fallback criteria.
- [ ] Harvest representative project fixtures.
- [ ] Harvest representative conversation fixtures.
- [ ] Harvest mixed graph and entity fixtures.
- [ ] Sanitize or synthesize sensitive fixture data.
- [ ] Generate Python search goldens.
- [ ] Generate Python wake-up goldens.
- [ ] Generate Python AAAK goldens.
- [ ] Generate Python graph goldens.
- [ ] Generate Python MCP contract goldens.
- [ ] Pin Python version and dependency set.
- [ ] Pin embedding model identifier and checksum.
- [ ] Document warm-cache generation flow.
- [ ] Add zero-network assertion for regeneration.
- [ ] Commit fixture lock manifest.
- [ ] Add fixture drift CI or scripted guard.
- [ ] Write subsystem acceptance criteria.

## Exit Gates

- Fixture corpus and goldens are committed.
- Reference environment is pinned and reproducible.
- Drift policy is enforceable in automation.
- Parity and divergence decisions are explicit.
- Subsystem acceptance criteria are written, linked, and mapped to the later phases that consume them.

## Risks To Watch

- Goldens generated from an unstable or drifting Python environment.
- Hidden product behavior living outside CLI and MCP surfaces.
- Sensitive real-world data leaking into committed fixtures.
- Team treating parity questions as implementation-time decisions instead of spec decisions.
