"""FF-NAME Task 2.6 — 值不變驗收（docs/FFNAME_SPEC.md §G、Task 2.6）。🔴 真實 kline reference run（重型；單組串行）。

§G 通過條件（v13）：①映射後欄集合相等（例外只准⑤之 L2 合併差集與⑥之新增 lag 欄，兩者逐筆列入收據）②每欄四雜湊全等 ③改名數 > 0
④新 run 全部欄名 parse 成功且 `format(parse(n)) == n` ⑤L2 配對簽名集合經映射後相等，差集只准為「同 canonical 身分之
舊兩分支重複」且逐筆列入收據 ⑥L4 lag 輸入集合＝L1 群組欄＋raw 欄（`volume_*_volume_VolumeMA-Ratio_*`、
`ohlc_*_pattern_BullishCount_*` 由此新增 lag），新增 lag 欄逐筆列入收據並驗其值＝輸入位移
⑦manifest `feature_naming_version == CURRENT`。收據 `handoffs/run_receipts/ffname-value-invariance.json` 之值雜湊不符數 == 0。
v17：⑥ lag 輸入＝L1 原子欄（不含 `*_L65`、扣 cascade 黑名單）＋raw 欄，位移 oracle 以同設定但關閉縮尾之小 run 比對
（同週期 raw 與合成 raw 依產生端同一來源，不略過）；⑧ L1 分群單一規則、欄序以「欄集合＋各群組成員」比對，
合併之舊群組列入收據並由本測試重算。
邊界：任一通過條件不等 ⇒ FAIL（回本 Phase，不得改 golden 遷就）。不以欄數相等代替逐欄雜湊。
mutation：§V ⑫§G 映射改為字串 replace（⑤必紅）。
"""

from __future__ import annotations

import collections
import copy
import fnmatch
import json
import re
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pytest

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.feature_reader import FeatureReader
from tests.feature_engineering.ffname_helpers import (
    BASELINE_PATH,
    G6_GLOBS,
    VALUE_RECEIPT,
    drop_last_op,
    group_layer,
    last_op_name,
    load_freeze_module,
    ops_tuple,
    roundtrip_ok,
)
from tests.feature_engineering.fftfmeta_golden_helpers import prepare_env

freeze = load_freeze_module()
_FP_KEYS = ("dtype", "shape", "nan_sha256", "value_sha256")


@pytest.fixture(scope="module")
def baseline() -> Dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def current(tmp_path_factory) -> Dict[str, Any]:
    tmp = tmp_path_factory.mktemp("ffname_value_invariance")
    with pytest.MonkeyPatch.context() as mp:
        prepare_env(mp, tmp, FFACT_MULTI_TF_PARALLEL="0")
        return freeze.run_reference(tmp, record_parts=False)


def oracle_payload() -> Dict[str, Any]:
    """SPEC v17 §G ⑥ 位移 oracle 之小 run 設定：reference main 之同一 timeframes／data_sources／L4／前處理，
    只關閉縮尾（L6.5 逐欄後處理，reference 開縮尾時落盤值為截尾界）；atomic 縮為新增 lag 兩家族所需之 volume
    （VolumeMA-Ratio 為引擎固定輸出）與 pattern（Bullish／BearishCount），L2／L3／L6 關閉以縮短時間。"""
    payload = copy.deepcopy(freeze.reference_payloads()["main"])
    ai = payload["atomic_indicators"]
    for key in list(ai):
        ai[key] = {"enabled": False}
    ai["trend"] = {"enabled": True, "indicators": [{"name": "EMA", "periods": [8]}]}
    ai["volume"] = {"enabled": True, "indicators": [{"name": "OBV"}]}
    ai["pattern"] = {"enabled": True, "indicators": [{"name": "CDLDOJI"}, {"name": "CDLENGULFING"}]}
    payload["operators"] = {"enabled": False}
    payload["rolling_aggregation"] = {"enabled": False}
    payload["meta_features"] = {"enabled": False}
    payload["preprocessing"]["winsorization"] = {"enabled": False}
    return payload


@pytest.fixture(scope="module")
def inverse_mapping(baseline) -> Dict[str, str]:
    """新名（標記後）→ 舊名（baseline 零件推導之映射之反函數）。"""
    return {new: old for old, new in _mapping(baseline).items()}


