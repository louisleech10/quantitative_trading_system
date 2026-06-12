# Batch1 Follow-up — Adversarial Review（Composer 2.5 獨立版）

> 審查對象：`docs/BATCH1_FOLLOWUP_MANIFEST.md` / `docs/BATCH1_FOLLOWUP_SPEC.md`（V2）/ `docs/BATCH1_FOLLOWUP_TODO.md`（V2）  
> 審查者：Composer 2.5（獨立，未讀 `handoffs/20260612-batch1-followup-adversarial-codex.md`）  
> 焦點：完整審查｜嚴格度：MAXIMUM｜日期：2026-06-12  
> 方法：逐段讀 SPEC/TODO/MANIFEST + §A 每條用 rg/Read/stat/shasum/pytest 獨立覆核

---

## Verdict：需修補後派工

V2 已收斂多數結構性問題（freeze script 先行、ownership 定死、fallback 語義、manifest 不動、78 基線）。但 **N7 改動錨點漏第二條 L7 metadata 組裝路徑**、**§A/TODO 多處行號與真實程式不符**、**T5 grep 範圍漏 `scripts/` 消費者**，足以讓執行端改錯檔或宣稱「全路徑統一」卻漏 legacy L7。修補 SPEC/TODO 錨點與 N7 scope 後可派工；不需整包重作。

---

## Findings

### 挑戰前提（§0，置頂）

| # | 嚴重度 | 信心度 | 證據 | 會怎麼失敗 | 修法 |
|---|--------|--------|------|------------|------|
| P1 | **BLOCKING** | High | SPEC Task 4.1 / TODO Task 4.1 只列 `feature_factory.py:3070-3071`；獨立 `rg '"failed_layers"' momentum/` 另有 `:3325-3326`（`_layer7_validate_and_persist` legacy wide L7）。`generate_features` 非 CGSA 路徑 `:351` 與 `multi_tf_generator.py` legacy `:1364` 皆走此函式。 | 宣稱「metadata 邊界全路徑 `L{n}:{tf}`」但 legacy single-TF / multi-TF legacy 仍輸出裸 `L{n}`；`-k n7` 若只測 CGSA stream 路徑 → 假綠。 | Task 4.1 明列 **兩處** metadata 組裝（`:3070-3071` stream CGSA + `:3325-3326` legacy L7）；驗收要求 legacy 路徑硬編斷言；TODO 刪除誤標的 `:3219`。 |
| P2 | **MAJOR** | High | SPEC §C / TODO §0 / Task 2.1-2.2 反覆引用 `feature_storage.py:938-943` 為 per-shard `nan_mask`；實測 `nan_mask` 在 `:917-918`，`:938-943` 為 `_source_reclaimable`/`registry.get`。 | 執行端照行號 patch → 改錯區塊或找不到掛點；B1-9「重用既有 mask」落空。 | 全文更正為 `:917-918`（或「`_write_group` 內 `nan_mask = np.isnan(array)` 區塊」函式級描述）。 |
| P3 | **MAJOR** | High | TODO Task 4.1：「修改檔案 … `:3070-3071`、`:3219` 對應段」；`:3219` 實為 `_apply_runtime_quality_gate` 呼叫，不含 `failed_layers`。 | Agent 在 quality gate 周邊找 metadata 組裝 → 徒勞或漏改。 | 改為 `:3325-3326`；`:3219` 僅保留於 N6/quality gate 相關 Task。 |
| P4 | **MAJOR** | Medium | SPEC §A / Task 4.2 / §B grep gate：`! grep actual_timeframes momentum/ api/ frontend/src`；獨立 `rg` 顯示 `scripts/profile_multi_tf_baseline.py:414`、`scripts/profile_v6v7_comparison.py:466` 仍 `.get("actual_timeframes")`。 | 改名後 profiling 腳本靜默得到 `[]`，效能/對照報告失真；若未列 scope 執行端可能拒改或漏改。 | 要麼把兩 script 列入 Task 4.2 允許改檔 + grep gate 擴至 `scripts/`；要麼 DECISION 明寫「scripts 非 production，接受空預設」並從 §A「無消費者」改為「momentum/api/frontend 無消費者」。 |
| P5 | **MAJOR** | Medium | SPEC §A assumed：「N6 fallback 在真實 run 誤標 partial」；設計靠 Task 2.2 整合測試「先紅後綠」。`max_nan_ratio` 實測 BTCUSDT/12h=`0.16346…`（`tests/_golden/failopen/max_nan_ratio.json`）。 | mid-hole fixture 若 abnormal 比例低於門檻 → 雙向斷言 (complete **與** partial) 無法同時可證偽；實作後假綠。 | Task 2.2 / `-k n6` 明定 mid-hole 欄 abnormal/total **必須** `> max_nan_ratio("BTCUSDT","12h")`（或測試用 symbol/tf 與 gate 一致）；手算步驟寫進測試註解。 |
| P6 | **MINOR** | Medium | Task 2.3：`tracemalloc` 峰值 +10%、耗時 +15% 相對對照；無 CI tier 固定、無 warmup 次數。 | 邊界機器或負載波動 → 間歇性紅燈，debug 燒輪次。 | 測試內固定 `n_workers`/shard 參數、warmup 一輪取 min、或標記 `@pytest.mark.flaky` 禁止；交接文件記錄實測 HEAD 餘量。 |
| P7 | **MINOR** | Low | Task 3.1「init 期 config  vs validate 前 setter **二選一**」仍未在 SPEC 層決策。 | 實作端選錯時序 → window 仍鎖 252 或雙重注入。 | DECISION 或 Task 3.1 預選 (b) setter（因 `:192` init 無 config 已 fact-verified），另一路徑寫「不可做」。 |
| P8 | Suggestion | Low | `_layer7_validate_and_persist_cgsa`（`:3142-3226`）metadata **無** `failed_layers`/`completeness_meta`（scan 路徑）。 | 若未來 caller 改用 scan CGSA 而非 stream，N7 仍不一致。 | 列為 out-of-scope 並註記「當前主路徑為 stream」；或補齊 completeness 組裝。 |

