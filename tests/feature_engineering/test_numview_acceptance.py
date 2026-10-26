"""NUMVIEW 驗收（docs/NUMVIEW_SPEC.md）：Phase 1 量測收據（Task 1.1、1.2、1.3）、§G 通過條件（Phase 0／2／4 值指紋逐位元）、
Task 4.2 ⑤ 結構重凍收據、Task 5.1 文件與 fact-key 更正。

驗證：
- Task 1.1（`handoffs/run_receipts/*-numview-postic-branchdiff.json`）：`exit_code`＝0、`criteria_sha256`＝現行判準檔 sha256；
  列數＝Σ_(格, 輸入) 該輸入分支數×7（判準 v8 起分支依輸入取 `comparison_outputs.postic_branch_vs_float64_oracle.branches_by_input`：(i)＝`tests/_golden/icpostleak/contract.json` 之 `branches` ∪ 候選臂、(ii)＝明列五臂；label_provenance、sink_routes／sink_runs 依同條目驗；
  七組合＝該契約 `combos`）；每格每可達臂具速度欄（三次牆鐘＋中位數）；ICPOSTLEAK 輸入集格（BTCUSDT 1h，取自該契約
  `kline`）之 legacy 對 optimized 七組合皆 0 差（並核 10-02 收據之 optimized 七列確為 0 差）；候選臂中間 dtype 皆記為
  float64（≥3 處；R10-A）。
- Task 1.2（`*-numview-precision-chain.json`）：rc、`criteria_sha256`；段 S0–S5 × 格逐欄統計列完整；S4 raw BSS 讀回逐位元
  相等否則 `lossless_violation`；延伸格具「降級欄數」欄。
- Task 1.3（`*-numview-l2-arm-matrix.json`）：rc、`criteria_sha256`；格數＝格 A＋格 B 全部；BTCUSDT 12h 重現
  `handoffs/run_receipts/20261004-icfirstalign-freeze-baselines.json` 之 f32diff=0。
- §G 通過條件（Phase 0、2、4）：凍結格於現行碼重生（模組範圍、每格一次）之值指紋經 `numview_helpers.bitwise_diff` 逐位元
  等於 `tests/_golden/numview/pre_change_fingerprints.json`（G1 每個已凍結臂份以其環境重跑；`arm_unreachable` 者因不在凍結檔
  而不比、不補造），沿用基準 `tests/_golden/preprov/pre_change_fingerprints.json` 以 `legacy=True` 比（相容欄）；Phase 3 例外
  只經決定紀錄 `tests/_golden/numview/decisions.json`（`changed_targets` 且已落地者）排除，其餘 atol=0。
- Task 4.2 ⑤：`tests/_golden/numview/refreeze_receipt.json` 證「剝除新鍵（鍵名讀契約）後依原算法重算＝現行凍結值」。
- Task 5.1：`白話說明/還沒做的事.md` 含 `0.00005` 之行皆含「單步」；`docs/ROADMAP.md` 之 RM-NUMVIEW 列位於 roadmap-status
  生成區塊且含 fact_keys RM-NUMVIEW 同文（含「零差」）；`docs/TICKET_ORDER.md` 第 36 行含 IC-first 與 IC 頁兩者之限定措辭；
  生成區塊無漂移（`gen_fact_key_blocks.sh --check`）；`check_decoupling.sh` 之 R1、R4 計數不增（基準＝凍結收據 `head`
  ——Phase 0 改前 HEAD——之 `git grep` R1 計數與 `scripts/decouple_baseline.txt` R4 債清單）。
邊界：13 近零參照值（Task 1.1 邊界①）；14 選欄全 ratio-unsafe 之格記零欄、非 material（Task 1.1 邊界②）；15 IC 全 ties／
全 NaN／有效對數 < 2 ⇒ τ-b NaN ⇒ material（Task 1.1 邊界③）；16 全 NaN 欄標 `all_nan`、不計誤差（Task 1.2 邊界①）；
17 codec 回退 zstd 計數並列原因（Task 1.2 邊界②）；18 格 C blocked ⇒ 各段標 blocked、不外推（Task 1.2 邊界③）；19 多週期格
L1 記 float64（Task 1.3 邊界①）；20 類別拋錯 ⇒ 記錯誤、不以缺欄計 0 差（Task 1.3 邊界②）；57 白話文件同 commit 產
`docs/site/還沒做的事.html`（Task 5.1 邊界①）；58 fact-key 寫入經 `live_doc_write_guard.sh`（Task 5.1 邊界②）。
mutation：Task 1.1 收據缺速度欄 ⇒ 速度檢查紅；`ic_material` 改為 `tau < 1` 判定 ⇒ 邊界 15 檢查翻紅；Task 1.2 收據刪一段之列
⇒ 完整性紅；Task 1.3 收據之錯誤改記 f32diff=0 ⇒ 錯誤檢查紅；§G `bitwise_diff` 改用 float32 `values` ⇒ 原生位元組鑑別翻紅；
Task 5.1 含 `0.00005` 而無「單步」之文字 ⇒ 措辭檢查紅。mutation 一律對載入之複本（monkeypatch 本模組讀取函式或受測模組屬性）。

測試接縫（實作須提供；欄名即契約）：
- 判準檔 `cell_definitions.{A,B}.min_history_bars`；格類列舉規則同 `test_numview_baseline.py`（格 C＝每個 symbol×tf）。
- 契約 `post_ic_arm_reachability.<臂>.min_selected_columns`（同 test_numview_baseline）。
- Task 1.1 收據：`exit_code, criteria_sha256, branches[], cells[].{cell_id, input("i"|"ii"), kind(ii), symbol, timeframes,
  selected[], columns:int}, rows[].{cell_id, input, branch, combo("+" 連接之契約組合), columns, max_abs, p99_abs, max_rel,
  near_zero_cells, near_zero_max_abs, nan_mask_diff, sign_flips, tau_b, material, material_reason},
  speed[].{cell_id, input, arm, seconds[3], median_seconds}, reproduction[].{symbol, timeframes, input, combo, diff_cells,
  nan_mask_diff, max_abs_diff}, candidate_intermediate_dtypes[].{cell_id, input, point, dtype}`。
- `postic_branchdiff.cell_diff(reference, output)` 回 `max_abs, p99_abs, max_rel, near_zero_cells, near_zero_max_abs,
  nan_mask_diff`（近零＝|ref| < float32 tiny，不計相對差）；`ic_material(ic_reference, ic_variant)` 回 `tau_b, sign_flips,
  material, reason`。
- Task 1.2 收據：`exit_code, criteria_sha256, cells[].{cell_id, kind(A|B|C), symbol, timeframes, status(measured|blocked),
  columns[], codec_fallback_count}, rows[].{segment(S0–S5), cell_id, column, status, max_abs, max_rel, nan_mask_diff,
  all_nan, float16_ok}, s4_raw_bss[].{cell_id, bitwise_equal}, lossless_violation:bool, codec_fallbacks[].{cell_id, column,
  reason}, extension[].{cell_id, downgraded_columns:int, new_evidence:bool}`；`precision_chain.checkpoint_stats` 全 NaN ⇒
  `all_nan=True`、`max_abs`／`max_rel` 為 None、`float16_ok=True`。
- Task 1.3 收據：`exit_code, criteria_sha256, cells[].{cell_id, kind, symbol, timeframes, l1_dtypes[], common_cols,
  only_returned[], only_category[], nan_mask_diff, f64diff, f32diff, max_abs, max_rel, errors[].{category, error}}`；
  有錯誤之格 `f32diff` 為 None；`l2_arm_matrix.compare_l2_arms` 回 docstring 所列鍵。
- `scripts/numview_freeze_baseline.freeze_cell(cell: Mapping, work_root: Path, *, arms: Sequence[str], run_kind: str) -> Dict`：以現行碼依凍結檔
  之格紀錄重生該格，回與凍結檔同形之 `{"g1": {臂: {env, actual_arm, fingerprint}}, "g2": {...}, "g3": {...}}`，G1 只跑 `arms`。
- 決定紀錄 `decisions.json`：`{"decisions": {鍵: {choice, changes_public_output, user_ruling{date, quote},
  implemented_commit, changed_targets[].{group(g1|g2|g3|legacy), cell?, copy?, columns?}}}}`；`implemented_commit` 為 HEAD 祖先才豁免。
- 凍結收據 `head`（Task 0.5；作 R1／R4 基準 commit）。
執行級距：Task 1.x／4.2／5.1 為 JSON／秒級；§G 兩個 `test_gate_*_at_current_code` 逐格真實生成（格 A＋B 全部，另 PRE-PROV 11 格）
屬小時級，一律丟背景、逐檔明列路徑。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import math
import re
import statistics
import subprocess
import sys
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering import numeric_view as nv
from momentum.factories import ratio_unsafe_category
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import numview_helpers as nh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = [pytest.mark.requires_kline, pytest.mark.timeout(43200)]

REPO = nh.REPO
THIS = sys.modules[__name__]
PROBE_DIR = REPO / "handoffs" / "run_receipts" / "numview_probes"
FREEZE_SCRIPT_PATH = REPO / "scripts" / "numview_freeze_baseline.py"
ICPOSTLEAK_CONTRACT_PATH = REPO / "tests" / "_golden" / "icpostleak" / "contract.json"
BRANCHDIFF_1002_PATH = REPO / "handoffs" / "run_receipts" / "20261002-icpostleak-branch-diff.json"
FREEZE_BASELINES_1004_PATH = REPO / "handoffs" / "run_receipts" / "20261004-icfirstalign-freeze-baselines.json"
FACT_KEYS_PATH = REPO / "scripts" / "fact_keys.json"
ROADMAP_PATH = REPO / "docs" / "ROADMAP.md"
TICKET_ORDER_PATH = REPO / "docs" / "TICKET_ORDER.md"
PLAIN_DOC_REL = "白話說明/還沒做的事.md"
SITE_DOC_REL = "docs/site/還沒做的事.html"
PLAIN_DOC_PATH = REPO / PLAIN_DOC_REL
SITE_DOC_PATH = REPO / SITE_DOC_REL
RENDERER_PATH = REPO / "scripts" / "plain_docs_render.py"
LIVE_DOC_REGISTRY_PATH = REPO / "scripts" / "live_doc_registry.json"
SETTINGS_PATH = REPO / ".claude" / "settings.json"
DECOUPLE_BASELINE_REL = "scripts/decouple_baseline.txt"

#: SPEC Task 1.2 之段名
SEGMENTS: Tuple[str, ...] = ("S0", "S1", "S2", "S3", "S4", "S5")
#: SPEC Task 1.2 以逐欄統計計之段（S5 為倖存者集合比較，逐檢查點一列）
PER_COLUMN_SEGMENTS: Tuple[str, ...] = ("S0", "S1", "S2", "S3", "S4")
#: SPEC Task 1.3 驗證點名之重現格（BTCUSDT 12h，freeze-baselines 收據之 `honest_bounds`）
L2_REPRO_SYMBOL, L2_REPRO_TF = "BTCUSDT", "12h"
#: SPEC Task 5.1 點名之識別碼與措辭
RM_NUMVIEW, ZERO_DIFF_WORD, SINGLE_STEP_WORD, OLD_ZSCORE_LITERAL = "RM-NUMVIEW", "零差", "單步", "0.00005"
#: 第 4 步之列首（SPEC 起草時位於第 36 行；其後檔案增修使行號漂移，改依列首定位，恰一列）
TICKET_ORDER_ROW_PREFIX = "| 4 |"
TICKET_ORDER_OLD_PHRASE = "post-IC 鎖 Polars 正式臂"
ROADMAP_BLOCK = "roadmap-status"

CellKey = Tuple[str, str, Tuple[str, ...]]


# ---------------------------------------------------------------------------------------------- 讀取（mutation 以 monkeypatch 替換）

_MODULES: Dict[str, ModuleType] = {}


def _load_module(name: str, path: Path) -> ModuleType:
    """以檔案路徑載入（探針非套件）；同模組同名只載一次，monkeypatch 作用於同一物件。"""
    if name not in _MODULES:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None, f"無法載入 {path}"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MODULES[name] = module
    return _MODULES[name]


def probe(name: str) -> ModuleType:
    return _load_module(f"numview_probe_{name}", PROBE_DIR / f"{name}.py")


def freeze_script() -> ModuleType:
    return _load_module("numview_freeze_baseline_acceptance", FREEZE_SCRIPT_PATH)


def _json(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"不存在：{path}"
    return json.loads(path.read_text(encoding="utf-8"))


def load_receipt(kind: str) -> Dict[str, Any]:
    """`handoffs/run_receipts/*-numview-<kind>.json`（恰一份）。"""
    hits = sorted(nh.RECEIPTS_DIR.glob(f"*-numview-{kind}.json"))
    assert len(hits) == 1, f"*-numview-{kind}.json 須恰一份，實得 {[p.name for p in hits]}"
    return json.loads(hits[0].read_text(encoding="utf-8"))


def load_freeze() -> Dict[str, Any]:
    return _json(nh.PRE_CHANGE_FINGERPRINTS_PATH)


def load_criteria() -> Dict[str, Any]:
    if nh.criteria_replaced():  # 判準檔已以 vN 取代（SPEC Task 0.3 邊界①：判準檔恰一存在）⇒ 讀現行判準；v1 現行時沿原斷言
        return _json(nh.current_criteria_path())
    return _json(nh.CRITERIA_PATH)


def load_contract() -> Dict[str, Any]:
    return nv.load_contract()


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def criteria_sha256() -> str:
    if nh.criteria_replaced():  # 判準檔已以 vN 取代（SPEC Task 0.3 邊界①：判準檔恰一存在）⇒ 讀現行判準；v1 現行時沿原斷言
        current = nh.current_criteria_path()
        assert current.is_file(), f"判準檔不存在：{current}"
        return hashlib.sha256(current.read_bytes()).hexdigest()
    assert nh.CRITERIA_PATH.is_file(), f"判準檔不存在：{nh.CRITERIA_PATH}"
    return hashlib.sha256(nh.CRITERIA_PATH.read_bytes()).hexdigest()


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), "-c", "core.quotePath=false", *args], capture_output=True, text=True)


# ---------------------------------------------------------------------------------------------- 獨立列舉

def kline_inventory() -> Dict[str, Dict[str, int]]:
    import h5py

    assert nh.KLINE_PATH.is_file(), f"真實 kline 不存在：{nh.KLINE_PATH}"
    out: Dict[str, Dict[str, int]] = {}
    with h5py.File(nh.KLINE_PATH, "r") as handle:
        for symbol in sorted(handle.keys()):
            group = handle[symbol]
            tfs = {tf: int(group[tf]["data"].shape[0]) for tf in sorted(group.keys())
                   if hasattr(group[tf], "keys") and "data" in group[tf]}
            if tfs:
                out[str(symbol)] = tfs
    assert out, "kline_cache.h5 無任何 symbol×tf"
    return out


def tf_seconds(tf: str) -> float:
    try:
        return float(pd.Timedelta(tf).total_seconds())
    except (ValueError, TypeError) as exc:
        raise AssertionError(f"無法解析週期 {tf!r}：{exc}") from exc


def enumerate_keys(kinds: Sequence[str]) -> Set[CellKey]:
    """格 A＝每個 symbol×tf；格 B＝每個具 ≥2 週期之 symbol（週期依長度升冪）；格 C＝每個 symbol×tf。判準 v3 起改為判準檔
    封閉路徑覆蓋清單中屬 `kinds` 之格（SPEC §C、Task 0.5 ②）。"""
    if nh.criteria_cell_list() is not None:  # 判準 v3 起：封閉清單取代全部 symbol×tf 列舉
        return nh.criteria_cell_keys(kinds)
    out: Set[CellKey] = set()
    for symbol, tfs in kline_inventory().items():
        for kind in kinds:
            if kind in ("A", "C"):
                out.update((kind, symbol, (tf,)) for tf in tfs)
            elif kind == "B" and len(tfs) >= 2:
                out.add(("B", symbol, tuple(sorted(tfs, key=tf_seconds))))
    return out


def cell_key(record: Mapping[str, Any]) -> CellKey:
    return (str(record["kind"]), str(record["symbol"]), tuple(str(t) for t in record["timeframes"]))


def kept_columns(selected: Sequence[str]) -> List[str]:
    seen: List[str] = []
    for name in (str(c) for c in selected):
        if name not in seen:
            seen.append(name)
    return [c for c in seen if ratio_unsafe_category(c) is None]


def reachable_by_contract(contract: Mapping[str, Any], selected_count: int) -> List[str]:
    arms = list(contract["post_ic_arm_values"]["values"])
    assert arms, "契約 post_ic_arm_values 為空"
    out: List[str] = []
    for arm in arms:
        minimum = (contract["post_ic_arm_reachability"].get(arm) or {}).get("min_selected_columns")
        assert isinstance(minimum, int) and minimum >= 1, f"契約 {arm}.min_selected_columns 非正整數：{minimum!r}"
        if selected_count >= minimum:
            out.append(arm)
    return out


def _is_nan_or_none(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _receipt_common_violations(receipt: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    if receipt.get("exit_code") != 0:
        out.append(f"exit_code={receipt.get('exit_code')!r}")
    if receipt.get("criteria_sha256") != criteria_sha256():
        out.append("criteria_sha256 ≠ 現行判準檔")
    return out


# ============================================================================================== Task 1.1

def icpostleak_contract() -> Dict[str, Any]:
    return _json(ICPOSTLEAK_CONTRACT_PATH)


def _branchdiff_output_spec() -> Dict[str, Any]:
    """判準 `comparison_outputs.postic_branch_vs_float64_oracle`（v8 起含 branches_by_input／label_provenance／sink_routes）。"""
    return load_criteria()["comparison_outputs"]["postic_branch_vs_float64_oracle"]


def expected_branches(contract: Optional[Mapping[str, Any]] = None) -> List[str]:
    """`contract`：ICPOSTLEAK 契約（驗收據時為其產生時之版本，`nh.contract_for_receipt`；未給 ⇒ 現行）。"""
    contract = contract if contract is not None else icpostleak_contract()
    return sorted(set(contract["branches"]) | {probe("postic_branchdiff").CANDIDATE_ARM})


def branches_for_input(input_kind: str, contract: Optional[Mapping[str, Any]] = None) -> List[str]:
    """判準 v8 `branches_by_input` 之該輸入分支封閉集合（SPEC v30 Task 1.1：(i)＝ICPOSTLEAK 契約 branches ∪ plus、
    (ii)＝明列五臂）。`contract` 同 `expected_branches`。"""
    spec = _branchdiff_output_spec()["branches_by_input"][str(input_kind)]
    if "contract_branches" in spec:
        contract = contract if contract is not None else icpostleak_contract()
        return sorted(set(contract["branches"]) | set(spec.get("plus") or []))
    return sorted(spec["branches"])


def combo_names() -> List[str]:
    combos = ["+".join(c) for c in icpostleak_contract()["combos"]]
    assert len(combos) == 7 == len(set(combos)), combos
    return combos


def _entry_key(entry: Mapping[str, Any]) -> Tuple[str, str]:
    return (str(entry["cell_id"]), str(entry["input"]))


def branchdiff_rows_violations() -> List[str]:
    """列數＝Σ_(格, 輸入) 該輸入分支數×7（判準 v8 起；v7 以前為格數×分支數×7）、每 (格, 輸入, 分支, 組合) 恰一列；格涵蓋：輸入 (i)＝每個 symbol×tf、輸入 (ii)＝凍結檔全部格。
    判準 v3 起（SPEC Task 1.1 v17）：輸入 (i)＝封閉清單格 A 之 symbol×tf、輸入 (ii)＝判準 `run_coverage.postic_branchdiff` 之格。"""
    receipt = load_receipt("postic-branchdiff")
    icpl = nh.contract_for_receipt(ICPOSTLEAK_CONTRACT_PATH, receipt)
    branches, combos = expected_branches(icpl), combo_names()
    out: List[str] = []
    if sorted(receipt.get("branches") or []) != branches:
        out.append(f"branches {sorted(receipt.get('branches') or [])} ≠ {branches}")
    cells = receipt["cells"]
    keys = [_entry_key(c) for c in cells]
    if len(keys) != len(set(keys)) or not keys:
        out.append("cells 重複或為空")
    inv_i = {(str(c["symbol"]), tuple(c["timeframes"])) for c in cells if c["input"] == "i"}
    want_i = (nh.criteria_symbol_timeframes("A") if nh.criteria_cell_list() is not None
              else {(s, (tf,)) for s, tfs in kline_inventory().items() for tf in tfs})
    if inv_i != want_i:
        out.append(f"輸入 (i) 涵蓋 ≠ 每個 symbol×tf：缺 {sorted(want_i - inv_i)[:5]}")
    inv_ii = {cell_key(c) for c in cells if c["input"] == "ii"}
    want_ii = (nh.criteria_run_cell_keys("postic_branchdiff") if nh.criteria_cell_list() is not None
               else {cell_key(r) for r in load_freeze()["cells"].values()})
    if inv_ii != want_ii:
        out.append(f"輸入 (ii) 涵蓋 ≠ 凍結格：缺 {sorted(want_ii - inv_ii)[:5]} 多 {sorted(inv_ii - want_ii)[:5]}")
    rows = receipt["rows"]
    row_keys = [(str(r["cell_id"]), str(r["input"]), str(r["branch"]), str(r["combo"])) for r in rows]
    if not isinstance(_branchdiff_output_spec().get("branches_by_input"), Mapping):  # 判準 v7 以前：全域同一分支集合
        want_rows = {(c, i, b, k) for (c, i) in set(keys) for b in branches for k in combos}
        if len(rows) != len(set(keys)) * len(branches) * len(combos):
            out.append(f"列數 {len(rows)} ≠ 格數 {len(set(keys))} × 分支數 {len(branches)} × {len(combos)}")
        if set(row_keys) != want_rows or len(row_keys) != len(set(row_keys)):
            out.append("列之 (格, 輸入, 分支, 組合) 非恰一")
        return out
    # 判準 v8 起（SPEC v30 Task 1.1）：分支依輸入取 `branches_by_input`，列數＝Σ_(格, 輸入) 該輸入分支數 × 組合數
    want_rows = {(c, i, b, k) for (c, i) in set(keys) for b in branches_for_input(i, icpl) for k in combos}
    if len(rows) != len(want_rows):
        out.append(f"列數 {len(rows)} ≠ Σ_(格, 輸入) 該輸入分支數 × {len(combos)}＝{len(want_rows)}")
    if set(row_keys) != want_rows or len(row_keys) != len(set(row_keys)):
        out.append("列之 (格, 輸入, 分支, 組合) 非恰一（含該輸入不准之分支或缺跑）")
    return out


def _array_sha256(values: np.ndarray) -> str:
    """判準 v8 `label_provenance.hash_rule`：sha256(C 連續原生位元組)。"""
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


_PRODUCTION_LABELS: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}


def production_label_record(cell: Mapping[str, Any]) -> Dict[str, Any]:
    """收據格（`cell_id`／`input`／`symbol`／`timeframes`／`kind`）之標籤出處，經生產 factory adapter 獨立重算（規格審查 r22
    CODEX-R22-P1-02；判準 v8 `label_provenance.window_rule`／`hash_rule`）：來源＝判準 `kline_source`（主週期）、
    `create_feature_factory(cache_dir=來源目錄)._layer0_data_ingestion` 讀窗、`_derive_row_index_for_artifact` 取時間軸、
    標籤＝IC-first 同一構造 `close.pct_change().shift(-1)`（`feature_factory.py:2920`）。窗：(ii)＝`estimate.cell_window`；
    (i)＝來源之該 symbol×tf 前 `icpostleak contract.kline.rows` 根。"""
    from momentum.factories import create_feature_factory

    criteria = load_criteria()
    est = probe("estimate")
    symbol, tf, kind = str(cell["symbol"]), str(cell["timeframes"][0]), str(cell["input"])
    memo = (str(cell["cell_id"]), kind, criteria_sha256(), nh.kline_dataset_sha256(est.kline_source(tf, criteria), symbol, tf))
    if memo in _PRODUCTION_LABELS:
        return dict(_PRODUCTION_LABELS[memo])
    source = est.kline_source(tf, criteria)
    probe_cell = {"id": str(cell["cell_id"]), "kind": str(cell.get("kind") or "A"), "symbol": symbol, "timeframes": [tf]}
    if kind == "ii":
        start, end = est.cell_window(probe_cell, criteria)
    else:
        import h5py

        rows = int(icpostleak_contract()["kline"]["rows"])
        with h5py.File(str(source), "r") as handle:
            stamps = handle[symbol][tf]["data"]["timestamp"]
            assert stamps.shape[0] >= rows, f"{symbol}/{tf} 根數 {stamps.shape[0]} < 輸入 (i) {rows}"
            first, last = int(stamps[0]), int(stamps[rows - 1])
        unit = "ms" if last > 10 ** 12 else "s"
        start = pd.Timestamp(first, unit=unit, tz="UTC").isoformat()
        end = pd.Timestamp(last, unit=unit, tz="UTC").isoformat()
    continuity = est.continuity_plan(probe_cell, criteria, [tf])
    factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=continuity["validate_continuity"])
    kline = factory._layer0_data_ingestion(symbol, tf, factory._resolve_config(None), start_date=start, end_date=end)
    index = factory._derive_row_index_for_artifact(kline)
    assert index is not None, f"{symbol}/{tf}：生產 adapter 取不到時間軸"
    close = pd.Series(kline["close"].to_numpy(dtype=np.float64), index=index)
    label = close.pct_change().shift(-1)
    stamps_ns = np.asarray(index.asi8, dtype=np.int64)
    record = {"cache_dir": str(source.parent.relative_to(REPO)),
              "source_sha256": nh.kline_dataset_sha256(source, symbol, tf),
              "output_start": start, "output_end": end, "rows": int(len(index)),
              "timestamp_sha256": _array_sha256(stamps_ns), "close_sha256": _array_sha256(close.to_numpy(np.float64)),
              "frame_index_sha256": _array_sha256(stamps_ns), "label_sha256": _array_sha256(label.to_numpy(np.float64))}
    _PRODUCTION_LABELS[memo] = dict(record)
    return record


def label_provenance_violations() -> List[str]:
    """判準 v8 `label_provenance`（規格審查 r18 X18-B；r22 CODEX-R22-P1-02）：每個 (格, 輸入) 恰一筆、鍵恰為 fields、雜湊欄為
    64 位 hex、`production_adapter_equal` 為 true；且各欄（來源目錄、來源資料集、窗起訖、列數、timestamp／close／frame
    索引／標籤雜湊）逐欄等於 `production_label_record` 經生產 adapter 獨立重算者——旗標為受驗結果、不作信任。"""
    spec = _branchdiff_output_spec()["label_provenance"]
    receipt = load_receipt("postic-branchdiff")
    entries = receipt.get(spec["receipt_key"])
    if not isinstance(entries, list) or not entries:
        return [f"收據缺 {spec['receipt_key']}"]
    out: List[str] = []
    fields = list(spec["fields"])
    seen: Set[Tuple[str, str]] = set()
    for entry in entries:
        key = _entry_key(entry)
        if key in seen:
            out.append(f"{key}：label_provenance 重複")
        seen.add(key)
        if sorted(entry) != sorted(fields):
            out.append(f"{key}：鍵 {sorted(entry)} ≠ {sorted(fields)}")
            continue
        for name in fields:
            if name.endswith("_sha256") and not re.fullmatch(r"[0-9a-f]{64}", str(entry[name])):
                out.append(f"{key}：{name} 非 sha256")
        if entry["production_adapter_equal"] is not True:
            out.append(f"{key}：production_adapter_equal＝{entry['production_adapter_equal']!r}（標籤與生產讀取不一致）")
        cell = next((c for c in receipt["cells"] if _entry_key(c) == key), None)
        if cell is None:
            out.append(f"{key}：收據 cells 無此 (格, 輸入)，無從重算")
            continue
        expected = production_label_record(cell)
        for name, value in expected.items():
            same = (pd.Timestamp(entry[name]) == pd.Timestamp(value)) if name in ("output_start", "output_end") \
                else entry[name] == value
            if not same:
                out.append(f"{key}：{name}＝{entry[name]!r} ≠ 生產 adapter 重算 {value!r}")
    want = {_entry_key(c) for c in receipt["cells"]}
    if seen != want:
        out.append(f"label_provenance 之 (格, 輸入) {sorted(seen)} ≠ cells {sorted(want)}")
    return out


def sink_routes_violations() -> List[str]:
    """判準 v8 `sink_routes`（規格審查 r18 X18-B）：registry_sink／registry_sink_sharded 每次執行逐群組有紀錄、鍵含
    fields；輸入 (i) 之 registry_sink_sharded 每筆 shard_stream 為 true；摘要鍵齊。"""
    spec = _branchdiff_output_spec()["sink_routes"]
    receipt = load_receipt("postic-branchdiff")
    entries = receipt.get(spec["receipt_key"])
    out: List[str] = []
    if not isinstance(entries, list) or not entries:
        return [f"收據缺 {spec['receipt_key']}"]
    for entry in entries:
        missing = [f for f in spec["fields"] if f not in entry]
        if missing:
            out.append(f"{entry.get('cell_id')}/{entry.get('input')}/{entry.get('branch')}：缺 {missing}")
    sink_rows = {(str(r["cell_id"]), str(r["input"]), str(r["branch"]), str(r["combo"])) for r in receipt["rows"]
                 if str(r["branch"]) in ("registry_sink", "registry_sink_sharded")}
    covered = {(str(e.get("cell_id")), str(e.get("input")), str(e.get("branch")), str(e.get("combo"))) for e in entries}
    if not sink_rows <= covered:
        out.append(f"sink 分支之列缺路由紀錄：{sorted(sink_rows - covered)[:5]}")
    # 規格審查 r19 CODEX-R19-P1-03：逐群組——sink_routes 依 (格, 輸入, 分支, 組合, 群組) 須恰等於 sink_runs 之展開
    runs = receipt.get(spec["run_inventory_key"])
    run_keys: List[Tuple[str, str, str, str]] = []
    expected_groups: Set[Tuple[str, str, str, str, str]] = set()
    for run in runs if isinstance(runs, list) else []:
        key = (str(run.get("cell_id")), str(run.get("input")), str(run.get("branch")), str(run.get("combo")))
        run_keys.append(key)
        groups = run.get("group_ids")
        if not (isinstance(groups, list) and groups and len(groups) == len(set(groups))):
            out.append(f"{key}：group_ids 須為非空且不重複之清單")
            continue
        expected_groups |= {(*key, str(g)) for g in groups}
    if not isinstance(runs, list) or sorted(run_keys) != sorted(sink_rows):
        out.append(f"{spec['run_inventory_key']} 須對 sink 分支每列恰一筆")
    route_groups = [(str(e.get("cell_id")), str(e.get("input")), str(e.get("branch")), str(e.get("combo")),
                     str(e.get("group_id"))) for e in entries]
    if set(route_groups) != expected_groups or len(route_groups) != len(set(route_groups)):
        out.append(f"sink_routes 之群組≠{spec['run_inventory_key']}：缺 {sorted(expected_groups - set(route_groups))[:3]} "
                   f"多 {sorted(set(route_groups) - expected_groups)[:3]}")
    sharded_i = [e for e in entries if e.get("branch") == "registry_sink_sharded" and e.get("input") == "i"]
    if not sharded_i:
        out.append("輸入 (i) 無 registry_sink_sharded 之路由紀錄")
    elif not all(e.get("shard_stream") is True for e in sharded_i):
        out.append("輸入 (i) 之 registry_sink_sharded 有未實走分片串流之群組")
    summary = receipt.get("sink_routes_summary") or {}
    for name in spec["summary_keys"]:
        if not isinstance(summary.get(name), int) or summary[name] <= 0:
            out.append(f"sink_routes_summary.{name} 缺或非正整數")
    return out


def speed_violations() -> List[str]:
    """每格每可達臂（契約可達條件＋候選臂）具三次牆鐘秒數與其中位數。"""
    receipt = load_receipt("postic-branchdiff")
    contract = nh.contract_for_receipt(nh.NUMVIEW_CONTRACT_PATH, receipt)
    candidate = probe("postic_branchdiff").CANDIDATE_ARM
    speed: Dict[Tuple[str, str, str], Mapping[str, Any]] = {}
    out: List[str] = []
    for entry in receipt.get("speed") or []:
        key = (str(entry.get("cell_id")), str(entry.get("input")), str(entry.get("arm")))
        if key in speed:
            out.append(f"速度列重複：{key}")
        speed[key] = entry
    checked = 0
    for cell in receipt["cells"]:
        if int(cell["columns"]) < 1:
            continue
        for arm in reachable_by_contract(contract, int(cell["columns"])) + [candidate]:
            key = (*_entry_key(cell), arm)
            entry = speed.get(key)
            checked += 1
            if entry is None:
                out.append(f"{key}: 缺速度列")
                continue
            seconds = entry.get("seconds")
            if not (isinstance(seconds, list) and len(seconds) == 3
                    and all(isinstance(s, (int, float)) and math.isfinite(s) and s > 0 for s in seconds)):
                out.append(f"{key}: seconds 須為三個正有限秒數，實得 {seconds!r}")
                continue
            if entry.get("median_seconds") != statistics.median(seconds):
                out.append(f"{key}: median_seconds ≠ 三次之中位數")
    if checked == 0:
        out.append("無任何可檢之速度列 ⇒ 空轉")
    return out


def test_postic_branchdiff_receipt_rc_and_criteria() -> None:
    """Task 1.1 驗證：收據 rc=0、`criteria_sha256` 相符。"""
    assert _receipt_common_violations(load_receipt("postic-branchdiff")) == []


def test_postic_branchdiff_rows_cells_times_branches_times_seven() -> None:
    """Task 1.1 驗證：每格每臂每組合一列（列數＝Σ_(格, 輸入) 該輸入分支數×7，判準 v8 起分支依輸入）。"""
    assert branchdiff_rows_violations() == []


def test_postic_branchdiff_speed_fields_present() -> None:
    """Task 1.1 驗證：每格每臂具速度欄（三次牆鐘與中位數，缺即紅）。"""
    assert speed_violations() == []


def test_postic_branchdiff_reproduces_legacy_optimized_zero_diff() -> None:
    """Task 1.1 驗證：ICPOSTLEAK 輸入集格（契約 `kline` 之 symbol／timeframe）輸入 (i) 之 legacy 對 optimized 七組合皆 0 差；
    所重現之 10-02 收據 optimized 七列確為 0 差。"""
    icpl = icpostleak_contract()
    symbol, tf = str(icpl["kline"]["symbol"]), str(icpl["kline"]["timeframe"])
    assert tf in kline_inventory().get(symbol, {}), f"{symbol}/{tf} 不在 kline_cache.h5"
    combos = combo_names()
    old = _json(BRANCHDIFF_1002_PATH)
    old_opt = {r["combo"]: r for r in old["rows"] if r["branch"] == "optimized"}
    assert set(old_opt) == set(combos) and all(r["diff_cells"] == 0 for r in old_opt.values())
    rows = [r for r in load_receipt("postic-branchdiff").get("reproduction") or []
            if r.get("symbol") == symbol and list(r.get("timeframes") or []) == [tf] and r.get("input") == "i"]
    assert sorted(r["combo"] for r in rows) == sorted(combos), rows
    for r in rows:
        assert r["diff_cells"] == 0 and r["nan_mask_diff"] == 0 and r["max_abs_diff"] == 0.0, r


def test_postic_branchdiff_definition_conventions_listed() -> None:
    """SPEC Task 0.6（定義差異須另列，不混入浮點誤差）：收據 `definition_conventions` 列常數窗與 zscore 最少有效值數兩項；
    registry 系分支（ICPOSTLEAK 契約 entry 非 transform）之列，其定義差異格數不少於同 (格, 輸入, 組合) 之非 registry 分支
    （registry 系另含 zscore 最少有效值數之格）。"""
    receipt = load_receipt("postic-branchdiff")
    assert {"constant_window", "zscore_min_valid"} <= set(receipt.get("definition_conventions") or {})
    branches = icpostleak_contract()["branches"]
    registry = {b for b, spec in branches.items() if spec["entry"] != "transform"}
    by_key: Dict[Tuple[str, str, str], Dict[str, int]] = {}
    for row in receipt["rows"]:
        by_key.setdefault((str(row["cell_id"]), str(row["input"]), str(row["combo"])), {})[str(row["branch"])] = \
            int(row.get("definition_cells") or 0)
    checked = strict = 0
    for key, cells in by_key.items():
        plain = [v for b, v in cells.items() if b not in registry]
        for b, v in cells.items():
            if b in registry and plain:
                assert v >= max(plain), (key, b, v, plain)
                checked += 1
                strict += int(v > max(plain))
    assert checked >= 1
    assert strict >= 1, "registry 系無任一列多出 zscore 最少有效值數之定義差異格（未重分類？）"


def test_postic_branchdiff_registry_definition_cells_causally_zero() -> None:
    """審碼 b2 r6 CODEX-R6-P1-01：registry 系列之 zscore 最少有效值數定義差異格，逐格核對 registry 輸出確為該約定之 0
    （`registry_definition_nonzero`＝0；每列具 `registry_definition_cells`）；且至少一列有此類格（防空轉）。門檻錯置（多列有效值
    數 ≥ 該路徑最少值數之格）⇒ 格內輸出非 0 ⇒ 紅。"""
    receipt = load_receipt("postic-branchdiff")
    registry = {b for b, spec in icpostleak_contract()["branches"].items() if spec["entry"] != "transform"}
    rows = [r for r in receipt["rows"] if str(r["branch"]) in registry and int(r["columns"]) >= 1]
    assert rows
    for row in rows:
        assert isinstance(row.get("registry_definition_cells"), int), row
        assert row.get("registry_definition_nonzero") == 0, row
    assert any(int(r["registry_definition_cells"]) > 0 for r in rows)


def test_perf_benchmark_receipt_rc_criteria_and_content() -> None:
    """Task 1.1 驗證（效能基準）：`*-numview-perf-benchmark.json` rc=0、`criteria_sha256` 相符；內容合
    `numview_helpers.perf_benchmark_receipt_violations`（判準 `run_coverage.perf_benchmark` 之格、契約臂＋候選臂、可達臂三次
    牆鐘與中位數、Polars 慢因剖析之逐步驟耗時與 rank UDF 是否逐欄 Python 迴圈；缺即紅）。"""
    receipt = load_receipt("perf-benchmark")
    assert _receipt_common_violations(receipt) == []
    assert nh.perf_benchmark_receipt_violations(receipt) == []


def test_postic_branchdiff_label_provenance_matches_production() -> None:
    """Task 1.1（判準 v8 `label_provenance`，規格審查 r18 X18-B）：每個 (格, 輸入) 之標籤出處齊備且與生產讀取逐值相等。"""
    assert label_provenance_violations() == []


def test_postic_branchdiff_sink_routes_recorded() -> None:
    """Task 1.1（判準 v8 `sink_routes`，規格審查 r18 X18-B）：sink 分支逐群組路由齊備、輸入 (i) 之分片分支實走分片串流。"""
    assert sink_routes_violations() == []


def _mutated_branchdiff(monkeypatch: pytest.MonkeyPatch, mutate: Callable[[Dict[str, Any]], None]) -> None:
    mutated = copy.deepcopy(load_receipt("postic-branchdiff"))
    mutate(mutated)
    original = THIS.load_receipt
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(mutated) if kind == "postic-branchdiff"
                        else original(kind))


@pytest.mark.parametrize("mutant", ["adapter_unequal", "label_hash_missing"])
def test_mutation_label_provenance_turns_red(monkeypatch: pytest.MonkeyPatch, mutant: str) -> None:
    """mutation（規格審查 r18 X18-B）：標籤與生產讀取不一致、或標籤雜湊欄缺 ⇒ 標籤出處檢查紅。"""
    def mutate(r: Dict[str, Any]) -> None:
        entry = r["label_provenance"][0]
        if mutant == "adapter_unequal":
            entry["production_adapter_equal"] = False
        else:
            entry.pop("label_sha256")
    _mutated_branchdiff(monkeypatch, mutate)
    assert label_provenance_violations() != []


def test_mutation_sink_route_sharded_not_streamed_turns_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（規格審查 r18 X18-B）：輸入 (i) 之 registry_sink_sharded 有群組未實走分片串流 ⇒ 路由檢查紅。"""
    def mutate(r: Dict[str, Any]) -> None:
        next(e for e in r["sink_routes"] if e["branch"] == "registry_sink_sharded" and e["input"] == "i")["shard_stream"] = False
    _mutated_branchdiff(monkeypatch, mutate)
    assert any("分片串流" in v for v in sink_routes_violations())


