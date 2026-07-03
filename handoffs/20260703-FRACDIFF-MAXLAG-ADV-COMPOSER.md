# FRACDIFF max_lag SPEC/TODO — Composer 雙家族 Adversarial Review

> task-id: `fracdiff-maxlag-adv-composer-20260703`  
> 審查對象：`docs/FRACDIFF_MAXLAG_SPEC.md`、`docs/FRACDIFF_MAXLAG_TODO.md`、`docs/FRACDIFF_MAXLAG_MANIFEST.md`、`docs/FRACDIFF_MAXLAG_EPIC_BRIEF.md`  
> 背景三腿：`handoffs/20260702-FF-DSTAR-GATE-{CLAUDE,CODEX,COMPOSER}.md`  
> 實碼驗證：`feature_preprocessor.py`、`_d_star_cache.py`、`ff_truncation_mr_helpers.py`、`build_l65_golden_baseline.py`、`test_ff_cross_symbol_value_isolation.py`  
> 方法：挑戰前提 + 獵漏（非確認式）；獨立重判 §A 事實 vs 假設

---

## Verdict：需修補後派工

SPEC/TODO 主修向（`max_lag` 解耦 `len(df)`、G2 對照、B-1 轉綠）與三腿根因分析一致，但 **§G 值守恆驗收鏈與 B-3 探針範圍存在可假綠空間**，且 **EPIC_BRIEF 與 SPEC 簽核範圍矛盾**。修補後可派工；未修前不宜 Frozen。

---

## 被當成事實的未驗證假設（§0）

| # | 陳述位置 | fact 還是 assumption？ | 判定 |
|---|---|---|---|
| 1 | SPEC §G / MANIFEST C-1：變更「僅」可由 max_lag 60→50 解釋 | **部分 assumption** | 「60」只在 MR 窗 `FRACDIFF_MIN_BARS=600`（`ff_truncation_mr_helpers.py:42,158-160`）下成立；Task 0.1 未鎖定 row 窗，G1 auto 可能是 `len(df)//10` 而非 60 |
| 2 | TODO Task 0.1：「複用既有 golden inventory 工具鏈」可支撐 §G「byte 級一致」 | **assumption（錯）** | `build_l65_golden_baseline.py:275-308` 用固定 row **抽樣** hash + per-feature mean/std，非 byte 級全欄比對 |
| 3 | EPIC_BRIEF §7：三方簽核用「10 幣種 × 3 TF」 | **與 SPEC 矛盾** | SPEC §G / Task 0.1 僅 BTC+ETH × 1h；C-2 繼承窄範圍 |
| 4 | SPEC §A.5 + Task 1.4：fracdiff_hash 含 max_lag → 舊 cache 自動 miss | **fact（已驗）** | `_compute_fracdiff_hash` 含 `max_lag`（`_d_star_cache.py:206-221`）；`_payload_matches` 比對 `fracdiff_hash`（`:399-401`） |
| 5 | B-3 五探針「足以覆蓋章程 B1 cache key 意圖」 | **assumption（不足）** | 本 epic 核心隔離軸是 **max_lag∈fracdiff_hash**；五探針未含 max_lag / fracdiff_hash |
| 6 | Task 2.2：parallel 路徑「參數同源論證」= 已覆蓋 | **assumption** | parallel 僅從 `column_metadata.get("max_lag")` 取值（`_slow_path_parallel.py:128`），無 mutation 實測 |

---

## Findings

### 挑戰前提（最前）

