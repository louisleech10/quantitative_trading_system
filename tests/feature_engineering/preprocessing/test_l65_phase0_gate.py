from pathlib import Path

import pytest

from scripts.benchmark_l65 import STATUS_PASS, build_parser, run_benchmark


def test_l65_phase0_gate_command_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """讓 `pytest tests/feature_engineering tests/api -k l65` 覆蓋 Task 0.8 harness。"""
    import scripts.benchmark_l65 as benchmark_module

    monkeypatch.setattr(benchmark_module, "RESULT_DIR", tmp_path / "results")
    monkeypatch.setattr(benchmark_module, "OUTPUT_DIR", tmp_path / "results" / "outputs")
    monkeypatch.setattr(benchmark_module, "CHECKPOINT_DIR", tmp_path / "results" / "checkpoints")

    args = build_parser().parse_args([
        "--tier=8gb",
        "--synthetic",
        "--max-rows=64",
        "--max-cols=4",
        "--full-l65",
    ])

    payload = run_benchmark(args)

    assert payload["status"] == STATUS_PASS
    assert payload["gate_id"] == "T0.P5"
    assert payload["entries"][0]["rows_per_item"] == 64
