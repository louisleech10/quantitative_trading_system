# NUMVIEW — post-IC 正式臂政策、數值核心與精度鏈量測、臂／算法 fingerprint 入不可變 run／view 身分 — SPEC

> 來源：偵察 r1 收斂檔 `handoffs/reconcile/20261020-numview-x-consult-r1/synth.md`（群集 C1–C9、縮尾 method 歸屬裁定、主委補項）；主委獨立版 `handoffs/20261020-numview-x-consult-r1-claude.md`；範圍權威 `docs/TICKET_ORDER.md` 第 42 行（全票排序第 8 步）　|　日期：2026-10-20　|　對應 TODO：`docs/manifests/NUMVIEW.json`
> 版本：v1（2026-10-20；初稿，待審查 r1）。起草 HEAD `75aaccae`（`c9cb493a..75aaccae` 僅 HANDOFF／白話文件提交，`momentum/`、`api/` 無差異，偵察碼證行號沿用有效）。
> 契約單一真相源：`momentum/FeatureEngineering/contracts/numeric_view.json`（Task 0.1 新建）；事前登記判準：`tests/_golden/numview/preregistered_criteria.json`（Task 0.3 新建）。本 SPEC 只 pointer，不列舉其值集。

## §RISK 風險分級
- **大小**：大（`docs/TICKET_ORDER.md:42` 標「中～大」；依 CLAUDE.md 判準命中 (a)(b)(c)(d)，以大任務管線執行。TICKET_ORDER 依其檔頭規則只定順序與範圍，不改其大小欄；大小以本節為準——偵察 r1 群集 C8 之處置）。
- **命中高風險原則**：
  - (a) 數值／資料品質——post-IC 三臂之 zscore 核心差（過期收據 rank+zscore 最大絕對差 0.0975）、落盤 float16／float32 自動選、processed 有損 int16／uint16 codec、多週期層間 float64 與單週期 float32、memmap 門檻依資料量改變合併 dtype；同一請求依環境得不同數值。
  - (b) 跨模組共用路徑——`momentum/FeatureEngineering/{preprocessing/feature_preprocessor.py, preprocessing/_numba_transforms.py, polars_adapter.py, feature_config.py, feature_factory.py, feature_storage.py, run_provenance.py, memmap_utils.py, timeframe/multi_tf_generator.py, ic_first_context.py, memory_budget.py}`、`momentum/factories.py`、`momentum/Analysis/ic_engine.py`、`api/services/ic_analysis_service.py`、`api/models/ic_models.py`、前端 IC 頁型別。
  - (c) 多 phase／難回退——`config_hash` 加鹽使全部既有 run 目錄不再命中（開發期資料可重產，`docs/TICKET_ORDER.md:9`）；若 Phase 3 改正式核心，公開值改變，第 9–12 步之驗收基準依之。
  - (d) ML／IC 正確性——IC 選欄所據之 raw 讀回精度、post-IC 輸出（ML 輸入）之臂與身分、IC 頁 view 可能套用於 IC 之後已重生之 run。
- RISK-HIT: a,b,c,d
- 命中 (a)(d) ⇒ §G 必填、adversarial review 必跑；資料正確性 scope（生成→計算→落盤→讀回）依三方數據正確性簽核鐵律（真實 kline、禁合成 fixture）。

