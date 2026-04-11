# Rust Parity Matrix

This matrix defines which Python behaviors the Rust implementation must preserve exactly, which can be matched with tolerance, and which are allowed to diverge intentionally.

## Exact Parity Required

| Surface | Requirement | Reason |
|---|---|---|
| CLI command names | `init`, `mine`, `split`, `search`, `compress`, `wake-up`, `status` | User-facing contract |
| CLI flag names | Preserve current long flags and meanings | Shell scripts and docs depend on them |
| CLI help surface | Same command/flag inventory, close wording acceptable | Discoverability contract |
| Search filter semantics | `wing`, `room`, and combined `$and` behavior | Retrieval scope correctness |
| Search formatting shape | Header, result numbering, source label, match label, verbatim body | High-signal CLI output contract |
| Wake-up structure | `L0`, blank line, `L1` sections in that order | Prompt injection contract |
| MCP tool names | Preserve all current tool ids | Client compatibility |
| MCP tool request field names | Preserve current JSON field names | Wire compatibility |
| MCP error envelope shape | JSON-RPC error object with current code/message pattern | Client handling contract |
| AAAK spec tool payload | Return key `aaak_spec` with current text shape | Agent bootstrap contract |
| Palace graph field names | Preserve `room`, `wings`, `halls`, `count`, `hop`, `connected_via`, `recent` | Graph client compatibility |

## Tolerant Parity Required

| Surface | Tolerance | Reason |
|---|---|---|
| Search ranking | Preserve useful relevance; exact ordering only where scores tie | Backend and embedding implementation will change |
| Similarity values | Numeric values may differ within backend/model tolerance | Distance math differs across stores |
| CLI search scores | Preserve layout and result identity, but tolerate raw `Match:` float drift | CLI prints backend-derived similarity values directly |
| Wake-up drawer selection | Preserve top-story usefulness, room membership, and bullet order within each room | Storage changes should not break user experience |
| Chunk boundaries | Preserve semantics on fixture corpus, not byte-identical splits for all inputs | Rust chunker may have minor boundary differences |
| Graph traversal ordering | Stable ordering preferred, but exact ordering only required for same hop/count groups | Derived graph can be normalized deterministically |
| Knowledge graph ids | Triple/entity ids may diverge if shape and query results match | Internal identifier format is implementation detail |

## Intentional Divergences

| Surface | Divergence | Reason |
|---|---|---|
| Storage backend | `ChromaDB` to `LanceDB` + `SQLite` | Explicit schema and migration control |
| Embedding ownership | Implicit Chroma default to explicit Rust embedding subsystem | Reproducibility and offline guarantees |
| Metadata schema | Loose dicts to typed structs/tables | Safer migrations and validation |
| Recovery behavior | Best-effort Python writes to explicit manifest/reconciliation contract | Idempotent ingest in dual-store architecture |
| MCP implementation | Hand-rolled JSON-RPC loop to Rust MCP crate | Maintainability and protocol coverage |

## Notes

- Any new divergence must be added here before Rust implementation depends on it.
- Goldens under `tests/fixtures/phase0/` are the reference for exact-parity surfaces.
