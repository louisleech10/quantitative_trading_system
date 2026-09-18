"""SPLITUNIFY `Task 10.4`／`R5-C10`：IC route 之標籤參數解析**只走共用出口**（真實資料）。

驗的是什麼：`api/routes/ic_analysis.py` 的 `_resolve_event_batch` 不得自己再算一份
值域檢查／深度讀取／預設導出——那份「第二實作」正是兩端對同一批算出不同答案窗的根因。
本條以 `momentum.factories` 出口之 spy 釘住：**恰被呼叫一次**，且 route 產出之四鍵
與 spy 觀察到之解析結果同源。

🔴 為什麼是「恰一次」而不是「至少一次」：route 若在錯誤分支或 retry 路徑重算一次，
兩次的輸入可能不同（例如第二次少了 `declared_receipt`）而最後一次贏——這種重算
在「至少一次」下完全看不出來。

鑑別力（改壞須轉紅）：
  ① route 改回自己內聯解析（不呼叫出口）⇒ `calls == 1` 轉紅（變 0）。
  ② route 在同一次請求內重算一次 ⇒ `calls == 1` 轉紅（變 2）。

🔴 真實資料缺席時 `skip`；禁合成 fixture 作為結論依據。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / "data_cache/events/20260909T130533Z-7f73e4c7.json"


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"真實資料缺席（不得以合成 fixture 代替）：{missing}")


def test_ic_route_calls_shared_resolver_once(monkeypatch) -> None:
    """factories 出口之 spy 被呼叫恰一次，且 route 的四鍵取自它的回傳。"""
    _require(BATCH)
    import momentum.factories as F
    from api.models.ic_models import ICAnalyzeRequest
    from api.routes.ic_analysis import _resolve_event_batch

    batch_id = json.loads(BATCH.read_text(encoding="utf-8"))["import_id"]
    real = F.create_event_label_spec_resolver
    calls = {"n": 0, "resolved": None}

    def _spy():
        resolve, err_cls = real()

        def _wrapped(*args, **kwargs):
            calls["n"] += 1
            calls["resolved"] = resolve(*args, **kwargs)
            return calls["resolved"]

        return _wrapped, err_cls

    # 🔴 route 於函式內 lazy import ⇒ 打在 `momentum.factories` 這個模組屬性上才攔得到。
    monkeypatch.setattr(F, "create_event_label_spec_resolver", _spy)

    request = ICAnalyzeRequest(
        symbol="ETHUSDT", timeframe="1h",
        config_hash="4a8a0b3726cc906ab3534994605e77f5",
        mode="longitudinal", event_import_id=batch_id,
    )
    batch = _resolve_event_batch(request)

    assert calls["n"] == 1, (
        f"共用解析出口被呼叫 {calls['n']} 次（應恰一次）"
        "——0 次代表 route 又自己算了一份；>1 次代表同一請求內重算，最後一次的輸入可能不同"
    )
    assert batch is not None and batch.get("event_label_spec"), "route 未帶出標籤參數"
    spec = batch["event_label_spec"]
    resolved_spec = calls["resolved"].spec
    assert set(resolved_spec) == {
        "entry_price_semantic", "label_return_mode", "horizon_bars", "decision_offset_bars",
    }, f"共用出口之 spec 不是恰四鍵：{sorted(resolved_spec)}"
    assert spec == resolved_spec, (
        f"route 之標籤參數與共用出口之解析結果不同源：{spec!r} vs {resolved_spec!r}"
    )
