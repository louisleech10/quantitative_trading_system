"""FFDSTAR Task 3.1（docs/FFDSTAR_SPEC.md §V oracle ①–⑥）：真實 kline 全格之整合驗收。

格子＝`preprov_helpers.CELLS`（逐格單行程串行、同模組同格只生成一次）。oracle 皆不讀紀錄自證：
① 窮盡性（manifest 群組欄聯集 ∪ 觀測器記錄之 L7 dead-drop 欄）；② `d` 以 `FeaturePreprocessor._frac_diff_ffd` 對觀測器
記錄之 fracdiff 輸入（同校準前史＋公開段之 L6.5 列）重算、依落盤 dtype 逐位元比；③ `applied` 之欄以
`independent_winsorize` 同參數重算、`ratio_unsafe` 終態之欄等於 L6.5 前值、縮尾不執行之格無 `applied`；
④ `independent_content_sha256` 自讀檔重算；⑤ IC-first JSON 快取：同身分沿用、值改變之重生必拒用舊快取且新快取帶新身分；
⑥ 公開值指紋與改前基準 `tests/_golden/preprov/pre_change_fingerprints.json` 逐位元相同（基準由凍結腳本另行產出）。
mutation 一律以 monkeypatch 對真實格另起根重跑。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Set, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

CELL_SYMBOLS: List[Tuple[str, str]] = [(c, s) for c in ph.CELLS for s in ph.cell_symbols(c)]
#: ② 適用格：平穩化開啟且單行程（觀測器可見）；只檢主週期群組（native 群組之列映射另經 idx_map，不在本 oracle）
#: replace 格（SPEC v4 §V）：fracdiff 輸入由觀測器於寫回前擷取（＝轉換前之值），故 ② 同樣適用
D_CELLS = ["h1_stat_on", "h12h1_multi", "h1_replace_stat_on", "h12h1_replace"]
#: ③ 適用格：單行程（worker 格之 L6.5 前值於子行程，觀測器不可見）；IC-first 之 raw 已刪。replace 格中被平穩化步驟
#: 就地改值之欄（觀測器 `replaced`，以步驟前後值比對而得）落盤值已非縮尾值 ⇒ 不入 ③（fracdiff 者由 ② 驗）
WINSOR_CELLS = ["h1_stat_on", "h1_stat_off", "h1_pp_off", "h12h1_multi", "ratio_unsafe", "dead_drop",
                "h1_replace_stat_on", "h12h1_replace"]
_PRE_WINDOW_BAR = "2025-12-31 12:00:00"  # 輸出窗（WINDOW）前之一根 1h：只改特徵值、不改 label（label 只用窗內 close）


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_acceptance"))


def _kinds(handle: ph.RunHandle) -> List[str]:
    return [k for k in ("raw", "processed") if k in ph.load_manifest(handle.run_dir).get("artifacts", {})]


def _kinds_with_files(handle: ph.RunHandle) -> List[str]:
    return [k for k in _kinds(handle) if (handle.run_dir / k).exists()]


def _dropped(handle: ph.RunHandle, cell: str, artifact_kind: str) -> Set[str]:
    """L7 dead-drop 欄（觀測器）；worker 格之子行程不可見 ⇒ 以 manifest 之剔除數為 0 為前提，回空集合。"""
    if artifact_kind == "processed":
        return set()
    if ph.cell_spec(cell)["path"] == "worker":
        assert int(ph.load_manifest(handle.run_dir)["generation_metadata"]["dead_dropped_cols"]) == 0
        return set()
    return set(ph.observation(handle).l7_dropped)


# ---------------------------------------------------------------------------------------------- oracle

def exhaustive_violations(handle: ph.RunHandle, artifact_kind: str, dropped: Iterable[str],
                          table: pd.DataFrame = None) -> List[str]:
    """① 紀錄輸出欄名集合＝manifest 群組欄聯集（`groups[*].columns`）∪ dead-drop 欄，逐名、無重複。"""
    table = ph.provenance_table(handle.run_dir, artifact_kind) if table is None else table
    names = list(table["output_column"])
    groups = ph.load_manifest(handle.run_dir)["artifacts"][artifact_kind]["groups"]
    group_cols = [c for g in groups.values() for c in g["columns"]]
    expected = set(group_cols) | set(dropped)
    out: List[str] = []
    if len(names) != len(set(names)) or len(group_cols) != len(set(group_cols)):
        out.append("欄名重複")
    if set(names) != expected:
        out.append(f"多 {sorted(set(names) - expected)[:3]} 缺 {sorted(expected - set(names))[:3]}")
    return out


def fracdiff_violations(handle: ph.RunHandle, table: pd.DataFrame = None) -> List[str]:
    """② 主週期群組中 fracdiff 已套用之欄：紀錄之 `d` 以 `_frac_diff_ffd` 對觀測之輸入重算，依落盤 dtype 逐位元等於落盤值。"""
    from momentum.FeatureEngineering.feature_naming import append_op_segments
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    obs = ph.observation(handle)
    table = (ph.provenance_table(handle.run_dir, "raw") if table is None else table).set_index("output_column")
    applied = {n for n in table.index[table["fracdiff"].fillna(False).astype(bool)]
               if table.loc[n, "native_timeframe"] == handle.tf}
    captured = {ph.output_name(c, tf): (tf, c, cap) for (tf, c), cap in obs.fracdiff.items() if tf == handle.tf}
    out: List[str] = []
    if applied != set(captured):
        out.append(f"紀錄 fracdiff 欄 ≠ 實際套用：多 {sorted(applied - set(captured))[:3]} 缺 {sorted(set(captured) - applied)[:3]}")
    checked = 0
    for name in sorted(applied & set(captured)):
        tf, col, cap = captured[name]
        derived = name if cap["mode"] == "replace" else ph.output_name(append_op_segments(col, "fracdiff"), tf)
        stored = ph.stored_columns(handle.run_dir, [derived]).get(derived)
        if stored is None:
            out.append(f"{name}: 落盤無 {derived}")
            continue
        recomputed = FeaturePreprocessor._frac_diff_ffd(pd.Series(cap["input"]), float(table.loc[name, "d"]),
                                                        threshold=cap["weight_threshold"],
                                                        max_width=cap["max_lag"]).to_numpy(dtype=np.float64)
        if not ph.bitwise_equal(ph.as_stored(ph.apply_row_slice(recomputed, obs), stored[1]), stored[0]):
            out.append(f"{name}: 以紀錄之 d 重算不等於落盤 {derived}")
        checked += 1
    if checked == 0:
        out.append("無可檢之 fracdiff 欄 ⇒ ② 空轉")
    return out


def winsor_violations(handle: ph.RunHandle, table: pd.DataFrame = None) -> Tuple[List[str], int, int]:
    """③ 回 (違反, 已檢 applied 欄數, 已檢 ratio_unsafe 欄數)。前處理總開關關或縮尾關 ⇒ 不得有 applied。"""
    spec = ph.contract()
    applied_value = ph.spec_named("winsor_applied", spec)
    ratio_unsafe = ph.spec_named("terminal_ratio_unsafe", spec)
    obs = ph.observation(handle)
    pre = obs.l65_preprocessor
    table = (ph.provenance_table(handle.run_dir, "raw") if table is None else table).set_index("output_column")
    is_applied = table["winsorization"] == applied_value
    if pre is None or not pre.winsor_config.get("enabled", True):
        return ([f"縮尾未執行之格出現 applied：{sorted(table.index[is_applied])[:3]}"] if is_applied.any() else []), 0, 0
    inputs = ph.l65_input_by_output(obs, primary_only=handle.tf)
    replaced = {ph.output_name(c, tf) for tf, c in obs.replaced}  # replace 模式：縮尾後又被平穩化步驟就地改值之欄
    out: List[str] = []
    if replaced and str(pre.mode) != "replace":
        out.append(f"非 replace 模式而輸入欄被平穩化步驟就地改值：{sorted(replaced)[:3]}")
    n_applied = n_unsafe = 0
    for name in sorted(table.index[is_applied]):
        if table.loc[name, "native_timeframe"] != handle.tf or name in obs.l7_dropped or name in replaced:
            continue
        parent = table.loc[name, "parent_column"]
        if isinstance(parent, str) and parent:
            # append 模式衍生欄（SPEC Task 1.2 邊界④）：步驟狀態承父欄，其值為父欄縮尾後再平穩化，不得以本欄獨立縮尾重算；
            # 改驗父欄存在於紀錄且狀態相同（父欄本身之重算由其自身列承擔）
            if parent not in table.index:
                out.append(f"{name}: 衍生欄之父欄 {parent} 不在紀錄")
            elif table.loc[parent, "winsorization"] != table.loc[name, "winsorization"]:
                out.append(f"{name}: 衍生欄縮尾狀態不等於父欄 {parent}")
            continue
        if name not in inputs:
            out.append(f"{name}: applied 但非 L6.5 輸入")
            continue
        values, dtype = ph.stored_columns(handle.run_dir, [name])[name]
        expected = ph.independent_winsorize(inputs[name][0], pre.winsor_config, pre._rolling_window())
        if not ph.bitwise_equal(ph.as_stored(ph.apply_row_slice(expected, obs), dtype), values):
            out.append(f"{name}: applied 之欄獨立縮尾重算不等於落盤")
        n_applied += 1
    for name in sorted(table.index[table["terminal"] == ratio_unsafe]):
        if name not in inputs or name in obs.l7_dropped:
            continue
        values, dtype = ph.stored_columns(handle.run_dir, [name])[name]
        if not ph.bitwise_equal(ph.as_stored(ph.apply_row_slice(inputs[name][0], obs), dtype), values):
            out.append(f"{name}: ratio_unsafe 終態之落盤值 ≠ L6.5 前值")
        n_unsafe += 1
    if n_applied == 0:
        out.append("縮尾開啟之格無 applied 欄可檢 ⇒ ③ 空轉")
    return out, n_applied, n_unsafe


def content_violations(handle: ph.RunHandle) -> List[str]:
    """④ 檔在之 artifact：manifest `content_sha256`＝獨立重算；raw 已刪者 manifest 仍須帶 64-hex 之值。"""
    manifest = ph.load_manifest(handle.run_dir)
    out: List[str] = []
    for kind in _kinds(handle):
        declared = manifest["artifacts"][kind].get("content_sha256")
        if not (isinstance(declared, str) and len(declared) == 64):
            out.append(f"{kind}: manifest 無 content_sha256")
        elif (handle.run_dir / kind).exists() and declared != ph.independent_content_sha256(handle.run_dir, kind):
            out.append(f"{kind}: content_sha256 ≠ 獨立重算")
    return out


def _find_values(node: Any, key: str) -> List[Any]:
    if isinstance(node, dict):
        return [v for k, v in node.items() if k == key] + [x for v in node.values() for x in _find_values(v, key)]
    if isinstance(node, list):
        return [x for v in node for x in _find_values(v, key)]
    return []


def ic_cache_scenario(root: Path, kline_root: Path) -> Dict[str, Any]:
    """⑤ 情境（同一 features 根）：A＝IC-first（cleanup_raw）；同請求重呼 ⇒ 沿用；以「輸出窗前一根 close 改值」之 kline
    複本只重生特徵（同 config_hash、label 不變、內容身分改變）並刪 raw ⇒ 以 A 之請求重呼須拒用舊快取；再以該複本跑完整
    IC-first ⇒ 新 JSON 快取之 content_sha256＝新 manifest raw 節點之值且≠舊值。"""
    from momentum.Analysis.ic_engine import ICCacheRawUnavailableError, ICEngine

    a = ph.generate_short_run(root, "ic_first")
    args, kwargs = ph.observation(a).ic_calls[-1]
    cache_json = a.run_dir / f"ic_selected_features_{a.symbol}_{a.tf}.json"
    old_sha = ph.load_manifest(a.run_dir)["artifacts"]["raw"]["content_sha256"]
    engine = ICEngine({"methods": ["spearman"]})
    reused = engine.compute_ic_from_l7_raw(*args, **kwargs)
    kline = ph.copy_kline_with_one_bar_changed(kline_root, symbol=a.symbol, tf=a.tf, when=_PRE_WINDOW_BAR)
    b = ph.generate_short_run(root, "ic_first_features", kline_path=kline)
    assert b.run_dir == a.run_dir and cache_json.is_file(), "前提：同 config_hash 重生且舊 JSON 快取仍在"
    new_sha = ph.load_manifest(b.run_dir)["artifacts"]["raw"]["content_sha256"]
    shutil.rmtree(b.run_dir / "raw")
    try:
        engine.compute_ic_from_l7_raw(*args, **kwargs)
        stale_refused = False
    except ICCacheRawUnavailableError:
        stale_refused = True
    c = ph.generate_short_run(root, "ic_first", kline_path=kline)
    final_sha = ph.load_manifest(c.run_dir)["artifacts"]["raw"]["content_sha256"]
    cached_ids = _find_values(json.loads(cache_json.read_text(encoding="utf-8")), "content_sha256")
    return {"reused_path": str(reused.selected_path), "cache_json": str(cache_json), "old_sha": old_sha,
            "new_sha": new_sha, "final_sha": final_sha, "stale_refused": stale_refused, "cached_ids": cached_ids,
            "identity": rp.resolve_run_identity(ph.load_manifest(c.run_dir), "raw")}


def _mutant_table(corrupt: Callable[[pd.DataFrame, Mapping[str, Any]], pd.DataFrame]) -> Callable[..., pd.DataFrame]:
    """改壞之 `build_provenance_table`：照生產組表後以 `corrupt` 改壞（呼叫端以 monkeypatch.setattr 換入）。"""
    real = rp.build_provenance_table
    return lambda records, **kw: corrupt(real(records, **kw), kw)


# ---------------------------------------------------------------------------------------------- oracle ①–⑥

@pytest.mark.parametrize("cell,symbol", CELL_SYMBOLS)
def test_oracle_01_exhaustive(runs: ph.RunCache, cell: str, symbol: str) -> None:
    """① 每格每 artifact：紀錄輸出欄名＝manifest 群組欄聯集 ∪ dead-drop 欄，逐名無重複。"""
    handle = runs.get(cell, symbol)
    for kind in _kinds(handle):
        assert exhaustive_violations(handle, kind, _dropped(handle, cell, kind)) == [], kind


@pytest.mark.parametrize("cell", D_CELLS)
def test_oracle_02_d_recompute(runs: ph.RunCache, cell: str) -> None:
    """② `d` 獨立重算與落盤值依 schema dtype 逐位元相等（atol=0）。"""
    assert fracdiff_violations(runs.get(cell)) == []


@pytest.mark.parametrize("cell", WINSOR_CELLS)
def test_oracle_03_winsor_state(runs: ph.RunCache, cell: str) -> None:
    """③ applied 之欄獨立縮尾重算＝落盤；ratio_unsafe 終態之欄＝L6.5 前值（ratio_unsafe 格須至少一欄）；
    前處理總開關關閉之格無任何 applied。"""
    violations, n_applied, n_unsafe = winsor_violations(runs.get(cell))
    if cell == "h1_pp_off":
        assert violations == [] and n_applied == 0
        return
    assert violations == []
    if cell == "ratio_unsafe":
        assert n_unsafe > 0


@pytest.mark.parametrize("cell,symbol", CELL_SYMBOLS)
def test_oracle_04_content_identity(runs: ph.RunCache, cell: str, symbol: str) -> None:
    """④ 測試內自讀檔獨立重算 `content_sha256` 相等。"""
    assert content_violations(runs.get(cell, symbol)) == []


def test_oracle_05_ic_cache_identity(tmp_path_factory: pytest.TempPathFactory) -> None:
    """⑤ IC 快取：同身分沿用；值改變之重生（同 config_hash）必拒用舊快取；新快取與 run 身分帶新內容身分。"""
    result = ic_cache_scenario(tmp_path_factory.mktemp("preprov_ic"), tmp_path_factory.mktemp("preprov_ic_kline"))
    assert result["reused_path"] == result["cache_json"]
    assert result["old_sha"] != result["new_sha"] and result["final_sha"] == result["new_sha"]
    assert result["stale_refused"]
    assert result["cached_ids"] and set(result["cached_ids"]) == {result["final_sha"]}
    assert result["identity"].content_sha256 == result["final_sha"] and not result["identity"].legacy


@pytest.mark.parametrize("cell,symbol", CELL_SYMBOLS)
def test_oracle_06_values_unchanged(runs: ph.RunCache, cell: str, symbol: str) -> None:
    """⑥ 公開值指紋（逐欄 float32 值、NaN 遮罩、dtype、欄名集合）與改前基準逐位元相同；不設容差、不得重凍。"""
    golden = json.loads(ph.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8"))
    expected = golden["cells"][cell][symbol]
    handle = runs.get(cell, symbol)
    kinds = _kinds_with_files(handle)
    assert kinds and sorted(expected) == sorted(kinds)
    for kind in kinds:
        assert ph.value_fingerprints(handle.run_dir, kind) == expected[kind], kind


def test_oracle_06b_baseline_covers_all_cells() -> None:
    """⑥ 改前基準涵蓋 §V 全格與各格之全部標的（缺格即 ⑥ 未驗）。"""
    golden = json.loads(ph.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8"))
    assert {(c, s) for c, by in golden["cells"].items() for s in by} >= set(CELL_SYMBOLS)


# ---------------------------------------------------------------------------------------------- mutation（§V 彙總）

def test_mutation_d_written_fixed(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：紀錄之 `d` 寫固定值 ⇒ ② 轉紅。"""
    def fixed_d(table: pd.DataFrame, kw: Mapping[str, Any]) -> pd.DataFrame:
        table = table.copy()
        table.loc[table["fracdiff"].fillna(False).astype(bool), "d"] = 0.5
        return table

    monkeypatch.setattr(rp, "build_provenance_table", _mutant_table(fixed_d))
    handle = ph.generate_short_run(tmp_path_factory.mktemp("preprov_mut_d"), "h1_stat_on")
    assert fracdiff_violations(handle) != []