def test_mutation_branchdiff_input_ii_excluded_branch_turns_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（規格審查 r18 X18-A）：輸入 (ii) 多跑判準 v8 排除之分支（registry_sink_sharded）⇒ 列檢查紅。"""
    def mutate(r: Dict[str, Any]) -> None:
        extra = [dict(row, branch="registry_sink_sharded") for row in r["rows"]
                 if row["input"] == "ii" and row["branch"] == "registry_sink"]
        r["rows"].extend(extra)
    _mutated_branchdiff(monkeypatch, mutate)
    assert any("非恰一" in v or "列數" in v for v in branchdiff_rows_violations())


def _synthetic_branchdiff_receipt() -> Dict[str, Any]:
    """依判準 v8 合規之合成 Task 1.1 收據（只含 rows／label_provenance／sink_routes／sink_runs 檢查所需欄；每 sink 執行兩群組）。
    供檢查器本身之可證偽測試（規格審查 r19 CODEX-R19-P1-04），不代表任何量測結果。"""
    combos = combo_names()
    cells: List[Dict[str, Any]] = []
    for symbol, tfs in sorted(nh.criteria_symbol_timeframes("A")):
        cells.append({"cell_id": f"i:{symbol}:{'+'.join(tfs)}", "input": "i", "symbol": symbol, "timeframes": list(tfs),
                      "kind": "A", "selected": [], "columns": 6})
    for kind, symbol, tfs in sorted(nh.criteria_run_cell_keys("postic_branchdiff")):
        cells.append({"cell_id": f"ii:{kind}:{symbol}:{'+'.join(tfs)}", "input": "ii", "symbol": symbol,
                      "timeframes": list(tfs), "kind": kind, "selected": [], "columns": 3})
    rows, labels, routes, runs = [], [], [], []
    for c in cells:
        for branch in branches_for_input(c["input"]):
            for combo in combos:
                rows.append({"cell_id": c["cell_id"], "input": c["input"], "branch": branch, "combo": combo,
                             "columns": c["columns"]})
                if branch in ("registry_sink", "registry_sink_sharded"):
                    runs.append({"cell_id": c["cell_id"], "input": c["input"], "branch": branch, "combo": combo,
                                 "group_ids": ["g1", "g2"]})
                    routes += [{"cell_id": c["cell_id"], "input": c["input"], "branch": branch, "combo": combo,
                                "group_id": g, "mode": "replace", "shards": 3, "requires_slow": False, "is_chunked": False,
                                "shard_stream": branch == "registry_sink_sharded", "group_arm": "arm", "status": "ok"}
                               for g in ("g1", "g2")]
        labels.append({"cell_id": c["cell_id"], "input": c["input"], **production_label_record(c),
                       "production_adapter_equal": True})
    return {"branches": expected_branches(), "cells": cells, "rows": rows, "label_provenance": labels,
            "sink_routes": routes, "sink_runs": runs,
            "sink_routes_summary": {"production_shard_bytes": 33554432, "input_ii_group_bytes": 6386000}}


def _synthetic_mutant(receipt: Dict[str, Any], mutant: str) -> None:
    sharded_i = [e for e in receipt["sink_routes"] if e["branch"] == "registry_sink_sharded" and e["input"] == "i"]
    if mutant == "adapter_unequal":
        receipt["label_provenance"][0]["production_adapter_equal"] = False
    elif mutant == "label_hash_missing":
        receipt["label_provenance"][0].pop("label_sha256")
    elif mutant == "label_forged_flag_true":  # r22 CODEX-R22-P1-02 原例：來源與雜湊皆假、旗標仍 true
        receipt["label_provenance"][0].update({
            "cache_dir": "/tmp/not-the-production-source", "source_sha256": "0" * 64, "timestamp_sha256": "1" * 64,
            "close_sha256": "2" * 64, "frame_index_sha256": "3" * 64, "label_sha256": "4" * 64,
            "production_adapter_equal": True})
    elif mutant == "label_hash_tampered":
        receipt["label_provenance"][-1]["label_sha256"] = "f" * 64
    elif mutant == "label_window_shifted":
        receipt["label_provenance"][-1]["output_end"] = receipt["label_provenance"][0]["output_end"] \
            if receipt["label_provenance"][0]["output_end"] != receipt["label_provenance"][-1]["output_end"] \
            else "2000-01-01T00:00:00+00:00"
    elif mutant == "sharded_not_streamed":
        sharded_i[0]["shard_stream"] = False
    elif mutant == "ii_extra_branch":
        receipt["rows"] += [dict(r, branch="registry_sink_sharded") for r in receipt["rows"]
                            if r["input"] == "ii" and r["branch"] == "registry_sink"]
    elif mutant == "ii_missing_branch":
        receipt["rows"] = [r for r in receipt["rows"] if not (r["input"] == "ii" and r["branch"] == "legacy")]
    elif mutant == "route_group_missing":
        receipt["sink_routes"].remove(next(e for e in receipt["sink_routes"] if e["group_id"] == "g2"))
    elif mutant == "route_group_extra":
        receipt["sink_routes"].append(dict(receipt["sink_routes"][0], group_id="g3"))


#: 合成收據各 mutant 應使之紅之檢查器（rows／label／sink）
_SYNTHETIC_MUTANT_RED = {"adapter_unequal": "label", "label_hash_missing": "label", "label_forged_flag_true": "label",
                         "label_hash_tampered": "label", "label_window_shifted": "label", "sharded_not_streamed": "sink",
                         "ii_extra_branch": "rows", "ii_missing_branch": "rows", "route_group_missing": "sink",
                         "route_group_extra": "sink"}


@pytest.mark.parametrize("mutant", [None, *_SYNTHETIC_MUTANT_RED])
def test_v8_branchdiff_checkers_on_synthetic_receipt(monkeypatch: pytest.MonkeyPatch, mutant: Optional[str]) -> None:
    """規格審查 r19 CODEX-R19-P1-04：判準 v8 之 Task 1.1 收據檢查器（`branchdiff_rows_violations`、
    `label_provenance_violations`、`sink_routes_violations`）以合成收據自證——合規收據三者皆無違規（列數＝Σ_(格, 輸入) 該輸入
    分支數×7）；每個 mutant 使其對應之檢查器紅、其餘不受牽連之檢查器維持綠（label／sink 變異不影響列檢查）。"""
    receipt = _synthetic_branchdiff_receipt()
    if mutant is not None:
        _synthetic_mutant(receipt, mutant)
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(receipt) if kind == "postic-branchdiff"
                        else pytest.fail(f"未預期讀取 {kind}"))
    result = {"rows": branchdiff_rows_violations(), "label": label_provenance_violations(),
              "sink": sink_routes_violations()}
    if mutant is None:
        assert result == {"rows": [], "label": [], "sink": []}, result
        want = sum(len(branches_for_input(c["input"])) for c in receipt["cells"]) * len(combo_names())
        assert len(receipt["rows"]) == want
        return
    assert result[_SYNTHETIC_MUTANT_RED[mutant]], (mutant, result)
    if _SYNTHETIC_MUTANT_RED[mutant] != "rows":
        assert result["rows"] == [], (mutant, result)


def test_postic_branchdiff_candidate_intermediate_dtypes_float64() -> None:
    """Task 1.1（R10-A）：候選臂 `polars_float64` 之中間 dtype 於每個有欄之格記 ≥3 處、皆 float64。"""
    receipt = load_receipt("postic-branchdiff")
    points: Dict[Tuple[str, str], Dict[str, str]] = {}
    for entry in receipt.get("candidate_intermediate_dtypes") or []:
        points.setdefault(_entry_key(entry), {})[str(entry["point"])] = str(entry["dtype"])
    checked = 0
    for cell in receipt["cells"]:
        if int(cell["columns"]) < 1:
            continue
        got = points.get(_entry_key(cell), {})
        assert len(got) >= 3, f"{_entry_key(cell)}: 中間 dtype 記錄點 {sorted(got)} 不足 3"
        assert all(d.lower() == "float64" for d in got.values()), (_entry_key(cell), got)
        checked += 1
    assert checked >= 1


#: 候選臂數值保真自檢點（審碼 b2 r1 CODEX-R1-P1-01／GROK-R1-P1-01、P1-02；`postic_branchdiff._candidate_fidelity`）
CANDIDATE_FIDELITY_POINTS = ("fidelity_roundtrip", "fidelity_mask", "fidelity_gaussian_rank", "fidelity_zscore")


def test_postic_branchdiff_candidate_value_fidelity_points() -> None:
    """Task 1.1（R10-A／R11-A；審碼 b2 r1）：候選臂每個有欄之格皆具三個數值保真自檢點且皆 float64（dtype 字串不足以證
    全程 Float64：出口轉換與 gaussian 內部 rank 曾於字串仍為 Float64 時把值截為 float32）。"""
    receipt = load_receipt("postic-branchdiff")
    points: Dict[Tuple[str, str], Dict[str, str]] = {}
    for entry in receipt.get("candidate_intermediate_dtypes") or []:
        points.setdefault(_entry_key(entry), {})[str(entry["point"])] = str(entry["dtype"])
    checked = 0
    for cell in receipt["cells"]:
        if int(cell["columns"]) < 1:
            continue
        got = points.get(_entry_key(cell), {})
        assert {p: got.get(p) for p in CANDIDATE_FIDELITY_POINTS} == {p: "float64" for p in CANDIDATE_FIDELITY_POINTS}, \
            (_entry_key(cell), got)
        checked += 1
    assert checked >= 1


# ---------------------------------------------------------------------------------------------- 真實向量

_REAL: Dict[str, Any] = {}


def real_log_returns() -> np.ndarray:
    """真實 BTCUSDT 1h close 之對數報酬（float64）。"""
    if "ret" not in _REAL:
        close = fsh.kline_frame()["close"].to_numpy(dtype=np.float64)
        ret = np.diff(np.log(close))
        assert ret.size > 5000 and np.isfinite(ret).all()
        _REAL["ret"] = ret
    return _REAL["ret"].copy()


def real_ic_vector(n: int = 8) -> np.ndarray:
    """真實 IC 向量：落後 k 根之報酬對次根報酬之 Spearman 相關（k=0..n-1），彼此相異且有限。"""
    if "ic" not in _REAL:
        r = pd.Series(real_log_returns())
        fwd = r.shift(-1)
        ics = np.array([r.shift(k).corr(fwd, method="spearman") for k in range(n)], dtype=np.float64)
        assert np.isfinite(ics).all() and len(set(ics.tolist())) == n, ics
        _REAL["ic"] = ics
    return _REAL["ic"].copy()


def boundary15_cases() -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    ic = real_ic_vector()
    tie = np.full_like(ic, ic[0])
    lt2_ref = ic.copy()
    lt2_ref[1:] = np.nan
    return {"all_ties": (tie, tie.copy()),
            "all_nan": (np.full_like(ic, np.nan), np.full_like(ic, np.nan)),
            "lt2_valid_pairs": (lt2_ref, ic * 0.5)}


def boundary15_violations(case: str) -> List[str]:
    """τ-b 未定義案 ⇒ `tau_b` 為 NaN、`material` True、`reason` 非空（經 `postic_branchdiff.ic_material` 模組屬性呼叫）。"""
    ref, var = boundary15_cases()[case]
    result = probe("postic_branchdiff").ic_material(ref.tolist(), var.tolist())
    out: List[str] = []
    if not _is_nan_or_none(result.get("tau_b")):
        out.append(f"{case}: tau_b={result.get('tau_b')!r} 應為 NaN")
    if result.get("material") is not True:
        out.append(f"{case}: material={result.get('material')!r} 應為 True（fail-closed）")
    if not (isinstance(result.get("reason"), str) and result["reason"]):
        out.append(f"{case}: 缺 reason")
    return out


def _tau_lt_1_variant(ic_reference: Sequence[float], ic_variant: Sequence[float]) -> Dict[str, Any]:
    """mutant：以 `tau < 1` 判翻轉（NaN < 1 為 False ⇒ 未定義之 τ-b 被判未翻轉）。"""
    from scipy.stats import kendalltau

    ref = np.asarray(ic_reference, dtype=np.float64)
    var = np.asarray(ic_variant, dtype=np.float64)
    mask = np.isfinite(ref) & np.isfinite(var)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tau = float(kendalltau(ref[mask], var[mask]).correlation) if mask.sum() >= 2 else float("nan")
    flips = int(np.sum(np.sign(ref[mask]) != np.sign(var[mask])))
    return {"tau_b": tau, "sign_flips": flips, "material": bool(flips > 0 or tau < 1), "reason": "tau<1"}


def test_ic_material_identical_and_flipped_real_ic() -> None:
    """Task 1.1 判定之對照：真實 IC 向量對自身 ⇒ τ-b＝1、無翻轉、非 material；一欄正負號翻轉 ⇒ material（防恆 True）。"""
    ic = real_ic_vector()
    same = probe("postic_branchdiff").ic_material(ic.tolist(), ic.tolist())
    assert math.isclose(float(same["tau_b"]), 1.0, rel_tol=0, abs_tol=1e-12)
    assert same["sign_flips"] == 0 and same["material"] is False
    flipped = ic.copy()
    flipped[0] = -flipped[0]
    changed = probe("postic_branchdiff").ic_material(ic.tolist(), flipped.tolist())
    assert changed["sign_flips"] == 1 and changed["material"] is True


def test_boundary_13_near_zero_reference_excluded_from_rel() -> None:
    """邊界①（SPEC Task 1.1）：近零參照值（|ref| < float32 tiny）⇒ 不計相對差、另列絕對差。`cell_diff` 於真實對數報酬
    （近零格與 NaN 遮罩差另行設置）之輸出等於測試端獨立重算；收據每列具近零欄。"""
    ref = real_log_returns()
    tiny = float(np.finfo(np.float32).tiny)
    near_idx = np.arange(10, ref.size, 397)
    ref[near_idx] = tiny * 0.25
    ref[near_idx[0]] = 0.0
    ref[[3, 4]] = np.nan
    out = ref.astype(np.float32).astype(np.float64)
    out[near_idx] = ref[near_idx] + 1e-9
    out[[3, 4]] = np.nan
    out[[20, 21]] = np.nan
    result = probe("postic_branchdiff").cell_diff(ref, out)
    both = np.isfinite(ref) & np.isfinite(out)
    diff = np.abs(out - ref)
    near = both & (np.abs(ref) < tiny)
    far = both & ~near
    assert near[near_idx].all(), "前提：植入之近零格須為近零"
    assert int(result["near_zero_cells"]) == int(near.sum()) >= near_idx.size
    assert math.isclose(float(result["near_zero_max_abs"]), float(diff[near].max()), rel_tol=1e-12)
    assert math.isclose(float(result["max_rel"]), float((diff[far] / np.abs(ref[far])).max()), rel_tol=1e-12)
    assert float(result["max_rel"]) < 1.0, "近零格被計入相對差"
    assert math.isclose(float(result["max_abs"]), float(diff[both].max()), rel_tol=1e-12)
    finite_diff = diff[both]
    assert np.quantile(finite_diff, 0.99, method="lower") <= float(result["p99_abs"]) <= \
        np.quantile(finite_diff, 0.99, method="higher")
    assert int(result["nan_mask_diff"]) == int((np.isnan(ref) != np.isnan(out)).sum()) == 2
    checked = 0
    for row in load_receipt("postic-branchdiff")["rows"]:
        if int(row["columns"]) < 1:
            continue
        checked += 1
        assert isinstance(row.get("near_zero_cells"), int) and row["near_zero_cells"] >= 0, row
        assert "near_zero_max_abs" in row, row
        if row["near_zero_cells"] > 0:
            assert isinstance(row["near_zero_max_abs"], float) and math.isfinite(row["near_zero_max_abs"]), row
    assert checked >= 1


def test_boundary_14_all_ratio_unsafe_cell_zero_columns_not_material() -> None:
    """邊界②（SPEC Task 1.1）：輸入 (ii) 之每格「記錄欄數＝其選欄經 IC 頁同一 ratio-unsafe 剔除後之欄數」（雙向：全為
    ratio-unsafe ⇔ 記零欄）；零欄格之每列 `material` 為 False 且附原因。對全部 (ii) 格逐格驗。"""
    receipt = load_receipt("postic-branchdiff")
    zero_cells: Set[Tuple[str, str]] = set()
    evaluated = 0
    for cell in receipt["cells"]:
        if cell["input"] != "ii":
            continue
        evaluated += 1
        kept = kept_columns(cell["selected"])
        assert int(cell["columns"]) == len(kept), f"{_entry_key(cell)}: 記錄欄數 {cell['columns']} ≠ 剔除後 {len(kept)}"
        if not kept:
            zero_cells.add(_entry_key(cell))
    assert evaluated >= 1
    for row in receipt["rows"]:
        if (str(row["cell_id"]), str(row["input"])) in zero_cells:
            assert int(row["columns"]) == 0 and row["material"] is False and row.get("material_reason"), row


@pytest.mark.parametrize("case", ["all_ties", "all_nan", "lt2_valid_pairs"])
def test_boundary_15_undefined_tau_b_is_material(case: str) -> None:
    """邊界③（SPEC Task 1.1、R2-D）：IC 全 ties／全 NaN／有效對數 < 2 ⇒ τ-b 為 NaN ⇒ `material` True 並記原因（真實 IC 向量
    構造）；收據中 τ-b 非有限之列皆 material 且具原因。"""
    assert boundary15_violations(case) == []
    for row in load_receipt("postic-branchdiff")["rows"]:
        if int(row["columns"]) >= 1 and _is_nan_or_none(row.get("tau_b")):
            if (row.get("material_reason") == "identical_all_nan" and row.get("finite_cells") == 0
                    and row.get("nan_mask_diff") == 0 and (row.get("all_cells") or {}).get("nan_mask_diff") == 0):
                # 判準 v9 `material.identical_all_nan`（SPEC Task 1.1 邊界④）：參照與變體皆全 NaN ⇒ 非 material
                assert row["material"] is False, row
                continue
            assert row["material"] is True and row.get("material_reason"), row


def test_mutation_branchdiff_receipt_missing_speed_turns_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC §V「Task 1.1 收據缺速度欄」）：刪一筆速度列之 `seconds` ⇒ 速度檢查紅。"""
    mutated = copy.deepcopy(load_receipt("postic-branchdiff"))
    assert mutated.get("speed"), "收據無速度列 ⇒ mutation 無對象"
    mutated["speed"][0].pop("seconds", None)
    original = THIS.load_receipt
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(mutated) if kind == "postic-branchdiff"
                        else original(kind))
    assert any("seconds" in v for v in speed_violations())


