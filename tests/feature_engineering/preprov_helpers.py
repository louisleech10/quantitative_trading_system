"""FFDSTAR／PRE-PROV（docs/FFDSTAR_SPEC.md §G、§V、Task 1.1–3.2）驗收共用 helper。

- 設定格 `CELLS`（§V 格子）與變體 `VARIANTS`（單一 Task 邊界專用、不屬 §V 全格）：真實 kline
  （`data_cache/feature_klines/kline_cache.h5`）短窗；禁合成 fixture。
- `generate_short_run`：單格真實生成；一切寫入（features 根、registry、CGSA 工作目錄、d* 快取、系統暫存、cwd）
  隔離於 `root` 之下，結束不刪（供同模組重用；pytest tmp 目錄由 pytest 回收）。
- 依 manifest 宣告讀取（Task 1.6）：`declared_feature_files` 只認 `groups[*].path` 與 row index 宣告；
  artifact 目錄下有未宣告之 parquet ⇒ 拋錯（不靜默忽略）。
- 獨立 oracle（§V「皆不讀紀錄自證」）：`independent_content_sha256` 依契約 `content_sha256._doc` 自讀檔重算，
  **不得** import／呼叫 `momentum.FeatureEngineering.run_provenance`；`independent_winsorize` 以 pandas rolling
  獨立重算縮尾；`d` 之重算於測試端以 `FeaturePreprocessor._frac_diff_ffd`（SPEC §V ② 指定）為之。
- 觀測器（observer）：生成期間以 monkeypatch 包住生產函式（只記錄、原樣轉呼叫），取得「L6.5 前值」、fracdiff
  之輸入與參數、L7 dead-drop 剔除欄、native 成功／回退群組、IC 呼叫參數等獨立於紀錄之事實；多標的 worker
  路徑之子行程觀測不到（該格只做不依賴觀測器之 oracle）。

契約值集一律讀 `momentum/FeatureEngineering/contracts/run_provenance.json`，本檔不列舉狀態值；唯一例外為
SPEC 正文以字面點名之值（`SPEC_NAMED_VALUES`），使用前一律先斷言其屬於契約值集。
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import icfirstalign_helpers as ich
from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR, REPO, WINDOW

CONTRACT_PATH: Path = REPO / "momentum" / "FeatureEngineering" / "contracts" / "run_provenance.json"
GOLDEN_DIR: Path = REPO / "tests" / "_golden" / "preprov"
PRE_CHANGE_FINGERPRINTS_PATH: Path = GOLDEN_DIR / "pre_change_fingerprints.json"
OUTPUT_SIZE_PATH: Path = GOLDEN_DIR / "output_size.json"
MANIFEST_NAME = "feature_manifest.json"
KLINE_FILE = Path(KLINE_DIR) / "kline_cache.h5"
NON_FEATURE_COLUMNS = frozenset({"timestamp", "__index_level_0__", "index"})

#: 生成之固定環境（同 PROBEWINSOR 之 FIXED_ENV：單行程、可重現）
FIXED_ENV: Dict[str, str] = {
    "FFACT_LAYER1_PARALLEL": "0",
    "FFACT_USE_POLARS": "1",
    "FFACT_L3_PERSIST_MODE": "streaming",
    "FFACT_MULTI_TF_PARALLEL": "0",
}

#: SPEC 正文以字面點名之值（鍵 → (契約值集路徑, 字面, SPEC 出處)）；使用前以 `spec_named` 斷言屬於契約值集
SPEC_NAMED_VALUES: Dict[str, Tuple[str, str, str]] = {
    "winsor_applied": ("step_status_values.winsorization", "applied", "docs/FFDSTAR_SPEC.md:170 §V oracle ③"),
    "terminal_ratio_unsafe": ("terminal_values", "ratio_unsafe", "docs/FFDSTAR_SPEC.md:170 §V oracle ③"),
    "post_ic_arm_polars": ("group_arm_values", "polars", "docs/FFDSTAR_SPEC.md:95 Task 1.4 驗證①"),
    # SPEC v4 §V replace 格：「numba 快速臂、shard 串流」須於驗收實際產出
    "shard_stream_arm": ("group_arm_values", "numba_shard", "docs/FFDSTAR_SPEC.md:169 §V replace 格"),
    "numba_fast_arm": ("group_arm_values", "numba_fast", "docs/FFDSTAR_SPEC.md:169 §V replace 格"),
}

#: SPEC 以語意點名而未給字面之值（鍵 → (契約 `named_values` 物件之鍵, 須屬之值集, SPEC 出處)）。
#: 契約約定（Task 1.1 填入）：`named_values` 為 {語意鍵: 值字面}；「須屬之值集」＝`steps`（屬每個步驟狀態值集）、
#: 值集路徑（屬該值集），或 None（事件值，只驗 `value_pattern`）。契約未填 ⇒ `contract_named` 拋 AssertionError
#: （依賴之驗收於 Task 1.1 前必紅，設計如此）。
CONTRACT_NAMED_VALUES: Dict[str, Tuple[str, Optional[str], str]] = {
    # 前處理總開關關閉（不建前處理器）⇒ writer 對全部欄全部步驟記之值
    "preprocessing_master_off": ("preprocessing_master_off", "steps", "docs/FFDSTAR_SPEC.md:62 盤點輸入①"),
    # ADF 檢定拋例外（現行以 p=1.0 續行）⇒ 逐欄紀錄 `events` 中之事件值
    "adf_test_error_event": ("adf_test_error_event", None, "docs/FFDSTAR_SPEC.md:76 Task 1.2 改法；§N FFDSTAR-R3"),
}

#: 平穩化決策欄（契約 record_columns 之子集；SPEC Task 1.1 邊界③、§K K-2 040）
STATIONARITY_DECISION_COLUMNS: Tuple[str, ...] = (
    "adf_pvalue", "n", "calibration_start", "calibration_end", "fracdiff", "d", "adf_differenced", "dstar_source",
)


# ---------------------------------------------------------------------------------------------- 契約

def contract() -> Dict[str, Any]:
    """契約 JSON（直接讀檔；不經 `run_provenance.load_contract`，後者為受測物）。"""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def enum_paths(spec: Optional[Mapping[str, Any]] = None) -> List[str]:
    """契約全部封閉值集之路徑（各步驟狀態、終態、d* 來源、群組臂、群組狀態、群組回退）。"""
    spec = spec or contract()
    return [f"step_status_values.{s}" for s in spec["steps"]] + [
        "terminal_values", "dstar_source_values", "group_arm_values", "group_status_values", "fallback_values"]


def enum_node(path: str, spec: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
    node: Any = spec or contract()
    for part in path.split("."):
        node = node[part]
    return node


def contract_values(path: str, spec: Optional[Mapping[str, Any]] = None) -> List[str]:
    """值集路徑（如 `step_status_values.winsorization`）之值清單。"""
    return list(enum_node(path, spec)["values"])


def record_enum_columns(spec: Optional[Mapping[str, Any]] = None) -> Dict[str, str]:
    """紀錄欄 → 其值集路徑（契約 `record_columns` 中型別為 `enum:<路徑>` 者）。"""
    spec = spec or contract()
    return {name: str(col["type"]).split(":", 1)[1] for name, col in spec["record_columns"].items()
            if str(col["type"]).startswith("enum:")}


def spec_named(key: str, spec: Optional[Mapping[str, Any]] = None) -> str:
    """SPEC 字面點名之值；不屬契約值集 ⇒ AssertionError（契約與 SPEC 不一致須回 Task 1.1 修正）。"""
    path, value, where = SPEC_NAMED_VALUES[key]
    values = contract_values(path, spec)
    assert value in values, f"SPEC 點名之值 {value!r}（{where}）不在契約 {path}：{values}"
    return value


def contract_named(key: str, spec: Optional[Mapping[str, Any]] = None) -> str:
    """SPEC 以語意點名之值，自契約 `named_values` 讀出（不在測試寫死字面）。契約缺該鍵、值不合樣式或不屬應屬之值集
    ⇒ AssertionError（Task 1.1 未填契約前必紅）。"""
    import re

    named_key, member_of, where = CONTRACT_NAMED_VALUES[key]
    spec = spec or contract()
    named = dict(spec.get("named_values") or {})
    assert named_key in named, f"契約缺 named_values.{named_key}（{where}；Task 1.1 待填）"
    value = str(named[named_key])
    assert re.fullmatch(str(spec["value_pattern"]), value), f"named_values.{named_key}={value!r} 不合 value_pattern"
    paths = ([f"step_status_values.{s}" for s in spec["steps"]] if member_of == "steps"
             else [] if member_of is None else [member_of])
    for path in paths:
        assert value in contract_values(path, spec), f"named_values.{named_key}={value!r} 不在契約 {path}"
    return value


# ---------------------------------------------------------------------------------------------- 設定格

def _stat(training: List[str], *, fracdiff: bool, adf: bool) -> Dict[str, Any]:
    payload = fsh.stat_payload(list(training), fracdiff=fracdiff, adf=adf)
    payload["timeframes"] = {"primary": training[0], "training": list(training), "alignment_mode": "open_minus"}
    return payload


def _pp_off() -> Dict[str, Any]:
    payload = _stat(["1h"], fracdiff=False, adf=False)
    payload["preprocessing"]["enabled"] = False
    return payload


def _with_pattern(payload: Dict[str, Any]) -> Dict[str, Any]:
    """加開 L1 pattern（ratio-unsafe 類，`tests/_golden/ratiounsafe/contract.json` 之 ratio_unsafe_categories）。"""
    payload["atomic_indicators"]["pattern"] = {"enabled": True}
    return payload


def _dead_drop() -> Dict[str, Any]:
    payload = _with_pattern(_stat(["1h"], fracdiff=False, adf=False))
    payload["nan_strategy"] = {"l7_dead_feature_drop": {"enabled": True}}
    return payload


def _gaussian(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload["preprocessing"]["gaussian_normalize"] = {"enabled": True}
    return payload


def _replace(payload: Dict[str, Any]) -> Dict[str, Any]:
    """前處理 mode 改為生產預設 replace（`feature_config.py` `mode: str = "replace"`；SPEC §V 格子 🔴：replace 才走 numba
    快速臂、shard 串流等路徑）。"""
    payload["preprocessing"]["mode"] = "replace"
    return payload


#: §V 格子（逐格單行程串行）。值＝生成路徑、主週期、payload（config_override）、輸出窗與額外環境。
#: `h12h1_multi` 主週期取 1h（training 1h＋12h）：12h 群組對 1h 主軸為 compact-aligned ⇒ 走 native-tf 路徑，
#: Task 1.2 驗證②（native 成功／回退）方有可觀測之對象（同 `fftfmeta_golden_helpers.MULTI_TFS` 先例）。
CELLS: Dict[str, Dict[str, Any]] = {
    "h1_stat_on": {"path": "generate", "primary": "1h", "window": WINDOW,
                   "payload": _stat(["1h"], fracdiff=True, adf=True)},
    "h1_stat_off": {"path": "generate", "primary": "1h", "window": WINDOW,
                    "payload": _stat(["1h"], fracdiff=False, adf=False)},
    "h1_pp_off": {"path": "generate", "primary": "1h", "window": WINDOW, "payload": _pp_off()},
    "h12h1_multi": {"path": "generate", "primary": "1h", "window": WINDOW,
                    "payload": _stat(["1h", "12h"], fracdiff=True, adf=True)},
    # 多標的 worker：`FeatureFactory.run_multi_symbol` → `_worker_entry`（worker 端 generate_features 不帶起訖日 ⇒
    # 全史；故用 S2 精簡 12h 設定控時長、平穩化關閉——worker 子行程不受本檔 d* 快取導向影響，平穩化關閉方不寫專案 d* 快取）
    "multi_symbol": {"path": "worker", "primary": "12h", "window": (None, None), "symbols": ["BTCUSDT", "ETHUSDT"],
                     "payload": ich.s2_payload(["12h"])},
    "ratio_unsafe": {"path": "generate", "primary": "1h", "window": WINDOW,
                     "payload": _with_pattern(_stat(["1h"], fracdiff=False, adf=False))},
    "dead_drop": {"path": "generate", "primary": "1h", "window": WINDOW, "payload": _dead_drop()},
    "ic_first": {"path": "ic_first", "primary": "1h", "window": WINDOW, "env": dict(fsh.IC_FIRST_OFF_ENV),
                 "ic_threshold": 0.0, "cleanup_raw": True,
                 "payload": _stat(["1h"], fracdiff=False, adf=False)},
    # SPEC v4 §V replace 格（生產預設 mode）：1h 單週期平穩化開＋縮尾開（`fast_payload` 縮尾開）
    "h1_replace_stat_on": {"path": "generate", "primary": "1h", "window": WINDOW,
                           "payload": _replace(_stat(["1h"], fracdiff=True, adf=True))},
    # SPEC v4 §V replace 格：1h 主＋12h 訓練週期（同 h12h1_multi，平穩化開；12h 群組走 native-tf 路徑）
    "h12h1_replace": {"path": "generate", "primary": "1h", "window": WINDOW,
                      "payload": _replace(_stat(["1h", "12h"], fracdiff=True, adf=True))},
}

#: 單一 Task 邊界專用之變體（不屬 §V 全格）；`workdir` 指定者與該格共用同一 features 根（同 run 目錄重生）。
VARIANTS: Dict[str, Dict[str, Any]] = {
    # Task 1.4 驗證③：IC 選擇為空（|IC| ≥ 2 不可能成立）
    "ic_first_empty": {**CELLS["ic_first"], "ic_threshold": 2.0, "payload": _stat(["1h"], fracdiff=False, adf=False)},
    # Task 1.4 邊界②：post-IC gaussian 開啟
    "ic_first_gaussian": {**CELLS["ic_first"], "payload": _gaussian(_stat(["1h"], fracdiff=False, adf=False))},
    # §V oracle ⑤：與 ic_first 同 features 根、同設定之「只重生特徵」（不跑 IC、不清 raw）
    "ic_first_features": {"path": "generate", "primary": "1h", "window": WINDOW, "env": dict(fsh.IC_FIRST_OFF_ENV),
                          "workdir": "ic_first", "payload": _stat(["1h"], fracdiff=False, adf=False)},
    # Task 1.2 驗證②：h12h1_multi 之 native 回退案（native 載入少一列 ⇒ 生產既有之 row mismatch 回退分支）
    "h12h1_native_fallback": {**CELLS["h12h1_multi"], "payload": _stat(["1h", "12h"], fracdiff=True, adf=True),
                              "native_fallback": True},
    # Task 1.2 群組 fallback 多重有序（審查 r7 CODEX-R7-P2-02）：同 h12h1_native_fallback（native 載入少一列 ⇒ native
    # 回退）＋ slow path worker 數固定 2、且 owner 每次 parallel fracdiff 嘗試於入口注入一般例外 ⇒ 生產既有之
    # parallel→serial 回退；同一 12h 群組依序經歷兩種回退（native 先、fracdiff 串行後）
    "h12h1_native_fallback_parallel_fail": {**CELLS["h12h1_multi"],
                                            "payload": _stat(["1h", "12h"], fracdiff=True, adf=True),
                                            "native_fallback": True, "parallel_fail": True},
    # SPEC v4 §V replace 格之 shard 串流臂：同 h1_replace_stat_on，但本次生成內 CGSA 分片目標
    # （`hardware_utils.get_cgsa_shard_bytes`，生產下限 32 MiB）壓為 64 KiB ⇒ 真實短窗之寬群組（每欄約數 KB）被切成
    # 多分片，raw 串流走 `_stream_sharded_group_to_sink`。分片目標非設定項（不入 config_hash），值須與未分片之
    # h1_replace_stat_on 逐位元相同（驗證 08）
    "h1_replace_sharded": {**CELLS["h1_replace_stat_on"], "payload": _replace(_stat(["1h"], fracdiff=True, adf=True)),
                           "shard_bytes": 64 * 1024},
}


def cell_spec(cell: str) -> Dict[str, Any]:
    if cell in CELLS:
        return copy.deepcopy(CELLS[cell])
    if cell in VARIANTS:
        return copy.deepcopy(VARIANTS[cell])
    raise KeyError(f"未知之格：{cell}（CELLS={sorted(CELLS)}、VARIANTS={sorted(VARIANTS)}）")


def cell_symbols(cell: str) -> List[str]:
    """該格之標的（worker 格為兩標的，其餘 BTCUSDT）。"""
    return list(cell_spec(cell).get("symbols") or ["BTCUSDT"])


# ---------------------------------------------------------------------------------------------- 執行把手與觀測

@dataclasses.dataclass(frozen=True)
class RunHandle:
    run_dir: Path
    features_root: Path
    symbol: str
    tf: str
    config_hash: str


@dataclasses.dataclass
class Observation:
    """生成期間觀測器所記錄之事實（皆非紀錄檔內容）。"""

    cell: str
    preprocessors: List[Any] = dataclasses.field(default_factory=list)
    raw_writer: Dict[str, Any] = dataclasses.field(default_factory=dict)
    l65_inputs: Dict[str, Tuple[List[str], np.ndarray, str, str]] = dataclasses.field(default_factory=dict)
    fracdiff: Dict[Tuple[str, str], Dict[str, Any]] = dataclasses.field(default_factory=dict)
    #: replace 模式下被平穩化步驟（fracdiff／ADF 差分）就地改值之輸入欄：{(原生週期, L6.5 所見欄名): 步驟方法名}；
    #: 以步驟前後值直接比對而得（非紀錄）。append 模式恆空（原欄不改、另增衍生欄）
    replaced: Dict[Tuple[str, str], str] = dataclasses.field(default_factory=dict)
    l7_dropped: Dict[str, str] = dataclasses.field(default_factory=dict)
    native_groups: Dict[str, bool] = dataclasses.field(default_factory=dict)
    native_shortened: Set[str] = dataclasses.field(default_factory=set)
    #: parallel_fail 變體：群組 id → 該群組於 owner 轉換中被注入失敗之 parallel fracdiff 嘗試次數（依實際發生計數）
    parallel_failures: Dict[str, int] = dataclasses.field(default_factory=dict)
    #: 進入 shard 串流路徑（`_stream_sharded_group_to_sink`）之群組 id → 進入時該群組之分片數（依實際呼叫記錄）
    shard_streams: Dict[str, int] = dataclasses.field(default_factory=dict)
    post_ic: List[Tuple[Any, List[str]]] = dataclasses.field(default_factory=list)
    ic_calls: List[Tuple[Tuple[Any, ...], Dict[str, Any]]] = dataclasses.field(default_factory=list)
    result_metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    config: Any = None

    @property
    def l65_preprocessor(self) -> Any:
        """L6.5 串流寫入端所用之前處理器（writer 之 `preprocessor` 參數；前處理總開關關閉為 None）。"""
        return self.raw_writer.get("preprocessor")


_OBSERVATIONS: Dict[str, Observation] = {}


def observation(handle: RunHandle) -> Observation:
    """該 run 最近一次生成之觀測（同一行程內）；無 ⇒ KeyError。"""
    key = str(handle.run_dir)
    if key not in _OBSERVATIONS:
        raise KeyError(f"無觀測紀錄（須於同一行程內以 generate_short_run 生成）：{key}")
    return _OBSERVATIONS[key]


def _isolate(mp: pytest.MonkeyPatch, work: Path, spec: Mapping[str, Any]) -> Path:
    """寫入隔離（同 `probewinsor_helpers.isolated` 之語意，但結束不刪 work）；回傳 features 根。"""
    import tempfile

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from tests.feature_engineering.probewinsor_helpers import tracked_config_files

    work.mkdir(parents=True, exist_ok=True)
    if not (work / "config").exists():
        (work / "config").mkdir()
        for rel in tracked_config_files():  # 只連結受版控之設定檔（本機未追蹤設定不得進入生成）
            (work / rel).symlink_to(REPO / rel)
    for name in ("sys_tmp", "dstar_cache"):
        (work / name).mkdir(exist_ok=True)
    env = {**FIXED_ENV, **dict(spec.get("env") or {}),
           "FFACT_FEATURE_REGISTRY_PATH": str(work / "features" / "registry.json"),
           "FFACT_CGSA_WORK_DIR": str(work / "cgsa_work")}
    for key, value in env.items():
        mp.setenv(key, value)
    worker = spec["path"] == "worker"
    if worker:  # 兩標的 worker 不得共用單一 CGSA 目錄（同 test_icfirstalign_domain 之 run_multi_symbol 案）
        mp.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    mp.chdir(work)
    mp.setattr(tempfile, "tempdir", str(work / "sys_tmp"))
    dstar = work / "dstar_cache"
    mp.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: dstar))
    return work / "data_cache" / "features" if worker else work / "features"


def _install_parallel_failure(mp: pytest.MonkeyPatch, obs: Observation) -> None:
    """parallel_fail 變體：slow path worker 數固定 2；owner 之群組轉換入口（單群組／分塊／分片三條路徑，皆以
    (registry, group, ...) 為前兩參數）記當前群組 id；`_apply_fractional_differencing_parallel` 於群組轉換內被呼叫
    （＝生產已依 n_jobs>1 且 ≥2 欄可轉換而選 parallel 臂）⇒ 計該群組失敗次數並於入口拋一般（可降級）例外，由生產既有
    之 except 分支回退串行（`feature_preprocessor.py:3780` 附近）。入口即拋 ⇒ 失敗嘗試未寫任何紀錄（撤回語意由驗證 05
    另驗）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    stack: List[str] = []
    mp.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self: 2)

    def tracked(name: str) -> None:
        orig = getattr(FeaturePreprocessor, name)

        def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
            group = args[1] if len(args) > 1 else kwargs["group"]
            stack.append(str(getattr(group, "group_id")))
            try:
                return orig(self, *args, **kwargs)
            finally:
                stack.pop()

        mp.setattr(FeaturePreprocessor, name, wrapped)

    for name in ("_transform_single_group_to_arrays", "_stream_single_group_chunked_to_sink",
                 "_stream_sharded_group_to_sink"):
        tracked(name)
    orig_parallel = FeaturePreprocessor._apply_fractional_differencing_parallel

    def failing_parallel(self: Any, *args: Any, **kwargs: Any) -> Any:
        if not stack:
            return orig_parallel(self, *args, **kwargs)
        obs.parallel_failures[stack[-1]] = obs.parallel_failures.get(stack[-1], 0) + 1
        raise RuntimeError(f"injected parallel fracdiff failure in group {stack[-1]}")

    mp.setattr(FeaturePreprocessor, "_apply_fractional_differencing_parallel", failing_parallel)


