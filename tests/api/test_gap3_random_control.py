"""GAP-3 `G3-D2` D5.1／D5.3 驗收（`-k "random_control_roundtrip or random_control_compare"`）。

三件事：
1. **落檔 round-trip**（D5.1 wire 鏈 (c)(d)）：`random_control_spec` 送進去、逐鍵回得來。
2. **匯入 envelope e2e**（D5.3 R4 三家 P1-01）：`import_records(..., label_rule=)` 是觸發批
   規則身分之**唯一** wire；缺席即缺席，比較回 `identity_unverifiable`。
3. **規則身分閘四段**（D5.3 ①–④）：`compare_random_control` 之逐條 reason。

資料一律真實 kline；隨機批由 `sample_random_bars` 產出，不手搓。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis.event_samples.random_control import sample_random_bars
from tests.momentum.event_samples.helpers import load_bars
from tests.momentum.event_samples.test_import_contract import canonical_event

client = TestClient(app)

SYMBOL = "ETHUSDT"
TF = "12h"
HORIZON = 2
THRESHOLD = 0.02
compare = ICAnalysisService.compare_random_control


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


@pytest.fixture(scope="module")
def bars():
    return load_bars(SYMBOL, (TF,))


def _grid(bars):
    df = bars[SYMBOL][TF]
    return df["open_time_ms"].to_numpy(), df["close_time_ms"].to_numpy(), df["close"].to_numpy()


def _trigger_records(bars, idxs=(200, 400, 700), *, direction="long", mode="close_to_close"):
    """觸發批：真實 bar 網格上之事件，label 由**同一條規則**算出（可被閘重評）。"""
    ot, _, close = _grid(bars)
    sign = 1.0 if direction == "long" else -1.0
    out = []
    for n, i in enumerate(idxs):
        lv = float(sign * (close[i + HORIZON] / close[i] - 1.0))
        e = canonical_event(
            n, t0=int(ot[i]), symbol=SYMBOL, timeframe=TF, direction=direction,
            entry_price_semantic="trigger_close", label=int(lv >= THRESHOLD),
            label_definition={"rule_id": "trig", "canonical_digest": "c" * 64,
                              "window": {"horizon_bars": HORIZON}, "label_return_mode": mode},
        )
        e["label_value"] = lv
        out.append(e)
    return out


def _balanced(recs):
    """契約要求批內 label 同時有 0 與 1；不足時補一列相反 label 之真實事件。"""
    labels = {r["label"] for r in recs}
    return labels == {0, 1}


def _trigger_batch(bars, **kw):
    """挑出一組**同時含 0 與 1** 之真實事件（不改 label，改的是挑哪些 bar）。"""
    ot, _, close = _grid(bars)
    direction = kw.get("direction", "long")
    sign = 1.0 if direction == "long" else -1.0
    pos, neg = [], []
    for i in range(150, 900):
        lv = float(sign * (close[i + HORIZON] / close[i] - 1.0))
        (pos if lv >= THRESHOLD else neg).append(i)
        if len(pos) >= 2 and len(neg) >= 2:
            break
    idxs = tuple(sorted(pos[:2] + neg[:2]))
    recs = _trigger_records(bars, idxs, **kw)
    assert _balanced(recs), "fixture 應同時含正反例（契約之 missing_control_group）"
    return recs


def _spec(bars, *, seed=20260905, n_requested=20, threshold=THRESHOLD, horizon=HORIZON,
          direction="long"):
    ot, _, _ = _grid(bars)
    return {
        "universe": {"symbol": SYMBOL, "timeframe": TF,
                     "start_ms": int(ot[100]), "end_ms": int(ot[900])},
        "strata": {"symbol": SYMBOL, "timeframe": TF,
                   "period": {"start_ms": int(ot[100]), "end_ms": int(ot[900])},
                   "direction": direction},
        "allocation": "proportional_to_candidates",
        "exclusion": {"trigger_ids_digest": "", "neighborhood_bars": 2, "embargo_bars": 6},
        "label_rule": {"threshold": threshold, "horizon_bars": horizon},
        "seed": seed, "n_requested": n_requested, "replacement": False,
    }


def _random_batch(bars, trigger_recs, spec):
    ot, ct, _ = _grid(bars)
    t0s = {int(r["t0"]) for r in trigger_recs}
    idx = {int(t): i for i, t in enumerate(ot)}
    receipts = [
        {"event_id": r["event_id"], "symbol": SYMBOL, "timeframe": TF,
         "t0_ms": int(r["t0"]), "label_end_ms": int(ct[idx[int(r["t0"])] + HORIZON])}
        for r in trigger_recs
    ]
    assert len(t0s) == len(trigger_recs)
    return sample_random_bars(bars, spec, receipts, scenario="C")


# ══════════════════════════════════════════════════════════════════════════
# 1. 落檔 round-trip（D5.1 wire 鏈 (c)(d)）
# ══════════════════════════════════════════════════════════════════════════

def test_random_control_roundtrip_spec_survives_storage(bars, _isolated_storage):
    """(c)(d)：`random_control_spec` 經 `import_records` 落檔後，detail **逐鍵**回同值。"""
    trig = _trigger_batch(bars)
    recs, receipt = _random_batch(bars, trig, _spec(bars))
    assert recs, "應抽得到（否則本條為空迴圈假綠）"
    out = _isolated_storage.import_records(
        recs, source_name="rc", upload_bytes=None, validate_only=False,
        random_control_spec=receipt, carried_declaration_acknowledged=True)
    detail = _isolated_storage.get_import(out.import_id)
    assert detail.receipt_batch.random_control_spec == receipt
    assert detail.receipt_batch.label_rule is None, "隨機批本身不寫 batch.label_rule"
    # response_model 靜默濾欄之防護：走 HTTP 也要看得到同一份
    http = client.get(f"/api/v1/case/events/{out.import_id}").json()
    assert http["receipt_batch"]["random_control_spec"] == receipt


def test_random_control_roundtrip_rejects_bad_spec(bars, _isolated_storage):
    """typed schema 之葉錯誤 ⇒ 落檔 0（拒收在寫檔之前）。"""
    trig = _trigger_batch(bars)
    recs, receipt = _random_batch(bars, trig, _spec(bars))
    bad = {**receipt, "seed": "not-an-int"}
    with pytest.raises(svc_mod.EventImportRejectedError) as ei:
        _isolated_storage.import_records(
            recs, source_name="rc", upload_bytes=None, validate_only=False,
            random_control_spec=bad, carried_declaration_acknowledged=True)
    fields = {f.field for f in ei.value.payload.failures}
    assert "batch.random_control_spec.seed" in fields
    assert _isolated_storage.list_imports().total == 0


# ══════════════════════════════════════════════════════════════════════════
# 2. 匯入 envelope e2e（觸發批之規則身分唯一 wire）
# ══════════════════════════════════════════════════════════════════════════

def test_random_control_compare_envelope_label_rule_roundtrip(bars, _isolated_storage):
    """(ii-c)：`import_records(..., label_rule=)` 落檔後 detail 回同值；`None` ⇒ `None`。"""
    trig = _trigger_batch(bars)
    rule = {"threshold": THRESHOLD, "horizon_bars": HORIZON}
    with_rule = _isolated_storage.import_records(
        trig, source_name="t", upload_bytes=None, validate_only=False, label_rule=rule)
    d1 = _isolated_storage.get_import(with_rule.import_id)
    assert d1.receipt_batch.label_rule.threshold == THRESHOLD
    assert d1.receipt_batch.label_rule.horizon_bars == HORIZON

    without = _isolated_storage.import_records(
        _trigger_batch(bars), source_name="t2", upload_bytes=None, validate_only=False)
    d2 = _isolated_storage.get_import(without.import_id)
    assert d2.receipt_batch.label_rule is None


def test_random_control_compare_envelope_rejects_bad_label_rule(bars, _isolated_storage):
    with pytest.raises(svc_mod.EventImportRejectedError) as ei:
        _isolated_storage.import_records(
            _trigger_batch(bars), source_name="t", upload_bytes=None, validate_only=False,
            label_rule={"threshold": "x", "horizon_bars": HORIZON})
    assert "batch.label_rule.threshold" in {f.field for f in ei.value.payload.failures}
    assert _isolated_storage.list_imports().total == 0


#  🔴 `generate_events` 之 provenance `label_rule`（單規則填／多規則 None）之驗收
#     住 `tests/momentum/event_samples/test_generator_adapters.py`（真的呼叫產生器），
#     不在此以 `inspect.getsource` 掃字串——那是 `B1-WEAKTEST-1` 的同型病。


# ══════════════════════════════════════════════════════════════════════════
# 3. 規則身分閘四段（D5.3 ①–④）
# ══════════════════════════════════════════════════════════════════════════

def _pair(bars, svc, *, trigger_rule, spec_kw=None, trigger_kw=None):
    """建一組（觸發批 detail, 隨機批 detail）。`trigger_rule=None` ⇒ 不寫 label_rule。"""
    trig = _trigger_batch(bars, **(trigger_kw or {}))
    t = svc.import_records(trig, source_name="t", upload_bytes=None, validate_only=False,
                           label_rule=trigger_rule)
    recs, receipt = _random_batch(bars, trig, _spec(bars, **(spec_kw or {})))
    r = svc.import_records(recs, source_name="rc", upload_bytes=None, validate_only=False,
                           random_control_spec=receipt, carried_declaration_acknowledged=True)
    return svc.get_import(t.import_id), svc.get_import(r.import_id)


def test_random_control_compare_i_identity_unverifiable(bars, _isolated_storage):
    """① 觸發批無 `label_rule` ⇒ `random_control_rule_identity_unverifiable`。"""
    t, r = _pair(bars, _isolated_storage, trigger_rule=None)
    v = compare(t, r)
    assert v.status == "unavailable"
    assert v.reason == "random_control_rule_identity_unverifiable"
    assert v.trigger_prevalence is None and v.random_prevalence is None


def test_random_control_compare_ii_leaf_mismatch(bars, _isolated_storage):
    """② 任一葉不等 ⇒ `random_control_rule_mismatch`。"""
    # 🔴 門檻只差一級（0.02 vs 0.01）而非極端值：極端門檻會讓隨機批變成單類別，
    #    被契約之 `missing_control_group` 先擋掉，本條就測不到規則身分閘
    #    （該單類別行為之殘留＝`B5-SINGLECLASS-1`，見 registry）。
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON},
                 spec_kw={"threshold": 0.01})
    v = compare(t, r)
    assert v.status == "unavailable" and v.reason == "random_control_rule_mismatch"
    assert "label_rule" in (v.message or "")


def test_random_control_compare_ii_direction_mismatch(bars, _isolated_storage):
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON},
                 spec_kw={"direction": "short"})
    v = compare(t, r)
    assert v.status == "unavailable" and v.reason == "random_control_rule_mismatch"
    assert "direction" in (v.message or "")


def test_random_control_compare_iib_trigger_mode_not_close_to_close(bars, _isolated_storage):
    """(ii-b) 觸發批 `label_return_mode=open_to_horizon_close` ⇒ mismatch。"""
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON},
                 trigger_kw={"mode": "open_to_horizon_close"})
    v = compare(t, r)
    assert v.status == "unavailable" and v.reason == "random_control_rule_mismatch"
    assert "label_return_mode" in (v.message or "")


def test_random_control_compare_iii_ok_and_prevalences(bars, _isolated_storage):
    """③ 相等且重評一致率 1.0 ⇒ 比較成立並回兩 prevalence。"""
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    v = compare(t, r)
    assert v.status == "ok", v.message
    assert v.reason is None
    assert 0.0 <= v.trigger_prevalence <= 1.0
    assert 0.0 <= v.random_prevalence <= 1.0
    assert v.n_trigger == 4 and v.n_random > 0
    assert v.sample_design == "unconditional_random"
    assert v.n_requested == 20 and v.n_drawn == v.n_random


def test_random_control_compare_iv_mutation_flipped_label_breaks_it(bars, _isolated_storage):
    """④ mutation：翻轉觸發批任一列 label ⇒ ③ 轉 `random_control_rule_mismatch`。

    🔴 這條是 ③ 的**可證偽對照**：沒有它，③ 對「重評根本沒跑」這種壞法也會綠。
    """
    trig = _trigger_batch(bars)
    trig[0]["label"] = 1 - int(trig[0]["label"])
    if {r["label"] for r in trig} != {0, 1}:          # 翻轉後仍須雙類別（契約要求）
        trig[1]["label"] = 1 - int(trig[1]["label"])
    t = _isolated_storage.import_records(
        trig, source_name="t", upload_bytes=None, validate_only=False,
        label_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    recs, receipt = _random_batch(bars, trig, _spec(bars))
    r = _isolated_storage.import_records(
        recs, source_name="rc", upload_bytes=None, validate_only=False,
        random_control_spec=receipt, carried_declaration_acknowledged=True)
    v = compare(_isolated_storage.get_import(t.import_id), _isolated_storage.get_import(r.import_id))
    assert v.status == "unavailable" and v.reason == "random_control_rule_mismatch"
    assert "一致率" in (v.message or "")


def test_random_control_compare_v_prevalence_missing(bars, _isolated_storage):
    """⑤ 缺 prevalence ⇒ `random_control_prevalence_missing`（隨機批空）。"""
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    r.records.clear()
    v = compare(t, r)
    assert v.status == "unavailable" and v.reason == "random_control_prevalence_missing"


def test_random_control_compare_missing_label_value_still_verifiable(bars, _isolated_storage):
    """🔴 **本條之期望在 R1 閉合後反轉**（`COMPOSER-R1-P1-02`）。

    舊版閘③拿 `label_value` 當 signed return ⇒ 缺它就無從重評，故回
    `identity_unverifiable`。新版**回 bar 表重算** ⇒ `label_value` 只是**額外**的
    一致性對照（有才比），缺它不影響重評能力。
    🔴 這不是放寬：真正的判準（落檔 `label` 是否等於 bar 表重算值）**一條都沒少**，
    而且新增了「`label_value` 若存在也必須等於 bar 表重算值」這條原本不存在的檢查
    （見 `test_random_control_gate3_reads_bar_table_not_label_value`）。
    """
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    for rec in t.records:
        rec.pop("label_value", None)
    assert compare(t, r).status == "ok"


def test_random_control_compare_missing_label_is_unverifiable(bars, _isolated_storage):
    """缺 `label`（不是 `label_value`）⇒ 無從比對 ⇒ `identity_unverifiable`（不以缺值當通過）。"""
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    t.records[0].pop("label", None)
    v = compare(t, r)
    assert v.status == "unavailable"
    assert v.reason == "random_control_rule_identity_unverifiable"


def test_random_control_compare_t0_off_grid_is_unverifiable(bars, _isolated_storage):
    """t0 不在 bar 網格上 ⇒ 無法重評 ⇒ 具名不可對證（**不以算不出來當一致**）。"""
    t, r = _pair(bars, _isolated_storage,
                 trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    t.records[0]["t0"] = int(t.records[0]["t0"]) + 1        # 偏一毫秒即不在網格上
    v = compare(t, r)
    assert v.status == "unavailable"
    assert v.reason == "random_control_rule_identity_unverifiable"


def test_random_control_compare_owner_does_not_import_case_service():
    """解耦 Rule 4：`compare_random_control` 之 owner 不得 import case service。"""
    import ast
    import inspect
    import textwrap

    # 🔴 以 **AST** 判定，不用 grep：本方法之 docstring 就寫著「不 import case_import_service」
    #    ——字串比對會打到那句說明，變成「寫對反而紅」的反向假綠。
    tree = ast.parse(textwrap.dedent(inspect.getsource(ICAnalysisService.compare_random_control)))
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    modules |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("case_import" in m for m in modules), modules
    assert modules, "正向對照：本方法確實有 import（否則上一條可能是空集合恆真）"


# ══════════════════════════════════════════════════════════════════════════
# 4. 端點 e2e
# ══════════════════════════════════════════════════════════════════════════

def test_random_control_roundtrip_endpoint_e2e(bars, _isolated_storage):
    """`POST /case/import-events/random-control`：依觸發批產一批、落檔、detail 回抽樣契約。"""
    trig = _trigger_batch(bars)
    t = client.post("/api/v1/case/import-events/json",
                    json={"records": trig, "source_name": "t"})
    assert t.status_code == 200, t.text
    trigger_id = t.json()["import_id"]

    spec = _spec(bars)
    for k in ("n_drawn", "candidate_count", "per_stratum", "sample_ids_digest",
              "data_snapshot_digest", "generator_version"):
        assert k not in spec, "端點只收輸入鍵；收據鍵由產生器填回"
    r = client.post("/api/v1/case/import-events/random-control",
                    json={"event_import_id": trigger_id, "random_control_spec": spec})
    assert r.status_code == 200, r.text
    rid = r.json()["import_id"]

    detail = client.get(f"/api/v1/case/events/{rid}").json()
    got = detail["receipt_batch"]["random_control_spec"]
    assert got["n_drawn"] == r.json()["n_valid"] > 0
    assert got["generator_version"] and got["sample_ids_digest"]
    assert {rec["control_kind"] for rec in detail["records"]} == {"platform_random_bars"}
    assert detail["batch_facts"]["label_origin"] == "platform_random"


def test_random_control_endpoint_404_for_unknown_trigger(bars, _isolated_storage):
    r = client.post("/api/v1/case/import-events/random-control",
                    json={"event_import_id": "no-such-batch", "random_control_spec": _spec(bars)})
    assert r.status_code == 404


def test_random_control_endpoint_period_mismatch_is_422(bars, _isolated_storage):
    trig = _trigger_batch(bars)
    t = client.post("/api/v1/case/import-events/json", json={"records": trig, "source_name": "t"})
    trigger_id = t.json()["import_id"]
    ot, _, _ = _grid(bars)
    spec = _spec(bars)
    spec["strata"]["period"] = {"start_ms": int(ot[1200]), "end_ms": int(ot[1400])}
    r = client.post("/api/v1/case/import-events/random-control",
                    json={"event_import_id": trigger_id, "random_control_spec": spec})
    assert r.status_code == 422, r.text
    body = r.text
    assert "random_control_period_mismatch" in body


# ══════════════════════════════════════════════════════════════════════════
# 5. R1 閉合：接線、輸入邊界、閘③讀 bar 表、單獨分析
# ══════════════════════════════════════════════════════════════════════════

def test_random_control_compare_endpoint_is_wired(bars, _isolated_storage):
    """🔴 R1 三家獨立命中之閉合：`compare_random_control` 有**產品面取用路徑**。

    原本它只有 service 靜態方法、`api/routes` 與 `frontend/src` 零呼叫
    ⇒ 閘在測面綠、使用者拿不到結論（與 B-D4「WS 不回填揭露欄」同型）。
    """
    trig = _trigger_batch(bars)
    t = client.post("/api/v1/case/import-events/json", json={"records": trig, "source_name": "t"})
    trigger_id = t.json()["import_id"]
    r = client.post("/api/v1/case/import-events/random-control",
                    json={"event_import_id": trigger_id, "random_control_spec": _spec(bars)})
    assert r.status_code == 200, r.text
    random_id = r.json()["import_id"]

    c = client.post("/api/v1/case/events/compare-random-control",
                    json={"trigger_import_id": trigger_id, "random_import_id": random_id})
    assert c.status_code == 200, c.text
    body = c.json()
    # 這批以 JSON 端點匯入 ⇒ 無 `receipt.batch.label_rule` ⇒ 閘① 具名不可對證
    assert body["status"] == "unavailable"
    assert body["reason"] == "random_control_rule_identity_unverifiable"
    assert body["trigger_prevalence"] is None and body["random_prevalence"] is None
    assert body["sample_design"] == "unconditional_random"


def test_random_control_compare_endpoint_404_and_ok_path(bars, _isolated_storage):
    """不存在之 id ⇒ 404；帶規則身分之批 ⇒ `ok` 且回兩 prevalence。"""
    r = client.post("/api/v1/case/events/compare-random-control",
                    json={"trigger_import_id": "nope", "random_import_id": "nope2"})
    assert r.status_code == 404

    t, rand = _pair(bars, _isolated_storage,
                    trigger_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    c = client.post("/api/v1/case/events/compare-random-control",
                    json={"trigger_import_id": t.summary.import_id,
                          "random_import_id": rand.summary.import_id})
    assert c.status_code == 200, c.text
    body = c.json()
    assert body["status"] == "ok", body["message"]
    assert 0.0 <= body["trigger_prevalence"] <= 1.0
    assert 0.0 <= body["random_prevalence"] <= 1.0


def test_random_control_standalone_ic_analysis_sample_design(bars, _isolated_storage):
    """🔴 D5.3 邊界④：隨機批**單獨**分析時須揭露 `sample_design='unconditional_random'`
    （`COMPOSER-R1-P2-01`／`GROK-R1-P2-01`：原本該字面只活在未被呼叫的 `CompareVerdict`）。

    以 `_sample_design_of` 之行為驗——它是分析揭露之唯一導出點，值由 `control_kind`
    機械導出、不由使用者宣告。
    """
    trig = _trigger_batch(bars)
    recs, receipt = _random_batch(bars, trig, _spec(bars))
    rand = _isolated_storage.import_records(
        recs, source_name="rc", upload_bytes=None, validate_only=False,
        random_control_spec=receipt, carried_declaration_acknowledged=True)
    rand_detail = _isolated_storage.get_import(rand.import_id)

    assert ICAnalysisService._sample_design_of(rand_detail.records) == "unconditional_random"
    # 正向對照：觸發批必須是 case_control（否則上一行對任何批都成立）
    assert ICAnalysisService._sample_design_of(trig) == "case_control"
    # 分析階段真的把它帶出來（欄名固定，前端據此顯示）
    import inspect

    src = inspect.getsource(ICAnalysisService._run_event_label_stages)
    assert "event_sample_design" in src


def test_random_control_gate3_reads_bar_table_not_label_value(bars, _isolated_storage):
    """🔴 `COMPOSER-R1-P1-02` 之閉合：閘③以**真實 bar 表**重算，不信任 `label_value`。

    反例（composer 逐字給的）：某列 `label_value` 與 `label` **內部自洽**
    （0.03 ≥ 0.02 ⇒ 1），但真實 bar 報酬完全不同 ⇒ 舊版閘③會回 `ok`、
    prevalence 與隨機批不可比，且沒有任何東西會報錯。
    """
    trig = _trigger_batch(bars)
    t = _isolated_storage.import_records(
        trig, source_name="t", upload_bytes=None, validate_only=False,
        label_rule={"threshold": THRESHOLD, "horizon_bars": HORIZON})
    recs, receipt = _random_batch(bars, trig, _spec(bars))
    rand = _isolated_storage.import_records(
        recs, source_name="rc", upload_bytes=None, validate_only=False,
        random_control_spec=receipt, carried_declaration_acknowledged=True)
    t_detail = _isolated_storage.get_import(t.import_id)
    rand_detail = _isolated_storage.get_import(rand.import_id)

    # 未竄改 ⇒ ok（正向對照）
    assert compare(t_detail, rand_detail).status == "ok"

    # 竄改：把某列之 label_value 改成「與 label 自洽但與 bar 表不符」的值
    victim = next(r for r in t_detail.records if int(r["label"]) == 1)
    # 與 `label=1` 內部自洽（≥ threshold），但遠離真實 bar 報酬 ⇒ 舊版會放行、新版須擋
    victim["label_value"] = float(THRESHOLD) + 0.5
    v = compare(t_detail, rand_detail)
    assert v.status == "unavailable" and v.reason == "random_control_rule_mismatch", v.message


@pytest.mark.parametrize(
    ("field", "value"),
    [("n_requested", 1.5), ("n_requested", True), ("n_requested", -1), ("seed", 1.0)],
    ids=["float_n", "bool_n", "negative_n", "float_seed"],
)
def test_random_control_endpoint_rejects_non_exact_int(bars, _isolated_storage, field, value):
    """🔴 `CODEX-R1-P1-02` 之閉合：非 exact `int`／負值 ⇒ **4xx**，不得靜默 coerce 或 500。

    原本 `int(1.5)==1`、`int(True)==1` 會讓**合法 JSON 請求得到與請求不同的 receipt**，
    而 `n_requested=-1` 會丟未被 route 捕捉的 `RuntimeError`（→500）。
    """
    trig = _trigger_batch(bars)
    t = client.post("/api/v1/case/import-events/json", json={"records": trig, "source_name": "t"})
    trigger_id = t.json()["import_id"]
    spec = _spec(bars)
    spec[field] = value
    r = client.post("/api/v1/case/import-events/random-control",
                    json={"event_import_id": trigger_id, "random_control_spec": spec})
    assert 400 <= r.status_code < 500, f"應為 4xx，實得 {r.status_code}: {r.text[:200]}"
    assert r.status_code != 500


def test_random_control_sample_design_fails_closed_on_mixed_kind():
    """🔴 `CODEX-R2-P2-01` 之閉合：混到 `platform_random_bars` 之批 ⇒ **raise**，
    不靜默回 `case_control`。

    原式「不是全隨機就當 case_control」依賴的是**別處**的不變式（validator 的混批拒收）。
    那條哪天被放寬，抽樣設計就會被靜默標錯——而症狀是「IC 數字看起來很正常、解讀完全相反」。
    """
    mixed = [{"control_kind": "platform_random_bars"}, {"control_kind": "user_labeled_same_trigger"}]
    with pytest.raises(ValueError) as ei:
        ICAnalysisService._sample_design_of(mixed)
    assert "platform_random_bars" in str(ei.value)
    # 兩個正向對照（否則上面對任何輸入都成立）
    assert ICAnalysisService._sample_design_of(
        [{"control_kind": "platform_random_bars"}] * 2) == "unconditional_random"
    assert ICAnalysisService._sample_design_of(
        [{"control_kind": "user_labeled_same_trigger"}] * 2) == "case_control"
