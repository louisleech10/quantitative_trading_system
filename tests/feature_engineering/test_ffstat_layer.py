"""FF-STAT Task 1.1：fracdiff 目標層只取自結構化層來源（docs/FFSTAT_SPEC.md §C「目標層」）。

層之正解由真實 run 落盤之 parquet 檔名（`<tf>_L<k>_…`）讀得——此為測試端觀測；生產碼不得由欄名解析層。
實作前應為紅。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pyarrow.parquet as pq
import pytest

from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as h

_PRE_CONFIG = {"fractional_differencing": {"enabled": True, "apply_to": "non_stationary"},
               "adf_differencing": {"enabled": False}}


def _layers_from_files(root: Path) -> Dict[str, str]:
    """真實 CGSA run 落盤之基礎欄 → 層（由群組檔名 `<tf>_L<k>_…` 讀得；測試端觀測）。
    只讀檔名符合該格式之群組檔（輸出目錄另有非群組之 parquet，如時間軸檔）。"""
    import re

    pattern = re.compile(r"^[0-9]+[mhdw]_(L[0-9]+)_")
    out: Dict[str, str] = {}
    for p in sorted(root.rglob("*.parquet")):
        match = pattern.match(p.name)
        if match is None or p.name.endswith("_L65.parquet"):
            continue
        for name in pq.ParquetFile(p).schema_arrow.names:
            if name not in ("timestamp", "__index_level_0__", "index"):
                out[name] = match.group(1)
    assert out, "落盤檔中找不到任何群組檔（測試前提）"
    return out


@pytest.mark.parametrize("cgsa", ["1", "0"], ids=["cgsa", "frame"])
def test_boundary_01_target_layers_on_both_paths(cgsa: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.1 邊界①（CGSA 與 frame 兩路徑各一）＋驗證：真實輕量 run 之 fracdiff 目標集合等於 L1∪L2 欄，
    且逐欄決策之層與落盤層一致。層之正解一律由同設定之 CGSA run 落盤群組檔名讀得（frame 路徑不落群組
    parquet；兩路徑欄名相同，主委實跑 2026-09-25）。"""
    h.prepare_stat_env(monkeypatch, tmp_path / "truth", FFACT_USE_CGSA="1")
    truth_root, _, _ = h.run_stat(tmp_path / "truth", h.stat_payload(adf=False))
    truth = _layers_from_files(truth_root)
    h.prepare_stat_env(monkeypatch, tmp_path / "run", FFACT_USE_CGSA=cgsa)
    _, _, result = h.run_stat(tmp_path / "run", h.stat_payload(adf=False))
    dec = h.decisions(result)
    targets = {c for c, d in dec.items() if d["layer"] in h.CONTRACT["fracdiff_target_layers"]}
    assert targets == {c for c, layer in truth.items() if layer in h.CONTRACT["fracdiff_target_layers"]}
    assert all(dec[c]["layer"] == truth[c] for c in dec if c in truth)


def _real_names(n: int = 40) -> List[str]:
    import json

    base = json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))["base"]
    return sorted(base)[:n]


def _map(names: List[str]) -> Dict[str, str]:
    # 以真實欄名配層（前半 L1、後半 L3）：測試只驗「層由對照給出」，不驗層之真值
    half = len(names) // 2
    return {**{c: "L1" for c in names[:half]}, **{c: "L3" for c in names[half:]}}


def test_missing_column_in_layer_map_fails_closed() -> None:
    """Task 1.1 驗證：自對照移除一欄 ⇒ fail-closed（ValueError），訊息含缺漏欄數。"""
    names = _real_names()
    layer_map = _map(names)
    layer_map.pop(names[0])
    pre = FeaturePreprocessor(_PRE_CONFIG, column_layer_map=layer_map)
    with pytest.raises(ValueError) as err:
        pre._filter_fracdiff_target_columns(names)
    assert "1" in str(err.value)


def test_boundary_02_empty_group_layer_fails_closed() -> None:
    """Task 1.1 邊界②：CGSA 群組 `layer` 為空（且無對照）⇒ fail-closed（ValueError），不退回欄名解析。"""
    pre = FeaturePreprocessor(_PRE_CONFIG, column_layer_map=None)
    with pytest.raises(ValueError):
        pre._filter_fracdiff_target_columns(_real_names(), source_layer="")


def test_rename_does_not_change_targets() -> None:
    """Task 1.1 驗證：改欄名（對照同步改名、層不變）⇒ 目標集合大小與層分佈不變。"""
    names = _real_names()
    renamed = [f"zz{i}_renamed" for i in range(len(names))]
    pre_a = FeaturePreprocessor(_PRE_CONFIG, column_layer_map=_map(names))
    pre_b = FeaturePreprocessor(_PRE_CONFIG, column_layer_map=_map(renamed))
    got_a = pre_a._filter_fracdiff_target_columns(names)
    got_b = pre_b._filter_fracdiff_target_columns(renamed)
    assert len(got_a) == len(names) // 2
    assert [renamed[names.index(c)] for c in got_a] == got_b


