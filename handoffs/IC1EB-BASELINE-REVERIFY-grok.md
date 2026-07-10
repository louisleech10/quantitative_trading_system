# IC1EB Golden baseline v2 — Grok 複驗（R1 BLOCK 閉合）

**角色**:R1 提出方複驗委員（Grok 4.5）  
**輸入**:`handoffs/IC1EB-BASELINE-REVIEW-grok.md` + `handoffs/IC1EB-BASELINE-RECONCILE.md`(F1–F17) + `scripts/capture_ic1eb_baseline.py` + `handoffs/ic1eb_baseline/`  
**約束**:data_cache 唯讀；未改 `handoffs/ic1eb_baseline/` 任何檔；本檔為唯一寫出。  
**方法**:用 R1 原可證偽反例重打；不採信 reconcile 文字。

---

## 1) R1 自提 findings 閉合表

### F-G1 — xsec `max_features` / `feature_filter` 靜默無效（R1 BLOCKING）

| 欄位 | 內容 |
|---|---|
| **R1 反例** | (A) `analyze_cross_sectional` 體內 `feature_filter\|max_features` 引用數；(B) 截斷是否實際把 xsec 欄數鎖在 N |
| **裁決對應** | RECONCILE F1 ACCEPT → 預物化 inputs，xsec 不靠 request 上的 feature_filter |
| **CLOSED/OPEN** | **CLOSED** |

**複驗 receipt**

```text
# A) production xsec 仍為 no-op（預期不變；截斷改走 premat）
analyze_cross_sectional lines 921-1162
feature_filter hits in xsec body: 0
max_features hits in xsec body: 0

# B) 物化 inputs + xsec 產物
BTCUSDT_12h_e53…_sha500.h5: features shape=(1696, 500), feature_names len=500
meta.baseline_subset = {
  max_features: 500,
  selection: "sorted(names, key=sha256(name))[:N] (F10)",
  source_feature_count: 218369
}
manifest.runs.xsec_3sym_12h_e53e2290.n_summary_rows = 500
xsec summary feature set == BTC premat 500-set: True
select_columns(2000 demo names) -> 500
```

**判定理由**:R1 解 BLOCK 條件 (a)「進 analyze_cross_sectional 前物化 sorted…[:N]」已落地；N=500 可重放，不再宣稱 request `max_features` 對 xsec 生效。production 旁路仍在，但 **capture/B5 重放路徑已繞過**。

---

### F-G2 — `dtypes_sha256` 未 canonical → None/NaN 假紅（R1 MAJOR）

| 欄位 | 內容 |
|---|---|
| **R1 反例** | 同數值表，缺測用 `None`(object) vs `np.nan`(float64)；舊邏輯 dtypes 腿紅、values/nanmask 不紅 |
| **裁決對應** | RECONCILE F8 ACCEPT → five_hash 對 float64/NaN canonical frame 計 dtypes |
| **CLOSED/OPEN** | **CLOSED** |

**複驗 receipt**

```text
# 原反例重打（scripts.capture_ic1eb_baseline.five_hash）
raw dtypes None path: all object
raw dtypes nan  path: all float64
OLD raw dtypes_sha equal? False   # 證實 R1 反例仍可擊中「未 canonical」世界

NEW five_hash:
  dtypes_sha256 equal? True
  values_sha256 equal? True
  nanmask_sha256 equal? True
  all core five equal? True
  dtypes_sha256 == sha_json(["float64"]*10)? True

# 實產物 recompute vs manifest（5 runs 抽樣全 match）
long_BTCUSDT_12h_e53e2290: match=True
xsec_3sym_12h_e53e2290: match=True
event_BTCUSDT_12h_e53e2290: match=True
full_BTCUSDT_12h_e53e2290: match=True
long_BTCUSDT_1h_4a8a0b37: match=True
全 12 runs dtypes_sha256 唯一值: 00daba83c15cda237e05…（canonical 一致）
```

---

### F-G3 — 雙產生器 / 雙產物並存（R1 MAJOR 程序）