## §A 假設與待使用者確認
- **已驗證事實**（FACT-RECEIPT；起草者於 HEAD `75aaccae` 實跑 2026-10-20）：
  - HEAD 與偵察 HEAD 之產品碼相同。FACT-RECEIPT: `git log --oneline c9cb493a..HEAD; git diff --stat c9cb493a HEAD -- momentum api` → 印出兩筆 `docs(handoff)` 提交，diff stat 輸出為空（起草者 實跑 2026-10-20）
  - IC 頁第三步不傳臂（C1）。FACT-RECEIPT: `sed -n 2896,2899p api/services/ic_analysis_service.py` → 印出 `transformed = preprocessor.transform_selected(kept_cols, {"ic_page": df}, config=transform_config)`，無 `arm=`（起草者 實跑 2026-10-20）
  - IC-first 鎖 Polars。FACT-RECEIPT: `sed -n 2978,2983p momentum/FeatureEngineering/feature_factory.py; grep -n 'POST_IC_ARM = ' momentum/FeatureEngineering/ic_first_context.py` → 印出 `arm=ctx.post_ic_arm,  # Task 3.2：固定 Polars 正式臂，不讀環境` 與 `29:POST_IC_ARM = "polars"`（起草者 實跑 2026-10-20）
  - 未指定臂時依環境選臂，且 Polars 未安裝時靜默改臂。FACT-RECEIPT: `sed -n 871,890p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py; sed -n 82,93p momentum/FeatureEngineering/polars_adapter.py` → 印出 `use_polars = True if getattr(self, "_forced_arm", None) == "polars" else polars_enabled()`、其後 `pandas_chunked`／`pandas_optimized`／`pandas_legacy` 分派；`polars_enabled` 於 `not _check_polars_available()` 時 `return False`（起草者 實跑 2026-10-20）
  - `transform_selected` 之生產呼叫者恰兩處。FACT-RECEIPT: `git ls-files -z momentum api scripts | xargs -0 grep -n "\.transform_selected("` → 印出 `api/services/ic_analysis_service.py:2899` 與 `momentum/FeatureEngineering/feature_factory.py:2978` 兩行；測試側 6 檔（`tests/api/test_icpostleak_api.py`、`tests/feature_engineering/{test_ic_first_pipeline,test_icfirstalign_icfirst,test_icfirstalign_timeaxis,test_preprov_processed,test_ratiounsafe_registry}.py`）（起草者 實跑 2026-10-20）
  - zscore 窗清單為空之臂間語意（C2）。FACT-RECEIPT: `grep -n "else 100\|no_windows" momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 印出 `1443: "zscore_window": int(zscore_windows[0]) if zscore_windows else 100,`（registry 快速臂）、`3547: primary_window = int(windows[0]) if windows else 100`（Polars 臂）、`3350`／`4616` 之 `"applied" if … else "no_windows"`（pandas optimized／legacy）；`sed -n 3215,3218p` 同檔 → 印出空窗 `return selected.to_numpy(dtype=np.float32, copy=True)`（回原值）（起草者 實跑 2026-10-20）
  - 空窗經 API 可達。FACT-RECEIPT: `grep -n "class ApplyTransformsRequest" -A 11 api/models/ic_models.py; sed -n 118,121p api/services/ic_analysis_service.py; sed -n 296,300p momentum/FeatureEngineering/feature_config.py` → 印出 `zscore_windows: List[int] = Field(default_factory=lambda: [100, 252], …)` 無最小長度、`_normalize_zscore_windows` 回 `sorted(...)`（空清單原樣）、`AdaptiveZScoreConfig.windows: List[int]` 無最小長度（起草者 實跑 2026-10-20）
  - 未知縮尾 method 之臂間語意（C3）。FACT-RECEIPT: `grep -n 'winsor_method == "sigma"\|elif causal_preprocessing:' momentum/FeatureEngineering/preprocessing/_numba_transforms.py; grep -n 'Unsupported winsorization method' momentum/FeatureEngineering/preprocessing/feature_preprocessor.py momentum/FeatureEngineering/polars_adapter.py` → 印出 numba `436: if winsor_method == "sigma":`、`453: elif causal_preprocessing:`（非 sigma 一律 quantile）；pandas `3200`、`3728` 與 polars `428`、`460` 皆 `raise ValueError`（起草者 實跑 2026-10-20）
  - 缺 `method` 鍵之預設臂間不一致（主委補，C3）。FACT-RECEIPT: `for n in 1427 3160 3671; do sed -n "${n}p" momentum/FeatureEngineering/preprocessing/feature_preprocessor.py; done; sed -n 3490p 同檔; sed -n 167,169p momentum/FeatureEngineering/feature_config.py` → 印出快速臂 `get("method", "quantile")`、pandas 兩處與 polars 臂 `get("method", "sigma")`、`WinsorConfig.method: str = "quantile"`（型別 `str`，非封閉值集）（起草者 實跑 2026-10-20）
  - pandas 縮尾兩分支回傳 dtype 不同（主委補，C6）。FACT-RECEIPT: `sed -n 3176p; sed -n 3198p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 印出 sigma 分支 `return result_array`（float64）、quantile 分支 `return result_array.astype(np.float32, copy=False)`（起草者 實跑 2026-10-20）
  - post-IC 強制縮尾關。FACT-RECEIPT: `sed -n 989p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 印出 `self._set_config_step_enabled(preprocessing_config, "winsorization", False)`（起草者 實跑 2026-10-20）
  - scipy 不可用時快速臂靜默略過 gaussian。FACT-RECEIPT: `sed -n 2548p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 印出 `if bool(transform_context.get("do_gaussian", False)) and HAS_SCIPY:`（起草者 實跑 2026-10-20）
  - Polars 臂 zscore 於 float32 欄上累積。FACT-RECEIPT: `sed -n 96,120p momentum/FeatureEngineering/polars_adapter.py | grep -n "use_float64\|Float32"; sed -n 594,597p 同檔` → 印出 `pandas_to_polars(df, *, use_float64: bool = False)`、`pl.Float64 if use_float64 else pl.Float32`、`rolling_mean(window_size=window, min_samples=1)`／`rolling_std(…)`；pandas 臂 `_rolling_zscore_2d` 以 `np.float64` 算後轉 float32（`feature_preprocessor.py:3212`）（起草者 實跑 2026-10-20）
  - RunIdentity 鍵不含臂／算法。FACT-RECEIPT: `jq -c '.run_identity_keys' momentum/FeatureEngineering/contracts/run_provenance.json` → 印出 `["symbol","tf","config_hash","feature_schema_hash","feature_naming_version","artifact_kind","content_sha256","provenance_sha256"]`（起草者 實跑 2026-10-20）
  - `config_hash` 組成不含環境選擇子、函式庫版本與算法版本，但已有「算法／政策版本鹽」之前例。FACT-RECEIPT: `sed -n 4140,4158p momentum/FeatureEngineering/feature_factory.py` → 印出 `_kline_last_ts`、`_start_date`、`_end_date`、`_timeframe`、`_mtf_align_version`、`_feature_naming_version`、`_warmup_policy`、`_warmup_table_sha256`、`_probe_l65_gate` 後 `hashlib.md5(...)`；無 `FFACT_`（起草者 實跑 2026-10-20）
  - processed 節點記臂但不入身分。FACT-RECEIPT: `sed -n 2202,2203p momentum/FeatureEngineering/feature_storage.py` → 印出 `if post_ic_arm is not None:` 與 `artifact_manifest["post_ic_arm"] = str(post_ic_arm)`（起草者 實跑 2026-10-20）
  - 落盤 dtype 逐欄整段自動選（不重議）。FACT-RECEIPT: `sed -n 2495,2496p; sed -n 2524,2558p momentum/FeatureEngineering/feature_storage.py` → 印出 `FLOAT16_MAX_REL_ERROR = 1e-3`、`FLOAT16_MAX_ABS_ERROR = 1e-12`；`_select_parquet_storage_array` 先 `_coerce_persistence_array`（float32）再 float16 往返，任一有限值非有限或誤差超界 ⇒ `"float32"`（起草者 實跑 2026-10-20）
  - L7 codec 升級依環境，processed 有損編碼依欄名字面推斷。FACT-RECEIPT: `sed -n 38,49p momentum/core/config.py; sed -n 1905,1913p momentum/FeatureEngineering/feature_storage.py; sed -n 1950,1952p 同檔` → 印出 `os.getenv("FFACT_L7_CODEC_UPGRADE", "0")`；`_infer_l7_processed_encoding` 以 `"zscore" in lowered`／`"gaussian"`／`"rank"` 判定；zscore int16 往返容差 `if max_diff > 0.001:` ⇒ `EncodeFallbackRequired`（起草者 實跑 2026-10-20）
  - 多週期層間保留 float64。FACT-RECEIPT: `sed -n 667,671p momentum/FeatureEngineering/feature_factory.py; grep -n "_execute_layer1_6_preserve_dtype" momentum/FeatureEngineering/timeframe/multi_tf_generator.py` → 印出 docstring `Multi-TF L1-L6：保留層間原始 dtype`；呼叫於 `1474`–`1502`、`1833`–`1880` 共 12 處（起草者 實跑 2026-10-20）
  - memmap 門檻使合併 dtype 依資料量而變。FACT-RECEIPT: `sed -n 42p; sed -n 157,162p momentum/FeatureEngineering/memmap_utils.py` → 印出 `MEMMAP_THRESHOLD_BYTES: int = 500_000_000`、`est_bytes = n_rows * total_cols * 4`、門檻下 `pd.concat(valid_dfs, axis=1, copy=False)`（保原 dtype）；收據 `jq -c '.dtypes' handoffs/run_receipts/20261004-icfirstalign-dtype-branch.json` → 印出 `{"small_branch":["float64","float64"],"large_branch":["float32","float32"]}`（起草者 實跑 2026-10-20）
  - L2 兩值來源與空白名單。FACT-RECEIPT: `sed -n 1968p; sed -n 1981p; sed -n 1803p momentum/FeatureEngineering/feature_factory.py` → 印出 `result = engine.compute_all_polars(layer1, data, indicator_specs)`、`category_frame = engine.compute_category(…)`、`L2_ROUTE_CERTIFIED: frozenset = frozenset()`（起草者 實跑 2026-10-20）
  - L2 收據之適用範圍（C7）。FACT-RECEIPT: `jq -c '.float32_finite_diffs,.max_abs_diff' handoffs/run_receipts/20261004-icfirstalign-l2-arm.json; jq -c '.l2_arms_in_pipeline,.honest_bounds' handoffs/run_receipts/20261004-icfirstalign-freeze-baselines.json` → 印出 `8842`、`1.1725453086253168E-7`；`[{'l1_dtypes': ['float32'], … 'f64diff': 0, 'f32diff': 0}]`、`只 BTCUSDT 12h（P1 加 1h）、精簡或 trend 預設 L1；…結論限於所測設定`（起草者 實跑 2026-10-20）
  - 分支差收據過期且無翻轉量測（C5）。FACT-RECEIPT: `jq -c '.summary' handoffs/run_receipts/20261002-icpostleak-branch-diff.json` → 印出 `{"pairs":42,…,"max_rel_diff_overall":58.82005852248459,"max_rel_diff_at":"registry_parallel_split|rank+zscore","max_abs_diff_overall":0.09747552871704102,…}`；`rows[*]` 鍵只含格級 abs／rel／NaN，無 IC／排序／選欄欄位（起草者 實跑 2026-10-20）
  - 原探針仍在版控（更正主委偵察稿 §2「已不在」）。FACT-RECEIPT: `git ls-files handoffs/run_receipts/icpostleak_probes/` → 印出含 `probe_formal_postic.py`、`probe_icpage_leak.py`、`probe_change_report.py` 共 10 檔（起草者 實跑 2026-10-20）
  - 分支差之輸入集。FACT-RECEIPT: `sed -n 43,55p tests/feature_engineering/test_icpostleak.py` → 印出 `§G 輸入集：真實 BTCUSDT 1h 前 3000 根之 close、volume、3 個真實 L1 特徵欄…另加人工晚生欄`（設定自 `tests/_golden/icpostleak/contract.json`）（起草者 實跑 2026-10-20）
  - 選擇子登記閘範圍不含前處理／儲存／core config（C4）。FACT-RECEIPT: `sed -n 36,43p tests/feature_engineering/test_icfirstalign_memory.py; sed -n 146,158p momentum/FeatureEngineering/memory_budget.py` → 印出 `PRODUCER_MODULES` 六模組（無 `preprocessing/`、`feature_storage.py`、`momentum/core/config.py`）；`SELECTORS` 11 鍵（起草者 實跑 2026-10-20）
  - `momentum/` 內 `FFACT_*` 字面鍵共 50 個，`api/` 另讀寫 26 個（含設給子行程者）。FACT-RECEIPT: `git ls-files -z momentum | xargs -0 grep -noE '"FFACT_[A-Z0-9_]+"' | awk -F: '{print $3}' | sort -u | wc -l` → 印出 `50`；`git ls-files -z api | xargs -0 grep -noE 'FFACT_[A-Z0-9_]+' | awk -F: '{print $3}' | sort -u` → 列出 26 鍵（含 `FFACT_L3_STREAMING`、`FFACT_L3_PERSIST_MODE`、`FFACT_NEW_COMPUTE_PATH`）（起草者 實跑 2026-10-20）
  - IC 頁第三步不經身分載入、輸出不記臂與來源。FACT-RECEIPT: `sed -n 2981p; sed -n 2985p; sed -n 2937,2938p api/services/ic_analysis_service.py` → 印出 `load_canonical_path(features_path)`、`self._feature_library.load(`（非 `load_with_identity`）、輸出 h5 只寫 `attrs["analysis_status"]`、`attrs["oos_guarantees"]`（起草者 實跑 2026-10-20）
  - registry 續跑以 `config_hash` 目錄為鍵。FACT-RECEIPT: `sed -n 1206p; sed -n 1248p momentum/FeatureEngineering/feature_factory.py` → 印出 `resume_allowed = manifest_path.exists() and not force_fresh` 與 `return ColumnGroupRegistry.resume_from_manifest(work_dir)`（起草者 實跑 2026-10-20）
  - 本機真實 kline 範圍。FACT-RECEIPT: `venv/bin/python -I <scratchpad>/kline_inventory.py data_cache/feature_klines/kline_cache.h5` → 印出 10 個 symbol（ADA、BCH、BNB、BTC、DOGE、ETH、LINK、SOL、TRX、XRP）× `12h:1696 1h:20352 4h:5088`（起草者 實跑 2026-10-20）
  - 現行函式庫版本（身分候選）。FACT-RECEIPT: `venv/bin/pip list | grep -iE "^(numpy|pandas|polars|numba|scipy|pyarrow|bottleneck) "` → 印出 `numpy 1.26.4`、`pandas 2.3.2`、`polars 1.36.1`、`numba 0.60.0`、`scipy 1.13.1`、`pyarrow 21.0.0`、`Bottleneck 1.5.0`；`venv/bin/python --version` → `Python 3.9.6`（起草者 實跑 2026-10-20）
- **更正偵察稿與文件**（無型別斷言；處置見 Phase 5）：主委稿 §2「原探針已不在」不實（見上一條收據）；FFDSTAR §N R4 與 HP-NUMVIEW 只寫「快速臂」，Polars 臂亦以 100 照做（C2）；`docs/TICKET_ORDER.md:36` 第 4 步「post-IC 鎖 Polars 正式臂」只對 IC-first 成立，Phase 2 後對 IC 頁亦成立（C8）。
- **歸屬裁定（偵察 r1 收斂檔）**：未知／缺鍵縮尾 method 之臂間不一致屬本票（以契約封閉值集 fail-closed，不改合法設定之輸出）；縮尾責任端與算法選擇屬第 9 步（見 §N）。
- **待確認**：無（動工前無使用者事實待問；量測後之產品取捨走下列白話閘，非動工前置）。
- **量測後白話閘（使用者裁定點，阻塞 Phase 3 對應 Task）**：Task 1.5 決定紀錄中任一決定會改變「現行合法設定之公開輸出值」（IC-first processed、raw 落盤值、IC 頁輸出）者，主委於 Phase 3 動工前以白話逐條報使用者（量測數字、改與不改之代價），使用者確認後才實作；不改值之決定（具名保留、只記身分）不需此閘。2026-09-29 dtype 裁定（`docs/FFSTAT_SPEC.md:221`「維持自動選」）不在任何決定之選項中，Phase 1 對其只量測；量得翻轉者以「新證據報告」形式附於白話閘，不提改案。
- **已確認結果**：2026-09-29 使用者裁定落盤精度「維持自動選（建議）」（`docs/FFSTAT_SPEC.md:221`）；2026-10-02 使用者裁定開發期資料皆可重新產生、非加密市場驗收列 blocked-by 資料、「不挑代表、不接受專項專用」（`docs/TICKET_ORDER.md:9-13`）；2026-09-28 使用者裁定「本機跑得動之完整驗證照跑不延後；跑不動者逐項 blocked-by 硬體列入」RM-FULLSCALE（`scripts/fact_keys.json` RM-FULLSCALE 列）；2026-08-05 使用者定修正只考慮以後、不回溯舊資料。

