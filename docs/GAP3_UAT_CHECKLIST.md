# GAP-3 事件型分析 — UAT Checklist（Task B5.3；W9）

> 每項＝步驟＋實跑命令＋rc＋預期畫面／輸出＋**使用者簽字欄**。使用者未簽字 ⇒ epic 不收案（TODO B5.3 邊界②）。
> UAT 發現缺陷 ⇒ 回對應批修（B1–B4），不在 B5 打補丁繞過（TODO B5.3 邊界①／C9）。
> 真實流程：匯入 → 對齊 → 三表 → 全 K 線 → 報告；bars 一律真實 kline（`data_cache/feature_klines/kline_cache.h5`），事件可為使用者標註或 `/search` 匯出。

## A. 機械前置（主委實跑；rc 欄由主委填、receipt 路徑可稽核）

| # | 步驟 | 命令 | rc | receipt |
|---|---|---|---|---|
| A1 | 事件樣本層全套 | `venv/bin/python -m pytest tests/momentum/event_samples/ -q` | ｜ | `handoffs/run_receipts/<ts>-gap3-b5-gate.log` |
| A2 | state-counter 算子 | `venv/bin/python -m pytest tests/momentum/feature_engineering/ -q -k state_counters` | ｜ | 同上 |
| A3 | GAP-1 防線不退步 | `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation -q` | ｜ | 同上 |
| A4 | API 匯入／分析 | `venv/bin/python -m pytest tests/api/ -q -k gap3_import` | ｜ | 同上 |
| A5 | 前端 build | `cd frontend && npm run build` | ｜ | 同上 |
| A6 | 前端 vitest（gap3） | `cd frontend && npx vitest run gap3` | ｜ | 同上 |
| A7 | 白話同步守衛 | `bash scripts/plain_docs_sync_check.sh` | ｜ | 同上 |
| A8 | IC 主線行為不變 | `venv/bin/python scripts/gap3_freeze_golden.py --check` | ｜ | 同上（sha 163c4ce…） |
| A9 | 萬級規模 receipt | `venv/bin/python scripts/gap3_import_scale.py --n 10000 --write` | ｜ | `handoffs/run_receipts/gap3_import_scale.json` |

## B. 使用者逐項驗收（真實操作；每項附預期畫面；簽字欄由使用者填）

| # | 步驟（你做） | 預期畫面／輸出 | 通過？（簽字／日期） |
|---|---|---|---|
| B1 | 啟動後端＋前端（`python run_api.py`；`cd frontend && npm run dev`），開 `/search`，跑一次正反例搜尋 | 結果列表出現；底部多一顆「匯出事件契約 JSON」 | ｜ |
| B2 | 點「匯出事件契約 JSON」 | 下載 `gap3_events_<日期>.json`；內容每筆含 `event_id/t0(ms)/label/label_definition/control_kind`；`skipped[]` 列出無法轉換者（reason） | ｜ |
| B3 | 開 `/data-preparation`，用「匯入事件（GAP-3 新契約）」上傳 B2 的 JSON（先勾「僅驗證」） | 顯示「驗證通過 N 筆（未落檔）」；若契約違規 ⇒ 逐列 reason 表格＋migration 提示（**不是**空白或 500） | ｜ |
| B4 | 取消「僅驗證」再上傳 | 顯示 import_id；右側「已匯入事件批」出現該批（symbols／timeframe／筆數） | ｜ |
| B5 | 把舊三欄 CSV（symbol/timestamp/Positive_case）丟進「匯入事件」 | 拒收：`legacy_schema_detected`＋migration 提示（欄位對照）；舊流程「導入案例」不受影響 | ｜ |
| B6 | 把 B2 的 JSON 轉成 CSV 丟進舊的「導入案例」 | 拒收：`new_schema_on_legacy_endpoint`，訊息指向 `/case/import-events` | ｜ |
| B7 | 開 `/ic-analysis`，分析模式切「Event-Driven」 | 出現「從已匯入案例選事件」下拉（未匯入時顯示 empty state 文字）；兩表區塊出現（未選批 ⇒ 「尚未選擇事件批」） | ｜ |
| B8 | 下拉選 B4 那批 | 兩表區塊顯示「匯入／對齊／train／test／purge」計數、事件後報酬表逐 horizon 數值（macro／micro／win_rate／n）；辨別表顯示 `not_computed：no_model_scores_in_event_pipeline`（原因非空白） | ｜ |
| B9 | 同一批按「開始分析」跑 IC | IC 報告 metadata `event_filter.mode=timestamps`、`n_events`＝該批對齊成功數；既有圖表照常 | ｜ |
| B10 | 切回 Global 模式 | 兩表區塊與事件下拉消失；全域報告不變 | ｜ |
| B11 | 看 `白話說明/GAP-3施工進度.md` 五批總覽 | B1–B5 狀態與本清單一致；無「收案」字樣貼批號 | ｜ |

## C. 殘留（登記 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」；三值理由）

| 項 | 為何現在不做 |
|---|---|
| 辨別表在 `/ic-analysis` 事件模式只顯示 `not_computed`（需 test 段模型分數） | `needs-research:分數來源＝B4.1 pattern 橋或外部模型；UI 接線屬 ML 層（不完整層），待 ML 層穩定後接 B4.1 輸出` |
| 萬級事件對齊 73s（純 Python 逐事件；receipt `gap3_import_scale.json`） | `user-ruling:W10 記錄型不設門檻；向量化對齊待需求出現再做` |
| `tests/api` 既有紅 7 條（B5 前即紅：batch_alias／ic_deep／ichc t2-t3／model_enhancement×3） | `blocked-by:非 GAP-3 模組；另開票處理` |

## 簽字

- 主委（Claude）：A 段全 rc=0 於 ＿＿＿＿（receipt 路徑：＿＿＿＿）
- 使用者：B 段逐項簽字完成於 ＿＿＿＿；epic 收案：是／否
