# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-02 | **Branch**: **main**（同步，`901a8d9`） | **狀態**: **T1 完工已 push；帳本 0 OPEN；下一步＝T2**

## 🔴 使用者定死（最高優先）

1. **不能 100% 擋下 → 解決 95%，出問題再記錄**
2. **擋意外，不要在「阻擋蓄意」上撞牆**
3. **寫出來的工具就是要有強制使用的機制——不准靠紀律和記憶**
   ⇒ 提出治理改善時**同一輪必須回答「它怎麼被強制執行」**。答「大家記得照做」＝未完成。記憶 `feedback_tools_must_enforce`。
4. **狀態回報**（2026-08-02 使用者第 N 次糾正後定的可查核形式）：
   **寫【進行中】的唯一條件＝同一則回覆裡有實際工具呼叫，或給出可查的背景任務 handle（round_id／task-id／指令）。**
   兩者皆無 → 寫【停住】。使用者不必相信自述，看有沒有動作／編號即可查核。

## 🔴 使用者授予的暫時豁免（2026-08-02）

**T1–T8 這些任務，Claude 可自己實作，再由委員 review。** 不必每項派實作端。

## ▶ TODO（使用者定序）

| # | 任務 | 狀態 |
|---|---|---|
| ~~T1~~ | `GOV-DOC-CHECK-AT-WRITE` + `GOV-DEXT-TEMPLATE-KIND` | ✅ **完工** `901a8d9`（3 輪 review + 1 輪 consult） |
| **T2** | `P16-GATE-D1-STRUCTURED-VERDICT` | ⬜ `gate.sh` Verdict 正則過鬆，骨架佔位行即命中，**曾真 fail-open** |
| **T3** | 線 C 債務事件分檔 | ⬜ 設計已定（A′＋D 延伸，三家一致）；**D-002 草案已寫**`handoffs/20260802-D002-DRAFT.md`（過 dext 檢查），待三家審＋升入 `docs/`＋戳記 |
| T4 | `Task 3.2` → B5 完工 → P1-6 epic 結案 | ⬜ |
| T5 | `GOV-FORMAT-SSOT` 委員端 ＋ 併 `GOV-ID-NAMESPACE-CHECK` | ⬜ 動機證據見下「委員品質」 |
| T6 | `GOV-DOCS-STAMP-PROVENANCE` | ⬜ 須走凍結程序 §5 的 R |
| T7 | 清尾小票 | ⬜ 見下「T7 清單」 |

## T1 完工摘要（`901a8d9`）

**病根**＝格式檢查點在消費端不在產出端。**測試 512 → 563 passed（+51）**。

三輪 code review 的 finding 全部由原提出方（codex）確認真關閉：
`R1-P1-01` committee_run 另有第二份 parser 且開債早於完整檢查（＝audit sequence 367 孤兒債的真成因）／
`R1-P2-04` glob 跨 `/`／`R2-P1-01`＋`R3-P1-01` 兩次同型 fail-open。

## T7 清單（含本 session 新開）

- **`GOV-FAILCLOSED-DEP-GUARD`**（新）：檢查器把「依賴缺席」當「檢查不適用」。
  ⚠️ **主委原案已被 codex 實跑否決**（60 支 shell／命中 5／**真陽性 0**／且漏抓 `gate_check.sh:66`）。
  採委員改寫版：**tripwire 警告**（非硬 gate）＋**隔離 runtime mutation 當硬 gate**＋
  **可過期豁免 registry**（task-id/owner/expiry/理由/mutation test，每檔上限 2 條）＋`require` helper。
  範圍收窄為 `gov_check`／`gate`／`verify_hooks_health` 閉包。
- **`GOV-TESTHARNESS-SCRIPTLIST-SSOT`**（新）：隔離 repo 腳本清單散在 **4 份 fixture**，
  加一支腳本要人肉改四處且無機制提醒——本 session 因此紅了 4 次。
- `docs/` 既有 **24 檔**格式 backlog（多為 `Archived/*` 與 `*_SPEC_PLAIN*` 誤報）
- `P16-SPEC-STAMP-DELTA-STALE`／`GOV-XREF-SYNC`／B-6／B-8／`GOV-VERIFY-RECEIPT-RUNNER`／`P16-DEBT-ROSTER-BINDING`

## 委員品質觀察（具名，T5 動機證據）

**composer 本 session 三次同型缺陷**（格式／嚴格度寬鬆，非隨機）：
①線 C 輪 `來源摘要` 寫成 `path#（repo HEAD）` 非 hex digest → 該輪 abandon
②T1 review 判「可 commit」，而 codex 四條經主委獨立驗證**全部成立**
③fail-open consult 輪戳記寫成 `## RECONCILE-STAMP` 標題（正確＝`## 戳記`＋內文行）→ 該輪 abandon

## 📌 開工前必做

1. 稽核本檔／ROADMAP vs repo 實況
2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`；收集節點用 `reconcile_build.sh`
4. **stamp brief 必須帶 `stamp-target:` 欄**
5. **不要對 `docs/*.D-NNN.md` 跑 `reconcile_stamps_check.sh`**（必 rc=1，＝T6）
6. **`git push` 會跑整套 governance（約 177s）→ 一律丟背景**，否則被 2 分鐘 timeout 砍掉
