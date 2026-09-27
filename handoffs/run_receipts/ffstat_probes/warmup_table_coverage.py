"""FF-STAT Task 2.4：倍數表覆蓋收據（取代 handoffs/run_receipts/20260927-warmup-table-coverage.py 之六類版）。

以預設全設定（ConfigManager().get_merged_config()）於真實 BTCUSDT 1h 跑 L1，攔截每個輸出點之 OutputPointSpec
（stable_mask.instance_k），逐一核對：倍數表有條目、條目之 period_keys ⊆ 該呼叫之參數字典。
類別全集＝AtomicIndicatorConfig 之模型欄位（十類）。輸出收據 JSON 至 stdout 或 --out。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/warmup_table_coverage.py [--out <path>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def coverage_report(timeframe: str = "1h") -> Dict[str, Any]:
    import yaml

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.FeatureEngineering.feature_config import AtomicIndicatorConfig
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    table = yaml.safe_load((REPO / "momentum/FeatureEngineering/atomic/warmup_table.yaml").read_text(encoding="utf-8"))
    entries: Dict[str, Any] = dict(table.get("indicators") or {})
    specs: List[Any] = []

    def record(spec, table_arg, upstream_k=None):  # noqa: ARG001 — 只記錄、不判定
        specs.append(spec)
        return 0

    original = sm.instance_k
    sm.instance_k = record
    try:
        factory = create_feature_factory(cache_dir=str(REPO / "data_cache/feature_klines"), validate_continuity=False)
        config = ConfigManager().get_merged_config()
        raw = factory._layer0_data_ingestion("BTCUSDT", timeframe, config)
        factory._layer1_atomic_indicators(raw.iloc[:3000], config)
    finally:
        sm.instance_k = original

    missing: List[str] = []
    missing_keys: List[Dict[str, Any]] = []
    for spec in specs:
        if spec.upstream:
            continue  # 同引擎衍生輸出之 K 依上游遞推（§C v39），不查表
        entry = entries.get(spec.indicator)
        if entry is None:
            missing.append(spec.indicator)
            continue
        lacking = [k for k in entry.get("period_keys", []) if k not in spec.params]
        if lacking:
            missing_keys.append({"engine": spec.engine, "column": spec.column, "indicator": spec.indicator, "missing": lacking})
    return {
        "categories": sorted(AtomicIndicatorConfig.model_fields),
        "output_points": len(specs),
        "indicators_seen": sorted({s.indicator for s in specs}),
        "missing": sorted(set(missing)),
        "missing_keys": missing_keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--tf", default="1h")
    args = parser.parse_args()
    report = coverage_report(args.tf)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not report["missing"] and not report["missing_keys"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
