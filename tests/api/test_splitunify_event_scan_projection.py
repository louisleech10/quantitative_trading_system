"""SPLITUNIFY `Task 10.5`（B10D）：事件掃描端接線（真實資料）。

驗的是什麼：帶 `feature_run` 的事件掃描請求，**與 IC 端走同一條 canonical 邊界**——
同一批事件在兩端得到同一個測試段。下沉前掃描端根本不碰 FF run（恆 `event-study-only`），
所以「兩端數字不一致」這件事以前不可能被發現；現在它是一條可證偽的斷言。

🔴 **本檔一律用真實資料**（`data_cache/events/`、`data_cache/features/`、
`data_cache/feature_klines/kline_cache.h5`）；禁合成 fixture（CLAUDE.md 資料真實性鐵律）。
資料缺席時 `skip`。

🔴 **route 層與 service 層都要驗**：`EventAnalyzeResponse` 以 `response_model` 序列化，
未宣告之頂層鍵會被 pydantic **靜默丟棄**——service 端算得再對，經 HTTP 出去可能就是沒有。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

REPO = Path(__file__).resolve().parents[2]
BATCH_FILE = REPO / "data_cache/events/20260909T130533Z-7f73e4c7.json"
RUN_1H = REPO / "data_cache/features/ETHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5"
RUN_12H = REPO / "data_cache/features/ETHUSDT/12h/e53e22906c35363757f4cd49d27f973e"
KLINE = REPO / "data_cache/feature_klines/kline_cache.h5"

SYM, TF, FF_RUN = "ETHUSDT", "1h", "4a8a0b3726cc906ab3534994605e77f5"
FEATURE_RUN = {"symbol": SYM, "timeframe": TF, "config_hash": FF_RUN}

# 🔴 **短 run**：post-trim 索引較窄，本批恰有 1 筆事件之錨點落在其外
#    ⇒ 這是邊界③「批內 1 筆界外 ⇒ 成功並揭露」唯一能在真實資料上觸發的組合。
#    預設長 run 上兩個剔除計數皆為 0，用它寫的揭露測試攔不住任何東西。
FF_RUN_SHORT = "5ea074390e98405cb83d602fe7b7fb00"
RUN_1H_SHORT = REPO / f"data_cache/features/ETHUSDT/1h/{FF_RUN_SHORT}"

# 🔴 **真實混 symbol 批**（BTCUSDT＋ETHUSDT）：`excluded_by_symbol` 唯一能非空之來源。
MULTI_BATCH_FILE = REPO / "data_cache/events/20260902T124358Z-ef2c6cd1.json"

# 🔴 **能產生「部分」coverage 剔除之真實組合**（實掃全部批×run 後取得）：
#    本批 × 短 run ⇒ `dropped_by_coverage` 非零。沒有它，「兩份剔除清單互斥」
#    那條守衛在所有測試下都碰不到（空集合交集恆為空），mutation 會存活。
COV_BATCH_FILE = REPO / "data_cache/events/20260906T105851Z-8cc44eea.json"

client = TestClient(app)


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"真實資料缺席（不得以合成 fixture 代替）：{missing}")


def _batch_id() -> str:
    return json.loads(BATCH_FILE.read_text(encoding="utf-8"))["import_id"]


def test_required_real_data_present_or_fail_closed() -> None:
    """🔴 `CODEX-R2-P2-02`：本檔所依賴之真實資料缺席時**轉紅**，不是整批 skip。

    🔴 問題不是 `_require` 的 skip 本身（資料缺席時 skip 是對的，禁以合成 fixture
    代替），而是**只看 rc 分不出「17 passed」與「17 skipped」**——`COV_BATCH_FILE`
    一被刪，重疊守衛那條就靜默消失而 `pytest` 仍 rc=0。
    ⇒ 由本條單獨承擔 fail-closed：缺任一必需檔即紅，其餘各條維持 skip 語意。

    🔴 另釘**內容**而非只釘存在：批之 `import_id` 與事件筆數一併斷言，
    該批被重凍成另一份內容時本條轉紅，而不是讓下游測試在新內容上「剛好還是綠」。
    """
    required = {
        # (檔, import_id, records 身分指紋前 16 位)
        "BATCH_FILE": (BATCH_FILE, "20260909T130533Z-7f73e4c7", "2bc04164bc075807"),
        "MULTI_BATCH_FILE": (MULTI_BATCH_FILE, "20260902T124358Z-ef2c6cd1", "b99c7a74d76beb52"),
        "COV_BATCH_FILE": (COV_BATCH_FILE, "20260906T105851Z-8cc44eea", "5c5f9c9cfa9ec2c5"),
    }
    missing = [name for name, (p, _, _) in required.items() if not p.exists()]
    missing += [n for n, p in (("RUN_1H", RUN_1H), ("RUN_1H_SHORT", RUN_1H_SHORT),
                               ("KLINE", KLINE)) if not p.exists()]
    assert not missing, (
        f"本檔之驗收依賴下列真實資料，現已缺席：{missing}。"
        "缺席時其餘各條會 skip 而 pytest 仍 rc=0 ⇒ 守衛靜默消失，故在此 fail-closed。"
        "🔴 **不得**以合成 fixture 補齊（CLAUDE.md 資料真實性鐵律）。"
    )
    # 🔴 `CODEX-R3-P2-01`：只釘 `import_id` 與筆數**擋不住內容替換**——該家實跑把
    #    `records[0].event_id` 改成與 `records[1]` 相同後，兩欄皆未變而測試仍綠。
    #    ⇒ 改釘 **records 之 canonical fingerprint**（逐事件之身分三元組排序後雜湊）。
    #    只雜湊身分欄而非整份 payload：批之非身分欄（例落檔時間戳）本就可能變動，
    #    拿整檔 SHA 會變成每次重凍都要改測試的噪音閘。
    import hashlib

    for name, (path, want_id, want_fp) in required.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("import_id") == want_id, (
            f"{name} 之 import_id 已變（{payload.get('import_id')!r} ≠ {want_id!r}）"
        )
        recs = payload.get("records") or []
        triples = sorted(
            f"{r.get('symbol')}|{r.get('timeframe')}|{r.get('t0')}|{r.get('event_id')}"
            for r in recs
        )
        fp = hashlib.sha256("\n".join(triples).encode("utf-8")).hexdigest()[:16]
        assert fp == want_fp, (
            f"{name} 之 records 身分指紋已變（{fp} ≠ {want_fp}，{len(recs)} 筆）"
            "——下游之非零前提可能不再成立；確認資料變更屬意圖後再更新本指紋"
        )


def _multi_batch_id() -> str:
    return json.loads(MULTI_BATCH_FILE.read_text(encoding="utf-8"))["import_id"]


def _post(body: dict, *, expect: int = 200, batch_id: str = "") -> dict:
    r = client.post(f"/api/v1/case/events/{batch_id or _batch_id()}/analyze", json=body)
    assert r.status_code == expect, f"HTTP {r.status_code}: {r.text[:400]}"
    return r.json()


def _analyze_projection(**extra) -> dict:
    return _post({"horizons": [1], "feature_run": FEATURE_RUN, **extra})


# ── ① 無 feature_run ⇒ 回應形狀不變（含帶 event_label_spec 之變體）──────────────

@pytest.mark.parametrize("extra", [
    {},
    {"event_label_spec": {"horizon_bars": 6, "decision_offset_bars": 1}},
], ids=["no_spec", "with_spec"])
def test_analyze_without_feature_run_bytes_identical(extra) -> None:
    """🔴 邊界①：無 `feature_run` ⇒ 逐鍵同 v5；**帶 `event_label_spec` 亦同**。

    後者是本條的重點：`event_label_spec` 是本票新增的欄，若它在**沒有** `feature_run`
    的情況下改到任何輸出，就代表事件研究表不再是匯入原值——而使用者完全沒要求切分。
    鑑別力：讓無 `feature_run` 分支去讀 `event_label_spec` ⇒ 兩個變體的輸出不再相等，本條轉紅。
    """
    _require(BATCH_FILE, KLINE)
    base = _post({"horizons": [1]})
    got = _post({"horizons": [1], **extra})

    assert got["capability"]["split"] == "unavailable"
    assert got["summary"] == base["summary"], "帶 event_label_spec 改變了 summary"
    assert got["tables"] == base["tables"], "帶 event_label_spec 改變了表身"
    assert got["event_timestamps"] == base["event_timestamps"]
    # 四個新欄在此分支恆為 None（宣告了但不填），不得憑空生出切分揭露
    for key in ("split_unify", "period_alignment", "excluded_by_symbol"):
        assert got.get(key) is None, f"無 feature_run 卻有 {key}"


# ── ② 有 feature_run ⇒ capability=ok、三計數鍵、四個新欄 ────────────────────────

def test_analyze_with_feature_run_split_ok() -> None:
    """🔴 `R5-C3` 3.：投影成功 ⇒ `capability.split=ok`、三計數鍵與四個新欄皆在。

    鑑別力：把分派改回恆走 event-study-only ⇒ `capability` 與三計數鍵同時轉紅。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    out = _analyze_projection()

    assert out["capability"]["split"] == "ok", out["capability"]
    summary = out["summary"]
    for key in ("n_train", "n_test", "n_purged"):
        assert key in summary, f"投影分支缺計數鍵 {key}"
        assert isinstance(summary[key], int)
    assert summary["split"] is not None, "投影分支之 summary.split 不得為 None"
    assert out["split_unify"] and out["split_unify"]["n_test"] == summary["n_test"], (
        "split_unify.n_test 與 summary.n_test 不一致——兩份數字必須同源"
    )
    assert out["event_label_spec"] and set(out["event_label_spec"]["spec"]) == {
        "entry_price_semantic", "label_return_mode", "horizon_bars", "decision_offset_bars",
    }
    assert out["period_alignment"] is not None
    assert out["excluded_by_symbol"] is not None


