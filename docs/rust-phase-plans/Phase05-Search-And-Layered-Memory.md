# Phase 5 Plan: Search and Layered Memory

## Objective

Reproduce semantic search, metadata filtering, layered retrieval, and wake-up behavior on the Rust storage and embeddings stack.

## Dependencies

- Phase 2 storage search primitives are complete.
- Phase 3 embeddings are available.
- Phase 4 ingest produces fixture-aligned drawer records.

## Implementation Workstreams

### 1. Search Execution Path

- Implement the semantic retrieval path from query embedding through vector search.
- Define exact behavior for `top_k`, score normalization, and tie-breaking.

### 2. Metadata Prefiltering

- Apply wing and room filtering before or alongside retrieval according to the selected storage strategy.
- Preserve Python-visible filter semantics exactly where required.

### 3. Ranking and Deterministic Ordering

- Normalize scores and merge ranking factors.
- Make deterministic tie-breaking explicit and testable.

### 4. Layered Memory Assembly

- Assemble wake-up and layered memory outputs from drawers, metadata, and graph context.
- Preserve output structure and formatting even where ranking quality is measured tolerantly.

### 5. Compressed Drawer Scope Decision

- Decide whether compressed drawers remain a first-release feature.
- If yes, implement and test them here.
- If no, document the deferment and remove hidden dependencies.

## Deliverables

- Search execution module
- Filter compilation and application logic
- Ranking and ordering logic
- Layered memory assembly module
- Wake-up generation path
- Scope decision record for compressed drawers

## Scope Decision: Compressed Drawers

Compressed drawers are deferred from the first Rust release.

Reasoning:

- Phase 5 needs retrieval parity, stable wake-up output, and deterministic filter semantics on the raw drawer corpus first.
- The current Rust storage layer does not yet carry a separate compressed-drawer table or retrieval path, and leaving that implicit would create a hidden dependency between Phase 5 and later storage/AAAK work.
- AAAK integration is already scheduled explicitly in Phase 7, which is the correct point to decide rendering shape and any compressed retrieval path together.

Operational consequence:

- Phase 5 implements search, recall, and wake-up only over the canonical raw drawer records.
- Phase 2 and later phases should treat compressed-drawer storage as out of scope unless the release plan is explicitly reopened.
- Phase 7 may add AAAK-backed wake-up rendering without requiring a separate compressed retrieval collection for first release.

## To-Do Checklist

- [x] Implement query embedding to vector search flow.
- [x] Implement `top_k` retrieval handling.
- [x] Implement wing prefiltering.
- [x] Implement room prefiltering.
- [x] Match Python filter semantics on fixtures.
- [x] Implement score normalization.
- [x] Implement deterministic tie-breaking.
- [x] Implement empty-result behavior.
- [x] Implement layered memory assembly.
- [x] Implement wake-up generation.
- [x] Generate wake-up output in stable order.
- [x] Decide compressed drawer scope for first release.
- [ ] Implement compressed drawer retrieval if retained.
- [ ] Add retrieval golden tests.
- [x] Add filter tests.
- [x] Add empty-state tests.
- [ ] Add wake-up golden tests.
- [ ] Add layered output integration tests.
- [ ] Add tolerant retrieval quality checks.
- [ ] Measure top-5 overlap against Python reference.
- [ ] Measure Recall@5 ratio against Python reference.

## Exit Gates

- Retrieval parity targets are met.
- Wake-up output is stable on fixtures.
- Compressed drawer scope is either implemented or explicitly deferred.

## Risks To Watch

- Chasing bit-identical ranking where the plan only requires tolerant quality parity.
- Leaving tie-breaking implicit and nondeterministic.
- Mixing output-format parity with retrieval-quality parity in one gate.

## Current Validation Scope

Current Phase 5 coverage is centered on Rust unit and backend tests for ranking, filters, empty states,
layered assembly, wake-up identity loading, Unicode budget handling, and Lance full-corpus listing.
Fixture-backed golden files and broader end-to-end integration parity checks remain pending work.
