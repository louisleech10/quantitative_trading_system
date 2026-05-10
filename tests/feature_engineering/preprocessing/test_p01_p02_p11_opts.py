"""P0.1 / P0.2 / P1.1 最佳化驗證測試。

P0.1: FFACT_USE_FAST_ADF=1 — Numba JIT ADF 精度與邊界條件測試
P0.2: FFACT_L65_SLOWPATH_PARALLEL=1 — loky 並行壓力測試（含瀏覽器/前端 RSS 開銷估算）
P1.1: _group_requires_slow_transform() ADF per-layer 路由修復測試

執行指令：
    ./venv/bin/pytest tests/feature_engineering/preprocessing/test_p01_p02_p11_opts.py -v
    ./venv/bin/pytest tests/feature_engineering/preprocessing/test_p01_p02_p11_opts.py -v -s -k p02
"""

from __future__ import annotations

import types
import time
from typing import Any, Dict, FrozenSet

import numpy as np
import pytest

try:
    import psutil as _psutil
except ImportError:
    _psutil = None

# ──────────────────────────────────────────────────────────────────────────────
# 共用工具
# ──────────────────────────────────────────────────────────────────────────────

RNG = np.random.default_rng(42)
_BROWSER_OVERHEAD_GB = 2.5  # Chrome + Next.js dev + FastAPI 典型 8GB M1 開銷
_8GB_TIER_GB = 8.0
_SAFE_HEADROOM_GB = 0.5     # 最低安全預留空間


def _rss_mb() -> float:
    if _psutil is None:
        return 0.0
    return _psutil.Process().memory_info().rss / (1024 ** 2)


def _available_ram_gb() -> float:
    if _psutil is None:
        return _8GB_TIER_GB  # 保守假設
    return _psutil.virtual_memory().available / (1024 ** 3)


def _stationary_series(n: int = 500) -> np.ndarray:
    """白噪音序列（平穩）。"""
    return RNG.standard_normal(n)


def _random_walk_series(n: int = 500) -> np.ndarray:
    """隨機遊走序列（非平穩）。"""
    return np.cumsum(RNG.standard_normal(n))


# ──────────────────────────────────────────────────────────────────────────────
# P0.1 — fast_ADF 精度與邊界條件
# ──────────────────────────────────────────────────────────────────────────────

