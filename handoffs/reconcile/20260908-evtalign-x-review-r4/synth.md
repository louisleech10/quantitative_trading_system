# Reconcile — 20260908-evtalign-x-review-r4

**來源** 20260908-evtalign-x-review-r4-codex.md, 20260908-evtalign-x-review-r4-composer.md, 20260908-evtalign-x-review-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**三家 Verdict 行**：codex「需修補後收案——B4 兩個 P2 進度語意缺陷；其餘無 blocking」／composer「可收案——無新 P0/P1；§G-1 golden 設計成立」／
grok「可收案——無新 P0／P1；B5 落點維持 service」。**碼證裁決**：codex 兩條 P2 皆附實跑反例（`1 1 [1]`、`[(1,0),(2,1),(3,2)]`），成立；
三家對 B3 漏／誤擋、B5 數字來源（只取自 `ic_train_test_split`、`purge_rows` producer-bound）、Task 2.2 spy 覆蓋（`analyze_full` 只委派、refilter 吃快取）、
mutation phase 2–5 紅集合（clean clone 各 rc=1、UNCOVERED=0）結論一致。**B5 落點維持 service**（三家一致：非事件 run 不寫 `isolation` 是刻意 scope＋保 golden）。

### F1 — P2 B4 進度回報語意（codex 兩條，同一處）
**出處**：`CODEX-R4-P2-01`（欄數 <3 時回報 1／2 次，低於 TODO「≥3」）；`CODEX-R4-P2-02`（回報在該欄處理**前**發出，`done` 高估一欄、最後一次「完成」時最後一欄尚未做）。
**處置**：① 回報改在該欄 winsorize／skip **完成後**發（`_after_column`）；② 下界改 `min(3, total)`——total<3 時每欄一次、**不補假回報**；
TODO Task 4.1 驗收式同步改；測試加 n∈{1,2,3} 與「`done`＝已處理欄數」spy（`test_progress_done_counts_only_processed_columns`）。
mutation 集合對此兩缺陷無紅錨（codex 5a 指出）⇒ 新測試即紅錨，不另加 mutation（A10／A11 錨點不變）。

### F2 — 三家 §0 對主委前提之覆核（無 finding，留底）
composer／grok 皆實跑驗收命令、mutation 與 golden，§0 表逐項「成立」；grok 在 `run_analyze` payloads 上補驗**無 warning**（主委 brief 自承未斷言者）。
主委「我沒查的」八列三家皆未推翻，其中真機 thrash／Linux psutil／瀏覽器渲染維持 NOT_RUN（進 UAT B28／B29／B31 由使用者實機驗）。

Verdict: 需修補後收案——F1（codex 兩條 P2）已修並加測試；其餘無 P0／P1；B5 落點維持 service；修後進使用者 UAT B26–B31。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P2-01
**斷言**: B4 的進度回報下界對 1–2 個特徵欄位不成立：實際 callback 數分別為 1、2，低於 TODO 要求的至少 3 次。
**碼證**: `data_preprocessor.py:43-52,240-243`；VERIFY `venv/bin/python -c ...` → `1 1 [1]`、`2 2 [1, 2]`、`3 3 [1, 2, 3]`，rc=0；RECHECK 同命令並以 `n in (1,2)` 重跑。
**來源摘要**: momentum/Analysis/data_preprocessor.py#976406c53838
P2，信心度=High；小型 feature run 或 filter 後只剩 1–2 欄時違反可觀測性契約。修法需明確安排至少三次有意義的回報，或把小 n 例外寫入 SPEC/TODO 並補測試；本 finding 不涉及數值洩漏。
## CODEX-R4-P2-02
**斷言**: B4 在處理當前欄位前就回報 `done=pos`，所以每次中間回報都高估一欄，最後回報 `done=total` 時最後一欄尚未完成。
**碼證**: `data_preprocessor.py:240-264`；VERIFY 將 `_clip_series` 記錄為已處理並收集 callback → `[(1, 0), (2, 1), (3, 2)]`，rc=0；RECHECK 同一 probe。修法是將回報移到該欄 winsorize/skip 完成後。
**來源摘要**: momentum/Analysis/data_preprocessor.py#976406c53838
P2，信心度=High；UI 可能先顯示 100%/完成再執行最後欄位，ETA 也以提前一欄的 elapsed/done 計算；不改 IC 數值但違反「已處理特徵數」語意。
## COMPOSER-R4-P3-00

**斷言**: 本輪對 B2–B5（`ba408826..d398b194`）逐項核對必答 1a–7、§1 十一類與 mutation oracle 後，無達 P0/P1 門檻之新 finding。

**碼證**: ① `pytest` 驗收 53 passed/0 skip（rc=0）；② `probe-split-baseline` True；③ vitest 11 passed；④ `run_analyze` payloads `warning_payloads=0`；⑤ 讀碼 `ic_filter_orchestrator.py:278-335,1078-1082,2910-2953,3030-3054`、`ic_analysis_service.py:152-205,278-358`、`data_preprocessor.py:43-72`；⑥ R3 E2 `test_stage0_preloaded_labels_from_longer_close_still_raise…` 仍綠；⑦ 5a 所列 mutation 盲區為 Medium 信心測試缺口，守衛 fail-closed，不升格 blocking。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4eacd28757b; api/services/ic_analysis_service.py#902a944497ac; handoffs/20260908-EVTALIGN-X-REVIEW-R4-BRIEF.md

[NON-BLOCKING] 信心度=High；核對依據=必答全格雙向 verdict＋驗收命令實跑＋brief 未查表逐條標三態；停輪條件 ①–④ 滿足（3b=維持 service）。

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——B2–B5 碼路徑與 SPEC／TODO 一致，必答 1a–4b 雙向皆有碼證或反例，mutation phase 2–5 紅集合等於 oracle 且紅因皆 pytest rc=1，無新 P0／P1。

**碼證**: 驗收表（53 passed／0 skip；gap2 非 budget 12 passed；probe True；vitest 11；mutate 2–5 UNCOVERED=0）；探針 `REAL_FIXTURE_WARN_COUNT 0`、`BOUNDARY_EQ_KEPT`、progress `first_est`／`in_bounds`；關鍵路徑 `ic_filter_orchestrator.py` `_intersect_features_with_kline_period`／`_stage1_progress_hook`／`_memory_pressure`，`ic_analysis_service.py` `check_feature_run_coverage`／`_inject_period_alignment`／`_inject_isolation_source`，`data_preprocessor.py` `_emit_progress`；3b 裁定維持 service。RECHECK：重跑上表命令＋clean-clone `handoffs/20260907-evtalign-mutate.py --phase {2,3,4,5}`。

**來源摘要**: handoffs/20260908-EVTALIGN-X-REVIEW-R4-BRIEF.md#d398b194dc4e; momentum/Analysis/ic_filter_orchestrator.py#e4eacd28757b; api/services/ic_analysis_service.py#902a944497ac; momentum/Analysis/data_preprocessor.py#976406c53838; handoffs/20260907-evtalign-mutate.py#a814de569314

[MINOR] 信心度=High。sentinel（零實質 finding）；非湊數。文件表頭 TODO 5.1「修改檔案」仍列 orchestrator 屬收案後順手清理，不升 finding。

---

STATUS: DONE
