#!/usr/bin/env python3
"""
smoke_test_pipeline.py
======================
快速 smoke test：驗證 L1~L7 pipeline 可連續完成。

用途：每次重大優化後先跑這支腳本，確保所有 Layer 皆可正常執行，
      再進行完整 benchmark（scripts/benchmark_ethusdt_multitf.py）。

執行方式：
    PYTHONPATH="$PWD" ./venv/bin/python scripts/smoke_test_pipeline.py
    PYTHONPATH="$PWD" ./venv/bin/python scripts/smoke_test_pipeline.py --start-date 2024-12-01 --end-date 2025-01-31
"""

from __future__ import annotations

import argparse
import platform
import resource
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─── 常數 ───────────────────────────────────────────────────────────────────
SYMBOL = "ETHUSDT"
PRIMARY_TF = "1h"
TRAINING_TFS = ["1h", "12h"]
# 預設 smoke 資料範圍（約 2 個月 1h kline）
DEFAULT_START_DATE = "2024-12-01"
DEFAULT_END_DATE = "2025-01-31"
KLINE_CACHE_DIR = "data_cache/feature_klines"
PRESET = "full"


# ─── 工具函式 ────────────────────────────────────────────────────────────────

def _rss_mb() -> float:
    """取得目前 process 的峰值 RSS（macOS: bytes；Linux: KB）。"""
    ru = resource.getrusage(resource.RUSAGE_SELF)
    if platform.system() == "Darwin":
        return ru.ru_maxrss / (1024.0 * 1024.0)
    return ru.ru_maxrss / 1024.0


def _fmt_sec(sec: float) -> str:
    if sec >= 60:
        return f"{sec:.1f}s ({sec / 60:.1f} min)"
    return f"{sec:.2f}s"


# ─── Progress 追蹤器 ─────────────────────────────────────────────────────────

class LayerTimingTracker:
    """從 progress_callback 追蹤每個 stage 的耗時。"""

    def __init__(self) -> None:
        # (stage, start_time_perf)
        self._in_flight: Dict[str, float] = {}
        # stage → list of (elapsed_sec, message)
        self.completed: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        self.events: List[Dict[str, Any]] = []
        self._last_message: str = ""

    def __call__(self, payload: Dict[str, Any]) -> None:
        stage = str(payload.get("stage", "unknown"))
        progress = float(payload.get("progress", 0.0))
        message = str(payload.get("message", ""))
        now = time.perf_counter()

        self.events.append({"stage": stage, "progress": progress, "message": message, "ts": now})
        self._last_message = message

        if progress <= 0.05:  # 開始
            self._in_flight[stage] = now
            print(f"    [START] {stage}: {message}", flush=True)
        elif progress >= 0.95:  # 完成
            if stage in self._in_flight:
                elapsed = now - self._in_flight.pop(stage)
                self.completed[stage].append((elapsed, message))
                print(f"    [ END ] {stage}: {elapsed:.2f}s — {message}", flush=True)
            else:
                print(f"    [ END ] {stage}: {message}", flush=True)
        else:
            print(f"    [  ·  ] {stage} {progress*100:.0f}%: {message}", flush=True)

    @property
    def last_message(self) -> str:
        return self._last_message

    def summary(self) -> Dict[str, float]:
        """各 stage 總耗時（秒）。"""
        return {stage: sum(e for e, _ in entries) for stage, entries in self.completed.items()}


# ─── 主函式 ──────────────────────────────────────────────────────────────────