def test_mutation_ic_material_tau_lt_1_flips_boundary_15(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC §V「τ-b 判定改為 `tau < 1`」）：`ic_material` 換成 `tau < 1` 版 ⇒ 邊界 15 之檢查於三案皆翻紅。"""
    monkeypatch.setattr(probe("postic_branchdiff"), "ic_material", _tau_lt_1_variant)
    for case in boundary15_cases():
        assert any("material" in v for v in boundary15_violations(case)), case


# ============================================================================================== Task 1.2

def precision_completeness_violations() -> List[str]:
    """段 × 格完整：格涵蓋＝格 A∪B∪C 列舉；blocked 格每段 ≥1 列；measured 格之 S0–S4 依格類分支（SPEC v37 驗證段）——
    逐欄格：該段逐欄列之欄集合＝該格該段欄（`columns_by_segment`，缺則 `columns`）；群組粒度格（`numview_helpers.
    GROUP_GRANULARITY_KINDS`）：該段有期望群組（`expected_groups`）者，每 (`source_run`, 群組) 恰一列、群組集合恰等、每列
    `columns_in_group` 等於期望、欄數合計等於期望合計；無期望群組之段（掛點同 A 不量）須具列。S5 ≥1 列。
    判準 v3 起：格涵蓋＝判準 `run_coverage.precision_chain` 之格（變體宿主格＋格 B＋格 C）。"""
    receipt = load_receipt("precision-chain")
    out: List[str] = []
    cells = {cell_key(c): c for c in receipt["cells"]}
    want = (nh.criteria_run_cell_keys("precision_chain") if nh.criteria_cell_list() is not None
            else enumerate_keys(("A", "B", "C")))
    if set(cells) != want:
        out.append(f"格涵蓋 ≠ A∪B∪C：缺 {sorted(want - set(cells))[:5]} 多 {sorted(set(cells) - want)[:5]}")
    rows: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for row in receipt["rows"]:
        rows.setdefault((str(row["segment"]), str(row["cell_id"])), []).append(row)
    for cell in cells.values():
        cid = str(cell["cell_id"])
        for seg in nh.precision_segments(cid, SEGMENTS):  # 判準 v4：只生成之格 C 無 S5（GROK-R8-P1-01）
            got = rows.get((seg, cid), [])
            if not got:
                out.append(f"{cid}/{seg}: 無列")
                continue
            if cell["status"] != "measured" or seg not in PER_COLUMN_SEGMENTS:
                continue
            if str(cell["kind"]) in nh.GROUP_GRANULARITY_KINDS:
                expected = (cell.get("expected_groups") or {}).get(seg)
                if seg in ("S3", "S4"):  # 審碼 r24：期望群組不得只信收據自報——等於凍結 manifest 群組（獨立來源）
                    canonical = probe("precision_chain").canonical_c_groups(cid)
                    if {str(g): int(n) for g, n in (expected or {}).items()} != canonical:
                        out.append(f"{cid}/{seg}: 期望群組 ≠ 凍結 manifest 群組")
                        continue
                elif seg == "S0" and not expected:  # measured 群組粒度格之 S0 期望群組不得缺或空
                    out.append(f"{cid}/{seg}: 期望群組缺或空")
                    continue
                if expected is None:
                    continue
                keys = [(str(r.get("source_run")), str(r.get("group"))) for r in got]
                if len(keys) != len(set(keys)):
                    out.append(f"{cid}/{seg}: (source_run, 群組) 重複")
                groups = [str(r.get("group")) for r in got]
                if sorted(groups) != sorted(expected):
                    out.append(f"{cid}/{seg}: 群組集合 ≠ 期望（缺 {sorted(set(expected) - set(groups))[:3]} 多 "
                               f"{sorted(set(groups) - set(expected))[:3]}）")
                for r in got:
                    if str(r.get("group")) in expected and r.get("columns_in_group") != int(expected[str(r["group"])]):
                        out.append(f"{cid}/{seg}: 群組 {r.get('group')} 欄數 {r.get('columns_in_group')} ≠ 期望")
                if sum(int(r.get("columns_in_group") or 0) for r in got) != sum(int(v) for v in expected.values()):
                    out.append(f"{cid}/{seg}: 群組欄數合計 ≠ 期望合計")
            else:
                names = [str(r["column"]) for r in got]
                expected_cols = (cell.get("columns_by_segment") or {}).get(seg, cell["columns"])
                if not expected_cols or sorted(names) != sorted(str(c) for c in expected_cols):
                    out.append(f"{cid}/{seg}: 逐欄列之欄集合 ≠ 該格欄")
    return out


def test_precision_chain_receipt_rc_and_criteria() -> None:
    """Task 1.2 驗證：收據 rc=0、`criteria_sha256` 相符。"""
    assert _receipt_common_violations(load_receipt("precision-chain")) == []


def test_precision_chain_segments_cells_complete() -> None:
    """Task 1.2 驗證：每段每格逐欄統計列存在（段×格完整）。"""
    assert precision_completeness_violations() == []


def precision_s4_bss_violations(receipt: Mapping[str, Any]) -> List[str]:
    """S4 raw BSS 無損判定之違規：每個 measured 格恰一列；狀態依格類綁定（SPEC v37 細則②：codec 只於 A 格開關量測 ⇒
    A＝measured、B／C＝codec_off，審碼 r19）；measured 列之 `bitwise_equal` 為布林；`lossless_violation` ⇔ 任一 measured
    列不等。"""
    out: List[str] = []
    pc = probe("precision_chain")
    # 審碼 r20：期望狀態以探針之格常數綁定（不讀收據 `kind`，防竄改）；未知格拒收
    expected = {pc.HOST_CELL: "measured", pc.B_CELL: "codec_off", pc.C_CELL: "codec_off"}
    bss = list(receipt.get("s4_raw_bss") or [])
    ids = [str(e.get("cell_id")) for e in bss]
    if len(ids) != len(set(ids)):
        out.append(f"s4_raw_bss 格重複：{ids}")
    status = {str(e.get("cell_id")): e.get("status") for e in bss}
    cells = {str(c["cell_id"]) for c in receipt.get("cells") or [] if c.get("status") == "measured"}
    all_cells = {str(c["cell_id"]) for c in receipt.get("cells") or []}
    if not cells:
        out.append("無 measured 格")
    if set(status) != all_cells:  # blocked 格之 S4 列亦在（如 C 被擋仍記 codec_off）；格集合對收據全部格
        out.append(f"s4_raw_bss 格集合 {sorted(status)} ≠ 收據格 {sorted(all_cells)}")
    for cid in sorted(cells):
        if cid not in expected:
            out.append(f"{cid}：非精度鏈格")
        elif status.get(cid) != expected[cid]:
            out.append(f"{cid}：s4_raw_bss 狀態 {status.get(cid)!r} ≠ {expected[cid]}")
    for cid in sorted(all_cells - cells):  # 審碼 r26：未量測格之 S4 狀態只准 blocked／codec_off
        if cid not in expected:
            out.append(f"{cid}：非精度鏈格")
        elif status.get(cid) not in ("blocked", "codec_off"):
            out.append(f"{cid}（未量測格）：s4_raw_bss 狀態 {status.get(cid)!r} 非 blocked／codec_off")
    entries = [e for e in bss if e.get("status") == "measured"]
    if any(not isinstance(e.get("bitwise_equal"), bool) for e in entries):
        out.append("measured 列之 bitwise_equal 非布林")
    if not entries:
        out.append("無 measured 之 s4_raw_bss 列")
    elif receipt.get("lossless_violation") is not (not all(e.get("bitwise_equal") is True for e in entries)):
        out.append(f"lossless_violation {receipt.get('lossless_violation')!r} 與 measured 列不符")
    return out


def test_precision_chain_s4_raw_bss_lossless_flag() -> None:
    """Task 1.2 驗證：S4 raw BYTE_STREAM_SPLIT 讀回逐位元相等之檢查於每個 measured 格皆有紀錄且狀態依格類；任一不等 ⇔
    `lossless_violation` 為 True。"""
    assert precision_s4_bss_violations(load_receipt("precision-chain")) == []


@pytest.mark.parametrize("mutant", ["a_hidden_as_codec_off", "a_not_equal_flag_false", "b_measured", "c_missing",
                                    "a_equal_none", "a_duplicate", "unknown_row", "kind_swapped",
                                    "blocked_c_unknown_status"])
def test_precision_s4_bss_violations_mutations(mutant: str) -> None:
    """審碼 r19–r20：A 格誤標 codec_off 而 B 誤標 measured（雙錯）、A 不等而旗標 False、B 標 measured、C 缺列、A 之
    bitwise_equal 為 None、A 列重複、多一未知格列、收據 `kind` 互換配合雙錯 ⇒ 各翻紅；合規收據 ⇒ 空。"""
    pc = probe("precision_chain")
    a, b, c = pc.HOST_CELL, pc.B_CELL, pc.C_CELL

    def receipt(a_equal: Any = True, flag: bool = False) -> Dict[str, Any]:
        return {"cells": [{"cell_id": k, "kind": k[0], "status": "measured"} for k in (a, b, c)],
                "s4_raw_bss": [{"cell_id": a, "status": "measured", "bitwise_equal": a_equal},
                               {"cell_id": b, "status": "codec_off", "bitwise_equal": None},
                               {"cell_id": c, "status": "codec_off", "bitwise_equal": None}],
                "lossless_violation": flag}
    assert precision_s4_bss_violations(receipt()) == []
    assert precision_s4_bss_violations(receipt(a_equal=False, flag=True)) == []
    r = receipt()
    if mutant == "a_hidden_as_codec_off":
        r = receipt(a_equal=False)
        r["s4_raw_bss"][0]["status"] = "codec_off"
        r["s4_raw_bss"][1].update(status="measured", bitwise_equal=True)
    elif mutant == "a_not_equal_flag_false":
        r = receipt(a_equal=False)
    elif mutant == "b_measured":
        r["s4_raw_bss"][1].update(status="measured", bitwise_equal=True)
    elif mutant == "c_missing":
        r["s4_raw_bss"].pop()
    elif mutant == "a_equal_none":
        r = receipt(a_equal=None)
    elif mutant == "unknown_row":
        r["s4_raw_bss"].append({"cell_id": "X_unknown", "status": "measured", "bitwise_equal": True})
    elif mutant == "kind_swapped":
        r = receipt(a_equal=False)
        r["cells"][0]["kind"], r["cells"][1]["kind"] = "B", "A"
        r["s4_raw_bss"][0]["status"] = "codec_off"
        r["s4_raw_bss"][1].update(status="measured", bitwise_equal=True)
    elif mutant == "blocked_c_unknown_status":  # 審碼 r26：C 未量測時其 S4 狀態仍須為 blocked／codec_off
        r["cells"][2]["status"] = "blocked"
        r["s4_raw_bss"][2]["status"] = "mystery"
    else:
        r["s4_raw_bss"].append(dict(r["s4_raw_bss"][0]))
    assert precision_s4_bss_violations(r) != []


def test_precision_chain_extension_downgrade_field() -> None:
    """Task 1.2 驗證：延伸格具「降級欄數」欄（預期 0；非 0 即為新證據並標 `new_evidence`）。"""
    extension = load_receipt("precision-chain")["extension"]
    assert extension, "無延伸格紀錄"
    for entry in extension:
        assert isinstance(entry["downgraded_columns"], int) and entry["downgraded_columns"] >= 0, entry
        assert entry["new_evidence"] is (entry["downgraded_columns"] > 0), entry


def test_boundary_16_all_nan_column_marked_no_error() -> None:
    """邊界①（SPEC Task 1.2）：全 NaN 欄 ⇒ `checkpoint_stats` 標 `all_nan`、不計誤差（`max_abs`／`max_rel` 為 None）、
    float16 判定恆可；對照：同一真實欄非 NaN ⇒ 非 all_nan、`max_abs` 等於獨立重算。收據中 all_nan 之列皆不計誤差。"""
    close = fsh.kline_frame()["close"].to_numpy(dtype=np.float64)
    stats = probe("precision_chain").checkpoint_stats
    nan_col = np.full_like(close, np.nan)
    result = stats(nan_col.astype(np.float32), nan_col)
    assert result["all_nan"] is True and result["max_abs"] is None and result["max_rel"] is None
    assert result["float16_ok"] is True
    control = stats(close.astype(np.float32), close)
    assert control["all_nan"] is False
    assert math.isclose(float(control["max_abs"]), float(np.abs(close.astype(np.float32).astype(np.float64) - close).max()),
                        rel_tol=1e-12)
    for row in load_receipt("precision-chain")["rows"]:
        if row.get("all_nan") is True:
            assert row.get("max_abs") is None and row.get("max_rel") is None, row


def test_boundary_17_codec_fallback_counted_with_reasons() -> None:
    """邊界②（SPEC Task 1.2）：codec 回退 zstd 之欄逐筆列原因；每個 measured 格之 `codec_fallback_count` 等於該格回退列數
    （對全部 measured 格驗）。"""
    receipt = load_receipt("precision-chain")
    fallbacks = receipt["codec_fallbacks"]
    for entry in fallbacks:
        assert isinstance(entry.get("reason"), str) and entry["reason"] and entry.get("column"), entry
    evaluated = 0
    for cell in receipt["cells"]:
        if cell["status"] != "measured":
            continue
        evaluated += 1
        count = sum(1 for e in fallbacks if str(e["cell_id"]) == str(cell["cell_id"]))
        assert cell["codec_fallback_count"] == count, cell["cell_id"]
    assert evaluated >= 1


def test_boundary_18_blocked_cell_c_all_segments_blocked() -> None:
    """邊界③（SPEC Task 1.2）：格 C（及任一 blocked 格）blocked ⇒ 該格每段皆有 blocked 列且無任何數值（不以格 A 外推冒充）；
    measured 格無 blocked 列。對全部格 C 驗（格 C＝每個 symbol×tf，列舉自 kline_cache.h5）。"""
    receipt = load_receipt("precision-chain")
    rows: Dict[str, List[Mapping[str, Any]]] = {}
    for row in receipt["rows"]:
        rows.setdefault(str(row["cell_id"]), []).append(row)
    c_cells = [c for c in receipt["cells"] if c["kind"] == "C"]
    assert {cell_key(c) for c in c_cells} == enumerate_keys(("C",))
    for cell in receipt["cells"]:
        assert cell["status"] in ("measured", "blocked"), cell
        got = rows.get(str(cell["cell_id"]), [])
        if cell["status"] == "blocked":
            # 判準 v4：只生成之格 C 之段集合依判準 segments（S0–S4，審查 r9 GROK-R9-P1-01）；其餘格仍為全段
            if list(nh.precision_segments(str(cell["cell_id"]), SEGMENTS)) != list(SEGMENTS):
                assert {str(r["segment"]) for r in got} == set(nh.precision_segments(str(cell["cell_id"]), SEGMENTS)), \
                    cell["cell_id"]
            else:
                assert {str(r["segment"]) for r in got} == set(SEGMENTS), cell["cell_id"]
            for r in got:
                assert r["status"] == "blocked" and r.get("max_abs") is None and r.get("max_rel") is None, r
        else:
            assert all(r["status"] != "blocked" for r in got), cell["cell_id"]


def test_mutation_precision_chain_segment_row_dropped_turns_completeness_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：自收據刪一段之一列 ⇒ 完整性檢查紅。"""
    mutated = copy.deepcopy(load_receipt("precision-chain"))
    victim = next(i for i, r in enumerate(mutated["rows"]) if r["segment"] in PER_COLUMN_SEGMENTS
                  and r.get("status") != "blocked")
    dropped = mutated["rows"].pop(victim)
    original = THIS.load_receipt
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(mutated) if kind == "precision-chain"
                        else original(kind))
    violations = precision_completeness_violations()
    assert any(str(dropped["cell_id"]) in v and str(dropped["segment"]) in v for v in violations), violations


# ============================================================================================== Task 1.3

def l2_error_violations() -> List[str]:
    """有錯誤之格不得以 0 差計（`f32diff` 須為 None）；`compute_all_polars` 表有而公開類別表無之欄須由錯誤紀錄解釋。"""
    out: List[str] = []
    for cell in load_receipt("l2-arm-matrix")["cells"]:
        cid = str(cell["cell_id"])
        errors = cell.get("errors") or []
        if errors and cell.get("f32diff") is not None:
            out.append(f"{cid}: 有錯誤卻記 f32diff={cell.get('f32diff')!r}")
        if (cell.get("only_returned") or []) and not errors:
            out.append(f"{cid}: 類別表缺欄而無錯誤紀錄")
        for err in errors:
            if not (err.get("category") and err.get("error")):
                out.append(f"{cid}: 錯誤紀錄缺 category／error")
    return out


def test_l2_matrix_receipt_rc_and_criteria() -> None:
    """Task 1.3 驗證：收據 rc=0、`criteria_sha256` 相符。"""
    assert _receipt_common_violations(load_receipt("l2-arm-matrix")) == []


def test_l2_matrix_cells_equal_a_plus_b() -> None:
    """Task 1.3 驗證：格數＝格 A＋格 B 全部（列舉自 kline_cache.h5）。判準 v3 起：格＝判準 `run_coverage.l2_arm_matrix`
    之格（`A:BTCUSDT:1h`、格 B、格 C，另 `A:BTCUSDT:12h` 重現 freeze-baselines）。"""
    cells = [cell_key(c) for c in load_receipt("l2-arm-matrix")["cells"]]
    assert len(cells) == len(set(cells))
    if nh.criteria_cell_list() is not None:  # 判準 v3 起：封閉清單之跑別涵蓋
        assert set(cells) == nh.criteria_run_cell_keys("l2_arm_matrix")
    else:
        assert set(cells) == enumerate_keys(("A", "B"))


def test_l2_matrix_btc_12h_reproduces_freeze_baselines() -> None:
    """Task 1.3 驗證：BTCUSDT 12h 格重現 freeze-baselines 收據之 f32diff=0。"""
    assert L2_REPRO_TF in kline_inventory().get(L2_REPRO_SYMBOL, {})
    old = _json(FREEZE_BASELINES_1004_PATH)
    arms = old["l2_arms_in_pipeline"]
    arms = ast.literal_eval(arms) if isinstance(arms, str) else arms
    old_f32 = {int(a["f32diff"]) for a in arms}
    assert old_f32 == {0}, old_f32
    hits = [c for c in load_receipt("l2-arm-matrix")["cells"]
            if cell_key(c) == ("A", L2_REPRO_SYMBOL, (L2_REPRO_TF,))]
    assert len(hits) == 1 and not hits[0].get("errors") and hits[0]["f32diff"] == 0, hits


def test_l2_matrix_no_error_counted_as_zero_diff() -> None:
    """Task 1.3 邊界②之收據規則（另見 boundary_20 之單元案）：錯誤不以 0 差計。"""
    assert l2_error_violations() == []


def test_boundary_19_multi_tf_cells_l1_float64() -> None:
    """邊界①（SPEC Task 1.3）：多週期格（格 B）之 L1 輸入 dtype 皆記為 float64（對全部格 B 驗）。"""
    b_cells = [c for c in load_receipt("l2-arm-matrix")["cells"] if c["kind"] == "B"]
    assert {cell_key(c) for c in b_cells} == enumerate_keys(("B",)) and b_cells
    for cell in b_cells:
        assert cell["l1_dtypes"] and {str(d) for d in cell["l1_dtypes"]} == {"float64"}, cell["cell_id"]


def test_boundary_20_category_error_not_counted_as_zero_diff() -> None:
    """邊界②（SPEC Task 1.3）：某類別 `compute_category` 拋錯 ⇒ 記錯誤，不以缺欄計 0 差。單元：`compare_l2_arms` 於真實 kline
    欄（類別表缺一欄、另一欄 float32 捨入、另設 NaN 遮罩差）回報缺欄於 `only_returned`、差異只計共同欄；收據規則同
    `l2_error_violations`。"""
    frame = fsh.kline_frame().iloc[-3000:]
    cols = [c for c in frame.columns if np.issubdtype(frame[c].dtype, np.floating)]
    assert len(cols) >= 3
    # 真實欄之 log1p(|x|)（float64 計算值；kline 原值可能本為 float32 可精確表示，故不直接用）
    returned = np.log1p(frame[cols].astype(np.float64).abs())
    dropped, rounded, masked = cols[-1], cols[0], cols[1]
    category = returned.drop(columns=[dropped]).copy()
    category[rounded] = category[rounded].astype(np.float32).astype(np.float64)
    category.iloc[::401, category.columns.get_loc(masked)] = np.nan
    result = probe("l2_arm_matrix").compare_l2_arms(returned, category)
    assert set(result["only_returned"]) == {dropped} and not list(result["only_category"])
    common = result["common_cols"]
    common_set = set(common) if isinstance(common, (list, tuple, set)) else None
    assert (common_set == set(cols) - {dropped}) if common_set is not None else int(common) == len(cols) - 1
    shared = [c for c in cols if c != dropped]
    a, b = returned[shared].to_numpy(), category[shared].to_numpy()
    both = np.isfinite(a) & np.isfinite(b)
    assert int(result["nan_mask_diff"]) == int((np.isnan(a) != np.isnan(b)).sum()) > 0
    assert int(result["f64diff"]) == int((both & (a != b)).sum()) > 0
    a32, b32 = a.astype(np.float32), b.astype(np.float32)
    assert int(result["f32diff"]) == int((both & (a32 != b32)).sum()) == 0
    assert l2_error_violations() == []


