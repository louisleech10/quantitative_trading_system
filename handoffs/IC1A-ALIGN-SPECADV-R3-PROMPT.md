# R3 增量閉合複驗:1-align SPEC/TODO v3(task-id: ic1a-align-specadv-r3)

v3 增量修 R2 Composer 的 STILL-OPEN + NEW-ISSUE:
- **D-4 index 同型化寫回**(SPEC §A):stage0/stage2 gate PASS 後 features+label index 實體寫回 DatetimeIndex(單一正規化點,值守恆 sha256,落盤 schema 不變);下游禁裸跨 dtype intersection/equals。
- **Task 2.4 修法**:交集前兩側同型化;features 收到 int64=上游繞過→raise;同型化後空交集才 raise。
- **Task 2.3**:混型同長→D-1 轉型比對;D-4 後混型=繞過→raise。
- §ADV-RESOLUTION typo(2.1→2.4)已更正。

檔:SPEC=docs/IC_PHASE1_1A_ALIGN_SPEC.md v3 / TODO=docs/IC_PHASE1_1A_ALIGN_TODO.md v3
你的 R2:handoffs/IC1A-ALIGN-SPECADV-R2-<你>.md

## 任務
- **Composer**:重跑你 R2 的兩個反例(int64∩datetime=∅ snippet / TypeError snippet)對照 v3 條文,判 ADV-COMPOSER-1A 與 NEW-ISSUE MAJOR 是否 CLOSED;D-4 是否引入新洞(特別想:寫回後有無 caller 依賴 int64 index 值本身?grep `\.index` 消費點)。
- **Codex**:v3 增量(D-4/2.4/2.3 改法)是否影響你 v2 APPROVE?有無新洞?
- 結論格式:`ID / CLOSED|STILL-OPEN|NEW-ISSUE / 依據`;結尾 `VERDICT: APPROVE|REJECT`;APPROVE 且同意凍結→另行輸出 `RECONCILE-STAMP APPROVED <你> 2026-07-08`。

## 產出
`handoffs/IC1A-ALIGN-SPECADV-R3-<codex|composer>.md`。只讀+寫自己輸出檔;不改生產 code/測試。
