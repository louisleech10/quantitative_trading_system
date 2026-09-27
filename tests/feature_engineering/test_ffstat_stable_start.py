"""FF-STAT Task 2.3（SPEC v32–v44）：逐欄穩定點、公開域預熱恆開、未填起始日之逐欄校準、死欄純函式與欄集合差異。

全部以真實 `data_cache/feature_klines/kline_cache.h5`（及長歷史快取）驗證，禁合成 fixture。
實作前本檔應為紅（`stable_mask` 為 NotImplementedError 空殼、生成路徑尚未接線）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.preprocessing import stable_mask as sm
from tests.feature_engineering import ffstat_helpers as h

CONTRACT = h.CONTRACT
REPO = Path(__file__).resolve().parents[2]
TABLE_PATH = REPO / CONTRACT["warmup_table"]["path"]


def _table() -> Dict[str, Dict[str, Any]]:
    import yaml

    return dict(yaml.safe_load(TABLE_PATH.read_text(encoding="utf-8"))["indicators"])


def _close(timeframe: str = "1h") -> np.ndarray:
    return h.kline_frame(timeframe=timeframe)["close"].to_numpy(dtype=np.float64)


def _hlc(timeframe: str = "1h") -> np.ndarray:
    frame = h.kline_frame(timeframe=timeframe)
    return frame[["high", "low", "close"]].to_numpy(dtype=np.float64)


def _spec(indicator: str, column: str, params: Dict[str, Any], **kw: Any) -> sm.OutputPointSpec:
    keys = tuple(_table()[indicator]["period_keys"]) if indicator in _table() else ()
    return sm.OutputPointSpec(engine="talib", indicator=indicator, column=column, params=params, period_keys=keys, **kw)


def _factor(indicator: str) -> float:
    return float(_table()[indicator]["recommended_factor"])


def _params_key(params: Dict[str, Any], keys: Any) -> str:
    """v46 `k_by_params` 之鍵：period_keys 各鍵值依鍵名升序以 `鍵=值` 逗號連接（值為整數字面）。"""
    return ",".join(f"{k}={int(params[k])}" for k in sorted(keys))


def _expected_k(indicator: str, params: Dict[str, Any]) -> int:
    """SPEC v46（R10）：表之 `k_by_params` 查得者取其值；查無才 ceil(max(period_keys 值)×係數)。"""
    entry = _table()[indicator]
    keys = entry["period_keys"]
    measured = (entry.get("k_by_params") or {}).get(_params_key(params, keys))
    if measured is not None:
        return int(measured)
    return math.ceil(max(float(params[k]) for k in keys) * float(entry["recommended_factor"]))


# ─────────────────────────────── ① L1 遮罩（逐呼叫 K）

@pytest.mark.parametrize("timeframe", ["1h", "12h"])
def test_l1_mask_first_valid_is_origin_plus_k(timeframe: str) -> None:
    """Task 2.3 ①：EMA_233（recursive）、SMA_200（window_only）、ADX_14（多輸入）首個有效值之列＝origin＋K，之前全 NaN。"""
    import talib

    close = _close(timeframe)
    hlc = _hlc(timeframe)
    cases = [
        ("EMA", "EMA_233", {"timeperiod": 233}, talib.EMA(close, timeperiod=233), close[:, None]),
        ("SMA", "SMA_200", {"timeperiod": 200}, talib.SMA(close, timeperiod=200), close[:, None]),
        ("ADX", "ADX_14", {"timeperiod": 14}, talib.ADX(hlc[:, 0], hlc[:, 1], hlc[:, 2], timeperiod=14), hlc),
    ]
    for indicator, column, params, raw, inputs in cases:
        k = sm.instance_k(_spec(indicator, column, params), _table())
        assert k == _expected_k(indicator, params), column
        origin = sm.l1_origin(inputs)
        masked = sm.apply_l1_mask(raw, origin, k)
        assert sm.first_finite_index(masked) == origin + k, column
        assert np.isnan(masked[: origin + k]).all(), column
        np.testing.assert_array_equal(masked[origin + k:], raw[origin + k:])


def test_l1_mask_per_call_k_ema5_vs_ema233() -> None:
    """Task 2.3 ①（v37）：同一指標之 EMA_5 與 EMA_233 之 K 分別依各自參數，不取整個指標之最大週期。"""
    k5 = sm.instance_k(_spec("EMA", "EMA_5", {"timeperiod": 5}), _table())
    k233 = sm.instance_k(_spec("EMA", "EMA_233", {"timeperiod": 233}), _table())
    assert k5 == _expected_k("EMA", {"timeperiod": 5})
    assert k233 == _expected_k("EMA", {"timeperiod": 233})
    assert k5 < k233


def test_l1_mask_stoch_combo_k_uses_max_period_key() -> None:
    """Task 2.3 ①：STOCH 一組 combo 之 K 依其三個週期鍵（v46：k_by_params 查得者優先，否則 ceil(max×係數)）；
    表外之組合（fastk 377）走比例公式。"""
    params = {"fastk_period": 55, "slowk_period": 8, "slowk_matype": 0, "slowd_period": 5, "slowd_matype": 0}
    k = sm.instance_k(_spec("STOCH", "STOCH_slowk", params), _table())
    assert k == _expected_k("STOCH", params)
    unmeasured = {"fastk_period": 377, "slowk_period": 8, "slowk_matype": 0, "slowd_period": 5, "slowd_matype": 0}
    assert sm.instance_k(_spec("STOCH", "STOCH_slowk", unmeasured), _table()) == math.ceil(377 * _factor("STOCH"))


def test_l1_mask_k_by_params_preferred_over_factor() -> None:
    """v46（R10 實測根數優先）：KAMA_233 之 K＝表 k_by_params 之實測值，且小於 ceil(233×係數)（比例公式高估）。"""
    params = {"timeperiod": 233}
    measured = _table()["KAMA"]["k_by_params"][_params_key(params, ["timeperiod"])]
    assert measured < math.ceil(233 * _factor("KAMA"))
    assert sm.instance_k(_spec("KAMA", "close_trend_KAMA_233", params), _table()) == measured


def test_derived_output_k_follows_upstream() -> None:
    """§C v39：同引擎衍生輸出之 K＝上游 K 最大者＋window−1（窗型）或上游 K 最大者（逐點聚合）。"""
    windowed = sm.OutputPointSpec(engine="microstructure", indicator="VPIN_ZSCORE", column="ms_vpin_zscore_21",
                                  params={"window": 21}, period_keys=(), upstream=("ms_vpin_30", "ms_sigma_50"), window=21)
    assert sm.instance_k(windowed, _table(), upstream_k={"ms_vpin_30": 40, "ms_sigma_50": 60}) == 60 + 20
    pointwise = sm.OutputPointSpec(engine="pattern", indicator="CDL_PATTERN", column="ohlc_pattern_Consensus",
                                   params={}, period_keys=(), upstream=("ohlc_pattern_CDLDOJI", "ohlc_pattern_CDLENGULFING"))
    assert sm.instance_k(pointwise, _table(), upstream_k={"ohlc_pattern_CDLDOJI": 5, "ohlc_pattern_CDLENGULFING": 7}) == 7


def test_output_point_missing_period_key_fails_closed() -> None:
    """§C 輸出點契約：參數字典缺登記之 period key ⇒ StableMaskError，訊息列引擎、輸出欄與缺少之鍵。"""
    with pytest.raises(sm.StableMaskError) as exc:
        sm.instance_k(_spec("STOCH", "STOCH_slowk", {"fastk_period": 55}), _table())
    message = str(exc.value)
    assert "talib" in message and "STOCH_slowk" in message and "slowk_period" in message


def test_output_point_unregistered_indicator_fails_closed() -> None:
    """§C／R5：倍數表查不到之指標 ⇒ StableMaskError（不得套後備係數）。"""
    spec = sm.OutputPointSpec(engine="talib", indicator="NOT_IN_TABLE_XYZ", column="x", params={"timeperiod": 10},
                              period_keys=("timeperiod",))
    with pytest.raises(sm.StableMaskError):
        sm.instance_k(spec, _table())


def test_custom_indicator_outputs_declaration_required() -> None:
    """§C v39②：`CustomIndicatorDef` 之 `outputs` 必填；缺即設定驗證失敗。"""
    from pydantic import ValidationError

    from momentum.FeatureEngineering.feature_config import CustomIndicatorDef

    with pytest.raises(ValidationError):
        CustomIndicatorDef(name="two_windows", module="tests.feature_engineering.test_ffstat_stable_start",
                           function="_custom_two_windows", params={})


def _custom_two_windows(data: pd.DataFrame) -> pd.DataFrame:
    """r18 codex 反例：一次呼叫回傳兩個不同窗長之欄。"""
    return pd.DataFrame({"short": data["close"].rolling(5).mean(), "long": data["close"].rolling(233).mean()})


def test_custom_indicator_undeclared_output_fails_closed() -> None:
    """§C v39②：回傳欄集合≠宣告集合 ⇒ concat 前 StableMaskError，訊息列引擎、輸出欄與缺少之鍵。"""
    from momentum.FeatureEngineering.atomic.custom_indicators import CustomIndicatorEngine

    data = h.kline_frame(timeframe="12h").iloc[:600]
    definition = {"name": "two_windows", "module": __name__, "function": "_custom_two_windows", "params": {},
                  "outputs": {"short": {"params": {"window": 5}, "period_keys": ["window"]}}}
    with pytest.raises(sm.StableMaskError) as exc:
        CustomIndicatorEngine().compute_all(data, [definition])
    assert "long" in str(exc.value)


# ─────────────────────────────── ② 不傳遞 NaN 之步驟

def test_incomplete_window_mask_winsor_full_window() -> None:
    """Task 2.3 ②：縮尾（第①類，window 252）⇒ 輸出首個有效值＝輸入首個有效值＋251；只遮罩、其後值不變。"""
    import talib

    rsi = talib.RSI(_close("1h"), timeperiod=14)
    first = sm.first_finite_index(rsi)
    fake_winsor_output = rsi.copy()  # 縮尾於界線未定時保留原值 ⇒ 以原值代表其開頭段
    out = sm.mask_incomplete_window(fake_winsor_output, rsi, CONTRACT["non_propagating_steps"]["incomplete_window"]["winsorization"])
    assert sm.first_finite_index(out) == first + 251
    np.testing.assert_array_equal(out[first + 251:], fake_winsor_output[first + 251:])


def test_pointwise_prefix_mask_binary_signal() -> None:
    """Task 2.3 ②（第④類）：binary_signal 之輸出首個有效值＝輸入首個有效值；其後之間歇 NaN 處理不變。"""
    import talib

    rsi = sm.apply_l1_mask(talib.RSI(_close("1h"), timeperiod=14), 0, 50)
    signal = (rsi > 70).astype(float)  # 現行 compute_binary_signal：NaN 比較為 False ⇒ 0
    out = sm.mask_pointwise_prefix(signal, [rsi])
    assert sm.first_finite_index(out) == sm.first_finite_index(rsi)
    np.testing.assert_array_equal(out[50:], signal[50:])


def test_nan_propagation_inventory_complete() -> None:
    """Task 2.3 ②：盤點收據之步驟集合＝AST 列舉 L2–L6.5 與多週期對齊之步驟函式集合（少一即紅），且每步有碼證與分類。"""
    receipts = sorted((REPO / "handoffs" / "run_receipts").glob("*-ffstat-nan-propagation-inventory.json"))
    assert receipts, "缺盤點收據（SPEC Task 2.3 檔案段）"
    inventory = json.loads(receipts[-1].read_text(encoding="utf-8"))
    steps = {row["function"]: row for row in inventory["steps"]}
    expected = _ast_step_functions()
    # r28 codex P1-01：三者須完全相等——AST 閉包、收據、golden 分類表；閉包意外縮小（漏列既有步驟）即紅
    golden = set(json.loads((REPO / "tests" / "_golden" / "ffstat" / "nan_propagation_classes.json")
                            .read_text(encoding="utf-8"))["steps"])
    assert set(steps) == expected, (sorted(expected - set(steps)), sorted(set(steps) - expected))
    assert set(steps) == golden, (sorted(golden - set(steps)), sorted(set(steps) - golden))
    classes = {"propagating", "incomplete_window", "recursive", "cumulative", "pointwise_prefix",
               "not_in_generation_path", "dispatcher", "index_derived", "helper", "column_filter", "mask"}
    for name, row in steps.items():
        assert row["propagates_nan"] in (True, False), name
        assert row["evidence"], name
        assert row["class"] in classes, name
        assert row["propagates_nan"] == (row["class"] == "propagating"), name
        if row["class"] == "dispatcher":
            # r25 codex P1-04／r26 codex P1-01：派發函式之輸出＝其所呼叫之已分類步驟之聯集 ⇒ 函式體須以限定名
            # （同類 self.X／cls.X ⇒ module:Class.X；同模組 X ⇒ module:X）呼叫至少一個非自身之已列步驟
            called = _called_qualified(name)
            assert called & (set(steps) - {name}), name
        if row["class"] in _NO_INLINE_CLASSES:
            # r27 codex P1-01：宣稱不自行產生未穩定值之類別，函式體不得內聯「NaN／未滿窗→有限值」之運算；
            # 有者須改列其非傳遞類（或列 _INLINE_ALLOWED 並附不產輸出值之理由）
            hits = _inline_nan_filling_calls(_function_node(name))
            assert not hits or name in _INLINE_ALLOWED, (name, hits)


# r27 codex P1-01：會把 NaN 或不完整窗變成有限值之運算（方法名）；比較式直接 astype 亦屬之（NaN 比較為 False）
_NAN_FILLING = frozenset({
    "rolling", "ewm", "expanding", "fillna", "ffill", "bfill", "interpolate", "cumsum", "cumprod", "cummax", "cummin",
    "nan_to_num", "where", "clip", "shift", "diff", "pct_change", "rank", "apply", "map_batches", "fill_null", "fill_nan",
    "forward_fill", "backward_fill", "nanmean", "nanstd", "nanquantile", "quantile", "rolling_mean", "rolling_std",
    "rolling_max", "rolling_min", "rolling_sum", "convolve", "lfilter",
})
# index_derived 之輸入為時間索引（無 NaN），由 test_index_derived_step_has_no_warmup 以真實切片驗證，不在此列
_NO_INLINE_CLASSES = frozenset({"dispatcher", "helper", "column_filter"})
# 函式體有上列運算但其結果不成為輸出特徵值者（限定名 → 理由）
_INLINE_ALLOWED = {
    "momentum.FeatureEngineering.preprocessing._hurst_prior:estimate_hurst_rs": "cumsum 算 Hurst 先驗純量（d* 搜尋用）",
    "momentum.FeatureEngineering.preprocessing._non_stationary_cache:NonStationaryCache.make_key": "nan_to_num 只用於快取鍵雜湊",
    "momentum.FeatureEngineering.preprocessing.feature_preprocessor:FeaturePreprocessor._find_min_d": "ffill 於校準值上搜尋 d*，產出 d",
    "momentum.FeatureEngineering.timeframe.multi_tf_generator:MultiTFGenerator._log_gap_source_if_any": "diff 於時間戳記判缺口並記日誌",
}


def _function_node(qualified: str) -> ast.FunctionDef:
    module, qual = qualified.split(":")
    path = REPO / Path(*module.split(".")).with_suffix(".py")
    return _module_functions(ast.parse(path.read_text(encoding="utf-8")))[qual]


def _inline_nan_filling_calls(node: ast.AST) -> List[str]:
    """函式體內 `X.<_NAN_FILLING>(…)` 與 `(比較式).astype(…)` 之呼叫（`名稱@行`）。"""
    hits = []
    for call in ast.walk(node):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
            attr = call.func.attr
            if attr in _NAN_FILLING or (attr == "astype" and isinstance(call.func.value, ast.Compare)):
                hits.append(f"{attr}@{call.lineno}")
    return hits


def test_mutation_dispatcher_inline_rolling_is_caught() -> None:
    """r27 codex P1-01 反例之可證偽版：派發函式先呼叫合法子步驟、再於函式體內以 min_periods=1 之 rolling 自原始
    close 造欄 ⇒ 內聯檢查須命中；只原樣搬移原始欄（無暖機，首個有限值即穩定）不在遮罩語意內，不命中。"""
    import inspect
    import textwrap

    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    node = ast.parse(textwrap.dedent(inspect.getsource(DerivedOperatorEngine.compute_all))).body[0]
    assert not _inline_nan_filling_calls(node)
    injected = ast.parse("_inj = raw_data['close'].rolling(20, min_periods=1).mean()").body[0]
    node.body.insert(0, injected)
    assert _inline_nan_filling_calls(node) == [f"rolling@{injected.lineno}"]
    node.body[0] = ast.parse("_inj = raw_data['close'].to_numpy()").body[0]
    assert not _inline_nan_filling_calls(node)
    node.body[0] = ast.parse("_inj = (raw_data['close'] > 0).astype(float)").body[0]
    assert _inline_nan_filling_calls(node)


def _step_source_files() -> List[Path]:
    """盤點之 AST 來源檔：L2–L6.5 與多週期對齊之子套件，外加 polars_adapter.py。"""
    base = REPO / "momentum" / "FeatureEngineering"
    files: List[Path] = []
    for root in ("operators", "cross_sectional", "meta_features", "preprocessing", "timeframe"):
        files.extend(sorted((base / root).rglob("*.py")))
    files.append(base / "polars_adapter.py")
    return files


def _import_map(tree: ast.AST, module: str) -> Dict[str, str]:
    """模組內 `from X import name [as alias]` 之 alias → X（相對 import 依 module 解析）。"""
    out: Dict[str, str] = {}
    pkg = module.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None or isinstance(node, ast.ImportFrom) and node.level:
            src = node.module or ""
            if node.level:
                parts = pkg.split(".")
                src = ".".join(parts[: len(parts) - node.level + 1] + ([src] if src else []))
            for alias in node.names:
                out[alias.asname or alias.name] = f"{src}:{alias.name}"
    return out


def _module_functions(tree: ast.AST) -> Dict[str, ast.FunctionDef]:
    """模組內函式之限定名 → 節點：類別方法 `Class.f`；非類別、非巢狀於函式者 `f`（含定義於模組層
    `if HAS_NUMBA:`／`try:` 區塊內者，如 `_worldquant_numba._ts_argmax_2d`）。"""
    out: Dict[str, ast.FunctionDef] = {}

    def visit(node: ast.AST, owner: Optional[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, child.name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[f"{owner}.{child.name}" if owner else child.name] = child
            else:
                visit(child, owner)

    visit(tree, None)
    return out


def _called_qualified(qualified: str) -> set:
    """函式體內引用之限定名集合（AST；含呼叫與以值傳遞如 `executor.submit(self.f, …)`）：`self.X`／`cls.X`
    綁定於同一類別；`Class.X`（同模組類別）綁定於該類別；裸名 `X` 依模組之 from-import 解析為來源限定名，
    否則綁定於同一模組；`mod.X`（`from pkg import mod`）⇒ `pkg.mod:X`（r27 codex P1-01）。"""
    module, qual = qualified.split(":")
    path = REPO / Path(*module.split(".")).with_suffix(".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = _module_functions(tree).get(qual)
    if node is None:
        return set()
    owner = qual.split(".")[0] if "." in qual else None
    imports = _import_map(tree, module)
    classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    names = set()
    for ref in ast.walk(node):
        if isinstance(ref, ast.Attribute) and isinstance(ref.value, ast.Name):
            base = ref.value.id
            if base in ("self", "cls") and owner:
                names.add(f"{module}:{owner}.{ref.attr}")
            elif base in classes:
                names.add(f"{module}:{base}.{ref.attr}")
            elif base in imports:
                # `from pkg import mod` ⇒ pkg.mod:X；`from pkg.mod import Class` ⇒ pkg.mod:Class.X（r28 codex P2-02）
                src, imported = imports[base].split(":")
                as_module = REPO / Path(*f"{src}.{imported}".split(".")).with_suffix(".py")
                names.add(f"{src}.{imported}:{ref.attr}" if as_module.exists() else f"{src}:{imported}.{ref.attr}")
        elif isinstance(ref, ast.Name) and isinstance(ref.ctx, ast.Load):
            names.add(imports.get(ref.id, f"{module}:{ref.id}"))
    return names


def test_dispatcher_call_resolution_is_class_bound() -> None:
    """r26 codex P1-01：派發檢查以限定名綁定類別——`_rolling_last_rank_pct` 於 L2（DerivedOperatorEngine）與
    L3（RollingAggregator）同名，L3 派發函式之呼叫集合不得含 L2 之同名方法，反之亦然。"""
    base = "momentum.FeatureEngineering.operators"
    l3 = _called_qualified(f"{base}.rolling_aggregator:RollingAggregator.compute_all")
    assert any(n.startswith(f"{base}.rolling_aggregator:RollingAggregator.") for n in l3)
    assert not any("DerivedOperatorEngine." in n for n in l3)
    l2 = _called_qualified(f"{base}.derived_operators:DerivedOperatorEngine.compute_all")
    assert any(n.startswith(f"{base}.derived_operators:DerivedOperatorEngine.") for n in l2)
    assert not any("RollingAggregator." in n for n in l2)


def test_inventory_closure_reaches_off_prefix_and_nested_steps() -> None:
    """r27 codex P1-01：盤點為呼叫鏈遞移閉包——名稱不合前綴（縮尾核心）、模組層 `if HAS_NUMBA:` 內定義（WQ 核心）、
    polars_adapter 經 import 呼叫、以及 L6.5 公開入口皆須入列。"""
    got = _ast_step_functions()
    fe = "momentum.FeatureEngineering"
    for name in (f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor._winsorize_2d_legacy_equivalent",
                 f"{fe}.operators._worldquant_numba:_ts_argmax_2d",
                 f"{fe}.polars_adapter:polars_l2_derived_momentum",
                 f"{fe}.polars_adapter:polars_l65_winsorization",
                 f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor.transform_registry_groups_to_sink",
                 f"{fe}.preprocessing._numba_transforms:transform_array_fast",
                 # r28 codex P2-02：`from … import TimeframeAligner` 後之 TimeframeAligner.X 解析為類別方法
                 f"{fe}.timeframe.tf_aligner:TimeframeAligner._timeframe_seconds_keys"):
        assert name in got, name


def test_index_derived_step_has_no_warmup() -> None:
    """r25 codex P1-04：index_derived（時間特徵）只由索引算出 ⇒ 真實 1h 切片第 0 列即有限值、與 L1 遮罩無關。"""
    from momentum.FeatureEngineering.meta_features.time_features import TimeFeatureEngine

    index = h.kline_frame(timeframe="1h").index[:500]
    out = TimeFeatureEngine().compute_all(pd.Series(index, index=index))
    assert not out.empty
    assert out.iloc[0].notna().all()


def _ast_step_functions() -> set:
    """L2 operators、L3 rolling、L4 lag、L5 cross_sectional、L6 meta_features、L6.5 preprocessing、多週期 tf_aligner
    之公開計算函式（模組:限定名）。"""
    # r24 codex P1-01：公開與私有之計算／對齊入口皆列（含 _compute_all_streaming、_searchsorted_align、_merge_asof_align）
    # r27 codex P1-01：納入 polars_adapter.py（L2 Polars 批次與 L6.5 Polars 縮尾）與 L6.5 之 _transform* 執行入口
    # 前綴只作種子；再取「種子所呼叫、且定義於來源檔之函式」之遞移閉包——名稱不合前綴之步驟
    # （如 _winsorize_2d_legacy_equivalent、_gaussian_2d）只要在呼叫鏈上即入盤點
    prefixes = ("compute", "_compute", "apply", "_apply", "align", "_align", "_merge", "_searchsorted", "_rolling",
                "_dead", "_variance", "polars_", "_transform")
    defined = set()
    for path in _step_source_files():
        module = ".".join(path.relative_to(REPO).with_suffix("").parts)
        defined |= {f"{module}:{q}" for q in _module_functions(ast.parse(path.read_text(encoding="utf-8")))}
    # 種子＝一切公開函式（L6.5 之 transform／transform_registry_groups* 等入口不合前綴）＋合前綴之私有函式
    out = {q for q in defined if not (n := q.split(":")[1].split(".")[-1]).startswith("_") or n.startswith(prefixes)}
    frontier = set(out)
    while frontier:
        reached = set().union(*(_called_qualified(q) for q in frontier)) & defined
        frontier = reached - out
        out |= frontier
    return out


# ─────────────────────────────── ③④ 無起始日

def test_no_start_stationarity_off_stable_values_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ③：無起始日、平穩化關閉 ⇒ 各欄 stable_start 前全 NaN；鏈上無第②③類者 stable_start 後與凍結基準逐位元組相同。"""
    baseline_path = REPO / CONTRACT["nostart_baseline"]
    assert baseline_path.exists(), "缺無起始日凍結基準（§G：以 FF-STAT 動工前 commit 於獨立 worktree 重凍）"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    block = int(baseline["block_rows"])
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False), start_date=None)
    stable = result.metadata[CONTRACT["stable_start_receipt_key"]]
    exempt = set(baseline.get("chain_has_class_2_or_3", []))
    compared = 0
    for column, blocks in baseline["columns"].items():
        series = _public_column(root, column)
        start = pd.Timestamp(stable[column])
        assert series.loc[:start - pd.Timedelta(microseconds=1)].isna().all(), column
        if column in exempt:
            continue
        first_full_block = -(-int((series.index < start).sum()) // block)
        values = series.to_numpy(dtype=np.float64)
        for b in range(first_full_block, len(blocks)):
            chunk = values[b * block:(b + 1) * block]
            assert hashlib.sha256(chunk.tobytes()).hexdigest() == blocks[b], (column, b)
            compared += 1
    assert compared > 0


def test_no_start_calibration_rows_masked_from_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：無起始日、平穩化開啟 ⇒ 校準值＝各欄最早 N 個有效值（spy）；該 N 列於公開輸出（含衍生欄）全 NaN。"""
    calls: List[Any] = []
    original = sm.calibration_rows_no_start

    def spy(values: np.ndarray, n: int):
        rows = original(values, n)
        calls.append(rows)
        return rows

    monkeypatch.setattr(sm, "calibration_rows_no_start", spy)
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(), start_date=None)
    assert calls, "未以 calibration_rows_no_start 取校準列"
    assert result.metadata[h.META["output_start_source"]] == "per_column"
    assert h.META["effective_output_start"] not in result.metadata  # v44：per_column 不寫
    for column, record in h.decisions(result).items():
        if record.get("calibration_end") is None:
            continue
        out = _public_column(root, column)
        window = out.loc[:pd.Timestamp(record["calibration_end"])]
        assert window.isna().all(), column


def _public_column(root: Path, column: str) -> pd.Series:
    import pyarrow.parquet as pq

    for p in sorted(root.rglob("*.parquet")):
        frame = pq.read_table(p).to_pandas()
        if column in frame.columns:
            idx = pd.to_datetime(frame["timestamp"], unit="ms", utc=True) if "timestamp" in frame.columns else frame.index
            return pd.Series(frame[column].to_numpy(), index=idx)
    raise AssertionError(f"找不到欄 {column}")


def test_no_start_leak_after_calibration_rows_does_not_change_decisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：改動校準列之後之 close（×1.5）⇒ 決策與 d 不變。"""
    h.prepare_stat_env(monkeypatch, tmp_path / "a")
    _r, _f, base = h.run_stat(tmp_path / "a", h.stat_payload(), start_date=None)
    klines = h.kline_copy(tmp_path / "b")
    latest_cal_end = max(pd.Timestamp(r["calibration_end"]) for r in h.decisions(base).values() if r.get("calibration_end"))
    h.scale_kline_close(klines, (latest_cal_end + pd.Timedelta(hours=1)).isoformat(), "2100-01-01", 1.5)
    h.prepare_stat_env(monkeypatch, tmp_path / "b")
    _r2, _f2, moved = h.run_stat(tmp_path / "b", h.stat_payload(), start_date=None, kline_dir=str(klines))
    for column, record in h.decisions(base).items():
        other = h.decisions(moved)[column]
        assert (record["fracdiff"], record["adf_differenced"], record["d"]) == (other["fracdiff"], other["adf_differenced"], other["d"]), column


def test_no_start_change_inside_calibration_rows_changes_some_decision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：改動校準列內之 close ⇒ 至少一欄決策或 d 改變（證明確實讀校準列）。"""
    h.prepare_stat_env(monkeypatch, tmp_path / "a")
    _r, _f, base = h.run_stat(tmp_path / "a", h.stat_payload(), start_date=None)
    klines = h.kline_copy(tmp_path / "b")
    first = h.kline_frame().index[0]
    h.scale_kline_close(klines, first.isoformat(), (first + pd.Timedelta(days=120)).isoformat(), 3.0)
    h.prepare_stat_env(monkeypatch, tmp_path / "b")
    _r2, _f2, moved = h.run_stat(tmp_path / "b", h.stat_payload(), start_date=None, kline_dir=str(klines))
    changed = [c for c, r in h.decisions(base).items()
               if (r["fracdiff"], r["d"]) != (h.decisions(moved)[c]["fracdiff"], h.decisions(moved)[c]["d"])]
    assert changed


def test_no_start_insufficient_history_column_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：全史有效值不足 N 之欄 ⇒ calibration_insufficient_history、未平穩化、partial、有效值照常輸出。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    klines = h.kline_copy(tmp_path)
    last = h.kline_frame().index[-1]
    h.drop_kline_rows_before(klines, (last - pd.Timedelta(hours=700)).isoformat(), symbol=h.SYMBOL)
    payload = h.stat_payload()
    payload["preprocessing"]["calibration_bars"] = 500
    root, _factory, result = h.run_stat(tmp_path, payload, start_date=None, kline_dir=str(klines))
    flagged = [c for c, r in h.decisions(result).items() if h.EVENTS["calibration_insufficient"] in " ".join(r["events"])]
    assert flagged
    assert result.metadata.get("quality_status") == "partial"
    for column in flagged:
        assert not h.decisions(result)[column]["fracdiff"]
        assert _public_column(root, column).notna().any(), column


# ─────────────────────────────── ⑤ 有起始日

def test_with_start_far_no_warmup_insufficient(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑤：起始日離資料起點足夠遠 ⇒ 全部欄首個有效值 ≤ 起始日、無 warmup_insufficient_history。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False))
    assert h.EVENTS["warmup_insufficient"] not in json.dumps(result.metadata.get("failure_reasons", []))
    start = pd.Timestamp(h.WINDOW[0], tz="UTC")
    for column, ts in result.metadata[CONTRACT["stable_start_receipt_key"]].items():
        assert pd.Timestamp(ts) <= start, column


def test_with_start_near_data_start_flags_slow_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑤：起始日取資料起點後 100 列 ⇒ 慢欄記 warmup_insufficient_history、partial、起始日至首個有效值為 NaN，快欄照常。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    index = h.kline_frame().index
    start = index[100].isoformat()
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False), start_date=start)
    reasons = json.dumps(result.metadata.get("failure_reasons", []))
    assert h.EVENTS["warmup_insufficient"] in reasons
    assert result.metadata.get("quality_status") == "partial"
    starts = {c: pd.Timestamp(t) for c, t in result.metadata[CONTRACT["stable_start_receipt_key"]].items()}
    assert any(t > pd.Timestamp(start) for t in starts.values())
    assert any(t <= pd.Timestamp(start) for t in starts.values())
    receipt = result.metadata.get(CONTRACT["warmup_doubling"]["key"])
    assert receipt and set(CONTRACT["warmup_doubling"]["fields"]) <= set(receipt)


# ─────────────────────────────── ⑦ 死欄純函式與欄集合差異

def test_dead_filter_mask_invariant_real_12h() -> None:
    """Task 2.3 ⑦：真實 BTC 12h close 前 1,540 列設 NaN（r13 codex 反例）⇒ L3 門檻下不判死欄。"""
    close = _close("12h")[:1696].copy()
    close[:1540] = np.nan
    decision = sm.dead_column_decision(close, nan_rate_threshold=CONTRACT["dead_filter_thresholds"]["l3_nan_rate"],
                                       min_valid=CONTRACT["dead_filter_thresholds"]["l3_min_effective_n"])
    assert not decision.dead
    assert decision.nan_rate == 0.0 and decision.valid_count == 156


@pytest.mark.parametrize("valid, threshold, dead", [(29, 30, True), (30, 30, False), (99, 100, True), (100, 100, False)])
def test_dead_filter_threshold_boundaries(valid: int, threshold: int, dead: bool) -> None:
    """Task 2.3 ⑦：L3 30、L7 100 之 29／30、99／100 邊界（真實 close 取段）。"""
    values = _close("1h")[:valid].copy()
    assert sm.dead_column_decision(values, nan_rate_threshold=None, min_valid=threshold).dead is dead


def test_dead_filter_shared_by_l3_and_l7(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑦：L3 與 L7 皆呼叫同一死欄純函式（spy），門檻依呼叫端。"""
    seen: List[Any] = []
    original = sm.dead_column_decision

    def spy(values, *, nan_rate_threshold, min_valid):
        seen.append((nan_rate_threshold, min_valid))
        return original(values, nan_rate_threshold=nan_rate_threshold, min_valid=min_valid)

    monkeypatch.setattr(sm, "dead_column_decision", spy)
    h.prepare_stat_env(monkeypatch, tmp_path)
    h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False))
    thresholds = CONTRACT["dead_filter_thresholds"]
    assert (thresholds["l3_nan_rate"], thresholds["l3_min_effective_n"]) in seen
    assert (None, thresholds["l7_min_valid_samples_default"]) in seen


