#!/usr/bin/env python3
"""Regenerate Phase 0 outputs in a temp tree and fail if exact or tolerant contracts drift."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "phase0"

EXACT_FILES = {
    "fixture-lock.json",
    "goldens/aaak.json",
    "goldens/knowledge-graph.json",
    "goldens/mcp-contract.json",
    "goldens/palace-graph.json",
    "goldens/search-cli.txt",
    "inventory/cli-help.json",
    "inventory/environment.json",
    "inventory/mcp-tools.json",
}
TOLERANT_FILES = {
    "goldens/search-programmatic.json",
    "goldens/wake-up-wing-code.txt",
    "goldens/wake-up.txt",
}
MANAGED_FILES = EXACT_FILES | TOLERANT_FILES
SEARCH_SIMILARITY_TOLERANCE = 0.05


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _read_text(root: Path, rel_path: str) -> str:
    return (root / rel_path).read_text(encoding="utf-8")


def _normalize_search_result(result: dict[str, object]) -> dict[str, object]:
    normalized = {
        "wing": result.get("wing"),
        "room": result.get("room"),
        "source_file": result.get("source_file"),
        "text": result.get("text"),
    }
    similarity = result.get("similarity")
    if similarity is not None:
        normalized["similarity"] = float(similarity)
    return normalized


def _compare_programmatic_search(before_root: Path, after_root: Path, rel_path: str) -> bool:
    before = _load_json(before_root / rel_path)
    after = _load_json(after_root / rel_path)
    if not isinstance(before, dict) or not isinstance(after, dict) or set(before) != set(after):
        return False

    for key in sorted(before):
        before_entry = before[key]
        after_entry = after[key]
        if before_entry.get("query") != after_entry.get("query"):
            return False
        if before_entry.get("filters") != after_entry.get("filters"):
            return False

        before_results = before_entry.get("results", [])
        after_results = after_entry.get("results", [])
        if len(before_results) != len(after_results):
            return False

        before_by_identity = {}
        after_by_identity = {}
        for result in before_results:
            normalized = _normalize_search_result(result)
            identity = (
                normalized["wing"],
                normalized["room"],
                normalized["source_file"],
                normalized["text"],
            )
            before_by_identity[identity] = normalized
        for result in after_results:
            normalized = _normalize_search_result(result)
            identity = (
                normalized["wing"],
                normalized["room"],
                normalized["source_file"],
                normalized["text"],
            )
            after_by_identity[identity] = normalized

        if set(before_by_identity) != set(after_by_identity):
            return False

        for identity in sorted(before_by_identity):
            before_norm = before_by_identity[identity]
            after_norm = after_by_identity[identity]
            if (
                before_norm["wing"] != after_norm["wing"]
                or before_norm["room"] != after_norm["room"]
                or before_norm["source_file"] != after_norm["source_file"]
                or before_norm["text"] != after_norm["text"]
            ):
                return False
            if "similarity" in before_norm or "similarity" in after_norm:
                if "similarity" not in before_norm or "similarity" not in after_norm:
                    return False
                if abs(before_norm["similarity"] - after_norm["similarity"]) > SEARCH_SIMILARITY_TOLERANCE:
                    return False
    return True


def _parse_wake_up(text: str) -> dict[str, object]:
    lines = text.splitlines()
    if len(lines) < 6:
        return {"header": [], "rooms": []}

    header = lines[:6]
    rooms = []
    current = None
    for line in lines[6:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            if current is not None:
                rooms.append(current)
            current = {"room": stripped[1:-1], "bullets": []}
            continue
        if stripped.startswith("- "):
            if current is None:
                continue
            current["bullets"].append(stripped)
    if current is not None:
        rooms.append(current)
    return {"header": header, "rooms": rooms}


def _compare_wake_up(before_root: Path, after_root: Path, rel_path: str) -> bool:
    before = _parse_wake_up(_read_text(before_root, rel_path))
    after = _parse_wake_up(_read_text(after_root, rel_path))
    if before["header"] != after["header"]:
        return False
    before_rooms = {room["room"]: room["bullets"] for room in before["rooms"]}
    after_rooms = {room["room"]: room["bullets"] for room in after["rooms"]}
    if not before_rooms or not after_rooms:
        return False
    for room_name, bullets in after_rooms.items():
        if not room_name or not bullets:
            return False
        if room_name not in before_rooms:
            return False
        if any(bullet not in before_rooms[room_name] for bullet in bullets):
            return False
    return True


def _compare_tolerant(rel_path: str, before_root: Path, after_root: Path) -> bool:
    if rel_path.endswith("search-programmatic.json"):
        return _compare_programmatic_search(before_root, after_root, rel_path)
    if rel_path.endswith("wake-up.txt") or rel_path.endswith("wake-up-wing-code.txt"):
        return _compare_wake_up(before_root, after_root, rel_path)
    raise ValueError(f"Unhandled tolerant file: {rel_path}")


def main() -> int:
    before = _load_tree(FIXTURE_ROOT)

    with tempfile.TemporaryDirectory(prefix="phase0-regenerated-") as temp_root_str:
        temp_root = Path(temp_root_str)
        env = os.environ.copy()
        env["MEMPALACE_PHASE0_OUTPUT_ROOT"] = str(temp_root)
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "phase0_capture.py")],
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

        after = _load_tree(temp_root)

        failures = []
        changed_files = sorted(set(before) | set(after))
        for rel in changed_files:
            if rel.startswith("inputs/"):
                continue
            if rel not in before or rel not in after:
                failures.append(f"{rel}: file added or removed")
                continue
            if rel in EXACT_FILES:
                if before[rel] != after[rel]:
                    failures.append(f"{rel}: exact contract changed")
                continue
            if rel in TOLERANT_FILES:
                if not _compare_tolerant(rel, FIXTURE_ROOT, temp_root):
                    failures.append(f"{rel}: tolerant contract changed")
                continue
            if rel not in MANAGED_FILES:
                failures.append(f"{rel}: unmanaged generated file present")

        if failures:
            print("Phase 0 fixture drift detected.")
            for failure in failures:
                print(failure)
            return 1

    print("Phase 0 fixtures are stable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