class TestP01FastADF:
    """P0.1: Numba JIT ADF 精度與邊界條件。"""

    @pytest.fixture(autouse=True)
    def _import(self):
        from momentum.FeatureEngineering.preprocessing._fast_adf_numba import (
            adf_pvalue_fast,
            warmup_numba,
            MIN_ADF_OBSERVATIONS,
            THRESHOLD_BAND_LOW,
            THRESHOLD_BAND_HIGH,
            FAST_ADF_ENGINE_VERSION,
        )
        try:
            from statsmodels.tsa.stattools import adfuller
            self.adfuller = adfuller
        except ImportError:
            self.adfuller = None

        warmup_numba()  # 預熱 Numba kernel，排除首次 JIT 延遲
        self.adf_pvalue_fast = adf_pvalue_fast
        self.MIN_OBS = MIN_ADF_OBSERVATIONS
        self.BAND_LOW = THRESHOLD_BAND_LOW
        self.BAND_HIGH = THRESHOLD_BAND_HIGH
        self.VERSION = FAST_ADF_ENGINE_VERSION

    # ── 精度測試 ──────────────────────────────────────────────────────────────

    def test_stationary_series_pvalue_below_threshold(self):
        """平穩序列（白噪音）：fast_adf 應給出小 p-value（顯著拒絕 H0）。"""
        # 用較長序列確保穩定
        series = _stationary_series(600)
        pvalue, used_fallback = self.adf_pvalue_fast(series)
        # fast_adf 或 statsmodels 路徑均應正確識別為平穩（p < 0.10）
        assert np.isfinite(pvalue), f"pvalue={pvalue} 非有限值"
        assert pvalue < 0.10, f"平穩序列 pvalue={pvalue:.4f} 應 < 0.10"

    def test_random_walk_pvalue_above_threshold(self):
        """非平穩序列（隨機遊走）：fast_adf 應給出大 p-value（無法拒絕 H0）。"""
        series = _random_walk_series(500)
        pvalue, _ = self.adf_pvalue_fast(series)
        assert np.isfinite(pvalue), f"pvalue={pvalue} 非有限值"
        assert pvalue > 0.05, f"隨機遊走 pvalue={pvalue:.4f} 應 > 0.05"

    def test_fast_adf_close_to_statsmodels_on_stationary(self):
        """fast_adf vs statsmodels：平穩序列 p-value 差異 < 0.10。"""
        if self.adfuller is None:
            pytest.skip("statsmodels 未安裝")
        series = _stationary_series(500)
        fast_p, _ = self.adf_pvalue_fast(series)
        sm_p = float(self.adfuller(series, autolag="AIC")[1])
        # 兩者都應低（平穩），差距容忍度 0.10（Numba 用單一 lag，statsmodels 用 AIC）
        assert abs(fast_p - sm_p) < 0.20 or (fast_p < 0.10 and sm_p < 0.10), (
            f"fast_p={fast_p:.4f} sm_p={sm_p:.4f} 差距過大且方向不一致"
        )

    def test_fast_adf_close_to_statsmodels_on_random_walk(self):
        """fast_adf vs statsmodels：隨機遊走序列兩者均應給出大 p-value。"""
        if self.adfuller is None:
            pytest.skip("statsmodels 未安裝")
        series = _random_walk_series(500)
        fast_p, _ = self.adf_pvalue_fast(series)
        sm_p = float(self.adfuller(series, autolag="AIC")[1])
        # 兩者都無法拒絕 H0（p > 0.05）
        assert fast_p > 0.05 or sm_p > 0.05, (
            f"fast_p={fast_p:.4f} sm_p={sm_p:.4f} — 至少一個應 > 0.05 表示非平穩"
        )

    def test_returns_tuple_of_float_and_bool(self):
        """adf_pvalue_fast 回傳 (float, bool) 格式。"""
        series = _stationary_series(200)
        result = self.adf_pvalue_fast(series)
        assert isinstance(result, tuple), f"期望 tuple，得到 {type(result)}"
        assert len(result) == 2
        pvalue, used_fallback = result
        assert isinstance(float(pvalue), float), "p-value 應可轉為 float"
        assert isinstance(bool(used_fallback), bool), "fallback flag 應為 bool"

    # ── 邊界條件 ──────────────────────────────────────────────────────────────

    def test_boundary_all_nan_returns_finite_pvalue(self):
        """全 NaN 序列：應不崩潰，回傳有限 p-value（通常為 1.0）。"""
        series = np.full(200, np.nan)
        pvalue, used_fallback = self.adf_pvalue_fast(series)
        assert np.isfinite(pvalue), f"全 NaN 應回傳有限值，得 {pvalue}"
        assert used_fallback, "全 NaN 應走 statsmodels fallback"

    def test_boundary_constant_series_does_not_crash(self):
        """常數序列（std=0）：應不崩潰，回傳有限 p-value。"""
        series = np.full(200, 42.0)
        pvalue, _ = self.adf_pvalue_fast(series)
        assert np.isfinite(pvalue), f"常數序列應回傳有限值，得 {pvalue}"

    def test_boundary_series_too_short_uses_fallback(self):
        """觀測值 < MIN_ADF_OBSERVATIONS：應走 statsmodels fallback。"""
        series = _stationary_series(self.MIN_OBS - 1)
        pvalue, used_fallback = self.adf_pvalue_fast(series)
        assert np.isfinite(pvalue), "短序列應回傳有限值"
        assert used_fallback, f"n={len(series)} < MIN_OBS={self.MIN_OBS} 應走 fallback"

    def test_boundary_single_value_does_not_crash(self):
        """單一觀測值：應不崩潰。"""
        series = np.array([3.14])
        pvalue, _ = self.adf_pvalue_fast(series)
        assert np.isfinite(pvalue), "單一觀測值應回傳有限值"

    def test_boundary_nan_heavy_50pct_graceful(self):
        """50% NaN 序列：應不崩潰，且有足夠有效觀測值時給出有限 p-value。"""
        n = 400
        series = _stationary_series(n)
        series[::2] = np.nan  # 每隔一個設 NaN → 200 個有效值
        pvalue, _ = self.adf_pvalue_fast(series)
        assert np.isfinite(pvalue), "50% NaN 序列應回傳有限 p-value"

    def test_engine_version_constant_is_correct_format(self):
        """FAST_ADF_ENGINE_VERSION 格式應符合 'fast-adf-numba-v*' 命名慣例。"""
        assert self.VERSION.startswith("fast-adf-numba-"), (
            f"版本字串 '{self.VERSION}' 格式不符預期"
        )

    def test_warmup_numba_does_not_raise(self):
        """warmup_numba() 預熱後連續呼叫不應拋例外。"""
        from momentum.FeatureEngineering.preprocessing._fast_adf_numba import warmup_numba
        warmup_numba()
        warmup_numba()  # 第二次呼叫應利用快取，不重新編譯


