# fracdiff max_lag 修復（併 P1-FF-6）TODO　（DRAFT / 基於 docs/FRACDIFF_MAXLAG_SPEC.md / 2026-07-03）

## 追溯索引（SPEC/manifest ID → 本檔位置；合計 14 ID）
| ID | SPEC 原文節錄 | TODO 落點 |
|---|---|---|
| A-1 | 「max_lag 預設分支改為 calibration-derived」 | Task 1.1 |
| A-2 | 「FractionalDifferencingConfig 新增顯式 max_lag」 | Task 1.2 |
| A-3 | 「warmup_window fallback 一致性決議」 | Task 1.3 |
| A-4 | 「fracdiff_hash 已含 max_lag → 自動 miss」 | Task 1.4 |
| A-5 | 「不得殘留其他 len(df)→max_lag 耦合」 | Task 1.4 |
| B-1 | 「移除兩個 fracdiff xfail…斷言一字不得放寬」 | Task 2.1 |
| B-2 | 「把 max_lag 改回 len(df)//10…必轉紅」 | Task 2.2 |
| B-3 | 「移除 cache key 中 symbol/TF/fingerprint…必紅」 | Task 2.3 |
| B-4 | 「len(df)∈{510,590,600,5000} 全部回傳 50」 | Task 2.4 |
| C-1 | 「非 fracdiff 欄 byte 級不變…pin=50 等價」 | Task 3.1 |
| C-2 | 「三方獨立簽核…至少一腿 adversarial」 | Task 3.1 |
| C-3 | 「slow 全鏈 receipt + restore_golden_inventory」 | Task 3.2 |
| D-1 | 「ROADMAP/HANDOFF/stateful audit 同步」 | Task 3.3 |
| D-2 | 「全過程檔 register-output」 | Task 3.3 |
| §G | Golden：G1(現行auto)/G2(現行pin50) 動工前凍結 | Task 0.1 |

## §0 全域規則與約束（執行端讀完即可遵守）
- 解耦：`momentum/` 不 import `api/`（`grep -r "from api\." momentum/` → 0）；config 單一來源。
- Logging：`from api.core.logging import get_logger` 僅 api 側；momentum 側用模組 logger；熱迴圈禁 log。
- 型別註記全函式；docstring 中文；vectorize 優先。
- 不可違反：不弱化 NaN/inf gate；不擅改輸出大小；不碰跨tier/多symbol 穩定性路徑；資料一律真實 kline（`data_cache/feature_klines/kline_cache.h5`），**禁合成 fixture 代替值守恆驗證**。
- **防假綠**：不得放寬/刪除既有測試斷言（尤其 `_assert_fracdiff_truncation_invariants`、`_assert_d_star_gate`、mutation negative controls）；驗收憑 diff 斷言 + receipt。
- 範圍紅線：**不做** d\* 持久化、其他 preprocessing 層行為變更、preset 盤點、batch checkpoint/RunLease 污染面（B-5 defer）。
- 慢測紀律：slow 跑後 `./scripts/restore_golden_inventory.sh`；清 pytest 舊輪次留 pytest-current。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B0 | 0.1 | 無 | Golden 凍結必先於改碼（改後就採不到「改前」基線） | 小 |
| B1 | 1.1, 1.2, 1.3, 1.4 | B0 | 同一 production 修復面、單 commit 可 revert | 中 |
| B2 | 2.1, 2.2, 2.3, 2.4 | B1 | 測試層整批、共用 helper | 中 |
| B3 | 3.1, 3.2 | B2 | 簽核證據包一次產出 | 中 |
| B4 | 3.3 | B3 | 文件收尾 | 小 |
- Batch Gate：B1→B2 憑 Task 2.4 unit 綠 + §G 條件 1/2 通過；B2→B3 憑兩 MR slow passed receipt；B3→B4 憑三方簽核檔齊。
- 派工 prompt 於派工時由編排端按本檔 Task 組裝（含前置狀態 + pytest 指令），不預嵌長 prompt。