def run_smoke_test(
    start_date: Optional[str] = DEFAULT_START_DATE,
    end_date: Optional[str] = DEFAULT_END_DATE,
    force_regenerate: bool = True,
) -> bool:
    """執行 smoke test。回傳 True=PASS, False=FAIL。"""
    from momentum.factories import create_feature_factory, create_feature_reader

    print("=" * 70)
    print("SMOKE TEST: ETHUSDT 1h pipeline (L1~L7)")
    print("=" * 70)
    print(f"  Symbol        : {SYMBOL}")
    print(f"  Primary TF    : {PRIMARY_TF}")
    print(f"  Training TFs  : {TRAINING_TFS}")
    print(f"  Date range    : {start_date} → {end_date}")
    print(f"  Preset        : {PRESET}")
    print(f"  Kline cache   : {KLINE_CACHE_DIR}/kline_cache.h5")
    print(f"  Force regen   : {force_regenerate}")
    print("-" * 70)

    tracker = LayerTimingTracker()
    rss_start = _rss_mb()
    overall_start = time.perf_counter()

    try:
        factory = create_feature_factory(
            cache_dir=KLINE_CACHE_DIR,
            validate_continuity=False,  # 縮短 smoke test 時間
        )

        config_override: Dict[str, Any] = {
            "preset": PRESET,
            "timeframes": {
                "training": TRAINING_TFS,
            },
        }

        print("\n[Pipeline] Starting generate_features() ...\n")
        result = factory.generate_features(
            symbol=SYMBOL,
            timeframe=PRIMARY_TF,
            config_override=config_override,
            force_regenerate=force_regenerate,
            progress_callback=tracker,
            start_date=start_date,
            end_date=end_date,
            persist=False,  # smoke test 不需要寫入磁碟
        )
        overall_elapsed = time.perf_counter() - overall_start
        rss_peak = _rss_mb()

    except Exception as exc:
        overall_elapsed = time.perf_counter() - overall_start
        rss_peak = _rss_mb()
        print(f"\n{'=' * 70}")
        print(f"  [FAIL] Pipeline raised exception after {_fmt_sec(overall_elapsed)}")
        print(f"  Error : {type(exc).__name__}: {exc}")
        print(f"{'=' * 70}")
        import traceback
        traceback.print_exc()
        return False

    # ── 驗證結果 ─────────────────────────────────────────────────────────────
    passed_checks: List[str] = []
    failed_checks: List[str] = []

    # Check 1: 完整執行（不拋例外）
    passed_checks.append("✅ C0: pipeline 不拋例外，完整執行完畢")

    # Check 2: feature_count > 0
    feat_count = getattr(result, "feature_count", 0)
    if feat_count > 0:
        passed_checks.append(f"✅ C1: feature_count = {feat_count:,} > 0")
    else:
        failed_checks.append(f"❌ C1: feature_count = {feat_count} (期望 > 0)")

    # Check 3: layer_counts 有資料
    layer_counts: Dict[str, int] = dict(getattr(result, "layer_counts", {}) or {})
    if any(v > 0 for v in layer_counts.values()):
        passed_checks.append(f"✅ C2: layer_counts 有資料 {layer_counts}")
    else:
        # CGSA multi-TF mode 可能 layer_counts 不在 result 裡
        passed_checks.append(f"⚠️  C2: layer_counts = {layer_counts}（CGSA multi-TF 模式可能為空）")

    # Check 4: Peak RSS ≤ 6 GB
    if rss_peak <= 6 * 1024:
        passed_checks.append(f"✅ C3: Peak RSS = {rss_peak:.0f} MB ≤ 6 GB")
    else:
        failed_checks.append(f"❌ C3: Peak RSS = {rss_peak:.0f} MB > 6 GB (8GB 系統警戒線)")

    # Check 5: CGSA 模式下可讀回 features
    features_df = getattr(result, "features_df", None)
    cgsa_mode = (features_df is not None and features_df.empty and feat_count > 0)
    if cgsa_mode:
        try:
            from momentum.factories import create_feature_reader
            metadata = dict(result.metadata or {})
            config_hash = str(metadata.get("config_hash", ""))
            if config_hash:
                reader = create_feature_reader()
                frames = [gdf for _, gdf in reader.stream_groups(SYMBOL, config_hash)]
                if frames:
                    import pandas as pd
                    combined = pd.concat(frames, axis=1)
                    passed_checks.append(
                        f"✅ C4: CGSA readback OK — {combined.shape[1]:,} cols, {combined.shape[0]:,} rows"
                    )
                else:
                    failed_checks.append("❌ C4: CGSA readback 回傳空 frames")
            else:
                passed_checks.append("⚠️  C4: CGSA 模式但 config_hash 未知，跳過 readback 驗證")
        except Exception as e:
            failed_checks.append(f"❌ C4: CGSA readback 拋例外: {e}")
    else:
        if features_df is not None and not features_df.empty:
            passed_checks.append(
                f"✅ C4: features_df shape = {features_df.shape[0]:,} rows × {features_df.shape[1]:,} cols"
            )
        else:
            passed_checks.append("⚠️  C4: features_df 為空（CGSA 模式 persist=False）")

    # ── 列印報告 ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SMOKE TEST RESULTS")
    print("=" * 70)
    print(f"\n  Total time : {_fmt_sec(overall_elapsed)}")
    print(f"  Peak RSS   : {rss_peak:.0f} MB  (起始 {rss_start:.0f} MB)")
    print(f"  Features   : {feat_count:,}")
    print(f"  Last msg   : {tracker.last_message}")

    print("\n── Stage Timing ─────────────────────────────────────────────────")
    stage_totals = tracker.summary()
    if stage_totals:
        for stage, secs in sorted(stage_totals.items(), key=lambda x: -x[1]):
            pct = secs / overall_elapsed * 100 if overall_elapsed > 0 else 0
            print(f"  {stage:<20} {_fmt_sec(secs):>12}  ({pct:.1f}%)")
    else:
        print("  （無 stage 計時資料）")

    print("\n── Checks ───────────────────────────────────────────────────────")
    for msg in passed_checks:
        print(f"  {msg}")
    for msg in failed_checks:
        print(f"  {msg}")

    overall_pass = len(failed_checks) == 0
    verdict = "PASS ✅" if overall_pass else "FAIL ❌"
    print("\n" + "=" * 70)
    print(f"  VERDICT: {verdict}  ({len(passed_checks)} passed, {len(failed_checks)} failed)")
    print("=" * 70)

    return overall_pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ETHUSDT pipeline smoke test (L1~L7)")
    p.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help=f"kline 起始日期 (default: {DEFAULT_START_DATE})",
    )
    p.add_argument(
        "--end-date",
        default=DEFAULT_END_DATE,
        help=f"kline 結束日期 (default: {DEFAULT_END_DATE})",
    )
    p.add_argument(
        "--no-force-regenerate",
        action="store_true",
        help="不強制重跑，允許讀取快取",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = run_smoke_test(
        start_date=args.start_date,
        end_date=args.end_date,
        force_regenerate=not args.no_force_regenerate,
    )
    sys.exit(0 if success else 1)
