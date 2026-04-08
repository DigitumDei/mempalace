# Rust Rewrite Task Plan

## Purpose

This document turns the Rust rewrite in `docs/RustMigration.md` into an execution plan.

Detailed implementation checklists for each phase live in `docs/RustImplementationPhasePlans.md` and `docs/rust-phase-plans/`.

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
- knowledge graph and local/manual entity workflows
- AAAK compression and rendering

It should also improve on the current Python version by making these explicit:

- schema versions
- embedding model choice
- import state where optional interoperability is supported
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
7. Python goldens are only valid when produced from a pinned reference environment with pinned model assets and a documented warm-cache procedure.

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
- MCP tool request/response shapes across status/taxonomy, search, graph, knowledge graph, write/delete, diary, and AAAK-spec tools

Implementation approach:

- create a frozen fixture corpus under `tests/fixtures/`
- capture Python outputs into golden JSON or text snapshots
- consume the same fixtures from Rust tests
- add fixture-drift checks so regenerated Python goldens cannot silently replace the baseline without review

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
- crash-recovery reconciliation between `LanceDB` and `SQLite`

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

- exact golden result tests for formatting and filter semantics
- tolerant retrieval checks for ranking quality
- recall-oriented benchmark fixtures
- threshold tests for low-CPU profile vs balanced profile

Ranking parity policy:

- exact snapshot parity is required for CLI formatting, wake-up structure, filter semantics, and deterministic tie-breaking
- retrieval quality parity is measured by overlap and benchmark thresholds, not bit-identical ranking
- the initial balanced-profile gate should require `>= 0.90` top-5 set overlap with the pinned Python reference on labeled fixtures and `>= 95%` of the Python Recall@5 score on the benchmark fixture

### 6. MCP Protocol Tests

Purpose:

- prove the Rust server is compatible with MCP clients

Coverage:

- tool registration
- request decoding
- response encoding
- error propagation
- search tool behavior
- graph and knowledge-graph tool behavior
- diary tool behavior
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
- explicit absence of automatic Wikipedia or other networked entity enrichment in Rust

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

### 9. Optional Python Interop Tests

Purpose:

- verify optional import and inspection tooling without making Python-user migration a product requirement

Coverage:

- inspect existing palace state
- read legacy Chroma records
- inspect legacy `config.json`, `people_map.json`, and project `mempalace.yaml`
- inspect legacy `entity_registry.json`
- inspect onboarding bootstrap artifacts
- inspect legacy `knowledge_graph.sqlite3`
- preserve metadata fields
- rebuild embeddings where necessary
- detect incompatible legacy state
- dry-run import reporting
- resume interrupted import runs

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
- interrupted model download or partial cache state
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
5. Python parity runner that regenerates fixtures only from a pinned reference environment.
6. Scripted warm-cache fixture-generation flow that pins:
   - Python version
   - `chromadb` version
   - model identifier and asset checksum
   - offline regeneration procedure after initial asset acquisition
   - a zero-network assertion for regeneration after cache warm-up
7. Commit a machine-readable fixture lock manifest:
   - lockfile path
   - dependency versions
   - model checksum
   - fixture corpus version
8. Add a fixture-drift job that fails if regenerated Python outputs differ without an intentional baseline update.
9. Benchmark harness for retrieval and low-CPU scenarios.
10. CI matrix for normal and constrained profiles.

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
- `mempalace-import`

Each crate should own its tests, with cross-crate integration tests under a top-level `tests/` directory.

## Execution Phases

## Phase 0: Spec Lock and Fixture Harvest

Goal:

- freeze what the Python app does today
- decide where parity is required and where divergence is intentional

Tasks:

1. Inventory all user-facing commands, MCP tools, and storage behaviors.
2. Evaluate the initial Rust MCP crate choice against explicit criteria:
   - stdio transport support
   - typed request/response surface
   - maintenance activity
   - ease of contract testing
3. Capture representative corpora:
   - project repo fixture
   - conversation export fixture
   - mixed personal/project memory fixture
