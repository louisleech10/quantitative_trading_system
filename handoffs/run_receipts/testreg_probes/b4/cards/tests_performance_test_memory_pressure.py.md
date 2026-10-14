# 任務卡：tests/performance/test_memory_pressure.py（G-c：檔內無測試函式）

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite_targets：[]（整檔；T 為空）
- 主委分類 note：
  0 個測試函式：全為 phase1–phase4／main 手動剖析腳本（:11 標以 python 直跑），`__main__` 守衛（:373）使 pytest 收集期不執行任何邏輯，零斷言；以 test_*.py 命名置於 tests/ 卻永不受測。無函式層 nodeid 可立碑 ⇒ 整檔改寫（轉為具斷言之效能測試或移出 tests/ 至 scripts/）。同 tests/test_data_source_simple.py 前例。