def test_route_response_contains_four_new_keys() -> None:
    """🔴 四個新欄須**經 HTTP** 仍在（`R5-C3` 3.）。

    `EventAnalyzeResponse` 以 `response_model` 序列化，未宣告之頂層鍵 pydantic 會
    **靜默丟棄**。只驗 service 回傳不算數——那正是這條存在的理由。
    鑑別力：把任一欄自 `EventAnalyzeResponse` 拿掉 ⇒ 本條轉紅。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    out = _analyze_projection()
    for key in ("split_unify", "period_alignment", "excluded_by_symbol", "event_label_spec"):
        assert key in out and out[key] is not None, f"經 HTTP 後 {key} 不見了"


# ── ③ 與 IC 端逐值相等（本票的核心不變式）──────────────────────────────────────

def test_scan_projection_test_segment_matches_ic() -> None:
    """🔴 **本檔最重要**：掃描端之測試段與 IC 端**同一條邊界**。

    以同一批事件、同一個 FF run 分別走兩端，斷言 `n_test`（落在 canonical 測試段之
    事件數）逐值相等。下沉前掃描端恆無切分，這條斷言不可能存在；它是「兩套切分已合一」
    的唯一可證偽證據。
    鑑別力：讓掃描端改用自己的 `test_fraction` 切 ⇒ 兩邊數字立刻分家，本條轉紅。

    🔴 **IC 端之參數不得用猜的**：本條走 `ICAnalysisService._run_event_label_stages`
    取得 IC 端**實際**用的 `purge_rows`／`label_window_rows`／`lookahead_depth_rows`，
    再以同一組數字解析邊界。寫死一個 `purge_gap` 會讓本條變成「拿我猜的去比我算的」。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import (
        create_canonical_holdout_resolver, create_event_sample_pipeline, load_ic_config,
    )

    scan = _analyze_projection()

    # ── IC 端：以同一批、同一個 run 跑五階段，取其實際之隔離列數 ──
    batch = json.loads(BATCH_FILE.read_text(encoding="utf-8"))
    decl = batch["lookahead_declaration"]["lookahead_bars_declared"]
    trigger_tfs = sorted({str(r["timeframe"]) for r in batch["records"]})
    ic_req = ICAnalyzeRequest(
        symbol=SYM, timeframe=TF, config_hash=FF_RUN,
        mode="longitudinal", event_import_id=batch["import_id"],
    )
    staged = ICAnalysisService._run_event_label_stages(
        ic_req,
        {"records": tuple(batch["records"]),
         "event_label_spec": {
             "entry_price_semantic": "trigger_open",
             "label_return_mode": "open_to_horizon_close",
             "horizon_bars": int(decl[trigger_tfs[0]]),
             "decision_offset_bars": 0,
         },
         "lookahead_bars_declared": decl},
        features_path=None, meta_path=None,
        feature_manifest_path=str(RUN_1H / "feature_manifest.json"),
    )

    resolve_holdout, _ = create_canonical_holdout_resolver()
    holdout = resolve_holdout(
        ff_run=FF_RUN, symbol=SYM, ic_config=load_ic_config(),
        purge_gap=max(int(staged["purge_rows"]), int(staged["label_window_rows"])),
        lookahead_depth_rows=int(staged["lookahead_depth_rows"]),
    )
    assert holdout.reason is None, f"IC 端無邊界（{holdout.reason}）——本條前提不成立"

    ic_test_ms = [
        int(v) for v in (
            holdout.feature_index[list(holdout.test_plan.row_index)].astype("int64") // 1_000_000
        )
    ]
    ic_disclosure = create_event_sample_pipeline().split_unify_disclosure(
        n_test=int(scan["summary"]["n_test"]),
        test_timestamps_ms=ic_test_ms,
        per_symbol_counts={SYM: int(scan["summary"]["n_test"])},
    )
    assert scan["split_unify"]["boundary_hash"] == ic_disclosure["boundary_hash"], (
        "掃描端與 IC 端之 boundary_hash 不同——兩端沒有共用同一條邊界"
    )


