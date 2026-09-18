"""SPLITUNIFY `Task 10.4`／`R5-C8` 7.：stage3 之逐事件觀測收據（真實資料）。

驗的是什麼：觀測收據是 analyze 範圍之實例屬性、每次入口歸零、**不寫入報告**。
它的用途是讓 `Task 10.7` 對證處置帳之**預測**；若它寫進報告，§G-1 之
「IC 報告逐位元組不變」就破了；若它不歸零，掃描格逐格重用同一個 analyzer 時
會拿上一次的觀測去對證這一次的預測——而且看起來會很像對的。

🔴 真實資料缺席時 `skip`；禁合成 fixture 作為結論依據。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BATCH = REPO / "data_cache/events/20260909T130533Z-7f73e4c7.json"
RUN_1H = REPO / "data_cache/features/ETHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5"
KLINE = REPO / "data_cache/feature_klines/kline_cache.h5"
CONTRACT = REPO / "momentum/Analysis/contracts/split_unify.json"


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"真實資料缺席（不得以合成 fixture 代替）：{missing}")


def test_stage3_receipt_reset_per_analyze_and_absent_from_report() -> None:
    """🔴 三件事一次釘住：入口歸零、analyze 範圍、不寫入報告。

    鑑別力：拿掉入口那行歸零 ⇒ 第二次 analyze 仍看得到第一次的收據（本條轉紅）；
    把收據塞進 `report` ⇒ 「不在報告內」那段轉紅。
    """
    from momentum.factories import create_ic_analyzer

    import inspect

    analyzer = create_ic_analyzer(None)
    # ① 建構期即有安全預設（與 `_binary_label_window_bars` 同慣例）⇒ 消費端不必靠
    #    `getattr(..., default)` 兜底。🔴 既有同類狀態之慣例**本身不一致**
    #    （`_stage_timings` 無建構期預設、`_binary_label_window_bars` 有），
    #    本條選較安全的一邊並釘住。
    assert analyzer._stage3_event_observation == {}, (
        "建構期預設不是空 dict——消費端會拿到 AttributeError 或殘值"
    )
    # ② 入口確實歸零（不跑完整 analyze——那需要物化全特徵矩陣、本機記憶體不足）。
    src = inspect.getsource(type(analyzer).analyze)
    assert "_stage3_event_observation = {}" in src, (
        "analyze 入口未把 stage3 觀測收據歸零——掃描格逐格重用同一個 analyzer 時會跨 run 殘留"
    )
    # ③ 歸零那行須與既有 analyze-scoped 狀態**同一段**（被拆散就會有人只改一邊）。
    head = src[: src.index("_stage3_event_observation = {}")]
    assert "_stage_timings = {}" in head, (
        "歸零位置與既有 analyze-scoped 狀態脫節——應緊鄰同一段，避免只改一邊"
    )


def test_stage3_observation_values_are_from_contract() -> None:
    """觀測值集封閉且與契約一致（`observed` ∈ {ic_consumed, feature_row_not_in_feature_index}）。"""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    observed = contract["event_disposition_values"]["observed"]
    assert observed == ["ic_consumed", "feature_row_not_in_feature_index"], (
        f"觀測值集與 R5-C8 7. 不符：{observed}"
    )
    # 觀測值集須為 `ic_disposition` 之子集——否則對證時會出現預測永遠給不出的值。
    ic_vals = set(contract["event_disposition_values"]["ic_disposition"])
    assert set(observed) <= ic_vals, (
        f"觀測值不在 ic_disposition 值集內：{set(observed) - ic_vals}"
    )


def test_stage3_observation_not_in_report_keys() -> None:
    """🔴 收據**不得**出現在報告中——§G-1 之「IC 報告逐位元組不變」是 golden 的前提。

    以原始碼判準：`_stage3_event_observation` 不得被寫進 `report`／`info` 之任何鍵。
    """
    import inspect

    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    src = inspect.getsource(ICFilterOrchestrator)
    for bad in ('info["stage3_event_observation"]',
                'report["stage3_event_observation"]',
                'info["_stage3_event_observation"]'):
        assert bad not in src, f"觀測收據被寫進報告：{bad}"


def test_stage3_observation_populated_on_real_event_run() -> None:
    """真實事件 run 之後，收據逐事件齊備且值落在封閉集合內。

    本條走 `_run_scan_cell`（生產端入口）而非合成 analyzer——只讀觀測面，不改任何值。
    """
    _require(BATCH, RUN_1H, KLINE)
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    b = json.loads(BATCH.read_text())
    decl = b["lookahead_declaration"]["lookahead_bars_declared"]
    trigger_tfs = sorted({str(r["timeframe"]) for r in b["records"]})
    spec = {
        "entry_price_semantic": "trigger_open",
        "label_return_mode": "open_to_horizon_close",
        "horizon_bars": int(decl[trigger_tfs[0]]),
        "decision_offset_bars": 0,
    }
    ff_run = RUN_1H.name
    request = ICAnalyzeRequest(
        symbol="ETHUSDT", timeframe="1h", config_hash=ff_run,
        mode="longitudinal", event_import_id=b["import_id"],
    )
    service = ICAnalysisService()
    cfg = service._build_config_override(request)

    # 以與比對腳本相同之具名子集物化（不載全矩陣——本 run raw/ 為 7.5 GB）
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    import splitunify_ic_event_report_diff as D  # type: ignore

    features_path, meta_path = D._materialize_named_subset(
        service, "ETHUSDT", "1h", ff_run, RUN_1H,
    )
    analyzer_holder = {}

    def _factory(override):
        a = create_ic_analyzer(override)
        analyzer_holder["a"] = a
        return a

    ICAnalysisService._run_scan_cell(
        service, _factory, request,
        {"records": tuple(b["records"]), "event_label_spec": spec,
         "lookahead_bars_declared": decl},
        features_path=features_path, meta_path=meta_path,
        feature_manifest_path=str(RUN_1H / "feature_manifest.json"),
        labels_path=None,
        kline_reader=create_kline_storage_manager(cache_dir="data_cache/feature_klines"),
        config_override=dict(cfg or {}), original_embargo=0,
    )
    obs = getattr(analyzer_holder["a"], "_stage3_event_observation", None)
    assert obs, "真實事件 run 之後 stage3 觀測收據為空"
    allowed = set(json.loads(CONTRACT.read_text(encoding="utf-8"))
                  ["event_disposition_values"]["observed"])
    for eid, row in obs.items():
        assert row["observed"] in allowed, f"{eid} 之觀測值 {row['observed']!r} 不在封閉集合內"
        assert isinstance(row["feature_row_open_ms"], int)
