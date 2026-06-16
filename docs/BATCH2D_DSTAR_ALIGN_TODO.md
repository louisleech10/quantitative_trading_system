# #2 d* / FracDiff 非 CGSA 對齊 — TODO V3（基於 SPEC V3｜2026-06-15）

> 追溯：manifest [D2-1]~[D2-10]；SPEC Task 0.1/1.1/2.1/3.1/4.1 共 5 Task。V1→V2 雙家族 adversarial reconcile（d* parity 主 oracle + 雙 extractor 同名 value parity + full-length golden + 移除 CGSA scope + exact-only no-backdoor）。

## §0 全域規則與約束
- **CGSA 主路徑禁改**：只動非 CGSA frame fracdiff 欄選 + tier2a builder；**禁碰 `_group_requires_slow_transform`（:1167-1206，CGSA 排程）**；CGSA frozen full hash 回歸證 byte 不變。
- **儲存格式不對稱**：CGSA L7_raw=raw_v2 parquet（features_df 回空）、非 CGSA=HDF5（features_df 非空、欄名帶 `_{tf}_` tag）。
  - **d* parity（主 oracle）**：`export_d_star_values()`,格式無關,計算時皆裸 key 直接比。
  - **value parity（次）**：CGSA via `FeatureReader.load_columns_v2(...,artifact_kind="raw")`/ 非 CGSA via HDF5(兩路同 tag,同名直比)→ 由 P0 provenance 取 L1/L2 expected set;assert expected 非空+左右 key-set 對 expected exact+row-index exact;float32 **exact**。
- **exact-only 治理**：batch2d 測試**禁新增 rtol/atol>0**；value parity 不 exact → `pytest.fail`+分案 ID+`STATUS: BLOCKED`，本 PR 不設 tolerance/不改 gate。
- 不改 schema（禁 Lx_ 前綴/attrs/逐層 transform/heuristic）；不弱化 NaN/inf gate；map 只控 fracdiff layer gate。
- 測試 cache 隔離：monkeypatch `FeaturePreprocessor._d_star_cache_dir`→tmp（禁寫 repo data_cache）。
- 防假綠：禁動既有 `test_fracdiff_registry_layer_filter_*`（CGSA）斷言；回歸 bundle 78 維持。
- 紀律：真實 kline 只讀；禁覆寫 tests/golden/l65/test_inventory.txt（--co 後查 git status 還原）；禁動根 HANDOFF/templates/docs governance；**你不負責 git commit**（協調者按 Phase 接手）；debug 3 輪未過或 T4 揭露既有差異 → STATUS: BLOCKED 停。

## §B 批次執行策略
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| P0 | 0.1 | 無（第一 commit，golden 先行） | 中 |
| P1 | 1.1 | P0 | 小 |
| P2 | 2.1 | P1 | 中 |
| P3 | 3.1 | P0（與 P1/P2 正交） | 小 |
| P4 | 4.1 | P1-P3 | 中 |

- 每 Phase 記 handoffs/20260615-batch2d-dstar.md（檔案+測試原文+T4 實測差異若有）。
- 總 Gate：新測試全綠 + 回歸 bundle 78 + CGSA 相關不紅 + grep `from api\.` momentum/=0。

## Phase 0 — Golden 凍結 [D2-8][D2-10]
### Task 0.1 — freeze control + cgsa_baseline + provenance + metadata（全長 hash）
- SPEC ref：Task 0.1/§G。
- 輸出：`scripts/freeze_batch2d_baseline.py`、`tests/_golden/batch2d/{control,cgsa_baseline,provenance}.json`、`test_batch2d_dstar_align.py::TestGolden`。
- 實作要點：
  1. control=非 CGSA + **顯式 `fractional_differencing.enabled=False`** run（非 HEAD 預設）的 L7（HDF5 features_df）。
  2. cgsa_baseline=CGSA(=1) via `FeatureReader.load_columns_v2(...,artifact_kind="raw")`。
  3. canonical=**全長 per-col float32 value hash + 全長 NaN-mask hash + row-index hash + ordered-column hash**（禁 aggregate-only）。
  4. provenance=merge 前六 layer column→layer map+`_apply_timeframe_tag` 後名稱映射+**CGSA ColumnGroup.layer 凍結交叉核對同名欄 layer 一致**。
  5. metadata=config dump+config_hash+env(FFACT_L65_WORKERS/tier/ADF engine·precision)+**storage schema version+套件 version(numpy/pandas/statsmodels/pyarrow)**+kline 檔 hash+cache fresh 宣告。
  6. 真實 kline BTCUSDT/12h 2024-06-01~2024-12-01；腳本冪等；測試只讀缺檔 pytest.fail 禁 skip；slow。