def test_analyze_event_label_spec_k1_h6_matches_ic() -> None:
    """🔴 `R5-C10`：指定 `k=1, h=6` 時，掃描端解析出的四鍵與 IC 端逐值相等。

    兩端若各自補預設，同一份請求會得到不同的答案窗與決策根 ⇒ 邊界不可能相等。
    鑑別力：在掃描端自寫任一鍵的預設 ⇒ 本條轉紅。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    from momentum.factories import create_event_label_spec_resolver, create_event_sample_pipeline
    from api.services.case_import_service import get_event_import_service

    spec_req = {"decision_offset_bars": 1, "horizon_bars": 6}
    scan = _analyze_projection(event_label_spec=spec_req)

    svc = get_event_import_service()
    records = svc.get_import(_batch_id()).records
    resolve_spec, _ = create_event_label_spec_resolver()
    ic_resolved = resolve_spec(
        records, requested_spec=spec_req,
        declared_receipt=svc._stored_declaration(_batch_id()),
        k_domain=create_event_sample_pipeline().int_field_domain("decision_offset_bars"),
        batch_label=_batch_id(),
    )
    assert scan["event_label_spec"]["spec"] == dict(ic_resolved.spec), (
        f"掃描端解析結果與共用出口不同：{scan['event_label_spec']['spec']} vs {dict(ic_resolved.spec)}"
    )


def test_scan_calls_shared_resolver_once(monkeypatch) -> None:
    """🔴 共用解析出口被呼叫**恰一次**（不是至少一次）。

    重算一次時兩次輸入可能不同（例如第二次少了 `declared_receipt`）而最後一次贏，
    這種重算在「至少一次」下完全看不出來。
    鑑別力：掃描端自寫解析 ⇒ 計數變 0；同請求內重算 ⇒ 變 2。兩種都轉紅。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    import momentum.factories as F

    real = F.create_event_label_spec_resolver
    calls = {"n": 0}

    def _spy():
        resolve, err = real()

        def _wrapped(*a, **kw):
            calls["n"] += 1
            return resolve(*a, **kw)

        return _wrapped, err

    monkeypatch.setattr(F, "create_event_label_spec_resolver", _spy)
    _analyze_projection()
    assert calls["n"] == 1, f"共用解析出口被呼叫 {calls['n']} 次（應恰一次）"


# ── ④ fail-closed 與具名錯誤 ───────────────────────────────────────────────────

def test_analyze_unknown_config_hash_4xx() -> None:
    """🔴 `R5-C3` 4.：run 不存在 ⇒ 4xx 具名錯誤，**不得**改走 event-study-only 冒充成功。

    鑑別力：把該例外吞掉並回退 event-study-only ⇒ 本條由 422 變 200，轉紅。
    """
    _require(BATCH_FILE, KLINE)
    r = client.post(
        f"/api/v1/case/events/{_batch_id()}/analyze",
        json={"horizons": [1], "feature_run": {"symbol": SYM, "timeframe": TF,
                                               "config_hash": "0" * 32}},
    )
    assert r.status_code == 422, f"應為 422，實得 {r.status_code}: {r.text[:300]}"
    assert r.json()["detail"]["kind"] == "feature_run_not_found", r.json()["detail"]


