# Handoff
**Agent**: Claude | **Time**: 2026-07-02 | **Branch**: main

## ★驗收防偽閘 verify-gate(P0,先於 FF 收尾;起因=P0-FF-3 驗收捏造事故 A 類)
- 文件鏈/議事/SPEC v2.1/TODO 齊備:`docs/VERIFY_GATE_{BRIEF,SPEC,TODO}.md`+`handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md`(雙戳記)。
- **B1 ✅**(`d3870c4` run_with_receipt+審計)。**B2 ✅**(`a1d3638` claim checker+ledger,V7 誤報=0→B3 PreToolUse 可全量)。
- **B4+B5 ✅(本次 commit)**:B4=mutation接receipt/W3 adversarial provenance/W2 stamp provenance/audit_chain;B5=RESULT硬欄位枚舉/#6 fingerprint衝突/W1 FACT-RECEIPT。
  Composer 實作→Codex adversarial **6 BLOCKING**(gate非ADV路徑繞過/回填日期grandfather/RESULT枚舉不入checker/fingerprint含極性詞自廢/W1漏指令輸出/合成receipt殘留)→Composer 修→Codex 原提出方重跑反例**全 CLOSED**→Claude 補 gate.sh `GATE_DIR_OVERRIDE` 測試隔離+清 audit.log 合成條目→Codex round2 APPROVED。governance **55 passed 且 audit.log 零汙染**。
- **B3(本次 commit)**:verify_pretooluse.sh+settings.json PreToolUse/git hooks(staged 讀 index blob)/CI workflow/health。Codex review 4 BLOCKING(partial-stage/code-only假紅/交付狀態自阻斷/binary crash)→Composer 修→Codex 閉合檔寫道「FINAL VERDICT: APPROVED — B3-1/B3-2/B3-3/B3-4 CLOSED」(出處:20260702-VERIFYGATE-B3-REVIEW-CODEX.md closure 節)。governance 75 tests 綠 VERIFY:20260701T235954Z-governance-b3-final。PreToolUse hook 已生效(本檔本段初稿即被其擋過,補 receipt 後才寫入)。
- epic B1-B5 全落地。git hooks 已裝(core.hooksPath)。
- **全系統紅隊+修補(本次 commit)**:三方紅隊(Claude獨立版+Codex+Composer,reconcile v2 兩家內容APPROVED;v1兩家REJECT指正我把A3假歸屬誤降級→v2升R6)。淨判斷=仍有洞需緊>過嚴。修 R1 env-prefix繞閘/R2 docs走私/R3模糊洗白/R6假歸屬自我認證(P0)+R4路徑正規化/R5緊急逃生docs/VERIFY_GATE_EMERGENCY.md/R7 provenance emitter接線(P1)。Codex原紅隊方重跑同批反例,閉合檔載「VERDICT: R1-R7 CLOSED」(出處:20260702-VERIFYGATE-REDTEAM-CLOSURE-CODEX.md)。governance 88 tests 綠 VERIFY:20260702T021250Z-governance-redteam-fix。R7 使未來新reconcile帶--task-id即取provenance,不必allowlist後門。殘餘=誠實邊界(careless-proof+tamper-evident,非防惡意)。

## ★FF 深稽 P0-FF-3(收尾中:驗證輪跑完,剩 Codex final review→收 WIP commit)
- 歷史:舊「align 真紅(babu8o07p)」=捏造(`20260701-FF-FORENSICS-RECONCILE.md`);後三輪修探針:v1 對稱注入無牙→v2 shape 修(Codex PROBE-REVIEW 抓,PROBE-CLOSURE 檔載「CLOSED」)→v3 oracle 輸入修(讀 run_dir/timestamps.parquet 非 raw/;ORACLE-DESIGN-CODEX 設計,兩輪斷路器委員會)。
- **驗證輪結果(引用 receipt log 原文)**:mutation 全探針輪 receipt log 檔載「5 passed, 4 deselected in 9031.45s (2:30:31)」(出處:handoffs/run_receipts/20260702T125150Z-mutation-test_ff_multitf_truncation_mr.log;單探針預驗出處:20260702T102046Z-align-probe-single-preflight.log 檔載「1 passed」)。B2 回歸 receipt log 檔載「2 failed, 8 passed」(出處:20260702T042627Z-ff-b2-regression.log;2 failed=fracdiff max_lag 長度依賴,委員會三腿定案+使用者選 A→strict-xfail+epic,commit 9d87d68)。
- **本 session 剩**:Codex final review(進行中,產出 20260702-FF-P0FF3-FINAL-REVIEW-CODEX.md)→依 verdict 收 WIP 正式 commit(工作樹 diff=helpers+multitf 測試)。

