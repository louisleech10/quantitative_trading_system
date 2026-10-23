"""NUMVIEW（docs/NUMVIEW_SPEC.md §G、§V、Task 0.5／1.5）驗收共用 helper。

- §G 值指紋包裝（Task 0.5，R3-C／R4-A）：呼叫 `preprov_helpers.value_fingerprints`（唯一 oracle），另加
  `column_order_sha256`（manifest 宣告群組順序內之欄名序列 sha256）、逐欄 `values_native`（讀回陣列以其落盤原生
  dtype 之位元組：NaN 位置以該 dtype 之 0 取代、little-endian、C 連續，之 sha256；逐位元判定之唯一值鍵）與
  mean／std／nan_ratio（只報不判）。不得改用 `ffstat_helpers.public_fingerprints`。
- IC 頁 h5 之 DataFrame 版（`frame_fingerprints`）依同欄位定義計算，dtype 取 pandas dtype 字面、原生 dtype 取
  DataFrame 欄之 numpy dtype。
- 沿用基準相容條件（`assert_legacy_compatible`）：沿用之 `tests/_golden/preprov/pre_change_fingerprints.json` 所記
  `dtype` 全為 `float`／`halffloat` 方可以 dtype 相等＋float32 `values` 相等視同原生逐位元相等；遇其他 dtype ⇒ 斷言紅。
- 決定紀錄讀取（`decision`／`core_selector`）：Task 1.5 之 `tests/_golden/numview/decisions.json`（schema 定義於
  Task 0.3 之 `tests/_golden/numview/preregistered_criteria.json`）；`core_selector` 依決定輸出
  `tests/feature_engineering/test_numview_core.py` 之 `-k` 表示式（SPEC Task 3.1–3.3 ASSERT 行之條件選取）。

已實作（NUMVIEW b1）：值指紋包裝與決定紀錄讀取；`decision`／`core_selector` 於決定紀錄（Task 1.5）產出前 fail-closed 拋錯。
命令列：`venv/bin/python -m tests.feature_engineering.numview_helpers core-selector` 印 `-k` 表示式（Task 1.5 後可用）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

REPO: Path = Path(__file__).resolve().parents[2]
GOLDEN_DIR: Path = REPO / "tests" / "_golden" / "numview"
PRE_CHANGE_FINGERPRINTS_PATH: Path = GOLDEN_DIR / "pre_change_fingerprints.json"
#: 判準檔 v1 之檔名路徑（`test_numview_criteria.CRITERIA_V1` 即此；不代表現行判準——現行判準一律經
#: `current_criteria_path()`：v1／v2 恰一存在者，SPEC Task 0.3 邊界①）
CRITERIA_PATH: Path = GOLDEN_DIR / "preregistered_criteria.json"
CRITERIA_V2_PATH: Path = GOLDEN_DIR / "preregistered_criteria_v2.json"
#: 判準檔名樣式（v1＝preregistered_criteria.json，其後 preregistered_criteria_v<N>.json）
CRITERIA_GLOB = "preregistered_criteria*.json"
DECISIONS_PATH: Path = GOLDEN_DIR / "decisions.json"
REFREEZE_RECEIPT_PATH: Path = GOLDEN_DIR / "refreeze_receipt.json"
LEGACY_BASELINE_PATH: Path = REPO / "tests" / "_golden" / "preprov" / "pre_change_fingerprints.json"
NUMVIEW_CONTRACT_PATH: Path = REPO / "momentum" / "FeatureEngineering" / "contracts" / "numeric_view.json"
RECEIPTS_DIR: Path = REPO / "handoffs" / "run_receipts"
KLINE_PATH: Path = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"

#: 沿用基準之相容 dtype（Arrow 型別字面；float16／float32 轉 float32 為精確；SPEC §G R4-A）
LEGACY_COMPATIBLE_DTYPES = ("float", "halffloat")

#: 新凍結值指紋之逐位元比對鍵（SPEC §G 通過條件：dtype、nan、values_native、column_set_sha256、column_order_sha256）
BITWISE_COLUMN_KEYS = ("dtype", "nan", "values_native")
BITWISE_TABLE_KEYS = ("column_set_sha256", "column_order_sha256")

#: Phase 3 決定點鍵（SPEC Task 3.1–3.3 ASSERT 行之 WHEN 鍵）
CORE_DECISION_KEYS = ("d_postic", "d_mtf", "d_memmap", "d_winsor_dtype", "d_codec", "d_l2")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def current_criteria_path() -> Path:
    """現行事前登記判準檔：`GOLDEN_DIR` 下 `preregistered_criteria*.json`（v1、v2、v3…）恰一存在者；非恰一 ⇒ RuntimeError
    （同 `_estimate_gate.resolve_criteria_path`）。刻意不用 assert：本函式被測試呼叫，無斷言即不被 TESTREG 展開為測試之
    斷言元素（不擾動既有斷言之正規化序號）。"""
    present = sorted(p for p in GOLDEN_DIR.glob(CRITERIA_GLOB) if p.is_file())
    if len(present) != 1:
        raise RuntimeError(f"判準檔（{CRITERIA_GLOB}）須恰一存在，實得 {[p.name for p in present]}")
    return present[0]


def criteria_replaced() -> bool:
    """現行判準檔已非 v1（`CRITERIA_PATH`）——即已依 SPEC Task 0.3 邊界①以 vN 取代。無斷言（同上理由）。"""
    return current_criteria_path() != CRITERIA_PATH


def criteria_cell_list() -> Optional[List[Dict[str, Any]]]:
    """現行判準之封閉格清單（v3 起 `cell_rules.cell_list.cells`；舊版無 ⇒ None）。無斷言。"""
    import json as _json

    rules = _json.loads(current_criteria_path().read_text(encoding="utf-8")).get("cell_rules") or {}
    cells = (rules.get("cell_list") or {}).get("cells")
    return [dict(c) for c in cells] if isinstance(cells, list) else None


def criteria_run_cells(run_kind: str) -> Optional[List[str]]:
    """現行判準 `run_coverage.<run_kind>.runs[].cell` 之格 id（去重保序；舊版無 ⇒ None）。無斷言。"""
    import json as _json

    coverage = _json.loads(current_criteria_path().read_text(encoding="utf-8")).get("run_coverage")
    if not isinstance(coverage, dict):
        return None
    runs = (coverage.get(run_kind) or {}).get("runs") or []
    return list(dict.fromkeys(str(r["cell"]) for r in runs))


def _closed_key(cell: Mapping[str, Any]) -> Tuple[str, str, Tuple[str, ...]]:
    return (str(cell["kind"]), str(cell["symbol"]), tuple(str(t) for t in cell["timeframes"]))


def criteria_cell_keys(kinds: Sequence[str]) -> Set[Tuple[str, str, Tuple[str, ...]]]:
    """現行判準封閉清單中格類屬 `kinds` 之格鍵 {(kind, symbol, timeframes)}（舊版無封閉清單 ⇒ RuntimeError，呼叫端須先以
    `criteria_cell_list() is not None` 分支）。無斷言。"""
    cells = criteria_cell_list()
    if cells is None:
        raise RuntimeError("現行判準無封閉格清單（cell_rules.cell_list）")
    return {_closed_key(c) for c in cells if str(c["kind"]) in kinds}


def criteria_run_cell_keys(run_kind: str) -> Set[Tuple[str, str, Tuple[str, ...]]]:
    """現行判準 `run_coverage.<run_kind>` 所涵蓋之格鍵（格 id 對封閉清單解析；id 不在清單或判準無封閉清單 ⇒ RuntimeError）。
    無斷言。"""
    cells = criteria_cell_list()
    ids = criteria_run_cells(run_kind)
    if cells is None or ids is None:
        raise RuntimeError("現行判準無封閉格清單或 run_coverage")
    by_id = {str(c["id"]): c for c in cells}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise RuntimeError(f"run_coverage.{run_kind} 之格不在封閉清單：{missing}")
    return {_closed_key(by_id[i]) for i in ids}


def criteria_symbol_timeframes(kind: str) -> Set[Tuple[str, Tuple[str, ...]]]:
    """現行判準封閉清單中格類 `kind` 之 {(symbol, timeframes)}。無斷言。"""
    return {(key[1], key[2]) for key in criteria_cell_keys((kind,))}


# ---------------------------------------------------------------------------------------------- Phase 2–4 批次共用生成

#: 批次共用快取根之環境覆寫（未設 ⇒ 系統暫存目錄下 numview-regen-batch）
REGEN_BATCH_ROOT_ENV = "NUMVIEW_REGEN_BATCH_ROOT"
#: 碼態之範圍（判準檔 cell_rules.batch_cache.code_state_paths；只計原始碼與契約，不計 __pycache__／numba 快取檔）
CODE_STATE_PATHSPECS = (":(glob)momentum/**/*.py", ":(glob)momentum/**/*.json", ":(glob)api/**/*.py")


#: 現行批次（b3／b4／b5）之環境變數：讀多批之檢查（§G：Phase 2＝b3、Phase 4＝b5）依此取批次標籤；各批驗收命令與收案
#: gate_cmd 設定之（docs/manifests/NUMVIEW.json）
REGEN_BATCH_ENV = "NUMVIEW_REGEN_BATCH"


def regen_batch_kind(check_kind: str) -> str:
    """驗收檢查跑別（regen_t21…regen_section_g）所讀之批次生成跑別（判準 `run_coverage.<檢查>.reads_from`）：只讀一批 ⇒
    該批；讀多批（§G）⇒ 環境變數 `NUMVIEW_REGEN_BATCH`（b3／b4／b5）所指之批，未設或不屬 reads_from ⇒ RuntimeError
    （不猜測：Phase 4 之 §G 須標 b5）。判準無 reads_from（v1／v2）⇒ 原檢查跑別。共用快取以碼態為鍵，不以批名。無斷言。"""
    import os

    coverage = json.loads(current_criteria_path().read_text(encoding="utf-8")).get("run_coverage")
    reads = ((coverage or {}).get(check_kind) or {}).get("reads_from") if isinstance(coverage, dict) else None
    if not reads:
        return check_kind
    if len(reads) == 1:
        return str(reads[0])
    wanted = f"regen_{os.environ.get(REGEN_BATCH_ENV, '')}"
    if wanted not in reads:
        raise RuntimeError(f"{check_kind} 讀多批 {reads}：須設 {REGEN_BATCH_ENV}（b3／b4／b5）指明現行批次，實得 "
                           f"{os.environ.get(REGEN_BATCH_ENV)!r}")
    return wanted


def regen_batch_root() -> Path:
    """批次共用生成快取根（判準檔 cell_rules.batch_cache）：凍結腳本 `generate_cell` 之 `root` 恰為此路徑時，生成落於
    `root / regen_cache_key(cell, env)`，已存在完整 run 即直接回傳；其他 `root`（含 mutant 之暫存根）一律不讀寫本快取。
    無斷言。"""
    import os
    import tempfile

    return Path(os.environ.get(REGEN_BATCH_ROOT_ENV) or Path(tempfile.gettempdir()) / "numview-regen-batch")


def regen_root(fallback: Path) -> Path:
    """驗收檢查之重生根：現行判準具批次共用生成（run_coverage 有 code_state 為 b3／b4／b5 之跑別）⇒ `regen_batch_root()`；
    否則 `fallback`（舊判準之隔離根）。mutant 生成不得經本函式（一律用測試暫存根）。無斷言。"""
    coverage = json.loads(current_criteria_path().read_text(encoding="utf-8")).get("run_coverage")
    batched = isinstance(coverage, dict) and any(isinstance(node, dict) and node.get("code_state") in ("b3", "b4", "b5")
                                                 for node in coverage.values())
    return regen_batch_root() if batched else Path(fallback)


def code_state_sha256() -> str:
    """碼態 sha256：`CODE_STATE_PATHSPECS` 之 git 索引（路徑＋blob）、對 HEAD 之工作樹差異、未追蹤檔之路徑與內容。任一 git
    呼叫失敗 ⇒ RuntimeError（不猜測）。無斷言。"""
    import subprocess

    digest = hashlib.sha256()

    def git(*args: str) -> bytes:
        proc = subprocess.run(["git", "-C", str(REPO), *args, "--", *CODE_STATE_PATHSPECS], capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} 失敗：{proc.stderr.decode(errors='replace')[:200]}")
        return proc.stdout

    digest.update(git("ls-files", "-s"))
    digest.update(git("diff", "HEAD", "--binary"))
    for rel in sorted(git("ls-files", "--others", "--exclude-standard").decode().split("\n")):
        if rel:
            digest.update(rel.encode())
            digest.update((REPO / rel).read_bytes())
    return digest.hexdigest()


def regen_cache_key(cell: Mapping[str, Any], env: Optional[Mapping[str, str]] = None) -> str:
    """批次共用生成之快取鍵（判準檔 cell_rules.batch_cache.key）：格描述子（id、kind、symbol、timeframes；變體改 timeframes
    即異鍵）、env 正規化、產品碼態、生成接縫碼態、格之 K 線資料集紀錄（`regen_cache_key_payload`）之 sha256。無斷言。"""
    payload = json.dumps(regen_cache_key_payload(cell, env), sort_keys=True, ensure_ascii=False)
    # 審查 r6（CODEX-R6-P1-01）：資料集或生成接縫改變而 momentum／api 不變時，鍵亦須改變（快取不命中、重生）
    # 組成見 regen_cache_key_payload（定義於檔末：避免既有函式行號位移）
    return _sha256(payload.encode("utf-8"))


def values_native_sha256(values: np.ndarray) -> str:
    """原生 dtype 位元組之 sha256（SPEC §G R4-A）：NaN 位置以該 dtype 之 0 取代、轉 little-endian、C 連續後雜湊。
    float64 陣列只差小於 float32 解析度者（例 `1.0` 與 `1.0 + 2**-40`）須得不同值。
    非數值（object 等）dtype ⇒ TypeError（無原生位元組語意，不得雜湊指標）。"""
    arr = np.asarray(values)
    if arr.dtype.kind not in "biufc":
        raise TypeError(f"values_native_sha256 只接受數值 dtype，實得 {arr.dtype}")
    if arr.dtype.kind in "fc":
        arr = np.where(np.isnan(arr), arr.dtype.type(0), arr)
    little = arr.astype(arr.dtype.newbyteorder("<"), copy=False)
    return _sha256(np.ascontiguousarray(little).tobytes())


def column_order_sha256(names: Sequence[str]) -> str:
    """欄名序列（保序、不排序）以換行連接之 UTF-8 sha256（SPEC §G R3-C）。"""
    return _sha256("\n".join(str(n) for n in names).encode("utf-8"))


def _column_set_sha256(names: Sequence[str]) -> str:
    """排序欄名以換行連接之 sha256（＝`preprov_helpers.value_fingerprints` 之 `column_set_sha256` 定義）。"""
    return _sha256("\n".join(sorted(str(n) for n in names)).encode("utf-8"))


def _float32_entry(native: np.ndarray) -> Dict[str, str]:
    """`preprov_helpers.value_fingerprints` 之逐欄 `nan`／`values` 定義（float32 NaN 遮罩 packbits、NaN→0 之 float32）。"""
    arr = np.asarray(native, dtype=np.float32)
    nan = np.isnan(arr)
    return {"nan": _sha256(np.packbits(nan).tobytes()),
            "values": _sha256(np.where(nan, np.float32(0), arr).tobytes())}


def _report_stats(native: np.ndarray) -> Dict[str, Optional[float]]:
    """只報不判之逐欄統計（mean／std 只取有限值、float64 累積；nan_ratio＝NaN 比例；無有限值 ⇒ None）。"""
    arr = np.asarray(native, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    nan_ratio = float(np.isnan(arr).mean()) if arr.size else None
    if finite.size == 0:
        return {"mean": None, "std": None, "nan_ratio": nan_ratio}
    return {"mean": float(finite.mean()), "std": float(finite.std()), "nan_ratio": nan_ratio}


def fingerprints(run_dir: Path, artifact_kind: str = "raw") -> Dict[str, Any]:
    """run 目錄之 §G 值指紋：`preprov_helpers.value_fingerprints` 之輸出，另於每欄加 `values_native`、`mean`、`std`、
    `nan_ratio`，於表層加 `column_order_sha256`（manifest 宣告群組順序內之欄名序列）。只讀 manifest 宣告之群組檔。"""
    import pyarrow.parquet as pq

    from tests.feature_engineering import preprov_helpers as ph

    base = ph.value_fingerprints(Path(run_dir), artifact_kind)
    order: List[str] = []
    for path in ph.declared_group_files(Path(run_dir), artifact_kind):
        table = pq.read_table(str(path))
        for name in table.column_names:
            if name in ph.NON_FEATURE_COLUMNS:
                continue
            native = np.asarray(table.column(name).to_numpy(zero_copy_only=False))
            entry = base["columns"][name]
            entry["values_native"] = values_native_sha256(native)
            entry.update(_report_stats(native))
            order.append(str(name))
    if sorted(set(order)) != sorted(base["columns"]) or len(order) != len(set(order)):
        raise AssertionError(f"{run_dir}/{artifact_kind}：宣告群組之欄序與 value_fingerprints 欄集合不一致或有重複欄")
    base["column_order_sha256"] = column_order_sha256(order)
    return base


def frame_fingerprints(frame: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame 版（IC 頁 h5 輸出；SPEC §G G1）：欄位定義同 `fingerprints`，dtype 取 pandas dtype 字面，
    `values_native` 依 DataFrame 欄之 numpy dtype，`column_order_sha256` 依 DataFrame 欄序。欄名重複 ⇒ ValueError。"""
    names = [str(c) for c in frame.columns]
    if len(names) != len(set(names)):
        raise ValueError(f"frame_fingerprints：欄名重複 {sorted({n for n in names if names.count(n) > 1})}")
    columns: Dict[str, Dict[str, Any]] = {}
    for position, name in enumerate(names):
        series = frame.iloc[:, position]
        native = series.to_numpy()
        entry: Dict[str, Any] = {"dtype": str(series.dtype)}
        entry.update(_float32_entry(native))
        entry["values_native"] = values_native_sha256(native)
        entry.update(_report_stats(native))
        columns[name] = entry
    return {"columns": columns, "column_set_sha256": _column_set_sha256(names),
            "column_order_sha256": column_order_sha256(names)}


