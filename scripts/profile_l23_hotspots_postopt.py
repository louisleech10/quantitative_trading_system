import json
import time

from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from momentum.factories import create_feature_factory


def main() -> None:
    cfg = ConfigManager().get_merged_config()
    factory = create_feature_factory()
    raw = factory._layer0_data_ingestion("ETHUSDT", "12h", cfg)
    layer1 = factory._layer1_atomic_indicators(raw, cfg)

    sections = [
        "distance",
        "cross",
        "ratio",
        "momentum",
        "binary_signal",
        "signed_strength",
        "worldquant",
    ]
    l2_results = {}
    for section in sections:
        op_cfg = cfg.operators.model_dump(by_alias=True)
        for key, value in op_cfg.items():
            if isinstance(value, dict) and "enabled" in value:
                value["enabled"] = key == section
        eng = DerivedOperatorEngine(op_cfg)
        t0 = time.perf_counter()
        out = eng.compute_all(layer1, raw)
        l2_results[section] = {"seconds": time.perf_counter() - t0, "cols": int(out.shape[1])}

    agg_base = cfg.rolling_aggregation.model_dump(by_alias=True)
    aggs = list(RollingAggregator.AGGREGATORS.keys())
    l3_results = {}
    for agg in aggs:
        agg_cfg = dict(agg_base)
        agg_cfg["enabled"] = True
        agg_cfg["aggregators"] = [agg]
        r = RollingAggregator(agg_cfg)
        t0 = time.perf_counter()
        out = r.compute_all(layer1)
        l3_results[agg] = {"seconds": time.perf_counter() - t0, "cols": int(out.shape[1])}

    eng_all = DerivedOperatorEngine(cfg.operators.model_dump(by_alias=True))
    t0 = time.perf_counter()
    l2_all = eng_all.compute_all(layer1, raw)
    l2_total = {"seconds": time.perf_counter() - t0, "cols": int(l2_all.shape[1])}

    r_all = RollingAggregator(cfg.rolling_aggregation.model_dump(by_alias=True))
    t0 = time.perf_counter()
    l3_all = r_all.compute_all(layer1)
    l3_total = {"seconds": time.perf_counter() - t0, "cols": int(l3_all.shape[1])}

    payload = {
        "layer1_shape": list(layer1.shape),
        "layer2_total": l2_total,
        "layer3_total": l3_total,
        "layer2_sections": l2_results,
        "layer3_aggs": l3_results,
    }

    out_path = "results/l56_golden_baseline/l23_hotspots_postopt_1run.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(out_path)


if __name__ == "__main__":
    main()
