# HANDOFF — 當前任務狀態

**更新：2026-09-04｜狀態：`G3-D2` 實作中——**B-D0 與 B-D1 皆 ✅ DONE**。B-D1 之 review 於 **R6 停輪**（三家零 finding、verdict 一致）。下一件＝**B-D3（D3.1 two_stage）**。唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`（收據 §5、流程 §2、地雷 §3、裁定總表 §4）。**

## 🔴 新 session 第一件事＝開 B-D3

照 `docs/GAP3D2_IMPL_HANDOFF.md` §2 的七步走，**不得跳步**。B-D3 內容見 §1 表與
`docs/GAP3_EVENT_UX_TODO.D-006.md` Task D3.1：two_stage 兩段必填、`search_unlabeled`
未標籤路徑、深度 ≥1、去重 `all_with_uniqueness`。

```
session: 20260905-gap3d2-b3-review-r1    task-id: 20260905-GAP3D2-B3-REVIEW-R1
基底: 54d8eb8e
```

## B-D1 五輪閉合輪的教訓（帶進 B-D3，別重犯）

1. 🔴 **同一個欄位的驗證被逐輪手刻了四次**（型別 → 缺 → 值域），而契約裡本來就有
   `{"type": "int", "min": 0}`。**判準：值域是資料不是程式碼，一律從契約導出**
   （配方＝`EventSamplePipeline.int_field_domain()`）。B-D3 動任何欄位驗證前先看契約有沒有寫。
2. 🔴 **寫鬆的 over 向斷言比沒有 over 向更危險**：`assert x in (0, None)` 讓 `None` 也算過，
   把一個真缺陷吞掉整整一輪。over 向一律**精確值**。
3. 🔴 **「證明 X 來自 Y」的測試，若 X 在正反兩種實作下取值相同，它什麼也沒證明。**
   配方＝用一個**與硬編值相異**的來源值（divergent value）。本輪 mutation 抓到主委自己的假綠。
4. 🔴 **同一個數字在同一畫面有多處顯示**：修一處不夠，改完要 `grep` 掃全檔逐處判讀
   （h 那件事修了三輪才乾淨）。
5. 🔴 **收斂節點與修 findings 是兩件事，每輪都要做**（`reconcile_build` → attribution →
   `completeness --lock` → `debt_clear`）。債 OPEN 會擋下一次派工。
6. 🔴 **codex 兩度在主委鎖檔後改寫產出**（R3 一次、R5 兩次）⇒ reconcile 要重建。
   收件後**先比 sha 再鎖**；brief 裡直接要求「寫完即定稿」有效（R6 沒再發生）。
7. **閉合輪的判定權屬原提出方**：codex 對群集 D、grok 對群集 I 各拒絕代簽他家判定。
   兩次、不同家族 ⇒ 這是正確語意，不是個別習慣。

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | 實作中：B-D0 ✅、**B-D1 ✅**；待做 B-D3→B-D4→B-D5 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN（可穿插） |

## 使用者裁定（本 epic 期間）
- **三家委員不可跳過**（2026-09-04）：codex 若停滯，改用輕量驗收版 brief 重派，**不得**拿兩家 quorum 收斂。
- **白話須有施工流程即時進度**：`白話說明/現在做到哪.md`；每完成一步即更新。

## 已知紅／不要誤判
- `tests/api` 四條既有紅（`batch_alias`、`service_wiring event_timestamps`、兩條 `progress_rss`）
  ——codex R4 實跑全套 `820 passed / 4 failed` 確認皆非本票造成。
- `tsc --noEmit` 8 行既有債；`test_ic_deep_analysis` 並行 ERROR、單跑綠。
- `cd frontend` 會讓 shell 停在該目錄 ⇒ 之後 `venv/bin/python` rc=127；動作前先確認 `pwd`。
- golden `--check` 之 glob **必須加引號**，不加會被 shell 展成多參數而 rc=2（**假紅**）。
- 背景 `sleep N` 不保證真的睡滿；輪詢一律用 `until <條件>; do sleep N; done`。
- 具名殘留（B-D1 八條，三家全接受）：`B1-PRESET-1`／`B1-GOLDEN-2`／`B1-VERIFY-1`／
  `B1-LEGACY-1`／`B1-LEGACY-2`／`B1-DEPTH-1`／`B1-KIND-1`／`B1-WEAKTEST-1`；
  詳見 `handoffs/reconcile/20260904-gap3d2-b1-review-r6/synth.md`（本機）。
  其餘：`B0-REVIEW-1/2`、`B0-ATTRIB-1/2`、`B0-DOC-1`、`B0-GOLDEN-1`、`B0-MUT-1`；
  `R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
- 🔴 **收 epic 前必做**（殘留之觸發條件到期）：`pytest tests/governance` 全套（`B1-VERIFY-1`）、
  `B1-KIND-1` 定案（route 422 kind registry；三家一致「不得硬塞進契約 JSON」）、
  `B1-LEGACY-2` 之讀取點窮舉。
