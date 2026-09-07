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