- 修改檔案：3 新檔。不可做：測試內禁生成；禁 aggregate-only。
- 邊界：kline 缺→fail；env 記 metadata。
- 驗證：`python scripts/freeze_batch2d_baseline.py` 兩次 exit 0；`pytest -k batch2d_golden -q`（slow）HEAD 綠；rm 後紅。

## Phase 1 — column_layer_map [D2-2]
### Task 1.1 — `_build_column_layer_map`
- SPEC ref：Task 1.1。
- 輸出：
  ```python
  _LAYER_LABELS = ("L1","L2","L3","L4","L5","L6")
  def _build_column_layer_map(layers):
      m = {}
      for label, df in zip(_LAYER_LABELS, layers):
          if df is None or df.empty: continue
          for col in df.columns:
              assert isinstance(col, str), f"non-str column: {col!r}"  # fail-fast,與 _combine_layers dedup key 一致
              m.setdefault(col, label)   # keep-first
      return m
  ```
  frame path `_combine_layers` 前（feature_factory.py:363-378）建 map。
- 修改檔案：feature_factory.py（新 helper + 呼叫）。
- 不可做：禁改 `_combine_layers` dedup；禁欄名前綴；禁混用 str(col)（直接用 col + fail-fast）。
- 邊界：空/None layer 跳過；跨層同名 keep-first；單 layer；非 str column→assert fail。
- 驗證：`pytest -k map_unit -q`——6 DFs（含同名跨層）→ keep-first；每 `_combine_layers` surviving col 有 entry。

## Phase 2 — filter + 接線 [D2-3][D2-4]
### Task 2.1 — preprocessor 消費 map + filter 優先序（不碰 CGSA 排程）
- SPEC ref：Task 2.1。
- 實作要點：
  1. `FeaturePreprocessor.__init__` 加 `column_layer_map: Optional[Mapping[str,str]]=None` → `self._column_layer_map`。
  2. `_filter_fracdiff_target_columns`（:2886-2929）`source_layer is None` 時插：`ALL → (col in self._column_layer_map and map[col] in _fracdiff_apply_to_layers) → regex fallback`；unknown fail-closed non-target+warning。
  3. 全鏈傳遞：`_transform_single`/`_transform_single_legacy`/`_transform_chunked`（:2651）；`_run_layer6_5_preprocessor`(feature_factory.py:2478-2517)**讀 self._column_layer_map 傳 FeaturePreprocessor(column_layer_map=),不改 wrapper 簽名**;factory 每次 generate 重設(frame=map/CGSA=None,防 stale)。
  4. **不動 `_group_requires_slow_transform`**（CGSA 排程，adversarial #4）。post_ic（feature_factory.py:2460-2464）全量 map 子查詢。
- 修改檔案：feature_preprocessor.py（__init__/filter/transform_single/legacy/chunked）、feature_factory.py（L6.5 鏈傳 map）。
- 不可做：禁動 CGSA source_layer 分支/`_group_requires_slow_transform`；禁改其他 transform 選欄。
- 邊界：unknown fail-closed；ALL；regex fallback（synthetic L1_*）；chunked 跨 chunk 一致。
- 驗證：`pytest -k "filter_parity or chunked" -q`——T2（裸名+map == source_layer="L1" 同欄集）；chunked 一致；非 CGSA log 無 `unparsed=N/N`；run 後 tmp d* cache（monkeypatch）新增。

