# FF-STAT SPEC v32 審查 r13 — 主委自審（獨立版，委員交件前寫成）

## CLAUDE-R13-P1-01

**斷言**: §C「逐欄穩定點」列舉之不傳遞 NaN 步驟類別（①固定窗不完整窗出值、②遞迴、③累積／expanding）漏「逐點運算而對 NaN 輸入給有限值」一類；預設啟用之 L2 `binary_signal` 屬之，照現條文實作後其輸出於 L1 遮罩列為 0（有限值），違反 R1「每欄第一個輸出值須已穩定」。

**碼證**: `config/scan_config.yaml:519-530` 預設啟用 binary_signal（RSI > 70、RSI < 30、ADX > 25）；`compute_binary_signal` 以比較後 `astype(int)`，NaN 比較為 False ⇒ 0。
CODE-ANCHOR: momentum/FeatureEngineering/operators/derived_operators.py:433
MUTATION: 照 v32 條文實作而不對 binary_signal 另遮 ⇒ §G ⑦ 之 B run 於 RSI 遮罩列輸出 0、A run 同一時點 RSI 已穩定可為 1 ⇒ 對證紅；即 SPEC 可證偽，但條文未給處置類別。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2

正文：修法——增第④類「逐點而對 NaN 給有限值 ⇒ 輸出沿用輸入之 NaN（任一輸入為 NaN 之列設 NaN）」，列 binary_signal 為已知成員。可行性：`compute_binary_signal` 之輸入 series 可得，`mask.astype(int).where(series.notna())` 即達成（pandas 語意確定，輸出 dtype 轉 float）。

## CLAUDE-R13-P2-02

**斷言**: L6 `consensus_features` 之 divergence 為第④類（`(sign_price * sign_volume < 0).astype(float)`）；其輸入若含 L1 遮罩欄，遮罩列為 0。盤點收據須列其輸入來源與處置。

**碼證**: momentum/FeatureEngineering/meta_features/consensus_features.py:91

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2

正文：輸入若只來自原始 OHLCV（未遮罩）則無影響；須於盤點收據實證。

## CLAUDE-R13-P2-03

**斷言**: `operators/state_counters.py`（cross_count 等計數語意「無 ⇒ 0」、warmup 以絕對列 t < lookback 計而非輸入首個有效值）不傳遞 NaN，但無生成路徑呼叫者；盤點收據須標「不在生成路徑」而非漏列。

**碼證**: `grep -rn OperatorRegistry momentum api` 只命中 `operators/operator_registry.py` 與 `operators/__init__.py`；momentum/FeatureEngineering/operators/state_counters.py:67

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2

正文：若日後接入生成路徑即屬第①類（計數窗含遮罩列）。

## CLAUDE-R13-P3-04

**斷言**: 進階 atomic（microstructure）多處 `fillna(0.0)` 使其 origin＝第 0 列；屬 L1、受 L1 遮罩覆蓋，前提是 Task 2.4 量得之 K 涵蓋 fillna 造成之偏差。

**碼證**: momentum/FeatureEngineering/atomic/microstructure_indicators.py:173、179、192、213、264-268

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2

正文：量測以對無限歷史之收斂判準，應可涵蓋；列入 Task 2.4 量測對象即可，無需改條文。

## 必答（主委自答）
1. R1–R7 落實：R1（§C 公開域預熱、刪開關）、R3（逐欄穩定點、不切齊）、R4（Task 2.4 量一次）、R5（倍數表完整性）、R6（縮尾遮罩）、R7（§N）皆有條文；R2 為排程，無條文需求。
3. assumed 一（除縮尾外皆傳遞 NaN）：**不成立**——binary_signal、consensus divergence（P1-01、P2-02）。assumed 二：未找到反例（窗內輸入皆穩定之列不受遮罩影響），但 binary_signal 於遮罩修正前違反。
5. NaN 傳遞 vs 逐欄血緣：NaN 傳遞以計算本身推出穩定點，新特徵只要傳遞 NaN 即自動成立；弱點是「不傳遞 NaN 之步驟」須盤點——範圍只列例外，小於血緣法之逐層登記。§G ⑦ 對兩法皆為終審。

VERDICT: blocked
BLOCKED-BY: CLAUDE-R13-P1-01
CLOSED: none

STATUS: DONE
