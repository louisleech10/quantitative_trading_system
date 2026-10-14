# 任務卡：tests/momentum/Analysis/test_ichc_xsec_capability.py

- 組：G11；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r15/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r15-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_ichc_xsec_capability.py::TestXsecCapabilityStatus::test_m4_probe_bare_empty_dict_would_fail（R(t) 符號數 2）
- 主委分類 note：
  記錄器無紀錄、未實跑。假 mutation 探針：test_m4 只把測試自建之 dict 某節設為 {} 後斷言該 {} 無 status，未呼叫生產、未讓第一條斷言轉紅，恆綠。修法：monkeypatch 生產端 xsec 節組裝（ic_filter_orchestrator.py:2344 之 _xsec_na）使任一節回裸 {}，重跑 analyze_cross_sectional 並斷言第一條之檢查邏輯回報問題（基線無問題、變異有問題）。其餘三條對契約枚舉與固定值比對有效；合成 MultiIndex 屬單元層
