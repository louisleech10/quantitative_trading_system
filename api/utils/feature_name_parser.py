"""Feature name parsing utilities.

Stateless helpers for inferring category, pipeline layer, and difficulty
level from 7-segment feature names.  Extracted from
``FeatureExportService`` to eliminate cross-service coupling (Rule 4).
"""

from __future__ import annotations

import re
from typing import Dict

# ── Constants ────────────────────────────────────────────────

LEVEL_CATEGORY_MAP: Dict[str, list] = {
    "L1_basic": ["trend", "momentum", "volatility", "volume"],
    "L2_intermediate": ["statistics", "cycle", "pattern", "tail_risk"],
    "L3_advanced": ["microstructure", "entropy"],
}

# Compiled once at module level — matches any Layer 2 derived-operator suffix.
_LAYER2_RE = re.compile(
    r"_(Cross|Ratio|Distance|SignedStrength|Sign|Log1p|Abs|Clip)$"
    r"|_Momentum_L\d+$"
    r"|_(TsArgmax|TsArgmin|TsRank|DecayLinear)_W\d+$"
    r"|_TsCorr_.+_W\d+$"
    r"|_BinarySignal"
)


# ── Public API ───────────────────────────────────────────────

def infer_category(feature_name: str) -> str:
    """Infer high-level feature category from the name prefix/infix."""
    if feature_name.startswith("ms_"):
        return "microstructure"
    if feature_name.startswith("ent_"):
        return "entropy"
    if feature_name.startswith("tr_"):
        return "tail_risk"
    if (
        feature_name.startswith("close_trend_")
        or feature_name.startswith("volume_trend_")
        or "_trend_" in feature_name
    ):
        return "trend"
    if "_momentum_" in feature_name:
        return "momentum"
    if "_volatility_" in feature_name:
        return "volatility"
    if "_volume_" in feature_name:
        return "volume"
    if "_cycle_" in feature_name:
        return "cycle"
    if "_pattern_" in feature_name:
        return "pattern"
    if (
        "_statistics_" in feature_name
        or "_stats_" in feature_name
        or "_stat_" in feature_name
    ):
        return "statistics"
    if feature_name.startswith("meta_"):
        return "meta"
    return "other"


def infer_level(category: str) -> str:
    """Map a category string to its difficulty level."""
    for level, categories in LEVEL_CATEGORY_MAP.items():
        if category in categories:
            return level
    return "L1_basic"


def infer_layer(feature_name: str) -> str:
    """Determine the pipeline layer that produced this feature.

    Detection order reflects pipeline depth — outermost transform wins.
    """
    # Layer 6.5: preprocessing — _rank/_gaussian/_zscore_{n}
    if feature_name.endswith("_rank") or feature_name.endswith("_gaussian"):
        return "layer6_5"
    if re.search(r"_zscore_\d+$", feature_name):
        return "layer6_5"
    # Layer 6: meta features
    if feature_name.startswith("meta_"):
        return "layer6"
    # Layer 5: cross-sectional features
    if feature_name.startswith("cs_"):
        return "layer5"
    # Layer 4: lag — suffix _Lag_{n}
    if "_Lag_" in feature_name:
        return "layer4"
    # Layer 3: rolling aggregation — suffix _{Agg}_W{n}
    if re.search(
        r"_(Mean|Std|Min|Max|Range|Slope|Rank|ZScore|Skew|Kurt)_W\d+$",
        feature_name,
    ):
        return "layer3"
    # Layer 2: derived operators
    if _LAYER2_RE.search(feature_name):
        return "layer2"
    # Layer 1: atomic indicators (fallback)
    return "layer1"
