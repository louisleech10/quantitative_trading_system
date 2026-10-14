# 任務卡：tests/momentum/event_samples/test_event_disposition_ledger.py

- 組：G13；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r17/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r17-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/event_samples/test_event_disposition_ledger.py::test_contract_change_takes_effect_without_manual_cache_clear（R(t) 符號數 1）
  - tests/momentum/event_samples/test_event_disposition_ledger.py::test_contract_change_with_preserved_mtime_still_takes_effect（R(t) 符號數 1）
  - tests/momentum/event_samples/test_event_disposition_ledger.py::test_duplicate_json_key_in_contract_is_fail_closed（R(t) 符號數 2）
  - tests/momentum/event_samples/test_event_disposition_ledger.py::test_observed_semantics_survive_contract_reordering（R(t) 符號數 2）
- 主委分類 note：
  記錄器無紀錄、未實跑。處置帳值集自契約讀、判定順序、post-trim 邊界、不讀 stage3、快取以內容雜湊為鍵、回深複本，斷言本身正常。缺陷：四支函式就地改寫入庫之生產契約 `momentum/Analysis/contracts/split_unify.json`（:207,:253,:287,:316）再 finally 還原，不密閉——中途被殺會留下壞契約；同時跑之其他讀該契約者（ic_filter_orchestrator、pipeline、canonical_holdout、split_projection）可能讀到探測值；工作區 dirty 數比對類斷言會 flaky（CLAUDE.md 已記同型事故）。修法（斷言不動）：monkeypatch `event_disposition._CONTRACT`（event_disposition.py:28 模組常數）指向 tmp_path 之複本後照原步驟改寫。
