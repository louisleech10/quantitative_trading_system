# 任務卡：tests/momentum/test_entropy_indicators.py

- 組：G7；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r11/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r11-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/test_entropy_indicators.py::test_hurst_low_r_squared（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑；test_hurst_low_r_squared 之 :87 isna().any() 恆真——rolling(55) 前 54 列暖機必為 NaN（momentum/FeatureEngineering/atomic/entropy_indicators.py:184），R²<0.1 置 NaN 分支（:304-306）未被鑑別；修法＝只斷言暖機後切片有 NaN，或直呼 _hurst_rs 以低 R² 窗斷言 NaN、高 R² 窗非 NaN；其餘多為欄數／前綴 smoke、資料不足全 NaN、常數輸入 Shannon／permutation 熵＝0、perm_m 非法 ValueError；無熵值獨立 oracle；add: Shannon／permutation entropy 手算小表