## Phase 0 — Golden 凍結（目標：改碼前基線入庫；完成後系統狀態：兩份 baseline receipt 存在）
### Task 0.1 — §G Golden G1/G2 凍結（adversarial 修訂：run contract 寫死 + 全欄 digest + cache 隔離）
- SPEC ref：§G　目標：動工前產出 G1（現行 auto）與 G2（現行 pin max_lag=50）兩份 baseline。
- **run contract（寫死，不得自選）**：config = `tests/feature_engineering/ff_truncation_mr_helpers._fracdiff_mr_config_payload()`（calibration_bars=500）；窗長 = `_fracdiff_window_bars(config)`（≥600，與 MR 同款）；symbol=BTC,ETH × 1h（`data_cache/feature_klines/kline_cache.h5`）；**每 run 獨立空 d\* cache 目錄** + `force_regenerate=True`。
- **G2 pin 法（2026-07-03 委員會裁定，SPEC §G/§A.10）**：config path 會丟棄 max_lag → G2 用 **G2-only `FeaturePreprocessor.__init__` wrapper 注入實例 `fracdiff_config["max_lag"]=50`**（wrapper 內 fail-fast assert）；防呆斷言四條：G2 全 d\* payload `max_lag==50`、G2 `fracdiff_hash`≠G1、fracdiff 欄 digest 必不同/非 fracdiff 必相同、patch 結束 `__init__` 還原。receipt 記 `pin_method=preprocessor_instance_fracdiff_config_injection`。
- 輸入 / 輸出：現行 main HEAD code + 真實 kline → 輸出 parquet（每 run 全欄位）+ digest json：`handoffs/run_receipts/<UTC>-fracdiff-maxlag-golden-{G1,G2}.json/.log`。
- **digest 內容（oracle，禁抽樣 hash）**：per-column 全量 `value_sha256` + `nan_mask_sha256` + dtype + index hash + feature 名稱/順序 schema hash；per-feature mean/std/nan_ratio 另列為人讀診斷。**不得**用 `build_l65_golden_baseline.py` 的 `_sampled_value_and_nan_hashes`（13 row 抽樣）充當 oracle——新寫全欄 digest helper（如 `tests/feature_engineering/ff_maxlag_golden_helpers.py::canonical_column_digests(df) -> dict`）。
- **receipt 必記**：每 run 的 resolved max_lag、DStarCache 檔案路徑與 payload `fracdiff_hash`、cache hit/miss 計數（`cache.stats()`）。
- **穩定性前置**：G1 同 config 同 n_jobs 連跑兩次 digest 全同才算凍結成功（float 並行 reduction 穩定性）。
- 修改檔案：新 helper + 腳本（`scripts/` 或 tests helper）；無 production 檔。既有 caller：無。
- 不可做：不改任何 production 檔；不採合成資料；不用抽樣 hash 當 oracle。
- 邊界：kline 快取缺 symbol → 明確報錯不靜默換資料；重跑冪等（同輸入同 digest）。
- 風險緩解：§G（無基線=驗收口說）+ Codex #1/#2 + Composer P0-1。
- 驗證：兩 receipt 檔存在且載上列欄位；G1 vs G2 的 fracdiff 欄 digest 不同（pin 生效證明）、非 fracdiff 欄 digest 相同；G1 記錄的實際推導 max_lag 落檔（不硬編 60）。

