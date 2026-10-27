"""NUMVIEW Task 2.1（docs/NUMVIEW_SPEC.md §C D3、Task 2.1、§V oracle ②）：數值政策驗證之 Python 入口驗收。

API 入口（`ApplyTransformsRequest` 之 422）見 `tests/api/test_numview_ic_page.py`。
三入口＝pydantic（`PreprocessingConfig`／`FactoryConfig`）、dict 直接建構 `FeaturePreprocessor`、API；臂＝
`pandas_optimized`、`pandas_legacy`、registry 快速臂（numba `transform_array_fast`，經生產 raw 串流入口）。臂之環境沿用
`tests/_golden/icpostleak/contract.json` 之 `branches`（optimized／legacy／registry_sink）。FFPROD Task 1.1：原四臂之
`polars`（post-IC Polars 轉換鏈）生產不可達已刪，其臂案與 mutation 一併移除。
「臂分派前拒收」以 spy 斷言（§V oracle ②）：各臂轉換函式（`_transform_single`、`_transform_single_optimized_df`、
`_transform_single_legacy`、`_transform_chunked`、`_build_registry_transform_context`、`_transform_single_group_to_arrays`、
`_numba_transforms.transform_array_fast`）呼叫次數皆 0。
每個臂案另以同臂合法設定為正控制（該臂之具名轉換函式確被呼叫），證 spy 與環境確能觀測該臂。

驗證：①空窗（zscore 啟用、windows=[]）：pydantic 驗證錯、dict 入口 `NumericPolicyError`，×四臂皆分派前拒收；
②未知 method（`bogus`）：同入口×四臂，含快速核心直接呼叫 `transform_array_fast(winsor_method="bogus")` 拋
`NumericPolicyError`；③dict 入口縮尾啟用而缺 `method` 鍵 ⇒ 拒收（依契約 `winsor_method_missing_key`；pydantic 由
`WinsorConfig` 預設填值不拒）；④合法設定（真實 kline 格 A 之 BTCUSDT 1h）四臂輸出對 §G 逐位元相等——
`pandas_optimized`／`pandas_legacy` 對 G1 同臂份（以 IC 頁預設請求之 post-IC 設定經 `transform()` 依環境
分派重算），registry 快速臂對 G2（格 A raw 於 `FFACT_USE_POLARS` 各值之份；並斷言該 run 確有群組走 numba 快速臂）；
另：winsor 缺鍵盤點收據（`handoffs/run_receipts/*-numview-winsor-key-inventory.json`）證生產 dict 來源皆帶 `method`。
邊界：23 `enabled=false` 且空窗 ⇒ 合法且輸出＝zscore 關之輸出；24 窗含 0 或負數 ⇒ 拒收；25 method 大小寫變體 ⇒ 拒收。
mutation：恢復快速核心 `elif causal_preprocessing`
（非 sigma 一律 quantile）⇒ ②快速核心案翻轉；驗證器只掛 pydantic 不掛 `__init__` ⇒ ①③dict 案翻轉。

測試接縫（實作須提供；名稱為本檔之假設，見回報）：
- `scripts/numview_freeze_baseline.py:generate_cell(root: Path, cell: Mapping, *, run_kind: str, env=None) -> preprov_helpers.RunHandle`（`cell`＝全票唯一格描述子 `{id, kind, symbol, timeframes}`，本檔取 `.run_dir`）：
  以凍結時同一生成程序於 `root` 下重生該格、回傳 run 目錄（`<features_root>/<symbol>/<tf>/<config_hash>`）。
- §G 凍結檔 `tests/_golden/numview/pre_change_fingerprints.json` 為全票唯一正規形（`test_numview_baseline.py` 檔頭）：
  `{"cells": {格id: {"kind": "A"|"B", "symbol", "timeframes": [...], "ic_first_selected": [...], "g1_source_env": {...},
  "g1": {臂: {"env": {...}, "actual_arm": 臂, "fingerprint": frame_fingerprints 輸出}},
  "g2": {"0"|"1": {"env": {...}, "fingerprint": fingerprints(run_dir, "raw") 輸出}}, …}}}`；本檔唯一讀取點
  `_frozen_cells` 經 `_cell_view` 轉為內部檢視。
- `FeaturePreprocessor` 之政策驗證由 `feature_preprocessor` 模組碼直接呼叫 `validate_preprocessing_policy`
  （模組全域名或 `numeric_view.validate_preprocessing_policy`）；pydantic 驗證器不經 `feature_preprocessor`。
- 快速核心未知 method 拋 `numeric_view.NumericPolicyError`（SPEC 只寫「拋錯」；本檔取具名型別）。
- winsor 缺鍵盤點收據欄位：`sources`（非空清單，每筆含 `path`〔repo 相對，屬 momentum/ 或 api/〕與
  `has_method_key`〔布林〕）。
真實 kline（`data_cache/feature_klines/kline_cache.h5`）；④為重型（重生格 A，模組內每格每環境至多一次）。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
import pydantic
import pytest

from momentum.FeatureEngineering import numeric_view as nv
from momentum.FeatureEngineering.feature_config import (
    AdaptiveZScoreConfig,
    FactoryConfig,
    PreprocessingConfig,
    WinsorConfig,
)
from momentum.FeatureEngineering.preprocessing import _numba_transforms as nt
from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import numview_helpers as nh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = [pytest.mark.requires_kline]

REPO = Path(__file__).resolve().parents[2]
ICPOSTLEAK = json.loads((REPO / "tests/_golden/icpostleak/contract.json").read_text(encoding="utf-8"))
RANK_W = int(ICPOSTLEAK["rank_window"])
Z_WINDOWS: List[int] = [int(w) for w in ICPOSTLEAK["zscore_windows"]]
FREEZE_SCRIPT = REPO / "scripts" / "numview_freeze_baseline.py"
WINSOR_INVENTORY_GLOB = "*-numview-winsor-key-inventory.json"

#: SPEC Task 2.1 點名之四臂（前三者為契約 `post_ic_arm_values` 之值，見 `test_spec_named_arms_belong_to_contract`）
REGISTRY_ARM = "registry_fast"  # 測試端標籤（SPEC「registry 快速臂」），非契約值
# FFPROD Task 1.1：Polars post-IC 轉換鏈已刪（契約 post_ic_arm_values 無 polars）；registry 快速臂經生產 raw 串流入口
ARMS: Tuple[str, ...] = ("pandas_optimized", "pandas_legacy", REGISTRY_ARM)
POST_IC_ARMS: Tuple[str, ...] = ARMS[:2]
#: 臂 → icpostleak 契約 `branches` 之鍵（環境與入口之既有單一落點）
ARM_BRANCH: Dict[str, str] = {"pandas_optimized": "optimized", "pandas_legacy": "legacy", REGISTRY_ARM: "registry_sink"}
#: 各臂之具名轉換函式（正控制：合法設定下須被呼叫）
ARM_PROBE: Dict[str, str] = {"pandas_optimized": "_transform_single_optimized_df",
                             "pandas_legacy": "_transform_single_legacy", REGISTRY_ARM: "transform_array_fast"}
#: 「臂分派」之 spy 對象（任一被呼叫即非分派前拒收；§V oracle ②）
DISPATCH_FUNCS: Tuple[str, ...] = (
    "_transform_single", "_transform_single_optimized_df", "_transform_single_legacy",
    "_transform_chunked", "_build_registry_transform_context", "_transform_single_group_to_arrays",
)
ARM_ENV_KEYS: Tuple[str, ...] = ("FFACT_USE_POLARS", "FFACT_L65_OPTIMIZATION_PROFILE", "FFACT_L65_CHUNK_SIZE")
#: SPEC §A／設計選擇③以字面點名之縮尾 method（mutant 重現舊快速核心語意用；先斷言屬契約值集）
SPEC_SIGMA, SPEC_QUANTILE = "sigma", "quantile"
BOGUS_METHOD = "bogus"  # SPEC Task 2.1 ② 之字面


# ---------------------------------------------------------------------------------------------- 輸入與設定

def _real_frame() -> pd.DataFrame:
    """真實 BTCUSDT 1h kline 前段之欄（icpostleak 契約 `kline` 之 symbol／timeframe／rows／columns），float64。"""
    k = ICPOSTLEAK["kline"]
    frame = fsh.kline_frame(symbol=k["symbol"], timeframe=k["timeframe"]).iloc[: k["rows"]]
    return frame[k["columns"]].astype(np.float64).copy()


def _payload(*, zscore: Optional[Dict[str, Any]] = None, winsor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """前處理 dict（replace、因果、平穩化關；rank 開；zscore／縮尾依參數）。同一 dict 亦為 pydantic 之輸入。"""
    return {
        "enabled": True, "mode": "replace", "causal_preprocessing": True,
        "winsorization": copy.deepcopy(winsor) if winsor is not None else {"enabled": False},
        "fractional_differencing": {"enabled": False}, "adf_differencing": {"enabled": False},
        "rank_transform": {"enabled": True, "window": RANK_W, "apply_to": "all"},
        "adaptive_zscore": copy.deepcopy(zscore) if zscore is not None
        else {"enabled": True, "windows": list(Z_WINDOWS), "apply_to": "all"},
        "gaussian_normalize": {"enabled": False, "apply_to": "all"},
    }


def _contract() -> Dict[str, Any]:
    return nv.load_contract()


def _method_values() -> List[str]:
    values = [str(v) for v in _contract()["winsor_method_values"]["values"]]
    assert values, "契約 winsor_method_values 為空（Task 0.1 未填）"
    return values


def _legal_winsor(method: str) -> Dict[str, Any]:
    return {"enabled": True, "method": method, "window": RANK_W, "apply_to": "all"}


# ---------------------------------------------------------------------------------------------- spy 與分派

@dataclasses.dataclass
class Outcome:
    error: Optional[BaseException]
    calls: List[str]
    output: Optional[pd.DataFrame]


def _install_spies(mp: pytest.MonkeyPatch) -> List[str]:
    """包住各臂轉換函式（只記錄、原樣轉呼叫）；回傳呼叫紀錄（名稱依序）。以字串取屬性，不於本檔留下直接引用。"""
    calls: List[str] = []

    def wrap(name: str, real: Callable[..., Any]) -> Callable[..., Any]:
        def spy(*args: Any, **kwargs: Any) -> Any:
            calls.append(name)
            return real(*args, **kwargs)
        return spy

    for name in DISPATCH_FUNCS:
        real = getattr(FeaturePreprocessor, name)
        mp.setattr(FeaturePreprocessor, name, wrap(name, real))
    mp.setattr(nt, "transform_array_fast", wrap("transform_array_fast", getattr(nt, "transform_array_fast")))
    return calls


def _set_arm_env(mp: pytest.MonkeyPatch, arm: str) -> None:
    for key in ARM_ENV_KEYS:
        mp.delenv(key, raising=False)
    for key, value in ICPOSTLEAK["branches"][ARM_BRANCH[arm]]["env"].items():
        mp.setenv(key, value)


def _dispatch(pre: FeaturePreprocessor, arm: str, frame: pd.DataFrame, work: Path) -> pd.DataFrame:
    """依臂之入口執行：registry 快速臂經生產 raw 串流入口 `transform_registry_groups_to_sink`（`tests/_fixtures/registry_l65.py`
    之收集式 sink 寫回；同 icpostleak 分支測試之群組建法），其餘經 `transform`。"""
    if ICPOSTLEAK["branches"][ARM_BRANCH[arm]]["entry"] == "transform":
        return pre.transform(frame.copy())
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    registry = ColumnGroupRegistry(work_dir=work / f"registry_{uuid.uuid4().hex}")
    group = ColumnGroup(group_id="1h_L1_numview", layer=LayerSource.L1, timeframe="1h", data_source="close",
                        indicator="NUMVIEW", columns=tuple(frame.columns), shape=(0, 0), dtype="float32", disk_path=None)
    group = registry.save_data(group, frame.to_numpy(dtype=np.float32))
    from tests._fixtures.registry_l65 import apply_l65_via_sink

    # 同生產：registry 路徑只服務 raw，raw 之 L6.5 一律關 rank／zscore／gaussian（`feature_factory.
    # _build_l7_raw_preprocessing_config`）；於建構後關閉，建構時之政策驗證仍對原設定執行（拒收案語意不變）
    for step_config in (pre.rank_config, pre.zscore_config, pre.gaussian_config):
        step_config["enabled"] = False
    apply_l65_via_sink(pre, registry, n_workers=1)
    return pd.DataFrame(registry.load_data(group.group_id), columns=list(frame.columns), index=frame.index)


def _attempt(build: Callable[[], FeaturePreprocessor], arm: str, frame: pd.DataFrame, work: Path) -> Outcome:
    """於臂環境下建構前處理器並分派；記錄例外（型別由呼叫端斷言）、spy 呼叫與輸出。環境與 spy 於結束時復原。"""
    with pytest.MonkeyPatch.context() as mp:
        calls = _install_spies(mp)
        _set_arm_env(mp, arm)
        try:
            out = _dispatch(build(), arm, frame, work)
        except Exception as exc:  # noqa: BLE001 — 例外型別由 oracle 斷言
            return Outcome(exc, list(calls), None)
        return Outcome(None, list(calls), out)


def rejected_before_dispatch(outcome: Outcome, error_type: type) -> bool:
    """§V oracle ②：拋具名型別且無任何臂轉換函式被呼叫。"""
    return isinstance(outcome.error, error_type) and outcome.calls == []


#: 三入口（Python 側）：名稱 → (由 payload 建構前處理器之函式, 預期例外型別)
ENTRIES: Dict[str, Tuple[Callable[[Dict[str, Any]], FeaturePreprocessor], type]] = {
    "pydantic_preprocessing": (lambda p: FeaturePreprocessor(PreprocessingConfig(**copy.deepcopy(p)).model_dump()),
                               pydantic.ValidationError),
    "pydantic_factory": (lambda p: FeaturePreprocessor(
        FactoryConfig(preprocessing=copy.deepcopy(p)).preprocessing.model_dump()), pydantic.ValidationError),
    "dict": (lambda p: FeaturePreprocessor(copy.deepcopy(p)), nv.NumericPolicyError),
}


def _positive_control(arm: str, payload: Dict[str, Any], frame: pd.DataFrame, work: Path) -> Outcome:
    """合法設定之同臂執行：須無例外且該臂具名函式被呼叫（證環境與 spy 確能觀測該臂）。"""
    outcome = _attempt(lambda: FeaturePreprocessor(copy.deepcopy(payload)), arm, frame, work)
    assert outcome.error is None, f"{arm} 合法設定拋錯：{outcome.error!r}"
    assert ARM_PROBE[arm] in outcome.calls, f"{arm} 合法設定未走該臂（calls={outcome.calls}）"
    return outcome


# ---------------------------------------------------------------------------------------------- 契約前提

def test_spec_named_arms_belong_to_contract() -> None:
    """SPEC 點名之 post-IC 臂（polars／pandas_optimized／pandas_legacy）屬契約 `post_ic_arm_values`；
    SPEC 字面之 sigma／quantile 屬契約 `winsor_method_values`，且 `bogus` 不屬之。"""
    contract = _contract()
    arms = set(contract["post_ic_arm_values"]["values"])
    assert set(POST_IC_ARMS) <= arms, sorted(arms)
    methods = set(_method_values())
    assert {SPEC_SIGMA, SPEC_QUANTILE} <= methods and BOGUS_METHOD not in methods, sorted(methods)


# ---------------------------------------------------------------------------------------------- 驗證①②③

@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_empty_zscore_windows_rejected_before_dispatch(entry: str, arm: str, tmp_path: Path) -> None:
    """①空窗（zscore 啟用、windows=[]）：pydantic 入口 ValidationError、dict 入口 NumericPolicyError；四臂皆於臂分派前拒收。"""
    frame = _real_frame()
    _positive_control(arm, _payload(), frame, tmp_path)
    build, error_type = ENTRIES[entry]
    bad = _payload(zscore={"enabled": True, "windows": [], "apply_to": "all"})
    outcome = _attempt(lambda: build(bad), arm, frame, tmp_path)
    assert rejected_before_dispatch(outcome, error_type), (entry, arm, repr(outcome.error), outcome.calls)


def test_empty_zscore_windows_rejected_by_config_models_and_validator() -> None:
    """①之模型層：`AdaptiveZScoreConfig`、`PreprocessingConfig`、`FactoryConfig` 皆驗證錯；`validate_preprocessing_policy`
    對同 dict 拋 `NumericPolicyError`；合法 dict 不拋（回 None）。"""
    bad = _payload(zscore={"enabled": True, "windows": [], "apply_to": "all"})
    with pytest.raises(pydantic.ValidationError):
        AdaptiveZScoreConfig(enabled=True, windows=[])
    with pytest.raises(pydantic.ValidationError):
        PreprocessingConfig(**bad)
    with pytest.raises(pydantic.ValidationError):
        FactoryConfig(preprocessing=bad)
    with pytest.raises(nv.NumericPolicyError):
        nv.validate_preprocessing_policy(bad)
    assert nv.validate_preprocessing_policy(_payload()) is None


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_unknown_winsor_method_rejected_before_dispatch(entry: str, arm: str, tmp_path: Path) -> None:
    """②未知 method（`bogus`，縮尾啟用）：三入口（Python 側）×四臂皆於臂分派前拒收。"""
    frame = _real_frame()
    _positive_control(arm, _payload(winsor=_legal_winsor(_method_values()[0])), frame, tmp_path)
    build, error_type = ENTRIES[entry]
    bad = _payload(winsor=_legal_winsor(BOGUS_METHOD))
    outcome = _attempt(lambda: build(bad), arm, frame, tmp_path)
    assert rejected_before_dispatch(outcome, error_type), (entry, arm, repr(outcome.error), outcome.calls)


def _fast_core_error(method: str) -> Optional[BaseException]:
    """快速核心直接呼叫（經模組屬性，mutant 可替換）；回傳所拋例外或 None。"""
    arr = _real_frame().to_numpy(dtype=np.float32)
    try:
        nt.transform_array_fast(arr, winsorize=True, winsor_method=method,
                                causal_preprocessing=True)
    except Exception as exc:  # noqa: BLE001 — 型別由呼叫端斷言
        return exc
    return None


def test_fast_core_unknown_method_raises() -> None:
    """②快速核心：`transform_array_fast(winsor_method="bogus")` 拋 `NumericPolicyError`；契約每個合法值皆可執行，且
    sigma 與 quantile 兩分支輸出不同（證兩分支皆真實存在、非一律同一算法）。"""
    assert isinstance(_fast_core_error(BOGUS_METHOD), nv.NumericPolicyError)
    arr = _real_frame().to_numpy(dtype=np.float32)
    outputs = {}
    for method in _method_values():
        outputs[method] = nt.transform_array_fast(arr, winsorize=True, winsor_method=method,
                                                  causal_preprocessing=True)
        assert outputs[method].shape == arr.shape
    assert not np.array_equal(outputs[SPEC_SIGMA], outputs[SPEC_QUANTILE], equal_nan=True)


def test_unknown_winsor_method_rejected_by_config_models() -> None:
    """②之模型層：`WinsorConfig(method="bogus")` 驗證錯；契約每個合法值皆可建構。"""
    with pytest.raises(pydantic.ValidationError):
        WinsorConfig(method=BOGUS_METHOD)
    for method in _method_values():
        assert WinsorConfig(method=method).method == method


@pytest.mark.parametrize("arm", ARMS)
def test_dict_winsor_enabled_missing_method_key_rejected(arm: str, tmp_path: Path) -> None:
    """③dict 入口縮尾啟用而缺 `method` 鍵 ⇒ 依契約 `winsor_method_missing_key`（須已填）拒收，四臂皆分派前；
    pydantic 入口由 `WinsorConfig` 預設填值、不拒（生產值不變；設計選擇③）。"""
    policy = _contract()["winsor_method_missing_key"]["value"]
    assert isinstance(policy, str) and policy, "契約 winsor_method_missing_key.value 未填"
    frame = _real_frame()
    _positive_control(arm, _payload(winsor=_legal_winsor(_method_values()[0])), frame, tmp_path)
    missing = _payload(winsor={"enabled": True, "window": RANK_W, "apply_to": "all"})
    outcome = _attempt(lambda: FeaturePreprocessor(copy.deepcopy(missing)), arm, frame, tmp_path)
    assert rejected_before_dispatch(outcome, nv.NumericPolicyError), (arm, repr(outcome.error), outcome.calls)
    filled = PreprocessingConfig(**missing).model_dump()
    assert filled["winsorization"]["method"] == WinsorConfig().method and filled["winsorization"]["method"] in _method_values()
    nv.validate_preprocessing_policy(filled)


def _winsor_inventory() -> Dict[str, Any]:
    paths = sorted(nh.RECEIPTS_DIR.glob(WINSOR_INVENTORY_GLOB))
    assert paths, f"winsor 缺鍵盤點收據不存在：{nh.RECEIPTS_DIR}/{WINSOR_INVENTORY_GLOB}（Task 2.1 改法）"
    return json.loads(paths[-1].read_text(encoding="utf-8"))


def test_winsor_key_inventory_receipt_all_production_sources_carry_method() -> None:
    """Task 2.1 改法：盤點收據列之生產 dict 來源非空、每筆路徑存在且屬 momentum/ 或 api/、皆帶 `method` 鍵。"""
    sources = _winsor_inventory().get("sources")
    assert isinstance(sources, list) and sources, "收據 sources 為空"
    for row in sources:
        rel = str(row["path"]).split(":", 1)[0]
        assert rel.startswith(("momentum/", "api/")) and (REPO / rel).is_file(), row
        assert row["has_method_key"] is True, row


# ---------------------------------------------------------------------------------------------- 驗證④（重型）

def _frozen_cells() -> Dict[str, Dict[str, Any]]:
    """§G 凍結檔之格表（唯一讀取點；結構見檔頭「測試接縫」）。缺檔或空 ⇒ 紅。"""
    assert nh.PRE_CHANGE_FINGERPRINTS_PATH.is_file(), f"§G 改前凍結檔不存在：{nh.PRE_CHANGE_FINGERPRINTS_PATH}"
    cells = json.loads(nh.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8")).get("cells")
    assert isinstance(cells, dict) and cells, "§G 凍結檔無 cells"
    return {cid: _cell_view(cid, cell) for cid, cell in cells.items()}


def _cell_view(cell_id: str, cell: Mapping[str, Any]) -> Dict[str, Any]:
    """凍結檔正規形（全票唯一，與 `test_numview_baseline.py` 同：`cells.<格>.{kind, symbol, timeframes, ic_first_selected,
    g1_source_env, g1.<臂>.{env, actual_arm, fingerprint}, g2.{"0","1"}.{env, fingerprint}, g3}`）→ 本檔檢視：`tf`（單週期格之
    唯一週期）、`g1.{source_env, selected, arms.<臂>.{env, recorded_arm〔＝actual_arm〕, fingerprint}}`。G1 所需欄缺 ⇒ 紅。"""
    view = dict(cell)
    timeframes = list(cell.get("timeframes") or [])
    view["tf"] = timeframes[0] if len(timeframes) == 1 else None
    # 凍結檔之格 B／C 不凍 G1 臂份（`g1` 為空物件，`scripts/numview_freeze_baseline.py` freeze_one）⇒ 無 G1 檢視；
    # 有任一 G1 臂份之格方須具 g1_source_env／ic_first_selected
    if isinstance(cell.get("g1"), Mapping) and cell["g1"]:
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


def _cell_a(symbol: str, tf: str) -> Tuple[str, Dict[str, Any]]:
    hits = [(cid, c) for cid, c in _frozen_cells().items()
            if c.get("kind") == "A" and c.get("symbol") == symbol and c.get("tf") == tf]
    assert len(hits) == 1, f"§G 凍結檔中格 A {symbol} {tf} 須恰一格，實得 {[h[0] for h in hits]}"
    return hits[0]


def _freeze_module() -> Any:
    spec = importlib.util.spec_from_file_location("numview_freeze_baseline", FREEZE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CellLab:
    """格之重生倉：同 (格, 生成環境) 於本模組只生成一次（經凍結腳本之 `generate_cell` 接縫）。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._runs: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Path] = {}

    def run_dir(self, cell_id: str, env: Mapping[str, str]) -> Path:
        key = (cell_id, tuple(sorted((str(k), str(v)) for k, v in env.items())))
        if key not in self._runs:
            work = self.root / f"{cell_id}_{len(self._runs)}"
            # 批次共用生成（判準檔 cell_rules.batch_cache）：root＝共用快取根、跑別＝本檢查所讀之批次（b3）；`work` 只作
            # 舊判準（無 reads_from）之隔離根
            run_dir = Path(_freeze_module().generate_cell(nh.regen_root(work), _descriptor(cell_id),
                                                          run_kind=nh.regen_batch_kind("regen_t21"),
                                                          env=dict(env)).run_dir)
            assert (run_dir / "feature_manifest.json").is_file(), f"重生之 run 無 manifest：{run_dir}"
            self._runs[key] = run_dir
        return self._runs[key]

    def raw_frame(self, cell_id: str, env: Mapping[str, str]) -> pd.DataFrame:
        from momentum.FeatureEngineering.feature_library import FeatureLibrary
        from momentum.FeatureEngineering.feature_reader import FeatureReader
        from momentum.FeatureEngineering.feature_registry import FeatureRegistry
        from momentum.FeatureEngineering.feature_storage import FeatureStorage
        from tests.feature_engineering.ffname_helpers import register_canonical_run

        run_dir = self.run_dir(cell_id, env)
        registry_path = self.root / f"registry_{uuid.uuid4().hex}.json"
        register_canonical_run(run_dir / "feature_manifest.json", registry_path)
        features_root = run_dir.parents[2]
        library = FeatureLibrary(FeatureRegistry(registry_path), FeatureStorage(str(features_root)),
                                 feature_reader=FeatureReader(str(features_root)))
        return library.load(run_dir.parent.parent.name, run_dir.parent.name, config_hash=run_dir.name)