def assert_legacy_compatible(fingerprint: Mapping[str, Any]) -> None:
    """沿用基準相容斷言（SPEC §G R4-A）：`fingerprint["columns"][*]["dtype"]` 皆屬 `LEGACY_COMPATIBLE_DTYPES`，
    否則 AssertionError（列出不相容欄；該欄須於 Task 0.5 以 `values_native` 重凍，不得以 float32 鍵通過）。"""
    bad = sorted(f"{name}:{entry.get('dtype')!r}" for name, entry in fingerprint["columns"].items()
                 if entry.get("dtype") not in LEGACY_COMPATIBLE_DTYPES)
    assert not bad, (f"沿用基準含非 {LEGACY_COMPATIBLE_DTYPES} 之欄 {len(bad)} 個（須以 values_native 重凍）："
                     f"{bad[:10]}")


#: 沿用基準（legacy）之逐欄比對鍵：dtype、float32 `values`，另比 `nan`（float32 `values` 以 0 代 NaN，遮罩須另比；SPEC §C）
_LEGACY_COLUMN_KEYS = ("dtype", "nan", "values")
_LEGACY_TABLE_KEYS = ("column_set_sha256",)


def bitwise_diff(before: Mapping[str, Any], after: Mapping[str, Any], *, legacy: bool = False) -> List[str]:
    """兩份值指紋之逐位元差異清單（空＝相等）。新凍結（`legacy=False`）比 `BITWISE_COLUMN_KEYS` 與
    `BITWISE_TABLE_KEYS`；沿用基準（`legacy=True`）先 `assert_legacy_compatible(before)`，再比 `dtype` 與 float32
    `values`（另比 `nan` 遮罩）、`column_set_sha256`。atol=0、rtol=0（SPEC §G 通過條件）。
    指紋缺比對鍵 ⇒ KeyError（無從判定，不得視為相等）。每條差異以欄名或表層鍵名起首。"""
    if legacy:
        assert_legacy_compatible(before)
    column_keys = _LEGACY_COLUMN_KEYS if legacy else BITWISE_COLUMN_KEYS
    table_keys = _LEGACY_TABLE_KEYS if legacy else BITWISE_TABLE_KEYS
    out: List[str] = []
    b_cols, a_cols = before["columns"], after["columns"]
    for name in sorted(set(b_cols) | set(a_cols)):
        if name not in a_cols:
            out.append(f"{name}: 只在改前")
            continue
        if name not in b_cols:
            out.append(f"{name}: 只在改後")
            continue
        for key in column_keys:
            if b_cols[name][key] != a_cols[name][key]:
                out.append(f"{name}: {key} 不同（{b_cols[name][key]!r} → {a_cols[name][key]!r}）")
    for key in table_keys:
        if before[key] != after[key]:
            out.append(f"{key}: 不同")
    return out


