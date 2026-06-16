# Batch2D d* Align Adversarial Review (V13)

## Verdict

**FAIL - SPEC/TODO 尚不可派工。** L7 比對方向正確，但 artifact 契約、完整 golden、layer provenance、CGSA 禁改邊界與 tier2a 驗收仍有阻塞矛盾。

## Findings

### BLOCKING

1. **[High] 所謂「兩路 L7_raw」不是同一 artifact contract，P0/P4 未定義可執行 extractor。**
   - 證據：SPEC §G/TODO Task 4.1 寫「CGSA vs 非 CGSA L7_raw」；實碼 CGSA 由 `feature_factory.py:3063-3086` 呼叫 `write_raw_from_registry_stream()`，產 `raw_v2` parquet；非 CGSA 由 `feature_factory.py:3363-3371` 合併、float32、tag 後，`3447-3449` 呼叫 `save_factory_output()` 寫 legacy HDF5。CGSA result 在 `3163-3165` 明確回空 frame。
   - 失敗方式：Agent 無法只靠「取 L7_raw 產物」決定讀哪個檔、如何還原 row index/欄序/NaN mask；可能退回比空 frame、比不同 storage representation，或自行發明 normalization。
   - 修法：SPEC 明列兩個 reader/extractor、共同 canonical matrix contract（row index、欄名/order、float32 bytes、NaN mask），並把「non-CGSA logical Layer-7 output/HDF5」與「CGSA raw_v2」分名。

2. **[High] P0 golden 只做抽樣 hash，不能支撐 P4 的 exact unchanged，也抓不到值重排/局部漂移。**
   - 證據：SPEC Task 0.1/TODO 0.1 僅存「mean/std/nan_ratio + 抽樣 value/mask hash」；同文件 §G #5/P4 卻要求 L3-L6 對 control exact unchanged，§C 又要求 CGSA byte 不變。V13 §2 明確警告 aggregate/抽樣會被值重排或局部漂移繞過。
   - 失敗方式：未抽中的 row 可被重排、改值或改 NaN mask而仍通過；實作後雙路同時被共用改動污染時，live parity 也會一起綠。
   - 修法：每欄保存全長 canonical float32 value hash + 全長 NaN-mask hash + row-index hash；另保存全 artifact/ordered-column hash。P4 必讀 frozen P0，不只重跑 live CGSA。

3. **[High] frozen baseline 沒有可用的 layer provenance，L1/L2 intersection 與 L3-L6 control gate 不可實作。**
   - 證據：SPEC §G #3/#5 要按 layer 分組；但非 CGSA 最終欄名在 `feature_factory.py:3368-3371` 只加 timeframe tag，沒有 layer tag；現況 `_combine_layers()` `3619-3652` keep-first 後遺失來源。P0 JSON 欄位未包含 `column -> layer` map。
   - 失敗方式：Agent 只能再用欄名 heuristic（被 [D2-5] 禁止），或把所有交集誤當 L1/L2；L3-L6 gate 形同不可驗。
   - 修法：P0 在 merge 前從 HEAD 六個 layer frame 凍結 ordered provenance，並將 timeframe-tag 後欄名映射寫入 baseline；CGSA 亦從 registry group metadata獨立凍結，兩者先驗證同名欄 layer 一致。

4. **[High] Task 2.1 同時要求「CGSA 禁改」與修改 registry-only `_group_requires_slow_transform`，scope 自相矛盾。**
   - 證據：TODO 2.1 第 3 點要求全鏈修改 `_group_requires_slow_transform`；該函式由 registry serial/parallel/raw-sink 排程呼叫（`feature_preprocessor.py:1167-1206`、`:463`），正是 CGSA 路徑。flat frame path `_transform_chunked()` 在 `2651` 只呼叫 `_transform_single()`，不經該函式。
   - 失敗方式：照 TODO 做會改 CGSA slow/fast routing；不做又違反 Task。即使 `source_layer` 分支文字不變，排程/輸出仍可能變。
   - 修法：從 P2 scope 移除 `_group_requires_slow_transform`；map 僅作 `FeaturePreprocessor` instance attr，由 flat `_filter_fracdiff_target_columns(source_layer=None)` 消費。用 frozen full CGSA hash證明主路徑未變。

5. **[High] tier2a 的「d* keys subset {L1,L2}」型別/語意錯誤。**
   - 證據：SPEC §G #6、Task 3.1、TODO 3.1 都寫 `d* keys ⊆ {L1,L2}`；實際 `DStarCache._entries` key 是 feature column name（`_d_star_cache.py:296,463,548`），現有 synthetic 欄名是 `L1_*`/`L2_*`，不是 layer label。
   - 失敗方式：字面實作必失敗；寬鬆實作者可能改成只驗非空，造成假綠。
   - 修法：明定 `all(layer_of_feature[key] in {"L1","L2"})`，layer_of_feature 來源用 synthetic inventory/explicit map；同時斷言沒有 L3-L6 prefix key。

