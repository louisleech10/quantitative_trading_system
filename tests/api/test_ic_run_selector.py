"""IC Run Selector golden / 消歧整合測試。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from api.models.ic_models import ICAnalyzeRequest
from api.services.cross_symbol_training_service import CrossSymbolTrainingService
from api.services.ic_analysis_service import ICAnalysisService
from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
# TESTREG Task 4.4：原釘本機兩套競爭 12h run（`e53e2290…`／`f754aad4…`，2026-10-03 已刪 ⇒ 恆 skip）
# ＋凍結基準 `tests/fixtures/ic_run_selector_baseline.json`（數字綁舊 run）。改由共用外掛
# `tests/fixtures/tmp_feature_runs_plugin.py` 以真實 K 線於 tmp 物化兩套競爭 run：
# 設定 A（L3 rolling 5／13）與 B（L3 rolling 5），同 symbol＋tf、同日期窗 ⇒ 列數同、特徵集不同；
# 物化順序 A（BTC/ETH/BCH）→ B（BTC/ETH）⇒ BTC／ETH 12h 之 latest 為 B。期望值由生成當下之
# 時間軸與落盤 raw 檔之欄名**獨立導出**（不經被測之 `library.load`／registry 選擇）。
RUN_A, RUN_B = "btc_12h_a", "btc_12h_b"
#: ML caller（跨標的訓練）之 load_multi 參數（原取自凍結基準之 `ml_caller_load_multi.load_multi_kwargs`）
LOAD_MULTI_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
LOAD_MULTI_LATEST = {"BTCUSDT": "btc_12h_b", "ETHUSDT": "eth_12h_b"}
LOAD_MULTI_ALLOW_PARTIAL = True
UNREGISTERED_HASH = "11111111111111111111111111111111"
ORPHAN_HASHES = (
    "4d26a4d46e8f53d9a443a1d65f93f831",
    "5218729ca187e1df263143e649bc5349",
)
MINI_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "ic_run_selector_mini_registry.json"
)


def _feature_sha256(columns: list[str]) -> str:
    payload = "|".join(sorted(columns)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _raw_feature_columns(run) -> list[str]:
    """獨立 oracle：run 之 raw parquet 落盤欄名（只讀 schema，不經 `library.load`）。"""
    import pyarrow.parquet as pq

    names: list[str] = []
    for p in sorted((run.run_dir / "raw").glob("*.parquet")):
        names.extend(n for n in pq.read_schema(p).names if not n.startswith("__index_level"))
    return names


@pytest.fixture
def pinned_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Hermetic mini registry — 不受 live orphan run 漂移影響。"""
    registry_copy = tmp_path / "registry.json"
    registry_copy.write_text(MINI_REGISTRY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_copy))
    return registry_copy


@pytest.fixture
def selector_runs(tmp_feature_run_env) -> Dict[str, Any]:
    """tmp 物化之 12h 競爭 run 組（registry 為本測試之 tmp 複本，hermetic）。"""
    runs = tmp_feature_run_env.activate("btc_12h_a", "btc_12h_b", "eth_12h_a", "eth_12h_b", "bch_12h_a")
    library = create_feature_library()
    for name in (RUN_A, RUN_B):
        entry = library._registry.get(SYMBOL, TIMEFRAME, runs[name].config_hash)
        # 前提（原為缺 run 即 skip；現由 fixture 保證，不成立即紅）
        assert entry is not None and library._registry.is_materialized(entry), f"前提不成立：{name} 未登記或未物化"
    return runs


def _capture_run_metrics(config_hash: Optional[str]) -> Dict[str, Any]:
    library = create_feature_library()
    if config_hash:
        resolved = config_hash
    else:
        entry = library._registry.find_latest_materialized(SYMBOL, TIMEFRAME)
        assert entry is not None
        resolved = str(entry["config_hash"])

    entry = library._registry.get(SYMBOL, TIMEFRAME, resolved)
    assert entry is not None
    df = library.load(SYMBOL, TIMEFRAME, config_hash=resolved)
    return {
        "selected_config_hash": resolved,
        "run_identity": {
            "symbol": entry["symbol"],
            "timeframe": entry["timeframe"],
            "config_hash": entry["config_hash"],
            "path": entry["hdf5_relative_path"],
        },
        "feature_sha256": _feature_sha256([str(c) for c in df.columns]),
        "row_count": len(df),
    }


