# Handoff
**Agent**: Claude | **Time**: 2026-07-11 | **Branch**: main

## ✅ P2 債票 1 閉合:governance 9 紅 → 0(task p2debt-t1,完整中型管線)
- 管線:Composer SPEC 初稿→grok+codex R1 雙 BLOCK(fact-scope 假綠+可證偽缺口)→R2/R3 閉合雙 STAMP→TODO R1-R4(B3 兩輪未閉**斷路器換手** codex 改 comm -13)→正式化 docs/P2DEBT_T1_GOVFIX_{SPEC,TODO}.md 機檢 PASS→reconcile v2 雙戳→codex 實作→grok+composer 雙審 APPROVE。
- 根因與修法:gate.sh D-1 `Verdict` 大小寫敏感+template_check(f5850c6,非 3edfa6c)RISK-HIT/canonical fact-scope 錨點;fixture 遷移+B 案補 docs/VERIFY_GATE_SPEC.md 錨點+3 顆新可證偽負例;scripts/ 零改動。
- 驗收:`venv/bin/python -m pytest tests/governance -q`=**151 passed 0 failed** VERIFY:20260711T070840Z-p2debt-t1-impl-final(Claude/grok/composer 三方各自複跑一致);scope gate delta=4 白名單檔+4 合約產物,零越界。
- 審計鏈:handoffs/P2DEBT-T1-*(全 register-output);docsync 前置=handoffs/P2DEBT-DOCSYNC-RECONCILE.md。

## ★★ 當前 session = P2 債餘四票(獨立票,逐項閉合;分工=四調行 ORCH §1)
2. legacy 測試寫 data_cache:1a cut1 等走真 service 路徑覆寫 data_cache 衍生檔;修法=測試輸出 tmp redirect(參考 1e+1b capture persist patch);出處=IC1EB-B3-REVIEW-R3-codex.md。
3. tsc 既存 errors:frontend feature-factory 測試檔全部既存型別錯誤(2026-07-11 實測 11,勿釘死數字)。
4. codex 沙箱間歇卡死(觀察債):CLI 0.144.1 蒐證→回報 OpenAI 或固化繞法入 ORCH;**本 session 新樣本 4 起**:TODO 複驗 template_check replay hang×2、實作 scope gate comm/sort/diff hang×2(見 P2DEBT-T1-{TODO-REVERIFY,IMPL-RESULT}-codex.md);另 docsync 補腿+實作主體正常=卡死集中在管線外圍 shell 命令。
5. 1a cut1 golden provenance 閉合(2 BLOCK 拆票):恢復+改寫 rebaseline_* 審計欄/reuse guard fail-closed 校驗+generator 測試/獨立重放 receipt 禁現綠自證/payload 處置寫死;與票 2 相鄰施工;閉合須 Grok+Codex 複驗(§B8)。
- 新制度(使用者 2026-07-11):開 session 先稽核 HANDOFF+相關文件 vs repo 實況再開工(已入 CLAUDE.md)。

### 之後 session = ROADMAP ③ 1c Net IC 量綱(大,完整管線)
- 病灶:net_ic_analyzer.py:34 IC(無量綱)減交易成本(報酬率量綱)。前置=P2 債完成。
- **facts-asked 預登記(1c SPEC 時必問使用者,禁提前假設)**:①成本來源=輸入/預設/費率表?②要不要免成本對照模式?③成本率 UI 入口與預設值。

### RULEIMPL(park 於 R5)
定稿=RULEIMPL-SPEC-DRAFT-R5.md;grok R5 PASS;codex R5 殘 4 條=正式化時綁定項。

### Grok/Composer 記分素材(本票新增)
Grok:SPEC/TODO/實作三輪審+複驗全高品質,零誤判。Composer:SPEC 初稿佳;TODO 腿 B3 兩輪未閉+一次未觀測聲稱(斷路器換手);戳記/確認輪正常。Codex:findings 全實跑反例級;實作一次過+誠實 BLOCKED 回報;沙箱 hang 見票 4。

## 鐵律(不變)+本票新教訓
- 審查 --risk low --template "n/a:";實作 --risk high 附三件;codex exec 接 </dev/null;register-output(**草稿也要,否則 stamps provenance FAIL**);10 分鐘回報;baseline 唯讀;golden 產物須入版。
- 新:reconcile 須含 Verdict 行(D-1)否則不能當 --adversarial;改 reconcile 本體=戳記作廢重戳(tamper-evident);--adversarial 檔須 ADV 命名或自帶雙戳。
- 未 commit 殘留:.claude/settings.json(使用者本機)+golden 4 檔(票 5 前不動)。
