import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import pytest

from scripts import check_phase0_drift
from scripts import phase0_capture


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "phase0"
GOLDEN_ROOT = FIXTURE_ROOT / "goldens"
INVENTORY_ROOT = FIXTURE_ROOT / "inventory"

EXPECTED_GOLDENS = {
    "aaak.json",
    "knowledge-graph.json",
    "mcp-contract.json",
    "palace-graph.json",
    "search-cli.txt",
    "search-programmatic.json",
    "wake-up-wing-code.txt",
    "wake-up.txt",
}
EXPECTED_INVENTORIES = {
    "cli-help.json",
    "environment.json",
    "mcp-tools.json",
}
EXPECTED_INPUTS = {
    "inputs/convos/product_strategy.txt",
    "inputs/project_alpha/backend/auth.py",
    "inputs/project_alpha/docs/plan.md",
    "inputs/project_alpha/mempalace.yaml",
}
EXPECTED_TOLERANT_FILES = {
    "goldens/search-cli.txt",
    "goldens/search-programmatic.json",
    "goldens/wake-up-wing-code.txt",
    "goldens/wake-up.txt",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase0_docs_exist():
    assert (ROOT / "docs" / "rust-phase0" / "parity-matrix.md").exists()
    assert (ROOT / "docs" / "rust-phase0" / "mcp-crate-evaluation.md").exists()
    assert (ROOT / "docs" / "rust-phase0" / "acceptance-criteria.md").exists()
    assert (ROOT / "docs" / "rust-phase0" / "reference-environment.md").exists()


def test_phase0_expected_assets_exist():
    assert {path.name for path in GOLDEN_ROOT.iterdir() if path.is_file()} == EXPECTED_GOLDENS
    assert {path.name for path in INVENTORY_ROOT.iterdir() if path.is_file()} == EXPECTED_INVENTORIES
    for rel in EXPECTED_INPUTS:
        assert (FIXTURE_ROOT / rel).exists()


def test_phase0_fixture_lock_matches_files():
    lock = json.loads((FIXTURE_ROOT / "fixture-lock.json").read_text(encoding="utf-8"))
    assert lock["phase"] == "0"
    assert lock["version"] == 1
    assert lock["generated_by"] == "scripts/phase0_capture.py"
    assert set(lock["tolerant_generated_files"]) == EXPECTED_TOLERANT_FILES

    actual_input_hashes = {
        str(path.relative_to(FIXTURE_ROOT)): _sha256(path)
        for path in sorted((FIXTURE_ROOT / "inputs").rglob("*"))
        if path.is_file()
    }
    assert lock["input_hashes"] == actual_input_hashes

    actual_generated_hashes = {
        str(path.relative_to(FIXTURE_ROOT)): _sha256(path)
        for root in (GOLDEN_ROOT, INVENTORY_ROOT)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and str(path.relative_to(FIXTURE_ROOT)) not in EXPECTED_TOLERANT_FILES
    }
    assert lock["generated_hashes"] == actual_generated_hashes


def test_phase0_json_goldens_have_expected_structure():
    search = json.loads((GOLDEN_ROOT / "search-programmatic.json").read_text(encoding="utf-8"))
    assert set(search) == {"room_filtered", "unfiltered", "wing_and_room_filtered", "wing_filtered"}
    assert search["wing_and_room_filtered"]["filters"] == {"room": "auth-migration", "wing": "wing_team"}
    assert len(search["wing_and_room_filtered"]["results"]) == 1
    assert search["wing_and_room_filtered"]["results"][0]["wing"] == "wing_team"
    assert search["wing_and_room_filtered"]["results"][0]["room"] == "auth-migration"

    palace_graph = json.loads((GOLDEN_ROOT / "palace-graph.json").read_text(encoding="utf-8"))
    assert any("connected_via" in node for node in palace_graph["traverse"] if node["hop"] > 0)

    knowledge_graph = json.loads((GOLDEN_ROOT / "knowledge-graph.json").read_text(encoding="utf-8"))
    assert knowledge_graph["invalidate"]["ended"] == "2026-04-04"
    assert any(
        item["predicate"] == "targets" and item["valid_to"] == "2026-04-04"
        for item in knowledge_graph["invalidate"]["post_query"]
    )

    mcp_contract = json.loads((GOLDEN_ROOT / "mcp-contract.json").read_text(encoding="utf-8"))
    assert mcp_contract["status_payload"]["palace_path"] == "/tmp/mempalace-phase0-home/.mempalace/palace"
    mcp_search_payload = json.loads(mcp_contract["search"]["result"]["content"][0]["text"])
    assert set(mcp_search_payload) == {"filters", "query", "results"}
    assert all("similarity" not in item for item in mcp_search_payload["results"])

    cli_inventory = json.loads((INVENTORY_ROOT / "cli-help.json").read_text(encoding="utf-8"))
    assert set(cli_inventory["commands"]) == {
        "compress",
        "init",
        "mine",
        "root",
        "search",
        "split",
        "status",
        "wake-up",
    }

    mcp_inventory = json.loads((INVENTORY_ROOT / "mcp-tools.json").read_text(encoding="utf-8"))
    assert {
        "mempalace_get_aaak_spec",
        "mempalace_search",
        "mempalace_status",
    }.issubset(mcp_inventory)


def test_phase0_environment_inventory_is_stable_shape():
    inventory = json.loads((INVENTORY_ROOT / "environment.json").read_text(encoding="utf-8"))
    assert inventory["python_version"]
    assert inventory["python_version"].count(".") == 1
    assert inventory["python_implementation"]
    assert "dependency_inputs" in inventory
    assert "pyproject" in inventory["dependency_inputs"]
    assert "requirements_txt" in inventory["dependency_inputs"]
    assert "resolved_packages" in inventory
    assert {"chromadb", "pytest", "pyyaml"}.issubset(
        {name.lower() for name in inventory["resolved_packages"]}
    )


def test_phase0_drift_contract_sets_match_docs():
    assert "goldens/search-cli.txt" in check_phase0_drift.TOLERANT_FILES
    assert "goldens/search-programmatic.json" in check_phase0_drift.TOLERANT_FILES
    assert "goldens/wake-up.txt" in check_phase0_drift.TOLERANT_FILES
    assert "goldens/wake-up-wing-code.txt" in check_phase0_drift.TOLERANT_FILES


def test_phase0_programmatic_search_tolerance_keeps_order_and_similarity_gate():
    with tempfile.TemporaryDirectory() as before_str, tempfile.TemporaryDirectory() as after_str:
        before_root = Path(before_str)
        after_root = Path(after_str)
        rel_path = "goldens/search-programmatic.json"
        for root in (before_root, after_root):
            (root / "goldens").mkdir(parents=True, exist_ok=True)

        baseline = {
            "unfiltered": {
                "query": "auth migration parity",
                "filters": {"wing": None, "room": None},
                "results": [
                    {
                        "wing": "wing_team",
                        "room": "auth-migration",
                        "source_file": "team.txt",
                        "text": "alpha",
                        "similarity": 0.49,
                    },
                    {
                        "wing": "wing_code",
                        "room": "auth-migration",
                        "source_file": "code.txt",
                        "text": "beta",
                        "similarity": 0.07,
                    },
                ],
            }
        }
        (before_root / rel_path).write_text(json.dumps(baseline), encoding="utf-8")

        tolerated = json.loads(json.dumps(baseline))
        tolerated["unfiltered"]["results"][0]["similarity"] = 0.46
        (after_root / rel_path).write_text(json.dumps(tolerated), encoding="utf-8")
        assert check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)

        reordered = json.loads(json.dumps(baseline))
        reordered["unfiltered"]["results"] = list(reversed(reordered["unfiltered"]["results"]))
        (after_root / rel_path).write_text(json.dumps(reordered), encoding="utf-8")
        assert not check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)

        tied = json.loads(json.dumps(baseline))
        tied["unfiltered"]["results"][0]["similarity"] = 0.10
        tied["unfiltered"]["results"][1]["similarity"] = 0.08
        (before_root / rel_path).write_text(json.dumps(tied), encoding="utf-8")
        reordered_tied = json.loads(json.dumps(tied))
        reordered_tied["unfiltered"]["results"] = list(reversed(reordered_tied["unfiltered"]["results"]))
        (after_root / rel_path).write_text(json.dumps(reordered_tied), encoding="utf-8")
        assert check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)

        (before_root / rel_path).write_text(json.dumps(baseline), encoding="utf-8")

        widened = json.loads(json.dumps(baseline))
        widened["unfiltered"]["results"][0]["similarity"] = 0.30
        (after_root / rel_path).write_text(json.dumps(widened), encoding="utf-8")
        assert not check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)

        changed_text = json.loads(json.dumps(baseline))
        changed_text["unfiltered"]["results"][0]["text"] = "gamma"
        (after_root / rel_path).write_text(json.dumps(changed_text), encoding="utf-8")
        assert not check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)

        duplicate_baseline = {
            "unfiltered": {
                "query": "auth migration parity",
                "filters": {"wing": None, "room": None},
                "results": [
                    {
                        "wing": "wing_team",
                        "room": "auth-migration",
                        "source_file": "team.txt",
                        "text": "alpha",
                        "similarity": 0.90,
                    },
                    {
                        "wing": "wing_team",
                        "room": "auth-migration",
                        "source_file": "team.txt",
                        "text": "alpha",
                        "similarity": 0.80,
                    },
                ],
            }
        }
        duplicate_drift = json.loads(json.dumps(duplicate_baseline))
        duplicate_drift["unfiltered"]["results"][0]["similarity"] = 0.80
        (before_root / rel_path).write_text(json.dumps(duplicate_baseline), encoding="utf-8")
        (after_root / rel_path).write_text(json.dumps(duplicate_drift), encoding="utf-8")
        assert not check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)


