# rolling 視窗依 run 週期換算之接線（`reference_tf`）— SPEC

> 來源：`handoffs/reconcile/20260908-evtwarmup-x-consult-r1/synth.md` W3（三家一致：另票、獨立 golden）　|　日期：2026-09-08　|　對應 TODO：本票收案前由 `docs/EVTWARMUP_TODO.md` Phase 3 承接（同 TODO 檔，批次獨立）
> 使用者裁定（2026-09-08 逐字）：「和要修改抓的的第二個bug」。

## §RISK 風險分級
- **大小**：中（orchestrator 建引擎一處接線＋config schema 一欄＋golden 重凍＋依賴未換算視窗鍵之測試更新）。
- **命中高風險原則**：(a)(d)——改變**全域**模式 rolling IC／ICIR 之數值語意（1h run 視窗 ×12）。
RISK-HIT: a,d

## §A 假設與待使用者確認
- **已核實事實**：
  - FACT-RECEIPT: `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `"engine_timeframe_key_present": false`、`"engine_timeframe_attr": null`、`"adjusted_windows_1h": [252, 756, 1512]`（主委 實跑 2026-09-08）
  - FACT-RECEIPT: `sed -n 988p momentum/Analysis/ic_filter_orchestrator.py` → `self._ic_engine = ICEngine(config.ic_calculation.model_dump())`（主委 實讀 2026-09-08）——metadata.timeframe 從未傳入
  - 引擎單測 `tests/momentum/test_ic_engine.py::test_rolling_window_adjustment_by_timeframe` 手動傳 `timeframe=4h` 通過 ⇒ 函式可用、是接線缺失（grok §0 實跑）。
- **待使用者確認**：`待確認：無`。
- **已確認結果**：`2026-09-08 使用者同意修第二個 bug（另票）`。

## §C 約束
1. 接線來源＝**run 之 `metadata.timeframe`**（stage0 讀入），不是 request 猜測；缺 ⇒ 不換算並揭露 `timeframe_adjustment="not_applied:missing_timeframe"`（fail-loud，非 fail-open 假換算）。
2. 換算後 warmup 門檻隨之變大（1h：1512＋horizon）；全域 1h 短歷史 run 誤擋面上升 ⇒ 必須有 §G 改前／改後對照與白話揭露，禁靜默。
3. 與 `EVTWARMUP` 互斥 golden：本票**不得**與其同 commit；先收 `EVTWARMUP`。
4. 事件路徑（`EVTWARMUP` 後 rolling 為診斷）亦套換算，但不影響其門檻。

## §G Golden / Baseline
- 改前：`tests/golden/evtwarmup/baseline.json::facts.adjusted_windows_default=[21,63,126]`；整份報告 golden `test_gap2_golden`（canonical sha256；12h fixture：因 `reference_tf=12h` ⇒ 因子 1 ⇒ **12h run sha256 逐位元組不變**——這是本票的 over 向對照）。
- 改後 1h golden：`tests/golden/tfwindow/rolling_keys_1h.json`＝1h fixture 之 rolling 鍵集＋每視窗序列長度＋序列值 sha256；通過條件：鍵集 `==`、長度 `==`、值 sha256 `==`（float 比對 `atol=1e-12`）。
- 測試層級（R1 `COMPOSER-R1-P2-02`／`GROK-R1-P2-02`）：`tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_ic_rolling_warmup` 直呼 `_stage4_ic_calculation`＝**引擎層回歸**（保留、不改期望鍵）；`tests/api/test_tfwindow.py` 經 `analyze` ＝**接線主 gate**；mutation「注入拿掉」須使主 gate 紅而引擎層測試仍綠。
- 12h 整份 golden：因子 1 ⇒ 數值逐位元組不變，但全域報告**新增** `ic_window_disclosure` 鍵 ⇒ 依本 §G 重凍，重凍 diff 只准含該鍵（R1 `CODEX-R1-P1-04`：揭露鍵與 byte-locked 投影之衝突在此票解，B1 不寫全域鍵）。
- 改後：新增 1h fixture 之 rolling 鍵集 golden（`window_252/756/1512`）與 warmup 門檻 receipt；`tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_ic_rolling_warmup` 之 `window_5` 類斷言依 fixture 週期重算（不得刪測試換綠）。
- 通過條件：12h run 逐鍵不變；1h run 視窗鍵＝原鍵×12；缺 timeframe ⇒ 不變＋揭露。

## §P Phase 與依賴
### Phase 3 — 接線（依賴：`EVTWARMUP` 收案）
**Task 3.1 — 建引擎時注入 run timeframe**
- 目標：`_adjust_rolling_windows` 在生產路徑生效。
- 檔案：`ic_filter_orchestrator.py::analyze`（stage0 後以 `metadata.timeframe` 重建／設定 `self._ic_engine._timeframe`，或 `ICEngine.set_timeframe()` 新方法）；`ic_config_schema.py::ICCalculationConfig`（不加欄；timeframe 來自 run 而非 config）；報告 `ic_window_disclosure.timeframe_adjustment="applied"`＋`adjusted_windows`。
- 改法：stage0 讀 meta ⇒ `tf = metadata.get("timeframe")`；有 ⇒ 注入；無 ⇒ 揭露 `not_applied:missing_timeframe`。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_tfwindow.py THEN rc=0`；`ASSERT venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py WHEN target=global_run THEN rc=0`（12h 不變）；1h 案例 rolling 鍵集 `== {window_252, window_756, window_1512}`。
- **邊界**：①12h run ⇒ 視窗不變；②1h run ⇒ ×12；③timeframe 缺 ⇒ 不變＋揭露；④timeframe 非法字串 ⇒ 既有 `logger.warning` 路徑＋揭露 `not_applied:invalid_timeframe`。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得改 `reference_tf` 預設；不得為了讓 1h 短 run 過門檻而縮視窗；不得靜默換算不揭露。

## §V 驗證策略與邊界測試目錄
- mutation（`handoffs/20260908-evtwarmup-mutate.py --phase 3`）：M1 注入拿掉 ⇒ `tests/api/test_tfwindow.py -k window_keys` 紅（rc=1）；M2 缺 timeframe 時假換算（用 reference）⇒ `-k missing_timeframe` 紅；C0 只改註解 ⇒ rc=0。
- golden：`pytest tests/momentum/Analysis/test_gap2_golden.py` rc=0（12h 整份 sha256 不變）；1h 新 golden `tests/golden/tfwindow/rolling_keys_1h.json` 受 adversarial 審。
- 邊界目錄：timeframe 缺／非法字串（Task 3.1 ③④）；12h＝reference（因子 1）；1h（因子 12）。

## §R 回退
- 單一 commit 可 revert；無 flag（換算是正確化，不做預設關閉——`feedback_no_default_off_after_validation`）。

## §N N/A 登記
- 三方 kline 簽核子項：不需要 — 不碰 kline／特徵生成（golden 本體已填）。
- 殘留：`TW-RESID-1` 1h 短歷史 run 因門檻 ×12 而 fallback 增多 — `為何現在不做: user-ruling:2026-09-08 三家「正確化方向，接受並揭露」`；觸發：UAT 出現非預期 fallback 時檢討 `rolling_windows` 預設；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`。
