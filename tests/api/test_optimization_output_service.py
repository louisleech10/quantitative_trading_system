from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from api.services.optimization_output_service import OptimizationOutputService


@dataclass
class _TaskProgress:
    completed_trials: int = 0
    total_trials: int = 100
    completion_percentage: float = 0.0
    best_value: float | None = None


@dataclass
class _TaskInfo:
    task_id: str
    study_name: str
    status: SimpleNamespace
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    progress: _TaskProgress
    result: object | None
    config: dict


@dataclass
class _Trade:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    position_size: float
    direction: str
    pnl: float
    pnl_pct: float
    exit_reason: str
    mae: float
    mfe: float


class _OptimizerStub:
    def __init__(self):
        trial = SimpleNamespace(
            number=1,
            state="COMPLETE",
            value=0.42,
            values=[0.42],
            datetime_start=datetime.now(),
            datetime_complete=datetime.now(),
            duration=SimpleNamespace(total_seconds=lambda: 1.23),
            params={"entry_threshold": 0.7},
            user_attrs={"win_rate": 0.55},
        )
        self.study = SimpleNamespace(trials=[trial])


def _make_task_info(task_id: str) -> _TaskInfo:
    trades = [
        _Trade(
            entry_time=pd.Timestamp("2026-01-01T00:00:00"),
            entry_price=100.0,
            exit_time=pd.Timestamp("2026-01-02T00:00:00"),
            exit_price=103.0,
            position_size=0.2,
            direction="long",
            pnl=0.006,
            pnl_pct=0.03,
            exit_reason="take_profit",
            mae=-0.01,
            mfe=0.05,
        )
    ]

    result = SimpleNamespace(
        best_trial_number=1,
        best_value=0.42,
        best_params={"entry_threshold": 0.7},
        metrics={"expectancy": 0.03, "win_rate": 0.55, "max_drawdown": -0.2, "total_trades": 15},
        parameter_importance={"entry_threshold": 0.88},
        trades=trades,
        equity_curve=pd.Series([1.0, 1.02, 1.01], index=pd.date_range("2026-01-01", periods=3, freq="12h")),
    )

    return _TaskInfo(
        task_id=task_id,
        study_name="phase45_test",
        status=SimpleNamespace(value="completed"),
        created_at=datetime.now(),
        started_at=datetime.now(),
        completed_at=datetime.now(),
        progress=_TaskProgress(completed_trials=10, total_trials=10, completion_percentage=100.0, best_value=0.42),
        result=result,
        config={
            "task_type": "strategy_backtest",
            "objective_config": {
                "constraints": {"max_drawdown": -0.3, "min_win_rate": 0.4, "min_trades": 10}
            },
        },
    )


def test_generate_outputs_creates_expected_files(tmp_path, monkeypatch):
    service = OptimizationOutputService()
    monkeypatch.setattr(service, "base_output_dir", tmp_path / "optimization_results")

    task_info = _make_task_info("task-phase45-1")
    artifacts = service.generate_outputs(
        task_type="execution",
        task_id="task-phase45-1",
        task_info=task_info,
        optimizer=_OptimizerStub(),
    )

    assert artifacts["summary_json"].exists()
    assert artifacts["trades_csv"].exists()
    assert artifacts["equity_curve_csv"].exists()
    assert artifacts["trials_csv"].exists()
    assert artifacts["ai_report_md"].exists()
    assert artifacts["html_report"].exists()

    summary_text = artifacts["summary_json"].read_text(encoding="utf-8")
    assert "constraint_satisfaction" in summary_text
    assert "benchmark_comparison" in summary_text


def test_generate_outputs_handles_empty_data(tmp_path, monkeypatch):
    service = OptimizationOutputService()
    monkeypatch.setattr(service, "base_output_dir", tmp_path / "optimization_results")

    empty_task = _TaskInfo(
        task_id="task-empty",
        study_name="phase45_empty",
        status=SimpleNamespace(value="completed"),
        created_at=datetime.now(),
        started_at=datetime.now(),
        completed_at=datetime.now(),
        progress=_TaskProgress(completed_trials=0, total_trials=10, completion_percentage=0.0, best_value=None),
        result=SimpleNamespace(best_trial_number=None, best_value=None, best_params={}, metrics={}, parameter_importance={}),
        config={"task_type": "model_hyperparam", "objective_config": {}},
    )

    artifacts = service.generate_outputs(
        task_type="hyperparameter",
        task_id="task-empty",
        task_info=empty_task,
        optimizer=None,
    )

    trades_rows = artifacts["trades_csv"].read_text(encoding="utf-8").splitlines()
    equity_rows = artifacts["equity_curve_csv"].read_text(encoding="utf-8").splitlines()

    assert len(trades_rows) == 1
    assert len(equity_rows) == 1
    assert artifacts["ai_report_md"].exists()
    assert artifacts["html_report"].exists()


def test_build_zip_bytes_includes_files(tmp_path):
    service = OptimizationOutputService()

    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("A", encoding="utf-8")
    file_b.write_text("B", encoding="utf-8")

    content = service.build_zip_bytes([file_a, file_b])
    assert isinstance(content, bytes)
    assert len(content) > 0
