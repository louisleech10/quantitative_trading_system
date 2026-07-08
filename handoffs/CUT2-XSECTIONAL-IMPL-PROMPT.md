# 派工:第二刀主體 cross_sectional 防洩漏 — 實作(Composer)

前置:main 乾淨;SPEC/TODO 已 freeze(三方 reconcile 戳記 APPROVED)。你是實作端。**嚴格照 SPEC/TODO,不自行改設計**;有疑問或 debug ≤2 輪未過→輸出 `STATUS: BLOCKED — <問題>`,不硬幹(交委員會)。

## 讀(repo 內,依序)
- `docs/IC_PHASE1_1a_CUT2_XSECTIONAL_SPEC.md`(凍結施工藍圖)
- `docs/IC_PHASE1_1a_CUT2_XSECTIONAL_TODO.md`(施工清單,含每 Task 實作要點/驗證/邊界/禁止)
- `handoffs/CUT2-XSECTIONAL-SPECADV-RECONCILE.md`(裁決 D-1~D-4,尤其 F3 全域時間邊界)
- `handoffs/CUT2-XSECTIONAL-RECON.md`(投偵察背景,VERIFY 附證)

## 實作範圍(照 TODO Batch 1→2→3)
- **Batch1**:Task 1.1(F1 `_append_cross_sectional_labels` datetime 對齊 + R8 fail-closed 單位契約)+ Task 2.1(F4 per-symbol 覆蓋守衛 + 推導下界)。
- **Batch2**:Task 3.1(F2 labels_path 單軸 fail-closed raise,**不建** symbol-aware loader)。
- **Batch3**:Task 4.1(F3 全域同步時間邊界 holdout;IC 及**全部** report 輸出僅 test frame;`_run_analysis` 傳 timeframe;審計用 `validate_split_pair_integrity` + `ICSplitAdapter._base_universe_hash`)。

## 測試(每 Batch 三層,禁廉價綠燈,見 SPEC §V/D-4)
- 單元 + Golden(真 3sym×12h e53e2290 + kline_cache.h5,label oracle 逐幣手算比對)+ 端到端**真路徑**(真 load_multi→append labels→analyze,**取代**現行 monkeypatch 假 frame+stub analyzer)。
- mutation red-on-break 必按 D-4:F1 還原對齊須真端到端回 0/5088;F4 monkeypatch 實關守衛+1/3幣全NaN→raises;F3 縮 purge_td→不等式斷言 FAIL。

## Batch Gate(全綠才算完成,逐字跑)
- `grep -r "from api\." momentum/ | wc -l` → 0
- `pytest tests/api/test_ic_analysis_service.py -k "append_cross_sectional_labels or cross_sectional_coverage_guard" -q`
- `pytest tests/momentum/ -k "cross_sectional_labels_path or cross_sectional_oos_split" -q`

## 禁止(逐條,違反=退回)
- 改特徵值/欄位/列數;改 `generate_log_return` forward 語意;改單幣 `analyze`/HDF5 fallback/`_write_features_h5`;放寬/刪除既有測試斷言換綠燈;把 OOS 藏預設關閉 flag(驗過預設 on);建 symbol-aware labels HDF5 loader(D-2 已 deferred);用 `>1e12` heuristic 猜時間單位(R8 須 fail-closed);per-symbol 比例切分(D-1 已否決,須全域時間邊界)。

## 收尾
- 產出(改動摘要 + 測試結果)寫 `handoffs/CUT2-XSECTIONAL-IMPL-RESULT.md`;結構化收尾報告 ASSUMPTIONS/TESTS/FAILURES/SCOPE/NUMERIC。
- 不得 `git checkout` tracked 共用檔。結尾 `STATUS: DONE` 或 `STATUS: BLOCKED — <原因>`。