| 欄位 | 內容 |
|---|---|
| **R1 反例** | `handoffs/ic1eb_baseline/generate_baseline.py` 與 `scripts/capture_ic1eb_baseline.py` 並存、N/矩陣不同 |
| **裁決對應** | RECONCILE F11 ACCEPT → N=50 隔離至 `ic1eb_baseline_n50_superseded/` |
| **CLOSED/OPEN** | **CLOSED** |

**複驗 receipt**

```text
canonical generator: scripts/capture_ic1eb_baseline.py exists=True
handoffs/ic1eb_baseline/generate_baseline.py exists=False
handoffs/ic1eb_baseline_n50_superseded/generate_baseline.py exists=True
manifest.generator = "scripts/capture_ic1eb_baseline.py"
generator_sha256 live == manifest: True
  (1a63444d4555df8cbfa2882e03341edf6f6bb810fe5383127886adada789361d)
canonical dir: 12 × *.report.json + baseline_manifest.json + inputs/ + expected_raise in manifest
```

---

### F-G4 — HEAD dirty / 工作樹稽核不足（R1 MAJOR）

| 欄位 | 內容 |
|---|---|
| **R1 反例** | 僅 `git rev-parse HEAD`；無 porcelain / tree fingerprint |
| **裁決對應** | RECONCILE F7 ACCEPT → HEAD + porcelain 全文 + script sha + env + atomic publish |
| **CLOSED/OPEN** | **CLOSED**（記錄義務滿足；**未**採「dirty 拒跑」） |

**複驗 receipt**

```text
manifest keys 含: head_sha, git_status_porcelain, generator_sha256, env_versions, generated_at_utc
head_sha: ce667ba58e995a513cdc68936d1dd7d285807461
porcelain at capture: 11 lines（含 ?? scripts/capture_ic1eb_baseline.py 等）→ dirty=true 仍發布
data_cache_fingerprint.unchanged: True
report_sha recompute match (xsec/event): True
```

**殘餘（非 reopen BLOCK）**:freeze 發生在 dirty tree；稽核鏈可還原「碼狀態含未提交 capture 腳本」，但跨 session 若腳本再改而 generator_sha 漂移需靠 sha 對帳，不靠 HEAD  alone。

---

## 2) Reconcile 裁決抽驗（有無走樣）

| # | 抽驗點 | 結果 |
|---|---|---|
| F1 | premat 500 + xsec 複刻前置 | **對齊**（見 §1 F-G1） |
| F3 | passed = summary − stage5 removed；≠ 頂層 `passed_features` | **對齊**；long/event/full `reconstruct_passed` len == `n_passed_features` |
| F6 | data_cache 零 diff + persist patch 入 procedure | **對齊**；`unchanged=True`；procedure 明文 B5 須同 patch |
| F8 | dtypes canonical | **對齊**（見 §1 F-G2） |
| F11 | 雙產生器隔離 | **對齊**（見 §1 F-G3） |
| F12 | full split-off；scope 真相 | **對齊**：`full_BTCUSDT_12h_e53e2290` metadata **無** `scope` 鍵；manifest `metadata_scope=None`；腳本 `expect_scope=None` 對 orchestrator:915 `pop("scope")` |
| F13 | event 真 kline 分位 query | **對齊有料**：`query="volume >= 16782.57763671875"`，`n_events=424`，`tier=sufficient`；見 §3 |
| F14 | labels_path return_5 舊路徑 raise receipt | **對齊**：`InvalidInputError` 訊息與 orchestrator:951-954 字面一致；labels h5 shape `(1696,1)` name `return_5` |
| F15 | 刪頂層 mode；`generated_at_utc` | **對齊**：`mode` absent；`generated_at_utc` present |
| F10 | 完整選欄清單 + family 直方入 manifest | **部分走樣**：選欄可從 `inputs/*.h5` `feature_names` 還原；manifest **無** family 直方 / 全欄名 list（僅 `column_selection` 字串）。**不獨否決 G-1**；G-2 解讀仍須自算 family 分布 |

矩陣計數：`runs`=12 report + `expected_raise_runs.xsec_labels_return5_12h`=1 → 與 RECONCILE「13 顆」一致。

---

## 3) 新產物 / event `scope=None` 與 G-2 可用性

### 3.1 事實（實讀 report，非推測）

