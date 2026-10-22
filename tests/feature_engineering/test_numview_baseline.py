"""NUMVIEW Task 0.5（docs/NUMVIEW_SPEC.md §G 新凍結 G1–G3、Task 0.5 驗證①②③、邊界①–④、R2-B／R3-D）：改前基準凍結檔與收據之驗收。

讀：凍結檔 `tests/_golden/numview/pre_change_fingerprints.json`（`numview_helpers.PRE_CHANGE_FINGERPRINTS_PATH`）、凍結收據
`handoffs/run_receipts/*-numview-freeze-baseline.json`（恰一份）、估時收據（`_estimate_gate.ESTIMATE_RECEIPT_GLOB`，恰一份）、
事前登記判準 `tests/_golden/numview/preregistered_criteria.json`、契約 `numeric_view.load_contract()`、真實 kline
`data_cache/feature_klines/kline_cache.h5`（h5py 唯讀列舉 symbol×tf，獨立於凍結腳本）。不生成特徵（秒級）。

驗證：
① 每個格 A 之 G1 臂份集合＝依契約 `post_ic_arm_reachability` 以該格實際選欄數（測試內自 `ic_first_selected` 經 IC 頁同一
   ratio-unsafe 剔除重算，不讀收據結論）判為可達之臂；每份記錄之實際臂＝標示臂、環境設定合 SPEC §G；份之欄序指紋＝
   剔除後選欄之欄序；不可達臂於收據具 `arm_unreachable`（臂名＋契約條件名＋實際選欄數）且凍結檔無該份；G2 兩份
   （`FFACT_USE_POLARS` 0／1）；格 B 之 G3 raw 與 processed。
② 格清單＝判準檔列舉規則套用於 kline_cache.h5 之結果（不得缺格；blocked 格附根數與理由）。
③ 凍結收據 `started_at` 晚於估時收據 `reported_at`。
邊界：09 前史不足 ⇒ 依判準標 blocked、記根數、不降門檻；10 記憶體守護終止 ⇒ blocked-by 硬體並列入 RM-FULLSCALE、不得以縮小
設定冒充同格；11 選欄數 ≤ 1 ⇒ `pandas_chunked` 不可達、只凍其餘臂份並記 `arm_unreachable`；12 選欄數 0 ⇒ G1 全臂
`arm_unreachable`、G2／G3 照凍。邊界皆對全部格逐格驗規則（若真實列舉無格觸發，仍對每格驗「若…則…」並直接呼叫凍結腳本之
可達性函式於觸發值），不空轉。
mutation（SPEC Task 0.5 原列）：凍結檔刪一格 ⇒ ②紅；`started_at` 早於 `reported_at` ⇒ ③紅；刪估時收據後執行凍結腳本 ⇒
拋 `EstimateGateError`（行程 rc≠0）且任何生成入口零呼叫；單欄格以 `pandas_optimized` 份複寫為 `pandas_chunked` 份 ⇒ ①紅；
可達格漏凍 `pandas_chunked` 份而標 `arm_unreachable` ⇒ ①紅。mutation 一律對載入之複本（monkeypatch 本模組讀取函式），不寫凍結檔。

測試接縫（實作須提供；名稱即契約）：
- 契約 `post_ic_arm_reachability.<臂>.min_selected_columns`（int；選欄數 ≥ 之即可達；SPEC R3-D／邊界④導出：`pandas_chunked`＝2、
  其餘＝1）。
- `scripts/numview_freeze_baseline.py`：模組屬性 `RECEIPTS_DIR`（呼叫時讀，作 `_estimate_gate.require(..., receipts_dir=)`）；
  `main(argv)` 於估時前置不成立時讓 `EstimateGateError` 外拋（行程 rc≠0）；`reachable_arms(selected_count: int) -> List[str]`（讀契約）。
- 判準檔 `cell_definitions.{A,B}.{min_history_bars:int, output_bars:int, config_override:object}`；列舉規則：格 A＝每個
  symbol×tf；格 B＝每個具 ≥2 週期之 symbol，`timeframes`＝依週期長度升冪（首項＝最細＝主週期）；任一所涉週期根數
  < `min_history_bars` ⇒ blocked（history）。
- 凍結檔（全票唯一正規形；policy／IC 頁測試經各自 `_cell_view` 讀同一形）：`head`、`cells.<cell_id>.{kind, symbol,
  timeframes, config_override, output_bars, ic_first_selected(格 A), g1_source_env(格 A；G1 來源 run 之生成環境),
  g1.<臂>.{env, actual_arm, fingerprint}, g2.{"0","1"}.{env, fingerprint}, g3.{raw, processed}(格 B)}`。
- 凍結收據：`head, started_at, exit_code, criteria_sha256, library_versions, cells[].{cell_id, kind, symbol, timeframes,
  status(frozen|blocked), blocked_by(history|hardware|null), reason, bar_counts{tf:int}, seconds, peak_rss_bytes},
  arm_unreachable[].{cell_id, arm, condition, selected_count}, residuals[].{cell_id, fact_key}`。
- 估時收據：`reported_at`。
實作前應為紅（凍結檔／收據不存在、契約未填、腳本為 NotImplementedError）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pandas as pd
import pytest

from momentum.FeatureEngineering import numeric_view as nv
from momentum.factories import ratio_unsafe_category
from tests.feature_engineering import numview_helpers as nh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

REPO = nh.REPO
GATE_PATH = REPO / "handoffs" / "run_receipts" / "numview_probes" / "_estimate_gate.py"
FREEZE_SCRIPT_PATH = REPO / "scripts" / "numview_freeze_baseline.py"
FACT_KEYS_PATH = REPO / "scripts" / "fact_keys.json"
FREEZE_RECEIPT_GLOB = "*-numview-freeze-baseline.json"

#: SPEC §G G1 以字面點名之 IC 頁臂（使用前斷言屬契約 `post_ic_arm_values`）
SPEC_ARM_POLARS = "polars"
SPEC_ARM_OPTIMIZED = "pandas_optimized"
SPEC_ARM_LEGACY = "pandas_legacy"
SPEC_ARM_CHUNKED = "pandas_chunked"
#: SPEC §G G1／G2 以字面點名之環境鍵
ENV_USE_POLARS = "FFACT_USE_POLARS"
ENV_PROFILE = "FFACT_L65_OPTIMIZATION_PROFILE"
ENV_CHUNK = "FFACT_L65_CHUNK_SIZE"
#: RM-FULLSCALE 之 fact-key 識別碼（SPEC §N NUMVIEW-R3 登記處）
FULLSCALE_KEY = "RM-FULLSCALE"

THIS = sys.modules[__name__]
CellKey = Tuple[str, str, Tuple[str, ...]]


# ---------------------------------------------------------------------------------------------- 讀取（mutation 以 monkeypatch 替換）

def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"無法載入 {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _gate() -> ModuleType:
    return _load_module("numview_estimate_gate_under_test", GATE_PATH)


def _freeze_script() -> ModuleType:
    return _load_module("numview_freeze_baseline_under_test", FREEZE_SCRIPT_PATH)


def _single(glob: str) -> Path:
    hits = sorted(nh.RECEIPTS_DIR.glob(glob))
    assert len(hits) == 1, f"{glob} 須恰一份，實得 {[p.name for p in hits]}"
    return hits[0]


def load_freeze() -> Dict[str, Any]:
    path = nh.PRE_CHANGE_FINGERPRINTS_PATH
    assert path.is_file(), f"凍結檔不存在：{path}（Task 0.5 未執行）"
    return json.loads(path.read_text(encoding="utf-8"))


def load_freeze_receipt() -> Dict[str, Any]:
    return json.loads(_single(FREEZE_RECEIPT_GLOB).read_text(encoding="utf-8"))


def load_estimate_receipt() -> Dict[str, Any]:
    return json.loads(_single(_gate().ESTIMATE_RECEIPT_GLOB).read_text(encoding="utf-8"))


def load_criteria() -> Dict[str, Any]:
    if nh.criteria_replaced():  # 判準檔已以 vN 取代（SPEC Task 0.3 邊界①：判準檔恰一存在） ⇒ 讀現行判準；v1 現行時沿原斷言
        return json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))
    assert nh.CRITERIA_PATH.is_file(), f"判準檔不存在：{nh.CRITERIA_PATH}（Task 0.3 未執行）"
    return json.loads(nh.CRITERIA_PATH.read_text(encoding="utf-8"))


def load_contract() -> Dict[str, Any]:
    return nv.load_contract()


def freeze_receipt_criteria_sha256() -> Any:
    """凍結收據所記 `criteria_sha256`（不含 assert：收據恰一份之檢查由 `load_freeze_receipt` 於呼叫端先行；本函式只取值，
    不被展開為呼叫端測試之斷言元素）。"""
    paths = sorted(nh.RECEIPTS_DIR.glob(FREEZE_RECEIPT_GLOB))
    if len(paths) != 1:
        raise RuntimeError(f"{FREEZE_RECEIPT_GLOB} 須恰一份，實得 {[p.name for p in paths]}")
    return json.loads(paths[0].read_text(encoding="utf-8")).get("criteria_sha256")


def run_history_blocked(record: Mapping[str, Any]) -> bool:
    """判準 v2 `cell_rules.insufficient_history` 之權威判定（測試端依現行判準重算，不讀收據結論）：收據該格所記
    `reason_counts` 非空、每項為正整數欄數且 `<事件>:<欄數>` 皆合 `reason_pattern`（生成之 run 只因前史不足而 partial）
    ⇒ True；判準無此規則（v1）⇒ False。不含 assert（不被展開為呼叫端測試之斷言元素）。"""
    rule = json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))["cell_rules"]["insufficient_history"]
    counts = record.get("reason_counts")
    if "reason_pattern" not in rule or not isinstance(counts, Mapping) or not counts:
        return False
    pattern = re.compile(str(rule["reason_pattern"]))
    return all(isinstance(n, int) and not isinstance(n, bool) and n > 0 and pattern.fullmatch(f"{event}:{n}") is not None
               for event, n in counts.items())


# ---------------------------------------------------------------------------------------------- 獨立列舉與重算

def kline_inventory() -> Dict[str, Dict[str, int]]:
    """真實 kline 之 {symbol: {tf: 根數}}（h5py 唯讀；不寫死 symbol／週期）。"""
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
    """週期字面之長度（秒；`pd.Timedelta` 解析，不假設 24h）；無法解析 ⇒ AssertionError。"""
    try:
        return float(pd.Timedelta(tf).total_seconds())
    except (ValueError, TypeError) as exc:
        raise AssertionError(f"無法解析週期 {tf!r}：{exc}") from exc


def _source_bar_count(source: Path, symbol: str, tf: str) -> int:
    """`<source>` 之 `<symbol>/<tf>/data` 根數（h5py 唯讀）；缺 ⇒ RuntimeError。不含 assert（不被 TESTREG 展開為呼叫端
    測試之斷言元素）。"""
    import h5py

    if not source.is_file():
        raise RuntimeError(f"K 線來源不存在：{source}")
    with h5py.File(source, "r") as handle:
        if symbol not in handle or tf not in handle[symbol] or "data" not in handle[symbol][tf]:
            raise RuntimeError(f"{source} 缺 {symbol}/{tf}/data")
        return int(handle[symbol][tf]["data"].shape[0])


def closed_enumeration(criteria: Mapping[str, Any]) -> Dict[CellKey, Dict[str, Any]]:
    """判準 v3 起之封閉路徑覆蓋清單（`cell_rules.cell_list.cells`，取代「全部 symbol×tf／每個 symbol」列舉；測試端獨立
    實作）：{(kind, symbol, timeframes): {bar_counts, blocked, threshold}}。根數取自格之單一來源＝主週期（最細週期）依
    `cell_rules.kline_source.by_timeframe` 對映之檔（多週期格之訓練週期同讀該檔）；未列週期 ⇒ RuntimeError（拒收不猜）；
    `blocked`＝任一週期根數 < 格類 `min_history_bars`（前置篩；格類無門檻〔C〕⇒ False，前史不足由 run 完整度判定）。
    不含 assert。"""
    rules = criteria["cell_rules"]
    by_tf = rules["kline_source"]["by_timeframe"]
    defs = criteria["cell_definitions"]
    out: Dict[CellKey, Dict[str, Any]] = {}
    for cell in rules["cell_list"]["cells"]:
        kind, symbol = str(cell["kind"]), str(cell["symbol"])
        group = tuple(sorted((str(t) for t in cell["timeframes"]), key=tf_seconds))
        if not group or group[0] not in by_tf:
            raise RuntimeError(f"{cell.get('id')}: 主週期 {group[:1]} 不在 kline_source.by_timeframe")
        source = nh.REPO / str(by_tf[group[0]])
        counts = {tf: _source_bar_count(source, symbol, tf) for tf in group}
        threshold = defs[kind].get("min_history_bars")
        key = (kind, symbol, group)
        if key in out:
            raise RuntimeError(f"封閉清單格重複：{key}")
        out[key] = {"bar_counts": counts, "threshold": threshold,
                    "blocked": isinstance(threshold, int) and any(n < threshold for n in counts.values())}
    return out


def enumerate_cells(criteria: Mapping[str, Any]) -> Dict[CellKey, Dict[str, Any]]:
    """判準檔列舉規則（測試端獨立實作）：{(kind, symbol, timeframes): {bar_counts, blocked}}。判準 v3 起改為封閉路徑覆蓋
    清單（`closed_enumeration`）；舊版判準沿原列舉。"""
    if nh.criteria_cell_list() is not None:  # 判準 v3 起：封閉清單（SPEC Task 0.5 ②）
        return closed_enumeration(criteria)
    defs = criteria["cell_definitions"]
    inventory = kline_inventory()
    out: Dict[CellKey, Dict[str, Any]] = {}
    for kind in ("A", "B"):
        threshold = defs[kind]["min_history_bars"]
        assert isinstance(threshold, int) and threshold > 0, f"判準 {kind}.min_history_bars 非正整數：{threshold!r}"
        for symbol, tfs in inventory.items():
            if kind == "A":
                groups = [(tf,) for tf in tfs]
            else:
                groups = [tuple(sorted(tfs, key=tf_seconds))] if len(tfs) >= 2 else []
            for group in groups:
                counts = {tf: tfs[tf] for tf in group}
                out[(kind, symbol, group)] = {"bar_counts": counts,
                                              "blocked": any(n < threshold for n in counts.values()),
                                              "threshold": threshold}
    return out


def cell_key(record: Mapping[str, Any]) -> CellKey:
    return (str(record["kind"]), str(record["symbol"]), tuple(str(t) for t in record["timeframes"]))


def kept_columns(selected: Sequence[str]) -> List[str]:
    """IC 頁第三步之選欄（`ic_analysis_service._apply_transforms_sync` 同規則）：保序去重、ratio-unsafe 欄剔除。"""
    seen: List[str] = []
    for name in (str(c) for c in selected):
        if name not in seen:
            seen.append(name)
    return [c for c in seen if ratio_unsafe_category(c) is None]


def contract_arms(contract: Mapping[str, Any]) -> List[str]:
    arms = list(contract["post_ic_arm_values"]["values"])
    assert arms, "契約 post_ic_arm_values 為空（Task 0.1 未填）"
    return arms


def reachable_by_contract(contract: Mapping[str, Any], selected_count: int) -> List[str]:
    """依契約 `post_ic_arm_reachability.<臂>.min_selected_columns` 判可達（測試端重算，不讀收據結論）。"""
    reach = contract["post_ic_arm_reachability"]
    out: List[str] = []
    for arm in contract_arms(contract):
        entry = reach.get(arm)
        assert isinstance(entry, Mapping) and entry.get("condition"), f"契約缺臂 {arm} 之可達條件"
        minimum = entry.get("min_selected_columns")
        assert isinstance(minimum, int) and minimum >= 1, f"契約 {arm}.min_selected_columns 非正整數：{minimum!r}"
        if selected_count >= minimum:
            out.append(arm)
    return out


def _receipt_cells(receipt: Mapping[str, Any]) -> Dict[CellKey, Dict[str, Any]]:
    out: Dict[CellKey, Dict[str, Any]] = {}
    for record in receipt["cells"]:
        key = cell_key(record)
        assert key not in out, f"收據格重複：{key}"
        out[key] = dict(record)
    return out


def _freeze_cells(freeze: Mapping[str, Any]) -> Dict[CellKey, Tuple[str, Dict[str, Any]]]:
    out: Dict[CellKey, Tuple[str, Dict[str, Any]]] = {}
    for cell_id, record in freeze["cells"].items():
        key = cell_key(record)
        assert key not in out, f"凍結檔格重複：{key}"
        out[key] = (str(cell_id), dict(record))
    return out


def _unreachable_index(receipt: Mapping[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for entry in receipt.get("arm_unreachable") or []:
        key = (str(entry["cell_id"]), str(entry["arm"]))
        assert key not in out, f"arm_unreachable 重複：{key}"
        out[key] = dict(entry)
    return out


def _parse_time(value: Any) -> datetime:
    assert isinstance(value, str) and value, f"時間欄缺或非字串：{value!r}"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None, f"時間欄須含時區：{value!r}"
    return parsed


# ---------------------------------------------------------------------------------------------- 檢查（回違規清單）

def env_violations(arm: str, env: Mapping[str, Any], selected_count: int) -> List[str]:
    """SPEC §G G1 各臂份之環境設定。"""
    env = {str(k): str(v) for k, v in env.items()}
    out: List[str] = []
    if arm == SPEC_ARM_POLARS:
        if env.get(ENV_USE_POLARS) != "1":
            out.append(f"{arm}: {ENV_USE_POLARS} 須為 1")
        return out
    if arm in (SPEC_ARM_OPTIMIZED, SPEC_ARM_LEGACY, SPEC_ARM_CHUNKED) and env.get(ENV_USE_POLARS) != "0":
        out.append(f"{arm}: {ENV_USE_POLARS} 須為 0")
    if arm == SPEC_ARM_LEGACY and env.get(ENV_PROFILE) != "legacy":
        out.append(f"{arm}: {ENV_PROFILE} 須為 legacy")
    if arm == SPEC_ARM_OPTIMIZED and (env.get(ENV_PROFILE) == "legacy" or ENV_CHUNK in env):
        out.append(f"{arm}: 不得設 legacy profile 或 chunk 值")
    if arm == SPEC_ARM_CHUNKED:
        raw = env.get(ENV_CHUNK)
        if raw is None or not re.fullmatch(r"[0-9]+", raw) or not 1 <= int(raw) < selected_count:
            out.append(f"{arm}: {ENV_CHUNK}={raw!r} 須為小於選欄數 {selected_count} 之正整數")
    return out


def g1_violations() -> List[str]:
    """驗證①（見模組說明）。"""
    contract = load_contract()
    freeze = load_freeze()
    receipt = load_freeze_receipt()
    arms = contract_arms(contract)
    for named in (SPEC_ARM_POLARS, SPEC_ARM_OPTIMIZED, SPEC_ARM_LEGACY, SPEC_ARM_CHUNKED):
        assert named in arms, f"SPEC 點名之臂 {named} 不屬契約 post_ic_arm_values"
    unreachable = _unreachable_index(receipt)
    out: List[str] = []
    checked = 0
    expected_unreachable: set = set()
    for cell_id, record in freeze["cells"].items():
        kind = str(record["kind"])
        if kind == "B":
            g3 = record.get("g3") or {}
            for artifact in ("raw", "processed"):
                if not isinstance(g3.get(artifact), Mapping) or "columns" not in g3[artifact]:
                    out.append(f"{cell_id}: G3 缺 {artifact} 份")
            continue
        assert kind == "A", f"{cell_id}: 未知格類 {kind!r}"
        checked += 1
        kept = kept_columns(record["ic_first_selected"])
        n = len(kept)
        reachable = reachable_by_contract(contract, n)
        g1 = dict(record.get("g1") or {})
        if set(g1) != set(reachable):
            out.append(f"{cell_id}: G1 臂份 {sorted(g1)} ≠ 可達臂 {sorted(reachable)}（選欄數 {n}）")
        for arm in sorted(set(g1) - set(reachable)):
            out.append(f"{cell_id}: 不可達之臂 {arm} 有凍結份（選欄數 {n}）")
        for arm, copy_ in g1.items():
            if copy_.get("actual_arm") != arm:
                out.append(f"{cell_id}: 實際臂 {copy_.get('actual_arm')!r} ≠ 標示臂 {arm!r}")
            out.extend(f"{cell_id}: {v}" for v in env_violations(arm, copy_.get("env") or {}, n))
            fp = copy_.get("fingerprint") or {}
            if fp.get("column_order_sha256") != nh.column_order_sha256(kept):
                out.append(f"{cell_id}/{arm}: 份之欄序指紋 ≠ 剔除後選欄之欄序")
        for arm in arms:
            if arm in reachable:
                if (str(cell_id), arm) in unreachable:
                    out.append(f"{cell_id}: 可達臂 {arm} 被標 arm_unreachable")
                continue
            expected_unreachable.add((str(cell_id), arm))
            entry = unreachable.get((str(cell_id), arm))
            if entry is None:
                out.append(f"{cell_id}: 不可達臂 {arm} 缺 arm_unreachable 條目")
                continue
            condition = contract["post_ic_arm_reachability"][arm]["condition"]
            if entry.get("condition") != condition:
                out.append(f"{cell_id}/{arm}: arm_unreachable 條件名 {entry.get('condition')!r} ≠ 契約 {condition!r}")
            if entry.get("selected_count") != n:
                out.append(f"{cell_id}/{arm}: arm_unreachable 選欄數 {entry.get('selected_count')!r} ≠ 重算 {n}")
        g2 = dict(record.get("g2") or {})
        if set(g2) != {"0", "1"}:
            out.append(f"{cell_id}: G2 臂份 {sorted(g2)} ≠ FFACT_USE_POLARS 0／1")
        for value, copy_ in g2.items():
            if str((copy_.get("env") or {}).get(ENV_USE_POLARS)) != value or "columns" not in (copy_.get("fingerprint") or {}):
                out.append(f"{cell_id}: G2 份 {value} 環境或指紋不符")
    stray = set(unreachable) - expected_unreachable
    if stray:
        out.append(f"arm_unreachable 含非預期條目：{sorted(stray)[:5]}")
    if checked == 0:
        out.append("凍結檔無任何格 A ⇒ ① 空轉")
    return out


def cell_list_violations() -> List[str]:
    """驗證②：格清單＝判準列舉規則於 kline_cache.h5 之結果；blocked 格附根數與理由；凍結檔格＝收據 frozen 格。"""
    expected = enumerate_cells(load_criteria())
    receipt_cells = _receipt_cells(load_freeze_receipt())
    frozen = _freeze_cells(load_freeze())
    out: List[str] = []
    if set(receipt_cells) != set(expected):
        out.append(f"收據格清單 ≠ 列舉：缺 {sorted(set(expected) - set(receipt_cells))[:5]} 多 "
                   f"{sorted(set(receipt_cells) - set(expected))[:5]}")
    receipt_frozen = {k for k, r in receipt_cells.items() if r.get("status") == "frozen"}
    if set(frozen) != receipt_frozen:
        out.append(f"凍結檔格 ≠ 收據 frozen 格：缺 {sorted(receipt_frozen - set(frozen))[:5]} 多 "
                   f"{sorted(set(frozen) - receipt_frozen)[:5]}")
    for key, record in receipt_cells.items():
        status = record.get("status")
        if status not in ("frozen", "blocked"):
            out.append(f"{key}: status {status!r} 非 frozen／blocked")
        if status == "blocked":
            if not isinstance(record.get("bar_counts"), Mapping) or not record.get("reason"):
                out.append(f"{key}: blocked 格缺根數或理由")
            if key in frozen:
                out.append(f"{key}: blocked 格不得有凍結份")
        if key in frozen and frozen[key][0] != record.get("cell_id"):
            out.append(f"{key}: 凍結檔 cell_id {frozen[key][0]!r} ≠ 收據 {record.get('cell_id')!r}")
    if not expected:
        out.append("列舉為空 ⇒ ② 空轉")
    return out


def order_violations() -> List[str]:
    """驗證③：凍結收據 `started_at` 晚於估時收據 `reported_at`。"""
    started = _parse_time(load_freeze_receipt().get("started_at"))
    reported = _parse_time(load_estimate_receipt().get("reported_at"))
    return [] if started > reported else [f"started_at {started.isoformat()} 未晚於 reported_at {reported.isoformat()}"]


# ---------------------------------------------------------------------------------------------- 驗證

def test_contract_reachability_matches_spec_dispatch_rule() -> None:
    """契約可達條件與 SPEC 一致：`pandas_chunked` 需 `chunk_size > 0 and num_cols > chunk_size`（R3-D ⇒ 最小選欄數 2）；
    選欄數 0 ⇒ IC 頁既有錯誤（邊界④ ⇒ 其餘臂最小選欄數 1）。"""
    contract = load_contract()
    arms = contract_arms(contract)
    assert SPEC_ARM_CHUNKED in arms
    assert reachable_by_contract(contract, 0) == []
    assert SPEC_ARM_CHUNKED not in reachable_by_contract(contract, 1)
    assert sorted(reachable_by_contract(contract, 1)) == sorted(a for a in arms if a != SPEC_ARM_CHUNKED)
    assert sorted(reachable_by_contract(contract, 2)) == sorted(arms)


def test_freeze_script_reachability_equals_contract() -> None:
    """凍結腳本之逐格可達判定（`reachable_arms`）於選欄數 0、1、2 與契約重算一致（不得另寫平行判定）。"""
    contract = load_contract()
    freeze = _freeze_script()
    for n in (0, 1, 2):
        assert sorted(freeze.reachable_arms(n)) == sorted(reachable_by_contract(contract, n)), n


def test_g1_arm_copies_follow_contract_reachability() -> None:
    """驗證①（SPEC Task 0.5、§G G1／G2／G3、R3-D）。"""
    assert g1_violations() == []


def test_cell_list_equals_criteria_enumeration() -> None:
    """驗證②（SPEC Task 0.5）。"""
    assert cell_list_violations() == []


def test_freeze_started_after_estimate_reported() -> None:
    """驗證③（SPEC Task 0.5、R2-B）。"""
    assert order_violations() == []


def test_freeze_receipt_fields_and_criteria_hash() -> None:
    """凍結收據含 HEAD、`started_at`、函式庫版本、每格耗時與峰值記憶體（SPEC §G、Task 0.5 改法），且 `criteria_sha256`
    等於現行判準檔；凍結檔 `head` 等於收據 `head`、`exit_code`＝0。"""
    receipt = load_freeze_receipt()
    freeze = load_freeze()
    assert re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("head"))), receipt.get("head")
    assert freeze.get("head") == receipt["head"]
    assert receipt.get("exit_code") == 0
    if not nh.criteria_replaced():  # 判準檔已以 vN 取代（SPEC Task 0.3 邊界①：判準檔恰一存在） ⇒ 取代後改於下方對現行判準比對
        assert receipt.get("criteria_sha256") == hashlib.sha256(nh.CRITERIA_PATH.read_bytes()).hexdigest()
    assert isinstance(receipt.get("library_versions"), Mapping) and receipt["library_versions"]
    frozen = [r for r in receipt["cells"] if r.get("status") == "frozen"]
    assert frozen, "收據無任何 frozen 格"
    for record in frozen:
        assert isinstance(record.get("seconds"), (int, float)) and record["seconds"] > 0, record.get("cell_id")
        assert isinstance(record.get("peak_rss_bytes"), int) and record["peak_rss_bytes"] > 0, record.get("cell_id")
    if nh.criteria_replaced():  # 判準檔已以 vN 取代（SPEC Task 0.3 邊界①：判準檔恰一存在）
        assert receipt.get("criteria_sha256") == hashlib.sha256(nh.current_criteria_path().read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_09_insufficient_history_cell_blocked_with_bar_counts() -> None:
    """邊界①（SPEC Task 0.5）：前史不足之格依判準標 blocked（history）、記根數、不降門檻——對列舉之每格驗「根數 < 門檻
    ⇔ blocked-by history」，且所記根數等於 kline_cache.h5 實際根數。判準 v2：另一 blocked 來源為權威之 run 完整度判定
    （`run_history_blocked`：收據所記 reason_counts 全合 reason_pattern）——該判定成立之格須為 blocked-by history；不成立者
    沿原「根數 < 門檻 ⇔ blocked」斷言（前置篩）。"""
    expected = enumerate_cells(load_criteria())
    receipt_cells = _receipt_cells(load_freeze_receipt())
    if not nh.criteria_replaced():  # 判準檔已以 vN 取代（SPEC Task 0.3 邊界①：判準檔恰一存在） ⇒ 取代後改於迴圈後對現行判準比對
        assert load_freeze_receipt().get("criteria_sha256") == hashlib.sha256(nh.CRITERIA_PATH.read_bytes()).hexdigest()
    evaluated = 0
    for key, exp in expected.items():
        record = receipt_cells.get(key)
        assert record is not None, f"{key}: 收據缺格"
        history_blocked = record.get("status") == "blocked" and record.get("blocked_by") == "history"
        if not run_history_blocked(record):
            assert history_blocked == exp["blocked"], f"{key}: 根數 {exp['bar_counts']} 對門檻 {exp['threshold']} 之 blocked 判定不符"
        else:
            assert history_blocked, f"{key}: run 完整度判定前史不足（reason_counts）而未標 blocked-by history"
        if history_blocked:
            assert {str(k): int(v) for k, v in record["bar_counts"].items()} == exp["bar_counts"], key
            assert record.get("reason"), key
        evaluated += 1
    assert evaluated >= 1
    if nh.criteria_replaced():  # 判準檔已以 vN 取代（SPEC Task 0.3 邊界①：判準檔恰一存在）
        assert freeze_receipt_criteria_sha256() == hashlib.sha256(nh.current_criteria_path().read_bytes()).hexdigest()


def test_boundary_10_memory_guard_blocked_by_hardware_listed_fullscale() -> None:
    """邊界②（SPEC Task 0.5）：記憶體守護具名終止之格 ⇒ blocked-by 硬體、收據 `residuals` 列 RM-FULLSCALE 且
    `scripts/fact_keys.json` 之 RM-FULLSCALE 列文字含 NUMVIEW 與該格 symbol／週期；不得以縮小設定冒充同格——每個凍結格之
    `config_override`、`output_bars` 等於判準檔該格類之定義（對全部凍結格驗）。"""
    receipt = load_freeze_receipt()
    criteria = load_criteria()
    facts = json.loads(FACT_KEYS_PATH.read_text(encoding="utf-8"))
    rows = [r for r in facts["roadmap-status"]["rows"] if len(r) > 1 and r[1] == FULLSCALE_KEY]
    assert len(rows) == 1, f"fact_keys 之 {FULLSCALE_KEY} 列須恰一"
    fullscale_text = str(rows[0][-1])
    residuals = {(str(r.get("cell_id")), str(r.get("fact_key"))) for r in receipt.get("residuals") or []}
    frozen_ids = set(load_freeze()["cells"])
    for record in receipt["cells"]:
        if record.get("blocked_by") != "hardware":
            continue
        cell_id = str(record["cell_id"])
        assert record.get("status") == "blocked" and record.get("reason"), cell_id
        assert (cell_id, FULLSCALE_KEY) in residuals, f"{cell_id}: 未列入 {FULLSCALE_KEY}"
        assert "NUMVIEW" in fullscale_text and str(record["symbol"]) in fullscale_text, cell_id
        assert all(str(tf) in fullscale_text for tf in record["timeframes"]), cell_id
        assert cell_id not in frozen_ids, f"{cell_id}: blocked-by 硬體之格不得有凍結份"
    defs = criteria["cell_definitions"]
    evaluated = 0
    for cell_id, record in load_freeze()["cells"].items():
        kind = str(record["kind"])
        assert record.get("config_override") == defs[kind]["config_override"], f"{cell_id}: 設定與判準格定義不同"
        assert record.get("output_bars") == defs[kind]["output_bars"], f"{cell_id}: 輸出段根數與判準格定義不同"
        evaluated += 1
    assert evaluated >= 1


def test_boundary_11_single_selected_column_chunked_unreachable() -> None:
    """邊界③（SPEC Task 0.5、R3-D）：剔除 ratio-unsafe 後選欄數 ≤ 1 之格 ⇒ `pandas_chunked` 不可達，只凍其餘臂份並記
    `arm_unreachable`——對每個格 A 驗「若選欄數 ≤ 1 則…」，並直接呼叫凍結腳本 `reachable_arms(1)` 驗觸發值。"""
    contract = load_contract()
    arms = contract_arms(contract)
    assert SPEC_ARM_CHUNKED in arms
    at_one = sorted(_freeze_script().reachable_arms(1))
    assert at_one == sorted(a for a in arms if a != SPEC_ARM_CHUNKED), at_one
    unreachable = _unreachable_index(load_freeze_receipt())
    evaluated = 0
    for cell_id, record in load_freeze()["cells"].items():
        if record["kind"] != "A":
            continue
        evaluated += 1
        n = len(kept_columns(record["ic_first_selected"]))
        g1 = set((record.get("g1") or {}).keys())
        if n <= 1:
            assert SPEC_ARM_CHUNKED not in g1, f"{cell_id}: 選欄數 {n} 卻凍 {SPEC_ARM_CHUNKED}"
            entry = unreachable.get((str(cell_id), SPEC_ARM_CHUNKED))
            assert entry is not None and entry.get("selected_count") == n, cell_id
        if n == 1:
            assert g1 == set(at_one), f"{cell_id}: 單欄格之臂份 {sorted(g1)} ≠ {at_one}"
    assert evaluated >= 1


def test_boundary_12_zero_selected_all_g1_unreachable_g2_g3_frozen() -> None:
    """邊界④（SPEC Task 0.5）：選欄數 0 ⇒ IC 頁第三步既有錯誤行為（無輸出）⇒ G1 該格全臂 `arm_unreachable`、G2 兩份照凍；
    格 B 之 G3 不受影響——對每格驗「若選欄數 0 則…」，並直接呼叫凍結腳本 `reachable_arms(0)` 驗觸發值為空。"""
    contract = load_contract()
    arms = contract_arms(contract)
    assert _freeze_script().reachable_arms(0) == []
    assert reachable_by_contract(contract, 0) == []
    unreachable = _unreachable_index(load_freeze_receipt())
    evaluated = 0
    for cell_id, record in load_freeze()["cells"].items():
        evaluated += 1
        if record["kind"] == "B":
            g3 = record.get("g3") or {}
            assert {"raw", "processed"} <= set(g3), f"{cell_id}: G3 須照凍 raw／processed"
            continue
        n = len(kept_columns(record["ic_first_selected"]))
        if n == 0:
            assert not (record.get("g1") or {}), f"{cell_id}: 選欄數 0 卻有 G1 份"
            for arm in arms:
                entry = unreachable.get((str(cell_id), arm))
                assert entry is not None and entry.get("selected_count") == 0, f"{cell_id}/{arm}"
            assert set((record.get("g2") or {}).keys()) == {"0", "1"}, f"{cell_id}: G2 須照凍兩份"
    assert evaluated >= 1


# ---------------------------------------------------------------------------------------------- mutation

def _a_cell_with(freeze: Mapping[str, Any], *, min_kept: int, arm: str) -> str:
    for cell_id, record in freeze["cells"].items():
        if record["kind"] == "A" and len(kept_columns(record["ic_first_selected"])) >= min_kept \
                and arm in (record.get("g1") or {}):
            return str(cell_id)
    raise AssertionError(f"凍結檔無選欄數 ≥ {min_kept} 且具 {arm} 份之格 A ⇒ mutation 無對象")


def test_mutation_freeze_cell_removed_turns_cell_list_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：凍結檔刪一格 ⇒ ②紅。"""
    mutated = copy.deepcopy(load_freeze())
    victim = sorted(mutated["cells"])[0]
    mutated["cells"].pop(victim)
    monkeypatch.setattr(THIS, "load_freeze", lambda: copy.deepcopy(mutated))
    violations = cell_list_violations()
    assert any("凍結檔格 ≠ 收據 frozen 格" in v for v in violations), violations