def _decision_record(key: str) -> Mapping[str, Any]:
    assert DECISIONS_PATH.is_file(), f"決定紀錄不存在：{DECISIONS_PATH}（Task 1.5 未產出）"
    data = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    records = data.get("decisions") if isinstance(data, Mapping) else None
    assert isinstance(records, Mapping), "決定紀錄之 decisions 須為 {決定點鍵: 紀錄} 物件"
    record = records.get(key)
    assert isinstance(record, Mapping), f"決定紀錄缺決定點 {key}"
    assert "key" not in record or record["key"] == key, f"決定紀錄 {key} 之內嵌 key={record['key']!r} 與物件鍵不同"
    return record


def decision(key: str) -> str:
    """決定紀錄（`DECISIONS_PATH`；全票唯一形 `{criteria_sha256, decisions: {<決定點鍵>: record}, measurement_limitations}`）
    中決定點 `key`（`CORE_DECISION_KEYS` 之一，或 `d_icpage_arm`／`d_research`）之 `record["choice"]`（如
    `polars_float64`／`retain`）；檔缺、鍵缺或 `choice` 缺 ⇒ AssertionError（fail-closed）。"""
    choice = _decision_record(key).get("choice")
    assert isinstance(choice, str) and choice, f"決定紀錄 {key} 缺 choice"
    return choice


