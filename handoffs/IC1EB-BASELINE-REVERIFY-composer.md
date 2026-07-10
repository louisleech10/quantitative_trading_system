# IC 1e+1b Golden Baseline v2 — Composer R1 複驗報告

**複驗標的**：`handoffs/ic1eb_baseline/`（v2 原子發布產物）+ `scripts/capture_ic1eb_baseline.py`  
**依據**：本人 R1 `handoffs/IC1EB-BASELINE-REVIEW-composer.md` BLOCKING/MAJOR findings + `handoffs/IC1EB-BASELINE-RECONCILE.md` F1–F17 裁決  
**方法**：逐條以 R1 原可證偽命令/反例重打；不採信 reconcile 文字；`data_cache` 唯讀；未改 `handoffs/ic1eb_baseline/` 任何檔。

---

## 1. R1 BLOCKING findings 複驗

### B1 — xsec 忽略 `feature_filter.max_features`（§1.1）

| 項目 | 結果 |
|---|---|
| **狀態** | **CLOSED** |
| **R1 反例** | `grep _apply_feature_filter` 僅縱向 `:828`；xsec 生產路徑不截斷 → 與 500 欄設計矛盾 |
| **複驗 receipt** | `grep -n _apply_feature_filter momentum/Analysis/ic_filter_orchestrator.py` → 2 行（828 呼叫、2009 定義），xsec `analyze_cross_sectional` 鏈零引用。**生產碼仍未接 filter**（預期不變）。v2 改走 premat：`inputs/BTCUSDT_12h_*_sha500.h5` → `features shape=(1696,500)`；`build_xsec_frame()` → `shape=(5088,501)`（500 feature + label）；`xsec_3sym_12h_e53e2290.report.json` `n_summary_rows=500`，`metadata.total_features_input=500`。 |
| **裁決落地** | F1 ACCEPT：premat inputs + capture 內 xsec 前置複刻；manifest `procedure.xsec` 明文。B5 重放須同構。 |

### B2 — 雙捕獲腳本 / 競爭產物（§1.1 程序）

| 項目 | 結果 |
|---|---|
| **狀態** | **CLOSED** |
| **R1 反例** | `generate_baseline.py`(N=50) 與 `capture_ic1eb_baseline.py`(N=500) 並存；`manifest.json` 與五 hash 語意異構 |
| **複驗 receipt** | `handoffs/ic1eb_baseline/` 頂層：12×`.report.json` + `baseline_manifest.json` + `inputs/`；**無** `generate_baseline.py`、**無** `manifest.json`。N=50 隔離至 `handoffs/ic1eb_baseline_n50_superseded/`（8 檔含舊 `generate_baseline.py`）。`baseline_manifest.json.max_features=500`。 |
| **裁決落地** | F11 ACCEPT。 |

### B3 — run 矩陣未齊（§1.1 暫 CHALLENGE；R1 VERDICT 要求 10 顆）

| 項目 | 結果 |
|---|---|
| **狀態** | **CLOSED** |
| **R1 反例** | 設計 10 顆；舊 manifest 僅 6/10 |
| **複驗 receipt** | `baseline_manifest.json.runs` 長度 **12**（9 縱向 + xsec + full + event）；另 `expected_raise_runs.xsec_labels_return5_12h`（F14 receipt）。鍵集合含 3×sym×(1h/12h×2 cfg) + 擴展 run，無缺 sym/cfg。 |
| **裁決落地** | 超 R1 原 10 顆；符合 reconcile v2 矩陣。 |

---

## 2. R1 MAJOR findings 複驗

### M1 — G-1 未覆蓋 `rolling_ic_series` / `ic_decay` / `grouped_ic`（§1.1）

| 項目 | 結果 |
|---|---|
| **狀態** | **CLOSED** |
| **R1 反例** | 五 hash 僅 summary 10 欄；改 rolling IC 一點 → G-1 靜默綠 |
| **複驗 receipt** | 12 run 皆含 `series_sha256.{rolling_ic_series,ic_decay,grouped_ic}`。重算：`python3` import `scripts.capture_ic1eb_baseline.SERIES_KEYS` + `sha256(json.dumps(...,sort_keys=True))` 對全部 12 run → **0 mismatch**。另全 run `g1_five_hash` 五鍵重算 → **0 mismatch**。 |
| **裁決落地** | F9 ACCEPT。 |