## Phase 3 — tier2a + d* export [D2-6][D2-7]
### Task 3.1 — export_d_star_values + builder + layer_of 斷言
- SPEC ref：Task 3.1。
- 實作要點：
  1. `_d_star_cache.py::export_d_star_values()->Dict[str,float]`（`_entries` 中 d_star 非 None）。
  2. `build_l65_golden.py`(:236-241):monkeypatch `_d_star_cache_dir`→tmp,transform 後 glob tmp 單一 `d_star_*.json`(assert 恰 1)直讀 entries(helper `read_d_star_json(path)`;**不重建 DStarCache**避 9-param hash 比對脆弱;**不設 `_d_star_cache_shared`**(屬 preprocessor lifecycle,與讀盤無關))。
  3. 斷言 `all(layer_of_feature(key) in {"L1","L2"})`——**layer_of_feature 來自 synthetic inventory**（builder 知道哪些 synth 欄是 L1/L2），**非** d* key 直接比 layer label；+ 無 L3-L6 key。
- 修改檔案：_d_star_cache.py（export）、build_l65_golden.py（builder）。
- 不可做：測試/builder 禁讀 private `_entries`；不擴 production API 超出 export；禁把 d* key 當 layer label。
- 邊界：cache 無 entry→明確 fail 非靜默空。
- 驗證：`pytest tests/golden/l65/test_l65_golden.py::test_l65_golden_tier2a_synthetic_baseline_exists -q` 綠+d* 非空+layer_of⊆{L1,L2}。

## Phase 4 — parity 驗收 [D2-8][D2-9][D2-10]
### Task 4.1 — d* parity（主）+ value parity（次 exact）+ control + CGSA 回歸
- SPEC ref：Task 4.1/§G。
- 實作要點（讀 frozen P0，非只重跑 live）：
  1. **T3 d* parity（主）**：非 CGSA `export_d_star_values()` L1/L2 d* == CGSA 同欄 d*(裸 key 直接比),exact。
  2. **T4 value parity（次）**：兩側各由 manifest 列欄;P0 provenance 取 L1/L2 expected set;assert expected 非空+左右 key-set 對 expected exact+row-index exact;float32 exact;不 exact → `pytest.fail`+分案 ID（禁 tolerance）。
  3. control：非 CGSA L3-L6 vs frozen control 全長 exact unchanged；L1/L2 變。
  4. CGSA 回歸：CGSA(=1) full hash vs frozen cgsa_baseline exact。
  5. cache invariant：d* 無 L3-L6 key；二跑 hit；跨 symbol 隔離。
- 修改檔案：test_batch2d_dstar_align.py（slow）。
- 不可做：T4 不 exact 且查明既有差異→`STATUS: BLOCKED` 分案（禁寬 tolerance）；禁改 production 遷就；kline 缺禁 skip；禁設 rtol/atol。
- 邊界：揭露既有 dtype/order/dead-drop 差異→BLOCKED 分案。
- 驗證：`pytest -k "parity or control or cgsa_regress" -q`（slow）——T3 d* exact；T4 value exact（或分案）；control L3-L6 exact；CGSA full hash exact；cache invariant。

## 派工 Prompt
> 前置：repo 根、main、venv。讀 SPEC V2 + 本 TODO。P0 先行→P1→P2→P3（正交）→P4。**不負責 git commit**。真實 kline 只讀。每 Phase 記交接（檔案+測試原文+T4 實測差異）。T4 非 exact→BLOCKED 分案。完成 STATUS: DONE + parity 結果原文。

## 階段 3 自檢
1. 追溯：[D2-1]→§A；[D2-2]→1.1；[D2-3][D2-4]→2.1；[D2-5]→§0；[D2-6][D2-7]→3.1；[D2-8]→0.1/4.1/§G oracle；[D2-9]→§0/4.1 exact-only；[D2-10]→0.1/§G/§B。10/10 ✓
2. 深度：5 Task ≥3 要點+函式級+≥2 邊界+可證偽 ✓
3. 語義：d* parity 格式無關（主）；value parity 同名直比(次)；移除 CGSA 排程 scope；map(P1)→filter(P2)→parity(P4 讀 P0) ✓
4. 全棧：純 momentum（§N）⋅
5. 錨點：§0/§B/5 Task 驗證·邊界·不可做 ✓
