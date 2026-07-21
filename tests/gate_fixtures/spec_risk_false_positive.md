# Probe SPEC — §RISK 干擾句 + RISK-HIT: none（ADV-P4 誤擋反例）

## §RISK
- **大小**：中。
- **命中高風險原則**：參見 (a) 原則（干擾句，非宣告）。
- | (a) | 否 |
- 可能命中 (d) 若改動 ML 路徑（敘述句，非宣告）。
- RISK-HIT: none

## §A
- **已確認**（2026-07-05 探針樣本）。
  - 低風險文檔不應被 NLP 誤強制 §G。
    FACT-RECEIPT: `echo low-risk-probe` → 印出 `low-risk-probe`（Composer 實跑 2026-07-05）
- **待使用者確認**：待確認：無

## §C
- 文檔 epic；不碰數值路徑。

## §G
- 自願 §G：exit 矩陣 diff；非 (a)/(d) 強制。

## §P
### Phase 1
**Task 1.1**
- **驗證**：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_risk_false_positive.md; echo $?` → 0。
- **邊界**：干擾句在 §RISK 內；宣告為 none。
- **存活至**：Phase 1 完工後保留（合規範例）。
- **覆蓋風險**：無。
- 不可做：不得改 RISK-HIT 為 a/d。

## §V
- 誤擋回歸探針。

## §R
- revert Task 2.2 NLP 嘗試。

## §N
- 無。