def test_analyze_event_label_spec_out_of_domain_same_kind_as_ic(monkeypatch) -> None:
    """🔴 邊界⑥：`EventLabelSpecError` ⇒ 422 且 `kind` 取自**例外自帶欄位**，非 route 手打。

    🔴 **為什麼用 monkeypatch 讓 resolver 丟例外，而不是送一個值域外的 k**：實測
    `int_field_domain("decision_offset_bars")` 為 `{"min": 0, "max": None}`——k **沒有上界**，
    而負值早在 pydantic（`ge=0`）就被擋成 FastAPI 的 422，走不到本票新加的映射。
    真實批的 records 值皆合法，故無法由請求觸發該具名例外。硬湊一個「值域外」的輸入
    只會讓本條測到別的東西。

    🔴 本條守的是**實際存在的洞**：`EventLabelSpecError` 之基底是 `Exception`（不是
    `ValueError`），排在 `except ValueError` 之後就會漏成 **500**；而 `kind` 若在 route 手打，
    就成了第二份字面（`R5-C3` 4. 要求與 IC route 逐字相同）。
    鑑別力：把該 except 移到 `except ValueError` 之後 ⇒ 本條由 422 變 500，轉紅；
    把 `exc.kind` 改成寫死字串 ⇒ 下面的 `sentinel` 斷言轉紅。
    """
    _require(BATCH_FILE, KLINE)
    import momentum.factories as F

    real = F.create_event_label_spec_resolver
    _, err_cls = real()
    sentinel = "probe_only_kind_not_handtyped"

    def _raising():
        def _boom(*_a, **_kw):
            raise err_cls(sentinel, "探針：resolver 具名失敗")

        return _boom, err_cls

    monkeypatch.setattr(F, "create_event_label_spec_resolver", _raising)
    r = client.post(
        f"/api/v1/case/events/{_batch_id()}/analyze",
        json={"horizons": [1], "feature_run": FEATURE_RUN},
    )
    assert r.status_code == 422, (
        f"具名例外未被映射成 422（實得 {r.status_code}）"
        "——排在 except ValueError 之後就會漏成 500"
    )
    assert r.json()["detail"]["kind"] == sentinel, (
        f"kind 不是取自例外自帶欄位（實得 {r.json()['detail']['kind']!r}）——route 手打了第二份字面"
    )


def test_ic_route_and_scan_route_share_the_same_spec_error_kinds() -> None:
    """🔴 `R5-C3` 4.：兩端之 `kind` 字面同源——皆為 `EventLabelSpecError.kind`。

    以原始碼判準釘住：兩個 route 都必須把 `exc.kind` 放進 detail，任一端改成字面即紅。
    """
    import inspect

    from api.routes import case as case_route
    from api.routes import ic_analysis as ic_route

    for mod, name in ((case_route, "case"), (ic_route, "ic_analysis")):
        src = inspect.getsource(mod)
        assert '"kind": exc.kind' in src, (
            f"{name} route 未以 exc.kind 映射——手打字面會讓兩端分家"
        )


def test_analyze_multi_symbol_discloses_exclusion() -> None:
    """🔴 `R5-C4` 2.：他 symbol 之事件於投影前排除，且**揭露** symbol、事件數與 ID。

    🔴 **用真實混 symbol 批**（`COMPOSER-R1-P2-02`）：原本用全 ETHUSDT 批，
    `excluded_by_symbol` 恆為 `{}` ⇒ 把它整個改成 `{}` 測試仍綠（該家實跑證明）。
    「斷言沒寫錯，是用例沒把會觸發的資料放進來」——空集合上的全稱斷言恆真。
    鑑別力：靜默排除（payload 之 `excluded_by_symbol` 改 `{}`）⇒ 本條轉紅。
    """
    _require(MULTI_BATCH_FILE, RUN_1H, KLINE)
    out = _post({"horizons": [1], "feature_run": FEATURE_RUN}, batch_id=_multi_batch_id())
    ex = out["excluded_by_symbol"]
    assert ex, "混 symbol 批之 excluded_by_symbol 為空——他 symbol 被靜默排除"
    assert set(ex) == {"BTCUSDT"}, f"排除清單之 symbol 不如預期：{sorted(ex)}"
    for sym, slot in ex.items():
        assert sym != SYM, "run symbol 自己不該出現在排除清單"
        assert int(slot["count"]) == len(slot["event_ids"]) > 0, f"{sym} 之計數與 ID 數不符"
    # 被排除者不得出現在投影結果之事件集合內
    assert out["summary"]["n_test"] > 0


def test_analyze_one_event_out_of_range_discloses_event_id() -> None:
    """🔴 邊界③：批內 **1 筆** post-trim 界外 ⇒ **成功並揭露該 `event_id`**，不是 422。

    🔴 **用短 run**（`COMPOSER-R1-P2-02`）：預設長 run 上兩個剔除計數皆為 0，
    把兩份 ids 清單併成同一份、測試仍綠（該家實跑證明）。本條改打會真的剔掉
    一筆的 `RUN_1H_SHORT`，並斷言**恰含**該事件。
    鑑別力：投影改回餵匯入原 records ⇒ `derive_event_split_from_plans` 炸成
    422 `pipeline_rejected`，本條轉紅（這正是修補前的實際行為）。
    """
    _require(BATCH_FILE, RUN_1H_SHORT, KLINE)
    out = _post({"horizons": [1],
                 "feature_run": {"symbol": SYM, "timeframe": TF, "config_hash": FF_RUN_SHORT}})
    pa = out["period_alignment"]
    assert out["capability"]["split"] == "ok", "界外 1 筆應仍成功切分（邊界③）"
    outside = pa["dropped_outside_post_trim_index"]
    assert outside["count"] == 1 and len(outside["ids"]) == 1, (
        f"post-trim 界外揭露不是恰 1 筆：{outside}"
    )
    lo, hi = pa["post_trim_index_bounds_ms"]
    assert isinstance(lo, int) and isinstance(hi, int) and lo < hi
    # 🔴 兩份清單**必須互斥**：`apply_event_coverage` 不動 `windows`，row-key 若取自
    #    全量窗，coverage 已剔除者會被再記一次界外（`CODEX-R1-P1-02` 實跑 21/21 同一組）。
    assert not (set(pa["dropped_by_coverage"]["ids"]) & set(outside["ids"])), (
        "coverage 與 post-trim 兩份剔除清單重疊——同一事件被記了兩次"
    )
    for key in ("dropped_by_coverage", "dropped_outside_post_trim_index"):
        assert int(pa[key]["count"]) == len(pa[key]["ids"]), f"{key} 之計數與 ID 數不符"


