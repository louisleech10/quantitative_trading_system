"""ICFIRSTALIGN Task 2.3 收據工具之分類可證偽（審碼 b2 r1 codex P2-01）：只認精確轉換，不以容差吸收漂移。

以真實 kline close（`icfirstalign_helpers.kline_close`）為值來源；不呼叫生成。
"""

from __future__ import annotations

import importlib.util

import numpy as np

from tests.feature_engineering import icfirstalign_helpers as h

_spec = importlib.util.spec_from_file_location("icfirstalign_preic_diff", h.REPO / "scripts" / "icfirstalign_preic_diff.py")
diff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diff)

CAP = 1e18


def _old() -> np.ndarray:
    """真實 close 之報酬（float32 可表示、在 float16 值域內）。"""
    close = h.kline_close().to_numpy(dtype=np.float64)[-301:]
    return (close[1:] / close[:-1] - 1.0).astype(np.float32).astype(np.float64)


def test_exact_float16_conversion_classified() -> None:
    old = _old()
    assert diff.classify("c", old, old.astype(np.float16).astype(np.float64), CAP) == "cgsa_storage_float16"


def test_one_ulp_float32_drift_is_unexplained() -> None:
    """codex 反例：首值改為下一個 float32 值（1 ULP）⇒ 非任何具名轉換之結果 ⇒ unexplained。"""
    old = _old()
    new = old.copy()
    new[0] = float(np.nextafter(np.float32(old[0]), np.float32(np.inf)))
    assert diff.classify("c", old, new, CAP) == "unexplained"


def test_nan_new_only_without_sanitize_source_is_unexplained() -> None:
    old = _old()
    new = old.copy()
    new[5] = np.nan  # 舊值有限且 ≤ cap ⇒ 非 numeric_sanitize
    assert diff.classify("c", old, new, CAP) == "unexplained"


def test_sanitize_exact_classified() -> None:
    old = _old()
    old[7] = np.inf
    new = old.copy()
    new[7] = np.nan
    assert diff.classify("c", old, new, CAP) == "numeric_sanitize"


def test_partial_sanitize_is_unexplained() -> None:
    """codex r2 反例：同欄 +inf、-inf、超 cap 各一，只淨化其一 ⇒ 不等於正式全欄淨化 ⇒ unexplained；全淨化 ⇒ 具名。"""
    old = _old()
    old[1], old[2], old[3] = np.inf, -np.inf, 5e18
    partial = old.copy()
    partial[1] = np.nan
    assert diff.classify("c", old, partial, CAP) == "unexplained"
    full = old.copy()
    full[[1, 2, 3]] = np.nan
    assert diff.classify("c", old, full, CAP) == "numeric_sanitize"
