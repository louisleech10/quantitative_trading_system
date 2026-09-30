"""FF-STAT §G golden 與 Task 4.1（docs/FFSTAT_SPEC.md §G）。

基準由 `handoffs/run_receipts/ffstat_probes/freeze_baseline.py --refreeze-baseline` 於動工前 HEAD 凍結至
`tests/_golden/ffstat/baseline.json`（L6.5 append 模式：基礎欄不被改寫、平穩化另存衍生欄）。實作前應為紅。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pyarrow.parquet as pq
import pytest

from tests.feature_engineering import ffstat_helpers as h
from tests.feature_engineering.ffstat_helpers import base_fingerprints, column_fingerprint  # noqa: F401  與凍結腳本同一定義

_SKIP = ("timestamp", "__index_level_0__", "index")
_REPO = Path(__file__).resolve().parents[2]


def derived_names(root: Path) -> set:
    return {n for p in root.rglob("*_L65.parquet") for n in pq.ParquetFile(p).schema_arrow.names if n not in _SKIP}


@pytest.fixture(scope="module")
def baseline() -> Dict[str, Any]:
    return json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def on_run(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("ffstat_golden_on")
    try:
        h.prepare_stat_env(mp, tmp)
        root, _, result = h.run_stat(tmp, h.stat_payload())
        return {"root": root, "result": result}
    finally:
        mp.undo()


def test_golden_baseline_frozen_before_change(baseline: Dict[str, Any]) -> None:
    """§G 凍結：基準存在、含逐欄四 hash、衍生欄集合與基準決策；列數與欄數非空。"""
    assert baseline["rows"] > 0 and len(baseline["base"]) > 1000 and baseline["derived"]
    assert set(baseline["decisions"]) == set(baseline["base"])
    assert sum(d["name_exempt"] for d in baseline["decisions"].values()) > 0


def test_golden_base_names_and_rows_equal(baseline: Dict[str, Any], on_run: Dict[str, Any]) -> None:
    """§G ①：基礎欄名集合全等、列數全等。"""
    fp = base_fingerprints(on_run["root"])
    assert set(fp) == h.approved_base_columns(baseline["base"])  # v49：改前基準＋使用者核可之欄集合差異
    assert {tuple(v["shape"]) for v in fp.values()} == {(baseline["rows"],)}


def test_golden_base_values_unchanged_after_stable_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G ②（v32／v33）：無起始日全史、平穩化關閉 ⇒ stable_start 前全 NaN；鏈上無第②③類之欄 stable_start 後與
    FF-STAT 動工前凍結之無起始日基準逐位元組相同（與 Task 2.3 ③ 同一判定，於此重用）。"""
    from tests.feature_engineering.test_ffstat_stable_start import test_no_start_stationarity_off_stable_values_unchanged

    test_no_start_stationarity_off_stable_values_unchanged(tmp_path, monkeypatch)


def test_golden_public_values_unchanged_by_calibration_domain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G ②（v32）：有起始日、預熱恆開 ⇒ 平穩化開與關兩次之基礎欄四 hash 全等（公開域值不因校準域存在而變）。"""
    h.prepare_stat_env(monkeypatch, tmp_path / "on")
    root_on, _, _ = h.run_stat(tmp_path / "on", h.stat_payload())
    h.prepare_stat_env(monkeypatch, tmp_path / "off")
    root_off, _, _ = h.run_stat(tmp_path / "off", h.stat_payload(fracdiff=False, adf=False))
    assert base_fingerprints(root_on) == base_fingerprints(root_off)


@pytest.mark.parametrize("timeframe", ["1h", "4h", "12h", "1d"])
def test_dual_start_convergence_default_config(timeframe: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦（v40–v43；v50 增 1d；v52 分解判準、4h 改長歷史）：預設全設定、單一原生週期、BTC。
    1h、4h、12h：合資格且 ①② 全部成立。1d：使用者 2026-09-29 裁定「日線不夠就先這樣」——深欄資料不足維持
    blocked 收據（不合資格、列數字），但可驗部分（① 資格內之 L1 輸出點、② 全部重疊列）仍須零違規。"""
    source = str(_REPO / h.CONTRACT["dual_start"]["timeframes"][timeframe])
    h.prepare_stat_env(monkeypatch, tmp_path)
    report = h.dual_start_report(tmp_path, timeframe, {}, source)
    numbers = {k: report[k] for k in ("rows", "rows_b", "m", "f_max", "margin")}
    assert not report["violations"], list(report["violations"].items())[:10]
    # v55（審查 r39；使用者 2026-09-30「資料不足應該也只是某些特徵的某些參數而已吧？」）：資格逐欄——B′ 內可驗
    # 之有效列 < min_overlap 之欄列入 `column_ineligible`（逐欄 blocked，記列數），其餘照驗且零違規。
    # 1h、4h（長歷史）須整週期全數合資格；12h（新倍數表後最深 13 欄）、1d（深欄）允許逐欄 blocked。
    min_overlap = int(h.CONTRACT["dual_start"]["min_overlap_rows"])
    assert all(n < min_overlap for n in report["column_ineligible"].values()), numbers
    if timeframe in ("1h", "4h"):
        assert report["eligible"], (numbers, report["ineligible"][:10], list(report["column_ineligible"].items())[:10])
    # 12h、1d：逐欄 blocked 之欄與列數即收據（上方 violations 為空已涵蓋可驗部分）；淺欄不得被開脫——
    # 由 test_mutation_dual_start_column_set_is_caught[missing]（刪 B′ 淺欄 ⇒ 上游 L1 有效列 ≥ min_overlap ⇒ 違規）承擔


