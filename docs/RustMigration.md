# Rust Migration Plan for MemPalace

## Purpose

This document maps the current Python MemPalace implementation to a Rust-native design, with `LanceDB` as the primary replacement for `ChromaDB`.

The goal is not just "rewrite it in Rust." The goal is to preserve the product shape:

- local-first storage
- verbatim drawer retention
- semantic retrieval with metadata filters
- CLI and MCP workflows
- wake-up / layered memory loading
- entity, room, and graph logic

It also calls out where the Rust version should deliberately diverge from the Python design because the Python version is convenient but not ideal.

## Executive Summary

Recommended Rust stack:

- `clap` for CLI
- `serde`, `serde_json`, `serde_yaml` for config and export parsing
- `tokio` for async runtime
- `walkdir` and `ignore` for filesystem traversal
- `sqlx` or `rusqlite` for SQLite-backed metadata and knowledge graph
- `lancedb` for vector-backed drawer storage
- `fastembed`, `ort`, or `candle` for explicit local embeddings
- `rmcp` or another Rust MCP implementation for the MCP server
- `tracing` for logs

Recommended storage split:

- `LanceDB`: drawer corpus, embeddings, retrieval metadata, compressed variants
- `SQLite`: config, migrations, entity registry, knowledge graph, ingest manifests, file hashes, operational state

That is a better long-term architecture than the current Python design, where Chroma is doing almost all content storage while SQLite is used only for the knowledge graph.

## Migration Principles

1. Keep embeddings explicit.
   Python Chroma currently hides too much behind `query_texts` and default collection behavior. In Rust, make embedding generation a first-class subsystem.

2. Separate operational metadata from retrieval data.
   SQLite is better for manifests, migration state, per-file dedupe state, and temporal graphs. LanceDB is better for vector search and large text payloads.

3. Preserve the user-facing product before optimizing the internals.
   A Rust rewrite should still feel like MemPalace: same commands, same "wing/room/drawer" model, same MCP tools, same offline-first posture.

4. Prefer deterministic schemas over dynamic metadata blobs.
   Python currently leans on free-form metadata dicts in Chroma. Rust should define stable structs and schema versions.

## Current Python Architecture

The current codebase breaks down into these major pieces:

1. CLI and config
   - `mempalace/cli.py`
   - `mempalace/config.py`

2. Project mining
   - `mempalace/miner.py`

3. Conversation mining and normalization
   - `mempalace/convo_miner.py`
   - `mempalace/normalize.py`
   - `mempalace/general_extractor.py`

4. Retrieval and memory layers
   - `mempalace/searcher.py`
   - `mempalace/layers.py`

5. MCP tool server
   - `mempalace/mcp_server.py`

6. Knowledge graph and palace graph
   - `mempalace/knowledge_graph.py`
   - `mempalace/palace_graph.py`

7. Entity detection, registry, onboarding
   - `mempalace/entity_detector.py`
   - `mempalace/entity_registry.py`
   - `mempalace/onboarding.py`

8. AAAK dialect and compression
   - `mempalace/dialect.py`

The Rust port should keep these as separate crates or at least separate modules. That will make the rewrite incremental and testable.

## Recommended Rust Architecture

Suggested workspace layout:

```text
mempalace-rs/
  crates/
    mempalace-core        # domain types, config, errors, ids
    mempalace-storage     # LanceDB + SQLite adapters
    mempalace-ingest      # project mining, convo mining, normalization
    mempalace-search      # retrieval, ranking, layer generation
    mempalace-graph       # KG + palace graph
    mempalace-dialect     # AAAK compression and rendering
    mempalace-mcp         # MCP server
    mempalace-cli         # CLI binary
```

Benefits:

- clear replacement boundaries for each Python module
- easier benchmarking and fuzzing
- easier to test retrieval independently from ingestion
- simpler future support for alternate vector stores if LanceDB ever becomes a bad fit

Costs:

- more up-front scaffolding than a single Rust binary
- more schema and interface discipline required early

