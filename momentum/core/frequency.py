"""timeframe → 每年期數／bar 數 → 年數之 **canonical 實作**（唯一定義處）。

出處：GAP-1 Task 1.1（`docs/GAP1_STRATEGY_OVERFIT_TODO.md` FROZEN R3）。

🔴 **為何住在 `momentum/core/` 而非 TODO 字面所寫的 `momentum/Analysis/strategy_validation/`**
（實作期發現之衝突，記於延伸檔 A1-19；B1 code review 須複核）：
Task 1.3 要求 `momentum/Strategy/vectorized_backtest.py` 呼叫本函式，而
`scripts/check_decoupling_imports.py` 判 `momentum/Strategy/` → `momentum/Analysis/` 為
**R2 跨域違規**（實跑 rc=1，2 筆 NEW）。`momentum.core.*` 與 `momentum.factories` 為該檢查之
豁免目標（`_is_exempt_target`）⇒ 本函式（純常數推導、無領域邏輯、TIMEFRAME_SECONDS 亦住 core）
放 core 才同時滿足「單一來源」與 canonical Rule 2。
`momentum/Analysis/strategy_validation/frequency.py` **re-export** 本模組，
故 TODO 所寫之 import 路徑與 API 逐字仍成立。
"""

from __future__ import annotations

from momentum.core.constants import TIMEFRAME_SECONDS

_SECONDS_PER_YEAR = 365 * 24 * 3600


class UnknownTimeframeError(ValueError):
    """timeframe 不在 `TIMEFRAME_SECONDS` 之內（fail-closed，禁回預設值）。"""


def resolve_periods_per_year(timeframe: str) -> int:
    """由 timeframe 推導每年期數；未知一律 raise（**不**回 730）。

    Args:
        timeframe: `TIMEFRAME_SECONDS` 之鍵（大小寫敏感，不做正規化／別名）。

    Returns:
        每年期數（整數）。

    Raises:
        UnknownTimeframeError: 非字串、空字串、或不在對照表內（含 `"1H"` 這類大小寫變體）。
    """
    if not isinstance(timeframe, str) or timeframe not in TIMEFRAME_SECONDS:
        raise UnknownTimeframeError(f"unknown timeframe: {timeframe!r}")
    return round(_SECONDS_PER_YEAR / TIMEFRAME_SECONDS[timeframe])


def available_years(*, n_bars: int, timeframe: str) -> float:
    """bar 數 → 年數之**唯一**推導處（Task 1.4 與 §V 反向測試皆須呼叫本函式）。

    Args:
        n_bars: bar 數（>= 0）。
        timeframe: 見 `resolve_periods_per_year`。

    Returns:
        年數（float）。

    Raises:
        UnknownTimeframeError: timeframe 未知。
        ValueError: `n_bars` 非整數或為負（把 bar 數當年數之取巧由 §V-15 mutation 鎖住）。
    """
    if isinstance(n_bars, bool) or not isinstance(n_bars, int):
        raise ValueError(f"n_bars must be int, got {type(n_bars).__name__}")
    if n_bars < 0:
        raise ValueError(f"n_bars must be >= 0, got {n_bars}")
    return n_bars / resolve_periods_per_year(timeframe)