def test_mutation_regex_layer_fallback_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ②：目標層退回欄名解析（忽略對照、以 `^L\\d+_` 取層）⇒ 改名測試必紅。"""
    import re

    def _legacy(self, columns, source_layer=None):
        return [c for c in columns if (m := re.match(r"^(L\d+)_", str(c))) and m.group(1) in ("L1", "L2")]

    monkeypatch.setattr(FeaturePreprocessor, "_filter_fracdiff_target_columns", _legacy)
    with pytest.raises(AssertionError):
        test_rename_does_not_change_targets()


def test_mutation_missing_map_entry_treated_as_non_target_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ③：對照缺欄時當非目標而不 fail ⇒ fail-closed 測試必紅。"""
    def _lenient(self, columns, source_layer=None):
        layer_map = self._column_layer_map or {}
        return [c for c in columns if layer_map.get(c) in ("L1", "L2")]

    monkeypatch.setattr(FeaturePreprocessor, "_filter_fracdiff_target_columns", _lenient)
    with pytest.raises(pytest.fail.Exception):
        test_missing_column_in_layer_map_fails_closed()


def test_rename_real_values_same_nonstationary_decisions() -> None:
    """§G ⑥（r18 codex P2-05）：以真實 kline 之值做 ADF 判定，欄名全數改掉後，逐欄（依位置對照）
    是否判為不平穩全同——判定只看值、不看名。"""
    frame = h.kline_frame().iloc[:500][["open", "high", "low", "close", "volume", "taker_ratio"]]
    frame = frame.assign(close_diff=frame["close"].diff(), vol_diff=frame["volume"].diff())
    pre = FeaturePreprocessor(_PRE_CONFIG)
    got = set(pre._get_non_stationary_columns(frame))
    renamed = frame.copy()
    renamed.columns = [f"zz{i}" for i in range(len(frame.columns))]
    got_renamed = set(FeaturePreprocessor(_PRE_CONFIG)._get_non_stationary_columns(renamed))
    mapping = dict(zip(frame.columns, renamed.columns))
    assert {mapping[c] for c in got} == got_renamed
    assert got and len(got) < len(frame.columns)


def test_provenance_error_not_degraded() -> None:
    """b1 審碼 r1 codex P1-01：平穩化來源缺漏之錯誤不得被 `_execute_l65_with_degradation`／`_safe_execute`
    降級為「未做 L6.5 照常輸出」。"""
    import pandas as pd

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import StationarityProvenanceError

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(h.stat_payload())

    def _missing(*_a, **_k):
        raise StationarityProvenanceError("no layer source")

    with pytest.raises(StationarityProvenanceError):
        factory._execute_l65_with_degradation("Layer 6.5", _missing, pd.DataFrame({"a": [1.0]}), config)
    with pytest.raises(StationarityProvenanceError):
        factory._safe_execute("Layer 6.5 pre_ic", _missing)


def test_legacy_multi_tf_uses_structured_layers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """b1 審碼 r1 codex P1-01：legacy 多週期 frame 路徑（CGSA 關閉、1h＋12h）以結構化層判 fracdiff 目標，
    L6.5 確有執行（未降級）、決策含 12h 原生週期之欄且其 timeframe 欄為 12h、層皆為 L1／L2。"""
    h.prepare_stat_env(monkeypatch, tmp_path, FFACT_USE_CGSA="0")
    _, factory, result = h.run_stat(tmp_path, h.stat_payload(["1h", "12h"], adf=False))
    assert factory._preprocessing_applied is True
    dec = h.decisions(result)
    assert dec and {d["layer"] for d in dec.values()} <= set(h.CONTRACT["fracdiff_target_layers"])
    tf12 = {c: d for c, d in dec.items() if "_12h_" in c}
    assert tf12 and all(d["timeframe"] == "12h" for d in tf12.values())
    assert all(d["timeframe"] == "1h" for c, d in dec.items() if "_1h_" in c)


def test_ic_first_fresh_path_uses_structured_layers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """b1 審碼 r1 codex P1-01：IC-first 自算路徑（fresh factory，未先跑 generate_features）之 L6.5 以本次 layers
    建之層對照判 fracdiff 目標：決策非空、層皆為 L1／L2（未因缺對照而失敗或降級）。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.warmup_window import resolve_output_window
    from momentum.factories import create_feature_factory

    h.prepare_stat_env(monkeypatch, tmp_path, FFACT_USE_CGSA="0")
    root = tmp_path / "features"
    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    config = factory._resolve_config(h.stat_payload(adf=False))
    factory._current_output_window = resolve_output_window(config, h.PRIMARY_TF, *h.WINDOW)
    h.ic_first_to_l65(factory, config, ic_engine=ICEngine({"methods": ["spearman"]}),
                      feature_reader=FeatureReader(str(root)), storage=factory._storage,
                      ic_threshold=0.0, persist=False)
    dec = factory.last_stationarity_decisions
    assert dec and {d["layer"] for d in dec.values()} <= set(h.CONTRACT["fracdiff_target_layers"])
