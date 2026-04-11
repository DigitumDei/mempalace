#!/usr/bin/env python3
"""Regenerate Phase 0 outputs in a temp tree and fail if exact or tolerant contracts drift."""

from __future__ import annotations

import json
import os
import re
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
    "inventory/cli-help.json",
    "inventory/environment.json",
    "inventory/mcp-tools.json",
}
TOLERANT_FILES = {
    "goldens/search-cli.txt",
    "goldens/search-programmatic.json",
    "goldens/wake-up-wing-code.txt",
    "goldens/wake-up.txt",
}
MANAGED_FILES = EXACT_FILES | TOLERANT_FILES
SEARCH_SIMILARITY_TOLERANCE = 0.05
CLI_RESULT_HEADER = re.compile(r"^  \[(?P<index>\d+)\] (?P<wing>.+) / (?P<room>.+)$")
CLI_SOURCE_LINE = re.compile(r"^      Source: (?P<source>.+)$")
CLI_MATCH_LINE = re.compile(r"^      Match:  (?P<similarity>-?\d+(?:\.\d+)?)$")


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


def _python_series(version: str) -> str:
    parts = version.split(".")
    if len(parts) < 2:
        return version
    return ".".join(parts[:2])


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


def _normalize_cli_result(result: dict[str, object]) -> dict[str, object]:
    normalized = {
        "wing": result["wing"],
        "room": result["room"],
        "source_file": result["source_file"],
        "body": list(result["body"]),
    }
    similarity = result.get("similarity")
    if similarity is not None:
        normalized["similarity"] = float(similarity)
    return normalized


def _compare_ranked_results(
    before_results: list[dict[str, object]], after_results: list[dict[str, object]]
) -> bool:
    if len(before_results) != len(after_results):
        return False

    def identity_of(result: dict[str, object]) -> tuple[object, ...]:
        identity = [result["wing"], result["room"], result["source_file"]]
        if "text" in result:
            identity.append(result["text"])
        identity.extend(result.get("body", []))
        return tuple(identity)

    def label_occurrences(
        results: list[dict[str, object]],
    ) -> tuple[list[tuple[tuple[object, ...], int]], dict[tuple[tuple[object, ...], int], dict[str, object]]]:
        seen: dict[tuple[object, ...], int] = {}
        labels: list[tuple[tuple[object, ...], int]] = []
        labeled_results: dict[tuple[tuple[object, ...], int], dict[str, object]] = {}
        for result in results:
            identity = identity_of(result)
            occurrence = seen.get(identity, 0)
            seen[identity] = occurrence + 1
            label = (identity, occurrence)
            labels.append(label)
            labeled_results[label] = result
        return labels, labeled_results

    before_labels, before_labeled = label_occurrences(before_results)
    after_labels, after_labeled = label_occurrences(after_results)
    if sorted(before_labels, key=lambda x: (tuple(str(v) if v is not None else "" for v in x[0]), x[1])) != sorted(after_labels, key=lambda x: (tuple(str(v) if v is not None else "" for v in x[0]), x[1])):
        return False

    for label in before_labels:
        before_norm = before_labeled[label]
        after_norm = after_labeled[label]
        if (
            before_norm["wing"] != after_norm["wing"]
            or before_norm["room"] != after_norm["room"]
            or before_norm["source_file"] != after_norm["source_file"]
            or before_norm.get("text") != after_norm.get("text")
            or before_norm.get("body", []) != after_norm.get("body", [])
        ):
            return False
        if "similarity" in before_norm or "similarity" in after_norm:
            if "similarity" not in before_norm or "similarity" not in after_norm:
                return False
            if abs(before_norm["similarity"] - after_norm["similarity"]) > SEARCH_SIMILARITY_TOLERANCE:
                return False

    after_positions = {label: index for index, label in enumerate(after_labels)}
    for index, higher_label in enumerate(before_labels):
        higher_similarity = before_labeled[higher_label].get("similarity")
        if higher_similarity is None:
            continue
        for lower_label in before_labels[index + 1 :]:
            lower_similarity = before_labeled[lower_label].get("similarity")
            if lower_similarity is None:
                continue
            if higher_similarity - lower_similarity <= SEARCH_SIMILARITY_TOLERANCE:
                continue
            if after_positions[higher_label] > after_positions[lower_label]:
                return False
    return True


def _parse_search_cli(text: str) -> dict[str, object] | None:
    lines = text.splitlines()
    first_result_index = None
    for index, line in enumerate(lines):
        if CLI_RESULT_HEADER.match(line):
            first_result_index = index
            break

    if first_result_index is None:
        return {"header": lines, "results": []}

    header = lines[:first_result_index]
    results = []
    index = first_result_index
    while index < len(lines):
        if not lines[index]:
            index += 1
            continue

        header_match = CLI_RESULT_HEADER.match(lines[index])
        if header_match is None:
            return None
        if index + 2 >= len(lines):
            return None
        source_match = CLI_SOURCE_LINE.match(lines[index + 1])
        similarity_match = CLI_MATCH_LINE.match(lines[index + 2])
        if source_match is None or similarity_match is None:
            return None

        index += 3
        if index >= len(lines) or lines[index] != "":
            return None
        index += 1

        body = []
        while index < len(lines) and lines[index] != "":
            if not lines[index].startswith("      "):
                return None
            body.append(lines[index][6:])
            index += 1

        if not body:
            return None
        if index >= len(lines) or lines[index] != "":
            return None
        index += 1

        if index >= len(lines) or lines[index] != f"  {'─' * 56}":
            return None
        index += 1

        results.append(
            {
                "wing": header_match.group("wing"),
                "room": header_match.group("room"),
                "source_file": source_match.group("source"),
                "similarity": float(similarity_match.group("similarity")),
                "body": body,
            }
        )

    return {"header": header, "results": results}


def _compare_search_cli(before_root: Path, after_root: Path, rel_path: str) -> bool:
    before = _parse_search_cli(_read_text(before_root, rel_path))
    after = _parse_search_cli(_read_text(after_root, rel_path))
    if before is None or after is None:
        return False
    if before["header"] != after["header"]:
        return False
    before_results = [_normalize_cli_result(result) for result in before["results"]]
    after_results = [_normalize_cli_result(result) for result in after["results"]]
    return _compare_ranked_results(before_results, after_results)


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
        before_normalized = [_normalize_search_result(result) for result in before_results]
        after_normalized = [_normalize_search_result(result) for result in after_results]
        if not _compare_ranked_results(before_normalized, after_normalized):
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
    if not before_rooms and not after_rooms:
        return True
    if not before_rooms or not after_rooms:
        return False
    if set(before_rooms) != set(after_rooms):
        return False
    for room_name, bullets in before_rooms.items():
        if not room_name or not bullets:
            return False
        after_bullets = after_rooms.get(room_name)
        if not after_bullets:
            return False
        if bullets != after_bullets:
            return False
    return True


def _compare_tolerant(rel_path: str, before_root: Path, after_root: Path) -> bool:
    if rel_path.endswith("search-cli.txt"):
        return _compare_search_cli(before_root, after_root, rel_path)
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
