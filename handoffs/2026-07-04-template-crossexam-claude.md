# 第二輪交叉詰問 — Claude 回答（2026-07-04）

**Q1: AGREE（我提的，但自我加限定）** — 條款須優雅降級，否則 read-only 委員（agy）無法履行。最小文字：「§A 宣稱事實凡可低成本核實（grep 碼庫/讀真實檔/一行 python 對真資料）者，有 shell 的 reviewer 必須實際執行並附命令+輸出；無 shell 則該事實標『未經覆核』，其相關 finding 不得標低於 MAJOR、不得被 reconcile 以『作者已自證』理由降級。」Composer 本輪三個探針就是此條款的存在性證明——同樣的洞，純讀文件的 Codex/Gemini/我只能「推測可繞」，Composer 實跑直接定案。

**Q2: 組合 (a)+(c)，(b) 順手加** — (a) 是 prompt 層改動零腳本成本：adversarial 輸出每條 finding 加 `ID:` 與 `RECHECK:<可重跑命令或可 Ctrl+F 檢查步驟>`。(c) 擴充既有 `scripts/reconcile_stamps_check.sh`：驗 adversarial 檔內每個 [BLOCKING]/[MAJOR] ID 都在 reconcile 檔出現且附處置行（修補位置或 REJECTED+理由），缺一 → 拒發 token；實作 ~30 行 awk，成本低。(b) verdict grep 幾乎免費但只防「空 findings 檔」，單獨不充分。閉合重驗（原提出方重跑 RECHECK）已是章程 §B8，(a) 讓它變可執行。

**Q3: PARTIAL（自我校準）** — 全 SPEC 一律要 mutation 設計過重。收斂為：僅 §RISK 命中 (a)/(d) 時，§V 須含一行「正確性測試的可證偽設計（改壞會 FAIL 的機制）＋引用 docs/TEST_DESIGN_CHARTER.md」；其他任務不強制。這樣 RESULT 的 MUTATION_CHECK 在高風險任務有上游來源，低風險任務可正當填 N/A:reason。

**Q4: 選 (b) 為主幹、(c) 補充** — Composer 指出的分叉是決定性論據：TODO 生成端讀 copilot-instructions，但執行端（Codex/Cursor）實際遵守的是 AGENTS.md/.cursorrules——照不一致的憲法生成 §0 本身就是 bug。改法：階段 0 必讀 `AGENTS.md`（小、且是執行端真合約）；解耦 7 條/不可違反原則從 SPEC §C 帶入（SPEC 作者已引用）；ARCHITECTURE/DEVELOPMENT_GUIDE 改「SPEC §C 列出觸及模組 → 只讀對應章節」。防重開「沒讀憲法」事故：adversarial §2 加查「TODO §0 是否含解耦 7 條與不可違反原則的本任務相關子集」，把守門從 input 端移到 output 端。

**Q5: 反駁/校準**
1. Gemini DRIFT-1 措辭「合法文件**必** FAIL」過度——僅含資料結構詞的行觸發；方向對，併入 U1 即可。
2. Codex C8（spec-to-todo 第二模式）降級 SUGGESTION——現行慣例是 manifest 同時對 SPEC 與 TODO 各跑 coverage_check，主防線已在；新模式是加值不是缺口。
3. Codex C5 修法中「grep DONE 極性」要小心誤傷引用/討論文字——RESULT_TEMPLATE 已有 `claim-context: discussion` 標記慣例，機檢應豁免該區塊。
4. Composer C-6（雙軌）成立但範圍應收窄：RESULT_TEMPLATE 目前是 VERIFY_GATE 域產物，修法首選「明訂適用場景＋合約 sync 腳本納入 RESULT 錨點」，不是立即全域統一。
5. 我自己的 C-7（頭注複製）維持 MINOR，一行 usage 修掉即可，不值得進優先序。

**Q6: 優先序** — U1（FACT-RECEIPT 漂移+繞過）→ U2（§RISK↔§G 聯動）→ U9（finding 閉合機制 Q2 組合）→ U3（per-Task 分段機檢）→ U5/Q4（憲法瘦身+來源改 AGENTS.md）。快贏另列：U11（舊錨點 6 處全庫替換，純文件、零風險）。

STATUS: DONE