def test_column_set_delta_canonical_and_permutation_invariant() -> None:
    """Task 2.3 ⑦（v35）：同一 delta 之鍵序與列序置換後 sha256 不變；欄名含非 ASCII 與 `,:"` 亦然；不同 delta 不同 digest。"""
    before = ["close_trend_EMA_233", "ohlc_pattern_Consensus", "測試,欄:\"x\""]
    after = ["close_trend_EMA_233", "新欄"]
    reasons = {"ohlc_pattern_Consensus": "stable_samples_below_min", "測試,欄:\"x\"": "stable_samples_below_min",
               "新欄": "nan_rate_rule"}
    delta = sm.column_set_delta(before, after, reasons)
    permuted = {"reasons": dict(reversed(list(delta["reasons"].items()))), "removed": list(reversed(delta["removed"])),
                "added": list(delta["added"])}
    assert sm.delta_sha256(sm.column_set_delta(after, before[::-1], {k: v for k, v in reasons.items()})) != sm.delta_sha256(delta)
    assert sm.canonical_delta_bytes(delta) == json.dumps(delta, sort_keys=True, ensure_ascii=False,
                                                         separators=(",", ":")).encode("utf-8")
    assert sm.delta_sha256(sm.column_set_delta(before[::-1], after[::-1], reasons)) == sm.delta_sha256(delta)
    assert sorted(permuted["removed"]) == delta["removed"]
    empty = sm.column_set_delta(after, after, {})
    assert empty == CONTRACT["column_set_delta"]["empty"]
    joined = "\n".join(sorted(set(after), key=lambda s: s.encode("utf-8"))).encode("utf-8")
    assert sm.column_set_sha256(after[::-1]) == hashlib.sha256(joined).hexdigest()


