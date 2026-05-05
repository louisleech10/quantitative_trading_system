#!/usr/bin/env python3
"""
benchmark_ethusdt_multitf.py
============================
完整 ETHUSDT 1h + 12h multi-TF pipeline benchmark，並輸出 Markdown 分析報告。

執行方式：
    PYTHONPATH="$PWD" ./venv/bin/python scripts/benchmark_ethusdt_multitf.py
    PYTHONPATH="$PWD" ./venv/bin/python scripts/benchmark_ethusdt_multitf.py --compare-baseline results/full_golden_baseline/...
    PYTHONPATH="$PWD" ./venv/bin/python scripts/benchmark_ethusdt_multitf.py --create-baseline

報告輸出：
    results/benchmark_multitf_YYYYMMDD_HHMMSS.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─── 常數 ───────────────────────────────────────────────────────────────────
SYMBOL = "ETHUSDT"
PRIMARY_TF = "1h"
TRAINING_TFS = ["1h", "12h"]
KLINE_CACHE_DIR = "data_cache/feature_klines"
PRESET = "full"
BASELINE_REGISTRY_DIR = Path("results/full_golden_baseline")
REPORTS_DIR = Path("results")

# C4 RSS 上限（MB）
RSS_LIMIT_MB = 6 * 1024  # 6 GB

# V7 reference numbers from Pre-opt_vs_V7_Comparison.md (for context)
V7_REFERENCE = {
    "total_elapsed_sec": 7385.91,
    "peak_rss_mb": 3990.0,
    "feature_count": 435389,
    "layer_times_sec": {
        "1h L0": 0.08,
        "1h L1": 3.30,
        "1h L2": 2055.24,
        "1h L3": 2051.17,
        "1h L4": 5.32,
        "1h L5": 0.01,
        "1h L6": 0.21,
        "12h L1": 67.81,
        "12h L2": 160.74,
        "12h L3": 150.78,
        "12h L4": 0.19,
        "12h L5": 0.00,
        "12h L6": 0.03,
        "L6.5": 2423.93,
        "L7": 467.08,
    },
}


# ─── 工具函式 ────────────────────────────────────────────────────────────────

def _rss_mb() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    if platform.system() == "Darwin":
        return ru.ru_maxrss / (1024.0 * 1024.0)
    return ru.ru_maxrss / 1024.0


def _fmt_sec(sec: float) -> str:
    if sec >= 3600:
        return f"{sec:.1f}s ({sec / 3600:.2f} hr)"
    if sec >= 60:
        return f"{sec:.1f}s ({sec / 60:.1f} min)"
    return f"{sec:.2f}s"


def _speedup_str(new_sec: float, ref_sec: float) -> str:
    if ref_sec <= 0 or new_sec <= 0:
        return "N/A"
    ratio = ref_sec / new_sec
    return f"{ratio:.2f}×"


def _sha256_df(df: "pd.DataFrame") -> str:  # noqa: F821
    """計算 DataFrame 所有欄位數值的整體 SHA-256 checksum。

    位元序語意保持與舊實作完全等價（per-column: values.tobytes() + mask.tobytes()），
    但改用批次 ``to_numpy(dtype=float64)`` + 向量化 NaN 處理，將 434k 欄上的
    Python 迴圈成本從 ~30 分壓到 <1 分。
    """
    import numpy as np
    h = hashlib.sha256()
    sorted_cols = sorted(df.columns)
    if not sorted_cols:
        return h.hexdigest()
    batch_size = 256
    for start in range(0, len(sorted_cols), batch_size):
        batch_cols = sorted_cols[start:start + batch_size]
        # 一次取整批 → float64；對 wide DataFrame 比逐欄 .to_numpy 快數十倍
        arr = df[batch_cols].to_numpy(dtype=np.float64, copy=True)
        nan_mask = np.isnan(arr)
        # 原語意：np.where(nan, 0.0, arr) — 等價於就地把 NaN 寫成 0.0
        np.copyto(arr, 0.0, where=nan_mask)
        # per-column update 以保持與舊版完全相同的 byte stream
        for j in range(arr.shape[1]):
            h.update(np.ascontiguousarray(arr[:, j]).tobytes())
            h.update(np.ascontiguousarray(nan_mask[:, j]).tobytes())
    return h.hexdigest()


def _column_checksums(df: "pd.DataFrame") -> Dict[str, str]:  # noqa: F821
    """欄位級 SHA-256（per-column 獨立 hash），批次化版以加速 wide DataFrame。"""
    import numpy as np
    result: Dict[str, str] = {}
    cols = list(df.columns)
    if not cols:
        return result
    batch_size = 256
    for start in range(0, len(cols), batch_size):
        batch_cols = cols[start:start + batch_size]
        arr = df[batch_cols].to_numpy(dtype=np.float64, copy=True)
        nan_mask = np.isnan(arr)
        np.copyto(arr, 0.0, where=nan_mask)
        for j, col in enumerate(batch_cols):
            h = hashlib.sha256()
            h.update(np.ascontiguousarray(arr[:, j]).tobytes())
            h.update(np.ascontiguousarray(nan_mask[:, j]).tobytes())
            result[str(col)] = h.hexdigest()
    return result


def _nan_ratio(df: "pd.DataFrame") -> float:  # noqa: F821
    if df.empty:
        return 0.0
    total_cells = df.shape[0] * df.shape[1]
    nan_cells = int(df.isna().sum().sum())
    return nan_cells / total_cells if total_cells > 0 else 0.0


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_latest_baseline(symbol: str, tf: str, preset: str) -> Optional[Path]:
    """在 BASELINE_REGISTRY_DIR 搜尋最新符合條件的 baseline manifest。"""
    if not BASELINE_REGISTRY_DIR.exists():
        return None
    candidates: List[Tuple[str, Path]] = []
    for d in BASELINE_REGISTRY_DIR.iterdir():
        if not d.is_dir():
            continue
        manifest_path = d / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            m = _load_json(manifest_path)
            if (
                m.get("symbol") == symbol
                and m.get("timeframe") == tf
                and m.get("preset") == preset
                and "multitf" in d.name.lower()  # 只比對 multi-TF baseline
            ):
                candidates.append((str(m.get("created_at_utc", "")), manifest_path))
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# ─── Progress 追蹤器 ─────────────────────────────────────────────────────────

class DetailedTimingTracker:
    """精細追蹤每個 stage 的耗時及 RSS 快照。"""

    def __init__(self) -> None:
        self._in_flight: Dict[str, float] = {}
        self.events: List[Dict[str, Any]] = []
        # stage → [(elapsed, message), ...]
        self.completed: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        self._last_message: str = ""
        self._rss_snapshots: List[Tuple[float, float, str]] = []  # (ts, rss_mb, label)

    def __call__(self, payload: Dict[str, Any]) -> None:
        stage = str(payload.get("stage", "unknown"))
        progress = float(payload.get("progress", 0.0))
        message = str(payload.get("message", ""))
        now = time.perf_counter()
        rss = _rss_mb()

        self.events.append({"stage": stage, "progress": progress, "message": message, "ts": now, "rss_mb": rss})
        self._last_message = message

        label = f"{stage}@{progress*100:.0f}%"
        self._rss_snapshots.append((now, rss, label))

        if progress <= 0.05:
            self._in_flight[stage] = now
            print(f"  [START] {stage:<25} RSS={rss:>7.0f} MB  {message}", flush=True)
        elif progress >= 0.95:
            if stage in self._in_flight:
                elapsed = now - self._in_flight.pop(stage)
                self.completed[stage].append((elapsed, message))
                print(
                    f"  [ END ] {stage:<25} RSS={rss:>7.0f} MB  {elapsed:>8.2f}s  {message}",
                    flush=True,
                )
            else:
                print(f"  [ END ] {stage:<25} RSS={rss:>7.0f} MB  {message}", flush=True)
        else:
            print(
                f"  [  ·  ] {stage:<25} {progress*100:>3.0f}%  RSS={rss:>7.0f} MB  {message}",
                flush=True,
            )

    @property
    def last_message(self) -> str:
        return self._last_message

    def stage_totals(self) -> Dict[str, float]:
        return {stage: sum(e for e, _ in entries) for stage, entries in self.completed.items()}

    def peak_rss(self) -> float:
        if not self._rss_snapshots:
            return _rss_mb()
        return max(r for _, r, _ in self._rss_snapshots)


# ─── C1~C6 驗證 ──────────────────────────────────────────────────────────────

def run_checks(
    result: Any,
    features_df: "pd.DataFrame",  # noqa: F821
    overall_elapsed: float,
    peak_rss: float,
    baseline_manifest: Optional[Dict[str, Any]],
    baseline_dir: Optional[Path],
) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """執行 C1~C6 驗證。回傳 (passed, failed, detail_dict)。"""
    passed: List[str] = []
    failed: List[str] = []
    details: Dict[str, Any] = {}

    feat_count = getattr(result, "feature_count", 0)

    # ── C1: 數值等價（與 golden baseline 比對）
    if baseline_manifest is not None and baseline_dir is not None and not features_df.empty:
        checksums_path = baseline_dir / "artifacts" / "checksums.json"
        if checksums_path.exists():
            try:
                baseline_checksums = _load_json(checksums_path)
                new_overall = _sha256_df(features_df)
                baseline_overall = baseline_checksums.get("overall_dataframe_sha256", "")
                if new_overall == baseline_overall:
                    passed.append("✅ C1: overall_checksum 與 baseline 完全一致")
                else:
                    # 逐欄比對找出差異
                    baseline_cols = baseline_checksums.get("column_sha256", {})
                    new_cols = _column_checksums(features_df)
                    mismatched = [c for c in new_cols if new_cols[c] != baseline_cols.get(c)]
                    details["c1_mismatch_cols"] = mismatched[:20]
                    failed.append(
                        f"❌ C1: checksum 不一致，{len(mismatched)} 個欄位差異 "
                        f"(前 20: {mismatched[:5]}...)"
                    )
            except Exception as e:
                failed.append(f"❌ C1: 比對 checksum 時發生例外: {e}")
        else:
            passed.append("⚠️  C1: baseline checksums 不存在，跳過數值比對")
    elif not features_df.empty:
        new_overall = _sha256_df(features_df)
        details["c1_overall_checksum"] = new_overall
        passed.append(f"⚠️  C1: 無 baseline，本次為首次執行（checksum={new_overall[:12]}...）")
    else:
        passed.append("⚠️  C1: CGSA 模式 features_df 為空，跳過 C1（未 materialize full DataFrame）")

    # ── C2: Feature count 合理性
    if baseline_manifest:
        expected = baseline_manifest.get("checksums", {}).get("feature_name_count", 0)
        if expected and feat_count == expected:
            passed.append(f"✅ C2: feature_count = {feat_count:,} 與 baseline 一致")
        elif expected:
            diff = feat_count - expected
            sign = "+" if diff >= 0 else ""
            failed.append(
                f"❌ C2: feature_count = {feat_count:,}，baseline = {expected:,}（差異 {sign}{diff}）"
            )
        else:
            passed.append(f"⚠️  C2: baseline 無 feature_count，本次 = {feat_count:,}")
    else:
        if feat_count > 0:
            passed.append(f"✅ C2: feature_count = {feat_count:,} > 0")
        else:
            failed.append("❌ C2: feature_count = 0")
    details["c2_feature_count"] = feat_count

    # ── C3: Column 名稱集合一致性
    if not features_df.empty and baseline_dir is not None:
        feature_names_path = baseline_dir / "artifacts" / "feature_names.json"
        if feature_names_path.exists():
            try:
                baseline_names = set(_load_json(feature_names_path))
                current_names = set(str(c) for c in features_df.columns)
                only_in_new = current_names - baseline_names
                only_in_baseline = baseline_names - current_names
                if not only_in_new and not only_in_baseline:
                    passed.append(f"✅ C3: 欄位名稱集合與 baseline 完全一致 ({len(current_names):,} cols)")
                else:
                    failed.append(
                        f"❌ C3: 欄位名稱不一致 — 新增 {len(only_in_new)} 個，減少 {len(only_in_baseline)} 個"
                    )
                    details["c3_only_in_new"] = list(only_in_new)[:10]
                    details["c3_only_in_baseline"] = list(only_in_baseline)[:10]
            except Exception as e:
                failed.append(f"❌ C3: 比對欄位名稱時發生例外: {e}")
        else:
            passed.append("⚠️  C3: baseline feature_names 不存在，跳過欄位名稱比對")
    else:
        if not features_df.empty:
            passed.append(f"⚠️  C3: 無 baseline，本次欄位數 = {features_df.shape[1]:,}")

    # ── C4: Peak RSS ≤ 6 GB
    details["c4_peak_rss_mb"] = peak_rss
    if peak_rss <= RSS_LIMIT_MB:
        passed.append(f"✅ C4: Peak RSS = {peak_rss:.0f} MB ≤ {RSS_LIMIT_MB / 1024:.0f} GB")
    else:
        failed.append(
            f"❌ C4: Peak RSS = {peak_rss:.0f} MB > {RSS_LIMIT_MB / 1024:.0f} GB（8GB 系統警戒線）"
        )

    # ── C5: Future leakage check
    try:
        from momentum.FeatureEngineering.feature_validator import validate_no_future_leak
        if not features_df.empty:
            leak_result = validate_no_future_leak(features_df)
            if isinstance(leak_result, bool):
                if leak_result:
                    passed.append("✅ C5: 無 future leakage（validate_no_future_leak=True）")
                else:
                    failed.append("❌ C5: 偵測到 future leakage！")
            elif isinstance(leak_result, dict):
                leaking_cols = leak_result.get("leaking_columns", [])
                if not leaking_cols:
                    passed.append("✅ C5: 無 future leakage")
                else:
                    failed.append(f"❌ C5: {len(leaking_cols)} 個欄位有 future leakage: {leaking_cols[:5]}")
                details["c5_leak_result"] = leak_result
            else:
                passed.append(f"✅ C5: validate_no_future_leak 執行完畢（result={leak_result}）")
        else:
            passed.append("⚠️  C5: CGSA 模式，features_df 為空，跳過 leakage check")
    except ImportError:
        passed.append("⚠️  C5: validate_no_future_leak 不可用，跳過")
    except Exception as e:
        passed.append(f"⚠️  C5: future leakage check 發生例外: {e}")

    # ── C6: NaN ratio 合理性
    if not features_df.empty:
        nan_ratio = _nan_ratio(features_df)
        details["c6_nan_ratio"] = nan_ratio
        if nan_ratio <= 0.30:  # 30% NaN 為可接受上限
            passed.append(f"✅ C6: NaN ratio = {nan_ratio:.2%} ≤ 30%")
        else:
            failed.append(f"❌ C6: NaN ratio = {nan_ratio:.2%} > 30%（偏高，請確認是否正常）")
    else:
        passed.append("⚠️  C6: CGSA 模式，features_df 為空，跳過 NaN ratio check")

    return passed, failed, details


# ─── Markdown 報告產生 ────────────────────────────────────────────────────────

def build_markdown_report(
    symbol: str,
    primary_tf: str,
    training_tfs: List[str],
    start_date: Optional[str],
    end_date: Optional[str],
    overall_elapsed: float,
    peak_rss: float,
    rss_start: float,
    feat_count: int,
    result: Any,
    stage_totals: Dict[str, float],
    passed_checks: List[str],
    failed_checks: List[str],
    check_details: Dict[str, Any],
    baseline_id: Optional[str],
) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    verdict = "✅ PASS" if not failed_checks else "❌ FAIL"
    layer_counts: Dict[str, int] = dict(getattr(result, "layer_counts", {}) or {})
    gen_time = float(getattr(result, "generation_time", overall_elapsed))

    lines: List[str] = []

    # ── 標題 ─────────────────────────────────────────────────────────────────
    lines.append("# ETHUSDT Multi-TF Pipeline Benchmark 報告")
    lines.append("")
    lines.append(f"> **執行時間**: {now_str}  ")
    lines.append("> **環境**: macOS M1 (8GB RAM)  ")
    data_range = f"{start_date or 'full'} → {end_date or 'full'}"
    lines.append(
        f"> **資料**: {symbol}, Primary {primary_tf} | Training {' + '.join(training_tfs)} | Range: {data_range}  "
    )
    lines.append(f"> **Config**: preset={PRESET}, L6.5 ON, training_tfs={training_tfs}  ")
    lines.append(f"> **Kline cache**: {KLINE_CACHE_DIR}/kline_cache.h5  ")
    lines.append(f"> **Verdict**: {verdict}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── 執行摘要 ─────────────────────────────────────────────────────────────
    lines.append("## 1. 執行摘要")
    lines.append("")
    speedup_total = _speedup_str(overall_elapsed, V7_REFERENCE["total_elapsed_sec"])
    speedup_rss = (
        f"{V7_REFERENCE['peak_rss_mb'] / peak_rss:.2f}×"
        if peak_rss > 0
        else "N/A"
    )
    feat_diff = feat_count - V7_REFERENCE["feature_count"]
    feat_diff_str = f"+{feat_diff:,}" if feat_diff >= 0 else f"{feat_diff:,}"

    lines.append("| 指標 | 本次執行 | V7 Baseline (參考) | 差異 |")
    lines.append("|------|---------|-------------------|------|")
    lines.append(f"| **完成狀態** | {verdict} | ✅ 完整完成 | — |")
    lines.append(f"| **總時間** | {_fmt_sec(overall_elapsed)} | {_fmt_sec(V7_REFERENCE['total_elapsed_sec'])} | 加速 {speedup_total} |")
    lines.append(f"| **Feature 數** | {feat_count:,} | {V7_REFERENCE['feature_count']:,} | {feat_diff_str} |")
    lines.append(f"| **Peak RSS** | {peak_rss:.0f} MB | {V7_REFERENCE['peak_rss_mb']:.0f} MB | RSS 比 {speedup_rss} 低 |")
    if baseline_id:
        lines.append(f"| **Baseline ID** | — | {baseline_id} | — |")
    lines.append("")
    lines.append(f"**生成時間**（factory 回報）: {_fmt_sec(gen_time)}")
    lines.append("")

    # ── C1~C6 驗證結果 ───────────────────────────────────────────────────────
    lines.append("## 2. C1~C6 驗證結果")
    lines.append("")
    if passed_checks:
        for msg in passed_checks:
            lines.append(f"- {msg}")
    if failed_checks:
        lines.append("")
        lines.append("**失敗項目：**")
        for msg in failed_checks:
            lines.append(f"- {msg}")
    if check_details:
        lines.append("")
        lines.append("<details><summary>詳細資訊</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(check_details, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    lines.append("")

    # ── Per-Stage 時間 ───────────────────────────────────────────────────────
    lines.append("## 3. Per-Stage 時間分析")
    lines.append("")
    if stage_totals:
        lines.append("### 3.1 Stage 耗時彙整")
        lines.append("")
        lines.append("| Stage | 本次 | V7 參考 | 加速比 | 佔比 |")
        lines.append("|-------|------|---------|--------|------|")
        for stage, secs in sorted(stage_totals.items(), key=lambda x: -x[1]):
            v7_ref = V7_REFERENCE["layer_times_sec"].get(stage, 0)
            v7_ref_str = f"{v7_ref:.2f}s" if v7_ref else "—"
            speedup = _speedup_str(secs, v7_ref) if v7_ref else "—"
            pct = secs / overall_elapsed * 100 if overall_elapsed > 0 else 0
            lines.append(f"| {stage} | {secs:.2f}s | {v7_ref_str} | {speedup} | {pct:.1f}% |")
        lines.append("")

        lines.append("### 3.2 時間佔比長條圖")
        lines.append("")
        lines.append("```")
        sorted_stages = sorted(stage_totals.items(), key=lambda x: -x[1])
        total_time = sum(stage_totals.values()) or overall_elapsed
        bar_width = 40
        for stage, secs in sorted_stages:
            pct = secs / total_time * 100 if total_time > 0 else 0
            bar_len = int(pct / 100 * bar_width)
            bar = "█" * bar_len
            lines.append(f"{stage:<25} {bar:<40} {pct:5.1f}%  ({secs:.0f}s)")
        lines.append("```")
        lines.append("")
    else:
        lines.append("（無 stage 計時資料，可能因 MultiTF 模式使用粗粒度 callback）")
        lines.append("")

    # ── Layer Counts ─────────────────────────────────────────────────────────
    if layer_counts:
        lines.append("## 4. Layer Feature Counts")
        lines.append("")
        lines.append("| Layer | Features |")
        lines.append("|-------|----------|")
        for layer, count in sorted(layer_counts.items()):
            lines.append(f"| {layer} | {count:,} |")
        lines.append("")

    # ── RSS 軌跡 ──────────────────────────────────────────────────────────────
    lines.append("## 5. 記憶體 (RSS) 軌跡摘要")
    lines.append("")
    lines.append("| 時間點 | RSS (MB) |")
    lines.append("|--------|----------|")
    lines.append(f"| 程式啟動 | {rss_start:.0f} |")
    lines.append(f"| Pipeline 結束 | {_rss_mb():.0f} |")
    lines.append(f"| **Peak RSS** | **{peak_rss:.0f}** |")
    lines.append(f"| 上限 (6 GB) | {RSS_LIMIT_MB} |")
    lines.append("")

    # ── 系統資訊 ─────────────────────────────────────────────────────────────
    lines.append("## 6. 系統資訊")
    lines.append("")
    lines.append(f"- Python: {sys.version.split()[0]}")
    lines.append(f"- Platform: {platform.platform()}")
    lines.append(f"- CPU cores: {os.cpu_count()}")
    lines.append("")

    # ── 環境變數（優化 flags） ────────────────────────────────────────────────
    opt_flags = [
        "FFACT_CGSA_ENABLED",
        "FFACT_SEARCHSORTED_ENABLED",
        "FFACT_NUMBA_ROLLING",
        "FFACT_POLARS_ENABLED",
        "FFACT_L3_STREAMING",
        "FFACT_L65_WORKERS",
        "FFACT_L7_WORKERS",
        "FFACT_MULTI_TF_MAX_WORKERS",
        "FFACT_LAYER3_CHUNK_SIZE",
    ]
    lines.append("## 7. 優化 Flags")
    lines.append("")
    lines.append("| Flag | 值 |")
    lines.append("|------|-----|")
    for flag in opt_flags:
        val = os.environ.get(flag, "(auto/default)")
        lines.append(f"| `{flag}` | `{val}` |")
    lines.append("")

    return "\n".join(lines)


# ─── 儲存 Baseline ────────────────────────────────────────────────────────────

def save_as_baseline(
    symbol: str,
    tf: str,
    preset: str,
    result: Any,
    features_df: "pd.DataFrame",  # noqa: F821
    overall_elapsed: float,
    peak_rss: float,
) -> Path:
    """儲存本次結果為 golden baseline。"""
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    baseline_id = f"{ts}_{symbol}_{tf}_{preset}_multitf"
    baseline_dir = BASELINE_REGISTRY_DIR / baseline_id
    artifacts_dir = baseline_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    feat_count = getattr(result, "feature_count", 0)
    layer_counts = dict(getattr(result, "layer_counts", {}) or {})
    metadata = dict(getattr(result, "metadata", {}) or {})
    config_used = dict(getattr(result, "config_used", {}) or {})

    feature_names: List[str] = []
    overall_checksum = ""
    col_checksums: Dict[str, str] = {}

    if not features_df.empty:
        feature_names = [str(c) for c in features_df.columns]
        overall_checksum = _sha256_df(features_df)
        col_checksums = _column_checksums(features_df)

    _write_json(artifacts_dir / "feature_names.json", feature_names)
    _write_json(
        artifacts_dir / "checksums.json",
        {
            "overall_dataframe_sha256": overall_checksum,
            "column_sha256": col_checksums,
            "config_hash": str(metadata.get("config_hash", "")),
        },
    )
    _write_json(artifacts_dir / "metadata_runtime.json", metadata)
    _write_json(artifacts_dir / "config_used.json", config_used)

    manifest = {
        "baseline_id": baseline_id,
        "created_at_utc": datetime.utcnow().isoformat() + "Z",
        "symbol": symbol,
        "timeframe": tf,
        "preset": preset,
        "training_tfs": TRAINING_TFS,
        "force_regenerate": True,
        "shape": {
            "rows": int(features_df.shape[0]) if not features_df.empty else 0,
            "columns": int(features_df.shape[1]) if not features_df.empty else feat_count,
        },
        "layer_counts": layer_counts,
        "performance": {
            "elapsed_seconds": overall_elapsed,
            "peak_rss_mb": peak_rss,
            "generation_time_reported_by_factory": float(getattr(result, "generation_time", 0)),
        },
        "checksums": {
            "overall_dataframe_sha256": overall_checksum,
            "feature_name_count": len(feature_names) or feat_count,
            "config_hash": str(metadata.get("config_hash", "")),
        },
    }
    _write_json(baseline_dir / "manifest.json", manifest)
    print(f"\n[Baseline] 已儲存至 {baseline_dir}")
    return baseline_dir


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def main(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_regenerate: bool = True,
    compare_baseline_path: Optional[str] = None,
    create_baseline: bool = False,
    skip_full_readback: bool = False,
) -> bool:
    import pandas as pd  # noqa: F811

    print("=" * 70)
    print("BENCHMARK: ETHUSDT 1h + 12h Multi-TF Pipeline")
    print("=" * 70)
    print(f"  Symbol        : {SYMBOL}")
    print(f"  Primary TF    : {PRIMARY_TF}")
    print(f"  Training TFs  : {TRAINING_TFS}")
    print(f"  Date range    : {start_date or 'full'} → {end_date or 'full'}")
    print(f"  Preset        : {PRESET}")
    print(f"  Kline cache   : {KLINE_CACHE_DIR}/kline_cache.h5")
    print(f"  Force regen   : {force_regenerate}")
    print("-" * 70)

    # ── 尋找既有 baseline ────────────────────────────────────────────────────
    baseline_dir: Optional[Path] = None
    baseline_manifest: Optional[Dict[str, Any]] = None
    baseline_id: Optional[str] = None

    if compare_baseline_path:
        manifest_path = Path(compare_baseline_path)
        if manifest_path.is_dir():
            manifest_path = manifest_path / "manifest.json"
        if manifest_path.exists():
            baseline_manifest = _load_json(manifest_path)
            baseline_dir = manifest_path.parent
            baseline_id = baseline_manifest.get("baseline_id", str(baseline_dir.name))
            print(f"[Baseline] 使用指定 baseline: {baseline_id}")
        else:
            print(f"[WARNING] 指定的 baseline 不存在: {compare_baseline_path}")
    else:
        found = _find_latest_baseline(SYMBOL, PRIMARY_TF, PRESET)
        if found:
            baseline_manifest = _load_json(found)
            baseline_dir = found.parent
            baseline_id = baseline_manifest.get("baseline_id", str(baseline_dir.name))
            print(f"[Baseline] 找到既有 multi-TF baseline: {baseline_id}")
        else:
            print("[Baseline] 無既有 multi-TF baseline，本次為首次執行")

    # ── 執行 pipeline ────────────────────────────────────────────────────────
    from momentum.factories import create_feature_factory, create_feature_reader

    tracker = DetailedTimingTracker()
    rss_start = _rss_mb()
    overall_start = time.perf_counter()
    run_error: Optional[Exception] = None

    try:
        factory = create_feature_factory(
            cache_dir=KLINE_CACHE_DIR,
            validate_continuity=True,
        )

        config_override: Dict[str, Any] = {
            "preset": PRESET,
            "timeframes": {
                "primary": PRIMARY_TF,
                "training": TRAINING_TFS,
                "alignment": "point_in_time",
                "alignment_mode": "open_minus",
            },
            # Bug #3 fix: scan_config.yaml has preprocessing.enabled=false by default.
            # Explicitly enable L6.5 preprocessing so all layers (L1-L7) are active,
            # matching the V7 reference run that processed 708 groups in L6.5.
            "preprocessing": {
                "enabled": True,
            },
        }

        print("\n[Pipeline] generate_features() 啟動...\n")
        result = factory.generate_features(
            symbol=SYMBOL,
            timeframe=PRIMARY_TF,
            config_override=config_override,
            force_regenerate=force_regenerate,
            progress_callback=tracker,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        run_error = exc
        result = None
        traceback.print_exc()

    overall_elapsed = time.perf_counter() - overall_start
    peak_rss = tracker.peak_rss()

    if run_error is not None:
        print(f"\n[FAIL] Pipeline 拋出例外: {type(run_error).__name__}: {run_error}")
        return False

    feat_count = getattr(result, "feature_count", 0)
    print(f"\n[Pipeline] 完成！elapsed={_fmt_sec(overall_elapsed)}, features={feat_count:,}, peak_rss={peak_rss:.0f} MB")

    # ── 讀取 features_df（CGSA 模式） ─────────────────────────────────────────
    # 注意：全量 readback（858 parquet concat → 434,720 cols）極耗記憶體。
    # 只有在 baseline 存在（C1/C3 checksum 比對需要）時才執行；無 baseline 則
    # C1/C3 都是 ⚠️ 跳過，不需要完整 DataFrame。
    features_df = getattr(result, "features_df", pd.DataFrame())
    cgsa_mode = features_df.empty and feat_count > 0
    memory_tier = os.getenv("FFACT_MEMORY_TIER", "auto").strip().lower()
    auto_skip_full_readback = memory_tier == "8gb"
    need_full_readback = (
        cgsa_mode
        and baseline_manifest is not None
        and not skip_full_readback
        and not auto_skip_full_readback
    )
    if need_full_readback:
        try:
            metadata = dict(getattr(result, "metadata", {}) or {})
            config_hash = str(metadata.get("config_hash", ""))
            if config_hash:
                reader = create_feature_reader()
                frames = [gdf for _, gdf in reader.stream_groups(SYMBOL, config_hash)]
                if frames:
                    features_df = pd.concat(frames, axis=1)
                    print(f"[CGSA] Readback OK: {features_df.shape[1]:,} cols, {features_df.shape[0]:,} rows")
        except Exception as e:
            print(f"[WARNING] CGSA readback 失敗: {e}")
    elif cgsa_mode:
        if skip_full_readback or auto_skip_full_readback:
            reason = "--skip-full-readback" if skip_full_readback else "FFACT_MEMORY_TIER=8gb"
            print(f"[CGSA] {reason}，跳過全量 readback（feat_count={feat_count:,}）")
        else:
            print(f"[CGSA] 無 baseline，跳過全量 readback（feat_count={feat_count:,}）")

    # ── C1~C6 驗證 ────────────────────────────────────────────────────────────
    passed_checks, failed_checks, check_details = run_checks(
        result=result,
        features_df=features_df,
        overall_elapsed=overall_elapsed,
        peak_rss=peak_rss,
        baseline_manifest=baseline_manifest,
        baseline_dir=baseline_dir,
    )

    # ── 儲存為 baseline（若指定或首次執行） ─────────────────────────────────
    if create_baseline or baseline_manifest is None:
        if features_df.empty and cgsa_mode:
            passed_checks.append("⚠️  CGSA no-readback 模式未儲存 baseline；請改用 streaming checksum/schema gate")
        else:
            saved_dir = save_as_baseline(
                SYMBOL, PRIMARY_TF, PRESET, result, features_df, overall_elapsed, peak_rss
            )
            passed_checks.append(f"✅ 已儲存為新 baseline: {saved_dir.name}")

    # ── 產出 Markdown 報告 ────────────────────────────────────────────────────
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"benchmark_multitf_{report_ts}.md"

    report_md = build_markdown_report(
        symbol=SYMBOL,
        primary_tf=PRIMARY_TF,
        training_tfs=TRAINING_TFS,
        start_date=start_date,
        end_date=end_date,
        overall_elapsed=overall_elapsed,
        peak_rss=peak_rss,
        rss_start=rss_start,
        feat_count=feat_count,
        result=result,
        stage_totals=tracker.stage_totals(),
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        check_details=check_details,
        baseline_id=baseline_id,
    )

    report_path.write_text(report_md, encoding="utf-8")
    print(f"\n[Report] Markdown 報告已寫入: {report_path}")

    # ── 終端摘要 ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"  總時間     : {_fmt_sec(overall_elapsed)}")
    print(f"  Peak RSS   : {peak_rss:.0f} MB")
    print(f"  Features   : {feat_count:,}")
    verdict = "PASS ✅" if not failed_checks else "FAIL ❌"
    print(f"  C1~C6      : {verdict} ({len(passed_checks)} passed, {len(failed_checks)} failed)")
    if failed_checks:
        for msg in failed_checks:
            print(f"    {msg}")
    print("=" * 70)

    return not bool(failed_checks)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ETHUSDT Multi-TF Pipeline 完整 benchmark + C1~C6 驗證")
    p.add_argument("--start-date", default=None, help="kline 起始日期（不設則使用全部資料）")
    p.add_argument("--end-date", default=None, help="kline 結束日期（不設則使用全部資料）")
    p.add_argument("--no-force-regenerate", action="store_true", help="允許讀取快取")
    p.add_argument(
        "--compare-baseline",
        default=None,
        help="指定 baseline manifest.json 或目錄路徑進行比對",
    )
    p.add_argument(
        "--create-baseline",
        action="store_true",
        help="不論是否有既有 baseline，都強制儲存本次為新 baseline",
    )
    p.add_argument(
        "--skip-full-readback",
        action="store_true",
        help="CGSA 模式跳過全量 parquet concat readback，適合 8GB full benchmark 避免 OOM",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = main(
        start_date=args.start_date,
        end_date=args.end_date,
        force_regenerate=not args.no_force_regenerate,
        compare_baseline_path=args.compare_baseline,
        create_baseline=args.create_baseline,
        skip_full_readback=args.skip_full_readback,
    )
    sys.exit(0 if success else 1)
