from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import tempfile

import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from api.routes import execution_optimization as execution_route
from api.routes import hyperparameter_optimization as hyper_route


class _StubTaskInfo:
    def __init__(self, task_id: str, task_type: str = "strategy_backtest"):
        self.task_id = task_id
        self.created_at = datetime.now()
        self.completed_at = None
        self.status = SimpleNamespace(value="running")
        self.config = {"task_type": task_type}
        self.result = SimpleNamespace(
            best_trial_number=3,
            best_value=0.321,
            best_params={"entry_threshold": 0.7},
            metrics={"expectancy": 0.12},
            parameter_importance={"entry_threshold": 0.8},
        )
        self.progress = SimpleNamespace(
            completed_trials=12,
            total_trials=100,
            completion_percentage=12.0,
            best_value=0.321,
        )


class _StubOptimizationTaskService:
    def __init__(self):
        self._tasks = {
            "execution-task": _StubTaskInfo("execution-task", "strategy_backtest"),
            "hyper-task": _StubTaskInfo("hyper-task", "model_hyperparam"),
        }

    def create_task(self, **kwargs):
        task_type = kwargs.get("task_type", "strategy_backtest")
        task_id = "hyper-task" if task_type == "model_hyperparam" else "execution-task"
        self._tasks[task_id] = _StubTaskInfo(task_id, task_type)
        return task_id

    async def start_task(self, task_id: str) -> bool:
        return task_id in self._tasks

    def get_task(self, task_id: str):
        return self._tasks.get(task_id)


class _StubOutputService:
    def __init__(self):
        self._temp_dir = Path(tempfile.mkdtemp(prefix="phase45_output_"))
        self._summary = {
            "meta": {"task_id": "hyper-task", "task_type": "hyperparameter", "status": "running"},
            "best_trial": {"trial_number": 3, "value": 0.321, "params": {"entry_threshold": 0.7}},
        }

    def ensure_outputs(self, task_type, task_id, task_info, optimizer=None):
        task_dir = self._temp_dir / task_type / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        summary_json = task_dir / "summary.json"
        summary_json.write_text('{"ok": true}', encoding="utf-8")

        summary_csv = task_dir / "summary.csv"
        summary_csv.write_text("field,value\nstatus,running\n", encoding="utf-8")

        trades_csv = task_dir / "trades.csv"
        trades_csv.write_text(
            "trade_id,entry_time,entry_price,exit_time,exit_price,position_size,direction,pnl,pnl_pct,exit_reason,mae,mfe\n",
            encoding="utf-8",
        )

        equity_curve_csv = task_dir / "equity_curve.csv"
        equity_curve_csv.write_text(
            "timestamp,strategy_equity,benchmark_equity,drawdown,returns\n",
            encoding="utf-8",
        )

        trials_csv = task_dir / "trials.csv"
        trials_csv.write_text("trial_number,state,value\n1,COMPLETE,0.1\n", encoding="utf-8")

        ai_report_md = task_dir / "ai_readable_report.md"
        ai_report_md.write_text("# report\n", encoding="utf-8")

        html_report = task_dir / "optimization_report.html"
        html_report.write_text("<html><body>ok</body></html>", encoding="utf-8")

        return {
            "output_dir": task_dir,
            "summary_json": summary_json,
            "summary_csv": summary_csv,
            "trades_csv": trades_csv,
            "equity_curve_csv": equity_curve_csv,
            "trials_csv": trials_csv,
            "ai_report_md": ai_report_md,
            "html_report": html_report,
        }

    def load_summary(self, task_type: str, task_id: str):
        return self._summary

    @staticmethod
    def build_zip_bytes(files):
        return b"fake-zip-content"

    @staticmethod
    def save_temp_bytes(content: bytes, suffix: str):
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(content)
            return f.name


def _create_csv(path: Path, rows: int = 10):
    df = pd.DataFrame(
        {
            "f1": range(rows),
            "f2": range(rows, rows * 2),
        }
    )
    df.to_csv(path, index=False)


