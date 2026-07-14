# IC1C-TODOREV R5 Codex 閉合重驗
Verdict: REJECT；審查鎖定 TODO r5 sha256 `3de9d3cba36122b3b5739f141912f5552fbfa6466c452c9f132f0b296dea6475`。SPEC reconcile 三家 APPROVED；本輪未補 TODO stamp。

## r3 的 5 個 BLOCKING 反例
- ADV-CODEX-1 **CLOSED**：§0:8 補負 turnover；T1:93 具名 `test_negative_turnover_skipped` 注入 `-0.2`、驗 `negative_turnover`，同檔 `m11_restore_clamp`；G-NEW:95 亦注入 `zscore_20=-0.2`。
- ADV-CODEX-7 **CLOSED**：G-NEW2:125 明定比對集排除 `oc_return/hl_range/zscore_20` 三個 post-hoc 注入特徵，且要求排除集寫死於腳本常數。
- R2-NEW-1 **CLOSED**：§B:30 已給可執行的 `h1`/`h2` 兩次生成、各自取 hash、`[ "$h1" = "$h2" ]` 命令。
- R4-CODEX-1 **CLOSED**：§0:9 與 T1:93 要求 capacity 子鍵集合恰等、型別、`calibration=="uncalibrated"`，多/少鍵失敗。
- R4-CODEX-2 **CLOSED**：`--collect-only` 已實際列入 §B:32 B2→B3 Gate，並於 :125 G-NEW2 定義同步。

## r5 新洞
- R5-CODEX-1 **[BLOCKING] G-NEW oracle 自相矛盾**：TODO:95 新增 `zscore_20 turnover=-0.2`，同句仍要求全部 `gross_ic/turnover` 對 G-OLD byte 等值；G-OLD:41 未注入該負值。故 `zscore_20.turnover` 必須同時等於舊真值與 `-0.2`，B1 Gate 不可達。修法需把三個注入特徵明確排除於「不變欄」比較，或讓 G-OLD 同輸入注入；不可只靠 diff manifest 掩蓋。
- R5-CODEX-2 **[BLOCKING] Task 1.3 非有限 turnover 有兩個相反合法結果**：TODO:75 允許 `raise 或 0.0，擇一`，但 :78 又唯一要求負/非有限 `raise ValueError`；SPEC fail-closed 與資料品質 gate 不允許執行端自行選值。需刪除 `或 0.0` 並讓 T3 具名斷言 raise（proxy 若刪除則刪除該舊測試）。

ASSUMPTIONS_VERIFIED: SPEC reconcile 三家戳記齊；r5 五項指定修補均有字面 oracle；G-OLD 僅注入 oc_return/hl_range，而 G-NEW 額外改 zscore_20 turnover；Task 1.3 同時存在 0.0/raise 兩規則。
TESTS_RUN: `shasum -a 256 docs/IC1C_NETIC_{SPEC,TODO}.md handoffs/20260714-IC1C-TODOREV-RECONCILE.md`→TODO `3de9...6475`；`nl -ba` 全讀 SPEC/TODO；`rg` 核對五修補及兩矛盾。文件審查，未跑產品測試。
FAILURES_SEEN: none（靜態反例重跑）；兩個不可達/歧義 oracle 為審查 finding。
SCOPE_CHANGES: 僅新增 `handoffs/20260714-IC1C-TODOREV-R5-codex.md`；未改 TODO/SPEC/RECONCILE/HANDOFF.md，未補戳記。
NUMERIC_OR_SCHEMA_IMPACT: none；唯讀審查內容，未改產品數值/schema/輸出大小。
TODO-REVIEW-R5: REJECT(2 BLOCKING)