### M2 — `dtypes_sha256` JSON 往返漂移（§3 CHALLENGE 低）

| 項目 | 結果 |
|---|---|
| **狀態** | **CLOSED** |
| **R1 反例** | `json.loads→DataFrame→five_hash` 連跑兩次 dtypes 飄移 |
| **複驗 receipt** | `long_BTCUSDT_1h_4a8a0b37`：`summary_table` JSON roundtrip 前後 `dtypes_sha256` 恆等 `00daba83c15cda23...`（canonical float64 後 hash，F8）。 |
| **裁決落地** | F8 ACCEPT。 |

---

## 3. R1 相關 CHALLENGE（§4/§5，R1 VERDICT 附帶）

| ID | 議題 | 狀態 | 複驗 receipt（摘要） |
|---|---|---|---|
| C1 | xsec 可重放性（§4） | **CLOSED** | premat 500 欄 + xsec report 500 rows；與縱向同 F10 選欄政策 |
| C2 | N=50 殘留（§4） | **CLOSED** | 見 B2 |
| C3 | manifest 完整性（§5） | **CLOSED** | 頂層無 `mode`；有 `generated_at_utc`/`head_sha`/`generator_sha256`/`env_versions`；每 run 含 `g1_five_hash` 五鍵 + `significance_old_iid_sha256` + `passed_set_sha256` + `report_sha256`；12/12 byte sha 重算 match |
| C4 | identity 覆蓋率（§3） | **CLOSED** | F9 序列 hash + report byte sha 兜底 |
| C5 | F5 coerce 吞 corruption | **CLOSED**（reconcile 延伸） | 注入 `ic_mean='not_a_number'` → `five_hash` raise `TypeError`（F5 嚴格 gate） |
| C6 | data_cache 副作用 | **CLOSED**（reconcile F6） | `data_cache_fingerprint.before==after`，`unchanged:true` |

---

## 4. Reconcile 裁決抽驗（ACCEPT 是否偷工）

| # | 裁決 | 抽驗結果 |
|---|---|---|
| F1 | premat 500 欄 | **PASS** — h5 `features (1696,500)`；xsec frame 500 feature cols |
| F3 | passed 由 stage5 重建 | **PASS** — 12 run `reconstruct_passed()` 與 `passed_set_sha256`/`n_passed_features` 全 match |
| F4 | raw 順序 hash | **PASS** — 抽樣 3 run `summary_feature_order_sha256` 重算 match |
| F5 | 嚴格型別 | **PASS** — 見 C5 |
| F6 | data_cache 零寫 | **PASS** — fingerprint 不變 |
| F7 | provenance + atomic | **PASS** — manifest 含 HEAD/porcelain/script sha/套件版本/report byte sha |
| F10 | sha256 選欄 + family 直方 | **PARTIAL** — `column_selection` 與 meta `baseline_subset.selection` 正確；**manifest 未見 family 分布直方**（裁決明文有、落地缺）。不屬 R1 BLOCKING；建議 B5 設計稿補披露，不阻本輪 baseline |
| F12 | full split-off | **PASS** — `full_BTCUSDT_12h_e53e2290` 存在；`metadata.scope=None`（舊路徑 pop scope） |
| F13 | event 真路徑 | **PASS** — `event_query="volume >= 16782.57763671875"`；`filter_log.stage3_event_filter`: `mode=query`, `n_events=424`, `tier=sufficient` |
| F14 | labels_path return_5 | **PASS** — `expected_raise_runs` 錄 `InvalidInputError`；重跑 `analyze_cross_sectional(..., labels_path=inputs/labels_BTCUSDT_12h_return5.h5)` → 同型別同訊息 |

---

## 5. 新產物風險：event run `metadata_scope=None` 與 G-2