def test_column_set_delta_unknown_reason_rejected() -> None:
    """Task 2.3 ⑦（v36）：原因值不在封閉集合 ⇒ DeltaReasonError；差異欄缺原因亦同。"""
    with pytest.raises(sm.DeltaReasonError):
        sm.column_set_delta(["a", "b"], ["a"], {"b": "constant_rule"})
    with pytest.raises(sm.DeltaReasonError):
        sm.column_set_delta(["a", "b"], ["a"], {})
    assert tuple(CONTRACT["column_set_delta"]["reasons"]) == sm.DELTA_REASONS


def test_column_set_approval_matches_delta() -> None:
    """Task 2.3 ⑦：核可紀錄之 delta sha256＝本次 delta sha256；delta 非空而無核可紀錄即紅。"""
    rr = REPO / "handoffs" / "run_receipts"
    deltas = sorted(rr.glob("*-ffstat-column-set-delta.json"))
    assert deltas, "缺欄集合差異收據"
    delta_doc = json.loads(deltas[-1].read_text(encoding="utf-8"))
    digest = sm.delta_sha256(delta_doc["delta"])
    assert digest == delta_doc["delta_sha256"]
    if delta_doc["delta"] != CONTRACT["column_set_delta"]["empty"]:
        approvals = sorted(rr.glob("*-ffstat-column-set-approval.json"))
        assert approvals, "delta 非空而無使用者核可紀錄"
        approval = json.loads(approvals[-1].read_text(encoding="utf-8"))
        assert set(CONTRACT["column_set_delta"]["approval_fields"]) <= set(approval)
        assert approval["delta_sha256"] == digest