def _small_dual_start_payload() -> Dict[str, Any]:
    """§G⑦ mutant 用之小設定：RSI 14、ADXR 233（係數 mutant 固定目標）、binary_signal、L3 21 窗、縮尾預設。"""
    payload = h.stat_payload(fracdiff=False, adf=False)
    payload["atomic_indicators"] = {
        "trend": {"enabled": False}, "volatility": {"enabled": False}, "volume": {"enabled": False},
        "statistics": {"enabled": False}, "cycle": {"enabled": False}, "pattern": {"enabled": False},
        "tail_risk": {"enabled": False}, "microstructure": {"enabled": False}, "entropy": {"enabled": False},
        "momentum": {"enabled": True, "indicators": [
            {"name": "RSI", "enabled": True, "periods": [14]},
            {"name": "ADXR", "enabled": True, "periods": [h.CONTRACT["dual_start"]["coefficient_mutant"]["period"]]},
        ]},
    }
    # 規則明列（同預設之 RSI 超買／超賣）另加「RSI > 20」：真實 BTC 1h 下絕大多數為 1 但非常數（常數欄會被死欄剔除，
    # 故不用「> 0」）；第④類遮罩若被拿掉，B 開頭（RSI 仍
    # 被 L1 遮為 NaN）之比較為 False ⇒ 0，而 A 同時點為 1 ⇒ 雙起點必抓（超買／超賣於開頭常為 0，兩邊巧合相同而抓不到）
    payload["operators"]["binary_signal"] = {"enabled": True, "rules": [
        {"indicator": "RSI", "condition": "> 70", "name_suffix": "Overbought"},
        {"indicator": "RSI", "condition": "< 30", "name_suffix": "Oversold"},
        {"indicator": "RSI", "condition": "> 20", "name_suffix": "Above20"},
    ]}
    payload["rolling_aggregation"] = {"enabled": True, "windows": [21]}
    return payload


def test_dual_start_small_config_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ mutant 之基準：小設定於真實 BTC 1h 通過雙起點對證。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    report = h.dual_start_report(tmp_path, "1h", _small_dual_start_payload(), str(_REPO / "data_cache/feature_klines"))
    assert report["margin"] >= 0 and report["eligible"]
    assert not report["violations"], report["violations"]


def test_mutation_dual_start_l1_mask_removed_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ mutant「刪 L1 遮罩」⇒ 必紅。"""
    import numpy as np

    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    monkeypatch.setattr(sm, "apply_l1_mask", lambda values, origin, k: np.asarray(values, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_dual_start_small_config_passes(tmp_path, monkeypatch)


def test_mutation_dual_start_winsor_unmasked_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ mutant「縮尾不遮」⇒ 必紅。"""
    import numpy as np

    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    # 生產縮尾路徑呼叫者為 `mask_incomplete_window_inplace`（feature_preprocessor、_numba_transforms、polars_adapter）；
    # 修前本 mutant 替換未被呼叫之 `mask_incomplete_window` 而無效（為雙起點 helper 列號對齊之假綠所掩蓋）
    monkeypatch.setattr(sm, "mask_incomplete_window", lambda output, input_values, window: np.asarray(output, dtype=float).copy())
    monkeypatch.setattr(sm, "mask_incomplete_window_inplace", lambda values, window: values)
    with pytest.raises(AssertionError):
        test_dual_start_small_config_passes(tmp_path, monkeypatch)


def test_dual_public_columns_reads_l65_files(tmp_path: Path) -> None:
    """§G⑦ v52（審查 r35 codex P1-01）：公開欄串流含 L6.5 之 `*_L65.parquet`（改前略過 ⇒ 只在 L6.5 之起算點漂移漏檢）。"""
    import numpy as np
    import pandas as pd

    stamps = np.arange(5, dtype=np.int64) * 3600
    pd.DataFrame({"timestamp": stamps}).to_parquet(tmp_path / "timestamps.parquet")
    pd.DataFrame({"base_x": np.arange(5.0)}).to_parquet(tmp_path / "grp.parquet")
    pd.DataFrame({"base_x_fracdiff": np.arange(5.0) * 2}).to_parquet(tmp_path / "grp_L65.parquet")
    names = {n for n, _ in h.dual_public_columns(tmp_path)}
    assert names == {"base_x", "base_x_fracdiff"}