| run | `metadata.scope` | split 真相 | event | n_passed | values 五 hash 與 long 同？ |
|---|---|---|---|---|---|
| `long_BTCUSDT_12h_e53e2290` | `"test"` | `ic_train_test_split.applied=true`，test_rows=335 | mode=none | 39 | — |
| `full_BTCUSDT_12h_e53e2290` | **鍵缺席**（manifest=None） | 請求 split off；無 split meta | mode=none | 21 | **否** |
| `event_BTCUSDT_12h_e53e2290` | **鍵缺席**（manifest=None） | **requested true 但 fallback**：`applied=false`，`reason=rolling_warmup_insufficient`，`test_rows=37 < min_test_rows=131`，`scope=full_sample_legacy`，`oos_guarantees=false` | mode=query，tier=**sufficient**，n_events=424 | 45 | **否** |

`scope=None` / 鍵缺席對 event：**不是**「事件模式天生無 split」的簡化標籤，而是舊路徑在 event 後樣本不足 → `_run_full_sample_fallback` → `pop("scope")`（orchestrator:915-917）的**誠實結果**。

### 3.2 對 G-2 的影響（可用性判斷）

| G-2 用途 | event run 是否可用 |
|---|---|
| selection-diff / passed_set / 舊 i.i.d. p 層 vs 同 symbol 主 long | **可用**：passed 45≠39，sig/values hash 均異於 long 與 full |
| 「event × train/test holdout」行為 | **不可用**：實際為 full_sample_legacy fallback，無 OOS 保證 |
| D-E low_confidence α 放寬 | **不可用**：本 run `tier=sufficient`（非 low_confidence）；R1 原條件「D-E 靠 T-2.2c 單元」仍成立 |
| 與 full run 混淆 | 需防：兩者 manifest `metadata_scope` 皆 None，但 event 有 `ic_train_test_split` fallback 物件 + `event_filter.mode=query`；G-2 簽核應以 filter_log/meta 欄位區分，**禁止**只看 scope 欄 |

### 3.3 其他新產物觀察（非 R1 reopen）

- **xsec** `n_passed=500==n_rows`：舊 xsec 無 stage5 閘，pass-set diff 資訊量低；G-2 仍以 p/t 層與五 hash 為主（與 R1/F17 精神一致）。
- **F10 family**：BTC 12h e53 500 欄 max family share ≈28.4%（volume 142/500）；均勻優於純字典序首段，但仍有結構偏，G-2 不得外推全宇宙。

---

## 4) 總判定

R1 四項自提 **BLOCKING/MAJOR**（xsec 截斷語義、dtypes canonical、雙產生器、HEAD/dirty 稽核記錄）以原反例重打後均 **CLOSED**。  
Reconcile 主路徑無推翻性走樣；F10 family/選欄清單入 manifest 為**輕度殘缺**（可自 inputs 還原）。  
event `scope=None` 為舊路徑 fallback **真值**，不使 baseline 失效，但 **限縮** event 腿的 G-2 敘事（非 holdout、非 low_confidence）。

```
ASSUMPTIONS_VERIFIED:
  - xsec body 仍 0×feature_filter；capture 以 premat 500 鎖欄
  - five_hash None/NaN 反例 dtypes 腿已閉；12 runs dtypes_sha 單一
  - n50 已隔離；canonical generator sha 與 live script 一致
  - porcelain/HEAD/script sha/env/data_cache fingerprint 入 manifest
  - event scope 缺席 = split fallback full_sample_legacy，非 holdout
TESTS_RUN:
  - 靜態 rg/analyze_cross_sectional 區段計數
  - python: five_hash None vs NaN；report recompute vs manifest（5 runs）
  - python: h5 500 欄 / xsec rows=500 / set 相等 / reconstruct_passed
  - python: event/full/long metadata+filter_log 對讀；F14 labels+raise 字面
FAILURES_SEEN: five_hash 微實驗誤塞 bool regime_robust → TypeError（嚴格 gate 預期）；改純數值反例後通過
SCOPE_CHANGES: none（只寫本複驗檔）
NUMERIC_OR_SCHEMA_IMPACT: none
```

VERDICT: PASS