@pytest.mark.ic_run_selector
@pytest.mark.disambig
def test_disambig_same_tf_different_hash(selector_runs: Dict[str, Any]) -> None:
    hash_a, hash_b = selector_runs[RUN_A].config_hash, selector_runs[RUN_B].config_hash
    result_a = _capture_run_metrics(hash_a)
    result_b = _capture_run_metrics(hash_b)
    assert result_a["run_identity"]["config_hash"] == hash_a
    assert result_b["run_identity"]["config_hash"] == hash_b
    assert result_a["feature_sha256"] != result_b["feature_sha256"]
    assert result_a["row_count"] == result_b["row_count"]
    # 逐 run 對獨立 oracle（落盤欄名／生成當下時間軸）：消歧須真的載到「該」run
    for name, got in ((RUN_A, result_a), (RUN_B, result_b)):
        assert got["feature_sha256"] == _feature_sha256(_raw_feature_columns(selector_runs[name])), name
        assert got["row_count"] == len(selector_runs[name].index_s), name


@pytest.mark.ic_run_selector
@pytest.mark.backward_compat
def test_backward_compat_matches_baseline(selector_runs: Dict[str, Any]) -> None:
    """未帶 config_hash ⇒ 選 latest（＝最後生成之 B），身分／特徵集／列數逐項對獨立導出之期望。"""
    run_b = selector_runs[RUN_B]
    expected = {
        "selected_config_hash": run_b.config_hash,
        "feature_sha256": _feature_sha256(_raw_feature_columns(run_b)),
        "row_count": len(run_b.index_s),
    }
    actual = _capture_run_metrics(None)
    for key in ("selected_config_hash", "feature_sha256", "row_count"):
        assert actual[key] == expected[key], f"diff {key}: {actual[key]} != {expected[key]}"
    assert actual["run_identity"] == {
        "symbol": SYMBOL, "timeframe": TIMEFRAME, "config_hash": run_b.config_hash,
        "path": actual["run_identity"]["path"],
    }
    assert Path(actual["run_identity"]["path"]).resolve() == run_b.manifest_path.resolve(), (
        "registry 之 run 路徑未指向 latest run 之 manifest"
    )


@pytest.mark.ic_run_selector
@pytest.mark.asyncio
async def test_ml_caller_load_multi_kwargs_match_baseline(selector_runs: Dict[str, Any]) -> None:
    service = CrossSymbolTrainingService()
    captured: Dict[str, Any] = {}
    original_load_multi = service._feature_library.load_multi

    def spy_load_multi(*args: Any, **kwargs: Any) -> Any:
        captured["args"] = args
        captured["kwargs"] = dict(kwargs)
        return original_load_multi(*args, **kwargs)

    service._feature_library.load_multi = spy_load_multi  # type: ignore[method-assign]

    symbols = list(LOAD_MULTI_SYMBOLS)
    timeframe = TIMEFRAME
    allow_partial = LOAD_MULTI_ALLOW_PARTIAL

    with patch.object(service._validator, "run_leave_one_symbol_out", return_value={}):
        try:
            await service.run_cross_symbol_validation(
                symbols=symbols,
                timeframe=timeframe,
                allow_partial_training=allow_partial,
            )
        except ValueError as exc:
            if "label" not in str(exc).lower():
                raise

    kwargs = captured.get("kwargs", {})
    assert kwargs.get("for_training") is True
    assert kwargs.get("allow_partial_training") == allow_partial
    assert kwargs.get("config_hashes") is None
    assert "feature_columns" in kwargs

    frames = original_load_multi(
        symbols,
        timeframe,
        for_training=True,
        allow_partial_training=allow_partial,
    )
    # 期望列數＝各標的 latest run 生成當下之時間軸長（獨立導出；原取自凍結基準之 per_symbol_row_count）
    for symbol, run_name in LOAD_MULTI_LATEST.items():
        assert len(frames[symbol]) == len(selector_runs[run_name].index_s)


@pytest.mark.ic_run_selector
def test_live_registry_skips_orphan_latest() -> None:
    """Live-registry canary：readable-latest 不得選 orphan（空 path / 缺 manifest）。"""
    library = create_feature_library()
    entry = library._registry.find_latest_materialized(SYMBOL, TIMEFRAME)
    # canary 只在 live registry 真有已物化的 12h run 時有意義；乾淨 checkout 無 12h 資料時誠實 skip。
    if entry is None:
        pytest.skip(f"no materialized {SYMBOL}/{TIMEFRAME} run in live registry")
    selected = str(entry.get("config_hash") or "")
    assert selected not in ORPHAN_HASHES
    assert library._registry.is_materialized(entry)