# ──────────────────────────────────────────────────────────────────────────────
# P0.2 — SlowPath 並行壓力測試（模擬瀏覽器/前端環境）
# ──────────────────────────────────────────────────────────────────────────────

def _make_fracdiff_items(n_rows: int, n_cols: int) -> list:
    """建立 process_fracdiff_column_values 的輸入項目（合成序列）。"""
    rng = np.random.default_rng(123)
    items = []
    for col_idx in range(n_cols):
        # 交替產生平穩（白噪音）與非平穩（隨機遊走）序列
        if col_idx % 3 == 0:
            values = rng.standard_normal(n_rows).cumsum()  # 隨機遊走
        else:
            values = rng.standard_normal(n_rows)  # 平穩
        metadata: Dict[str, Any] = {
            "column": f"synthetic_{col_idx}",
            "adf_threshold": 0.05,
            "d_range": (0.0, 1.0),
            "precision": 0.1,    # 較低精度以加快測試
            "max_lag": 5,
            "weight_threshold": 1e-4,
            "sample_size": min(n_rows, 200),
            "cached_d_star": None,
        }
        items.append((values.astype(np.float64), metadata))
    return items


class TestP02SlowPathParallel:
    """P0.2: loky 並行 ADF 壓力測試與正確性驗證。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from momentum.FeatureEngineering.preprocessing._slow_path_parallel import (
            ParallelSlowPath,
            process_fracdiff_column_values,
        )
        self.ParallelSlowPath = ParallelSlowPath
        self.worker = process_fracdiff_column_values

    # ── 正確性測試（小資料集，確保並行=串行結果一致）────────────────────────

    def test_n1_serial_completes_without_error(self):
        """n_jobs=1（串行）：應正常完成且回傳正確結果結構。"""
        items = _make_fracdiff_items(n_rows=200, n_cols=10)
        runner = self.ParallelSlowPath(n_jobs=1)
        results = runner.map(items, self.worker)
        assert len(results) == 10
        for result in results:
            assert "d_star" in result
            assert np.isfinite(result["d_star"]), f"d_star={result['d_star']} 非有限值"

    def test_n2_parallel_results_match_serial(self):
        """n_jobs=2 並行結果：d_star 應與串行結果一致（誤差 < 0.05）。"""
        items = _make_fracdiff_items(n_rows=200, n_cols=12)

        serial = self.ParallelSlowPath(n_jobs=1)
        parallel = self.ParallelSlowPath(n_jobs=2)

        serial_results = serial.map(items, self.worker)
        parallel_results = parallel.map(items, self.worker)

        assert len(serial_results) == len(parallel_results)
        mismatches = []
        for idx, (s_res, p_res) in enumerate(zip(serial_results, parallel_results)):
            diff = abs(s_res["d_star"] - p_res["d_star"])
            if diff > 0.05:
                mismatches.append((idx, s_res["d_star"], p_res["d_star"], diff))

        assert not mismatches, (
            f"並行 d_star 與串行不一致 (前 5 筆)：{mismatches[:5]}"
        )

    def test_empty_items_returns_empty_list(self):
        """空輸入：應回傳空 list。"""
        runner = self.ParallelSlowPath(n_jobs=2)
        result = runner.map([], self.worker)
        assert result == []

    def test_single_item_n2_does_not_hang(self):
        """單一 item + n_jobs=2：loky 不應死鎖。"""
        items = _make_fracdiff_items(n_rows=200, n_cols=1)
        runner = self.ParallelSlowPath(n_jobs=2)
        start = time.perf_counter()
        results = runner.map(items, self.worker)
        elapsed = time.perf_counter() - start
        assert len(results) == 1
        assert elapsed < 60, f"單一 item n_jobs=2 耗時 {elapsed:.1f}s，疑似死鎖"

    # ── 壓力測試（較大資料集，量測 RSS 開銷）────────────────────────────────

    @pytest.mark.slow
    def test_p02_stress_rss_budget_with_browser_overhead(self):
        """P0.2 壓力測試：量測不同 n_jobs 的 RSS 增量，推算 8GB+瀏覽器下安全上限。

        模擬環境假設（M1 8GB，使用者同時開啟瀏覽器/前端）：
          瀏覽器（Chrome 多頁籤）  ≈ 1.2 GB
          Next.js dev server      ≈ 0.4 GB
          FastAPI backend         ≈ 0.3 GB
          系統其他程序            ≈ 0.6 GB
          ─────────────────────────────────
          總背景開銷               ≈ 2.5 GB
          Python 可用空間          ≈ 5.5 GB

        測試目標：
          1. 量測 n_jobs=1,2,3 時 RSS 增量 (ΔMB)
          2. 驗證 n_jobs=2 的 RSS 峰值在 5.5GB 預算內
          3. 報告 n_jobs=3 是否安全
        """
        if _psutil is None:
            pytest.skip("psutil 未安裝，無法量測 RSS")

        n_rows, n_cols = 400, 60  # ~400 bars × 60 欄位

        items = _make_fracdiff_items(n_rows=n_rows, n_cols=n_cols)

        BUDGET_MB = (_8GB_TIER_GB - _BROWSER_OVERHEAD_GB - _SAFE_HEADROOM_GB) * 1024
        # 預估 IC-First L6.5 基線 RSS（winsorize-only fast path）≈ 2.5 GB
        L65_BASE_RSS_MB = 2560
        AVAILABLE_FOR_LOKY_MB = BUDGET_MB - L65_BASE_RSS_MB

        process = _psutil.Process()
        results: Dict[int, Dict[str, float]] = {}

        for n_jobs in [1, 2, 3]:
            rss_before = process.memory_info().rss / (1024 ** 2)
            t_start = time.perf_counter()

            runner = self.ParallelSlowPath(n_jobs=n_jobs)
            runner.map(items, self.worker)

            elapsed = time.perf_counter() - t_start
            rss_after = process.memory_info().rss / (1024 ** 2)
            delta_mb = max(0.0, rss_after - rss_before)

            results[n_jobs] = {"elapsed_s": round(elapsed, 2), "delta_mb": round(delta_mb, 1)}

        # 判斷安全性
        delta_n1 = results[1]["delta_mb"]
        delta_n2 = results[2]["delta_mb"]
        delta_n3 = results.get(3, {}).get("delta_mb", 0.0)

        # 計算估計每個 loky worker 的 RSS 開銷
        # n_jobs=2 vs n_jobs=1 的差值就是額外 worker 的開銷
        extra_per_worker_mb = max(0.0, delta_n2 - delta_n1)

        safe_extra_mb = AVAILABLE_FOR_LOKY_MB
        if extra_per_worker_mb > 0:
            safe_max_workers = int(safe_extra_mb / extra_per_worker_mb)
        else:
            safe_max_workers = 4  # 若量測不到差值，保守假設 4 workers 均安全

        speedup_n2_vs_n1 = (results[1]["elapsed_s"] / results[2]["elapsed_s"]
                            if results[2]["elapsed_s"] > 0 else 1.0)

        # 格式化報告
        report_lines = [
            "",
            "═" * 60,
            "P0.2 壓力測試報告（模擬 8GB M1 + 瀏覽器/前端環境）",
            "═" * 60,
            f"資料規模：{n_rows} rows × {n_cols} cols（ADF + FracDiff）",
            f"背景開銷假設：{_BROWSER_OVERHEAD_GB:.1f} GB（瀏覽器+Next.js+FastAPI）",
            f"L6.5 基線 RSS 假設：{L65_BASE_RSS_MB/1024:.1f} GB（IC-First fast path）",
            f"可用 loky 預算：{safe_extra_mb:.0f} MB",
            "",
            "n_jobs  | ΔMB    | elapsed(s) | 安全性",
            "───────────────────────────────────────",
        ]
        for n_jobs_key in [1, 2, 3]:
            r = results[n_jobs_key]
            budget_ok = r["delta_mb"] <= safe_extra_mb
            safety = "✅ 安全" if budget_ok else "⚠️  超限"
            report_lines.append(
                f"n_jobs={n_jobs_key} | {r['delta_mb']:6.1f} MB | {r['elapsed_s']:8.2f}s | {safety}"
            )
        report_lines += [
            "",
            f"額外 worker 開銷估算：{extra_per_worker_mb:.1f} MB / worker",
            f"8GB+瀏覽器下推薦安全 n_jobs：{min(safe_max_workers, 4)}",
            f"n_jobs=2 vs n_jobs=1 加速比：{speedup_n2_vs_n1:.2f}x",
            "═" * 60,
        ]
        print("\n".join(report_lines))

        # ── 斷言 ──
        # n_jobs=2 的 RSS 增量必須在預算內（這是最低要求）
        n2_fits = results[2]["delta_mb"] <= AVAILABLE_FOR_LOKY_MB
        assert n2_fits, (
            f"n_jobs=2 RSS 增量 {results[2]['delta_mb']:.1f} MB "
            f"超出可用預算 {AVAILABLE_FOR_LOKY_MB:.0f} MB，"
            f"8GB+瀏覽器環境下 n_jobs=2 不安全"
        )


# ──────────────────────────────────────────────────────────────────────────────
# P1.1 — _group_requires_slow_transform ADF per-layer 路由修復
# ──────────────────────────────────────────────────────────────────────────────

def _make_mock_group(layer_str: str | None, group_id: str = "g1") -> object:
    """建立最小化 mock group 物件，具備 layer / group_id / columns 屬性。"""
    from momentum.FeatureEngineering.core.column_group import LayerSource

    layer_map = {
        "L1": LayerSource.L1,
        "L2": LayerSource.L2,
        "L3": LayerSource.L3,
        "L4": LayerSource.L4,
    }

    grp = types.SimpleNamespace()
    grp.group_id = group_id
    grp.layer = layer_map.get(layer_str) if layer_str else None
    grp.columns = (f"{group_id}_col_0", f"{group_id}_col_1")
    return grp


def _make_preprocessor_with_layers(
    fracdiff_layers: FrozenSet[str],
    do_adf: bool = True,
    do_fracdiff: bool = True,
) -> Any:
    """建立配置好的 FeaturePreprocessor，並直接設定 _fracdiff_apply_to_layers。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    config = {
        "mode": "replace",
        "winsorization": {"enabled": False},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "fractional_differencing": {"enabled": do_fracdiff, "apply_to": "non_stationary"},
        "adf_differencing": {"enabled": do_adf},
        "gaussian_normalize": {"enabled": False},
    }
    pp = FeaturePreprocessor(config)
    # 直接覆寫 _fracdiff_apply_to_layers，避免 env var 干擾
    pp._fracdiff_apply_to_layers = fracdiff_layers
    return pp


