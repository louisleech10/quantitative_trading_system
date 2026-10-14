# 任務卡：tests/api/test_ic_models.py

- 組：G6；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r10/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r10-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/api/test_ic_models.py::test_empty_import_id_also_rejected_for_spec_and_scan（R(t) 符號數 1）
- 主委分類 note：
  斷言與 docstring 不符：rewrite 目標的 docstring 說 event_label_spec 與 event_label_scan 兩條不變式都要擋空字串 import id，實際只斷 scan（:133-135）。生產端 spec 分支（api/models/ic_models.py:254 的 not self.event_import_id）全 repo 沒有任何測試以 event_import_id="" 覆蓋（grep 為空）。修法：同函式補 spec 加空字串的 raises（純增斷言）。其餘為 pydantic 請求模型契約：mode 值集取自契約檔 event_label_mode.json（單一來源、非自指）、正反組合皆有對照。unknown_value 一支用 pytest.raises(Exception) 太寬，屬小瑕疵不改
