# Reference Environment

## Baseline

- Python version used for the committed Phase 0 capture: `3.11.2`
- Python implementation: `CPython`
- Dependency inputs recorded from: `pyproject.toml` and `requirements.txt`
- Resolved package versions from the capture environment are snapshotted in `tests/fixtures/phase0/inventory/environment.json`.
- Local dependency bootstrap used for the committed Phase 0 capture in this repo:
  - `pip3 install --target .phase0_vendor chromadb pyyaml pytest build twine`

The bootstrap command above is a record of how the current baseline was captured, not a lockfile-backed installer. Until Phase 0 pinning is tightened further, treat `environment.json` plus the dependency inputs as the authoritative environment record.

## Regeneration Command

```bash
PYTHONPATH=.phase0_vendor:. python3 scripts/phase0_capture.py
```

## Drift Check Command

```bash
PYTHONPATH=.phase0_vendor:. python3 scripts/check_phase0_drift.py
```

## Warm Cache Policy

- The capture script uses the Python reference implementation directly.
- Search goldens rely on Chroma's default embedding path and may warm model assets on first run.
- Drift enforcement is split by contract surface: exact-byte for CLI/MCP/graph assets, semantic comparison for search outputs and wake-up outputs. `search-cli.txt` preserves layout, result identity, and meaningful ranking, but raw similarity floats are treated as tolerant.
- `scripts/check_phase0_drift.py` captures into a temporary output root via `MEMPALACE_PHASE0_OUTPUT_ROOT` before comparing against committed fixtures, so the workspace is not rewritten during drift detection.
- Some committed graph and search fixtures also depend on deterministic in-script seed records added during capture so the corpus exercises tunnel traversal, `connected_via`, and mixed-wing search cases consistently.
- Regeneration should be run once with network access to warm assets, then rerun in a no-network environment when Phase 0 pinning is tightened further.

## Zero-Network Goal

Phase 0 establishes the workflow but does not yet prove zero-network replay for Chroma's implicit embedding model. Before Rust Phase 1 starts, this doc should be updated with:

- exact model identifier
- local model asset path or checksum
- a verified no-network regeneration invocation

## Review Rule

Do not overwrite committed goldens blindly. Regenerate, inspect diffs, and update the fixture lock manifest intentionally.
