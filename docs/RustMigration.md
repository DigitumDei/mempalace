# Rust Rewrite Plan for MemPalace

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

This is not a commitment to migrate the existing Python user base. The Python app is the reference implementation and the source of many good product ideas, but the Rust effort should be treated as a sibling implementation or a selective reimplementation of the core ideas. Import or interoperability tooling can exist later, but it is optional rather than foundational.

## Executive Summary

Recommended Rust stack:

- `clap` for CLI
- `serde`, `serde_json`, `serde_yaml` for config and export parsing
- `tokio` for async runtime
- `walkdir` and `ignore` for filesystem traversal
- `sqlx` or `tokio-rusqlite` for SQLite-backed metadata and knowledge graph
- `time` or `chrono` for date and timestamp handling
- `lancedb` for vector-backed drawer storage
- `fastembed`, `ort`, or `candle` for explicit local embeddings
- `rmcp` or another Rust MCP implementation for the MCP server
- `tracing` for logs

Recommended storage split:

- `LanceDB`: drawer corpus, embeddings, retrieval metadata, compressed variants
- `SQLite`: config, migrations, entity registry, knowledge graph, ingest manifests, file hashes, operational state

That is a better long-term architecture than the current Python design, where Chroma is doing almost all content storage while SQLite is used only for the knowledge graph.

## Rewrite Principles

1. Keep embeddings explicit.
   Python Chroma currently hides too much behind `query_texts` and default collection behavior. In Rust, make embedding generation a first-class subsystem.

2. Separate operational metadata from retrieval data.
   SQLite is better for manifests, import state, per-file dedupe state, and temporal graphs. LanceDB is better for vector search and large text payloads.

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
   - `mempalace/spellcheck.py`
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
   - `mempalace/room_detector_local.py`
   - `mempalace/onboarding.py`

8. AAAK dialect and compression
   - `mempalace/dialect.py`
   - `mempalace/split_mega_files.py`

The Rust port should keep these as separate crates or at least separate modules. That will make the rewrite incremental and testable.

## Recommended Rust Architecture

Suggested workspace layout:

```text
mempalace-rs/
  crates/
    mempalace-core        # domain types, errors, ids
    mempalace-config      # config loading, profile resolution, path rules
    mempalace-storage     # LanceDB + SQLite adapters
    mempalace-embeddings  # embedding providers, model config, cache management
    mempalace-ingest      # project mining, convo mining, normalization
    mempalace-search      # retrieval, ranking, layer generation
    mempalace-graph       # KG + palace graph
    mempalace-dialect     # AAAK compression and rendering
    mempalace-mcp         # MCP server
    mempalace-cli         # CLI binary
    mempalace-import      # optional Python-state import and inspection tools
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
    date: Option<time::Date>,
    source_file: String,
    chunk_index: i32,
    ingest_mode: String,
    extract_mode: Option<String>,
    added_by: String,
    filed_at: time::OffsetDateTime,
    importance: Option<f32>,
    emotional_weight: Option<f32>,
    weight: Option<f32>,
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

Important parity note:

- `date` is required if the Rust graph wants parity with `palace_graph.py`.
- `importance`, `emotional_weight`, and `weight` are required if Layer 1 ranking should preserve the current metadata-based weighting behavior in `layers.py`.
- `filed_at` should be a real timestamp type, not a free-form string, because recency ranking and ingest bookkeeping depend on it.

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

### Cross-Store Consistency Contract

The Rust plan introduces a real dual-write hazard because drawer rows live in `LanceDB` while ingest manifests, hashes, and graph state live in `SQLite`.

The rewrite should therefore adopt an explicit contract:

1. Create a SQLite ingest run with status `pending`.
2. Predeclare the deterministic chunk ids expected for that run in SQLite.
3. Upsert those chunk ids into LanceDB.
4. Mark the SQLite rows `committed` only after the LanceDB write succeeds.

Recovery rule:

- SQLite is the source of truth for whether an ingest run completed.
- On startup, scan for stale `pending` ingest runs.
- Delete LanceDB rows whose ids are not present in committed SQLite manifest rows.
- Mark incomplete SQLite runs failed and eligible for retry.

Without this rule, idempotency and dedupe claims are not trustworthy.

## Embeddings and Semantic Search

### Python Today

`searcher.py` and `mcp_server.py` query Chroma by passing raw text:

- `query_texts=[query]`
- `include=["documents", "metadatas", "distances"]`
- optional `where` on wing/room

This is simple, but the actual embedding model and distance behavior are not controlled in application code.

What that means in practice:

- the app does not set an embedding function explicitly
- Chroma chooses the default collection embedding behavior
- in a pinned reference environment today, that will often resolve to a local `all-MiniLM-L6-v2` path, but that is a library default rather than an app-level guarantee
- first run may trigger a model download
- later embedding inference runs locally from the machine cache

So the current Python implementation is close to "local embeddings by default," but it is still implicit, version-sensitive, and unsuitable as an unpinned contract.

Strengths of the current Python behavior:

- minimal app code
- no embedding pipeline to maintain
- good default quality for general semantic search

Weaknesses of the current Python behavior:

- model choice is not visible in MemPalace config
- startup behavior can include a network download
- upgrades can change behavior indirectly through Chroma
- hard to tune for constrained hardware

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

Recommended interface:

```rust
trait EmbeddingProvider {
    type Error: std::error::Error + Send + Sync + 'static;
    fn model_id(&self) -> &'static str;
    fn dimension(&self) -> usize;
    fn embed_documents(&self, texts: &[String]) -> Result<Vec<Vec<f32>>, Self::Error>;
    fn embed_query(&self, text: &str) -> Result<Vec<f32>, Self::Error>;
}
```

That keeps the storage layer independent from the embedding backend and makes it possible to support different deployment profiles.

### Recommended Rust Default

For the first Rust version, the best default is:

- `LanceDB` for vector storage
- explicit local embeddings
- an `EmbeddingProvider` trait
- `fastembed` as the initial backend
- a pinned model selected in MemPalace config rather than by DB default

This is a better long-term design than the Python version because the application, not the database wrapper, owns the embedding contract.

### Rust Embedding Options

There is no single best model for every deployment target. The right answer depends on whether you want:

- closest behavior to current Python Chroma defaults
- strongest retrieval quality
- lowest CPU and RAM footprint
- easiest packaging and reproducibility

#### Option 1: MiniLM-class models for parity

Examples:

- `all-MiniLM-L6-v2`
- other 384-dimensional MiniLM sentence embedding variants with ONNX support

Best fit:

- closest semantic behavior to the current Python setup
- general-purpose retrieval across code, notes, and chats

Pros:

- best parity story with the current Python system
- relatively small vectors
- good quality per CPU cycle compared with larger models
- easy to explain to users because it mirrors current behavior

Cons:

- still non-trivial CPU work on ingest
- not ideal for a very weak always-on VM if ingest volume is high
- model acquisition and packaging need to be owned explicitly

Recommendation:

- use explicit `all-MiniLM-L6-v2` at `384` dimensions as the initial `balanced` profile
- strongest choice if you want the Rust app to start from Python-like retrieval behavior without inheriting Chroma's implicit defaults

#### Option 2: BGE-small or other compact modern models

Examples:

- compact BGE small English models
- similar ONNX-exported small embedding models

Best fit:

- users who want somewhat more modern embedding quality and are willing to retune thresholds

Pros:

- can outperform older MiniLM-family defaults on some retrieval tasks
- good ecosystem support
- still small enough to run locally

Cons:

- less parity with the current Python system
- can be slower or heavier than MiniLM depending on the exact model
- may require more benchmark validation to avoid subtle regressions

Recommendation:

- a good `quality_first` option
- not the first rewrite target if compatibility with current Python behavior matters most

#### Option 3: Very small models for constrained infrastructure

Examples:

- very small MiniLM-family models
- aggressively compact ONNX sentence embedding models

Best fit:

- low-end cloud VMs
- background services that must stay responsive under tiny CPU budgets

Pros:

- lowest CPU cost
- faster query embedding
- easier to keep latency bounded on a weak machine

Cons:

- weaker semantic recall
- greater need for metadata filtering and chunk quality
- more likely to miss subtle cross-document relationships

Recommendation:

- suitable as a dedicated `low_cpu` profile
- not ideal as the universal default unless infrastructure constraints dominate quality

#### Option 4: `ort` with directly managed ONNX models

Best fit:

- teams that want explicit model files, explicit runtime behavior, and direct control over loading

Pros:

- strongest control over packaging and reproducibility
- clearer separation between application logic and model assets
- easier to support multiple selectable local models

Cons:

- more engineering work than `fastembed`
- more runtime management details to own
- easier to make deployment awkward if packaging is sloppy

Recommendation:

- best long-term choice if model management becomes a first-class product concern
- probably not necessary for the first parity release

#### Option 5: `candle`

Best fit:

- teams committed to a broader Rust-native ML stack

Pros:

- strongest pure-Rust direction
- less dependence on external inference runtimes over time

Cons:

- highest implementation effort
- weakest path for "ship parity fast"
- more likely to consume time in ML plumbing rather than product work

Recommendation:

- good strategic option later
- poor first move for a practical rewrite

### Comparison with the Python Approach

Python today:

- Chroma owns the default embedding choice
- the app passes raw text and gets retrieval back
- less code, but more hidden behavior

Rust with explicit embeddings:

- MemPalace owns the model choice
- MemPalace embeds both documents and queries directly
- more code, but better determinism, auditability, and deployment control

What Rust gains:

- explicit model pinning
- predictable startup and offline guarantees
- hardware-specific profiles
- easier debugging when search quality changes

What Rust loses:

- convenience of implicit DB-managed embeddings
- slightly longer setup path
- a need for real benchmark discipline when switching models

### Embedding Dimension and Profile Locking

Embedding dimension is part of the storage contract.

That means:

- `balanced` is explicitly pinned to `all-MiniLM-L6-v2` at `384` dimensions
- the active table schema records its expected vector dimension
- startup validation fails loudly if the configured query model dimension differs from the stored table dimension
- switching embedding profiles on an existing corpus requires a full reindex or a separate table namespace

Dimension mismatch is not graceful degradation. It is a hard compatibility failure.

### Recommended Deployment Profiles

#### Profile A: Balanced default

- backend: `fastembed`
- model: explicit `all-MiniLM-L6-v2`
- dimension: `384`
- use case: laptop, desktop, or modest server

Why:

- closest practical replacement for the current Python behavior

#### Profile B: Low CPU

- backend: `fastembed` or `ort`
- model class: smallest acceptable local embedding model that still clears benchmark targets
- use case: `e2-micro`, always-on background service, or very low-cost personal VM

Why:

- optimizes for responsiveness and operating cost, not best retrieval quality

#### Profile C: Quality first

- backend: `ort`
- model class: stronger compact local model, potentially BGE-small class
- use case: workstation or larger VM where ingest time matters less than recall

Why:

- better ceiling for retrieval quality, at the cost of more tuning and packaging work

### Recommendation

The practical path is:

- ship with a MiniLM-class model for parity
- keep the provider trait stable
- add a `low_cpu` profile for weak machines
- benchmark both retrieval quality and ingest/query latency before changing the default model

What you gain:

- deterministic and auditable search behavior
- model pinning by version
- easier performance tuning and offline guarantees

What you lose:

- Chroma convenience
- some short-term development speed

## Low-CPU Deployment on e2-micro

One of the most important constraints in this rewrite is the target machine. An `e2-micro` class VM changes the design materially.

This is not just a performance concern. It affects:

- which embedding model is realistic
- whether ingest should be interactive or batch-oriented
- whether reranking is affordable
- how aggressive chunking and indexing can be
- whether MCP search remains responsive under load

### What an e2-micro target implies

For this class of machine, assume:

- CPU is the hard bottleneck
- memory headroom is limited
- cold starts and model loads matter
- background indexing competes directly with interactive search

This means the Rust design should not assume "embed everything eagerly with a medium model and rerank every query."

Deployment cost note:

- `fastembed` is attractive for parity and developer speed, but it brings ONNX Runtime plus local model assets into the package and memory footprint.
- On a `1 GB` machine, cold-start model loads and transient resident-memory spikes matter.
- If `low_cpu` is a real product profile, those runtime costs must be treated as design constraints, not left to later tuning.

### Recommended e2-micro strategy

If `e2-micro` support is a real requirement, the best strategy is:

1. Keep LanceDB, because the storage/query shape still fits the product well.
2. Use SQLite for all manifests and metadata to minimize operational complexity.
3. Make embeddings selectable by profile, with a dedicated `low_cpu` setting.
4. Prefer smaller vectors and cheaper models over chasing maximum recall.
5. Disable optional reranking by default on that profile.
6. Batch ingest work and rate-limit it rather than embedding aggressively in the foreground.

### Suggested low-CPU operating mode

For an `e2-micro`-friendly mode:

- use a small local embedding model
- reduce ingest concurrency to `1`
- keep chunk sizes only modestly larger, and only when measurements justify it
- rely more on `wing` and `room` metadata prefilters before vector search
- avoid secondary rerank passes unless explicitly enabled
- cache query embeddings for repeated queries where appropriate

This shifts more retrieval quality burden onto:

- decent room classification
- stable chunking
- good metadata filters
- careful ranking heuristics

### What you gain on e2-micro

- cheap always-on deployment
- simple single-node local-first architecture
- a realistic path to hosting personal memory infrastructure on minimal hardware

### What you lose on e2-micro

- slower ingest
- lower-quality semantic embeddings if you choose a tiny model
- less headroom for query reranking or fancy retrieval pipelines
- greater sensitivity to bad chunking or noisy metadata
- lower retrieval precision if chunk sizes are increased too aggressively to save CPU

### Comparison with the Python implementation

The current Python system benefits from Chroma's convenience, but it does not express a hardware-aware embedding strategy. On stronger machines that is fine. On an `e2-micro`, it is a weakness.

The Rust design can do better by making deployment intent explicit:

- `balanced` profile for normal developer machines
- `low_cpu` profile for tiny VMs
- optional `quality_first` profile for larger systems

That is a meaningful gain over the Python implementation because the resource tradeoffs stop being accidental.

### Recommendation for this project

If `e2-micro` is a real target, do not optimize only for parity with Chroma defaults.

Instead:

- keep MiniLM-class embeddings as the reference profile
- add a smaller low-CPU model profile from the start
- design ingest as resumable and batch-friendly
- keep retrieval simple and metadata-aware
- treat reranking as optional, not baseline

That approach will preserve the product on weak hardware, even though it will give up some semantic quality compared with a less constrained machine.

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

Configuration and local state are read from:

- env vars
- `~/.mempalace/config.json`
- `~/.mempalace/people_map.json`
- `~/.mempalace/entity_registry.json`
- `~/.mempalace/aaak_entities.md`
- `~/.mempalace/critical_facts.md`
- `~/.mempalace/knowledge_graph.sqlite3`
- project-local `mempalace.yaml`

### Rust Recommendation

Use:

- `clap` for command parsing
- `serde` config structs
- `directories` or `dirs` for user config paths

Suggested config split:

- global config in `~/.config/mempalace/config.toml` or preserve `~/.mempalace/config.json` for operator familiarity
- project-local `mempalace.yaml` retained if it remains the cleanest per-project override mechanism

What Rust improves:

- stronger input validation
- cleaner command surface
- better typed config with explicit defaults
- easier tests for CLI parsing and config merging

Possible downside:

- slightly more verbose implementation for config loading/merging
- migration friction if you also change file formats

Recommendation:

- preserve the existing file shapes only where they remain operationally useful
- do not treat Python-state compatibility as a release requirement for the Rust app
- if optional import tooling is ever shipped, scope it explicitly across all declared Python-era state rather than only the Chroma drawers
- only add import or conversion helpers later if they materially reduce operator friction

## Project Mining

### Python Today

`miner.py`:

- walks project files
- skips common directories
- filters readable extensions
- chunks content by boundary-aware windows with overlap
- heuristically routes files to a room, with separate local room-detection support also living in `room_detector_local.py`
- stores verbatim chunks as drawers
- uses `source_file` existence as the main idempotency check

Strengths:

- simple
- easy to understand
- preserves raw text faithfully

Weaknesses:

- dedupe is weak
- chunking is still simple and window-based even though it does try paragraph and line boundaries before falling back
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

The Python chunker is workable and more boundary-aware than a pure fixed-window splitter, but it is still intentionally simple.

Recommended Rust upgrade:

- start with existing boundary-aware fixed windows for parity
- add an internal chunker abstraction
- later support code-aware chunking and transcript-aware chunking with different policies

Suggested trait:

```rust
struct SourceDocument {
    source_file: String,
    content: String,
    media_type: MediaType,
}