def test_phase0_search_cli_tolerance_preserves_structure_and_ranking():
    with tempfile.TemporaryDirectory() as before_str, tempfile.TemporaryDirectory() as after_str:
        before_root = Path(before_str)
        after_root = Path(after_str)
        rel_path = "goldens/search-cli.txt"
        for root in (before_root, after_root):
            (root / "goldens").mkdir(parents=True, exist_ok=True)

        baseline = "\n".join(
            [
                "",
                "=" * 60,
                '  Results for: "auth migration parity"',
                "=" * 60,
                "",
                "  [1] wing_team / auth-migration",
                "      Source: team.txt",
                "      Match:  0.49",
                "",
                "      alpha",
                "",
                f"  {'─' * 56}",
                "  [2] wing_code / auth-migration",
                "      Source: code.txt",
                "      Match:  0.07",
                "",
                "      beta",
                "",
                f"  {'─' * 56}",
                "",
            ]
        )
        (before_root / rel_path).write_text(baseline, encoding="utf-8")

        tolerated = baseline.replace("0.49", "0.46", 1)
        (after_root / rel_path).write_text(tolerated, encoding="utf-8")
        assert check_phase0_drift._compare_search_cli(before_root, after_root, rel_path)

        reordered = baseline.replace(
            "\n".join(
                [
                    "  [1] wing_team / auth-migration",
                    "      Source: team.txt",
                    "      Match:  0.49",
                    "",
                    "      alpha",
                    "",
                    f"  {'─' * 56}",
                    "  [2] wing_code / auth-migration",
                    "      Source: code.txt",
                    "      Match:  0.07",
                    "",
                    "      beta",
                    "",
                    f"  {'─' * 56}",
                ]
            ),
            "\n".join(
                [
                    "  [1] wing_code / auth-migration",
                    "      Source: code.txt",
                    "      Match:  0.07",
                    "",
                    "      beta",
                    "",
                    f"  {'─' * 56}",
                    "  [2] wing_team / auth-migration",
                    "      Source: team.txt",
                    "      Match:  0.49",
                    "",
                    "      alpha",
                    "",
                    f"  {'─' * 56}",
                ]
            ),
            1,
        )
        (after_root / rel_path).write_text(reordered, encoding="utf-8")
        assert not check_phase0_drift._compare_search_cli(before_root, after_root, rel_path)

        tied = baseline.replace("0.49", "0.10", 1).replace("0.07", "0.08", 1)
        (before_root / rel_path).write_text(tied, encoding="utf-8")
        reordered_tied = tied.replace(
            "\n".join(
                [
                    "  [1] wing_team / auth-migration",
                    "      Source: team.txt",
                    "      Match:  0.10",
                    "",
                    "      alpha",
                    "",
                    f"  {'─' * 56}",
                    "  [2] wing_code / auth-migration",
                    "      Source: code.txt",
                    "      Match:  0.08",
                    "",
                    "      beta",
                    "",
                    f"  {'─' * 56}",
                ]
            ),
            "\n".join(
                [
                    "  [1] wing_code / auth-migration",
                    "      Source: code.txt",
                    "      Match:  0.08",
                    "",
                    "      beta",
                    "",
                    f"  {'─' * 56}",
                    "  [2] wing_team / auth-migration",
                    "      Source: team.txt",
                    "      Match:  0.10",
                    "",
                    "      alpha",
                    "",
                    f"  {'─' * 56}",
                ]
            ),
            1,
        )
        (after_root / rel_path).write_text(reordered_tied, encoding="utf-8")
        assert check_phase0_drift._compare_search_cli(before_root, after_root, rel_path)


