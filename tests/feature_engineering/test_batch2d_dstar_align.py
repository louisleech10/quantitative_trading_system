from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_factory import (
    FeatureFactory,
)
from momentum.FeatureEngineering.preprocessing._d_star_cache import read_d_star_json
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from scripts.freeze_batch2d_baseline import (
    FREEZE_ENV_DEFAULTS,
    KLINE_PATH,
    _run_cgsa,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH2D_GOLDEN_DIR = REPO_ROOT / "tests" / "_golden" / "batch2d"
_L36_LAYERS = frozenset({"L3", "L4", "L5", "L6"})
_L12_LAYERS = frozenset({"L1", "L2"})


def _require_real_kline() -> Path:
    if not KLINE_PATH.is_file():
        pytest.fail(f"missing required real kline cache: {KLINE_PATH}")
    return KLINE_PATH


def _load_golden(name: str) -> Dict[str, Any]:
    path = BATCH2D_GOLDEN_DIR / f"{name}.json"
    if not path.is_file():
        pytest.fail(f"missing required batch2d golden: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_batch2d_env(monkeypatch: pytest.MonkeyPatch, *, use_cgsa: bool) -> None:
    for key, value in FREEZE_ENV_DEFAULTS.items():
        monkeypatch.setenv(key, value)


# TESTSEL I10：P4 重跑一致性（兩次生成 NaN mask 逐欄相同）與欄寬無關 ⇒ 生產預設之 7 個標準 atomic 類別各留一指標一週期、
# L2 momentum 只 1 個 lag、L3 窗 2 個（聚合器全部），其餘層與前處理照生產預設；輸出窗縮為起始日起兩個月。
# 環境臂（pandas、L6.5 chunk 500、slowpath 序列、nested batch）不變；欄數仍 > chunk 500 ⇒ L6.5 多 chunk 路徑在場。
_NARROW_ATOMIC = {
    "trend": [{"name": "EMA", "periods": [13]}],
    "momentum": [{"name": "RSI", "periods": [14]}],
    "volatility": [{"name": "ATR", "periods": [14]}],
    "volume": [{"name": "OBV"}],
    "statistics": [{"name": "STDDEV", "periods": [13]}],
    "cycle": [{"name": "HT_DCPERIOD"}],
    "pattern": [{"name": "CDLDOJI"}],
}
_NARROW_END_DATE = "2024-08-01"


def _narrow_cgsa_run(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.freeze_batch2d_baseline as fb

    base = fb._base_override

    def _narrow_override() -> Dict[str, Any]:
        override = base()
        override["atomic_indicators"] = {
            name: {"enabled": True, "indicators": [dict(i) for i in indicators]}
            for name, indicators in _NARROW_ATOMIC.items()
        }
        override["operators"] = {"momentum": {"lags": [3]}}
        override["rolling_aggregation"] = {"windows": [5, 13]}
        return override

    monkeypatch.setattr(fb, "_base_override", _narrow_override)
    monkeypatch.setattr(fb, "END_DATE", _NARROW_END_DATE)


def _read_d_star_cache_dir(cache_dir: Path) -> Dict[str, float]:
    cache_paths = sorted(cache_dir.glob("d_star_*.json"))
    if not cache_paths:
        pytest.fail(f"expected d-star cache file under {cache_dir}, found none")
    if len(cache_paths) != 1:
        pytest.fail(
            f"expected exactly one d-star cache under {cache_dir}, found {len(cache_paths)}"
        )
    return read_d_star_json(cache_paths[0])








def _assert_nan_mask_gate(
    first_hashes: Dict[str, Dict[str, str]],
    second_hashes: Dict[str, Dict[str, str]],
    columns: List[str],
    *,
    label: str,
) -> None:
    """IC-First 值可變；NaN mask 必須在重跑時完全穩定。"""
    mismatches: List[str] = []
    for column in columns:
        if column not in first_hashes:
            mismatches.append(f"{column}: missing in first {label}")
            continue
        if column not in second_hashes:
            mismatches.append(f"{column}: missing in second {label}")
            continue
        if first_hashes[column]["nan_mask_sha256"] != second_hashes[column]["nan_mask_sha256"]:
            mismatches.append(f"{column}: nan_mask_sha256")
    if mismatches:
        pytest.fail(
            f"{label} NaN-mask mismatch count={len(mismatches)} "
            f"sample={mismatches[:5]}"
        )


class TestGolden:
    @pytest.mark.slow
    def test_batch2d_golden_files_are_complete_and_read_only(self) -> None:
        payloads = {}
        for name in ("cgsa_baseline", "provenance"):
            path = BATCH2D_GOLDEN_DIR / f"{name}.json"
            if not path.is_file():
                pytest.fail(f"missing required batch2d golden: {path}")
            payloads[name] = json.loads(path.read_text(encoding="utf-8"))

        for name in ("cgsa_baseline",):
            payload = payloads[name]
            frame = payload["frame"]
            assert frame["rows"] > 0
            assert frame["columns"] > 0
            assert len(frame["ordered_columns"]) == frame["columns"]
            assert set(frame["ordered_columns"]) == set(frame["per_column"])
            assert len(frame["row_index"]["sha256"]) == 64
            assert len(frame["ordered_column_sha256"]) == 64
            assert all(
                len(column_hashes["value_sha256"]) == 64
                and len(column_hashes["nan_mask_sha256"]) == 64
                for column_hashes in frame["per_column"].values()
            )

        provenance = payloads["provenance"]
        assert provenance["frame_column_to_layer"]
        assert provenance["cgsa_column_to_layer"]
        assert provenance["common_column_count"] > 0
        assert provenance["same_layer_for_common_columns"] is True






def test_batch2d_filter_parity_map_matches_registry_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1,L2")
    columns = ["close", "volume", "rolling"]
    column_layer_map = {"close": "L1", "volume": "L2", "rolling": "L3"}
    mapped = FeaturePreprocessor({"winsorization": {"method": "sigma"}}, column_layer_map=column_layer_map)
    l1_registry = FeaturePreprocessor({"winsorization": {"method": "sigma"}})
    l2_registry = FeaturePreprocessor({"winsorization": {"method": "sigma"}})

    mapped_columns = mapped._filter_fracdiff_target_columns(columns)
    expected = (
        l1_registry._filter_fracdiff_target_columns(["close"], source_layer="L1")
        + l2_registry._filter_fracdiff_target_columns(["volume"], source_layer="L2")
    )

    assert mapped_columns == expected
    assert "rolling" not in mapped_columns
    # FFSTAT Task 1.1（改寫：原斷言「對照缺欄 unknown 當非目標」）：對照缺欄 ⇒ fail-closed，不當非目標
    with pytest.raises(ValueError, match="缺 1/4"):
        mapped._filter_fracdiff_target_columns(columns + ["unknown"])


def test_batch2d_filter_parity_all_precedes_map(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "ALL")
    preprocessor = FeaturePreprocessor({"winsorization": {"method": "sigma"}}, column_layer_map={"known": "L6"})
    assert preprocessor._filter_fracdiff_target_columns(["known", "unknown"]) == [
        "known",
        "unknown",
    ]


def test_batch2d_filter_without_map_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FFSTAT Task 1.1（取代已退役之 `test_batch2d_filter_parity_regex_fallback_without_map`：該測試驗無對照時
    以欄名 `L<k>_` 解析層之退路，此退路依 SPEC §C「目標層」刪除）：無對照、無群組 layer ⇒ fail-closed。"""
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1,L2")
    preprocessor = FeaturePreprocessor({"winsorization": {"method": "sigma"}})
    with pytest.raises(ValueError, match="無層來源"):
        preprocessor._filter_fracdiff_target_columns(["L1_price", "L2_volume", "L3_rolling", "bare"])


def test_batch2d_read_d_star_json_exports_values(tmp_path: Path) -> None:
    path = tmp_path / "d_star_test.json"
    path.write_text(
        json.dumps(
            {
                "entries": {
                    "l1": {"d_star": 0.25},
                    "l2": {"d_star": 1},
                    "missing": {"d_star": None},
                }
            }
        ),
        encoding="utf-8",
    )
    assert read_d_star_json(path) == {"l1": 0.25, "l2": 1.0}


class TestP4Parity:


    @pytest.mark.slow
    @pytest.mark.requires_kline
    # 全規模層（小規模姊妹未覆蓋）：與 legacy 凍結 sha 不等之斷言只在凍結時同一份生產預設全特徵設定下有意義（584 秒）；窄設定 NaN 遮罩可重現性由姊妹 test_cgsa_narrow_rerun_nan_mask_reproducible 承擔
    @pytest.mark.fullscale
    def test_cgsa_baseline_runs_ic_first_not_legacy_frozen(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """CGSA regression：L65 B2 後不得再回到 legacy-era frozen full-output。"""
        _require_real_kline()
        frozen_cgsa = _load_golden("cgsa_baseline")

        _apply_batch2d_env(monkeypatch, use_cgsa=True)
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))
        with tempfile.TemporaryDirectory(prefix="batch2d_p4_cgsa_") as temp_dir:
            payload, _ = _run_cgsa(Path(temp_dir))
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work_repeat"))
        with tempfile.TemporaryDirectory(prefix="batch2d_p4_cgsa_repeat_") as temp_dir:
            repeat_payload, _ = _run_cgsa(Path(temp_dir))

        assert payload["frame"]["rows"] > 0
        assert payload["frame"]["columns"] > 0
        assert payload["frame"]["canonical_sha256"] != frozen_cgsa["frame"]["canonical_sha256"]
        assert payload["manifest_columns"]
        common_columns = sorted(
            set(payload["frame"]["per_column"]) & set(repeat_payload["frame"]["per_column"])
        )
        if not common_columns:
            pytest.fail("CGSA gate vacuous: no live columns overlap repeated run")
        _assert_nan_mask_gate(
            payload["frame"]["per_column"],
            repeat_payload["frame"]["per_column"],
            common_columns,
            label="CGSA common columns",
        )

    @pytest.mark.slow
    @pytest.mark.requires_kline
    def test_cgsa_narrow_rerun_nan_mask_reproducible(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """TESTSEL I10 小規模姊妹測試（上一條為生產預設全特徵、逾 300 秒，原樣保留列豁免——其「≠ legacy 凍結 sha」只在
        與凍結同設定時有意義）：同環境臂（pandas、L6.5 chunk 500、slowpath 序列、nested batch）、窄設定（各層仍在、
        欄數 > L6.5 chunk ⇒ 多 chunk 路徑）兩次 CGSA 生成，逐欄 NaN mask 完全相同。"""
        _require_real_kline()
        _apply_batch2d_env(monkeypatch, use_cgsa=True)
        _narrow_cgsa_run(monkeypatch)
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))
        with tempfile.TemporaryDirectory(prefix="batch2d_narrow_cgsa_") as temp_dir:
            payload, layers = _run_cgsa(Path(temp_dir))
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work_repeat"))
        with tempfile.TemporaryDirectory(prefix="batch2d_narrow_cgsa_repeat_") as temp_dir:
            repeat_payload, _ = _run_cgsa(Path(temp_dir))

        assert payload["frame"]["rows"] > 0
        assert payload["frame"]["columns"] > int(FREEZE_ENV_DEFAULTS["FFACT_L65_CHUNK_SIZE"])
        assert payload["manifest_columns"]
        assert {"L1", "L2", "L3", "L4", "L6"} <= set(layers.values()), sorted(set(layers.values()))
        common_columns = sorted(
            set(payload["frame"]["per_column"]) & set(repeat_payload["frame"]["per_column"])
        )
        if not common_columns:
            pytest.fail("CGSA gate vacuous: no live columns overlap repeated run")
        _assert_nan_mask_gate(
            payload["frame"]["per_column"],
            repeat_payload["frame"]["per_column"],
            common_columns,
            label="CGSA narrow common columns",
        )




