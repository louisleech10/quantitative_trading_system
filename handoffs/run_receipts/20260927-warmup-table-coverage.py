"""列出預設 FF 設定中啟用、但 warmup_table.yaml 查不到（落入 4.5 後備）之 L1 指標。"""
import sys

sys.path.insert(0, ".")
from momentum.FeatureEngineering.config_manager import ConfigManager  # noqa: E402
from momentum.FeatureEngineering.atomic import warmup_lookup as wl  # noqa: E402
from momentum.FeatureEngineering.warmup_window import _resolve_indicator_max_period  # noqa: E402

table = wl._load()
cfg = ConfigManager().get_merged_config()
ai = cfg.atomic_indicators
rows = []
for cat_name in ("trend", "momentum", "volatility", "volume", "cycle", "statistics"):
    cat = getattr(ai, cat_name)
    for ind in cat.indicators:
        name = str(ind.name).upper()
        period = _resolve_indicator_max_period(ind.model_dump())
        hit = name in table
        rows.append((cat_name, name, bool(cat.enabled and ind.enabled), period, hit))

total = len(rows)
missing = [r for r in rows if not r[4]]
print(f"total_indicators={total} in_table={total - len(missing)} missing={len(missing)}")
for cat_name, name, enabled, period, _ in missing:
    print(f"MISSING {cat_name:<11} {name:<24} enabled={enabled} max_period={period} fallback_bars={wl.get_warmup_bars(name, period)}")
