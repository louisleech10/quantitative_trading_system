from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest

from scripts.benchmark_l65 import (
    STATUS_BLOCKED,
    STATUS_PASS,
    build_parser,
    detect_regression,
    run_benchmark,
    run_smoke_suite,
)


@contextmanager
def _disabled_tier_limit(*_args: object, **_kwargs: object) -> Iterator[Dict[str, Any]]:
    yield {
        "enabled": False,
        "requested_tier_gb": 8,
        "status": "skipped",
        "reason": "disabled in unit test",
    }


def _redirect_benchmark_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.benchmark_l65 as benchmark_module

    monkeypatch.setattr(benchmark_module, "RESULT_DIR", tmp_path / "results")
    monkeypatch.setattr(benchmark_module, "OUTPUT_DIR", tmp_path / "results" / "outputs")
    monkeypatch.setattr(benchmark_module, "CHECKPOINT_DIR", tmp_path / "results" / "checkpoints")
    monkeypatch.setattr(benchmark_module, "_tier_memory_limit", _disabled_tier_limit)


@pytest.mark.slow
def test_l65_smoke_suite_runs_explicit_tier_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 Task 3.1 smoke mode 會跑指定 tier 的 3 個 phase 並產出 JSON。"""
    _redirect_benchmark_outputs(tmp_path, monkeypatch)
    args = build_parser().parse_args([
        "--smoke",
        "--tier=8gb",
        "--max-rows=80",
        "--max-cols=6",
    ])
    setattr(args, "_tier_explicit", True)

    payload = run_smoke_suite(args)

    assert payload["status"] == STATUS_PASS
    assert payload["gate_id"] == "T3.1"
    assert payload["smoke_tiers"] == ["8gb"]
    assert payload["smoke_phases"] == ["0", "1", "2"]
    assert len(payload["entries"]) == 3
    assert payload["result_paths"]
    for relative_path in payload["result_paths"]:
        assert (Path.cwd() / relative_path).exists()


def test_l65_benchmark_writes_suite_and_legacy_result_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 Task 3.1 新結果命名與 Task 0.8 legacy gate 命名同時保留。"""
    _redirect_benchmark_outputs(tmp_path, monkeypatch)
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
    result_names = [Path(path).name for path in payload["result_paths"]]
    assert any(name.startswith("8gb_0_") for name in result_names)
    assert any(name.startswith("phase0_gate_T0_P5_") for name in result_names)
    assert payload["l7_size_mb"] is not None
    assert payload["history_sample_count"] >= 0


def test_l65_detect_regression_flags_wall_or_rss_degradation() -> None:
    """測試 7-day history regression flag 在 wall/RSS 退化超過 20% 時為 True。"""
    current: Dict[str, Any] = {
        "status": STATUS_PASS,
        "wall_time_seconds": 130.0,
        "peak_rss_mb": 1300,
    }
    history: List[Dict[str, Any]] = [
        {"wall_time_seconds": 100.0, "peak_rss_mb": 1000},
        {"wall_time_seconds": 101.0, "peak_rss_mb": 1005},
        {"wall_time_seconds": 99.0, "peak_rss_mb": 995},
    ]

    assert detect_regression(current, history) is True


def test_l65_full_mode_blocks_8gb_without_best_effort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 8GB 不允許未標 best-effort 的 full benchmark。"""
    _redirect_benchmark_outputs(tmp_path, monkeypatch)
    args = build_parser().parse_args(["--tier=8gb", "--full"])

    payload = run_benchmark(args)

    assert payload["status"] == STATUS_BLOCKED
    assert "8GB --full requires --best-effort" in payload["blocking_reason"]
