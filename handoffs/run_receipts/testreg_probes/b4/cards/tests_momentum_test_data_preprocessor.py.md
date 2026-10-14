# 任務卡：tests/momentum/test_data_preprocessor.py

- 組：G7；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r11/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r11-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/test_data_preprocessor.py::test_preprocess_full_sample_escape（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑；test_preprocess_full_sample_escape 之 :65 置 5／200＝2.5% 尾端為 1e6 ⇒ 全期 p99（pandas 線性插值第 197.01 位）本身即 1e6，:84 out.max≤p99 對未裁尾、PIT 裁尾皆恆真，數值斷言空心（只 :80-81 log 斷言有效）；修法＝outlier 少於 1%（如 1 個）使 p99<1e6，斷言 out.max 等於獨立 pandas 算之全期 p99 且異於 pit_expanding 結果；其餘：手算分位裁尾邊界、低覆蓋／常數欄移除、unset 模式 fail-closed、PIT 截尾 vs 加未來之 type 判定一致（:175-235，metamorphic 防洩漏）、first-valid＝MIN_SAMPLES-1 並以手算雙 warmup＝198 對照（對照組非生產注入）；no-probe