def test_mutation_l2_error_replaced_by_zero_diff_turns_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：收據某格之錯誤改記 f32diff=0（錯誤保留而記 0 差；或錯誤刪除而缺欄仍在）⇒ 錯誤檢查紅。"""
    base = copy.deepcopy(load_receipt("l2-arm-matrix"))
    assert base["cells"], "收據無格 ⇒ mutation 無對象"
    with_error = copy.deepcopy(base)
    with_error["cells"][0]["errors"] = [{"category": "numview_mutant", "error": "RuntimeError: mutant"}]
    with_error["cells"][0]["f32diff"] = 0
    erased = copy.deepcopy(base)
    erased["cells"][0]["errors"] = []
    erased["cells"][0]["only_returned"] = ["numview_mutant_column"]
    erased["cells"][0]["f32diff"] = 0
    original = THIS.load_receipt
    for mutated in (with_error, erased):
        monkeypatch.setattr(THIS, "load_receipt", lambda kind, m=mutated: copy.deepcopy(m) if kind == "l2-arm-matrix"
                            else original(kind))
        assert l2_error_violations(), "mutant 存活：錯誤以 0 差計仍判通過"


def _l2_record(domain: str, rows: int, **over: Any) -> Dict[str, Any]:
    base = {"schema": 1, "domain": domain, "rows": rows, "l1_dtypes": ["float32"], "returned_arm": "polars",
            "returned_dtypes": ["float32"], "common_cols": 10, "only_returned": [], "only_category": [], "nan_mask_diff": 0,
            "f64diff": 0, "f32diff": 0, "max_abs": 0.0, "max_rel": 0.0, "row_mismatch": [], "category_errors": {}}
    return {**base, **over}


def test_l2_summarize_arm_main_domain_totals_and_errors() -> None:
    """Task 1.3（實作）：格層數字＝主生成域各次呼叫之合計（計數相加、max 取最大、清單聯集），校準域另列；類別錯誤、擷取錯誤
    或無主生成域紀錄 ⇒ `errors` 非空且 `f32diff` 為 None（邊界②）。"""
    m = probe("l2_arm_matrix")
    recs = [_l2_record("calibration", 4050, f32diff=99), _l2_record("main", 100, f32diff=3, l1_dtypes=["float64"]),
            _l2_record("main", 25, f32diff=2, max_abs=0.5, only_category=["x"])]
    got = m.summarize_arm(recs)
    assert (got["f32diff"], got["common_cols"], got["max_abs"], got["main_rows"]) == (5, 20, 0.5, [100, 25])
    assert got["l1_dtypes"] == ["float32", "float64"] and got["only_category"] == ["x"] and not got["errors"]
    assert len(got["calibration"]) == 1 and got["calibration"][0]["f32diff"] == 99
    for bad in ([_l2_record("main", 100, category_errors={"trend": "ValueError: x"})],
                [_l2_record("main", 100, capture_error="RuntimeError: y")], [_l2_record("calibration", 10)],
                [_l2_record("main", 100, row_mismatch=[[100, 99]])],  # 審碼 r29：列數不符
                [_l2_record("main", 100), _l2_record("calibration", 50, category_errors={"Cross": "KeyError: z"})]):
        out = m.summarize_arm(bad)
        assert out["errors"] and out["f32diff"] is None, bad
    assert got["blacklist_applied"] is False  # schema 1 紀錄未套 cascade blacklist（審碼 r29）
    assert m.summarize_arm([_l2_record("main", 100, blacklist_applied=True)])["blacklist_applied"] is True


def test_l2_assemble_sources_and_checks() -> None:
    """Task 1.3（實作）：generations＝0 ⇒ 取凍結紀錄（缺 ⇒ 該臂錯誤、`all_runs_available` 假）；generations＝1 ⇒ 取另行生成，
    凍結已有同 (格, 環境) ⇒ `not_regenerating_frozen` 假；生成未 complete ⇒ 該臂錯誤；12h 重現格 f32diff≠0 ⇒ 重現檢查假。"""
    m = probe("l2_arm_matrix")
    plan = [{"cell": "A_BTCUSDT_12h", "env": {}, "generations": 0},
            {"cell": "B_BTCUSDT_1h_4h", "env": {"FFACT_USE_POLARS": "0"}, "generations": 1}]
    frozen = {"A_BTCUSDT_12h": {"default": [_l2_record("main", 3855)]}}
    gen = {("B_BTCUSDT_1h_4h", "FFACT_USE_POLARS=0"): {"status": "complete", "seconds": 1.0,
                                                       "l2_capture": [_l2_record("main", 12256, l1_dtypes=["float64"])]}}
    ok = m.assemble(plan, frozen, gen)
    assert all(ok["checks"].values()), ok["checks"]
    assert {r["source"] for r in ok["runs"]} == {"freeze_baseline", "generated"}
    b = next(c for c in ok["cells"] if c["cell_id"] == "B_BTCUSDT_1h_4h")
    assert b["arms"]["FFACT_USE_POLARS=0"]["l1_dtypes"] == ["float64"]
    regen = copy.deepcopy(frozen)
    regen["B_BTCUSDT_1h_4h"] = {"FFACT_USE_POLARS=0": [_l2_record("main", 12256)]}
    assert m.assemble(plan, regen, gen)["checks"]["B_BTCUSDT_1h_4h.FFACT_USE_POLARS=0.not_regenerating_frozen"] is False
    failed = {k: {**v, "status": "failed", "l2_capture": None} for k, v in gen.items()}
    out = m.assemble(plan, frozen, failed)
    arm = next(c for c in out["cells"] if c["cell_id"] == "B_BTCUSDT_1h_4h")["arms"]["FFACT_USE_POLARS=0"]
    assert arm["errors"] and arm["f32diff"] is None and out["checks"]["all_runs_available"] is False
    assert m.assemble(plan, {}, gen)["checks"]["all_runs_available"] is False
    nonzero = {"A_BTCUSDT_12h": {"default": [_l2_record("main", 3855, f32diff=1)]}}
    assert m.assemble(plan, nonzero, gen)["checks"]["repro_btc_12h_f32diff_zero"] is False
    # 審碼 r29：非重現格之臂有類別錯誤 ⇒ 該臂 no_errors 假（收據 rc≠0）
    err_gen = {k: {**v, "l2_capture": [_l2_record("main", 12256, category_errors={"Distance": "ValueError: e"})]}
               for k, v in gen.items()}
    assert m.assemble(plan, frozen, err_gen)["checks"]["B_BTCUSDT_1h_4h.FFACT_USE_POLARS=0.no_errors"] is False
    assert "coverage_note" in b  # 多週期非主週期未擷取之量測限制具名


# ============================================================================================== §G 通過條件（Phase 0／2／4）

def _string_leaves(node: Any) -> List[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [s for item in node for s in _string_leaves(item)]
    if isinstance(node, Mapping):
        return [s for k, v in node.items() if not str(k).startswith("_") for s in _string_leaves(v)]
    return []


def decision_exclusions() -> List[Dict[str, Any]]:
    """Phase 3 例外（SPEC §G）：只取決定紀錄中 `changes_public_output` 為 True、具 `user_ruling`、且 `implemented_commit` 為
    HEAD 祖先（已落地）之 `changed_targets`；決定紀錄不存在 ⇒ 無例外（全部 atol=0，較嚴）。"""
    if not nh.DECISIONS_PATH.is_file():
        return []
    records = _json(nh.DECISIONS_PATH)["decisions"]
    assert isinstance(records, Mapping), "decisions.json 之 decisions 須為物件"
    out: List[Dict[str, Any]] = []
    for key, record in records.items():
        targets = record.get("changed_targets") or []
        if not targets:
            continue
        assert record.get("changes_public_output") is True, f"{key}: 有 changed_targets 而未標 changes_public_output"
        ruling = record.get("user_ruling") or {}
        assert ruling.get("date") and ruling.get("quote"), f"{key}: 改值決定缺 user_ruling"
        assert nh.decision(key) == record.get("choice"), f"{key}: 決定紀錄讀取不一致"
        commit = record.get("implemented_commit")
        if not commit or _git("merge-base", "--is-ancestor", str(commit), "HEAD").returncode != 0:
            continue
        for target in targets:
            assert target.get("group") in ("g1", "g2", "g3", "legacy"), f"{key}: 未知 group {target.get('group')!r}"
            out.append(dict(target, decision=key))
    return out


def _excluded_columns(exclusions: Sequence[Mapping[str, Any]], group: str, cell: str, copy_key: str) -> Optional[Set[str]]:
    """None ⇒ 無例外；空集合以外之集合 ⇒ 只排除該些欄；含 `"*"` ⇒ 整份排除。"""
    hit: Optional[Set[str]] = None
    for target in exclusions:
        if target["group"] != group or target.get("cell") not in (None, cell) or target.get("copy") not in (None, copy_key):
            continue
        hit = set() if hit is None else hit
        columns = target.get("columns")
        hit |= {"*"} if columns is None else {str(c) for c in columns}
    return hit


def _strip_columns(fp: Mapping[str, Any], columns: Set[str]) -> Dict[str, Any]:
    out = copy.deepcopy(dict(fp))
    out["columns"] = {k: v for k, v in fp["columns"].items() if k not in columns}
    return out


def gate_compare(frozen: Mapping[str, Any], current: Mapping[str, Any], *, label: str, excluded: Optional[Set[str]],
                 legacy: bool = False) -> List[str]:
    if excluded is not None and "*" in excluded:
        return []
    cols = excluded or set()
    diff = nh.bitwise_diff(_strip_columns(frozen, cols), _strip_columns(current, cols), legacy=legacy)
    return [f"{label}: {d}" for d in diff]


class _Regen:
    """凍結格於現行碼之重生（每格一次；G1 只跑已凍結之臂份）。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, cell_id: str, record: Mapping[str, Any]) -> Dict[str, Any]:
        if cell_id not in self._cache:
            arms = sorted((record.get("g1") or {}).keys())
            # `freeze_cell` 吃全票唯一格描述子 `{id, kind, symbol, timeframes}`（凍結檔格紀錄無 `id`；與
            # `test_numview_ic_page.py` 之 `_descriptor` 同形）
            descriptor = {"id": cell_id, "kind": record["kind"], "symbol": record["symbol"],
                          "timeframes": list(record["timeframes"])}
            # 批次共用生成（判準檔 cell_rules.batch_cache）：root＝共用快取根、跑別＝§G 所讀之批次（舊判準 ⇒ 本倉隔離根）
            self._cache[cell_id] = freeze_script().freeze_cell(
                descriptor, nh.regen_root(self.root / re.sub(r"[^A-Za-z0-9_.-]", "_", cell_id)),
                arms=arms, run_kind=nh.regen_batch_kind("regen_section_g"))
        return self._cache[cell_id]


@pytest.fixture(scope="module")
def regen(tmp_path_factory: pytest.TempPathFactory) -> _Regen:
    return _Regen(tmp_path_factory.mktemp("numview_gate_regen"))


@pytest.fixture(scope="module")
def legacy_runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("numview_gate_legacy"))


def test_gate_new_freeze_bitwise_equal_at_current_code(regen: _Regen) -> None:
    """§G 通過條件（Phase 0／2／4；小時級）：每個凍結格於現行碼重生，G1 每個已凍結臂份（以其環境）、G2、G3 之 `dtype`、`nan`、
    `values_native`、`column_set_sha256`、`column_order_sha256` 逐位元等於凍結值；G1 實際臂＝標示臂；臂份集合不增不減
    （`arm_unreachable` 者不比、不補造）；例外只經已落地之決定紀錄。"""
    freeze = load_freeze()
    exclusions = decision_exclusions()
    violations: List[str] = []
    compared = 0
    for cell_id, record in sorted(freeze["cells"].items()):
        current = regen.get(cell_id, record)
        for group in ("g1", "g2", "g3"):
            frozen_copies = dict(record.get(group) or {})
            current_copies = dict(current.get(group) or {})
            if set(frozen_copies) != set(current_copies):
                violations.append(f"{cell_id}/{group}: 臂份 {sorted(current_copies)} ≠ 凍結 {sorted(frozen_copies)}")
                continue
            for copy_key, frozen in frozen_copies.items():
                now = current_copies[copy_key]
                excluded = _excluded_columns(exclusions, group, cell_id, copy_key)
                if group == "g1" and excluded is None and now.get("actual_arm") != copy_key:
                    violations.append(f"{cell_id}/{copy_key}: 實際臂 {now.get('actual_arm')!r} ≠ 標示臂")
                frozen_fp = frozen["fingerprint"] if group in ("g1", "g2") else frozen
                current_fp = now["fingerprint"] if group in ("g1", "g2") else now
                violations += gate_compare(frozen_fp, current_fp, label=f"{cell_id}/{group}/{copy_key}", excluded=excluded)
                compared += 1
    assert compared >= 1, "無任何凍結份可比"
    assert violations == [], violations[:20]


def test_gate_legacy_preprov_baseline_bitwise_equal_at_current_code(legacy_runs: ph.RunCache) -> None:
    """§G 通過條件（沿用基準；小時級）：PRE-PROV 11 格於現行碼重生（`preprov_helpers.RunCache`），以 `legacy=True` 比 `dtype`
    與 float32 `values`、`column_set_sha256`（相容條件由 `bitwise_diff` 內之 `assert_legacy_compatible` 斷言）。"""
    baseline = _json(nh.LEGACY_BASELINE_PATH)
    exclusions = decision_exclusions()
    violations: List[str] = []
    compared = 0
    for cell, symbols in sorted(baseline["cells"].items()):
        for symbol, artifacts in sorted(symbols.items()):
            handle = legacy_runs.get(cell, symbol)
            for artifact, frozen in sorted(artifacts.items()):
                current = nh.fingerprints(handle.run_dir, artifact)
                excluded = _excluded_columns(exclusions, "legacy", cell, f"{symbol}/{artifact}")
                violations += gate_compare(frozen, current, label=f"{cell}/{symbol}/{artifact}", excluded=excluded,
                                           legacy=True)
                compared += 1
    assert compared >= len(baseline["cells"]) >= 1
    assert violations == [], violations[:20]


def _native_pair_frames() -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """真實欄（float32 可精確表示者）與其 +|x|·2**-40 擾動：float32 相等、float64 位元組不同。"""
    frame = fsh.kline_frame()
    col = "close"
    base = frame[[col]].astype(np.float32).astype(np.float64)
    bumped = base.copy()
    bumped[col] = base[col] + np.abs(base[col]) * 2.0 ** -40
    assert np.array_equal(bumped[col].astype(np.float32).to_numpy(), base[col].astype(np.float32).to_numpy())
    assert not np.array_equal(bumped[col].to_numpy(), base[col].to_numpy())
    return base, bumped, col


def gate_native_discrimination_violations() -> List[str]:
    """§G 判定須以 `values_native` 為準：只差小於 float32 解析度之真實欄對 ⇒ `gate_compare` 回報不等。"""
    base, bumped, col = _native_pair_frames()
    found = gate_compare(nh.frame_fingerprints(base), nh.frame_fingerprints(bumped), label="native", excluded=None)
    return [] if any(col in d for d in found) else ["§G 判定未區分小於 float32 解析度之原生位元組差"]


def _float32_values_bitwise_diff(before: Mapping[str, Any], after: Mapping[str, Any], *, legacy: bool = False) -> List[str]:
    out: List[str] = []
    for name in sorted(set(before["columns"]) | set(after["columns"])):
        b, a = before["columns"].get(name, {}), after["columns"].get(name, {})
        if b.get("values") != a.get("values") or b.get("nan") != a.get("nan"):
            out.append(f"{name}: values")
    return out


def test_gate_oracle_discriminates_native_bytes_on_real_column() -> None:
    """§G 判定之鑑別力（秒級）：真實欄之原生位元組差（float32 相同）須被判不等。"""
    assert gate_native_discrimination_violations() == []


def test_mutation_gate_bitwise_diff_float32_values_misses_native_difference(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC §V、R4-A）：§G 之 `bitwise_diff` 改用 float32 `values` ⇒ 原生位元組鑑別翻紅。"""
    monkeypatch.setattr(nh, "bitwise_diff", _float32_values_bitwise_diff)
    assert gate_native_discrimination_violations(), "mutant 存活：float32 values 判定仍區分原生位元組差"


# ============================================================================================== Task 4.2 ⑤

def contract_new_keys() -> Set[str]:
    contract = load_contract()
    keys = set(_string_leaves(contract["manifest_keys"])) | {str(k) for k in contract["run_identity_new_keys"]}
    assert keys, "契約 manifest_keys／run_identity_new_keys 為空（Task 4.2 未填）"
    return keys


def test_structural_refreeze_receipt_proves_strip_equals_frozen() -> None:
    """Task 4.2 驗證⑤（SPEC §G 結構凍結）：重凍收據之剝除鍵涵蓋契約新鍵；每檔 rc=0、每項「剝除新鍵後依原算法重算」＝凍結前值
    且 `equal` 為 True；`sha256_after` 等於現行凍結檔之 sha256（重凍確已寫入）。"""
    receipt = _json(nh.REFREEZE_RECEIPT_PATH)
    # 收據分記 artifact 節點之剝除鍵（stripped_keys）與頂層之剝除鍵（stripped_root_keys；observed_arms 只寫頂層）
    stripped = {str(k) for k in receipt["stripped_keys"]} | {str(k) for k in receipt.get("stripped_root_keys") or []}
    missing = contract_new_keys() - stripped
    assert not missing, f"剝除鍵缺契約新鍵：{sorted(missing)}"
    assert receipt["files"], "重凍收據無任何檔"
    for entry in receipt["files"]:
        assert entry["exit_code"] == 0 and entry["items"], entry.get("path")
        for item in entry["items"]:
            assert item["equal"] is True and item["frozen_before"] == item["stripped_recomputed"], (entry["path"], item.get("item"))
        target = REPO / entry["path"]
        assert entry["written"] is True and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256_after"], entry["path"]


# ============================================================================================== Task 5.1

def single_step_violations() -> List[str]:
    """`白話說明/還沒做的事.md` 含 `0.00005` 之行皆含「單步」（SPEC Task 5.1；經 `read_text` 讀取）。"""
    lines = [ln for ln in read_text(PLAIN_DOC_PATH).splitlines() if OLD_ZSCORE_LITERAL in ln]
    return [f"缺「{SINGLE_STEP_WORD}」：{ln[:80]}" for ln in lines if SINGLE_STEP_WORD not in ln]


def _fact_row(key: str) -> List[Any]:
    rows = [r for r in _json(FACT_KEYS_PATH)["roadmap-status"]["rows"] if len(r) > 1 and r[1] == key]
    assert len(rows) == 1, f"fact_keys roadmap-status 之 {key} 列須恰一"
    return rows[0]


def test_plain_doc_zscore_literal_lines_say_single_step() -> None:
    """Task 5.1 驗證：`grep "0.00005" 白話說明/還沒做的事.md` 之命中行皆含「單步」限定。"""
    assert PLAIN_DOC_PATH.is_file()
    assert single_step_violations() == []


def test_roadmap_rm_numview_row_matches_fact_key_zero_diff() -> None:
    """Task 5.1 驗證：fact_keys RM-NUMVIEW 文字含「零差」，且 `docs/ROADMAP.md` 之 RM-NUMVIEW 列位於 roadmap-status 生成
    區塊內並含同文（隨生成區塊重生、不手改）。"""
    text = str(_fact_row(RM_NUMVIEW)[-1])
    assert ZERO_DIFF_WORD in text
    lines = read_text(ROADMAP_PATH).splitlines()
    begin = lines.index(f"<!-- BEGIN GENERATED: {ROADMAP_BLOCK} -->")
    end = lines.index(f"<!-- END GENERATED: {ROADMAP_BLOCK} -->")
    hits = [i for i, ln in enumerate(lines) if f"| {RM_NUMVIEW} |" in ln]
    assert len(hits) == 1 and begin < hits[0] < end, hits
    assert text in lines[hits[0]]


def test_ticket_order_line_36_scoped_ic_first_and_ic_page() -> None:
    """Task 5.1 驗證：`docs/TICKET_ORDER.md` 第 36 行（第 4 步）含 IC-first 與 IC 頁兩者之限定措辭（IC 頁依使用者
    2026-10-21 方向裁定於第 8 步一併鎖定），不再以「post-IC 鎖 Polars 正式臂」概稱。"""
    rows = [r for r in read_text(TICKET_ORDER_PATH).splitlines() if r.startswith(TICKET_ORDER_ROW_PREFIX)]
    assert len(rows) == 1, f"第 4 步列須恰一列：{len(rows)}"
    line = rows[0]
    assert "IC-first" in line and re.search(r"IC ?頁", line) and "2026-10-21" in line, line
    assert TICKET_ORDER_OLD_PHRASE not in line


def test_fact_key_generated_blocks_in_sync() -> None:
    """Task 5.1 驗證：fact-key 生成區塊無漂移（`gen_fact_key_blocks.sh --check` rc=0；即 `--write` 後無區塊外變動之前提）。"""
    result = subprocess.run(["bash", "scripts/gen_fact_key_blocks.sh", "--check"], cwd=str(REPO), capture_output=True,
                            text=True)
    assert result.returncode == 0, (result.stdout + result.stderr)[-2000:]


def _r1_count_at(commit: str) -> int:
    result = _git("grep", "-n", "-E", r"^from api\.|^import api\.", commit, "--", "momentum/*.py")
    assert result.returncode in (0, 1), result.stderr
    return len([ln for ln in result.stdout.splitlines() if ln.strip()])


def _r4_keys_from_baseline(text: str) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 4 and parts[1] == "R4":
            out.append((parts[0], parts[2], parts[3]))
    return out


def decoupling_violations() -> List[str]:
    """R1、R4 計數不增：基準 commit＝凍結收據 `head`（Phase 0 改前 HEAD）。R1 基準＝該 commit 之 `git grep` 計數、現值＝
    `check_decoupling.sh` 之 Rule 1；R4 基準＝該 commit 之 `scripts/decouple_baseline.txt` R4 債、現值＝
    `check_decoupling_imports.py` 之 R4 違反（逐鍵多重集合不增）。"""
    head = str(load_receipt("freeze-baseline")["head"])
    assert re.fullmatch(r"[0-9a-f]{40}", head), head
    out: List[str] = []
    scan = subprocess.run(["bash", "scripts/check_decoupling.sh"], cwd=str(REPO), capture_output=True, text=True)
    text = scan.stdout + scan.stderr
    m = re.search(r"Rule 1 FAIL.*?\((\d+) violations\)", text)
    current_r1 = int(m.group(1)) if m else (0 if "Rule 1 PASS" in text else -1)
    assert current_r1 >= 0, "無法自 check_decoupling.sh 輸出判讀 Rule 1"
    base_r1 = _r1_count_at(head)
    if current_r1 > base_r1:
        out.append(f"R1 {current_r1} > 基準 {base_r1}")
    base = _git("show", f"{head}:{DECOUPLE_BASELINE_REL}")
    assert base.returncode == 0, base.stderr
    base_keys = _r4_keys_from_baseline(base.stdout)
    imports = subprocess.run([str(REPO / "venv" / "bin" / "python"), "scripts/check_decoupling_imports.py"], cwd=str(REPO),
                             capture_output=True, text=True)
    current_keys: List[Tuple[str, str, str]] = []
    for line in imports.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 5 and parts[-3] == "R4":
            rel = str(Path(":".join(parts[:-4])).resolve().relative_to(REPO.resolve()))
            current_keys.append((rel, parts[-2], parts[-1]))
    summary = re.search(r"R4=(\d+)", imports.stdout)
    assert summary is not None and int(summary.group(1)) == len(current_keys), "無法判讀 R4 計數"
    if len(current_keys) > len(base_keys):
        out.append(f"R4 {len(current_keys)} > 基準 {len(base_keys)}")
    for key in set(current_keys):
        if current_keys.count(key) > base_keys.count(key):
            out.append(f"R4 新增：{key}")
    return out


def test_decoupling_r1_r4_not_increased() -> None:
    """Task 5.1 驗證：`bash scripts/check_decoupling.sh` 之 R1、R4 計數不增（基準見 `decoupling_violations`）。"""
    assert decoupling_violations() == []


def test_boundary_57_plain_doc_site_html_regenerated_same_commit() -> None:
    """邊界①（SPEC Task 5.1）：白話文件依其生成規則（`scripts/plain_docs_render.py`）同 commit 產 `docs/site/還沒做的事.html`：
    現行 html 位元組＝渲染器自現行 md 之輸出、兩檔最後一次提交為同一 commit、html 含「單步」且 `0.00005` 出現次數同 md。"""
    renderer = _load_module("numview_plain_docs_render", RENDERER_PATH)
    outputs, _dead = renderer.build(renderer.DEFAULT_SRC, renderer.DEFAULT_OUT)
    expected = outputs[SITE_DOC_PATH.resolve()]
    html_text = read_text(SITE_DOC_PATH)
    assert html_text == expected, "docs/site/還沒做的事.html 非現行 md 之渲染結果"
    md_commit = _git("log", "-1", "--format=%H", "--", PLAIN_DOC_REL).stdout.strip()
    html_commit = _git("log", "-1", "--format=%H", "--", SITE_DOC_REL).stdout.strip()
    assert md_commit and md_commit == html_commit, (md_commit, html_commit)
    md_text = read_text(PLAIN_DOC_PATH)
    assert SINGLE_STEP_WORD in md_text, f"{PLAIN_DOC_REL} 未含「{SINGLE_STEP_WORD}」"
    assert SINGLE_STEP_WORD in html_text, f"{SITE_DOC_REL} 未含「{SINGLE_STEP_WORD}」"
    assert html_text.count(OLD_ZSCORE_LITERAL) == md_text.count(OLD_ZSCORE_LITERAL)


def test_boundary_58_fact_key_write_through_live_doc_guard() -> None:
    """邊界②（SPEC Task 5.1）：fact-key 寫入經 `scripts/live_doc_write_guard.sh`。`scripts/fact_keys.json` 非登記活文件（guard 對其
    `--tree` 判定空轉），故改驗其生成目標：`docs/ROADMAP.md` 與 `白話說明/還沒做的事.md` 皆為登記活文件，且 HEAD 版經
    `live_doc_write_guard.sh --tree HEAD --path <檔>` rc=0；guard 掛於 `.claude/settings.json` PreToolUse Edit|Write。"""
    registry = _json(LIVE_DOC_REGISTRY_PATH)
    exact = {str(row[0]) for row in registry["exact"]}
    prefixes = [str(row[0]) for row in registry["prefix"]]
    for rel in ("docs/ROADMAP.md", PLAIN_DOC_REL):
        assert rel in exact or any(rel.startswith(p) for p in prefixes), f"{rel} 非登記活文件"
        result = subprocess.run(["bash", "scripts/live_doc_write_guard.sh", "--tree", "HEAD", "--path", rel],
                                cwd=str(REPO), capture_output=True, text=True)
        assert result.returncode == 0, (rel, (result.stdout + result.stderr)[-1500:])
    settings = _json(SETTINGS_PATH)
    mounted = [h.get("command", "") for entry in settings["hooks"]["PreToolUse"] if "Edit" in str(entry.get("matcher"))
               and "Write" in str(entry.get("matcher")) for h in entry.get("hooks", [])]
    assert "bash scripts/live_doc_write_guard.sh" in mounted, mounted


def test_mutation_plain_doc_literal_without_single_step_turns_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 5.1）：文件含 `0.00005` 而無「單步」之一行（經 monkeypatch 之讀取函式）⇒ 措辭檢查紅。"""
    real = read_text(PLAIN_DOC_PATH)
    mutated = real + "\n- 變體：Polars 分支標準化差約 0.00005\n"
    original = THIS.read_text
    monkeypatch.setattr(THIS, "read_text", lambda path: mutated if Path(path) == PLAIN_DOC_PATH else original(path))
    violations = single_step_violations()
    assert any("變體" in v for v in violations), violations


# ---------------------------------------------------------------------------------------------- 精度鏈段集合依判準（審查 r8 GROK-R8-P1-01）

def _synthetic_precision_receipt(drop_c_s5: bool = True) -> Dict[str, Any]:
    """精度鏈收據之結構樣本（判準 precision_chain 之格；每格一欄 `x`，依判準 segments 逐段列；格 C 只生成 ⇒ 無 S5 列）。"""
    cells, rows = [], []
    for key in sorted(nh.criteria_run_cell_keys("precision_chain")):
        cid = _cell_id_of(key)
        grouped = key[0] in nh.GROUP_GRANULARITY_KINDS  # SPEC v37 細則①：格 C 逐群組列
        # 審碼 r24：S3／S4 期望群組須等於凍結 manifest 群組（驗收之獨立來源）
        canonical = probe("precision_chain").canonical_c_groups(cid) if grouped else {}
        expected = {"S0": {"g": 1}, "S3": dict(canonical), "S4": dict(canonical)} if grouped else None
        cells.append({"cell_id": cid, "kind": key[0], "symbol": key[1], "timeframes": list(key[2]), "status": "measured",
                      "columns": ["x"], "granularity": "group" if grouped else "column", "expected_groups": expected})
        for seg in SEGMENTS:
            if seg == "S5" and key[0] == "C" and drop_c_s5:
                continue
            if grouped and seg in ("S0", "S3", "S4"):
                rows += [{"cell_id": cid, "segment": seg, "group": g, "columns_in_group": n, "source_run": "r"}
                         for g, n in expected[seg].items()]
            elif grouped:
                rows.append({"cell_id": cid, "segment": seg, "group": "*", "columns_in_group": None, "source_run": "r"})
            else:
                rows.append({"cell_id": cid, "segment": seg, "column": "x"})
    return {"cells": cells, "rows": rows}


def _cell_id_of(key: CellKey) -> str:
    return f"{key[0]}_{key[1]}_{'_'.join(key[2])}"


def test_precision_completeness_generate_only_cell_without_s5(monkeypatch: pytest.MonkeyPatch) -> None:
    """判準 v4：只生成之格 C 之精度鏈只具 S0–S4（無 S5 IC 選欄）——依 SPEC 不產 C／S5 列之收據通過段×格完整檢查；
    mutation：段集合改回一律要求 S5（忽略判準 segments）⇒ 紅。"""
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: _synthetic_precision_receipt())
    assert precision_completeness_violations() == []
    monkeypatch.setattr(nh, "precision_segments", lambda cid, default: list(default))
    assert any("C_BTCUSDT_1h/S5" in v for v in precision_completeness_violations())


