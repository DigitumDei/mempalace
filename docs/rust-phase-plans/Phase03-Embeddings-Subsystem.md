# Phase 3 Plan: Embeddings Subsystem

## Objective

Make embeddings an explicit, configurable, offline-capable subsystem with clear model profiles, cache validation, and performance budgets.

## Dependencies

- Phase 1 embedding profiles and dimensions are locked.
- Phase 2 storage schema is ready to consume explicit vector dimensions.

## Implementation Workstreams

### 1. Provider Abstraction

- Define an `EmbeddingProvider` trait with clear input, output, batch, and error semantics.
- Keep provider behavior consistent enough for contract testing across future backends.

### 2. Initial Backend

- Implement the first provider using `fastembed`.
- Ensure warm-cache and missing-asset behavior are observable and testable.

### 3. Profile Selection

- Implement `balanced` profile support with `all-MiniLM-L6-v2` and `384` dimensions.
- Add `low_cpu` profile with explicit model id and dimensions.
- Support config-driven profile selection without implicit defaults leaking into storage.

### 4. Cache and Startup Validation

- Validate model presence and integrity at startup.
- Detect corrupted or partial downloads.
- Fail clearly when offline startup cannot proceed due to missing assets.

### 5. Performance Budget Enforcement

- Build measurement hooks for latency and memory budgets.
- Capture warm path benchmarks on the reference environment.

## Deliverables

- Embedding provider trait
- `fastembed` implementation
- Profile selection and validation logic
- Cache validation and startup checks
- Benchmark harness for embedding-related budgets

## To-Do Checklist

- [ ] Define `EmbeddingProvider` trait.
- [ ] Define provider input and output contract types.
- [ ] Implement `fastembed` provider.
- [ ] Implement `balanced` profile mapping.
- [ ] Implement `low_cpu` profile mapping.
- [ ] Implement config-driven profile selection.
- [ ] Enforce configured dimension checks.
- [ ] Implement warm-cache startup path.
- [ ] Implement missing-assets failure path.
- [ ] Implement partial-download detection.
- [ ] Implement corrupted-cache detection.
- [ ] Expose startup validation status to CLI or logs.
- [ ] Add provider contract tests.
- [ ] Add profile resolution tests.
- [ ] Add dimension mismatch tests.
- [ ] Add offline startup tests with warm cache.
- [ ] Add missing-asset tests.
- [ ] Add partial-download and corrupted-cache tests.
- [ ] Add benchmark harness for embedding latency.
- [ ] Record `balanced` warm query embedding p95.
- [ ] Record `low_cpu` warm query embedding p95.
- [ ] Record `low_cpu` end-to-end search p95 on the small VM fixture.
- [ ] Record `low_cpu` idle warm RSS.
- [ ] Record `low_cpu` single-worker ingest RSS.

## Exit Gates

- Embedding provider tests pass.
- Startup behavior is deterministic and actionable in offline scenarios.
- Performance numbers are recorded against the initial budget targets.

## Risks To Watch

- Treating model download state as a side effect instead of part of the contract.
- Letting profile selection change vector dimensions after storage is initialized.
- Missing benchmark instrumentation until after higher-level phases are already built.