def test_coverage_and_post_trim_drop_lists_are_disjoint() -> None:
    """🔴 `CODEX-R1-P1-02`：coverage 與 post-trim 兩份剔除清單**互斥**，且各自具名。

    🔴 **本條必須用會產生非零 coverage 剔除之真實組合**：`apply_event_coverage`
    只改 `allowed_event_ids`、**不動 `windows`**，而 `feature_row_keys` 迭代全量窗
    ⇒ 若不先以 coverage 存活集合過濾，已被 coverage 剔除者會被**再記一次**界外，
    兩份清單出現同一批 ID（提出方實跑 21/21 同一組）。
    在 `dropped_by_coverage` 為 0 的批上，本斷言之交集恆為空 ⇒ 守衛沒被執行到，
    把過濾拿掉 mutation 也會存活（主委實跑證明）。

    鑑別力：把 row-key 之 `if str(k) in allowed` 過濾拿掉 ⇒ 本條轉紅。
    """
    _require(COV_BATCH_FILE, RUN_1H_SHORT, KLINE)
    batch_id = json.loads(COV_BATCH_FILE.read_text(encoding="utf-8"))["import_id"]
    out = _post({"horizons": [1],
                 "feature_run": {"symbol": SYM, "timeframe": TF, "config_hash": FF_RUN_SHORT}},
                batch_id=batch_id)
    pa = out["period_alignment"]
    cov_ids = set(pa["dropped_by_coverage"]["ids"])
    out_ids = set(pa["dropped_outside_post_trim_index"]["ids"])
    assert cov_ids, "本條前提不成立：該組合未產生任何 coverage 剔除，守衛碰不到"
    assert not (cov_ids & out_ids), (
        f"兩份剔除清單重疊 {len(cov_ids & out_ids)} 筆——已被 coverage 剔除者被再記一次界外"
    )
    for key in ("dropped_by_coverage", "dropped_outside_post_trim_index"):
        assert int(pa[key]["count"]) == len(pa[key]["ids"]), f"{key} 之計數與 ID 數不符"


@pytest.mark.parametrize("batch_key,ff", [
    ("BATCH", FF_RUN_SHORT),        # post-trim 剔 1 筆
    ("MULTI", FF_RUN),              # 他 symbol 排除 66 筆
    ("COV", FF_RUN_SHORT),          # 對齊失敗 12 ＋ coverage 22 ＋ 他 symbol 75
], ids=["post_trim", "multi_symbol", "partial_coverage"])
def test_every_input_event_falls_in_exactly_one_partition(batch_key, ff) -> None:
    """🔴 `CODEX-R3-P1-01`：**每個輸入事件恰落一個具名分區**，無人憑空消失。

    提出方實跑抓到 12 個 `event_id` 既不在三個剔除清單、也不在 `align_failures`，
    而服務仍回 HTTP 200。根因是 `prepare_analysis_windows` 內部把 `align_events`
    的失敗逐字丟棄（`receipts, _failures = align_events(...)`），失敗事件
    **根本不會出現在 `prepared0.windows`** ⇒ 我原本的揭露從第一步就少算一整類。

    🔴 用**集合**而非計數：等量錯置（A 分區多一個、B 分區少一個）在計數下看不出來。
    鑑別力：拿掉 `dropped_in_alignment` 分區 ⇒ 部分 coverage 那組轉紅（12 筆未歸戶）。
    """
    files = {"BATCH": BATCH_FILE, "MULTI": MULTI_BATCH_FILE, "COV": COV_BATCH_FILE}
    path = files[batch_key]
    _require(path, RUN_1H, RUN_1H_SHORT, KLINE)
    payload = json.loads(path.read_text(encoding="utf-8"))
    out = _post({"horizons": [1],
                 "feature_run": {"symbol": SYM, "timeframe": TF, "config_hash": ff}},
                batch_id=payload["import_id"])

    pa = out["period_alignment"]
    partitions = {
        k: set(pa[k]["ids"]) for k in
        ("dropped_in_alignment", "dropped_by_coverage", "dropped_outside_post_trim_index")
    }
    partitions["excluded_by_symbol"] = {
        e for slot in out["excluded_by_symbol"].values() for e in slot["event_ids"]
    }
    all_input = {str(r["event_id"]) for r in payload["records"]}

    union: set = set()
    overlaps = {}
    for name, ids in partitions.items():
        if union & ids:
            overlaps[name] = sorted(union & ids)[:5]
        union |= ids
    assert not overlaps, f"分區重疊：{overlaps}"

    n_projected = len(out["event_timestamps"])
    assert len(all_input) == len(union) + n_projected, (
        f"分區不守恆：輸入 {len(all_input)} ≠ 剔除 {len(union)} ＋ 投影 {n_projected}；"
        f"各分區 { {k: len(v) for k, v in partitions.items()} }"
    )