def _install_observers(mp: pytest.MonkeyPatch, obs: Observation, *, native_fallback: bool,
                       parallel_fail: bool = False) -> None:
    """觀測器：只記錄、原樣轉呼叫生產函式（不改任何回傳值；native 回退與 parallel 失敗變體除外）。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.FeatureEngineering.utils import dead_feature_filter as dff

    orig_writer = FeatureStorage.write_raw_from_registry_stream

    def writer(self: Any, *args: Any, **kwargs: Any) -> Any:
        obs.raw_writer = {"preprocessor": kwargs.get("preprocessor"), "row_slice": kwargs.get("row_slice"),
                          "row_index": kwargs.get("row_index"), "dead_drop_min_valid": kwargs.get("dead_drop_min_valid")}
        return orig_writer(self, *args, **kwargs)

    mp.setattr(FeatureStorage, "write_raw_from_registry_stream", writer)

    orig_capture = FeatureFactory._capture_stationarity_decisions

    def capture(self: Any, preprocessor: Any, config: Any = None) -> Any:
        obs.preprocessors.append(preprocessor)
        return orig_capture(self, preprocessor, config)

    mp.setattr(FeatureFactory, "_capture_stationarity_decisions", capture)

    orig_sink = FeaturePreprocessor.transform_registry_groups_to_sink

    def sink(self: Any, registry: Any, sink_fn: Any, n_workers: int = 1) -> Any:
        if registry is not None:  # L6.5 前值（registry 對齊至主軸之列；寫入端之 row_slice 另記）
            for group_id, group in registry.iter_all():
                cols = [str(c) for c in group.columns]
                arr = np.array(registry.load_data(str(group_id)), dtype=np.float32, copy=True)
                layer = getattr(group.layer, "value", group.layer)  # LayerSource（str Enum）→ "L1" 等
                obs.l65_inputs[str(group_id)] = (cols, arr, str(group.timeframe), str(layer))
        return orig_sink(self, registry, sink_fn, n_workers=n_workers)

    mp.setattr(FeaturePreprocessor, "transform_registry_groups_to_sink", sink)

    orig_native = FeaturePreprocessor._maybe_run_native_l65_to_sink

    def native(self: Any, registry: Any, group: Any, sink_fn: Any) -> Any:
        out = orig_native(self, registry, group, sink_fn)
        if getattr(group, "alignment", None) is not None:
            obs.native_groups[str(getattr(group, "group_id"))] = out is not None
        return out

    mp.setattr(FeaturePreprocessor, "_maybe_run_native_l65_to_sink", native)

    orig_sharded = FeaturePreprocessor._stream_sharded_group_to_sink

    def sharded(self: Any, registry: Any, group: Any, *args: Any, **kwargs: Any) -> Any:
        obs.shard_streams[str(getattr(group, "group_id"))] = len(tuple(getattr(group, "shards", ()) or ()))
        return orig_sharded(self, registry, group, *args, **kwargs)

    mp.setattr(FeaturePreprocessor, "_stream_sharded_group_to_sink", sharded)

    pending: Dict[Tuple[int, str], np.ndarray] = {}
    lock = threading.Lock()
    orig_assign = FeaturePreprocessor.__dict__["_assign_fracdiff_result"].__func__

    def assign(result: pd.DataFrame, column: str, fracdiff_series: pd.Series, mode: str) -> None:
        with lock:  # fracdiff 之輸入＝套用時該欄之值（縮尾後、fracdiff 前）
            pending[(threading.get_ident(), str(column))] = np.array(result[column], dtype=np.float64, copy=True)
        return orig_assign(result, column, fracdiff_series, mode)

    mp.setattr(FeaturePreprocessor, "_assign_fracdiff_result", staticmethod(assign))

    orig_register = FeaturePreprocessor._register_derived_calibration

    def register(self: Any, column: str, d_star: float, *, max_lag: int, weight_threshold: float) -> Any:
        tf = str(self._decision_timeframe_for(str(column)))
        with lock:
            values = pending.pop((threading.get_ident(), str(column)), None)
        if values is not None:
            obs.fracdiff[(tf, str(column))] = {"input": values, "max_lag": int(max_lag),
                                               "weight_threshold": float(weight_threshold),
                                               "mode": str(self.mode), "applied_d": float(d_star)}
        return orig_register(self, column, d_star, max_lag=max_lag, weight_threshold=weight_threshold)

    mp.setattr(FeaturePreprocessor, "_register_derived_calibration", register)

    def watch_replacement(name: str) -> None:
        """平穩化步驟（DataFrame 入出）前後逐欄比值：輸出中同名欄之值（NaN 視為相同）不同於輸入者記為就地改值。"""
        orig_step = getattr(FeaturePreprocessor, name)

        def step(self: Any, df: pd.DataFrame, *args: Any, **kwargs: Any) -> Any:
            out = orig_step(self, df, *args, **kwargs)
            if isinstance(out, pd.DataFrame):
                for column in df.columns:
                    if column in out.columns and not np.array_equal(
                            np.asarray(df[column], dtype=np.float64), np.asarray(out[column], dtype=np.float64),
                            equal_nan=True):
                        with lock:
                            obs.replaced[(str(self._decision_timeframe_for(str(column))), str(column))] = name
            return out

        mp.setattr(FeaturePreprocessor, name, step)

    for name in ("_apply_fractional_differencing", "_apply_adf_differencing"):
        watch_replacement(name)

    orig_mask = dff.dead_column_mask

    def dead_mask(array: Any, min_valid_samples: int = 100) -> Any:
        mask = orig_mask(array, min_valid_samples=min_valid_samples)
        frame = sys._getframe(1).f_locals
        names = frame.get("columns_list")
        if names is not None and len(names) == np.asarray(array).shape[1]:  # 只記 L7 串流寫入端
            group = str(frame.get("source_group_id") or frame.get("group_id") or "")
            for name, dead in zip(names, np.asarray(mask)):
                if bool(dead):
                    obs.l7_dropped[str(name)] = group
        return mask

    mp.setattr(dff, "dead_column_mask", dead_mask)

    orig_selected = FeaturePreprocessor.transform_selected

    def selected(self: Any, selected_cols: List[str], groups: Any, config: Any = None, arm: Any = None) -> Any:
        obs.post_ic.append((self, [str(c) for c in selected_cols]))
        return orig_selected(self, selected_cols, groups, config, arm=arm)

    mp.setattr(FeaturePreprocessor, "transform_selected", selected)

    orig_ic = ICEngine.compute_ic_from_l7_raw

    def ic(self: Any, *args: Any, **kwargs: Any) -> Any:
        obs.ic_calls.append((tuple(args), dict(kwargs)))
        return orig_ic(self, *args, **kwargs)

    mp.setattr(ICEngine, "compute_ic_from_l7_raw", ic)

    if native_fallback:
        orig_load_native = ColumnGroupRegistry.load_data_native

        def short_native(self: Any, group_id: str) -> np.ndarray:
            obs.native_shortened.add(str(group_id))
            return np.asarray(orig_load_native(self, group_id))[:-1]  # 列數不符 ⇒ 生產既有之回退分支

        mp.setattr(ColumnGroupRegistry, "load_data_native", short_native)

    if parallel_fail:
        _install_parallel_failure(mp, obs)


def _install_shard_target(mp: pytest.MonkeyPatch, shard_bytes: int) -> None:
    """shard 變體：CGSA 分片目標改為 `shard_bytes`（繞過生產下限 32 MiB）。`ColumnGroupRegistry._compute_shard_slices`
    於呼叫時才自 `hardware_utils` 取 `get_cgsa_shard_bytes`（惰性 import）⇒ 換模組屬性即生效；由本次生成之
    MonkeyPatch 安裝、生成結束即還原（不外溢至其他格）。"""
    from momentum.FeatureEngineering.utils import hardware_utils

    target = int(shard_bytes)
    mp.setattr(hardware_utils, "get_cgsa_shard_bytes", lambda: target)


def _dispatch(spec: Mapping[str, Any], symbol: str, kline_dir: str, features_root: Path,
              obs: Observation) -> Dict[str, Tuple[str, str]]:
    """依格之路徑生成；回傳 {標的: (週期, config_hash)}。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    payload = copy.deepcopy(spec["payload"])
    primary = str(spec["primary"])
    start, end = spec["window"]
    factory = create_feature_factory(cache_dir=kline_dir, validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    if spec["path"] == "generate":
        result = factory.generate_features(symbol, primary, config_override=payload, force_regenerate=True,
                                           start_date=start, end_date=end, persist=True)
        obs.result_metadata = dict(result.metadata or {})
        obs.config = factory._resolve_config(payload)
        return {symbol: (primary, str(result.metadata["config_hash"]))}
    if spec["path"] == "ic_first":
        from momentum.Analysis.ic_engine import ICEngine
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        config = factory._resolve_config(payload)
        obs.config = config
        result = factory.run_ic_first(symbol, primary, config, start_date=start, end_date=end,
                                      ic_engine=ICEngine({"methods": ["spearman"]}),
                                      feature_reader=FeatureReader(str(features_root)),
                                      ic_threshold=float(spec["ic_threshold"]), cleanup_raw=bool(spec["cleanup_raw"]))
        obs.result_metadata = dict(result.metadata or {})
        return {symbol: (primary, str(result.metadata["config_hash"]))}
    if spec["path"] == "worker":
        symbols = list(spec["symbols"])
        if symbol not in symbols:
            raise ValueError(f"標的 {symbol} 不屬 worker 格之標的 {symbols}")
        obs.config = factory._resolve_config(payload)
        results, errors = factory.run_multi_symbol(symbols, config_override=payload, max_workers=2,
                                                   cache_dir=kline_dir)
        if errors or sorted(results) != sorted(symbols):
            raise RuntimeError(f"多標的 worker 生成失敗：errors={errors} results={sorted(results)}")
        tf = str(payload["timeframes"]["training"][0])  # worker 以 training[0] 為生成週期（`_worker_entry`）
        obs.result_metadata = {s: dict(results[s]) for s in symbols}
        return {s: (tf, str(results[s]["config_hash"])) for s in symbols}
    raise ValueError(f"未知之生成路徑：{spec['path']}")


def _check_preconditions(cell: str, spec: Mapping[str, Any], handles: Mapping[str, RunHandle],
                         obs: Observation) -> None:
    """格之前提（fail-closed，以 RuntimeError 而非 assert）：不成立則該格之 oracle 無對象、會空轉。"""
    from momentum.FeatureEngineering.feature_naming import is_ratio_unsafe_column

    for handle in handles.values():
        if not (handle.run_dir / MANIFEST_NAME).is_file():
            raise RuntimeError(f"{cell}：run 無 manifest：{handle.run_dir}")
    if cell == "dead_drop" and not obs.l7_dropped:
        raise RuntimeError("dead_drop 格前提不成立：L7 dead-drop 未剔除任何欄")
    if cell == "ratio_unsafe" and not any(
            cols and all(is_ratio_unsafe_column(c) for c in cols) for cols, _a, _t, _l in obs.l65_inputs.values()):
        raise RuntimeError("ratio_unsafe 格前提不成立：無全為 ratio-unsafe 欄之 L6.5 群組")
    if cell in ("h12h1_multi", "h12h1_replace") and not any(obs.native_groups.values()):
        raise RuntimeError(f"{cell} 格前提不成立：無任何群組走 native-tf 路徑成功")
    expected_mode = str((spec["payload"].get("preprocessing") or {}).get("mode", ""))
    if expected_mode == "replace" and (obs.l65_preprocessor is None or str(obs.l65_preprocessor.mode) != "replace"):
        raise RuntimeError(f"{cell} 格前提不成立：L6.5 前處理器非 replace 模式")
    if spec.get("native_fallback") and not obs.native_shortened:
        raise RuntimeError("native 回退變體前提不成立：未經 native 載入（無回退對象）")
    if spec.get("parallel_fail") and not obs.parallel_failures:
        raise RuntimeError("parallel 失敗變體前提不成立：無任何群組選入 parallel fracdiff 臂（無注入對象）")
    if spec.get("shard_bytes") and not any(n > 1 for n in obs.shard_streams.values()):
        raise RuntimeError(f"{cell} 格前提不成立：無任何多分片群組經 shard 串流路徑（shard_streams={obs.shard_streams}）")
    if spec["path"] == "ic_first":
        for handle in handles.values():
            if spec.get("cleanup_raw") and (handle.run_dir / "raw").exists():
                raise RuntimeError(f"{cell}：cleanup_raw 後 raw 目錄仍在")


def _generate(root: Path, cell: str, symbol: str, kline_path: Optional[Path]) -> Dict[str, RunHandle]:
    spec = cell_spec(cell)
    if kline_path is not None and Path(kline_path).name != "kline_cache.h5":
        raise ValueError(f"kline_path 須為 kline_cache.h5 之複本：{kline_path}")
    kline_dir = str(Path(kline_path).parent) if kline_path is not None else KLINE_DIR
    workdir = str(spec.get("workdir", cell))
    work = Path(root) / workdir if spec["path"] == "worker" else Path(root) / workdir / symbol
    obs = Observation(cell=cell)
    mp = pytest.MonkeyPatch()
    try:
        features_root = _isolate(mp, work, spec)
        _install_observers(mp, obs, native_fallback=bool(spec.get("native_fallback")),
                           parallel_fail=bool(spec.get("parallel_fail")))
        if spec.get("shard_bytes"):
            _install_shard_target(mp, int(spec["shard_bytes"]))
        produced = _dispatch(spec, symbol, kline_dir, features_root, obs)
    finally:
        mp.undo()
    handles = {s: RunHandle(run_dir=features_root / s / tf / h, features_root=features_root, symbol=s, tf=tf,
                            config_hash=h)
               for s, (tf, h) in produced.items()}
    for handle in handles.values():
        _OBSERVATIONS[str(handle.run_dir)] = obs
    _check_preconditions(cell, spec, handles, obs)
    return handles


def generate_short_run(root: Path, cell: str, *, symbol: str = "BTCUSDT",
                       kline_path: Optional[Path] = None) -> RunHandle:
    """單格真實生成（force_regenerate、persist）；同 (root, cell, symbol) 必落同一 features 根（重生覆寫同 run 目錄）。

    `kline_path`：`copy_kline_with_one_bar_changed` 產生之 `kline_cache.h5` 複本（值改變之重生用）；None ⇒ 真實 kline。
    worker 格一次生成兩標的，回傳 `symbol` 之把手（另一標的之把手經 `RunCache` 取得，免重生）。"""
    return _generate(Path(root), cell, symbol, kline_path)[symbol]


class RunCache:
    """模組範圍之 lazy run 倉：同 (cell, symbol) 於本倉只生成一次（mutation 案一律另起根、不經本倉）。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._handles: Dict[Tuple[str, str], RunHandle] = {}

    def get(self, cell: str, symbol: str = "BTCUSDT") -> RunHandle:
        key = (cell, symbol)
        if key not in self._handles:
            for sym, handle in _generate(self.root, cell, symbol, None).items():
                self._handles[(cell, sym)] = handle
        return self._handles[key]

    def all_of(self, cell: str) -> List[RunHandle]:
        return [self.get(cell, s) for s in cell_symbols(cell)]


def copy_kline_with_one_bar_changed(dst_dir: Path, *, symbol: str, tf: str, when: str) -> Path:
    """複製真實 kline 至 `dst_dir/kline_cache.h5`，把 `symbol/tf` 於時點 `when`（UTC；須恰對上一根）之 close 乘 1.01。
    回傳複本路徑。只改複本；找不到恰一根或值未改變 ⇒ ValueError。"""
    import h5py

    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "kline_cache.h5"
    shutil.copy2(KLINE_FILE, dst)
    target = pd.Timestamp(when)
    target = target.tz_localize("UTC") if target.tzinfo is None else target.tz_convert("UTC")
    with h5py.File(dst, "r+") as f:
        ds = f[symbol][tf]["data"]
        arr = ds[()]
        ts = arr["timestamp"].astype("int64")
        unit = "ms" if ts.max() > 10**12 else "s"
        hits = np.flatnonzero(pd.to_datetime(ts, unit=unit, utc=True) == target)
        if hits.size != 1:
            raise ValueError(f"{symbol}/{tf} 於 {target} 須恰一根，實得 {hits.size}")
        i = int(hits[0])
        old = arr["close"][i]
        arr["close"][i] = old * arr["close"].dtype.type(1.01)
        if arr["close"][i] == old:
            raise ValueError("close 未改變")
        ds[...] = arr
    return dst


# ---------------------------------------------------------------------------------------------- manifest 宣告讀取

def load_manifest(run_dir: Path) -> Dict[str, Any]:
    return json.loads((Path(run_dir) / MANIFEST_NAME).read_text(encoding="utf-8"))


def _safe_rel(raw: Any) -> str:
    rel = Path(str(raw))
    if not str(raw) or rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"manifest 宣告路徑不安全：{raw!r}")
    return str(rel)


def row_index_rel(manifest: Mapping[str, Any], artifact_kind: str) -> Optional[str]:
    """artifact 之 row index 檔相對路徑：processed 取其節點之 `row_index`；raw 取節點（若有）否則根之 `row_index`。"""
    node = manifest["artifacts"][artifact_kind]
    ri = node.get("row_index") if isinstance(node.get("row_index"), dict) else None
    if ri is None and artifact_kind == "raw" and isinstance(manifest.get("row_index"), dict):
        ri = manifest["row_index"]
    return None if ri is None else _safe_rel(ri["path"])


def declared_feature_files(run_dir: Path, artifact_kind: str = "raw") -> List[Path]:
    """Task 1.6：特徵檔集合只自 manifest 該 artifact 節點之 `groups[*].path` 與 row index 宣告導出。
    宣告檔缺 ⇒ FileNotFoundError；artifact 目錄下有未宣告之 parquet ⇒ ValueError（不靜默忽略）。"""
    run_dir = Path(run_dir)
    manifest = load_manifest(run_dir)
    artifacts = manifest.get("artifacts") or {}
    if artifact_kind not in artifacts:
        raise FileNotFoundError(f"manifest 無 artifact {artifact_kind!r}：{run_dir}")
    groups = artifacts[artifact_kind].get("groups") or {}
    files = [run_dir / _safe_rel(info.get("path")) for info in groups.values()]
    ri = row_index_rel(manifest, artifact_kind)
    if ri is not None:
        files.append(run_dir / ri)
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"manifest 宣告之檔不存在：{missing[:5]}")
    art_dir = run_dir / artifact_kind
    if art_dir.exists():
        declared = {p.resolve() for p in files}
        undeclared = sorted(str(p) for p in art_dir.rglob("*.parquet") if p.resolve() not in declared)
        if undeclared:
            raise ValueError(f"artifact 目錄下有 manifest 未宣告之 parquet：{undeclared[:5]}")
    return files


def declared_group_files(run_dir: Path, artifact_kind: str = "raw") -> List[Path]:
    """`declared_feature_files` 去掉 row index 檔（只留群組檔）。"""
    manifest = load_manifest(run_dir)
    ri = row_index_rel(manifest, artifact_kind)
    skip = None if ri is None else (Path(run_dir) / ri).resolve()
    return [p for p in declared_feature_files(run_dir, artifact_kind) if p.resolve() != skip]


def declared_feature_files_of_run(run_dir: Path) -> List[Path]:
    """Task 1.6：run 內全部 artifact 之宣告特徵檔（`declared_feature_files` 之聯集；路徑升冪、去重）。

    artifact 目錄已整個回收者（IC-first `cleanup_raw` 刪 `raw/`，manifest 仍留該節點）：其群組檔不復存在，只列其仍在之
    row index 宣告（raw 之 row index＝run 根 `timestamps.parquet`，回收後仍在）。"""
    run_dir = Path(run_dir)
    manifest = load_manifest(run_dir)
    out = set()
    for kind, node in (manifest.get("artifacts") or {}).items():
        art_dir = run_dir / _safe_rel((node or {}).get("path") or kind)
        if art_dir.is_dir():
            out.update(declared_feature_files(run_dir, kind))
            continue
        ri = row_index_rel(manifest, kind)
        if ri is not None and (run_dir / ri).is_file():
            out.add(run_dir / ri)
    return sorted(out)


def feature_run_dirs(root: Path) -> List[Path]:
    """features 根（或 run 目錄本身）下全部 V2 run 目錄（以 manifest 定位；不列舉特徵檔）。"""
    root = Path(root)
    if (root / MANIFEST_NAME).is_file():
        return [root]
    if not root.exists():
        return []
    return sorted(m.parent for m in root.rglob(MANIFEST_NAME))


def declared_feature_files_under(root: Path) -> List[Path]:
    """Task 1.6：features 根下全部 run 之宣告特徵檔（路徑升冪；取代舊 `sorted(root.rglob("*.parquet"))`）。"""
    return sorted({p for run_dir in feature_run_dirs(root) for p in declared_feature_files_of_run(run_dir)})


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    """測試端自算之檔案 sha256（不經 `run_provenance.file_sha256`）。"""
    return _sha_file(path)


_ARROW_DTYPE = {"halffloat": "float16", "float": "float32", "double": "float64"}


def _file_dtype_summary(schema: Any, columns: Sequence[str]) -> str:
    """契約 `content_sha256.dtype_doc`（SPEC v3 Task 1.1 契約補充）：該檔各特徵欄（同 entry 之 `columns`）之 Arrow 型別
    字串去重、升冪排序後以 `|` 連接（不做 float16 等別名轉換、不以 "mixed" 代替）。"""
    return "|".join(sorted({str(schema.field(c).type) for c in columns}))


def independent_content_sha256(run_dir: Path, artifact_kind: str) -> str:
    """依契約 `content_sha256._doc` 自讀檔獨立重算 run 內容身分（SPEC Task 1.3 ③、§V oracle ④）。

    entries＝每個宣告群組檔之 [相對路徑, 檔內特徵欄名（檔內順序）, 列數, dtype 摘要, 檔案 sha256]，依相對路徑升冪；
    payload＝{"entries": [...], "row_index_sha256": <row index 檔 sha256>}；以
    json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=False) 之 UTF-8 位元組取 sha256。紀錄檔不入。
    dtype 摘要＝契約 `content_sha256.dtype_doc`：檔內各特徵欄之 Arrow 型別字串去重、升冪排序後以 `|` 連接。"""
    run_dir = Path(run_dir)
    manifest = load_manifest(run_dir)
    entries: List[List[Any]] = []
    for path in declared_group_files(run_dir, artifact_kind):
        parquet = pq.ParquetFile(str(path))
        schema = parquet.schema_arrow
        cols = [n for n in schema.names if n not in NON_FEATURE_COLUMNS]
        entries.append([str(path.relative_to(run_dir)), cols, int(parquet.metadata.num_rows),
                        _file_dtype_summary(schema, cols), _sha_file(path)])
    entries.sort(key=lambda e: e[0])
    ri = row_index_rel(manifest, artifact_kind)
    if ri is None:
        raise FileNotFoundError(f"{artifact_kind} 無 row index 宣告：{run_dir}")
    payload = {"entries": entries, "row_index_sha256": _sha_file(run_dir / ri)}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def group_columns(run_dir: Path, artifact_kind: str = "raw") -> List[str]:
    """宣告群組檔之特徵欄名（逐檔讀 schema；保留重複以供窮盡性之無重複檢查）。"""
    out: List[str] = []
    for path in declared_group_files(run_dir, artifact_kind):
        out.extend(n for n in pq.read_schema(str(path)).names if n not in NON_FEATURE_COLUMNS)
    return out


def stored_columns(run_dir: Path, names: Iterable[str], artifact_kind: str = "raw") -> Dict[str, Tuple[np.ndarray, str]]:
    """宣告群組檔中指定欄之落盤值與 arrow 型別：{欄名: (ndarray〔落盤 dtype〕, 型別字面)}。"""
    wanted = set(names)
    out: Dict[str, Tuple[np.ndarray, str]] = {}
    for path in declared_group_files(run_dir, artifact_kind):
        schema = pq.read_schema(str(path))
        cols = [n for n in schema.names if n in wanted and n not in out]
        if not cols:
            continue
        table = pq.read_table(str(path), columns=cols)
        for name in cols:
            out[name] = (np.asarray(table.column(name).to_numpy(zero_copy_only=False)),
                         _ARROW_DTYPE.get(str(schema.field(name).type), str(schema.field(name).type)))
    return out


def value_fingerprints(run_dir: Path, artifact_kind: str = "raw") -> Dict[str, Any]:
    """§G 改前基準之公開值指紋（同 `ffstat_helpers.public_fingerprints` 式＋dtype＋欄名集合）：
    {"columns": {欄: {"dtype", "nan"(float32 NaN 遮罩 packbits sha256), "values"(NaN→0 之 float32 sha256)}},
     "column_set_sha256": 排序欄名以換行連接之 sha256}。只讀 manifest 宣告之群組檔（Task 1.6）。
    `tests/_golden/preprov/pre_change_fingerprints.json` 之格式＝{"cells": {格: {標的: {artifact: 本函式輸出}}}}。"""
    columns: Dict[str, Dict[str, str]] = {}
    for path in declared_group_files(run_dir, artifact_kind):
        table = pq.read_table(str(path))
        for name in table.column_names:
            if name in NON_FEATURE_COLUMNS:
                continue
            arr = np.asarray(table.column(name).to_numpy(zero_copy_only=False), dtype=np.float32)
            nan = np.isnan(arr)
            columns[name] = {"dtype": str(table.schema.field(name).type),
                             "nan": hashlib.sha256(np.packbits(nan).tobytes()).hexdigest(),
                             "values": hashlib.sha256(np.where(nan, np.float32(0), arr).tobytes()).hexdigest()}
    names = sorted(columns)
    return {"columns": columns, "column_set_sha256": hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()}


def provenance_pointer(run_dir: Path, artifact_kind: str) -> Dict[str, Any]:
    """manifest 該 artifact 節點之 `provenance` 物件（缺 ⇒ KeyError）。"""
    return dict(load_manifest(run_dir)["artifacts"][artifact_kind]["provenance"])


def provenance_file(run_dir: Path, artifact_kind: str) -> Path:
    """紀錄檔路徑（manifest 宣告；並斷言等於契約 `files[artifact_kind]`）。"""
    pointer = provenance_pointer(run_dir, artifact_kind)
    expected = contract()["files"][artifact_kind]
    assert pointer["path"] == expected, f"manifest 紀錄檔路徑 {pointer['path']!r} ≠ 契約 {expected!r}"
    return Path(run_dir) / _safe_rel(pointer["path"])


def provenance_table(run_dir: Path, artifact_kind: str) -> pd.DataFrame:
    """測試端自讀紀錄檔（pyarrow；不經 `load_provenance_v2`／`read_provenance_table`）。"""
    return pq.read_table(str(provenance_file(run_dir, artifact_kind))).to_pandas()


def output_name(column: str, timeframe: str) -> str:
    """L6.5 所見欄名 → 落盤欄名（唯一標記實作 `feature_naming.tag_timeframe`）。"""
    from momentum.FeatureEngineering.feature_naming import tag_timeframe

    return tag_timeframe(str(column), str(timeframe))


# ---------------------------------------------------------------------------------------------- 獨立重算

def independent_winsorize(values: np.ndarray, winsor_config: Mapping[str, Any], window: int) -> np.ndarray:
    """縮尾之獨立重算（pandas rolling；不呼叫生產縮尾核心）：因果滾動界線（quantile＝線性內插分位數、
    sigma＝均值±k·樣本標準差〔ddof=1，界線取 float32〕）、min_periods＝`resolve_winsor_min_periods(window)`、
    界線未定之列保留原值、NaN 寫回、自首個有限值起 window−1 列遮為 NaN；輸出 float32。"""
    from momentum.FeatureEngineering.utils.winsor_params import resolve_winsor_min_periods

    x32 = np.asarray(values, dtype=np.float32)
    x = x32.astype(np.float64)
    series = pd.Series(x)
    min_periods = resolve_winsor_min_periods(int(window))
    rolling = series.rolling(int(window), min_periods=min_periods)
    method = str(winsor_config["method"])
    if method == "quantile":
        lower_q, upper_q = (float(q) for q in winsor_config.get("quantile_range", [0.01, 0.99]))
        lo = rolling.quantile(lower_q, interpolation="linear").to_numpy(dtype=np.float64)
        hi = rolling.quantile(upper_q, interpolation="linear").to_numpy(dtype=np.float64)
    elif method == "sigma":
        k = float(winsor_config.get("sigma_k", 3.0))
        mean = rolling.mean().to_numpy(dtype=np.float64).astype(np.float32).astype(np.float64)
        std = rolling.std(ddof=1).to_numpy(dtype=np.float64).astype(np.float32).astype(np.float64)
        lo, hi = mean - k * std, mean + k * std
    else:
        raise ValueError(f"未知縮尾方法：{method}")
    out = x.copy()
    valid = np.isfinite(lo) & np.isfinite(hi)
    out[valid] = np.clip(x[valid], lo[valid], hi[valid])
    out[np.isnan(x)] = np.nan
    finite = np.isfinite(out)
    if finite.any() and int(window) > 1:
        out[: min(int(np.argmax(finite)) + int(window) - 1, len(out))] = np.nan
    return out.astype(np.float32)


def as_stored(values: np.ndarray, dtype: str) -> np.ndarray:
    """重算值轉成落盤型別（float16／float32／float64）。"""
    return np.asarray(values, dtype=np.float32).astype({"float16": np.float16, "float32": np.float32,
                                                         "float64": np.float64}[dtype])


def bitwise_equal(a: np.ndarray, b: np.ndarray) -> bool:
    """同 dtype、同長度，NaN 位置相同且非 NaN 位置逐位元相同。"""
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype != b.dtype or a.shape != b.shape:
        return False
    na, nb = np.isnan(a), np.isnan(b)
    if not np.array_equal(na, nb):
        return False
    return bool(np.array_equal(np.where(na, 0, a).view(np.uint8), np.where(nb, 0, b).view(np.uint8)))


def l65_input_by_output(obs: Observation, *, primary_only: Optional[str] = None) -> Dict[str, Tuple[np.ndarray, str]]:
    """L6.5 前值：{落盤欄名: (L6.5 輸入列〔對齊主軸、row_slice 前〕, 原生週期)}；`primary_only` 給定時只取該週期之群組。"""
    out: Dict[str, Tuple[np.ndarray, str]] = {}
    for cols, arr, tf, _layer in obs.l65_inputs.values():
        if primary_only is not None and tf != primary_only:
            continue
        for i, col in enumerate(cols):
            out[output_name(col, tf)] = (arr[:, i], tf)
    return out


def apply_row_slice(values: np.ndarray, obs: Observation) -> np.ndarray:
    row_slice = obs.raw_writer.get("row_slice")
    return np.asarray(values)[row_slice] if row_slice is not None else np.asarray(values)


# ---------------------------------------------------------------------------------------------- 重跑失敗之回復 oracle（Task 1.3 ⑤b、Task 1.4 之 processed 版）

#: artifact → 寫入端公開入口（重跑時於入口平移 row index；不依賴寫入端內部函式名）
_WRITER_ENTRY: Dict[str, str] = {"raw": "write_raw_from_registry_stream", "processed": "write_processed"}
#: artifact → 重跑所用之格（raw：單週期平穩化關；processed：IC-first 含 cleanup_raw）
RERUN_CELL: Dict[str, str] = {"raw": "h1_stat_off", "processed": "ic_first"}
_STRICT_REFUSALS: Tuple[type, ...] = (ValueError, FileNotFoundError)


@dataclasses.dataclass(frozen=True)
class RunSnapshot:
    """run 之 artifact 狀態（逐檔 sha256；位元組相同 ⇔ sha256 相同）。

    `artifact_files`＝artifact 目錄下全部檔（含未宣告檔；相對 run 目錄 → sha256）；`row_index`＝宣告之 row index 檔
    sha256（不存在 ⇒ None）；`manifest`＝raw 取 manifest 檔全文 sha256，processed 取 manifest `artifacts.processed`
    節點正規化 JSON 之 sha256（processed 重跑時 raw 先合法重寫 manifest 之 raw 部分，故只比 processed 節點）。"""

    artifact_files: Tuple[Tuple[str, str], ...]
    row_index: Optional[str]
    manifest: Optional[str]


@dataclasses.dataclass(frozen=True)
class RerunOutcome:
    before: RunSnapshot
    after: RunSnapshot
    generation_failed: bool
    injected: Tuple[str, ...]       # 注入點實際觸發時之 config_hash（應恰一個、等於 run A）
    expected_config_hash: str
    strict_readable_after: bool
    new_axis_on_disk: bool          # 宣告 row index 路徑之檔解碼後＝重跑之新時間軸


def snapshot_run(run_dir: Path, artifact_kind: str, row_index_relpath: str) -> RunSnapshot:
    """位元組快照（非特徵讀取：須含未宣告檔，故列舉 artifact 目錄全部檔；只算 sha256、不解析內容）。"""
    run_dir = Path(run_dir)
    files: List[Tuple[str, str]] = []
    art = run_dir / artifact_kind
    if art.is_dir():
        for path in sorted(art.rglob("*")):
            if path.is_file():
                files.append((str(path.relative_to(run_dir)), _sha_file(path)))
    ri = run_dir / row_index_relpath
    manifest_path = run_dir / MANIFEST_NAME
    manifest_sha: Optional[str] = None
    if manifest_path.is_file():
        if artifact_kind == "raw":
            manifest_sha = _sha_file(manifest_path)
        else:
            node = (json.loads(manifest_path.read_text(encoding="utf-8")).get("artifacts") or {}).get(artifact_kind)
            blob = json.dumps(node, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            manifest_sha = hashlib.sha256(blob).hexdigest()
    return RunSnapshot(artifact_files=tuple(files), row_index=_sha_file(ri) if ri.is_file() else None,
                       manifest=manifest_sha)


def _strict_readable(handle: RunHandle, artifact_kind: str) -> bool:
    """`FeatureReader.load_manifest_v2(..., consumer="strict")` 讀得為完整 ⇒ True；具名拒讀 ⇒ False。
    紀錄錯誤以類別 MRO 之名稱 `ProvenanceError` 判定，不匯入被測模組 run_provenance（oracle 獨立性，test_preprov_helpers 驗證 04）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    try:
        FeatureReader(str(handle.features_root)).load_manifest_v2(handle.symbol, handle.tf, handle.config_hash,
                                                                   artifact_kind, consumer="strict")
    except _STRICT_REFUSALS:
        return False
    except Exception as exc:
        if any(cls.__name__ == "ProvenanceError" for cls in type(exc).__mro__):
            return False
        raise
    return True


