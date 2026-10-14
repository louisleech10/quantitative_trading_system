# 任務卡：tests/momentum/Analysis/test_icfirstalign_fu2.py

- 組：G11；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r15/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r15-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_icfirstalign_fu2.py::test_mutation_carrier_positional_reindex_all_nan（R(t) 符號數 4）
- 主委分類 note：
  記錄器無紀錄、未實跑。輸入表 real_kline=N，實經 scripts/ic1d_baseline_freeze.prepare_real_kline_inputs 跑真實 kline production analyze。close carrier 於特徵時間戳逐值等於測試端獨立依時間戳取之 kline close、全 NaN／時間不相交／長度 0 具名拒、部分 NaN 位置保持、UTC 表示四格等值（METAMORPHIC）、事件型路徑值與 NaN 位置對證。_utc_instant_key 改恆等、_validate_close_carrier 改 no-op 兩支探針實呼叫生產 _build_close_carrier（模組全域查找，替身生效）。缺陷：test_mutation_carrier_positional_reindex_all_nan 把 ifo._build_close_carrier 換成測試自寫之 head_carrier 後直接呼叫該替身並斷言全 NaN（:159-164），只驗測試自算之值、未經任何生產碼 ⇒ 假 mutation 探針；修法＝替身裝上後重跑 orchestrator.analyze（生產呼叫點 :4306-4308 走模組全域），斷言 _ic_cache close_series 全 NaN、即 test_production_close_carrier_equals_kline_close 之相等斷言翻轉