@pytest.fixture(scope="module")
def oracle_run(tmp_path_factory, inverse_mapping) -> Dict[str, Any]:
    """SPEC v17 §G ⑥：同設定但關閉縮尾之小真實 kline run（隔離同 prepare_env）；期間攔截 L4 輸入供非 raw 新增 lag 欄之
    完整 oracle（審查 r13）。回傳 `{run, columns}`。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader as _Reader

    spec = freeze._reference_spec()
    tmp = tmp_path_factory.mktemp("ffname_lag_oracle")
    with pytest.MonkeyPatch.context() as mp:
        prepare_env(mp, tmp, FFACT_MULTI_TF_PARALLEL="0")
        from tests.feature_engineering.ffstat_helpers import prepare_stat_env

        prepare_stat_env(mp, tmp / "run")
        LAG_INPUT_CAPTURES.clear()
        install_lag_input_capture(mp, inverse_mapping)
        root, _factory, result = freeze._generate(tmp / "run", oracle_payload(), spec["symbol"], spec["primary_tf"],
                                                  spec["window"])
    config_hash = str(result.metadata["config_hash"])
    run = {"base": str(root), "symbol": spec["symbol"], "tf": spec["primary_tf"], "config_hash": config_hash}
    manifest = _Reader(str(root)).load_manifest_v2(run["symbol"], run["tf"], config_hash, artifact_kind="raw",
                                                   allow_partial=True)
    columns = [c for g in manifest["artifacts"]["raw"]["groups"].values() for c in g["columns"]]
    return {"run": run, "columns": columns}


def _parts(baseline: Dict[str, Any]):
    return {row["old_name"]: freeze.NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                                                  "ops": tuple(row.get("ops") or ())})
            for row in baseline["parts"]}


def _mapping(baseline: Dict[str, Any]) -> Dict[str, str]:
    parts = _parts(baseline)
    return freeze.derive_mapping(parts, {k: p.tf for k, p in parts.items()})


def _l2_merge_dups(baseline, current, mapping) -> Set[str]:
    """舊兩分支重複：多個舊名映到同一新名者（同 canonical 身分），除第一筆外之舊名。"""
    seen: Dict[str, str] = {}
    dups: Set[str] = set()
    for old in sorted(baseline["columns"]):
        new = mapping[old]
        if new in seen:
            dups.add(old)
        else:
            seen[new] = old
    return dups


def _new_lag_cols(current: Dict[str, Any], mapped: Set[str]) -> Set[str]:
    """⑥ 新增 lag 欄：新 run 有、映射集無，且最外層 op 為 Lag、輸入（去 Lag）屬 L1 群組欄或 raw 欄。"""
    groups = current["manifest_groups"]
    l1 = {c for gid, cols in groups.items() if group_layer(gid) == "L1" for c in cols}
    out = set()
    for c in current["columns"]:
        if c in mapped:
            continue
        ident = fn.parse_feature_name(c)
        if last_op_name(ident) != "Lag":
            continue
        base = drop_last_op(ident)
        if fn.format_feature_name(base) in l1 or base.category == "raw":
            out.add(c)
    return out


def cond1(baseline, current, mapping) -> List[str]:
    """①：映射後欄集合相等；例外只准⑤之 L2 合併差集（多舊名映到同一新名，須皆為 derived）與⑥之新增 lag 欄。"""
    mapped = {mapping[o] for o in baseline["columns"]}
    cur = set(current["columns"])
    extra = cur - mapped - _new_lag_cols(current, mapped)
    missing = mapped - cur
    non_l2_merge = [o for o in _l2_merge_dups(baseline, current, mapping) if fn.parse_feature_name(mapping[o]).kind != "derived"]
    return (sorted(f"extra:{c}" for c in extra) + sorted(f"missing:{c}" for c in missing)
            + sorted(f"merge_not_l2:{o}" for o in non_l2_merge))


def cond2(baseline, current, mapping) -> List[str]:
    bad = []
    for old, fp in baseline["columns"].items():
        new = mapping[old]
        got = current["columns"].get(new)
        if got is None or any(fp[k] != got[k] for k in _FP_KEYS):
            bad.append(f"{old}->{new}")
    return bad


def _mapped_pair_signatures(baseline, mapping) -> List[Tuple[str, str, str]]:
    """baseline `l2_pairs` 之列為 `{column, fast, slow, op}`（Task 0.1 凍結版面）。"""
    return [(mapping[row["fast"]], mapping[row["slow"]], row["op"]) for row in baseline["l2_pairs"]]


def l2_merged_signatures(baseline, mapping) -> List[Tuple[str, str, str]]:
    """⑤ 之合併差集：多個舊配對簽名映到同一新簽名（同 canonical 身分之舊兩分支重複）。"""
    counts = collections.Counter(_mapped_pair_signatures(baseline, mapping))
    return sorted(sig for sig, n in counts.items() if n > 1)


def cond5(baseline, current, mapping) -> List[str]:
    """⑤：映射後配對簽名集合（同新簽名之舊重複已收斂）== 新 run 配對簽名集合；其餘任何差集＝FAIL。"""
    mapped = set(_mapped_pair_signatures(baseline, mapping))
    cur = {tuple(x) for x in current["l2_pairs"]}
    return sorted(map(str, mapped ^ cur))


def cascade_blacklisted(columns) -> Set[str]:
    """reference 設定之 cascade 黑名單（生產 `nan_strategy.categorical_blacklist` 經生產
    `utils.cascade_blacklist.expand_blacklist_patterns` 展開；L4 前即剔除，改前即如此）。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.utils.cascade_blacklist import expand_blacklist_patterns

    config = create_feature_factory()._resolve_config(freeze.reference_payloads()["main"])
    patterns = list(config.nan_strategy.categorical_blacklist or [])
    assert patterns, "reference 設定之 cascade 黑名單為空（⑥ 之扣除前提不成立）"
    return set(expand_blacklist_patterns(patterns, list(columns)))


