# HANDOFF — 當前任務狀態

**更新：2026-09-03 13:30｜狀態：`G3-D2` v1（D-001／D-006）三家戳記後，使用者白話閘**四裁定**（A 併入預測型／IC 三種報酬選項依深度預設、D4.1 提前 D0／k、h 掃描網格／k 註記）已寫回為 **v2**（commit 見 log）；v2 三家 review r1 派工中（session `20260903-gap3d2v2-x-review-r1`）→ 戳記 → **停下**（實作待使用者放行）。白話：`白話說明/G3-D2灰色項目說明.md` §二之二。**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **規格與清單凍結中**：D-001（`handoffs/reconcile/20260903-gap3d2-x-review-r4/synth.md` 三家 APPROVED＋鏡像）；D-006（`…gap3d2todo-x-review-r5/synth.md`，body sha `327aadac…`；戳記待三家）。實作未開工。 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN |

## 待使用者裁（白話檔 §四）
(甲) C 名實只改揭露；(乙) 契約 k 欄保留必填恆 0；(丙) k 軟上限 10。殘留：既有 9 批不能與隨機對照批比較（無 `label_rule`）；產生器批無 api 落檔入口（另票）。

## 下一步（使用者點頭後）
1. TODO 戳記三家 APPROVED ⇒ 鏡像至 D-006 `## 戳記`、commit＋push；`reconcile_stamps_check.sh` 兩份皆 PASS 才算 FROZEN。
2. 實作 B-D1（Claude 自任；D-006 D1.1–D1.6）→ 三家 code review 至閉合 → B-D2 → B-D3 → B-D4 → B-D5（串行）。
3. 派工規約：session `<YYYYMMDD>-<epic>-<b<n>|x>-<kind>-r<N>`、task-id＝大寫；派前 `gate.sh dispatch` mint；三家齊交之 round 以 `debt_clear.sh --round-id … --session … --lock` 銷帳；composer 失敗 ⇒ `--abandon --kind collection-failed` → mint → `ROUND_ID=<id> cx_run.sh composer …`。
4. commit 含 scope 外路徑須 `Governance-Scope:` trailer；`handoffs/` gitignore；白話新檔須登記 `scripts/plain_docs_sync_check.sh`。

## 已知紅／不要誤判
- 九個 ABANDONED rounds（composer CLI 整晚失敗）；產物齊全、completeness PASS。
- `reconcile_cluster_attribution_check.sh` 對前輪 ID 誤報「未被引用」＝假警。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