6. **[High] 驗收命令要求在 `data_cache/feature_preprocessing` 新增檔，違反執行合約且未隔離 cache。**
   - 證據：TODO 2.1 驗證明寫 run 後 `data_cache/feature_preprocessing/d_star_*.json` 新增；實碼 `_d_star_cache_dir()` 固定 project `data_cache`（`feature_preprocessor.py:2959-2962`）。本任務合約禁止修改 `data_cache/`；P4 雖寫隔離 work/cache，卻沒有可用 injection 契約。
   - 失敗方式：執行 Agent 不是違反紅線，就是無法完成驗收；還可能讀到 stale d* cache 造成假 hit/parity。
   - 修法：所有 P0/P2/P4 驗證用 tmp root，SPEC 指定 monkeypatch/injection 點與 fresh-cache assertion；production path 行為另以 path-resolution unit test證明，不實寫 repo data_cache。

### MAJOR

7. **[High] exact-first 分案仍留有「實測後改 tolerance」後門，沒有治理 gate。**
   - 證據：SPEC §G #3 寫「確認非 provenance 修復造成才以實測誤差定 gate」；同頁 §P4/§R 又寫既有差異應 fail+分案、不寬容差。兩者互斥。
   - 失敗方式：實作者可在同一批依觀察到的最大 diff 設 tolerance，等同用答案定門檻；「確認非修復造成」也無可證偽程序。
   - 修法：本批只允許 exact。任何 non-exact 一律 BLOCKED，另開有 frozen evidence、根因與獨立 review 的 SPEC；本 SPEC 不授權設定 atol/rtol。

8. **[High] 「CGSA byte 不變」目前沒有 byte-level oracle，且 live CGSA parity 無法抓 shared-code 同向漂移。**
   - 證據：SPEC §C 宣稱 registry 行為 byte 不變，但 P0 只存抽樣 JSON；P4 比當下 CGSA vs 當下 non-CGSA。`FeaturePreprocessor` 與 filter 是共用 production code。
   - 失敗方式：constructor/filter/common safe-skip 改動若同時影響兩路，parity 仍通過；registry 排程變化也可能不被欄值抽樣抓到。
   - 修法：P0 保存 CGSA ordered columns、row index、每欄 value/mask full hash、d* payload canonical hash；P4 對 frozen CGSA baseline做回歸。

9. **[Medium] P0「HEAD baseline」未凍結完整 config/env，golden 可重生但不一定可重現。**
   - 證據：文件只指定 symbol/tf/window 與 CGSA flag；實碼受 `FFACT_L65_WORKERS`、memory tier、L6.5 mode、dead-drop、sanitize、ADF engine/precision/cache state 等影響（例如 `feature_factory.py:3019-3074`）。
   - 失敗方式：不同機器/tier/env 生成不同 baseline，或 cache hit/miss 改變診斷；「腳本二跑 byte 同」不足以跨 tier。
   - 修法：baseline metadata 冻結 config dump、config hash、相關 env、engine versions、storage schema、cache fresh state與資料檔 hash；禁止讀既有 d* cache。

10. **[Medium] P3 宣稱「tmp cache dir + 完整 context」但沒有精確建立/保留 shared cache 的步驟。**
    - 證據：`FeaturePreprocessor` constructor 沒有 cache-dir 參數（`:129-148`）；`_create_d_star_cache()` 固定 `_d_star_cache_dir()`；chunked path結束會 `self._d_star_cache = None`（`:2666-2670`）。TODO 只說 `_d_star_cache_shared=True` 後 export。
    - 失敗方式：builder 仍寫 project data_cache，或 transform 後拿不到 cache object；Agent 可能再碰 private fields補洞。
    - 修法：指定 public/injected cache-dir API，或 builder 明確建立 `DStarCache(tmpdir, context, exact params)` 並定義 ownership/flush/export lifecycle；加 chunked 與 non-chunked 測試。

11. **[Medium] control + CGSA 雙 golden 只保護 L1/L2 parity 與 L3-L6 non-CGSA stability，沒有驗證 CGSA 與 non-CGSA 的 L3-L6 原本是否一致。**
    - 證據：SPEC §G T3 限定 L1/L2 交集；control #5 只比較修前/修後 non-CGSA L3-L6。
    - 失敗方式：既有 L3-L6 CGSA/frame 分歧可被保留且報告仍稱「對齊」；若目標僅 fracdiff selection，文件需明示此非目標，避免過度宣稱。
    - 修法：明確把目標命名為「L1/L2 fracdiff selection parity」；另報告 L3-L6 cross-path差異 inventory，若要求全路徑對齊則需擴 scope。

### MINOR

12. **[High] `_build_column_layer_map` key 型別在同一 Task 互相矛盾。**
    - 證據：SPEC/TODO signature 與偽碼是 `Dict[str,str]`、`setdefault(str(col), ...)`，下一句又要求非字串欄名用實際 key避免 `str()` collision。
    - 修法：選定 `Mapping[Hashable, str]` 並保持原 key，或先用實測證明所有 production columns 必為 `str` 後 fail-fast。