@pytest.fixture(scope="module")
def lab(tmp_path_factory: pytest.TempPathFactory) -> CellLab:
    return CellLab(tmp_path_factory.mktemp("numview_policy_cells"))


def _ic_page_default_post_ic_output(raw: pd.DataFrame, selected: List[str],
                                    arm_env: Mapping[str, str]) -> Tuple[pd.DataFrame, List[str]]:
    """G1 之同一轉換於 `transform()` 依環境分派重算：IC 頁預設請求（`ApplyTransformsRequest` 預設值、zscore 窗排序）之
    post-IC 設定；選欄保序去重、只取存在者、排除 ratio-unsafe（同 IC 頁第三步）。spy 斷言實際所走之臂。"""
    from api.models.ic_models import ApplyTransformsRequest
    from momentum.factories import create_feature_preprocessor, create_post_ic_transform_config, ratio_unsafe_category

    request = ApplyTransformsRequest(selected_features=list(selected))
    kept: List[str] = []
    for name in dict.fromkeys(str(c) for c in request.selected_features):
        if name in raw.columns and ratio_unsafe_category(name) is None:
            kept.append(name)
    assert kept, "前提不成立：G1 選欄於重生 raw 中無可轉換之欄"
    cfg = create_post_ic_transform_config(rank=request.rank, rank_window=request.rank_window, zscore=request.zscore,
                                          zscore_windows=sorted(int(w) for w in request.zscore_windows),
                                          gaussian=request.gaussian)
    with pytest.MonkeyPatch.context() as mp:
        for key in ARM_ENV_KEYS:
            mp.delenv(key, raising=False)
        for key, value in arm_env.items():
            mp.setenv(key, str(value))
        calls = _install_spies(mp)
        out = create_feature_preprocessor(cfg.model_dump()).transform(raw.loc[:, kept].copy())
    return out.loc[:, kept], calls