## Phase 1 — production 修復（目標：max_lag 與 len(df) 解耦；完成後：預設推導=f(calibration_bars)）
### Task 1.1 — [A-1] max_lag 預設改 calibration-derived
- SPEC ref：Task 1.1　目標：`_apply_fractional_differencing` 預設分支解耦 len(df)。
- 輸入 / 輸出：`feature_preprocessor.py:3198-3200` 現行分支 → 新推導（int）。
- 實作要點：①新增 **resolver seam** `def _resolve_fracdiff_max_lag(self) -> int:`——config 顯式正值→原值，否則 `min(max(2, self._calibration_bars() // 10), 252)`；②`_apply_fractional_differencing` 的 :3198-3200 分支改為呼叫該 resolver（production 唯一推導點，供 Task 2.2 monkeypatch）；③更新行內註解為「校準窗長度推導，禁 len(df) 依賴（截斷不變性）」；④確認該值傳入 cache 建構與 serial/parallel 兩路徑（介面不變，僅值來源改）。
- 修改檔案：`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py::_apply_fractional_differencing` + 新方法 `_resolve_fracdiff_max_lag`。既有 caller：同檔 cache 建構、`_apply_fractional_differencing_{serial,parallel}`（無簽名變更）。
- 不可做：不改 `_get_weights_ffd`/`_frac_diff_convolve`；不動 precision/adf_threshold/weight_threshold。
- 邊界：①df=300 根（<500）→ resolver 回 50 且 d\* 搜尋實際只用 300 bars；短 df oracle：resolved==50、輸出 row count 不變、無例外、`size<w` NaN 保護不弱化（補一測）；②config calibration_bars=800 → max_lag=80。短窗截斷 MR 保證不在範圍（SPEC §N）。
- 風險緩解：(a)(d) + Codex #4。
- 驗證：Task 2.4 unit 全綠；§G 條件 1（修後 fresh-cache vs G2 全欄 digest 一致）。

### Task 1.2 — [A-2] config 顯式 max_lag 欄位
- SPEC ref：Task 1.2　目標：schema 顯式化。
- 輸入 / 輸出：`feature_config.py:183-191` → `max_lag: int = 0`（0=auto）。
- 實作要點：①加欄位 `max_lag: int = Field(default=0, ge=0)` + 中文註解「0=auto（由 calibration_bars 推導）；>0 顯式覆蓋」；②負值由 `ge=0` fail-fast；③檢查 config_manager / `momentum/FeatureEngineering/preprocessing/_native_tf_helpers.py:98-118` / warmup_window 讀取點相容（皆 `.get`/model_dump，向後相容）。
- 修改檔案：`momentum/FeatureEngineering/feature_config.py::FractionalDifferencingConfig`。既有 caller：`warmup_window.py:292`、`_native_tf_helpers.py:98-118`、config 序列化消費者。
- 不可做：不加其他欄位；不改 enabled 預設。
- 邊界：①舊 config dict（無 max_lag）載入 → 0 且不炸；②max_lag=-1 → ValidationError。
- 風險緩解：(b) schema 下游。
- 驗證：pydantic round-trip 測試 passed；舊 dict（無 max_lag）載入後值 == 0 測試 passed；**G2' 交叉驗證**：schema 落地後用真 config 路徑 pin=50 重跑 golden run contract，G2' digest == G2（SPEC §G D 增強）。

### Task 1.3 — [A-3] warmup fallback 決議落地
- SPEC ref：Task 1.3　目標：保留 252 保守 fallback + 註解引用本 epic。
- 輸入 / 輸出：`warmup_window.py:292-295` → 僅加註解，邏輯不動。
- 實作要點：①註解說明「值路徑 max_lag 已改 calibration-derived(50)；warmup 保守取 252 上限，只影響預熱長度非值正確性」；②引用 `docs/FRACDIFF_MAXLAG_SPEC.md`；③確認 config 顯式 max_lag>0 時 warmup 用顯式值（現行為）。
- 修改檔案：`momentum/FeatureEngineering/warmup_window.py`（註解）。既有 caller：不變。
- 不可做：不改 fallback 值（縮短預熱=行為變更，超範圍）。
- 邊界：①config max_lag=37 → warmup base_windows 含 37；②max_lag=0 → 含 252（不變）。
- 風險緩解：⊘。
- 驗證：`pytest tests/ -k warmup_window -v` 全 passed（既有測試零修改，diff 為證）。