### 5.1 觀測（實跑）

```text
long_BTCUSDT_12h_e53e2290: metadata.scope=test
  ic_train_test_split.applied=True, scope=train_test_holdout, test_rows=335
full_BTCUSDT_12h_e53e2290: metadata.scope=None, ic_train_test_split=None
event_BTCUSDT_12h_e53e2290: metadata.scope=None
  ic_train_test_split: requested=True, applied=False
  reason=rolling_warmup_insufficient, scope=full_sample_legacy
  stage3_event_filter.tier=sufficient, n_events=424
```

manifest 記 `metadata_scope=null`（取 `metadata.scope` 頂層鍵）；**真相在 report**：
- **full(F12)**：刻意 `ic_train_test_split=False` → 舊路徑 pop scope，全樣本 IC/p 閘，符合 reconcile。
- **event(F13)**：事件過濾後 warmup 不足 → **split fallback** 至 `full_sample_legacy`（非 `scope=test`）。stage3 事件過濾仍生效（424 events）；tier=sufficient。

### 5.2 G-2 可用性判定

| 維度 | 判定 |
|---|---|
| **單 run 內 G-2**（舊 p vs 新 p、passed_set diff） | **可用** — 各 run 均有 `significance_old_iid_sha256` + `passed_set_sha256` + 完整 `summary_table`/`stage5_threshold_log`；event/full 的 p 與 pass 集合定義在各自實際樣本上，改後路徑應同樣本比對 |
| **跨 run 橫向比較 pass 率** | **需分層解讀** — `scope=test`(9 縱向) vs `full_sample_legacy`(event) vs split-off(full) 母體不同；不可把 event passed=45 與 long passed=39 當同分布標量 |
| **F17（12h passed=0）** | **已緩解** — 6 條 12h 縱向 passed 22–40；G-2 有 pass 集合 diff 素材 |
| **是否阻 B1** | **否** — 屬舊路徑語意揭露；manifest 已標 `metadata_scope`；event report 含 `ic_train_test_split` + `stage3_event_filter` 足夠稽核。建議 B5 G-2 簽核表註明三類 scope 分桶 |

---

## 6. 複驗命令彙總

```bash
source venv/bin/activate
# 主 harness（B1–B3, M1–M2, C1–C6, F3/F4/F9 全 run hash）
python3 <<'PY'  # 見本次 session 實跑腳本
# grep xsec filter
grep -n _apply_feature_filter momentum/Analysis/ic_filter_orchestrator.py
# 目錄歧義
ls handoffs/ic1eb_baseline/ ; ls handoffs/ic1eb_baseline_n50_superseded/
# h5 欄數
python3 -c "import h5py; f=h5py.File('handoffs/ic1eb_baseline/inputs/BTCUSDT_12h_e53e22906c35363757f4cd49d27f973e_sha500.h5'); print(f['BTCUSDT/12h/features'].shape)"
# F14 repro + scope 探針 — 同上 session python 區塊
PY
```

**摘要**：12 report `g1_five_hash`+`series_sha256` 重算 0 mismatch；12 `report_sha256` match；`data_cache` fingerprint unchanged；F14 `InvalidInputError` 可重現。

---

## 7. Finding 總表

| R1 ID | 嚴重度 | 狀態 |
|---|---|---|
| xsec max_features | BLOCKING | **CLOSED** |
| 雙腳本/產物歧義 | BLOCKING | **CLOSED** |
| run 矩陣未齊 | BLOCKING(暫) | **CLOSED** |
| rolling_ic/decay/grouped 未入 G-1 | MAJOR | **CLOSED** |
| dtypes 假陽性 | MAJOR(低) | **CLOSED** |
| xsec 可重放 / N=50 / manifest | CHALLENGE | **CLOSED** |
| event scope=None → G-2 | 新觀測 | **不阻過**（單 run G-2 可用；跨 run 需分桶） |
| F10 family 直方未入 manifest | reconcile 抽驗 | **PARTIAL**（非 R1 finding） |

---

VERDICT: PASS
