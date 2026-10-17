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
    mapped = FeaturePreprocessor({}, column_layer_map=column_layer_map)
    l1_registry = FeaturePreprocessor({})
    l2_registry = FeaturePreprocessor({})

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
    preprocessor = FeaturePreprocessor({}, column_layer_map={"known": "L6"})
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
    preprocessor = FeaturePreprocessor({})
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




