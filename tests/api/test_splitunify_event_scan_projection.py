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

client = TestClient(app)


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"真實資料缺席（不得以合成 fixture 代替）：{missing}")


def _batch_id() -> str:
    return json.loads(BATCH_FILE.read_text(encoding="utf-8"))["import_id"]


def _post(body: dict, *, expect: int = 200) -> dict:
    r = client.post(f"/api/v1/case/events/{_batch_id()}/analyze", json=body)
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

    鑑別力：靜默排除（不寫 `excluded_by_symbol`）⇒ 本條轉紅。使用者會看到一份
    「少了一半事件」卻沒說為什麼的報告。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    out = _analyze_projection()
    assert out["excluded_by_symbol"] is not None, "缺 excluded_by_symbol 揭露欄"
    for sym, slot in out["excluded_by_symbol"].items():
        assert sym != SYM, "run symbol 自己不該出現在排除清單"
        assert int(slot["count"]) == len(slot["event_ids"]), f"{sym} 之計數與 ID 數不符"


def test_analyze_one_event_out_of_range_discloses_event_id() -> None:
    """🔴 `R5-C4` 1.：coverage 與 post-trim 首尾兩步之剔除各自具名揭露 `event_id`。

    兩步界線不同（manifest 區間是裁頭尾**前**），少任一步都會讓合法批在投影內部炸掉
    而不是被具名剔除。
    鑑別力：把兩個 ids 清單併成一個計數 ⇒ 本條轉紅（看不出是哪一步剔的）。
    """
    _require(BATCH_FILE, RUN_1H, KLINE)
    pa = _analyze_projection()["period_alignment"]
    for key in ("dropped_by_coverage", "dropped_outside_post_trim_index"):
        assert key in pa, f"period_alignment 缺 {key}"
        assert int(pa[key]["count"]) == len(pa[key]["ids"]), f"{key} 之計數與 ID 數不符"
    lo, hi = pa["post_trim_index_bounds_ms"]
    assert isinstance(lo, int) and isinstance(hi, int) and lo < hi


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
    hits = []
    for node in ast.walk(tree):
        # `x.setdefault("<四鍵之一>", ...)`
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setdefault" and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value in four):
            hits.append(f"line {node.lineno}: setdefault({node.args[0].value!r}, ...)")
        # `<四鍵之一> = <字面值>`（賦一個常數即為自寫預設）
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (isinstance(tgt, ast.Name) and tgt.id in four
                        and isinstance(node.value, ast.Constant)):
                    hits.append(f"line {node.lineno}: {tgt.id} = {node.value.value!r}")
    assert not hits, (
        "事件掃描端自寫了標籤參數預設（須一律經共用出口）：\n  " + "\n  ".join(hits)
    )
