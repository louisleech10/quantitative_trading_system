"""GAP-3 UX Task 2.1b — 由篩選條件導出答案窗下界（D-7 第 2 層）。

🔴 **本檔之 `depth_by_timeframe()` 是本批唯一 exported 深度函式**——
Task 1.9（B3，CSV 路徑）與 Task 4.1（B7，匯出端）皆呼叫它，禁各自實作。
第二份實作＝兩條路徑會各自演化，正是本 epic 要防的漂移。

深度公式（SPEC Task 2.1b；本批唯一權威定義）::

    depth(tf) = max( declared_window_bars[tf],
                     max over 所有**實際被引用**之欄位 c of bars_of(c, tf) )

    bars_of(c, tf) = registry 解析（bar 命名回根數；小時命名以 tf 換算，禁寫死常數）

    lookahead_bars_declared = { tf: depth(tf) for tf in 批內出現之 timeframe 集合 }

三個容易做錯的點，各有對應之 fail-closed：

1. 左項是 **`declared_window_bars[tf]`**，不是 `label_definition.window.horizon_bars`
   ——後者下限為 1，深度 0 時只是 serialization floor，直接當左項會把真實 0 讀成 1。
   缺該 tf 之鍵 ⇒ raise，**不得**以 1 或其他 tf 之值默認替代。
2. 輸出**逐 tf**：`bars_of` 本就 tf-parameterized（`future72_*` 在 1h 是 72 根、12h 是 6 根）
   ⇒ depth 亦逐 tf 不同，不得塌成單一 scalar。
3. **附帶欄不得納入 `max`**：只有「條件實際引用」之欄進來。附帶欄與 label 判定無關，
   納入會過度 purge 吃掉訓練樣本——保守過頭亦屬錯誤。此區分由呼叫端遵守，
   本函式只吃 `referenced_columns`。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from momentum.Analysis.event_samples.lookahead_registry import (
    load_lookahead_registry,
    resolve_lookahead_bars,
)


class UnresolvableLookaheadDepth(ValueError):
    """條件引用了深度不可由 registry 導出之欄位（fail-closed；交由 Task 1.11 之 L2 強制宣告）。"""


def depth_by_timeframe(
    referenced_columns: Iterable[str],
    declared_window_bars: Mapping[str, int],
    timeframes: Iterable[str],
    registry: Optional[Mapping[str, Any]] = None,
) -> Dict[str, int]:
    """回傳 `{tf: depth}`——答案窗下界，逐 tf 各求一次。

    Args:
        referenced_columns: 篩選條件**實際引用**之欄位（🔴 不含附帶欄）。
        declared_window_bars: 使用者宣告之答案窗根數，逐 tf（不含 floor）。
        timeframes: 批內出現過之 timeframe 集合。
        registry: 覆寫用（測試）；預設讀契約 SoT。

    Raises:
        KeyError: `declared_window_bars` 缺某個 tf 之鍵（fail-closed，不默認替代）。
        UnresolvableLookaheadDepth: 引用之欄位深度不可由 registry 導出。
    """
    r = registry if registry is not None else load_lookahead_registry()
    cols = [str(c) for c in referenced_columns]
    tfs = [str(tf) for tf in timeframes]

    depth: Dict[str, int] = {}
    for tf in tfs:
        if tf not in declared_window_bars:
            raise KeyError(
                f"declared_window_bars 缺 timeframe {tf!r}（fail-closed：不得以 1 或其他 tf 之值默認替代）"
            )
        declared = declared_window_bars[tf]
        if type(declared) is not int or declared < 0:
            raise ValueError(
                f"declared_window_bars[{tf!r}] 須為非負 int（bool 亦拒），實得 {declared!r}"
            )

        candidates = [declared]
        unresolved = []
        for c in cols:
            bars = resolve_lookahead_bars(c, tf, r)
            if bars is None:
                unresolved.append(c)
            else:
                candidates.append(bars)
        if unresolved:
            raise UnresolvableLookaheadDepth(
                f"timeframe {tf!r} 之下列引用欄深度不可由 registry 導出: {sorted(unresolved)}"
                "（依 D-7 走 Task 1.11 之 L2 強制宣告，本函式不猜）"
            )
        depth[tf] = max(candidates)

    return depth
