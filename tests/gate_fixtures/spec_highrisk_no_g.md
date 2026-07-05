# Probe SPEC — 高風險 §G:N/A 繞過（Composer C-3 / U2）

## §RISK
- **大小**：大。
- **命中高風險原則**：(a) 數值正確性；(d) ML 路徑。
- RISK-HIT: a, d

## §C
- 不弱化 NaN·inf gate；不 fake 資料。

## §P
### Phase 1 — 探針（依賴：無）
**Task 1.1 — §G 逃脫**
- 目標：§N 標 §G N/A 仍 PASS（現行繞過）。
- **驗證**：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_highrisk_no_g.md; echo $?` → 0。
- **邊界**：無 `## §A` 段時 W1 跳過。
- 不可做：不得填真 §G。

## §V
- 行為 golden 探針。

## §R
- revert。

## §N
- §G：N/A — 探針故意用 §N 豁免高風險 Golden（現行機檢漏洞）。