## Storage Layer

### Python Today

Current behavior:

- `chromadb.PersistentClient(path=...)`
- single main collection: `mempalace_drawers`
- query by `query_texts`
- optional `where` filter on `wing` and `room`
- documents stored verbatim
- metadata stored as flexible dicts
- optional secondary collection for compressed drawers

Strengths of the Python version:

- very small amount of code
- easy to add/query/delete
- no explicit embedding plumbing in app code

Weaknesses of the Python version:

- embedding behavior is implicit and version-sensitive
- metadata schema is loose
- operational bookkeeping is mixed into the vector DB
- limited control over ingestion idempotency and migrations

### Rust Recommendation

Use `LanceDB` for drawers and `SQLite` for the operational state.

Suggested LanceDB `drawers` schema:

```rust
struct DrawerRecord {
    id: String,
    wing: String,
    room: String,
    hall: Option<String>,
    source_file: String,
    chunk_index: i32,
    ingest_mode: String,
    extract_mode: Option<String>,
    added_by: String,
    filed_at: String,
    content: String,
    content_hash: String,
    embedding: Vec<f32>,
}
```

Suggested SQLite tables:

- `config`
- `migrations`
- `ingest_files`
- `entity_registry`
- `kg_entities`
- `kg_triples`
- `tool_state`

How it compares:

- Gain: explicit ownership of embeddings, schema, indexes, and migrations
- Gain: clearer separation between searchable content and app metadata
- Gain: easier audits and deterministic behavior
- Lose: some convenience of Chroma's high-level Python API
- Lose: more code to write around ingestion, filtering, and schema evolution

### Why LanceDB is the best Chroma replacement here

Best-fit reasons:

- embedded and local-first
- Rust-native API
- natural fit for "large text payload + vector + filterable metadata"
- good support for columnar data and future analytics
- better long-term control than a Python-dependent Chroma layer

Tradeoffs:

- not a drop-in Chroma clone, so retrieval code must change
- you must own embedding generation
- filtering semantics and ranking behavior need explicit implementation and validation

## Embeddings and Semantic Search

### Python Today

`searcher.py` and `mcp_server.py` query Chroma by passing raw text:

- `query_texts=[query]`
- `include=["documents", "metadatas", "distances"]`
- optional `where` on wing/room

This is simple, but the actual embedding model and distance behavior are not controlled in application code.

### Rust Recommendation

Make embedding generation explicit:

1. At ingest time:
   - chunk content
   - embed content locally
   - store vectors in LanceDB

2. At query time:
   - embed query locally
   - prefilter by metadata when provided
   - vector search in LanceDB
   - optional rerank in app code

Good embedding options:

- `fastembed`
  - easiest local-first path
  - good operational simplicity
- `ort` with ONNX models
  - more control
  - heavier model/runtime management
- `candle`
  - best if you want a pure Rust ML direction
  - more engineering effort

Recommended first version:

- `fastembed` for MVP and early parity
- keep the embedding provider behind a trait so it can be swapped later

What you gain:

- deterministic and auditable search behavior
- model pinning by version
- easier performance tuning and offline guarantees

What you lose:

- Chroma convenience
- some short-term development speed

## CLI and Configuration

### Python Today

The CLI in `cli.py` is thin and imperative:

- `init`
- `mine`
- `search`
- `wake-up`
- `split`
- `status`
- `compress`

Configuration is read from:

- env vars
- `~/.mempalace/config.json`
- project-local `mempalace.yaml`

### Rust Recommendation

Use:

- `clap` for command parsing
- `serde` config structs
- `directories` or `dirs` for user config paths

Suggested config split:

- global config in `~/.config/mempalace/config.toml` or preserve `~/.mempalace/config.json` for compatibility
- project-local `mempalace.yaml` retained for easy migration

What Rust improves:

- stronger input validation
- cleaner command surface
- better typed config with explicit defaults
- easier tests for CLI parsing and config merging

Possible downside:

- slightly more verbose implementation for config loading/merging
- migration friction if you also change file formats

Recommendation:

- preserve the existing config file shapes for v1 Rust compatibility
- add a migration command later if you want to move to TOML

## Project Mining

### Python Today

`miner.py`:

- walks project files
- skips common directories
- filters readable extensions
- chunks content by fixed char windows with overlap
- heuristically routes files to a room
- stores verbatim chunks as drawers
- uses `source_file` existence as the main idempotency check

Strengths:

- simple
- easy to understand
- preserves raw text faithfully

Weaknesses:

- dedupe is weak
- chunking is char-count based
- file state tracking is primitive
- room detection is heuristic-only and not reusable enough

### Rust Recommendation

Use:

- `ignore` or `walkdir` for traversal
- `blake3` for file content hashes
- a structured ingest manifest in SQLite

Suggested ingest flow:

1. discover candidate files
2. read text with encoding fallback
3. hash file contents
4. compare against previous ingest state
5. chunk content
6. route to room
7. embed and store drawers
8. write ingest manifest entries

Suggested SQLite `ingest_files` fields:

- `source_file`
- `file_hash`
- `size_bytes`
- `modified_time`
- `last_ingested_at`
- `ingest_kind`
- `drawer_count`

What you gain:

- proper idempotency
- ability to re-ingest only changed files
- safer resume/retry semantics
- cleaner observability

What you lose:

- more moving parts than the current "check source_file in Chroma" approach

### Chunking Strategy

The Python chunker is workable but crude.

Recommended Rust upgrade:

- start with existing boundary-aware fixed windows for parity
- add an internal chunker abstraction
- later support code-aware chunking and transcript-aware chunking with different policies

Suggested trait:

```rust
trait Chunker {
    fn chunk(&self, input: &SourceDocument) -> Vec<Chunk>;
}
```

Pros:

- easy experimentation without rewriting the pipeline
- better fit for code vs prose vs chats

Cons:

- slightly more abstraction than the current Python script style

## Conversation Mining and Normalization

### Python Today

`normalize.py` handles:

- plain text
- Claude.ai JSON
- ChatGPT mapping JSON
- Claude Code JSONL
- Slack JSON export

`convo_miner.py` then:

- normalizes each file
- chunks by exchange pair or general extractor mode
- heuristically assigns rooms

Strengths:

- broad format support
- good product value for relatively little code

Weaknesses:

- parsers are somewhat ad hoc
- little schema validation
- mixed concerns between parse, normalize, classify, and store

### Rust Recommendation

Break this into four layers:

1. `importers`
   - parse known export formats into typed message structs
2. `normalizers`
   - canonical transcript form
3. `extractors`
   - exchange chunks, general memory extraction, future plugins
4. `ingest writers`
   - write drawers and manifest state

Suggested canonical model:

```rust
struct Message {
    role: Role,
    content: String,
    timestamp: Option<String>,
    speaker_id: Option<String>,
}

struct Transcript {
    source_file: String,
    messages: Vec<Message>,
    source_format: SourceFormat,
}
```

What you gain:

- cleaner parser boundaries
- easier tests with fixture files
- better resilience to malformed exports
- simpler future support for Discord, iMessage, email, or other sources

What you lose:

- more code than the current Python normalization helpers

Recommendation:

- preserve the exact currently supported formats first
- make unsupported/partial parses return structured warnings, not silent skips

## General Extraction

### Python Today

`general_extractor.py` is pure heuristics:

- decisions
- preferences
- milestones
- problems
- emotional memories

This is one of the better candidates for a direct Rust translation because the logic is already deterministic and regex-based.

### Rust Recommendation

Use:

- `regex`
- typed extractor rules

Suggested design:

```rust
struct ExtractionRule {
    memory_type: MemoryType,
    patterns: Vec<Regex>,
}
```

What you gain:

- faster execution
- easier unit testing
- fewer hidden runtime surprises

What you lose:

- nothing important, assuming the rules are ported carefully