def l1_atomic_columns(current) -> Set[str]:
    """SPEC v17 §G ⑥：L1 原子欄＝L1 群組之欄，不含 `*_L65` 平穩化群組；每欄身分 kind 須為 atomic。"""
    groups = current["manifest_groups"]
    cols = {c for gid, cols in groups.items() if group_layer(gid) == "L1" and not str(gid).endswith("_L65") for c in cols}
    bad = sorted(c for c in cols if fn.parse_feature_name(c).kind != "atomic")
    assert bad == [], bad[:20]
    return cols


def cond6(current, baseline) -> List[str]:
    """⑥：lag 輸入集合＝L1 原子欄（扣 cascade 黑名單）＋raw 欄；raw 欄集合＝改前 raw lag 輸入（`(tf, "raw", 資料鍵)`）
    經 `<canonical raw>_<tf>_raw_value` 身分之集合（不以新 run 自身之 raw 輸入當基準）。"""
    l1 = l1_atomic_columns(current)
    expected_l1 = l1 - cascade_blacklisted(l1)
    expected_raw = {fn.format_feature_name(fn.raw_value_identity(key, tf))
                    for tf, kind, key in (tuple(x) for x in baseline["l4_lag_inputs"]) if kind == "raw"}
    assert expected_raw, "baseline 無 raw lag 輸入"
    inputs = set(current["l4_lag_inputs"])
    return sorted(inputs ^ (expected_l1 | expected_raw))


# ---------------------------------------------------------------- §G 通過條件

def test_condition_1_column_set_equal_after_mapping(baseline, current):
    assert cond1(baseline, current, _mapping(baseline)) == []


def test_condition_2_four_hashes_equal_per_column(baseline, current):
    assert cond2(baseline, current, _mapping(baseline)) == []


def test_condition_3_rename_count_positive(baseline):
    mapping = _mapping(baseline)
    assert sum(1 for o, n in mapping.items() if o != n) > 0


def test_condition_4_all_new_names_roundtrip(current):
    bad = [c for c in current["columns"] if not roundtrip_ok(c)]
    assert bad == [], bad[:20]


def test_condition_5_l2_pair_signatures_equal_modulo_merge(baseline, current):
    assert cond5(baseline, current, _mapping(baseline)) == []


def test_condition_6_lag_inputs_and_new_lag_values_are_shifts(baseline, current, oracle_run):
    assert cond6(current, baseline) == []
    mapping = _mapping(baseline)
    new_lags = sorted(_new_lag_cols(current, {mapping[o] for o in baseline["columns"]}))
    assert new_lags
    inputs = {fn.format_feature_name(drop_last_op(fn.parse_feature_name(c))) for c in new_lags}
    for glob in G6_GLOBS:
        assert any(fnmatch.fnmatch(i, glob) for i in inputs), glob
    # SPEC v17 §G ⑥：位移值以「同設定但關閉縮尾」之小 run 驗（reference 開縮尾時落盤值為截尾界）；
    # 新增 lag 欄須全數出現於 oracle run，且 NaN mask 與 reference 落盤者相同（縮尾不改 NaN mask）
    oracle_cols = set(oracle_run["columns"])
    missing = [c for c in new_lags if c not in oracle_cols]
    assert missing == [], missing
    run = oracle_run["run"]
    reader = FeatureReader(run["base"])
    ref = current["run"]
    ref_reader = FeatureReader(ref["base"])
    for col in new_lags:
        stored_ref = ref_reader.load_columns_v2(ref["symbol"], ref["tf"], ref["config_hash"], [col],
                                               artifact_kind="raw")[col].to_numpy(dtype=np.float64)
        stored_orc = reader.load_columns_v2(run["symbol"], run["tf"], run["config_hash"], [col],
                                            artifact_kind="raw")[col].to_numpy(dtype=np.float64)
        np.testing.assert_array_equal(np.isnan(stored_ref), np.isnan(stored_orc), err_msg=col)
        ident = fn.parse_feature_name(col)
        k = int(ops_tuple(ident)[-1].split("-")[1])
        base_name = fn.format_feature_name(drop_last_op(ident))
        if fn.parse_feature_name(base_name).category == "raw" or ident.tf != run["tf"]:
            continue  # raw 輸入不落盤；非主週期欄於主週期列軸上位移 k 列 ≠ 位移 k 根 ⇒ 由下方完整 oracle 驗
        frame = reader.load_columns_v2(run["symbol"], run["tf"], run["config_hash"], [col, base_name], artifact_kind="raw")
        np.testing.assert_array_equal(frame[col].to_numpy()[k:], frame[base_name].to_numpy()[:-k])
    # 審查 r12 CODEX-R12-P1-03：新增 raw lag 欄之值＝真實 kline raw 欄於其週期位移 k（對齊至主週期列時間軸），不得略過
    raw_cols = [c for c in new_lags if drop_last_op(fn.parse_feature_name(c)).category == "raw"]
    assert raw_lag_cols_mismatched(oracle_run, raw_cols) == []
    # 審查 r13：非 raw 新增 lag 欄亦以完整陣列（含前綴與 NaN mask）比對 L4 輸入攔截之 oracle
    feature_cols = [c for c in new_lags if drop_last_op(fn.parse_feature_name(c)).category != "raw"]
    assert feature_cols
    assert feature_lag_cols_mismatched(oracle_run, feature_cols) == []