@pytest.mark.parametrize("arm", POST_IC_ARMS)
def test_legal_setting_post_ic_arms_bitwise_equal_g1(arm: str, lab: CellLab) -> None:
    """④合法設定（格 A BTCUSDT 1h）：`polars`／`pandas_optimized`／`pandas_legacy` 各於 G1 同臂份之環境下重算，
    值指紋（dtype、nan、values_native、欄集合、欄序）逐位元等於 G1 同臂份，且實際走該臂（spy）。"""
    cell_id, cell = _cell_a("BTCUSDT", "1h")
    g1 = cell["g1"]
    assert arm in g1["arms"], f"G1 {cell_id} 無 {arm} 份（不得補造）"
    copy_ = g1["arms"][arm]
    assert copy_["recorded_arm"] == arm
    raw = lab.raw_frame(cell_id, g1["source_env"])
    out, calls = _ic_page_default_post_ic_output(raw, list(g1["selected"]), copy_["env"])
    assert ARM_PROBE[arm] in calls, (arm, calls)
    assert nh.bitwise_diff(copy_["fingerprint"], nh.frame_fingerprints(out)) == []


def test_legal_setting_registry_fast_arm_bitwise_equal_g2(lab: CellLab) -> None:
    """④registry 快速臂（格 A BTCUSDT 1h 之 L6.5 raw）：G2 每份（`FFACT_USE_POLARS` 各值）以同環境重生，raw 值指紋
    逐位元等於凍結份；且該 run 確有群組走 numba 快速臂（manifest raw 紀錄之群組臂）。"""
    cell_id, cell = _cell_a("BTCUSDT", "1h")
    g2 = cell["g2"]
    assert isinstance(g2, dict) and len(g2) >= 2, f"G2 {cell_id} 須含 FFACT_USE_POLARS 各值之份：{sorted(g2 or {})}"
    fast = ph.spec_named("numba_fast_arm")
    for label, frozen in g2.items():
        run_dir = lab.run_dir(cell_id, frozen["env"])
        assert nh.bitwise_diff(frozen["fingerprint"], nh.fingerprints(run_dir, "raw")) == [], label
        arms = {str(g.get("arm")) for g in ph.provenance_pointer(run_dir, "raw")["groups"].values()}
        assert fast in arms, (label, sorted(arms))