# ─────────────────────────────── ⑧⑨⑩ 多週期、快取、開關

def test_multi_tf_mask_applied_before_alignment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑧：1h＋12h 無起始日 ⇒ 12h 欄於對齊後之首個有效值時間＝其 12h stable_start 可被 1h 取用之時間。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(["1h", "12h"], fracdiff=False, adf=False), start_date=None)
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    stable = result.metadata[CONTRACT["stable_start_receipt_key"]]
    twelve = [c for c in stable if "12h" in c]
    assert twelve
    idx_12h = h.kline_frame(timeframe="12h").index
    idx_1h = h.kline_frame(timeframe="1h").index
    for column in twelve:
        # 預期：12h 於其 stable_start 首個有效之列，經同一對齊器對到 1h 後之第一個有值時間（r24 codex P1-03：精確相等）
        marker = pd.DataFrame({"m": np.where(idx_12h >= pd.Timestamp(stable[column]), 1.0, np.nan)}, index=idx_12h)
        marker.index.name = "timestamp"
        aligned = TimeframeAligner.align_to_primary(marker.reset_index(), "12h", pd.Series(idx_1h), "1h")
        expected = aligned["m"].first_valid_index()
        series = _public_column(root, column)
        assert series.first_valid_index() == expected, column
        assert series.loc[:expected - pd.Timedelta(microseconds=1)].isna().all(), column


