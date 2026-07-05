# Handoff
**Agent**: Claude | **Time**: 2026-07-05 | **Branch**: main

## ★制度層總審查 epic — Phase A(憲法重構+合約補齊)✅ 完成待 commit

### 本 session 完成(走完整大任務管線,全程機檢+雙家族+code review)
- **SPEC/TODO**:`docs/INSTREV_PHASEA_{SPEC,TODO}.md`(template+coverage 三道機檢過)+ 簡述/manifest `handoffs/20260705-INSTREV-PHASEA-BRIEF-MANIFEST.md`(16 個 [A-x])。
- **雙家族 adversarial**:Codex 3 + Composer 12 findings(含 2 BLOCKING)→ reconcile `handoffs/20260705-INSTREV-PHASEA-ADV-RECONCILE.md`;R1 雙 REJECTED(抓 SPEC 落後 TODO 的選層對調)→ 修 → **R2 雙戳記 APPROVED**(sha256:6a14a0f6)。
- **實作**(Composer 2.5)+ **Codex code review** 抓 2 BLOCKING(ORCH §6/§7 殘留 Codex 主力預設、CLAUDE 三方鐵律 token 在但義務被壓掉)→ Composer 修 → **Codex 閉合重驗雙 CLOSED**。
- **成果**:copilot 739→8 行 pointer;CLAUDE.md 216→128 行(敘事移 `docs/SCAR_LEDGER.md`,規則零刪減 grep 驗);任務分派決策表單一化;選層 ORCH §1 單一「現行分工行」(動態,現行=**Composer 實作+Codex review**,07-05 額度切換);合約補 5 項制度;輪詢 10 分鐘、debug 2 輪(含 BOOTSTRAP);ARCH/DEV banner。
- **記憶層(Phase 6,Claude 自做)**:feedback_task_routing 標 SUPERSEDED、dispatch_polling 改 pointer、executor_override 更新現行分工、MEMORY.md 索引同步。

### 驗收(Claude 獨立跑,不採信執行端 STATUS)
- postflight data_cache 完整未縮減;sync check ✅;CLAUDE 128/copilot 8 行;3輪·5分鐘 全 repo 清零;現行分工錨點=1;零刪減 12 token + 合約 A-12 token 全在;敘事負向核對乾淨。

### 下一步
1. **commit + push**(本次即將做)。
2. **Phase B(腳本,中風險)**:U-9 sync 重構(加 A-12 token 到 CONTRACT_TOKENS)、U-12 gate DENY 落 audit、U-14 claim auto-fix、U-15 錯誤訊息模板。
3. **Phase C(觀察)**:U-13 批次戳記慣例、U-20/21 證據累積。
4. 之後才回 IC Analysis(前置=使用者手動生成 FF 測試資料;ROADMAP P0 IC 節)。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員派工帶 --task-id+--output,產出後 register-output。
- pre-existing 失敗=test_ic_engine。執行端可能誤還原根 HANDOFF——commit 前重驗內容。
