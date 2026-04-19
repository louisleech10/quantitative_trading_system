"""Gate 3→4 Full-Pipeline Re-Profile

完整走 generate_features() multi-TF pipeline（primary=1h, training=[1h,12h]），
全層開啟（L0~L7 + L6.5），量測真實時間、記憶體、輸出欄位數與檔案大小。
"""
from __future__ import annotations

import gc
import json
import os
import sys
import time
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Phase 0-3 所有優化現已預設開啟（main codebase 預設值 = "1"）
# 此處不需額外設定 FFACT_* 環境變數
# 如需關閉特定優化可設 FFACT_USE_CGSA=0 等

from momentum.core.logging import get_logger
from momentum.factories import create_feature_factory

logger = get_logger(__name__)

SYMBOL = "ETHUSDT"
PRIMARY_TF = "1h"
TRAINING_TFS = ["1h", "12h"]
KLINE_CACHE_DIR = str(PROJECT_ROOT / "data_cache" / "feature_klines")


def main() -> None:
    process = psutil.Process()

    gc.collect()
    rss_before = process.memory_info().rss

    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR)

    # 使用 full config — 全層開啟（包含 preprocessing L6.5）
    config_override = {
        "timeframes": {
            "primary": PRIMARY_TF,
            "training": TRAINING_TFS,
            "alignment": "point_in_time",
            "alignment_mode": "open_minus",
        },
        # 確保 preprocessing 開啟
        "preprocessing": {
            "enabled": True,
        },
    }

    print(f"Starting full pipeline: {SYMBOL}, primary={PRIMARY_TF}, training={TRAINING_TFS}")
    print(f"RSS before: {rss_before / (1024**2):.1f} MB")
    print("=" * 60)

    t_start = time.perf_counter()
    result = factory.generate_features(
        symbol=SYMBOL,
        timeframe=PRIMARY_TF,
        config_override=config_override,
        force_regenerate=True,
        persist=True,
    )
    t_total = time.perf_counter() - t_start

    gc.collect()
    rss_after = process.memory_info().rss
    rss_peak = rss_after  # 近似峰值（GC 後）

    # 收集輸出資訊
    feature_count = result.feature_count if hasattr(result, 'feature_count') else 0
    output_shape = None
    if hasattr(result, 'features') and result.features is not None:
        output_shape = list(result.features.shape)
    elif hasattr(result, 'metadata') and 'shape' in result.metadata:
        output_shape = result.metadata['shape']

    # 收集 layer_counts
    layer_counts = {}
    if hasattr(result, 'layer_counts') and result.layer_counts:
        layer_counts = result.layer_counts
    elif hasattr(result, 'metadata') and 'layer_counts' in result.metadata:
        layer_counts = result.metadata['layer_counts']

    # 檢查輸出檔案大小
    output_dir = Path("data_cache/features") / SYMBOL
    output_files = []
    total_file_size_mb = 0.0
    if output_dir.exists():
        for f in output_dir.rglob("*"):
            if f.is_file():
                size_mb = f.stat().st_size / (1024**2)
                total_file_size_mb += size_mb
                output_files.append({"path": str(f.relative_to(output_dir)), "size_mb": round(size_mb, 2)})

    # 也檢查 parquet cache
    cache_dir = Path("data_cache/features")
    parquet_count = 0
    parquet_total_mb = 0.0
    if cache_dir.exists():
        for f in cache_dir.rglob("*.parquet"):
            parquet_count += 1
            parquet_total_mb += f.stat().st_size / (1024**2)

    payload = {
        "symbol": SYMBOL,
        "primary_tf": PRIMARY_TF,
        "training_tfs": TRAINING_TFS,
        "pipeline_total_seconds": round(t_total, 3),
        "pipeline_total_minutes": round(t_total / 60, 2),
        "feature_count": feature_count,
        "output_shape": output_shape,
        "layer_counts": layer_counts,
        "rss_before_mb": round(rss_before / (1024**2), 1),
        "rss_after_mb": round(rss_after / (1024**2), 1),
        "rss_delta_mb": round((rss_after - rss_before) / (1024**2), 1),
        "output_files_count": len(output_files),
        "output_total_size_mb": round(total_file_size_mb, 2),
        "parquet_files_count": parquet_count,
        "parquet_total_size_mb": round(parquet_total_mb, 2),
        "gate3_to_4": {
            "condition": "L2+L6.5 > 30% total → Phase 4; else SKIP",
            "note": "Per-layer timing from pipeline logs (see above)",
        },
        "no_phase4": {
            "condition": "pipeline_total < 420s (7 min/sym) → SKIP Phase 4",
            "pipeline_total_s": round(t_total, 3),
            "threshold_s": 420,
            "result": "SKIP Phase 4" if t_total < 420 else "PROCEED to Phase 4",
        },
        "metadata": {
            k: v for k, v in (result.metadata.items() if hasattr(result, 'metadata') and result.metadata else [])
        },
    }

    out_dir = Path("results/l56_golden_baseline")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "phase3_gate_full_pipeline_reprofile.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"Pipeline Total: {t_total:.3f}s ({t_total/60:.1f} min)")
    print(f"Feature Count: {feature_count}")
    print(f"Output Shape: {output_shape}")
    print(f"Layer Counts: {json.dumps(layer_counts, indent=2)}")
    print(f"RSS Before: {rss_before/(1024**2):.1f} MB | After: {rss_after/(1024**2):.1f} MB | Delta: {(rss_after-rss_before)/(1024**2):.1f} MB")
    print(f"Output Files: {len(output_files)} files, {total_file_size_mb:.2f} MB")
    print(f"Parquet Cache: {parquet_count} files, {parquet_total_mb:.2f} MB")
    print(f"No-Phase-4: {payload['no_phase4']['result']}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
