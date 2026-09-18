"""SPLITUNIFY `Task 10.4`：分析用標籤參數之單一解析入口（`R5-C10` 1.–2.）。

驗的是什麼：事件掃描端與 IC 端**共用同一支**解析器，對同一批算出同一組四鍵。
下沉前兩端各有一份預設導出，答案窗與決策根因此不同、切分邊界差一整個週期。

🔴 本檔之 fixture 為**契約形狀**（records 之欄與批次 receipt），不是特徵數值，
故不需真實 K 線；涉及真實數值之對證在 `test_splitunify_canonical_holdout.py`。
"""
from __future__ import annotations

import pytest

from momentum.factories import create_event_label_spec_resolver, create_event_sample_pipeline

_K_DOMAIN = {"min": 0, "max": None}


def _resolver():
    return create_event_label_spec_resolver()


def _recs(n=2, *, tf="12h", k=0, declared=None):
    rows = []
    for i in range(n):
        r = {"event_id": f"e{i}", "symbol": "ETHUSDT", "timeframe": tf}
        if k is not None:
            r["decision_offset_bars"] = k
        if declared is not None:
            r["lookahead_bars_declared"] = declared
        rows.append(r)
    return rows


def test_event_label_spec_absent_matches_ic() -> None:
    """請求未給 spec ⇒ 依**批次宣告深度**導出四鍵；恆為恰四鍵。

    鑑別力：把深度來源改回「逐列 `label_definition.window.horizon_bars`」即給出不同 h。
    """
    resolve, _err = _resolver()
    out = resolve(
        _recs(), requested_spec=None,
        declared_receipt={"lookahead_bars_declared": {"12h": 13}},
        k_domain=_K_DOMAIN, batch_label="b1",
    )
    assert set(out.spec) == {
        "entry_price_semantic", "label_return_mode", "horizon_bars", "decision_offset_bars",
    }, f"spec 須恰四鍵，實得 {sorted(out.spec)}"
    assert out.spec["label_return_mode"] == "open_to_horizon_close"
    assert out.spec["horizon_bars"] == 13, "h 之初始值須等於宣告深度"
    assert out.spec["decision_offset_bars"] == 0, "k 之初始值＝契約 min，不取自該批宣告"
    assert out.lookahead_bars_declared == {"12h": 13}


def test_event_label_spec_k1_h6_matches_ic() -> None:
    """請求**明給**之鍵一律優先，解析器只補沒給的。"""
    resolve, _err = _resolver()
    out = resolve(
        _recs(), requested_spec={"decision_offset_bars": 1, "horizon_bars": 6},
        declared_receipt={"lookahead_bars_declared": {"12h": 13}},
        k_domain=_K_DOMAIN, batch_label="b1",
    )
    assert out.spec["decision_offset_bars"] == 1, "明給之 k 被覆寫"
    assert out.spec["horizon_bars"] == 6, "明給之 h 被覆寫"
    assert out.spec["label_return_mode"] == "open_to_horizon_close", "未給者仍依深度導出"


def test_depth_zero_gives_same_bar_mode() -> None:
    """深度 0 ⇒「當根」；`horizon_bars` 仍送 1（inert 哨兵，恆四鍵）。"""
    resolve, _err = _resolver()
    out = resolve(
        _recs(), requested_spec=None,
        declared_receipt={"lookahead_bars_declared": {"12h": 0}},
        k_domain=_K_DOMAIN, batch_label="b1",
    )
    assert out.spec["label_return_mode"] == "open_to_close"
    assert out.spec["horizon_bars"] == 1
    assert "當根" in out.seed_note


def test_mixed_timeframe_batch_does_not_guess_depth() -> None:
    """🔴 `Task 10.4` 邊界⑥：混週期批**不自動選深度**，回「當根」並在說明中揭露。

    各 tf 之「一根」長度不同，取任一個都是猜；猜錯會讓答案窗整批錯。
    """
    resolve, _err = _resolver()
    recs = _recs(1, tf="12h") + _recs(1, tf="1h")
    out = resolve(
        recs, requested_spec=None,
        declared_receipt={"lookahead_bars_declared": {"12h": 13, "1h": 156}},
        k_domain=_K_DOMAIN, batch_label="b1",
    )
    assert out.mixed_timeframe is True
    assert out.spec["label_return_mode"] == "open_to_close", "混週期批不得依任一 tf 之深度選持有"
    assert "混合 timeframe" in out.seed_note and "未自動依深度選擇" in out.seed_note