def test_column_set_reasons_keyed_by_public_timeframe_tagged_names() -> None:
    """§G⑦ v54（2026-09-30 主委實跑 1h／12h：8／21 欄 `no_recorded_reason`）：L3 死欄過濾點之欄名尚未加週期標記，
    `column_set_reasons` 須以公開欄名（加週期標記、已標記者不動）為鍵；DeadDropSpy 同規則。拿掉標記轉換 ⇒ 紅。"""
    from types import SimpleNamespace

    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    stub = SimpleNamespace(
        _public_warmup_probe=[], _current_output_window=None, _current_timeframe="1h",
        _last_l3_aggregator=SimpleNamespace(dead_reasons={"taker-ratio_momentum_STOCHRSI-fastd_14-3-3-0_Max_W233": "constant"}),
        _l7_dead_reasons={"close_1h_momentum_RSI_14_Min_W21": "stable_samples_below_min"},
        _timeframe_tagged_name=FeatureFactory._timeframe_tagged_name,
        _start_dependent_columns=lambda cols: [],
    )
    meta = FeatureFactory._stable_start_metadata(stub, {}, [], {"volume_momentum_MFI_14_Range_W34": "constant"})
    assert meta["column_set_reasons"] == {
        "taker-ratio_1h_momentum_STOCHRSI-fastd_14-3-3-0_Max_W233": "constant",
        "close_1h_momentum_RSI_14_Min_W21": "stable_samples_below_min",
        "volume_1h_momentum_MFI_14_Range_W34": "constant",
    }
    spy = h.DeadDropSpy(offset=0, timeframe="1h")
    spy.record("L3", ["taker-ratio_momentum_STOCHRSI-fastd_14-3-3-0_Max_W233"], [[1.0], [1.0]], [True], {})
    assert "taker-ratio_1h_momentum_STOCHRSI-fastd_14-3-3-0_Max_W233" in spy.dropped


def test_timeframe_tag_single_name_matches_frame_rule_and_idempotent() -> None:
    """v55（審查 r39 codex P2-07）：`column_set_reasons` 之單欄標記（`_timeframe_tagged_name`）須與公開欄名之整表
    標記（`_apply_timeframe_tag`）同一結果，且已標記者再標不變（含自訂引擎欄名、欄名後段含週期字樣者）。"""
    import pandas as pd

    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    tf_keys = set(TimeframeAligner._timeframe_seconds_keys())
    names = ["close_trend_EMA_144_Kurt_W13", "taker-ratio_momentum_STOCHRSI-fastd_14-3-3-0_Max_W233",
             "ent_shannon_close_21", "tr_cvar_5pct_55", "ms_amihud_illiq_21", "meta_consensus_score",
             "close_momentum_RSI_14_Momentum_L1h", "hl_1h_momentum_AROON-aroonup_21_Min_W89", "label_fwd_ret_4",
             "taker_ratio_momentum_RSI_14", "taker_ratio_1h_momentum_RSI_14"]
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator

    for tf in ("1h", "12h", "1d"):
        frame = pd.DataFrame([[0.0] * len(names)], columns=names)  # 多週期版對空表直接回傳
        framed = list(FeatureFactory._apply_timeframe_tag(frame, tf).columns)
        multi = list(MultiTFGenerator._apply_timeframe_tag(frame, tf).columns)
        single = [FeatureFactory._timeframe_tagged_name(n, tf, tf_keys) for n in names]
        assert single == framed == multi, list(zip(names, single, framed, multi))
        assert [FeatureFactory._timeframe_tagged_name(n, tf, tf_keys) for n in single] == single  # 冪等
        # r40 codex P2-01：底線來源且週期段在後方者不重複加標記
        assert FeatureFactory._timeframe_tagged_name("taker_ratio_1h_momentum_RSI_14", tf, tf_keys) == \
            "taker_ratio_1h_momentum_RSI_14"


