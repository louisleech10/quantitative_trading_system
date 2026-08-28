# GAP-3 事件型分析 — UAT Checklist（Task B5.3；W9）

> 每項＝步驟＋實跑命令＋rc＋預期畫面／輸出＋**使用者簽字欄**。使用者未簽字 ⇒ epic 不收案（TODO B5.3 邊界②）。
> UAT 發現缺陷 ⇒ 回對應批修，不在此打補丁繞過（TODO B5.3 邊界①／C9）。
> 真實流程：匯入 → 對齊 → 三表 → 全 K 線 → 報告；bars 一律真實 kline（`data_cache/feature_klines/kline_cache.h5`）。
>
> 🔴 **B 段已於 2026-08-29 重寫並移至白話版**（見下方 §B）。B5 時代那份的兩項在 B7 之後
> **照做必失敗**——`label_value` 已不寫進匯出檔、匯出端之答案窗選擇器已移除（Task 4.1②／§D-3′）。

## A. 機械前置（主委實跑；rc 欄由主委填、receipt 路徑可稽核）

> **主委實跑 2026-08-29**（B10 收斂後），receipt＝`handoffs/run_receipts/20260829T000000Z-gap3-uat-sectionA.log`。
> 🔴 舊版（2026-08-22，receipt `20260822T040000Z-gap3-b5-uat-sectionA.log`）之數字已被 B6–B10 推進，不再適用。

| # | 步驟 | 命令 | rc | 結果 |
|---|---|---|---|---|
| A1 | 事件樣本層全套 | `venv/bin/python -m pytest tests/momentum/event_samples/ -q` | 0 | 345 passed |
| A2 | state-counter 算子 | `venv/bin/python -m pytest tests/momentum/feature_engineering/ -q -k state_counters` | 0 | 17 passed |
| A3 | GAP-1 防線不退步 | `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation -q` | 0 | 272 passed |
| A4 | API 十九項 GAP-3 選擇器 | `venv/bin/python -m pytest tests/api -q -k "<見 receipt 該行>"` | 0 | 279 passed |
| A5 | 前端 build | `npm --prefix frontend run build` | 0 | build 成功 |
| A6 | 前端 vitest 全套 | `npm --prefix frontend test -- --run` | 0 | 68 files／419 passed |
| A7 | 白話同步守衛 | `bash scripts/plain_docs_sync_check.sh` | 0 | 受管 13 檔皆同步 |
| A8 | IC 主線行為不變（G-1） | `venv/bin/python scripts/gap3_freeze_golden.py --check` | 0 | CHECK PASS sha `163c4cec…e463` |
| A9 | 型別關卡（`build` 不涵蓋測試檔） | `npx --prefix frontend tsc --noEmit -p frontend/tsconfig.json` | 1 | **8 行既有債**（`FactorReturnChart.test.tsx` 4＋`useFeatureFactory.batchDate.test.ts` 4）；GAP-3 相關檔 0 錯 |
| A10 | 破壞測試（全批） | `venv/bin/python handoffs/gap3ux_b10_mutations.py <out>.json` | 0 | **58 條 `closure=CLOSED`**、verdict 全 PASS、六個 baseline 還原後皆空紅 |
| A11 | 萬級規模 receipt（B5 實跑，未重跑） | `venv/bin/python scripts/gap3_import_scale.py --n 10000 --write` | 0 | `gap3_import_scale.json`：n_events 10000／direct 76.978s／api_path 0.382s／peak_rss 496.4MB |

## B. 使用者逐項驗收 — **見白話版**

🔴 **唯一來源＝[`白話說明/GAP-3驗收清單.md`](../白話說明/GAP-3驗收清單.md)**（20 項，逐項附「你做什麼／
應該看到什麼／不是這樣代表什麼」）。**本檔不再保留第二份步驟表**——B5 那份與現況不符，
而兩份並存必然漂移（本 epic 已為副本漂移付過多次代價）。

涵蓋面（白話版之編號）：

| 段 | 項 | 對應交付 |
|---|---|---|
| 匯出（`/search`） | B1–B6 | 匯出面板、篩選與筆數（2.1–2.3）、五維度 UI（7.1）、七項揭露（7.3）、匯出檔形狀（4.1／4.2）、IC decay 邊界（7.4） |
| 匯入（`/data-preparation`） | B7–B12 | JSON 匯入與逐列拒收（1.1–1.4）、CSV 逐欄對映（1.5–1.7）、答案窗宣告（1.9／1.11／1.12）、舊格式雙向擋、批次刪除（3.1–3.3） |
| 分析（`/ic-analysis`） | B13–B20 | 事件模式入口、批次事實 vs 分析參數兩區（7.6）、參數不回寫、三組報酬表（7.5）、條件 IC 可算（7.0b）、run 涵蓋期對證（7.7）、特徵數止血閘（6.1） |

🔴 **雙向要求**：B11（舊格式）與 B18（run 涵蓋期）**兩個方向都要試**——
只試「該擋的有沒有擋住」的話，一個「永遠擋」的實作也會看起來正常（B9 五輪重工之病根）。

## C. 殘留（登記 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」；三值理由）

| 項 | 為何現在不做 |
|---|---|
| G3-R9 辨別表在 `/ic-analysis` 事件模式只顯示 `not_computed：no_model_scores_in_event_pipeline` | `blocked-by:分數來源＝pattern 橋／ML 層（成熟度地圖之不完整層）；匯入管線不產分數`（registry 已登記；`/pending-features` 有占位） |
| G3-R10 事件匯入大檔串流／背景 worker（現＝50MB 上限＋CSV 分塊解析） | `user-ruling:W10 記錄型不設門檻；效能門檻須 SPEC amendment` |
| G3-R11 `tests/api` 既有紅（B5 前即紅；乾淨 HEAD 同紅） | `blocked-by:非 GAP-3 模組；另開票處理` |
| `R-GOV7-1` G-7 scope 淨差長期紅 | `user-ruling`：判準要求 trailer 落在該 commit 自身、前向修不掉。🔴 **本批另有 5 筆是 B10 自己的**（三個 `scripts/` 改動未帶 trailer ＋兩個 GAP-3 測試檔不在 scope manifest），**不併入既有帳**，見 `HANDOFF.md` 之坑 |

## 簽字

- 主委（Claude）：A 段 11 項實跑於 **2026-08-29**（receipt：`handoffs/run_receipts/20260829T000000Z-gap3-uat-sectionA.log`）；
  A9 之 rc=1 為既有 8 行型別債，GAP-3 相關檔 0 錯。
  十批實作皆經三家 code review；B10 之 R3（八條 findings 全成立全修）與 R4 閉合輪（原提出方逐條 CLOSED）
  收斂檔＝`handoffs/reconcile/20260828-gap3ux-b10-review-r{3,4}/synth.md`。
- 使用者：B 段逐項簽字完成於 ＿＿＿＿；epic 收案：是／否
