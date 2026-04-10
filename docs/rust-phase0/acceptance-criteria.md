# Phase 0 Acceptance Criteria

## Global

- A committed fixture corpus exists under `tests/fixtures/phase0/inputs/`.
- A committed golden corpus exists under `tests/fixtures/phase0/goldens/`.
- A fixture lock manifest exists and records the reference environment plus input file hashes.
- Regeneration and drift-check commands are documented and scriptable.
- Any deterministic in-script seed data required to exercise a contract surface is documented explicitly in the Phase 0 docs.

## CLI

- Command inventory and per-command help snapshots are committed.
- Search and wake-up snapshots exist for the synthetic fixture corpus.
- Later Rust phases must preserve command names, flag names, and formatting rules defined in the goldens.

## MCP

- Tool inventory JSON is committed from the Python reference.
- MCP initialize, tools/list, representative success calls, and representative error calls are snapshotted.
- Later Rust MCP work must pass contract tests against these snapshots or an approved divergence note.

## Search And Layers

- Programmatic search goldens exist for unfiltered, wing-filtered, and room-filtered queries.
- Wake-up goldens exist for global and wing-scoped output.
- Layered retrieval acceptance in later phases uses these snapshots plus tolerant ranking gates.

## Graph

- Palace graph traversal, tunnel discovery, and graph stats goldens exist on a mixed-wing fixture.
- Knowledge graph query, timeline, invalidate, and stats goldens exist on a seeded SQLite fixture.

## AAAK

- AAAK compression output exists for representative drawer text.
- Compression stats are captured alongside rendered AAAK text.

## Environment And Drift

- The reference environment doc states Python version, dependency inputs, and model warm-up requirements.
- Drift check regenerates into a disposable output tree, leaving committed fixtures untouched.
- Drift check fails if regenerated exact-contract inventories or goldens differ byte-for-byte from committed snapshots, and if tolerant search or wake-up surfaces drift semantically.
- Regeneration must target a disposable local palace path and disposable HOME directory.