def test_config_hash_includes_warmup_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑨：設定 hash 納入 warmup_policy ⇒ 改動政策字串即改變 hash（改前快取未命中）。"""
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(h.stat_payload())
    base = factory._compute_config_hash(config, h.SYMBOL, h.PRIMARY_TF, start_date=None, end_date=None)
    monkeypatch.setattr(sm, "WARMUP_POLICY", "per_column_stable_v0")
    assert factory._compute_config_hash(config, h.SYMBOL, h.PRIMARY_TF, start_date=None, end_date=None) != base


def test_warmup_trim_switch_removed() -> None:
    """Task 2.3 ⑩：`FFACT_WARMUP_TRIM` 與 `is_warmup_trim_enabled` 於生產碼 0 命中。"""
    hits = []
    for root in ("momentum", "api"):
        for path in (REPO / root).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "FFACT_WARMUP_TRIM" in text or "is_warmup_trim_enabled" in text:
                hits.append(str(path.relative_to(REPO)))
    assert not hits, hits


# ─────────────────────────────── 12h 逐輸出點、每個 L1 輸出皆經契約

def test_every_l1_output_column_passes_output_point_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ①（v38）：以真實 BTC 12h 跑預設全設定之 L1 ⇒ 每個 L1 輸出欄皆有一次 instance_k 呼叫（未驗即紅）。"""
    seen: List[str] = []
    original = sm.instance_k

    def spy(spec, table, upstream_k=None):
        seen.append(spec.column)
        return original(spec, table, upstream_k)

    monkeypatch.setattr(sm, "instance_k", spy)
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.factories import create_feature_factory

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    config = ConfigManager().get_merged_config()
    raw = factory._layer0_data_ingestion(h.SYMBOL, "12h", config)
    layer1 = factory._layer1_atomic_indicators(raw, config).data
    missing = sorted(set(layer1.columns) - set(seen))
    assert not missing, missing[:20]
    receipts = sorted((REPO / "handoffs" / "run_receipts").glob("*-ffstat-12h-output-points.json"))
    assert receipts, "缺 12h 逐輸出點收據（列已驗與未驗之輸出點）"
    doc = json.loads(receipts[-1].read_text(encoding="utf-8"))
    assert not doc["unverified"], doc["unverified"][:20]


