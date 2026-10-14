# 任務卡：tests/test_phase1_registry.py（G-c：檔內無測試函式）

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite_targets：[]（整檔；T 為空）
- 主委分類 note：
  0 個測試函式：全部邏輯為模組層程式碼，pytest 收集期即執行 strategy_registry 呼叫；Test 4–6 參數驗證以 print 代斷言（:70-73、:89-94、:109-114），結果錯也不紅；Test 1–3、7 失敗時 sys.exit(1)（:29、:42、:59、:130）於收集期中斷 session。無函式層 nodeid 可立碑 ⇒ 整檔改寫（轉測試函式並 assert，或移出 tests/）；同類 registry 驗證已見 tests/test_phase2_integration.py:89-115
