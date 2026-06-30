# B2 比對效能設計 — 三方 reconcile(定案)

三腿(Claude/Codex/Composer)收斂。核心:**generate 全鏈不變(因果本體);比對加速 = 批次讀 parquet + 分層抽樣**。

## 定案(實作清單)
1. **批次讀 parquet(最大槓桿,兩家點名根因)**:現 `_assert_values_gate_main`/`_assert_warmup_nan_masks_equal` 逐欄 `read_parquet`(22萬次)= >20分主因。改為:按 parquet 檔 groupby 抽樣欄 → 每檔 full/trunc 各讀一次 → 記憶體內 slice + numpy 批次算。不改 oracle 語義。
2. **columns gate 維持全集**(便宜,只欄名 set):交集 + 不對稱掉欄 `max(100, 0.1%×|union|)` + metadata(schema_hash/total_features/row_count/range)。
3. **values + NaN mask + warmup mask 分層抽樣**(共用同一 sampled set):
   - 分組鍵:由 parquet group stem(= production group_id)+ 欄名 suffix → (layer, tf, source, indicator/operator, group/chunk class)。L3/L4 chunked group 去尾 `_\d+` 後加 chunk bucket(避免只抽第一 chunk)。
   - K = min(32~40, 組大小)/組 + 邊界樣本(first/middle/last);總上限 ~8k;**下限 ≥3000**(防抽樣 bug 空轉)。
   - fallback 解析欄名前綴,fallback 命中數寫入輸出、比例異常 fail。
4. **mutation 硬保證**:sampled set = 分層抽樣 ∪ required-probe 欄。required 由 mutation 型別選(L3 rolling stat/window 含 mean 類、L4 lag family 含 lag_1、L6.5 transform/source group 高 fill 優先);**sampled 未含對應層 → mutation test 先 fail 為設計錯,不准假綠**。
5. **fracdiff 專屬 MR 不抽樣**(欄數小,維持 d-star equality + atol=1e-8 + exact NaN mask)。
6. **覆蓋率守衛**:comparable/len(sampled) ≥ 0.95;輸出 sampled/total common、分組數、fallback 數、required-probe 命中數。

## 範圍
只改 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 比對 helper;不改 generate/storage/oracle 語義。