# ─────────────────────────────── 邊界（Task 2.3 邊界①–④，接續既有編號 22–25）

def test_boundary_22_sparse_column_calibrates_on_first_n_valid() -> None:
    """Task 2.3 邊界①：稀疏欄之校準取遮罩後最早 N 個有效值（間歇 NaN 跳過）。"""
    values = _close("1h")[:3000].copy()
    values[::3] = np.nan
    rows = sm.calibration_rows_no_start(values, 500)
    finite_positions = np.flatnonzero(np.isfinite(values))
    assert rows == (int(finite_positions[0]), int(finite_positions[499]))


def test_boundary_23_cumulative_listed_start_dependent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 邊界②：累積型欄（OBV、AD）列入 start_dependent_columns。"""
    payload = h.stat_payload(fracdiff=False, adf=False)
    payload["atomic_indicators"]["volume"] = {"enabled": True, "indicators": [{"name": "OBV", "enabled": True}]}
    h.prepare_stat_env(monkeypatch, tmp_path)
    _root, _factory, result = h.run_stat(tmp_path, payload)
    listed = result.metadata[CONTRACT["start_dependent_key"]]
    assert any("OBV" in c for c in listed)


def test_boundary_24_reference_symbol_origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 邊界③：參考標的起點晚於主標的 ⇒ cs 欄之 stable_start 不早於參考標的之首列。"""
    klines = h.kline_copy(tmp_path)
    ref_start = h.kline_frame(symbol="ETHUSDT").index[0] + pd.Timedelta(days=60)
    h.drop_kline_rows_before(klines, ref_start.isoformat(), symbol="ETHUSDT")
    h.prepare_stat_env(monkeypatch, tmp_path)
    _root, _factory, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False, cross_sectional=True),
                                         start_date=None, kline_dir=str(klines))
    for column, ts in result.metadata[CONTRACT["stable_start_receipt_key"]].items():
        if column.startswith("cs_"):
            assert pd.Timestamp(ts) >= ref_start, column


