# Phase 4 Plan: Ingest Pipeline

## Objective

Port project mining, conversation mining, normalization, extraction, and incremental indexing into a deterministic Rust ingest pipeline.

## Dependencies

- Phase 2 storage layer is operational.
- Phase 3 embeddings subsystem is usable and benchmarked enough for integration.
- Phase 0 fixtures include representative project and conversation inputs.

## Implementation Workstreams

### 1. File Discovery and Ignore Semantics

- Implement filesystem walking and ignore handling.
- Match current project-mining behavior where parity is required.
- Define what counts as skipped, ignored, unreadable, or malformed.

### 2. Project Chunking

- Port chunking boundaries for code, docs, and large files.
- Preserve deterministic chunk ids and file-hash behavior.
- Keep chunking testable independently from embedding and storage.

### 3. Conversation Parsing

- Port chat export parsing for supported formats.
- Normalize date, speaker, and message boundaries.
- Fail gracefully on malformed exports without poisoning the run.

### 4. Normalization and Extraction

- Port normalization logic and spellcheck-adjacent mutation rules.
- Port general extraction mode.
- Make intentional divergences explicit if Python logic is too loose to preserve exactly.

### 5. Incremental Reindexing

- Implement file hashing and change detection.
- Reindex only when content or relevant metadata changed.
- Preserve deterministic rerun behavior.

### 6. Storage Write Path

- Write indexed records using the Phase 2 dual-store contract.
- Ensure partial ingest runs do not create invisible inconsistencies.

## Deliverables

- File discovery module
- Chunking module
- Conversation parsers
- Normalization and extraction modules
- Incremental reindex logic
- End-to-end ingest path into storage

## To-Do Checklist

- [ ] Implement filesystem traversal.
- [ ] Implement ignore file and ignore-rule handling.
- [ ] Define skipped versus failed file behavior.
- [ ] Port project chunking logic.
- [ ] Port large-file cutoff and truncation policy.
- [ ] Port conversation export parsing.
- [ ] Normalize timestamps, speakers, and message boundaries.
- [ ] Implement malformed export handling.
- [ ] Port normalization functions.
- [ ] Port spellcheck-related normalization behavior.
- [ ] Port general extraction mode.
- [ ] Define deterministic chunk id generation.
- [ ] Implement file hashing.
- [ ] Implement changed-file reindex decisions.
- [ ] Implement idempotent rerun behavior.
- [ ] Write records through manifest and drawer stores.
- [ ] Add project fixture ingest tests.
- [ ] Add conversation fixture ingest tests.
- [ ] Add normalization golden tests.
- [ ] Add spellcheck-mutation normalization tests.
- [ ] Add extraction golden tests.
- [ ] Add reindex idempotency tests.
- [ ] Add malformed export tests.
- [ ] Add ignored-file behavior tests.

## Exit Gates

- Fixture-based ingest tests pass.
- Reruns are deterministic and idempotent.
- Malformed and ignored inputs are handled predictably.

## Risks To Watch

- Tight coupling between parse, normalize, embed, and store steps.
- Hidden Python edge-case behavior not captured in fixtures.
- Reindex logic that appears idempotent but diverges after partial failures.