def test_phase0_wake_up_tolerance_requires_structure():
    with tempfile.TemporaryDirectory() as before_str, tempfile.TemporaryDirectory() as after_str:
        before_root = Path(before_str)
        after_root = Path(after_str)
        rel_path = "goldens/wake-up.txt"
        for root in (before_root, after_root):
            (root / "goldens").mkdir(parents=True, exist_ok=True)

        baseline = (GOLDEN_ROOT / "wake-up.txt").read_text(encoding="utf-8")
        (before_root / rel_path).write_text(baseline, encoding="utf-8")
        variant = baseline.replace("[auth-migration]", "[unexpected-room]", 1)
        (after_root / rel_path).write_text(variant, encoding="utf-8")
        assert not check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)

        subset_lines = baseline.splitlines()
        subset = "\n".join(subset_lines[:10]) + "\n"
        (after_root / rel_path).write_text(subset, encoding="utf-8")
        assert not check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)

        missing_bullet = baseline.replace(
            "  - Code notes: auth-migration keeps search filter semantics exact while storage changes underneath.  (code.txt)\n",
            "",
            1,
        )
        (after_root / rel_path).write_text(missing_bullet, encoding="utf-8")
        assert not check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)

        broken = "\n".join(baseline.splitlines()[:6]) + "\n"
        (after_root / rel_path).write_text(broken, encoding="utf-8")
        assert not check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)

        ordered = "\n".join(
            [
                "## L0 - IDENTITY",
                "I am the MemPalace phase 0 reference capture.",
                "",
                "## L1 - WAKE UP",
                "Top drawers:",
                "",
                "[auth-migration]",
                "  - alpha",
                "  - beta",
                "",
            ]
        )
        reordered = ordered.replace("  - alpha\n  - beta", "  - beta\n  - alpha", 1)
        (before_root / rel_path).write_text(ordered + "\n", encoding="utf-8")
        (after_root / rel_path).write_text(reordered + "\n", encoding="utf-8")
        assert not check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)