#: 決定值 → `test_numview_core.py` 分支記號（SPEC Task 3.1–3.3 ASSERT … WHEN … 行）
_CORE_TOKENS: Dict[str, Dict[str, str]] = {
    "d_postic": {"polars_float64": "postic_float64", "retain": "postic_retained"},
    "d_mtf": {"unify": "mtf_dtype", "retain": "mtf_retained"},
    "d_memmap": {"decouple": "memmap_dtype", "retain": "memmap_retained"},
    "d_winsor_dtype": {"unify": "(winsor_dtype and not winsor_dtype_retained)", "retain": "winsor_dtype_retained"},
    "d_codec": {"provenance": "codec_by_provenance", "retain": "codec_retained"},
    "d_l2": {"unify": "l2_unified", "retain": "l2_named"},
}
_CORE_ALWAYS = "core_always"


def core_selector() -> str:
    """依決定紀錄輸出 `test_numview_core.py` 之 pytest `-k` 表示式（SPEC Task 3.1–3.3 之 ASSERT … WHEN … 行：
    每個決定點恰選其一支）。決定紀錄缺或任一決定點缺 ⇒ 拋錯（呼叫端之 `-k` 因而為空 ⇒ 全部分支皆跑 ⇒ 必紅，fail-closed）。
    分支記號（決定值 → 記號）：d_postic polars_float64→`postic_float64`／retain→`postic_retained`；d_mtf unify→`mtf_dtype`／
    retain→`mtf_retained`；d_memmap decouple→`memmap_dtype`／retain→`memmap_retained`；d_winsor_dtype
    unify→`(winsor_dtype and not winsor_dtype_retained)`／retain→`winsor_dtype_retained`；d_codec
    provenance→`codec_by_provenance`／retain→`codec_retained`；d_l2 unify→`l2_unified`／retain→`l2_named`；另恆含
    `core_always`。輸出＝`core_always or <六記號 or 連接>`。記號間之子字串碰撞已逐對檢查：唯一者為
    `winsor_dtype` ⊂ `winsor_dtype_retained`，故以 `and not` 排除。決定值不屬該點之兩支 ⇒ ValueError。"""
    tokens = [_CORE_ALWAYS]
    for key in CORE_DECISION_KEYS:
        choice = decision(key)
        mapping = _CORE_TOKENS[key]
        if choice not in mapping:
            raise ValueError(f"決定紀錄 {key}={choice!r} 不屬 {sorted(mapping)}")
        tokens.append(mapping[choice])
    return " or ".join(tokens)