Recommendation:

- port this subsystem almost verbatim first
- then refine rule weighting after parity tests

## Retrieval and Layered Memory

### Python Today

`searcher.py` handles deep semantic search.

`layers.py` implements:

- Layer 0: identity text file
- Layer 1: generated "essential story" from top drawers
- Layer 2: filtered retrieval
- Layer 3: full semantic search

Strengths:

- clear product concept
- simple retrieval surface

Weaknesses:

- L1 ranking is simplistic
- no stable scoring model
- retrieval formatting logic is mixed with data access

### Rust Recommendation

Split into:

- `retriever`
- `ranker`
- `formatter`
- `layer_builder`

Suggested retrieval pipeline:

1. metadata prefilter
2. vector search
3. optional lexical score boost
4. optional freshness/importance weighting
5. result formatting for CLI or MCP

For Layer 1, avoid "top N by importance only." Use a more explicit score:

- importance metadata if present
- recency
- source diversity
- room diversity

What you gain:

- more predictable wake-up context
- better explainability for why a memory was chosen
- cleaner boundary between retrieval and presentation

What you lose:

- a bit of implementation simplicity

Recommendation:

- preserve current output shape first
- improve ranking once regression tests exist

## MCP Server

### Python Today

`mcp_server.py` is a large mixed module with:

- status and taxonomy tools
- search tools
- duplicate checking
- add/delete drawer tools
- graph tools
- knowledge graph tools
- embedded AAAK protocol text

Strengths:

- practical and directly useful
- exposes the core product capabilities

Weaknesses:

- mixed transport, business logic, and storage calls in one file
- little policy separation
- no capability boundaries between read and write operations

### Rust Recommendation

Treat MCP as a thin service layer over internal application services.

Suggested service split:

- `taxonomy_service`
- `search_service`
- `drawer_service`
- `graph_service`
- `kg_service`
- `wake_service`

The MCP layer should do only:

- parameter validation
- service dispatch
- response shaping

What Rust improves:

- cleaner separation between core logic and exposed tools
- easier to add permissions, policy gates, and audit logs
- easier to test without running a live MCP server

What you lose:

- very little, beyond writing the interfaces cleanly

Recommendation:

- implement the Rust MCP server after core storage and retrieval are stable
- do not port the current single-file design directly

## Knowledge Graph

### Python Today

`knowledge_graph.py` already uses SQLite and is one of the easiest subsystems to port.

Capabilities:

- entity nodes
- typed triples
- temporal validity
- invalidation
- entity/timeline queries

Strengths:

- local
- explicit
- not dependent on vector DB behavior

Weaknesses:

- schema is simple and mostly stringly typed
- weak transactional boundaries
- limited indexing and no formal migrations

### Rust Recommendation

Keep this in SQLite.

Use:

- `sqlx` if you want async and compile-time query checking
- `rusqlite` if you want a smaller dependency footprint and simpler embedding in a local CLI app

My recommendation here:

- `rusqlite` is enough unless you expect heavy async server concurrency

Enhancements for Rust:

- schema migrations with `refinery` or `sqlx migrate`
- stricter date handling with `time` or `chrono`
- typed predicate enums where possible
- transaction wrappers for add/invalidate flows

What you gain:

- safer writes
- easier future evolution
- stronger guarantees than the Python `sqlite3` wrapper

What you lose:

- almost nothing

This is one of the least risky parts of the rewrite.

## Palace Graph

### Python Today

`palace_graph.py` builds a navigable room graph from Chroma metadata:

- nodes are rooms
- cross-wing overlaps become tunnels
- graph is built on demand

Strengths:

- clever feature with little infrastructure
- no external graph DB required

Weaknesses:

- graph data is derived repeatedly
- depends on scanning the whole collection
- hall/date metadata are loosely defined

### Rust Recommendation

Keep this derived, but make the derivation strategy explicit.

Two viable options:

1. On-demand graph build from LanceDB + SQLite metadata
2. Materialized graph tables in SQLite, updated during ingest

