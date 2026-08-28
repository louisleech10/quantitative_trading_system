# HANDOFF — 當前任務狀態

**更新**：2026-08-28　**分支**：main　**HEAD**：見 `git log --oneline -1`

## 現在在哪

**GAP-3 事件型 UAT 缺口修補**：42 Task 中已完成 **33** 個；第一批到第九批皆已結案。
**下一批＝B10（Phase 7 全棧接線，9 個 Task）**。
唯一入口 `docs/GAP3UX_IMPL_HANDOFF.md`（**先讀 §1 稽核 → §2E B10 是什麼**）；
白話看板 `白話說明/GAP-3施工看板.md`。

## 🔴 接手第一件事

1. 照 `docs/GAP3UX_IMPL_HANDOFF.md` **§1** 跑開工前稽核（期望值已更新為第九批結案後之實測）。
2. 讀 **§2E**。🔴 **B10 的座標偵察沒有做**——§2A–§2D 都有座標表是因為上個 session 先偵察過，
   §2E **刻意留白**，因為填了就是編的。**偵察是接手的第一件工作**，
   且依規約 **Claude 與三委員平行各做一份**，不是 Claude 先產、委員後審。

## 收案判準（B9 之後改寫，**不要退回舊判準**）

🔴 **禁用「三家零 finding」當停輪條件**——三家 consult 一致廢止
（`handoffs/reconcile/20260828-gap3ux-b9-consult-r1/synth.md`）：它與「每輪擴攻擊面」耦合，
會製造非單調重輪（B9 實測 10→3→4→5→3）。改用可列完的判準：
① **雙向矩陣**：每種輸入形態都有 under（該擋擋住）與 over（**不該擋沒被擋**）各一條可重跑測試；
② mutation `closure=CLOSED` 且紅集合**逐一等於**；③ 具名殘留皆有三值理由；
④ 上輪 P0／P1 原反例 CLOSED **且**本輪對矩陣雙向探針無新 P0／P1。

🔴 **B9 五輪的病根**：我只測「該擋的有沒有擋住」，從沒測「不該擋的有沒有被誤擋」；
前五輪的缺陷**全部藏在只有單向對照的格子裡**。B10 的 Task 7.2 也是機械閘，同一個坑會再出現。

## 🔴 派工單寫法：`templates/BRIEF_REVIEW_TEMPLATE.md`（**紀律型，無機械閘**）

派 review／consult 前**自己開那份範本逐欄對一遍**——**沒有任何東西會提醒你**。
七條紅線：`assumed` 須附否證觀測且**先跑**／攻擊面分「已排除·**我沒查**」兩欄／
驗收禁寫聚合期望數／必答成對／禁零-finding 停輪／ID 一律 canonical／不設行數上限。

**為什麼沒有閘**（2026-08-28 使用者裁定，別重試）：三種綁法實測皆失敗——
全域綁進 `brief_conformance_check.sh` ⇒ 治理測試紅 13→9→16；
路徑分流只擋真實 `handoffs/` ⇒ **49 條紅**（治理測試本身就寫進真實 `handoffs/`）；
共用 test helper 收斂後再開閘 ⇒ 窮舉為 **26 檔** retrofit。
使用者：「兩個都沒辦法機械解決，你自己知道要用就好。」

## 待辦

- [ ] **B10 偵察 → 實作 → 三家 review → reconcile → 閉合輪**
- [ ] **收 GAP-3 epic 前兩件**：`D-003` 戳記輪；使用者 **UAT B 段 13 項簽字**（未簽不收案）
- [ ] 動過 `scripts/` 者收 epic 前跑 `bash scripts/gov_check.sh --no-probe`（丟背景，十分鐘級）

## 具名殘留（全文見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.3）

B9 新增 `R-B9-1..5`（上限綁本機 8GB／安全閥截斷真實 peak／
`R-B9-3` **已知破口，不得說成沒有**／接線為原始碼層斷言／等價性靠單一共用點＋矩陣維持，
耐久解法 `LoadPlan` 屬 GAP-6 或 D-00N）。
`MEASURE-CANCEL-1` 無取消端點。三家裁定**全部可具名封存**。
B10 會解除的：`R-B7-1`／`R-B3-3`（Task 7.0b）、`R-B8-1`（Task 7.5）、`R-B2-2`（全棧接線）。

## 給下一個 session 的坑

- `pytest tests/api` **會改寫** `data_cache/features/registry.json`——任何以「本機 latest 超過 cap」
  為前提的斷言都不可靠；測試須注入受控 entry。
- `tests/api` 全套 6 failed／10 errors **在 HEAD 乾淨 worktree 亦紅**（HEAD 為 15/18），非 B9 造成。
- 背景任務「完工通知」本 session **誤報兩次**；等長工作請用哨兵等自訂結束標記，別信通知。
- 治理測試與真實 `handoffs/` 目錄天生耦合——任何想用「路徑分流」豁免測試的設計都行不通。