**[BLOCKING | High]** §G 宣稱「byte 級一致」，Task 0.1 卻指向抽樣 hash 工具鏈 — 值守恆可假綠  
- **證據**：SPEC §G L33-36「fracdiff 欄 **byte 級一致**」「非 fracdiff 欄 **byte 級一致**」；TODO Task 0.1 L45「複用既有 golden inventory 工具鏈」+ `sampled_value_hash`；`build_l65_golden_baseline.py:275-308` `_sampled_value_and_nan_hashes` 僅 13 個固定 row × 全欄抽樣。  
- **會怎麼失敗**：非抽樣列漂移、值重排、局部 NaN 位移 → sampled hash + mean/std 仍同 → §G 條件 1/2 假 PASS，B-1 MR 仍紅。  
- **修法**：Task 0.1 / 3.1 明寫比對工具（建議 `ff_artifact_compare_helpers.canonical_frame_digest` 或 MR 同款 parquet `np.array_equal`/`assert_allclose` per-column）；§G 與 Task 3.1 禁止僅用 `sampled_value_hash` 作為 byte 級 PASS 依據；保留 per-feature stats 作輔助非替代。

**[BLOCKING | High]** Task 0.1 Golden 凍結缺可重現的 run contract（config / 窗長 / pipeline）  
- **證據**：SPEC §G L30-31 要求「MR 同款 config」；TODO Task 0.1 L45 只列 inventory 欄位，**未**引用 `_fracdiff_mr_config_payload()` 或 full-chain vs L6.5-only；`build_l65_golden_baseline.py` 走 IC-First L6.5（`:122-139`），與 MR fracdiff-only 不同。  
- **會怎麼失敗**：執行端各用不同 config/窗長凍結 G1/G2 → C-1「60→50」敘事失真；G2 與修後對照不可復現。  
- **修法**：Task 0.1 寫死：config 來源（`ff_truncation_mr_helpers._fracdiff_mr_config_payload` + G2 覆寫 `max_lag:50`）、symbol/TF、date window、`window_bars`（建議 ≥600 與 MR 一致）、產物路徑與比對腳本。

**[BLOCKING | High]** EPIC_BRIEF 三方簽核範圍與 SPEC C-2 不一致  
- **證據**：EPIC_BRIEF §7 L70-72「10 幣種 × 3 時間框架」；SPEC §G / TODO Task 0.1 / 3.1 僅「BTC+ETH × 1h」。  
- **會怎麼失敗**：使用者以 Brief 為準期待廣覆蓋；執行端按 SPEC 窄跑 → 簽核爭議或假完成。  
- **修法**：Brief §7 改與 SPEC 一致，或 SPEC/Task 3.1 擴大並標成本；C-2 明寫最終符號×TF 清單。

---

### ① §G Golden（G1/G2 + 三條件）— Claude 腿重點

**[BLOCKING | High]** G2 與修後對照邏輯正確，但驗收鏈不保證與 G2 **byte** 等價（見上抽樣 hash）  
- **證據**：§G 條件 1「修後預設 vs (G2) fracdiff byte 級一致」；G2 語意 = 現行 code + 顯式 `max_lag=50`（SPEC §G L31）。  
- **碼證（G2 隔離語意）**：`fracdiff_hash` 含 `max_lag`（`_d_star_cache.py:221,302-307`）；檔名 `d_star_{symbol}_{timeframe}_{fhash[:12]}.json`（`:327-331`）。G1 auto（600 行→60）與 G2 pin50 **不同 hash**，修後 auto50 應與 G2 **同 hash**，不會誤讀 G1 舊檔 — **隔離語意成立**。  
- **假綠空間**：條件 1 PASS 不代表條件 2 非 fracdiff 無漏；條件 1+2 皆 PASS 仍可能未跑 B-1 截斷 MR（600→590 d* gate）。§G 對「同窗全量 run」有效，對「截斷不變」是必要非充分。

**[MAJOR | High]** §G 條件 2 與條件 1 的 fracdiff 敘事硬編「60→50」可能與實際 G1 不符  
- **證據**：MANIFEST C-1 L41-42「max_lag 60→50」；G1 推導 `len(df)//10`（`feature_preprocessor.py:3198-3200`）。若 Golden 窗 ≠600，G1 max_lag ≠60。  
- **會怎麼失敗**：簽核報告敘事錯但測試仍可能 PASS（50 vs 50）。  
- **修法**：條件 2 改為「fracdiff 欄允許差異；diff 報告須列 G1 實際推導 max_lag 與修後值」。

