# HANDOFF — 當前任務狀態

**更新**：2026-08-28　**分支**：main　**HEAD**：`af3be231`（＋本批收案 commit）

## 現在在哪

**GAP-3 事件型 UAT 缺口修補**：42 Task 中已完成 33 個；第一批到第九批皆已結案。
唯一入口 `docs/GAP3UX_IMPL_HANDOFF.md`；白話看板 `白話說明/GAP-3施工看板.md`。

**第九批（Phase 6，IC 止血閘）於 2026-08-28 結案**：Task 6.0–6.4；
五輪 review 10→3→4→5→3（非單調）＋兩輪 consult；mutation **29 條** `closure: CLOSED` 逐一等於；
pytest `-k "gap3_matrix or ic_feature_cap or ic_stop_gate_alive or ic_progress_fields"` 39 passed；
vitest 58 檔 334 passed；build rc=0；golden sha `163c4cec…` 未變。

## 🔴 本批最重要的三件事（不是程式碼）

1. **收案判準已改寫**（三家 consult 一致）：過渡止血型 Task **禁用「三家零 finding」當停輪條件**
   ——它與「每輪擴攻擊面」耦合，會製造非單調重輪。改用**請求形狀雙向矩陣**：
   每種請求寫法都要有 under-block（該擋擋住）與 over-block（**不該擋沒被擋**）各一條。
   前五輪的缺陷**全部藏在只有單向對照的格子裡**。
2. **brief 寫法紅線七條**已定案並存入記憶 `feedback_brief_writing_method`
   （assumed 須附否證觀測且**先跑**／攻擊面分「已排除·我沒查」兩欄／驗收禁寫聚合期望數／
   必答成對／禁零-finding 停輪／ID 一律 canonical／不設行數上限）。
3. **兩條我被推翻的宣稱**：「每輪都命中我標的 assumed」（實查僅第二、三、五輪，第四輪記的是相反）、
   「47 brief 是純程序摩擦」（僅檔名 proxy，內容含實質判斷）。**印象不得寫成事實。**

## 待辦（依序）

- [ ] **`templates/BRIEF_REVIEW_TEMPLATE.md`**——使用者已裁定「要做，但先與委員討論格式與內容」。
      諮詢輪 R2 已派（session `20260828-briefmethod-x-consult-r2`），待三家回報後設計、實作。
- [ ] **收 GAP-3 epic 前兩件**：`D-003` 戳記輪；使用者 **UAT B 段 13 項簽字**（未簽不收案）。
- [ ] **Phase 7（Task 7.0–7.7，9 個）** 尚未開工。
- [ ] 使用者未裁定：我對**使用者**講判斷時如何機械化區分「查過／沒查」
      （使用者已指出「靠紀律和記憶＝等於沒有遵守」，我尚未提出可執行的機械方案）。

## 具名殘留（全文見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.3）

`R-B9-1` 上限綁本機 8GB／`R-B9-2` 安全閥截斷真實 peak／`R-B9-3` 硬塞讀不出的 `features_path`
（**已知破口，不得說成沒有**）／`R-B9-4` 接線為原始碼層斷言非整頁 render／
`R-B9-5` 等價性靠單一共用點＋矩陣維持，耐久解法 `LoadPlan` 屬 GAP-6／D-00N／
`MEASURE-CANCEL-1` 無取消端點。三家裁定**全部可具名封存，無一須收案前解除**。

## 給下一個 session 的提醒

- `pytest tests/api` **會改寫** `data_cache/features/registry.json`——任何以「本機 latest 超過 cap」
  為前提的斷言都不可靠；測試須注入受控 entry。
- `tests/api` 全套 6 failed／10 errors **在 HEAD 乾淨 worktree 亦紅**（HEAD 為 15/18），非本批造成。
- 背景任務的「完工通知」本 session **誤報兩次**；等長工作請用哨兵等自訂結束標記，別信通知。
