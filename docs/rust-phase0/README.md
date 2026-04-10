# Rust Phase 0

Phase 0 locks the Python reference behavior before Rust implementation starts.

Artifacts in this folder:

- `parity-matrix.md` — exact vs tolerant parity policy and intentional divergences
- `mcp-crate-evaluation.md` — initial Rust MCP crate choice and fallback criteria
- `acceptance-criteria.md` — measurable gates for each later subsystem
- `reference-environment.md` — reference regeneration workflow, current environment constraints, and drift policy

Primary generated artifacts live under `tests/fixtures/phase0/`.

Phase 0 is a spec-lock for the current Python implementation, not a fully hermetic replay environment yet. The committed goldens are generated from a mix of fixture inputs under `tests/fixtures/phase0/inputs/` and a small amount of deterministic in-script seed data used to exercise graph and search surfaces that the file corpus alone does not hit. That seeded behavior is part of the committed reference contract until a later phase replaces it with fixture-derived inputs.
