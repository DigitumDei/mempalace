#!/usr/bin/env python3
"""Capture Phase 0 inventories and goldens from the Python reference implementation."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "phase0"
OUTPUT_FIXTURE_ROOT = Path(
    os.environ.get("MEMPALACE_PHASE0_OUTPUT_ROOT", str(SOURCE_FIXTURE_ROOT))
).resolve()
INPUT_ROOT = SOURCE_FIXTURE_ROOT / "inputs"
GOLDEN_ROOT = OUTPUT_FIXTURE_ROOT / "goldens"
INVENTORY_ROOT = OUTPUT_FIXTURE_ROOT / "inventory"
LOCK_PATH = OUTPUT_FIXTURE_ROOT / "fixture-lock.json"
SANITIZED_HOME = "/tmp/mempalace-phase0-home"
SANITIZED_PALACE_PATH = f"{SANITIZED_HOME}/.mempalace/palace"
TOLERANT_OUTPUTS = {
    "goldens/search-cli.txt",
    "goldens/search-programmatic.json",
    "goldens/wake-up-wing-code.txt",
    "goldens/wake-up.txt",
}


def _bootstrap_paths() -> None:
    vendor = REPO_ROOT / ".phase0_vendor"
    if vendor.exists():
        sys.path.insert(0, str(vendor))
    sys.path.insert(0, str(REPO_ROOT))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _python_series() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_help(args: list[str], env: dict[str, str]) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "mempalace", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"help command failed for {args!r} with exit {proc.returncode}: {proc.stderr.strip()}"
        )
    return proc.stdout


def _sanitize_payload(payload: object, tmp_home: Path, tmp_palace: Path) -> object:
    if isinstance(payload, dict):
        return {
            key: _sanitize_payload(value, tmp_home=tmp_home, tmp_palace=tmp_palace)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_sanitize_payload(value, tmp_home=tmp_home, tmp_palace=tmp_palace) for value in payload]
    if isinstance(payload, str):
        return (
            payload.replace(str(tmp_palace), SANITIZED_PALACE_PATH).replace(str(tmp_home), SANITIZED_HOME)
        )
    return payload


def _load_dependency_inputs() -> dict[str, object]:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    optional = project.get("optional-dependencies", {})

    requirements = [
        line.strip()
        for line in (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    return {
        "pyproject": {
            "requires_python": project.get("requires-python"),
            "dependencies": project.get("dependencies", []),
            "optional_dependencies": optional,
        },
        "requirements_txt": requirements,
    }


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


def _normalize_mcp_search_contract(payload: dict[str, object]) -> dict[str, object]:
    normalized_payload = json.loads(json.dumps(payload))
    content = normalized_payload.get("result", {}).get("content", [])
    if not content:
        return normalized_payload

    first = content[0]
    if not isinstance(first, dict) or first.get("type") != "text":
        return normalized_payload

    search_payload = json.loads(first["text"])
    normalized_search = {
        "query": search_payload["query"],
        "filters": search_payload["filters"],
        "results": _normalize_search_results(search_payload["results"]),
    }
    normalized_payload["result"]["content"][0]["text"] = json.dumps(
        normalized_search, indent=2, sort_keys=True
    )
    return normalized_payload


def main() -> int:
    _bootstrap_paths()

    tmp_home = Path(tempfile.mkdtemp(prefix="mempalace-phase0-home-"))
    tmp_palace = tmp_home / ".mempalace" / "palace"
    tmp_home_mempal = tmp_home / ".mempalace"
    old_home = os.environ.get("HOME")

    try:
        tmp_home_mempal.mkdir(parents=True, exist_ok=True)
        (tmp_home_mempal / "identity.txt").write_text(
            "## L0 - IDENTITY\nI am the MemPalace phase 0 reference capture.\n"
            "Traits: deterministic, local-first, test-oriented.\n"
            "Mission: freeze the Python surface before Rust implementation.\n",
            encoding="utf-8",
        )

        os.environ["HOME"] = str(tmp_home)
        os.environ["MEMPALACE_PALACE_PATH"] = str(tmp_palace)

        env = os.environ.copy()
        extra_pythonpath = []
        vendor = REPO_ROOT / ".phase0_vendor"
        if vendor.exists():
            extra_pythonpath.append(str(vendor))
        extra_pythonpath.append(str(REPO_ROOT))
        env["PYTHONPATH"] = os.pathsep.join(extra_pythonpath + [env.get("PYTHONPATH", "")]).strip(
            os.pathsep
        )

        from mempalace.convo_miner import mine_convos
        from mempalace.dialect import Dialect
        from mempalace.layers import MemoryStack
        from mempalace.mcp_server import TOOLS, handle_request, tool_status
        from mempalace.miner import get_collection, mine
        from mempalace.palace_graph import find_tunnels, graph_stats, traverse
        from mempalace.searcher import search, search_memories
        from mempalace.knowledge_graph import KnowledgeGraph

        GOLDEN_ROOT.mkdir(parents=True, exist_ok=True)
        INVENTORY_ROOT.mkdir(parents=True, exist_ok=True)

        mine(str(INPUT_ROOT / "project_alpha"), str(tmp_palace), wing_override=None, agent="phase0")
        mine_convos(
            str(INPUT_ROOT / "convos"),
            str(tmp_palace),
            wing="strategy_convos",
            agent="phase0",
            extract_mode="exchange",
        )

        col = get_collection(str(tmp_palace))
        col.add(
            ids=[
                "drawer_wing_team_auth_migration_001",
                "drawer_wing_code_auth_migration_001",
                "drawer_wing_user_release_readiness_001",
                "drawer_wing_team_phase0_rollout_001",
            ],
            documents=[
                "The team decided the auth-migration must preserve CLI and MCP parity.",
                "Code notes: auth-migration keeps search filter semantics exact while storage changes underneath.",
                "Release readiness depends on reproducible fixtures and drift checks before Phase 1 starts.",
                "Phase 0 rollout stays on the team wing so graph traversal captures connected_via semantics.",
            ],
            metadatas=[
                {
                    "wing": "wing_team",
                    "room": "auth-migration",
                    "hall": "hall_facts",
                    "date": "2026-04-01",
                    "source_file": "seed/team.txt",
                    "chunk_index": 0,
                    "added_by": "phase0",
                    "filed_at": "2026-04-01T10:00:00",
                    "importance": 5,
                },
                {
                    "wing": "wing_code",
                    "room": "auth-migration",
                    "hall": "hall_discoveries",
                    "date": "2026-04-02",
                    "source_file": "seed/code.txt",
                    "chunk_index": 0,
                    "added_by": "phase0",
                    "filed_at": "2026-04-02T11:00:00",
                    "importance": 4,
                },
                {
                    "wing": "wing_user",
                    "room": "release-readiness",
                    "hall": "hall_events",
                    "date": "2026-04-03",
                    "source_file": "seed/user.txt",
                    "chunk_index": 0,
                    "added_by": "phase0",
                    "filed_at": "2026-04-03T12:00:00",
                    "importance": 4,
                },
                {
                    "wing": "wing_team",
                    "room": "phase0-rollout",
                    "hall": "hall_events",
                    "date": "2026-04-04",
                    "source_file": "seed/rollout.txt",
                    "chunk_index": 0,
                    "added_by": "phase0",
                    "filed_at": "2026-04-04T09:00:00",
                    "importance": 3,
                },
            ],
        )

        kg = KnowledgeGraph()
        kg.add_triple(
            "MemPalace", "depends_on", "Fixture Corpus", valid_from="2026-04-01", source_file="phase0"
        )
        kg.add_triple(
            "Rust Rewrite", "preserves", "CLI Parity", valid_from="2026-04-02", source_file="phase0"
        )
        kg.add_triple(
            "Rust Rewrite",
            "preserves",
            "MCP Tool Names",
            valid_from="2026-04-02",
            source_file="phase0",
        )
        kg.add_triple(
            "Rust Rewrite", "targets", "Phase 1", valid_from="2026-04-03", source_file="phase0"
        )
        kg.invalidate("Rust Rewrite", "targets", "Phase 1", ended="2026-04-04")

        cli_inventory = {
            "commands": {
                "root": _run_help(["--help"], env),
                "init": _run_help(["init", "--help"], env),
                "mine": _run_help(["mine", "--help"], env),
                "split": _run_help(["split", "--help"], env),
                "search": _run_help(["search", "--help"], env),
                "compress": _run_help(["compress", "--help"], env),
                "wake-up": _run_help(["wake-up", "--help"], env),
                "status": _run_help(["status", "--help"], env),
            }
        }
        _write_json(INVENTORY_ROOT / "cli-help.json", cli_inventory)

        mcp_inventory = {
            name: {
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            for name, tool in sorted(TOOLS.items())
        }
        _write_json(INVENTORY_ROOT / "mcp-tools.json", mcp_inventory)

        packages = {}
        for pkg in ["chromadb", "PyYAML", "pytest"]:
            try:
                packages[pkg] = importlib.metadata.version(pkg)
            except importlib.metadata.PackageNotFoundError:
                continue

        env_inventory = {
            "python_version": _python_series(),
            "python_implementation": platform.python_implementation(),
            "dependency_inputs": _load_dependency_inputs(),
            "resolved_packages": packages,
        }
        _write_json(INVENTORY_ROOT / "environment.json", env_inventory)

        programmatic_search = {
            "unfiltered": search_memories("auth migration parity", str(tmp_palace), n_results=3),
            "wing_filtered": search_memories(
                "auth migration parity", str(tmp_palace), wing="wing_team", n_results=3
            ),
            "room_filtered": search_memories(
                "auth migration parity", str(tmp_palace), room="auth-migration", n_results=3
            ),
            "wing_and_room_filtered": search_memories(
                "auth migration parity",
                str(tmp_palace),
                wing="wing_team",
                room="auth-migration",
                n_results=3,
            ),
        }
        _write_json(GOLDEN_ROOT / "search-programmatic.json", programmatic_search)

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            search("auth migration parity", str(tmp_palace), n_results=3)
        _write_text(GOLDEN_ROOT / "search-cli.txt", stdout.getvalue())

        stack = MemoryStack(str(tmp_palace), str(tmp_home_mempal / "identity.txt"))
        _write_text(GOLDEN_ROOT / "wake-up.txt", stack.wake_up())
        _write_text(GOLDEN_ROOT / "wake-up-wing-code.txt", stack.wake_up(wing="wing_code"))

        dialect = Dialect()
        aaak_source = (
            "We decided to preserve CLI parity and MCP tool names because fixture drift would "
            "make the Rust rewrite impossible to evaluate."
        )
        aaak_rendered = dialect.compress(aaak_source, metadata={"wing": "wing_code", "room": "planning"})
        _write_json(
            GOLDEN_ROOT / "aaak.json",
            {
                "source": aaak_source,
                "rendered": aaak_rendered,
                "stats": dialect.compression_stats(aaak_source, aaak_rendered),
            },
        )

        _write_json(
            GOLDEN_ROOT / "palace-graph.json",
            {
                "traverse": traverse("auth-migration", col=col, max_hops=2),
                "tunnels": find_tunnels(col=col),
                "stats": graph_stats(col=col),
            },
        )

        _write_json(
            GOLDEN_ROOT / "knowledge-graph.json",
            {
                "query": kg.query_entity("Rust Rewrite", direction="both"),
                "invalidate": {
                    "subject": "Rust Rewrite",
                    "predicate": "targets",
                    "object": "Phase 1",
                    "ended": "2026-04-04",
                    "post_query": kg.query_entity("Rust Rewrite", direction="both"),
                },
                "timeline": kg.timeline("Rust Rewrite"),
                "stats": kg.stats(),
            },
        )

        mcp_contract = {
            "initialize": handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
            "tools_list": handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            "status": handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "mempalace_status", "arguments": {}},
                }
            ),
            "search": handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "mempalace_search",
                        "arguments": {"query": "auth migration parity", "limit": 2},
                    },
                }
            ),
            "error": handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "mempalace_nope", "arguments": {}},
                }
            ),
            "status_payload": tool_status(),
        }
        mcp_contract["search"] = _normalize_mcp_search_contract(mcp_contract["search"])
        _write_json(
            GOLDEN_ROOT / "mcp-contract.json",
            _sanitize_payload(mcp_contract, tmp_home=tmp_home, tmp_palace=tmp_palace),
        )

        input_hashes = {
            str(path.relative_to(SOURCE_FIXTURE_ROOT)): _sha256(path)
            for path in sorted(INPUT_ROOT.rglob("*"))
            if path.is_file()
        }
        generated_hashes = {
            str(path.relative_to(OUTPUT_FIXTURE_ROOT)): _sha256(path)
            for root in (GOLDEN_ROOT, INVENTORY_ROOT)
            for path in sorted(root.rglob("*"))
            if path.is_file()
            and path != LOCK_PATH
            and str(path.relative_to(OUTPUT_FIXTURE_ROOT)) not in TOLERANT_OUTPUTS
        }
        _write_json(
            LOCK_PATH,
            {
                "phase": "0",
                "version": 1,
                "generated_by": "scripts/phase0_capture.py",
                "python": _python_series(),
                "input_hashes": input_hashes,
                "generated_hashes": generated_hashes,
                "tolerant_generated_files": sorted(TOLERANT_OUTPUTS),
            },
        )
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
        os.environ.pop("MEMPALACE_PALACE_PATH", None)
        shutil.rmtree(tmp_home, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