Recommendation:

- start with on-demand derivation for parity
- materialize later only if graph queries become hot or expensive

What you gain in Rust:

- faster graph building
- typed graph structures
- easier future support for graph caching

What you lose:

- nothing important if the on-demand model remains acceptable

## Entity Detection and Registry

### Python Today

`entity_detector.py` and `entity_registry.py` combine:

- regex/entity heuristics
- onboarding-seeded registry
- learned knowledge
- optional Wikipedia lookup for unknown terms

Strengths:

- useful product feature
- mostly deterministic

Weaknesses:

- some logic is broad and heuristic-heavy
- registry schema is JSON-file centric
- Wikipedia lookup violates the repo's strongest "local only" messaging

### Rust Recommendation

Split the problem:

1. `entity_registry`
   - SQLite-backed or JSON-backed, but with a typed schema
2. `entity_detector`
   - regex/rule engine
3. `entity_enrichment`
   - optional external lookups behind an explicit feature flag

Recommendation:

- default to local-only behavior in Rust
- make Wikipedia enrichment opt-in and disabled by default

What you gain:

- clearer privacy posture
- less policy confusion
- easier testing

What you lose:

- slightly less "magic" for unknown names unless the user opts in

On storage choice:

- move the registry into SQLite if you want one coherent operational store
- keep JSON export/import for portability and manual edits

## Onboarding

### Python Today

`onboarding.py` is a terminal interview that seeds:

- people
- projects
- wings
- AAAK bootstrap files
- entity registry

Strengths:

- product-friendly
- helps early accuracy

Weaknesses:

- very interactive and imperative
- hard to automate or script

### Rust Recommendation

Support both:

- interactive onboarding
- non-interactive `--from-file` bootstrapping

Use:

- `inquire` or `dialoguer` for terminal prompts

What you gain:

- easier automation
- cleaner testability
- better CI/setup workflows

What you lose:

- nothing, if you preserve the interactive path

## AAAK Dialect and Compression

### Python Today

`dialect.py` provides:

- a symbolic compression dialect
- compression stats
- entity code mapping
- compressed drawer output

Strengths:

- deterministic and portable
- independent of model/provider APIs

Weaknesses:

- compression heuristics are relatively informal
- currently feels adjacent to the main retrieval system rather than fully integrated

### Rust Recommendation

Port this logic as a dedicated crate with:

- parser-free rendering first
- optional parser/validator later

Suggested path:

1. direct output-compatible Rust implementation
2. add structured intermediate representation later

Suggested model:

```rust
struct AaakEntry {
    entities: Vec<String>,
    topics: Vec<String>,
    quote: Option<String>,
    weight: Option<f32>,
    emotions: Vec<String>,
    flags: Vec<String>,
}
```

What you gain:

- speed
- easier batch compression
- opportunity for stronger syntax validation

What you lose:

- little, assuming you preserve current emitted text shapes

## Compression Storage Strategy

The Python version stores compressed drawers in a second Chroma collection.

In Rust, better options are:

1. separate LanceDB table `compressed_drawers`
2. same `drawers` table with nullable `compressed_content`

Recommendation:

- use a separate table initially

Why:

- keeps raw retrieval and compressed retrieval separate
- avoids widening the core drawer schema too early
- easier to benchmark compressed-vs-raw retrieval independently

## Dedupe and Identity

### Python Today

Dedupe is mostly:

- "does a record from this source file already exist?"
- or duplicate similarity checks at MCP add time

That is not robust enough for a Rust rewrite worth doing.

### Rust Recommendation

Use three levels of identity:

1. file identity
   - path + content hash
2. chunk identity
   - source hash + chunk index + chunk content hash
3. semantic near-duplicate detection
   - optional search-time or ingest-time similarity guard

What you gain:

- proper idempotency
- fewer duplicate drawers
- cleaner migrations

What you lose:

- modest additional complexity

## Data Model Compatibility

