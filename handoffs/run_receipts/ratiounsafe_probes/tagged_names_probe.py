"""RATIOUNSAFE 預查：以生產命名規則造落盤欄名，量 `_is_ratio_unsafe_column` 漏判／誤判（輕量，不生成特徵）。
用法：venv/bin/python handoffs/run_receipts/ratiounsafe_probes/tagged_names_probe.py
命名：L1＝talib_wrapper 之 `<source>_<category>_<indicator>`；週期標記＝feature_storage CGSA 寫檔規則
（:1059 起，插於第一個底線後）與 FeatureFactory._timeframe_tagged_name 兩套各算一次。
"""

import json

from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fp
from momentum.FeatureEngineering.operators import rolling_aggregator as ra
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


def storage_tag(col: str, tf: str) -> str:
    # 逐字重放 feature_storage.py CGSA 寫檔之標記（僅 m/h/d 結尾之週期才標）
    if not (tf and tf[-1] in ("m", "h", "d") and tf[:-1].isdigit()):
        return col
    cp = col.split("_", 1)
    if len(cp) == 2 and not cp[1].startswith(tf + "_"):
        return f"{cp[0]}_{tf}_{cp[1]}"
    return col


def main() -> None:
    tf_keys = sorted(TimeframeAligner._timeframe_seconds_keys())
    cmap = TALibWrapper._CATEGORY_MAP
    pattern = [f"ohlc_pattern_{TALibWrapper.normalize_indicator_name(i)}" for i in cmap["pattern"]]
    pattern_l2 = [f"{c}_BinarySignal" for c in pattern] + [f"{c}_Momentum_L5" for c in pattern]
    others = []
    for cat, inds in cmap.items():
        if cat in ("pattern", "price_transform"):
            continue
        for i in inds:
            others.append(f"close_{cat}_{TALibWrapper.normalize_indicator_name(i)}_20")
    others += ["ms_amihud_illiq_5", "ent_shannon_close_20", "tr_cvar_5pct_20", "meta_Trend_Consensus",
               "close_trend_EMA_20_mean_W20"]
    out = {"tf_keys": tf_keys, "n_pattern_l1": len(pattern), "n_pattern_l2": len(pattern_l2), "n_others": len(others),
           "untagged": {}, "storage_tagged": {}, "factory_tagged": {}}
    for label, fn in (("untagged", lambda c, tf: c), ("storage_tagged", storage_tag),
                      ("factory_tagged", lambda c, tf: FactoryTag(c, tf, set(tf_keys)))):
        for tf in tf_keys:
            pos = [fn(c, tf) for c in pattern + pattern_l2]
            neg = [fn(c, tf) for c in others]
            out[label][tf] = {
                "pattern_flagged_preprocessor": sum(fp._is_ratio_unsafe_column(c) for c in pos),
                "pattern_flagged_rolling_aggregator": sum(ra._is_ratio_unsafe_column(c) for c in pos),
                "pattern_total": len(pos),
                "others_false_positive": sum(fp._is_ratio_unsafe_column(c) for c in neg),
                "example": pos[0],
            }
            if label == "untagged":
                break
    print(json.dumps(out, ensure_ascii=False, indent=1))


def FactoryTag(col: str, tf: str, keys: set) -> str:  # noqa: N802
    return FeatureFactory._timeframe_tagged_name(col, tf, keys)


if __name__ == "__main__":
    main()