struct Chunk {
    content: String,
    chunk_index: i32,
    room_hint: Option<String>,
    metadata: std::collections::BTreeMap<String, String>,
}

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
- stores text that may already include user-turn spellcheck mutation from `spellcheck.py`

Strengths:

- broad format support
- good product value for relatively little code

Weaknesses:

- parsers are somewhat ad hoc
- little schema validation
- mixed concerns between parse, normalize, classify, and store
- the "verbatim" promise is not literal at normalization time because user turns can be corrected before storage

### Rust Recommendation

Break this into four layers:

1. `importers`
   - parse known export formats into typed message structs
2. `normalizers`
   - canonical transcript form, including any intentionally preserved text mutations
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
- make spellcheck-altered transcript behavior explicit in parity fixtures rather than treating normalization as formatting-only
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
- `layers.py` is not just formatting; it also performs direct vector lookups for later layers

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
- keep exact snapshot parity for formatting and filter semantics, but use tolerant benchmark and overlap gates for ranking quality because Rust embeddings will not be float-identical to Chroma defaults

## MCP Server

### Python Today

`mcp_server.py` is a large mixed module with:

- status and taxonomy tools
- search tools
- duplicate checking
- add/delete drawer tools
- graph tools
- knowledge graph tools
- diary tools
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
- `diary_service`

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
- evaluate `rmcp` early, and if it proves unstable or under-maintained, fall back to whichever Rust MCP implementation best supports stdio transport, typed tool schemas, and robust integration testing
- inventory all current tool families up front: status/taxonomy, search, duplicate checking, graph traversal, knowledge graph mutation/query, drawer write/delete, diary write/read, and AAAK-spec exposure

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
- `tokio-rusqlite` if you want a `rusqlite`-style API without blocking the async runtime