@pytest.mark.parametrize("mutant", [None, "c_blocked_claims_s5", "c_blocked_missing_s4"])
def test_boundary_18_blocked_generate_only_cell_segments_follow_criteria(mutant: Optional[str],
                                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界③（審查 r9 GROK-R9-P1-01）：格 C blocked 之收據只具 S0–S4 blocked 列（判準 v4 segments）⇒ 邊界③通過；
    mutation：C blocked 列多 S5／缺 S4 ⇒ 紅。收據為合成列（只測段集合契約，不含數值）。"""
    receipt = _synthetic_precision_receipt(drop_c_s5=True)
    for cell in receipt["cells"]:
        if cell["kind"] == "C":
            cell["status"] = "blocked"
    for row in receipt["rows"]:
        if row["cell_id"].startswith("C_"):
            row.update(status="blocked", max_abs=None, max_rel=None)
        else:
            row["status"] = "measured"
    c_id = next(c["cell_id"] for c in receipt["cells"] if c["kind"] == "C")
    if mutant == "c_blocked_claims_s5":
        receipt["rows"].append({"cell_id": c_id, "segment": "S5", "column": "x", "status": "blocked",
                                "max_abs": None, "max_rel": None})
    elif mutant == "c_blocked_missing_s4":
        receipt["rows"] = [r for r in receipt["rows"] if not (r["cell_id"] == c_id and r["segment"] == "S4")]
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: receipt)
    monkeypatch.setattr(THIS, "enumerate_keys", lambda kinds: {cell_key(c) for c in receipt["cells"] if c["kind"] in kinds})
    if mutant is None:
        test_boundary_18_blocked_cell_c_all_segments_blocked()
    else:
        with pytest.raises(AssertionError):
            test_boundary_18_blocked_cell_c_all_segments_blocked()


# ---------------------------------------------------------------------------------------------- Task 1.2 身分表與增列兌現（SPEC v37）

#: SPEC v37 驗證段：各 `source_run` 之 `observed_settings` 期望（字面鎖定；探針 `VARIANT_SETTINGS`）
_A_BASE_SETTINGS: Dict[str, Any] = {"preserve_dtype": [False], "l2_polars_lift": False,
                                    "memmap_threshold_bytes": [500_000_000], "memmap_branch": ["concat"],
                                    "spill_triggered": False, "lag_enabled": [False], "codec_upgrade": False,
                                    "winsor_method": ["quantile"], "stationarity": ["fracdiff+adf"], "end_offset_bars": 0,
                                    "multi_tf_parallel_calls": 0}
VARIANT_SETTINGS_EXPECTED: Dict[str, Dict[str, Any]] = {
    "s0_float64_chain": {**_A_BASE_SETTINGS, "preserve_dtype": [True], "l2_polars_lift": True},
    "memmap_forced_low": {**_A_BASE_SETTINGS, "memmap_threshold_bytes": [0], "memmap_branch": ["memmap"],
                          "lag_enabled": [True]},
    "memmap_forced_high": {**_A_BASE_SETTINGS, "memmap_threshold_bytes": [10 ** 18], "lag_enabled": [True]},
    "codec_upgrade_on": {**_A_BASE_SETTINGS, "codec_upgrade": True},
    "tail_extension": {**_A_BASE_SETTINGS, "end_offset_bars": 100},
    "winsor_sigma_dtype": {**_A_BASE_SETTINGS, "winsor_method": ["sigma"]},
    "b_production_spy": {"preserve_dtype": [True], "l2_polars_lift": False, "spill_triggered": False,
                         "lag_enabled": [False], "codec_upgrade": False, "winsor_method": ["quantile"],
                         "stationarity": ["fracdiff+adf"], "end_offset_bars": 0, "multi_tf_parallel_calls": 0},
    "c_preserve_dtype": {"preserve_dtype": [True], "l2_polars_lift": True, "spill_triggered": False,
                         "l2_spill_bypassed": True, "lag_enabled": [True], "codec_upgrade": False, "end_offset_bars": 0,
                         "multi_tf_parallel_calls": 0},
}


def precision_c_chain_violations(receipt: Mapping[str, Any]) -> List[str]:
    """SPEC v39（諮詢 r3）：C 格 measured ⇒ 其 R run 主鏈 layer2 spill 已停用（`l2_spill_bypassed` 真、`spill_triggered`
    假）、子行程峰值 RSS 為正整數、格層 `s0_incomplete` 存在且記 L3–L6 讀入之 layer2 dtype（非空）；C 之 S0 群組列皆記
    `s0_non_float64_columns`（非負整數）。C blocked 時不查（依 SPEC 標 blocked-by）。"""
    pc = probe("precision_chain")
    cid = pc.C_CELL
    cell = next((c for c in receipt.get("cells") or [] if str(c.get("cell_id")) == cid), None)
    if cell is None or cell.get("status") != "measured":
        return []
    out: List[str] = []
    observed = (receipt.get("observed_settings") or {}).get("c_preserve_dtype") or {}
    if observed.get("l2_spill_bypassed") is not True or observed.get("spill_triggered") is not False:
        out.append(f"C 主鏈 spill 未停用：{ {k: observed.get(k) for k in ('l2_spill_bypassed', 'spill_triggered')} }")
    if not isinstance(observed.get("calibration_spill"), bool):  # 審碼 r22：主鏈與校準域分記
        out.append(f"C 未分記校準域 spill：{observed.get('calibration_spill')!r}")
    memory = (receipt.get("memory") or {}).get("c_preserve_dtype") or {}
    peak = memory.get("peak_rss_bytes")
    if isinstance(peak, bool) or not isinstance(peak, int) or peak <= 0:
        out.append(f"C 峰值 RSS 未記：{peak!r}")
    swap = memory.get("swap_growth_max_mb")  # 審碼 r22：swap 增長（卡死監看）亦須記
    if isinstance(swap, bool) or not isinstance(swap, (int, float)) or not math.isfinite(swap) or swap < 0:
        out.append(f"C swap 增長未記：{swap!r}")
    if not any(str(r.get("cell_id")) == cid and r.get("segment") == "S0" and r.get("status") == "measured"
               for r in receipt.get("rows") or []):
        out.append("C 無 measured 之 S0 列")
    inc = [e for e in receipt.get("s0_incomplete") or [] if str(e.get("cell_id")) == cid]
    if len(inc) != 1 or not isinstance(inc[0].get("l2_consumer_dtypes"), list) or not inc[0]["l2_consumer_dtypes"]:
        out.append(f"C s0_incomplete 缺或未記 layer2 dtype：{inc}")
    for row in receipt.get("rows") or []:
        if str(row.get("cell_id")) == cid and row.get("segment") == "S0" and row.get("status") != "blocked":
            n = row.get("s0_non_float64_columns")
            if isinstance(n, bool) or not isinstance(n, int) or n < 0:
                out.append(f"C S0 群組 {row.get('group')} 缺 s0_non_float64_columns")
                break
    return out


def test_precision_c_chain_contract() -> None:
    """Task 1.2 驗證（SPEC v39）：正式收據之 C 格主鏈 spill 停用、記憶體與 s0_incomplete 已記。"""
    assert precision_c_chain_violations(load_receipt("precision-chain")) == []


@pytest.mark.parametrize("mutant", ["spill_not_bypassed", "spill_happened", "peak_missing", "peak_bool",
                                    "incomplete_missing", "consumer_dtypes_empty", "group_count_missing",
                                    "calibration_spill_missing", "swap_missing", "no_s0_rows"])
def test_precision_c_chain_violations_mutations(mutant: str) -> None:
    """諮詢 r3、審碼 r22：C 主鏈 spill 未停用或仍發生、峰值 RSS 缺或為布林、s0_incomplete 缺、layer2 dtype 空、S0 群組缺
    非 float64 計數、校準域 spill 未分記、swap 增長缺、無 measured S0 列 ⇒ 各翻紅；合規 ⇒ 空；C blocked ⇒ 不查。"""
    cid = probe("precision_chain").C_CELL
    good = {"cells": [{"cell_id": cid, "status": "measured"}],
            "observed_settings": {"c_preserve_dtype": {"l2_spill_bypassed": True, "spill_triggered": False,
                                                       "calibration_spill": True}},
            "memory": {"c_preserve_dtype": {"peak_rss_bytes": 5_000_000_000, "swap_growth_max_mb": 3000.0}},
            "s0_incomplete": [{"cell_id": cid, "l2_consumer_dtypes": ["float32", "float64"]}],
            "rows": [{"cell_id": cid, "segment": "S0", "status": "measured", "group": "g", "s0_non_float64_columns": 3}]}
    assert precision_c_chain_violations(good) == []
    r = copy.deepcopy(good)
    if mutant == "spill_not_bypassed":
        r["observed_settings"]["c_preserve_dtype"]["l2_spill_bypassed"] = False
    elif mutant == "spill_happened":
        r["observed_settings"]["c_preserve_dtype"]["spill_triggered"] = True
    elif mutant == "peak_missing":
        r["memory"] = {}
    elif mutant == "peak_bool":
        r["memory"]["c_preserve_dtype"]["peak_rss_bytes"] = True
    elif mutant == "incomplete_missing":
        r["s0_incomplete"] = []
    elif mutant == "consumer_dtypes_empty":
        r["s0_incomplete"][0]["l2_consumer_dtypes"] = []
    elif mutant == "calibration_spill_missing":
        del r["observed_settings"]["c_preserve_dtype"]["calibration_spill"]
    elif mutant == "swap_missing":
        del r["memory"]["c_preserve_dtype"]["swap_growth_max_mb"]
    elif mutant == "no_s0_rows":
        r["rows"] = []
    else:
        del r["rows"][0]["s0_non_float64_columns"]
    assert precision_c_chain_violations(r) != []
    blocked = copy.deepcopy(r)
    blocked["cells"][0]["status"] = "blocked"
    assert precision_c_chain_violations(blocked) == []


def _merge_fixture() -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    """合成 parent（A、B、C 三格）與只重做 C 之 child（C 列、run、checks 皆新值）。"""
    pc = probe("precision_chain")
    a, b, c = pc.HOST_CELL, pc.B_CELL, pc.C_CELL

    def lists(cells: Sequence[str], tag: str) -> Dict[str, Any]:
        return {k: [{"cell_id": x, "tag": tag} for x in cells] for k in pc.CELL_LIST_KEYS}

    parent = {"trial": False, "criteria_sha256": "s", "generated_at": "t0", "head": "h0", "command": "c0",
              **lists((a, b, c), "old"),
              **{k: {"s0_float64_chain": {"v": k}, "b_production_spy": {"v": k}, "c_preserve_dtype": {"v": "old"},
                     "freeze_C": {"v": "old"}} for k in pc.RUN_MAP_KEYS},
              "checks": {f"{a}.x": True, f"{b}.y": True, f"{c}.z": False, "settings.c_preserve_dtype": False,
                         "settings.s0_float64_chain": True},
              "s4_raw_bss": [{"cell_id": a, "status": "measured", "bitwise_equal": True},
                             {"cell_id": b, "status": "codec_off", "bitwise_equal": None},
                             {"cell_id": c, "status": "blocked", "bitwise_equal": False}],
              "lossless_violation": False, "exit_code": 3}
    child = {"trial": False, "criteria_sha256": "s", "generated_at": "t1", "head": "h1", "command": "c1",
             **lists((c,), "new"),
             **{k: {"c_preserve_dtype": {"v": "new"}, "freeze_C": {"v": "new"}} for k in pc.RUN_MAP_KEYS},
             "checks": {f"{c}.z": True, f"{c}.no_reference_rows_zero": True, "settings.c_preserve_dtype": True},
             "s4_raw_bss": [{"cell_id": c, "status": "codec_off", "bitwise_equal": None}]}
    # 審碼 r23–r24：child 之 C 列涵蓋 S0–S4；S3／S4 期望群組＝凍結 C manifest 群組（獨立來源），每群組一列；S0 期望非空
    groups = pc.canonical_c_groups(c)
    child["cells"] = [{"cell_id": c, "tag": "new", "status": "measured", "expected_groups": {"S0": {"g0": 1}, "S3": dict(groups),
                                                                       "S4": dict(groups)}}]
    child["rows"] = ([{"cell_id": c, "segment": "S0", "group": "g0", "status": "measured"}]
                     + [{"cell_id": c, "segment": s, "group": "*", "status": "not_measured"} for s in ("S1", "S2")]
                     + [{"cell_id": c, "segment": "S3", "group": g, "status": "measured"} for g in groups]
                     + [{"cell_id": c, "segment": "S4", "group": g, "status": "codec_off"} for g in groups])
    child["run_status"] = {"c_preserve_dtype": "complete"}
    return pc, parent, child


def test_precision_merge_receipt_failed_run_reports_blocked() -> None:
    """審碼 r23：C 生成失敗（run 無身分、run_status failed）而 C 列全為 blocked／codec_off ⇒ 照常合併、C 呈 blocked、
    `exit_code` 3（設定檢查為假），不中止。"""
    pc, parent, child = _merge_fixture()
    c = pc.C_CELL
    del child["runs"]["c_preserve_dtype"]
    child["run_status"] = {"c_preserve_dtype": "failed"}
    child["checks"]["settings.c_preserve_dtype"] = False
    for row in child["rows"]:
        row["status"] = "codec_off" if row["segment"] == "S4" else "blocked"
    child["cells"][0]["status"] = "blocked"
    merged = pc.merge_receipt(parent, child, c, "abc")
    assert merged["exit_code"] == 3 and "c_preserve_dtype" not in merged["runs"]
    assert {r["status"] for r in merged["rows"] if r["cell_id"] == c} == {"blocked", "codec_off"}


def test_precision_merge_receipt_replaces_only_c() -> None:
    """SPEC v39：合併後非 C 之清單項、run 對應表、checks 逐位等於 parent；C 之項全為 child 者；exit_code 重算；記 merge。"""
    pc, parent, child = _merge_fixture()
    c = pc.C_CELL
    merged = pc.merge_receipt(parent, child, c, "abc")
    for key in pc.CELL_LIST_KEYS:
        assert [e for e in merged[key] if e["cell_id"] != c] == [e for e in parent[key] if e["cell_id"] != c], key
        assert [e for e in merged[key] if e["cell_id"] == c] == child[key], key
    for key in pc.RUN_MAP_KEYS:
        assert {k: v for k, v in merged[key].items() if k not in ("c_preserve_dtype", "freeze_C")} == \
            {k: v for k, v in parent[key].items() if k not in ("c_preserve_dtype", "freeze_C")}, key
        assert merged[key] == {**{k: v for k, v in parent[key].items() if k not in ("c_preserve_dtype", "freeze_C")},
                               **child[key]}, key
    assert merged["checks"] == {f"{pc.HOST_CELL}.x": True, f"{pc.B_CELL}.y": True, f"{c}.z": True,
                                f"{c}.no_reference_rows_zero": True, "settings.c_preserve_dtype": True,
                                "settings.s0_float64_chain": True}
    assert merged["exit_code"] == 0 and merged["lossless_violation"] is False
    assert merged["merge"]["parent_sha256"] == "abc" and merged["merge"]["replaced_cell"] == c
    assert (merged["head"], merged["generated_at"]) == ("h1", "t1")


@pytest.mark.parametrize("mutant", ["parent_trial", "criteria_differ", "child_has_a_row", "child_has_b_run",
                                    "child_has_a_check", "parent_lacks_c", "parent_c_twice", "cell_not_mergeable",
                                    "child_no_rows", "child_missing_run", "child_missing_settings_check",
                                    "child_missing_no_reference_check", "child_missing_segment",
                                    "child_group_missing", "failed_run_with_measured_rows",
                                    "expected_groups_forged", "expected_groups_empty", "child_missing_key",
                                    "settings_false_with_measured", "cell_status_forged"])
def test_precision_merge_receipt_rejects(mutant: str) -> None:
    """SPEC v39、審碼 r22–r23：parent 為試跑、判準雜湊不同、child 含他格列／run／checks、parent 缺 C 或含兩次、指定格不可
    單獨重做、child 無 C 統計列、缺 C 之 run 身分、缺設定檢查或缺參照檢查、缺一段、群組粒度段少一群組、生成失敗之 run 無身分
    而 C 仍有 measured 列 ⇒ `MergeError`。"""
    pc, parent, child = _merge_fixture()
    cell = pc.C_CELL
    if mutant == "parent_trial":
        parent["trial"] = True
    elif mutant == "criteria_differ":
        child["criteria_sha256"] = "other"
    elif mutant == "child_has_a_row":
        child["rows"].append({"cell_id": pc.HOST_CELL})
    elif mutant == "child_has_b_run":
        child["runs"]["b_production_spy"] = {}
    elif mutant == "child_has_a_check":
        child["checks"][f"{pc.HOST_CELL}.x"] = False
    elif mutant == "parent_lacks_c":
        parent["cells"] = [e for e in parent["cells"] if e["cell_id"] != cell]
    elif mutant == "parent_c_twice":
        parent["cells"].append({"cell_id": cell})
    elif mutant == "child_no_rows":
        child["rows"] = []
    elif mutant == "child_missing_run":
        del child["runs"]["freeze_C"]
    elif mutant == "child_missing_settings_check":
        del child["checks"]["settings.c_preserve_dtype"]
    elif mutant == "child_missing_no_reference_check":
        del child["checks"][f"{cell}.no_reference_rows_zero"]
    elif mutant == "child_missing_segment":
        child["rows"] = [r for r in child["rows"] if r["segment"] != "S2"]
    elif mutant == "child_group_missing":
        first = next(r for r in child["rows"] if r["segment"] == "S3")
        child["rows"].remove(first)
    elif mutant == "failed_run_with_measured_rows":
        del child["runs"]["c_preserve_dtype"]
        child["run_status"] = {"c_preserve_dtype": "failed"}
    elif mutant == "expected_groups_forged":  # 同刪一群組之列與自報期望（codex r24 反例）
        first = next(r for r in child["rows"] if r["segment"] == "S3")
        child["rows"].remove(first)
        del child["cells"][0]["expected_groups"]["S3"][first["group"]]
    elif mutant == "expected_groups_empty":  # grok r24 反例
        child["cells"][0]["expected_groups"] = {}
    elif mutant == "child_missing_key":
        del child["forks"]
    elif mutant == "settings_false_with_measured":
        child["checks"]["settings.c_preserve_dtype"] = False
    elif mutant == "cell_status_forged":  # 審碼 r25：列全非 measured 而格標 measured
        for row in child["rows"]:
            row["status"] = "codec_off" if row["segment"] == "S4" else "blocked"
    else:
        cell = pc.HOST_CELL
    with pytest.raises(pc.MergeError):
        pc.merge_receipt(parent, child, cell, "abc")


def test_precision_variant_settings_locked() -> None:
    """SPEC v37 驗證段：探針 `VARIANT_SETTINGS` 逐鍵等於字面期望（含 memmap 兩變體開 lag、C／S0 變體 preserve 與 L2
    Polars 抬升、B 並行分派 0 次）。"""
    assert probe("precision_chain").VARIANT_SETTINGS == VARIANT_SETTINGS_EXPECTED


def precision_runs_violations(receipt: Mapping[str, Any]) -> List[str]:
    """SPEC v37 驗證段之身分表：每個統計列之 `source_run` 為 `runs` 之鍵且格相符；每個生成型 `source_run` 之
    `observed_settings` 逐鍵等於 `VARIANT_SETTINGS`（探針 `settings_violations` 之同一判定）；`generation_inputs_sha256`
    以同一程序獨立重算相等；run 目錄仍在時 `feature_manifest.json` sha256 自目錄重算相等；資料集與兩碼態等於同格凍結
    run 之身分。"""
    pc = probe("precision_chain")
    out: List[str] = []
    runs = receipt.get("runs") or {}
    for row in receipt.get("rows") or []:
        src = row.get("source_run")
        if src is None:
            # 審碼 r8：只 blocked 列（生成未成或等價不成立，無可指之 run）得無 source_run；其餘缺即違規
            if row.get("status") != "blocked":
                out.append(f"{row.get('cell_id')}/{row.get('segment')}：非 blocked 列缺 source_run")
            continue
        if src not in runs:
            out.append(f"{row.get('cell_id')}/{row.get('segment')}：source_run {src} 不在身分表")
        elif str(runs[src].get("cell_id")) != str(row.get("cell_id")):
            out.append(f"{row.get('cell_id')}/{row.get('segment')}：source_run {src} 之格 {runs[src].get('cell_id')} 不符")
    # 審碼 r12：身分表中每個生成型 run 皆須有觀測設定與窗（以身分表為準，不以觀測表自身之鍵為準）
    generated = [n for n in runs if n in pc.RUN_SPECS]
    for name in sorted(set(generated) | set(receipt.get("observed_settings") or {})):
        observed = (receipt.get("observed_settings") or {}).get(name)
        window = (receipt.get("windows") or {}).get(name)
        if observed is None or window is None:
            out.append(f"{name}：缺 observed_settings 或 window")
            continue
        out += pc.settings_violations(name, observed, window[1])
    freeze_names = dict(pc.FREEZE_RUN_NAMES)
    for name, ident in runs.items():
        if ident.get("variant") != name:  # 審碼 r12：身分表鍵＝其 variant（不得重新標籤）
            out.append(f"{name}：身分表 variant {ident.get('variant')!r} ≠ 鍵")
        want = hashlib.sha256(json.dumps(pc.variant_generation_inputs(name), sort_keys=True, default=str,
                                         ensure_ascii=False).encode("utf-8")).hexdigest()
        if ident.get("generation_inputs_sha256") != want:
            out.append(f"{name}：generation_inputs_sha256 與獨立重算不等")
        run_dir = REPO / str(ident.get("run_dir"))
        if (run_dir / "feature_manifest.json").is_file():
            if hashlib.sha256((run_dir / "feature_manifest.json").read_bytes()).hexdigest() != ident.get(
                    "feature_manifest_sha256"):
                out.append(f"{name}：feature_manifest sha256 與目錄不符")
        frozen = runs.get(freeze_names.get(str(ident.get("cell_id")), ""))
        if frozen is not None:
            # 產品碼態與資料集須等於凍結（同一生產計算之前提）；接縫碼態含本票探針與估時器位元組，本批改之 ⇒ 不要求相等，
            # 生產等價另由落盤逐位元相等證明（SPEC v38）
            for key in ("datasets", "code_state_sha256"):
                if ident.get(key) != frozen.get(key):
                    out.append(f"{name}：{key} 與凍結 {ident.get('cell_id')} 不同")
            if not ident.get("seam_state_sha256"):
                out.append(f"{name}：缺 seam_state_sha256")
    return out


#: SPEC v37 比對定義之各 (格, 段) 來源：{段: (允許之 source_run 集合, reference_run)}（審碼 r11：不得以同格他 run 冒充）
EXPECTED_PRECISION_SOURCES: Dict[str, Dict[str, Tuple[Set[str], Optional[str]]]] = {
    "A_BTCUSDT_1h": {"S0": ({"s0_float64_chain"}, "s0_float64_chain"), "S1": ({"codec_upgrade_on"}, "s0_float64_chain"),
                     "S2": ({"codec_upgrade_on"}, "s0_float64_chain"), "S3": ({"freeze_A"}, "s0_float64_chain"),
                     "S4": ({"codec_upgrade_on"}, "freeze_A"),
                     "S5": ({"codec_upgrade_on", "freeze_A"}, "s0_float64_chain")},
    "B_BTCUSDT_1h_4h": {"S0": ({"b_production_spy"}, "b_production_spy"), "S1": ({"b_production_spy"}, None),
                        "S2": ({"b_production_spy"}, None), "S3": ({"freeze_B"}, "b_production_spy"),
                        "S4": ({"freeze_B"}, None), "S5": ({"b_production_spy"}, "b_production_spy")},
    "C_BTCUSDT_1h": {"S0": ({"c_preserve_dtype"}, "c_preserve_dtype"), "S1": ({"freeze_C"}, None),
                     "S2": ({"freeze_C"}, None), "S3": ({"freeze_C"}, "c_preserve_dtype"), "S4": ({"freeze_C"}, None)},
}


def precision_source_violations(receipt: Mapping[str, Any]) -> List[str]:
    """審碼 r11：每個非 blocked 統計列之 `source_run`／`reference_run` 須等於 `EXPECTED_PRECISION_SOURCES` 該 (格, 段)。"""
    out: List[str] = []
    for row in receipt.get("rows") or []:
        if row.get("status") == "blocked":
            continue
        want = EXPECTED_PRECISION_SOURCES.get(str(row.get("cell_id")), {}).get(str(row.get("segment")))
        if want is None:
            out.append(f"{row.get('cell_id')}/{row.get('segment')}：無期望來源")
            continue
        if row.get("source_run") not in want[0] or row.get("reference_run") != want[1]:
            out.append(f"{row.get('cell_id')}/{row.get('segment')}：來源 ({row.get('source_run')}, {row.get('reference_run')}) "
                       f"≠ 期望 ({sorted(want[0])}, {want[1]})")
    return out


def precision_addenda_fulfillment_violations(receipt: Mapping[str, Any]) -> List[str]:
    """SPEC v37：每個 `estimate.PRECISION_ADDENDA` 列之 `unique_output` 每一段於該格具該變體之非 blocked 統計列，且該變體
    於該段之角色合乎 `EXPECTED_PRECISION_SOURCES`（`source_run` 或該段定義之 `reference_run`；審碼 r11：不得任取一欄位）。"""
    out: List[str] = []
    for spec in probe("estimate").PRECISION_ADDENDA:
        for seg in spec["unique_output"]:
            want = EXPECTED_PRECISION_SOURCES.get(spec["cell"], {}).get(seg)
            role = "source_run" if want and spec["variant"] in want[0] else (
                "reference_run" if want and want[1] == spec["variant"] else None)
            hits = [r for r in receipt.get("rows") or [] if role and str(r.get("cell_id")) == spec["cell"]
                    and str(r.get("segment")) == seg and r.get("status") != "blocked" and r.get(role) == spec["variant"]]
            if not hits:
                out.append(f"{spec['cell']}/{seg}：無 {spec['variant']}（{role}）之統計列")
    return out


def test_precision_chain_runs_identity_and_settings() -> None:
    """Task 1.2 驗證（SPEC v37）：身分表、觀測設定、生成輸入與 manifest 雜湊、資料集與碼態。"""
    assert precision_runs_violations(load_receipt("precision-chain")) == []


def test_precision_chain_addenda_fulfilled() -> None:
    """Task 1.2 驗證（SPEC v37）：B／C 增列之 `unique_output` 各段於量測收據兌現。"""
    assert precision_addenda_fulfillment_violations(load_receipt("precision-chain")) == []


def test_precision_chain_s5_replay_oracle() -> None:
    """SPEC v36 S5：重演程序算凍結讀回之 `ic_scores` 與凍結 json 逐值相等（收據 checks 之 oracle 為 True）。"""
    checks = load_receipt("precision-chain")["checks"]
    assert checks.get("A_BTCUSDT_1h.s5_replay_oracle") is True, checks


@pytest.mark.parametrize("mutant", ["source_run_unknown", "settings_preserve_false", "generation_inputs_swapped"])
def test_mutation_precision_runs_identity(mutant: str) -> None:
    """mutation（SPEC v37 驗證段）：統計列 `source_run` 不在身分表、C 增列觀測 `preserve_dtype` 含 False、身分表
    `generation_inputs_sha256` 換為他 run 之值 ⇒ 各翻紅。"""
    receipt = copy.deepcopy(load_receipt("precision-chain"))
    if mutant == "source_run_unknown":
        next(r for r in receipt["rows"] if r.get("source_run"))["source_run"] = "mutant_run"
    elif mutant == "settings_preserve_false":
        receipt["observed_settings"]["c_preserve_dtype"]["preserve_dtype"] = [False, True]
    else:
        receipt["runs"]["b_production_spy"]["generation_inputs_sha256"] = \
            receipt["runs"]["codec_upgrade_on"]["generation_inputs_sha256"]
    assert precision_runs_violations(receipt) != []


def test_mutation_precision_group_rows_swapped_turns_completeness_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC v37 細則①）：群組粒度格刪一群組列並複製另一群組列使欄數合計不變 ⇒ 段×格完整檢查紅。"""
    receipt = _synthetic_precision_receipt()
    c_cell = next(c for c in receipt["cells"] if c["kind"] in nh.GROUP_GRANULARITY_KINDS)
    c_cell["expected_groups"]["S0"] = {"g": 1, "h": 1}
    receipt["rows"].append({"cell_id": c_cell["cell_id"], "segment": "S0", "group": "h", "columns_in_group": 1,
                            "source_run": "r"})
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(receipt))
    assert precision_completeness_violations() == []
    mutated = copy.deepcopy(receipt)
    mutated["rows"] = [r for r in mutated["rows"] if not (r["cell_id"] == c_cell["cell_id"] and r["segment"] == "S0"
                                                          and r.get("group") == "h")]
    mutated["rows"].append({"cell_id": c_cell["cell_id"], "segment": "S0", "group": "g", "columns_in_group": 1,
                            "source_run": "r2"})
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(mutated))
    assert any("S0" in v for v in precision_completeness_violations())


