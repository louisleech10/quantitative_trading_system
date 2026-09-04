# HANDOFF — 當前任務狀態

**更新：2026-09-04｜狀態：`G3-D2` 實作中——**B-D0（Task D4.1）已 DONE 並 push（`49204458`）**。下一件＝**B-D1（D1.1–D1.7）**。唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`（收據見 §5、地雷見 §3）。**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **實作中**：B-D0 ✅（EntryPriceRef 側載＋`open_to_*` 取價＋label golden 機制）；待做 B-D1→B-D3→B-D4→B-D5 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN（可穿插） |

## 🔴 codex 於 B-D0 三度未交件——**根因未定**（勿當已知；四個假說已被反證）
B-D0 已以 composer＋grok 兩家 quorum 收斂（兩家皆零 P0／P1）。
🔴 主委曾斷言「全域 gstack review skill 劫持＝根因」，**該斷言已收回**：該 skill 存在兩個多月，
且 `gap3d2v2-x-review-r1`／`gap3d2todo-x-review-r1` 同樣載入它而正常交件。
已排除之四個假說與已知事實見 `docs/GAP3D2_IMPL_HANDOFF.md` §3（含反證命令）。
**下一批（B-D1）照常派三家**；若 codex 再度未交件，優先查「驗收命令的重量」
（B-D0 是本 epic 第一次程式碼審查：386 行 diff ＋ 兩支 mutation 驅動共約 15 次 pytest）。

## B-D0 收據摘要（完整見 `docs/GAP3D2_IMPL_HANDOFF.md` §5）
- `pytest tests/momentum/event_samples/` 365 passed；`-k "open_to or entry_price_ref"` 21 passed；`tests/api -k "event_analysis or event_batch_detail_dims"` 32 passed；golden `--check` 9/9 rc=0
- 生產碼 6 種具名 mutation 於 pytest 層全紅、還原後綠；golden 層 4/6 紅（2 項具名邊界 `B0-MUT-1`）
- hash 合法改變一次、`label_values` 逐位元組不變（`receipt-vi` 以 `git show HEAD:` 對跑 8 組，rc=0）

## 已知紅／不要誤判
- 派工命名／gate／commit trailer／白話守衛／**codex 不可用**／**派工期間守檔**：見 `docs/GAP3D2_IMPL_HANDOFF.md` §3。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`B0-REVIEW-1/2`、`B0-ATTRIB-1`、`B0-DOC-1`、`B0-GOLDEN-1`、`B0-MUT-1`（皆在
  `handoffs/reconcile/20260904-gap3d2-b0-review-r1/synth.md`，本機 gitignore）；
  `R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
