"""Phase 4.5 optimization output generation service."""

from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from api.core.config import settings
from api.core.logging import get_logger


class OptimizationOutputService:
    """Generate optimization outputs for execution/hyperparameter tasks."""

    def __init__(self) -> None:
        self.logger = get_logger("api.optimization_output_service")
        self.base_output_dir = Path(settings.project_root) / "optimization_results"
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

        templates_dir = Path(settings.project_root) / "templates"
        self.template_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate_outputs(
        self,
        task_type: str,
        task_id: str,
        task_info: Any,
        optimizer: Optional[Any] = None,
    ) -> Dict[str, Path]:
        """Generate summary/json/csv/markdown/html artifacts."""
        normalized_task_type = self._normalize_task_type(task_type)
        output_dir = self.base_output_dir / normalized_task_type / task_id
        output_dir.mkdir(parents=True, exist_ok=True)

        summary = self._build_summary(normalized_task_type, task_id, task_info, optimizer)

        summary_json_path = output_dir / "summary.json"
        summary_json_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary_csv_path = output_dir / "summary.csv"
        self._write_summary_csv(summary, summary_csv_path)

        trades_csv_path = output_dir / "trades.csv"
        self._write_trades_csv(summary.get("trades", []), trades_csv_path)

        equity_curve_csv_path = output_dir / "equity_curve.csv"
        self._write_equity_curve_csv(summary.get("equity_curve", []), equity_curve_csv_path)

        trials_csv_path = output_dir / "trials.csv"
        self._write_trials_csv(summary.get("trials", []), trials_csv_path)

        report_md_path = output_dir / "ai_readable_report.md"
        report_md_path.write_text(self._build_ai_report(summary), encoding="utf-8")

        html_report_path = output_dir / "optimization_report.html"
        html_report_path.write_text(self._render_html_report(summary), encoding="utf-8")

        self.logger.info(
            f"Optimization outputs generated: task_type={normalized_task_type}, task_id={task_id}, dir={output_dir}"
        )

        return {
            "output_dir": output_dir,
            "summary_json": summary_json_path,
            "summary_csv": summary_csv_path,
            "trades_csv": trades_csv_path,
            "equity_curve_csv": equity_curve_csv_path,
            "trials_csv": trials_csv_path,
            "ai_report_md": report_md_path,
            "html_report": html_report_path,
        }

    def ensure_outputs(
        self,
        task_type: str,
        task_id: str,
        task_info: Any,
        optimizer: Optional[Any] = None,
    ) -> Dict[str, Path]:
        output_dir = self.base_output_dir / self._normalize_task_type(task_type) / task_id
        artifacts = self._artifacts_from_dir(output_dir)
        if all(path.exists() for path in artifacts.values() if path != artifacts["output_dir"]):
            return artifacts
        return self.generate_outputs(task_type=task_type, task_id=task_id, task_info=task_info, optimizer=optimizer)

    def load_summary(self, task_type: str, task_id: str) -> Dict[str, Any]:
        output_dir = self.base_output_dir / self._normalize_task_type(task_type) / task_id
        summary_path = output_dir / "summary.json"
        if not summary_path.exists():
            return {}
        return json.loads(summary_path.read_text(encoding="utf-8"))

    def build_zip_bytes(self, files: Iterable[Path]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in files:
                if file_path.exists() and file_path.is_file():
                    zip_file.write(file_path, arcname=file_path.name)
        return buffer.getvalue()

    @staticmethod
    def save_temp_bytes(content: bytes, suffix: str) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            return temp_file.name

    def _build_summary(
        self,
        task_type: str,
        task_id: str,
        task_info: Any,
        optimizer: Optional[Any],
    ) -> Dict[str, Any]:
        result = getattr(task_info, "result", None)
        progress = getattr(task_info, "progress", None)
        config = getattr(task_info, "config", {}) or {}

        best_trial = {
            "trial_number": getattr(result, "best_trial_number", None),
            "value": getattr(result, "best_value", None),
            "params": getattr(result, "best_params", None) or {},
        }

        performance_metrics = self._to_dict(getattr(result, "metrics", None))
        if not performance_metrics and progress is not None:
            performance_metrics = {"best_value": getattr(progress, "best_value", None)}

        parameter_importance = self._to_dict(getattr(result, "parameter_importance", None))
        if not parameter_importance:
            parameter_importance = {}

        constraints = self._to_dict(config.get("objective_config", {}).get("constraints"))
        constraint_satisfaction = self._evaluate_constraints(performance_metrics, constraints)

        trials = self._extract_trials(optimizer)
        trades = self._extract_trades(result)
        equity_curve = self._extract_equity_curve(result)

        benchmark_comparison = self._build_benchmark_comparison(performance_metrics)

        summary: Dict[str, Any] = {
            "meta": {
                "task_id": task_id,
                "task_type": task_type,
                "status": getattr(getattr(task_info, "status", None), "value", "unknown"),
                "study_name": getattr(task_info, "study_name", None),
                "created_at": self._iso_or_none(getattr(task_info, "created_at", None)),
                "started_at": self._iso_or_none(getattr(task_info, "started_at", None)),
                "completed_at": self._iso_or_none(getattr(task_info, "completed_at", None)),
            },
            "best_trial": best_trial,
            "performance_metrics": performance_metrics,
            "constraint_satisfaction": constraint_satisfaction,
            "parameter_importance": parameter_importance,
            "benchmark_comparison": benchmark_comparison,
            "trials": trials,
            "trades": trades,
            "equity_curve": equity_curve,
        }
        return summary

    def _build_ai_report(self, summary: Dict[str, Any]) -> str:
        meta = summary.get("meta", {})
        best_trial = summary.get("best_trial", {})
        performance = summary.get("performance_metrics", {})
        constraints = summary.get("constraint_satisfaction", {})
        warnings = self._collect_report_warnings(summary)
        recommended_action = self._decide_recommended_action(performance, constraints)

        return "\n".join(
            [
                f"# Optimization Report — {meta.get('task_id', 'unknown')}",
                "",
                "## Summary",
                f"- task_type: {meta.get('task_type', 'unknown')}",
                f"- status: {meta.get('status', 'unknown')}",
                f"- completed_at: {meta.get('completed_at')}",
                "",
                "## Best Parameters",
                f"- best_trial_number: {best_trial.get('trial_number')}",
                f"- best_value: {best_trial.get('value')}",
                f"- params: {json.dumps(best_trial.get('params', {}), ensure_ascii=False)}",
                "",
                "## Performance",
                f"- metrics: {json.dumps(performance, ensure_ascii=False)}",
                f"- constraint_satisfaction: {json.dumps(constraints, ensure_ascii=False)}",
                "",
                "## Decision",
                f"- RECOMMENDED_ACTION: {recommended_action}",
                "",
                "## Warnings",
                *(warnings if warnings else ["- None"]),
                "",
                "## Next Steps",
                "- 若 RECOMMENDED_ACTION=PROCEED，建議進入下一階段驗證。",
                "- 若 RECOMMENDED_ACTION=REOPTIMIZE，建議調整搜索空間與限制後重跑。",
            ]
        )

    def _render_html_report(self, summary: Dict[str, Any]) -> str:
        template = self.template_env.get_template("optimization_report.html")
        return template.render(
            summary=summary,
            meta=summary.get("meta", {}),
            best_trial=summary.get("best_trial", {}),
            performance_metrics=summary.get("performance_metrics", {}),
            constraint_satisfaction=summary.get("constraint_satisfaction", {}),
            benchmark_comparison=summary.get("benchmark_comparison", {}),
            equity_curve=summary.get("equity_curve", []),
        )

    def _write_summary_csv(self, summary: Dict[str, Any], output_path: Path) -> None:
        rows: List[Tuple[str, str]] = []
        flat_fields = {
            "task_id": summary.get("meta", {}).get("task_id"),
            "task_type": summary.get("meta", {}).get("task_type"),
            "status": summary.get("meta", {}).get("status"),
            "best_trial_number": summary.get("best_trial", {}).get("trial_number"),
            "best_value": summary.get("best_trial", {}).get("value"),
        }
        for key, value in flat_fields.items():
            rows.append((key, "" if value is None else str(value)))

        with output_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["field", "value"])
            writer.writerows(rows)

    def _write_trades_csv(self, trades: List[Dict[str, Any]], output_path: Path) -> None:
        headers = [
            "trade_id",
            "entry_time",
            "entry_price",
            "exit_time",
            "exit_price",
            "position_size",
            "direction",
            "pnl",
            "pnl_pct",
            "exit_reason",
            "mae",
            "mfe",
        ]

        with output_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for index, trade in enumerate(trades, start=1):
                row = {"trade_id": index}
                for header in headers[1:]:
                    row[header] = trade.get(header)
                writer.writerow(row)

    def _write_equity_curve_csv(self, equity_curve: List[Dict[str, Any]], output_path: Path) -> None:
        headers = ["timestamp", "strategy_equity", "benchmark_equity", "drawdown", "returns"]

        with output_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for row in equity_curve:
                writer.writerow(
                    {
                        "timestamp": row.get("timestamp"),
                        "strategy_equity": row.get("strategy_equity"),
                        "benchmark_equity": row.get("benchmark_equity"),
                        "drawdown": row.get("drawdown"),
                        "returns": row.get("returns"),
                    }
                )

    def _write_trials_csv(self, trials: List[Dict[str, Any]], output_path: Path) -> None:
        headers = [
            "trial_number",
            "state",
            "value",
            "values",
            "datetime_start",
            "datetime_complete",
            "duration_seconds",
            "params",
            "user_attrs",
        ]

        with output_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for trial in trials:
                writer.writerow(
                    {
                        "trial_number": trial.get("trial_number"),
                        "state": trial.get("state"),
                        "value": trial.get("value"),
                        "values": json.dumps(trial.get("values"), ensure_ascii=False),
                        "datetime_start": trial.get("datetime_start"),
                        "datetime_complete": trial.get("datetime_complete"),
                        "duration_seconds": trial.get("duration_seconds"),
                        "params": json.dumps(trial.get("params"), ensure_ascii=False),
                        "user_attrs": json.dumps(trial.get("user_attrs"), ensure_ascii=False),
                    }
                )

    def _extract_trials(self, optimizer: Optional[Any]) -> List[Dict[str, Any]]:
        if optimizer is None:
            return []

        study = getattr(optimizer, "study", None)
        if study is None:
            return []

        trials: List[Dict[str, Any]] = []
        for trial in getattr(study, "trials", []):
            duration_seconds = None
            if getattr(trial, "duration", None) is not None:
                duration_seconds = trial.duration.total_seconds()

            trial_values = getattr(trial, "values", None)
            try:
                trial_value = getattr(trial, "value", None)
            except RuntimeError:
                trial_value = trial_values[0] if trial_values else None

            trials.append(
                {
                    "trial_number": getattr(trial, "number", None),
                    "state": str(getattr(trial, "state", "")).split(".")[-1],
                    "value": trial_value,
                    "values": list(trial_values) if trial_values is not None else [],
                    "datetime_start": self._iso_or_none(getattr(trial, "datetime_start", None)),
                    "datetime_complete": self._iso_or_none(getattr(trial, "datetime_complete", None)),
                    "duration_seconds": duration_seconds,
                    "params": dict(getattr(trial, "params", {}) or {}),
                    "user_attrs": dict(getattr(trial, "user_attrs", {}) or {}),
                }
            )
        return trials

    def _extract_trades(self, result: Any) -> List[Dict[str, Any]]:
        if result is None:
            return []

        backtest_result = getattr(result, "backtest_result", None)
        trades = getattr(backtest_result, "trades", None) if backtest_result is not None else None
        if trades is None:
            trades = getattr(result, "trades", None)

        if not isinstance(trades, list):
            return []

        rows: List[Dict[str, Any]] = []
        for trade in trades:
            if is_dataclass(trade):
                trade_dict = asdict(trade)
            elif isinstance(trade, dict):
                trade_dict = dict(trade)
            else:
                trade_dict = self._to_dict(trade)
            rows.append({key: self._normalize_scalar(value) for key, value in trade_dict.items()})
        return rows

    def _extract_equity_curve(self, result: Any) -> List[Dict[str, Any]]:
        if result is None:
            return []

        backtest_result = getattr(result, "backtest_result", None)
        equity_curve = getattr(backtest_result, "equity_curve", None) if backtest_result is not None else None
        if equity_curve is None:
            equity_curve = getattr(result, "equity_curve", None)

        if isinstance(equity_curve, pd.Series):
            series = equity_curve.ffill().fillna(1.0)
            running_max = series.cummax()
            drawdown = (series / running_max) - 1.0
            returns = series.pct_change().fillna(0.0)
            rows: List[Dict[str, Any]] = []
            for idx, value in series.items():
                rows.append(
                    {
                        "timestamp": self._normalize_scalar(idx),
                        "strategy_equity": float(value),
                        "benchmark_equity": 1.0,
                        "drawdown": float(drawdown.loc[idx]),
                        "returns": float(returns.loc[idx]),
                    }
                )
            return rows

        if isinstance(equity_curve, list):
            normalized_rows = []
            for row in equity_curve:
                if isinstance(row, dict):
                    normalized_rows.append(
                        {
                            "timestamp": self._normalize_scalar(row.get("timestamp")),
                            "strategy_equity": row.get("strategy_equity"),
                            "benchmark_equity": row.get("benchmark_equity", 1.0),
                            "drawdown": row.get("drawdown", 0.0),
                            "returns": row.get("returns", 0.0),
                        }
                    )
            return normalized_rows

        return []

    def _artifacts_from_dir(self, output_dir: Path) -> Dict[str, Path]:
        return {
            "output_dir": output_dir,
            "summary_json": output_dir / "summary.json",
            "summary_csv": output_dir / "summary.csv",
            "trades_csv": output_dir / "trades.csv",
            "equity_curve_csv": output_dir / "equity_curve.csv",
            "trials_csv": output_dir / "trials.csv",
            "ai_report_md": output_dir / "ai_readable_report.md",
            "html_report": output_dir / "optimization_report.html",
        }

    def _evaluate_constraints(
        self,
        performance_metrics: Dict[str, Any],
        constraints: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        if not constraints:
            return {}

        checks: Dict[str, Dict[str, Any]] = {}

        metric_mapping = {
            "max_drawdown": "max_drawdown",
            "min_win_rate": "win_rate",
            "min_trades": "total_trades",
        }

        for key, limit in constraints.items():
            metric_key = metric_mapping.get(key)
            actual = performance_metrics.get(metric_key) if metric_key else None
            satisfied = None
            if actual is not None:
                if key == "max_drawdown":
                    satisfied = float(actual) >= float(limit)
                elif key in {"min_win_rate", "min_trades"}:
                    satisfied = float(actual) >= float(limit)
            checks[key] = {
                "limit": limit,
                "actual": actual,
                "satisfied": satisfied,
            }

        return checks

    def _build_benchmark_comparison(self, performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "strategy": {
                "total_return": performance_metrics.get("total_return"),
                "sharpe_ratio": performance_metrics.get("sharpe_ratio"),
                "max_drawdown": performance_metrics.get("max_drawdown"),
            },
            "benchmark": {
                "total_return": None,
                "sharpe_ratio": None,
                "max_drawdown": None,
            },
            "difference": {
                "total_return": None,
                "sharpe_ratio": None,
                "max_drawdown": None,
            },
        }

    def _collect_report_warnings(self, summary: Dict[str, Any]) -> List[str]:
        warnings: List[str] = []
        metrics = summary.get("performance_metrics", {})
        trades = summary.get("trades", [])
        constraints = summary.get("constraint_satisfaction", {})

        if not trades:
            warnings.append("- No trades data available.")

        total_trades = metrics.get("total_trades")
        if total_trades is not None and float(total_trades) < 10:
            warnings.append("- Trade count is below 10; result stability may be limited.")

        for key, value in constraints.items():
            if value.get("satisfied") is False:
                warnings.append(f"- Constraint not satisfied: {key}.")

        return warnings

    def _decide_recommended_action(
        self,
        performance_metrics: Dict[str, Any],
        constraints: Dict[str, Dict[str, Any]],
    ) -> str:
        if constraints and any(item.get("satisfied") is False for item in constraints.values()):
            return "REOPTIMIZE"

        expectancy = performance_metrics.get("expectancy")
        sharpe = performance_metrics.get("sharpe_ratio")

        if expectancy is None and sharpe is None:
            return "INSUFFICIENT_DATA"

        if expectancy is not None and float(expectancy) <= 0:
            return "REOPTIMIZE"

        if sharpe is not None and float(sharpe) < 1.0:
            return "REVIEW"

        return "PROCEED"

    @staticmethod
    def _to_dict(value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return {}

    @staticmethod
    def _normalize_task_type(task_type: str) -> str:
        lowered = task_type.lower()
        if lowered in {"execution", "strategy_backtest"}:
            return "execution"
        if lowered in {"hyperparameter", "model_hyperparam"}:
            return "hyperparameter"
        return lowered

    @staticmethod
    def _iso_or_none(value: Any) -> Optional[str]:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _normalize_scalar(value: Any) -> Any:
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value


_optimization_output_service: Optional[OptimizationOutputService] = None


def get_optimization_output_service() -> OptimizationOutputService:
    global _optimization_output_service
    if _optimization_output_service is None:
        _optimization_output_service = OptimizationOutputService()
    return _optimization_output_service