# ---------------------------------------------------------------------------------------------- Task 1.2 審碼 r8 之單元（不依賴收據）

def test_precision_bitwise_is_native_dtype_strict() -> None:
    """審碼 r8：生產等價與 raw BSS 之逐位元比較為原生（不同 dtype 一律不等；同 dtype 同值才等；NaN 遮罩須同）。"""
    bitwise = probe("precision_chain")._bitwise
    assert bitwise(np.array([1.5], dtype=np.float32), np.array([1.5], dtype=np.float32)) is True
    assert bitwise(np.array([1.5], dtype=np.float32), np.array([1.5], dtype=np.float64)) is False
    assert bitwise(np.array([1.5, np.nan], dtype=np.float16), np.array([1.5, 0.0], dtype=np.float16)) is False
    assert bitwise(np.array([1.0], dtype=np.float32), np.array([np.nextafter(np.float32(1.0), np.float32(2.0))],
                                                               dtype=np.float32)) is False


COMPLETE = {"memmap_forced_low": "complete", "memmap_forced_high": "complete"}  # 開 lag 試跑 run 狀態（審碼 r17）


def test_precision_formal_readiness_requires_both_lag_rows() -> None:
    """審碼 r8：正式跑前置——兩 memmap 列缺任一、重複或未標 `measured_lag_on` ⇒ 違規。"""
    pc, est = probe("precision_chain"), probe("estimate")
    addenda = [{**a, "seconds": 100.0} for a in est.PRECISION_ADDENDA]  # 完整增列列（審碼 r11 之結構檢查）
    meas = {a["cell"]: {"seconds": 100.0, "status": "measured"} for a in est.PRECISION_ADDENDA}  # 增列秒數之實測來源（審碼 r15–r16）
    good = [{"cell": "A_BTCUSDT_1h", "variant": v, "measured_lag_on": True, "trial_status": "complete", "seconds": 200.0}
            for v in est.PRECISION_LAG_ON_VARIANTS]
    ok = {"run_kinds": {"precision_chain": {"addenda": addenda, "runs": good}}, "measurements": meas}
    assert pc.formal_readiness_violations(ok) == []
    for runs in ([], good[:1], good + good[:1], [dict(good[0], measured_lag_on=False), good[1]],
                 [dict(good[0], trial_status="blocked"), good[1]],  # 審碼 r17：秒數出自非完成之試跑 run
                 [{k: v for k, v in good[0].items() if k != "trial_status"}, good[1]]):
        receipt = {"run_kinds": {"precision_chain": {"addenda": addenda, "runs": runs}}, "measurements": meas}
        assert pc.formal_readiness_violations(receipt) != [], runs


def test_precision_unindexed_groups_detected(tmp_path: Path) -> None:
    """審碼 r8：對不上時間軸之 registry 群組（`S1_unindexed`）被列出（比對據以 fail-closed）。"""
    pc = probe("precision_chain")
    (tmp_path / "capture.json").write_text(json.dumps({"entries": [
        {"segment": "S1", "key": "g1", "rows": 500, "columns": ["a"]},
        {"segment": "S1_unindexed", "key": "g2", "rows": 3855, "columns": ["b"]}]}), encoding="utf-8")
    assert pc.unindexed_groups(str(tmp_path)) == ["g2"]


def test_precision_runs_violations_flags_missing_source_run() -> None:
    """審碼 r8：非 blocked 之統計列缺 `source_run` ⇒ 違規；blocked 列得無。"""
    receipt = {"rows": [{"cell_id": "C_BTCUSDT_1h", "segment": "S4", "status": "codec_off"}], "runs": {},
               "observed_settings": {}, "windows": {}}
    assert any("缺 source_run" in v for v in precision_runs_violations(receipt))
    receipt["rows"][0]["status"] = "blocked"
    assert precision_runs_violations(receipt) == []


def test_precision_checkpoint_stats_inf_vs_nan_not_all_nan() -> None:
    """審碼 r9：inf 對 NaN 為非有限類別不同 ⇒ 計入 `nan_mask_diff`、非 all_nan；兩邊皆 NaN 才 all_nan。"""
    stats = probe("precision_chain").checkpoint_stats
    got = stats(np.array([np.inf]), np.array([np.nan]))
    assert got["all_nan"] is False and got["nan_mask_diff"] == 1, got
    assert stats(np.array([-np.inf, 1.0]), np.array([np.inf, 1.0]))["nan_mask_diff"] == 1
    assert stats(np.array([np.nan]), np.array([np.nan]))["all_nan"] is True


def test_precision_group_rows_partial_reference_not_measured() -> None:
    """審碼 r9：群組內任一欄缺參照 ⇒ 群組列非 measured（`partial_no_reference`），不得被同群其他欄掩蓋。"""
    pc = probe("precision_chain")
    rows = pc.column_rows("S0", "C_BTCUSDT_1h", {"a": np.array([1.0]), "b": np.array([2.0])}, {"a": np.array([1.0])},
                          source_run="v", reference_run="r")
    grouped = pc.group_rows(rows, {"a": "g", "b": "g"}, "S0", "C_BTCUSDT_1h", "v", "r")
    assert len(grouped) == 1 and grouped[0]["status"] == "partial_no_reference" and grouped[0]["no_reference_columns"] == 1


def test_precision_formal_readiness_rejects_wrong_cell_and_bad_seconds() -> None:
    """審碼 r9：memmap 列之格非 A 宿主格、或秒數非有限正數 ⇒ 正式跑前置違規；估時增列套用拒非正秒數。"""
    pc, est = probe("precision_chain"), probe("estimate")
    addenda = [{**a, "seconds": 100.0} for a in est.PRECISION_ADDENDA]  # 完整增列列（審碼 r11 之結構檢查）
    meas = {a["cell"]: {"seconds": 100.0, "status": "measured"} for a in est.PRECISION_ADDENDA}  # 增列秒數之實測來源（審碼 r15–r16）
    base = [{"cell": "A_BTCUSDT_1h", "variant": v, "measured_lag_on": True, "trial_status": "complete", "seconds": 200.0}
            for v in est.PRECISION_LAG_ON_VARIANTS]
    assert pc.formal_readiness_violations({"run_kinds": {"precision_chain": {"addenda": addenda, "runs": base}}, "measurements": meas}) == []
    for mutate in ({"cell": "C_BTCUSDT_1h"}, {"seconds": 0.0}, {"seconds": -1.0}, {"seconds": float("nan")}):
        runs = [dict(base[0], **mutate), base[1]]
        assert pc.formal_readiness_violations({"run_kinds": {"precision_chain": {"addenda": addenda, "runs": runs}}, "measurements": meas}), mutate
    receipt = json.loads(sorted(nh.RECEIPTS_DIR.glob("*-numview-estimate.json"))[0].read_text(encoding="utf-8"))
    with pytest.raises(est.EstimateError):
        est.apply_precision_addenda(receipt, {"memmap_forced_low": -1.0, "memmap_forced_high": 0.0}, COMPLETE)
    with pytest.raises(est.EstimateError):  # 審碼 r10：JSON 布林 true 不得當 1 秒
        est.apply_precision_addenda(receipt, {"memmap_forced_low": True, "memmap_forced_high": 200.0}, COMPLETE)
    for status in ({**COMPLETE, "memmap_forced_low": "blocked"}, {"memmap_forced_high": "complete"}):  # 審碼 r17
        with pytest.raises(est.EstimateError):
            est.apply_precision_addenda(receipt, {"memmap_forced_low": 200.0, "memmap_forced_high": 190.0}, status)


def test_precision_chain_row_sources_match_definition() -> None:
    """Task 1.2 驗證（審碼 r11）：每個非 blocked 統計列之來源等於 SPEC v37 比對定義。"""
    assert precision_source_violations(load_receipt("precision-chain")) == []


def test_mutation_precision_row_source_swapped() -> None:
    """審碼 r11 之 mutation：A／S0 列之 `source_run` 換成同格他 run、或增列變體只放 `reference_run` ⇒ 來源檢查或兌現檢查紅
    （合成列，不依賴收據）。"""
    good = {"cell_id": "A_BTCUSDT_1h", "segment": "S0", "status": "measured", "source_run": "s0_float64_chain",
            "reference_run": "s0_float64_chain"}
    assert precision_source_violations({"rows": [good]}) == []
    assert precision_source_violations({"rows": [dict(good, source_run="codec_upgrade_on")]}) != []
    b_row = {"cell_id": "B_BTCUSDT_1h_4h", "segment": "S1", "status": "reference_is_production", "source_run": None,
             "reference_run": "b_production_spy"}
    assert any("B_BTCUSDT_1h_4h/S1" in v for v in precision_addenda_fulfillment_violations({"rows": [b_row]}))


def test_precision_l2_lift_observed_not_declared() -> None:
    """審碼 r11：`observed_settings.l2_polars_lift` 為實際觀測（抬升函式被呼叫次數 > 0），非取自變體宣告。"""
    pc = probe("precision_chain")
    obs = pc.Observer.__new__(pc.Observer)
    pc.Observer.__init__(obs, pc.Capture.__new__(pc.Capture), {"lift_l2": True})
    assert obs.settings()["l2_polars_lift"] is False
    obs.l2_lift_calls = 3
    assert obs.settings()["l2_polars_lift"] is True


@pytest.mark.parametrize("mutant", ["observed_settings_dropped", "variant_relabelled"])
def test_mutation_precision_runs_identity_r12(mutant: str) -> None:
    """審碼 r12 之 mutation：刪一個生成 run 之 `observed_settings`、身分表某鍵之 `variant` 改為他名 ⇒ 身分檢查紅。"""
    receipt = copy.deepcopy(load_receipt("precision-chain"))
    if mutant == "observed_settings_dropped":
        receipt["observed_settings"].pop("b_production_spy")
    else:
        receipt["runs"]["b_production_spy"]["variant"] = "codec_upgrade_on"
    assert precision_runs_violations(receipt) != []


def test_precision_chain_c_columns_closed_against_provenance() -> None:
    """Task 1.2 驗證（審碼 r12）：C 之 registry 擷取欄集合等於 provenance、讀回欄差只由死欄剔除解釋；A 之 S5 重演等於同次
    生產呼叫（收據 checks）。"""
    checks = load_receipt("precision-chain")["checks"]
    for key in ("C_BTCUSDT_1h.c_s0_columns_equal_provenance", "C_BTCUSDT_1h.c_readback_columns_explained",
                "A_BTCUSDT_1h.s5_replay_matches_production_run"):
        assert checks.get(key) is True, (key, checks.get(key))


def test_precision_provenance_duplicate_rows_rejected(tmp_path: Path) -> None:
    """審碼 r13：raw provenance 欄名重複 ⇒ `raw_provenance_terminals` 拋錯（不得壓成單鍵後通過閉合）。"""
    import pyarrow as pa
    import pyarrow.parquet as pq

    pc = probe("precision_chain")
    (tmp_path / "provenance").mkdir()
    table = pa.table({"output_column": ["a", "b"], "terminal": ["written", "written"]})
    pq.write_table(table, str(tmp_path / "provenance" / "raw_columns.parquet"))
    assert pc.raw_provenance_terminals(tmp_path) == {"a": "written", "b": "written"}
    pq.write_table(pa.table({"output_column": ["a", "a"], "terminal": ["written", "dead_dropped"]}),
                   str(tmp_path / "provenance" / "raw_columns.parquet"))
    with pytest.raises(RuntimeError, match="重複"):
        pc.raw_provenance_terminals(tmp_path)


def test_precision_blocked_run_not_production_equivalent() -> None:
    """審碼 r13：status 非 complete 之 run 不得判生產等價——以凍結 B run 本身充當 `b_production_spy`（讀回必逐位元相等），
    只把 status 設為 blocked ⇒ `b_production_equivalent` 為 False。"""
    pc = probe("precision_chain")
    fake = {"run_dir": str(pc._freeze_run_dir(pc.B_CELL)), "capture_dir": None, "status": "blocked",
            "settings_violations": []}
    out = pc.compare_b({"b_production_spy": fake}, {})
    assert out["checks"]["b_production_equivalent"] is False
    fake["status"] = "complete"
    assert pc.compare_b({"b_production_spy": fake}, {})["checks"]["b_production_equivalent"] is True


def test_precision_blocked_run_not_production_equivalent_a_and_c() -> None:
    """審碼 r14：A 之生產等價與 C 之 measured 路徑亦要求 status＝complete——以凍結 A run 充當 `codec_upgrade_on`
    （讀回必逐位元相等）：blocked ⇒ `a_production_equivalent` False、complete ⇒ True；C 之 `c_preserve_dtype` 為 failed
    ⇒ C 各段 blocked（以凍結 C run 充當，不讀擷取）。"""
    pc = probe("precision_chain")
    fake_a = {"run_dir": str(pc._freeze_run_dir(pc.HOST_CELL)), "capture_dir": None, "status": "blocked",
              "settings_violations": [], "raw_fallbacks": [], "processed_fallbacks": []}
    assert pc.compare_a({"codec_upgrade_on": fake_a})["checks"]["a_production_equivalent"] is False
    fake_a["status"] = "complete"
    assert pc.compare_a({"codec_upgrade_on": fake_a})["checks"]["a_production_equivalent"] is True
    fake_c = {"run_dir": str(pc._freeze_run_dir(pc.C_CELL)), "capture_dir": None, "status": "failed",
              "settings_violations": []}
    rows = pc.compare_c({"c_preserve_dtype": fake_c})["rows"]
    assert rows and {r["status"] for r in rows} == {"blocked"}
    # 審碼 r22：卡死監看判停滯 ⇒ S0–S3 blocked-by 硬體、凍結讀回之 S4 照記 codec_off
    fake_c["watch_status"] = pc._watchdog().STALLED
    rows = pc.compare_c({"c_preserve_dtype": fake_c})["rows"]
    chain = [r for r in rows if r["segment"] != "S4"]
    assert chain and all(r["status"] == "blocked" and r["reason"].startswith("blocked-by 硬體") for r in chain)
    s4 = [r for r in rows if r["segment"] == "S4"]
    assert s4 and {r["status"] for r in s4} == {"codec_off"}


@pytest.mark.parametrize("mutant", ["generations_bool", "seconds_unbound", "measurement_blocked", "measurement_zero"])
def test_precision_formal_readiness_addenda_type_and_binding(mutant: str) -> None:
    """審碼 r15–r16：正式跑前置——增列 `generations` 為布林、秒數脫離估時收據 `measurements` 實測值、該實測非 measured、
    或實測秒數為 0（增列秒數取極小正值）⇒ 違規。"""
    pc, est = probe("precision_chain"), probe("estimate")
    receipt = json.loads(sorted(nh.RECEIPTS_DIR.glob("*-numview-estimate.json"))[0].read_text(encoding="utf-8"))
    applied = est.apply_precision_addenda(receipt, {"memmap_forced_low": 200.0, "memmap_forced_high": 190.0}, COMPLETE)
    assert pc.formal_readiness_violations(applied) == []
    row = next(a for a in applied["run_kinds"]["precision_chain"]["addenda"] if a["variant"] == "b_production_spy")
    if mutant == "generations_bool":
        row["generations"] = True
    elif mutant == "seconds_unbound":
        row["seconds"] += 1.0
    elif mutant == "measurement_blocked":
        applied["measurements"]["B_BTCUSDT_1h_4h"]["status"] = "blocked"
    else:
        applied["measurements"]["B_BTCUSDT_1h_4h"]["seconds"] = 0.0
        row["seconds"] = 1e-10
    assert pc.formal_readiness_violations(applied) != []


# ============================================================================================== Task 1.6（v40）

POSTIC_CORE_KIND = "postic-core-select"
#: SPEC Task 1.6：核心收據名、路徑 × 輸入（分塊 (a)、(b)；直接 (a)）
POSTIC_CORES: Tuple[str, ...] = ("pandas_optimized", "pandas_legacy")
POSTIC_PATHS: Tuple[Tuple[str, str], ...] = (("chunked", "a"), ("direct", "a"), ("chunked", "b"))
#: 輸入 → 格（SPEC Task 1.6：(a) A_BTCUSDT_1h 凍結選欄、(b) 全特徵 C_BTCUSDT_1h 之 IC 重算選欄）
POSTIC_CELLS: Dict[str, str] = {"a": "A_BTCUSDT_1h", "b": "C_BTCUSDT_1h"}
#: blocked（未執行）單元得非 null 之欄（白名單；其餘監看、量測、身分、摘要欄一律須 null）
POSTIC_BLOCKED_FIELDS: Tuple[str, ...] = ("unit_id", "core", "path", "input", "cell", "status", "reason")
#: 單元之子行程回報欄（`postic_core_select._unit_row` 取自子行程結果者；failed 時一律 null）
POSTIC_CHILD_REPORTED_FIELDS: Tuple[str, ...] = (
    "wall_seconds", "load_seconds", "peak_rss_bytes", "arm_recorded", "core_observed", "chunk_calls",
    "ratio_unsafe_dropped", "terminals", "input_columns", "input_rows", "input_sha256", "post_ic_config", "output")
#: 收據 `checks` 之封閉鍵集（與 `postic_core_select.assemble` 同步；增刪須同改兩處）
POSTIC_CHECK_KEYS: Tuple[str, ...] = (
    "units_exactly_six", "watch_status_consistent", "inputs_identical_a", "inputs_identical_b", "chunk_calls_valid",
    "arm_recorded_matches_path", "post_ic_config_same", "pair_counts_recomputable", "ic_recompute_reproduces_a",
    "no_choice_without_choice")


def _postic_unit_id(core: str, path: str, inp: str) -> str:
    return f"{core}__{path}__{inp}"


def _postic_selection_with_rule(receipt: Mapping[str, Any]) -> Tuple[str, str, str]:
    """擇一規則之獨立重算（不呼叫探針；SPEC Task 1.6 ①–③）：回 ("choice", 核心, 規則) 或 ("no_choice", 規則分支, 規則分支)。"""
    units = {str(u["unit_id"]): u for u in receipt["units"]}
    wanted = [_postic_unit_id(c, p, i) for p, i in POSTIC_PATHS for c in POSTIC_CORES]
    if sorted(units) != sorted(wanted):
        return "no_choice", "1", "1"
    for uid in wanted:
        u = units[uid]
        short = uid.split("__")[0][len("pandas_"):]
        if u.get("status") != "complete" or list(u.get("core_observed") or []) != [short]:
            return "no_choice", "1", "1"
    pairs = {(str(p["path"]), str(p["input"])): p for p in receipt["pairs"]}
    if set(pairs) != set(POSTIC_PATHS):
        return "no_choice", "1", "1"

    def tiebreak() -> str:
        ranked = sorted(POSTIC_CORES, key=lambda c: (float(units[_postic_unit_id(c, "chunked", "b")]["wall_seconds"]),
                                                     int(units[_postic_unit_id(c, "chunked", "b")]["peak_rss_bytes"]),
                                                     POSTIC_CORES.index(c)))
        return ranked[0]

    if all(p["bitwise_equal"] for p in pairs.values()):
        return "choice", tiebreak(), "2"
    if any(not p["structure_equal"] for p in pairs.values()):
        return "no_choice", "3_structure", "3_structure"
    stats = (receipt.get("reference") or {}).get("stats")
    if not stats:
        return "no_choice", "3_reference_missing", "3_reference_missing"
    scale_units = {"a": [(p, "a") for p, i in POSTIC_PATHS if i == "a"], "b": [("chunked", "b")]}
    mask = {c: [all(int(stats[_postic_unit_id(c, p, i)]["nan_mask_diff"]) == 0 for p, i in scale_units[s])
                for s in ("a", "b")] for c in POSTIC_CORES}
    passing = [c for c in POSTIC_CORES if all(mask[c])]
    if len(passing) == 1:
        return "choice", passing[0], "3_nan_mask"
    if not passing:
        return "no_choice", "3_nan_mask", "3_nan_mask"
    err: Dict[str, List[float]] = {}
    for c in POSTIC_CORES:
        err[c] = []
        for s in ("a", "b"):
            rows = [stats[_postic_unit_id(c, p, i)] for p, i in scale_units[s]]
            if any(int(r["common_finite_cells"]) == 0 for r in rows):
                return "no_choice", "3_no_common_finite", "3_no_common_finite"
            err[c].append(max(float(r["max_abs"]) for r in rows))
    x, y = POSTIC_CORES
    x_better = [ex < ey for ex, ey in zip(err[x], err[y])]
    y_better = [ey < ex for ex, ey in zip(err[x], err[y])]
    if not any(x_better) and not any(y_better):
        return "choice", tiebreak(), "3_error_tie"
    if any(x_better) and not any(y_better):
        return "choice", x, "3_error"
    if any(y_better) and not any(x_better):
        return "choice", y, "3_error"
    return "no_choice", "3_error_conflict", "3_error_conflict"


def expected_postic_selection(receipt: Mapping[str, Any]) -> Tuple[str, str]:
    """擇一規則之獨立重算：回 ("choice", 核心) 或 ("no_choice", 規則分支)。"""
    kind, value, _ = _postic_selection_with_rule(receipt)
    return kind, value


