# 任務卡：tests/momentum/Analysis/test_net_ic_analyzer.py

- 組：G11；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r15/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r15-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_net_ic_analyzer.py::test_mutation_m1_restore_mixed_subtraction（R(t) 符號數 1）
  - tests/momentum/Analysis/test_net_ic_analyzer.py::test_mutation_m2_reinstate_x2（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。NetIC 契約（三 profile 鍵集、unavailable union、無 net_ic 鍵、cost_bps 域檢、負／非有限 turnover SKIPPED、無預設成本）正常；cost_drag 與 breakeven=20bps 為手算獨立 oracle。缺陷：M1／M2 兩支探針把 compute_cost_drag 換成測試自寫函式後，直接呼叫該替身並斷言其值≠0.0015（:343-349、:358-360）——只驗測試自算之值，未經生產 batch_analyze（:457 才是生產呼叫點），也未讓 test_cost_drag_hand_calc 轉紅，恆綠假探針。修法：注入後改斷言 batch_analyze 之 cost_drag_return 不再等於 0.0015（或以 pytest.raises 包住原手算測試之斷言）。M3／M6／M9／M11 以包裝方法污染輸出，只證斷言 helper 有鑑別力，可接受；M5、M10 真打生產路徑（:171 經模組層 _validate_cost_params）。no-probe（數值面在 M1／M2 改寫前無有效探針，暫標 contract）
