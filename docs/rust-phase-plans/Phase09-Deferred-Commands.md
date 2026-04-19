# Phase 9 Deferred Commands

Phase 9 delivers the Rust CLI for the core day-to-day flows: `init`, `mine`, `search`, `status`, and `wake-up`.

Two Python CLI commands are explicitly deferred instead of being silently omitted:

- `split`
  Reason: the Rust workspace does not yet have a transcript file-splitting subsystem or fixture set that would let us preserve the Python command contract safely.
- `compress`
  Reason: the AAAK dialect library exists, but the Rust CLI does not yet have a storage-level compressed drawer workflow that matches the Python command semantics.

Phase 9 behavior:

- both commands remain visible in `--help`
- both commands exit non-zero with a message that they are deferred
- both commands point callers at this record so the gap is explicit

This keeps the Phase 9 parity surface honest while leaving room to add those workflows in a later phase without pretending they were already shipped.
