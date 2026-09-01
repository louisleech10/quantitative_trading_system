# HANDOFF — 當前任務狀態

**更新：2026-09-01｜狀態：GAP-3 UAT 進行中（使用者驗到 B12），程式面 42 Task 全數落地**

## 現在的阻塞＝使用者驗收，不是實作
- B1–B12 使用者已走過並在 `白話說明/GAP-3驗收清單.md` 標記；**下一步是 B13–B20**。
- 收 epic 之條件已改變（見下方 D 票），**不是「簽字即收案」**。

## 驗收抓到的票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D1` 匯出前篩選正反例共用一組條件 | **OPEN**。修法方向使用者已裁（正反例獨立條件／深度改直接問使用者／purge 取大者）；動 SPEC Task 2.1／2.1b／1.9 須開延伸檔 `D-006`。**排程待使用者裁定**：擋在結案前／另開票＋先止血／只止血 |
| `G3-D2` 五維度三類值永久灰著 | **OPEN**。使用者裁定不接受永久灰著 ⇒ UAT B3 在三者全交付前一律記未完成 |
| `G3-D3` 匯出 CSV 無法回灌 | CLOSED（本批） |
| `G3-D4` 後端 dotted 還原漏 `lookahead_bars_declared` | CLOSED（本批；mutation 已驗可證偽） |
| `G3-D5` 答案窗預填一個驗證自己會拒的 0 | CLOSED（本批） |

## 本批（commit：feat(gap3) 契約 CSV）做了什麼
- `/search`「導出CSV檔案（可回灌）」改契約欄名 CSV：新 `frontend/src/lib/eventContractCsv.ts`、
  `eventExport.ts` 加 `includeUnlabeled`；零對映可直接上傳。
- 後端 `_nested_fields()` 改**從契約導出**（原手寫清單漏欄）。
- 答案窗宣告在「檔內無可解析未來欄」時留空、改寫提示。
- `gen_uat_samples.py` 加第五個樣本 `uat_samples/events_contract.csv`，且**產出前讓後端自己收一次**。
- B12 turbopack 已修並**用 `npm run dev` 實跑驗過**（`/ic-analysis` 200）。

## 已知紅／不要誤判
- `tests/api` 既有紅 4 條（batch_alias／ichc_event_timestamps／progress_rss_fields×2）。
  後兩條**只在整包跑時紅、單跑 7 passed**＝event-loop 污染，已用 `--ignore` 排除法確認與本批無關（`G3-R11`）。
- `tsc --noEmit` 8 行既有債（FactorReturnChart.test／useFeatureFactory.batchDate.test），非本批。

## 下一步（依序）
1. 等使用者驗 B13–B20 的回報。
2. 使用者裁定 `G3-D1` 排程後，開 `D-006` 走完整管線（SPEC 延伸＋TODO＋三家 adversarial）。
3. `G3-D2` (c) 最近可做：逐組合 exact golden（§G G-3 擴充）。