My recommendation here:

- prefer `sqlx` or `tokio-rusqlite` by default because `LanceDB` already pulls the rewrite toward Tokio
- use plain `rusqlite` only for deliberately synchronous tooling paths

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
- an optional Python-only Wikipedia lookup path for unknown terms, initiated from the registry side

Strengths:

- useful product feature
- mostly deterministic

Weaknesses:

- some logic is broad and heuristic-heavy
- registry schema is JSON-file centric
- the Wikipedia research path is networked, heuristic, untested in normal app flow, and not core to the local-first product shape

### Rust Recommendation

Split the problem:

1. `entity_registry`
   - SQLite-backed or JSON-backed, but with a typed schema
2. `entity_detector`
   - regex/rule engine

Recommendation:

- default to local-only behavior in Rust
- do not implement Wikipedia enrichment or any automatic external entity lookup in the Rust release
- keep entity handling limited to local heuristics, onboarding data, and explicit user-managed registry state
- treat external enrichment as out of scope unless there is a later product decision to add a separately reviewed feature

What you gain:

- clearer privacy posture
- less policy confusion
- easier testing

What you lose:

- less "magic" for unknown names, but no current product dependency on that behavior

On storage choice:

- move the registry into SQLite if you want one coherent operational store
- keep JSON export/import for portability and manual edits

