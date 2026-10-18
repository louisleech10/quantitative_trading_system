"""Feature name parsing utilities（FF-NAME Task 3.1）.

欄名語意一律由 `parse_feature_name`（`momentum/FeatureEngineering/feature_naming.py`，經 `momentum.factories`
取用）決定；本模組只把身分投影為 API 之 category／layer／level，不保留任何子字串或正則啟發式。

非特徵名具名回傳、不落入 other：`label_*` ⇒ `label`；其餘不合文法者（raw kline 欄、舊世代欄名等）⇒
`unsupported`（fail-closed，不猜）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from momentum.factories import feature_layer_of, feature_name_errors, parse_feature_name

# ── Constants ────────────────────────────────────────────────

LEVEL_CATEGORY_MAP: Dict[str, list] = {
    "L1_basic": ["trend", "momentum", "volatility", "volume"],
    "L2_intermediate": ["statistics", "cycle", "pattern", "tail-risk"],
    "L3_advanced": ["microstructure", "entropy"],
}

LABEL_CATEGORY = "label"
LABEL_LAYER = "label"
UNSUPPORTED = "unsupported"


def _identity(feature_name: str) -> Tuple[Optional[Any], Optional[str]]:
    """欄名 → (身分, None)；label ⇒ (None, "label")；不合文法 ⇒ (None, "unsupported")。"""
    parse_error, label_error = feature_name_errors()
    try:
        return parse_feature_name(str(feature_name)), None
    except label_error:
        return None, LABEL_CATEGORY
    except parse_error:
        return None, UNSUPPORTED


# ── Public API ───────────────────────────────────────────────

def infer_category(feature_name: str) -> str:
    """欄名之 category＝`parse_feature_name(name).category`；label ⇒ `label`；不合文法 ⇒ `unsupported`。"""
    identity, named = _identity(feature_name)
    if identity is None:
        return str(named)
    return str(identity.category)


def infer_level(category: str) -> str:
    """Map a category string to its difficulty level."""
    for level, categories in LEVEL_CATEGORY_MAP.items():
        if category in categories:
            return level
    return "L1_basic"


def infer_layer(feature_name: str) -> str:
    """欄名之管線層由身分之最外層 op 導出（`feature_naming.feature_layer`）；label ⇒ `label`；不合文法 ⇒ `unsupported`。"""
    identity, named = _identity(feature_name)
    if identity is None:
        return LABEL_LAYER if named == LABEL_CATEGORY else UNSUPPORTED
    return feature_layer_of(identity)
