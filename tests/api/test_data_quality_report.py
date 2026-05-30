"""Unit tests for the data-quality dashboard report assembly (dq_v2).

Covers the 2026-05-29 quant-grade redesign:
  - coverage rebuild from first_valid/last_valid (was a dead all-1.0 metric)
  - honest NaN classification (warmup_only_high_nan vs real_problem)
  - group_breakdown (layer × tf)
  - schema_version cache invalidation
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from api.services.feature_factory_service import FeatureFactoryService


def _svc() -> FeatureFactoryService:
    return FeatureFactoryService.__new__(FeatureFactoryService)


def _ratios(d: dict) -> pd.Series:
    return pd.Series(d, dtype=float)


# ─── P0: coverage rebuild from first/last_valid ────────────────────────────


class TestCoverageRebuild:
    def test_warmup_drives_low_early_coverage(self):
        svc = _svc()
        total_rows = 100
        cols = ["a", "b"]
        # a: warmup 0 (valid from row 0); b: warmup 50 (valid from row 50)
        fv = {"a": 0, "b": 50}
        lv = {"a": 99, "b": 99}
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=cols,
            nan_ratios=_ratios({"a": 0.0, "b": 0.5}),
            first_valid_map=fv,
            last_valid_map=lv,
            row_nan_count=np.zeros(total_rows, dtype=np.int64),  # placeholder
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        cov = {p["index"]: p["coverage"] for p in report["coverage_timeline"]}
        # row 0: only 'a' valid → 50%
        assert cov[0] == pytest.approx(0.5)
        # min coverage must be < 1.0 (the bug was all-1.0)
        assert report["min_coverage"] < 1.0

    def test_all_valid_gives_full_coverage(self):
        svc = _svc()
        total_rows = 50
        cols = ["a", "b", "c"]
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=cols,
            nan_ratios=_ratios({c: 0.0 for c in cols}),
            first_valid_map={c: 0 for c in cols},
            last_valid_map={c: total_rows - 1 for c in cols},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        assert report["min_coverage"] == pytest.approx(1.0)
        assert report["is_clean"] is True

    def test_all_nan_column_counted_once_not_double(self):
        # all-NaN (fv=total_rows sentinel, lv=-1) must contribute exactly 1 to
        # every row's NaN count — not 2 (leading+trailing double-count bug).
        svc = _svc()
        total_rows = 10
        cols = ["good", "dead"]
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=cols,
            nan_ratios=_ratios({"good": 0.0, "dead": 1.0}),
            first_valid_map={"good": 0, "dead": total_rows},  # dead sentinel
            last_valid_map={"good": total_rows - 1, "dead": -1},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        # 2 features, 1 missing everywhere → coverage 0.5 everywhere (not 0.0)
        cov = [p["coverage"] for p in report["coverage_timeline"]]
        assert all(c == pytest.approx(0.5) for c in cov)

    def test_trailing_reduces_late_coverage(self):
        svc = _svc()
        total_rows = 100
        cols = ["a", "b"]
        # b stops being valid after row 49 (trailing)
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=cols,
            nan_ratios=_ratios({"a": 0.0, "b": 0.5}),
            first_valid_map={"a": 0, "b": 0},
            last_valid_map={"a": 99, "b": 49},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        cov = {p["index"]: p["coverage"] for p in report["coverage_timeline"]}
        assert cov[0] == pytest.approx(1.0)   # both valid early
        assert cov[99] == pytest.approx(0.5)  # only 'a' valid late


# ─── P1: honest NaN classification ─────────────────────────────────────────


class TestNaNClassification:
    def test_warmup_only_high_nan_is_benign(self):
        # 60% leading warmup, then fully valid → high NaN but warmup-only (benign)
        svc = _svc()
        total_rows = 100
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=["warmup_feat"],
            nan_ratios=_ratios({"warmup_feat": 0.60}),
            first_valid_map={"warmup_feat": 60},
            last_valid_map={"warmup_feat": 99},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        assert report["counts"]["warmup_only_high_nan"] == 1
        assert report["counts"]["real_problem"] == 0
        assert report["counts"]["high_nan"] == 1  # legacy total still counts it

    def test_mid_hole_is_real_problem(self):
        # valid span 0..99 but 40% NaN scattered inside → mid-hole (real problem)
        svc = _svc()
        total_rows = 100
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=["holey"],
            nan_ratios=_ratios({"holey": 0.40}),
            first_valid_map={"holey": 0},
            last_valid_map={"holey": 99},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        assert report["counts"]["real_problem"] == 1
        assert report["counts"]["warmup_only_high_nan"] == 0
        assert report["counts"]["mid_holes"] == 1

    def test_all_nan_is_real_problem(self):
        svc = _svc()
        total_rows = 100
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=["dead"],
            nan_ratios=_ratios({"dead": 1.0}),
            first_valid_map={"dead": total_rows},
            last_valid_map={"dead": -1},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        assert report["counts"]["real_problem"] == 1

    def test_low_nan_not_flagged(self):
        # 3% NaN (below 5% threshold) → not high_nan at all
        svc = _svc()
        total_rows = 1000
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=["clean"],
            nan_ratios=_ratios({"clean": 0.03}),
            first_valid_map={"clean": 30},
            last_valid_map={"clean": 999},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
        )
        assert report["counts"]["high_nan"] == 0
        assert report["counts"]["warmup_only_high_nan"] == 0
        assert report["counts"]["real_problem"] == 0


# ─── P3: group_breakdown ───────────────────────────────────────────────────


class TestGroupBreakdown:
    def test_layer_tf_aggregation(self):
        svc = _svc()
        total_rows = 100
        cols = ["x_l3_12h", "y_l3_12h", "z_l2_1h"]
        group_map = {
            "x_l3_12h": ("L3", "12h"),
            "y_l3_12h": ("L3", "12h"),
            "z_l2_1h": ("L2", "1h"),
        }
        report = svc._assemble_data_quality_report(
            total_rows=total_rows,
            columns=cols,
            nan_ratios=_ratios({"x_l3_12h": 0.6, "y_l3_12h": 0.0, "z_l2_1h": 0.0}),
            first_valid_map={"x_l3_12h": 60, "y_l3_12h": 0, "z_l2_1h": 0},
            last_valid_map={c: 99 for c in cols},
            row_nan_count=np.zeros(total_rows, dtype=np.int64),
            timestamps=[str(i) for i in range(total_rows)],
            rebuild_row_nan_from_valid=True,
            group_map=group_map,
        )
        gb = {(g["layer"], g["tf"]): g for g in report["group_breakdown"]}
        assert gb[("L3", "12h")]["feature_count"] == 2
        assert gb[("L3", "12h")]["warmup_only"] == 1   # x is warmup-only high-NaN
        assert gb[("L2", "1h")]["feature_count"] == 1

    def test_no_group_map_yields_empty_breakdown(self):
        svc = _svc()
        report = svc._assemble_data_quality_report(
            total_rows=10,
            columns=["a"],
            nan_ratios=_ratios({"a": 0.0}),
            first_valid_map={"a": 0},
            last_valid_map={"a": 9},
            row_nan_count=np.zeros(10, dtype=np.int64),
            timestamps=[str(i) for i in range(10)],
            rebuild_row_nan_from_valid=True,
        )
        assert report["group_breakdown"] == []


# ─── _build_group_map parsing ──────────────────────────────────────────────


class TestBuildGroupMap:
    def test_parses_layer_tf_from_stem(self):
        svc = _svc()
        c2p = {
            "col1": Path("/x/1h_L3_rolling_W3_Skew_1_shard00.parquet"),
            "col2": Path("/x/12h_L2_WorldQuant_part3.parquet"),
            "col3": Path("/x/1h_L1_trend_EMA.parquet"),
        }
        gm = svc._build_group_map(c2p)
        assert gm["col1"] == ("L3", "1h")
        assert gm["col2"] == ("L2", "12h")
        assert gm["col3"] == ("L1", "1h")

    def test_unparseable_stem_maps_to_question(self):
        svc = _svc()
        gm = svc._build_group_map({"c": Path("/x/garbage.parquet")})
        assert gm["c"] == ("?", "?")


# ─── schema_version on report ──────────────────────────────────────────────


class TestSchemaVersion:
    def test_report_carries_schema_version(self):
        svc = _svc()
        report = svc._assemble_data_quality_report(
            total_rows=10,
            columns=["a"],
            nan_ratios=_ratios({"a": 0.0}),
            first_valid_map={"a": 0},
            last_valid_map={"a": 9},
            row_nan_count=np.zeros(10, dtype=np.int64),
            timestamps=[str(i) for i in range(10)],
            rebuild_row_nan_from_valid=True,
        )
        assert report["schema_version"] == FeatureFactoryService._DATA_QUALITY_SCHEMA_VERSION

    def test_empty_report_carries_schema_version(self):
        assert (
            FeatureFactoryService._empty_data_quality_report()["schema_version"]
            == FeatureFactoryService._DATA_QUALITY_SCHEMA_VERSION
        )
