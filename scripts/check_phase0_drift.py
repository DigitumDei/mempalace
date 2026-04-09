#!/usr/bin/env python3
"""Regenerate Phase 0 outputs in-place and fail if anything changed."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "phase0"


def _digest_tree() -> dict[str, str]:
    hashes = {}
    for path in sorted(FIXTURE_ROOT.rglob("*")):
        if path.is_file():
            hashes[str(path.relative_to(FIXTURE_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def main() -> int:
    before = _digest_tree()
    proc = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "phase0_capture.py")], cwd=REPO_ROOT)
    if proc.returncode != 0:
        return proc.returncode

    after = _digest_tree()
    if before != after:
        print("Phase 0 fixture drift detected. Review the regenerated files under tests/fixtures/phase0/.")
        for rel in sorted(set(before) | set(after)):
            if before.get(rel) != after.get(rel):
                print(rel)
        return 1

    print("Phase 0 fixtures are stable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