#: Task 1.1 效能基準收據之 repo 相對路徑形（D-ICPAGE-ARM 之 re_presentation 所據）
PERF_RECEIPT_PATTERN = r"handoffs/run_receipts/\d{8}-numview-perf-benchmark\.json"


def perf_receipt_first_commit_date(rel: str) -> Optional[str]:
    """效能基準收據之首次提交日（`YYYY-MM-DD`，提交者日期）；未提交或 git 失敗 ⇒ None。無斷言。"""
    import subprocess

    proc = subprocess.run(["git", "-C", str(REPO), "log", "--diff-filter=A", "--format=%cs", "--", rel], capture_output=True)
    dates = proc.stdout.decode().split() if proc.returncode == 0 else []
    return dates[-1] if dates else None


def re_presentation_violations(record: Mapping[str, Any], *, exists: Any = None, committed_date: Any = None,
                               load: Any = None) -> List[str]:
    """D-ICPAGE-ARM 之 `re_presentation`（SPEC v17 §A 重新呈報條件、Task 1.5 ⑦、Task 3.4 施工前提；判準檔
    decision_rules.d_icpage_arm.candidate_conditions.lock.requires_re_presentation）：{date（不早於效能基準收據之首次提交日）,
    quote（使用者回覆逐字，非空字串清單）, perf_benchmark_receipt（Task 1.1 效能基準收據路徑，須存在且已提交，且其內容合
    `perf_benchmark_receipt_violations`——審查 r6 CODEX-R6-P1-04）, confirmed_choice（＝本筆 choice）}。`exists`／
    `committed_date`／`load`（讀收據 JSON）可注入（預設讀 repo 與 git）。無斷言。"""
    import re as _re

    exists = exists or (lambda rel: (REPO / rel).is_file())
    committed_date = committed_date or perf_receipt_first_commit_date
    load = load or (lambda rel: json.loads((REPO / rel).read_text(encoding="utf-8")))
    rp = record.get("re_presentation")
    if not isinstance(rp, Mapping):
        return ["d_icpage_arm：缺 re_presentation（Task 3.4 落地前須以效能基準重新呈報使用者並逐字記回覆）"]
    out: List[str] = []
    date = rp.get("date")
    if not (isinstance(date, str) and _re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)):
        out.append(f"d_icpage_arm：re_presentation.date {date!r} 非 YYYY-MM-DD")
        date = None
    quote = rp.get("quote")
    if not (isinstance(quote, list) and quote and all(isinstance(q, str) and q.strip() for q in quote)):
        out.append("d_icpage_arm：re_presentation.quote 須為非空之使用者原話清單")
    receipt = rp.get("perf_benchmark_receipt")
    if not (isinstance(receipt, str) and _re.fullmatch(PERF_RECEIPT_PATTERN, receipt)):
        out.append(f"d_icpage_arm：re_presentation.perf_benchmark_receipt {receipt!r} 非效能基準收據路徑")
    elif not exists(receipt):
        out.append(f"d_icpage_arm：效能基準收據 {receipt} 不存在")
    else:
        committed = committed_date(receipt)
        if committed is None:
            out.append(f"d_icpage_arm：效能基準收據 {receipt} 未提交（重新呈報須據已提交之收據）")
        elif date is not None and date < committed:
            out.append(f"d_icpage_arm：re_presentation.date {date} 早於效能基準收據之提交 {committed}")
        try:
            content = load(receipt)
        except (OSError, ValueError) as exc:
            out.append(f"d_icpage_arm：效能基準收據 {receipt} 不可讀：{exc}")
        else:
            out += [f"d_icpage_arm：效能基準收據 {receipt}：{v}" for v in perf_benchmark_receipt_violations(content)]
    if rp.get("confirmed_choice") != record.get("choice"):
        out.append(f"d_icpage_arm：re_presentation.confirmed_choice {rp.get('confirmed_choice')!r} ≠ choice "
                   f"{record.get('choice')!r}")
    return out