# ---------------------------------------------------------------------------------------------- 邊界

@pytest.mark.parametrize("arm", ARMS)
def test_boundary_23_zscore_disabled_with_empty_windows_is_legal(arm: str, tmp_path: Path) -> None:
    """邊界①（Task 2.1）：`enabled=false` 且窗清單為空 ⇒ 合法不拒（pydantic、validator、dict 建構皆通過），且真實資料
    輸出逐位元等於 zscore 關（預設窗）之輸出；rank 開故輸出≠輸入（非空轉）——registry 臂同生產只做縮尾，改以縮尾開防空轉。"""
    frame = _real_frame()
    winsor = _legal_winsor("quantile") if arm == REGISTRY_ARM else None
    off_empty = _payload(zscore={"enabled": False, "windows": [], "apply_to": "all"}, winsor=winsor)
    off_default = _payload(zscore={"enabled": False, "apply_to": "all"}, winsor=winsor)
    PreprocessingConfig(**off_empty)
    AdaptiveZScoreConfig(enabled=False, windows=[])
    assert nv.validate_preprocessing_policy(off_empty) is None
    a = _attempt(lambda: FeaturePreprocessor(copy.deepcopy(off_empty)), arm, frame, tmp_path)
    b = _attempt(lambda: FeaturePreprocessor(copy.deepcopy(off_default)), arm, frame, tmp_path)
    assert a.error is None and b.error is None, (repr(a.error), repr(b.error))
    assert ARM_PROBE[arm] in a.calls, a.calls
    got = a.output.to_numpy(dtype=np.float64)
    assert np.array_equal(got, b.output.to_numpy(dtype=np.float64), equal_nan=True)
    assert not np.array_equal(got, frame.to_numpy(dtype=np.float64), equal_nan=True)


