# B2 比對效能設計 — Codex 委員腿

## 讀碼依據
- 已讀 `HANDOFF.md`、`CLAUDE.md`、`handoffs/20260629-FF-B2-PERF-PROMPT.md`、Claude 腿。
- 已靜態讀 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 與 L7 raw/registry manifest 寫入碼；未跑慢全鏈。
- 現有瓶頸點：`_assert_values_gate_main()` 對每個 common column 反覆 `pd.read_parquet()`，22 萬欄時 I/O 與 Python loop 皆放大。

## 結論
同意 Claude 的「generate 全鏈不變、values/NaN 分層抽樣」方向，但分組鍵應以 L7 raw manifest 的 group metadata 為主，不以欄名前綴為主。

## 定案方案
1. columns/schema gate 維持全集：
   - full/trunc 欄名 set、交集、不對稱掉欄門檻 `max(100, 0.1% union)` 保留。
   - metadata gate 保留 `feature_schema_hash`、`total_features`、row_count/time_range 檢查。
2. values + NaN mask 改抽樣：
   - 從 `feature_manifest.json["artifacts"]["raw"]["groups"]` 建立 `column -> group`。
   - 分組鍵：`(layer, timeframe, data_source, indicator, parquet_group_id_class)`。
   - `parquet_group_id_class` 規則：L1/L2 用實際 group_id；L3/L4/L5/L6 chunked group 統一去尾 `_\\d+` 後再加 chunk bucket，避免只抽到第一個 chunk；L6.5/preprocessed group 保留 transform/source indicator。
   - fallback 才解析欄名前綴；fallback 命中數要寫入測試輸出，比例異常時 fail。
3. K：
   - 每組 deterministic sample `min(32, group_size)`。
   - 對大組再加邊界樣本：sorted columns 的 first/middle/last 各 1；chunked L3/L4 每個 parquet group 至少 1 欄。
   - 全樣本數上限建議 8k 欄；若超過，按 group 等權 stride 裁切，但不得裁掉 required mutation columns。
4. mutation 相容硬保證：
   - sampled set = stratified sample ∪ required probes。
   - required probes 不靠名稱猜單一欄；由 mutation 類型選欄：
     - L3 center=True：至少每個 L3 rolling stat/window family 1 欄，且包含 mean 類欄。
     - L4 shift(-1)：至少每個 lag family 1 欄，且包含 lag_1/最小 lag 類欄。
     - L6.5 full-fit winsor：每個 preprocessing transform/source group 至少 1 欄，高 fill-rate 欄優先。
     - fracdiff 維持現有專屬嚴格 MR，不納入主 MR 抽樣放寬。
   - mutation 測試若 sampled set 未含對應層/類型，先 fail 為測試設計錯誤，不允許變成假綠。
5. 比對實作要求：
   - 不要逐欄讀 parquet。先把 sampled columns 按 `(full_file, trunc_file)` 分桶，每個 parquet 檔只讀需要欄位一次。
   - 對同一檔內多欄用 numpy matrix 批次算 fill_rate、both-non-NaN allclose、NaN mask；錯誤訊息再定位到欄。
   - 覆蓋率守衛應以 sampled common columns 計算，同時輸出 `sampled/total common` 與分組覆蓋摘要。

## 對風險的判斷
- 抽樣確實會降低「任意單欄特異 bug」的檢出率；但 B2 主目標是全鏈因果 MR，而已三方讀碼確認 look-ahead 屬層級算法性質。用 layer/operator/group metadata 覆蓋每型別，足以代表此目標。
- 單欄洩漏若來自資料/欄位命名特例，不應只靠 B2；應由 B1 atomic differential、B3 multi-TF/cross-sectional 分級 MR 或後續 stateful-param audit 補。
- columns gate 全集 + values/NaN 抽樣分工足夠；比「向量化全比」更實際。全比若改成批次讀可改善，但 22 萬欄仍會掃完整數據，單測牆鐘不穩。

## 推薦驗收
- 只需跑 B2 相關單測與 mutation；不要跑慢全 repo。
- 驗收輸出需列：總 common 欄、sampled 欄、分組數、未解析 fallback 數、required probe 命中數。
- mutation 五項仍必紅；若任一 mutation 綠，先檢查 required probe 是否進 sampled set。

STATUS: DONE
