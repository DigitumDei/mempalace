import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "phase0"


def test_phase0_docs_exist():
    assert (ROOT / "docs" / "rust-phase0" / "parity-matrix.md").exists()
    assert (ROOT / "docs" / "rust-phase0" / "mcp-crate-evaluation.md").exists()
    assert (ROOT / "docs" / "rust-phase0" / "acceptance-criteria.md").exists()
    assert (ROOT / "docs" / "rust-phase0" / "reference-environment.md").exists()


def test_phase0_fixture_inputs_exist():
    assert (FIXTURE_ROOT / "inputs" / "project_alpha" / "mempalace.yaml").exists()
    assert (FIXTURE_ROOT / "inputs" / "convos" / "product_strategy.txt").exists()


def test_phase0_fixture_lock_shape():
    lock = json.loads((FIXTURE_ROOT / "fixture-lock.json").read_text())
    assert lock["phase"] == "0"
    assert "input_hashes" in lock
    assert "generated_hashes" in lock