@pytest.mark.parametrize("windows", [[0], [-5], [100, 0]], ids=["zero", "negative", "contains_zero"])
def test_boundary_24_zscore_window_zero_or_negative_rejected(windows: List[int], tmp_path: Path) -> None:
    """邊界②（Task 2.1）：zscore 啟用而窗含 0 或負數 ⇒ pydantic 驗證錯、validator 與 dict 入口 `NumericPolicyError`
    （四臂皆分派前）。"""
    bad = _payload(zscore={"enabled": True, "windows": list(windows), "apply_to": "all"})
    with pytest.raises(pydantic.ValidationError):
        AdaptiveZScoreConfig(enabled=True, windows=list(windows))
    with pytest.raises(pydantic.ValidationError):
        PreprocessingConfig(**bad)
    with pytest.raises(nv.NumericPolicyError):
        nv.validate_preprocessing_policy(bad)
    frame = _real_frame()
    for arm in ARMS:
        outcome = _attempt(lambda: FeaturePreprocessor(copy.deepcopy(bad)), arm, frame, tmp_path)
        assert rejected_before_dispatch(outcome, nv.NumericPolicyError), (arm, repr(outcome.error), outcome.calls)


def test_boundary_25_winsor_method_case_variant_rejected(tmp_path: Path) -> None:
    """邊界③（Task 2.1）：method 大小寫變體（如 `Sigma`、`QUANTILE`，自契約合法值導出）⇒ 拒收（值集區分大小寫）：
    pydantic 驗證錯、validator 與 dict 入口 `NumericPolicyError`（四臂分派前）、快速核心直接呼叫拋 `NumericPolicyError`。"""
    legal = _method_values()
    variants = sorted({v for m in legal for v in (m.capitalize(), m.upper())} - set(legal))
    assert variants, "契約值無大小寫變體可導出（值須為小寫，契約樣式 ^[a-z]…）"
    assert SPEC_SIGMA.capitalize() in variants  # SPEC 點名之 `Sigma`
    frame = _real_frame()
    for variant in variants:
        assert variant not in legal and variant.lower() in legal
        bad = _payload(winsor=_legal_winsor(variant))
        with pytest.raises(pydantic.ValidationError):
            WinsorConfig(method=variant)
        with pytest.raises(nv.NumericPolicyError):
            nv.validate_preprocessing_policy(bad)
        assert isinstance(_fast_core_error(variant), nv.NumericPolicyError), variant
        for arm in ARMS:
            outcome = _attempt(lambda: FeaturePreprocessor(copy.deepcopy(bad)), arm, frame, tmp_path)
            assert rejected_before_dispatch(outcome, nv.NumericPolicyError), (variant, arm, repr(outcome.error))


