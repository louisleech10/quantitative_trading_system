# 任務卡：tests/momentum/Analysis/strategy_validation/test_cscv.py

- 組：G13；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r17/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r17-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/strategy_validation/test_cscv.py::test_is_lazy_generator（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。path 數＝math.comb（獨立 oracle）、S=12 全 924 組覆蓋且互斥、塊長餘數手算值、奇數／過多塊 raise、雙預算 fail-closed、S=2 逐值。no-probe：gap1_b1_mutation_probe.sh 只把本檔列入 baseline（:54），無 CSCV mutant ⇒ 降 contract。缺陷：test_is_lazy_generator 之計數探針（:76-79）計的是測試自建包裝生成器之迭代次數，next(probe) 後 counter 必為 1，與生產無關；docstring 宣稱「只 next() 一次即只計算一條 path」未被驗——若 _iter_splits 先物化全部 path 再 yield，:70 之 isgenerator 與 :79 仍綠。修法：monkeypatch cscv 模組之 itertools.combinations（或 np.concatenate）為計數包裝，next() 一次後斷言只產出一組。
