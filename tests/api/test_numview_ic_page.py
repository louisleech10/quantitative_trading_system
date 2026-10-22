"""NUMVIEW IC 頁第三步（docs/NUMVIEW_SPEC.md §C D3／D4／D5／D10、§G G1、Task 2.1 API 部分、Task 2.2、Task 3.4、
Task 4.3、設計選擇⑦、§V oracle ①⑥⑫⑮）之驗收。

經真服務路徑 `ic_analysis_service._apply_transforms_sync`（註冊假任務、`monkeypatch.chdir` 使相對路徑
`data_cache/reports` 落於 tmp；同 `tests/api/test_icpostleak_api.py`）。特徵來源一律真實 kline：輕量案以
`ffname_helpers.write_canonical_run` 寫真實 BTCUSDT 1h kline 欄（icpostleak 契約 `kline`）之 canonical run；
G1 案以凍結腳本接縫重生 §V 格 A；Task 4.3 ③以 `preprov_helpers.generate_short_run` 生成並於隔離 kline 複本改一根重生。
h5 屬性鍵與回應鍵一律讀契約 `ic_page_output_attrs`／`ic_page_response_keys`（未填即紅）。

**契約狀態感知（Task 2.2 與 Task 3.4 之 SPEC 矛盾）**：Task 2.2 存活至「本票交付後保留」，但其驗證①②、邊界②
（Polars 不可用 ⇒ 靜默改走 pandas 並如實記錄）與 mutation 於 Task 3.4 鎖臂後不再成立（IC 頁恆走 Polars、
Polars 不可用 ⇒ `PostICArmUnavailableError`）。故 Task 2.2 之測試讀契約 `post_ic_entries.ic_page_apply_transforms`：
有 `arm_policy`（Task 3.4 前）⇒ 斷言 Phase 2 語意（各臂份輸出＝G1 同臂份、記錄臂＝標示臂、Polars 不可用 ⇒ 記 pandas 臂且
輸出＝同環境 pandas 輸出）；有 `arm_ref`（須＝`ic_first`；Task 3.4 後）⇒ 斷言鎖臂語意（各環境記錄臂＝`post_ic_arm`、
輸出＝鎖定臂參照、Polars 不可用 ⇒ 具名錯誤且無輸出檔）；兩者皆無 ⇒ 紅。兩支皆有實質斷言；mutation 依當下狀態設計使之翻轉
（鎖臂狀態下「記臂寫契約政策值」以偽造執行紀錄臂使記錄≠執行而翻轉）。

驗證：
- Task 2.1 API：`zscore=true` 且 `zscore_windows=[]` ⇒ 422（FastAPI TestClient 打真路由；服務不被呼叫），模型層亦驗證錯。
- Task 2.2：①G1 每格每個已凍結臂份之環境下 IC 頁輸出（依契約狀態）逐位元比對；②h5 屬性與回應之記錄臂（依契約狀態），且
  ＝獨立擷取之執行紀錄臂；③h5 `ff_run_identity`＝另行 `load_with_identity` 之身分（服務經 `load_with_identity` 載入）；
  ④`load_with_identity` 之 DataFrame＝`load` 者逐位元。邊界 26（全 ratio-unsafe ⇒ ValueError、無輸出）、27（Polars 不可用）。
  mutation：記臂寫契約政策值、記臂以環境推算（chunked 案）、IC 頁誤傳／改傳臂。
- Task 3.4（名稱皆含 `icpage_arm_locked`）：①G1 每格各環境輸出＝鎖定臂參照（Task 3.1 改 Polars 計算者以現行 Polars
  環境輸出為參照）；②被移除臂份之差異逐份列於收據且＝自凍結值重算；③各環境記錄臂＝`polars`；④Polars 不可用 ⇒
  `PostICArmUnavailableError`、無輸出檔；⑤AST：生產碼每個 `.transform_selected(` 帶 `arm=`，且 `arm` 為無預設之關鍵字專用參數；
  ⑥決定紀錄 `d_icpage_arm`：`changes_public_output=true`、`user_ruling` 為 2026-10-21 原話；⑦pandas 臂呼叫者盤點收據與
  AST 一致。邊界 37／38／39；mutation：刪 IC 頁 `arm=`、`arm` 改回可選、不可用時退回 pandas、刪除仍有呼叫者之函式。
- Task 4.3：①同請求兩次 ⇒ 同 `view_id`、同檔、內容相等；②轉換設定不同 ⇒ 不同檔、舊檔不變；③IC 後重生 run ⇒
  `ICViewIdentityMismatchError`、無輸出；④h5 `ff_run_identity`＝`load_with_identity`；⑤選欄增減或欄序不同 ⇒ 不同
  `view_id`、不同檔、舊檔不變；另 `view_id` 由測試依契約 `ic_page_view_identity` 組成獨立重算。邊界 53／54；mutation：
  比對去 `content_sha256`、檔名去 `view_id`、view 身分去 `kept_cols`、`kept_cols` 排序後入身分。

測試接縫（實作須提供；名稱為本檔之假設，見回報）：
- 契約 `ic_page_output_attrs`／`ic_page_response_keys`：{語意槽: 鍵名}，語意槽＝`arm`、`ff_run_identity`（Task 2.2）、
  `view_id`、`algorithm_id`（Task 4.3）；h5 屬性寫於檔根 `attrs`，`ff_run_identity` 屬性值為 JSON 字串（或可解析為 dict），
  `arm` 屬性與回應值為單一臂字串（IC 頁單一群組）。
- 契約 `ic_page_view_identity.components` ＝ `ic_page_view_id` 之五個關鍵字參數名；正規化＝JSON `sort_keys`、無空白、
  sha256 hex；`transform_config` 取 `create_post_ic_transform_config(...).model_dump()`（zscore 窗排序後）、`run_identity`
  取 `load_with_identity(...)[1].to_dict()`、`arm` 與 `algorithm_id` 取 h5 屬性。
- 服務取 `view_id` 時經 `numeric_view.ic_page_view_id`（模組屬性，或服務／`momentum.factories` 模組全域名）；身分經
  `run_provenance.resolve_run_identity`（`FeatureLibrary.load_with_identity` 既有實作）。
- IC 任務報告身分位置：`task_info["result"]["metadata"]["ff_run_identity"]`（既有報告 metadata 鍵）；報告缺 metadata 或身分為
  null ⇒ 依設計選擇⑦建議拒收，型別 `ICViewIdentityMismatchError`（本檔假設；設計選擇⑦待委員審）。
- `scripts/numview_freeze_baseline.py:generate_cell(root: Path, cell: Mapping, *, run_kind: str, env=None) -> preprov_helpers.RunHandle`（`cell`＝全票唯一格描述子 `{id, kind, symbol, timeframes}`；本檔取 `.run_dir`）；
  §G 凍結檔為全票唯一正規形（`test_numview_baseline.py` 檔頭：`cells.<格>.{kind, symbol, timeframes, ic_first_selected,
  g1_source_env, g1.<臂>.{env, actual_arm, fingerprint}, …}`），本檔經 `_cell_view` 轉為內部檢視。
- 收據：`handoffs/run_receipts/*-numview-pandas-arm-callers.json` ＝ {"functions": [{"name": 函式名（可含類別前綴）,
  "status": "deleted"|"kept", ...}]}；`handoffs/run_receipts/*-numview-icpage-arm-lock.json` ＝ {"cells": {格: {被移除臂:
  {"differing_columns": [...]}}}}；決定紀錄 `tests/_golden/numview/decisions.json` ＝ {"decisions": {鍵: {...,
  "changes_public_output": bool, "user_ruling": {"date": "YYYY-MM-DD", "quote": 字串或字串清單}}}}。
真實 kline；G1 與 Task 4.3 ③為重型（重生格；模組內每格至多一次）。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple

import h5py
import numpy as np
import pandas as pd
import pydantic
import pytest

from momentum.FeatureEngineering import numeric_view as nv
from momentum.FeatureEngineering import polars_adapter
from momentum.FeatureEngineering import run_provenance
from momentum.FeatureEngineering.ic_first_context import PostICArmUnavailableError
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import numview_helpers as nh
from tests.feature_engineering import preprov_helpers as ph
from tests.feature_engineering.ffname_helpers import register_canonical_run, write_canonical_run

pytestmark = [pytest.mark.requires_kline, pytest.mark.timeout(3600)]

REPO = Path(__file__).resolve().parents[2]
ICPOSTLEAK = json.loads((REPO / "tests/_golden/icpostleak/contract.json").read_text(encoding="utf-8"))
RATIOUNSAFE = json.loads((REPO / "tests/_golden/ratiounsafe/contract.json").read_text(encoding="utf-8"))
FREEZE_SCRIPT = REPO / "scripts" / "numview_freeze_baseline.py"
PANDAS_ARM_CALLERS_GLOB = "*-numview-pandas-arm-callers.json"
ICPAGE_ARM_LOCK_GLOB = "*-numview-icpage-arm-lock.json"
ENTRY = "ic_page_apply_transforms"  # SPEC 點名之入口
IC_FIRST = "ic_first"  # SPEC 點名之入口
ENV_STATE, LOCKED_STATE = "env_resolved", "locked"
#: SPEC §G G1 之臂份環境（字面見 SPEC；`pandas_chunked` 之 chunk 值須小於選欄數——輕量案選 2 欄，取 1）
ARM_ENVS: Dict[str, Dict[str, str]] = {
    "polars": {"FFACT_USE_POLARS": "1"},
    "pandas_optimized": {"FFACT_USE_POLARS": "0"},
    "pandas_legacy": {"FFACT_USE_POLARS": "0", "FFACT_L65_OPTIMIZATION_PROFILE": "legacy"},
    "pandas_chunked": {"FFACT_USE_POLARS": "0", "FFACT_L65_CHUNK_SIZE": "1"},
}
ARM_ENV_KEYS: Tuple[str, ...] = ("FFACT_USE_POLARS", "FFACT_L65_OPTIMIZATION_PROFILE", "FFACT_L65_CHUNK_SIZE")
#: Task 4.3 view 身分之組成（＝`numeric_view.ic_page_view_id` 之關鍵字參數；契約 `components` 須恰為此集合）
VIEW_COMPONENTS: Tuple[str, ...] = ("run_identity", "transform_config", "arm", "algorithm_id", "kept_cols")
#: SPEC §A 所引使用者 2026-10-21 原話（D-ICPAGE-ARM 之 user_ruling；Task 1.5 ④、Task 3.4 ⑥）
RULING_DATE = "2026-10-21"
RULING_QUOTES: Tuple[str, ...] = ("跑13-107小時這是什麼東西？這時間完全不能接受",
                                  "Ok, 你確保相關的文件和檔案有更新到最新的方向和結論")
DELETED, KEPT = "deleted", "kept"
REGEN_CELL = "h1_pp_off"  # Task 4.3 ③：前處理關（紀錄不隨值變），使身分差只在 content_sha256（前提於測試內斷言）
EXEC_MISMATCH = "記錄臂≠執行紀錄臂"
LABEL_MISMATCH = "記錄臂≠預期臂"


# ---------------------------------------------------------------------------------------------- 契約讀取

def contract_state() -> str:
    """IC 頁入口之契約狀態：`arm_policy` ⇒ Phase 2（依環境）；`arm_ref`（須指 `ic_first`）⇒ Task 3.4 鎖臂；否則紅。"""
    entry = nv.load_contract()["post_ic_entries"][ENTRY]
    if "arm_ref" in entry:
        assert entry["arm_ref"] == IC_FIRST, f"{ENTRY}.arm_ref={entry['arm_ref']!r} ≠ {IC_FIRST!r}"
        return LOCKED_STATE
    if "arm_policy" in entry:
        return ENV_STATE
    raise AssertionError(f"契約 post_ic_entries.{ENTRY} 既無 arm_policy 亦無 arm_ref：{entry!r}")


def g1_regen_kind() -> str:
    """G1 格重產之估時跑別（SPEC Task 0.4、R15-A）：Phase 2（依環境）⇒ `regen_t22`（Task 2.2，批 b3）；鎖臂後 ⇒
    `regen_t34`（Task 3.4，批 b4）。兩批各重產一次，故估時分列。判準具批次共用生成時回其所讀之批次跑別（b3／b4；
    判準檔 cell_rules.batch_cache：同批碼態內每格每環境只生成一次、全部檢查共用）。"""
    return nh.regen_batch_kind("regen_t34" if contract_state() == LOCKED_STATE else "regen_t22")


def locked_arm() -> str:
    arm = nv.post_ic_arm(IC_FIRST)
    assert arm in nv.load_contract()["post_ic_arm_values"]["values"], arm
    return arm


def attr_key(slot: str) -> str:
    key = nv.load_contract()["ic_page_output_attrs"].get(slot)
    assert isinstance(key, str) and key, f"契約 ic_page_output_attrs.{slot} 未填"
    return key


def resp_key(slot: str) -> str:
    key = nv.load_contract()["ic_page_response_keys"].get(slot)
    assert isinstance(key, str) and key, f"契約 ic_page_response_keys.{slot} 未填"
    return key


def _spec_arm(arm: str) -> str:
    """SPEC 字面之臂名使用前斷言屬契約 `post_ic_arm_values`。"""
    assert arm in nv.load_contract()["post_ic_arm_values"]["values"], arm
    return arm


# ---------------------------------------------------------------------------------------------- 服務路徑

def _service() -> Any:
    from api.services.ic_analysis_service import ic_analysis_service

    return ic_analysis_service


def _default_request(selected: List[str], **overrides: Any) -> Any:
    from api.models.ic_models import ApplyTransformsRequest

    return ApplyTransformsRequest(selected_features=list(selected), **overrides)


def _decode(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.generic):
        return value.item()
    return value


def _read_attrs(path: Path) -> Dict[str, Any]:
    with h5py.File(str(path), "r") as handle:
        return {str(k): _decode(handle.attrs[k]) for k in handle.attrs}


def report_files(cwd: Path) -> List[str]:
    reports = cwd / "data_cache" / "reports"
    return sorted(str(p.relative_to(cwd)) for p in reports.rglob("*") if p.is_file()) if reports.exists() else []


@dataclasses.dataclass
class Source:
    library: Any
    manifest: Path
    symbol: str
    tf: str
    config_hash: str
    identity: Dict[str, Any]


@dataclasses.dataclass
class PageRun:
    result: Dict[str, Any]
    output: Path
    frame: pd.DataFrame
    attrs: Dict[str, Any]
    exec_arms: Set[str]
    load_with_identity_calls: int
    cwd: Path


def task_result_for(identity: Optional[Mapping[str, Any]], *, with_metadata: bool = True) -> Dict[str, Any]:
    result: Dict[str, Any] = {"analysis_status": "ok_oos", "oos_guarantees": True}
    if with_metadata:
        result["metadata"] = {"ff_run_identity": copy.deepcopy(dict(identity)) if identity is not None else None}
    return result


def run_ic_page(*, cwd: Path, source: Source, selected: List[str], env: Mapping[str, str], task_id: str,
                task_result: Optional[Dict[str, Any]] = None, request: Any = None, register: bool = True) -> PageRun:
    """於 `cwd`（chdir）、臂環境下經真服務跑 IC 頁第三步；獨立擷取實際執行之群組臂（包住 `transform_selected`，讀其
    `last_post_ic_execution()`）與 `FeatureLibrary.load_with_identity` 呼叫數。環境、cwd、spy 結束即復原；例外原樣上拋。"""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    req = request if request is not None else _default_request(selected)
    svc = _service()
    executed: List[Set[str]] = []
    identity_calls: List[int] = []
    cwd.mkdir(parents=True, exist_ok=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(cwd)
        for key in ARM_ENV_KEYS:
            mp.delenv(key, raising=False)
        for key, value in env.items():
            mp.setenv(key, str(value))
        real_ts = getattr(FeaturePreprocessor, "transform_selected")

        def capture(self: Any, *args: Any, **kwargs: Any) -> Any:
            out = real_ts(self, *args, **kwargs)
            _records, groups = self.last_post_ic_execution()
            executed.append({str(g.get("arm")) for g in groups.values()})
            return out

        mp.setattr(FeaturePreprocessor, "transform_selected", capture)
        real_lwi = getattr(FeatureLibrary, "load_with_identity")

        def counting(self: Any, *args: Any, **kwargs: Any) -> Any:
            identity_calls.append(1)
            return real_lwi(self, *args, **kwargs)

        mp.setattr(FeatureLibrary, "load_with_identity", counting)
        mp.setattr(svc, "_feature_library", source.library)
        if register:
            svc._tasks[task_id] = {"req_features_path": str(source.manifest),
                                   "result": task_result if task_result is not None else task_result_for(source.identity)}
        try:
            result = svc._apply_transforms_sync(task_id, list(req.selected_features), req.rank, req.zscore, req.gaussian,
                                                req.rank_window, list(req.zscore_windows))
        finally:
            svc._tasks.pop(task_id, None)
        output = Path(result["output_path"])
        output = output if output.is_absolute() else cwd / output
        frame = pd.read_hdf(str(output), key="features")
        attrs = _read_attrs(output)
    return PageRun(result=dict(result), output=output, frame=frame, attrs=attrs,
                   exec_arms=set().union(*executed) if executed else set(), load_with_identity_calls=len(identity_calls),
                   cwd=cwd)


def arm_record_violations(run: PageRun, expected_arm: str) -> List[str]:
    """②：h5 屬性臂＝回應臂（②之一致）、＝獨立擷取之執行紀錄臂（EXEC_MISMATCH）、＝預期臂（LABEL_MISMATCH）。"""
    out: List[str] = []
    attr = run.attrs.get(attr_key("arm"))
    resp = run.result.get(resp_key("arm"))
    if attr is None:
        out.append("h5 缺實際臂屬性")
    if attr != resp:
        out.append(f"h5 屬性臂 {attr!r} ≠ 回應臂 {resp!r}")
    if run.exec_arms != {attr}:
        out.append(f"{EXEC_MISMATCH}：記錄 {attr!r}、執行 {sorted(run.exec_arms)}")
    if attr != expected_arm:
        out.append(f"{LABEL_MISMATCH}：記錄 {attr!r}、預期 {expected_arm!r}")
    return out


def identity_from_attr(run: PageRun) -> Dict[str, Any]:
    value = run.attrs.get(attr_key("ff_run_identity"))
    value = json.loads(value) if isinstance(value, str) else value
    assert isinstance(value, dict), f"h5 ff_run_identity 屬性非物件：{value!r}"
    return value


def identity_from_response(run: PageRun) -> Dict[str, Any]:
    value = run.result.get(resp_key("ff_run_identity"))
    value = json.loads(value) if isinstance(value, str) else value
    assert isinstance(value, dict), f"回應 ff_run_identity 非物件：{value!r}"
    return value


# ---------------------------------------------------------------------------------------------- 輕量真實來源

def light_frame(extra_columns: int = 0) -> pd.DataFrame:
    """真實 BTCUSDT 1h kline 前段（icpostleak 契約 `kline` 之 rows／columns），另可附加 kline 之其他欄（依檔內欄序取）。"""
    k = ICPOSTLEAK["kline"]
    base = fsh.kline_frame(symbol=k["symbol"], timeframe=k["timeframe"]).iloc[: k["rows"]]
    names = list(k["columns"]) + [c for c in base.columns if c not in k["columns"]][:extra_columns]
    assert len(names) == len(k["columns"]) + extra_columns, "kline 欄不足以附加"
    return base[names].astype(np.float64).copy()


def with_ratio_unsafe(frame: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """附加 ratio-unsafe 欄：名稱與 TA-Lib 函式取自 `tests/_golden/ratiounsafe/contract.json`，值以真實 kline 計算。"""
    import talib

    spec = RATIOUNSAFE["branch_columns"]["unsafe"][0]
    k = ICPOSTLEAK["kline"]
    kline = fsh.kline_frame(symbol=k["symbol"], timeframe=k["timeframe"]).loc[frame.index]
    out = frame.copy()
    out[spec["name"]] = getattr(talib, spec["fn"])(*(kline[c].to_numpy(dtype=np.float64)
                                                       for c in ("open", "high", "low", "close"))).astype(np.float64)
    return out, str(spec["name"])


def light_source(base: Path, frame: pd.DataFrame, tag: str) -> Source:
    k = ICPOSTLEAK["kline"]
    config_hash = f"cfg_{tag}"
    library, manifest = write_canonical_run(base / f"features_{tag}", frame, k["symbol"], k["timeframe"], config_hash)
    _df, identity = library.load_with_identity(k["symbol"], k["timeframe"], config_hash=config_hash)
    return Source(library, manifest, k["symbol"], k["timeframe"], config_hash, identity.to_dict())


def light_run(tmp_path: Path, source: Source, env: Mapping[str, str], *, tag: str, selected: Optional[List[str]] = None,
              request: Any = None, task_id: str = "numview_light", cwd: Optional[Path] = None) -> PageRun:
    names = selected if selected is not None else list(source.library.load(source.symbol, source.tf,
                                                                           config_hash=source.config_hash).columns)
    return run_ic_page(cwd=cwd or tmp_path / f"cwd_{tag}", source=source, selected=names, env=env, task_id=task_id,
                       request=request)


def direct_transform(frame: pd.DataFrame, env: Mapping[str, str]) -> Tuple[pd.DataFrame, List[str]]:
    """IC 頁預設請求之 post-IC 設定，直接 `transform()` 依環境分派（特徵階段同一分派點）；回傳輸出與被呼叫之臂函式。"""
    from momentum.factories import create_feature_preprocessor, create_post_ic_transform_config

    req = _default_request(list(frame.columns))
    cfg = create_post_ic_transform_config(rank=req.rank, rank_window=req.rank_window, zscore=req.zscore,
                                          zscore_windows=sorted(int(w) for w in req.zscore_windows), gaussian=req.gaussian)
    calls: List[str] = []
    with pytest.MonkeyPatch.context() as mp:
        for key in ARM_ENV_KEYS:
            mp.delenv(key, raising=False)
        for key, value in env.items():
            mp.setenv(key, value)
        for name in ("_transform_single_polars", "_transform_single"):
            real = getattr(FeaturePreprocessor, name)

            def spy(*args: Any, _n: str = name, _r: Callable[..., Any] = real, **kwargs: Any) -> Any:
                calls.append(_n)
                return _r(*args, **kwargs)

            mp.setattr(FeaturePreprocessor, name, spy)
        out = create_feature_preprocessor(cfg.model_dump()).transform(frame.copy())
    return out, calls


# ---------------------------------------------------------------------------------------------- G1 重生倉（重型）

def _frozen_cells() -> Dict[str, Dict[str, Any]]:
    """§G 凍結檔之格表（唯一讀取點）。缺檔或空 ⇒ 紅。"""
    assert nh.PRE_CHANGE_FINGERPRINTS_PATH.is_file(), f"§G 改前凍結檔不存在：{nh.PRE_CHANGE_FINGERPRINTS_PATH}"
    cells = json.loads(nh.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8")).get("cells")
    assert isinstance(cells, dict) and cells, "§G 凍結檔無 cells"
    return {cid: _cell_view(cid, cell) for cid, cell in cells.items()}


def _cell_view(cell_id: str, cell: Mapping[str, Any]) -> Dict[str, Any]:
    """凍結檔正規形（全票唯一，與 `test_numview_baseline.py` 同：`cells.<格>.{kind, symbol, timeframes, ic_first_selected,
    g1_source_env, g1.<臂>.{env, actual_arm, fingerprint}, g2, g3}`）→ 本檔檢視：`tf`（單週期格之唯一週期）、
    `g1.{source_env, selected, arms.<臂>.{env, recorded_arm〔＝actual_arm〕, fingerprint}}`。G1 所需欄缺 ⇒ 紅（fail-closed）。"""
    view = dict(cell)
    timeframes = list(cell.get("timeframes") or [])
    view["tf"] = timeframes[0] if len(timeframes) == 1 else None
    if isinstance(cell.get("g1"), Mapping):
        assert "g1_source_env" in cell and "ic_first_selected" in cell, f"§G 凍結檔格 {cell_id} 缺 g1_source_env／ic_first_selected"
        view["g1"] = {
            "source_env": dict(cell["g1_source_env"]),
            "selected": list(cell["ic_first_selected"]),
            "arms": {arm: {**copy_, "recorded_arm": copy_.get("actual_arm")}
                     for arm, copy_ in cell["g1"].items() if not str(arm).startswith("_")},
        }
    return view


def _descriptor(cell_id: str) -> Dict[str, Any]:
    """凍結格之全票唯一格描述子 `{id, kind, symbol, timeframes}`（`generate_cell` 之輸入）。"""
    cell = _frozen_cells()[cell_id]
    return {"id": cell_id, "kind": cell["kind"], "symbol": cell["symbol"], "timeframes": list(cell["timeframes"])}


def _g1(cell_id: str) -> Dict[str, Any]:
    cell = _frozen_cells().get(cell_id)
    assert isinstance(cell, dict) and isinstance(cell.get("g1"), dict), f"§G 凍結檔無格 {cell_id} 之 G1"
    g1 = cell["g1"]
    assert g1.get("arms"), f"G1 {cell_id} 無任何已凍結臂份"
    return g1


def _g1_cell_ids_at_collection() -> List[str]:
    """收集期列舉凍結檔之 G1 格（每格一參數）；檔缺或無 G1 ⇒ 單一佔位參數，於測試內斷言失敗（不 skip）。"""
    try:
        cells = json.loads(nh.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8"))["cells"]
        ids = sorted(cid for cid, c in cells.items() if isinstance(c, dict) and "g1" in c)
    except (OSError, ValueError, KeyError, TypeError):
        ids = []
    return ids or ["<frozen_g1_missing>"]


G1_CELLS = _g1_cell_ids_at_collection()


def _freeze_module() -> Any:
    spec = importlib.util.spec_from_file_location("numview_freeze_baseline", FREEZE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _library_for(run_dir: Path, registry_path: Path) -> Any:
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    register_canonical_run(run_dir / "feature_manifest.json", registry_path)
    root = run_dir.parents[2]
    return FeatureLibrary(FeatureRegistry(registry_path), FeatureStorage(str(root)), feature_reader=FeatureReader(str(root)))


def _source_of(run_dir: Path, library: Any) -> Source:
    symbol, tf, config_hash = run_dir.parent.parent.name, run_dir.parent.name, run_dir.name
    _df, identity = library.load_with_identity(symbol, tf, config_hash=config_hash)
    return Source(library, run_dir / "feature_manifest.json", symbol, tf, config_hash, identity.to_dict())


class G1Lab:
    """G1 格之重生與 IC 頁輸出倉：每格重生一次、每（格, 臂份）之 IC 頁輸出只跑一次。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._sources: Dict[str, Source] = {}
        self._pages: Dict[Tuple[str, str], PageRun] = {}

    def source(self, cell_id: str) -> Source:
        if cell_id not in self._sources:
            g1 = _g1(cell_id)
            # 批次共用生成（判準檔 cell_rules.batch_cache）：root＝共用快取根（舊判準 ⇒ 本倉隔離根）
            run_dir = Path(_freeze_module().generate_cell(nh.regen_root(self.root / f"gen_{cell_id}"),
                                                          _descriptor(cell_id),
                                                          run_kind=g1_regen_kind(),
                                                          env=dict(g1["source_env"])).run_dir)
            self._sources[cell_id] = _source_of(run_dir, _library_for(run_dir, self.root / f"registry_{cell_id}.json"))
        return self._sources[cell_id]

    def page(self, cell_id: str, arm: str) -> PageRun:
        key = (cell_id, arm)
        if key not in self._pages:
            g1 = _g1(cell_id)
            self._pages[key] = run_ic_page(cwd=self.root / "cwd" / cell_id / arm, source=self.source(cell_id),
                                           selected=list(g1["selected"]), env=g1["arms"][arm]["env"],
                                           task_id=f"numview_g1_{arm}")
        return self._pages[key]