def test_replay_dead_reason_reproduces_pure_function() -> None:
    """§G⑦ v53（審查 r36 P1-03）：欄集合差異之重播與生產同一純函式——真實 BTC 1h：RSI 14 > 99 之二元欄（全 0）
    於 L7 ⇒ constant；只保留末 50 個有效值之 RSI ⇒ stable_samples_below_min；含 inf ⇒ L3 has_inf；正常 RSI ⇒ 不剔除。"""
    import numpy as np
    import talib

    from momentum.FeatureEngineering.operators.rolling_aggregator import _VARIANCE_FILTER_MIN_EFFECTIVE_N

    close = h.kline_frame(timeframe="1h")["close"].to_numpy(dtype=np.float64)[:3000]
    rsi = talib.RSI(close, 14)
    binary = np.where(np.isfinite(rsi), (rsi > 99).astype(float), np.nan)
    sparse = np.full_like(rsi, np.nan)
    sparse[-50:] = rsi[-50:]
    with_inf = rsi.copy()
    with_inf[-1] = np.inf
    assert h.replay_dead_reason({"site": "L7", "values": binary, "params": {"min_valid": 100}}) == "constant"
    assert h.replay_dead_reason({"site": "L7", "values": sparse, "params": {"min_valid": 100}}) == \
        "stable_samples_below_min"
    assert h.replay_dead_reason({"site": "L3", "values": with_inf, "params": {"nan_threshold": 0.9}}) == "has_inf"
    assert h.replay_dead_reason({"site": "L3", "values": rsi, "params": {"nan_threshold": 0.9}}) is None
    assert _VARIANCE_FILTER_MIN_EFFECTIVE_N > 0


def _drop_one_public_column(root: Path) -> None:
    """mutant：刪 B′ 某 parquet 之一個非時間欄（改寫該檔）。"""
    import pyarrow.parquet as pq

    for p in sorted(root.rglob("*.parquet")):
        if p.name == "timestamps.parquet":
            continue
        table = pq.read_table(p)
        names = [n for n in table.column_names if n not in ("timestamp", "__index_level_0__", "index")]
        if len(names) >= 2:
            pq.write_table(table.drop([names[0]]), p)
            return
    raise AssertionError("找不到可刪欄之 parquet")


def _add_one_public_column(root: Path) -> None:
    """mutant：於 B′ 某 parquet 多加一欄。"""
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq

    p = next(q for q in sorted(root.rglob("*.parquet")) if q.name != "timestamps.parquet")
    table = pq.read_table(p)
    pq.write_table(table.append_column("ffstat_mutant_extra", pa.array(np.zeros(table.num_rows))), p)