async def _drive_to_terminal(
    service: ICAnalysisService, request: ICAnalyzeRequest, timeout_seconds: int = 30
) -> Dict[str, Any]:
    """啟動 IC 任務並輪詢至 completed/failed，回傳終態 status。"""
    started = await service.start_analysis(request)
    task_id = started["task_id"]
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = service.get_task_status(task_id)
        if status and status.get("status") in ("completed", "failed"):
            return status
        await asyncio.sleep(0.05)
    raise TimeoutError(f"task did not terminate: {task_id}")


@pytest.mark.ic_run_selector
def test_failclosed_registry_miss_without_features_path(pinned_registry: Path) -> None:
    """契約(hermetic)：config_hash 未註冊 + 無 features_path → fail-closed(run not found)，
    不靜默回退挑別的 run。此路徑在載入資料前即 raise，故不需真實 12h 特徵——即使 gitignored
    資料缺席也能守住 run-selector 的核心保證(彌補 skip-guard 在乾淨 checkout 略過的覆蓋)。"""
    service = ICAnalysisService()
    request = ICAnalyzeRequest(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        config_hash=UNREGISTERED_HASH,
        mode="longitudinal",
    )
    status = asyncio.run(_drive_to_terminal(service, request))
    assert status["status"] == "failed"
    assert "run not found" in str(status.get("error", ""))


@pytest.mark.ic_run_selector
def test_relaxed_explicit_features_path_passes_through(
    pinned_registry: Path, tmp_path: Path
) -> None:
    """契約(hermetic)：config_hash 未註冊但呼叫端明確給 features_path(+meta_path/labels_path)
    → 不因未註冊而擋，analyzer 收到該 exact features_path。stub analyzer 不跑真分析、不觸真實資料，
    直接驗證放寬後的路由行為(mutation:若守衛仍硬擋，此測會轉 failed 而非 completed)。"""
    captured: Dict[str, Any] = {}

    class _FakeAnalyzer:
        def analyze(self, **kwargs: Any) -> Dict[str, Any]:
            captured.update(kwargs)
            return {"metadata": {}, "features": {}}

    features_path = str(tmp_path / "explicit_top50.h5")
    meta_path = str(tmp_path / "explicit_meta.json")
    with patch(
        "api.services.ic_analysis_service.create_ic_analyzer",
        return_value=_FakeAnalyzer(),
    ):
        service = ICAnalysisService()
        request = ICAnalyzeRequest(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            config_hash=UNREGISTERED_HASH,
            features_path=features_path,
            meta_path=meta_path,
            labels_path=str(tmp_path / "labels.h5"),
            mode="longitudinal",
        )
        status = asyncio.run(_drive_to_terminal(service, request))

    assert status["status"] == "completed", status.get("error")
    assert captured.get("features_path") == features_path


@pytest.mark.ic_run_selector
def test_service_sees_runs_registered_after_startup(pinned_registry: Path) -> None:
    """UAT 2026-09-09：後端啟動後才用 Feature Factory 生成的 run，IC 一律回「run not found」——
    service 之 registry 為啟動時快照。修法＝解析 run 前 `reload_registry()`；本測試在 service 建立**之後**
    才把 run 寫進 registry 檔，斷言不再是 run not found（會走到載入資料而以別的理由失敗，但錯誤字串不得含 run not found）。"""
    service = ICAnalysisService()  # 此時 registry 快照不含 LATE_HASH
    late_hash = "22222222222222222222222222222222"
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    writer = FeatureRegistry(path=pinned_registry)
    writer.add({"symbol": SYMBOL, "timeframe": TIMEFRAME, "config_hash": late_hash, "run_status": "complete",
                "features_path": str(pinned_registry.parent / "missing_late.h5"), "feature_count": 1})
    assert FeatureRegistry(path=pinned_registry).get(SYMBOL, TIMEFRAME, late_hash) is not None, "registry 檔須已含新 run"
    request = ICAnalyzeRequest(symbol=SYMBOL, timeframe=TIMEFRAME, config_hash=late_hash, mode="longitudinal")
    status = asyncio.run(_drive_to_terminal(service, request))
    assert "run not found" not in str(status.get("error", "")), status.get("error")
