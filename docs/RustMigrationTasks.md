# Rust Migration Task Plan

## Purpose

This document turns the Rust migration in `docs/RustMigration.md` into an execution plan.

The emphasis here is:

- break the rewrite into concrete tasks
- define the full test suite before implementation starts
- enforce a TDD workflow across each subsystem
- keep parity with Python where it matters and make deliberate changes where the Rust design is better

This is not a vague roadmap. It is the working delivery plan for a Rust rewrite.

## Delivery Goals

The Rust version should preserve the product shape of the current Python app:

- local-first storage
- explicit offline embeddings
- project and conversation mining
- semantic retrieval with metadata filters
- wake-up and layered memory loading
- MCP server support
- knowledge graph and entity workflows
- AAAK compression and rendering

It should also improve on the current Python version by making these explicit:

- schema versions
- embedding model choice
- migration state
- ingestion idempotency
- low-CPU deployment behavior

## TDD Rules

These rules should govern the whole rewrite.

1. No production module starts without its tests and acceptance criteria already written.
2. Every subsystem begins with contract tests against Python behavior or a documented intentional divergence.
3. Golden fixtures come first for parsing, extraction, retrieval formatting, and wake-up output.
4. Integration tests must run against real local storage backends, not mocks alone.
5. Performance and low-CPU budgets are part of definition-of-done, not a later optimization pass.
6. A subsystem is not complete when it compiles. It is complete when its unit, integration, regression, and benchmark gates pass.

## Test Suite Defined Up Front

The full suite should be defined before implementation starts, even if some tests are initially skipped pending infrastructure.

### 1. Contract Tests Against Python

Purpose:

- lock down current observable behavior
- make parity decisions explicit
- catch accidental product drift

Coverage:

- CLI command outputs and exit codes
- chunking boundaries for representative project files and chat exports
- search result formatting
- metadata filter behavior for wing and room
- wake-up payload structure
- AAAK output rendering
- knowledge graph edge creation on known fixture inputs
- MCP tool request/response shapes

Implementation approach:

- create a frozen fixture corpus under `tests/fixtures/`
- capture Python outputs into golden JSON or text snapshots
- consume the same fixtures from Rust tests

### 2. Unit Tests

Purpose:

- validate pure logic cheaply and deterministically

Coverage:

- config parsing and defaults
- path expansion and validation
- chunking logic
- normalization functions
- metadata mapping
- ID generation
- content hashing
- embedding provider selection logic
- filter compilation
- rank merging and score normalization
- graph edge derivation
- AAAK tokenization and formatting

### 3. Storage Integration Tests

Purpose:

- prove the Rust storage layer works with real `LanceDB` and `SQLite`

Coverage:

- create/open database state
- insert drawers
- duplicate insert handling
- filtered vector search
- delete and update behavior
- migration application and rollback safety
- compressed drawer storage if retained
- concurrent reads during ingest

### 4. Ingest Pipeline Integration Tests

Purpose:

- validate end-to-end mining on local fixtures

Coverage:

- project mining
- conversation mining
- general extraction mode
- re-run idempotency
- changed-file reindex behavior
- ignored-file behavior
- malformed export handling
- large-file cutoffs and truncation policies

### 5. Retrieval and Ranking Tests

Purpose:

- preserve useful search behavior while changing the implementation

Coverage:

- top-k retrieval on labeled fixture sets
- metadata filtering
- empty-result behavior
- deterministic tie-breaking
- layered retrieval assembly
- wake-up content generation
- optional rerank path if added later

These should include:

- golden result tests
- recall-oriented benchmark fixtures
- threshold tests for low-CPU profile vs balanced profile

### 6. MCP Protocol Tests

Purpose:

- prove the Rust server is compatible with MCP clients

Coverage:

- tool registration
- request decoding
- response encoding
- error propagation
- search tool behavior
- write and delete tool behavior if retained
- startup/shutdown behavior
- invalid input handling

### 7. Knowledge Graph and Entity Tests

Purpose:

- preserve graph integrity and room/tunnel semantics

Coverage:

- entity recognition on fixture text
- registry persistence
- room assignment
- hall and tunnel creation
- duplicate edge handling
- graph traversal queries
- onboarding-derived entities

### 8. AAAK Tests

Purpose:

- keep compression behavior stable and auditable

Coverage:

- formatting invariants
- deterministic output
- parsing if reverse support exists
- long-input handling
- structured shorthand rendering
- token-budget-oriented output checks