def _axis_seconds(path: Path) -> Optional[np.ndarray]:
    if not Path(path).is_file():
        return None
    return np.asarray(pq.read_table(str(path)).column("timestamp").to_numpy(), dtype=np.int64)


def legacy_direct_axis_writer(orig_entry: Any, row_index_filename: str) -> Any:
    """mutation 用之改壞寫入端入口（包住 `orig_entry`）：寫入端失敗後把本次收到之 `row_index`（新時間軸）以 epoch 秒直寫
    run 根之 `row_index_filename`、不備份不回復，再原樣上拋（改前碼 `feature_storage.py:1138-1142`／`:1400-1405` 之行為）。
    由 mutation 測試以 `monkeypatch.setattr(FeatureStorage, <入口>, ...)` 安裝；`rerun_with_injected_failure` 之平移包裝
    疊於其外，故此處收到者即平移後之新時間軸。"""

    def entry(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return orig_entry(self, *args, **kwargs)
        except Exception:
            names = ("symbol", "tf", "config_hash")
            ident = [kwargs[n] if n in kwargs else args[i] for i, n in enumerate(names)]
            row_index = kwargs["row_index"]
            seconds = (np.asarray(row_index.view("int64"), dtype=np.int64) // 1_000_000_000).astype(np.int64)
            pq.write_table(pa.table({"timestamp": pa.array(seconds, type=pa.int64())}),
                           str(self.feature_run_dir(*ident) / row_index_filename))
            raise

    return entry


def rerun_with_injected_failure(root: Path, artifact_kind: str, *, retain_source: bool = False) -> RerunOutcome:
    """Task 1.3 ⑤b（processed 版同 Task 1.4）：先完整生成 run A，再以同設定重跑（強制重生）並於「新 row index 寫出後、
    `_atomic_merge_feature_manifest_v2`（該 artifact 之提交合併）前」注入 `OSError`。

    重跑使新舊可區分：①kline 複本改 run A 時間軸中段一根之 close（值改變、config_hash 不變 ⇒ 同 run 目錄、新特徵檔位元組
    不同）；②於寫入端公開入口把 `row_index` 整體平移一根（新時間軸）。包裝於呼叫當下之 `FeatureStorage` 入口之外
    （mutation 測試先以 `legacy_direct_axis_writer` 安裝改壞入口者，即包於其外）。

    `retain_source`（只 raw）：寫入端入口改傳 `cleanup_intermediate=False`，使來源 npy 不刪 ⇒ 走 SPEC Task 1.3 ⑥「來源未刪
    ⇒ 三者自備份回復」之分支；False＝生產預設（來源已刪 ⇒ 不回復、manifest 維持不完整）。processed 無來源刪除，恆為回復分支。"""
    if retain_source and artifact_kind != "raw":
        raise ValueError("retain_source 只適用 raw（processed 無來源刪除）")
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    root = Path(root)
    cell = RERUN_CELL[artifact_kind]
    first = generate_short_run(root, cell)
    if not _strict_readable(first, artifact_kind):
        raise RuntimeError(f"前提不成立：run A 之 {artifact_kind} 不可被 strict 讀為完整")
    rel = row_index_rel(load_manifest(first.run_dir), artifact_kind)
    if rel is None:
        raise RuntimeError(f"前提不成立：run A 之 {artifact_kind} 無 row index 宣告")
    axis = _axis_seconds(first.run_dir / rel)
    if axis is None or len(axis) < 3:
        raise RuntimeError("前提不成立：run A 之 row index 少於 3 列（無法平移／改值）")
    before = snapshot_run(first.run_dir, artifact_kind, rel)
    when = str(pd.Timestamp(int(axis[len(axis) // 2]), unit="s", tz="UTC"))
    kline = copy_kline_with_one_bar_changed(root / "kline_changed", symbol=first.symbol, tf=first.tf, when=when)

    shifted: Dict[str, np.ndarray] = {}
    injected: List[str] = []
    entry_name = _WRITER_ENTRY[artifact_kind]
    orig_entry = getattr(FeatureStorage, entry_name)
    orig_merge = FeatureStorage._atomic_merge_feature_manifest_v2

    def entry(self: Any, *args: Any, **kwargs: Any) -> Any:
        row_index = kwargs.get("row_index")
        if row_index is None or len(row_index) < 2:
            raise RuntimeError(f"前提不成立：{entry_name} 未收到可平移之 row_index")
        new_axis = row_index + (row_index[1] - row_index[0])
        shifted["seconds"] = (np.asarray(new_axis.view("int64"), dtype=np.int64) // 1_000_000_000).astype(np.int64)
        kwargs["row_index"] = new_axis
        if retain_source:
            kwargs["cleanup_intermediate"] = False
        return orig_entry(self, *args, **kwargs)

    def merge(self: Any, run_dir: Path, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get("artifact_kind") == artifact_kind and kwargs.get("group_manifest") is not None:
            injected.append(str(kwargs.get("config_hash")))
            raise OSError(f"injected {artifact_kind} manifest merge failure after new row index written")
        return orig_merge(self, run_dir, *args, **kwargs)

    mp = pytest.MonkeyPatch()
    failed = False
    try:
        mp.setattr(FeatureStorage, entry_name, entry)
        mp.setattr(FeatureStorage, "_atomic_merge_feature_manifest_v2", merge)
        generate_short_run(root, cell, kline_path=kline)
    except Exception:  # noqa: BLE001 — 注入之失敗預期使生成失敗；是否確由注入點觸發另以 injected 斷言
        failed = True
    finally:
        mp.undo()
    on_disk = _axis_seconds(first.run_dir / rel)
    new_axis_on_disk = bool(on_disk is not None and "seconds" in shifted
                            and np.array_equal(on_disk, shifted["seconds"]))
    return RerunOutcome(before=before, after=snapshot_run(first.run_dir, artifact_kind, rel), generation_failed=failed,
                        injected=tuple(injected), expected_config_hash=first.config_hash,
                        strict_readable_after=_strict_readable(first, artifact_kind),
                        new_axis_on_disk=new_axis_on_disk)


def rerun_failure_violations(outcome: RerunOutcome) -> List[str]:
    """oracle（SPEC Task 1.3 ⑤b）：重跑失敗後須「artifact 目錄、row index、manifest 三者逐位元組回復為 run A」或「run 不可被
    strict 讀為完整」；且無論何者，**不得**出現「舊特徵檔（位元組＝run A）＋新時間軸」。注入未到達 ⇒ 不成立（防空轉）。"""
    out: List[str] = []
    if not outcome.generation_failed:
        out.append("注入失敗而生成照常成功")
    if list(outcome.injected) != [outcome.expected_config_hash]:
        out.append(f"注入點未恰觸發一次於 run A 之提交合併：{list(outcome.injected)}")
    restored = outcome.after == outcome.before
    if not restored and outcome.strict_readable_after:
        out.append("未逐位元組回復為 run A，且 run 仍可被 strict 讀為完整")
    if outcome.new_axis_on_disk and outcome.after.artifact_files == outcome.before.artifact_files:
        out.append("舊特徵檔（位元組＝run A）＋新時間軸（錯配）")
    return out


# ---------------------------------------------------------------------------------------------- 前處理器紀錄存取（單一假設點）

def preprocessor_records(preprocessor: Any) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """前處理器 run 層級執行紀錄（SPEC Task 1.2「run 層級之執行紀錄容器」；鍵＝(原生週期, L6.5 所見欄名)）。
    SPEC 未命名其公開存取點；本 helper 假設為 `FeaturePreprocessor.execution_records()`（唯一假設點，改名只改此處）。"""
    return dict(preprocessor.execution_records())


def preprocessor_groups(preprocessor: Any) -> Dict[str, Dict[str, Any]]:
    """前處理器之群組轉換臂表（SPEC Task 1.2「群組轉換臂與回退、失敗群組」；值之鍵＝契約 `manifest_group_keys`）。
    SPEC 未命名其公開存取點；本 helper 假設為 `FeaturePreprocessor.execution_groups()`（唯一假設點）。"""
    return dict(preprocessor.execution_groups())


def post_ic_execution(preprocessor: Any) -> Tuple[Dict[Tuple[str, str], Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """post-IC 轉換之紀錄（SPEC Task 1.4：呼叫 `transform_selected` 之實例之 `last_post_ic_execution()`，回
    (`execution_records()` 同形, `execution_groups()` 同形)）。唯一假設點。"""
    records, groups = preprocessor.last_post_ic_execution()
    return dict(records), dict(groups)


def real_feature_frame(handle: RunHandle, max_columns: int = 12, *, layer: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """自真實 run 之宣告 raw 群組檔取若干特徵欄為 DataFrame（UTC DatetimeIndex；欄名去週期標記＝L6.5 所見名）；
    回傳 (frame, {欄: 層})。供前處理器單元案例使用（值為真實生成之特徵，非合成）。"""
    from momentum.FeatureEngineering.feature_naming import strip_timeframe_tag

    manifest = load_manifest(handle.run_dir)
    seconds = pq.read_table(str(handle.run_dir / row_index_rel(manifest, "raw"))).column("timestamp").to_numpy()
    index = pd.DatetimeIndex(pd.to_datetime(seconds, unit="s", utc=True))
    data: Dict[str, np.ndarray] = {}
    layers: Dict[str, str] = {}
    for gid, info in manifest["artifacts"]["raw"]["groups"].items():
        source = str(info.get("source_group_id") or gid)
        group_layer = source.split("_")[1] if len(source.split("_")) > 1 else ""
        if layer is not None and group_layer != layer:
            continue
        table = pq.read_table(str(handle.run_dir / _safe_rel(info["path"])))
        for name in table.column_names:
            if name in NON_FEATURE_COLUMNS or len(data) >= max_columns:
                continue
            values = np.asarray(table.column(name).to_numpy(zero_copy_only=False), dtype=np.float32)
            if not np.isfinite(values).any():
                continue
            plain = strip_timeframe_tag(name)
            data[plain] = values
            layers[plain] = group_layer
    if not data:
        raise RuntimeError(f"{handle.run_dir} 無可用之真實特徵欄（layer={layer}）")
    return pd.DataFrame(data, index=index), layers


__all__ = [
    "CELLS", "VARIANTS", "RunHandle", "RunCache", "Observation", "generate_short_run", "observation",
    "copy_kline_with_one_bar_changed", "declared_feature_files", "declared_group_files",
    "independent_content_sha256", "value_fingerprints", "provenance_table", "provenance_file", "provenance_pointer",
    "contract", "contract_values", "enum_paths", "record_enum_columns", "spec_named", "SPEC_NAMED_VALUES",
    "contract_named", "CONTRACT_NAMED_VALUES",
    "STATIONARITY_DECISION_COLUMNS", "independent_winsorize", "bitwise_equal", "as_stored", "stored_columns",
    "group_columns", "preprocessor_records", "preprocessor_groups", "post_ic_execution", "real_feature_frame",
    "load_manifest",
    "sha256_file", "row_index_rel", "output_name", "l65_input_by_output", "apply_row_slice",
    "PRE_CHANGE_FINGERPRINTS_PATH", "OUTPUT_SIZE_PATH", "GOLDEN_DIR", "CONTRACT_PATH", "WINDOW", "KLINE_DIR", "REPO",
]
