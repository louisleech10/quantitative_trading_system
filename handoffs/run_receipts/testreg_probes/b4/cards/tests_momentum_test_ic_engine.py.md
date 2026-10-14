# 任務卡：tests/momentum/test_ic_engine.py

- 組：G7；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r11/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r11-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/test_ic_engine.py::test_compute_rolling_ic_and_icir（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑；compute_ic Spearman／Pearson 對 scipy 逐特徵差分 <1e-9（A15 獨立 oracle，但無 mutation 收據 ⇒ no-probe）、rolling 窗依 timeframe 換算（10x12h/4h=30）、_align_label_to_group 同長錯位／子集拒用且超集依時間戳取值、winsorized 標籤 LOOKAHEAD_LABEL_UNSUPPORTED fail-closed、其餘多為邊界分支（空／短／std=0／全 NaN 回 NaN 或空）；rewrite：test_compute_rolling_ic_and_icir 宣稱「Rolling IC + ICIR 計算正確」，實際只斷鍵存在、長度>0、icir>0、hit_rate>0.8（:49-53），算法錯但同號仍綠——章程 §E1 明列 ic_engine rolling IC 僅 SMOKE、必補 vs scipy 逐窗（docs/TEST_DESIGN_CHARTER.md:88），全 repo 無逐窗 scipy 差分；修法＝逐窗與 scipy.stats.spearmanr 比對 <=1e-12、窗數＝(n-w)/stride+1、ICIR 對手算 mean/std 比對；kendall／unknown method 只斷鍵存在（:258,:261，未知方法生產端 warning 後回退 spearman）屬弱斷言不另列
