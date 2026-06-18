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
    _build_column_layer_map,
)
from momentum.FeatureEngineering.preprocessing._d_star_cache import read_d_star_json
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from scripts.freeze_batch2d_baseline import (
    FREEZE_ENV_DEFAULTS,
    KLINE_PATH,
    _run_cgsa,
    _run_control,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH2D_GOLDEN_DIR = REPO_ROOT / "tests" / "_golden" / "batch2d"
_L36_LAYERS = frozenset({"L3", "L4", "L5", "L6"})
_L12_LAYERS = frozenset({"L1", "L2"})
_T4_BLOCKED_REASON = (
    "T4 value parity BLOCKED per batch2d exact-only governance: pre-existing CGSA vs "
    "frame structural divergence (index dtype int64 vs datetime64, float32 vs float16 "
    "materialization, L7 dead-drop inventory) — out-of-scope for #2; see "
    "handoffs/20260616-d2-parity-investigation-composer.md §2"
)


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
    monkeypatch.setenv("FFACT_USE_CGSA", "1" if use_cgsa else "0")


def _read_d_star_cache_dir(cache_dir: Path) -> Dict[str, float]:
    cache_paths = sorted(cache_dir.glob("d_star_*.json"))
    if not cache_paths:
        pytest.fail(f"expected d-star cache file under {cache_dir}, found none")
    if len(cache_paths) != 1:
        pytest.fail(
            f"expected exactly one d-star cache under {cache_dir}, found {len(cache_paths)}"
        )
    return read_d_star_json(cache_paths[0])


def _subprocess_dstar_phase(phase: str) -> Dict[str, Any]:
    """隔離記憶體：子程序跑 frame/cgsa d* phase（fracdiff ON）。"""
    with tempfile.TemporaryDirectory(prefix=f"batch2d_p4_{phase}_") as temp_dir:
        out_path = Path(temp_dir) / "result.json"
        env = os.environ.copy()
        for key, value in FREEZE_ENV_DEFAULTS.items():
            env.setdefault(key, value)
        env["FFACT_USE_CGSA"] = "1" if phase == "cgsa" else "0"
        if phase != "cgsa":
            env.pop("FFACT_CGSA_WORK_DIR", None)
        runner = f"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = {str(REPO_ROOT)!r}
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.freeze_batch2d_baseline import (
    END_DATE,
    KLINE_PATH,
    START_DATE,
    SYMBOL,
    TIMEFRAME,
    _base_override,
)
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing._d_star_cache import read_d_star_json
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.factories import create_feature_factory

def _read_cache(cache_dir: Path):
    paths = sorted(cache_dir.glob("d_star_*.json"))
    if len(paths) != 1:
        raise RuntimeError(f"expected one d-star cache, found {{len(paths)}}")
    return read_d_star_json(paths[0])

with tempfile.TemporaryDirectory(prefix="batch2d_p4_worker_") as temp_dir:
    temp_root = Path(temp_dir)
    override = _base_override()
    override["preprocessing"] = {{"fractional_differencing": {{"enabled": True}}}}
    if {phase!r} == "frame":
        os.environ["FFACT_USE_CGSA"] = "0"
        feature_dir = temp_root / "frame" / "features"
        cache_dir = temp_root / "frame" / "d_star"
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: cache_dir)
        factory = create_feature_factory(
            cache_dir=str(KLINE_PATH.parent), validate_continuity=False
        )
        factory._storage = FeatureStorage(str(feature_dir))
        result = factory.generate_features(
            SYMBOL,
            TIMEFRAME,
            config_override=override,
            force_regenerate=True,
            start_date=START_DATE,
            end_date=END_DATE,
            persist=True,
        )
        if result.features_df.empty:
            raise RuntimeError("non-CGSA frame path returned empty features_df")
        column_layer_map = dict(factory._column_layer_map or {{}})
        if not column_layer_map:
            raise RuntimeError("non-CGSA frame path missing column_layer_map")
        payload = {{
            "d_star": _read_cache(cache_dir),
            "column_layer_map": column_layer_map,
        }}
    else:
        os.environ["FFACT_USE_CGSA"] = "1"
        os.environ["FFACT_CGSA_WORK_DIR"] = str(temp_root / "cgsa" / "registry")
        feature_dir = temp_root / "cgsa" / "features"
        cache_dir = temp_root / "cgsa" / "d_star"
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: cache_dir)
        factory = create_feature_factory(
            cache_dir=str(KLINE_PATH.parent), validate_continuity=False
        )
        factory._storage = FeatureStorage(str(feature_dir))
        factory.generate_features(
            SYMBOL,
            TIMEFRAME,
            config_override=override,
            force_regenerate=True,
            start_date=START_DATE,
            end_date=END_DATE,
            persist=True,
        )
        payload = {{"d_star": _read_cache(cache_dir)}}
    Path({str(out_path)!r}).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