def postic_core_violations(receipt: Mapping[str, Any]) -> List[str]:
    """SPEC Task 1.6 驗證（收據層）：單元完整與記錄齊全、監看與狀態一致、實際核心與塊呼叫數、成對比對列存在且計數可由逐欄
    列重算、擇一結果等於獨立重算、`no_choice` 無 `choice` 且具理由、擇定核心之單元皆 complete、IC 重算具監看與牆鐘。"""
    out: List[str] = []
    units = {str(u["unit_id"]): u for u in receipt.get("units") or []}
    wanted = [_postic_unit_id(c, p, i) for p, i in POSTIC_PATHS for c in POSTIC_CORES]
    if sorted(units) != sorted(wanted) or len(receipt.get("units") or []) != len(wanted):
        out.append(f"單元集合 {sorted(units)} ≠ {sorted(wanted)}")
    for uid, u in units.items():
        if u.get("status") not in ("complete", "failed", "blocked"):
            out.append(f"{uid}：狀態 {u.get('status')!r} 非 complete／failed／blocked")
        if u.get("status") == "blocked":
            # blocked＝未執行（前置不可得）：須具理由且無任何監看或量測紀錄
            if not u.get("reason"):
                out.append(f"{uid}：blocked 無理由")
            ran = sorted(k for k, v in u.items() if v is not None and k not in POSTIC_BLOCKED_FIELDS)
            if ran:
                out.append(f"{uid}：blocked（未執行）而有監看／量測紀錄 {ran}")
            continue
        if u.get("status") == "failed":
            if not u.get("reason"):
                out.append(f"{uid}：failed 無理由")
            # failed＝子行程未回報 ⇒ 子行程回報之欄一律 null（不得帶量測值）
            reported = sorted(k for k in POSTIC_CHILD_REPORTED_FIELDS if u.get(k) is not None)
            if reported:
                out.append(f"{uid}：failed 而帶子行程回報欄 {reported}")
        if not u.get("watch_status") or "returncode" not in u:
            out.append(f"{uid}：缺 watch_status 或 returncode 欄")
        normal = u.get("watch_status") == "exited" and u.get("returncode") == 0
        if not normal and u.get("status") != "failed":
            out.append(f"{uid}：watch_status={u.get('watch_status')} rc={u.get('returncode')} 而狀態 {u.get('status')}")
        if u.get("child_wall_seconds") is None:
            out.append(f"{uid}：缺 child_wall_seconds")
        if u.get("status") == "complete":
            for key in ("wall_seconds", "peak_rss_bytes", "input_sha256", "output"):
                if u.get(key) is None:
                    out.append(f"{uid}：complete 缺 {key}")
            core, path, _ = uid.split("__")
            if list(u.get("core_observed") or []) != [core[len("pandas_"):]]:
                out.append(f"{uid}：core_observed={u.get('core_observed')}")
            if int(u.get("chunk_calls") or 0) < (2 if path == "chunked" else 1):
                out.append(f"{uid}：chunk_calls={u.get('chunk_calls')}")
            if list(u.get("arm_recorded") or []) != (["pandas_chunked"] if path == "chunked" else [core]):
                out.append(f"{uid}：arm_recorded={u.get('arm_recorded')}")
    checks = receipt.get("checks")
    if (not isinstance(checks, Mapping) or set(checks) != set(POSTIC_CHECK_KEYS)
            or not all(v is True for v in checks.values())):
        out.append(f"收據自我檢查非封閉鍵集或非全真：{checks}")
    # 收據旗標之外獨立重算：同輸入之 complete 單元輸入身分相同、全部 complete 單元之 post-IC 設定相同
    done = [u for u in units.values() if u.get("status") == "complete"]
    for inp in ("a", "b"):
        shas = {u.get("input_sha256") for u in done if u.get("input") == inp}
        if len(shas) > 1:
            out.append(f"輸入 ({inp}) 之單元輸入身分不同：{sorted(map(str, shas))}")
    if len({json.dumps(u.get("post_ic_config"), sort_keys=True) for u in done}) > 1:
        out.append("complete 單元之 post-IC 設定不同")
    pair_rows = list(receipt.get("pairs") or [])
    pairs = {(str(p["path"]), str(p["input"])): p for p in pair_rows}
    if len(pairs) != len(pair_rows) or not set(pairs) <= set(POSTIC_PATHS):
        out.append(f"成對比對列重複或含非契約路徑：{[(p.get('path'), p.get('input')) for p in pair_rows]}")
    for key, p in pairs.items():
        expected_units = [_postic_unit_id(c, *key) for c in POSTIC_CORES]
        if list(p.get("units") or []) != expected_units:
            out.append(f"成對比對 {key}：units={p.get('units')} ≠ {expected_units}")
        both_done = all((units.get(uid) or {}).get("status") == "complete" for uid in expected_units)
        if not both_done:
            out.append(f"成對比對 {key}：兩單元非皆 complete 而有比對列")
        rows_max = max((float(v) for v in (p.get("diff_columns") or {}).get("max_abs") or []), default=0.0)
        if float(p.get("max_abs") if p.get("max_abs") is not None else -1.0) != rows_max:
            out.append(f"成對比對 {key}：max_abs={p.get('max_abs')} ≠ 逐欄列最大值 {rows_max}")
    for path, inp in POSTIC_PATHS:
        both = all((units.get(_postic_unit_id(c, path, inp)) or {}).get("status") == "complete" for c in POSTIC_CORES)
        if both and (path, inp) not in pairs:
            out.append(f"成對比對缺 {path}/{inp}")
    for key, p in pairs.items():
        rows = p.get("diff_columns") or {}
        dtype_x, dtype_y = rows.get("dtype_x") or [], rows.get("dtype_y") or []
        if (p.get("columns_unequal_native") != len(rows.get("column") or [])
                or p.get("nan_mask_diff") != sum(rows.get("nan_mask_diff") or [])
                or p.get("value_neq_cells") != sum(rows.get("value_neq_cells") or [])
                or p.get("dtype_mismatch_columns") != sum(1 for a, b in zip(dtype_x, dtype_y) if a != b)):
            out.append(f"成對比對 {key}：計數與逐欄列不符")
        # 結構與逐位元旗標由構成欄重算（欄集合與順序、時間軸、只在一側之欄、dtype 不符欄數、原生不等欄數）
        only = list(p.get("only_x") or []) + list(p.get("only_y") or [])
        if only and p.get("columns_equal"):
            out.append(f"成對比對 {key}：有只在一側之欄而 columns_equal 為真")
        structure = (p.get("columns_equal") is True and p.get("index_equal") is True and not only
                     and int(p.get("dtype_mismatch_columns") or 0) == 0)
        if p.get("structure_equal") is not structure:
            out.append(f"成對比對 {key}：structure_equal={p.get('structure_equal')} ≠ 重算 {structure}")
        bitwise = structure and int(p.get("columns_unequal_native") or 0) == 0
        if p.get("bitwise_equal") is not bitwise:
            out.append(f"成對比對 {key}：bitwise_equal={p.get('bitwise_equal')} ≠ 重算 {bitwise}")
    for uid, u in units.items():
        core, path, inp = uid.split("__")
        if (u.get("core"), u.get("path"), u.get("input"), u.get("cell")) != (core, path, inp, POSTIC_CELLS.get(inp)):
            out.append(f"{uid}：身分欄 {(u.get('core'), u.get('path'), u.get('input'), u.get('cell'))} 與 unit_id／契約格不符")
    # 參考實作比對只在「全部單元 complete、三對結構皆一致、而非全部逐位元相等」時存在（規則③）
    needs_reference = (len(pairs) == len(POSTIC_PATHS) and all(u.get("status") == "complete" for u in units.values())
                       and all(p.get("structure_equal") for p in pairs.values())
                       and not all(p.get("bitwise_equal") for p in pairs.values()))
    if needs_reference != (receipt.get("reference") is not None):
        out.append(f"參考實作比對之有無（{receipt.get('reference') is not None}）與規則③之需要（{needs_reference}）不符")
    kind, value, rule = _postic_selection_with_rule(receipt)
    if kind == "choice":
        if receipt.get("choice") != value or "no_choice" in receipt or receipt.get("choice_rule") != rule:
            out.append(f"擇一重算＝choice {value}（規則 {rule}）；收據 choice={receipt.get('choice')!r} "
                       f"choice_rule={receipt.get('choice_rule')!r} no_choice={receipt.get('no_choice')!r}")
        elif any(u.get("status") != "complete" for uid, u in units.items() if uid.startswith(value + "__")):
            out.append(f"擇定 {value} 而其單元非全 complete")
    else:
        node = receipt.get("no_choice") or {}
        if "choice" in receipt or node.get("rule") != value or not node.get("reason"):
            out.append(f"擇一重算＝no_choice 規則 {value}；收據 choice={receipt.get('choice')!r} no_choice={node!r}")
        elif value == "3_structure":
            # 理由須逐字列出重算之結構不一致路徑（依契約路徑序）
            broken = [f"{p}/{i}" for p, i in POSTIC_PATHS if not (pairs.get((p, i)) or {}).get("structure_equal", True)]
            if not str(node.get("reason")).endswith(repr(broken)):
                out.append(f"no_choice 理由未列重算之結構不一致路徑 {broken}：{node.get('reason')!r}")
        elif value == "1":
            bad = [uid for uid in (_postic_unit_id(c, p, i) for p, i in POSTIC_PATHS for c in POSTIC_CORES)
                   if (units.get(uid) or {}).get("status") != "complete"]
            if any(uid not in str(node.get("reason")) for uid in bad):
                out.append(f"no_choice 理由未列非 complete 之單元 {bad}：{node.get('reason')!r}")
    ic = receipt.get("ic_recompute") or {}
    # IC 重算之 wall_seconds＝監看量得之子行程牆鐘（complete／failed 皆可得）；返回碼欄須存在（被終止者可為 null）
    if not ic.get("watch_status") or "returncode" not in ic or ic.get("child_wall_seconds") is None:
        out.append("IC 重算缺 watch_status、returncode 欄或子行程牆鐘")
    if ic.get("wall_seconds") is None or ic.get("wall_seconds") != ic.get("child_wall_seconds"):
        out.append(f"IC 重算 wall_seconds={ic.get('wall_seconds')} ≠ 子行程牆鐘 {ic.get('child_wall_seconds')}")
    if ic.get("status") not in ("complete", "failed"):
        out.append(f"IC 重算狀態 {ic.get('status')!r} 非 complete／failed")
    if ic.get("status") == "complete" and ic.get("peak_rss_bytes") is None:
        out.append("IC 重算 complete 缺峰值 RSS")
    if ic.get("status") == "complete":
        # 選欄摘要須具並與輸入及單元一致：(a) 重算數＝凍結選欄數、(b) 選欄數＝收據 inputs.b、各單元讀入欄數＝其輸入之選欄數
        inputs = receipt.get("inputs") or {}
        for inp in ("a", "b"):
            summary = ic.get(inp) or {}
            if not isinstance(summary.get("selected_count"), int) or not summary.get("label_rows"):
                out.append(f"IC 重算 complete 缺 ({inp}) 選欄摘要")
                continue
            if (inputs.get(inp) or {}).get("selected") != summary["selected_count"]:
                out.append(f"({inp}) 選欄數：inputs={(inputs.get(inp) or {}).get('selected')} ≠ IC 重算 {summary['selected_count']}")
            for u in done:
                if u.get("input") == inp and u.get("input_columns") != summary["selected_count"]:
                    out.append(f"{u['unit_id']}：讀入欄數 {u.get('input_columns')} ≠ ({inp}) 選欄數 {summary['selected_count']}")
    if ic.get("status") == "failed":
        if not ic.get("reason"):
            out.append("IC 重算 failed 無理由")
        reported = sorted(k for k in ("peak_rss_bytes", "a", "b") if ic.get(k) is not None)
        if reported:
            out.append(f"IC 重算 failed 而帶子行程回報欄 {reported}")
    # SPEC Task 1.6：watch_status 非正常結束（非 exited 或 rc≠0）⇒ 狀態必為 failed 且收據不得有 choice（單元與 IC 重算皆然）
    ic_normal = ic.get("watch_status") == "exited" and ic.get("returncode") == 0
    if not ic_normal and ic.get("status") != "failed":
        out.append(f"IC 重算 watch_status={ic.get('watch_status')} rc={ic.get('returncode')} 而狀態 {ic.get('status')}")
    if ic.get("status") != "complete":
        if "choice" in receipt:
            out.append("IC 重算未完成而收據有 choice")
        if any(u.get("input") == "b" and u.get("status") != "blocked" for u in units.values()):
            out.append("IC 重算未完成而 (b) 單元非 blocked")
    abnormal = [uid for uid, u in units.items() if u.get("status") != "blocked"
                and not (u.get("watch_status") == "exited" and u.get("returncode") == 0)]
    if abnormal and "choice" in receipt:
        out.append(f"單元監看非正常結束而收據有 choice：{abnormal}")
    return out


def test_postic_core_receipt_rc_and_criteria() -> None:
    assert _receipt_common_violations(load_receipt(POSTIC_CORE_KIND)) == []


def test_postic_core_receipt_contract() -> None:
    """SPEC Task 1.6 驗證：收據層全部檢查（含擇一結果由獨立重算相等）。"""
    assert postic_core_violations(load_receipt(POSTIC_CORE_KIND)) == []


def _postic_saved(out_dir: Path) -> Tuple[List[str], Dict[str, str], np.ndarray, Callable[[str], np.ndarray]]:
    """量測產物讀回（獨立於探針 `SavedFrame`）：`meta.json` 之欄序與 dtype、`index.npy`、依 dtype 分塊之 `block_<dtype>.npy`。"""
    meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    columns = [str(c) for c in meta["columns"]]
    dtypes = dict(zip(columns, [str(d) for d in meta["dtypes"]]))
    blocks = {d: np.load(out_dir / f"block_{d}.npy", mmap_mode="r") for d in meta["blocks"]}
    where = {name: (d, j) for d, names in meta["blocks"].items() for j, name in enumerate(names)}
    assert sorted(where) == sorted(columns) and all(blocks[d].dtype == np.dtype(d) for d in blocks), out_dir

    def column(name: str) -> np.ndarray:
        d, j = where[name]
        return np.asarray(blocks[d][:, j])

    return columns, dtypes, np.load(out_dir / "index.npy"), column


def _postic_pair_from_outputs(x_dir: Path, y_dir: Path) -> Dict[str, Any]:
    """成對比對之獨立重算（SPEC Task 1.6：值原生逐位元〔NaN payload 不計〕、NaN 遮罩、dtype、欄集合與順序、時間軸）。"""
    xc, xd, xi, xcol = _postic_saved(x_dir)
    yc, yd, yi, ycol = _postic_saved(y_dir)
    rows: Dict[str, List[Any]] = {k: [] for k in ("column", "dtype_x", "dtype_y", "nan_mask_diff", "value_neq_cells", "max_abs")}
    for name in (c for c in xc if c in yd):
        a, b = xcol(name), ycol(name)
        a64, b64 = a.astype(np.float64), b.astype(np.float64)
        na, nb = np.isnan(a64), np.isnan(b64)
        same = (a.dtype == b.dtype and np.array_equal(na, nb)
                and np.array_equal(a[~na].tobytes(), b[~nb].tobytes()))
        if same:
            continue
        both = ~na & ~nb
        rows["column"].append(name)
        rows["dtype_x"].append(str(a.dtype))
        rows["dtype_y"].append(str(b.dtype))
        rows["nan_mask_diff"].append(int((na != nb).sum()))
        rows["value_neq_cells"].append(int((both & (a64 != b64)).sum()))
        rows["max_abs"].append(float(np.abs(a64[both] - b64[both]).max()) if both.any() else 0.0)
    return {"columns_equal": xc == yc, "index_equal": bool(np.array_equal(xi, yi)),
            "only_x": sorted(set(xc) - set(yd)), "only_y": sorted(set(yc) - set(xd)), "diff_columns": rows,
            "output_x": {"shape": [int(len(xi)), len(xc)],
                         "dtypes": {d: sum(1 for c in xc if xd[c] == d) for d in sorted(set(xd.values()))}},
            "output_y": {"shape": [int(len(yi)), len(yc)],
                         "dtypes": {d: sum(1 for c in yc if yd[c] == d) for d in sorted(set(yd.values()))}}}


def postic_core_artifact_violations(receipt: Mapping[str, Any]) -> List[str]:
    """收據對量測產物之重建（秒級）：工作目錄之輸出逐單元重算成對比對（逐欄列與全部旗標）與輸出摘要、輸入來源身分
    （複本路徑、凍結 sidecar 之 config_hash、凍結與複本 manifest 之 sha256、(a) 凍結選欄數）、牆鐘與記憶體欄之一致界限。"""
    out: List[str] = []
    work = Path(str(receipt.get("work_root")))
    if not work.is_dir():
        return [f"量測工作目錄不存在（產物須保留至收票）：{work}"]
    units = {str(u["unit_id"]): u for u in receipt["units"]}
    for uid, u in units.items():
        if u.get("status") != "complete":
            continue
        if Path(str(u.get("out_dir"))) != work / "outputs" / uid:
            out.append(f"{uid}：out_dir {u.get('out_dir')} ≠ {work / 'outputs' / uid}")
        wall, load, child = u.get("wall_seconds"), u.get("load_seconds"), u.get("child_wall_seconds")
        if not (isinstance(wall, (int, float)) and isinstance(load, (int, float)) and isinstance(child, (int, float))
                and 0 < wall and 0 <= load and wall + load <= child):
            out.append(f"{uid}：牆鐘不一致 wall={wall} load={load} child={child}")
        if not (isinstance(u.get("peak_rss_bytes"), int) and u["peak_rss_bytes"] > 0):
            out.append(f"{uid}：峰值 RSS {u.get('peak_rss_bytes')}")
    for p in receipt["pairs"]:
        x_id, y_id = p["units"]
        rebuilt = _postic_pair_from_outputs(work / "outputs" / x_id, work / "outputs" / y_id)
        key = (p["path"], p["input"])
        for field in ("columns_equal", "index_equal", "only_x", "only_y", "diff_columns"):
            if p.get(field) != rebuilt[field]:
                out.append(f"成對比對 {key}：{field} 與產物重算不符")
        for uid, side in ((x_id, "output_x"), (y_id, "output_y")):
            if (units.get(uid) or {}).get("output") != rebuilt[side]:
                out.append(f"{uid}：output 摘要 {units.get(uid, {}).get('output')} ≠ 產物 {rebuilt[side]}")
            if (units.get(uid) or {}).get("input_rows") != rebuilt[side]["shape"][0]:
                out.append(f"{uid}：input_rows ≠ 輸出列數 {rebuilt[side]['shape'][0]}")
    for inp, cell in POSTIC_CELLS.items():
        node = (receipt.get("inputs") or {}).get(inp) or {}
        frozen = REPO / "data_cache" / "numview_freeze_runs" / f"{cell}__default"
        side = json.loads((frozen / "numview_cell.json").read_text(encoding="utf-8"))
        rel = Path("features") / side["symbol"] / side["primary_tf"] / side["config_hash"] / "feature_manifest.json"
        # 選欄來源（SPEC Task 1.6）：(a)＝凍結 run 之 IC-first 選欄、(b)＝以生產 IC-first 程序重算
        expect = {"cell": cell, "selected_source": {"a": "frozen", "b": "ic_recompute"}[inp],
                  "features_root": str(work / "copies" / cell / "features"),
                  "config_hash": side["config_hash"],
                  "manifest_sha256": hashlib.sha256((frozen / rel).read_bytes()).hexdigest(),
                  "copy_manifest_sha256": hashlib.sha256((work / "copies" / cell / rel).read_bytes()).hexdigest()}
        for k, v in expect.items():
            if node.get(k) != v:
                out.append(f"inputs.{inp}.{k}={node.get(k)!r} ≠ {v!r}")
        if expect["manifest_sha256"] != expect["copy_manifest_sha256"]:
            out.append(f"({inp}) 複本 manifest 與凍結不同")
        if inp == "a" and node.get("selected") != len(side["ic_first_selected"]):
            out.append(f"inputs.a.selected={node.get('selected')} ≠ 凍結選欄數 {len(side['ic_first_selected'])}")
    ic = receipt.get("ic_recompute") or {}
    if ic.get("status") == "complete":
        seconds = sum(float((ic.get(i) or {}).get("seconds") or 0.0) for i in ("a", "b"))
        if not (0 < seconds <= float(ic.get("child_wall_seconds") or 0.0)):
            out.append(f"IC 重算各格秒數合計 {seconds} 不在 (0, 子行程牆鐘] 內")
    return out


def test_postic_core_receipt_reproduced_from_outputs() -> None:
    """SPEC Task 1.6「成對比對列存在且數字可由收據列機械重算」之產物層：成對比對與輸出摘要由工作目錄之輸出獨立重算（審碼
    b2 r39：收據自報欄不得只對自身對證）。"""
    assert postic_core_artifact_violations(load_receipt(POSTIC_CORE_KIND)) == []


@pytest.mark.parametrize("mutant", ["diff_row", "output_summary", "config_hash", "wall", "selected_source"])
def test_postic_core_artifact_mutations(mutant: str) -> None:
    """mutation：正式收據之逐欄差異列、單元輸出摘要、輸入 config_hash、牆鐘（轉換＋讀入逾子行程牆鐘）各單改 ⇒ 產物重建紅。"""
    receipt = copy.deepcopy(load_receipt(POSTIC_CORE_KIND))
    if mutant == "diff_row":
        pair = next(p for p in receipt["pairs"] if p["diff_columns"]["column"])
        pair["diff_columns"]["dtype_y"][0] = "float16"
    elif mutant == "output_summary":
        receipt["units"][0]["output"]["shape"][1] += 1
    elif mutant == "config_hash":
        receipt["inputs"]["a"]["config_hash"] = "0" * 32
    elif mutant == "selected_source":
        receipt["inputs"]["b"]["selected_source"] = "frozen"
    else:
        receipt["units"][0]["wall_seconds"] = float(receipt["units"][0]["child_wall_seconds"]) + 1.0
    assert postic_core_artifact_violations(receipt), f"mutant {mutant} 存活"


def _postic_frame_sha256(frame: pd.DataFrame) -> str:
    """輸入身分之獨立重算（定義同 SPEC Task 1.6 收據：欄序與逐欄 dtype、時間軸 int64、逐欄原生位元組）。"""
    digest = hashlib.sha256()
    digest.update(json.dumps([[str(c), str(frame[c].dtype)] for c in frame.columns]).encode("utf-8"))
    digest.update(np.ascontiguousarray(np.asarray(frame.index.asi8, dtype=np.int64)).tobytes())
    for c in frame.columns:
        digest.update(np.ascontiguousarray(frame[c].to_numpy()).tobytes())
    return digest.hexdigest()


@pytest.fixture
def postic_vm_snapshot() -> Any:
    """系統記憶體讀數（`sysctl vm.swapusage`）於部分沙箱不可用 ⇒ 以既有測試接縫注入固定快照（同
    test_icfirstalign_memory.py:_snapshot）；只隔離環境讀數，IC 與轉換路徑不變。"""
    from momentum.FeatureEngineering import memory_budget as mb

    snapshot = mb.VMSnapshot(free_bytes=8 * 2 ** 30, file_backed_bytes=0, swap_free_bytes=0, pressure_level=1,
                             swap_volume_free_bytes=75 * 2 ** 30, swap_volume_capacity_bytes=228 * 2 ** 30)
    with mb.vm_snapshot_override(snapshot):
        yield snapshot


def test_postic_core_ic_and_inputs_reproduced(tmp_path: Path, postic_vm_snapshot: Any) -> None:
    """IC 重算與單元輸入之獨立重現（約 5 分鐘；峰值 RSS 約 0.7 GB）：凍結 A、C 之 run 複製至 tmp，以生產標籤（kline close
    之 `pct_change().shift(-1)`、公開窗遮罩）與 `ICEngine.compute_ic_from_l7_raw`（判準 `cell_definitions.A.generation`、
    選窗＝標籤時間戳起訖）重算選欄——A 須逐項等於凍結選欄、C 之選欄數等於收據；標籤列數與 sha256 等於收據；以重算選欄自收據之
    複本讀 raw（`load_columns_v2`），輸入身分等於各單元 `input_sha256`、讀入欄數等於 `input_columns`；(b) 輸出欄＝選欄依序去
    ratio-unsafe 欄。"""
    import shutil

    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    receipt = load_receipt(POSTIC_CORE_KIND)
    criteria = load_criteria()
    est = probe("estimate")
    generation = criteria["cell_definitions"]["A"]["generation"]
    work = Path(receipt["work_root"])
    for inp, cell_id in POSTIC_CELLS.items():
        cell = next(c for c in criteria["cell_rules"]["cell_list"]["cells"] if str(c["id"]) == cell_id)
        frozen = REPO / "data_cache" / "numview_freeze_runs" / f"{cell_id}__default"
        side = json.loads((frozen / "numview_cell.json").read_text(encoding="utf-8"))
        rel = Path("features") / side["symbol"] / side["primary_tf"] / side["config_hash"]
        shutil.copytree(frozen / rel, tmp_path / cell_id / rel)
        training = [str(t) for t in cell["timeframes"]]
        source = est.cell_source(cell, criteria)
        start, end = est.cell_window(cell, criteria)
        factory = create_feature_factory(cache_dir=str(source.parent),
                                         validate_continuity=est.continuity_plan(cell, criteria, training)["validate_continuity"])
        config = factory._resolve_config(est.cell_payload(cell, criteria, training))
        kline = factory._layer0_data_ingestion(side["symbol"], side["primary_tf"], config, start_date=start, end_date=end)
        index = factory._derive_row_index_for_artifact(kline)
        close = pd.Series(kline["close"].to_numpy(dtype=float), index=index)
        label = close.pct_change().shift(-1)[factory._utc_window_mask(index, start, end)]
        summary = receipt["ic_recompute"][inp]
        assert summary["label_rows"] == len(label)
        assert summary["label_sha256"] == hashlib.sha256(
            np.ascontiguousarray(label.to_numpy(dtype=np.float64)).tobytes()).hexdigest()
        stamps = pd.DatetimeIndex(label.index)
        result = ICEngine(dict(generation["ic_engine_config"])).compute_ic_from_l7_raw(
            side["symbol"], side["primary_tf"], side["config_hash"], label,
            feature_reader=FeatureReader(str(tmp_path / cell_id / "features")), ic_threshold=generation["ic_threshold"],
            allow_partial_ic=False, method=None, label_horizon=str(generation["label_horizon"]),
            selection_window={"start": str(stamps.min()), "end": str(stamps.max())}, split_id="ic_first_full_window")
        selected = [str(f) for f in getattr(result, "selected", [])]
        assert summary["selection_window"] == {"start": str(stamps.min()), "end": str(stamps.max())}
        assert summary["ic_params"] == {k: generation[k] for k in ("ic_engine_config", "ic_threshold", "label_horizon")}
        # post-IC 設定：生產已解析設定之 preprocessing（IC-first 傳 `config.preprocessing`）之 rank／zscore／gaussian 與模式
        pre = config.preprocessing.model_dump()
        expected_post_ic = {k: pre.get(k) for k in ("mode", "causal_preprocessing", "rank_transform", "adaptive_zscore",
                                                    "gaussian_normalize")}
        for u in receipt["units"]:
            if u["input"] == inp and u["status"] == "complete":
                assert json.loads(json.dumps(u["post_ic_config"])) == json.loads(json.dumps(expected_post_ic)), u["unit_id"]
        if inp == "a":
            assert selected == [str(c) for c in side["ic_first_selected"]], "A 之 IC 重算未重現凍結選欄"
        assert len(selected) == summary["selected_count"] == receipt["inputs"][inp]["selected"]
        raw = FeatureReader(receipt["inputs"][inp]["features_root"]).load_columns_v2(
            side["symbol"], side["primary_tf"], side["config_hash"], selected, artifact_kind="raw", attach_row_index=True)
        sha = _postic_frame_sha256(raw)
        for u in receipt["units"]:
            if u["input"] == inp and u["status"] == "complete":
                assert u["input_sha256"] == sha and u["input_columns"] == raw.shape[1], u["unit_id"]
                columns, _, _, _ = _postic_saved(work / "outputs" / u["unit_id"])
                assert columns == [c for c in selected if ratio_unsafe_category(c) is None], u["unit_id"]
                assert u["ratio_unsafe_dropped"] == sum(1 for c in selected if ratio_unsafe_category(c) is not None)
        del raw


