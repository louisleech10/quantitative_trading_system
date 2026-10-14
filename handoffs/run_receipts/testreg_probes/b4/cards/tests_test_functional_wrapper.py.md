# 任務卡：tests/test_functional_wrapper.py（G-c：檔內無測試函式）

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite_targets：[]（整檔；T 為空）
- 主委分類 note：
  記錄器無紀錄、未實跑。整檔改寫：無任何 test_ 函式（pytest 收集 0 節點），所有檢查寫在模組層、於 import／收集期執行，失敗以 sys.exit(1) 呈現為收集錯誤而非測試失敗；Test 8 類裝飾器 EMAIndicator 與函數式 calculate_ema 之對照只 print 差異、不斷言（:174-177，宣稱「兼容性」而無斷言）；Test 3／5 用未設種子之亂數（:61、:114）。修法：拆為 test_* 函式、Test 8 改 assert_series_equal 或明定容差斷言、固定 seed；參數驗證改 pytest.raises。
