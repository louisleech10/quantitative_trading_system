# 任務卡：tests/momentum/Analysis/test_gap2_golden.py

- 組：G10；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r14/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r14-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_gap2_golden.py::test_mutation_counter_without_fit_call_breaks_spy（R(t) 符號數 3）
- 主委分類 note：
  記錄器無紀錄、未實跑。§G-1 改前＝改後 canonical_sha（pre 檔 a17b57e7 於 2026-09-09 重凍，其後生產另有提交，未實跑無法確認仍綠，非已證紅）、§G-2 兩次決定性、fit_projection spy 計數＝n_regressions。test_mutation_counter_without_fit_call_breaks_spy 自指：以 dataclasses.replace 由測試自造 n_regressions=14 再斷言 14≠13（:166-168），未改動生產，任何實作皆紅；修法：monkeypatch 生產計數路徑（如讓 fit_projection 不被呼叫或計數 +1）後斷言 spy≠counter。另 test_budget_bench_receipt 每跑寫 handoffs/run_receipts/<ts>-gap2-budget-bench.log 入工作區（:121-122）
