# Probe SPEC — 已驗證事實繞過 FACT-RECEIPT（Composer C-2 / template-review）

## §RISK
- **大小**：中。
- **命中高風險原則**：不命中 (a)/(d)。
- RISK-HIT: none

## §A

### 已驗證事實（附驗證方式）
- raw_data.index 是 DatetimeIndex，timestamp 欄 dtype 為 int64 秒級。

### 待使用者確認
- 待確認：無

### 已確認結果
- 探針用空殼標題滿足 facts-resolved。

## §C
- 約束：`grep -r "from api\." momentum/` → 0。

## §G
- 行為 golden：`bash scripts/template_check.sh spec <f>; echo $?` == 0（修前繞過）。

## §P
### Phase 1 — 探針（依賴：無）
**Task 1.1 — 繞過探針**
- 目標：重現現行機檢 PASS。
- **驗證**：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_verified_bypass.md; echo $?` → 0。
- **邊界**：§A 子標題承載 fact bullet，避開「已確認」行級 receipt 觸發（Task 2.1）。
- 不可做：不得附 FACT-RECEIPT。

## §V
- 測試：exit == 0 為現行 baseline 事實。

## §R
- revert Phase 2 commit。

## §N
- 無。
