# 第二輪交叉詰問回答 — Codex (GPT-5.5)

Q1: AGREE — Composer 的三個探針證明「只讀文件」不足以擋錯前提；條款應最小化但強制。建議文字：「Reviewer 對 §A 已驗證/已確認事實中可低成本核實者（grep/讀檔/一行 python/現有 checker）必須實跑並貼命令與輸出；未能實跑者標 `FACT_UNRECHECKED`，若該事實影響 §RISK/§G/§V/執行 scope，finding severity 不得低於 MAJOR。」不要要求昂貴長測或真資料重跑，只要求低成本反例。

Q2: AGREE — 最小充分組合是 (a) finding 穩定 ID + RECHECK、(c) reconcile 對映表、(b) gate 輕量 grep。成本：低到中；prompt/template 改動低，gate grep 低，RECHECK 自動重跑只對 shell command 類 finding 可選中成本。機檢只需要求：每個 BLOCKING/MAJOR 有 `ID:`、`RECHECK:`；reconcile 有 `[ID] -> [FIXED section/file] -> [RECHECK PASS/WAIVED reason]`；gate 拒絕未處理 BLOCKING 或缺 verdict。原提出方重跑是高價值但可作 workflow 要求，不必第一版全自動化。

Q3: AGREE — 不是過度工程，因 RESULT 已有 `MUTATION_CHECK`，上游卻沒要求設計可證偽 oracle，會自然退化成 `NOT_RUN`。最小改法是在 SPEC §V 加一行：「凡宣稱驗證數值/資料/ML/回測正確性的測試，須依 `docs/TEST_DESIGN_CHARTER.md` 說明 mutation 或等價可證偽設計；不適用時寫明原因。」TODO 每 Task 驗證欄只需繼承，不必複製章程。

Q4: PARTIAL — 我選 Composer 案為主、吸收 Codex/Gemini：TODO 必讀改為 `AGENTS.md`（執行端合約）+ `CLAUDE.md` 中治理摘要/已生成短 canonical 摘要，`ARCHITECTURE`/`DEVELOPMENT_GUIDE` 只在 SPEC §C 或觸及模組要求時按章節讀。避免重開事故面的關鍵是把短憲法摘要列入 gate/template 的固定輸入，且摘要由 `AGENTS.md`/`CLAUDE.md` 生成或人工同步檢查；不能改成「自由判斷要不要讀規則」。copilot-instructions 與 AGENTS 分叉是實際風險，所以不應以 copilot 作為執行端憲法來源。

Q5: PARTIAL — Codex C8（SPEC ID→TODO 追溯）我會降級為 MINOR/後續項；若 manifest 是唯一 ID 來源，現行 coverage 已覆蓋主幹，真正問題是 ID 可出現在無關文字（Gemini PREMISE-2/Composer C-12），不是必須立刻新增 spec-to-todo 模式。Composer C-6（RESULT vs ASSUMPTIONS 雙軌）是實際衝突但不是 BLOCKING：它會造成收尾格式分裂與檢查漏接，短期可用映射表修，不應阻擋 template 修補主線。Claude C-10（float32 canonical atol/rtol）我認為過度；數值容差不能跨任務硬給預設，應要求 SPEC 說明來源與驗證，不要提供可能被濫用的官方寬鬆值。Composer C-13/Gemini PREMISE-1 若稱 gate 必須語義確認則過度，但「grep verdict + 無未處理 BLOCKING + reconcile mapping」是合理最小閉合。U13 只應 MINOR，因它是誤擋可用措辭，不是放行壞文件。

Q6: U1 -> U2 -> U3 -> Q2閉合機制(CL-3/C-13/PREMISE-1) -> U11；緊接著做 Q1 adversarial 實跑條款與 Q4 憲法瘦身。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、CROSSEXAM brief、Claude/Codex/Composer review；Gemini 版依 CROSSEXAM 附錄摘要納入判斷。
TESTS_RUN: 文檔審閱任務，未執行測試；已用 `test ! -e handoffs/2026-07-04-template-crossexam-codex.md` 確認目標檔不存在後新增。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: DONE