def test_mutation_started_before_reported_turns_order_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：凍結收據 `started_at` 改為早於估時收據 `reported_at` ⇒ ③紅。"""
    reported = _parse_time(load_estimate_receipt()["reported_at"])
    mutated = copy.deepcopy(load_freeze_receipt())
    mutated["started_at"] = (reported - timedelta(seconds=1)).astimezone(timezone.utc).isoformat()
    monkeypatch.setattr(THIS, "load_freeze_receipt", lambda: copy.deepcopy(mutated))
    assert order_violations(), "mutant 存活：started_at 早於 reported_at 仍判通過"


def test_mutation_estimate_receipt_missing_freeze_script_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：刪估時收據（`RECEIPTS_DIR` 指向空目錄）後執行凍結腳本 ⇒ 拋 `EstimateGateError`（行程 rc≠0），且任何生成入口
    （FeatureFactory 之 generate_features／run_ic_first／run_multi_symbol、IC 頁 `_apply_transforms_sync`、
    `preprov_helpers._generate`）零呼叫——NotImplementedError 骨架不滿足本案。"""
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    freeze = _freeze_script()
    empty = tmp_path / "receipts"
    empty.mkdir()
    monkeypatch.setattr(freeze, "RECEIPTS_DIR", empty)
    calls: List[str] = []

    def spy(name: str):
        def _entry(*_args: Any, **_kwargs: Any) -> Any:
            calls.append(name)
            raise AssertionError(f"生成入口 {name} 於估時前置之前被呼叫")
        return _entry

    for owner, attr in ((FeatureFactory, "generate_features"), (FeatureFactory, "run_ic_first"),
                        (FeatureFactory, "run_multi_symbol"), (ICAnalysisService, "_apply_transforms_sync")):
        monkeypatch.setattr(owner, attr, spy(f"{owner.__name__}.{attr}"))
    monkeypatch.setattr(ph, "_generate", spy("preprov_helpers._generate"))
    with pytest.raises(Exception) as excinfo:
        freeze.main([])
    exc_type = type(excinfo.value)
    assert exc_type.__name__ == "EstimateGateError", f"拋出 {exc_type.__name__}：{excinfo.value}"
    assert Path(inspect.getfile(exc_type)).resolve() == GATE_PATH.resolve()
    assert calls == [], calls


