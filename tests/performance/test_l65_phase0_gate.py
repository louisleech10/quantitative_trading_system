from pathlib import Path

import pytest

from scripts.benchmark_l65 import (
    STATUS_PASS,
    _memory_sanity_failed,
    _parse_tier_gb,
    build_parser,
    run_benchmark,
)
from scripts.compare_output_size import compare_phase_outputs


@pytest.mark.slow
def test_l65_phase0_benchmark_synthetic_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 Task 0.8 benchmark harness 可在小型合成資料上完成。"""
    import scripts.benchmark_l65 as benchmark_module
    import scripts.compare_output_size as compare_module

    monkeypatch.setattr(benchmark_module, "RESULT_DIR", tmp_path / "results")
    monkeypatch.setattr(benchmark_module, "OUTPUT_DIR", tmp_path / "results" / "outputs")
    monkeypatch.setattr(benchmark_module, "CHECKPOINT_DIR", tmp_path / "results" / "checkpoints")
    monkeypatch.setattr(compare_module, "RESULT_DIR", tmp_path / "results")

    args = build_parser().parse_args([
        "--tier=8gb",
        "--synthetic",
        "--max-rows=80",
        "--max-cols=6",
        "--full-l65",
    ])

    payload = run_benchmark(args)

    assert payload["status"] == STATUS_PASS
    assert payload["gate_id"] == "T0.P5"
    assert payload["entries"]
    assert payload["entries"][0]["output_columns"] >= payload["entries"][0]["input_columns"]


def test_l65_phase0_memory_sanity_detects_monotonic_growth() -> None:
    """測試 Task 0.8 RSS sanity gate 會偵測持續累積。"""
    parser = build_parser()
    args = parser.parse_args([])
    assert _parse_tier_gb(args.tier) == 8

    class Entry:
        def __init__(self, value: int) -> None:
            self.rss_before_mb = value
            self.peak_rss_mb = value + 10
            self.rss_after_gc_mb = value

    entries = [Entry(100 + index * 100) for index in range(20)]
    assert _memory_sanity_failed(entries) is True


def test_l65_phase0_output_size_compare_blocks_without_baseline(tmp_path: Path) -> None:
    """測試沒有 benchmark output 時，size compare 會 BLOCKED 而非假 PASS。"""
    payload = compare_phase_outputs(0, result_dir=tmp_path)

    assert payload["status"] == "BLOCKED"
    assert payload["result_files_scanned"] == 0