# Task 2.3 邊界④（帶 start_date ⇒ output_start_source == "user"、effective_output_start＝該日）之唯一具名測試為既有
# test_ffstat_calibration.py::test_boundary_11_user_start_source_is_user（r24 codex P2-05：不另建重複落點）；
# per_column 不寫 effective_output_start 由 test_no_start_calibration_rows_masked_from_output 斷言。


# ─────────────────────────────── ⑪ 四條執行路徑

_PATHS = {
    "frame": {"FFACT_USE_CGSA": "0"},
    "cgsa_serial": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0"},
    "cgsa_parallel": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "1"},
}


def _path_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> Dict[str, Any]:
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    env = _PATHS["cgsa_serial" if mode == "resume" else mode]
    h.prepare_stat_env(monkeypatch, tmp_path, **env)
    payload = h.stat_payload(["1h", "12h"])
    root, _factory, result = h.run_stat(tmp_path, payload, start_date=None)
    if mode == "resume":
        # r25 codex P1-01：第二次須真走 CGSA 續跑——令快取探測落空，並斷言 resume_from_manifest 被呼叫
        resumed: List[Any] = []
        real_resume = ColumnGroupRegistry.resume_from_manifest  # classmethod（已綁定）

        def spy_resume(cls, work_dir):
            resumed.append(1)
            return real_resume(work_dir)

        monkeypatch.setattr(FeatureFactory, "_try_load_cache", lambda self, *a, **k: None)
        monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(spy_resume))
        root, _factory, result = h.run_stat(tmp_path, payload, start_date=None, force_regenerate=False)
        assert resumed, "resume 路徑未呼叫 ColumnGroupRegistry.resume_from_manifest"
    return {"root": root, "result": result}


@pytest.mark.parametrize("mode", ["cgsa_serial", "cgsa_parallel", "resume"])
def test_paths_same_stable_start_and_masks(mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑪（r24 codex P1-02）：frame、CGSA 序列、CGSA 平行、resume 之 stable_start、校準列與公開輸出全同。"""
    key = CONTRACT["stable_start_receipt_key"]
    base = _path_run(tmp_path / "frame", monkeypatch, "frame")
    other = _path_run(tmp_path / mode, monkeypatch, mode)
    assert other["result"].metadata[key] == base["result"].metadata[key]
    strip = lambda d: {c: {k: v for k, v in r.items() if k != "dstar_cache_hit"} for c, r in d.items()}  # noqa: E731
    assert strip(h.decisions(other["result"])) == strip(h.decisions(base["result"]))
    assert h.base_fingerprints(other["root"]) == h.base_fingerprints(base["root"])


# ─────────────────────────────── ⑫ run_ic_first（v29–v31）

def _ic_first_kwargs(tmp_path: Path) -> Dict[str, Any]:
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    return {"storage": FeatureStorage(str(tmp_path / "ic_first")), "persist": True}


def _factory_and_config():
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    return factory, factory._resolve_config(h.stat_payload())


def test_run_ic_first_requires_start_date_when_stationarizing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v29）：平穩化開啟而 start_date 為 None ⇒ CalibrationError（field＝output_start）、零寫入。"""
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    kwargs = _ic_first_kwargs(tmp_path)
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError) as exc:
        factory.run_ic_first(h.SYMBOL, h.PRIMARY_TF, config, start_date=None, end_date=h.WINDOW[1], **kwargs)
    assert getattr(exc.value, "field", None) == "output_start"
    assert h.snapshot_tree(tmp_path) == before