def test_mutation_winsor_success_record_removed(tmp_path_factory: pytest.TempPathFactory,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：刪縮尾成功紀錄（applied 改記為其他值）⇒ ③ 轉紅。"""
    spec = ph.contract()
    applied = ph.spec_named("winsor_applied", spec)
    other = next(v for v in ph.contract_values("step_status_values.winsorization", spec) if v != applied)

    def drop_applied(table: pd.DataFrame, kw: Mapping[str, Any]) -> pd.DataFrame:
        table = table.copy()
        table.loc[table["winsorization"] == applied, "winsorization"] = other
        return table

    monkeypatch.setattr(rp, "build_provenance_table", _mutant_table(drop_applied))
    handle = ph.generate_short_run(tmp_path_factory.mktemp("preprov_mut_w"), "h1_stat_off")
    assert winsor_violations(handle)[0] != []


def test_mutation_dead_drop_terminal_skipped(tmp_path_factory: pytest.TempPathFactory,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：略過 dead-drop 終態（被剔欄不入紀錄）⇒ 兩層各自轉紅：生產端窮盡性檢查（`check_exhaustive`）於生成時拋錯；
    將該檢查換為無作用後，測試端 oracle ① 獨立轉紅（證 oracle 不依賴生產端自檢）。"""
    def skip_dead(table: pd.DataFrame, kw: Mapping[str, Any]) -> pd.DataFrame:
        return table[~table["output_column"].isin(set(kw.get("dropped_columns") or {}))].reset_index(drop=True)

    monkeypatch.setattr(rp, "build_provenance_table", _mutant_table(skip_dead))
    with pytest.raises(rp.ProvenanceExhaustivenessError):
        ph.generate_short_run(tmp_path_factory.mktemp("preprov_mut_dd_guard"), "dead_drop")
    monkeypatch.setattr(rp, "check_exhaustive", lambda *args, **kwargs: None)
    handle = ph.generate_short_run(tmp_path_factory.mktemp("preprov_mut_dd"), "dead_drop")
    assert exhaustive_violations(handle, "raw", ph.observation(handle).l7_dropped) != []


def test_mutation_record_file_listed_as_feature_group(tmp_path_factory: pytest.TempPathFactory,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：紀錄檔列入 manifest 特徵群組 ⇒ ① 轉紅（群組欄聯集多出紀錄欄）。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    spec = ph.contract()
    real = FeatureStorage._build_feature_manifest_v2

    def listing_record(self: Any, **kwargs: Any) -> Dict[str, Any]:
        manifest = real(self, **kwargs)
        kind = kwargs["artifact_kind"]
        manifest["artifacts"][kind]["groups"]["__provenance__"] = {
            "path": spec["files"][kind], "file": Path(spec["files"][kind]).name,
            "columns": list(spec["record_columns"]), "column_count": len(spec["record_columns"])}
        return manifest

    monkeypatch.setattr(FeatureStorage, "_build_feature_manifest_v2", listing_record)
    handle = ph.generate_short_run(tmp_path_factory.mktemp("preprov_mut_grp"), "h1_stat_off")
    assert exhaustive_violations(handle, "raw", ph.observation(handle).l7_dropped) != []


def test_mutation_content_sha_without_row_index(tmp_path_factory: pytest.TempPathFactory,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：`content_sha256` 漏 row index ⇒ ④ 轉紅（與獨立重算不等）。"""
    real = rp.compute_content_sha256
    monkeypatch.setattr(rp, "compute_content_sha256", lambda entries, row_index_sha256: real(entries, "0" * 64))
    handle = ph.generate_short_run(tmp_path_factory.mktemp("preprov_mut_cs"), "h1_stat_off")
    assert content_violations(handle) != []


def test_mutation_ic_cache_identity_drops_content_sha(tmp_path_factory: pytest.TempPathFactory,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：IC-first 快取身分移除 `content_sha256` ⇒ ⑤ 轉紅（值改變後仍沿用舊快取）。"""
    from momentum.Analysis import ic_engine

    monkeypatch.setattr(ic_engine, "CACHE_IDENTITY_FIELDS",
                        tuple(f for f in ic_engine.CACHE_IDENTITY_FIELDS if f != "content_sha256"))
    result = ic_cache_scenario(tmp_path_factory.mktemp("preprov_mut_ic"), tmp_path_factory.mktemp("preprov_mut_ick"))
    assert not result["stale_refused"]