### Task 1.4 — [A-4]+[A-5] cache 失效確認 + 耦合掃描
- SPEC ref：Task 1.4　目標：無殘留耦合、無舊 cache 污染。
- 輸入 / 輸出：掃描報告（交接檔節）+ 新測試。
- 實作要點：①grep/讀 `feature_preprocessor.py`、`_slow_path_parallel.py`、`_d_star_cache.py`、`preprocessing/_native_tf_helpers.py` 全部 max_lag 來源，列表證明僅 [A-1] resolver 一處推導；②測試：同 config、len(df)=600 vs 590 → `fracdiff_hash` 相同（修前不同）；③**舊 cache 兩案分立**（Codex #3）：(a) 修前 auto cache（max_lag=60 hash）→ 修後必 miss 重算不炸；(b) 修前顯式 pin=50 cache → payload + strong_value_fp 全符時允許合法命中（正確重用非污染），兩案分開斷言。
- 修改檔案：新測試檔 `tests/feature_engineering/test_fracdiff_maxlag_derivation.py`（與 Task 2.4 同檔）。既有 caller：無。
- 不可做：不改 cache 檔格式/校驗邏輯。
- 邊界：①cache 目錄不存在 → 正常建立；②payload row_count 檢核行為不變（截斷對 full/trunc 仍分開快取——這是 payload 隔離，非 hash 耦合）。
- 風險緩解：(a) 舊值污染。
- 驗證：len 600 vs 590 fracdiff_hash == 測試 passed；掃描列表入交接檔（grep 產物）。

### Phase 1 測試 + Gate
- 單元：Task 2.4 推導測試、1.2 schema 測試、1.4 hash 測試。邊界：短 df、負值 config、舊 cache。效能：無新增熱路徑（推導一次性），⋅跳過 benchmark。
- **Gate**：`pytest tests/feature_engineering/test_fracdiff_maxlag_derivation.py -v` 全綠 + §G 條件 1/2 通過才進 Phase 2。

## Phase 2 — 測試轉綠 + P1-FF-6 探針（目標：護網轉綠且可證偽）
### Task 2.1 — [B-1] 移除兩 xfail
- SPEC ref：Task 2.1　目標：兩 fracdiff MR 轉綠。
- 輸入 / 輸出：`test_ff_fullchain_truncation_mr.py:111-155` 兩個 `@pytest.mark.xfail(strict=True)` 裝飾器與其註解塊（:111-115, :135-138）移除 → 測試本體不動。
- 實作要點：①只刪 xfail 裝飾器+過時註解；②`_assert_fracdiff_truncation_invariants`、`_assert_d_star_gate`（`ff_truncation_mr_helpers.py`）一字不改；③slow 實跑兩測試。
- 修改檔案：`tests/feature_engineering/test_ff_fullchain_truncation_mr.py`。既有 caller：無。
- 不可做：不放寬 atol/d\* 相等/NaN mask exact；不改 helper。
- 邊界：①實跑紅 → 修 production 回 Phase 1，不修測試；②xfail(strict) 殘留會使綠燈報 XPASS 錯誤 → 必須真移除。
- 風險緩解：(d)。
- 驗證：slow 實跑「2 passed」receipt（`handoffs/run_receipts/<UTC>-fracdiff-maxlag-mr-green.log`）；diff 確認斷言零修改。

### Task 2.2 — [B-2] max_lag mutation 探針
- SPEC ref：Task 2.2　目標：MR 可證偽（紅得起來）。
- 輸入 / 輸出：新 mutation 測試（同既有 `test_mutation_fracdiff_*` 慣例）。
- 實作要點：①monkeypatch **`FeaturePreprocessor._resolve_fracdiff_max_lag`**（Task 1.1 seam）使回傳 len(df)//10 等效值；②**兩 MR 各一 mutation 檢查**：截斷 MR（600→590）與尾端擾動 MR 皆斷言 `_assert_d_star_gate`/值斷言拋 AssertionError（共用 mutant fixture 可）；③**parallel mutation case**：強制 `n_jobs>1` 走 `_slow_path_parallel`（縮欄數控時長）實測 mutant 穿透，不得只用參數同源論證。
- 修改檔案：`tests/feature_engineering/test_ff_fullchain_truncation_mr.py`（新增 `test_mutation_fracdiff_maxlag_len_coupling_fails` 等）。既有 caller：無。
- 不可做：不把 mutant 寫進 production 碼（僅 monkeypatch resolver seam）；不複製 helper 邏輯。
- 邊界：①mutant 下 d\* 恰好相等（網格巧合）→ 選已知會分歧的窗長組合（600/590 已實證分歧 0.4844/0.4688）；②monkeypatch 洩漏到其他測試 → fixture 隔離。
- 風險緩解：測試章程 B1 + Codex #4/#6 + Composer ⑤。
- 驗證：mutation 測試 pytest 單跑 passed（serial+parallel 各≥1、兩 MR 皆覆蓋，=內部斷言確實 FAIL）。

