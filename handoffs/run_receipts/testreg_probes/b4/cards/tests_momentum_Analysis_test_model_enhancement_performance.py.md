# 任務卡：tests/momentum/Analysis/test_model_enhancement_performance.py

- 組：G11；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r15/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r15-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_model_enhancement_performance.py::test_phase5_performance_targets（R(t) 符號數 8）
- 主委分類 note：
  記錄器無紀錄、未實跑。回傳未斷言致效能斷言可假綠：只斷言耗時與記憶體上界，Full Enhancement 之 FullEnhancementResponse 被丟棄（:172-185），模組失敗被服務吞為 status=failed（model_enhancement_service.py:147-148）仍快速通過。修法：取回傳斷言 status==completed 且六模組皆在 modules；M1–M6 亦取回傳斷言非空。tests/momentum 下匯入 api 服務，歸屬可議（非 R6 違規）
