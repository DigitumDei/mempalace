# Phase 11 Plan: Low-CPU Hardening for e2-micro

## Objective

Make the Rust implementation usable on a very small always-on VM by enforcing bounded concurrency, memory ceilings, and degraded-mode behavior intentionally.

## Dependencies

- Phase 3 embeddings subsystem has profile and benchmark support.
- Phase 4 through Phase 9 have working end-to-end flows to harden.

## Implementation Workstreams

### 1. Low-CPU Mode Definition

- Lock the approved low-CPU operating profile:
  - smallest approved embedding model
  - batch ingest only
  - no default rerank
  - bounded worker count

### 2. Concurrency and Backpressure

- Add worker caps and queue limits.
- Prevent ingest and query work from exhausting memory on small hosts.

### 3. Lazy Initialization

- Delay expensive model work where it is safe.
- Keep startup deterministic and avoid hidden first-query surprises where possible.

### 4. Instrumentation and Benchmarks

- Capture latency and RSS under low-CPU conditions.
- Treat the measurements recorded in Phase 3 as the subsystem baseline, and use this phase to validate the final low-CPU acceptance budgets on end-to-end flows.
- Validate behavior on a fixture set that resembles personal always-on use.

## Deliverables

- Low-CPU config mode
- Bounded concurrency and backpressure controls
- Lazy initialization where safe
- Benchmark and instrumentation support for low-resource environments

## To-Do Checklist

- [ ] Define low-CPU profile behavior in config and docs.
- [ ] Lock smallest approved embedding model for low-CPU mode.
- [ ] Disable default rerank in low-CPU mode.
- [ ] Bound worker count.
- [ ] Bound ingest batch size.
- [ ] Add backpressure for queued work.
- [ ] Add lazy model initialization where safe.
- [ ] Add latency instrumentation.
- [ ] Add RSS instrumentation.
- [ ] Add small-VM benchmark fixture.
- [ ] Add low-CPU config tests.
- [ ] Add bounded concurrency tests.
- [ ] Add degraded-mode behavior tests.
- [ ] Measure warm query p95.
- [ ] Measure idle warm RSS.
- [ ] Measure single-worker ingest RSS.
- [ ] Validate results against documented budgets.

## Exit Gates

- Low-CPU suite passes.
- Warm query and memory budgets are met.
- Degraded-mode behavior is documented and test-covered.

## Risks To Watch

- Treating low-CPU mode as a benchmark-only concern instead of a product mode.
- Hidden concurrency paths bypassing worker caps.
- Lazy initialization creating user-visible latency spikes without documentation.
