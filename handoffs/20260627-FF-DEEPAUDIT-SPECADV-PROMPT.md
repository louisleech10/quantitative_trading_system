# 任務:adversarial 審 FF 深稽 SPEC + TODO(不同模型,作者不自審)

被審:`docs/FF_DEEPAUDIT_P0_SPEC.md` + `docs/FF_DEEPAUDIT_P0_TODO.md`。
依據:`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`(套用其全部檢查面向)。
背景(已雙戳記,設計基準):`handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md`。

你是 adversary,禁確認式放水。每 finding 附可證偽反例或真實程式路徑。重點挑戰:

1. **忠實度**:SPEC/TODO 是否忠實編碼已戳記 reconcile?有沒有偷偷弱化(warmup config-driven、columns gate、雙 oracle、mutation TDD-first、§B8、三方數據簽核)?有沒有掉項(reconcile 的 BLOCK 全進來了嗎)?
2. **可實作性**:`estimate_max_warmup_bars` 真實簽名對不對(實際讀 warmup_window.py)?`TALIB_INPUT_SEMANTICS` 表可建嗎?BUG-1「列所有舊欄名消費者同步點」——SPEC 有沒有真的指出那些消費者在哪(grep feature_storage/IC/ML),還是空話?
3. **測試假綠**:每個 mutation probe 的 patch 點具體嗎?C2-1 warmup 區間排除規則會不會仍掩蓋洩漏?BUG-1 golden「未受影響欄 byte 不變」如何界定受影響範圍?
4. **TODO 覆蓋**:9 個 Task 全覆蓋 SPEC?Batch 依賴拓撲對嗎(B1/B2 真能並行?)?
5. **遺漏的高風險**:有沒有 SPEC 沒接住的 (a)(d) 風險?

## 輸出
寫到 `handoffs/20260627-FF-DEEPAUDIT-SPECADV-<codex或composer>.md`:結論一行(可派實作/須修)+ BLOCK(問題+反例+修法)+ RISK/OK + 對 TODO 的具體補強。只寫你的 review 檔,不改 SPEC/TODO/repo 其他檔。