def test_phase0_wake_up_tolerance_allows_matching_short_outputs():
    with tempfile.TemporaryDirectory() as before_str, tempfile.TemporaryDirectory() as after_str:
        before_root = Path(before_str)
        after_root = Path(after_str)
        rel_path = "goldens/wake-up.txt"
        for root in (before_root, after_root):
            (root / "goldens").mkdir(parents=True, exist_ok=True)

        short = "L0\nL0b\nL0c\nL0d\nL0e\n"
        (before_root / rel_path).write_text(short, encoding="utf-8")
        (after_root / rel_path).write_text(short, encoding="utf-8")
        assert check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)


def test_phase0_drift_script_ignores_inputs_and_leaves_workspace_unchanged(tmp_path, monkeypatch):
    temp_fixture_root = tmp_path / "phase0"
    shutil.copytree(FIXTURE_ROOT, temp_fixture_root)
    baseline = {
        str(path.relative_to(temp_fixture_root)): path.read_bytes()
        for path in sorted(temp_fixture_root.rglob("*"))
        if path.is_file()
    }
    monkeypatch.setattr(check_phase0_drift, "FIXTURE_ROOT", temp_fixture_root)

    def fake_run(args, cwd, env, check):
        output_root = Path(env["MEMPALACE_PHASE0_OUTPUT_ROOT"])
        shutil.copytree(temp_fixture_root / "goldens", output_root / "goldens")
        shutil.copytree(temp_fixture_root / "inventory", output_root / "inventory")
        shutil.copy2(temp_fixture_root / "fixture-lock.json", output_root / "fixture-lock.json")
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(check_phase0_drift.subprocess, "run", fake_run)
    assert check_phase0_drift.main() == 0

    after = {
        str(path.relative_to(temp_fixture_root)): path.read_bytes()
        for path in sorted(temp_fixture_root.rglob("*"))
        if path.is_file()
    }
    assert after == baseline


