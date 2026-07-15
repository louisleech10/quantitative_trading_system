"""LA-0 B1: pit_stats 七原語單元 + M-lookahead 驗收。

SPEC: docs/IC_LA0_SPEC.md §MS / LA0-0
TODO: docs/IC_LA0_TODO.md Task 1.1
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.pit_stats import (
    MIN_SAMPLES,
    PIT_STATS_VERSION,
    effective_count,
    first_valid_index,
    pit_expanding_bounds,
    pit_expanding_mad,
    pit_expanding_mean_std,
    pit_expanding_qcut_label,
    pit_expanding_rank,
    pit_train_fit,
    pit_valid_mask,
    rolling_window_rank_corr,
)

ATOL = 1e-12
RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def dense_series() -> pd.Series:
    """無 NaN dense 序列，長度 250，方便 first_valid==min_samples-1。"""
    n = 250
    vals = RNG.normal(size=n).cumsum() * 0.01 + 100.0
    # 注入 ties
    vals[10:15] = vals[10]
    return pd.Series(vals, index=pd.RangeIndex(n, name="t"), name="feat")


@pytest.fixture
def sparse_series() -> pd.Series:
    """前 20 為 NaN，其後 dense；first_valid 應晚於 min_samples-1。"""
    n = 250
    vals = RNG.normal(size=n)
    vals[:20] = np.nan
    return pd.Series(vals, index=pd.RangeIndex(n), name="sparse")


# ---------------------------------------------------------------------------
# §MS helpers
# ---------------------------------------------------------------------------
class TestSectionMS:
    def test_canonical_min_samples_is_100(self) -> None:
        assert MIN_SAMPLES == 100

    def test_first_valid_dense_is_min_samples_minus_one(self, dense_series: pd.Series) -> None:
        fv = first_valid_index(dense_series, min_samples=MIN_SAMPLES)
        assert fv == MIN_SAMPLES - 1  # 99, 禁 hard-code == 100
        assert fv != MIN_SAMPLES

    def test_first_valid_with_nan_uses_effective_count(
        self, sparse_series: pd.Series
    ) -> None:
        counts = effective_count(sparse_series)
        fv = first_valid_index(sparse_series, min_samples=MIN_SAMPLES)
        assert fv is not None
        assert counts[fv] >= MIN_SAMPLES
        if fv > 0:
            assert counts[fv - 1] < MIN_SAMPLES
        # 前 20 NaN → first_valid = 20 + 99 = 119
        assert fv == 20 + MIN_SAMPLES - 1

    def test_valid_mask_aligns_and_matches_count(self, dense_series: pd.Series) -> None:
        mask = pit_valid_mask(dense_series, min_samples=MIN_SAMPLES)
        assert len(mask) == len(dense_series)
        assert mask.index.equals(dense_series.index)
        assert mask.dtype == bool
        assert not bool(mask.iloc[MIN_SAMPLES - 2])
        assert bool(mask.iloc[MIN_SAMPLES - 1])
        assert bool(mask.iloc[-1])

    def test_version_exported(self) -> None:
        assert isinstance(PIT_STATS_VERSION, str)
        assert len(PIT_STATS_VERSION) > 0


# ---------------------------------------------------------------------------
# rolling_window_rank_corr
# ---------------------------------------------------------------------------
class TestRollingWindowRankCorr:
    def _make_xy(self, n: int = 200, f: int = 8) -> tuple[np.ndarray, np.ndarray]:
        x = RNG.normal(size=(n, f))
        # 讓部分特徵與 y 相關
        y = x[:, 0] * 0.5 + RNG.normal(size=n) * 0.1
        # ties
        x[5:10, 1] = x[5, 1]
        return x, y

    def test_signature_freeze(self) -> None:
        """鎖定凍結公開簽名：位置參數 (x,y,window,stride) + ties 預設。

        chunk_size/use_numba 為 RULING-1/T4 keyword-only 擴展，允許存在，
        但不得改寫凍結位置參數語意。
        """
        sig = inspect.signature(rolling_window_rank_corr)
        params = list(sig.parameters.values())
        # 位置參數順序（前 4 個）：x, y, window, stride
        pos_names = [
            p.name
            for p in params
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        assert pos_names[:4] == ["x", "y", "window", "stride"]
        # stride 必填、無預設（凍結 TODO Task 1.1；有 default 即漂移）
        stride_p = sig.parameters["stride"]
        assert stride_p.default is inspect.Parameter.empty
        # ties 在位置/keyword 區，預設 'average'
        assert "ties" in sig.parameters
        ties_p = sig.parameters["ties"]
        assert ties_p.default == "average"
        assert ties_p.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
        # RULING-1/T4 擴展必須 keyword-only
        for name in ("chunk_size", "use_numba"):
            assert name in sig.parameters
            assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY

    def test_shape_emitted_ends(self) -> None:
        x, y = self._make_xy()
        window, stride = 21, 1
        out = rolling_window_rank_corr(x, y, window=window, stride=stride)
        n_expected = (x.shape[0] - window) // stride + 1
        assert out.shape == (n_expected, x.shape[1])

    def test_stride(self) -> None:
        x, y = self._make_xy()
        out = rolling_window_rank_corr(x, y, window=21, stride=5)
        n_expected = (x.shape[0] - 21) // 5 + 1
        assert out.shape[0] == n_expected

    def test_numba_vs_numpy_equivalence(self) -> None:
        x, y = self._make_xy(n=120, f=6)
        a = rolling_window_rank_corr(
            x, y, window=21, stride=1, use_numba=True, chunk_size=None
        )
        b = rolling_window_rank_corr(
            x, y, window=21, stride=1, use_numba=False, chunk_size=None
        )
        np.testing.assert_allclose(a, b, atol=ATOL, equal_nan=True)

    def test_chunk_vs_no_chunk_equivalence(self) -> None:
        x, y = self._make_xy(n=100, f=20)
        full = rolling_window_rank_corr(
            x, y, window=21, stride=1, use_numba=True, chunk_size=None
        )
        chunked = rolling_window_rank_corr(
            x, y, window=21, stride=1, use_numba=True, chunk_size=7
        )
        np.testing.assert_allclose(full, chunked, atol=ATOL, equal_nan=True)

    def test_matches_per_window_spearman_oracle(self) -> None:
        x, y = self._make_xy(n=80, f=3)
        window = 15
        got = rolling_window_rank_corr(
            x, y, window=window, stride=1, use_numba=False, chunk_size=None
        )
        for oi, end in enumerate(range(window, len(y) + 1)):
            start = end - window
            for fi in range(x.shape[1]):
                rx = pd.Series(x[start:end, fi]).rank(method="average")
                ry = pd.Series(y[start:end]).rank(method="average")
                expected = float(rx.corr(ry))  # pearson of ranks
                if np.isnan(expected):
                    assert np.isnan(got[oi, fi])
                else:
                    assert got[oi, fi] == pytest.approx(expected, abs=ATOL)

    def test_rolling_neq_global_rank_then_rolling(self) -> None:
        """防混用：窗內 rank ≠ 全序列 pre-rank + rolling pearson。"""
        x, y = self._make_xy(n=150, f=4)
        window = 21
        window_rank = rolling_window_rank_corr(
            x, y, window=window, stride=1, use_numba=True, chunk_size=None
        )
        # global pre-rank then rolling pearson (legacy leak path)
        rx = pd.DataFrame(x).rank(axis=0, method="average").to_numpy(dtype=float)
        ry = pd.Series(y).rank(method="average").to_numpy(dtype=float)
        n_rows = rx.shape[0]
        csum_x = np.vstack([np.zeros((1, rx.shape[1])), np.cumsum(rx, axis=0)])
        csum_x2 = np.vstack([np.zeros((1, rx.shape[1])), np.cumsum(rx * rx, axis=0)])
        csum_xy = np.vstack(
            [np.zeros((1, rx.shape[1])), np.cumsum(rx * ry[:, None], axis=0)]
        )
        csum_y = np.concatenate(([0.0], np.cumsum(ry)))
        csum_y2 = np.concatenate(([0.0], np.cumsum(ry * ry)))
        starts = np.arange(0, n_rows - window + 1)
        ends = starts + window
        sum_x = csum_x[ends] - csum_x[starts]
        sum_x2 = csum_x2[ends] - csum_x2[starts]
        sum_xy = csum_xy[ends] - csum_xy[starts]
        sum_y = csum_y[ends] - csum_y[starts]
        sum_y2 = csum_y2[ends] - csum_y2[starts]
        w = float(window)
        cov = sum_xy - (sum_x * sum_y[:, None]) / w
        var_x = sum_x2 - (sum_x * sum_x) / w
        var_y = sum_y2 - (sum_y * sum_y) / w
        with np.errstate(divide="ignore", invalid="ignore"):
            global_rank = cov / np.sqrt(var_x * var_y[:, None])
        global_rank[~np.isfinite(global_rank)] = np.nan

        # 至少部分 emitted 應不同（否則此 fixture 無鑑別力）
        both_finite = np.isfinite(window_rank) & np.isfinite(global_rank)
        assert both_finite.any()
        diffs = np.abs(window_rank[both_finite] - global_rank[both_finite])
        assert float(np.max(diffs)) > 1e-6

    def test_rolling_neq_expanding_rank_corr(self) -> None:
        """P0-1 鎖：『窗內 rank-corr』≠『expanding-rank-then-corr』。

        非僅排除 global pre-rank；此測鎖定語意=每窗內 rank，非逐 t 用
        [0..t] 全歷史 rank 再 corr（expanding 冒充 rolling）。
        """
        x, y = self._make_xy(n=150, f=4)
        window = 21
        rolling = rolling_window_rank_corr(
            x, y, window=window, stride=1, use_numba=False, chunk_size=None
        )
        n_bars, n_features = x.shape
        n_out = n_bars - window + 1
        expanding = np.empty((n_out, n_features), dtype=np.float64)
        for oi in range(n_out):
            # end exclusive = window + oi；history = [0..end)
            end = window + oi
            y_hist = y[:end]
            ry = pd.Series(y_hist).rank(method="average").to_numpy(dtype=float)
            for fi in range(n_features):
                rx = pd.Series(x[:end, fi]).rank(method="average").to_numpy(
                    dtype=float
                )
                expected = float(pd.Series(rx).corr(pd.Series(ry)))
                expanding[oi, fi] = expected

        both_finite = np.isfinite(rolling) & np.isfinite(expanding)
        assert both_finite.any()
        diffs = np.abs(rolling[both_finite] - expanding[both_finite])
        assert float(np.max(diffs)) > 1e-6

    def test_m_lookahead_early_equal(self) -> None:
        x, y = self._make_xy(n=180, f=5)
        window, stride, tr = 21, 1, 30
        full = rolling_window_rank_corr(x, y, window=window, stride=stride)
        trunc = rolling_window_rank_corr(x[:-tr], y[:-tr], window=window, stride=stride)
        # emitted ends with end < n-TR → end index = window-1 + k*stride
        # full[k] corresponds to end = window - 1 + k (0-based end exclusive? )
        # start=0 → end exclusive window, end inclusive index window-1
        n = x.shape[0]
        keep = []
        for k in range(full.shape[0]):
            end_inclusive = window - 1 + k * stride
            if end_inclusive < n - tr:
                keep.append(k)
        keep_arr = np.array(keep, dtype=int)
        assert len(keep_arr) > 0
        np.testing.assert_allclose(
            full[keep_arr], trunc[: len(keep_arr)], atol=ATOL, equal_nan=True
        )

    def test_window_gt_n_empty(self) -> None:
        x = RNG.normal(size=(10, 2))
        y = RNG.normal(size=10)
        out = rolling_window_rank_corr(x, y, window=50, stride=1)
        assert out.shape == (0, 2)


# ---------------------------------------------------------------------------
# pit_expanding_qcut_label
# ---------------------------------------------------------------------------
class TestPitExpandingQcutLabel:
    def test_warmup_nan_and_first_valid(
        self, dense_series: pd.Series
    ) -> None:
        ms = 20
        labels = pit_expanding_qcut_label(dense_series, q=5, min_samples=ms)
        assert labels.index.equals(dense_series.index)
        assert labels.iloc[: ms - 1].isna().all()
        assert labels.iloc[ms - 1:].notna().any()
        fv = first_valid_index(dense_series, min_samples=ms)
        assert fv == ms - 1
        assert pd.notna(labels.iloc[fv])

    def test_returns_labels_not_values(self, dense_series: pd.Series) -> None:
        labels = pit_expanding_qcut_label(dense_series, q=4, min_samples=30)
        valid = labels.dropna()
        assert len(valid) > 0
        # labels are bin ids 0..q-1 (possibly fewer with drop)
        assert valid.min() >= 0
        assert valid.max() < 4
        # not raw feature values
        assert not np.allclose(valid.to_numpy(), dense_series.loc[valid.index].to_numpy())

    def test_m_lookahead(self, dense_series: pd.Series) -> None:
        ms, tr = 25, 40
        full = pit_expanding_qcut_label(dense_series, q=5, min_samples=ms)
        trunc = pit_expanding_qcut_label(dense_series.iloc[:-tr], q=5, min_samples=ms)
        fv = first_valid_index(dense_series, min_samples=ms)
        assert fv is not None
        end = len(dense_series) - tr
        a = full.iloc[fv:end].to_numpy(dtype=float)
        b = trunc.iloc[fv:end].to_numpy(dtype=float)
        np.testing.assert_allclose(a, b, atol=ATOL, equal_nan=True)

    def test_all_nan(self) -> None:
        s = pd.Series([np.nan] * 50)
        out = pit_expanding_qcut_label(s, q=3, min_samples=10)
        assert out.isna().all()

    def test_empty(self) -> None:
        s = pd.Series([], dtype=float)
        out = pit_expanding_qcut_label(s, q=3, min_samples=10)
        assert len(out) == 0


# ---------------------------------------------------------------------------
# pit_expanding_bounds
# ---------------------------------------------------------------------------
class TestPitExpandingBounds:
    def test_warmup_is_pm_inf(self, dense_series: pd.Series) -> None:
        ms = 30
        lo, hi = pit_expanding_bounds(dense_series, 0.05, 0.95, min_samples=ms)
        assert lo.iloc[: ms - 1].eq(-np.inf).all()
        assert hi.iloc[: ms - 1].eq(np.inf).all()
        fv = first_valid_index(dense_series, min_samples=ms)
        assert fv is not None
        assert np.isfinite(lo.iloc[fv])
        assert np.isfinite(hi.iloc[fv])
        assert lo.iloc[fv] <= hi.iloc[fv]

    def test_m_lookahead(self, dense_series: pd.Series) -> None:
        ms, tr = 30, 40
        lo_f, hi_f = pit_expanding_bounds(dense_series, 0.01, 0.99, min_samples=ms)
        lo_t, hi_t = pit_expanding_bounds(
            dense_series.iloc[:-tr], 0.01, 0.99, min_samples=ms
        )
        fv = first_valid_index(dense_series, min_samples=ms)
        assert fv is not None
        end = len(dense_series) - tr
        np.testing.assert_allclose(
            lo_f.iloc[fv:end].to_numpy(),
            lo_t.iloc[fv:end].to_numpy(),
            atol=ATOL,
            equal_nan=True,
        )
        np.testing.assert_allclose(
            hi_f.iloc[fv:end].to_numpy(),
            hi_t.iloc[fv:end].to_numpy(),
            atol=ATOL,
            equal_nan=True,
        )

    def test_n_lt_min_samples_all_inf(self) -> None:
        s = pd.Series(RNG.normal(size=50))
        lo, hi = pit_expanding_bounds(s, 0.1, 0.9, min_samples=100)
        assert lo.eq(-np.inf).all()
        assert hi.eq(np.inf).all()


# ---------------------------------------------------------------------------
# pit_expanding_rank
# ---------------------------------------------------------------------------
class TestPitExpandingRank:
    def test_first_valid_and_ties(self) -> None:
        # controlled: values [1,2,2,3,...] after warmup
        vals = np.arange(1, 121, dtype=float)
        vals[50] = vals[51]  # ties
        s = pd.Series(vals)
        ms = 10
        ranks = pit_expanding_rank(s, min_samples=ms, ties="average")
        assert ranks.iloc[: ms - 1].isna().all()
        # at t=ms-1, hist = 1..ms, rank of current = ms
        assert ranks.iloc[ms - 1] == pytest.approx(float(ms), abs=ATOL)

    def test_m_lookahead(self, dense_series: pd.Series) -> None:
        ms, tr = 20, 35
        full = pit_expanding_rank(dense_series, min_samples=ms)
        trunc = pit_expanding_rank(dense_series.iloc[:-tr], min_samples=ms)
        fv = first_valid_index(dense_series, min_samples=ms)
        assert fv is not None
        end = len(dense_series) - tr
        np.testing.assert_allclose(
            full.iloc[fv:end].to_numpy(),
            trunc.iloc[fv:end].to_numpy(),
            atol=ATOL,
            equal_nan=True,
        )


# ---------------------------------------------------------------------------
# pit_expanding_mean_std
# ---------------------------------------------------------------------------
class TestPitExpandingMeanStd:
    def test_ddof_is_one(self) -> None:
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0] + list(RNG.normal(size=20)))
        ms = 5
        mean, std = pit_expanding_mean_std(s, min_samples=ms)
        # at t=4 (0-based), hist=[1,2,3,4,5], sample std ddof=1
        expected_std = float(np.std([1.0, 2.0, 3.0, 4.0, 5.0], ddof=1))
        expected_mean = 3.0
        assert mean.iloc[4] == pytest.approx(expected_mean, abs=ATOL)
        assert std.iloc[4] == pytest.approx(expected_std, abs=ATOL)
        # prove not ddof=0
        wrong = float(np.std([1.0, 2.0, 3.0, 4.0, 5.0], ddof=0))
        assert abs(std.iloc[4] - wrong) > 1e-9

    def test_std_zero_constant(self) -> None:
        s = pd.Series([7.0] * 50)
        mean, std = pit_expanding_mean_std(s, min_samples=10)
        assert mean.iloc[9] == pytest.approx(7.0, abs=ATOL)
        assert std.iloc[9] == pytest.approx(0.0, abs=ATOL)

    def test_m_lookahead(self, dense_series: pd.Series) -> None:
        ms, tr = 30, 40
        m_f, s_f = pit_expanding_mean_std(dense_series, min_samples=ms)
        m_t, s_t = pit_expanding_mean_std(dense_series.iloc[:-tr], min_samples=ms)
        fv = first_valid_index(dense_series, min_samples=ms)
        assert fv is not None
        end = len(dense_series) - tr
        np.testing.assert_allclose(
            m_f.iloc[fv:end], m_t.iloc[fv:end], atol=ATOL, equal_nan=True
        )
        np.testing.assert_allclose(
            s_f.iloc[fv:end], s_t.iloc[fv:end], atol=ATOL, equal_nan=True
        )


# ---------------------------------------------------------------------------
# pit_expanding_mad
# ---------------------------------------------------------------------------
class TestPitExpandingMad:
    def test_returns_median_and_mad(self) -> None:
        s = pd.Series(np.linspace(0, 100, 120))
        med, mad = pit_expanding_mad(s, min_samples=20)
        assert med.iloc[:19].isna().all()
        assert mad.iloc[:19].isna().all()
        # constant after? no — linear
        assert pd.notna(med.iloc[19])
        assert pd.notna(mad.iloc[19])
        finite = s.iloc[:20].to_numpy()
        exp_med = float(np.median(finite))
        exp_mad = float(np.median(np.abs(finite - exp_med)))
        assert med.iloc[19] == pytest.approx(exp_med, abs=ATOL)
        assert mad.iloc[19] == pytest.approx(exp_mad, abs=ATOL)

    def test_mad_zero_constant(self) -> None:
        s = pd.Series([3.0] * 40)
        med, mad = pit_expanding_mad(s, min_samples=10)
        assert med.iloc[9] == pytest.approx(3.0, abs=ATOL)
        assert mad.iloc[9] == pytest.approx(0.0, abs=ATOL)

    def test_m_lookahead(self, dense_series: pd.Series) -> None:
        ms, tr = 25, 40
        med_f, mad_f = pit_expanding_mad(dense_series, min_samples=ms)
        med_t, mad_t = pit_expanding_mad(dense_series.iloc[:-tr], min_samples=ms)
        fv = first_valid_index(dense_series, min_samples=ms)
        assert fv is not None
        end = len(dense_series) - tr
        np.testing.assert_allclose(
            med_f.iloc[fv:end], med_t.iloc[fv:end], atol=ATOL, equal_nan=True
        )
        np.testing.assert_allclose(
            mad_f.iloc[fv:end], mad_t.iloc[fv:end], atol=ATOL, equal_nan=True
        )


# ---------------------------------------------------------------------------
# pit_train_fit
# ---------------------------------------------------------------------------
class TestPitTrainFit:
    def test_fit_on_mask_transform_full_no_leak(self) -> None:
        df = pd.DataFrame(
            {
                "a": np.arange(20, dtype=float),
                "b": np.arange(100, 120, dtype=float),
            }
        )
        fit_mask = np.zeros(20, dtype=bool)
        fit_mask[:10] = True  # only first 10 for fit

        def transform_fn(fit_df: pd.DataFrame, full_df: pd.DataFrame) -> pd.DataFrame:
            # winsor-like: clip to fit quantiles
            lo = fit_df.quantile(0.1)
            hi = fit_df.quantile(0.9)
            # record that we only saw fit rows
            assert len(fit_df) == 10
            return full_df.clip(lo, hi, axis=1)

        out = pit_train_fit(df, fit_mask, transform_fn)
        assert out.shape == df.shape
        assert out.index.equals(df.index)
        # values outside fit range should be clipped using fit-only bounds
        lo = df.iloc[:10].quantile(0.1)
        hi = df.iloc[:10].quantile(0.9)
        expected = df.clip(lo, hi, axis=1)
        pd.testing.assert_frame_equal(out, expected)

    def test_empty_mask_raises(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError, match="fit_mask"):
            pit_train_fit(df, np.array([False, False, False]), lambda f, full: full)

    def test_m_lookahead_train_segment_stable(self) -> None:
        """截尾不影響 train mask 段（fit 不看 future）。"""
        n = 80
        df = pd.DataFrame({"x": RNG.normal(size=n).cumsum()})
        fit_mask = np.zeros(n, dtype=bool)
        fit_mask[:40] = True
        tr = 15

        def zscore(fit_df: pd.DataFrame, full_df: pd.DataFrame) -> pd.DataFrame:
            mu = fit_df.mean()
            sigma = fit_df.std(ddof=1).replace(0, np.nan)
            return (full_df - mu) / sigma

        full = pit_train_fit(df, fit_mask, zscore)
        trunc = pit_train_fit(df.iloc[:-tr], fit_mask[:-tr], zscore)
        # train segment [0,40) must be equal
        np.testing.assert_allclose(
            full.iloc[:40].to_numpy(),
            trunc.iloc[:40].to_numpy(),
            atol=ATOL,
            equal_nan=True,
        )


# ---------------------------------------------------------------------------
# FR-ready (no production factor_return_analyzer)
# ---------------------------------------------------------------------------
class TestFRReady:
    def test_qcut_label_and_bounds_serve_fr_semantics(
        self, dense_series: pd.Series
    ) -> None:
        """FR 語意：qcut label 作分位桶 + bounds 作 winsor；不呼叫 production FR。"""
        labels = pit_expanding_qcut_label(dense_series, q=5, min_samples=50)
        lo, hi = pit_expanding_bounds(dense_series, 0.01, 0.99, min_samples=50)
        valid = pit_valid_mask(dense_series, min_samples=50)
        # FR-like position: top bucket → +1, bottom → -1（僅示意，不接 production）
        pos = pd.Series(0.0, index=dense_series.index)
        top = labels.max(skipna=True)
        pos = pos.mask(labels == top, 1.0)
        pos = pos.mask(labels == 0, -1.0)
        pos = pos.where(valid, 0.0)
        clipped = dense_series.clip(lo, hi)
        assert clipped.notna().any()
        assert float(pos.abs().sum()) > 0
        # 確認 pit_stats 模組本身無 FR 依賴
        import momentum.Analysis.pit_stats as ps

        src = open(ps.__file__, encoding="utf-8").read()
        assert "factor_return_analyzer" not in src


# ---------------------------------------------------------------------------
# boundary bag
# ---------------------------------------------------------------------------
class TestBoundaries:
    def test_empty_series_all_primitives(self) -> None:
        s = pd.Series([], dtype=float)
        assert len(pit_expanding_rank(s)) == 0
        m, st = pit_expanding_mean_std(s)
        assert len(m) == 0 and len(st) == 0
        med, mad = pit_expanding_mad(s)
        assert len(med) == 0
        lo, hi = pit_expanding_bounds(s, 0.1, 0.9)
        assert len(lo) == 0

    def test_canonical_min_samples_dense_first_valid_99(self) -> None:
        s = pd.Series(RNG.normal(size=150))
        assert first_valid_index(s, min_samples=100) == 99
        mean, _ = pit_expanding_mean_std(s, min_samples=100)
        assert mean.iloc[:99].isna().all()
        assert pd.notna(mean.iloc[99])