@pytest.mark.parametrize("case,mutate,expect_substr", [
    ("duplicate", lambda rs: rs + [dict(rs[0])], "事件身分重複"),
    ("none_id", lambda rs: [dict(r, event_id=None) if i == 0 else r for i, r in enumerate(rs)],
     "身分不合契約"),
    ("int_id", lambda rs: [dict(r, event_id=123456789) if i == 0 else r for i, r in enumerate(rs)],
     "身分不合契約"),
    # 🔴 空白字串現由**契約公式對證**擋下（不再 strip 後判空）——訊息字面隨之改變。
    ("blank_id", lambda rs: [dict(r, event_id="  ") if i == 0 else r for i, r in enumerate(rs)],
     "不符契約公式"),
])
def test_partition_gate_rejects_malformed_identity(case, mutate, expect_substr, monkeypatch) -> None:
    """🔴 `CODEX-R4-P1-01`：守恆閘對**身分不合契約**之輸入 fail-closed。

    首版把 records 直接降成 set 再比對 ⇒ 四個方向 fail-open（提出方實跑皆 HTTP 200）：
    重複 `event_id` 被 set 折疊、`None` 變成字面 `"None"`、整數變成 `"123456789"`、
    空字串照收。這些值還會**原樣出現在回應**，使用者看到的是一份「成功」的報告。
    鑑別力：把 `_assert_event_partition_conserved` 之身分檢查拿掉 ⇒ 四個 case 皆轉綠。
    """
    _require(COV_BATCH_FILE, RUN_1H_SHORT, KLINE)
    import copy as _copy

    import api.services.case_import_service as svc_mod

    batch_id = json.loads(COV_BATCH_FILE.read_text(encoding="utf-8"))["import_id"]
    svc = svc_mod.get_event_import_service()
    real_get = svc.get_import

    def _patched(iid):
        d = real_get(iid)
        if d is None or iid != batch_id:
            return d
        d2 = _copy.deepcopy(d)
        d2.records = mutate([dict(r) for r in d2.records])
        return d2

    monkeypatch.setattr(svc, "get_import", _patched)
    r = client.post(f"/api/v1/case/events/{batch_id}/analyze",
                    json={"horizons": [1], "feature_run": {
                        "symbol": SYM, "timeframe": TF, "config_hash": FF_RUN_SHORT}})
    assert r.status_code == 422, f"{case}: 應被擋下，實得 HTTP {r.status_code}"
    assert expect_substr in str(r.json()["detail"]["message"]), (
        f"{case}: 訊息未指出原因——{r.json()['detail']['message'][:120]}"
    )


def _canon(sym: str, tf: str, t0: int) -> str:
    from momentum.factories import create_event_id_canonicalizer

    return create_event_id_canonicalizer()(sym, tf, t0)


def _ok_rows():
    a = _canon("ETHUSDT", "12h", 1735776000000)
    b = _canon("ETHUSDT", "12h", 1735819200000)
    return a, b, [
        {"event_id": a, "symbol": "ETHUSDT", "timeframe": "12h", "t0": 1735776000000},
        {"event_id": b, "symbol": "ETHUSDT", "timeframe": "12h", "t0": 1735819200000},
    ]


def test_partition_gate_identity_authority_is_the_contract() -> None:
    """🔴 `CODEX-R5-P1-01`：身分規則之權威在**契約**，分析端不得自立。

    首版以 `.strip()` 自訂 ID，兩個後果（提出方實跑）：
      ①帶空白之原始 ID 與已正規化之分區被誤判為同一個 ⇒ 真正的不一致被遮蔽；
      ②`event_id="A"` 在分析端 200，而同一列在契約之 canonical 模式被判 `type_error`。
    ⇒ 改為逐字 exact identity ＋ 直接對證 `canonical_event_id`。
    鑑別力：把契約對證拿掉（只留非空字串檢查）⇒ 本條兩個 case 皆轉綠。
    """
    from api.services.case_import_service import _assert_event_partition_conserved

    a, b, rows = _ok_rows()
    _assert_event_partition_conserved(records=rows, partitions={"projected": [a, b]})  # baseline

    with pytest.raises(ValueError) as ei:
        _assert_event_partition_conserved(
            records=[dict(rows[0], event_id="A"), rows[1]],
            partitions={"projected": ["A", b]},
        )
    assert "不符契約公式" in str(ei.value)

    with pytest.raises(ValueError) as ei2:
        _assert_event_partition_conserved(
            records=[dict(rows[0], event_id=f" {a} "), rows[1]],
            partitions={"projected": [a, b]},
        )
    assert "不符契約公式" in str(ei2.value), "帶空白之 ID 被 strip 後誤判為相同"


@pytest.mark.parametrize("case,kwargs,expect", [
    ("records_none", {"records": None, "partitions": {"projected": []}}, "須為序列"),
    ("records_not_dict", {"records": ["x"], "partitions": {"projected": []}}, "非 dict"),
    ("partition_value_none", None, "之值須為序列"),
    ("partition_contains_none", None, "含非字串或空"),
])
def test_partition_gate_rejects_malformed_partitions(case, kwargs, expect) -> None:
    """🔴 `CODEX-R5-P2-01`：分區側之型別邊界亦須**受控拒絕**，不得冒成 HTTP 500。

    首版直接 `set(ids)`／`sorted(...)` ⇒ `ids` 為 `None` 或含 `None` 時 `TypeError`
    冒到 route 外變成 **500**（提出方實跑 `partition_value_none 500`、
    `partition_value_mixed_ghosts 500`）。500 與 422 的差別是「系統壞了」與
    「你的輸入不合契約」——前者讓使用者以為是平台問題。
    """
    from api.services.case_import_service import _assert_event_partition_conserved

    a, b, rows = _ok_rows()
    if kwargs is None:
        kwargs = {"records": rows, "partitions": (
            {"projected": None} if case == "partition_value_none"
            else {"projected": [a, b], "g": [None, "GHOST"]}
        )}
    with pytest.raises(ValueError) as ei:
        _assert_event_partition_conserved(**kwargs)
    assert expect in str(ei.value), f"{case}: {str(ei.value)[:120]}"


