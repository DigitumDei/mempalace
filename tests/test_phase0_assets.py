import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts import check_phase0_drift


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
        for path in sorted(FIXTURE_ROOT.rglob("*"))
        if path.is_file()
        and path != FIXTURE_ROOT / "fixture-lock.json"
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
    assert inventory["python_implementation"]
    assert "dependency_inputs" in inventory
    assert "pyproject" in inventory["dependency_inputs"]
    assert "requirements_txt" in inventory["dependency_inputs"]
    assert "resolved_packages" in inventory


def test_phase0_drift_contract_sets_match_docs():
    assert "goldens/search-cli.txt" in check_phase0_drift.EXACT_FILES
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
        assert check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)

        widened = json.loads(json.dumps(baseline))
        widened["unfiltered"]["results"][0]["similarity"] = 0.30
        (after_root / rel_path).write_text(json.dumps(widened), encoding="utf-8")
        assert not check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)

        changed_text = json.loads(json.dumps(baseline))
        changed_text["unfiltered"]["results"][0]["text"] = "gamma"
        (after_root / rel_path).write_text(json.dumps(changed_text), encoding="utf-8")
        assert not check_phase0_drift._compare_programmatic_search(before_root, after_root, rel_path)


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
        assert check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)

        broken = "\n".join(baseline.splitlines()[:6]) + "\n"
        (after_root / rel_path).write_text(broken, encoding="utf-8")
        assert not check_phase0_drift._compare_wake_up(before_root, after_root, rel_path)


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
        return

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
        return

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
