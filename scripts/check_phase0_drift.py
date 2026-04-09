#!/usr/bin/env python3
"""Regenerate Phase 0 outputs in-place and fail if exact or tolerant contracts drift."""

from __future__ import annotations

import json
import tempfile
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "phase0"

EXACT_FILES = {
    "fixture-lock.json",
    "goldens/aaak.json",
    "goldens/knowledge-graph.json",
    "goldens/mcp-contract.json",
    "goldens/palace-graph.json",
    "goldens/wake-up-wing-code.txt",
    "goldens/wake-up.txt",
    "inventory/cli-help.json",
    "inventory/environment.json",
    "inventory/mcp-tools.json",
}
TOLERANT_FILES = {
    "goldens/search-cli.txt",
    "goldens/search-programmatic.json",
}
MANAGED_FILES = EXACT_FILES | TOLERANT_FILES


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_search_results(results: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized = []
    for result in results:
        normalized.append(
            {
                "wing": result.get("wing"),
                "room": result.get("room"),
                "source_file": result.get("source_file"),
                "text": result.get("text"),
            }
        )
    return sorted(
        normalized,
        key=lambda item: (
            str(item["wing"]),
            str(item["room"]),
            str(item["source_file"]),
            str(item["text"]),
        ),
    )


def _normalize_programmatic_search(path: Path) -> object:
    payload = _load_json(path)
    normalized = {}
    for key, entry in payload.items():
        normalized[key] = {
            "query": entry["query"],
            "filters": entry["filters"],
            "results": _normalize_search_results(entry["results"]),
        }
    return normalized


def _parse_search_cli(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next((line.strip() for line in lines if "Results for:" in line), "")
    blocks = []
    current = None

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("[") and "]" in stripped and " / " in stripped:
            if current:
                blocks.append(current)
            location = stripped.split("]", 1)[1].strip()
            wing, room = [part.strip() for part in location.split(" / ", 1)]
            current = {"wing": wing, "room": room, "source_file": "", "text": []}
            continue
        if current is None:
            continue
        if stripped.startswith("Source:"):
            current["source_file"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("Match:"):
            continue
        if stripped.startswith("────────────────"):
            blocks.append(current)
            current = None
            continue
        if raw_line.startswith("      ") and stripped:
            current["text"].append(stripped)

    if current:
        blocks.append(current)

    normalized_blocks = sorted(
        (
            {
                "wing": block["wing"],
                "room": block["room"],
                "source_file": block["source_file"],
                "text": "\n".join(block["text"]).strip(),
            }
            for block in blocks
        ),
        key=lambda item: (item["wing"], item["room"], item["source_file"], item["text"]),
    )
    return {"title": title, "results": normalized_blocks}


def _compare_tolerant(rel_path: str, before_root: Path, after_root: Path) -> bool:
    before_path = before_root / rel_path
    after_path = after_root / rel_path
    if rel_path.endswith("search-programmatic.json"):
        return _normalize_programmatic_search(before_path) == _normalize_programmatic_search(after_path)
    if rel_path.endswith("search-cli.txt"):
        return _parse_search_cli(before_path) == _parse_search_cli(after_path)
    raise ValueError(f"Unhandled tolerant file: {rel_path}")


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    before = _snapshot_tree(FIXTURE_ROOT)
    proc = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "phase0_capture.py")], cwd=REPO_ROOT)
    if proc.returncode != 0:
        return proc.returncode

    after = _snapshot_tree(FIXTURE_ROOT)

    failures = []
    changed_files = sorted(set(before) | set(after))
    for rel in changed_files:
        if rel not in before or rel not in after:
            failures.append(f"{rel}: file added or removed")
            continue
        if rel in EXACT_FILES:
            if before[rel] != after[rel]:
                failures.append(f"{rel}: exact contract changed")
            continue
        if rel not in MANAGED_FILES and before[rel] != after[rel]:
            failures.append(f"{rel}: unmanaged generated file changed")

    if any(rel in TOLERANT_FILES for rel in changed_files):
        with tempfile.TemporaryDirectory(prefix="phase0-before-") as before_tmp_str:
            with tempfile.TemporaryDirectory(prefix="phase0-after-") as after_tmp_str:
                before_tmp = Path(before_tmp_str)
                after_tmp = Path(after_tmp_str)
                for rel, payload in before.items():
                    path = before_tmp / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)
                for rel, payload in after.items():
                    path = after_tmp / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)

                for rel in changed_files:
                    if rel not in TOLERANT_FILES:
                        continue
                    if not _compare_tolerant(rel, before_tmp, after_tmp):
                        failures.append(f"{rel}: tolerant contract changed")

    if failures:
        print("Phase 0 fixture drift detected.")
        for failure in failures:
            print(failure)
        return 1

    print("Phase 0 fixtures are stable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
