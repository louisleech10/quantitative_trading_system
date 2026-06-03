"""批次品質彙整 adapter 測試 — 真實 NaN / real_problem / warmup 拆分。"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import api.services.feature_factory_service as feature_service_module
from api.services.feature_factory_batch_adapters import FeatureFactoryQualityAdapter
from api.services.feature_factory_service import FeatureFactoryService
from tests.api.conftest import MockQualityComputer


def _write_cgsa_manifest(
    tmp_path,
    *,
    symbol: str,
    timeframe: str,
    config_hash: str,
    frame: pd.DataFrame,
):
    manifest_dir = tmp_path / "features" / symbol / timeframe / config_hash
    manifest_dir.mkdir(parents=True)
    parquet_path = manifest_dir / "features.parquet"
    frame.to_parquet(parquet_path, index=False)
    manifest_path = manifest_dir / "feature_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "symbol": symbol,
                "primary_tf": timeframe,
                "config_hash": config_hash,
                "total_features": len(frame.columns),
                "groups": [
                    {
                        "group_id": f"{timeframe}_L1_{config_hash}",
                        "parquet_path": str(parquet_path),
                        "columns": list(frame.columns),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def test_batch_quality_uses_real_nan_not_null_count(monkeypatch, tmp_path):
    """NaN 均/峰須來自 dq np.isnan 掃描，不可因 parquet null_count 顯示 0。"""
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    service = FeatureFactoryService()

    n_rows = 500
    warmup = np.full(n_rows, np.nan, dtype=float)
    warmup[400:] = np.arange(100, dtype=float)
    clean = np.arange(n_rows, dtype=float)

    manifest_path = _write_cgsa_manifest(
        tmp_path,
        symbol="BTCUSDT",
        timeframe="1h",
        config_hash="cfg_nan_real",
        frame=pd.DataFrame({"feat_warmup": warmup, "feat_clean": clean}),
    )

    result = FeatureFactoryQualityAdapter(service).compute(str(manifest_path))
    independent_max = float(pd.DataFrame({"feat_warmup": warmup, "feat_clean": clean}).isna().mean().max())

    assert result["nan_ratio_max"] > 0.5
    assert abs(result["nan_ratio_max"] - independent_max) <= 0.01
    assert result["nan_ratio_mean"] > 0.0
    assert result["nan_quantiles"]["median"] > 0.0
    assert result["real_problem_count"] == result["alert_count"]


def test_batch_quality_invalidates_dq_v4_disk_cache_and_persists_nan_ratio(monkeypatch, tmp_path):
    """舊 dq_v4 disk cache 無 nan_ratio 時須 miss 重算，adapter 不可退回 0。"""
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    service = FeatureFactoryService()

    n_rows = 500
    high_nan = np.full(n_rows, np.nan, dtype=float)
    high_nan[425:] = np.arange(75, dtype=float)
    clean = np.arange(n_rows, dtype=float)
    frame = pd.DataFrame({"feat_high_nan": high_nan, "feat_clean": clean})

    manifest_path = _write_cgsa_manifest(
        tmp_path,
        symbol="BTCUSDT",
        timeframe="1h",
        config_hash="cfg_old_dq_cache",
        frame=frame,
    )
    cache_path = manifest_path.parent / "data_quality.json"
    cache_path.write_text(
        json.dumps(
            {
                "schema_version": "dq_v4",
                "total_features": 2,
                "total_timesteps": n_rows,
                "counts": {"real_problem": 0, "warmup_only_high_nan": 0},
            }
        ),
        encoding="utf-8",
    )

    result = FeatureFactoryQualityAdapter(service).compute(str(manifest_path))
    independent = frame.isna().mean()

    assert result["nan_ratio_max"] > 0.5
    assert abs(result["nan_ratio_max"] - float(independent.max())) <= 0.01
    assert abs(result["nan_ratio_mean"] - float(independent.mean())) <= 0.01

    persisted = json.loads(cache_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == "dq_v6"
    assert persisted["nan_ratio_max"] > 0.5
    assert abs(float(persisted["nan_ratio_max"]) - float(independent.max())) <= 0.01
    quantiles = persisted["nan_ratio_quantiles"]
    expected_q = np.percentile(independent.values, [0, 25, 50, 75, 100])
    for key, idx in [("min", 0), ("q1", 1), ("median", 2), ("q3", 3), ("max", 4)]:
        assert abs(float(quantiles[key]) - float(expected_q[idx])) <= 0.01


def test_batch_quality_warmup_only_does_not_trigger_watch(monkeypatch, tmp_path):
    """純暖機 leading NaN：real_problem=0 → pass，warmup_only_count>0。"""
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    service = FeatureFactoryService()

    n_rows = 600
    warmup_only = np.full(n_rows, np.nan, dtype=float)
    warmup_only[500:] = np.arange(100, dtype=float)

    manifest_path = _write_cgsa_manifest(
        tmp_path,
        symbol="ETHUSDT",
        timeframe="1h",
        config_hash="cfg_warmup_only",
        frame=pd.DataFrame({"feat_warmup": warmup_only}),
    )

    result = FeatureFactoryQualityAdapter(service).compute(str(manifest_path))

    assert result["alert_count"] == 0
    assert result["real_problem_count"] == 0
    assert result["warmup_only_count"] > 0
    assert result["grade"] == "pass"
    assert "median" in result["nan_quantiles"]


def test_batch_quality_mid_hole_triggers_watch(monkeypatch, tmp_path):
    """mid-hole 真問題 → alert_count=real_problem，grade 至少 watch。"""
    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    service = FeatureFactoryService()

    n_rows = 600

    def _mid_hole_series() -> np.ndarray:
        arr = np.arange(n_rows, dtype=float)
        arr[100:400] = np.nan
        return arr

    frame = pd.DataFrame({f"feat_hole_{i}": _mid_hole_series() for i in range(8)})

    manifest_path = _write_cgsa_manifest(
        tmp_path,
        symbol="DOGEUSDT",
        timeframe="1h",
        config_hash="cfg_mid_hole",
        frame=frame,
    )

    result = FeatureFactoryQualityAdapter(service).compute(str(manifest_path))

    assert result["alert_count"] >= 8
    assert result["grade"] in {"watch", "reject"}


def test_browse_summary_exposes_stats_warmup(monkeypatch):
    """browse_summary 須含 stats_warmup 結構化進度欄位。"""
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._stats_cache = {}
    service._stats_warming_tasks = set()
    service._cgsa_stats_mem_cache = {}
    service._cgsa_stats_warming_tasks = set()
    service._lock = __import__("threading").Lock()
    service._coalesce_browse = lambda _fp, fn: fn()

    monkeypatch.setattr(
        service,
        "_load_task_features",
        lambda _task_id: (
            pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]}),
            {"symbol": "BTCUSDT", "timeframe": "1h", "metadata": {}},
        ),
    )
    monkeypatch.setattr(service, "_start_stats_cache_warmup", lambda *_a, **_k: None)
    monkeypatch.setattr(service, "_start_adf_cache_warmup", lambda *_a, **_k: None)
    monkeypatch.setattr(
        service,
        "_get_stats_warmup_progress",
        lambda *_a, **_k: {
            "computed": 1,
            "total": 2,
            "pct": 50.0,
            "complete": False,
        },
    )

    result = service.browse_summary("task-stats-warmup")

    warmup = result.get("stats_warmup")
    assert warmup is not None
    assert warmup["computed"] == 1
    assert warmup["total"] == 2
    assert warmup["pct"] == 50.0
    assert warmup["complete"] is False


@pytest.mark.asyncio
async def test_get_batch_quality_summary_recovers_from_checkpoint_after_restart(
    tmp_path,
    batch_service_factory,
):
    """模擬 API 重啟：清 self._tasks 後仍從 checkpoint 重建品質彙整。"""
    grade_by_symbol = {
        "BTCUSDT": "pass",
        "ETHUSDT": "watch",
    }

    class SymbolAwareQualityComputer(MockQualityComputer):
        def compute(self, manifest_path: str) -> dict:
            self.calls.append(manifest_path)
            symbol = "BTCUSDT"
            for known_symbol in grade_by_symbol:
                if known_symbol in manifest_path:
                    symbol = known_symbol
                    break
            return {
                "symbol": symbol,
                "bar_count": 500,
                "feature_count": 2,
                "nan_ratio_mean": 0.0,
                "nan_ratio_max": 0.0,
                "constant_feature_count": 0,
                "alert_count": 0,
                "grade": grade_by_symbol[symbol],
            }

    quality_computer = SymbolAwareQualityComputer()
    service = batch_service_factory(tmp_path)
    service._quality_computer = quality_computer

    batch_id = "batch-restart-quality"
    btc_manifest = tmp_path / "BTCUSDT_manifest.json"
    eth_manifest = tmp_path / "ETHUSDT_manifest.json"
    btc_manifest.write_text("{}", encoding="utf-8")
    eth_manifest.write_text("{}", encoding="utf-8")

    service._tasks[batch_id] = {
        "task_id": batch_id,
        "status": "completed",
        "total": 2,
        "completed": 2,
        "failed": 0,
        "results": {
            "BTCUSDT": str(btc_manifest),
            "ETHUSDT": str(eth_manifest),
        },
        "errors": {},
    }

    before = await service.get_batch_quality_summary(batch_id)
    assert before is not None
    before_by_symbol = {item["symbol"]: item["grade"] for item in before["summaries"]}

    checkpoint = {
        "batch_id": batch_id,
        "completed_items": [
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "output_paths": [str(btc_manifest)],
            },
            {
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "output_paths": [str(eth_manifest)],
            },
        ],
        "failed_items": [],
        "queued_items": [],
    }
    service._safe_persist_checkpoint(checkpoint)
    service._tasks.clear()

    after = await service.get_batch_quality_summary(batch_id)
    assert after is not None
    assert after["total_symbols"] == before["total_symbols"]
    assert {item["symbol"] for item in after["summaries"]} == {"BTCUSDT", "ETHUSDT"}
    after_by_symbol = {item["symbol"]: item["grade"] for item in after["summaries"]}
    assert after_by_symbol == before_by_symbol == grade_by_symbol


@pytest.mark.asyncio
async def test_get_batch_quality_summary_returns_none_without_task_or_checkpoint(
    tmp_path,
    batch_service_factory,
):
    service = batch_service_factory(tmp_path)
    assert await service.get_batch_quality_summary("missing-batch-id") is None