13. **[High] §A 多個「已驗證事實」行號已漂移或描述過度。**
    - 證據：SPEC §A/manifest [D2-8] 引 `feature_factory.py:2508-2511` 作「L7 從 registry 讀」；這幾行只證明 `_run_layer6_5_preprocessor` 回空 frame，真正 registry-to-L7_raw 是 `3063-3085`。§A 把「fracdiff/ADF/d* 整段 no-op」綁在 filter，但 `_apply_adf_differencing()` `3311-3378` 仍獨立掃未 fracdiff 欄，不能由 fracdiff target empty 推出 ADF no-op。
    - 修法：更新事實為「fracdiff/d* no-op；ADF 是否改值需實測另證」，並用真正 L7 writer 行號。

## §0 被當成事實的未驗證假設

- 「兩 path 都有同質 L7_raw artifact」：**assumption，被實碼否定**。
- 「抽樣 hash 足以證明 exact/byte unchanged」：**assumption，否定**。
- 「最終 artifact 可辨識 layer」：**assumption，否定**。
- 「map 接線需改 `_group_requires_slow_transform`」：**assumption，flat path 控制流否定**。
- 「CGSA/non-CGSA float32 exact 可達」：文件標中信心，尚未實測；可作 fail-closed hypothesis，不可作已知。
- 「non-CGSA fracdiff empty 等於 ADF 也 no-op」：**未驗證且由獨立 ADF 控制流質疑**。

## §1 十類檢查

1. 矛盾/互斥：有，見 #4、#7、#12。
2. 漏項/端到端：有，缺雙 artifact extractor、layer provenance、cache isolation，見 #1、#3、#6。
3. 不可測驗收：有，抽樣 golden 無法證 exact，見 #2、#5。
4. 可疑 quant 假設：有，ADF no-op 宣稱未證、layer parity 範圍過度宣稱，見 #11、#13。
5. 過度工程：有風險；修改 registry scheduler helper 對 flat 修復無必要，見 #4。
6. OOM/並行：未發現新增 production 並行設計；但 full golden 應用 streaming hash，避免 materialize CGSA 全矩陣。
7. Cache 正確性：有，repo data_cache 寫入/stale cache/isolation 未封閉，見 #6、#9、#10。
8. API/型別/相容：有，map key type矛盾與新增 export lifecycle不完整，見 #10、#12。
9. 測試品質：有，sample hash、live-vs-live parity、錯誤 d* layer assertion，見 #2、#5、#8。
10. Agent 可執行性：有，Task 2.1 scope互斥、P3 cache dir無接線、artifact reader未指定，見 #1、#4、#10。

## §A 親自抽查

- `FFACT_USE_CGSA` default `1`：確認，`feature_factory.py:915-917`。
- CGSA L6.5 helper回空 frame：確認，`feature_factory.py:2501-2511`。
- CGSA 真正 L7_raw writer：確認，`feature_factory.py:3063-3085`；result空 frame：`3163-3165`。
- non-CGSA Layer 7：確認，`feature_factory.py:3363-3371,3447-3449`，為 final frame + legacy HDF5，不是同一 raw_v2 writer。
- provenance merge前存在、merge後遺失：確認，`feature_factory.py:348,3619-3652`。
- registry source_layer filter：確認，`feature_preprocessor.py:2886-2929`；現有回歸 `tests/test_l65_parallel.py:214-228`。
- `_group_requires_slow_transform` 屬 registry/CGSA排程：確認，`feature_preprocessor.py:1167-1206` 及 raw-sink caller `:463`。
- tier2a 舊 dict bug：確認，`scripts/build_l65_golden.py:236-241`；DStarCache entries為 feature-name key，`_d_star_cache.py:296,548`。
- 真實 kline：親自讀 `data_cache/feature_klines/kline_cache.h5`，`BTCUSDT/12h/data` 1696 rows、int64 epoch seconds，範圍 2024-01-01 至 2026-04-27；指定 2024-06-01~2024-12-01 有 367 rows。

ASSUMPTIONS_VERIFIED: CGSA empty-result trap; CGSA raw_v2 vs non-CGSA legacy HDF5 split; merge前provenance/merge後遺失; registry-only slow-routing helper; d* key語意; real kline timestamp unit/range
TESTS_RUN: read-only static inspection (rg/nl); h5py data probe PASS (BTCUSDT/12h 1696 rows, requested window 367 rows); no generation/pytest run to avoid modifying data_cache or golden files
FAILURES_SEEN: none
SCOPE_CHANGES: none; added only this handoff report; docs/ and momentum/ untouched
NUMERIC_OR_SCHEMA_IMPACT: none (review only)
STATUS: FAIL — 六項 BLOCKING：artifact contract/extractor、full golden、layer provenance、CGSA scope矛盾、tier2a key語意、cache隔離
