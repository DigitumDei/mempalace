import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


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


def test_phase0_environment_inventory_is_stable_shape():
    inventory = json.loads((INVENTORY_ROOT / "environment.json").read_text(encoding="utf-8"))
    assert inventory["python_version"]
    assert inventory["python_implementation"]
    assert "dependency_inputs" in inventory
    assert "pyproject" in inventory["dependency_inputs"]
    assert "requirements_txt" in inventory["dependency_inputs"]
    assert "resolved_packages" in inventory


def test_phase0_drift_script_is_stable_when_vendor_env_exists():
    vendor = ROOT / ".phase0_vendor"
    if not vendor.exists():
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(vendor), str(ROOT), env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)
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
