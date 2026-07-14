# IC1C-TODOREV R6 Codex 閉合重驗
Verdict: APPROVE；審查鎖定 TODO r6 sha256 `dfccd79a4a8a20625a5c19257ad594dbb83a9569ad7df0e7167e52ec9d72af7c`。本輪不寫 RECONCILE-STAMP。

## r5 的 2 個 BLOCKING 反例
- R5-CODEX-1 **CLOSED**：TODO:95 將 `oc_return/hl_range/zscore_20` 明確排除於 G-OLD 的 `gross_ic`/`turnover` byte-equality 比對集；三者改驗各自 `SCHEMA_SKIPPED` 形狀與 reason。TODO:125 的 G-NEW2 排除集為相同三特徵，且要求腳本常數固定。
- R5-CODEX-2 **CLOSED**：TODO:75 將 nan turnover 唯一規則釘為 `raise ValueError`；TODO:78 對負/非有限 turnover 同為 `raise ValueError`。全文無 `raise 或`、`或 0.0`、`擇一` 殘留；turnover=0→0.0 僅是合法零值邊界，非錯誤分支。

## r6 delta 掃描
- G-NEW 的鍵集合、獨立 canonical 重算、strict JSON、diff manifest 規則保持；排除只限三個 post-hoc 注入特徵，未放寬其餘 feature 的不變欄 oracle。
- Task 1.3 仍禁止修改 `quantile_turnover` 本體與 clamp，M8 probe/手算 oracle 保持；未見新增 BLOCKING。

ASSUMPTIONS_VERIFIED: SPEC reconcile 三家 APPROVED；G-NEW/G-NEW2 排除集字面一致；三注入特徵另驗 SKIPPED shape+reason；Task 1.3 負/非有限 turnover 僅有 raise 語意。
TESTS_RUN: `shasum -a 256 docs/IC1C_NETIC_SPEC.md docs/IC1C_NETIC_TODO.md handoffs/20260714-IC1C-TODOREV-R5-codex.md`→TODO `dfccd79...d72af7c`；`nl -ba docs/IC1C_NETIC_TODO.md` 全讀；5 個 `rg -nF` 正向斷言+`rg -n 'raise 或|或 0\\.0|擇一'` 負向斷言→`R5_COUNTEREXAMPLES_CLOSED_STATIC_ASSERTIONS=PASS`。文件審查，未跑產品測試。
FAILURES_SEEN: none（兩條靜態反例均 CLOSED）。
SCOPE_CHANGES: 僅新增本檔；未改 TODO/SPEC/RECONCILE/HANDOFF.md，未戳記。
NUMERIC_OR_SCHEMA_IMPACT: none；文件審查未改產品數值、schema 或輸出大小。
TODO-REVIEW-R6: APPROVE
