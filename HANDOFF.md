# HANDOFF — 當前任務狀態

**更新：2026-09-02｜狀態：`G3-D1`（R 重開）程式面 CLOSED；等使用者驗收 B2（改寫）／B5／B10／B13–B20**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D1` | **CLOSED（2026-09-02）**：規格 R 重開（R35–R37＋三家戳記）→ 實作 `c6dd057a` → code review R1（4 P1／P2 修法 `7e0a7a94`）→ R2 閉合（六條 CLOSED；反向 1 P1 修法 `dd4baa2c`）→ R3 閉合（CLOSED、無新 P0／P1）。使用者側 UAT 待驗 |
| `G3-D2` | **OPEN**：五維度三類值不接受永久灰著 |
| `KLINE-1` | **OPEN**：`/data-preparation` 舊區塊已標 deprecated；移除票待開（大任務） |
| `G3-D3`…`D9` | CLOSED |
| `G3-D10`／`D11` | **CLOSED（2026-09-02 晚，UAT B15）**：coverage 閘對註冊 run 誤判 legacy（manifest 找錯目錄）；任務秒失敗時 WS 錯過通知、畫面停「執行中」。兩端各修一處＋測試；使用者須重啟後端重做 B15（run 選 `abc9b9fe`） |
| `G3-D12` | **CLOSED（2026-09-02 晚，UAT B16）**：分析完成後「Failed to fetch」＝`/ic/refilter` 回原始 dict 含 NaN／inf ⇒ 500；改走 `get_result()` 同一出口＋回歸測試 |
| `G3-D13` | **CLOSED（2026-09-02 晚，UAT B17）**🔴 正確性：`event_import_id` 路徑未開 `event_filter.enabled` ⇒ 事件模式報告實為全樣本 IC（`mode=none`）。一行修＋回歸測試；**B15–B17 須重跑**。教訓：B10 三輪 review 無一條斷言 `event_filter.mode`／`statistic_kind` |
| `G3-D14` | **CLOSED（2026-09-02 晚，UAT B17）**：D13 之後條件 IC 真跑，survivor 落檔要 v2 六鍵 `event_context`，五階段路徑沒產 ⇒ fail-closed。補 `ic_feed.event_context_from_windows`（唯一實作）→ pipeline 出口 → `analyze(event_context=)`；10i 測試加六鍵斷言 |

## 這條 epic 最終落地了什麼（細節＝`docs/GAP3UX_IMPL_HANDOFF.md` §1／§1b／§2）
- `/search` 匯出面板：篩選整區拆除；答案窗宣告框（與匯入頁同一元件／validator／守衛形狀）；預設候選只取勾選之附帶欄、系統預填與使用者明填分開記；preview 重取失敗即作廢。
- 後端：每批一律宣告（表單或列內攜帶；皆無 ⇒ 拒收）；深度＝宣告逐鍵複製（不與任何欄位取 max）；「須勾選」唯一判定 `declaration_is_unverifiable`（兩端 preview 以 `acknowledgement_required` 承載）；攜帶值自動勾選只限 JSON 直傳路由；`0` 合法須明填；`/case/lookahead-depth` 與 `ON_MISSING_BLOCK` 刪除。
- 委員會足跡：consult r1 → review R35／R36／R37 → stamp r1 → b11 review r1／r2／r3（債全清）；本機 `handoffs/reconcile/20260902-*`。

## 下一步（依序）
1. 使用者回來後驗清單 B2（改寫）／B5／B10，再 B13–B20；有缺陷開 `G3-D10+`。
2. `KLINE-1` 移除票走完整管線；`G3-D2`。
3. 具名殘留：`R35-L2-ACK`（JSON 直傳無法複驗勾選 provenance；needs-research）、`MUT-CSV-MAP`（語意等值副本 ⑥ 抓不到；needs-research）、`GOV-DOC-STATUS-1`、看板 42→39＋1 機械重產工具、commit-msg claim 閘以整則訊息為單位（見 `白話說明/流程摩擦記錄.md` 9/2 下午）。

## 已知紅／不要誤判
- `tests/api` 既有紅（batch_alias／ichc_event_timestamps／progress_rss_fields×2，見 `G3-R11`）；`test_ic_deep_analysis` 與其他 pytest 並行時 ERROR、單跑綠；`tsc --noEmit` 8 行既有債。
- `uat_samples/*拷貝*`、`_tmp_new_schema.csv` 為本機雜物，未納版控。