#: 效能基準之候選臂（SPEC Task 1.1：契約臂之外另量 polars_float64）
PERF_CANDIDATE_ARM = "polars_float64"
#: 每臂每輸入之牆鐘重複次數（SPEC Task 1.1：各跑三次取中位）
PERF_RUNS = 3


def perf_benchmark_receipt_violations(receipt: Any) -> List[str]:
    """Task 1.1 效能基準收據之內容（SPEC v17 Task 1.1「效能基準」；審查 r6 CODEX-R6-P1-04；D-ICPAGE-ARM 重新呈報與收案閘共用）：
    `inputs`＝[{cell, arms: {臂: {runs_seconds: [3 個正數], median_seconds, reachable} 或 {reachable: false, unreachable_reason}}}]，
    須恰涵蓋判準 `run_coverage.perf_benchmark` 之格（C 格選欄全集、`A:BTCUSDT:1h` 選欄）；每輸入之臂集合＝契約
    `post_ic_arm_values` ∪ {polars_float64}；可達臂恰 3 次牆鐘、`median_seconds`＝其中位數；`polars_profile`＝{steps:
    [{step, seconds}]（非空）, rank_udf_per_column_python_loop: bool}（Polars 慢因剖析）。不合 ⇒ 違規。無斷言。"""
    import statistics

    if not isinstance(receipt, Mapping):
        return ["收據非物件"]
    out: List[str] = []
    contract = json.loads(NUMVIEW_CONTRACT_PATH.read_text(encoding="utf-8"))
    arms_want = set(contract["post_ic_arm_values"]["values"]) | {PERF_CANDIDATE_ARM}
    cells_want = set(criteria_run_cells("perf_benchmark") or [])
    inputs = receipt.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        return out + ["缺 inputs"]
    cells_got = {str(i.get("cell")) for i in inputs if isinstance(i, Mapping)}
    if cells_got != cells_want or len(cells_got) != len(inputs):
        out.append(f"inputs 之格 {sorted(cells_got)} ≠ 判準 perf_benchmark 之格 {sorted(cells_want)}（或重複）")
    for item in inputs:
        if not isinstance(item, Mapping):
            out.append("inputs 項非物件")
            continue
        cell = item.get("cell")
        arms = item.get("arms")
        if not isinstance(arms, Mapping) or set(arms) != arms_want:
            out.append(f"{cell}：臂集合 {sorted(arms or {})} ≠ 契約臂＋{PERF_CANDIDATE_ARM} {sorted(arms_want)}")
            continue
        for arm, rec in arms.items():
            if not isinstance(rec, Mapping):
                out.append(f"{cell}/{arm}：紀錄非物件")
            elif rec.get("reachable") is False:
                if not str(rec.get("unreachable_reason") or "").strip():
                    out.append(f"{cell}/{arm}：不可達而無理由")
            else:
                runs = rec.get("runs_seconds")
                if not (isinstance(runs, list) and len(runs) == PERF_RUNS
                        and all(isinstance(r, (int, float)) and not isinstance(r, bool) and r > 0 for r in runs)):
                    out.append(f"{cell}/{arm}：牆鐘須恰 {PERF_RUNS} 次正數，實得 {runs!r}")
                elif rec.get("median_seconds") != statistics.median(runs):
                    out.append(f"{cell}/{arm}：median_seconds {rec.get('median_seconds')!r} ≠ 三次之中位數")
    profile = receipt.get("polars_profile")
    steps = profile.get("steps") if isinstance(profile, Mapping) else None
    if not (isinstance(steps, list) and steps and all(isinstance(s, Mapping) and str(s.get("step") or "").strip()
                                                       and isinstance(s.get("seconds"), (int, float)) for s in steps)):
        out.append("缺 Polars 慢因剖析（polars_profile.steps 逐步驟耗時）")
    if not isinstance(profile, Mapping) or not isinstance(profile.get("rank_udf_per_column_python_loop"), bool):
        out.append("polars_profile 須判明 rank UDF 是否逐欄 Python 迴圈（rank_udf_per_column_python_loop: bool）")
    return out