def test_all_raw_lag_columns_equal_shift_oracle(oracle_run):
    """SPEC v17 §G ⑥：全部 raw lag 欄（含同週期 raw 與合成 raw `avg-price`）之完整陣列＝依產生端同一來源計算之
    位移 oracle，不得略過。"""
    raw_cols = [c for c in oracle_run["columns"]
                if last_op_name(fn.parse_feature_name(c)) == "Lag"
                and drop_last_op(fn.parse_feature_name(c)).category == "raw"]
    tfs = {fn.parse_feature_name(c).tf for c in raw_cols}
    sources = {fn.parse_feature_name(c).source for c in raw_cols}
    assert oracle_run["run"]["tf"] in tfs and len(tfs) >= 2, tfs
    assert "avg-price" in sources, sources
    assert raw_lag_cols_mismatched(oracle_run, raw_cols) == []


def test_lag_input_capture_covers_each_new_lag_family(baseline, current, oracle_run):
    """審查 r13 之攔截須涵蓋 ⑥ 每個新增 lag 家族（VolumeMA-Ratio、Bullish／BearishCount）之輸入。"""
    mapping = _mapping(baseline)
    new_lags = _new_lag_cols(current, {mapping[o] for o in baseline["columns"]})
    captured = {c for f in LAG_INPUT_CAPTURES for c in f.columns if c != "timestamp"}
    bases = {fn.strip_timeframe_tag(fn.format_feature_name(drop_last_op(fn.parse_feature_name(c)))) for c in new_lags
             if drop_last_op(fn.parse_feature_name(c)).category != "raw"}
    for family in ("VolumeMA-Ratio", "BullishCount", "BearishCount"):
        fam = {b for b in bases if fn.parse_feature_name(b, tagged=False).indicator == family}
        assert fam and fam <= captured, (family, sorted(fam - captured))


def raw_lag_expected(run: Dict[str, Any], col: str, shift_fn=None) -> Tuple[np.ndarray, Any]:
    """raw lag 欄之 oracle：真實 kline 之 raw 欄（canonical 對回原始資料鍵）於其週期位移 k，
    再以 `TimeframeAligner.align_to_primary`（FFNAME 不改對齊）對到主週期 run 之列時間軸。"""
    import pandas as pd

    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
    from tests.feature_engineering.ffstat_helpers import kline_frame

    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    ident = fn.parse_feature_name(col)
    k = int(ops_tuple(ident)[-1].split("-")[1])
    raw = kline_frame(run["symbol"], ident.tf)
    # SPEC v17 §G ⑥：合成 raw（如 `avg-price`）依產生端同一函式計算（`CryptoSpotAdapter._add_synthetic_fields`，不另實作）
    raw = CryptoSpotAdapter._add_synthetic_fields(CryptoSpotAdapter.__new__(CryptoSpotAdapter), raw.copy())
    keys = [c for c in raw.columns if fn.canonical_segment(c) == ident.source]
    assert len(keys) == 1, (col, keys)  # 不略過：查無或多於一個來源即紅
    key = keys[0]
    shifted = (shift_fn or (lambda s, n: s.shift(n)))(raw[[key]], k)
    reader = FeatureReader(run["base"])
    row_index = reader.load_row_index_v2(run["symbol"], run["tf"], run["config_hash"], artifact_kind="raw")
    # 同週期分支以時間戳 reindex：兩側統一為 UTC naive，避免 tz-aware kline 索引對 naive 列軸全 NaN（非主週期分支
    # 以 epoch 對齊，不受影響）
    def _naive_utc(values) -> pd.DatetimeIndex:
        index = pd.DatetimeIndex(TimeframeAligner._to_datetime_index(values))
        return index.tz_convert(None) if index.tz is not None else index

    primary = _naive_utc(pd.Series(row_index))
    shifted.index = _naive_utc(shifted.index)
    aligned = TimeframeAligner.align_to_primary(shifted, ident.tf, pd.Series(primary), run["tf"])
    return aligned[key].to_numpy(), row_index


