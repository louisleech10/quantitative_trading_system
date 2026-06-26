# IC Phase 1 1-contract — SPEC Adversarial Review 派工指令

> 雙家族各獨立做一次（GPT-5.5 / Composer 2.5），不得互看、不得自審作者框架。
> 依 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md（V13）執行。

## 你要審的檔（全讀，讀不到要說，不得假裝讀過）
- SPEC：`docs/IC_PHASE1_CONTRACT_SPEC.md`
- Manifest（覆蓋對照）：`handoffs/20260625-ic-PHASE1-CONTRACT-MANIFEST.md`
- 白話背景：`handoffs/20260625-ic-PHASE1-BRIEF.md`
- 上游 Phase 計畫：`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`
- 範本（你要套的審查法）：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`

## 變數
- `{{SPEC_FILE}}` = docs/IC_PHASE1_CONTRACT_SPEC.md
- `{{TODO_FILE}}` = N/A（TODO 尚未生成，本輪只審 SPEC）
- `{{PLAN_FILE}}` = handoffs/20260624-ic-roadmap-phasing-CONVERGED.md
- `{{REVIEW_FOCUS}}` = 完整審查 + 特別聚焦下列「使用者點名的權衡」
- `{{STRICTNESS}}` = MAXIMUM

## 本任務必額外挑戰的點（使用者明示，非鐵則，請各自 brainstorm 反對/替代）
1. **[Q-1] artifact 格式**：SPEC 預設 HDF5。從「檔案大小 / 篩選效率 / 跨 hardware tier(8-32GB) 載入 / 量化業界慣例」挑戰 HDF5 vs parquet vs 其他。
2. **[Q-2] API 版本化**：SPEC 預設同 endpoint 加 schema_version 欄。挑戰「前端返工面 / 向後相容 / 是否該新 endpoint」。
3. **[Q-3] 舊 JSON 共存**：SPEC 預設漸進遷移。挑戰遷移風險 / 雙寫一致性。
4. **複用 ML 孤島 split() 的洩漏紅線 [C-3]**：SPEC 主張 per-symbol 套用既有 positional-index split 即可防跨 symbol 洩漏。**嚴格挑戰**：per-symbol 後在單 symbol 內，purge/embargo 的 positional 假設是否仍成立（時間是否真連續、有無 gap/缺漏 bar 使 positional purge 對不上時間）？這是 (d) 正確性紅線。
5. **行為不變宣稱 [§G]**：SPEC 主張「只加 contract surface、舊路徑數值 byte 級不變」。挑戰是否真有不經意改到既有計算路徑的風險。
6. **使用者點名的橫向考量**：數據品質 / 計算時間 / 計算穩定性 / 跨 hardware tier / 檔案大小 / 量化業界經驗標準——逐一檢查 SPEC 有無在這些面向留洞。

## 輸出
- 依範本 §輸出格式：Verdict + Findings（[BLOCKING|MAJOR|MINOR]+信心度+證據+怎麼失敗+修法）+ 被當成事實的未驗證假設。
- **GPT-5.5 寫到**：`handoffs/20260626-ic-PHASE1-CONTRACT-ADVERSARIAL-CODEX.md`
- **Composer 2.5 寫到**：`handoffs/20260626-ic-PHASE1-CONTRACT-ADVERSARIAL-CURSOR.md`
- 完成輸出 `STATUS: DONE`，BLOCKED 則 `STATUS: BLOCKED — <原因>`。
