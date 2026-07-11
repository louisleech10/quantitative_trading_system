# Handoff
**Agent**: Claude | **Time**: 2026-07-11 | **Branch**: main

## ✅ P2 債前置:文件同步稽核完成(task p2debt-docsync)
- Claude 自產+Grok/Composer/Codex 三腿委員審;reconcile=handoffs/P2DEBT-DOCSYNC-RECONCILE.md;HANDOFF/ROADMAP/CLAUDE.md 已同步(9 處修正)。
- **新制度(使用者 2026-07-11)**:每次開 session 先稽核 HANDOFF+相關文件 vs repo 實況再開工(已入 CLAUDE.md)。
- golden 4 檔(tests/golden/ic_phase1_1a_cut1/)**2 BLOCK 不入版**,留 working tree,拆票 5;綁定項見 reconcile 裁決二。

## ★★ 當前 session = P2 債五票(獨立票,逐項閉合;分工=四調行 ORCH §1;Grok 記分照跑)
1. governance 9 紅:tests/governance b4×3+b5×5+redteam r7——7/5 制度強化(template_check 3edfa6c 等)後 fixture 過期斷言舊行為;修法=遷移 fixture 至現行檢查器語意,**禁放鬆檢查器換綠**。
2. legacy 測試寫 data_cache:1a cut1 等走真 service 路徑覆寫 data_cache 衍生檔;修法=測試輸出 tmp redirect(參考 1e+1b capture persist patch);出處=IC1EB-B3-REVIEW-R3-codex.md。
3. tsc 既存 errors:frontend feature-factory 測試檔全部既存型別錯誤(2026-07-11 實測 11,勿釘死數字)。
4. codex 沙箱間歇卡死(觀察債):CLI 0.144.1 蒐證(復現條件/頻率)→回報 OpenAI 或固化繞法入 ORCH;p2debt-docsync 補腿一次正常完成=樣本 1。
5. 1a cut1 golden provenance 閉合(新,2 BLOCK 拆票):恢復+改寫 rebaseline_* 審計欄(留 1-align B2 史+2026-07-11 unlock 鏈)/reuse guard fail-closed 校驗+generator 測試/獨立重放 receipt 禁現綠自證/payload 處置寫死;與票 2 相鄰施工;閉合須 Grok+Codex 複驗(§B8)。

### 之後 session = ROADMAP ③ 1c Net IC 量綱(大,完整管線)
- 病灶:net_ic_analyzer.py:34 IC(無量綱)減交易成本(報酬率量綱)。前置=P2 債完成。
- **facts-asked 預登記(1c SPEC 時必問使用者,禁提前假設)**:①成本來源=輸入/預設/費率表?②要不要免成本對照模式?③成本率 UI 入口與預設值。

### RULEIMPL(park 於 R5,2026-07-11;本檔舊 R3 記載已收斂於此)
定稿=RULEIMPL-SPEC-DRAFT-R5.md;grok R5 PASS;codex R5 殘 4 條=正式化時綁定項(cutoff full-SHA/base fallback/digest exclusion/sidecar 自參照)。正式化→逐項落值→codex 終驗→再派工。

## 鐵律(不變)+新教訓
- 審查用 --risk low --template "n/a:";實作 --risk high 附三件;codex exec 接 </dev/null;register-output;10 分鐘回報;執行端產物不可信;baseline 唯讀;golden 產物須入版或外部雜湊。
- 新:untracked 計數依快照時點浮動,清單列檔名不釘數字;「suite 現綠」不能自證 golden 世代正確(codex/grok 一致)。
- 未 commit 殘留:.claude/settings.json(使用者本機)+golden 4 檔(票 5 前不動)。