def full_array_mismatches(stored: np.ndarray, expected: np.ndarray) -> int:
    """完整陣列比對（審查 r13 CODEX-R13-P1-02）：含 warmup 前綴之全長；NaN mask 逐列相等；有限值轉為落盤 dtype 後
    逐列位元相等。回傳不符列數（長度不同 ⇒ 全長計不符；全欄 NaN 且 oracle 亦全 NaN 視為退化 ⇒ 計 1）。"""
    if stored.shape != expected.shape:
        return max(len(stored), len(expected), 1)
    exp = expected.astype(stored.dtype)
    s_nan = np.isnan(stored.astype(np.float64))
    e_nan = np.isnan(exp.astype(np.float64))
    if s_nan.all() and e_nan.all():
        return 1
    bad = s_nan != e_nan
    finite = ~s_nan & ~e_nan
    as_int = f"u{stored.dtype.itemsize}"
    bad[finite] = stored[finite].view(as_int) != exp[finite].view(as_int)
    return int(bad.sum())


def raw_lag_mismatch(reader: FeatureReader, run: Dict[str, Any], col: str, shift_fn=None) -> int:
    """落盤 raw lag 欄與真實 kline oracle 之完整陣列比對不符列數（含前綴與 NaN mask；審查 r13）。"""
    stored = reader.load_columns_v2(run["symbol"], run["tf"], run["config_hash"], [col], artifact_kind="raw")[col].to_numpy()
    expected, _ = raw_lag_expected(run, col, shift_fn)
    return full_array_mismatches(stored, expected)


# ---------------------------------------------------------------- 非 raw 新增 lag 欄之完整 oracle（L4 輸入攔截）

LAG_INPUT_CAPTURES: List[Any] = []


def _old_heuristic_rejects(name: str) -> bool:
    """舊 `_is_layer1_or_raw` 之子字串黑名單＋`_W\\d+$`（新增 lag 欄即其誤排除之 L1／raw 欄）。"""
    tokens = ("_Distance", "_Cross", "_Momentum", "_Ratio", "_BinarySignal", "_SignedStrength", "_TsArgmax", "_TsArgmin",
              "_TsRank", "_DecayLinear", "_TsCorr", "_Sign", "_Log1p", "_Abs", "_Clip", "_Slope_", "_Std_", "_Mean_",
              "_Rank_", "_ZScore_", "_Skew_", "_Kurt_", "_Min_", "_Max_", "_Range_", "_Lag_")
    return any(t in name for t in tokens) or re.search(r"_W\d+$", name) is not None


def install_lag_input_capture(mp, inverse_mapping: Dict[str, str]) -> None:
    """於 oracle run 期間包裝 L4 `LagProcessor.compute_all`，攔截其輸入中「L1（身分 kind＝atomic）且舊啟發式會排除」之欄
    （含時間軸），作為非 raw 新增 lag 欄（含 warmup 前綴）之 oracle 來源——與 L4 輸出及命名無關。
    「舊啟發式會排除」以舊名判定：輸入欄（未標記）依本批輸入之週期標記後，經 baseline 映射之反函數取回舊名，
    再套 `_old_heuristic_rejects`（舊啟發式只認得舊名之 `_Ratio`、`_W5` 等字樣）。"""
    from momentum.FeatureEngineering.operators.lag_processor import LagProcessor

    real = LagProcessor.compute_all

    def wrapped(self, features_df, *a, **k):
        keep = []
        try:
            tf = _capture_tf(features_df)
        except (KeyError, StopIteration, ValueError):
            # 校準域之 L4 輸入無時間軸（非公開輸出之 oracle 來源）⇒ 不攔截；公開域呼叫之攔截由
            # test_lag_input_capture_covers_each_new_lag_family 驗涵蓋
            return real(self, features_df, *a, **k)
        for c in features_df.columns:
            try:
                ident = fn.parse_feature_name(str(c), tagged=False)
            except fn.FeatureNameParseError:
                continue
            old = inverse_mapping.get(fn.tag_timeframe(str(c), tf))
            if ident.kind == "atomic" and old is not None and _old_heuristic_rejects(old):
                keep.append(c)
        extra = [c for c in ("timestamp",) if c in features_df.columns]
        if keep:
            LAG_INPUT_CAPTURES.append(features_df[keep + extra].copy())
        return real(self, features_df, *a, **k)

    mp.setattr(LagProcessor, "compute_all", wrapped)


def _naive_utc_index(values) -> "pd.DatetimeIndex":
    """時間軸（DatetimeIndex、epoch 秒／毫秒整數或時間字串）→ UTC naive DatetimeIndex（同 `TimeframeAligner` 判讀）。"""
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    import pandas as pd

    index = pd.DatetimeIndex(TimeframeAligner._to_datetime_index(values))
    return index.tz_convert(None) if index.tz is not None else index


def _capture_index(frame) -> "pd.DatetimeIndex":
    """攔截框之時間軸：`timestamp` 欄（若有）否則索引（L4 輸入索引為 epoch 秒整數，實測）。"""
    return _naive_utc_index(frame["timestamp"] if "timestamp" in frame.columns else frame.index)