def test_partition_gate_rejects_ghost_ids() -> None:
    """🔴 `CODEX-R4-P1-01`：分區裡出現**不存在於輸入**之 `event_id` ⇒ fail-closed。

    首版只算 `_all_input - _union`（未歸戶），沒算 `_union - _all_input` ⇒ 幽靈 ID
    被當成「已處置」（提出方實跑注入 `GHOST:12h:0` ⇒ HTTP 200 且它出現在剔除清單）。
    兩個方向都要算：少算一邊，守恆就只守了一半。
    """
    from api.services.case_import_service import _assert_event_partition_conserved

    a, b, rows = _ok_rows()
    with pytest.raises(ValueError) as ei:
        _assert_event_partition_conserved(
            records=rows,
            partitions={"projected": [a, b], "dropped_by_coverage": ["ETHUSDT:12h:1"]},
        )
    assert "不在輸入卻被歸戶" in str(ei.value), str(ei.value)[:160]


def test_partition_gate_runs_on_unavailable_branch(monkeypatch) -> None:
    """🔴 `CODEX-R4-P1-01`：`holdout.reason` 支線**也要**過守恆閘。

    該分支直接 `return`，閘擺在它後面等於「沒有邊界的請求不受守恆約束」——
    而那條路徑照樣把三份揭露回給使用者。
    鑑別力：把閘移回 `return` 之後 ⇒ 呼叫次數變 0，本條轉紅。
    """
    _require(COV_BATCH_FILE, RUN_1H_SHORT, KLINE)
    import api.services.case_import_service as svc_mod

    calls = {"n": 0}
    real = svc_mod._assert_event_partition_conserved

    def _spy(**kw):
        calls["n"] += 1
        return real(**kw)

    monkeypatch.setattr(svc_mod, "_assert_event_partition_conserved", _spy)
    batch_id = json.loads(COV_BATCH_FILE.read_text(encoding="utf-8"))["import_id"]
    out = _post({"horizons": [1],
                 "feature_run": {"symbol": SYM, "timeframe": TF, "config_hash": FF_RUN_SHORT},
                 "config_override": {"ic_train_test_split": False}},
                batch_id=batch_id)
    assert out["capability"]["reason"] == "canonical_holdout_disabled"
    assert calls["n"] == 1, f"unavailable 支線未經守恆閘（呼叫 {calls['n']} 次）"


@pytest.mark.parametrize("batch_key,ff_run", [
    ("BATCH", FF_RUN_SHORT), ("MULTI", FF_RUN), ("COV", FF_RUN_SHORT),
], ids=["post_trim", "multi_symbol", "partial_coverage"])
def test_projection_input_event_ids_equal_allowed_set(batch_key, ff_run, monkeypatch) -> None:
    """🔴 `CODEX-R2-P2-01`：投影**實際消費**之 `event_id` 集合**逐值等於**存活集合。

    🔴 筆數守恆擋不住「等長、錯內容」：三步剔除若剔錯人但剔對數量，
    `len` 完全一樣。本條在投影入口攔截實際傳入之 records，與回應揭露推得之
    存活集合做集合相等（`missing`／`extra` 兩側皆列出）。

    鑑別力：把 `projected_records` 改成「剔除數量相同但換一批 event_id」
    （例：改取 `records[:len(allowed)]`）⇒ 筆數守恆那條仍綠，本條轉紅。
    """
    files = {"BATCH": BATCH_FILE, "MULTI": MULTI_BATCH_FILE, "COV": COV_BATCH_FILE}
    path, ff = files[batch_key], ff_run
    _require(path, RUN_1H, RUN_1H_SHORT, KLINE)
    from momentum.Analysis.event_samples.pipeline import EventSamplePipeline

    captured: dict = {}
    real = EventSamplePipeline.run_projection_with_params

    def _spy(self, records, bars_by_tf, **kw):
        captured["ids"] = {str(r.get("event_id")) for r in records}
        return real(self, records, bars_by_tf, **kw)

    monkeypatch.setattr(EventSamplePipeline, "run_projection_with_params", _spy)
    payload = json.loads(path.read_text(encoding="utf-8"))
    out = _post({"horizons": [1],
                 "feature_run": {"symbol": SYM, "timeframe": TF, "config_hash": ff}},
                batch_id=payload["import_id"])

    pa = out["period_alignment"]
    all_ids = {str(r["event_id"]) for r in payload["records"]}
    dropped = set(pa["dropped_in_alignment"]["ids"]) | set(pa["dropped_by_coverage"]["ids"]) \
        | set(pa["dropped_outside_post_trim_index"]["ids"])
    for slot in out["excluded_by_symbol"].values():
        dropped |= set(slot["event_ids"])
    expected = all_ids - dropped

    assert captured.get("ids") is not None, "投影入口未被呼叫——本條前提不成立"
    assert dropped, "本條前提不成立：該組合未剔除任何事件"
    missing = sorted(expected - captured["ids"])
    extra = sorted(captured["ids"] - expected)
    assert not missing and not extra, (
        f"投影消費集合與存活集合不符：缺 {missing[:5]}（共 {len(missing)}）、"
        f"多 {extra[:5]}（共 {len(extra)}）"
    )


def test_projection_consumes_only_surviving_events() -> None:
    """🔴 `CODEX-R1-P1-01`／`COMPOSER-R1-P1-01`：投影**只吃存活事件**，不吃匯入原列表。

    `pipeline.run` 會對傳入之 records 重跑 `_prepare`；餵原列表等於把 coverage／
    post-trim／run symbol 三步剔除全部丟掉——「算了但沒用」，而回應上的揭露欄
    仍照常填，看起來完全正常。
    鑑別力：把投影輸入改回 `records` ⇒ 短 run 那條轉 422、混 symbol 批之
    `n_test` 會把他 symbol 一起算進去，本條兩項斷言皆轉紅。
    """
    _require(BATCH_FILE, MULTI_BATCH_FILE, RUN_1H, RUN_1H_SHORT, KLINE)
    # ① 界外事件確實未進投影：投影後之事件時刻集合不含被剔除者之錨點
    short = _post({"horizons": [1],
                   "feature_run": {"symbol": SYM, "timeframe": TF, "config_hash": FF_RUN_SHORT}})
    dropped_ids = set(short["period_alignment"]["dropped_outside_post_trim_index"]["ids"])
    assert dropped_ids, "本條前提不成立：該 run 未剔除任何事件"
    n_in = len(json.loads(BATCH_FILE.read_text(encoding="utf-8"))["records"])
    assert len(short["event_timestamps"]) == n_in - len(dropped_ids), (
        f"投影後事件數（{len(short['event_timestamps'])}）≠ 匯入數－剔除數"
        f"（{n_in}－{len(dropped_ids)}）——投影吃到了被剔除的事件"
    )
    # ② 他 symbol 事件確實未進投影
    multi = _post({"horizons": [1], "feature_run": FEATURE_RUN}, batch_id=_multi_batch_id())
    n_multi = len(json.loads(MULTI_BATCH_FILE.read_text(encoding="utf-8"))["records"])
    n_excluded = sum(int(v["count"]) for v in multi["excluded_by_symbol"].values())
    assert n_excluded > 0
    assert len(multi["event_timestamps"]) == n_multi - n_excluded, (
        f"投影後事件數（{len(multi['event_timestamps'])}）≠ 匯入數－他 symbol 排除數"
        f"（{n_multi}－{n_excluded}）——他 symbol 事件進了投影"
    )