def test_resolver_out_of_domain_k_maps_to_422_same_kind() -> None:
    """🔴 `Task 10.4` 邊界⑦：`decision_offset_bars` 值域外 ⇒ 具名例外，`kind` 字面不變。

    `kind` 是契約：route 依它映射 422 之 `detail.kind`，前端與既有測試釘住該字面。
    """
    resolve, err_cls = _resolver()
    with pytest.raises(err_cls) as ei:
        resolve(
            _recs(k=-1), requested_spec=None,
            declared_receipt={"lookahead_bars_declared": {"12h": 13}},
            k_domain=_K_DOMAIN, batch_label="b1",
        )
    assert ei.value.kind == "invalid_decision_offset_bars", (
        f"kind 字面改變會破壞 route 之 422 契約：{ei.value.kind}"
    )


def test_bool_is_type_error_not_k_one() -> None:
    """`True` 是 `int` 之子型別且會被當成 1 ⇒ 一律視為型別錯，不是 k=1。"""
    resolve, err_cls = _resolver()
    with pytest.raises(err_cls) as ei:
        resolve(
            _recs(k=True), requested_spec=None,
            declared_receipt={"lookahead_bars_declared": {"12h": 13}},
            k_domain=_K_DOMAIN, batch_label="b1",
        )
    assert ei.value.kind == "invalid_decision_offset_bars"


def test_missing_declaration_is_fail_closed() -> None:
    """批次 receipt 與逐列欄皆缺深度宣告 ⇒ 具名拒絕（purge 下界無從導出）。"""
    resolve, err_cls = _resolver()
    with pytest.raises(err_cls) as ei:
        resolve(_recs(), requested_spec=None, declared_receipt=None,
                k_domain=_K_DOMAIN, batch_label="b1")
    assert ei.value.kind == "missing_lookahead_declaration"


def test_row_level_declaration_is_fallback_not_primary() -> None:
    """深度之權威是**批次 receipt**；逐列欄只是退路。

    🔴 只讀 `records[0]` 對真實批次會拿到 `{}` 而使分析根本跑不完（B-D1 R2 實跑命中）。
    """
    resolve, _err = _resolver()
    out = resolve(
        _recs(declared={"12h": 7}), requested_spec=None,
        declared_receipt={"lookahead_bars_declared": {"12h": 13}},
        k_domain=_K_DOMAIN, batch_label="b1",
    )
    assert out.spec["horizon_bars"] == 13, "批次 receipt 應優先於逐列欄"
    out2 = resolve(
        _recs(declared={"12h": 7}), requested_spec=None, declared_receipt={},
        k_domain=_K_DOMAIN, batch_label="b1",
    )
    assert out2.spec["horizon_bars"] == 7, "receipt 缺時才退回逐列欄"


def test_k_domain_comes_from_contract_not_hardcoded() -> None:
    """值域由契約導出——手刻永遠補不完，因為值域是資料、不是程式碼。

    本條同時釘住「pipeline 之契約出口確實提供該欄之 min」。
    """
    domain = create_event_sample_pipeline().int_field_domain("decision_offset_bars")
    assert "min" in domain, f"契約出口未提供 min：{domain}"
    assert domain["min"] is not None and int(domain["min"]) >= 0


def test_empty_records_is_named_error() -> None:
    """空批 ⇒ 具名 `empty_event_batch`（route 映 422，字面不變）。"""
    resolve, err_cls = _resolver()
    with pytest.raises(err_cls) as ei:
        resolve([], requested_spec=None,
                declared_receipt={"lookahead_bars_declared": {"12h": 13}},
                k_domain=_K_DOMAIN, batch_label="b1")
    assert ei.value.kind == "empty_event_batch"