def _install_phase0_capture_stubs(monkeypatch):
    def register(name: str, module: types.ModuleType) -> None:
        monkeypatch.setitem(sys.modules, name, module)

    convo_miner = types.ModuleType("mempalace.convo_miner")
    convo_miner.mine_convos = lambda *args, **kwargs: None
    register("mempalace.convo_miner", convo_miner)

    dialect = types.ModuleType("mempalace.dialect")

    class FakeDialect:
        def compress(self, source, metadata=None):
            return f"AAAK::{metadata['wing']}::{metadata['room']}::{source}"

        def compression_stats(self, source, rendered):
            return {"source_len": len(source), "rendered_len": len(rendered)}

    dialect.Dialect = FakeDialect
    register("mempalace.dialect", dialect)

    layers = types.ModuleType("mempalace.layers")

    class FakeMemoryStack:
        def __init__(self, palace_path, identity_path):
            self.palace_path = palace_path
            self.identity_path = identity_path

        def wake_up(self, wing=None):
            room_name = "auth-migration" if wing != "wing_code" else "code-focus"
            source = "team.txt" if wing != "wing_code" else "code.txt"
            return "\n".join(
                [
                    "## L0 - IDENTITY",
                    "I am the MemPalace phase 0 reference capture.",
                    "",
                    "## L1 - WAKE UP",
                    "Top drawers:",
                    "",
                    f"[{room_name}]",
                    f"  - Code notes: auth-migration keeps search filter semantics exact while storage changes underneath.  ({source})",
                    "",
                ]
            )

    layers.MemoryStack = FakeMemoryStack
    register("mempalace.layers", layers)

    mcp_server = types.ModuleType("mempalace.mcp_server")
    mcp_server.TOOLS = {
        "mempalace_get_aaak_spec": {
            "description": "Return the AAAK spec",
            "input_schema": {"type": "object", "properties": {}},
        },
        "mempalace_search": {
            "description": "Search memories",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
        "mempalace_status": {
            "description": "Return status",
            "input_schema": {"type": "object", "properties": {}},
        },
    }

    def handle_request(payload):
        method = payload["method"]
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"serverInfo": {"name": "phase0"}}}
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"tools": [{"name": name} for name in sorted(mcp_server.TOOLS)]},
            }
        if method == "tools/call":
            name = payload["params"]["name"]
            if name == "mempalace_status":
                return {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"content": [{"type": "text", "text": json.dumps({"ok": True})}]},
                }
            if name == "mempalace_search":
                return {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "query": "auth migration parity",
                                        "filters": {"wing": None, "room": None},
                                        "results": [
                                            {
                                                "wing": "wing_team",
                                                "room": "auth-migration",
                                                "source_file": "team.txt",
                                                "text": "alpha",
                                                "similarity": 0.49,
                                            },
                                            {
                                                "wing": "wing_code",
                                                "room": "auth-migration",
                                                "source_file": "code.txt",
                                                "text": "beta",
                                                "similarity": 0.07,
                                            },
                                        ],
                                    }
                                ),
                            }
                        ]
                    },
                }
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "error": {"code": -32601, "message": "unknown tool"},
            }
        raise AssertionError(method)

    def tool_status():
        return {"palace_path": os.environ["MEMPALACE_PALACE_PATH"]}

    mcp_server.handle_request = handle_request
    mcp_server.tool_status = tool_status
    register("mempalace.mcp_server", mcp_server)

    miner = types.ModuleType("mempalace.miner")

    class FakeCollection:
        def add(self, **kwargs):
            self.last_add = kwargs

    miner.mine = lambda *args, **kwargs: None
    miner.get_collection = lambda path: FakeCollection()
    register("mempalace.miner", miner)

    palace_graph = types.ModuleType("mempalace.palace_graph")
    palace_graph.traverse = lambda *args, **kwargs: [
        {"room": "auth-migration", "hop": 0, "wings": ["wing_team"], "halls": ["hall_facts"], "count": 2},
        {
            "room": "phase0-rollout",
            "hop": 1,
            "wings": ["wing_team"],
            "halls": ["hall_events"],
            "count": 1,
            "connected_via": "wing_team",
            "recent": "2026-04-04",
        },
    ]
    palace_graph.find_tunnels = lambda *args, **kwargs: [{"source": "auth-migration", "target": "phase0-rollout"}]
    palace_graph.graph_stats = lambda *args, **kwargs: {"rooms": 2, "tunnels": 1}
    register("mempalace.palace_graph", palace_graph)

    searcher = types.ModuleType("mempalace.searcher")

    def search(query, palace_path, wing=None, room=None, n_results=5):
        print()
        print("=" * 60)
        print(f'  Results for: "{query}"')
        if wing:
            print(f"  Wing: {wing}")
        if room:
            print(f"  Room: {room}")
        print("=" * 60)
        print()
        results = [
            ("wing_team", "auth-migration", "team.txt", 0.49, "alpha"),
            ("wing_code", "auth-migration", "code.txt", 0.07, "beta"),
        ]
        for index, (wing_name, room_name, source, similarity, body) in enumerate(results, 1):
            print(f"  [{index}] {wing_name} / {room_name}")
            print(f"      Source: {source}")
            print(f"      Match:  {similarity}")
            print()
            print(f"      {body}")
            print()
            print(f"  {'─' * 56}")
        print()

    def search_memories(query, palace_path, wing=None, room=None, n_results=5):
        results = [
            {
                "wing": "wing_team",
                "room": "auth-migration",
                "source_file": "team.txt",
                "text": "alpha",
                "similarity": 0.49,
            },
            {
                "wing": "wing_code",
                "room": "auth-migration",
                "source_file": "code.txt",
                "text": "beta",
                "similarity": 0.07,
            },
        ]
        filtered = [
            result
            for result in results
            if (wing is None or result["wing"] == wing) and (room is None or result["room"] == room)
        ]
        return {"query": query, "filters": {"wing": wing, "room": room}, "results": filtered[:n_results]}

    searcher.search = search
    searcher.search_memories = search_memories
    register("mempalace.searcher", searcher)

    knowledge_graph = types.ModuleType("mempalace.knowledge_graph")

    class FakeKnowledgeGraph:
        def __init__(self):
            self.rows = []

        def add_triple(self, subject, predicate, obj, valid_from=None, source_file=None):
            self.rows.append(
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "valid_from": valid_from,
                    "valid_to": None,
                    "source_file": source_file,
                }
            )

        def invalidate(self, subject, predicate, obj, ended=None):
            for row in self.rows:
                if row["subject"] == subject and row["predicate"] == predicate and row["object"] == obj:
                    row["valid_to"] = ended

        def query_entity(self, entity, direction="both"):
            return [row for row in self.rows if row["subject"] == entity or row["object"] == entity]

        def timeline(self, entity):
            return sorted(self.query_entity(entity), key=lambda row: row["valid_from"] or "")

        def stats(self):
            return {"triples": len(self.rows)}

    knowledge_graph.KnowledgeGraph = FakeKnowledgeGraph
    register("mempalace.knowledge_graph", knowledge_graph)


