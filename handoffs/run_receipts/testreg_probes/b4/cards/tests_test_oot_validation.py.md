# 任務卡：tests/test_oot_validation.py

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/test_oot_validation.py::TestPurgedTimeSeriesSplit::test_embargo_removes_validation_start（R(t) 符號數 1）
  - tests/test_oot_validation.py::TestPurgedTimeSeriesSplit::test_purge_removes_training_end（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。TimeSplitter 切分總數／時間順序／重疊與樣本不足例外、XGBoostAnalyzer.validate_oot 樣本數與正樣本率、gap 門檻分類、to_dict 鍵之契約；合成資料（契約層可接受）。無同檔 mutation 探針（no-probe）。兩支洩漏相關從嚴改寫：① test_embargo_removes_validation_start 迴圈內只 pass（:292-294），docstring 宣稱驗 embargo 移除驗證集開頭而無任何斷言（空心）；修法 assert 每 fold val_idx.min()−原 val 起點＝max(1,int(len×embargo_pct))。② test_purge_removes_training_end 註解宣稱 train_max+purge_gap < val_min，斷言卻用 <=（:276-277），實際 train_max+5＝val_min−1，purge 少移 1 根（purge_gap−1）時仍綠，斷言與宣稱不符；修法改 assert val_min−train_max−1==purge_gap。test_cv_oot_gap_calculation 期望 gap 由 result.oot_auc 導出（self-ref，只驗減法公式，oot_auc 未對 sklearn roc_auc_score 獨立核）。輸入表 19 支含 fixture test_df（:105，名以 test_ 起頭）。
