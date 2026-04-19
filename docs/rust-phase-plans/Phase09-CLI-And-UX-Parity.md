# Phase 9 Plan: CLI and UX Parity

## Objective

Make the Rust application feel like MemPalace by porting the CLI command surface, output formatting, and core user workflows.

## Dependencies

- Phase 4 ingest is functional.
- Phase 5 search and wake-up are stable.
- Phase 8 MCP work has clarified any shared command and config semantics.

## Implementation Workstreams

### 1. Command Surface

- Implement CLI commands and flags from the approved parity inventory.
- Preserve help text quality, exit codes, and command semantics.

### 2. Core Flows

- Port `init`, `mine`, `search`, `status`, and `wake-up`.
- Ensure these flows compose correctly with config, storage, and embeddings.

### 3. Output Formatting

- Match Python-visible formatting where exact parity is required.
- Keep human-readable output stable enough for snapshot tests.

### 4. Deferred Command Decisions

- Decide whether `split` is in scope.
- Decide whether `compress` is in scope.
- If deferred, mark them explicitly rather than leaving silent gaps.
- Decision record: [Phase09-Deferred-Commands.md](Phase09-Deferred-Commands.md)

## Deliverables

- Rust CLI binary crate
- Ported command implementations
- Snapshot-tested output formatting
- Scope decision record for `split` and `compress`

## To-Do Checklist

- [ ] Implement CLI command parser and flags.
- [ ] Implement `init`.
- [ ] Implement `mine`.
- [ ] Implement `search`.
- [ ] Implement `status`.
- [ ] Implement `wake-up`.
- [ ] Port search output formatting.
- [ ] Match approved exit code behavior.
- [ ] Match approved help text behavior.
- [ ] Decide whether `split` remains in scope.
- [ ] Implement `split` if retained.
- [ ] Decide whether `compress` remains in scope.
- [ ] Implement `compress` if retained.
- [ ] Document deferred commands if omitted.
- [ ] Add CLI snapshot tests.
- [ ] Add exit code tests.
- [ ] Add help text tests.
- [ ] Add `split` contract tests if retained.
- [ ] Add `compress` contract tests if retained.
- [ ] Add end-to-end command tests.

## Exit Gates

- CLI parity tests pass.
- Core user workflows work end to end.
- Any deferred commands are explicit in docs and help output.

## Risks To Watch

- Matching functionality while letting UX and output drift.
- Silent removal of `split` or `compress`.
- Snapshot churn caused by unstable formatting decisions.
