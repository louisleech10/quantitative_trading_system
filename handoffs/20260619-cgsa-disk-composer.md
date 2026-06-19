# 20260619 CGSA Disk — Composer 獨立架構審查
角色:獨立審查(不附和 Claude/Codex)。證據來自 brief + 四檔原始碼 + git。

## T-A 串流釋放 / 峰值 bound
**裁決:Claude 方向對,但兩處需修正。(1)峰值不必等 35GB 才爆**—本次在 L3 `persist-shard` 中途(`column_group_registry.py:810-815,1542-1550`),隨 shard 單調累積即可能撐滿;L4-L6 尚未寫入。(2)**L7 內已有增量釋放,非「L7 結束才釋放」**—fast L6.5 每 shard 寫完 parquet 即 `unlink_shard`(`feature_preprocessor.py:2089-2091`);最後 chunk `release_storage`(`feature_storage.py:1021-1033`→`column_group_registry.py:1034-1078`)。但 **L7 前零釋放**:multi-TF 迴圈先 persist L3-L6 全 TF(`multi_tf_generator.py:204-212`),再單次 `_layer7_raw_from_cgsa_pipeline`(`:305-323`);`release_storage` 無其他 caller。
**L7/cross/meta 是否需一次看到全部 group?** L5/L6 生成只吃 in-memory L1/L2(`feature_factory.py:370-375,1684-1686`),persist 後 registry 上的 L3 僅供 L6.5→L7 讀;`transform_registry_groups_to_sink` 明確 per-group 串流(`feature_preprocessor.py:396-407,529+`),無跨 group 矩陣依賴。阻塞點是**編排**:最終 manifest 一次組裝(`feature_storage.py:1122+`)、非 primary TF 須先 compact-align(`multi_tf_generator.py:250-268,790-827`)、`get_cgsa_per_layer_pipeline_enabled()` 已 scaffold 但預設 OFF 且註明未開(`hardware_utils.py:353-366`)。
**最小改法**:P1 啟用 Phase2 per-layer sink(先 primary-TF L3 only)→persist 後立即 raw-sink+release;保留現 L7 manifest 終局校驗。**風險**:resume/parquet 綁定、compact idx_map 順序、slow fracdiff/native 路徑 parity。**優先序:P1**(事故後);當次 outage 救不了 L3 中途爆。

## T-B float16 cgsa 暫存
**裁決:磁碟有效(~÷2)但非首選;現況 float32 是持久化契約非數值必要。** `save_data` 強制 `data_fp32`(`column_group_registry.py:747`);worker npy `normalize_npy_persistence_float32` 註解為 Batch0 byte 穩定(`:36-40`);讀路徑 `load_data`/`load_data_native` 皆升 float32(`:434,448+`)。L7 parquet 預估已按 float16 終態(`feature_storage.py:2741-2751`);暫存 float16 只砍 cgsa_work。fracdiff precision 預設 0.02(`feature_preprocessor.py:2855-2856`)—float16 可能動 d*/ADF 邊界。
**最小改法**:opt-in `FFACT_CGSA_TEMP_DTYPE=float16` + load 邊界必 upcast float32;先限 L3 rank/zscore 類,禁 L1/L2 原價量與 fracdiff 輸入。**風險**:IC/rank 翻轉、golden byte churn。**優先序:P2**(需真實 kline A/B)。

## T-C 累積磁碟預檢
**裁決:P0 必做;現 guard 結構性不足。** `_persist_group_array` 只比「當前 shard vs 當前 free」(`column_group_registry.py:1542-1550`);寫入還有 `.tmp` 雙份 headroom(`:1554-1560`)。L7 已有累積模型:final+reclaimable+inflight+reserve(`feature_storage.py:2726-2791`)。
**最小改法**:L3 開寫前估 `registry 已佔 + Σ(rows×planned_cols×4) + max_shard×2(tmp) + reserve`;不足即 abort 列 symbol/tf/需 GiB/可用 GiB。**風險**:高估( compact 非 primary 物理列較少 `:422-449` )或 L7 dead-drop 低估—訊息應列分量。**優先序:P0**。

## T-D 為何以前 28GB 夠
**裁決:現 437K×20352×4≈35.6GB 是 naive 上界(全欄當 primary 列);不能證明「同 config 曾穩進 28GB cgsa_work」。** compact alignment 預設 ON(`multi_tf_generator.py:1128-1131`),非 primary 磁碟按 `source_n_rows` 存(`column_group_registry.py:422-449`)—總 footprint **低於** brief 公式,但 primary L3 仍主導。28GB 曾過較可能:(a)較少 TF/欄/列或舊 config_hash;(b)同 partition 當時空間更大;(c)非 CGSA 或 L7 已 reclaim 後才量—**非**(b)pre-L7 串流釋放(程式證偽)。816b3f8(2026-05-11)才有 sharded+release;67c4f28(2026-06-12)才 normalize float32。
**最小改法**:比對舊 run manifest 的 layer_counts/row_count/config_hash vs 本次;量 `cgsa_work` 分 layer。**優先序:P1 取證**。

## 總序
**P0 T-C → P1 T-A(Phase2 sink) + T-D 取證 → P2 T-B**。

ASSUMPTIONS_VERIFIED:release_storage 單 caller;L5/L6 不依 registry L3;compact 減非 primary 列。
TESTS_RUN:read-only(rg/read/git log);無 pytest。
FAILURES_SEEN:none。SCOPE_CHANGES:none。NUMERIC_OR_SCHEMA_IMPACT:none(審查)。
STATUS: DONE
