# Phase 12 Plan: Release Readiness

## Objective

Cut a first Rust release with frozen schemas, known scope boundaries, passing gates, and operator documentation for normal and low-CPU deployments.

## Dependencies

- All in-scope prior phases are complete.
- Any deferred features are explicitly documented.

## Implementation Workstreams

### 1. Schema and Surface Freeze

- Freeze CLI behavior and config schemas for the release.
- Confirm no unresolved parity gaps remain in in-scope surfaces.

### 2. Final Validation

- Run the full regression, benchmark, and low-CPU suites.
- Run optional Python interop validation only if that feature ships.

### 3. Packaging and Distribution

- Build release artifacts.
- Validate installation and execution paths for supported targets.

### 4. Operator Documentation

- Write deployment and operational docs for standard and low-CPU modes.
- Document model acquisition, warm-cache expectations, storage recovery, and troubleshooting.

## Deliverables

- Frozen CLI and config schema references
- Final regression and benchmark reports
- Release artifacts
- Operator documentation
- Explicit release scope statement

## Current Branch Artifacts

The release-readiness documentation set for the implemented Rust surface lives in [../rust-release/README.md](../rust-release/README.md).

Current artifacts added for Phase 12 documentation and scope freeze:

- [Release Scope](../rust-release/Release-Scope.md)
- [CLI Surface](../rust-release/CLI-Surface.md)
- [Config Schema](../rust-release/Config-Schema.md)
- [Standard Operator Guide](../rust-release/Operator-Standard.md)
- [Low-CPU Operator Guide](../rust-release/Operator-Low-CPU.md)
- [Packaging And Validation](../rust-release/Packaging-And-Validation.md)

## To-Do Checklist

- [ ] Freeze CLI command surface.
- [ ] Freeze config schema.
- [ ] Review remaining parity gaps.
- [ ] Confirm all in-scope gaps have owners or are closed.
- [ ] Run full unit suite.
- [ ] Run full integration suite.
- [ ] Run regression suite.
- [ ] Run benchmark suite.
- [ ] Run low-CPU suite.
- [ ] Run optional interop suite if interop ships.
- [ ] Build packaging artifacts.
- [ ] Validate install flow for release artifacts.
- [ ] Write operator docs for standard deployment.
- [ ] Write operator docs for low-CPU deployment.
- [ ] Document model acquisition and warm-cache workflow.
- [ ] Document storage recovery and troubleshooting.
- [ ] Publish release scope and known limitations.

## Exit Gates

- All required suites pass.
- Benchmarks and low-CPU targets are met.
- Release artifacts and operator docs are complete.
- No unowned parity gaps remain.

## Risks To Watch

- Treating release readiness as packaging only.
- Freezing schemas before deferred-scope decisions are resolved.
- Shipping without operator guidance for offline and recovery scenarios.