### Task 2.3 — [B-3] P1-FF-6 d\* cache key mutation 探針
- SPEC ref：Task 2.3　目標：cache 隔離護網可證偽。
- 輸入 / 輸出：新測試集（每 mutant 一測）。
- 實作要點（對準 v3 真實 guard，Codex #5 + Composer P0-2 重設計）：①mutant 清單：path symbol（構造「同 path 錯 payload」或跨 symbol 錯誤命中，**不重複** P1-FF-5 V5.2）、path timeframe、`fracdiff_hash` 移除 **max_lag** 成分（本 epic 核心軸）、`fracdiff_hash` 移除 **calibration_bars** 成分（`_d_star_cache.py:227`）、payload `row_count`（:421）、payload `time_range`（:425）、per-column `strong_value_fp`（:482-486；若 `test_d_star_col_fingerprint.py` 已覆蓋則引用標「不重複」）；②每 mutant 下對應隔離/失效測試必 FAIL，pytest.raises + match 訊息可辨識；③mutant 逐一開關互不遮蔽（獨立 fixture）；④`data_fingerprint` 不做（legacy 路徑，SPEC §N）。
- 修改檔案：新檔 `tests/feature_engineering/test_dstar_cache_key_mutation.py`。既有 caller：無。
- 不可做：不動 production cache 邏輯；不擴到 batch checkpoint/RunLease（B-5 defer）；不重複既有 fingerprint/path 測試。
- 邊界：①mutant 後 cache 誤命中須被**值斷言**抓到（非只 hash 斷言）；②cache 停用（cache_d_star=False）時測試 skip 有明確 reason。
- 風險緩解：(d) 章程 B1。
- 驗證：≥6 mutant 測試全綠（各自內部 FAIL 被捕獲）；`pytest tests/feature_engineering/test_dstar_cache_key_mutation.py -v` 通過 + `scripts/mutation_probe_check.sh tests/feature_engineering/test_dstar_cache_key_mutation.py` exit 0。

### Task 2.4 — [B-4] 推導 unit 測試
- SPEC ref：Task 2.4　目標：快測常駐 CI。
- 輸入 / 輸出：`tests/feature_engineering/test_fracdiff_maxlag_derivation.py`。
- 實作要點：①len(df)∈{510,590,600,5000} → 推導皆 50（calibration_bars=500）；②calibration_bars=800 → 80；③config 顯式 37 → 37；④上限 252：calibration_bars=3000 → 252。
- 修改檔案：同上新檔。既有 caller：無。
- 不可做：不標 slow；不依賴 kline 資料（純推導邏輯 unit）。
- 邊界：①calibration_bars=10 → max(2, 1)=2 下限；②len(df)=0 空 DF → 既有早退路徑不觸推導；③`len(clean)<20` 時 d\* 硬回 1.0（`feature_preprocessor.py:3701-3702`）行為不變記錄一例。
- 風險緩解：⊘。
- 驗證：`pytest tests/feature_engineering/test_fracdiff_maxlag_derivation.py -v` 全綠、<10s。

### Phase 2 測試 + Gate
- 單元：2.4。邊界：mutant 隔離、XPASS。效能：mutation 測試用縮小窗防慢測膨脹。
- **Gate**：兩 MR slow「2 passed」receipt + mutation 套件綠才進 Phase 3。

