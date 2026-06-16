# BATCH2D d* Align — Adversarial R2 確認輪（Composer 2.5 獨立）

> 對照：R1 `handoffs/20260615-d2-adversarial-composer.md`（2 BLOCKING + 5 MAJOR）  
> 作者 V2：`docs/BATCH2D_DSTAR_ALIGN_{SPEC,TODO,MANIFEST}.md`  
> 角色：獨立確認（不附和設計 doc）；**禁改 docs/momentum/**，本輪讀碼驗證 reframe。  
> 日期：2026-06-15

## 總判

V2 以 **d* map parity 主 oracle（格式無關）+ value parity 雙 extractor（exact-only）** 化解 R1 兩項 BLOCKING 的根因（「兩路無同名 L7_raw artifact」）。配套修正：fracdiff-off control 定義、§A 行號、全長 golden、exact-only 後門封死、str(col) 矛盾、tier2b scope、CGSA 排程出 scope、provenance 凍結、cache monkeypatch。**無新引入之實質 BLOCKING**。殘留 2 項 MAJOR 為實作指引精度（非 gate 阻擋）。

---

## R1 Findings 逐條收斂

### BLOCKING #1 — 非 CGSA 無 L7_raw，P0/P4 未給雙路徑抽取 API

| 狀態 | **RESOLVED**（reframe，非「補同名 reader」） |
|------|---------------------------------------------|
| V2 證據 | Manifest [D2-8]、SPEC §G T3/T4、§V、TODO §0/4.1：主 oracle = `export_d_star_values()`（d* 在 cache JSON，與 parquet/HDF5 無關）；次 oracle = CGSA `FeatureReader.load_columns_v2(..., artifact_kind="raw")`（裸名）vs 非 CGSA `features_df`/HDF5 + 名稱正規化。Task 0.1 分別凍結 `cgsa_baseline`（raw_v2）與 `control`（HDF5 fracdiff-off）。 |
| 讀碼驗證 | CGSA：`write_raw_from_registry_stream`（`feature_factory.py:3063-3086`），`features_df` 空（`:3163-3164`）。非 CGSA：`_layer7_validate_and_persist` → HDF5（`:3447-3448`），`features_df` 非空且 `_apply_timeframe_tag`（`:3370-3371`）。reframe 承認不對稱，不再假裝「兩路讀同一 L7_raw 目錄」。 |
| 殘留 | T3 **CGSA 側 live d* 取得**未寫「generate_features 後從 monkeypatched tmp 讀 `d_star_*.json`」一步（見 MAJOR-R2-1）；P0 若已凍結 d* canonical，P4 可讀 frozen 緩解。 |

### BLOCKING #2 — fracdiff-off control 與 HEAD 混淆

| 狀態 | **RESOLVED** |
|------|--------------|
| V2 證據 | SPEC §G 凍結、Task 0.1、Manifest [D2-9]、TODO Task 0.1 均明寫 control = **顯式 `fractional_differencing.enabled=False`**（非 HEAD 預設 no-op regex 狀態）。 |
| 讀碼驗證 | HEAD 非 CGSA fracdiff 已 enabled 但 regex 對裸欄 no-op（`feature_preprocessor.py:2905-2927`）；與 fracdiff-off control 語意不同 — V2 已分離。 |

### MAJOR #1 — §A 行號錨點錯誤

| 狀態 | **RESOLVED** |
|------|--------------|
| V2 證據 | SPEC §A / Manifest [D2-1]：`transform()` `:215`、legacy fracdiff `:2505-2508`、filter `:2886-2929`、factory L6.5 `:2478-2517`；ADF `:3311-3378` 獨立於 fracdiff filter。 |
| 讀碼驗證 | `transform()` 在 `:183-215`；`:2481` 為 `_run_layer6_5_preprocessor` 非 `transform`；與 V2 一致。 |

### MAJOR #2 — P0 golden aggregate 偏弱

| 狀態 | **RESOLVED** |
|------|--------------|
| V2 證據 | SPEC §G canonical、Task 0.1、Manifest [D2-10]、TODO 0.1：**全長** per-col float32 value hash + 全長 NaN-mask hash + row-index hash + ordered-column hash；明禁 aggregate-only。 |
| 殘留 | L3-L6 exact 仍主要綁 P4 control（合理）；P0 已足夠支撐欄級 gate。 |

### MAJOR #3 — D2-9 tolerance 後門

| 狀態 | **RESOLVED** |
|------|--------------|
| V2 證據 | SPEC §C、§G T4、§R；Manifest [D2-9]；TODO §0/4.1：**禁** batch2d 新增 `rtol/atol>0`；不 exact → `pytest.fail` + 分案 ID + BLOCKED，本 PR 不得改 gate。 |
| 讀碼驗證 | V1「實測誤差定 gate」措辭已移除。 |

### MAJOR #4 — TODO `str(col)` vs SPEC 非 str key

| 狀態 | **RESOLVED** |
|------|--------------|
| V2 證據 | TODO Task 1.1：`assert isinstance(col, str)` fail-fast + `m.setdefault(col, label)`；Manifest [D2-2] 明寫不混用 `str(col)`。 |
| 讀碼驗證 | production 欄名實測皆 str；fail-fast 與 `_combine_layers` dedup key 路徑一致。 |

### MAJOR #5 — Manifest D2-8 tier2b 未落 SPEC/TODO

| 狀態 | **RESOLVED** |
|------|--------------|
| V2 證據 | V2 三檔 **無 tier2b/T5**；scope 命名「L1/L2 fracdiff selection + d* parity」（Manifest [D2-10]、SPEC §N）。 |

### MINOR（R1 附帶，一併確認）

| 項目 | 狀態 | V2 處理 |
|------|------|---------|
| chunked map 傳遞 | **RESOLVED** | instance attr `column_layer_map`；chunked 走 `_transform_single`（`:2651`） |
| post_ic map | **ACCEPTED N/A** | fracdiff 已關（`:2462-2464`）；全量 map 子查詢無害 |
| dedup↔map 一致 | **PARTIAL** | Task 1.1 要求 surviving col 有 entry；fail-closed 行為仍靠測試落地 |
| CGSA 禁改 | **RESOLVED** | 移除 `_group_requires_slow_transform`；frozen CGSA full hash 回歸 |
| tier2a | **RESOLVED** | `layer_of_feature` from synthetic inventory（非 d* key ⊆ {L1,L2} 字面） |

---

## Reframe 專項驗證

### 1. d* map parity 主 oracle（格式無關）是否化解 L7 雙路徑 BLOCKING？

**是。** d* 在 L6.5 `DStarCache` 寫入（`feature_preprocessor.py:3212-3231`），早於非 CGSA L7 `_apply_timeframe_tag`（`:3370-3371`）。兩路徑 fracdiff/d* 語意可比，無需強制「非 CGSA 也產 raw_v2 parquet」。value parity 降為次 oracle，僅驗 L1/L2 交集 — 與任務目標一致。

### 2. 雙 extractor + 去 tag 是否正確？

**大方向正確；用詞略粗，但 V2 有更强護欄。**

| 聲稱 | 實碼 | 判定 |
|------|------|------|
| CGSA raw 裸名 | `load_columns_v2(..., artifact_kind="raw")` 讀 registry stream 欄名（`feature_reader.py:115-160`） | ✓ |
| 非 CGSA HDF5/features_df 有 tag | `_apply_timeframe_tag`：`ema_20` → `ema_12h_20`（插入 **第二段** `timeframe`，非包 `_{tf}_` 前後綴）（`feature_factory.py:3603-3613`） | ✓ 有 tag |
| 「去 `_{tf}_` tag」 | 對 `foo_12h_bar` 字面替換 `_12h_`→`_` 多數情況可得 `foo_bar`；**正確逆變換**應為：若 `parts[1] in TimeframeAligner._timeframe_seconds_keys()` 則刪除該段（與 `_apply_timeframe_tag` 互逆） | **MAJOR-R2-2**：文案應寫「`_apply_timeframe_tag` 逆變換」，非僅 `_{tf}_` 子字串 |
| 更穩做法 | P0 凍結 **provenance + tag 後名稱映射**（SPEC Task 0.1 #4、Manifest [D2-8]） | ✓ 可用 lookup 取代 heuristic，降低誤剝 tag 風險 |

**T3 d* parity 的「去 tag」**：d* cache key 為 L6.5 裸欄名（`cache.set(column, ...)`），理論上 **T3 不需 tag 正規化**；V2 寫「去 tag 後 key」屬保守冗餘，不構成 BLOCKING。

### 3. 新引入漏洞掃描

| 檢查 | 結果 |
|------|------|
| 新 BLOCKING（scope/契約/quant gate） | **無** |
| CGSA 排程誤改 | V2 明確移除 `_group_requires_slow_transform` — 化解 Codex B4 |
| data_cache 紅線 | TODO §0 monkeypatch `_d_star_cache_dir`→tmp — 化解 Codex B6 |
| L3-L6 過度宣稱 | §N / [D2-10] 明示 out-of-scope + inventory — 化解 Codex M11 |
| T4 假綠 | 既有 CGSA/frame dtype·dead-drop 差異可能觸發 BLOCKED 分案 — 治理正確，非漏洞 |

---

## 殘留 MAJOR（非 BLOCKING，派工後實作注意）

### MAJOR-R2-1 — T3 CGSA 側 live d* 抽取步驟未顯式

- **現象**：`generate_features(CGSA=1)` 不回傳 preprocessor；`transform_registry_groups` 結束後 `self._d_star_cache = None`（`:1679-1681` 等），但 JSON 已 flush 至 cache dir。
- **建議**（實作指引，非改 SPEC）：parity/freeze 腳本在 monkeypatched tmp 下跑 CGSA → `glob(d_star_*.json)` 或 `export_d_star_values()` 從 reload 的 `DStarCache` 讀取；P0 凍結 d* canonical 後 P4 可對 frozen 比對。
- **是否阻派工**：否 — Task 3.1 新增 export + P0 凍結路徑可閉環。

### MAJOR-R2-2 — tag 正規化文案 vs 實作

- **現象**：V2 多處寫「去 `_{tf}_` tag」；實際為 **第二段插入**（`feature_factory.py:3613`）。
- **建議**：freeze/parity helper 應複用 `TimeframeAligner._timeframe_seconds_keys()` 做互逆，或 **優先**用 P0 `provenance` 映射表。
- **是否阻派工**：否 — provenance 已凍結映射；錯寫子字串風險可被測試暴露。

---

## 與 Codex R1 對照（簡表）

| Codex BLOCKING 主題 | V2 狀態 |
|---------------------|---------|
| B1 雙路徑 extractor | RESOLVED（同 reframe） |
| B2 抽樣 golden | RESOLVED（全長 hash） |
| B3 provenance | RESOLVED（P0 provenance map） |
| B4 `_group_requires_slow_transform` | RESOLVED（出 scope） |
| B5 tier2a keys 型別 | RESOLVED（layer_of_feature） |
| B6 data_cache 驗收 | RESOLVED（monkeypatch tmp） |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: CGSA/non-CGSA artifact 不對稱（factory:3063-3164 vs 3363-3448）；_apply_timeframe_tag 插入第二段非包裝 _{tf}_（:3603-3613）；d* 在 L6.5 裸欄名寫入（preprocessor:3212-3231）；HEAD fracdiff regex no-op（:2905-2927）
TESTS_RUN: none（讀取型 R2；未跑 pytest）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: 無代碼變更；V2 仍宣稱修後 schema 不變、L1/L2 數值變、exact-only
```

STATUS: PASS — 可派工