### §1 十類必查

**1. 矛盾/互斥**  
- P1（N7 scope 與「全路徑統一」矛盾）  
- 其餘：fallback 語義 SPEC/TODO/Manifest 一致（producer 必產鍵 + 消費端缺鍵 warning 沿用 1-coverage）→ 無新增矛盾

**2. 漏項/端到端**  
- P1（legacy L7 `:3325`）  
- P4（`scripts/` 消費者）  
- P5（N6 mid-hole 門檻與 fixture 未綁定）  
- 無：resume/checkpoint（§N 已登記 N/A，與 manifest 不動決策一致）

**3. 不可測驗收**  
- P5  
- P6（perf 相對門檻）  
- §G hash / 缺檔 FAIL / 先 freeze 後改碼 → 可測性良好  
- Task 0.1 / freeze script 尚不存在（預期派工前產物）→ 無

**4. 可疑 quant 假設**  
- N6 修 warmup 誤判、不放宽門檻 → 方向正確；scan `:2733` 已用 warmup-aware `nan_ratio`，stream 補齊合理  
- N3 公式 `min(w,max(20,w//4))` 與 preprocessor `:156-158`、validator 寫死 63 一致 → 無  
- 無 leakage/lookahead 改動

**5. 過度工程**  
- 無（utils 兩檔 + freeze script，比例合理）

**6. OOM/並行**  
- P2 行號錯誤影響 B1-9 落地（見上）  
- 累積器 O(1) 設計與禁全寬陣列原則一致  
- 無 ProcessPool 巢狀新增

**7. Cache 正確性**  
- N4 byte-copy + sha256 防漂移 → 無  
- 無 cross-symbol cache 改動

**8. API/型別/相容**  
- P4（metadata 鍵改名與 scripts 未列）  
- `quality_status` 值域不變（`api/services/feature_factory_service.py:246,626` 映射 `completed_degraded`）→ 無 API breaking  
- manifest `present_timeframes` `:598` 不動 → 無

**9. 測試品質**  
- P1（N7 路徑覆蓋不足）  
- P5（N6 雙向斷言可證偽性）  
- [B1-3] 真實 `write_raw_from_registry_stream` 要求 → 優點  
- 回歸 bundle：**獨立實測 78 collected / 78 passed**（217.79s）→ 與 §A 一致

**10. Agent 可執行性**  
- P2、P3（錯誤行號）  
- P1（漏檔案錨點）  
- Task 2.1 accumulator `update` 伪代码较简，靠 200 case 对拍兜底 → 可接受但建议在 TODO 加「chunk 边界」边界用例一条

### §2 範本錨點 + 獵空殼

| 錨點 | 狀態 |
|------|------|
| §RISK/§A/§C/§G/§P/§V/§R/§N | 齊全 |
| §G 可證偽（value_hash+mask_hash exact、缺檔 FAIL、雙向 N6） | 有實質內容，非空殼 |
| TODO §0/§B/8 Task 驗證·邊界·不可做 | 有實質內容 |
| Manifest [B1-1]~[B1-10] ↔ SPEC/TODO | 10/10 可追溯 |
| 空殼 Task | **無** |

### §3 不可違反原則

- 未發現要求弱化 NaN/inf gate、fake data、跳過檢查的條款  
- 無與 §3 直接衝突的修補建議

---

## §A 獨立覆核表（fact-verified / assumed）

