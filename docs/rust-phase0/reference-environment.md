# Reference Environment

## Baseline

- Python executable: `python3`
- Package metadata source: `pyproject.toml` and `requirements.txt`
- Local dependency bootstrap used for Phase 0 capture in this repo:
  - `pip3 install --target .phase0_vendor chromadb pyyaml pytest build twine`

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
- Regeneration should be run once with network access to warm assets, then rerun in a no-network environment when Phase 0 pinning is tightened further.

## Zero-Network Goal

Phase 0 establishes the workflow but does not yet prove zero-network replay for Chroma's implicit embedding model. Before Rust Phase 1 starts, this doc should be updated with:

- exact model identifier
- local model asset path or checksum
- a verified no-network regeneration invocation

## Review Rule

Do not overwrite committed goldens blindly. Regenerate, inspect diffs, and update the fixture lock manifest intentionally.