def _capture_tf(frame) -> str:
    import pandas as pd

    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    index = _capture_index(frame)
    step = float(pd.Series(index).diff().dropna().dt.total_seconds().median())
    return next(tf for tf in sorted(fn.timeframe_keys()) if TimeframeAligner._timeframe_to_seconds(tf) == step)


def feature_lag_expected(run: Dict[str, Any], col: str) -> np.ndarray:
    """非 raw 新增 lag 欄之完整 oracle：攔截之 L4 輸入（未裁 warmup）於其週期位移 k，再對齊至主週期 run 之列時間軸。
    攔截框取該週期最後一次（公開域；校準域之 L4 先於公開域執行）且時間軸涵蓋本 run 列時間軸者。"""
    import pandas as pd

    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    ident = fn.parse_feature_name(col)
    k = int(ops_tuple(ident)[-1].split("-")[1])
    base_untagged = fn.strip_timeframe_tag(fn.format_feature_name(drop_last_op(ident)))
    reader = FeatureReader(run["base"])
    row_index = reader.load_row_index_v2(run["symbol"], run["tf"], run["config_hash"], artifact_kind="raw")
    primary = _naive_utc_index(pd.Series(row_index))
    frames = [f for f in LAG_INPUT_CAPTURES if base_untagged in f.columns and _capture_tf(f) == ident.tf
              and _capture_index(f).min() <= primary.min() and _capture_index(f).max() >= primary.max()
              - pd.Timedelta(seconds=TimeframeAligner._timeframe_to_seconds(ident.tf))]
    if not frames:
        raise StopIteration(col)
    frame = frames[-1]
    shifted = frame[[base_untagged]].shift(k)
    shifted.index = _capture_index(frame)
    aligned = TimeframeAligner.align_to_primary(shifted, ident.tf, pd.Series(primary), run["tf"])
    return aligned[base_untagged].to_numpy()


def lag_stored_and_expected(current: Dict[str, Any], col: str) -> Tuple[np.ndarray, np.ndarray]:
    run = current["run"]
    reader = FeatureReader(run["base"])
    stored = reader.load_columns_v2(run["symbol"], run["tf"], run["config_hash"], [col], artifact_kind="raw")[col].to_numpy()
    if drop_last_op(fn.parse_feature_name(col)).category == "raw":
        expected, _ = raw_lag_expected(run, col)
    else:
        expected = feature_lag_expected(run, col)
    return stored, expected


def feature_lag_cols_mismatched(current: Dict[str, Any], feature_cols: List[str]) -> List[str]:
    """⑥ 非 raw 新增 lag 欄之完整陣列比對；無 oracle（未攔截到輸入）亦計為不符。"""
    bad = []
    for c in feature_cols:
        try:
            stored, expected = lag_stored_and_expected(current, c)
        except StopIteration:
            bad.append(f"no_oracle:{c}")
            continue
        if full_array_mismatches(stored, expected) != 0:
            bad.append(c)
    return bad


def _first_new_lag(baseline: Dict[str, Any], current: Dict[str, Any]) -> str:
    """新增 lag 欄中第一個非 raw 者（非 raw 之 oracle 為 L4 輸入攔截；raw 者另由 off-by-one 測試涵蓋）。"""
    mapping = _mapping(baseline)
    return next(c for c in sorted(_new_lag_cols(current, {mapping[o] for o in baseline["columns"]}))
                if drop_last_op(fn.parse_feature_name(c)).category != "raw")


def test_new_lag_full_array_including_prefix_and_nan_mask(baseline, current, oracle_run):
    """審查 r13：全部新增 lag 欄（raw 與非 raw）之完整陣列＝oracle（含 warmup 前綴、NaN mask、有限值位元相等）；
    SPEC v17 §G ⑥：值於同設定但關閉縮尾之 oracle run 驗。"""
    mapping = _mapping(baseline)
    new_lags = sorted(_new_lag_cols(current, {mapping[o] for o in baseline["columns"]}))
    assert new_lags
    bad = [c for c in new_lags if full_array_mismatches(*lag_stored_and_expected(oracle_run, c)) != 0]
    assert bad == []


def test_mutation_lag_prefix_constant_is_caught(baseline, current, oracle_run):
    """mutant：新增 lag 欄前 k 筆改常數 ⇒ 完整陣列比對不符。"""
    col = _first_new_lag(baseline, current)
    k = int(ops_tuple(fn.parse_feature_name(col))[-1].split("-")[1])
    stored, expected = lag_stored_and_expected(oracle_run, col)
    assert full_array_mismatches(stored, expected) == 0
    mutated = stored.copy()
    mutated[:k] = 0
    assert full_array_mismatches(mutated, expected) > 0