4. Generate golden outputs from Python:
   - search results
   - wake-up output
   - AAAK output
   - graph outputs
5. Define the official Rust profiles:
   - `balanced`
   - `low_cpu`
   - `quality_first`
6. Pin the Python reference environment for fixture generation:
   - Python version
   - `chromadb` version
   - embedding model identifier
   - model asset checksum or cached artifact source
   - offline warm-cache regeneration procedure
   - explicit zero-network assertion during regeneration
7. Commit fixture lock and drift policy:
   - fixture lock manifest checked into the repo
   - regeneration allowed only through the pinned environment
   - drift requires explicit review and baseline update
8. Write acceptance criteria for each subsystem.

Tests to write first:

- contract tests for CLI output
- contract tests for search result shape
- contract tests for MCP tool registration surface
- fixture loading helpers

Exit criteria:

- fixtures committed
- fixture-generation environment lock committed
- fixture-drift check committed
- MCP crate choice or fallback criteria committed
- acceptance criteria written with measurable gates
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
5. Lock embedding profile constants before storage work starts:
   - `balanced = all-MiniLM-L6-v2`
   - `balanced_dimension = 384`
   - `low_cpu` model and dimension recorded explicitly
6. Implement path resolution and local data directory logic.

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
- embedding profile constants are committed and referenced by storage tests

## Phase 2: Storage Layer

Goal:

- replace Chroma with `LanceDB` and formalize operational state in `SQLite`
- use embedding dimensions already locked in Phase 1 so the LanceDB schema is not guessed ad hoc

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
- migration rollback tests
- drawer insert/get/delete integration tests
- duplicate insert tests
- metadata filter tests
- concurrent read tests
- dual-write crash recovery tests

Pros vs Python:

- gain deterministic schemas and easier audits
- gain better migration control
- lose Chroma convenience methods
- lose implicit embedding management

Exit criteria:

- storage integration suite passes on real local DBs
- orphaned `LanceDB` rows are pruned after simulated crashes
- incomplete SQLite ingest runs are marked failed and retryable

## Phase 3: Embeddings Subsystem

Goal:

- make embeddings explicit and selectable

Tasks:

1. Define `EmbeddingProvider` trait.
2. Implement initial backend with `fastembed`.
3. Implement the already-pinned `balanced` model:
   - `all-MiniLM-L6-v2`
   - `384` dimensions
4. Add `low_cpu` profile with a smaller model.
5. Add config-driven model selection.
6. Add model cache and startup validation behavior.

Tests first:

- provider contract tests
- model profile resolution tests
- dimension mismatch tests
- offline startup tests with warm cache
- expected failure tests when model assets are missing
- partial-download and corrupted-cache tests

Performance gates:

- `balanced` warm query embedding p95: `<= 750 ms` on the reference fixture host
- `low_cpu` warm query embedding p95: `<= 1500 ms`
- `low_cpu` end-to-end search p95 on the small-VM fixture: `<= 2500 ms`
- `low_cpu` resident memory while idle and warm: `<= 450 MB`
- `low_cpu` resident memory during single-worker ingest: `<= 850 MB`

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
- spellcheck-mutation normalization tests
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
6. Document and test that Wikipedia research/enrichment from the Python registry layer is intentionally not implemented in Rust.

Tests first:

- entity detection fixtures
- registry persistence tests
- graph edge creation tests
- palace graph tunnel-derivation parity tests
- duplicate relation tests
- traversal query tests
- negative tests proving entity workflows do not perform network lookups or depend on Wikipedia-derived cache state

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
2. Port status and taxonomy tools.
3. Port search, wake-up, and layer tools.
4. Port graph and knowledge-graph tools.
5. Port diary tools.
6. Port write/delete tools if still in scope.
7. Implement structured error mapping.
8. Test stdio lifecycle behavior.

Tests first:

- MCP contract tests
- invalid input tests
- tool output shape tests
- tool-surface completeness tests
- concurrent MCP write-vs-ingest tests
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
6. Port `split` or explicitly mark it deferred.
7. Port `compress` or explicitly mark it deferred.