@pytest.mark.parametrize("mutator", [_drop_one_public_column, _add_one_public_column], ids=["missing", "extra"])
def test_mutation_dual_start_column_set_is_caught(mutator: Any, tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ v52（審查 r35 codex P1-02）：B′ 少欄或多欄 ⇒ `missing_public_columns`／`extra_public_columns` 非空。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    report = h.dual_start_report(tmp_path, "1h", _small_dual_start_payload(), str(_REPO / "data_cache/feature_klines"),
                                 b_mutator=mutator)
    assert report["missing_public_columns"] or report["extra_public_columns"]
    assert any(k.startswith("column_set:") for k in report["violations"])  # v53：未記原因之集合差異即違規


def _drop_rsi14_public_column(root: Path) -> None:
    """刪 B′ 已落盤之第一個 `_RSI_14` 公開欄（1d 小設定下其 L1 上游於 B′ 有效列 > 0 而 < 500）。"""
    import pyarrow.parquet as pq

    for p in sorted(root.rglob("*.parquet")):
        if p.name == "timestamps.parquet":
            continue
        table = pq.read_table(p)
        names = [n for n in table.column_names if n.endswith("_RSI_14")]
        if names:
            if len(table.column_names) == 1:
                p.unlink()
            else:
                pq.write_table(table.drop([names[0]]), p)
            return
    raise AssertionError("B′ 無 _RSI_14 欄")


def test_mutation_dual_start_1d_generated_column_missing_is_caught(tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ 逐欄資格（b5；b4 評測 gpt-6.1-sol 反例）：B′ 已生成而遺失之欄不得以「上游有效列不足」開脫——只有上游
    於 B′ 全無有效值才證明其不可能有值。真實 BTC 1d（長歷史，B′ 約 604 列、RSI 14 上游有效約 468 列）刪 B′ 之
    RSI 14 公開欄 ⇒ 必有該欄之 column_set 違規（改前：記為 column_ineligible、violations 空）。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    report = h.dual_start_report(tmp_path, "1d", _small_dual_start_payload(),
                                 str(_REPO / "data_cache/feature_klines_longhist"), b_mutator=_drop_rsi14_public_column)
    missing = [k for k in report["violations"] if k.startswith("column_set:") and k.endswith("_RSI_14")]
    assert missing, (report["violations"], {k: v for k, v in report["column_set_explained"].items()
                                            if k.endswith("_RSI_14")})


def _small_no_winsor_payload() -> Dict[str, Any]:
    """小設定關縮尾：縮尾之完整窗遮罩（251 列）涵蓋第④類之開頭段（RSI 14 之 K 遠小於 251），開縮尾時「第④類不遮」
    於最終輸出不可觀測 ⇒ 第④類 mutant 以關縮尾之同一小設定驗（主委實跑 2026-09-28：開縮尾時該 mutant 恆綠）。"""
    payload = _small_dual_start_payload()
    payload["preprocessing"] = {**payload["preprocessing"], "winsorization": {"enabled": False}}
    return payload


def test_dual_start_small_config_no_winsor_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ 第④類 mutant 之基準：關縮尾之小設定於真實 BTC 1h 通過雙起點對證。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    report = h.dual_start_report(tmp_path, "1h", _small_no_winsor_payload(), str(_REPO / "data_cache/feature_klines"))
    assert report["margin"] >= 0 and report["eligible"]
    assert not report["violations"], report["violations"]


def test_mutation_dual_start_pointwise_unmasked_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ mutant「第④類不遮」⇒ 必紅（於關縮尾之小設定；見 `_small_no_winsor_payload`）。"""
    import numpy as np

    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    monkeypatch.setattr(sm, "mask_pointwise_prefix", lambda output, inputs: np.asarray(output, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_dual_start_small_config_no_winsor_passes(tmp_path, monkeypatch)


def test_mutation_dual_start_adxr_factor_one_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G⑦ mutant「倍數表 ADXR 係數改為 1.0」（v42 固定目標）⇒ 必紅（r22 codex：ADXR 233 normalized 0.1053）。"""
    import math

    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    original = sm.instance_k
    target = h.CONTRACT["dual_start"]["coefficient_mutant"]

    def factor_one(spec, table, upstream_k=None):
        if spec.indicator == target["indicator"] and not spec.upstream:
            return math.ceil(max(float(spec.params[k]) for k in target["period_keys"]) * 1.0)
        return original(spec, table, upstream_k)

    monkeypatch.setattr(sm, "instance_k", factor_one)
    with pytest.raises(AssertionError):
        test_dual_start_small_config_passes(tmp_path, monkeypatch)


def test_golden_derived_consistent_with_decisions(baseline: Dict[str, Any], on_run: Dict[str, Any]) -> None:
    """§G ②′：改後衍生欄集合與逐欄決策一致（有 `_fracdiff` ⇔ fracdiff、有 `_diffK` ⇔ ADF 差分 K 階）；
    摘要與逐欄重新計數一致。與基準相比之決策改變由 `test_golden_receipt_change_report` 驗。"""
    derived = derived_names(on_run["root"])
    dec = h.decisions(on_run["result"])
    for col, d in dec.items():
        assert (f"{col}_fracdiff" in derived) == bool(d["fracdiff"]), col
        order = next((k for k in (1, 2) if f"{col}_diff{k}" in derived), 0)
        assert order == int(d["adf_differenced"] or 0), col
    # 摘要（契約 metadata_keys.summary）須與逐欄資料重新計數一致（r18 codex P2-05）
    summary = on_run["result"].metadata[h.META["summary"]]
    assert set(h.CONTRACT["summary_fields"]) <= set(summary)
    # tested＝有 p 值之欄（b4 後真實資料下有欄校準窗有效值不足而未檢定）；未檢定者須有說明事件，不得無故缺 p 值
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import EVENT_ADF_UNTESTED

    explain = {EVENT_ADF_UNTESTED, h.EVENTS["calibration_insufficient"]}
    untested = {c: d for c, d in dec.items() if d.get("adf_pvalue") is None}
    assert summary["tested"] == len(dec) - len(untested)
    assert all(explain & set(d["events"]) for d in untested.values()), untested
    assert summary["fracdiff"] == sum(1 for d in dec.values() if d["fracdiff"])
    assert summary["adf_diff_1"] == sum(1 for c in dec if f"{c}_diff1" in derived)
    assert summary["adf_diff_2"] == sum(1 for c in dec if f"{c}_diff2" in derived)
    for key, event in (("search_failed", "search_failed"), ("cache_read_failed", "cache_read_failed"),
                       ("cache_write_failed", "cache_write_failed"),
                       ("calibration_insufficient", "calibration_insufficient")):
        assert summary[key] == sum(1 for d in dec.values() if h.EVENTS[event] in d["events"])


def test_decision_change_report_counts_exactly() -> None:
    """§G ②′ 報告函式之鑑別力（純邏輯、手算期望）：兩欄改變（一欄原屬名字免檢）、一欄不變、一欄只在一邊。"""
    base = {"a": {"fracdiff": False, "adf_diff_order": 0, "name_exempt": True},
            "b": {"fracdiff": True, "adf_diff_order": 0, "name_exempt": False},
            "c": {"fracdiff": False, "adf_diff_order": 1, "name_exempt": False},
            "only_base": {"fracdiff": False, "adf_diff_order": 0, "name_exempt": False}}
    now = {"a": {"fracdiff": False, "adf_differenced": 1}, "b": {"fracdiff": True, "adf_differenced": None},
           "c": {"fracdiff": True, "adf_differenced": 0}, "only_now": {"fracdiff": True, "adf_differenced": 0}}
    rep = h.decision_change_report(base, now)
    assert rep["changed_count"] == 2 and set(rep["changed_columns"]) == {"a", "c"}
    assert rep["by_kind"] == {"(False, 0)->(False, 1)": 1, "(False, 1)->(True, 0)": 1}
    assert rep["name_exempt_changed"] == ["a"]


def test_golden_receipt_change_report(baseline: Dict[str, Any], on_run: Dict[str, Any]) -> None:
    """§G ②′／Task 4.1 收據（r19 codex P2-04）：最新 `handoffs/run_receipts/*-ffstat-golden.json`
    （由 `ffstat_probes/golden_receipt.py` 產出）之逐欄決策與本次 run 相同（fracdiff、ADF 階數、d），
    且其 `change_report` 等於以收據逐欄決策對基準獨立重算之結果。"""
    receipts = sorted((_REPO / "handoffs" / "run_receipts").glob("*-ffstat-golden.json"))
    assert receipts, "缺 golden 收據：須跑 handoffs/run_receipts/ffstat_probes/golden_receipt.py"
    receipt = json.loads(receipts[-1].read_text(encoding="utf-8"))
    dec = h.decisions(on_run["result"])
    key = ("fracdiff", "adf_differenced", "d")
    assert {c: [d[k] for k in key] for c, d in receipt["decisions"].items()} == \
        {c: [d[k] for k in key] for c, d in json.loads(json.dumps(dec)).items()}
    assert receipt["change_report"] == json.loads(json.dumps(h.decision_change_report(baseline["decisions"],
                                                                                      receipt["decisions"])))


def test_boundary_21_both_off_identical_to_baseline_base(baseline: Dict[str, Any], on_run: Dict[str, Any],
                                                         tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界①（v49 依 v32 改寫）：fracdiff 與 ADF 差分皆關閉 ⇒ 無任何衍生欄、無平穩化決策，且基礎欄與同設定
    開平穩化之基礎欄逐位元組相同（§G ②）。原「與改前基準逐位元組相同」隨 v32 R1 預熱恆開——有起始日時值不再與改前
    相同（§C）——改寫；無起始日全史之改前對照由 test_golden_base_values_unchanged_after_stable_start 驗。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False))
    assert base_fingerprints(root) == base_fingerprints(on_run["root"])
    assert set(base_fingerprints(root)) == h.approved_base_columns(baseline["base"])
    assert derived_names(root) == set()
    assert not result.metadata.get(h.META["decisions"])


def test_mutation_fracdiff_overwrites_base_is_caught(baseline: Dict[str, Any], tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """§G 鑑別力：fracdiff 結果改寫回基礎欄（非平穩化路徑被動到）⇒ ② 之逐欄比對必紅。
    （v32 起 ② 之有起始日判定為「平穩化開與關兩次之基礎欄四 hash 全等」，即
    test_golden_public_values_unchanged_by_calibration_domain；原 trim0 對改前基準之比對隨預熱恆開退役。）"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    def _mutant(result, column, fracdiff_series, mode):
        result[column] = fracdiff_series

    monkeypatch.setattr(FeaturePreprocessor, "_assign_fracdiff_result", staticmethod(_mutant))
    with pytest.raises(AssertionError):
        test_golden_public_values_unchanged_by_calibration_domain(tmp_path, monkeypatch)


def _cost_probe():
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "handoffs" / "run_receipts" / "ffstat_probes" / "cost_probe.py"
    spec = importlib.util.spec_from_file_location("ffstat_cost_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cost_probe_verdict_flags_over_tier_and_leftover() -> None:
    """Task 4.1 驗證（r18 codex P1-04、r19 codex P2-03）：成本探針之判定——tier run 任一階段（校準／交接／公開）
    之 USS 合計峰值 9 GiB 且 rc=0 ⇒ 失敗；tier run 缺交接階段峰值 ⇒ 失敗；RSS 合計超過而 USS 未超過 ⇒ 不失敗
    （共享頁不重計）；暫存殘留 ⇒ 失敗；皆正常 ⇒ 通過。"""
    probe = _cost_probe()
    ok_row = {"symbol": "BTCUSDT", "timeframe": "1h", "n": 500, "rc": 0, "calibration_tmp_leftover": 0}
    ok_tier = {"rc": 0, **{f"peak_{m}_{s}_bytes": 3 * probe.GIB for m in ("rss", "uss", "judged")
                           for s in probe.STAGES}}
    assert probe.verdict([ok_row], ok_tier) == []
    for stage in probe.STAGES:
        assert probe.verdict([ok_row], {**ok_tier, f"peak_judged_{stage}_bytes": 9 * probe.GIB}), stage
    assert probe.verdict([ok_row], {**ok_tier, "peak_rss_handoff_bytes": 9 * probe.GIB}) == []
    no_handoff = {k: v for k, v in ok_tier.items() if "handoff" not in k}
    assert probe.verdict([ok_row], no_handoff)
    assert probe.verdict([ok_row], {**ok_tier, "samples_incomplete": 1})
    assert probe.verdict([{**ok_row, "calibration_tmp_leftover": 1}], ok_tier)
    assert probe.verdict([{**ok_row, "rc": 1}], ok_tier)
    # b5：平穩化關閉列與改前列失敗亦判失敗（且標出模式與改前 commit）
    off_fail = probe.verdict([ok_row, {"symbol": "BTCUSDT", "timeframe": "12h", "mode": "off", "rc": 1}], ok_tier)
    assert off_fail and "mode=off" in off_fail[0]
    before_fail = probe.verdict([{"symbol": "BTCUSDT", "timeframe": "1h", "mode": "on", "commit": "5a148b8e",
                                  "rc": 1}], ok_tier)
    assert before_fail and "before=5a148b8e" in before_fail[0]


def test_cost_probe_late_agreement_counts_and_danger() -> None:
    """Task 4.1 v41（b5）：對獨立後段之一致率——校準判定取決策 `adf_pvalue`>0.05、後段取傳入之 ADF 函式 >0.05；
    危險方向＝校準判平穩而後段不平穩；無 p 值、無後段值、後段有限值不足 LATE_MIN_VALUES 之欄略過（不計入分母）；
    後段只以有限值計數與檢定（總長足而有限值不足者略過）。以假 ADF（依序列均值定 p）驗四種組合。"""
    import numpy as np

    probe = _cost_probe()
    m = probe.LATE_MIN_VALUES
    nonstat, stat = np.full(m, 1.0), np.full(m, 0.0)  # 假 ADF：均值 1 ⇒ p=0.9（不平穩）、均值 0 ⇒ p=0.01
    fake = lambda v: 0.9 if float(np.mean(v)) > 0.5 else 0.01  # noqa: E731
    dec = {"agree_ns": {"adf_pvalue": 0.2}, "agree_s": {"adf_pvalue": 0.01}, "danger": {"adf_pvalue": 0.01},
           "danger2": {"adf_pvalue": 0.04},
           "miss": {"adf_pvalue": 0.5}, "nop": {"adf_pvalue": None}, "short": {"adf_pvalue": 0.5},
           "nan_padded": {"adf_pvalue": 0.01}}
    late = {"agree_ns": nonstat, "agree_s": stat, "danger": nonstat, "danger2": nonstat, "miss": stat, "nop": stat,
            "short": np.full(m - 1, 1.0), "nan_padded": np.concatenate([np.full(50, np.nan), stat[: m - 10]])}
    got = probe.late_agreement(dec, late, fake)
    assert got["late_columns_counted"] == 5 and got["late_columns_skipped"] == 3, got
    assert got["agreement_vs_late"] == round(2 / 5, 4), got
    assert got["danger_rate_vs_late"] == round(2 / 5, 4), got  # 兩個危險方向、一個反方向（miss）：方向寫反即紅
    assert probe.late_agreement({}, {}, fake)["agreement_vs_late"] is None


def test_cost_probe_sampler_counts_child_when_uss_denied() -> None:
    """Task 4.1 驗證（r20 codex P1-01、r21 codex P1-01／P2-01／P2-02）：取樣器五種序列——
    ①子程序 USS 被拒（macOS 對 spawn 子程序之實況）⇒ 整筆以 RSS 合計判定、7 GiB 子程序不漏算、記 rss_fallback；
    ②子程序連 RSS 亦取不到 ⇒ 記 samples_incomplete、不留判定值；
    ③列舉子程序本身拋例外（沙箱禁 sysctl）⇒ 記 samples_incomplete、不留判定值，verdict 判失敗；
    ④子程序 RSS 已計入後 USS 拋 NoSuchProcess ⇒ 改以 RSS 合計判定（不以較小之 USS 充數）；
    ⑤取樣途中階段由交接轉公開 ⇒ 該筆兩階段皆記；⑥途中 public→handoff→public ⇒ 交接亦記；⑦實際起點間隔入 max_sample_gap_seconds；⑧轉收據保留秒數小數；⑨階段設定與快照共用一鎖。
    另對真實子程序取樣一次：須完整。"""
    import subprocess
    import sys

    import psutil

    probe = _cost_probe()
    gib = probe.GIB

    class _Info:
        def __init__(self, rss: int, uss: int = 0) -> None:
            self.rss, self.uss = rss, uss

    class _Proc:
        def __init__(self, rss=None, uss=None, rss_exc=None, uss_exc=None, children=(), children_exc=None,
                     on_uss=None) -> None:
            self._rss, self._uss, self._rss_exc, self._uss_exc = rss, uss, rss_exc, uss_exc
            self._children, self._children_exc, self._on_uss = list(children), children_exc, on_uss

        def children(self, recursive=True):
            if self._children_exc is not None:
                raise self._children_exc
            return self._children

        def memory_info(self):
            if self._rss_exc is not None:
                raise self._rss_exc
            return _Info(self._rss)

        def memory_full_info(self):
            if self._on_uss is not None:
                self._on_uss()
            if self._uss_exc is not None:
                raise self._uss_exc
            return _Info(self._rss, self._uss)

    def _run_one(proc: "_Proc", stage: str = "handoff", sampler=None):
        sampler = sampler or probe._Sampler()
        sampler._proc = proc
        sampler.stage = stage
        sampler._tick()
        return sampler

    parent = dict(rss=gib, uss=gib // 2)
    # ①
    s = _run_one(_Proc(**parent, children=[_Proc(rss=7 * gib, uss_exc=psutil.AccessDenied(1))]))
    assert s.peaks["peak_judged_handoff_bytes"] == 8 * gib and s.peaks["samples_rss_fallback"] == 1
    assert "peak_uss_handoff_bytes" not in s.peaks and "samples_incomplete" not in s.peaks
    # ②
    s = _run_one(_Proc(**parent, children=[_Proc(rss_exc=psutil.AccessDenied(1))]))
    assert s.peaks["samples_incomplete"] == 1 and "peak_judged_handoff_bytes" not in s.peaks
    # ③：先有三階段低峰值，再一筆列舉失敗 ⇒ verdict 仍判失敗
    s = probe._Sampler()
    for stage in probe.STAGES:
        _run_one(_Proc(**parent), stage, s)
    _run_one(_Proc(**parent, children_exc=PermissionError(1, "Operation not permitted")), "public", s)
    assert s.peaks["samples_incomplete"] == 1
    assert probe.verdict([], {"rc": 0, **s.peaks})
    # ④
    s = _run_one(_Proc(**parent, children=[_Proc(rss=9 * gib, uss_exc=psutil.NoSuchProcess(123))]))
    assert s.peaks["peak_judged_handoff_bytes"] == 10 * gib and s.peaks["samples_rss_fallback"] == 1
    # ⑤
    s = probe._Sampler()
    child = _Proc(rss=9 * gib, uss=9 * gib, on_uss=lambda: setattr(s, "stage", "public"))
    _run_one(_Proc(**parent, children=[child]), "handoff", s)
    assert s.peaks["peak_judged_handoff_bytes"] == s.peaks["peak_judged_public_bytes"] == 9 * gib + gib // 2
    # ⑥ 取樣途中 public→handoff→public（首個 worker 送出即完成）⇒ 交接峰值亦記（r22 codex P2-01）
    s = probe._Sampler()

    def _flip_twice() -> None:
        s.stage = "handoff"
        s.stage = "public"

    child = _Proc(rss=9 * gib, uss=9 * gib, on_uss=_flip_twice)
    _run_one(_Proc(**parent, children=[child]), "public", s)
    assert s.peaks["peak_judged_handoff_bytes"] == s.peaks["peak_judged_public_bytes"] == 9 * gib + gib // 2
    # ⑦ 實際起點間隔：每筆取樣耗時 0.1 s ⇒ max_sample_gap_seconds ≥ 0.1（不以睡眠常數充當間隔；r22 codex P2-02）
    import time as _time

    s = probe._Sampler()
    s._proc = _Proc(**parent, on_uss=lambda: _time.sleep(0.1))
    s._tick()
    s._tick()
    assert s.peaks["max_sample_gap_seconds"] >= 0.1
    # ⑧ 轉收據保留秒數小數（r23 codex P2-01：int() 曾把 0.1 秒截為 0）
    out = probe.peaks_for_result(s.peaks)
    assert out["max_sample_gap_seconds"] >= 0.1 and isinstance(out["peak_judged_public_bytes"], int)
    assert probe.peaks_for_result({"max_sample_gap_seconds": 0.1017, "samples_rss_fallback": 2}) == \
        {"max_sample_gap_seconds": 0.1017, "samples_rss_fallback": 2}
    # ⑨ 階段設定與取樣之階段快照共用一鎖（r23 codex P2-02）：鎖被持有時，設定不會只改一半、快照不會讀到半態
    import threading

    s = probe._Sampler()
    s._proc = _Proc(**parent)
    with s._lock:
        setter = threading.Thread(target=lambda: setattr(s, "stage", "handoff"))
        ticker = threading.Thread(target=s._tick)
        setter.start()
        ticker.start()
        _time.sleep(0.1)
        assert setter.is_alive() and ticker.is_alive()
        assert s._stage == "public" and s._history == ["public"]
    setter.join(2)
    ticker.join(2)
    assert not setter.is_alive() and not ticker.is_alive()
    assert s._stage == "handoff" and s._history[-1] == "handoff"
    # 真實子程序
    real = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"])
    try:
        import time

        time.sleep(0.5)
        rss, _, complete = probe._Sampler()._sample()
        assert complete
        assert rss >= psutil.Process(real.pid).memory_info().rss
    finally:
        real.kill()
        real.wait()