@pytest.fixture(scope="module")
def lab(tmp_path_factory: pytest.TempPathFactory) -> G1Lab:
    return G1Lab(tmp_path_factory.mktemp("numview_ic_page_g1"))


def locked_reference(lab: G1Lab, cell_id: str) -> Dict[str, Any]:
    """鎖臂參照（Task 3.4 ①）：D-POSTIC 決定為 `polars_float64`（Task 3.1 已改 Polars 計算）⇒ 現行鎖定臂環境之輸出；
    否則 ⇒ G1 改前鎖定臂份之凍結值指紋。"""
    arm = locked_arm()
    g1 = _g1(cell_id)
    assert arm in g1["arms"], f"G1 {cell_id} 無鎖定臂 {arm} 份"
    if nh.decision("d_postic") == "polars_float64":
        return nh.frame_fingerprints(lab.page(cell_id, arm).frame)
    return g1["arms"][arm]["fingerprint"]


# ---------------------------------------------------------------------------------------------- Task 2.1（API）

def test_api_zscore_enabled_empty_windows_rejected_422(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 ①（API 入口）：`zscore=true` 且 `zscore_windows=[]` ⇒ 422，服務不被呼叫；正控制：`zscore=false` 且空窗、
    `zscore=true` 且非空窗 ⇒ 200 並各呼叫服務一次。模型層同規則（ValidationError／合法）。"""
    from fastapi.testclient import TestClient

    from api.main import app
    from api.models.ic_models import ApplyTransformsRequest
    from api.routes import ic_analysis as route

    calls: List[Dict[str, Any]] = []

    async def fake_apply(**kwargs: Any) -> Dict[str, Any]:
        calls.append(kwargs)
        return {"task_id": kwargs["task_id"], "selected_feature_count": 1, "transforms_applied": ["rank"],
                "output_path": "x.h5", "output_rows": 1, "output_cols": 1}

    monkeypatch.setattr(route.ic_analysis_service, "apply_transforms", fake_apply)
    client = TestClient(app)
    url = "/api/v1/ic/apply-transforms/numview_api"
    bad = client.post(url, json={"selected_features": ["close"], "zscore": True, "zscore_windows": []})
    assert bad.status_code == 422 and calls == []
    off = client.post(url, json={"selected_features": ["close"], "zscore": False, "zscore_windows": []})
    assert off.status_code == 200 and len(calls) == 1
    ok = client.post(url, json={"selected_features": ["close"], "zscore": True, "zscore_windows": [100]})
    assert ok.status_code == 200 and len(calls) == 2
    with pytest.raises(pydantic.ValidationError):
        ApplyTransformsRequest(selected_features=["close"], zscore=True, zscore_windows=[])
    assert ApplyTransformsRequest(selected_features=["close"], zscore=False, zscore_windows=[]).zscore_windows == []


# ---------------------------------------------------------------------------------------------- Task 2.2 驗證

@pytest.mark.parametrize("cell_id", G1_CELLS)
def test_g1_output_per_contract_state(cell_id: str, lab: G1Lab) -> None:
    """Task 2.2 ①（§G G1，每個已凍結臂份；`arm_unreachable` 者不在凍結檔、不比、不補造）：
    Phase 2（`arm_policy`）⇒ 各臂份環境下輸出逐位元＝G1 同臂份；鎖臂（`arm_ref`）⇒ 各臂份環境下輸出＝鎖臂參照。"""
    g1 = _g1(cell_id)
    state = contract_state()
    if state == ENV_STATE:
        for arm, frozen in g1["arms"].items():
            assert frozen["recorded_arm"] == arm, (cell_id, arm)
            assert nh.bitwise_diff(frozen["fingerprint"], nh.frame_fingerprints(lab.page(cell_id, arm).frame)) == [], arm
    else:
        reference = locked_reference(lab, cell_id)
        for arm in g1["arms"]:
            assert nh.bitwise_diff(reference, nh.frame_fingerprints(lab.page(cell_id, arm).frame)) == [], arm


@pytest.mark.parametrize("cell_id", G1_CELLS)
def test_g1_recorded_arm_per_contract_state(cell_id: str, lab: G1Lab) -> None:
    """Task 2.2 ②：各臂份之 h5 屬性臂＝回應臂＝獨立擷取之執行紀錄臂；且 Phase 2 ⇒＝該份標示臂，鎖臂 ⇒＝`post_ic_arm`。"""
    g1 = _g1(cell_id)
    state = contract_state()
    for arm in g1["arms"]:
        expected = arm if state == ENV_STATE else locked_arm()
        assert arm_record_violations(lab.page(cell_id, arm), expected) == [], (cell_id, arm)


@pytest.mark.parametrize("arm", sorted(ARM_ENVS))
def test_light_recorded_arm_per_contract_state(arm: str, tmp_path: Path) -> None:
    """Task 2.2 ②（輕量、四環境含 chunked）：Phase 2 ⇒ 記錄臂＝該環境之標示臂；鎖臂 ⇒＝`post_ic_arm`；皆＝執行紀錄臂。"""
    state = contract_state()
    source = light_source(tmp_path, light_frame(), arm)
    run = light_run(tmp_path, source, ARM_ENVS[arm], tag=arm)
    expected = _spec_arm(arm) if state == ENV_STATE else locked_arm()
    assert arm_record_violations(run, expected) == []


def test_response_model_declares_recorded_arm_and_identity_keys() -> None:
    """Task 2.2：`ApplyTransformsResponse` 新增之記臂與來源身分鍵（鍵名讀契約）為選填；既有欄不變。"""
    from api.models.ic_models import ApplyTransformsResponse

    fields = ApplyTransformsResponse.model_fields
    for slot in ("arm", "ff_run_identity"):
        name = resp_key(slot)
        assert name in fields and not fields[name].is_required(), name
    for name in ("task_id", "selected_feature_count", "transforms_applied", "output_path", "output_rows", "output_cols"):
        assert name in fields


def test_h5_ff_run_identity_equals_separate_load_with_identity(tmp_path: Path) -> None:
    """Task 2.2 ③：h5 屬性與回應之 `ff_run_identity` 逐鍵＝測試另行呼叫 `load_with_identity` 之身分；服務經
    `load_with_identity` 載入（呼叫數 ≥ 1）。"""
    source = light_source(tmp_path, light_frame(), "ident")
    run = light_run(tmp_path, source, ARM_ENVS["polars"], tag="ident")
    _df, identity = source.library.load_with_identity(source.symbol, source.tf, config_hash=source.config_hash)
    expected = identity.to_dict()
    assert identity_from_attr(run) == expected
    assert identity_from_response(run) == expected
    assert run.load_with_identity_calls >= 1


def test_load_with_identity_frame_bitwise_equals_load(lab: G1Lab) -> None:
    """Task 2.2 ④：格 A BTCUSDT 1h 之重生 run，`load_with_identity` 之 DataFrame 與 `load` 者逐位元相等（值指紋、欄序、索引）。"""
    hits = [cid for cid, c in _frozen_cells().items()
            if c.get("kind") == "A" and c.get("symbol") == "BTCUSDT" and c.get("tf") == "1h" and "g1" in c]
    assert len(hits) == 1, hits
    source = lab.source(hits[0])
    plain = source.library.load(source.symbol, source.tf, config_hash=source.config_hash)
    with_id, _identity = source.library.load_with_identity(source.symbol, source.tf, config_hash=source.config_hash)
    assert list(plain.columns) == list(with_id.columns) and plain.index.equals(with_id.index)
    assert nh.bitwise_diff(nh.frame_fingerprints(plain), nh.frame_fingerprints(with_id)) == []


# ---------------------------------------------------------------------------------------------- Task 2.2 邊界

def test_boundary_26_all_ratio_unsafe_selection_error_unchanged(tmp_path: Path) -> None:
    """邊界①（Task 2.2）：選欄全為 ratio-unsafe ⇒ 既有錯誤行為不變（ValueError 列出該欄）、無輸出檔（故無記臂）。"""
    frame, unsafe = with_ratio_unsafe(light_frame())
    source = light_source(tmp_path, frame, "unsafe")
    cwd = tmp_path / "cwd_unsafe"
    with pytest.raises(ValueError, match=unsafe):
        light_run(tmp_path, source, ARM_ENVS["polars"], tag="unsafe", selected=[unsafe], cwd=cwd)
    assert report_files(cwd) == []


def test_boundary_27_polars_unavailable_with_use_polars_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界②（Task 2.2）：Polars 不可用而 `FFACT_USE_POLARS=1`。Phase 2 ⇒ 現行靜默改走 pandas 臂並如實記錄（記錄臂＝執行
    紀錄臂≠polars）、輸出＝同 profile 明示 `FFACT_USE_POLARS=0` 之輸出；鎖臂 ⇒ `PostICArmUnavailableError`、無輸出檔（D10）。"""
    state = contract_state()
    source = light_source(tmp_path, light_frame(), "nopolars")
    reference = light_run(tmp_path, source, ARM_ENVS["pandas_optimized"], tag="ref") if state == ENV_STATE else None
    monkeypatch.setattr(polars_adapter, "_check_polars_available", lambda: False)
    cwd = tmp_path / "cwd_nopolars"
    if state == ENV_STATE:
        run = light_run(tmp_path, source, ARM_ENVS["polars"], tag="nopolars", cwd=cwd)
        recorded = run.attrs.get(attr_key("arm"))
        assert recorded != _spec_arm("polars")
        assert arm_record_violations(run, reference.attrs.get(attr_key("arm"))) == []
        assert nh.bitwise_diff(nh.frame_fingerprints(reference.frame), nh.frame_fingerprints(run.frame)) == []
    else:
        with pytest.raises(PostICArmUnavailableError):
            light_run(tmp_path, source, ARM_ENVS["polars"], tag="nopolars", cwd=cwd)
        assert report_files(cwd) == []


# ---------------------------------------------------------------------------------------------- Task 2.2 mutation

def _arm_rewriting_service(value_of: Callable[[], str]) -> Callable[..., Dict[str, Any]]:
    """mutant 服務方法：照常轉換與寫檔後，把 h5 屬性與回應之記錄臂改寫為 `value_of()`（於服務執行之環境內求值）。
    呼叫端以 `monkeypatch.setattr(_service(), "_apply_transforms_sync", …)` 換入。"""
    real = _service()._apply_transforms_sync

    def mutant(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        result = dict(real(*args, **kwargs))
        value = value_of()
        with h5py.File(str(result["output_path"]), "a") as handle:
            handle.attrs[attr_key("arm")] = value
        result[resp_key("arm")] = value
        return result

    return mutant


def _forge_execution_arm(monkeypatch: pytest.MonkeyPatch, arm: str) -> None:
    """注入：前處理器之 post-IC 執行紀錄回報群組臂為 `arm`（模擬實際執行之臂≠政策值）。"""
    real = getattr(FeaturePreprocessor, "last_post_ic_execution")

    def forged(self: Any) -> Any:
        records, groups = real(self)
        return records, {gid: dict(info, arm=arm) for gid, info in groups.items()}

    monkeypatch.setattr(FeaturePreprocessor, "last_post_ic_execution", forged)


def test_mutation_recorded_arm_from_contract_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 2.2）：記臂改為寫契約政策值。Phase 2 ⇒ `FFACT_USE_POLARS=0` 案記錄≠標示臂（②紅）；鎖臂 ⇒ 政策值恆
    ＝polars，故另注入執行紀錄臂≠政策值，記錄≠執行紀錄臂（②紅）。"""
    state = contract_state()
    entry = nv.load_contract()["post_ic_entries"][ENTRY]
    source = light_source(tmp_path, light_frame(), "policy")
    if state == ENV_STATE:
        policy_value, expected = str(entry["arm_policy"]), _spec_arm("pandas_optimized")
        marker = LABEL_MISMATCH
    else:
        policy_value = expected = nv.post_ic_arm(ENTRY)
        other = next(a for a in nv.load_contract()["post_ic_arm_values"]["values"] if a != policy_value)
        _forge_execution_arm(monkeypatch, other)
        marker = EXEC_MISMATCH
    monkeypatch.setattr(_service(), "_apply_transforms_sync", _arm_rewriting_service(lambda: policy_value))
    run = light_run(tmp_path, source, ARM_ENVS["pandas_optimized"], tag="policy")
    assert any(marker in v for v in arm_record_violations(run, expected))


def test_mutation_recorded_arm_inferred_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 2.2）：記臂改為讀 `FFACT_USE_POLARS`（與 profile）推算 ⇒ `pandas_chunked` 環境案翻轉（推算得
    pandas_optimized；Phase 2 ≠ 標示臂 chunked，鎖臂 ≠ 執行紀錄臂 polars）。"""
    import os

    state = contract_state()

    def inferred() -> str:
        if os.environ.get("FFACT_USE_POLARS", "1") != "0":
            return _spec_arm("polars")
        legacy = os.environ.get("FFACT_L65_OPTIMIZATION_PROFILE", "") == "legacy"
        return _spec_arm("pandas_legacy" if legacy else "pandas_optimized")

    monkeypatch.setattr(_service(), "_apply_transforms_sync", _arm_rewriting_service(inferred))
    source = light_source(tmp_path, light_frame(), "envinfer")
    run = light_run(tmp_path, source, ARM_ENVS["pandas_chunked"], tag="envinfer")
    expected = _spec_arm("pandas_chunked") if state == ENV_STATE else locked_arm()
    assert arm_record_violations(run, expected) != []


def test_mutation_ic_page_passes_wrong_arm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 2.2／§V）：Phase 2 ⇒ IC 頁傳入 `arm="polars"`，pandas 環境之輸出≠同環境參照（①之 pandas 臂份紅）；
    鎖臂 ⇒ IC 頁改傳環境臂（pandas_optimized），輸出≠鎖臂參照或拋錯（①紅）。前提：同一真實輸入之 polars 與 pandas 輸出不等。"""
    state = contract_state()
    frame = light_frame()
    polars_out, _ = direct_transform(frame, ARM_ENVS["polars"])
    pandas_out, _ = direct_transform(frame, ARM_ENVS["pandas_optimized"])
    assert nh.bitwise_diff(nh.frame_fingerprints(polars_out), nh.frame_fingerprints(pandas_out)) != [], \
        "前提不成立：polars 與 pandas 輸出相等，無從觀測換臂"
    source = light_source(tmp_path, frame, "wrongarm")
    env = ARM_ENVS["pandas_optimized"]
    reference = light_run(tmp_path, source, env, tag="ref")
    forced = _spec_arm("polars") if state == ENV_STATE else _spec_arm("pandas_optimized")
    real = getattr(FeaturePreprocessor, "transform_selected")

    def wrong_arm(self: Any, selected: Any, groups: Any, config: Any = None, **kwargs: Any) -> Any:
        kwargs["arm"] = forced
        return real(self, selected, groups, config=config, **kwargs)

    monkeypatch.setattr(FeaturePreprocessor, "transform_selected", wrong_arm)
    try:
        mutated = light_run(tmp_path, source, env, tag="mut")
    except Exception:  # noqa: BLE001 — 改壞後拒收（拋錯）亦為①翻轉
        flipped = True
    else:
        flipped = nh.bitwise_diff(nh.frame_fingerprints(reference.frame), nh.frame_fingerprints(mutated.frame)) != []
    assert flipped


# ---------------------------------------------------------------------------------------------- Task 3.4 驗證

def _assert_locked() -> str:
    assert contract_state() == LOCKED_STATE, f"Task 3.4 未落地：契約 {ENTRY} 仍為依環境政策"
    arm = locked_arm()
    assert nv.post_ic_arm(ENTRY) == arm == _spec_arm("polars")
    return arm


@pytest.mark.parametrize("cell_id", G1_CELLS)
def test_icpage_arm_locked_g1_every_env_equals_locked_reference(cell_id: str, lab: G1Lab) -> None:
    """Task 3.4 ①③：G1 每個已凍結臂份之環境下，IC 頁輸出逐位元＝鎖臂參照（改前 polars 份；Task 3.1 落地者為現行 Polars
    輸出），且記錄臂＝`polars`＝執行紀錄臂。"""
    arm_locked = _assert_locked()
    reference = locked_reference(lab, cell_id)
    for arm in _g1(cell_id)["arms"]:
        run = lab.page(cell_id, arm)
        assert nh.bitwise_diff(reference, nh.frame_fingerprints(run.frame)) == [], arm
        assert arm_record_violations(run, arm_locked) == [], arm


def _differing_columns(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
    cols_a, cols_b = before.get("columns", {}), after.get("columns", {})
    names = set(cols_a) | set(cols_b)
    return sorted(n for n in names if n not in cols_a or n not in cols_b
                  or any(cols_a[n].get(k) != cols_b[n].get(k) for k in nh.BITWISE_COLUMN_KEYS))


def test_icpage_arm_locked_removed_arm_diffs_listed_in_receipt() -> None:
    """Task 3.4 ②：被移除之臂份（G1 中非鎖定臂之份）對改前鎖定臂份之差異逐份列於收據，且＝自凍結值指紋重算之差異欄集合。"""
    arm_locked = _assert_locked()
    paths = sorted(nh.RECEIPTS_DIR.glob(ICPAGE_ARM_LOCK_GLOB))
    assert paths, f"IC 頁鎖臂收據不存在：{nh.RECEIPTS_DIR}/{ICPAGE_ARM_LOCK_GLOB}"
    receipt = json.loads(paths[-1].read_text(encoding="utf-8"))["cells"]
    compared = 0
    for cell_id, cell in _frozen_cells().items():
        arms = (cell.get("g1") or {}).get("arms") or {}
        if not arms:
            continue
        assert arm_locked in arms, cell_id
        for arm, frozen in arms.items():
            if arm == arm_locked:
                continue
            expected = _differing_columns(arms[arm_locked]["fingerprint"], frozen["fingerprint"])
            assert sorted(receipt[cell_id][arm]["differing_columns"]) == expected, (cell_id, arm)
            compared += 1
    assert compared > 0, "無任何被移除臂份可比（G1 無 pandas 臂份）"


@pytest.mark.parametrize("arm", sorted(ARM_ENVS))
def test_icpage_arm_locked_recorded_arm_polars_every_env(arm: str, tmp_path: Path) -> None:
    """Task 3.4 ③（輕量、四環境含 chunked）：記錄臂＝`polars`＝執行紀錄臂，輸出＝`FFACT_USE_POLARS=1` 之輸出。"""
    arm_locked = _assert_locked()
    source = light_source(tmp_path, light_frame(), arm)
    reference = light_run(tmp_path, source, ARM_ENVS["polars"], tag="ref")
    run = light_run(tmp_path, source, ARM_ENVS[arm], tag=arm)
    assert arm_record_violations(run, arm_locked) == []
    assert nh.bitwise_diff(nh.frame_fingerprints(reference.frame), nh.frame_fingerprints(run.frame)) == []


def unavailable_rejected(tmp_path: Path, source: Source, env: Mapping[str, str], tag: str) -> bool:
    """Task 3.4 ④ oracle：Polars 不可用（已由呼叫端注入）⇒ 拋 `PostICArmUnavailableError` 且無任何輸出檔。"""
    cwd = tmp_path / f"cwd_{tag}"
    try:
        light_run(tmp_path, source, env, tag=tag, cwd=cwd)
    except PostICArmUnavailableError:
        return report_files(cwd) == []
    except Exception:  # noqa: BLE001 — 其他型別即非具名拒收
        return False
    return False


@pytest.mark.parametrize("env_name", ["polars", "pandas_optimized"])
def test_icpage_arm_locked_polars_unavailable_named_error(env_name: str, tmp_path: Path,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.4 ④：模擬 Polars 不可用（`FFACT_USE_POLARS` 為 1 或 0）⇒ `PostICArmUnavailableError`、無輸出檔（不退回 pandas）。"""
    _assert_locked()
    source = light_source(tmp_path, light_frame(), f"unavail_{env_name}")
    monkeypatch.setattr(polars_adapter, "_check_polars_available", lambda: False)
    assert unavailable_rejected(tmp_path, source, ARM_ENVS[env_name], env_name)


def _git_py_files(*roots: str) -> List[str]:
    out = subprocess.run(["git", "ls-files", "-z", *roots], cwd=REPO, capture_output=True, check=True).stdout
    return sorted(p for p in out.decode("utf-8").split("\0") if p.endswith(".py"))


def transform_selected_call_violations() -> Tuple[List[str], Set[str]]:
    """⑤AST：`git ls-files momentum api scripts` 之 `.py` 中每個 `.transform_selected(` 呼叫須帶 `arm=` 關鍵字。
    回傳（違規之 path:line, 有呼叫之檔集合）。"""
    bad: List[str] = []
    files: Set[str] = set()
    for rel in _git_py_files("momentum", "api", "scripts"):
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "transform_selected":
                files.add(rel)
                if not any(kw.arg == "arm" for kw in node.keywords):
                    bad.append(f"{rel}:{node.lineno}")
    return bad, files


def arm_signature_violations(fn: Callable[..., Any]) -> List[str]:
    """⑤簽名：`arm` 為無預設之關鍵字專用參數（必填關鍵字）。"""
    param = inspect.signature(fn).parameters.get("arm")
    if param is None:
        return ["transform_selected 無 arm 參數"]
    out: List[str] = []
    if param.default is not inspect.Parameter.empty:
        out.append(f"arm 有預設值 {param.default!r}")
    if param.kind is not inspect.Parameter.KEYWORD_ONLY:
        out.append(f"arm 非關鍵字專用（{param.kind}）")
    return out


def test_icpage_arm_locked_transform_selected_arm_required_and_passed() -> None:
    """Task 3.4 ⑤：生產碼每個 `.transform_selected(` 帶 `arm=`（含 SPEC 所列兩處生產呼叫檔），且 `arm` 為必填關鍵字。"""
    _assert_locked()
    bad, files = transform_selected_call_violations()
    assert bad == []
    assert {"api/services/ic_analysis_service.py", "momentum/FeatureEngineering/feature_factory.py"} <= files, sorted(files)
    assert arm_signature_violations(getattr(FeaturePreprocessor, "transform_selected")) == []


def _decision_record(key: str) -> Dict[str, Any]:
    assert nh.DECISIONS_PATH.is_file(), f"決定紀錄不存在：{nh.DECISIONS_PATH}"
    record = json.loads(nh.DECISIONS_PATH.read_text(encoding="utf-8"))["decisions"][key]
    assert isinstance(record, dict), record
    return record


def test_icpage_arm_locked_decision_record_user_ruling() -> None:
    """Task 3.4 ⑥：決定紀錄 `d_icpage_arm` 之 `changes_public_output` 為 true、`user_ruling` 日期為 2026-10-21 且含 §A 所引
    兩句原話；`numview_helpers.decision` 可讀出其處置值。"""
    _assert_locked()
    record = _decision_record("d_icpage_arm")
    assert record["changes_public_output"] is True
    ruling = record["user_ruling"]
    assert ruling["date"] == RULING_DATE
    quote = ruling["quote"]
    text = "\n".join(quote) if isinstance(quote, list) else str(quote)
    for sentence in RULING_QUOTES:
        assert sentence in text, sentence
    choice = nh.decision("d_icpage_arm")
    assert isinstance(choice, str) and choice


def test_icpage_arm_locked_decision_record_re_presentation() -> None:
    """Task 3.4 施工前提／⑥（SPEC v17 §A 重新呈報條件、Task 1.5 ⑦）：決定紀錄 `d_icpage_arm` 具 `re_presentation`——日期不早於
    Task 1.1 效能基準收據之首次提交、使用者回覆逐字、所據收據存在且已提交、`confirmed_choice`＝`choice`＝鎖臂（同
    `numview_helpers.re_presentation_violations`，與 Task 1.5 ⑦ 同一判定）。缺或不合 ⇒ 本批（b4）不得施工。"""
    record = _decision_record("d_icpage_arm")
    assert nh.re_presentation_violations(record) == []
    assert record["choice"] == record["re_presentation"]["confirmed_choice"]


def test_mutation_icpage_arm_locked_re_presentation_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：決定紀錄 `d_icpage_arm` 刪 `re_presentation`（保留鎖臂、改公開輸出與 2026-10-21 user_ruling；經本檔決定紀錄
    讀取入口 `_decision_record` 注入）⇒ b4 閘之判定紅。"""
    record = {"choice": "lock", "changes_public_output": True,
              "user_ruling": {"date": RULING_DATE, "quote": list(RULING_QUOTES)}}
    monkeypatch.setattr(sys.modules[__name__], "_decision_record", lambda key: dict(record))
    assert any("缺 re_presentation" in v for v in nh.re_presentation_violations(_decision_record("d_icpage_arm")))


def _pandas_arm_callers_receipt() -> Dict[str, Any]:
    paths = sorted(nh.RECEIPTS_DIR.glob(PANDAS_ARM_CALLERS_GLOB))
    assert paths, f"pandas 臂呼叫者盤點收據不存在：{nh.RECEIPTS_DIR}/{PANDAS_ARM_CALLERS_GLOB}"
    return json.loads(paths[-1].read_text(encoding="utf-8"))


def _references(names: Set[str]) -> Dict[str, List[str]]:
    """AST：`git ls-files` 之全部 `.py` 中對各名稱之引用（屬性存取或名稱載入；定義本身不計）。"""
    refs: Dict[str, List[str]] = {n: [] for n in names}
    for rel in _git_py_files():
        try:
            tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in names and isinstance(node.ctx, ast.Load):
                refs[node.attr].append(f"{rel}:{node.lineno}")
            elif isinstance(node, ast.Name) and node.id in names and isinstance(node.ctx, ast.Load):
                refs[node.id].append(f"{rel}:{node.lineno}")
    return refs


def pandas_arm_receipt_violations() -> List[str]:
    """⑦：收據標 `deleted` 之函式零引用、標 `kept` 者至少一個引用；狀態值須屬二者。"""
    functions = _pandas_arm_callers_receipt().get("functions")
    assert isinstance(functions, list) and functions, "收據 functions 為空"
    short = {str(f["name"]).rsplit(".", 1)[-1]: str(f["status"]) for f in functions}
    refs = _references(set(short))
    out: List[str] = []
    for name, status in short.items():
        if status == DELETED and refs[name]:
            out.append(f"{name} 標已刪而仍有引用：{refs[name][:3]}")
        elif status == KEPT and not refs[name]:
            out.append(f"{name} 標保留而無任何引用")
        elif status not in (DELETED, KEPT):
            out.append(f"{name} 狀態 {status!r} 不屬 {DELETED}/{KEPT}")
    return out


def test_icpage_arm_locked_pandas_arm_callers_receipt_consistent() -> None:
    """Task 3.4 ⑦：pandas 臂呼叫者盤點收據與 AST 一致（已刪者零呼叫、保留者 ≥1 呼叫者）。"""
    _assert_locked()
    assert pandas_arm_receipt_violations() == []


# ---------------------------------------------------------------------------------------------- Task 3.4 邊界

def test_boundary_37_icpage_arm_locked_ratio_unsafe_only_error_unchanged(tmp_path: Path) -> None:
    """邊界①（Task 3.4）：鎖臂後選欄全為 ratio-unsafe ⇒ 既有錯誤行為不變（ValueError 列該欄、無輸出），各環境皆同。"""
    _assert_locked()
    frame, unsafe = with_ratio_unsafe(light_frame())
    source = light_source(tmp_path, frame, "unsafe_locked")
    for env_name in ("polars", "pandas_optimized"):
        cwd = tmp_path / f"cwd_{env_name}"
        with pytest.raises(ValueError, match=unsafe):
            light_run(tmp_path, source, ARM_ENVS[env_name], tag=env_name, selected=[unsafe], cwd=cwd)
        assert report_files(cwd) == []


def test_boundary_38_icpage_arm_locked_ic_first_empty_selection_unchanged(tmp_path_factory: pytest.TempPathFactory) -> None:
    """邊界②（Task 3.4；IC-first 入口）：IC 選擇為空 ⇒ 既有空 processed 行為不變（processed 節點 total_features=0、
    quality_status=empty_selection），臂仍記（節點與回傳 metadata 之 post_ic_arm＝`post_ic_arm("ic_first")`）；
    `transform_selected([], …, arm=鎖定臂)` 回 {} 且執行紀錄為 ({}, {})。"""
    from momentum.factories import create_post_ic_transform_config

    arm = _assert_locked()
    handle = ph.RunCache(tmp_path_factory.mktemp("numview_ic_first_empty")).get("ic_first_empty")
    node = ph.load_manifest(handle.run_dir)["artifacts"]["processed"]
    assert node["total_features"] == 0 and node["quality_status"] == "empty_selection"
    assert node["post_ic_arm"] == arm
    meta = ph.observation(handle).result_metadata
    assert meta["post_ic_arm"] == arm and meta["selected_count"] == 0
    cfg = create_post_ic_transform_config(rank=True, rank_window=252, zscore=True, zscore_windows=[100, 252], gaussian=False)
    pre = FeaturePreprocessor(cfg.model_dump())
    assert pre.transform_selected([], {}, config=cfg, arm=arm) == {}
    assert pre.last_post_ic_execution() == ({}, {})


def test_boundary_39_icpage_arm_locked_use_polars_off_still_polars(tmp_path: Path) -> None:
    """邊界③（Task 3.4）：`FFACT_USE_POLARS=0` ⇒ IC 頁仍走 Polars（記錄臂＝polars＝執行紀錄臂、輸出＝polars 環境輸出）；
    該環境變數對特徵階段照舊（直接 `transform()` 不走 Polars 臂）。"""
    arm = _assert_locked()
    frame = light_frame()
    source = light_source(tmp_path, frame, "off")
    reference = light_run(tmp_path, source, ARM_ENVS["polars"], tag="ref")
    run = light_run(tmp_path, source, ARM_ENVS["pandas_optimized"], tag="off")
    assert arm_record_violations(run, arm) == []
    assert nh.bitwise_diff(nh.frame_fingerprints(reference.frame), nh.frame_fingerprints(run.frame)) == []
    _out, calls = direct_transform(frame, ARM_ENVS["pandas_optimized"])
    assert "_transform_single_polars" not in calls and "_transform_single" in calls, calls


# ---------------------------------------------------------------------------------------------- Task 3.4 mutation

def test_mutation_icpage_arm_locked_ic_page_arm_kw_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 3.4）：刪 IC 頁 `arm=` ⇒ 必填參數 TypeError，①無輸出（紅）；未改壞前同輸入可跑出輸出。"""
    _assert_locked()
    source = light_source(tmp_path, light_frame(), "noarm")
    assert light_run(tmp_path, source, ARM_ENVS["polars"], tag="ok").output.is_file()
    real = getattr(FeaturePreprocessor, "transform_selected")

    def without_arm(self: Any, selected: Any, groups: Any, config: Any = None, **kwargs: Any) -> Any:
        kwargs.pop("arm", None)
        return real(self, selected, groups, config=config, **kwargs)

    monkeypatch.setattr(FeaturePreprocessor, "transform_selected", without_arm)
    with pytest.raises(TypeError):
        light_run(tmp_path, source, ARM_ENVS["polars"], tag="mut")


def test_mutation_icpage_arm_locked_arm_optional_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 3.4）：`arm` 改回 `Optional[str] = None` ⇒ ⑤之簽名檢查翻紅。"""
    real = getattr(FeaturePreprocessor, "transform_selected")

    def optional_arm(self: Any, selected: Any, groups: Any, config: Any = None, arm: Optional[str] = None) -> Any:
        return real(self, selected, groups, config=config, arm=arm)

    monkeypatch.setattr(FeaturePreprocessor, "transform_selected", optional_arm)
    assert arm_signature_violations(getattr(FeaturePreprocessor, "transform_selected")) != []


def test_mutation_icpage_arm_locked_fallback_to_pandas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 3.4）：臂不可用時改為退回 pandas（攔 `PostICArmUnavailableError` 改走環境分派）⇒ ④翻轉（有輸出或非具名錯誤）。"""
    _assert_locked()
    source = light_source(tmp_path, light_frame(), "fallback")
    monkeypatch.setattr(polars_adapter, "_check_polars_available", lambda: False)
    real = getattr(FeaturePreprocessor, "transform_selected")

    def fallback(self: Any, selected: Any, groups: Any, config: Any = None, **kwargs: Any) -> Any:
        try:
            return real(self, selected, groups, config=config, **kwargs)
        except PostICArmUnavailableError:
            cfg = config.model_dump() if hasattr(config, "model_dump") else dict(config or {})
            pandas_pre = FeaturePreprocessor(cfg)
            return {gid: pandas_pre.transform(df.loc[:, [c for c in selected if c in df.columns]].copy())
                    for gid, df in groups.items()}

    monkeypatch.setattr(FeaturePreprocessor, "transform_selected", fallback)
    assert not unavailable_rejected(tmp_path, source, ARM_ENVS["polars"], "fallback")


def test_mutation_icpage_arm_locked_shared_function_marked_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 3.4）：把仍有呼叫者之共用函式（`_transform_single`，特徵階段 registry 路徑與 scripts 使用）標為已刪
    ⇒ ⑦翻紅。"""
    name = "_transform_single"
    assert callable(getattr(FeaturePreprocessor, name))
    mutated = copy.deepcopy(_pandas_arm_callers_receipt())
    functions = [f for f in mutated.get("functions", []) if str(f.get("name")).rsplit(".", 1)[-1] != name]
    functions.append({"name": f"FeaturePreprocessor.{name}", "status": DELETED})
    mutated["functions"] = functions
    monkeypatch.setattr(sys.modules[__name__], "_pandas_arm_callers_receipt", lambda: mutated)
    assert any(v.startswith(name) for v in pandas_arm_receipt_violations())


# ---------------------------------------------------------------------------------------------- Task 4.3 驗證

def _view_id(run: PageRun) -> str:
    attr = run.attrs.get(attr_key("view_id"))
    assert isinstance(attr, str) and attr, f"h5 缺 view_id 屬性：{sorted(run.attrs)}"
    assert run.result.get(resp_key("view_id")) == attr
    return attr


def _sha_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_view_same_request_twice_same_view_same_file(tmp_path: Path) -> None:
    """Task 4.3 ①：同 run 兩次相同請求 ⇒ 同 `view_id`、同輸出檔、內容逐位元相等（值指紋）。"""
    source = light_source(tmp_path, light_frame(), "same")
    cwd = tmp_path / "cwd_same"
    a = light_run(tmp_path, source, ARM_ENVS["polars"], tag="a", cwd=cwd)
    b = light_run(tmp_path, source, ARM_ENVS["polars"], tag="b", cwd=cwd)
    assert _view_id(a) == _view_id(b) and a.output == b.output
    assert nh.bitwise_diff(nh.frame_fingerprints(a.frame), nh.frame_fingerprints(b.frame)) == []


def view_isolation_violations(first: PageRun, first_sha: str, second: PageRun) -> List[str]:
    """②⑤ oracle：兩 view 之 `view_id` 不同、輸出檔不同、第一檔位元組不變。"""
    out: List[str] = []
    if _view_id(first) == _view_id(second):
        out.append("view_id 相同")
    if first.output == second.output:
        out.append("輸出檔相同")
    if not first.output.is_file() or _sha_file(first.output) != first_sha:
        out.append("舊檔被改寫")
    return out


def test_view_different_transform_config_new_file_old_unchanged(tmp_path: Path) -> None:
    """Task 4.3 ②：轉換設定不同（rank 窗不同之合法值）⇒ 不同 `view_id`、不同檔、舊檔位元組不變。"""
    source = light_source(tmp_path, light_frame(), "cfg")
    cwd = tmp_path / "cwd_cfg"
    names = list(light_frame().columns)
    first = light_run(tmp_path, source, ARM_ENVS["polars"], tag="c1", cwd=cwd)
    sha = _sha_file(first.output)
    other = _default_request(names, rank_window=_default_request(names).rank_window + 1)
    second = light_run(tmp_path, source, ARM_ENVS["polars"], tag="c2", cwd=cwd, request=other)
    assert view_isolation_violations(first, sha, second) == []


@dataclasses.dataclass
class Regenerated:
    source: Source
    before: Dict[str, Any]
    after: Dict[str, Any]
    selected: List[str]


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory: pytest.TempPathFactory) -> Regenerated:
    """真實短窗 run（IC 當時身分＝before），再於隔離 kline 複本改一根（窗尾附近）同設定於同一特徵根重生（after）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.factories import ratio_unsafe_category

    root = tmp_path_factory.mktemp("numview_view_regen")
    run = ph.generate_short_run(root, REGEN_CELL)
    library = _library_for(run.run_dir, root / "numview_registry.json")
    before = _source_of(run.run_dir, library).identity
    axis = FeatureReader(str(run.features_root)).load_row_index_v2(run.symbol, run.tf, run.config_hash)
    assert axis is not None and len(axis) > 5, "前提不成立：run 無時間軸"
    kline = ph.copy_kline_with_one_bar_changed(root / "kline", symbol=run.symbol, tf=run.tf, when=str(axis[-3]))
    again = ph.generate_short_run(root, REGEN_CELL, symbol=run.symbol, kline_path=kline)
    assert again.run_dir == run.run_dir, "前提不成立：重生未落於同一 run 目錄"
    source = _source_of(run.run_dir, library)
    columns = list(library.load(run.symbol, run.tf, config_hash=run.config_hash).columns)
    selected = [c for c in columns if ratio_unsafe_category(c) is None][:3]
    assert selected, "前提不成立：run 無可轉換之欄"
    return Regenerated(source=source, before=before, after=source.identity, selected=selected)


def test_view_regenerated_run_after_ic_rejected(regenerated: Regenerated, tmp_path: Path) -> None:
    """Task 4.3 ③：IC 後 run 於隔離 kline 複本改一根而重生（身分改變）⇒ IC 頁以任務當時身分比對 ⇒
    `ICViewIdentityMismatchError`、無輸出檔。"""
    assert regenerated.before != regenerated.after, "前提不成立：重生後身分未變"
    cwd = tmp_path / "cwd_regen"
    with pytest.raises(nv.ICViewIdentityMismatchError):
        run_ic_page(cwd=cwd, source=regenerated.source, selected=regenerated.selected, env=ARM_ENVS["polars"],
                    task_id="numview_regen", task_result=task_result_for(regenerated.before))
    assert report_files(cwd) == []


def test_view_h5_ff_run_identity_equals_load_with_identity(tmp_path: Path) -> None:
    """Task 4.3 ④：view 輸出之 h5 `ff_run_identity`＝`load_with_identity` 回傳之身分，且 h5 帶 `view_id`、`algorithm_id`。"""
    source = light_source(tmp_path, light_frame(), "view_ident")
    run = light_run(tmp_path, source, ARM_ENVS["polars"], tag="view_ident")
    _df, identity = source.library.load_with_identity(source.symbol, source.tf, config_hash=source.config_hash)
    assert identity_from_attr(run) == identity.to_dict()
    assert _view_id(run)
    algo = run.attrs.get(attr_key("algorithm_id"))
    assert isinstance(algo, str) and algo and run.result.get(resp_key("algorithm_id")) == algo


@pytest.mark.parametrize("variant", ["add_one", "drop_one", "reorder"])
def test_view_selection_or_order_change_new_view_old_unchanged(variant: str, tmp_path: Path) -> None:
    """Task 4.3 ⑤：轉換設定相同而選欄增一欄、減一欄或同組欄換序 ⇒ 不同 `view_id`、不同檔、舊檔位元組不變（R7-A）。"""
    frame = light_frame(extra_columns=1)
    names = list(frame.columns)
    source = light_source(tmp_path, frame, variant)
    base = names[:2]
    other = {"add_one": names[:3], "drop_one": names[:1], "reorder": list(reversed(base))}[variant]
    cwd = tmp_path / "cwd_sel"
    first = light_run(tmp_path, source, ARM_ENVS["polars"], tag="s1", selected=base, cwd=cwd)
    sha = _sha_file(first.output)
    second = light_run(tmp_path, source, ARM_ENVS["polars"], tag="s2", selected=other, cwd=cwd)
    assert list(second.frame.columns) == other
    assert view_isolation_violations(first, sha, second) == []


def recomputed_view_id(run: PageRun, source: Source, kept: List[str]) -> str:
    """測試端依契約 `ic_page_view_identity` 之組成獨立重算 `view_id`（正規 JSON：sort_keys、無空白；sha256 hex）。"""
    from momentum.factories import create_post_ic_transform_config

    section = nv.load_contract()["ic_page_view_identity"]
    components = list(section["components"])
    assert set(components) == set(VIEW_COMPONENTS) and len(components) == len(VIEW_COMPONENTS), components
    assert section["normalization"], "契約 ic_page_view_identity.normalization 未填"
    req = _default_request(kept)
    cfg = create_post_ic_transform_config(rank=req.rank, rank_window=req.rank_window, zscore=req.zscore,
                                          zscore_windows=sorted(int(w) for w in req.zscore_windows), gaussian=req.gaussian)
    values = {"run_identity": source.identity, "transform_config": cfg.model_dump(), "arm": run.attrs.get(attr_key("arm")),
              "algorithm_id": run.attrs.get(attr_key("algorithm_id")), "kept_cols": list(kept)}
    payload = {name: values[name] for name in components}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_view_id_recomputed_from_contract_components(tmp_path: Path) -> None:
    """Task 4.3（§V oracle ⑮）：h5／回應之 `view_id`＝測試依契約組成獨立重算值＝`numeric_view.ic_page_view_id` 之值。"""
    from momentum.factories import create_post_ic_transform_config

    frame = light_frame()
    kept = list(frame.columns)
    source = light_source(tmp_path, frame, "recompute")
    run = light_run(tmp_path, source, ARM_ENVS["polars"], tag="recompute", selected=kept)
    expected = recomputed_view_id(run, source, kept)
    assert _view_id(run) == expected
    req = _default_request(kept)
    cfg = create_post_ic_transform_config(rank=req.rank, rank_window=req.rank_window, zscore=req.zscore,
                                          zscore_windows=sorted(int(w) for w in req.zscore_windows), gaussian=req.gaussian)
    assert nv.ic_page_view_id(run_identity=source.identity, transform_config=cfg.model_dump(),
                              arm=run.attrs.get(attr_key("arm")), algorithm_id=run.attrs.get(attr_key("algorithm_id")),
                              kept_cols=kept) == expected


# ---------------------------------------------------------------------------------------------- Task 4.3 邊界

def test_boundary_53_ic_task_missing_value_error_no_output(tmp_path: Path) -> None:
    """邊界①（Task 4.3）：IC 任務不存在 ⇒ ValueError（同現行）、無輸出檔。"""
    source = light_source(tmp_path, light_frame(), "notask")
    cwd = tmp_path / "cwd_notask"
    with pytest.raises(ValueError, match="not found"):
        run_ic_page(cwd=cwd, source=source, selected=list(light_frame().columns), env=ARM_ENVS["polars"],
                    task_id="numview_no_such_task", register=False)
    assert report_files(cwd) == []


@pytest.mark.parametrize("shape", ["no_metadata", "identity_key_missing", "identity_null"])
def test_boundary_54_report_without_identity_rejected(shape: str, tmp_path: Path) -> None:
    """邊界②（Task 4.3）：報告缺 metadata（舊任務）、metadata 缺 `ff_run_identity` 或其值為 null ⇒ 視同 null 身分；依設計
    選擇⑦建議（本檔假設，待委員審）拒收並提示重跑 IC：`ICViewIdentityMismatchError`、無輸出檔。"""
    source = light_source(tmp_path, light_frame(), shape)
    result = {"no_metadata": task_result_for(None, with_metadata=False),
              "identity_key_missing": dict(task_result_for(None, with_metadata=False), metadata={}),
              "identity_null": task_result_for(None)}[shape]
    cwd = tmp_path / f"cwd_{shape}"
    with pytest.raises(nv.ICViewIdentityMismatchError):
        run_ic_page(cwd=cwd, source=source, selected=list(light_frame().columns), env=ARM_ENVS["polars"],
                    task_id=f"numview_{shape}", task_result=result)
    assert report_files(cwd) == []


# ---------------------------------------------------------------------------------------------- Task 4.3 mutation

def _view_id_holders() -> List[Any]:
    """持有 view_id 計算之模組：`numeric_view`，及服務／`momentum.factories` 若以模組全域名持有 `ic_page_view_id`。"""
    import api.services.ic_analysis_service as service_module
    import momentum.factories as factories

    return [nv] + [m for m in (service_module, factories) if hasattr(m, "ic_page_view_id")]


def test_mutation_view_comparison_without_content_sha256(regenerated: Regenerated, tmp_path: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 4.3）：身分比對拿掉 `content_sha256` ⇒ ③翻轉（重生之 run 被接受、有輸出）。前提：兩身分只差
    `content_sha256`；mutant 以載入身分之 `content_sha256` 取任務當時值實現「不比此鍵」。"""
    diff = {k for k in set(regenerated.before) | set(regenerated.after)
            if regenerated.before.get(k) != regenerated.after.get(k)}
    assert diff == {"content_sha256"}, f"前提不成立：身分差異鍵 {sorted(diff)}"
    real = run_provenance.resolve_run_identity

    def ignore_content(*args: Any, **kwargs: Any) -> Any:
        identity = real(*args, **kwargs)
        return dataclasses.replace(identity, content_sha256=regenerated.before["content_sha256"])

    monkeypatch.setattr(run_provenance, "resolve_run_identity", ignore_content)
    cwd = tmp_path / "cwd_mut_regen"
    run = run_ic_page(cwd=cwd, source=regenerated.source, selected=regenerated.selected, env=ARM_ENVS["polars"],
                      task_id="numview_regen_mut", task_result=task_result_for(regenerated.before))
    assert run.output.is_file() and report_files(cwd) != []


def test_mutation_view_filename_without_view_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 4.3）：檔名去掉 `view_id`（以 view_id 不再隨 view 變化實現：恆回同值）⇒ ②翻轉（同檔、舊檔被改寫）。"""
    for holder in _view_id_holders():
        monkeypatch.setattr(holder, "ic_page_view_id", lambda **kwargs: "0" * 64)
    source = light_source(tmp_path, light_frame(), "mut_cfg")
    cwd = tmp_path / "cwd_mut_cfg"
    names = list(light_frame().columns)
    first = light_run(tmp_path, source, ARM_ENVS["polars"], tag="m1", cwd=cwd)
    sha = _sha_file(first.output)
    other = _default_request(names, rank_window=_default_request(names).rank_window + 1)
    second = light_run(tmp_path, source, ARM_ENVS["polars"], tag="m2", cwd=cwd, request=other)
    assert view_isolation_violations(first, sha, second) != []


def _view_id_with_kept_cols(transform: Callable[[List[str]], List[str]]) -> Callable[..., str]:
    """mutant view_id：`kept_cols` 先經 `transform` 再交真實計算。"""
    real = nv.ic_page_view_id

    def mutant(**kwargs: Any) -> str:
        kwargs["kept_cols"] = transform(list(kwargs["kept_cols"]))
        return real(**kwargs)

    return mutant


def _selection_views(tmp_path: Path, variant: str) -> List[str]:
    """⑤ 之兩 view（基準選欄 vs 增一欄或換序）於同 cwd 之隔離違規清單。"""
    frame = light_frame(extra_columns=1)
    names = list(frame.columns)
    source = light_source(tmp_path, frame, f"mut_{variant}")
    base = names[:2]
    other = {"add_one": names[:3], "reorder": list(reversed(base))}[variant]
    cwd = tmp_path / f"cwd_mut_{variant}"
    first = light_run(tmp_path, source, ARM_ENVS["polars"], tag="k1", selected=base, cwd=cwd)
    sha = _sha_file(first.output)
    second = light_run(tmp_path, source, ARM_ENVS["polars"], tag="k2", selected=other, cwd=cwd)
    return view_isolation_violations(first, sha, second)


def test_mutation_view_identity_without_kept_cols(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 4.3）：view 身分去掉 `kept_cols`（恆以空清單入身分）⇒ ⑤之增一欄案翻轉。"""
    mutant = _view_id_with_kept_cols(lambda kept: [])
    for holder in _view_id_holders():
        monkeypatch.setattr(holder, "ic_page_view_id", mutant)
    assert _selection_views(tmp_path, "add_one") != []


def test_mutation_view_kept_cols_sorted_before_hashing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 4.3）：`kept_cols` 排序後才入身分 ⇒ ⑤之欄序案翻轉。"""
    mutant = _view_id_with_kept_cols(sorted)
    for holder in _view_id_holders():
        monkeypatch.setattr(holder, "ic_page_view_id", mutant)
    assert _selection_views(tmp_path, "reorder") != []
