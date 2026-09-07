"""UAT B23 閉合：`label_rule` 之路由 wire。"""
from __future__ import annotations

import pytest

from api.models.event_import_models import EventImportJsonRequest


def test_json_import_request_accepts_label_rule():
    """模型收得下 `label_rule`，缺席仍合法（人工標註批通常沒有）。"""
    r = EventImportJsonRequest(records=[], label_rule={"threshold": 0.07, "horizon_bars": 5})
    assert r.label_rule.model_dump() == {"threshold": 0.07, "horizon_bars": 5}
    assert EventImportJsonRequest(records=[]).label_rule is None


@pytest.mark.asyncio
async def test_route_actually_forwards_label_rule(monkeypatch):
    """🔴 **行為測試**：路由必須真的把 `label_rule` 傳進 service。

    出生事故（UAT B23，2026-09-07）：`import_records` 早就有 `label_rule=` 參數，
    但 `api/routes/case.py` 裡 `label_rule` 出現 **0 次** ⇒ 沒有任何路由傳它。
    畫面卻叫使用者「重新匯入該批時以 label_rule 帶入規則」——那條路不存在。
    本 epic 第四個「兩端都有、中間沒接上」。

    掃字串擋不住這種病（service 有、model 有、就是沒接），所以這裡驗**實際傳進去的 kwargs**。
    """
    from api.routes import case as case_route

    seen: dict = {}

    class _Svc:
        def import_records(self, records, **kwargs):
            seen.update(kwargs)
            return {"accepted": True, "n_rows": 0, "n_valid": 0}

    monkeypatch.setattr(case_route, "get_event_import_service", lambda: _Svc())

    req = EventImportJsonRequest(records=[], label_rule={"threshold": 0.07, "horizon_bars": 5})
    await case_route.import_events_json(req)
    assert seen.get("label_rule") == {"threshold": 0.07, "horizon_bars": 5}, (
        "路由沒把 label_rule 傳進 service —— 隨機對照組永遠無法並排 prevalence"
    )

    # 缺席 ⇒ 傳 None（不是不傳、也不是捏一個假的）
    seen.clear()
    await case_route.import_events_json(EventImportJsonRequest(records=[]))
    assert "label_rule" in seen and seen["label_rule"] is None


# ══════════════════════════════════════════════════════════════════════════
# 檔案端點（UI 實際走的那一支）
# ══════════════════════════════════════════════════════════════════════════


def test_envelope_reader_takes_structured_rule_only():
    """🔴 只認結構化 `label_rule`，**不認** `_label_rule`。

    出生事故（UAT B23 第二輪，2026-09-07）：使用者說「匯入裡面都有 label_rule 啊」——
    他看到的是樣本檔的 `_label_rule`，那是**散文說明**
    （「label = 1 若 close[t0+3根] > close[t0]」），與 `_readme` 同屬底線註解欄。
    把它當規則身分讀進來，等於拿一段人類文字冒充可逐葉比對的 tuple。
    """
    import json as _j

    from api.routes.case import _envelope_label_rule

    prose_only = _j.dumps({
        "_label_rule": "label = 1 若 close[t0 + 3 根] > close[t0]",
        "records": [],
    }).encode("utf-8")
    assert _envelope_label_rule(prose_only) is None, "散文說明被誤當成規則身分"

    structured = _j.dumps({
        "_label_rule": "同上（散文）",
        "label_rule": {"threshold": 0.0, "horizon_bars": 3},
        "records": [],
    }).encode("utf-8")
    assert _envelope_label_rule(structured) == {"threshold": 0.0, "horizon_bars": 3}

    # CSV／壞 JSON ⇒ None（解析錯誤不是本函式的事）
    assert _envelope_label_rule(b"event_id,symbol\n1,ETHUSDT\n") is None
    assert _envelope_label_rule(b"{not json") is None
    # 型別不合 ⇒ None（不猜、不轉型）
    assert _envelope_label_rule(_j.dumps({"label_rule": "0.0/3"}).encode()) is None


def test_uat_sample_carries_structured_label_rule():
    """UAT 樣本必須真的能拿來驗 B23——否則使用者照文件做也做不到。"""
    import json as _j
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    payload = _j.loads((repo / "uat_samples" / "events_ok.json").read_text(encoding="utf-8"))
    rule = payload.get("label_rule")
    assert isinstance(rule, dict), "樣本檔沒有結構化 label_rule，B23 無從驗起"
    assert isinstance(rule["threshold"], float) and isinstance(rule["horizon_bars"], int)