## §C 約束
- 解耦 7 條：契約讀取、政策驗證、fingerprint 解析一律置 `momentum/`（新模組 `momentum/FeatureEngineering/numeric_view.py`，純函式）；`api/` 只經 `momentum.factories` 或既有公開函式取用，不自組身分、不自判臂；不新增服務互相 import；`momentum/` 不 import `api/`。
- **契約單一真相源**：post-IC 各入口之正式臂、研究臂登記、zscore 窗規則、縮尾 method 封閉值集與缺鍵政策、`FFACT_*` 選擇子分類與解析器、能力旗標、函式庫清單、算法版本常數、fingerprint 各段之鍵、`config_hash` 鹽之組成、RunIdentity 新鍵、IC 頁輸出屬性鍵與 API 回應新鍵，一律定義於 `momentum/FeatureEngineering/contracts/numeric_view.json`；`ic_first_context.POST_IC_ARM`、`WinsorConfig`、`AdaptiveZScoreConfig`、`ApplyTransformsRequest` 之對應約束改讀契約，不得另寫字面。事前登記判準與決定紀錄 schema 定義於 `tests/_golden/numview/preregistered_criteria.json`。新增 RunIdentity 鍵依 PRE-PROV 前例同步 `contracts/run_provenance.json` 之 `run_identity_keys`（`RunIdentity.to_dict` 機械比對）。
- 不可違反原則：Phase 0、2、4 **不改任何現行合法設定之特徵值、NaN 遮罩、欄集合、欄順序、dtype**（§G 逐位元）；Phase 3 只改 Task 1.5 決定紀錄具名之臂／欄族，其餘逐位元不變；不弱化 NaN／inf 閘；不放寬既有測試斷言（測試刪改依 2026-10-17 裁定同提交登記審清單）。
- **2026-09-29 dtype 裁定不重議**：`FLOAT16_MAX_*` 常數與自動選邏輯不改；量測只讀。
- **不寫死市場**：量測格自 `kline_cache.h5` 列舉 symbol×tf（不寫死清單、不假設 24h／UTC、窗以根數定義）；非加密市場 blocked-by PRE-MARKET-DATA（§N）。
- **重型跑紀律**：真實資料生成一律單行程串行、獨占機器（派委員前確認無背景重型跑且磁碟 ≥30 GB）；任何預估 >30 分鐘之跑，先以 Task 1.1 收據列格數×實測單格耗時、找不降驗證之省法、白話報成本再開跑；量完刪中間輸出。
- **嚴禁慢閘**：新增之登記閘、契約閘、身分比對皆秒級（AST／JSON／stat 級）；不在讀取時重算特徵檔雜湊。
- **刻意可見差異（Phase 0、2、4；Phase 3 另依決定紀錄）**：
  - D1 `config_hash` 新增鹽鍵（鍵名見契約）⇒ 全部既有 run 目錄不再命中（不刪、不遷移；開發期資料重產）。
  - D2 manifest 頂層與 artifact 節點新增 fingerprint 物件與 `algorithm_id`（鍵見契約）；RunIdentity 增鍵 ⇒ IC ingest 快取、IC-first JSON 快取一律重建。
  - D3 非法設定改為具名拒收：zscore 啟用而窗清單為空、縮尾 method 不屬封閉值集、dict 入口縮尾啟用而缺 `method` 鍵（API 回 422；Python 入口拋 `NumericPolicyError`）。
  - D4 IC 頁第三步固定契約臂；臂不可用 ⇒ 具名錯誤（不退回 pandas）；輸出檔路徑含 view 身分（不覆寫）、h5 與 API 回應帶來源 run 身分、臂、轉換設定、`algorithm_id`。
  - D5 `transform_selected` 之 `arm` 改為必填關鍵字參數（值須屬契約之 post-IC 臂集合）。
  - D6 續跑閘比對 `algorithm_id`，不等 ⇒ 不續跑（重生）。
- 範圍外：縮尾唯一責任端與算法（第 9 步）；FFSTORE 快照版本與 append 語意（第 14 步，沿用本票 `algorithm_id` 契約）；FF 生成提速（使用者 2026-10-11 延後）。

## §G Golden / Baseline
- **feature/kline 條件**：適用。一律真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。三方數據正確性簽核適用於 Phase 3 任何改值 Task 與 Phase 1 量測收據之解讀。
- **值指紋格式**：同 `tests/feature_engineering/ffstat_helpers.py:447` `public_fingerprints`（逐欄 float32 值 sha256＋NaN 遮罩 sha256＋dtype＋欄名集合 sha256），另加每欄 mean／std／nan_ratio（容差對照用）。
- **沿用之既有基準（不重跑）**：`tests/_golden/preprov/pre_change_fingerprints.json` 之 11 格（含 `ic_first_default` post-IC 生產預設、replace 格、多週期格）——PRE-PROV 已證其值於改後不變，且 `momentum/` 自該凍結後至 HEAD 未改值（§A 第一條）；本票直接作為 IC-first processed 與 L6.5 raw 之改前基準。另沿用 `tests/_golden/{failopen,framepath,ffstat,ffname,icfirstalign,icpostleak,probewinsor,ratiounsafe}` 之值指紋。
- **新凍結（Task 0.4，動工前 HEAD 產品碼態）**，存 `tests/_golden/numview/pre_change_fingerprints.json`：
  - G1 IC 頁第三步輸出（C1）：每個量測格（§V 格 A）之 IC-first 選欄，以 IC 頁預設請求（`ApplyTransformsRequest` 預設值）分別於臂 `polars`（`FFACT_USE_POLARS=1`）、`pandas_optimized`（`=0`）、`pandas_legacy`（`=0`＋`FFACT_L65_OPTIMIZATION_PROFILE=legacy`）各跑 `_apply_transforms_sync` 之同一轉換，存三份值指紋。
  - G2 L6.5 raw 依臂（C6）：格 A 之 raw 於 `FFACT_USE_POLARS` 0／1 各一份。
  - G3 多週期格（格 B）之 raw 與 processed。
  - 凍結腳本 `scripts/numview_freeze_baseline.py`；收據含 HEAD、格清單、每格耗時、函式庫版本。
- **通過條件（可證偽）**：
  - Phase 0、2、4：所有值指紋（沿用＋新凍結）改前＝改後，atol=0、rtol=0；唯一例外＝D3 新拒收之非法設定（無基準）。G1 於改後只存 `polars` 一份有效輸出（D4），須逐位元等於改前 `polars` 份；改前 `pandas_*` 份保留為 Phase 1 量測輸入，不作改後比對對象。
  - 結構凍結（`config_hash` 目錄名、manifest 全文雜湊、run 目錄檔案集合）因 D1／D2 必變：沿用 PRE-PROV 之「剝除新鍵後依原算法重算須等於現行凍結值」證法（`scripts/preprov_refreeze.py` 擴充新鍵清單，鍵名讀契約），相等才以含新鍵之值重凍；不等 ⇒ 停下歸因、不重凍。重凍收據 `tests/_golden/numview/refreeze_receipt.json`。凍結比對以「格」為鍵，不以 `config_hash` 為鍵。
  - Phase 3（只限決定紀錄具名之改動）：被改之臂／欄族對 Task 3.x 獨立 float64 oracle 之 float32 轉型值，逐格 `|out − float32(oracle)| ≤ np.spacing(float32(oracle))`（1 ulp）且 NaN 遮罩 exact；決定紀錄未具名之欄 atol=0、rtol=0；超出即列欄名與實際 diff ⇒ FAIL。

## §P Phase 與依賴
> 執行序：0.1 → 0.2 → 0.3 → 0.4 → 1.1 → 1.2 → 1.3 → 1.4 → 1.6 → 1.5 → 2.1 → 2.2 → 3.1／3.2／3.3（依決定）→ 4.1 → 4.2 → 4.3 → 4.4 → 5.1。自檢：每個 Task 之輸入僅來自編號在前者；Phase 1 全程於 Phase 0 提交後之 HEAD 產品碼（未改）上量；Phase 3 依賴 1.5 決定與白話閘；Phase 4 依賴 Phase 3 以凍結算法版本常數。無 forward dependency。

### Phase 0 — 契約凍結與改前基準（依賴：無；C9 第一段）

**Task 0.1 — 契約 JSON 與讀取模組**
- 目標：把 C1–C4 之政策與身分鍵定為唯一真相源。　檔案：新建 `momentum/FeatureEngineering/contracts/numeric_view.json`、`momentum/FeatureEngineering/numeric_view.py`（`load_contract()`、`post_ic_arm(entry: str) -> str`、`NumericPolicyError`）。　既有 caller／影響面：新建，無 caller（Phase 2、4 接入）。
- 改法：契約段落（鍵名以草稿 `numview_contract_draft.json` 為起點，審查輪定稿）——`post_ic_entries`（每入口：臂、`_sources`）、`post_ic_arm_values`（須 ⊆ `run_provenance.json` 之 `group_arm_values.values`）、`research_arms`（研究臂與不可達理由，承 ICPOSTLEAK §N）、`zscore_windows_policy`、`winsor_method_values`、`winsor_method_missing_key`、`selectors`（每個 `FFACT_*` 鍵：類別、解析器、`_sources`、理由）、`selector_classes`、`capability_flags`、`library_versions`、`algorithm_versions`、`fingerprint_sections`、`config_hash_salt`、`run_identity_new_keys`、`manifest_keys`、`ic_page_output_attrs`、`ic_page_response_keys`。每個 `_sources` 為 `path:line`，該行須含被引用之字面。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_contract.py -q` 全綠：①JSON schema 自洽（必要段齊、值合樣式 `^[a-z][a-z0-9_]*$`）；②`post_ic_arm_values ⊆ group_arm_values.values`（讀兩契約）；③每個 `_sources` 之 `path:line` 存在且該行含引用字面；④`ic_first_context.POST_IC_ARM == post_ic_arm("ic_first")`（Phase 2 起改為讀契約，本 Task 先斷言相等）。mutation：契約 `post_ic_arm_values` 加入 `run_provenance` 無之值 ⇒ ②紅；`_sources` 行號偏移一行 ⇒ ③紅。
- **邊界**：①契約檔缺段 ⇒ `load_contract` 拋 `NumericPolicyError`（不回預設）；②契約值含大寫或空白 ⇒ ①紅。
- **存活至**：本票交付後保留（第 14 步 FFSTORE 沿用）。
- **覆蓋風險**：Task 1.5 決定與 Phase 3 可能更新 `algorithm_versions`、`research_arms`、`selectors` 之類別（以新提交修改，不刪段）；Task 4.1 填入 fingerprint 解析器名。均為同檔增修，非覆蓋產出。
- 不可做：不得在 SPEC、測試或產品碼另寫契約值集之字面清單；不得杜撰無 `_sources` 之值。

**Task 0.2 — 選擇子登記閘（全範圍 AST）**
- 目標：所有影響執行之 `FFACT_*` 鍵封閉登記並分類（C4）。　檔案：新建 `tests/feature_engineering/test_numview_selectors.py`；`numeric_view.json` 之 `selectors` 段。　既有 caller／影響面：既有 `tests/feature_engineering/test_icfirstalign_memory.py` 之 `PRODUCER_MODULES` 測試保留不改（範圍較窄，由本閘涵蓋其超集）。
- 改法：AST 掃描 `git ls-files 'momentum/*.py' 'api/*.py'` 之全部字串常值符合 `^FFACT_[A-Z0-9_]+$` 者（含 `os.getenv`、`os.environ[...]`、`selector(...)`、寫入子行程環境者）；集合須恰等於契約 `selectors` 鍵集（多 ⇒ 未登記紅；少 ⇒ 過期登記紅）。分類三值（值集見契約 `selector_classes`）之判定規則：會選擇演算法、臂、dtype、codec、或改變進入計算之欄集合者 ⇒ `value_affecting`；臂選擇子且有既存真實 kline 逐位元等價測試涵蓋其全部合法值者 ⇒ `certified_equal`（`evidence` 欄須指向該測試節點 id，閘驗該測試存在）；只影響排程、路徑、緩衝、日誌、磁碟預檢者 ⇒ `non_value`（`reason` 欄必填）。另登記非環境之能力旗標（Polars、numba、scipy、statsmodels 可用性）於 `capability_flags`。`memory_budget.SELECTORS ∪ NON_ARM_FFACT_KEYS ⊆ selectors` 且 `SELECTORS` 之鍵不得標 `non_value`（除非附 `certified_equal` 證據）。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_selectors.py -q` 全綠，耗時 < 10 秒。mutation：於 `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` 暫加 `os.getenv("FFACT_NUMVIEW_MUTANT")` ⇒ 紅；自契約刪 `FFACT_L7_CODEC_UPGRADE` ⇒ 紅；將 `FFACT_USE_POLARS` 標 `non_value` ⇒ 紅；`certified_equal` 指向不存在之測試 id ⇒ 紅。
- **邊界**：①鍵名以 f-string 或串接組成（非常值）⇒ AST 另掃 `JoinedStr`／`BinOp` 含 `FFACT_` 前綴者，命中即紅（要求改為常值）；②`api/` 只寫入子行程環境而不讀之鍵（如 `FFACT_L3_PERSIST_MODE`）同樣須登記。
- **存活至**：本票交付後保留（產出端登記閘）。
- **覆蓋風險**：Task 1.6 實測可能把 `non_value` 改判 `value_affecting`（契約增修，閘本身不變）。
- 不可做：不得以檔案白名單縮小掃描範圍；不得把分類判斷寫在測試內（只讀契約）。

