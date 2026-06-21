# FF consistency FINAL review — Codex

審閱: `20260619-ffconsist-FINAL.md` 對照 R2 三方與 R2 互審五份。
結論: **同意**；可作為後續 SPEC/TODO 來源，但 SPEC 必須把驗收命令/允許改檔/禁止事項重新落成可執行條款。

1. 漏項檢查: **同意** FINAL 未漏掉我方或他方 R2 的阻斷重點。
2. E: **同意** 薄 `normalize_progress_event()` / retention 對應函式列 mandatory；正確吸收 Codex + 互審裁決，且明確拒絕厚 Sink/runner adapter。
3. Q2 背壓: **同意** pending retained output bytes soft threshold + 暫停新 wave + UI 提示已納入 mandatory；修正 Claude/Composer R2 原漏。
4. #1 smoke: **同意** 父+1~4 子進程 append smoke 作 P0 門檻；比「TODO/註解」更正確，且未升級成完整 T-A 壓測。
5. Parity 5 條: **同意** schema/version、error enum、retention 狀態、concurrent>1 無假 current_stage、retention decided 前無 `browse_task_id` 都正確。
6. Q3 RSS: **同意** 互斥分欄與 deprecate `current_rss_mb`；**補充** SPEC 可保留備選欄名討論，但 FINAL 採 `process_rss_mb` / `worker_rss_mb` 可實作。
7. Q2 staging 切點: **同意** 放在 checkpoint output_paths 後、browse register 前；符合 R2 現碼證據。
8. 優先序: **同意** Q5(P0a) → #1(P0b) → E(P0c) → Q3(P1) → Q2-A(P2) → Q2-B(P2.5)。
9. SPEC/TODO 轉寫提醒: Q2-A 必同時包含非阻塞、背壓、checkpoint 狀態機、resume 重建 pending queue；Q2-B 才做交易式 bulk-delete。
10. 反對事項: none。

ASSUMPTIONS_VERIFIED: 已逐份讀 FINAL、R2 三方、R2 互審並比對上述裁決。
TESTS_RUN: read-only document review; no code tests run.
FAILURES_SEEN: none.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: review only; no code/schema changed.
STATUS: DONE
