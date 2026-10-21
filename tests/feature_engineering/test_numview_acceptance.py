"""NUMVIEW 驗收（docs/NUMVIEW_SPEC.md）：Phase 1 量測收據（Task 1.1、1.2、1.3）、§G 通過條件（Phase 0／2／4 值指紋逐位元）、
Task 4.2 ⑤ 結構重凍收據、Task 5.1 文件與 fact-key 更正。

驗證：
- Task 1.1（`handoffs/run_receipts/*-numview-postic-branchdiff.json`）：`exit_code`＝0、`criteria_sha256`＝現行判準檔 sha256；
  列數＝格數×分支數×7（分支＝`tests/_golden/icpostleak/contract.json` 之 `branches` ∪ 候選臂 `postic_branchdiff.CANDIDATE_ARM`；
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
TICKET_ORDER_LINE = 36
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
    return _json(nh.CRITERIA_PATH)


def load_contract() -> Dict[str, Any]:
    return nv.load_contract()


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def criteria_sha256() -> str:
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
    """格 A＝每個 symbol×tf；格 B＝每個具 ≥2 週期之 symbol（週期依長度升冪）；格 C＝每個 symbol×tf。"""
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


def expected_branches() -> List[str]:
    return sorted(set(icpostleak_contract()["branches"]) | {probe("postic_branchdiff").CANDIDATE_ARM})


def combo_names() -> List[str]:
    combos = ["+".join(c) for c in icpostleak_contract()["combos"]]
    assert len(combos) == 7 == len(set(combos)), combos
    return combos


def _entry_key(entry: Mapping[str, Any]) -> Tuple[str, str]:
    return (str(entry["cell_id"]), str(entry["input"]))


def branchdiff_rows_violations() -> List[str]:
    """列數＝格數×分支數×7、每 (格, 輸入, 分支, 組合) 恰一列；格涵蓋：輸入 (i)＝每個 symbol×tf、輸入 (ii)＝凍結檔全部格。"""
    receipt = load_receipt("postic-branchdiff")
    branches, combos = expected_branches(), combo_names()
    out: List[str] = []
    if sorted(receipt.get("branches") or []) != branches:
        out.append(f"branches {sorted(receipt.get('branches') or [])} ≠ {branches}")
    cells = receipt["cells"]
    keys = [_entry_key(c) for c in cells]
    if len(keys) != len(set(keys)) or not keys:
        out.append("cells 重複或為空")
    inv_i = {(str(c["symbol"]), tuple(c["timeframes"])) for c in cells if c["input"] == "i"}
    want_i = {(s, (tf,)) for s, tfs in kline_inventory().items() for tf in tfs}
    if inv_i != want_i:
        out.append(f"輸入 (i) 涵蓋 ≠ 每個 symbol×tf：缺 {sorted(want_i - inv_i)[:5]}")
    inv_ii = {cell_key(c) for c in cells if c["input"] == "ii"}
    want_ii = {cell_key(r) for r in load_freeze()["cells"].values()}
    if inv_ii != want_ii:
        out.append(f"輸入 (ii) 涵蓋 ≠ 凍結格：缺 {sorted(want_ii - inv_ii)[:5]} 多 {sorted(inv_ii - want_ii)[:5]}")
    rows = receipt["rows"]
    row_keys = [(str(r["cell_id"]), str(r["input"]), str(r["branch"]), str(r["combo"])) for r in rows]
    want_rows = {(c, i, b, k) for (c, i) in set(keys) for b in branches for k in combos}
    if len(rows) != len(set(keys)) * len(branches) * len(combos):
        out.append(f"列數 {len(rows)} ≠ 格數 {len(set(keys))} × 分支數 {len(branches)} × {len(combos)}")
    if set(row_keys) != want_rows or len(row_keys) != len(set(row_keys)):
        out.append("列之 (格, 輸入, 分支, 組合) 非恰一")
    return out


def speed_violations() -> List[str]:
    """每格每可達臂（契約可達條件＋候選臂）具三次牆鐘秒數與其中位數。"""
    receipt = load_receipt("postic-branchdiff")
    contract = load_contract()
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
    """Task 1.1 驗證：每格每臂每組合一列（列數＝格數×分支數×7）。"""
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
    """段 × 格完整：格涵蓋＝格 A∪B∪C 列舉；measured 格之 S0–S4 逐欄列之欄集合＝該格欄、S5 ≥1 列；blocked 格每段 ≥1 列。"""
    receipt = load_receipt("precision-chain")
    out: List[str] = []
    cells = {cell_key(c): c for c in receipt["cells"]}
    want = enumerate_keys(("A", "B", "C"))
    if set(cells) != want:
        out.append(f"格涵蓋 ≠ A∪B∪C：缺 {sorted(want - set(cells))[:5]} 多 {sorted(set(cells) - want)[:5]}")
    rows: Dict[Tuple[str, str], List[Mapping[str, Any]]] = {}
    for row in receipt["rows"]:
        rows.setdefault((str(row["segment"]), str(row["cell_id"])), []).append(row)
    for cell in cells.values():
        cid = str(cell["cell_id"])
        for seg in SEGMENTS:
            got = rows.get((seg, cid), [])
            if not got:
                out.append(f"{cid}/{seg}: 無列")
                continue
            if cell["status"] == "measured" and seg in PER_COLUMN_SEGMENTS:
                names = [str(r["column"]) for r in got]
                if not cell["columns"] or sorted(names) != sorted(str(c) for c in cell["columns"]):
                    out.append(f"{cid}/{seg}: 逐欄列之欄集合 ≠ 該格欄")
    return out


def test_precision_chain_receipt_rc_and_criteria() -> None:
    """Task 1.2 驗證：收據 rc=0、`criteria_sha256` 相符。"""
    assert _receipt_common_violations(load_receipt("precision-chain")) == []


def test_precision_chain_segments_cells_complete() -> None:
    """Task 1.2 驗證：每段每格逐欄統計列存在（段×格完整）。"""
    assert precision_completeness_violations() == []


def test_precision_chain_s4_raw_bss_lossless_flag() -> None:
    """Task 1.2 驗證：S4 raw BYTE_STREAM_SPLIT 讀回逐位元相等之檢查於每個 measured 格皆有紀錄；任一不等 ⇔
    `lossless_violation` 為 True。"""
    receipt = load_receipt("precision-chain")
    entries = {str(e["cell_id"]): bool(e["bitwise_equal"]) for e in receipt["s4_raw_bss"]}
    measured = {str(c["cell_id"]) for c in receipt["cells"] if c["status"] == "measured"}
    assert measured and measured <= set(entries), sorted(measured - set(entries))[:5]
    assert receipt["lossless_violation"] is (not all(entries.values()))


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
    """Task 1.3 驗證：格數＝格 A＋格 B 全部（列舉自 kline_cache.h5）。"""
    cells = [cell_key(c) for c in load_receipt("l2-arm-matrix")["cells"]]
    assert len(cells) == len(set(cells))
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
            self._cache[cell_id] = freeze_script().freeze_cell(record, self.root / re.sub(r"[^A-Za-z0-9_.-]", "_", cell_id),
                                                               arms=arms, run_kind="regen_section_g")
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
    missing = contract_new_keys() - {str(k) for k in receipt["stripped_keys"]}
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
    line = read_text(TICKET_ORDER_PATH).splitlines()[TICKET_ORDER_LINE - 1]
    assert line.startswith("| 4 |"), line[:40]
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