def criteria_version() -> int:
    """現行判準檔之版本號：`preregistered_criteria.json`＝1、`preregistered_criteria_v<N>.json`＝N；判準檔非恰一或檔名不合
    ⇒ RuntimeError。無斷言。"""
    import re as _re

    path = current_criteria_path()
    if path == CRITERIA_PATH:
        return 1
    match = _re.fullmatch(r"preregistered_criteria_v(\d+)\.json", path.name)
    if match is None:
        raise RuntimeError(f"判準檔名不合 preregistered_criteria_v<N>.json：{path.name}")
    return int(match.group(1))


#: 生成接縫之碼態範圍（審查 r6 CODEX-R6-P1-01）：凍結腳本、本 helper、PRE-PROV 生成 helper、numview 探針模組
SEAM_GLOBS = ("scripts/numview_freeze_baseline.py", "tests/feature_engineering/numview_helpers.py",
              "tests/feature_engineering/preprov_helpers.py", "handoffs/run_receipts/numview_probes/*.py")


def _read_bytes(path: Path) -> bytes:
    return Path(path).read_bytes()


def seam_state_sha256() -> str:
    """生成接縫碼態 sha256：`SEAM_GLOBS` 所指檔（工作樹內容，含未提交改動）之 repo 相對路徑與位元組。無斷言。"""
    digest = hashlib.sha256()
    for pattern in SEAM_GLOBS:
        for path in sorted(REPO.glob(pattern)):
            if path.is_file():
                digest.update(str(path.relative_to(REPO)).encode("utf-8"))
                digest.update(_read_bytes(path))
    return digest.hexdigest()


def kline_dataset_sha256(source: Path, symbol: str, tf: str) -> str:
    """`<source>` 之 `<symbol>/<tf>/data` 資料集 sha256（dtype 描述＋C 連續位元組；同估時器 `estimate.dataset_record`、判準檔
    kline_source.dataset_sha256）。無斷言。"""
    import h5py

    with h5py.File(str(source), "r") as handle:
        arr = handle[symbol][tf]["data"][()]
    digest = hashlib.sha256()
    digest.update(str(arr.dtype.descr).encode("utf-8"))
    digest.update(np.ascontiguousarray(arr).tobytes())
    return digest.hexdigest()


def cell_dataset_records(cell: Mapping[str, Any]) -> Dict[str, Dict[str, str]]:
    """格之 K 線資料集紀錄 {tf: {source, dataset_sha256}}：來源＝格之主週期（最短週期）依現行判準 `cell_rules.kline_source.
    by_timeframe` 之檔，各週期皆讀自該檔（單一 cache_dir）；未列週期 ⇒ RuntimeError。無斷言。"""
    rules = json.loads(current_criteria_path().read_text(encoding="utf-8"))["cell_rules"]["kline_source"]["by_timeframe"]
    tfs = [str(t) for t in cell.get("timeframes") or []]
    primary = min(tfs, key=lambda t: pd.Timedelta(t)) if tfs else None
    if primary is None or primary not in rules:
        raise RuntimeError(f"格 {cell.get('id')} 之主週期 {primary!r} 不在 kline_source.by_timeframe")
    source = REPO / str(rules[primary])
    return {tf: {"source": str(rules[primary]), "dataset_sha256": kline_dataset_sha256(source, str(cell["symbol"]), tf)}
            for tf in tfs}


