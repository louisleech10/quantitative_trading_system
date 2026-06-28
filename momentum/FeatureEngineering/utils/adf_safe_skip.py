"""ADF / Fracdiff safe-skip whitelist。

對「數學上嚴格 I(0)」的欄位 bypass ADF 測試，直接判定 I(0) → 不執行 fracdiff。

依據（詳見 docs/NAN_REDUCTION_STRATEGY.md §4.5）：
    (a) 嚴格有界：公式硬限取值範圍 → 數學上不可能有單位根 → 必為 I(0)
    (b) 數學差分 / 共整合差：構造上即為 I(0)（差分 I(1) 給 I(0) 是定義）

為何需要 safe-skip：
    1. 省 ADF CPU：對數十萬個已知 I(0) 欄位重複跑 ADF 是純浪費
    2. 跨 symbol 一致性：ADF 在 finite sample 偶會 false-positive，導致同名特徵
       在不同 symbol 被處理到不同空間（fracdiff vs raw），破壞 IC 可比性

不加入 whitelist 的指標（保留 ADF 測試）：
    - CCI: 公式中 0.015 是 normalize const 非 bound，實測偶超 ±400
    - STDDEV / VAR / BETA / Beta-CloseVolume: 統計估計，regime change 時可 spike
    - LINEARREG_SLOPE / LINEARREG / LINEARREG_INTERCEPT / TSF: I(1) 或 borderline
    - TRANGE / ATR / Parkinson_Vol / GarmanKlass_Vol: I(1) 量級，**該執行 fracdiff**
    - HT_DCPERIOD / HT_PHASOR: 實務有界但無數學硬限
    - PLUS_DM / MINUS_DM: per-bar 方向動量，無硬限
    - ADOSC / Force_Index / Klinger / Ease_of_Movement / Volume_MA_Ratio: 衍生 oscillator
"""

from __future__ import annotations

from typing import Iterable, Sequence


# ─── 數學上嚴格 I(0) 欄位的 substring pattern ───
# Column 命名慣例（已對照真實 catalog 驗證 2026-05-28）：
#   {source}_{tf}_{category}_{indicator}_{params}[_derivation]
#   - 單組件指標用 underscore 包夾：`_RSI_`, `_MOM_`
#   - **多組件指標用 hyphen**：`MACD-Line`, `HT-DCPHASE`, `STOCH-slowk`,
#     `AROON-aroonup`, `LINEARREG-ANGLE`, `PLUS-DI`
#   - L2 Cross 是 suffix：`..._5_20_Cross`（無 trailing underscore）
ADF_SAFE_SKIP_PATTERNS: frozenset[str] = frozenset({
    # ── L1 嚴格有界振盪器 (a) ─────────────────────────────────
    "_RSI_",
    "_ADX_",
    "_ADXR_",
    "_DX_",
    "_WILLR_",
    "_MFI_",
    "AROON-aroonup",       # hyphen
    "AROON-aroondown",     # hyphen
    "_AROONOSC_",
    "_ULTOSC_",
    "STOCH-slowk",         # hyphen
    "STOCH-slowd",         # hyphen
    "STOCHF-fastk",        # hyphen
    "STOCHF-fastd",        # hyphen
    "STOCHRSI-fastk",      # hyphen
    "STOCHRSI-fastd",      # hyphen
    "_BOP",
    "_CORREL_",
    "Correl-CloseVolume",
    "_CMO_",
    "LINEARREG-ANGLE",     # hyphen
    "PLUS-DI",             # hyphen
    "MINUS-DI",            # hyphen
    # ── L1 normalized (a) ─────────────────────────────────────
    "_NATR_",
    # ── L1 一階差分 / 共整合差 (b) ─────────────────────────────
    "_MOM_",
    "_ROC_",
    "_ROCP_",
    "_ROCR_",
    "_ROCR100_",
    "_TRIX_",
    "MACD-Line",           # hyphen
    "MACD-Signal",         # hyphen
    "MACD-Hist",           # hyphen
    "MACDEXT-Line",        # hyphen
    "MACDEXT-Signal",      # hyphen
    "MACDEXT-Hist",        # hyphen
    "MACDFIX-Line",        # hyphen
    "MACDFIX-Signal",      # hyphen
    "MACDFIX-Hist",        # hyphen
    "_APO_",
    "_PPO_",
    # ── L1 binary / sinusoid (a) ─────────────────────────────
    "HT-TRENDMODE",        # hyphen
    "HT-SINE",             # hyphen（涵蓋 HT-SINE-LeadSine 的 sine + leadsine）
    # ── L2 構造性離散 / 有界 (a) ──────────────────────────────
    "_Cross",              # suffix（無 trailing underscore）
    "_BinarySignal_",
    "_Sign_",
    "_TsRank_",
    "_TsArgMax_",
    "_TsArgMin_",
    "_TsCorr_",
})


def is_safe_skip(
    column_name: str,
    enabled: bool = True,
    additional_patterns: Sequence[str] = (),
    exclusion_patterns: Sequence[str] = (),
) -> bool:
    """判斷某欄位是否可 bypass ADF 測試直接視為 I(0)。

    Args:
        column_name: 待判斷的欄位名稱
        enabled: 是否啟用 safe-skip；False 時直接回傳 False（等同 no-op）
        additional_patterns: 使用者額外擴增的 skip pattern
        exclusion_patterns: 強制讓某些 whitelist 命中項回到 ADF 測試（debug 用）；
            exclusion 優先於 whitelist 與 additional

    Returns:
        True = 可 skip（該欄位為 I(0)，不需 ADF / fracdiff）
        False = 需正常跑 ADF
    """
    if not enabled:
        return False
    # I-1: exclusion 最高優先
    for excl in exclusion_patterns:
        if excl and excl in column_name:
            return False
    # I-2: 內建 whitelist
    for pat in ADF_SAFE_SKIP_PATTERNS:
        if pat in column_name:
            return True
    # I-3: 使用者擴增 pattern
    for pat in additional_patterns:
        if pat and pat in column_name:
            return True
    return False


def filter_safe_skip(
    columns: Iterable[str],
    enabled: bool = True,
    additional_patterns: Sequence[str] = (),
    exclusion_patterns: Sequence[str] = (),
) -> tuple[list[str], list[str]]:
    """對 columns 做 safe-skip 過濾。

    Returns:
        (needs_adf, skipped)
            needs_adf: 仍需跑 ADF 測試的欄位 list（保留原順序）
            skipped:   被 bypass 的欄位 list（保留原順序）
    """
    needs_adf: list[str] = []
    skipped: list[str] = []
    for col in columns:
        if is_safe_skip(col, enabled, additional_patterns, exclusion_patterns):
            skipped.append(col)
        else:
            needs_adf.append(col)
    return needs_adf, skipped
