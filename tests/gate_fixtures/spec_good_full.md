# Probe SPEC — 合規正樣本（FACT-RECEIPT + RISK-HIT + §G）

## §RISK
- **大小**：中。
- **命中高風險原則**：(b) 共用路徑；(c) 多 phase。
- RISK-HIT: b,c

## §A
- **已確認**（2026-07-05 使用者：探針合規樣本用）。
  - template_check.sh 對本檔預期 exit 0。
    FACT-RECEIPT: `bash scripts/template_check.sh spec tests/gate_fixtures/spec_good_full.md; echo $?` → 印出 `0`（Composer 實跑 2026-07-05）
- **待使用者確認**：待確認：無

## §C
- 只加強機檢；不碰 momentum/api。

## §G
- baseline：`diff tests/gate_fixtures/EXPECTED.txt tests/gate_fixtures/AFTER.txt` → exit 0；sha256 對照矩陣。

## §P
### Phase 1 — 正樣本（依賴：無）
**Task 1.1 — 合規探針**
- 目標：全錨點 + receipt。
- **驗證**：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_good_full.md; echo $?` → 0。
- **邊界**：含嚴格已確認 + FACT-RECEIPT。
- **存活至**：Phase 1 完工後保留（合規範例）。
- **覆蓋風險**：無。
- 不可做：不得刪 §G。

## §V
- fixture 矩陣；`bash scripts/test_template_check.sh` exit 0（Phase 2 後）。

## §R
- revert Phase commit。

## §N
- 無。