"""
        subprocess.run(
            [sys.executable, "-c", runner],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        return json.loads(out_path.read_text(encoding="utf-8"))


def _l12_dstar_intersection(
    frame_d_star: Dict[str, float],
    cgsa_d_star: Dict[str, float],
    bare_layer_map: Dict[str, str],
) -> List[str]:
    return sorted(
        column
        for column in frame_d_star
        if column in cgsa_d_star
        and bare_layer_map.get(column) in _L12_LAYERS
    )


def _tagged_l36_columns(provenance: Dict[str, str]) -> List[str]:
    return sorted(column for column, layer in provenance.items() if layer in _L36_LAYERS)


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
        for name in ("control", "cgsa_baseline", "provenance"):
            path = BATCH2D_GOLDEN_DIR / f"{name}.json"
            if not path.is_file():
                pytest.fail(f"missing required batch2d golden: {path}")
            payloads[name] = json.loads(path.read_text(encoding="utf-8"))

        for name in ("control", "cgsa_baseline"):
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


def test_batch2d_map_unit_keep_first_and_matches_combine() -> None:
    index = pd.RangeIndex(2)
    layers = [
        pd.DataFrame({"shared": [1.0, 2.0], "l1": [3.0, 4.0]}, index=index),
        pd.DataFrame({"shared": [5.0, 6.0], "l2": [7.0, 8.0]}, index=index),
        pd.DataFrame(index=index),
        None,
        pd.DataFrame({"l5": [9.0, 10.0]}, index=index),
        pd.DataFrame({"l6": [11.0, 12.0]}, index=index),
    ]

    column_layer_map = _build_column_layer_map(layers)
    combined = FeatureFactory._combine_layers(layers, context="batch2d_map_unit")

    assert column_layer_map == {
        "shared": "L1",
        "l1": "L1",
        "l2": "L2",
        "l5": "L5",
        "l6": "L6",
    }
    assert set(combined.columns) == set(column_layer_map)


def test_batch2d_map_unit_rejects_non_string_column() -> None:
    layers = [pd.DataFrame({1: [1.0]})]
    with pytest.raises(AssertionError, match="non-str column"):
        _build_column_layer_map(layers)


def test_batch2d_filter_parity_map_matches_registry_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1,L2")
    columns = ["close", "volume", "rolling", "unknown"]
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
    assert "unknown" not in mapped_columns


def test_batch2d_filter_parity_all_precedes_map(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "ALL")
    preprocessor = FeaturePreprocessor({}, column_layer_map={"known": "L6"})
    assert preprocessor._filter_fracdiff_target_columns(["known", "unknown"]) == [
        "known",
        "unknown",
    ]


def test_batch2d_filter_parity_regex_fallback_without_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1,L2")
    preprocessor = FeaturePreprocessor({})
    assert preprocessor._filter_fracdiff_target_columns(
        ["L1_price", "L2_volume", "L3_rolling", "bare"]
    ) == ["L1_price", "L2_volume"]


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
    def test_t3_d_star_parity_exact_on_l12_intersection(self) -> None:
        """T3 主 gate：非 CGSA vs CGSA L1/L2 交集 d* exact，0 mismatch。"""
        _require_real_kline()
        frame_payload = _subprocess_dstar_phase("frame")
        cgsa_payload = _subprocess_dstar_phase("cgsa")
        frame_d_star = {str(k): float(v) for k, v in frame_payload["d_star"].items()}
        cgsa_d_star = {str(k): float(v) for k, v in cgsa_payload["d_star"].items()}
        bare_layer_map = {
            str(column): str(layer)
            for column, layer in frame_payload["column_layer_map"].items()
        }

        intersection = _l12_dstar_intersection(frame_d_star, cgsa_d_star, bare_layer_map)
        if not intersection:
            pytest.fail("T3 vacuous: L1/L2 d* intersection is empty")

        mismatches = [
            column
            for column in intersection
            if frame_d_star[column] != cgsa_d_star[column]
        ]
        if mismatches:
            sample = mismatches[:5]
            details = [
                f"{column}: frame={frame_d_star[column]} cgsa={cgsa_d_star[column]}"
                for column in sample
            ]
            pytest.fail(
                f"T3 d* mismatch count={len(mismatches)}/{len(intersection)} "
                f"sample={details}"
            )

        assert len(mismatches) == 0
        assert len(intersection) >= 3000

    @pytest.mark.slow
    def test_control_l3_l6_runs_ic_first_not_legacy_frozen(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """control：L65 B2 後不得再回到 legacy-era frozen full-output。"""
        _require_real_kline()
        frozen_control = _load_golden("control")
        provenance = _load_golden("provenance")["frame_column_to_layer"]
        # Provenance 含 CGSA registry 全欄位；control baseline 僅含 frame 實際輸出欄。
        l36_columns = [
            column
            for column in _tagged_l36_columns(provenance)
            if column in frozen_control["frame"]["per_column"]
        ]
        if not l36_columns:
            pytest.fail("control gate vacuous: no L3-L6 columns in frozen control")

        _apply_batch2d_env(monkeypatch, use_cgsa=False)
        with tempfile.TemporaryDirectory(prefix="batch2d_p4_control_") as temp_dir:
            payload, _ = _run_control(Path(temp_dir))
        with tempfile.TemporaryDirectory(prefix="batch2d_p4_control_repeat_") as temp_dir:
            repeat_payload, _ = _run_control(Path(temp_dir))

        assert payload["frame"]["rows"] > 0
        assert payload["frame"]["columns"] > 0
        assert payload["frame"]["canonical_sha256"] != frozen_control["frame"]["canonical_sha256"]
        live_per_column = payload["frame"]["per_column"]
        repeat_per_column = repeat_payload["frame"]["per_column"]
        live_l36 = [column for column in l36_columns if column in live_per_column]
        assert live_l36, "control gate vacuous: no live L3-L6 columns under IC-First"
        assert all(
            column in repeat_per_column for column in live_l36
        ), "control repeat gate vacuous: repeated run missing live L3-L6 columns"
        _assert_nan_mask_gate(
            live_per_column,
            repeat_per_column,
            live_l36,
            label="control L3-L6",
        )

    @pytest.mark.slow
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


def test_t4_value_parity_inventory_record_only() -> None:
    """T4 value parity：只記 inventory，不 assert exact（三方裁定 out-of-scope）。"""
    control = _load_golden("control")
    cgsa = _load_golden("cgsa_baseline")
    provenance = _load_golden("provenance")
    frame_map = provenance["frame_column_to_layer"]
    cgsa_map = provenance["cgsa_column_to_layer"]

    l12_expected = sorted(
        column
        for column in frame_map
        if frame_map[column] in _L12_LAYERS and cgsa_map.get(column) in _L12_LAYERS
    )
    control_cols = set(control["frame"]["per_column"])
    cgsa_cols = set(cgsa["frame"]["per_column"])
    l12_present_both = [
        column for column in l12_expected if column in control_cols and column in cgsa_cols
    ]

    value_matches = 0
    mask_matches = 0
    for column in l12_present_both:
        control_entry = control["frame"]["per_column"][column]
        cgsa_entry = cgsa["frame"]["per_column"][column]
        if control_entry["value_sha256"] == cgsa_entry["value_sha256"]:
            value_matches += 1
        if control_entry["nan_mask_sha256"] == cgsa_entry["nan_mask_sha256"]:
            mask_matches += 1

    inventory = {
        "blocked_reason": _T4_BLOCKED_REASON,
        "l12_expected_provenance": len(l12_expected),
        "l12_present_both_outputs": len(l12_present_both),
        "value_hash_matches": value_matches,
        "nan_mask_hash_matches": mask_matches,
        "row_index_hash_equal": (
            control["frame"]["row_index"]["sha256"]
            == cgsa["frame"]["row_index"]["sha256"]
        ),
        "control_columns": control["frame"]["columns"],
        "cgsa_columns": cgsa["frame"]["columns"],
    }
    assert inventory["l12_expected_provenance"] > 0
    assert inventory["l12_present_both_outputs"] > 0
    assert inventory["value_hash_matches"] == 0
    assert inventory["nan_mask_hash_matches"] == len(l12_present_both)
    assert inventory["row_index_hash_equal"] is False


@pytest.mark.skip(reason=_T4_BLOCKED_REASON)
@pytest.mark.slow
def test_t4_value_parity_exact_blocked() -> None:
    """T4 exact gate 分案：禁 rtol/atol，維持 skip 供 inventory 追蹤。"""
    pytest.fail("T4 exact value parity is BLOCKED for batch2d #2 scope")
