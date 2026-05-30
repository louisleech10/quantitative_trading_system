"""Cascade categorical blacklist。

阻斷「計算本身錯誤」的下游 derivation（rolling/diff/lag/distance/ratio 等）：
    - CDL Pattern：97% 為 0 的稀疏離散值 → 衍生 ≈ 全零 / 無意義
    - HT_DCPHASE：0-360° 循環值在翻轉處（359→1°）算出**錯誤值**（(359+1)/2=180）

L1 原始欄位**保留**於最終 feature store（供 IC Gatekeeper 評估 raw 信號）；
被攔的只是它們的下游 derivation。

詳見 docs/NAN_REDUCTION_STRATEGY.md §5.1。
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


# ─── TA-Lib 全部 61 個 CDL Pattern 指標名稱（來自 scan_config.yaml pattern 段）
CDL_PATTERN_NAMES: frozenset[str] = frozenset({
    "CDL2CROWS",
    "CDL3BLACKCROWS",
    "CDL3INSIDE",
    "CDL3LINESTRIKE",
    "CDL3OUTSIDE",
    "CDL3STARSINSOUTH",
    "CDL3WHITESOLDIERS",
    "CDLABANDONEDBABY",
    "CDLADVANCEBLOCK",
    "CDLBELTHOLD",
    "CDLBREAKAWAY",
    "CDLCLOSINGMARUBOZU",
    "CDLCONCEALBABYSWALL",
    "CDLCOUNTERATTACK",
    "CDLDARKCLOUDCOVER",
    "CDLDOJI",
    "CDLDOJISTAR",
    "CDLDRAGONFLYDOJI",
    "CDLENGULFING",
    "CDLEVENINGDOJISTAR",
    "CDLEVENINGSTAR",
    "CDLGAPSIDESIDEWHITE",
    "CDLGRAVESTONEDOJI",
    "CDLHAMMER",
    "CDLHANGINGMAN",
    "CDLHARAMI",
    "CDLHARAMICROSS",
    "CDLHIGHWAVE",
    "CDLHIKKAKE",
    "CDLHIKKAKEMOD",
    "CDLHOMINGPIGEON",
    "CDLIDENTICAL3CROWS",
    "CDLINNECK",
    "CDLINVERTEDHAMMER",
    "CDLKICKING",
    "CDLKICKINGBYLENGTH",
    "CDLLADDERBOTTOM",
    "CDLLONGLEGGEDDOJI",
    "CDLLONGLINE",
    "CDLMARUBOZU",
    "CDLMATCHINGLOW",
    "CDLMATHOLD",
    "CDLMORNINGDOJISTAR",
    "CDLMORNINGSTAR",
    "CDLONNECK",
    "CDLPIERCING",
    "CDLRICKSHAWMAN",
    "CDLRISEFALL3METHODS",
    "CDLSEPARATINGLINES",
    "CDLSHOOTINGSTAR",
    "CDLSHORTLINE",
    "CDLSPINNINGTOP",
    "CDLSTALLEDPATTERN",
    "CDLSTICKSANDWICH",
    "CDLTAKURI",
    "CDLTASUKIGAP",
    "CDLTHRUSTING",
    "CDLTRISTAR",
    "CDLUNIQUE3RIVER",
    "CDLUPSIDEGAP2CROWS",
    "CDLXSIDEGAP3METHODS",
})


def _matches_cdl_pattern_all(column_name: str) -> bool:
    """Column name 是否含任一 CDL pattern 名稱？"""
    for cdl in CDL_PATTERN_NAMES:
        if cdl in column_name:
            return True
    return False


def expand_blacklist_patterns(
    patterns: Iterable[str],
    columns: Iterable[str],
) -> frozenset[str]:
    """展開 pattern aliases 到實際命中 columns 中的具體欄位名稱集合。

    支援的 alias：
        - 'CDL_PATTERN_ALL'：命中任何含 CDL_PATTERN_NAMES 中名稱的欄位
        - 'HT_DCPHASE'：命中任何含 'HT_DCPHASE' substring 的欄位

    其他 pattern 走通用 substring match。

    Args:
        patterns: 黑名單 pattern 列表
        columns: 待過濾的欄位名稱列表

    Returns:
        frozenset[str]：命中的具體欄位名稱（columns 子集）
    """
    cols_list = [str(c) for c in columns]
    if not cols_list:
        return frozenset()
    pattern_list = [str(p) for p in patterns if p]
    if not pattern_list:
        return frozenset()

    matched: set[str] = set()
    for pat in pattern_list:
        if pat == "CDL_PATTERN_ALL":
            for col in cols_list:
                if _matches_cdl_pattern_all(col):
                    matched.add(col)
        else:
            # 通用 substring match（涵蓋 'HT_DCPHASE' 與使用者自訂 pattern）
            for col in cols_list:
                if pat in col:
                    matched.add(col)
    return frozenset(matched)


def strip_blacklisted(
    df: pd.DataFrame,
    blacklist_cols: Iterable[str],
) -> pd.DataFrame:
    """從 df 移除 blacklist_cols 中的欄位。純函式、idempotent。

    Args:
        df: 待清理的 DataFrame
        blacklist_cols: 欲剝離的欄位名稱集合

    Returns:
        新 DataFrame；欄位順序保持 input 相對順序；不存在的欄位安全忽略
    """
    if df is None or df.empty or len(df.columns) == 0:
        return df
    blacklist_frozen = frozenset(str(c) for c in blacklist_cols)
    if not blacklist_frozen:
        return df
    cols_to_drop = [c for c in df.columns if str(c) in blacklist_frozen]
    if not cols_to_drop:
        return df
    return df.drop(columns=cols_to_drop)