def test_mutation_finite_row_set_nan_is_caught(baseline, current, oracle_run):
    """mutant：某原為有限值之列改為 NaN ⇒ NaN mask 不符。"""
    col = _first_new_lag(baseline, current)
    stored, expected = lag_stored_and_expected(oracle_run, col)
    assert full_array_mismatches(stored, expected) == 0
    finite_rows = np.flatnonzero(~np.isnan(stored.astype(np.float64)))
    assert finite_rows.size > 0 and fn.parse_feature_name(col).ops
    mutated = stored.copy()
    mutated[finite_rows[len(finite_rows) // 2]] = np.nan
    assert full_array_mismatches(mutated, expected) > 0


def raw_lag_cols_mismatched(current: Dict[str, Any], raw_cols: List[str], shift_fn=None) -> List[str]:
    """⑥ lag 欄中輸入為 raw 者，逐欄與真實 kline oracle 比對；回傳不符之欄。"""
    run = current["run"]
    reader = FeatureReader(run["base"])
    return [c for c in raw_cols if raw_lag_mismatch(reader, run, c, shift_fn) != 0]


def test_mutation_raw_lag_off_by_one_is_caught(baseline, current, oracle_run):
    """§G ⑥（審查 r12）：raw lag 之值錯位一格 ⇒ oracle 比對不等（以位移 k+1 之 oracle 模擬錯位實作）；
    SPEC v17：於關閉縮尾之 oracle run 驗，並逐一涵蓋非主週期 raw、同週期 raw 與合成 raw（`avg-price`）。"""
    mapping = _mapping(baseline)
    run = oracle_run["run"]
    reader = FeatureReader(run["base"])
    raw_lags = [c for c in sorted(_new_lag_cols(current, {mapping[o] for o in baseline["columns"]}))
                if drop_last_op(fn.parse_feature_name(c)).category == "raw"]
    all_raw = [c for c in oracle_run["columns"]
               if last_op_name(fn.parse_feature_name(c)) == "Lag"
               and drop_last_op(fn.parse_feature_name(c)).category == "raw"]
    picks = list(dict.fromkeys(raw_lags[:1]
                               + [next(c for c in all_raw if fn.parse_feature_name(c).tf != run["tf"])]
                               + [next(c for c in all_raw if fn.parse_feature_name(c).tf == run["tf"])]
                               + [next(c for c in all_raw if fn.parse_feature_name(c).source == "avg-price")]))
    assert len(picks) >= 3
    for col in picks:
        assert raw_lag_mismatch(reader, run, col) == 0, col
        assert raw_lag_mismatch(reader, run, col, shift_fn=lambda s, n: s.shift(n + 1)) > 0, col


def test_receipt_values_recomputed_by_test(baseline, current):
    """審查 r12 CODEX-R12-P1-02：收據須存在，其自報值由本測試重算後相符（值雜湊不符數、改名清單、欄名長度變化）。"""
    assert VALUE_RECEIPT.is_file()
    receipt = json.loads(VALUE_RECEIPT.read_text(encoding="utf-8"))
    mapping = _mapping(baseline)
    mismatches = cond2(baseline, current, mapping)
    renamed = sorted([o, n] for o, n in mapping.items() if o != n)
    length_change = {o: len(n) - len(o) for o, n in mapping.items()}
    assert receipt["value_hash_mismatch_count"] == len(mismatches) == 0
    assert sorted(map(list, receipt["renamed"])) == renamed
    assert {k: int(v) for k, v in receipt["name_length_change"].items()} == length_change


def test_receipt_lists_exceptions_one_by_one(baseline, current):
    """①⑤⑥ 之例外逐筆列入收據：L2 合併差集與新增 lag 欄與計算值相等。"""
    mapping = _mapping(baseline)
    receipt = json.loads(VALUE_RECEIPT.read_text(encoding="utf-8"))
    assert sorted(map(list, l2_merged_signatures(baseline, mapping))) == sorted(map(list, receipt["l2_merged"]))
    assert sorted(_new_lag_cols(current, {mapping[o] for o in baseline["columns"]})) == sorted(receipt["l4_new_lag"])


def l1_group_merges(baseline, current, mapping) -> Dict[str, List[str]]:
    """SPEC v17 §G ⑧：每個舊 manifest 群組（成員經映射、扣合併差集）恰落入一個新群組；回傳含多個舊群組之新群組
    （新 group_id → 排序後之舊 group_id）。任一舊群組落入 0 個或 >1 個新群組 ⇒ AssertionError。"""
    dups = _l2_merge_dups(baseline, current, mapping)
    new_lags = _new_lag_cols(current, {mapping[o] for o in baseline["columns"]})
    owner = {c: gid for gid, cols in current["manifest_groups"].items() for c in cols if c not in new_lags}
    merges: Dict[str, List[str]] = collections.defaultdict(list)
    for old_gid, cols in baseline["manifest_groups"].items():
        members = {mapping[c] for c in cols if c not in dups}
        if not members:
            continue
        targets = {owner.get(c) for c in members}
        assert len(targets) == 1 and None not in targets, (old_gid, sorted(t for t in targets if t))
        merges[targets.pop()].append(old_gid)
    return {new: sorted(olds) for new, olds in merges.items() if len(olds) > 1}


def test_task25_order_groups_stationarity_keys_consistent_after_mapping(baseline, current):
    """Task 2.5／SPEC v17 §G ⑧：欄序以「欄集合＋各群組成員」比對（不比絕對位置：群組依 group_id 排序、group_id 帶
    category 後位置必變）；每個舊群組恰落入一個新群組、成員聯集相等，合併之舊群組逐筆列入收據並由本測試重算；
    L1 群組之 group_id＝`{tf}_L1_{category}_{indicator}`；平穩化決策鍵經映射一致（⑥ 新增 lag 欄之決策鍵另列）。"""
    mapping = _mapping(baseline)
    dups = _l2_merge_dups(baseline, current, mapping)
    new_lags = _new_lag_cols(current, {mapping[o] for o in baseline["columns"]})
    # (a) 欄集合（無重複）
    old_order = [mapping[o] for o in baseline["column_order"] if o not in dups]
    new_order = [c for c in current["column_order"] if c not in new_lags]
    assert len(old_order) == len(set(old_order)) and len(new_order) == len(set(new_order))
    assert set(old_order) == set(new_order)
    # (b) 群組成員：每個舊群組恰落入一個新群組、聯集相等；未合併之新群組與其舊群組成員相等
    merges = l1_group_merges(baseline, current, mapping)
    old_union = {mapping[c] for cols in baseline["manifest_groups"].values() for c in cols if c not in dups}
    new_union = {c for cols in current["manifest_groups"].values() for c in cols if c not in new_lags}
    assert old_union == new_union
    old_sets = {frozenset(mapping[c] for c in cols if c not in dups) for cols in baseline["manifest_groups"].values()}
    for gid, cols in current["manifest_groups"].items():
        members = frozenset(c for c in cols if c not in new_lags)
        if members and gid not in merges:
            assert members in old_sets, gid
    for gid in merges:  # 合併只准發生於 L1（含其平穩化 `_L65` 群組）
        assert group_layer(gid) == "L1", gid
    for gid, cols in current["manifest_groups"].items():
        if group_layer(gid) == "L1" and not gid.endswith("_L65"):
            expected = {f"{i.tf}_L1_{i.category}_{i.indicator}" for i in map(fn.parse_feature_name, cols)}
            assert expected == {gid}, (gid, sorted(expected))
    receipt = json.loads(VALUE_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["l1_group_merges"] == merges
    # (c) 平穩化決策鍵：舊鍵映射＝新鍵扣 ⑥ 新增 lag 欄；多出之鍵只准為新增 lag 欄；映射後之決策值相同
    current_keys = set(current["stationarity_keys"])
    mapped_keys = {mapping[k] for k in baseline["stationarity_keys"]}
    assert mapped_keys == current_keys - new_lags
    assert current_keys - mapped_keys <= new_lags
    assert sorted(current_keys - mapped_keys) == sorted(receipt["stationarity_new_lag_keys"])
    canonical = lambda obj: json.dumps(obj, sort_keys=True, default=str)  # noqa: E731
    bad = [k for k, v in baseline["stationarity_decisions"].items()
           if canonical(v) != canonical(json.loads(canonical(current["stationarity_decisions"][mapping[k]])))]
    assert bad == [], bad[:10]


def test_condition_7_manifest_naming_version(current):
    assert current["manifest"]["feature_naming_version"] == fn.CURRENT_FEATURE_NAMING_VERSION


def test_receipt_value_mismatch_zero_and_sections():
    receipt = json.loads(VALUE_RECEIPT.read_text(encoding="utf-8"))
    for key in ("schema_version", "command", "exit_code"):
        assert key in receipt
    assert receipt["value_hash_mismatch_count"] == 0
    for key in ("renamed", "l2_merged", "l4_new_lag", "name_length_change", "l1_group_merges",
                "stationarity_new_lag_keys"):
        assert key in receipt, key


# ---------------------------------------------------------------- 邊界

def test_boundary_01_any_condition_unequal_fails(baseline, current):
    """任一通過條件不等 ⇒ FAIL：擾動一欄值雜湊（真實 baseline 之複本）⇒ 條件②列出該欄。"""
    mapping = _mapping(baseline)
    perturbed = copy.deepcopy(baseline)
    victim = sorted(perturbed["columns"])[0]
    perturbed["columns"][victim]["value_sha256"] = "0" * 64
    failures = cond2(perturbed, current, mapping)
    assert failures and failures[0].startswith(f"{victim}->")


# ---------------------------------------------------------------- mutation

def test_mutation_string_replace_mapping_breaks_condition_5(baseline, current, monkeypatch):
    """§V mutation ⑫：§G 映射改為字串 replace（數字參數前之底線改連字號）⇒ 條件⑤必紅。"""
    monkeypatch.setattr(freeze, "derive_mapping",
                        lambda parts, tf_of: {o: re.sub(r"_(\d)", r"-\1", o) for o in parts})
    assert cond5(baseline, current, _mapping(baseline)) != []
