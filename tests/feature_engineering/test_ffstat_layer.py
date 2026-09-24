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
    """真實 run 落盤之基礎欄 → 層（由檔名 `<tf>_L<k>_…` 讀得；測試端觀測）。"""
    out: Dict[str, str] = {}
    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet"):
            continue
        layer = p.name.split("_")[1]
        for name in pq.ParquetFile(p).schema_arrow.names:
            if name not in ("timestamp", "__index_level_0__", "index"):
                out[name] = layer
    return out


@pytest.mark.parametrize("cgsa", ["1", "0"], ids=["cgsa", "frame"])
def test_boundary_01_target_layers_on_both_paths(cgsa: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.1 邊界①（CGSA 與 frame 兩路徑各一）＋驗證：真實輕量 run 之 fracdiff 目標集合等於 L1∪L2 欄，
    且逐欄決策之層與落盤層一致。"""
    h.prepare_stat_env(monkeypatch, tmp_path, FFACT_USE_CGSA=cgsa)
    root, _, result = h.run_stat(tmp_path, h.stat_payload(adf=False))
    truth = _layers_from_files(root)
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
