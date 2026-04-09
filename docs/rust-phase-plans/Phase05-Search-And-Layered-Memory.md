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

## To-Do Checklist

- [ ] Implement query embedding to vector search flow.
- [ ] Implement `top_k` retrieval handling.
- [ ] Implement wing prefiltering.
- [ ] Implement room prefiltering.
- [ ] Match Python filter semantics on fixtures.
- [ ] Implement score normalization.
- [ ] Implement deterministic tie-breaking.
- [ ] Implement empty-result behavior.
- [ ] Implement layered memory assembly.
- [ ] Implement wake-up generation.
- [ ] Generate wake-up output in stable order.
- [ ] Decide compressed drawer scope for first release.
- [ ] Implement compressed drawer retrieval if retained.
- [ ] Add retrieval golden tests.
- [ ] Add filter tests.
- [ ] Add empty-state tests.
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