**[MAJOR | Medium]** G1/G2 凍結未要求記錄 `fracdiff_hash` / 實際 `max_lag` 入 receipt  
- **證據**：TODO Task 0.1 inventory 欄位無 `fracdiff_hash`、無 runtime `max_lag`。  
- **會怎麼失敗**：事後無法證明 G2 pin 生效或 cache 隔離如預期。  
- **修法**：receipt 必含每 run 的 `max_lag` 推導值、`DStarCache.path` 檔名、payload `fracdiff_hash`。

**[NON-BLOCKING | Medium]** §G 條件 3「列出 feature + diff」未規範精度/欄數上限  
- **證據**：SPEC §G L36。  
- **修法**：引用 MR 同款 `atol≤1e-8` + exact NaN mask（`ff_truncation_mr_helpers.py:44,1009-1019`）或列最多 N 欄樣本。

---

### ② Task 2.3 / P1-FF-6 — 五個 cache key mutation 探針 vs 章程 B1

**[BLOCKING | High]** 五探針未覆蓋本 epic 核心：`max_lag` / `fracdiff_hash`  
- **證據**：TODO Task 2.3 L122 列 symbol、TF、fingerprint、row_count、time_range；**無** max_lag、fracdiff_hash、calibration_bars（均在 `_compute_fracdiff_hash`，`_d_star_cache.py:206-227`）。章程 B1（`TEST_DESIGN_CHARTER.md:50`）要求 cache key 少隔離維度必紅；本 epic 修的就是 max_lag 進 hash。  
- **會怎麼失敗**：有人從 hash 移除 max_lag → 600/590 或 G1/G2 共用錯誤 d* → Task 1.4 正向測試仍可能過（若只測同 max_lag），B-3 全綠但回歸無探針。  
- **修法**：增第 6 探針 `max_lag` 或 `fracdiff_hash` 失效；最好兩者各一。Task 1.4 hash 測試需配對 mutation negative control（B1.1 同檔 `test_mutation_*`）。

**[MAJOR | High]** 「fingerprint」未指名，探針可能測錯層或與既有測試重複  
- **證據**：MANIFEST B-3 L31「fingerprint（含 row_count/time_range 類 payload 欄）」；`_d_star_cache.py` 同時有 `data_fingerprint`（`:38,494-495`）、`value_fp`/`strong_value_fp`（`:482-486`）。`test_d_star_col_fingerprint.py` 已覆蓋 value_fp（`:116-126,181-189`）；`test_ff_cross_symbol_value_isolation.py` V5.2 已覆蓋 path 級 symbol 隔離（`:60-62,431-441`）。  
- **會怎麼失敗**：B-3 實作 `data_fingerprint` mutant 與既有測試重複；未測「payload symbol 檢查移除但 path 仍含 symbol」時是否仍能 cross-hit。  
- **修法**：B-3 明寫探針目標函式（`_payload_matches` 哪個 field）；symbol/TF mutant 須構造 **同 path 錯 payload** 或 **跨 symbol 錯誤命中** 場景，而非重複 V5.2 path 測試。

**[MAJOR | Medium]** B-3 未覆蓋 `calibration_bars`∈fracdiff_hash 與 per-column `value_fp` 失效  
- **證據**：`calibration_bars` 在 hash（`_d_star_cache.py:227`）；`get_by_value_fingerprint` 為 production 熱路徑（`:495-500,501+`）。  
- **修法**：至少增 calibration_bars mutant；value_fp 若已由 P1-FF-5 覆蓋則 B-3 標「不重複」並引用檔名。

**[NON-BLOCKING | Medium]** Task 2.3 未寫 `mutation_probe_check.sh` / `MUTATION-PROBE` 合規  
- **證據**：章程 B1.1（`TEST_DESIGN_CHARTER.md:51`）；新檔 `test_dstar_cache_key_mutation.py` 需同檔 `test_mutation_*` 或行首 N/A。  
- **修法**：Task 2.3 驗證欄加 `scripts/mutation_probe_check.sh tests/feature_engineering/test_dstar_cache_key_mutation.py`。

