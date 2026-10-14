# 任務卡：tests/api/test_gap3_t0_unit_detect.py

- 組：G6；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r10/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r10-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/api/test_gap3_t0_unit_detect.py::test_gap3_t0_unit_detect_bands_are_disjoint（R(t) 符號數 2）
- 主委分類 note：
  記錄器無紀錄、未實跑；t0 單位偵測：ms 原樣、秒級精確 ×1000==1704067200000、兩側模糊值與非整數／bool raise 且 reason 屬契約集合、JSON 與 CSV 對映路徑落檔皆為 ms、判不出者端到端 422 落檔 0；rewrite：test_gap3_t0_unit_detect_bands_are_disjoint 於測試內自訂 ms_max=ms_min*1000（:73，複寫生產 import_contract.py:325 之定義）再驗「v 與 1000v 不同時落帶」之數學恆等式，全程未呼叫 detect_t0_unit_ms＝恆綠（改生產帶界不會紅）；修法：改以 detect_t0_unit_ms 打帶界（ms_min-1、ms_min、ms_min*1000-1、ms_min*1000、ms_min//1000 與其 -1）斷言各值唯一結果或 raise；no-probe