def test_analyze_ic_train_test_split_off_reason() -> None:
    """🔴 `R5-C3` 5.：`ic_train_test_split` 關 ⇒ `capability.unavailable` ＋ 具名 reason。

    🔴 與 `canonical_feature_universe_unavailable` **必須分得出來**：那條是「根本拿不到
    universe」，這條是「拿得到但依設定本來就不切」。混用會讓使用者以為自己的 run 壞了。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    out = _analyze_projection(config_override={"ic_train_test_split": False})
    assert out["capability"]["split"] == "unavailable", out["capability"]
    assert out["capability"]["reason"] == "canonical_holdout_disabled", out["capability"]
    assert out["split_unify"]["reason"] == "canonical_holdout_disabled"
    # fail-closed 時不得留半套數字
    assert out["split_unify"]["n_test"] is None and out["split_unify"]["boundary_hash"] is None
    # 🔴 但剔除揭露照常在——那是「確實照你指定的 run 篩過事件」的證據
    assert out["period_alignment"] is not None and out["excluded_by_symbol"] is not None


def test_analyze_with_feature_run_lookahead_blocked() -> None:
    """🔴 邊界②：深度不可證**優先於本節全部**——帶 `feature_run` 也不得走投影。

    鑑別力：把分派順序倒過來（先看 `feature_run`）⇒ 一個深度不可證的批會走進投影，
    本條轉紅。順序不是風格問題：①②③ 的條件並非互斥。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    import api.services.case_import_service as svc_mod

    svc = svc_mod.get_event_import_service()
    original = svc._pipeline.lookahead_split_blocked
    try:
        svc._pipeline.__class__.lookahead_split_blocked = staticmethod(lambda receipt: True)
        out = _analyze_projection()
    finally:
        svc._pipeline.__class__.lookahead_split_blocked = staticmethod(original)

    assert out["capability"]["split"] == "unavailable", (
        "深度不可證之批走進了投影——分派順序被破壞"
    )
    assert out["summary"].get("execution_mode") == "event_study_only"


# ── ⑤ 掃描端不得自寫標籤參數預設（AST 機械掃）──────────────────────────────────

def test_case_import_service_has_no_local_spec_defaults() -> None:
    """🔴 `M-SU-R5-23`：事件掃描端**不得**自寫四鍵之預設或 `setdefault`。

    🔴 用 AST 掃而不是 grep 註解：預設值一旦在這裡出現第二份，兩端對同一批會算出
    不同的答案窗，而兩份報告都看起來很正常。
    鑑別力：在該檔任一處寫 `spec.setdefault("horizon_bars", 12)` 或
    `horizon_bars = 12` ⇒ 本條轉紅。
    """
    import ast

    src = (REPO / "api/services/case_import_service.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    four = {"horizon_bars", "entry_price_semantic", "label_return_mode", "decision_offset_bars"}

    def _is_four_key(node) -> bool:
        return isinstance(node, ast.Constant) and node.value in four

    def _mentions_four_key(node) -> bool:
        """子樹內是否出現四鍵之一（字面或下標）。"""
        return any(_is_four_key(n) for n in ast.walk(node))

    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # ① `x.setdefault("<四鍵>", <預設>)`
            if (node.func.attr == "setdefault" and node.args and _is_four_key(node.args[0])):
                hits.append(f"line {node.lineno}: setdefault({node.args[0].value!r}, …)")
            # ② 🔴 `x.get("<四鍵>", <預設>)`（`COMPOSER-R1-P2-03`：原網只認 ①④，
            #    這形態實跑證明可繞過）。單引數之 `.get` 不是預設，不算。
            if (node.func.attr == "get" and len(node.args) >= 2 and _is_four_key(node.args[0])
                    and isinstance(node.args[1], ast.Constant)):
                hits.append(f"line {node.lineno}: .get({node.args[0].value!r}, {node.args[1].value!r})")
        # ③ 🔴 `<含四鍵之運算式> or <常數>`（同上，原網漏）
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for i, val in enumerate(node.values[:-1]):
                nxt = node.values[i + 1]
                if _mentions_four_key(val) and isinstance(nxt, ast.Constant) and nxt.value is not None:
                    hits.append(f"line {node.lineno}: <…{'／'.join(sorted(four & {c.value for c in ast.walk(val) if _is_four_key(c)}))}…> or {nxt.value!r}")
        # ④ `<四鍵> = <字面值>`
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (isinstance(tgt, ast.Name) and tgt.id in four
                        and isinstance(node.value, ast.Constant)):
                    hits.append(f"line {node.lineno}: {tgt.id} = {node.value.value!r}")
    assert not hits, (
        "事件掃描端自寫了標籤參數預設（須一律經共用出口）：\n  " + "\n  ".join(hits)
    )