---

### ③ 值守恆通過條件可證偽性

**[BLOCKING | High]** 見 §G「byte 級」vs 抽樣 hash — 三條件整體可證偽性不足（合併上列）。  

**[MAJOR | High]** Task 3.1 內部表述衝突：要求 per-feature 統計，又寫「hash 相等」即可  
- **證據**：TODO Task 3.1 L149「不以 hash 相同單點取代 per-feature 統計」vs L147「byte 級一致（hash 相等）」。  
- **修法**：改為「canonical digest 全欄 + per-feature stats 輔助；任一 fracdiff 欄 digest 不同即 FAIL」。

**[MAJOR | Medium]** 條件 1/2 未綁定 B-1 截斷 MR — 值守恆可與 MR 脫鉤  
- **證據**：Batch Gate B1→B2（TODO §B L39）用 §G 1/2，Phase 2 才跑 B-1；§G 為同窗全量 run，B-1 為 600→590 pair。  
- **會怎麼失敗**：全量 G2 等價 PASS，但尾截斷 d* 仍因其他 prefix 問題 FAIL（機率低但 C-1 不涵蓋）。  
- **修法**：Task 3.1 明列 B-1 slow receipt 為條件 4（必要），或 C-1 文案降級為「全量窗守恆」≠「截斷守恆」。

**[NON-BLOCKING | Low]** float 並行 reduction 穩定性（Task 3.1 L150）未給具體命令  
- **修法**：補「同 config 連跑兩次 canonical digest 相同」可執行 pytest/腳本。

---

### ④ Task 1.1 邊界 df < calibration_bars

**[MAJOR | Medium]** max_lag 推導邊界有寫、截斷語意邊界未封  
- **證據**：SPEC Task 1.1 L46「df=300 → max_lag 仍 50」；`_calibration_bars()` 不依 `len(df)`（`feature_preprocessor.py:175-178`）；但 `_calibration_series` 用 `min(len, bars)`（`:180-182`），300 行僅 300 根參與 d*。  
- **碼證**：`_fracdiff_values` 在 `_filled_slice.size < w` 回全 NaN（`:3737-3739`）。  
- **會怎麼失敗**：短窗生產路徑 d* 行為與 500 根校準語意不一致；SPEC 只要求「補一測」NaN 保護，未要求短窗截斷 MR。  
- **修法**：Task 1.1/2.4 增 case：`len(df)=300` 推導仍 50 + d* 搜尋實際用 300 bars；或 SPEC §N 明列「短於 calibration_bars 不做截斷 MR 保證」。

**[NON-BLOCKING | Medium]** `len(clean)<20` 時 d* 硬回 1.0 未列入邊界目錄  
- **證據**：`feature_preprocessor.py:3701-3702`。  
- **修法**：Task 2.4 或 §V 邊界目錄補充。

**[NON-BLOCKING | Low]** Task 2.4 已列 `calibration_bars=10 → max_lag=2`（TODO L134）— 與 Task 1.1 邊界一致，無矛盾。

---

### ⑤ 掉項 / 不可證偽 / 矛盾 / 與既有測試

**[MAJOR | Medium]** Task 2.2 parallel 路徑無 mutation，僅 serial 實測 + 論證  
- **證據**：TODO Task 2.2 L112-113；`_slow_path_parallel.py:128` 獨立取 max_lag。  
- **會怎麼失敗**：parallel  regress 時 B-2 不紅。  
- **修法**：增 `test_mutation_fracdiff_maxlag_parallel_*` 或 slow 子集強制 `n_jobs>1`。

**[NON-BLOCKING | Medium]** B-5（batch checkpoint/RunLease）defer 一致 — SPEC/TODO/MANIFEST 排除節與 HANDOFF 殘餘對齊，非掉項。  

