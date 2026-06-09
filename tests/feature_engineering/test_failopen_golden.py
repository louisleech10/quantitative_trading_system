"""Task 0.1 fail-open baseline 完整性 gate。"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "tests/_golden/failopen"
# 委員會 2026-06-09:2 代表性 symbol × 2 TF(硬碟/記憶體;全量逐格 hash 下足以抓回歸)。
SYMBOLS = {"BTCUSDT", "ETHUSDT"}
TIMEFRAMES = {"1h", "12h"}
PERF_FIELDS = {
    "generation_wall_seconds",
    "hash_wall_seconds",
    "wall_seconds",
    "rss_before_mb",
    "rss_after_mb",
    "process_peak_rss_mb",
    "layer_counts",
}
MULTI_TF_STAGE_FIELDS = {"dual_tf_l1_l6", "alignment", "l65_l7"}
HASH_FIELDS = {
    "canonical_sha256", "column_order_sha256", "dtypes_sha256",
    "index_sha256", "values_sha256", "nan_mask_sha256",
}


def _assert_hash_record(record: dict) -> None:
    assert HASH_FIELDS <= record.keys()
    assert all(len(record[field]) == 64 for field in HASH_FIELDS)
    assert record["rows"] > 0
    assert record["groups"] >= 0
    assert 0.0 <= record["nan_ratio"] <= 1.0


def test_baseline_frozen() -> None:
    baseline_path = GOLDEN_DIR / "baseline.json"
    nan_path = GOLDEN_DIR / "max_nan_ratio.json"
    assert baseline_path.is_file()
    assert nan_path.is_file()

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert set(baseline["symbols"]) == SYMBOLS
    assert set(baseline["timeframes"]) == TIMEFRAMES
    assert set(baseline["single_tf"]) == SYMBOLS
    assert set(baseline["multi_tf"]) == SYMBOLS

    environment = baseline["environment"]
    assert len(environment["commit_sha"]) == 40
    assert len(environment["kline_sha256"]) == 64
    assert environment["env"]["PYTHONHASHSEED"] == "0"
    assert environment["env"]["resolved_l3_persist_mode"] in {
        "streaming", "hybrid", "in_memory"
    }
    assert environment["tier"]["total_ram_bytes"] > 0
    for version in ("python", "pandas", "numpy", "TA-Lib", "numba"):
        assert environment["versions"][version] != "not-installed"

    for symbol in SYMBOLS:
        assert set(baseline["single_tf"][symbol]) == TIMEFRAMES
        for timeframe in TIMEFRAMES:
            record = baseline["single_tf"][symbol][timeframe]
            assert len(record["config_payload_sha256"]) == 64
            assert len(record["config_hash"]) >= 32
            assert set(record["layers"]) == {f"L{number}" for number in range(1, 7)}
            for layer_record in record["layers"].values():
                _assert_hash_record(layer_record)
            l3 = record["layers"]["L3"]
            assert l3["storage"] == "registry_groups"
            assert l3["groups"] > 0
            assert l3["columns"] > 0
            _assert_hash_record(record["final_L7"])
            assert record["artifacts"]["file_count"] > 0
            assert len(record["artifacts"]["aggregate_sha256"]) == 64
            # 效能/記憶體基準(防時間爆炸/記憶體爆炸回歸)
            assert PERF_FIELDS <= record["perf"].keys()
            assert record["perf"]["generation_wall_seconds"] > 0
            assert record["perf"]["hash_wall_seconds"] >= 0
            assert record["perf"]["wall_seconds"] > 0
            assert record["perf"]["process_peak_rss_mb"] > 0

        multi_record = baseline["multi_tf"][symbol]
        assert set(multi_record["training_timeframes"]) == TIMEFRAMES
        _assert_hash_record(multi_record["merged_L7"])
        assert multi_record["merged_L7"]["storage"] == "l7_raw_parquet"
        assert multi_record["merged_L7"]["columns"] > 0
        assert multi_record["merged_L7_source"]["kind"] == "l7_raw_parquet"
        assert multi_record["merged_L7_source"]["manifest_path"]
        assert multi_record["artifacts"]["file_count"] > 0
        assert len(multi_record["artifacts"]["aggregate_sha256"]) == 64
        assert PERF_FIELDS <= multi_record["perf"].keys()
        assert multi_record["perf"]["generation_wall_seconds"] > 0
        assert multi_record["perf"]["hash_wall_seconds"] >= 0
        assert multi_record["perf"]["process_peak_rss_mb"] > 0
        stage_seconds = multi_record["perf"].get("multi_tf_stage_seconds") or {}
        assert MULTI_TF_STAGE_FIELDS <= stage_seconds.keys()
        # baseline 走 serial(FFACT_MULTI_TF_PARALLEL=0); dual_tf_l1_l6 須有實測值
        assert stage_seconds["dual_tf_l1_l6"] > 0
        assert stage_seconds["l65_l7"] > 0
        assert stage_seconds["alignment"] >= 0

    nan_limits = json.loads(nan_path.read_text(encoding="utf-8"))
    assert set(nan_limits["ratios"]) == SYMBOLS
    for symbol, ratios in nan_limits["ratios"].items():
        assert set(ratios) == TIMEFRAMES, symbol
        assert all(0.0 <= value <= 1.0 for value in ratios.values())
