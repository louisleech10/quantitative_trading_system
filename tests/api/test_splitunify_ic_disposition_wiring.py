"""SPLITUNIFY `R5-C8`／`CODEX-R45-P1-02`：IC 主路徑之**處置帳接線**（真實資料）。

驗的是什麼：`ICAnalysisService._run_event_label_stages`（IC 事件分析之五階段編排，
`_run_scan_cell` 與 `/analyze` 主流程都走它）確實**產生**逐事件處置帳，而不是只在
`momentum` 留一個沒人呼叫的入口。

🔴 為什麼要有這一條：`Task 10.4` 之交付若只有 momentum 端的單元測試，
「入口存在」與「生產端真的用它」是兩件事——後者沒有任何東西擋，
下一票很容易在不知情的情況下把接線改掉而全綠。

鑑別力（改壞須轉紅）：
  ① 拿掉 staged 之 `event_disposition_ledger` 鍵 ⇒ 第一條 assert 紅。
  ② 把 `post_trim_index_ms` 餵成空集合 ⇒ 每筆都變 `feature_row_not_in_feature_index`，
     `ic_consumed` 筆數歸零 ⇒ 第四條 assert 紅。
  ③ 只把**被消費**的事件送進帳（漏掉被剔除者）⇒ 覆蓋率那條 assert 紅。

🔴 真實資料缺席時 `skip`；禁合成 fixture 作為結論依據。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / "data_cache/events/20260909T130533Z-7f73e4c7.json"
RUN_1H = REPO / "data_cache/features/ETHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5"
KLINE = REPO / "data_cache/feature_klines/kline_cache.h5"
CONTRACT = REPO / "momentum/Analysis/contracts/split_unify.json"


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"真實資料缺席（不得以合成 fixture 代替）：{missing}")


def _staged():
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService

    b = json.loads(BATCH.read_text(encoding="utf-8"))
    decl = b["lookahead_declaration"]["lookahead_bars_declared"]
    trigger_tfs = sorted({str(r["timeframe"]) for r in b["records"]})
    request = ICAnalyzeRequest(
        symbol="ETHUSDT", timeframe="1h", config_hash=RUN_1H.name,
        mode="longitudinal", event_import_id=b["import_id"],
    )
    event_batch = {
        "records": tuple(b["records"]),
        "event_label_spec": {
            "entry_price_semantic": "trigger_open",
            "label_return_mode": "open_to_horizon_close",
            "horizon_bars": int(decl[trigger_tfs[0]]),
            "decision_offset_bars": 0,
        },
        "lookahead_bars_declared": decl,
    }
    # 🔴 不物化特徵矩陣：本階段只做對齊／coverage／特徵列鍵／label，
    #    `feature_manifest_path` 已足以定位 run 目錄與 post-trim 索引。
    return b, ICAnalysisService._run_event_label_stages(
        request, event_batch,
        features_path=None, meta_path=None,
        feature_manifest_path=str(RUN_1H / "feature_manifest.json"),
    )


def test_ic_main_path_emits_event_disposition_ledger() -> None:
    """IC 主路徑之 staged 產物含處置帳，且逐筆值落在契約之封閉集合內。"""
    _require(BATCH, RUN_1H, KLINE)
    batch, staged = _staged()

    ledger = staged.get("event_disposition_ledger")
    assert ledger, (
        "IC 主路徑沒有產生處置帳——`R5-C8` 之入口存在但無生產呼叫端，本 Task 不可驗"
    )

    values = json.loads(CONTRACT.read_text(encoding="utf-8"))["event_disposition_values"]
    scan_vals, ic_vals = set(values["scan_disposition"]), set(values["ic_disposition"])
    for row in ledger:
        assert row["scan_disposition"] in scan_vals, f"{row['event_id']}：{row['scan_disposition']!r}"
        assert row["ic_disposition"] in ic_vals, f"{row['event_id']}：{row['ic_disposition']!r}"

    # 🔴 **全批覆蓋**：帳要記的是「每一筆事件怎麼了」，只記活下來的那些就只是換個名字的消費清單。
    assert {r["event_id"] for r in ledger} == {str(r["event_id"]) for r in batch["records"]}, (
        "處置帳未覆蓋全批事件——被剔除者才是這份帳存在的理由"
    )

    consumed = [r for r in ledger if r["ic_disposition"] == values["observed"]["consumed"]]
    assert consumed, (
        "處置帳沒有任何 `ic_consumed`——post-trim 索引若餵成空集合會正好長這樣"
    )
    assert len(consumed) == len(staged["event_label_values"]), (
        f"預測之 consumed（{len(consumed)}）與實際餵進 IC 之列數"
        f"（{len(staged['event_label_values'])}）不符"
    )
