# Rust Implementation Phase Plans

This document expands the execution phases in [RustMigrationTasks.md](RustMigrationTasks.md) into working implementation plans.

Each phase has its own plan document with:

- implementation scope
- prerequisites and dependencies
- concrete workstreams
- deliverables
- explicit to-do lists
- exit gates

Phase documents:

- [Phase 0](rust-phase-plans/Phase00-Spec-Lock-And-Fixture-Harvest.md)
- [Phase 1](rust-phase-plans/Phase01-Workspace-And-Core-Foundations.md)
- [Phase 2](rust-phase-plans/Phase02-Storage-Layer.md)
- [Phase 3](rust-phase-plans/Phase03-Embeddings-Subsystem.md)
- [Phase 4](rust-phase-plans/Phase04-Ingest-Pipeline.md)
- [Phase 5](rust-phase-plans/Phase05-Search-And-Layered-Memory.md)
- [Phase 6](rust-phase-plans/Phase06-Knowledge-Graph-And-Entity-Workflow.md)
- [Phase 7](rust-phase-plans/Phase07-AAAK-Dialect.md)
- [Phase 8](rust-phase-plans/Phase08-MCP-Server.md)
- [Phase 9](rust-phase-plans/Phase09-CLI-And-UX-Parity.md)
- [Phase 10 (Optional)](rust-phase-plans/Phase10-Optional-Python-Interop-Tooling.md)
- [Phase 11](rust-phase-plans/Phase11-Low-CPU-Hardening.md)
- [Phase 12](rust-phase-plans/Phase12-Release-Readiness.md)

Phase sequencing note:

- Phase 10 is conditional. Only execute it if Python-state inspection or import remains in release scope after the Phase 10 scope-lock decision.

Recommended usage:

1. Keep [RustMigration.md](RustMigration.md) as the architecture source.
2. Keep [RustMigrationTasks.md](RustMigrationTasks.md) as the top-level execution map and test policy.
3. Use the per-phase documents as the delivery checklist while work is active.
4. Update phase documents when scope, gates, or parity decisions change so the detailed plans do not drift from the master task plan.