def test_mutation_single_column_cell_chunked_copy_turns_g1_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：單欄格以 `pandas_optimized` 份複寫為 `pandas_chunked` 份 ⇒ ①紅（實際臂≠標示臂且可達性重算為不可達）。"""
    mutated = copy.deepcopy(load_freeze())
    cell_id = _a_cell_with(mutated, min_kept=1, arm=SPEC_ARM_OPTIMIZED)
    record = mutated["cells"][cell_id]
    record["ic_first_selected"] = kept_columns(record["ic_first_selected"])[:1]
    record["g1"][SPEC_ARM_CHUNKED] = copy.deepcopy(record["g1"][SPEC_ARM_OPTIMIZED])
    monkeypatch.setattr(THIS, "load_freeze", lambda: copy.deepcopy(mutated))
    violations = g1_violations()
    assert any(f"不可達之臂 {SPEC_ARM_CHUNKED} 有凍結份" in v for v in violations), violations
    assert any("≠ 標示臂" in v and cell_id in v for v in violations), violations


def test_mutation_reachable_cell_missing_chunked_marked_unreachable_turns_g1_red(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：可達格（選欄數 ≥ 2）漏凍 `pandas_chunked` 份而於收據標 `arm_unreachable` ⇒ ①紅。"""
    contract = load_contract()
    mutated = copy.deepcopy(load_freeze())
    cell_id = _a_cell_with(mutated, min_kept=2, arm=SPEC_ARM_CHUNKED)
    n = len(kept_columns(mutated["cells"][cell_id]["ic_first_selected"]))
    mutated["cells"][cell_id]["g1"].pop(SPEC_ARM_CHUNKED)
    receipt = copy.deepcopy(load_freeze_receipt())
    receipt.setdefault("arm_unreachable", []).append(
        {"cell_id": cell_id, "arm": SPEC_ARM_CHUNKED, "selected_count": n,
         "condition": contract["post_ic_arm_reachability"][SPEC_ARM_CHUNKED]["condition"]})
    monkeypatch.setattr(THIS, "load_freeze", lambda: copy.deepcopy(mutated))
    monkeypatch.setattr(THIS, "load_freeze_receipt", lambda: copy.deepcopy(receipt))
    violations = g1_violations()
    assert any(f"可達臂 {SPEC_ARM_CHUNKED} 被標 arm_unreachable" in v for v in violations), violations
    assert any("G1 臂份" in v and cell_id in v for v in violations), violations