def test_phase0_capture_collects_declared_dependency_versions(monkeypatch):
    monkeypatch.setattr(
        phase0_capture.importlib.metadata,
        "version",
        lambda name: {
            "build": "1.0.0",
            "chromadb": "1.2.3",
            "pytest": "9.9.9",
            "pyyaml": "6.0.0",
            "twine": "4.0.0",
        }[name],
    )

    dependency_inputs = {
        "pyproject": {
            "dependencies": ["chromadb>=0.4.0", "pyyaml>=6.0"],
            "optional_dependencies": {"dev": ["pytest>=7.0", "build>=1.0", "twine>=4.0"]},
        },
        "requirements_txt": ["chromadb>=0.4.0", "pyyaml>=6.0"],
    }

    assert phase0_capture._resolved_declared_packages(dependency_inputs) == {
        "build": "1.0.0",
        "chromadb": "1.2.3",
        "pytest": "9.9.9",
        "pyyaml": "6.0.0",
        "twine": "4.0.0",
    }


def test_phase0_capture_round_trip_with_stubbed_reference(tmp_path, monkeypatch):
    _install_phase0_capture_stubs(monkeypatch)
    source_fixture_root = tmp_path / "source"
    shutil.copytree(FIXTURE_ROOT / "inputs", source_fixture_root / "inputs")

    output_a = tmp_path / "out-a"
    output_b = tmp_path / "out-b"

    monkeypatch.setattr(phase0_capture, "_run_help", lambda args, env: f"help:{' '.join(args)}\n")
    monkeypatch.setattr(phase0_capture, "SOURCE_FIXTURE_ROOT", source_fixture_root)
    monkeypatch.setattr(phase0_capture, "INPUT_ROOT", source_fixture_root / "inputs")

    def configure_output(output_root: Path) -> None:
        monkeypatch.setattr(phase0_capture, "OUTPUT_FIXTURE_ROOT", output_root)
        monkeypatch.setattr(phase0_capture, "GOLDEN_ROOT", output_root / "goldens")
        monkeypatch.setattr(phase0_capture, "INVENTORY_ROOT", output_root / "inventory")
        monkeypatch.setattr(phase0_capture, "LOCK_PATH", output_root / "fixture-lock.json")

    configure_output(output_a)
    assert phase0_capture.main() == 0
    configure_output(output_b)
    assert phase0_capture.main() == 0

    tree_a = {
        str(path.relative_to(output_a)): path.read_bytes()
        for path in sorted(output_a.rglob("*"))
        if path.is_file()
    }
    tree_b = {
        str(path.relative_to(output_b)): path.read_bytes()
        for path in sorted(output_b.rglob("*"))
        if path.is_file()
    }
    assert tree_a == tree_b

    lock = json.loads((output_a / "fixture-lock.json").read_text(encoding="utf-8"))
    assert lock["python"].count(".") == 1
    assert "goldens/search-cli.txt" in lock["tolerant_generated_files"]
    assert set(lock["generated_hashes"]) == {
        "goldens/aaak.json",
        "goldens/knowledge-graph.json",
        "goldens/mcp-contract.json",
        "goldens/palace-graph.json",
        "inventory/cli-help.json",
        "inventory/environment.json",
        "inventory/mcp-tools.json",
    }

    env_inventory = json.loads((output_a / "inventory" / "environment.json").read_text(encoding="utf-8"))
    assert env_inventory["python_version"].count(".") == 1