## Onboarding

### Python Today

`onboarding.py` is a terminal interview that seeds:

- people
- projects
- wings
- people-map aliases and name normalization inputs
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
- explicitly local-only entity handling with no networked enrichment

## Security and Privacy Impact of the Rust Port

From the Chroma replacement perspective, a Rust + LanceDB design improves things mostly by making behavior explicit, not by creating a new privacy model.

What improves:

- fewer dynamic runtime surprises
- easier auditability of storage behavior
- no hidden Python dependency behavior around vector storage
- easier to guarantee exact local embedding paths if you own the embedding stack

What does not automatically improve:

- intentional MCP exposure to hosted LLM clients
- user choice to ingest sensitive files
- verbatim storage of private text

The first item is an accepted product behavior, not an accidental flaw. If the Rust app keeps the same MCP-facing product shape, the trust model remains the same: local storage, but user-approved exposure to whichever LLM client is connected. The storage rewrite is still a sound engineering upgrade, but it is not itself a new privacy boundary unless you also enforce local-only embedding and local-only model usage.

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

## Execution Planning Note

The old five-phase rewrite sketch that previously lived here is superseded by the maintained execution plan in [RustMigrationTasks.md](RustMigrationTasks.md) and [RustImplementationPhasePlans.md](RustImplementationPhasePlans.md).

Use this document for architecture and design rationale. Use the task and phase-plan documents for sequencing, scope gates, and implementation checklists.

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