def test_postic_core_receipt_bound_to_probe_source() -> None:
    """收據綁定產出之量測程式（試跑收據轉為正式收據時尤須）：`probe_sha256` 等於現行 `postic_core_select.py` 之 sha256。"""
    receipt = load_receipt(POSTIC_CORE_KIND)
    current = hashlib.sha256((PROBE_DIR / "postic_core_select.py").read_bytes()).hexdigest()
    assert receipt.get("probe_sha256") == current, (receipt.get("probe_sha256"), current)


def test_postic_core_decision_matches_receipt() -> None:
    """SPEC Task 1.6／1.5 ⑧：決定紀錄 d_icpage_arm 之 `report.post_ic_core` 等於收據 `choice`；收據 `no_choice` ⇒
    `report.no_choice_reason` 等於收據理由，且無 `report.core_user_ruling` 時該欄為 `"no_choice"`、有之（`{date, quote}`
    非空；v41 使用者 2026-10-24「legacy」）時為裁定之核心（屬兩核心）；收據已擇一而具 `core_user_ruling` ⇒ 紅。決定紀錄未
    產出（Task 1.5）前為紅。"""
    receipt = load_receipt(POSTIC_CORE_KIND)
    report = nh._decision_record("d_icpage_arm").get("report") or {}
    ruling = report.get("core_user_ruling")
    if "choice" in receipt:
        assert ruling is None, "收據已擇一而決定紀錄另具使用者裁定"
        assert report.get("post_ic_core") == receipt["choice"], report
    else:
        assert report.get("no_choice_reason") == receipt["no_choice"]["reason"], report
        if ruling is None:
            assert report.get("post_ic_core") == "no_choice", report
        else:
            assert isinstance(ruling, Mapping) and ruling.get("date") and ruling.get("quote"), ruling
            core = ruling.get("core")
            assert core in POSTIC_CORES and report.get("post_ic_core") == core, (ruling, report)
            short, other = core[len("pandas_"):], next(c for c in POSTIC_CORES if c != core)[len("pandas_"):]
            assert short in str(ruling["quote"]) and other not in str(ruling["quote"]), ruling
            assert ruling.get("output_dtype") == "float32" and "float32" in str(ruling.get("output_dtype_quote") or ""), ruling
            assert report.get("post_ic_output_dtype") == ruling["output_dtype"], report


def _postic_synthetic(**over: Any) -> Dict[str, Any]:
    """擇一規則單元案之合成收據骨架（只供規則之分支測試；數值為控制變因，非量測資料）：全單元 complete、三對逐位元相等。"""
    units = []
    for path, inp in POSTIC_PATHS:
        for core in POSTIC_CORES:
            units.append({"unit_id": _postic_unit_id(core, path, inp), "core": core, "path": path, "input": inp,
                          "status": "complete", "watch_status": "exited", "returncode": 0, "child_wall_seconds": 10.0,
                          "wall_seconds": 5.0, "peak_rss_bytes": 1000, "input_sha256": f"in-{inp}",
                          "core_observed": [core[len("pandas_"):]], "chunk_calls": 2 if path == "chunked" else 1,
                          "arm_recorded": ["pandas_chunked"] if path == "chunked" else [core],
                          "cell": POSTIC_CELLS[inp], "input_columns": 3, "output": {"shape": [500, 3]}})
    pairs = [{"path": p, "input": i, "units": [_postic_unit_id(c, p, i) for c in POSTIC_CORES], "max_abs": 0.0,
              "columns_equal": True, "index_equal": True, "only_x": [], "only_y": [],
              "structure_equal": True, "bitwise_equal": True, "columns_unequal_native": 0,
              "nan_mask_diff": 0, "value_neq_cells": 0, "dtype_mismatch_columns": 0,
              "diff_columns": {"column": [], "dtype_x": [], "dtype_y": [], "nan_mask_diff": [], "value_neq_cells": [],
                               "max_abs": []}} for p, i in POSTIC_PATHS]
    receipt = {"units": units, "pairs": pairs, "reference": None, "checks": {k: True for k in POSTIC_CHECK_KEYS},
               "inputs": {inp: {"cell": cell, "selected": 3} for inp, cell in POSTIC_CELLS.items()},
               "ic_recompute": {"status": "complete", "watch_status": "exited", "returncode": 0, "wall_seconds": 1.0,
                                "child_wall_seconds": 1.0, "peak_rss_bytes": 1,
                                "a": {"selected_count": 3, "label_rows": 500}, "b": {"selected_count": 3, "label_rows": 500}}}
    receipt.update(over)
    return receipt


def _postic_unit(receipt: Dict[str, Any], uid: str) -> Dict[str, Any]:
    return next(u for u in receipt["units"] if u["unit_id"] == uid)


def _postic_unequal(receipt: Dict[str, Any], key: Tuple[str, str]) -> None:
    pair = next(p for p in receipt["pairs"] if (p["path"], p["input"]) == key)
    pair.update(bitwise_equal=False, columns_unequal_native=1, value_neq_cells=3, max_abs=1e-7,
                diff_columns={"column": ["c0"], "dtype_x": ["float32"], "dtype_y": ["float32"], "nan_mask_diff": [0],
                              "value_neq_cells": [3], "max_abs": [1e-7]})


def _postic_reference(mask: Mapping[str, Tuple[int, int]], err: Mapping[str, Tuple[float, float]],
                      finite: int = 100) -> Dict[str, Any]:
    stats = {}
    for core in POSTIC_CORES:
        for path, inp in POSTIC_PATHS:
            s = 0 if inp == "a" else 1
            stats[_postic_unit_id(core, path, inp)] = {"nan_mask_diff": mask[core][s], "common_finite_cells": finite,
                                                      "max_abs": err[core][s]}
    return {"status": "complete", "stats": stats}


def _postic_cases() -> List[Tuple[str, Dict[str, Any], Tuple[str, str]]]:
    """(名稱, 收據, 期望)：規則①–③各分支與平手次序。"""
    cases: List[Tuple[str, Dict[str, Any], Tuple[str, str]]] = []
    r = _postic_synthetic()
    _postic_unit(r, "pandas_optimized__chunked__b")["wall_seconds"] = 9.0
    cases.append(("rule2_wall", r, ("choice", "pandas_legacy")))
    r = _postic_synthetic()
    _postic_unit(r, "pandas_optimized__chunked__b")["peak_rss_bytes"] = 2000
    cases.append(("rule2_rss", r, ("choice", "pandas_legacy")))
    cases.append(("rule2_name", _postic_synthetic(), ("choice", "pandas_optimized")))
    r = _postic_synthetic()
    _postic_unit(r, "pandas_legacy__chunked__b").update(status="failed", watch_status="stalled", returncode=None,
                                                        wall_seconds=None, peak_rss_bytes=None)
    r["pairs"] = [p for p in r["pairs"] if p["input"] != "b"]
    cases.append(("rule1_failed", r, ("no_choice", "1")))
    r = _postic_synthetic()
    _postic_unit(r, "pandas_optimized__direct__a")["core_observed"] = ["legacy"]
    cases.append(("rule1_core_mismatch", r, ("no_choice", "1")))
    r = _postic_synthetic()
    _postic_unequal(r, ("chunked", "a"))
    next(p for p in r["pairs"] if (p["path"], p["input"]) == ("chunked", "a")).update(
        structure_equal=False, dtype_mismatch_columns=1,
        diff_columns={"column": ["c0"], "dtype_x": ["float64"], "dtype_y": ["float32"], "nan_mask_diff": [0],
                      "value_neq_cells": [3], "max_abs": [1e-7]})
    cases.append(("rule3_structure", r, ("no_choice", "3_structure")))
    r = _postic_synthetic()
    _postic_unequal(r, ("chunked", "b"))
    cases.append(("rule3_reference_missing", r, ("no_choice", "3_reference_missing")))
    for name, mask, err, expected in (
            ("rule3_mask_single", {"pandas_optimized": (0, 2), "pandas_legacy": (0, 0)}, None, ("choice", "pandas_legacy")),
            ("rule3_mask_none", {"pandas_optimized": (1, 0), "pandas_legacy": (0, 1)}, None, ("no_choice", "3_nan_mask")),
            ("rule3_err_both_less", None, {"pandas_optimized": (1e-7, 1e-7), "pandas_legacy": (2e-7, 2e-7)},
             ("choice", "pandas_optimized")),
            ("rule3_err_one_less_one_equal", None, {"pandas_optimized": (2e-7, 1e-7), "pandas_legacy": (2e-7, 3e-7)},
             ("choice", "pandas_optimized")),
            ("rule3_err_conflict", None, {"pandas_optimized": (1e-7, 3e-7), "pandas_legacy": (2e-7, 2e-7)},
             ("no_choice", "3_error_conflict")),
            ("rule3_err_tie", None, {"pandas_optimized": (1e-7, 1e-7), "pandas_legacy": (1e-7, 1e-7)},
             ("choice", "pandas_optimized"))):
        r = _postic_synthetic()
        _postic_unequal(r, ("chunked", "b"))
        r["reference"] = _postic_reference(mask or {"pandas_optimized": (0, 0), "pandas_legacy": (0, 0)},
                                           err or {"pandas_optimized": (0.0, 0.0), "pandas_legacy": (0.0, 0.0)})
        cases.append((name, r, expected))
    r = _postic_synthetic()
    _postic_unequal(r, ("chunked", "b"))
    r["reference"] = _postic_reference({"pandas_optimized": (0, 0), "pandas_legacy": (0, 0)},
                                       {"pandas_optimized": (0.0, 0.0), "pandas_legacy": (0.0, 0.0)}, finite=0)
    cases.append(("rule3_no_common_finite", r, ("no_choice", "3_no_common_finite")))
    return cases


@pytest.mark.parametrize("name", [c[0] for c in _postic_cases()])
def test_postic_core_selection_rule_cases(name: str) -> None:
    """擇一規則各分支（SPEC Task 1.6 ①–③、平手次序）：獨立重算與探針 `select_core` 皆等於期望。"""
    _, receipt, expected = next(c for c in _postic_cases() if c[0] == name)
    assert expected_postic_selection(receipt) == expected
    got = probe("postic_core_select").select_core(receipt["units"], receipt["pairs"],
                                                  (receipt.get("reference") or {}).get("stats"))
    assert (("choice", got["choice"]) if "choice" in got else ("no_choice", got["no_choice"]["rule"])) == expected, got


def _postic_mutants() -> Dict[str, Callable[[Dict[str, Any]], None]]:
    def drop_pair(r: Dict[str, Any]) -> None:
        r["pairs"] = r["pairs"][1:]

    def stalled_complete(r: Dict[str, Any]) -> None:
        r["units"][0]["watch_status"] = "stalled"

    def chosen_blocked(r: Dict[str, Any]) -> None:
        chosen = r.get("choice") or POSTIC_CORES[0]
        _postic_unit(r, _postic_unit_id(chosen, "direct", "a")).update(status="blocked", reason="mutant")

    def drop_b_unit(r: Dict[str, Any]) -> None:
        r["units"] = [u for u in r["units"] if u["unit_id"] != _postic_unit_id(POSTIC_CORES[0], "chunked", "b")]

    def tamper_count(r: Dict[str, Any]) -> None:
        r["pairs"][0]["columns_unequal_native"] = int(r["pairs"][0]["columns_unequal_native"]) + 1

    def wrong_arm(r: Dict[str, Any]) -> None:
        r["units"][0]["arm_recorded"] = ["pandas_legacy"]

    def check_false(r: Dict[str, Any]) -> None:
        r["checks"][sorted(r["checks"])[0]] = False

    def check_key_dropped_input_tampered(r: Dict[str, Any]) -> None:
        r["checks"].pop("inputs_identical_a", None)
        next(u for u in r["units"] if u["input"] == "a")["input_sha256"] = "numview-mutant"

    def input_tampered(r: Dict[str, Any]) -> None:
        next(u for u in r["units"] if u["input"] == "b" and u["status"] == "complete")["input_sha256"] = "numview-mutant"

    def config_check_dropped(r: Dict[str, Any]) -> None:
        r["checks"].pop("post_ic_config_same", None)

    def ic_stalled_complete(r: Dict[str, Any]) -> None:
        r["ic_recompute"]["watch_status"] = "stalled"

    def dup_pair(r: Dict[str, Any]) -> None:
        r["pairs"].append(copy.deepcopy(r["pairs"][0]))

    def pair_max_abs_tampered(r: Dict[str, Any]) -> None:
        r["pairs"][0]["max_abs"] = float(r["pairs"][0]["max_abs"]) + 1.0

    def blocked_with_watch(r: Dict[str, Any]) -> None:
        u = next(x for x in r["units"] if x["input"] == "b")
        u.update(status="blocked", reason="numview-mutant", watch_status="stalled", returncode=1)

    def blocked_with_measurement(r: Dict[str, Any]) -> None:
        u = next(x for x in r["units"] if x["input"] == "b")
        keep = {k: u[k] for k in POSTIC_BLOCKED_FIELDS if k in u}
        u.clear()
        u.update(keep, status="blocked", reason="numview-mutant", load_seconds=1.0)

    def ic_returncode_missing(r: Dict[str, Any]) -> None:
        r["ic_recompute"].pop("returncode", None)

    def ic_wall_mismatch(r: Dict[str, Any]) -> None:
        r["ic_recompute"]["wall_seconds"] = float(r["ic_recompute"]["child_wall_seconds"]) + 1.0

    def structure_flag_contradicts(r: Dict[str, Any]) -> None:
        r["pairs"][0]["structure_equal"] = not r["pairs"][0]["structure_equal"]

    def only_side_columns_with_equal_flag(r: Dict[str, Any]) -> None:
        r["pairs"][0].update(columns_equal=True, only_x=["numview_mutant"])

    def ic_summary_dropped(r: Dict[str, Any]) -> None:
        r["ic_recompute"].pop("a", None)
        r["ic_recompute"].pop("b", None)

    def choice_rule_wrong(r: Dict[str, Any]) -> None:
        if "choice" in r:
            r["choice_rule"] = "3_error"
        else:
            r["no_choice"] = dict(r["no_choice"], rule="3_error_conflict")

    def unit_identity_tampered(r: Dict[str, Any]) -> None:
        r["units"][0]["cell"] = "numview_mutant_cell"

    def reference_spurious(r: Dict[str, Any]) -> None:
        r["reference"] = {"status": "complete", "stats": {}}

    def failed_unit_with_measurement(r: Dict[str, Any]) -> None:
        u = next(x for x in r["units"] if x["input"] == "b")
        u.update(status="failed", watch_status="stalled", returncode=None, reason="numview-mutant")

    def failed_ic_with_rss(r: Dict[str, Any]) -> None:
        r["ic_recompute"].update(status="failed", watch_status="stalled", returncode=None, reason="numview-mutant",
                                 peak_rss_bytes=1)

    def ic_failed_choice_kept(r: Dict[str, Any]) -> None:
        r["ic_recompute"].update(status="failed", watch_status="stalled", returncode=None)
        r["choice"] = r.get("choice") or POSTIC_CORES[0]
        r.pop("no_choice", None)

    return {"drop_pair": drop_pair, "stalled_complete": stalled_complete, "chosen_blocked": chosen_blocked,
            "drop_b_unit": drop_b_unit, "tamper_count": tamper_count, "wrong_arm": wrong_arm,
            "check_false": check_false, "check_key_dropped_input_tampered": check_key_dropped_input_tampered,
            "input_tampered": input_tampered, "config_check_dropped": config_check_dropped,
            "ic_stalled_complete": ic_stalled_complete, "ic_failed_choice_kept": ic_failed_choice_kept,
            "dup_pair": dup_pair, "pair_max_abs_tampered": pair_max_abs_tampered, "blocked_with_watch": blocked_with_watch,
            "blocked_with_measurement": blocked_with_measurement, "ic_returncode_missing": ic_returncode_missing,
            "ic_wall_mismatch": ic_wall_mismatch, "failed_unit_with_measurement": failed_unit_with_measurement,
            "failed_ic_with_rss": failed_ic_with_rss, "structure_flag_contradicts": structure_flag_contradicts,
            "only_side_columns_with_equal_flag": only_side_columns_with_equal_flag,
            "ic_summary_dropped": ic_summary_dropped, "choice_rule_wrong": choice_rule_wrong,
            "unit_identity_tampered": unit_identity_tampered, "reference_spurious": reference_spurious}


@pytest.mark.parametrize("mutant", sorted(_postic_mutants()))
def test_postic_core_receipt_mutations(mutant: str) -> None:
    """mutation（SPEC Task 1.6）：刪成對比對列、complete 單元標 stalled、擇定核心單元改 blocked、刪 (b) 單元、竄改不等欄數、
    實際臂紀錄改錯、收據任一自我檢查改 False ⇒ 紅。
    對象＝合成全 complete 收據（擇定 `pandas_optimized`）與正式收據之複本。"""
    base = _postic_synthetic(choice="pandas_optimized", choice_rule="2")
    assert postic_core_violations(base) == []
    receipts = [base]
    hits = sorted(nh.RECEIPTS_DIR.glob(f"*-numview-{POSTIC_CORE_KIND}.json"))
    if len(hits) == 1:
        receipts.append(json.loads(hits[0].read_text(encoding="utf-8")))
    for receipt in receipts:
        mutated = copy.deepcopy(receipt)
        _postic_mutants()[mutant](mutated)
        assert postic_core_violations(mutated), f"mutant {mutant} 存活"


def test_postic_core_decision_mutation_loser_core_turns_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：決定紀錄 `report.post_ic_core` 改為落選核心（或 no_choice 時改為任一核心）⇒ 綁定檢查紅。"""
    receipt = _postic_synthetic(choice="pandas_optimized", choice_rule="2")
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(receipt))
    monkeypatch.setattr(nh, "_decision_record", lambda key: {"choice": "lock", "report": {"post_ic_core": "pandas_legacy"}})
    with pytest.raises(AssertionError):
        test_postic_core_decision_matches_receipt()


def test_postic_core_decision_user_ruling_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """v41（SPEC Task 1.5 ⑧）：收據 no_choice 而無使用者裁定卻記核心名 ⇒ 紅；有裁定而核心名不屬兩核心 ⇒ 紅；收據已擇一而
    具裁定 ⇒ 紅；合法之使用者裁定分支（no_choice＋`core_user_ruling`＋legacy）⇒ 綠。"""
    receipt = _postic_synthetic(choice="pandas_optimized", choice_rule="2")
    no_choice = _postic_synthetic(no_choice={"rule": "3_structure", "reason": "r"})
    ruling = {"date": "2026-10-24", "quote": "legacy", "core": "pandas_legacy", "output_dtype": "float32",
              "output_dtype_quote": "legacy＋一律 float32"}
    good = {"post_ic_core": "pandas_legacy", "no_choice_reason": "r", "core_user_ruling": ruling,
            "post_ic_output_dtype": "float32"}
    bad_cases = (
        ({"post_ic_core": "pandas_legacy", "no_choice_reason": "r"}, no_choice),  # 無裁定卻記核心名
        (dict(good, post_ic_core="pandas_optimized"), no_choice),  # 報告核心與裁定不符
        (dict(good, core_user_ruling=dict(ruling, core="pandas_optimized"), post_ic_core="pandas_optimized"),
         no_choice),  # 裁定核心與原話不符
        ({k: v for k, v in good.items() if k != "post_ic_output_dtype"}, no_choice),  # 漏記輸出 dtype
        (dict(good, core_user_ruling=dict(ruling, output_dtype="float64")), no_choice),  # 輸出 dtype 裁定被改
        (dict(good, post_ic_core="pandas_optimized"), receipt),  # 收據已擇一而另裁
    )
    for rec, rcp in bad_cases:
        monkeypatch.setattr(THIS, "load_receipt", lambda kind, r=rcp: copy.deepcopy(r))
        monkeypatch.setattr(nh, "_decision_record", lambda key, rr=rec: {"choice": "lock", "report": rr})
        with pytest.raises(AssertionError):
            test_postic_core_decision_matches_receipt()
    monkeypatch.setattr(THIS, "load_receipt", lambda kind: copy.deepcopy(no_choice))
    monkeypatch.setattr(nh, "_decision_record", lambda key: {"choice": "lock", "report": copy.deepcopy(good)})
    test_postic_core_decision_matches_receipt()  # 合法之使用者裁定分支須綠


def test_boundary_59_postic_core_memory_failure_is_no_choice() -> None:
    """邊界①（SPEC Task 1.6）：(b) 規模任一核心因記憶體不可完成（子行程失敗）⇒ 擇一規則①之 `no_choice`；正式收據若有
    (b) 單元非 complete ⇒ 收據無 `choice`。"""
    r = _postic_synthetic()
    _postic_unit(r, "pandas_optimized__chunked__b").update({k: None for k in POSTIC_CHILD_REPORTED_FIELDS},
                                                           status="failed", watch_status="exited", returncode=-9,
                                                           reason="exited（MemoryError；rc=-9）")
    r["pairs"] = [p for p in r["pairs"] if p["input"] != "b"]
    assert expected_postic_selection(r) == ("no_choice", "1")
    got = probe("postic_core_select").select_core(r["units"], r["pairs"], None)
    assert got.get("no_choice", {}).get("rule") == "1", got
    r["no_choice"] = got["no_choice"]
    assert postic_core_violations(r) == []
    hits = sorted(nh.RECEIPTS_DIR.glob(f"*-numview-{POSTIC_CORE_KIND}.json"))
    if len(hits) == 1:
        formal = json.loads(hits[0].read_text(encoding="utf-8"))
        if any(u["input"] == "b" and u["status"] != "complete" for u in formal["units"]):
            assert "choice" not in formal and formal["no_choice"]["rule"] == "1"


def test_boundary_60_postic_core_ratio_unsafe_dropped_counted() -> None:
    """邊界②（SPEC Task 1.6）：選欄含 ratio-unsafe 欄 ⇒ 入口既有剔除（兩核心同），剔除數入紀錄。真實 C_BTCUSDT_1h 凍結 run
    之 raw：取 20 個安全欄＋3 個 ratio-unsafe 欄，兩核心經探針 `transform_unit`（生產 `transform_selected`）各轉一次，剔除數
    等於獨立計數、輸出不含之且兩核心相同；正式收據同輸入之兩核心剔除數相等，(a) 等於凍結選欄之獨立計數。"""
    pcs = probe("postic_core_select")
    criteria = load_criteria()
    work = pcs.FREEZE_RUNS / f"{pcs.CELLS['b']}__default"
    side = json.loads((work / "numview_cell.json").read_text(encoding="utf-8"))
    manifest = json.loads(next((work / "features" / side["symbol"] / side["primary_tf"]).glob("*/feature_manifest.json"))
                          .read_text(encoding="utf-8"))
    names = [str(c) for g in manifest["groups"].values() for c in g.get("columns") or []]
    unsafe = [c for c in names if ratio_unsafe_category(c) is not None][:3]
    safe = [c for c in names if ratio_unsafe_category(c) is None][:20]
    assert len(unsafe) == 3 and len(safe) == 20, "C 之 raw 無足量 ratio-unsafe／安全欄"
    ctx = pcs.production_context(pcs.CELLS["b"], criteria)
    from momentum.FeatureEngineering import memory_budget as mb

    # 系統記憶體讀數（`sysctl vm.swapusage`）於部分沙箱不可用 ⇒ 以既有測試接縫注入固定快照（同
    # test_icfirstalign_memory.py:_snapshot）；只隔離環境，剔除與轉換路徑不變
    snapshot = mb.VMSnapshot(free_bytes=8 * 2 ** 30, file_backed_bytes=0, swap_free_bytes=0, pressure_level=1,
                             swap_volume_free_bytes=75 * 2 ** 30, swap_volume_capacity_bytes=228 * 2 ** 30)
    # NUMVIEW Task 3.4 後 `transform_selected` 只收擇定核心（必填 `arm`、不依環境）；Task 1.6 探針（sha 綁收據、不改）依環境
    # 選核心而不傳 arm ⇒ 以測試端轉接把探針所設之 profile 對應之核心作為 arm 傳入（只放行該核心），兩核心之入口剔除路徑不變
    import os

    from momentum.FeatureEngineering import numeric_view as nv
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    real_ts = FeaturePreprocessor.transform_selected

    def env_core_arm(self: Any, selected: Any, groups: Any, config: Any = None, **kwargs: Any) -> Any:
        profile = os.environ.get("FFACT_L65_OPTIMIZATION_PROFILE", "optimized")
        return real_ts(self, selected, groups, config, arm="pandas_legacy" if profile == "legacy" else "pandas_optimized")

    infos = {}
    for core in ("optimized", "legacy"):
        with mb.vm_snapshot_override(snapshot), pytest.MonkeyPatch.context() as mp:
            mp.setattr(FeaturePreprocessor, "transform_selected", env_core_arm)
            mp.setattr(nv, "require_post_ic_core", lambda arm: arm)
            mp.setattr(nv, "post_ic_output_float32", lambda frame: frame)  # 探針量原生輸出（optimized 臂原生含 float64）
            processed, info = pcs.transform_unit(ctx, work / "features", side["config_hash"], safe + unsafe, core,
                                                 "direct")
        out = processed["selected"]
        assert info["ratio_unsafe_dropped"] == 3 and not set(unsafe) & {str(c) for c in out.columns}
        assert [str(c) for c in out.columns] == safe
        infos[core] = info
    assert infos["optimized"]["ratio_unsafe_dropped"] == infos["legacy"]["ratio_unsafe_dropped"]
    hits = sorted(nh.RECEIPTS_DIR.glob(f"*-numview-{POSTIC_CORE_KIND}.json"))
    if len(hits) == 1:
        formal = json.loads(hits[0].read_text(encoding="utf-8"))
        frozen_a = json.loads((pcs.FREEZE_RUNS / f"{pcs.CELLS['a']}__default" / "numview_cell.json")
                              .read_text(encoding="utf-8"))["ic_first_selected"]
        independent_a = sum(1 for c in frozen_a if ratio_unsafe_category(str(c)) is not None)
        for inp in ("a", "b"):
            counts = {u["ratio_unsafe_dropped"] for u in formal["units"] if u["input"] == inp and u["status"] == "complete"}
            assert len(counts) <= 1, (inp, counts)
            if inp == "a" and counts:
                assert counts == {independent_a}, (counts, independent_a)