def test_run_ic_first_rejects_config_hash_when_stationarizing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v29）：平穩化開啟而傳入 config_hash ⇒ CalibrationError（field＝config_hash）、零寫入。"""
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    kwargs = _ic_first_kwargs(tmp_path)
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError) as exc:
        factory.run_ic_first(h.SYMBOL, h.PRIMARY_TF, config, start_date=h.WINDOW[0], end_date=h.WINDOW[1],
                             config_hash="deadbeef", **kwargs)
    assert getattr(exc.value, "field", None) == "config_hash"
    assert h.snapshot_tree(tmp_path) == before


def test_run_ic_first_uses_own_window_not_previous(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v29）：同一 factory 先生成 A 窗再生成 B 窗，run_ic_first 帶 A 之起訖 ⇒ 校準上界 < A 起始日、
    lease hash＝以 A 起訖重算之設定 hash；預設不相干之 _current_output_window／_current_config_hash 亦同。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    a_start, a_end = h.WINDOW
    b_start = (pd.Timestamp(a_end) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    b_end = (pd.Timestamp(a_end) + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    factory._storage = FeatureStorage(str(tmp_path / "gen"))
    factory.generate_features(h.SYMBOL, h.PRIMARY_TF, config_override=h.stat_payload(), start_date=a_start, end_date=a_end)
    factory.generate_features(h.SYMBOL, h.PRIMARY_TF, config_override=h.stat_payload(), start_date=b_start, end_date=b_end)
    expected_hash = factory._compute_config_hash(config, h.SYMBOL, h.PRIMARY_TF, start_date=a_start, end_date=a_end)
    for preset in (False, True):
        if preset:
            factory._current_output_window = object()
            factory._current_config_hash = "unrelated"
        leases: List[Any] = []
        try:
            h.ic_first_to_l65(factory, config, start_date=a_start, end_date=a_end, lease_sink=leases,
                              **_ic_first_kwargs(tmp_path / str(preset)))
            decisions = getattr(factory, CONTRACT["factory_decisions_attr"])
            assert all(pd.Timestamp(d["calibration_end"]) < pd.Timestamp(a_start, tz="UTC")
                       for d in decisions.values() if d.get("calibration_end")), preset
            # r25 codex P1-02：RunLease 無 __str__，以 lease.path 之檔名比對設定 hash
            assert leases and any(expected_hash in lease.path.name for lease in leases), preset
        finally:
            for lease in leases:  # r25 codex P1-03：釋放 exclusive lease，避免下一迭代 RunBusyError
                lease.release()


@pytest.mark.parametrize("ending", ["preflight_error", "l1_l6_error", "success"])
def test_run_ic_first_restores_state_on_all_endings(ending: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v30）：平穩化開啟之 run_ic_first 結束後（前置關卡失敗、L1–L6 失敗、成功）
    `_current_output_window` 與 `_current_config_hash` 皆與呼叫前為同一物件（is）。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    factory._storage = FeatureStorage(str(tmp_path / "gen"))
    factory.generate_features(h.SYMBOL, h.PRIMARY_TF, config_override=h.stat_payload(), start_date=h.WINDOW[0], end_date=h.WINDOW[1])
    window_before, hash_before = factory._current_output_window, factory._current_config_hash
    w1_start = (pd.Timestamp(h.WINDOW[1]) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    w1_end = (pd.Timestamp(h.WINDOW[1]) + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    if ending == "preflight_error":
        monkeypatch.setattr(FeatureFactory, "run_calibration_preflight",
                            lambda *a, **k: (_ for _ in ()).throw(CalibrationError("injected")))
    elif ending == "l1_l6_error":
        monkeypatch.setattr(FeatureFactory, "_run_l1_l6_for_ic_first",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
    try:
        h.ic_first_to_l65(factory, config, start_date=w1_start, end_date=w1_end, **_ic_first_kwargs(tmp_path))
    except (CalibrationError, RuntimeError):
        assert ending != "success"
    assert factory._current_output_window is window_before
    assert factory._current_config_hash is hash_before


def test_retired_tests_absent_and_replaced() -> None:
    """§V 防假綠：退役表中之舊測試已不在原檔，且其接替測試存在。"""
    table = json.loads((REPO / CONTRACT["retired_tests_path"]).read_text(encoding="utf-8"))
    for row in table["retired"]:
        old_file, old_name = row["test"].split("::")
        new_file, new_name = row["replacement"].split("::")
        assert f"def {old_name}(" not in (REPO / old_file).read_text(encoding="utf-8"), row["test"]
        assert f"def {new_name}(" in (REPO / new_file).read_text(encoding="utf-8"), row["replacement"]
        assert row["reason"], row["test"]


# ─────────────────────────────── §V mutants（v32–v42）

def test_mutation_l1_mask_removed_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹⁴：刪 L1 遮罩（apply_l1_mask 原樣回傳）⇒ ① 必紅。"""
    monkeypatch.setattr(sm, "apply_l1_mask", lambda values, origin, k: np.asarray(values, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_l1_mask_first_valid_is_origin_plus_k("1h")


def test_mutation_k_by_params_ignored_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v46：instance_k 忽略 k_by_params（一律比例公式）⇒ 實測根數優先測試必紅。"""
    stripped = {name: {k: v for k, v in entry.items() if k != "k_by_params"} for name, entry in _table().items()}
    original = sm.instance_k
    monkeypatch.setattr(sm, "instance_k", lambda spec, table, upstream_k=None: original(spec, stripped, upstream_k))
    with pytest.raises(AssertionError):
        test_l1_mask_k_by_params_preferred_over_factor()


def test_mutation_whole_indicator_max_period_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v37：K 改取整個指標之最大週期（EMA_5 亦 336）⇒ 逐呼叫測試必紅。"""
    monkeypatch.setattr(sm, "instance_k", lambda spec, table, upstream_k=None: math.ceil(233 * _factor(spec.indicator)))
    with pytest.raises(AssertionError):
        test_l1_mask_per_call_k_ema5_vs_ema233()


def test_mutation_winsor_unmasked_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹⁵：縮尾輸出不遮 ⇒ ② 必紅。"""
    monkeypatch.setattr(sm, "mask_incomplete_window", lambda output, input_values, window: np.asarray(output, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_incomplete_window_mask_winsor_full_window()


def test_mutation_pointwise_prefix_unmasked_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦²⁰：第④類不遮 ⇒ ② 必紅。"""
    monkeypatch.setattr(sm, "mask_pointwise_prefix", lambda output, inputs: np.asarray(output, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_pointwise_prefix_mask_binary_signal()


def test_mutation_calibration_rows_not_masked_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹¹（v32）：校準列取法錯位（取最末 N 個）⇒ 邊界① 必紅。"""
    monkeypatch.setattr(sm, "calibration_rows_no_start",
                        lambda values, n: (int(np.flatnonzero(np.isfinite(values))[-n]), int(np.flatnonzero(np.isfinite(values))[-1])))
    with pytest.raises(AssertionError):
        test_boundary_22_sparse_column_calibrates_on_first_n_valid()


def test_mutation_dead_filter_full_denominator_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹⁸／⑦²²：死欄 NaN 率分母改回全列 ⇒ ⑦ 反例必紅。"""
    def full_denominator(values, *, nan_rate_threshold, min_valid):
        arr = np.asarray(values, dtype=float)
        rate = float(np.isnan(arr).mean())
        valid = int(np.isfinite(arr).sum())
        dead = (nan_rate_threshold is not None and rate > nan_rate_threshold) or valid < min_valid
        return sm.DeadDecision(dead=dead, reason=None, nan_rate=rate, valid_count=valid)

    monkeypatch.setattr(sm, "dead_column_decision", full_denominator)
    with pytest.raises(AssertionError):
        test_dead_filter_mask_invariant_real_12h()


def test_mutation_delta_non_canonical_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v35：delta 序列化不排序鍵 ⇒ 置換不變測試必紅。"""
    monkeypatch.setattr(sm, "canonical_delta_bytes", lambda delta: json.dumps(delta, ensure_ascii=False).encode("utf-8"))
    with pytest.raises(AssertionError):
        test_column_set_delta_canonical_and_permutation_invariant()


def test_mutation_unknown_reason_accepted_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v36：接受第三種原因值 ⇒ 必紅。"""
    monkeypatch.setattr(sm, "DELTA_REASONS", ("nan_rate_rule", "stable_samples_below_min", "constant_rule"))
    # 內層以 pytest.raises 斷言；mutant 下「未拋」為 pytest 之 Failed（非 AssertionError 子類），兩者皆算抓到
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        test_column_set_delta_unknown_reason_rejected()


def test_mutation_config_hash_without_policy_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹²（v32）：設定 hash 不含 warmup_policy ⇒ ⑨ 必紅。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    original = FeatureFactory._compute_config_hash

    def hash_ignoring_policy(self, *a, **k):
        saved = sm.WARMUP_POLICY
        try:
            sm.WARMUP_POLICY = "fixed"
            return original(self, *a, **k)
        finally:
            sm.WARMUP_POLICY = saved

    monkeypatch.setattr(FeatureFactory, "_compute_config_hash", hash_ignoring_policy)
    with pytest.raises(AssertionError):
        test_config_hash_includes_warmup_policy(monkeypatch)