**Task 0.3 — 事前登記判準與決定紀錄 schema**
- 目標：Phase 1 開跑前凍結量測輸出欄、翻轉判準、決定規則（C5：接受門檻須在跑前核可）。　檔案：新建 `tests/_golden/numview/preregistered_criteria.json`、`tests/feature_engineering/test_numview_criteria.py`。　既有 caller／影響面：新建。
- 改法：判準檔含——量測格定義規則（自 `kline_cache.h5` 列舉、輸出段根數、前史不足之 blocked 規則）、各比較對（參照 vs 變體）之輸出欄、`material` 判準、決定規則（每個決定點：觸發條件 → 候選處置 → 候選須另滿足之條件）、決定紀錄 schema。數值性門檻只准來自：exact 集合比較、NaN 遮罩 exact、IC 正負號、float32 ulp；不得自訂 atol／rtol（提案見下方「待委員審之設計選擇」②）。判準檔提交後不得修改：Phase 1 每份收據記 `criteria_sha256`。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_criteria.py -q` 全綠：①判準檔合其內嵌 schema；②`git log --format=%H -- tests/_golden/numview/preregistered_criteria.json` 只有一筆（凍結後未改）；③每份 `handoffs/run_receipts/*-numview-*.json` 之 `criteria_sha256` 等於現檔 sha256，且其提交晚於判準檔提交（`git log` 先後）。mutation：改判準檔一字 ⇒ ②③紅；收據改寫 `criteria_sha256` ⇒ ③紅。
- **邊界**：①判準須改（審查 finding）⇒ 只准於 Phase 1 任何收據產出前改，且以新檔名 `preregistered_criteria_v2.json` 取代並刪舊檔（②改讀現行檔名）；②收據產出後發現判準缺陷 ⇒ 不改判準，於 Task 1.5 決定紀錄具名列為量測限制。
- **存活至**：本票交付後保留（審計證據）。
- **覆蓋風險**：無。
- 不可做：不得於看到任何 HEAD 量測數字後設定或調整門檻。

**Task 0.4 — 改前基準凍結**
- 目標：於任何產品碼改動前凍結 §G G1–G3。　檔案：新建 `scripts/numview_freeze_baseline.py`、`tests/_golden/numview/pre_change_fingerprints.json`、收據 `handoffs/run_receipts/<date>-numview-freeze-baseline.json`。　既有 caller／影響面：無。
- 改法：格 A／格 B 依判準檔之格定義逐格單行程串行生成（生成與 Phase 1 共用：生成之 run 目錄保留至 Phase 1 結束，供 Task 1.2–1.4 讀取，避免重生）；凍結值指紋；收據含每格實測耗時與峰值記憶體。開跑前依 Task 1.1 之估時規則先跑單格實測並白話報總估時。
- **驗證**：腳本 rc=0；`venv/bin/python -m pytest tests/feature_engineering/test_numview_baseline.py -q` 全綠：凍結檔之每格具 G1 三臂、G2 兩臂指紋；格清單等於判準檔列舉規則於 `kline_cache.h5` 之結果（不得缺格；blocked 格附根數與理由）。mutation：凍結檔刪一格 ⇒ 紅。
- **邊界**：①某格前史不足 ⇒ 依判準檔標 blocked、記根數，不降門檻；②生成被記憶體守護具名終止 ⇒ 該格標 blocked-by 硬體並列入 §N RM-FULLSCALE，不得以縮小設定冒充同格。
- **存活至**：本票交付後保留；Phase 1 中間 run 目錄於 Task 1.5 後刪除（量完刪輸出）。
- **覆蓋風險**：Task 4.2 之重凍只改結構項（§G），值指紋不動。
- 不可做：不得於改過產品碼之工作樹凍結；不得以合成資料補格。

### Phase 1 — HEAD 量測與政策決定點（依賴：Phase 0；C5、C6、C7；產品碼不改）

**Task 1.1 — 量測格清單與估時收據**
- 目標：列出全部量測格與實測估時，>30 分鐘之總量先報使用者。　檔案：新建 `handoffs/run_receipts/numview_probes/estimate.py`；收據 `handoffs/run_receipts/<date>-numview-estimate.json`。　既有 caller／影響面：無。
- 改法：自 `kline_cache.h5` 列舉 symbol×tf；格 A＝每個 symbol×tf 之單週期短窗（生產預設 `mode=replace`，平穩化開＋縮尾開；append 模式由沿用之 PRE-PROV 基準格涵蓋）；格 B＝每個 symbol 之「最細週期主＋其餘週期訓練」多週期格；格 C＝生產預設全特徵設定（`FactoryConfig()` 預設）於每個 symbol×tf。各類先跑一格實測耗時與峰值記憶體，外推總量；格 C 依實測判定本機可跑者照跑、記憶體守護判定不可跑者列 blocked-by 硬體（§N）。收據列：格數、單格實測秒數、外推總秒數、可省而不降驗證之作法（共用生成、單次生成多檢查點、沿用 PRE-PROV 全特徵 run〔產品碼未變〕）。
- **驗證**：收據 rc=0、含上述欄；主委白話報告（總估時、各段成本）之時間戳早於任何格 B／格 C 生成開跑時間（收據 `reported_at` 與生成收據 `started_at` 比對，`test_numview_criteria.py` 斷言之）。
- **邊界**：①格 C 單格實測即逾機器上限 ⇒ 該 symbol×tf 之格 C 全列 blocked-by 硬體，不再逐格試；②磁碟 < 30 GB ⇒ 估時腳本 rc=1 並列所需空間。
- **存活至**：本票交付後保留為收據。
- **覆蓋風險**：無。
- 不可做：不得因耗時而刪減格類或 symbol（「不挑代表」）；只准以共用生成與檢查點合併省時。

**Task 1.2 — post-IC 分支差 HEAD 重量與翻轉（C5）**
- 目標：取代過期收據，量各臂對 float64 參照之格級差與 IC 層翻轉。　檔案：新建 `handoffs/run_receipts/numview_probes/postic_branchdiff.py`（以 `tests/_golden/icpostleak/contract.json` 之分支與七組合為母集，另加探針專用候選臂 `polars_float64`〔`pandas_to_polars(use_float64=True)` 之 zscore，探針內 monkeypatch，不改產品碼〕）；收據 `handoffs/run_receipts/<date>-numview-postic-branchdiff.json`。　既有 caller／影響面：無。
- 改法：輸入兩類——(i) ICPOSTLEAK §G 輸入集之建法套用於每個 symbol×tf（BTCUSDT 1h 格與 10-02 收據並陳 diff-of-diff）；(ii) 格 A／格 B 之 IC-first 實際選欄之 raw 欄（真實特徵）。參照＝測試端獨立 numpy float64 實作（沿 ICPOSTLEAK §G oracle 定義：rank→gaussian→zscore、窗未滿 NaN），另列 legacy 臂。輸出欄依判準檔：格級 max_abs／p99_abs／max_rel（近零格另列）／NaN 遮罩差；IC 層：各臂輸出對生產標籤之逐欄 IC、IC 正負號翻轉數、逐欄 IC 排序之 Kendall τ-b、`material` 判定。
- **驗證**：收據 rc=0；`criteria_sha256` 相符；每格每臂每組合一列（列數＝格數×分支數×7，測試斷言）；BTCUSDT 1h 輸入 (i) 之 legacy 對 optimized 七組合皆 0 差（重現 10-02 收據之已知零差列；不符 ⇒ 探針或輸入錯，停下歸因）。
- **邊界**：①近零參照值（|ref| < float32 tiny）⇒ 相對差不計、另列絕對差；②選欄全為 ratio-unsafe 之格 ⇒ 記零欄、不算 material。
- **存活至**：本票交付後保留為收據（ICPOSTLEAK §N 研究②之答案）。
- **覆蓋風險**：無。
- 不可做：不得以任一臂之輸出重建另一臂；不得於產品碼加探針鉤子。

**Task 1.3 — 精度鏈逐段量測（C6）**
- 目標：量來源→計算→float32→落盤 dtype→codec→讀回各段誤差與對 IC 選欄之翻轉；不重議 2026-09-29 裁定。　檔案：新建 `handoffs/run_receipts/numview_probes/precision_chain.py`；收據 `handoffs/run_receipts/<date>-numview-precision-chain.json`。　既有 caller／影響面：無。
- 改法：於格 A／B／C 之生成（共用 Task 0.4 之 run；需變體者另跑）以探針 monkeypatch 擷取檢查點並即時算逐欄統計（不存整表）：S0 float64 鏈（變體：單週期改 `preserve_dtype=True`）；S1 層出口 float32（生產）；S2 L6.5 輸出；S3 落盤 dtype 選擇結果與讀回值（含 float16 欄數）；S4 codec：raw BYTE_STREAM_SPLIT 開／關讀回逐位元相等檢查、processed 有損 int16／uint16 開／關讀回誤差，及「欄名含 rank／zscore／gaussian 字面而非該轉換產物」之欄數（名稱推斷誤判）；S5 以每個檢查點之值跑生產 IC 選欄（同標籤、同切分、同門檻），比較倖存者集合。另四個分岔格：多週期 float64 層間 vs 同欄單週期 float32；memmap 門檻強制兩支（探針將門檻設 0 與極大）；pandas sigma 縮尾回 float64 vs 轉 float32 後續 fracdiff／ADF 之值與決策差；同一起點尾端延伸 N 根後各欄 dtype 只升不降與歷史列讀回值變化（C6）。IC 引擎讀入 float16 之 upcast 路徑以實跑記錄 dtype（偵察「我沒查」項）。
- **驗證**：收據 rc=0、`criteria_sha256` 相符；每段每格逐欄統計列存在（測試斷言段×格完整）；S4 raw BSS 讀回逐位元相等（無損宣稱之可證偽檢查：不等即收據標 `lossless_violation` 並使 Task 1.5 觸發決定）；延伸格「降級欄數」欄存在（預期 0；非 0 即為新證據）。
- **邊界**：①全 NaN 欄 ⇒ float16 判定恆 float16，統計標 `all_nan` 不計誤差；②codec 回退 zstd 之欄 ⇒ 計數並列原因；③格 C blocked ⇒ 該格各段標 blocked，不以格 A 外推冒充。
- **存活至**：本票交付後保留為收據（亦供第 14 步 FFSTORE append 語意）。
- **覆蓋風險**：無。
- 不可做：不得改 `FLOAT16_MAX_*`、自動選邏輯或 codec 預設；不得把 float16 改 float32 列為決定選項。

**Task 1.4 — L2 兩臂矩陣（C7）**
- 目標：把「兩臂差為 0」之證據擴至全部單週期與多週期格。　檔案：沿用 `handoffs/run_receipts/icfirstalign_probes/l2_arm_pipeline_probe.py`（必要時參數化 symbol／tf／多週期，複本改名 `numview_probes/l2_arm_matrix.py`）；收據 `handoffs/run_receipts/<date>-numview-l2-arm-matrix.json`。　既有 caller／影響面：無。
- 改法：每格記 L1 輸入 dtype、兩臂（L5／L6 所吃之 `compute_all_polars` 表 vs 公開落盤之 `compute_category`）之欄集合、NaN 遮罩、float32 有限值差格數、max_abs、max_rel，及 `FFACT_USE_POLARS=0` 時 pandas 臂之同表。
- **驗證**：收據 rc=0；格數＝格 A＋格 B 全部（測試斷言）；BTCUSDT 12h 格重現 freeze-baselines 收據之 f32diff=0（不符 ⇒ 停下歸因）。
- **邊界**：①多週期格之 L1 為 float64（預期觸發 l2-arm 收據之非零情境）；②某類別 `compute_category` 拋錯 ⇒ 記錯誤，不以缺欄計 0 差。
- **存活至**：本票交付後保留為收據。
- **覆蓋風險**：無。
- 不可做：不得因單週期 0 差而略過多週期格。

**Task 1.6 — 選擇子值影響實測**
- 目標：以實測核 Task 0.2 之 `non_value`／`certified_equal` 分類（只靠讀碼之分類屬量化正確性風險）。　檔案：新建 `handoffs/run_receipts/numview_probes/selector_effect.py`；收據 `handoffs/run_receipts/<date>-numview-selector-effect.json`。　既有 caller／影響面：無。
- 改法：對契約中讀取點位於計算模組（`preprocessing/`、`operators/`、`timeframe/`、`feature_storage.py`、`memmap_utils.py`、`feature_factory.py`）且標 `non_value` 或 `certified_equal` 之每個鍵，於格 A 之 BTCUSDT 1h 與一個多週期格以其每個合法值（形狀參數取預設與極端兩值）各生成一次，比較 raw 值指紋。估時列入 Task 1.1。
- **驗證**：收據 rc=0；逐鍵逐值一列；任一鍵之值指紋不等 ⇒ 收據標 `misclassified` 並於 Task 1.5 將該鍵改判 `value_affecting`（契約修改由 Task 0.2 閘驗）。
- **邊界**：①只影響平行度之鍵在 1 worker 與多 worker 間比；②鍵之合法值為開放整數 ⇒ 取預設與契約登記之兩個極端值。
- **存活至**：本票交付後保留為收據。
- **覆蓋風險**：無。
- 不可做：不得只挑「看起來可疑」之鍵；範圍以上述模組規則機械決定。

**Task 1.5 — 政策決定點（委員＋白話閘）**
- 目標：依事前登記之決定規則，對每個決定點產出決定紀錄。　檔案：新建 `tests/_golden/numview/decisions.json`（schema 見判準檔）；收斂檔 `handoffs/reconcile/<session>/synth.md`。　既有 caller／影響面：Phase 3 各 Task 讀之。
- 改法：決定點至少——D-POSTIC（post-IC zscore 核心：保留 Polars float32 累積／改 float64 累積）、D-MTF（多週期層出口 dtype 與單週期一致與否）、D-MEMMAP（合併 dtype 與資料量脫鉤與否）、D-WINSOR-DTYPE（pandas sigma 縮尾回傳 dtype）、D-CODEC（processed 有損 codec：保留並改以轉換紀錄判定／保留現狀並入身分／移除）、D-L2（具名保留／統一值來源）、D-SELECTOR（Task 1.6 改判清單）、D-RESEARCH（registry 快速臂 zscore 研究臂之處置）。每點：觸發與否（依判準檔，引收據列）、選定處置、是否改變現行合法設定之公開輸出、受影響之 run 類與欄族、記憶體與耗時代價（實測）。主委起草、三家審查輪；改輸出者依 §A 白話閘報使用者並記錄使用者原話與日期。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_criteria.py -q` 含決定紀錄案例全綠：①每個決定點恰一筆且合 schema；②每筆之觸發判定可由所引收據列依判準檔機械重算（測試內重算，不讀決定紀錄之結論欄）；③`changes_public_output=true` 之筆具 `user_ruling` 欄（日期＋原話）。mutation：把某觸發判定改為與收據不符 ⇒ ②紅；刪 `user_ruling` ⇒ ③紅。
- **邊界**：①收據顯示判準未預見之情況 ⇒ 記為量測限制，不事後加判準；②委員分歧 ⇒ 依碼證與收據，不決採較嚴版並具名殘留。
- **存活至**：本票交付後保留（Phase 3 施工依據、審計證據）。
- **覆蓋風險**：無。
- 不可做：不得把 2026-09-29 dtype 裁定列為決定點；不得在無收據列支持下選定處置。

### Phase 2 — 邊界 fail-closed 與 IC 頁鎖臂（依賴：Phase 0、Phase 1 量測完成；C1、C2、C3）

**Task 2.1 — 數值政策驗證（空窗、縮尾 method、缺鍵）**
- 目標：所有入口於臂分派前對非法設定具名拒收，消除臂間分歧（C2、C3）。　檔案：`momentum/FeatureEngineering/numeric_view.py`（`validate_preprocessing_policy(config: Mapping) -> None`）；`momentum/FeatureEngineering/feature_config.py` 之 `WinsorConfig`（method 驗證器讀契約值集）、`AdaptiveZScoreConfig`（`enabled` 時窗清單非空且皆正整數）；`api/models/ic_models.py` 之 `ApplyTransformsRequest`（`zscore=true` 時 `zscore_windows` 非空）；`preprocessing/feature_preprocessor.py` 之 `FeaturePreprocessor.__init__`（呼叫驗證）、`:1443`、`:3547` 之 `else 100` 改為不可達之具名拋錯、`:3350`／`:4616`／`:3215` 之空窗分支同改；`preprocessing/_numba_transforms.py:436-462` 快速核心 `elif causal_preprocessing` 改為明列 quantile 分支＋未知值拋錯；`polars_adapter.py` 既有拋錯保留。　既有 caller／影響面：全部建構 `FeaturePreprocessor` 之處（生產：`feature_factory.py` 各 L6.5／post-IC 建構點、`momentum/factories.py:create_feature_preprocessor`；測試側以 grep 窮舉，缺 `method` 鍵而縮尾啟用之測試 dict 同提交補鍵並登記審清單）。
- 改法：驗證規則全讀契約；缺 `method` 鍵之處置依契約 `winsor_method_missing_key`（草案：縮尾啟用而缺鍵 ⇒ 拒收；pydantic 路徑由 `WinsorConfig` 預設填值，故生產值不變——見「待委員審之設計選擇」③）。先以 AST＋實跑盤點生產 dict 來源皆帶 `method` 鍵（收據 `handoffs/run_receipts/<date>-numview-winsor-key-inventory.json`），盤點不成立 ⇒ 停下回 Task 1.5 增決定點。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_policy.py tests/api/test_numview_ic_page.py -q` 全綠：①空窗：API 422、`FactoryConfig`／`PreprocessingConfig` 驗證錯、直接 dict 建構 `FeaturePreprocessor` 拋 `NumericPolicyError`——三入口×臂（polars、pandas_optimized、pandas_legacy、registry 快速臂）皆於臂分派前拒收；②未知 method：同三入口×四臂拒收，含快速核心直接呼叫 `transform_array_fast(winsor_method="bogus")` 拋錯；③缺鍵：dict 入口拒收；④合法設定（真實 kline 格 A 之 BTCUSDT 1h）四臂輸出對 §G 逐位元相等。mutation：恢復 `:3547` 之 `else 100` 並繞過驗證 ⇒ ①之 Polars 案紅；恢復 `elif causal_preprocessing` ⇒ ②之快速核心案紅；驗證器只掛 pydantic 不掛 `__init__` ⇒ ①③ dict 案紅。
- **邊界**：①`enabled=false` 且窗清單為空 ⇒ 合法、不拒；②窗含 0 或負數 ⇒ 拒收；③method 大小寫變體（`Sigma`）⇒ 拒收（值集區分大小寫）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：Task 3.x 若改縮尾回傳 dtype，只改同檔另一函式，不動本驗證。
- 不可做：不得於任何臂內保留靜默預設窗或預設 method；不得改合法設定之數值。

**Task 2.2 — IC 頁第三步鎖契約臂並記臂**
- 目標：IC 頁與 IC-first 同一正式臂、輸出可辨識臂（C1）。　檔案：`preprocessing/feature_preprocessor.py` 之 `transform_selected`（`arm` 改為必填關鍵字、值須屬契約 `post_ic_arm_values`）；`ic_first_context.py`（`POST_IC_ARM` 改讀契約）；`api/services/ic_analysis_service.py:_apply_transforms_sync`（傳 `arm=post_ic_arm("ic_page_apply_transforms")`，回應與 h5 屬性加臂）；`api/models/ic_models.py:ApplyTransformsResponse`；`frontend/src/hooks/useICAnalysis.ts` 回應型別。　既有 caller／影響面：兩處生產呼叫者；6 個測試檔呼叫 `transform_selected`（同提交補 `arm=`，登記審清單）。
- 改法：同上；臂不可用 ⇒ 既有 `PostICArmUnavailableError` 上拋，API 轉具名錯誤回應；不退回 pandas。
- **驗證**：`venv/bin/python -m pytest tests/api/test_numview_ic_page.py tests/api/test_icpostleak_api.py -q` 全綠：①同一真實輸入於 `FFACT_USE_POLARS=0` 與 `=1` 之 IC 頁輸出逐位元相等且皆等於 §G G1 改前 `polars` 份；②輸出 h5 屬性與回應之臂＝契約值；③模擬 Polars 不可用 ⇒ 具名錯誤、無輸出檔；④AST：生產碼中每個 `.transform_selected(` 呼叫帶 `arm=` 關鍵字。mutation：刪 IC 頁 `arm=` ⇒ 因必填參數 TypeError，①紅；`transform_selected` 改回 `arm: Optional[str] = None` ⇒ ④與必填斷言紅。
- **邊界**：①選欄全為 ratio-unsafe ⇒ 既有錯誤行為不變；②IC-first 選欄為空 ⇒ 既有空 processed 行為不變（臂仍記）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：Task 4.3 擴充同一函式之載入與輸出身分（增修，不覆蓋臂行為）。
- 不可做：不得以環境變數覆寫正式臂；不得新增平行之轉換器。

### Phase 3 — 正式核心處置（依賴：Task 1.5 決定紀錄、改輸出者之使用者白話閘確認；C5–C7 之實修，條件式）
> 每個 Task 之施工內容由決定紀錄選定；決定為「保留」者，本 Task 只交付具名保留之釘住測試與契約 `research_arms`／`algorithm_versions` 登記，不改產品碼。各決定獨立提交、可單獨 revert。

**Task 3.1 — post-IC zscore 核心（D-POSTIC）**
- 目標：正式臂之 zscore 與 float64 參照之差異依決定處置。　檔案：`polars_adapter.py:polars_l65_adaptive_zscore` 或 `feature_preprocessor.py:_transform_single_polars` 之 zscore 輸入轉換；`numeric_view.json` `algorithm_versions` 對應項 +1。　既有 caller／影響面：IC-first processed、IC 頁輸出（兩者同臂）。
- 改法：決定＝改 float64 累積 ⇒ zscore 步之輸入以 Float64 計算、輸出轉 float32（其餘步不變）；決定＝保留 ⇒ 不改碼。
- **驗證**（依 decisions.json `d_postic` 取一，tests/feature_engineering/test_numview_core.py）：
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k postic_float64 WHEN d_postic=float64_accumulate THEN rc=0
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k postic_retained WHEN d_postic=retain THEN rc=0
  - 前者內容：兩路 oracle——(i) 測試端獨立 numpy float64 實作、(ii) legacy pandas 臂——於格 A 全部 symbol×tf 之真實選欄，正式臂輸出對兩者皆 ≤1 ulp、NaN 遮罩 exact；§G 其餘值指紋 atol=0；記憶體峰值與耗時對改前之比值記入收據並不得超過決定紀錄所核可之值。mutation：zscore 輸入改回 Float32 ⇒ (i) 紅；rank 步誤改 Float64 ⇒ 未具名欄之 §G 比對紅。後者內容：釘住現行 Polars 臂對 (i) 之差異上界等於 Task 1.2 收據之 max_abs（逐格），任何核心改動即紅。
- **邊界**：①窗內常數（std=0）⇒ 輸出 0、與 legacy 同；②窗未滿 ⇒ NaN（ICPOSTLEAK 既有語意不變）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得同時改 rank／gaussian 核心；不得改窗未滿遮罩語意。

**Task 3.2 — 精度鏈分岔（D-MTF、D-MEMMAP、D-WINSOR-DTYPE、D-CODEC）**
- 目標：依決定處置精度鏈之環境／資料量相依分岔。　檔案：依決定——`feature_factory.py:_execute_layer1_6_preserve_dtype` 與 `multi_tf_generator.py` 呼叫點（D-MTF）；`memmap_utils.py:concat_with_memmap`（D-MEMMAP）；`feature_preprocessor.py:_winsorize_2d_legacy_equivalent`（D-WINSOR-DTYPE）；`feature_storage.py:_infer_l7_processed_encoding` 與 processed 編碼入口（D-CODEC）。　既有 caller／影響面：多週期生成、L3／L4 合併、pre-IC 慢臂、processed 落盤。
- 改法：每個決定點一個子提交；改者附決定紀錄引用與版本常數 +1；保留者附釘住測試。D-CODEC 若「改以轉換紀錄判定」⇒ 編碼判定改讀 processed 之 post-IC 轉換紀錄（PRE-PROV 紀錄檔之步驟狀態），不再以欄名字面。
- **驗證**（依 decisions.json 各決定取對應案，tests/feature_engineering/test_numview_core.py）：
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k mtf_dtype WHEN d_mtf=unify THEN rc=0
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k memmap_dtype WHEN d_memmap=decouple THEN rc=0
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k winsor_dtype WHEN d_winsor_dtype=unify THEN rc=0
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k codec_by_provenance WHEN d_codec=provenance THEN rc=0
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k retained WHEN d_mtf=retain THEN rc=0
  - 各改案之兩路 oracle：D-MTF＝同欄於單週期 run 與多週期 run 逐位元相等（真實格 B）＋獨立 float64 重算 ≤1 ulp；D-MEMMAP＝同輸入強制兩支輸出逐位元相等；D-WINSOR-DTYPE＝sigma／quantile 兩分支回傳 dtype 相同且後續 fracdiff 值對獨立重算 ≤1 ulp；D-CODEC＝原始名含 rank／zscore／gaussian 字面之 raw 特徵經 post-IC 只做 zscore 時編碼型別取自紀錄（非名稱），讀回誤差在該編碼容差內。mutation：各改案還原單行 ⇒ 對應 oracle 紅。
- **邊界**：①資料量恰等於 memmap 門檻；②多週期格中只有單一訓練週期；③processed 零選欄。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得改 float16 自動選；不得以放寬 oracle 容差使改案過關。

**Task 3.3 — L2 值來源（D-L2）**
- 目標：L5／L6 所吃之 L2 值與公開 L2 值之關係定案。　檔案：決定＝統一 ⇒ `feature_factory.py:_layer2_derived_polars`（L5／L6 改吃與公開落盤同一值來源，或公開落盤改用回傳表；擇一依決定紀錄）；決定＝具名保留 ⇒ `numeric_view.json` 登記兩臂與適用證據收據。　既有 caller／影響面：L5、L6 與 L2 公開值。
- 改法：同上。
- **驗證**（依 decisions.json `d_l2` 取一，tests/feature_engineering/test_numview_core.py）：
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k l2_unified WHEN d_l2=unify THEN rc=0
  - ASSERT venv/bin/python -m pytest tests/feature_engineering/test_numview_core.py -q -k l2_named WHEN d_l2=retain THEN rc=0
  - 統一案：格 A＋格 B 真實格之 L5／L6 以公開 L2 獨立重算逐位元相等；mutation：L5 改回吃另一臂 ⇒ 多週期格紅（Task 1.4 已證多週期 L1 float64）。保留案：Task 1.4 矩陣之每格 f32diff 被釘（重跑相等），任何非零格須於契約具名列出適用範圍；mutation：契約刪一格 ⇒ 紅。
- **邊界**：①`compute_all_polars` 拋錯之回退；②`FFACT_USE_POLARS=0` 之 pandas 臂（只走 `compute_category`）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得匿名統一（無決定紀錄）；不得刪任一臂而無多週期證據。

### Phase 4 — 臂／算法 fingerprint 入不可變 run／view 身分（依賴：Phase 3；C4）

**Task 4.1 — fingerprint 解析（純函式）**
- 目標：定義並計算 run 之數值 fingerprint 與 `algorithm_id`。　檔案：`numeric_view.py`（`resolve_numeric_fingerprint(*, preprocessing_config, environ, capabilities) -> Dict`、`algorithm_id(fingerprint) -> str`、`config_hash_salt(fingerprint) -> Dict`）；`numeric_view.json` 之 `fingerprint_sections`、`config_hash_salt`。　既有 caller／影響面：新建（Task 4.2 接入）。
- 改法：fingerprint 段（鍵見契約）——契約政策（各入口臂）、`value_affecting` 選擇子之**解析後有效值**（非原始字串；例 `FFACT_USE_POLARS=1` 而 Polars 不可用 ⇒ 記有效值）、能力旗標、函式庫版本、算法版本常數、表示層（codec 開關、float16 判定常數）。`algorithm_id`＝fingerprint 正規 JSON（`sort_keys`、無空白）之 sha256。`config_hash_salt`＝fingerprint 去除函式庫版本段（設計選擇①）。執行後觀測之實際臂（L6.5 群組臂取 PRE-PROV 紀錄、L2 值來源、post-IC 臂、`memory_budget.route_records()`）另存 `observed_arms`，入 manifest、不入 `algorithm_id`。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_identity.py -q -k resolve` 全綠：①對契約每個 `value_affecting` 鍵（參數化自契約）改其值 ⇒ `algorithm_id` 與 `config_hash_salt` 皆變；②每個 `non_value` 鍵改值 ⇒ 兩者皆不變；③改函式庫版本（monkeypatch 版本字串）⇒ `algorithm_id` 變、`config_hash_salt` 不變；④能力旗標變 ⇒ 兩者皆變；⑤同輸入兩次呼叫結果相同。mutation：自鹽組成刪一個 `value_affecting` 鍵 ⇒ ①該參數案紅；有效值改記原始字串 ⇒ Polars 不可用案紅。
- **邊界**：①環境未設 ⇒ 用契約登記之預設（同 `memory_budget.SELECTOR_DEFAULTS`）；②非法環境值（現行碼對部分鍵 warning 後退回預設，如 `momentum/core/config.py:24-35`）⇒ fingerprint 記退回後之有效值並帶 `invalid_env` 標記。
- **存活至**：本票交付後保留（FFSTORE 沿用 `algorithm_id`）。
- **覆蓋風險**：無。
- 不可做：不得把 `observed_arms` 放入 `algorithm_id`（執行後才知，無法作事前快取鍵）；不得讀契約外之環境鍵。

**Task 4.2 — 寫入端、身分、續跑閘**
- 目標：fingerprint 進 `config_hash` 鹽、manifest、RunIdentity，續跑與 IC 快取依之失效。　檔案：`feature_factory.py:_compute_config_hash`（加鹽鍵）、續跑閘（`:1206` 附近）、IC-first 寫 processed；`feature_storage.py:_build_feature_manifest_v2`／`_atomic_merge_feature_manifest_v2`（manifest 頂層 fingerprint 與 `algorithm_id`、processed 節點同記）；`run_provenance.py:RunIdentity`、`resolve_run_identity`；`contracts/run_provenance.json:run_identity_keys`；`momentum/Analysis/ic_engine.py:CACHE_IDENTITY_FIELDS`；倖存者契約（若其驗證 `ff_run_identity` 內鍵 ⇒ 版本 +1，依 PRE-PROV Task 2.4 前例）；`scripts/preprov_refreeze.py`（剝除鍵清單讀契約）。　既有 caller／影響面：全部生成、IC ingest／IC-first 快取、倖存者讀取端、結構凍結檔。
- 改法：manifest 合併沿 PRE-PROV 單一提交點；舊 run 無 `algorithm_id` ⇒ RunIdentity 記 `None` 並視為 legacy（快取不沿用）。續跑：已存 manifest 之 `algorithm_id` ≠ 本次 ⇒ `resume_allowed=False` 並記錄原因。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_identity.py tests/feature_engineering/test_preprov_identity.py tests/api/test_preprov_ingest_cache.py tests/momentum/Analysis/test_preprov_ic_cache.py -q` 全綠（既有斷言不放寬）：①真實短窗生成之 manifest 帶 fingerprint、`algorithm_id` 等於 Task 4.1 獨立計算；②`FFACT_USE_POLARS` 0／1 兩次生成 ⇒ 不同 `config_hash` 目錄（不互相覆寫）；③函式庫版本 monkeypatch 改變 ⇒ 同 `config_hash` 但續跑被拒、IC ingest 快取重建；④§G 全部值指紋逐位元相等；⑤結構重凍收據證「剝除新鍵後等於現行凍結值」。mutation：續跑閘不比 `algorithm_id` ⇒ ③紅；RunIdentity 漏新鍵 ⇒ `to_dict` 契約比對拋錯（既有機制）。
- **邊界**：①舊 run（無新鍵）讀特徵不受影響、IC 快取不沿用；②IC-first 已刪 raw 之 run 之 processed 節點身分。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得以 `content_sha256` 代替 `algorithm_id`（前者證內容、後者證產生方式，兩者正交）；不得遷移舊 run。

**Task 4.3 — IC 頁 view 身分**
- 目標：IC 頁第三步之輸入綁定 IC 任務當時之 run、輸出為不可變 view（C4）。　檔案：`api/services/ic_analysis_service.py` 之 `_load_features_for_transforms`（改 `load_with_identity`；`features_path` 經 canonical 解析後同）、`_apply_transforms_sync`（比對 IC 任務報告 metadata 之 `ff_run_identity`；輸出路徑與屬性）；`momentum/FeatureEngineering/feature_library.py`（如需 canonical 路徑之身分載入變體）；`api/models/ic_models.py`；`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/app/ic-analysis/page.tsx:828`（輸出路徑說明）；`docs/API_SPECIFICATION.md`（apply-transforms 回應）。　既有 caller／影響面：前端 IC 頁、`ApplyTransformsResult` 元件與其測試。
- 改法：載入身分 ≠ 任務報告身分（逐鍵）⇒ 具名錯誤 `ICViewIdentityMismatchError`（run 已於 IC 後重生）；報告身分為 null（外部 features_path 任務）之處置依設計選擇⑦；view 身分 `view_id`＝sha256（正規 JSON：run 身分、轉換設定、臂、`algorithm_id`）；輸出檔名含 `view_id` 前綴（同 view 冪等、不同 view 不覆寫）；h5 屬性與 API 回應鍵見契約 `ic_page_output_attrs`／`ic_page_response_keys`。
- **驗證**：`venv/bin/python -m pytest tests/api/test_numview_ic_page.py -q` 全綠：①同 run 兩次相同請求 ⇒ 同 `view_id`、同檔、內容逐位元相等；②轉換設定不同 ⇒ 不同檔、舊檔不變；③IC 後於隔離資料副本改一根 K 線並重生 run ⇒ 具名錯誤、無輸出；④h5 屬性之 `ff_run_identity` 等於 `load_with_identity` 回傳。mutation：比對條件拿掉 `content_sha256` ⇒ ③紅；檔名去掉 `view_id` ⇒ ②紅。前端：`npm run build` 通過、`ApplyTransformsResult.test.tsx` 綠。
- **邊界**：①IC 任務不存在；②報告缺 metadata（舊任務）⇒ 視同 null 身分處置。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：`api/` 不得自組 run 身分（只經 `load_with_identity` 與契約函式）；不得以 mtime 代替身分。

**Task 4.4 — 選擇子閘與身分之連動閘**
- 目標：新增 `value_affecting` 選擇子時，身分自動涵蓋、不得漏。　檔案：`tests/feature_engineering/test_numview_selectors.py` 增案。　既有 caller／影響面：無。
- 改法：斷言 Task 4.1 之解析器所讀之鍵集合＝契約 `value_affecting` 鍵集合（AST 讀 `numeric_view.py` 之解析表，或解析表本身即自契約生成）。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_numview_selectors.py -q` 全綠，< 10 秒。mutation：契約新增一個 `value_affecting` 鍵而解析器未讀 ⇒ 紅。
- **邊界**：①鍵改判 `certified_equal` ⇒ 自鹽移除須同提交附證據測試；②能力旗標新增同理。
- **存活至**：本票交付後保留（產出端閘）。
- **覆蓋風險**：無。
- 不可做：不得以人工清單同步代替機械比對。

### Phase 5 — 文件同步（依賴：Phase 4；C8）

**Task 5.1 — 文件與 fact-key 更正**
- 目標：把偵察所揭之文件不符改為現況。　檔案：`白話說明/還沒做的事.md`（第 47 行方向更正：純尾端延伸只會 float16→float32；第 101 行：0.00005 為單步 zscore、改引 Task 1.2 收據之 HEAD 數字、registry「zscore 分支」於現行 raw 設定不達成而非整條 registry 路徑不走）；`scripts/fact_keys.json` RM-NUMVIEW（補 freeze-baselines 真實管線零差語境與 Task 1.4 矩陣結論）、HP-NUMVIEW（R4 含 Polars 臂）後跑 `bash scripts/gen_fact_key_blocks.sh --write`；`docs/API_SPECIFICATION.md`（若 Task 4.3 未併入）。凍結之 `docs/ICPOSTLEAK_SPEC.md`、`docs/FFDSTAR_SPEC.md`、`docs/ICFIRSTALIGN_SPEC.md` 不改字面（面向未來），其 §N 對應項之關閉於本 SPEC §N 與 fact-key 記錄。
- **驗證**：`bash scripts/gen_fact_key_blocks.sh --write` rc=0 後 `git diff --exit-code` 於生成區塊外無意外變動；`grep -c "0.00005" 白話說明/還沒做的事.md` 之命中行皆含「單步」限定；`bash scripts/check_decoupling.sh` 之 R1、R4 計數不增。
- **邊界**：①白話文件依其生成規則同 commit 產 `docs/site/*.html`；②fact-key 寫入經 `scripts/live_doc_write_guard.sh`。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得改凍結 SPEC 之字面；不得改 `docs/TICKET_ORDER.md` 之順序或範圍欄。

### 待委員審之設計選擇（每項：建議／替代／理由；審查輪定稿後併入契約）
1. **fingerprint 放 `config_hash` 或另立鍵** — 建議：兩層。`value_affecting` 有效值＋能力旗標＋算法版本＋有損表示開關入 `config_hash` 鹽（前例 `_mtf_align_version`、`_feature_naming_version`、`_warmup_policy`）；完整 fingerprint（含函式庫版本）入 manifest 與 RunIdentity `algorithm_id`，續跑與 IC 快取比對之。理由：run 目錄以 `config_hash` 為鍵（§A 續跑收據），臂不同之 run 若同目錄即互相覆寫或混續——只有進鹽能結構性分開；函式庫小版本不入鹽可免目錄碎裂，但由 `algorithm_id` 比對擋混續。替代 A：全部入 `config_hash`（最簡、目錄隨每次升版碎裂、`config_hash` 不再只表設定）；替代 B：全部另立鍵不入鹽（每個重用點都須比對，攻擊面大，同目錄覆寫無結構阻擋）。
2. **函式庫版本是否入身分** — 建議：入 `algorithm_id`、不入鹽（見 1）；版本集＝契約 `library_versions`（數值相關庫）。理由：版本漂移屬會改值之環境，靜默漂移違資料品質優先序；開發期資料可重產，代價為升版後重生。替代：不入（靜默漂移）或入鹽（目錄碎裂）。
3. **缺 `method` 鍵之處置** — 建議：dict 入口縮尾啟用而缺鍵 ⇒ 拒收；pydantic 預設（`quantile`）為唯一預設來源。理由：生產 dict 皆源自 `model_dump`（Task 2.1 盤點驗之），拒收不改生產值；填預設會令現行 pandas／polars 臂之缺鍵 dict 由 sigma 變 quantile（改值）。替代：驗證器以契約預設填值（統一但改值）。
4. **L2 兩臂** — 建議：依 Task 1.4 矩陣；多週期格出現非零差 ⇒ 統一（L5／L6 改吃公開值來源，使公開 L2 可重算 L5／L6），否則具名保留並以契約登記適用格。理由：非零時公開 L2 與其衍生層不自洽，屬可重現性缺陷；零差則統一只增改動面。替代：一律具名保留（偵察 r1 群集 C7 兩家之短期立場）。
5. **有損 codec 去留** — 建議：Task 1.3 量得名稱推斷誤判欄數 > 0 ⇒ 改以 post-IC 轉換紀錄判定編碼；= 0 ⇒ 保留現狀但入鹽與身分。移除選項保留於決定點。理由：名稱字面與實際轉換無必然關係（replace 模式 post-IC 欄名不帶轉換字面），判定依據應為紀錄。替代：移除有損編碼（processed 檔變大，屬儲存取捨，須白話閘）。
6. **翻轉「實質」判準** — 建議：任一 NaN 遮罩差、任一 IC 正負號翻轉、IC 選欄倖存者集合任一進出、或（post-IC 無選欄時）逐欄 IC 排序 Kendall τ-b < 1 ⇒ `material`；|ΔIC| 以 IC 抽樣標準誤為單位另報（只報不判）。理由：全為 exact 判準，不自訂容差，符合偵察 r1 群集 C5「不發明門檻」；`material` 只觸發決定點，不自動改碼。替代：top-k Jaccard 閾值（偵察 r1 群集 C5 之另一提案；須另定 k 與閾值，屬自訂數字）。
7. **IC 任務報告身分為 null 時 IC 頁第三步之處置** — 建議：拒收並提示以 symbol／timeframe 重跑 IC。理由：無法證明 view 與 IC 所用之 run 相同，屬 IC 正確性（d）。替代：照做並於輸出與回應標 `identity_verified=false`（保留功能、透明但不擋）。
8. **量測輸入範圍** — 建議：格 A／B 為 `kline_cache.h5` 全部 symbol×tf（現 10×3）；格 C（生產預設全特徵）本機可跑者照跑、不可跑者 blocked-by 硬體入 RM-FULLSCALE。理由：「不挑代表」與 2026-09-28「本機跑得動之完整驗證照跑」；估時先報（Task 1.1）。替代：沿 10-02 收據只量 BTCUSDT 1h（不足以支撐多標的穩定性，優化優先序第 2 位）。

## §V 驗證策略與邊界測試目錄
- **格子**（真實 kline；逐格單行程串行；生成共用）：格 A＝每個 symbol×tf 單週期短窗（生產預設 replace 設定，平穩化開＋縮尾開；輸出段根數依判準檔；append 由沿用之 PRE-PROV 基準格涵蓋）；格 B＝每個 symbol 之多週期（最細週期主、其餘週期訓練）；格 C＝生產預設全特徵（本機可跑者）。另 ICPOSTLEAK §G 輸入集建法套用於每個 symbol×tf（秒級）。
- **oracle**（皆獨立重算，不讀被測輸出之自述）：①臂無關——IC 頁輸出於環境 0／1 逐位元相等且等於改前 `polars` 份；②非法設定——三入口×四臂皆於臂分派前拒收（以「無任何轉換函式被呼叫」之 spy 斷言分派前）；③post-IC 數值——測試端 numpy float64 實作（rank→gaussian→zscore、窗未滿 NaN）與 legacy 臂兩路；④精度鏈——各檢查點自探針擷取之值對 float64 鏈獨立比對；⑤身分——`algorithm_id` 以測試端獨立計算（讀契約、自讀環境與版本）相等；⑥view——載入身分與任務報告身分逐鍵；⑦值不變——§G 全部值指紋逐位元。
- **mutation**（各 Task 已列者彙總；Phase 3 只對已施工之決定）：恢復空窗 `else 100`；恢復快速核心 `elif causal_preprocessing`；驗證器不掛 `__init__`；IC 頁刪 `arm=`；`arm` 改回可選；`value_affecting` 鍵自鹽刪除；fingerprint 記原始字串而非有效值；續跑閘不比 `algorithm_id`；IC 頁比對拿掉 `content_sha256`；輸出檔名去 `view_id`；判準檔改字；收據 `criteria_sha256` 改寫；決定紀錄觸發判定與收據不符；Phase 3 各改案單行還原。每個 mutant 須由對應 oracle 轉紅。
- **測試層級與佈局**：單元（`tests/feature_engineering/test_numview_{contract,selectors,criteria,policy,identity}.py`，秒級）；整合（`tests/api/test_numview_ic_page.py`、`tests/feature_engineering/test_numview_core.py`，真實 kline 短窗）；Golden 對照（`tests/feature_engineering/test_numview_baseline.py`、`test_numview_acceptance.py`）；量測探針與收據（`handoffs/run_receipts/numview_probes/`、`handoffs/run_receipts/<date>-numview-*.json`）。皆可獨立 `pytest` 執行，不需 `run_api.py`；pytest 一律逐檔明列路徑。
- **防假綠**：既有斷言 diff 不放寬；測試刪改依 2026-10-17 裁定同提交登記審清單；量測收據之重現檢查（Task 1.2 已知零差列、Task 1.4 已知零差格）不符即停。
- **估時**（本機 8 GB，單行程串行；正式數字以 Task 1.1 實測收據為準）：秒級閘（0.1–0.3、2.1 單元、4.1、4.4）< 1 分鐘；格 A 短窗生成每格約 1–5 分鐘（PRE-PROV／PROBEWINSOR 同型格量級）× 30 格 ≈ 0.5–2.5 小時（Task 0.4 與 Phase 1 共用一次）；格 B 每格約 3–8 分鐘 × 10 ≈ 0.5–1.5 小時；Task 1.3 float64 鏈變體與 memmap 雙支另各需一輪格 A／B 生成 ≈ 1–4 小時；Task 1.4 每格兩臂約 20 秒（freeze-baselines 校準 17.2 秒）× 40 格 × 2 ≈ 0.5 小時；Task 1.6 依鍵數，估 1 小時內；格 C 每格約 60–100 分鐘（PRE-PROV 全特徵 12h 實測量級），可跑格數待 Task 1.1。合計格 A／B 部分約 3–9 小時，格 C 另計——依 §C 先白話報再跑。
- **邊界目錄**：空窗清單 ✔ 2.1／未知 method 與大小寫 ✔ 2.1／缺鍵 ✔ 2.1／std=0 ✔ 3.1／全 NaN 欄 ✔ 1.3／近零參照值 ✔ 1.2／資料量恰等於 memmap 門檻 ✔ 3.2／Polars 不可用 ✔ 2.2、4.1／舊 run 與舊快取 ✔ 4.2／IC 後 run 重生 ✔ 4.3／前史不足格 ✔ 0.4／記憶體守護終止 ✔ 0.4／並發寫：單 run 單寫者（既有 manifest 鎖），✗。

## §R 回退
- 每 Phase 獨立 commit、可單獨 revert；Phase 3 每個決定點獨立 commit。
- Phase 2 revert ⇒ 回到非法設定臂間分歧與 IC 頁依環境選臂（含現存缺陷）；Phase 4 revert ⇒ `config_hash` 回舊組成（新 run 目錄名改變，開發期資料重產）、身分無新鍵；Phase 3 revert ⇒ 回改前核心，`algorithm_versions` 一併回退使身分區分。
- 不設 feature flag（改值之核心不得保留可切回之環境分岔——本票目的即消除環境依賴數值）。
- §G 任一值指紋不符（Phase 0、2、4）或改案 oracle 不過（Phase 3）⇒ 不合併。

## §N N/A 登記與殘留

### N/A
- 無（各必填段皆適用）。

### 殘留
- **NUMVIEW-R1 跨市場量測與驗收**（台股、美股、期貨之格 A／B／C）— `為何現在不做: blocked-by:PRE-MARKET-DATA（docs/TICKET_ORDER.md 第 B 列；本機無非加密市場 K 線，使用者 2026-10-02 裁定跨市場驗收列 blocked-by 資料）`；觸發：非加密市場資料與 adapter 到位；登記處：本 SPEC §N、`白話說明/還沒做的事.md`。設計面已不寫死市場（§C）。
- **NUMVIEW-R2 縮尾唯一責任端與算法檢驗**（pre-IC 與 IC 端是否重複縮尾、sigma／quantile 之算法正確性）— `為何現在不做: blocked-by:全票排序第 9 步「縮尾重複」（docs/TICKET_ORDER.md:43，硬依賴 7、8；須依 PRE-PROV 逐欄紀錄與本票臂政策定案後之實際證據定責任端）`；本票只處理臂間不一致（C3 歸屬裁定）；觸發：第 9 步開工；登記處：本 SPEC §N。
- **NUMVIEW-R3 格 C 本機不可跑之 symbol×tf**（若 Task 1.1 判定）— `為何現在不做: user-ruling:2026-09-28 使用者裁定開發路線「本機跑得動之完整驗證照跑不延後；跑不動者逐項 blocked-by 硬體列入」RM-FULLSCALE`；觸發：≥32 GB 機器到位（RM-FULLSCALE 第 16 步）；登記處：`scripts/fact_keys.json` RM-FULLSCALE 清單、本 SPEC §N。Task 1.1 未判出不可跑格 ⇒ 刪除本條。
- **NUMVIEW-R4 FFSTORE 快照（snapshot）與 append 語意下之歷史列 dtype 變動**— `為何現在不做: blocked-by:全票排序第 14 步 FFSTORE（docs/TICKET_ORDER.md 第 14 列「依研究 r1 與第 8 步契約」，消費本票 algorithm_id 與 Task 1.3 延伸格收據）`；觸發：FFSTORE 開工；登記處：本 SPEC §N、RM-FFSTORE。
- 承接關閉（收案時於 fact-key 記錄，不改凍結 SPEC 字面）：ICPOSTLEAK §N 各分支 zscore 核心差（研究②由 Task 1.2、處置由 Task 1.5／3.1；研究①registry float64 依 D-RESEARCH）；FFDSTAR §N R4（Task 2.1）；ICFIRSTALIGN §N L2 兩臂（Task 1.4／3.3）。
