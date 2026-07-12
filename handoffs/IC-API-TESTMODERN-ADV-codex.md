# IC-API-TEST-MODERNIZATION — Codex adversarial
task-id: icatm-adv-codex | reviewer: Codex (independent; drafter=Claude) | 2026-07-12

## Verdict: BLOCK

至少一個可證偽反例已成立於 SPEC 文字本身：照 §修法順序「先切 512 → 衍生
`log_return_1/log_return_5/rvol_20/zscore_20` → 寫 H5」，trailing rolling/positive-lag
特徵必然令前 1/5/20 附近為 NaN。SPEC 只強制 label 尾 5 NaN，沒有 warmup-prefetch、
共同 finite mask 或同步裁切規則；因此不是一個可直接實作且能保證過 gate 的契約。

## Blocking findings
1. **PIT/切片契約欠定義**：feature 必須明定只用 `t` 或更早資料：例如
   `log(close/close.shift(+k))`、trailing `rolling(window)`；禁止 feature `shift(-k)`。
   label 應是 `log(close.shift(-5)/close)`（或全案選定 simple），尾 5 自然 NaN，禁止
   用 fill/ffill/bfill。須先多讀至少 `max_lookback-1` 根 warmup，再把 feature、label、
   close oracle、timestamp **共同裁成同一 512 軸**；不可亂填 rolling 初值。
2. **PIT 驗收不夠可證偽**：現 API file-based path 呼叫 `validate_alignment` 時是否傳
   `close` 必須釘死並驗證。該函式只有收到 `close` 才做逐點 forward-return oracle；
   否則 `return_5` 名稱、cadence、尾 5、coverage 全合法的「錯方向 label」仍可結構綠。
   新增 mutation：把 label 改為 backward `log(close/close.shift(5))` 且保留尾 5 NaN，
   測試必須 FAIL；這比僅改 `return_5→return_1` 更能抓 PIT。
3. **ETH/12h/512 尚未實證**：單一 Python 命令讀
   `data_cache/feature_klines/kline_cache.h5` 超過 60 秒無輸出，已終止，標 **DELEGATED**；
   本 reviewer 未驗證 shape、timestamp 單位、`[200:712]` 或 tail-512 連續性，故不得沿用
   顧問聲稱當 receipt。reconcile 必須補獨立命令 receipt：dataset shape/dtype、epoch 秒、
   每個 diff、gap_count/rate、指定切片首尾 timestamp、以及完整 builder 跑
   `validate_alignment(..., close=..., return_kind=...)`。`min_rows>=712`/manifest 只證列數/指紋，
   不證選中視窗無 gap，也不證 feature finite；這就是 cadence/tail/coverage/gap 外的第五層。
4. **去重候選需收窄**：`test_feature_list` 可刪（保留的
   `test_list_available_features_success` 還多驗 feature payload）；`test_full_analysis` 可刪
   （與 endpoint 版等價）。第三個不能寫「start 或 result」任選：組合測只驗 POST 200，
   沒驗 start response 的 `status in {started,running}`，所以刪 `test_deep_analysis_start`
   會損獨特契約。應保留 start，刪較弱的 `test_deep_analysis_result`（組合測已更強驗
   results/summary/progress）。
5. **分層錯置/共用敘述矛盾**：`test_full_analysis_endpoint`、
   `test_full_analysis_with_deep_analysis_config` 各自 POST `/full-analysis` 並等待真計算，
   明確是 L2；不能由「session 建檔一次 + `/analyze` 一次」供應結果。feature-list 只讀 H5，
   是 L1 但不需要 completed task。numpy scalar 測直接改 service task state，屬獨特 L1
   serialization seam；可依賴 completed task 作容器，但不可宣稱真 deep pipeline。
6. **仍藏合成**：export fixture 另外手寫 `deep_analysis_result` 數值與 filtered H5
   `[[1.0,2.0]]`。它們不是 kline 衍生；若保留，SPEC 的「fixture 零合成」驗收會假通過
   （只 grep `rng.normal/np.arange`）。須逐一裁決：改由真 deep result/真 filtered artifact，
   或明確定義為 API serialization stub 並把「無合成」限縮為 IC input features/labels/timestamps；
   不可用目前的全稱聲明。

## Reconcile 必補的最小 gate
- builder 演算法、lookback、計算先後、共同裁切與 simple/log 單一選擇寫死；輸出 512 列全 feature finite，label 僅尾 5 NaN。
- 兩個 mutation：backward label 必紅；任一 feature `shift(-1)` 必由獨立 PIT oracle 紅。
- 針對實際選定 window 的 HDF5 receipt 與一次真 `/analyze`、兩個 `/full-analysis` nodeid receipt；不能用 advisor 建議值代替。
- 精確列出 3 個刪除 nodeid，第三個固定刪較弱 result 測；列出剩餘 assertion 對照。

ASSUMPTIONS_VERIFIED: 實讀三 API 測試檔；實讀 `validate_alignment`：cadence、tail==lag、label coverage，且 close 非 None 才啟用值 oracle；實讀現 deep 測斷言差異。
TESTS_RUN: `source venv/bin/activate && python - <<'PY' ...`（HDF5 shape/timestamp/window/warmup/alignment 綜合驗證）；超過 60 秒無輸出後終止，結果 DELEGATED/未驗證。
FAILURES_SEEN: HDF5 驗證命令逾 60 秒，無可採用輸出。
SCOPE_CHANGES: none；只新增本 adversarial 文件。
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼/資料）。
STATUS: BLOCK