def regen_cache_key_payload(cell: Mapping[str, Any], env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """批次共用生成快取鍵之組成（判準檔 cell_rules.batch_cache.key）。無斷言。"""
    return {"cell": {k: cell.get(k) for k in ("id", "kind", "symbol", "timeframes")},
            "env": {str(k): str(v) for k, v in dict(env or {}).items()},
            "code_state": code_state_sha256(), "seam_state": seam_state_sha256(),
            "datasets": cell_dataset_records(cell)}


#: b4 之 mutant／故障注入生成之估時跑別（審查 r6 CODEX-R6-P1-02：判準 run_coverage.regen_b4_mutants）
REGEN_MUTANT_KIND = "regen_b4_mutants"


def regen_core_kind(patched: bool) -> str:
    """Task 3.1–3.3 核心測試生成之估時跑別：含 mutant／故障注入 patch ⇒ `regen_b4_mutants`（另一碼態、不讀寫共用快取，判準
    有此跑別時）；否則 `regen_t3_core` 所讀之批次（b4）。無斷言。"""
    coverage = json.loads(current_criteria_path().read_text(encoding="utf-8")).get("run_coverage")
    if patched and isinstance(coverage, dict) and REGEN_MUTANT_KIND in coverage:
        return REGEN_MUTANT_KIND
    return regen_batch_kind("regen_t3_core")


def frozen_cells_without_kind(cells: Mapping[str, Any], kind: str) -> Dict[str, Any]:
    """凍結檔 `cells` 去除格類 `kind` 之格（保序；非物件之項保留，由呼叫端之斷言判）。無斷言。"""
    return {k: v for k, v in cells.items() if not (isinstance(v, Mapping) and v.get("kind") == kind)}


def criteria_freeze_group(name: str) -> List[str]:
    """現行判準 `cell_rules.freeze_groups.<name>` 之格 id（舊版無 ⇒ 空清單）。無斷言。"""
    groups = (json.loads(current_criteria_path().read_text(encoding="utf-8")).get("cell_rules") or {}).get("freeze_groups")
    return [str(x) for x in (groups or {}).get(name) or []] if isinstance(groups, dict) else []


def precision_segments(cell_id: str, default: Sequence[str]) -> List[str]:
    """精度鏈該格須具之段（判準 `run_coverage.precision_chain` 之讀取列 `segments`；審查 r8 GROK-R8-P1-01：只生成之格 C 無 S5）；
    判準無此欄（舊版）⇒ `default`。無斷言。"""
    coverage = json.loads(current_criteria_path().read_text(encoding="utf-8")).get("run_coverage")
    runs = ((coverage or {}).get("precision_chain") or {}).get("runs") if isinstance(coverage, dict) else None
    for r in runs or []:
        if str(r.get("cell")) == str(cell_id) and not r.get("generations") and isinstance(r.get("segments"), list):
            return [str(s) for s in r["segments"]]
    return list(default)


#: 群組粒度值指紋之格類（SPEC §G：全特徵格 C 約 20.9 萬欄，逐欄指紋實測每欄 355 bytes ⇒ raw＋processed 約 148 MB，逾版控單檔上限）
GROUP_GRANULARITY_KINDS = ("C",)


def group_fingerprints(run_dir: Path, artifact_kind: str = "raw") -> Dict[str, Any]:
    """大格之 §G 值指紋（群組粒度；SPEC §G）：以 manifest 宣告之群組檔為單位，每群組之 `dtype`／`nan`／`values`／
    `values_native` 為該群組各欄（依檔內欄序）之欄名與逐欄同定義位元組（`fingerprints` 之 float32 NaN 遮罩、NaN→0 之
    float32 值、`values_native_sha256`）串接之 sha256；表層 `column_set_sha256`／`column_order_sha256` 同 `fingerprints`。
    鍵與 `bitwise_diff` 相容（`columns` 之鍵為群組檔相對路徑）；任一欄之值、NaN、dtype、欄名或欄序改變 ⇒ 所屬群組或表層
    雜湊改變。無斷言。"""
    import pyarrow.parquet as pq

    from tests.feature_engineering import preprov_helpers as ph

    groups: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for path in ph.declared_group_files(Path(run_dir), artifact_kind):
        table = pq.read_table(str(path))
        digests = {key: hashlib.sha256() for key in ("dtype", "nan", "values", "values_native")}
        names: List[str] = []
        for name in table.column_names:
            if name in ph.NON_FEATURE_COLUMNS:
                continue
            native = np.asarray(table.column(name).to_numpy(zero_copy_only=False))
            label = str(name).encode("utf-8") + b"\x00"
            arr = np.asarray(native, dtype=np.float32)
            nan = np.isnan(arr)
            digests["dtype"].update(label + str(table.schema.field(name).type).encode("utf-8") + b"\n")
            digests["nan"].update(label + np.packbits(nan).tobytes())
            digests["values"].update(label + np.where(nan, np.float32(0), arr).tobytes())
            digests["values_native"].update(label + bytes.fromhex(values_native_sha256(native)))
            names.append(str(name))
        rel = str(Path(path).resolve().relative_to(Path(run_dir).resolve()))
        groups[rel] = {**{key: d.hexdigest() for key, d in digests.items()}, "column_count": len(names)}
        order += names
    if len(order) != len(set(order)):
        raise AssertionError(f"{run_dir}/{artifact_kind}：宣告群組間有重複欄")
    return {"columns": groups, "granularity": "group", "column_count": len(order),
            "column_set_sha256": _column_set_sha256(order), "column_order_sha256": column_order_sha256(order)}


def _main(argv: Sequence[str]) -> int:
    if list(argv) == ["core-selector"]:
        print(core_selector())
        return 0
    print("用法: python -m tests.feature_engineering.numview_helpers core-selector", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