Tests first:

- CLI snapshot tests
- exit code tests
- help text tests
- `split` contract tests if retained
- `compress` contract tests if retained
- end-to-end command tests

Pros vs Python:

- gain a single compiled binary distribution path
- gain faster startup and simpler deploys
- lose the flexibility of Python package patching for power users

Exit criteria:

- CLI parity tests pass

## Phase 10: Optional Python Interop Tooling

Goal:

- support inspection or selective import of Python-era data without making it a release requirement

Tasks:

1. Implement legacy state inspection.
2. Implement dry-run import report.
3. Implement Chroma-to-LanceDB conversion.
4. If import is kept, cover all relevant Python-era persisted state explicitly:
   - `config.json`
   - `people_map.json`
   - `entity_registry.json`
   - onboarding-generated markdown artifacts
   - `knowledge_graph.sqlite3`
   - project-local `mempalace.yaml`
5. Preserve or remap metadata fields explicitly.
6. Implement resumable import runs.
7. Implement post-import verification report.

Tests first:

- import fixture tests
- interrupted import resume tests
- data-count parity tests
- metadata parity tests
- fixture coverage for non-Chroma persisted state
- project-local config import or inspection tests
- compressed-drawer interop tests if compressed storage is shipped

Pros vs Python:

- gain optional interoperability without coupling the Rust release to Python internals forever
- lose some simplicity if you choose to support broad import coverage
- lose ongoing maintenance time for the pinned Python reference environment if interop and parity fixtures are retained

Exit criteria:

- interop tooling is either complete for all declared state or explicitly removed from the release scope

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
- documented budgets are met:
  - warm query p95 `<= 2500 ms`
  - idle warm RSS `<= 450 MB`
  - single-worker ingest RSS `<= 850 MB`

## Phase 12: Release Readiness

Goal:

- cut a usable first Rust release without hidden gaps

Tasks:

1. Freeze CLI and config schemas.
2. Run full regression and benchmark suite.
3. Validate optional Python interop only if that feature remains in scope.
4. Build packaging and release artifacts.
5. Write operator docs for normal and low-CPU deployments.

Required gates:

- all unit and integration suites pass
- optional interop suite passes if shipped
- benchmark thresholds met
- low-CPU profile passes
- no unowned parity gaps remain

## Cross-Cutting Acceptance Criteria

These criteria apply across all phases.

Budget policy:

- the numeric latency and memory gates in this document are the initial definition-of-done
- they may be revised only by an explicit doc update after benchmark review, not ad hoc during implementation

### Functional

- Rust CLI can initialize, mine, search, wake up, and serve MCP locally.
- Search results preserve meaningful parity with Python for representative fixtures.
- Python-state import is optional and, if omitted, explicitly documented as out of scope for the first Rust release.
- if import is shipped, it covers every declared Python-era state artifact or the missing artifacts are explicitly removed from scope before release

### Operational

- default deployment is fully local after model acquisition
- low-CPU profile is explicitly supported
- startup and query behavior are deterministic
- Python fixture regeneration is reproducible from a pinned environment and fails if it requires network after cache warm-up
- cross-store recovery after interrupted ingest is deterministic and covered by integration tests

### Quality

- schema versions are explicit
- failures are actionable, not silent
- no critical path depends on unchecked dynamic metadata blobs
- retrieval ranking parity uses tolerant quality metrics; formatting and filter semantics use exact snapshots

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
- release candidate with optional interop settled

## Recommendation

The safest path is not "rewrite everything and hope."

The safest path is:

1. lock down Python behavior with fixtures
2. build the Rust test harness first
3. implement storage and embeddings before ingest
4. make low-CPU constraints part of the plan from day one
5. treat fixture reproducibility and benchmarks as core work, not cleanup work
6. budget explicitly for maintaining the pinned Python reference environment as long as parity fixtures remain part of the workflow

If this discipline is followed, the Rust rewrite becomes a controlled reimplementation instead of a speculative rewrite.