## Phase 3 — 值守恆簽核 + 收尾（目標：三方 PASS、文件入庫）
### Task 3.1 — [C-1]+[C-2] 三方值守恆簽核
- SPEC ref：Task 3.1　目標：§G **四**條件證據包 + 三方獨立簽核。
- 輸入 / 輸出：G1/G2（Task 0.1）+ 修後跑（同 run contract、**fresh 獨立空 cache**）→ 對照報告 `handoffs/<date>-FRACDIFF-MAXLAG-CONSERVATION-{claude,codex,composer}.md`。
- 實作要點：①修後預設（fresh cache）vs G2：fracdiff 欄 per-column 全欄 digest 一致（**oracle=canonical digest，任一欄不同即 FAIL**；per-feature 統計僅輔助，無雙軌）；②修後 vs G1：非 fracdiff 欄全欄 digest 一致 + row count/index 相等；fracdiff 欄 diff 報告列 G1 實際 max_lag（非硬編 60）+ 差異樣本（≤20 欄，1e-8 尺度）；③條件 4：[B-1] slow MR receipt 引用（截斷不變另證，§G 為必要非充分）；④三方各自獨立審方法論+證據，至少一腿 adversarial 式（主動構造反例：換 symbol、換窗長重跑試圖打破守恆）；⑤Claude 先自產一版再派兩家；⑥receipt 引用 resolved max_lag / fracdiff_hash / cache hit-miss。
- 修改檔案：無 production；報告檔。既有 caller：無。
- 不可做：不用合成 fixture；不用抽樣 hash 作 oracle；不共用 cache 目錄跨 run。
- 邊界：①float 並行 reduction → 同 config 同 n_jobs 連跑兩次 digest 全同（Task 0.1 已前置）才有效；②任一方 FAIL → 回 Phase 1，不降級。
- 風險緩解：(a)(d) 三方簽核鐵律。
- 驗證：3 份簽核檔（handoffs/*.md）各載「PASS」+ 反例嘗試記錄；引用格式「檔載『…』(出處:檔名)」。

### Task 3.2 — [C-3] slow 全鏈 receipt
- SPEC ref：Task 3.2　目標：全鏈實跑存證。
- 實作要點：①`pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -v -m slow`（含 fracdiff MR、mutation controls）；②receipt 進 `handoffs/run_receipts/`；③跑後 `./scripts/restore_golden_inventory.sh` + 清 pytest 舊輪次。
- 修改檔案：無。不可做：不跳 mutation controls。
- 邊界：①跑掛在中途 → receipt 記 FAIL 不得改寫；②golden inventory 未還原 → 後續測試污染（必還原）。
- 風險緩解：慢測紀律（§0）。
- 驗證：receipt 檔載 passed 計數；restore 腳本 exit 0。

### Task 3.3 — [D-1]+[D-2] 文件與留痕
- SPEC ref：Task 3.3　目標：治理收尾。
- 實作要點：①ROADMAP P1 節標完成+殘餘；②HANDOFF ≤30 行更新；③`docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md` max_lag 語意同步（若載）；④全過程檔 `gate.sh register-output`。
- 修改檔案：docs/ROADMAP.md、HANDOFF.md、audit 檔。既有 caller：無。
- 不可做：不覆蓋他人 handoff；HANDOFF 不超 30 行。
- 邊界：①register-output 檔案 sha 綁定（改一字失效）→ 註冊後不再編輯；②「已驗/passed」必附 receipt 出處。
- 風險緩解：治理 O3。
- 驗證：`scripts/reconcile_stamps_check.sh` 與 gate checker exit 0；commit 過 pre-commit checklist。

### Phase 3 測試 + Gate
- **Gate（epic 完成）**：三方簽核檔齊 PASS + slow receipt + 文件 commit/push。

---
自檢（階段 3）：14 ID 全落點（見追溯索引，合計數一致）；每 Task 含驗證/邊界/不可做；單層任務（純後端+測試）全棧鏈 ⋅跳過；無空殼 Task。
Frozen 前 handoff：`SPEC=docs/FRACDIFF_MAXLAG_SPEC.md TODO=docs/FRACDIFF_MAXLAG_TODO.md FOCUS=值守恆/截斷不變/mutation可證偽`（未過雙家族 adversarial 前 = Internal Frozen）。
