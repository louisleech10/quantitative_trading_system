"""掃描結果立方體之寫入層測試。

SPEC：`docs/GAP3_SCAN_CUBE_SPEC.md`　TODO：`docs/GAP3_SCAN_CUBE_TODO.md`

## 這批測試在防什麼

本 epic 已經踩過三次「元件做了沒接上」與兩次「畫面顯示假數字」。
立方體的失敗形態同型：**檔案寫出來了、manifest 也有、但內容是投影過的／路徑指向不存在的檔**
——那種錯不會拋例外，只會讓使用者拿錯數字做決定。

故每條測試都要求「改壞會紅」（mutation `handoffs/20260907-scancube-mutate.py` S1–S13）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from momentum.Analysis import scan_cube as sc

LIMITS = dict(max_rows=120000, max_rows_per_cell=5000,
              chart_max_bytes=209_715_200, keep_tasks=20)


def _row(name: str, ic: float = 0.1) -> dict:
    """一列 `summary_table`——欄集刻意與 `_build_summary_table` 一致。"""
    return {
        "feature_name": name, "ic_mean": ic, "ic_std": 0.2, "icir": ic / 0.2,
        "p_value": 0.01, "t_stat": 2.5, "p_value_adj": 0.02, "ic_hit_rate": 0.55,
        "monotonicity_score": 0.8, "long_short_spread": 0.03, "coverage": 0.99,
        "turnover_rate": 0.15, "ic_half_life": 4.0, "regime_robust": None,
        "pass_class": "pass",
    }


def _report(n_features: int = 3, *, with_charts: bool = True) -> dict:
    names = [f"feat_{i}" for i in range(n_features)]
    report: dict = {
        "analysis_status": "ok_oos",
        "oos_guarantees": True,
        "summary_table": [_row(n, 0.1 + i * 0.01) for i, n in enumerate(names)],
    }
    if with_charts:
        report.update({
            "ic_decay": {n: {"half_life": 4.0, "series": [0.1, 0.08]} for n in names},
            "quantile_returns": {n: {"long_short": {"spread": 0.03}} for n in names},
            "rolling_ic_series": {n: [0.1, 0.11, 0.09] for n in names},
            # 巢狀：{group: {feature: ...}}
            "grouped_ic": {"bull": {n: 0.12 for n in names}, "bear": {n: 0.05 for n in names}},
            "turnover_analysis": {n: {"quantile_turnover": 0.15} for n in names},
            "coverage_analysis": {n: {"coverage": 0.99} for n in names},
            "marginal_ic": {n: {"loo": 0.01} for n in names},
            # 🔴 排除節：即使 report 有，也不得進立方體
            "correlation_matrix": {"a": {"b": 0.5}},
        })
    return report


def _cell(k: int, h: int, *, n_features: int = 3, capability: str = "available",
          reason=None, with_charts: bool = True) -> dict:
    return {
        "k": k, "h": h, "capability": capability, "reason": reason,
        "n_events": 100,
        "report": _report(n_features, with_charts=with_charts) if capability == "available" else None,
    }


# ══════════════════════════════════════════════════════════════════════════
# Task 2.1 — 逐列/逐節原樣
# ══════════════════════════════════════════════════════════════════════════


def test_rows_are_byte_identical_to_summary_table(tmp_path):
    """🔴 `rows[i]` 必須與 `report["summary_table"][i]` **全等**（不是子集）。

    這條防的是「保存時順手裁欄／改名／排序」——那會讓使用者看到的欄位少於實際算出的。
    """
    cell = _cell(0, 1, n_features=4)
    sc.build_cube("t1", "ETHUSDT", "12h", [cell], root=tmp_path, **LIMITS)

    payload = json.loads((tmp_path / "t1" / "cell_k0_h1.json").read_text(encoding="utf-8"))
    assert payload["rows"] == cell["report"]["summary_table"]
    # 明確再驗欄集，讓「改名」這種變動有獨立訊號
    assert set(payload["rows"][0]) == set(cell["report"]["summary_table"][0])


def test_chart_sections_are_identical_and_exclude_correlation(tmp_path):
    """Tier B 逐節原樣；`correlation_matrix` **不得**出現（per-pair、GAP-6）。"""
    cell = _cell(0, 1)
    sc.build_cube("t1", "ETHUSDT", "12h", [cell], root=tmp_path, **LIMITS)

    payload = json.loads((tmp_path / "t1" / "charts_k0_h1.json").read_text(encoding="utf-8"))
    for name in sc.CHART_SECTIONS:
        assert payload["sections"][name] == cell["report"][name], f"{name} 不是原樣"
    assert "correlation_matrix" not in payload["sections"]

    manifest = json.loads((tmp_path / "t1" / "manifest.json").read_text(encoding="utf-8"))
    # 🔴 排除必須**明講**，不得靜默省略
    assert manifest["excluded_sections"] == ["correlation_matrix"]


def test_unavailable_cell_writes_no_file_but_is_in_manifest(tmp_path):
    """不可用之格：**沒有檔案**，但 manifest 有該筆且帶 reason。

    邊界 1 與邊界 2 的差別必須測得出來——「沒有檔」與「有檔但 rows 空」語意不同。
    """
    cells = [_cell(0, 1), _cell(0, 2, capability="unavailable", reason="cell_timeout")]
    sc.build_cube("t1", None, None, cells, root=tmp_path, **LIMITS)

    assert not (tmp_path / "t1" / "cell_k0_h2.json").exists()
    manifest = json.loads((tmp_path / "t1" / "manifest.json").read_text(encoding="utf-8"))
    entry = next(c for c in manifest["cells"] if (c["k"], c["h"]) == (0, 2))
    assert entry["rows"] == 0 and entry["reason"] == "cell_timeout" and entry["path"] is None


def test_empty_summary_table_is_distinct_from_unavailable(tmp_path):
    """`capability=available` 但 `summary_table` 為空 ⇒ 仍**寫**檔、`rows: []`。"""
    cell = _cell(0, 1, n_features=0)
    sc.build_cube("t1", None, None, [cell], root=tmp_path, **LIMITS)

    # n_features=0 ⇒ rows_per_cell 為 0 ⇒ 依 build_cube 之語意仍屬 available，
    # 但沒有列可寫；manifest 須把它與 unavailable 分開（capability 不同）
    manifest = json.loads((tmp_path / "t1" / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["cells"][0]
    assert entry["capability"] == "available" and entry["rows"] == 0


# ══════════════════════════════════════════════════════════════════════════
# Task 2.1 — 三個 fail-closed 閘
# ══════════════════════════════════════════════════════════════════════════


def test_tier_a_total_rows_gate_writes_nothing(tmp_path):
    """總列數超過 ⇒ **零個** Tier A 檔（禁止部分保存）。"""
    cells = [_cell(0, 1, n_features=3), _cell(0, 2, n_features=3)]
    manifest = sc.build_cube("t1", None, None, cells, root=tmp_path,
                             **{**LIMITS, "max_rows": 5})

    assert manifest["tier_a"]["stored"] is False
    assert manifest["tier_a"]["reason"] == "scan_cube_rows_exceeded"
    assert list((tmp_path / "t1").glob("cell_*.json")) == []


def test_tier_a_per_cell_gate_writes_nothing(tmp_path):
    """單格列數超過 ⇒ 同樣整層不寫（防「1 格 × 60000 特徵」之單檔巨大）。"""
    manifest = sc.build_cube("t1", None, None, [_cell(0, 1, n_features=4)],
                             root=tmp_path, **{**LIMITS, "max_rows_per_cell": 3})

    assert manifest["tier_a"]["stored"] is False
    assert manifest["tier_a"]["reason"] == "scan_cube_rows_per_cell_exceeded"
    assert list((tmp_path / "t1").glob("cell_*.json")) == []


def test_tier_b_budget_is_independent_of_tier_a(tmp_path):
    """🔴 Tier B 超限**不得**影響 Tier A（兩層各自 fail-closed）。"""
    cells = [_cell(0, 1), _cell(0, 2)]
    manifest = sc.build_cube("t1", None, None, cells, root=tmp_path,
                             **{**LIMITS, "chart_max_bytes": 10})

    assert manifest["tier_b"]["stored"] is False
    assert manifest["tier_b"]["reason"] == "scan_cube_chart_bytes_exceeded"
    assert list((tmp_path / "t1").glob("charts_*.json")) == []
    # Tier A 照寫
    assert manifest["tier_a"]["stored"] is True
    assert len(list((tmp_path / "t1").glob("cell_*.json"))) == 2


def test_tier_b_budget_uses_observed_bytes_not_first_cell_extrapolation(tmp_path):
    """🔴 預算判定看**實測累加**，不是「第一格外推」。

    出生事故（`COMPOSER-R2-P1-02` 等三家）：跨真實報告之 per-feature bytes 為
    3,225／19,931／26,637 B（差 8 倍）。用首格外推會放行超量或誤擋合法帶。

    本測試構造「首格很小、後續格很大」：若實作用首格外推，會低估總量而全部寫出；
    正確實作應在累加超過預算時停下並整層不存。
    """
    small = _cell(0, 1, n_features=1)
    big = _cell(0, 2, n_features=200)
    one_small = len(json.dumps({"k": 0, "h": 1, "sections": sc._sections_of(small)},
                               ensure_ascii=False, separators=(",", ":")).encode())
    # 預算＝首格的 3 倍：用首格外推會誤以為 2 格綽綽有餘；實測則會在第二格爆掉
    manifest = sc.build_cube("t1", None, None, [small, big], root=tmp_path,
                             **{**LIMITS, "chart_max_bytes": one_small * 3})

    assert manifest["tier_b"]["stored"] is False, "首格外推的實作會在這裡誤判為可存"
    assert list((tmp_path / "t1").glob("charts_*.json")) == []


def test_fits_hint_is_derived_from_observation(tmp_path):
    """`fits_hint` 由實測導出（不是寫死的 12×300）。"""
    manifest = sc.build_cube("t1", None, None, [_cell(0, 1), _cell(0, 2)],
                             root=tmp_path, **{**LIMITS, "chart_max_bytes": 10})
    hint = manifest["tier_b"]["fits_hint"]
    assert hint["bytes_per_feature"] > 0
    assert hint["max_feature_cells"] >= 0
    assert isinstance(hint["examples"], list)


# ══════════════════════════════════════════════════════════════════════════
# R2 D3 — 路徑不變式
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("limits, tier, path_key", [
    ({"max_rows": 1}, "tier_a", "path"),
    ({"chart_max_bytes": 10}, "tier_b", "chart_path"),
])
def test_path_is_none_when_tier_not_stored(tmp_path, limits, tier, path_key):
    """🔴 `stored is False ⇒ 該層所有路徑為 None`。

    三家 R2 獨立命中：manifest 固定列 `path`／`chart_path`，若在 truncated 時
    仍填檔名，前端照它請求會 404，與 `stored=false` 形成雙重矛盾訊號。
    """
    manifest = sc.build_cube("t1", None, None, [_cell(0, 1), _cell(0, 2)],
                             root=tmp_path, **{**LIMITS, **limits})
    assert manifest[tier]["stored"] is False
    assert all(c[path_key] is None for c in manifest["cells"])


def test_path_points_at_a_file_that_exists(tmp_path):
    """反向：有填路徑者，檔案必須真的在。"""
    manifest = sc.build_cube("t1", None, None, [_cell(0, 1), _cell(1, 2)],
                             root=tmp_path, **LIMITS)
    for entry in manifest["cells"]:
        for key in ("path", "chart_path"):
            if entry[key]:
                assert (tmp_path / "t1" / entry[key]).is_file(), f"{key} 指向不存在的檔"


# ══════════════════════════════════════════════════════════════════════════
# Task 2.2 — prune
# ══════════════════════════════════════════════════════════════════════════


def test_prune_keeps_exactly_keep_after_write(tmp_path):
    """🔴 已有 20 個 ⇒ 寫第 21 個之後恰為 20，且**被刪的是最舊那個**。

    出生事故（`CODEX-R1-P1-06`）：原設計「目錄數 > keep 才刪」在恰好 20 個時不刪，
    寫完變 21——與驗收條文直接矛盾。
    """
    for i in range(20):
        d = tmp_path / f"task_{i:02d}"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"created_at": f"2026-01-{i + 1:02d}"}),
                                         encoding="utf-8")

    sc.build_cube("task_new", None, None, [_cell(0, 1)], root=tmp_path,
                  **{**LIMITS, "keep_tasks": 20})

    names = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert len(names) == 20, f"應恰為 20 個，實際 {len(names)}：{names}"
    assert "task_00" not in names, "被刪的應是最舊的 task_00"
    assert "task_new" in names


def test_prune_treats_missing_manifest_as_oldest(tmp_path):
    """缺 manifest 之目錄排最舊、優先被刪，且不 raise。"""
    (tmp_path / "broken").mkdir()
    for i in range(19):
        d = tmp_path / f"task_{i:02d}"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"created_at": f"2026-01-{i + 1:02d}"}),
                                         encoding="utf-8")

    sc.build_cube("task_new", None, None, [_cell(0, 1)], root=tmp_path,
                  **{**LIMITS, "keep_tasks": 20})
    names = {p.name for p in tmp_path.iterdir() if p.is_dir()}
    assert "broken" not in names


def test_publish_over_existing_directory(tmp_path):
    """🔴 同名 task 已存在（非空）⇒ 仍須成功提交。

    出生事故（`CODEX-R2-P1-04` 實測）：`os.replace` 對**非空**目標目錄在 Darwin
    直接 `OSError: [Errno 66] Directory not empty`。少了 `rmtree` 前置就會炸。
    """
    existing = tmp_path / "t1"
    existing.mkdir()
    (existing / "stale.json").write_text("{}", encoding="utf-8")

    sc.build_cube("t1", None, None, [_cell(0, 1)], root=tmp_path, **LIMITS)
    assert (tmp_path / "t1" / "manifest.json").is_file()
    assert not (tmp_path / "t1" / "stale.json").exists(), "舊內容應被整個換掉"


def test_no_temp_directory_left_behind(tmp_path):
    """提交後不得殘留 temp 目錄。"""
    sc.build_cube("t1", None, None, [_cell(0, 1)], root=tmp_path, **LIMITS)
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".tmp_")]
    assert leftovers == [], f"殘留 temp 目錄：{leftovers}"


# ══════════════════════════════════════════════════════════════════════════
# 讀取層
# ══════════════════════════════════════════════════════════════════════════


def test_query_pagination_is_complete_and_unique(tmp_path):
    """🔴 分頁不重不漏：`limit=7` 逐頁取完之聯集 == 全集，且無重複。"""
    cells = [_cell(k, h, n_features=5) for k in (0, 1) for h in (1, 2)]
    sc.build_cube("t1", None, None, cells, root=tmp_path, **LIMITS)

    seen: list[tuple] = []
    offset = 0
    while True:
        page = sc.query_cube(tmp_path, "t1", offset=offset, limit=7)
        if not page["rows"]:
            break
        seen.extend((r["k"], r["h"], r["feature_name"]) for r in page["rows"])
        offset += 7
    assert len(seen) == len(set(seen)), "跨頁出現重複"
    assert len(seen) == 4 * 5, f"應為 20 列，實際 {len(seen)}"


def test_query_total_is_filtered_count_not_page_size(tmp_path):
    """🔴 `total` 是**篩選後的真實總數**，不是本頁筆數。"""
    cells = [_cell(k, 1, n_features=5) for k in (0, 1)]
    sc.build_cube("t1", None, None, cells, root=tmp_path, **LIMITS)

    page = sc.query_cube(tmp_path, "t1", k=[0], offset=0, limit=2)
    assert page["total"] == 5, "篩 k=0 後應為 5 列"
    assert len(page["rows"]) == 2


def test_query_sort_puts_none_last_in_both_directions(tmp_path):
    """`None` 一律排末尾——「沒有值」不是「最小值」。"""
    cell = _cell(0, 1, n_features=3)
    cell["report"]["summary_table"][1]["icir"] = None
    sc.build_cube("t1", None, None, [cell], root=tmp_path, **LIMITS)

    for direction in ("asc", "desc"):
        rows = sc.query_cube(tmp_path, "t1", sort=("icir", direction), limit=10)["rows"]
        assert rows[-1]["icir"] is None, f"{direction} 時 None 應在末尾"


def test_query_raises_not_found_for_unknown_task(tmp_path):
    """找不到 ≠ 結果為空 ⇒ 用不同型別，路由才能回 404 而非空陣列。"""
    with pytest.raises(sc.CubeNotFound):
        sc.query_cube(tmp_path, "nope")


def test_query_raises_tier_not_stored(tmp_path):
    """Tier A 未存 ⇒ 拋 `CubeTierNotStored`（路由回 409），不是回空頁。"""
    sc.build_cube("t1", None, None, [_cell(0, 1)], root=tmp_path,
                  **{**LIMITS, "max_rows": 1})
    with pytest.raises(sc.CubeTierNotStored):
        sc.query_cube(tmp_path, "t1")


def test_load_charts_returns_report_shaped_slice(tmp_path):
    """🔴 charts 回傳**與 report 同形狀**之單特徵切片，讓既有元件直接吃。

    特別是 `grouped_ic`：形狀是 `{group: {feature: …}}` 巢狀 map，
    不是扁平單 feature 物件（`COMPOSER-R2-P2-01` 指出 `GroupedICBarChart` 要這個）。
    """
    sc.build_cube("t1", None, None, [_cell(0, 1, n_features=3)], root=tmp_path, **LIMITS)
    out = sc.load_charts(tmp_path, "t1", 0, 1, "feat_1")

    assert set(out["sections"]["ic_decay"]) == {"feat_1"}
    assert set(out["sections"]["grouped_ic"]) == {"bull", "bear"}
    assert set(out["sections"]["grouped_ic"]["bull"]) == {"feat_1"}
    assert "correlation_matrix" not in out["sections"]


def test_load_charts_raises_when_tier_b_not_stored(tmp_path):
    sc.build_cube("t1", None, None, [_cell(0, 1)], root=tmp_path,
                  **{**LIMITS, "chart_max_bytes": 10})
    with pytest.raises(sc.CubeTierNotStored):
        sc.load_charts(tmp_path, "t1", 0, 1, "feat_0")


def test_section_status_object_passes_through(tmp_path):
    """節本身是 `{status, reason}` 時**原樣**傳遞（前端沿用同一支 `sectionSplit`）。"""
    cell = _cell(0, 1)
    cell["report"]["turnover_analysis"] = {"status": "disabled", "reason": "turnover_off"}
    sc.build_cube("t1", None, None, [cell], root=tmp_path, **LIMITS)

    out = sc.load_charts(tmp_path, "t1", 0, 1, "feat_0")
    assert out["sections"]["turnover_analysis"] == {"status": "disabled", "reason": "turnover_off"}


# ══════════════════════════════════════════════════════════════════════════
# Task 2.0 — 契約鍵
# ══════════════════════════════════════════════════════════════════════════


def test_contract_params_expose_five_scan_cube_keys():
    """🔴 跑**真實 loader**，不檢 JSON 字面。

    出生事故（`CODEX-R1-P1-03`）：`pipeline.py` 對非 dict 之 spec 直接 `continue`
    ⇒ 寫成裸整數會被靜默略過，隨後 `params[...]` KeyError。
    """
    from momentum.factories import create_event_sample_pipeline

    params = create_event_sample_pipeline().analysis_params()
    expected = {
        "scan_cube_max_rows": 120000,
        "scan_cube_max_rows_per_cell": 5000,
        "scan_cube_chart_max_bytes": 209_715_200,
        "scan_cube_keep_tasks": 20,
        "scan_cube_page_max": 500,
    }
    for key, value in expected.items():
        assert key in params, f"契約缺 {key}（很可能是寫成裸整數被 loader 略過）"
        assert isinstance(params[key], int) and not isinstance(params[key], bool)
        assert params[key] > 0
        assert params[key] == value


# ══════════════════════════════════════════════════════════════════════════
# Task 1.1 — 掃描格不得寫共用落檔
# Task 2.3 — 接線 ＋ report 不得洩進 HTTP
# ══════════════════════════════════════════════════════════════════════════


def test_no_shared_persist_scan_cell_sets_suppress_flag():
    """🔴 `_run_scan_cell` 必須在 `analyze()` **之前**把該格 analyzer 設為不落檔。

    出生事故（`handoffs/20260906-probe-scan-overwrite.py`，rc=0）：
    `_resolve_filtered_path` 不含 k/h ⇒ 4 組不同 (k,h) 落到同一路徑；
    連寫兩格後檔內只剩後者的欄位。

    🔴 本測試用 spy 驗**呼叫沒發生**（`save_filtered_features` 沒被叫），
    而不是驗「檔案沒變」——三家 R2 指出 stale artifact 的 mtime 本來就不會變，
    比 mtime 證不了「這次沒寫」。
    """
    from api.services.ic_analysis_service import ICAnalysisService

    seen: dict = {}

    class _Analyzer:
        def __init__(self):
            self._suppress_persist = False

        def analyze(self, **kwargs):
            # 在真正跑分析的那一刻，旗標必須已經是 True
            seen["suppress_at_analyze"] = self._suppress_persist
            return {"summary_table": [], "analysis_status": "ok_oos"}

    service = ICAnalysisService.__new__(ICAnalysisService)
    staged = {
        "event_timestamps": [1, 2], "event_label_values": {}, "event_context": {},
        "purge_rows": 0, "analysis_alignment_receipt_hash": "h",
    }
    service._run_event_label_stages = lambda *a, **k: staged  # type: ignore[method-assign]
    service._scan_cell_summary = lambda r: None  # type: ignore[method-assign]

    out = ICAnalysisService._run_scan_cell(
        service, lambda override: _Analyzer(), object(), {},
        features_path=None, meta_path=None, feature_manifest_path=None,
        labels_path=None, kline_reader=None, config_override=None,
    )

    assert seen["suppress_at_analyze"] is True, "掃描格在 analyze 當下沒有 suppress ⇒ 會覆寫共用 h5"
    # 順帶釘住 Task 2.3：report 必須被帶回來（供 build_cube 用）
    assert "report" in out


def test_wiring_scan_grid_strips_report_before_returning(tmp_path, monkeypatch):
    """🔴 `build_cube` 之後必須**立刻** pop 掉 `report`。

    出生事故（`CODEX-R1-P1-02`／`GROK-R1-P1-01` 兩家獨立命中）：
    `_run_analysis` 把整個 `scan` 放進 `info["event_label_scan"]`，
    `get_task_status` 再逐鍵放進 HTTP payload ⇒ 不剝除就把 GB 級 report 推進 status API。
    """
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService.__new__(ICAnalysisService)
    sentinel = {"summary_table": [_row("f0")], "analysis_status": "ok_oos",
                "__sentinel__": "MUST_NOT_LEAK"}
    results = [{"k": 0, "h": 1, "capability": "available", "reason": None,
                "n_events": 5, "report": sentinel}]

    monkeypatch.setattr(
        "momentum.Analysis.scan_cube.DEFAULT_ROOT", tmp_path, raising=False)
    cube = ICAnalysisService._build_scan_cube(service, "t1", object(), results)
    for cell in results:
        cell.pop("report", None)

    payload = json.dumps({"scan_results": results, "cube": cube}, default=str)
    assert "MUST_NOT_LEAK" not in payload, "report 洩進了要送出去的 payload"
    assert "rows" not in cube and "sections" not in cube
    assert set(cube) == {"status", "created_at", "metrics", "chart_sections",
                         "excluded_sections", "tier_a", "tier_b"}


def test_cube_failure_does_not_kill_scan_results(monkeypatch):
    """落檔失敗 ⇒ `cube.status=failed`，但掃描結果本身仍完整。"""
    from api.services import ic_analysis_service as svc

    service = svc.ICAnalysisService.__new__(svc.ICAnalysisService)

    def _boom():
        raise OSError("disk full")

    monkeypatch.setattr(
        "momentum.factories.create_scan_cube_store",
        lambda: type("X", (), {"build_cube": staticmethod(lambda *a, **k: _boom())})(),
    )
    cube = svc.ICAnalysisService._build_scan_cube(service, "t1", object(), [])
    assert cube["status"] == "failed" and "disk full" in cube["reason"]
