from pathlib import Path

import pytest

from scripts.benchmark_l65 import STATUS_PASS, build_parser, run_benchmark


def test_l65_phase0_gate_command_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """讓 `pytest tests/feature_engineering tests/api -k l65` 覆蓋 Task 0.8 harness。"""
    import scripts.benchmark_l65 as benchmark_module

    monkeypatch.setattr(benchmark_module, "RESULT_DIR", tmp_path / "results")
    monkeypatch.setattr(benchmark_module, "OUTPUT_DIR", tmp_path / "results" / "outputs")
    monkeypatch.setattr(benchmark_module, "CHECKPOINT_DIR", tmp_path / "results" / "checkpoints")

    # 列數 64 → 80（§N R17）：`--full-l65` 縮尾後 64 列每欄有效值僅 10，低於工具校準下限 20
    # （scripts/build_l65_golden.py:146-147）而 FAIL；80 列與 tests/performance 同 harness 之綠燈 smoke 一致。
    # 改的是測試輸入，不改工具下限。
    args = build_parser().parse_args([
        "--tier=8gb",
        "--synthetic",
        "--max-rows=80",
        "--max-cols=4",
        "--full-l65",
    ])

    payload = run_benchmark(args)

    assert payload["status"] == STATUS_PASS
    assert payload["gate_id"] == "T0.P5"
    assert payload["entries"][0]["rows_per_item"] == 80