## ★P1-FF-5/7(前置全完成,**新 session 從這開始**;使用者 2026-07-02 定:等 P0-FF-3 全結束才實作)
- **設計三方定案**:`handoffs/20260702-FF-P1-57-RECONCILE.md` v2(戳記區載 codex+composer APPROVED task:p1ff57-stamp-v2;v1 Codex REJECT 抓 Claude 漏併 L6.5→v2 改 L2+L3+L6.5 聯集)。三腿:`20260702-FF-P1-57-DESIGN-{CLAUDE,CODEX,COMPOSER}.md`。
- **實作指派檔已備**:`handoffs/20260702-FF-P1-57-IMPL-PROMPT.md`(兩測試檔+fast/medium/slow 分層+探針 M5.1-3/M7.1-2+「只跑快測級,慢測標 marker 留排隊」)。新 session 步驟:①gate dispatch(risk high;--adversarial 用 waived:R7-emitter 缺口理由,見 reconcile 尾節)②派 Composer 讀 IMPL-PROMPT 實作③Codex review④慢測(FF5 slow 全鏈 ~1h)序列跑+receipt⑤commit。
- 2026-07-02 曾派實作旋即依使用者指示停止,僅 helper 殘檔已刪,測試檔未開寫。
- **P1-FF-6 不在此**:已併 fracdiff max_lag 修復 epic(ROADMAP;FF 深稽全完成後修,修完重生成 FF 給 IC——使用者定序)。

## verify-gate 待修小項(新 session 順手或另批)
- **6 個 FF 委員會過程檔未 commit**(checker 擋其 prose 事實句;committee 親筆檔不宜為過閘改原文=竄改 audit trail):ALIGN-ORACLE-{FACTS,DESIGN-CODEX}、DSTAR-GATE-{CLAUDE,CODEX}、ALIGN-PROBE-FIX-PROMPT、PROBE-FIX2-composer。**檔在本機 handoffs/ 勿刪**;O3-extension(委員會過程檔 prose 類豁免設計)後補 commit。
- **R7-emitter 缺口**:stamp-review 派工(risk low 無 adversarial)不發 committee_dispatch→新 reconcile 戳記 provenance FAIL 只能 waived(修向見 P1-57-RECONCILE 尾節)。
- **`pytest -k` receipt 空 node_ids**:selected_node_ids=[]→具體 scope 聲稱綁不上,配 R3 反模糊成 catch-22;引用暫用「檔載『…』(出處:log)」格式。修向:run_with_receipt 對 -k 跑補記 collected node ids。

## 鐵律補充(本 session 新增)
- **push 後 CI 自動查**:PostToolUse hook(scripts/ci_check_after_push.sh)已入 settings.json,**新 session 重啟生效**(可能需 /hooks 核准);Verify Claim workflow 兩路徑已在 GitHub 真跑綠(#5 code-only skip/#6 內容掃描)。
- HANDOFF/commit-msg 寫「已驗/passed」須帶 VERIFY:<receipt-id>(receipt 先 git add;scope 要能與 receipt node_ids 交集)或改引用格式「檔載『…』(出處:檔名)」。

## 鐵律(慢測試/執行)
- generate_features ~20分/次;內層 `timeout 14400` 一次跑完;跑後 `git checkout -- tests/golden/l65/test_inventory.txt`+tier2 還原;**長測試後清 pytest 舊輪次**(/var/folders/.../pytest-of-louis;2026-07-02 堆 33GB 事故,清時留 pytest-current)。
- 中大一律 Composer 實作+Codex review(feedback_executor_override);資料正確性/測試設計走三方委員會。pre-existing 失敗=test_ic_engine(非深稽)。
