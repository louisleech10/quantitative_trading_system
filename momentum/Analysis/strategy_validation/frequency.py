"""Task 1.1 — 年化頻率解析（單一來源）＋ bar 數→年數之唯一推導處。

SPEC ref：Task 1.1 ＋ A1-14（`available_years`）＋ **A1-19**（實作期之落點修正）。

🔴 **本檔為 re-export，canonical 實作住 `momentum/core/frequency.py`**：
TODO 字面把本函式放在本檔，但 Task 1.3 要求 `momentum/Strategy/vectorized_backtest.py` 呼叫它，
而解耦 scanner 判 `momentum/Strategy/` → `momentum/Analysis/` 為 **R2 跨域違規**（實跑 rc=1）。
`momentum.core.*` 為該檢查之豁免目標 ⇒ canonical 實作移至 core，本檔保留**逐字相同的 import 路徑與 API**
（三關與測試皆可續用 `from momentum.Analysis.strategy_validation.frequency import …`）。
詳見延伸檔 `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md` A1-19；B1 code review 須複核本決定。
"""

from __future__ import annotations

from momentum.core.frequency import (
    UnknownTimeframeError,
    available_years,
    resolve_periods_per_year,
)

__all__ = ["UnknownTimeframeError", "available_years", "resolve_periods_per_year"]