def test_phase0_drift_script_reports_exact_drift_without_rewriting_workspace(tmp_path, monkeypatch):
    temp_fixture_root = tmp_path / "phase0"
    shutil.copytree(FIXTURE_ROOT, temp_fixture_root)
    baseline = {
        str(path.relative_to(temp_fixture_root)): path.read_bytes()
        for path in sorted(temp_fixture_root.rglob("*"))
        if path.is_file()
    }
    monkeypatch.setattr(check_phase0_drift, "FIXTURE_ROOT", temp_fixture_root)

    def fake_run(args, cwd, env, check):
        output_root = Path(env["MEMPALACE_PHASE0_OUTPUT_ROOT"])
        shutil.copytree(temp_fixture_root / "goldens", output_root / "goldens")
        shutil.copytree(temp_fixture_root / "inventory", output_root / "inventory")
        shutil.copy2(temp_fixture_root / "fixture-lock.json", output_root / "fixture-lock.json")
        search_cli = output_root / "goldens" / "search-cli.txt"
        search_cli.write_text(search_cli.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(check_phase0_drift.subprocess, "run", fake_run)
    assert check_phase0_drift.main() == 1

    after = {
        str(path.relative_to(temp_fixture_root)): path.read_bytes()
        for path in sorted(temp_fixture_root.rglob("*"))
        if path.is_file()
    }
    assert after == baseline


def test_phase0_drift_script_is_stable_when_vendor_env_exists():
    vendor = ROOT / ".phase0_vendor"
    if not vendor.exists():
        pytest.skip(".phase0_vendor is not present")

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(vendor)!r}); "
                "import chromadb"
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        pytest.skip(f".phase0_vendor does not provide importable chromadb: {probe.stderr}")

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(vendor), str(ROOT), env.get("PYTHONPATH", "")]).strip(
        os.pathsep
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_phase0_drift.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Phase 0 fixtures are stable." in proc.stdout