The Rust app should preserve these MemPalace concepts:

- wing
- room
- hall
- tunnel
- drawer
- layer 0/1/2/3

It should not preserve the Python implementation quirks where they are accidental rather than conceptual.

Examples of good compatibility:

- same CLI commands and flags where practical
- same metadata names in exported JSON
- same MCP tool names if you want existing clients to keep working

Examples of good divergence:

- explicit embedding subsystem
- SQLite ingest manifests
- stronger schema validation
- opt-in external enrichment

## Security and Privacy Impact of the Rust Port

From the Chroma replacement perspective, a Rust + LanceDB design improves things mostly by making behavior explicit, not by creating a new privacy model.

What improves:

- fewer dynamic runtime surprises
- easier auditability of storage behavior
- no hidden Python dependency behavior around vector storage
- easier to guarantee exact local embedding paths if you own the embedding stack

What does not automatically improve:

- MCP exposure to hosted LLM clients
- user choice to ingest sensitive files
- verbatim storage of private text

So the storage rewrite is a sound engineering upgrade, but it is not itself a privacy boundary unless you also enforce local-only embedding and local-only model usage.

## Gains and Losses by Major Choice

### Chroma -> LanceDB

Gain:

- Rust-native and embedded
- better schema ownership
- better fit for long-term Rust architecture

Loss:

- no drop-in `query_texts` convenience
- more application code required

### Implicit embeddings -> explicit local embeddings

Gain:

- deterministic behavior
- version pinning
- easier audits

Loss:

- model lifecycle becomes your problem

### Chroma metadata state -> SQLite operational state

Gain:

- better migrations and manifests
- more reliable ingest bookkeeping

Loss:

- two persistence systems instead of one primary one

### Python script-style modules -> typed services/crates

Gain:

- maintainability
- testability
- safer refactors

Loss:

- more up-front design work

## Suggested Migration Phases

### Phase 1: Storage and Search Parity

Build:

- config loader
- drawer schema
- LanceDB adapter
- embedding provider trait
- `search`
- `status`
- `list_wings`
- `list_rooms`

Goal:

- replace the main Chroma dependency first

### Phase 2: Ingestion Parity

Build:

- project miner
- conversation normalizers
- conversation miner
- general extractor
- ingest manifest tables

Goal:

- same corpus in, same retrieval utility out

### Phase 3: Layered Memory and AAAK

Build:

- wake-up generation
- Layer 1/2/3 formatting
- compression storage
- AAAK tooling

Goal:

- restore the distinctive MemPalace UX

### Phase 4: Graph and MCP

Build:

- knowledge graph
- palace graph
- MCP server tools

Goal:

- full tool-driven assistant integration

### Phase 5: Compatibility and Migration Tooling

Build:

- Chroma export/import bridge
- config migration helpers
- regression benchmark harness

Goal:

- safe production cutover

## Recommended First Rust MVP

If you want the best balance between speed and correctness, the MVP should include:

- `init`
- `mine` for projects
- `mine --mode convos`
- `search`
- `status`
- LanceDB drawers
- SQLite ingest manifest
- SQLite knowledge graph
- local embeddings via `fastembed`

It should defer:

- AAAK compression parity
- full MCP parity
- graph traversal bells and whistles
- optional external enrichment

That gives you a credible Rust core without prematurely rebuilding every edge feature.

## Final Recommendation

For this repository, `LanceDB + SQLite + explicit local embeddings` is the right Rust replacement for `ChromaDB`.

That choice best matches what MemPalace actually is:

- a local semantic memory store
- heavy on verbatim text retention
- dependent on metadata filters
- small enough to benefit from embedded storage
- broad enough to need more structure than a single SQLite table hack

If the rewrite is done carefully, the Rust version should gain:

- better determinism
- better ingest correctness
- better schema clarity
- easier security review
- better long-term maintainability

The main things it will lose are convenience and speed of initial implementation. Those are real losses, but they are acceptable for a product intended to be durable, local, and inspectable.
