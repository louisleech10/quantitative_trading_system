# 任務卡：tests/phase24/test_rolling_oos_validator.py

- 組：G14；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r18/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r18-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/phase24/test_rolling_oos_validator.py::test_auto_reduce_step_generate_splits（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。缺陷：test_auto_reduce_step_generate_splits 名稱宣稱「自動縮步」，但 :39 只斷言 len>=1；n=260、train100/test20、step50 時不縮步也有 3 段（仍 >=1），縮步後應為 step25 共 6 段（rolling_oos_validator.py:170-184）⇒ 斷言偵測不到縮步失效。修法：斷言 len==6，並逐段驗 train=range(s,s+100)、test=range(s+100,s+120)、s 每次遞增 25——這同時補上本檔唯一能驗 OOS 切分時序（test 緊接 train、不重疊，章程 A2）的斷言。現況全檔沒有任何斷言驗切分無前視，故不得標 A2。:24 assessment∈全值域為恆真子斷言（同函式 :23 仍有效，smoke）。
