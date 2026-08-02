# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-02 | **Branch**: **main**（同步，`f8922dd`） | **狀態**: **票 `GOV-STAMP-TASKID-INJECT` 完工已 push；帳本 0 OPEN；下一步＝依 T1–T8 逐項做完**

## 🔴 使用者 2026-08-02 定死（最高優先，含一條新的）

1. **不能 100% 擋下 → 解決 95%，出問題再記錄**
2. **擋意外，不要在「阻擋蓄意」上撞牆**
3. 🔴 **新增**：**寫出來的工具就是要有強制使用的機制——不准靠紀律和記憶**
   ⇒ 提出任何治理改善時，**同一輪必須回答「它怎麼被強制執行」**（掛 hook／進 `gov_check.sh`／gate 拒發 token）。
   答案若是「大家記得照做」＝該提案未完成。記憶 `feedback_tools_must_enforce`。

## 🔴 使用者授予的暫時豁免（2026-08-02）

**T1–T8 這些任務，Claude 可以自己實作，再由委員 review。** 不必每項都派實作端。
（原規則＝中/大任務執行端寫檔、Claude 只讀 diff；本輪明示豁免。）

## ▶ TODO（使用者定序，逐項完成）

| # | 任務 | 備註 |
|---|---|---|
| **T1** | `GOV-DOC-CHECK-AT-WRITE` ＋ `GOV-DEXT-TEMPLATE-KIND`（**合併一票**） | 設計已定，見下節 |
| **T2** | `P16-GATE-D1-STRUCTURED-VERDICT` | `gate.sh:246` Verdict 正則過鬆，**骨架佔位行即可命中，曾真的 fail-open**；B3 遺留必做項 |
| **T3** | **線 C** 債務事件分檔 | 立論要用對的那個，見下節；**codex 從未對分檔表態**，開工先讓三家表態 |
| **T4** | `Task 3.2` mutation 探針＋既有測試回歸 | 完成後 **B5 完工 → P1-6 epic 結案** |
| **T5** | `GOV-FORMAT-SSOT` 委員端部分 ＋ 併 `GOV-ID-NAMESPACE-CHECK` | 動 `cx_run.sh` 屬大任務；T1 做完後範圍會縮小 |
| **T6** | `GOV-DOCS-STAMP-PROVENANCE` | 修它要走凍結程序 §5 的 R（整份重審），建議再累積實戰案例 |
| **T7** | 清尾小票 | `P16-SPEC-STAMP-DELTA-STALE`／`GOV-XREF-SYNC`／B-6／B-8／`GOV-VERIFY-RECEIPT-RUNNER`／`P16-DEBT-ROSTER-BINDING` |
| **T8** | Compact 前置＋交接 | — |

## T1 設計（已定案，**不要重推**）

病＝**格式檢查點在消費端不在產出端**（`GOV-FORMAT-SSOT` 症狀 B 原文）。本 session 實證燒 4 輪，B4 實證燒 5 輪（該批 38%）。

1. `scripts/template_check.sh` 新增 **`dext` kind**：錨點依 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` §2
   （`BASE:`／`PREDECESSOR:`／`改什麼:`／`為什麼:`／`## 觸及面宣告`／`## 內容`／`## 戳記`）
2. **把 brief 合規檢查從 `cx_run.sh:30-79` 抽成 `scripts/brief_conformance_check.sh`**，
   `cx_run.sh` 改呼叫它 ⇒ **一份實作、兩個呼叫點**（禁複製邏輯，那是第二真相源）
3. 新增 `scripts/doc_format_precheck.sh`，掛 **PostToolUse `Edit|Write`**（`.claude/settings.json:177` 已有該區塊）：
   依路徑判型別（`docs/*.D-NNN.md`→dext／`*SPEC*`→spec／`*TODO*`→todo／含 `^brief-kind:`→brief），
   跑對應檢查，失敗以 exit 2 把訊息回灌 Claude context ⇒ **寫完當下就紅，不必等派工**
4. `gate.sh` 對 `--spec <*.D-NNN.md>` 路由到 `dext`（現況走 `spec` → **永遠拒發 token**）
5. 既有 gate/dispatch 檢查**全部保留不動**＝defense-in-depth（寫檔時軟提醒、派工時硬擋）

## T3（線 C）的正確立論——**不是效能**

出處 `handoffs/reconcile/20260801-p16-b5-t31-clos-supp/synth.md`：

- 真正的病＝為了達成效能驗收，grok 加了 **marker prefilter**，而它會**吞掉壞行**（違反已簽核的 fail-closed）。線 A 已移除該 prefilter 並在 `_debt_ledger_core.py:87` 留下禁令註解。
- codex 開的判準是「**使單次成本與 audit 行數無關**」，**不是「要更快」**。
- 分檔的價值＝掃描量固定在債務事件數 ⇒ **prefilter 的誘惑永久消失**。
- ⚠️ **效能立論已被實測推翻**（46–64ms，SPEC 只要求 <100ms）`REF:docs/P16_COMMITTEE_DEBT_SPEC.D-001.md`；
  92% 散文**不可刪**（含 JSON 沒有的 `intent`／`risk`／`facts_asked` 等欄）；`gate_deny` 僅 1.2%。
  **拿效能當理由會被打穿**。草案 `handoffs/20260802-LINEC-AUDIT-SPLIT-SPEC-DRAFT.md` 的 §1–§2.4 可用，§3 已過時。

## 結構澄清（上一版交接寫錯過）

**B5 不是一張票，是 P1-6 的最後一個施工批次＝`Task 3.1 + Task 3.2`**（`docs/P16_COMMITTEE_DEBT_TODO.md:100`）。
Task 3.1 實作時被 code review 打回，拆成 線 A ✅／線 B ✅／**線 C ❌**。
⇒ **B5 完工 = 線 C ＋ Task 3.2 都做完**；`GOV-STAMP-TASKID-INJECT` 不在 B5 內（是 backlog 獨立票）。

## 📌 開工前必做

1. 稽核本檔／ROADMAP vs repo 實況
2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`；收集節點用 `reconcile_build.sh`
4. **stamp brief 現在必須帶 `stamp-target:` 欄**（`GOV-STAMP-TASKID-INJECT` 新增的閘已生效）
5. **不要對 `docs/*.D-NNN.md` 跑 `reconcile_stamps_check.sh`**（必 rc=1，屬已知缺陷 `GOV-DOCS-STAMP-PROVENANCE`；
   要驗核可請對 `handoffs/reconcile/<session>/synth.md` 跑）