**[NON-BLOCKING | Low]** Manifest 未單列 §G ID — 由 TODO Task 0.1 追溯 §G，coverage 14 ID 自洽。  

**[NON-BLOCKING | Low]** A-3 warmup 252 vs 值路徑 50 — SPEC 已決議保留；`warmup_window.py:292-295` 與修後推導不一致但註解任務明確，不構成邏輯矛盾。  

**無問題類別（§1 快掃）**  
- **矛盾（修向）**：三腿檔與 SPEC 主修向一致（max_lag 耦合為根因）。  
- **OOM/並行**：未新增熱路徑，無額外風險。  
- **API 型別**：A-2 `ge=0` 與舊 dict 相容路徑合理。  
- **過度工程**：範圍受控。

---

## §1 必查十類摘要

| 類別 | 結果 |
|---|---|
| 1 矛盾/互斥 | **有** — EPIC_BRIEF 10×3 vs SPEC 2×1；§G byte vs 抽樣 hash |
| 2 漏項/端到端 | **有** — Task 0.1 run contract；B-3 缺 max_lag |
| 3 不可測驗收 | **有** — §G byte 級與工具不匹配 |
| 4 可疑 quant 假設 | **無新增** — 主因 max_lag 耦合已實碼確認 |
| 5 過度工程 | 無 |
| 6 OOM/並行 | 無 |
| 7 Cache 正確性 | **有缺口** — B-3 未探 max_lag∈hash |
| 8 API/相容 | 無 blocking |
| 9 測試品質 | **有** — parallel mutation 缺；B-3 與 P1-FF-5 重疊風險 |
| 10 Agent 可執行性 | Task 0.1 工具/config 模糊 |

## §2 範本錨點 + 獵空殼

- SPEC §RISK/§A/§C/§G/§P/§V/§R/§N：**齊**（§A 含「已驗證」行號，多項與實碼一致）。  
- §G：**非空殼**，但通過條件與 TODO 工具鏈**脫節** → 邏輯空殼風險。  
- TODO 各 Task 驗證/邊界/不可做：**齊**；Task 0.1 / 2.3 / 3.1 需上述修補。

---

## 結構化收尾（機器可掃）

```
ASSUMPTIONS_VERIFIED:
  - max_lag 預設 len(df)//10 @ feature_preprocessor.py:3198-3200
  - _find_min_d 用 _calibration_series + max_width=max_lag @ :3699,3733-3734
  - fracdiff_hash 含 max_lag; payload 驗 row_count/time_range @ _d_star_cache.py:206-227,399-427
  - FractionalDifferencingConfig 無 max_lag @ feature_config.py:183-191
  - MR 窗 FRACDIFF_MIN_BARS=600 @ ff_truncation_mr_helpers.py:42
  - golden baseline 工具為抽樣 hash 非全 byte @ build_l65_golden_baseline.py:275-308
  - P1-FF-5 已有 d* path symbol 隔離測試 @ test_ff_cross_symbol_value_isolation.py:60-62

TESTS_RUN: read-code only (no pytest)

FAILURES_SEEN: none (review-only)

SCOPE_CHANGES: none (review-only; 僅建議修 SPEC/TODO 文案)

NUMERIC_OR_SCHEMA_IMPACT: review 未改 production；文件修補應標記 §G 驗收工具變更
```

---

## 修補優先序（供 reconcile）

1. **P0**：Task 0.1/3.1 綁定 byte 級比對工具 + 寫死 G1/G2 run contract（MR config + 窗長）。  
2. **P0**：B-3 增 `max_lag`/`fracdiff_hash` mutant；指名 fingerprint 層級。  
3. **P1**：統一 EPIC_BRIEF 與 SPEC 簽核符號×TF 範圍。  
4. **P1**：Task 2.2 parallel mutation；Task 1.1 短 df 邊界測試補齊。  
5. **P2**：receipt 記錄 fracdiff_hash；C-1 文案去硬編「60」。

STATUS: DONE