| §A 陳述 | 標記 | 獨立驗證 |
|---------|------|----------|
| N4：`:2790-2810` 讀 `tests/_golden/failopen/max_nan_ratio.json`，失敗 raise | **fact-verified** | `:2792` `parents[2]/tests/...`；`:2807-2810` raise；檔案 296B；sha256=`dadc1da8…0189ee0b` |
| N6：stream validation dict `:1127-1135` **固定缺** `nan_ratio` | **fact-verified** | dict 僅 has_nan/has_inf/coverage/inf_* /warnings，無 nan_ratio 鍵 |
| N6：`:3079` 走 `1.0-coverage` fallback | **fact-verified** | `get("nan_ratio", 1.0 - coverage)` |
| N6：scan `:2632-2768` 有 warmup-aware ratio | **fact-verified** | `:2692` `_abnormal_nan_count`；`:2733` `nan_ratio=abnormal/total`；return `:2767` 含 nan_ratio |
| N6：`_abnormal_nan_count` `:2773-2787` | **fact-verified** | 首尾有效值之間 NaN 語義與 docstring 一致 |
| N7：multi-TF `L{n}:{tf}` `:1464-1473` | **fact-verified** | `_collect_failed_layer_ids` → `f"L{index}:{timeframe}"` |
| N7：manifest 裸 `L{n}` `:571-601` | **fact-verified** | `failed_layers.append(layer_id)`；`present_timeframes` `:598` |
| N7：raw_v2/processed_v2 `:521-539` | **fact-verified** | `V2_FAILOPEN_SCHEMA_VERSIONS`、`COMPLETENESS_FIELD_NAMES` |
| N3：validator `:179-209` window=252/min_periods=63 | **fact-verified** | `:194-195` 寫死 |
| N3：`__init__` 無 config 注入 | **fact-verified** | `:49-56` 僅 correlation_threshold |
| N3：`WinsorConfig.window=252` 無 min_periods | **fact-verified** | `feature_config.py:165-171` |
| N3：preprocessor 公式 252→63 | **fact-verified** | `preprocessing/feature_preprocessor.py:156-158` |
| T5：producer 三處 `:327/619/1376` | **fact-verified** | 皆 `actual_timeframes` 賦值 |
| T5：tests 四處舊鍵 | **fact-verified** | 四檔行號與 §A 一致 |
| T5：production 無消費者 | **fact-verified（限 momentum/api/frontend）** | 三目錄 `rg actual_timeframes` → 0；**scripts/ 有 2 處**（見 P4） |
| 回歸 bundle 78 passed | **fact-verified** | `pytest --co` 78；實跑 78 passed 217.79s |
| §C `nan_mask` 在 `:938-943` | **錯誤陳述** | 實際 `:917-918`；應標 **assumed/錯锚** 非 fact-verified |
| N6「真實 run 誤標 partial」 | **assumed**（code-supported） | 因果鏈成立但未跑全量真實 run；[B1-3] 為設計驗證閘 |
| production 部署無 tests/ | **assumed** | 無部署證據；[B1-1] 方向仍合理 |

---

## 被當成事實的未驗證假設（§0）

1. **「T5 production 無消費者」** — 在 momentum/api/frontend 成立，但 **scripts/ 仍讀 `actual_timeframes`**；若「production」含運維腳本則不成立（P4，MAJOR）。
2. **「metadata 全路徑 `L{n}:{tf}`」** — 僅覆蓋 stream CGSA `:3070`，**未覆蓋 legacy L7 `:3325`**（P1，BLOCKING）。
3. **「`nan_mask` 錨點 `:938-943`」** — 行號與程式不符（P2）；屬錯誤 fact 陳述。
4. **「N6 fallback 在真實 run 誤標」** — SPEC 已誠實標 assumed；依賴整合測試，可接受但需 P5 門檻綁定。

---

## ASSUMPTIONS_VERIFIED（執行端摘要）

- §A 核心程式主張（N4/N6 缺鍵/N3 寫死/T5 三 producer/78 tests）獨立覆核通過。  
- 回歸 bundle 78/78 綠。  
- max_nan_ratio.json sha256 與 §A 一致。

## TESTS_RUN

- `pytest tests/feature_engineering/test_failopen_*.py tests/test_multi_tf_generator.py --co -q` → 78 collected  
- 同上實跑 `-q` → **78 passed in 217.79s**  
- `shasum -a 256 tests/_golden/failopen/max_nan_ratio.json`  
- `rg` / `Read` 覆核 §A 行號與符號

## FAILURES_SEEN

- none（審查階段未改碼）

## SCOPE_CHANGES

- none（審查-only）；建議修補 SPEC/TODO 錨點與 N7 scope，非擴大實作範圍

## NUMERIC_OR_SCHEMA_IMPACT

- 審查無改碼；若按現 SPEC 實作：N6 改 stream nan_ratio 語義、N3 可配置 window（預設 byte 不變）、N7 metadata 字串格式變更；manifest schema 不變（與 SPEC 一致）

---

STATUS: DONE