# ---------------------------------------------------------------------------------------------- mutation

def _bypass_validation(monkeypatch: pytest.MonkeyPatch, only_from_preprocessor: bool) -> None:
    """繞過政策驗證：`only_from_preprocessor=False` ⇒ 全部入口皆不驗；True ⇒ 只有 `feature_preprocessor` 模組碼發起之
    呼叫不驗（＝驗證器只掛 pydantic、不掛 `__init__`），其他呼叫者（pydantic 驗證器）照驗。"""
    real = nv.validate_preprocessing_policy

    def mutant(config: Mapping[str, Any]) -> None:
        if not only_from_preprocessor:
            return None
        if sys._getframe(1).f_globals.get("__name__") == fp_mod.__name__:
            return None
        return real(config)

    monkeypatch.setattr(nv, "validate_preprocessing_policy", mutant)
    if hasattr(fp_mod, "validate_preprocessing_policy"):
        monkeypatch.setattr(fp_mod, "validate_preprocessing_policy", mutant)



def test_mutation_fast_core_elif_causal_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：恢復快速核心 `elif causal_preprocessing:`（非 sigma 之 method 一律走 quantile）⇒ ②快速核心案翻轉：
    `bogus` 不拋錯，且輸出等於 quantile 輸出（靜默換算法）。"""
    assert SPEC_SIGMA in _method_values() and SPEC_QUANTILE in _method_values()
    real = nt.transform_array_fast

    def old_core(arr: np.ndarray, *, winsor_method: str = SPEC_QUANTILE, **kwargs: Any) -> np.ndarray:
        return real(arr, winsor_method=SPEC_SIGMA if winsor_method == SPEC_SIGMA else SPEC_QUANTILE, **kwargs)

    monkeypatch.setattr(nt, "transform_array_fast", old_core)
    assert _fast_core_error(BOGUS_METHOD) is None
    arr = _real_frame().to_numpy(dtype=np.float32)
    kwargs = dict(winsorize=True, causal_preprocessing=True)
    assert np.array_equal(nt.transform_array_fast(arr, winsor_method=BOGUS_METHOD, **kwargs),
                          real(arr, winsor_method=SPEC_QUANTILE, **kwargs), equal_nan=True)


@pytest.mark.parametrize("arm", ARMS)
def test_mutation_validator_only_on_pydantic_not_init(arm: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutation：驗證器只掛 pydantic、不掛 `FeaturePreprocessor.__init__`（`feature_preprocessor` 模組發起之驗證失效）⇒
    ①③之 dict 案翻轉（不再於分派前拒收）；pydantic 入口照常拒收（證 mutant 只拆掉 `__init__` 之掛點）。"""
    _bypass_validation(monkeypatch, only_from_preprocessor=True)
    empty = _payload(zscore={"enabled": True, "windows": [], "apply_to": "all"})
    missing = _payload(winsor={"enabled": True, "window": RANK_W, "apply_to": "all"})
    with pytest.raises(pydantic.ValidationError):
        PreprocessingConfig(**empty)
    frame = _real_frame()
    for name, bad in (("empty_windows", empty), ("missing_method", missing)):
        outcome = _attempt(lambda: FeaturePreprocessor(copy.deepcopy(bad)), arm, frame, tmp_path)
        assert not rejected_before_dispatch(outcome, nv.NumericPolicyError), (name, arm, outcome.calls)