### 9. Migration Tests

Purpose:

- safely move users from Python local state to Rust local state

Coverage:

- import existing palace state
- read legacy Chroma records
- preserve metadata fields
- rebuild embeddings where necessary
- detect incompatible legacy state
- dry-run migration reporting
- resume interrupted migration

### 10. Performance and Resource Tests

Purpose:

- prevent the Rust rewrite from becoming too heavy for the target environments

Coverage:

- cold start time
- query latency
- ingest throughput
- resident memory during indexing
- resident memory during query
- startup without warm model cache
- e2-micro profile ceilings

### 11. Reliability and Abuse Tests

Purpose:

- make the local system robust against bad inputs and operational failures

Coverage:

- corrupted SQLite file
- corrupted LanceDB state
- partial write interruption
- malformed JSON/YAML/config files
- malformed chat exports
- huge documents
- Unicode edge cases
- invalid filesystem symlinks
- permission errors

### 12. Property and Fuzz Tests

Purpose:

- catch parser and normalization bugs early

Coverage:

- normalization inputs
- chat export parsers
- config deserialization
- AAAK formatting inputs
- room and wing name sanitization

Recommended tools:

- `proptest`
- `cargo-fuzz` for parser-heavy paths

## Test Infrastructure to Build First

Before product implementation, build the harness:

1. Rust workspace test scaffold.
2. Fixture corpus copied from representative local project and conversation samples.
3. Golden snapshot framework for text and JSON outputs.
4. Temporary-database helpers for `SQLite` and `LanceDB`.
5. Optional Python parity runner to regenerate fixtures when intentionally updating behavior.
6. Benchmark harness for retrieval and low-CPU scenarios.
7. CI matrix for normal and constrained profiles.

Without this harness, the rewrite will drift.

## Recommended Workspace Breakdown

Suggested crates:

- `mempalace-core`
- `mempalace-config`
- `mempalace-storage`
- `mempalace-embeddings`
- `mempalace-ingest`
- `mempalace-search`
- `mempalace-graph`
- `mempalace-dialect`
- `mempalace-mcp`
- `mempalace-cli`
- `mempalace-migrate`

Each crate should own its tests, with cross-crate integration tests under a top-level `tests/` directory.

## Execution Phases

## Phase 0: Spec Lock and Fixture Harvest

Goal:

- freeze what the Python app does today
- decide where parity is required and where divergence is intentional

Tasks:

1. Inventory all user-facing commands, MCP tools, and storage behaviors.
2. Capture representative corpora:
   - project repo fixture
   - conversation export fixture
   - mixed personal/project memory fixture
3. Generate golden outputs from Python:
   - search results
   - wake-up output
   - AAAK output
   - graph outputs
4. Define the official Rust profiles:
   - `balanced`
   - `low_cpu`
   - `quality_first`
5. Write acceptance criteria for each subsystem.

Tests to write first:

- contract tests for CLI output
- contract tests for search result shape
- fixture loading helpers

Exit criteria:

- fixtures committed
- acceptance criteria written
- parity vs divergence list approved

## Phase 1: Workspace and Core Foundations

Goal:

- create the Rust workspace and core domain model

Tasks:

1. Create workspace and crate layout.
2. Define core domain structs:
   - `WingId`
   - `RoomId`
   - `DrawerId`
   - `DrawerRecord`
   - `SearchQuery`
   - `SearchResult`
   - `EmbeddingProfile`
3. Define error model and tracing setup.
4. Define versioned config schema.
5. Implement path resolution and local data directory logic.

Tests first:

- config round-trip tests
- default profile selection tests
- path resolution tests
- ID serialization tests

Pros vs Python:

- gain explicit types and schema boundaries
- lose some implementation speed early

Exit criteria:

- crates compile
- foundational unit suite passes

## Phase 2: Storage Layer

Goal:

- replace Chroma with `LanceDB` and formalize operational state in `SQLite`

Tasks:

1. Implement `SQLite` schema migrations.
2. Implement `LanceDB` drawer table creation.
3. Implement repository traits:
   - drawer store
   - ingest manifest store
   - entity registry store
   - graph store
4. Implement add/get/delete/search primitives.
5. Implement idempotent ingest bookkeeping.

Tests first:

- migration application tests
- drawer insert/get/delete integration tests
- duplicate insert tests
- metadata filter tests
- concurrent read tests

Pros vs Python:

- gain deterministic schemas and easier audits
- gain better migration control
- lose Chroma convenience methods
- lose implicit embedding management

Exit criteria:

- storage integration suite passes on real local DBs

## Phase 3: Embeddings Subsystem

Goal:

- make embeddings explicit and selectable

Tasks:

1. Define `EmbeddingProvider` trait.
2. Implement initial backend with `fastembed`.
3. Pin a default MiniLM-class model for `balanced`.
4. Add `low_cpu` profile with a smaller model.
5. Add config-driven model selection.
6. Add model cache and startup validation behavior.

Tests first:

- provider contract tests
- model profile resolution tests
- dimension mismatch tests
- offline startup tests with warm cache
- expected failure tests when model assets are missing

Performance gates:

- query embedding latency threshold
- ingest embedding throughput threshold
- memory ceiling threshold for low-CPU profile

Pros vs Python:

- gain explicit model control and offline guarantees
- gain reproducibility across environments
- lose the simplicity of `query_texts=[...]`

Exit criteria:

- embedding provider suite passes
- low-CPU benchmark gates recorded

## Phase 4: Ingest Pipeline

Goal:

- port project mining, conversation mining, normalization, and extraction

Tasks:

1. Port file discovery and ignore handling.
2. Port project chunking logic.
3. Port conversation export parsing.
4. Port normalization logic.
5. Port general extraction mode.
6. Implement file hashing and incremental reindex decisions.
7. Write indexed records into storage.

Tests first:

- project fixture ingest tests
- conversation fixture ingest tests
- reindex idempotency tests
- malformed export tests
- normalization golden tests
- extraction golden tests

Pros vs Python:

- gain safer parsing and stronger incremental indexing
- gain clearer boundaries between parse, normalize, and store
- lose some fast scripting flexibility for edge-case formats

Exit criteria:

- ingest pipeline reproduces fixture expectations
- re-run behavior is deterministic

## Phase 5: Search and Layered Memory

Goal:

- reproduce search, filtering, and wake-up behavior on Rust storage

Tasks:

1. Port semantic search path.
2. Implement metadata prefiltering by wing and room.
3. Implement score normalization and deterministic ordering.
4. Port layered memory assembly from drawers plus graph context.
5. Port wake-up generation.
6. Decide whether compressed drawers remain a first-release feature.

Tests first:

- retrieval golden tests
- filter tests
- empty-state tests
- wake-up golden tests
- layered output integration tests

Pros vs Python:

- gain visibility into ranking and filter logic
- gain room for future hybrid retrieval
- lose some “DB does everything” simplicity

Exit criteria:

- retrieval parity targets met
- wake-up output stable

## Phase 6: Knowledge Graph and Entity Workflow

Goal:

- preserve palace structure and cross-room relationships

Tasks:

1. Port entity detection heuristics.
2. Port entity registry persistence.
3. Port hall, room, and tunnel derivation.
4. Port graph traversal APIs.
5. Port onboarding-derived setup behavior if retained.

Tests first:

- entity detection fixtures
- registry persistence tests
- graph edge creation tests
- duplicate relation tests
- traversal query tests

Pros vs Python:

- gain stronger graph consistency guarantees
- gain cleaner graph migrations
- lose some loose metadata flexibility

Exit criteria:

- graph and entity suites pass on fixture corpus

## Phase 7: AAAK Dialect

Goal:

- preserve shorthand rendering and token efficiency behavior

Tasks:

1. Port AAAK formatting rules.
2. Port wake-up AAAK generation.
3. Decide whether reverse parsing is needed in v1.
4. Add deterministic rendering guarantees.

Tests first:

- AAAK golden tests
- formatting invariant tests
- token-budget tests
- long-input tests

Pros vs Python:

- gain deterministic output and easier low-level performance tuning
- lose the convenience of rapidly changing formatter logic without tests

Exit criteria:

- AAAK snapshots stable
- token budget checks pass

## Phase 8: MCP Server

Goal:

- provide a compatible Rust MCP server for hosted or local LLM clients

Tasks:

1. Implement tool registration.
2. Port search tools.
3. Port wake-up and layer tools.
4. Port write/delete tools if still in scope.
5. Implement structured error mapping.
6. Test stdio lifecycle behavior.

Tests first:

- MCP contract tests
- invalid input tests
- tool output shape tests
- startup/shutdown tests

Pros vs Python:

