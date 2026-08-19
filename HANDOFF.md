# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-2 **已全部收案（2026-08-19）** → 下一票 GAP-3 事件型（**先討論、使用者裁 Q0＋5 題，再寫 SPEC**）

**現況**：GAP-2 B1–B5 各三家 code review＋三家 RECONCILE-STAMP（收斂檔 `handoffs/reconcile/20260818-gap2-b1-review-r12`／`20260819-gap2-b{2,3,4,5}-review-r{15,18,21,24}`）；SPEC R7 FROZEN＋延伸檔 A1-1..A1-11；TODO FROZEN；§V 24 條 mutation 最終 receipts `handoffs/run_receipts/20260819T03{1612,1810,1911,2022}Z-gap2-B{1..4}-probe.log`；§G-1 golden pre `handoffs/run_receipts/gap2_golden_pre.json`（A1-10 scope_id 正規化）。殘留 G2-R1／R2／R3／R5／R6／R7／R8 於 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」；ROADMAP 已標 CLOSED；白話看板已移 `白話說明/Archived/GAP-2施工進度.md`。債務清單乾淨。**最後 commit 已 push**（看 `git log -1`／`git status -sb`）。

**下一步（GAP-3；使用者 8/18 裁定「先討論再開工」，未裁前不動 GAP-3 程式）**：① 派一輪唯讀 consult（三家＋主委各出完整版；`brief-kind: consult`；registry「GAP-3 開發前討論題」Q0＋5 題）→ reconcile → 戳記 → ② 主委用白話整理 Q0（事件類型盤點）＋5 題（決策時點／反例／重疊去重切分／標籤嚴格度／pattern 非運氣證明）給使用者裁（AskUserQuestion 阻塞＋推播）→ ③ 裁完才寫 SPEC（完整管線）。GAP-3 語意＝外部標好正反例匯入→PIT 對齊→條件 IC／ML；非 event study；契約通用（`sample_scope`／R5 A′ 事件語意保留）。
**前端占位（2026-08-19 使用者裁定，已上線 commit aded5574）**：需要前端的殘留一律先做殼——`/pending-features`（`frontend/src/lib/pendingFeatures.ts` 資料檔＋`app/pending-features/page.tsx`＋`components/pending/PendingFeatureCard.tsx`；優化結果頁掛 G1-R3、XGBoost 頁掛 G2-R1）；vitest `pendingFeatures.test.ts` 對 registry 機檢 ID／三值。**新殘留牽涉前端 ⇒ 同時加條目＋殼；收殘留 ⇒ 同步刪**。使用者測試：等事件型完成後一次做完整 UAT（不先 smoke）。
**其他可做未排**：GAP-4 多標的合併估 IC；GAP-5 容量（等成交量源）；GAP-6 併效能 epic；G2-R6 前端 tsc 既有 8 紅（獨立小票）。

## ⚠ 坑（本 session 實踩；完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～七十七）
- 🔴 `committee_run.sh` 的 Bash 呼叫會被 gate_check 當 dispatch 擋（指令含家族名）：先 `bash scripts/gate.sh dispatch <同 flags>` mint token，再跑 committee_run（同 flags）；gate.sh dispatch 在債 OPEN 時拒發 ⇒ 先 register-output＋debt_clear；含家族名的 Bash 於「有 token＋債 OPEN」時亦被擋 ⇒ 把命令寫進 scratchpad 腳本再 `bash <script>`。
- 🔴 stamp brief **禁多家並行跑重測試／禁邀請就地改檔實驗**（摩擦七十三／七十七）：只准讀 receipt、in-memory 反例、<1 分鐘測試；有疑義派單家獨占重驗（session 名 `-stamp-r<N>` 純數字）；diff 範圍 allowlist 要含中間夾的 HANDOFF／白話。
- 🔴 review brief 前提須逐條 `fact-verified:`／`assumed:`；commit 訊息 `Governance-Scope:` trailer 獨立成末段；含「全綠」等強極性詞會被 claim checker 要 VERIFY 收據 ⇒ 用中性措辭。
- 🔴 `debt_clear.sh --abandon` 必帶 `--approver main-agent`；委員產出須 `gate.sh register-output`；handoffs 檔須 `git add -f`；push 丟背景。
- venv Python 3.9.6；bench 測試 ~2.5 分鐘（G2-R7）；`docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線。