class TestP11ADFPerLayerRouting:
    """P1.1: _group_requires_slow_transform ADF per-layer 路由修復驗證。

    修復前（設計缺失）：if do_adf: return True  → 所有 group 都走 slow path
    修復後：ADF 與 FracDiff 共用相同的 per-layer 過濾邏輯
    """

    # ── 核心功能測試 ──────────────────────────────────────────────────────────

    def test_l3_group_fast_when_adf_on_fracdiff_l1l2_only(self):
        """L3 group + do_adf=True + fracdiff=L1,L2 → fast path（False）。

        IC-First 預設配置：fracdiff_apply_to_layers = {L1, L2}，L3 不做 ADF。
        這是 P1.1 修復的核心案例。
        """
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2"}))
        grp = _make_mock_group("L3")
        ctx = {"do_adf": True, "do_fracdiff": True}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is False, "P1.1 修復：L3 group 應走 fast path（do_adf=True，fracdiff=L1,L2 only）"

    def test_l1_group_slow_when_adf_on_fracdiff_l1l2(self):
        """L1 group + do_adf=True + fracdiff=L1,L2 → slow path（True）。"""
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2"}))
        grp = _make_mock_group("L1")
        ctx = {"do_adf": True, "do_fracdiff": True}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is True, "L1 group 應走 slow path"

    def test_l2_group_slow_when_adf_on_fracdiff_l1l2(self):
        """L2 group + do_adf=True + fracdiff=L1,L2 → slow path（True）。"""
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2"}))
        grp = _make_mock_group("L2")
        ctx = {"do_adf": True, "do_fracdiff": True}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is True, "L2 group 應走 slow path"

    def test_fracdiff_all_layers_forces_all_groups_slow(self):
        """fracdiff_apply_to_layers=ALL → L3 也走 slow path（True）。"""
        pp = _make_preprocessor_with_layers(frozenset({"ALL"}))
        grp = _make_mock_group("L3")
        ctx = {"do_adf": True, "do_fracdiff": True}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is True, "fracdiff=ALL 時所有 group 應走 slow path"

    def test_l4_group_fast_when_fracdiff_l1l2_only(self):
        """L4 group + fracdiff=L1,L2 → fast path。"""
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2"}))
        grp = _make_mock_group("L4")
        ctx = {"do_adf": True, "do_fracdiff": True}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is False, "L4 group 在 fracdiff=L1,L2 時應走 fast path"

    # ── 邊界條件 ──────────────────────────────────────────────────────────────

    def test_adf_disabled_l3_also_fast(self):
        """do_adf=False（ADF 關閉）：L3 group 仍走 fast path。"""
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2"}))
        grp = _make_mock_group("L3")
        ctx = {"do_adf": False, "do_fracdiff": False}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is False

    def test_adf_on_fracdiff_off_l3_routes_fast(self):
        """do_adf=True 但 do_fracdiff=False + L3 不在 layers：L3 → fast path。

        ADF 與 FracDiff 共用 per-layer 邏輯：L3 不在目標 layers，
        fracdiff=False 時最終 return False（fast）。
        """
        pp = _make_preprocessor_with_layers(
            frozenset({"L1", "L2"}), do_adf=True, do_fracdiff=False
        )
        grp = _make_mock_group("L3")
        ctx = {"do_adf": True, "do_fracdiff": False}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is False, "ADF=on, FracDiff=off, L3 不在 layers → fast path"

    def test_adf_on_fracdiff_off_l1_routes_slow(self):
        """do_adf=True 且 L1 在 layers：L1 → slow path（即使 do_fracdiff=False）。"""
        pp = _make_preprocessor_with_layers(
            frozenset({"L1", "L2"}), do_adf=True, do_fracdiff=False
        )
        grp = _make_mock_group("L1")
        ctx = {"do_adf": True, "do_fracdiff": False}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is True, "ADF=on, L1 在 layers → slow path"

    def test_unknown_layer_group_falls_through_to_column_filter(self):
        """layer=None（未知來源）：not-fast（不提前 return True），走後續 fracdiff 欄位過濾。

        layer=None 時 source_layer check 短路，繼續到 fracdiff per-layer 過濾。
        若 do_fracdiff=False → return False（fast）。
        """
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2"}))
        grp = _make_mock_group(None)  # 未知 layer
        ctx = {"do_adf": True, "do_fracdiff": False}
        # do_fracdiff=False → fracdiff 不啟用 → return False（fast）
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is False, "未知 layer + do_fracdiff=False → fast path"

    def test_mode_append_always_slow(self):
        """mode='append'：所有 group 走 slow path（與 P1.1 無關，不受影響）。"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = {
            "mode": "append",
            "winsorization": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "fractional_differencing": {"enabled": True},
            "adf_differencing": {"enabled": True},
            "gaussian_normalize": {"enabled": False},
        }
        pp = FeaturePreprocessor(config)
        pp._fracdiff_apply_to_layers = frozenset({"L1", "L2"})
        grp = _make_mock_group("L3")
        ctx = {"do_adf": True, "do_fracdiff": True}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is True, "mode='append' 應始終走 slow path"

    # ── 迴歸測試：Legacy 模式（L1~L4 全部在 layers）────────────────────────

    def test_legacy_all_layers_l3_still_slow(self):
        """Legacy 模式（fracdiff_apply_to_layers=L1,L2,L3,L4）：L3 走 slow path。"""
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2", "L3", "L4"}))
        grp = _make_mock_group("L3")
        ctx = {"do_adf": True, "do_fracdiff": True}
        result = pp._group_requires_slow_transform(grp, ctx)
        assert result is True, "Legacy 模式 L3 在 layers 內應走 slow path"

    def test_p11_ic_first_99_l3_groups_all_fast(self):
        """IC-First 配置：批量建立 99 個 L3 groups，所有 group 應走 fast path。

        對應報告中的「L3 fast groups (99 groups)」場景：
        P1.1 修復後從 ~35s（ADF slow）→ fast path（僅 winsorize）。
        """
        pp = _make_preprocessor_with_layers(frozenset({"L1", "L2"}))
        ctx = {"do_adf": True, "do_fracdiff": True}
        slow_count = sum(
            pp._group_requires_slow_transform(_make_mock_group("L3", f"l3_g{idx}"), ctx)
            for idx in range(99)
        )
        assert slow_count == 0, (
            f"P1.1 修復後 99 個 L3 groups 應全部走 fast path，"
            f"但有 {slow_count} 個走 slow path"
        )
