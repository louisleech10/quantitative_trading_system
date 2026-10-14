# 任務卡：tests/momentum/Analysis/test_splitunify_derive.py

- 組：G11；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r15/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r15-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_splitunify_derive.py::test_fingerprint_independent_oracle_matches_producer_value（R(t) 符號數 4）
- 主委分類 note：
  記錄器無紀錄、未實跑。投影純函式 derive_event_split_from_plans：答案窗跨界 train 事件必 purge（含 == 與差 1ms 兩側界）、三態互斥涵蓋、多標的交錯與單跑逐筆相同（METAMORPHIC）、逐列指紋擋中段位移、遞增閘、換錨邊界事件、接線 spy（刪呼叫即紅）、clusters 對凍結手推 oracle（tests/golden/splitunify/clusters_oracle.json）、大量具名 fail-closed；檔內多處記載 M-SU-* mutation 實跑撈出之缺口，claim 依此標 correctness。缺陷：test_fingerprint_independent_oracle_matches_producer_value 名稱宣稱獨立 oracle，但 train.row_time_fingerprint 由本檔 _plans（:69-75）以同一支 build_row_time_fingerprint、同一組參數算出，:1364-1367 再算一次比對——自指、恆綠，未觸任何生產 producer。修法：期望值改以 hashlib＋json 手組 canonical payload 獨立重算（同 test_splitunify_golden.py:85-90 之作法），或改比生產 _build_holdout_split_plan 寫入之指紋。另 test_unmatched_timestamp_is_purged_not_train／test_membership_set_not_interval 名稱與現行斷言相反（:394-396 斷言 train），docstring 已明載 9.2b 反轉並保留追溯，不列缺陷