- gain tighter control over protocol handling and resource use
- gain a smaller runtime surface than a Python server plus dependencies
- lose some iteration speed while protocol details are still moving

Exit criteria:

- MCP integration suite passes with a real client harness

## Phase 9: CLI and UX Parity

Goal:

- make the Rust app feel like the current MemPalace tool

Tasks:

1. Implement CLI commands and flags.
2. Port status reporting.
3. Port init and mine flows.
4. Port search output formatting.
5. Port wake-up command.
6. Add migration command for Python users.

Tests first:

- CLI snapshot tests
- exit code tests
- help text tests
- end-to-end command tests

Pros vs Python:

- gain a single compiled binary distribution path
- gain faster startup and simpler deploys
- lose the flexibility of Python package patching for power users

Exit criteria:

- CLI parity tests pass

## Phase 10: Migration Tooling

Goal:

- give existing Python users a safe path to Rust

Tasks:

1. Implement legacy state inspection.
2. Implement dry-run migration report.
3. Implement Chroma-to-LanceDB conversion.
4. Preserve or remap metadata fields explicitly.
5. Implement resumable migrations.
6. Implement post-migration verification report.

Tests first:

- migration fixture tests
- interrupted migration resume tests
- data-count parity tests
- metadata parity tests

Pros vs Python:

- gain a one-time clean storage model
- lose the ease of simply reusing the old DB format forever

Exit criteria:

- migration dry-run and real-run tests pass

## Phase 11: Low-CPU Hardening for e2-micro

Goal:

- make the system usable on a tiny VM without pretending it has workstation resources

Tasks:

1. Define low-CPU operational mode:
   - smallest approved embedding model
   - batch ingest only
   - no default rerank
   - bounded worker count
2. Add concurrency caps and backpressure.
3. Add lazy model initialization where safe.
4. Add memory and latency instrumentation.
5. Add a benchmark fixture representative of personal use on a small VM.

Tests first:

- low-CPU config tests
- bounded concurrency tests
- benchmark gates for query latency
- benchmark gates for resident memory
- degraded-mode behavior tests

What we gain:

- realistic support for cheap always-on deployments
- lower operating cost

What we lose:

- slower ingest
- weaker semantic recall if the smallest model is used
- less headroom for reranking or heavy extraction

Exit criteria:

- low-CPU suite passes
- documented budgets are met

## Phase 12: Release Readiness

Goal:

- cut a usable first Rust release without hidden gaps

Tasks:

1. Freeze CLI and config schemas.
2. Run full regression and benchmark suite.
3. Validate upgrade from Python state.
4. Build packaging and release artifacts.
5. Write operator docs for normal and low-CPU deployments.

Required gates:

- all unit and integration suites pass
- migration suite passes
- benchmark thresholds met
- low-CPU profile passes
- no unowned parity gaps remain

## Cross-Cutting Acceptance Criteria

These criteria apply across all phases.

### Functional

- Rust CLI can initialize, mine, search, wake up, and serve MCP locally.
- Search results preserve meaningful parity with Python for representative fixtures.
- Migration from Python local data is supported or explicitly deferred with a documented fallback.

### Operational

- default deployment is fully local after model acquisition
- low-CPU profile is explicitly supported
- startup and query behavior are deterministic

### Quality

- schema versions are explicit
- failures are actionable, not silent
- no critical path depends on unchecked dynamic metadata blobs

## Suggested Task Ordering Inside Each Phase

For every subsystem, use the same order:

1. Write acceptance criteria.
2. Add or update fixtures.
3. Write failing unit and integration tests.
4. Implement the smallest production slice that passes.
5. Refactor only after green.
6. Add regression test for every bug found.
7. Record performance numbers before closing the phase.

## Suggested Milestones

Milestone 1:

- phases 0 to 3 complete
- Rust storage and embeddings foundation proven

Milestone 2:

- phases 4 and 5 complete
- ingest and search usable locally

Milestone 3:

- phases 6 to 9 complete
- product-parity beta

Milestone 4:

- phases 10 to 12 complete
- migration-ready release candidate

## Recommendation

The safest path is not "rewrite everything and hope."

The safest path is:

1. lock down Python behavior with fixtures
2. build the Rust test harness first
3. implement storage and embeddings before ingest
4. make low-CPU constraints part of the plan from day one
5. treat migration and benchmarks as core work, not cleanup work

If this discipline is followed, the Rust rewrite becomes a controlled product migration instead of a speculative reimplementation.
