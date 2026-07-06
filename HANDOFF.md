# Handoff
**Agent**: Claude | **Time**: 2026-07-06 | **Branch**: main

## ★制度層總審查 epic — Phase B(治理腳本補強)✅ 完成待 commit

### 本 session 完成(走完整中任務管線,全程機檢+adversarial+雙戳記+閉合重驗)
- **SPEC/TODO**:`docs/INSTREV_PHASEB_{SPEC,TODO}.md`(中,RISK-HIT: b;template_check PASS)。
- **adversarial**:Codex 8 findings(2 BLOCKING+4 MAJOR+2 MINOR,REJECT)→ 全數 ACCEPTED+SPEC/TODO 逐項修訂 → Codex 閉合重驗 8 findings 全 CLOSED。reconcile 雙戳記(sha256:1e919edd,`reconcile_stamps_check` 為權威)。
- **實作**(Composer)+ **Codex code review**(3 findings,APPROVE-WITH-FIXES)→ Composer 修 → 閉合重驗 REVIEW-2/3 CLOSED、REVIEW-1(pre-existing checker 非UTF-8 crash,折入修)再修 → Codex 最終 REVIEW-1 CLOSED。
- **成果(四 Task)**:U-9 `check_agent_contract_sync.sh` 兩層(CONTRACT_REQUIRED/PLANNER_REQUIRED)+選層單一來源反向檢查+A-12 新 token;U-12 `gate_check.sh` DENY(no_fresh_token/token_expired)落 audit.log(護欄 `||true` 保 exit 2);U-14 `pre-commit` index-only 尾空白 auto-fix(排除 fenced/hard-break/表格,binary-safe)+checker 缺 backing 提示;U-15 `gate.sh` 用法模板+新 `scripts/dispatch.sh`(碰撞 fail-closed+透傳)。
- **驗收(Claude 獨立跑)**:governance 140 passed/9 pre-existing failed(stash 確認非本批,舊 spec/fixture 不符演進規則);既有 `test_verify_gate*.py` 斷言 0 改動(防假綠);sync check exit 0;U-9 反向檢查/U-12 DENY 留痕 falsifiability spot-check 過;postflight data_cache 完整;CLAUDE.md 乾淨。

### 踩坑(執行端越權)
- Composer 於 impl 輪對 `.claude/gate/audit.log` 跑 `git checkout` 清測試污染,連帶移除 RECSTAMP 的 committee_dispatch,使 reconcile provenance 暫時對不上;處置=重跑 gate 派工補回該審計事件(harness task 輸出可稽核)。後續派工明禁 `git checkout` tracked 檔。

### 下一步
1. **commit + push**(本次即將做)+ 更新 ROADMAP。
2. **技術債另記**:governance 9 pre-existing 紅(b4/b5/r7:舊 spec/fixture 不符演進後 template_check/D-1/provenance)—與 Phase B 無關,擇期清。
3. **Phase C(觀察)**:U-13 批次戳記慣例、U-20/21 證據累積。之後回 IC Analysis(前置=使用者手動生成 FF 測試資料)。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員派工帶 --task-id+--output,產出後 register-output。
- 執行端產物不可信;接回只讀 diff+測試+摘要,diff 既有測試斷言防假綠;**執行端不得 git checkout tracked 共用檔**。
