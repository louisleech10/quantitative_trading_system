# HANDOFF — 當前任務狀態

**更新：2026-09-05｜狀態：`G3-D2` 實作中——**B-D0／B-D1／B-D3 皆 ✅ DONE**。B-D3 之 review 於 **R4 停輪**（三家零 finding、verdict 一致）。下一件＝**B-D4（D4.2＋D4.3）**。唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`（收據 §5、流程 §2、地雷 §3、裁定總表 §4）。**

## 🔴 新 session 第一件事＝開 B-D4

照 `docs/GAP3D2_IMPL_HANDOFF.md` §2 的七步走，**不得跳步**。B-D4 內容見 §1 表與
`docs/GAP3_EVENT_UX_TODO.D-006.md` Task D4.2／D4.3：
13 對矩陣＋`rejected_pairs`／`pair_rejected` UI＋成對可行域與兩上界＋三層 oracle；
k 參數化（seeds 去 k、雙值揭露）＋`event_label_scan` 網格
（背景 task、`to_thread`、timeout、progress、partial；**benchmark 子步先於凍結 cap**）。

```
session: 20260906-gap3d2-b4-review-r1    task-id: 20260906-GAP3D2-B4-REVIEW-R1
基底: <B-D4 實作 commit>
```

🔴 **B-D4 是本票最大的一批**（兩個 Task、13 對矩陣、掃描網格、三層 oracle）。
D4.3 之 ⓪b 明列「benchmark 子步**先於**凍結 cap」——先量真實單格耗時再定
`scan_grid_max_runs`，不要先寫死 121。

## 🔴 待使用者裁定（B-D3 交回，主委不代決）

`B1-VERIFY-1`（`pytest tests/governance` 全套未跑）之三值理由已由 `cost` 更正為
**`blocked-by`（既有 g7）**——三家一致認為那是誠實分類。
**但觸發條件「既有 g7 修好」不在本 epic 範圍 ⇒ 目前無人推進。**
codex 明確交回：**是否另立 governance ticket？** 治理排程屬使用者裁定，我不自行處置。

## B-D1／B-D3 七輪閉合輪的教訓（帶進 B-D4，別重犯）

1. 🔴 **同一欄位的驗證被逐輪手刻四次**（型別 → 缺 → 值域），而契約裡本來就有
   `{"type":"int","min":0}`。**值域是資料不是程式碼，一律從契約導出**
   （配方＝`EventSamplePipeline.int_field_domain()`）。
2. 🔴 **over 向斷言禁 `in (...)`，一律精確值**——`assert x in (0, None)` 讓 `None` 也算過，
   把一個真缺陷吞掉整整一輪。**寫鬆的 over 向比沒有 over 向更危險。**
3. 🔴 **「證明 X 來自 Y」之測試——判準已升級三次，用最終版**：
   - v1（B-D1 R6）：用 divergent value。**不夠**——我用 `['label']` 這種明顯不同的
     hardcode 去 mutation，漏掉「完整現值 hardcode」。
   - v2（B-D3 R2）：divergent 必須來自「把**來源本身**換掉」，不是「把值改小」。
   - **v3（B-D3 R3，最終）：要證明**模組層常數**之來源，必須把來源模組換掉再重新 import**
     （`vi.doMock` ＋ `vi.resetModules()` ＋ fresh `import`），看常數跟不跟著變。
     只餵變異輸入給導出函式，證明的是**那個函式**，不是**那個常數**。
   - **mutation 之 hardcode 字面應由驅動自己從來源現值產生**，否則會退化成弱 mutation。
   - 三家 R4 裁定：`vi.doMock` 足以測；**不要為此在 production 開 DI seam**（過度反應）。
4. 🔴 **同一個數字／欄集在多處顯示或使用**：修一處不夠，改完 `grep` 掃全檔逐處判讀
   （h 那件事修了三輪；CSV header 那件事三家全員命中）。
5. 🔴 **`fact-verified` 之收據必須是「最後一次改動之後」跑的**。
   我在 B-D3 R1 把「寫測試檔**之前**跑的 `tsc` 數字」寫進 brief ⇒ 假收據被 grok 逐字打穿。
6. 🔴 **收斂節點與修 findings 是兩件事，每輪都要做**（`reconcile_build` → attribution →
   `completeness --lock` → `debt_clear`）。債 OPEN 會擋下一次派工。
7. 🔴 **收件後先比 sha 再鎖**：codex 曾三度在鎖檔後改寫產出（B-D1 R3 一次、R5 兩次）。
   brief 裡寫「寫完即定稿」有效——此後未再發生。
8. **閉合輪的判定權屬原提出方**：codex 對群集 D、grok 四次拒絕代簽他家判定。
   **這是正確語意，不是個別委員的習慣。**
9. 🔴 **三家 verdict 不一致時取聯集全修**，不投票、不以多數壓過單一家之阻塞判定。
   **且不帶已知 P2 進下一批**（B-D3 R2／R3 兩次裁定）——留著＝把已知假綠帶進更大的面。
10. **殘留理由沿用前要重新檢視前提**：`B1-VERIFY-1` 之 `cost` 是我從 B-D1 沿用的，
    三家在 B-D3 都撞到 g7 之後，那個理由已經不誠實 ⇒ 改 `blocked-by`。

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | 實作中：B-D0 ✅、B-D1 ✅、**B-D3 ✅**；待做 B-D4→B-D5 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN（可穿插） |

## 使用者裁定（本 epic 期間）
- **三家委員不可跳過**（2026-09-04）：codex 若停滯，改用輕量驗收版 brief 重派，**不得**拿兩家 quorum 收斂。
- **白話須有施工流程即時進度**：`白話說明/現在做到哪.md`；每完成一步即更新。

## 已知紅／不要誤判
- `tests/api` 四條既有紅（`batch_alias`、`service_wiring event_timestamps`、兩條 `progress_rss`）
  ——codex 於 B-D1 R4 與 B-D3 R1 兩度實跑全套確認皆非本 epic 造成（826 passed / 4 failed）。
- `tsc --noEmit` **8 行**既有債（`FactorReturnChart.test.tsx` 4／`useFeatureFactory.batchDate.test.ts` 4）。
- `pytest tests/governance` **卡在既有 g7**（三家 B-D3 R2／R3 皆撞到）⇒ `B1-VERIFY-1`。
- 🔴 `cd frontend` 會讓 shell 停在該目錄 ⇒ 之後 `venv/bin/python` rc=127；
  **composer 於 B-D3 R2 因此把 mutation 誤報成 GREEN**——mutation 腳本一律在**專案根**跑。
- golden `--check` 之 glob **必須加引號**，不加會被 shell 展成多參數而 rc=2（**假紅**）。
- 背景 `sleep N` 不保證真的睡滿；輪詢一律用 `until <條件>; do sleep N; done`。
- 具名殘留：B-D3 三條（`B3-OPTIONAL-COL-1`／`B1-VERIFY-1`／`B3-WIRING-1`）；
  B-D1 八條（`B1-PRESET-1`／`B1-GOLDEN-2`／`B1-VERIFY-1`／`B1-LEGACY-1`／`B1-LEGACY-2`／
  `B1-DEPTH-1`／`B1-KIND-1`／`B1-WEAKTEST-1`）；
  B-D0 七條（`B0-REVIEW-1/2`、`B0-ATTRIB-1/2`、`B0-DOC-1`、`B0-GOLDEN-1`、`B0-MUT-1`）；
  其餘 `R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
  詳見各輪 `handoffs/reconcile/*/synth.md`（本機）。
- 🔴 **收 epic 前必做**：`B1-KIND-1` 定案（route 422 kind registry；三家一致「不得硬塞進契約 JSON」）、
  `B1-LEGACY-2` 之讀取點窮舉、`B1-VERIFY-1`（待使用者裁是否另立 ticket）。