def test_hyperparameter_optimization_start(monkeypatch, tmp_path):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(hyper_route, "optimization_task_service", stub_service)

    features_path = tmp_path / "features.csv"
    labels_path = tmp_path / "labels.csv"
    _create_csv(features_path)
    pd.DataFrame({"label": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]}).to_csv(labels_path, index=False)

    client = TestClient(app)
    response = client.post(
        "/api/v1/optimization/hyperparameter",
        json={
            "model_type": "lightgbm",
            "features_path": str(features_path),
            "labels_path": str(labels_path),
            "n_trials": 5,
            "timeout_seconds": 60,
            "max_train_val_gap": 0.1,
            "cv_folds": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "hyper-task"
    assert payload["status"] == "running"


def test_execution_optimization_start(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(execution_route, "optimization_task_service", stub_service)

    client = TestClient(app)
    response = client.post(
        "/api/v1/optimization/execution",
        json={
            "model_predictions_path": "data/predictions.csv",
            "target_metric": "expectancy",
            "n_trials": 5,
            "timeout_seconds": 60,
            "constraints": {"max_drawdown": -0.3, "min_win_rate": 0.4, "min_trades": 10},
            "backtest_config": {"commission": 0.001, "slippage": 0.0005},
            "multi_objective": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "execution-task"


def test_get_optimization_config(monkeypatch):
    monkeypatch.setattr(
        hyper_route.MomentumConfig,
        "load_optimization_config",
        staticmethod(lambda: {"execution": {"search_space": {}}, "hyperparameter": {"lightgbm": {}}}),
    )

    client = TestClient(app)
    response = client.get("/api/v1/optimization/config")

    assert response.status_code == 200
    payload = response.json()
    assert "execution" in payload
    assert "hyperparameter" in payload


def test_get_optimization_result(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(execution_route, "optimization_task_service", stub_service)

    client = TestClient(app)
    response = client.get("/api/v1/optimization/execution-task/result")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "execution-task"
    assert payload["best_trial"]["trial_number"] == 3


def test_export_optimization_result_json(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(hyper_route, "optimization_task_service", stub_service)
    monkeypatch.setattr(hyper_route, "get_optimization_output_service", lambda: _StubOutputService())

    client = TestClient(app)
    response = client.post(
        "/api/v1/optimization/hyperparameter/hyper-task/export",
        json={"format": "json"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["task_id"] == "hyper-task"
    assert payload["meta"]["task_type"] == "hyperparameter"


def test_export_optimization_result_html(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(hyper_route, "optimization_task_service", stub_service)
    monkeypatch.setattr(hyper_route, "get_optimization_output_service", lambda: _StubOutputService())

    client = TestClient(app)
    response = client.post(
        "/api/v1/optimization/hyperparameter/hyper-task/export",
        json={"format": "html"},
    )

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_export_optimization_result_csv(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(hyper_route, "optimization_task_service", stub_service)
    monkeypatch.setattr(hyper_route, "get_optimization_output_service", lambda: _StubOutputService())

    client = TestClient(app)
    response = client.post(
        "/api/v1/optimization/hyperparameter/hyper-task/export",
        json={"format": "csv"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")


def test_export_optimization_result_charts_zip(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(hyper_route, "optimization_task_service", stub_service)
    monkeypatch.setattr(hyper_route, "get_optimization_output_service", lambda: _StubOutputService())

    client = TestClient(app)
    response = client.post(
        "/api/v1/optimization/hyperparameter/hyper-task/export",
        json={"format": "charts"},
    )

    assert response.status_code == 200
    assert "application/zip" in response.headers.get("content-type", "")


def test_export_optimization_result_full_zip(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(hyper_route, "optimization_task_service", stub_service)
    monkeypatch.setattr(hyper_route, "get_optimization_output_service", lambda: _StubOutputService())

    client = TestClient(app)
    response = client.post(
        "/api/v1/optimization/hyperparameter/hyper-task/export",
        json={"format": "full"},
    )

    assert response.status_code == 200
    assert "application/zip" in response.headers.get("content-type", "")


def test_result_task_not_found(monkeypatch):
    stub_service = _StubOptimizationTaskService()
    monkeypatch.setattr(execution_route, "optimization_task_service", stub_service)

    client = TestClient(app)
    response = client.get("/api/v1/optimization/not-found/result")

    assert response.status_code == 404
