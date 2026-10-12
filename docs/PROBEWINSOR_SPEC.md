# PROBEWINSOR — 公開域預熱探測之縮尾門檻與公開輸出同源 — SPEC

> 來源：偵察 r1 收斂檔 `handoffs/reconcile/20261012-probewinsor-x-consult-r1/synth.md`（主委獨立版 `handoffs/20261012-probewinsor-x-consult-r1-claude.md`）；起因 TESTREG 第 2 批審碼 r1（`handoffs/reconcile/20261010-testreg-b2-review-r1/synth.md`）、TESTREG SPEC §N R9　|　日期：2026-10-12　|　對應 TODO：`docs/manifests/PROBEWINSOR.json`
> 版本：v5（2026-10-13；v4 經審查 r5 修訂：凍結錨點加「HEAD 生產 .py 身分等於契約所記改前身分」與「kline 等於契約所記權威雜湊」、`config/` 納入凍結輸入、10c 依 pathspec 分臂並加三案、M9–M12 改為只拿掉凍結閘一臂之變體、09g 監聽公開身分方法之呼叫與 M7d）。v4（v3 經審查 r4 修訂：凍結之輸入〔契約、helper、凍結腳本〕亦須為已提交版本並記其 blob、本票符號清單改讀該提交自身之契約、驗收直接覆蓋實際凍結閘〔10c〕與實作後符號存在〔10d〕、09g 改用真實身分不替換身分函式）。v3（v2 經審查 r3 修訂：凍結錨點改自動取 HEAD 並以內容證明改前碼、Task 1.4 經公開續跑入口驗收、舊格式完成項維持保留並列殘留、兩支既有續跑測試之身分替身、manifest 禁令納入 Task 1.4、受影響測試掃描之清單取得 fail-closed）

## §RISK 風險分級
- **大小**：大（全票排序第 5a-1 步；使用者 2026-10-12 裁定）。
- **命中高風險原則**：(a) 數值／資料品質——前處理總開關關閉時公開輸出之預熱深度、晚到判定、品質狀態、輸出欄集合與值；(b) 跨模組共用路徑——前處理總開關之判斷現散於 `feature_factory.py`、`warmup_window.py`、`config_manager.py` 共 6 處，本票收為單一函式；API 批次續跑（`api/services/feature_factory_batch_service.py`）改經工廠公開身分方法核對完成項。
- RISK-HIT: a,b
- 命中 (a) ⇒ §G 必填、adversarial review 必跑。

## §A 假設與待使用者確認
- **已驗證事實**（FACT-RECEIPT 10 條）：
  - 缺陷碼路徑：探測縮尾器只看子開關。FACT-RECEIPT: `sed -n 2686,2695p momentum/FeatureEngineering/feature_factory.py` → 印出 `if not config.preprocessing.winsorization.enabled: return None`，無 `preprocessing.enabled` 判斷（主委 實跑 2026-10-12）
  - 公開輸出看總開關。FACT-RECEIPT: `sed -n 3861,3866p momentum/FeatureEngineering/feature_factory.py` → 印出 `if getattr(config.preprocessing, "enabled", False):` 才建 `FeaturePreprocessor`（主委 實跑 2026-10-12）
  - 總開關判斷現有 6 處各自寫。FACT-RECEIPT: `git ls-files -z -- 'momentum/*.py' 'api/*.py' | xargs -0 grep -nE "preprocessing\.enabled|pp\.enabled|getattr\((config\.)?preprocessing, *\"enabled\""` → 印出 `config_manager.py:338`、`feature_factory.py:363`、`:3158`、`:3224`、`:3863`、`warmup_window.py:257`；另 `feature_validator.py:223`、`api/services/feature_export_service.py:108` 讀成品中繼資料字典（非設定），不在此列（主委 實跑 2026-10-12）
  - 機制：縮尾遮窗未滿之列（`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3230`、`:3255`）使首個有限值後移「窗長−1」列；探測段內全無有限值之欄只入 `late_names`、不觸發加倍（`feature_factory.py:2646–2657`）；總開關關閉時 D₀ 不含縮尾窗（`warmup_window.py:257`）⇒ 晚到但有值之欄被遮成探測段內全 NaN ⇒ 少加倍。FACT-RECEIPT: `bash handoffs/run_receipts/probewinsor_probes/run_cheap.sh e1h_off:current e1h_off:fixed` → 印出 current `rounds [{depth 374, late_columns 0}]`、fixed `rounds [{374, 2}, {748, 0}]`（主委 實跑 2026-10-12；composer 偵察 r1 獨立複跑同值）
  - 公開輸出後果（真實 kline、BTCUSDT、窗 2026-01-01～01-31、`icfirstalign_helpers.s2_payload`）。FACT-RECEIPT: `bash handoffs/run_receipts/probewinsor_probes/compare_gen.sh e1h_off e12h_off` → 印出 `e1h_off` depth `[374,748]`、quality `["partial","complete"]`、`warmup_insufficient [3,0]`、`value_or_nan_diff_cols 3`；`e12h_off` quality `["partial","complete"]`、`stable_start_diff 3`（其中 2 欄現行碼整窗全 NaN 且無事件）（主委 實跑 2026-10-12）
  - 死欄剔除開啟（生產預設 `feature_config.py:503`）時現行碼靜默剔欄。FACT-RECEIPT: `PW_WINDOW=2026-01-01,2026-03-01 bash handoffs/run_receipts/probewinsor_probes/run_gen.sh <scratch> e12h_off_dd:current e12h_off_dd:fixed` → 印出 current `public_column_count 151`、`quality_status complete`；fixed `154`、`complete`（主委 實跑 2026-10-12）
  - 前處理開啟不受影響。FACT-RECEIPT: `bash handoffs/run_receipts/probewinsor_probes/compare_gen.sh e1h_on e1h12h_on` → 印出兩格 `value_or_nan_diff_cols 0`、depth 相同、quality 相同（主委 實跑 2026-10-12）
  - 舊 registry 沿用路徑：多週期 resume 對已有 L1–L6 檢查點之週期跳過重算（`momentum/FeatureEngineering/timeframe/multi_tf_generator.py:473–496`），resume 閘不比對載入窗（`feature_factory.py:1205–1249`）；`_try_load_cache` 經 `load_factory_output` 讀 `*_factory.h5`、CGSA 不寫此檔 ⇒ 恆不命中。FACT-RECEIPT: `sed -n 4151,4162p momentum/FeatureEngineering/feature_factory.py` → 印出 `cached = self._storage.load_factory_output(symbol, timeframe)`（主委 實跑 2026-10-12）
  - API 批次續跑之第二條沿用路徑：`FeatureFactoryBatchService.resume_batch` 對 checkpoint 之完成項，只要能自輸出路徑解析 run hash（＝當時之 config_hash）且其 `feature_manifest.json` 存在即保留、不重算，不比對目前碼之身分。FACT-RECEIPT: `sed -n 256,271p api/services/feature_factory_batch_service.py` → 印出 `if self._completed_manifest_exists(item, run_hash): retained_completed.append(item)`（主委 實跑 2026-10-12；審查 r2 codex 指出）
  - 舊格式完成項之既有契約與跨票凍結：`tests/api/test_run_lifecycle_api.py::test_resume_batch_keeps_legacy_completed_item` 斷言 run hash 無法解析之完成項保留（`skipped_items == 1`、不重算）；FRAMEPATH 已凍結並蓋章之處置表對該測試有改寫操作 OP-116（綁原文雜湊、全部斷言保留）。FACT-RECEIPT: `jq -c '.. | objects | select(.id? == "OP-116") | {kind, phase}' tests/_golden/framepath/test_disposition.json` → 印出 `{"kind":"rewrite","phase":2}`（主委 實跑 2026-10-13）
- **待確認**：無
- **已確認結果**：2026-10-12 使用者裁定新增全票排序第 5a-1 步 PROBEWINSOR（`docs/TICKET_ORDER.md`「使用者裁定（2026-10-12，插入一步）」）；2026-10-11 使用者裁定 FF 生成提速（含 R8 重複縮尾）延後至全專案跑通。

## §C 約束
- 解耦 7 條：新函式置 `momentum/`，不 import `api/`；不新增服務互相 import。
- 不可違反原則：不弱化 NaN／inf 閘、不放寬既有測試斷言、跨 tier 與多 symbol 行為一致；不得寫死加密貨幣／24h／UTC 假設（本票不涉時間單位）。
- **不變之範圍（逐位元）**：凡 `preprocessing.enabled=True`，或 `preprocessing.enabled=False ∧ winsorization.enabled=False` 之生成——探測輪次與深度、`probe_late`、首個有限值表、`output_window`、公開全部欄之值與 NaN 遮罩、輸出欄集合、`stable_start`、`warmup_insufficient_columns`、`quality_status`、`config_hash`——修正前後逐位元相同。
- **刻意可見差異（只在 `preprocessing.enabled=False ∧ winsorization.enabled=True` 之子空間）**：
  - C1 探測不再縮尾 ⇒ 每輪 `late_columns`、加倍次數與末深度、`max_warmup_bars`、`ingest_start`、`probe_late`、末輪首個有限值表可變；其值須等於同設定「縮尾子開關關」者（總開關關閉時子開關不得有任何效果）。
  - C2 因 C1 載入起點提前 ⇒ 公開輸出之晚到欄值與 NaN 遮罩、`stable_start`、`warmup_insufficient_columns`、`quality_status`（partial→complete）可變；起點相依欄（遞迴、累計）之值可變。
  - C3 死欄剔除開啟時，現行碼下有效值不足而被剔之晚到欄於修正後保留 ⇒ **輸出欄集合與輸出大小可變**（實測 151→154 欄）；此變化屬正確性修正，須經使用者白話審閱核可（不擅改輸出大小原則）。
  - C4 `config_hash` 於此子空間改變（Task 1.2 之鹽），使修正前同 hash 之 registry 與成品不被沿用；其餘子空間 `config_hash` 不變。
- **刻意可見差異（API 批次續跑，全部設定；Task 1.4）**：C5 續跑時每個已完成項以目前碼重算身分（`FeatureFactory.config_identity`），與其輸出路徑之 run hash 不符者重排重算（與 manifest 遺失者同一處理）。身分含 K 線最後時間戳與起訖日（`_compute_config_hash` 既有欄位），故**改碼或 K 線更新後之續跑會重算已完成項**（改前會沿用）；無法自輸出路徑解析 run hash 之舊格式項維持保留（改前契約，見 §N R3）；身分重算拋例外者重排。
- 耗時：此子空間探測不再縮尾（V-6 型探測 85% 之縮尾不再發生）；若修正後多加倍則探測與生成耗時增加（實測 e1h_off 探測 1.6→2.5 秒）。
- 範圍外：前處理開啟時探測與公開 L6.5 各縮尾一次之重複計算（R8，user-ruling 2026-10-11）；IC 端縮尾（全票排序第 9 步）；前端（總開關 `PreprocessingPanel.tsx:212` 行為不變）。

## §G Golden / Baseline
- **feature/kline 條件**：真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。
- **凍結時機**：Task 1.0 於錨點碼態（錨點＝執行時之 HEAD，由腳本自取、不由呼叫者指定；須為本票首個生產碼提交前之碼，以 **HEAD 自身之** contract 為錨：`anchor_production_py_sha256`（改前之 `momentum/`、`api/` 全部 .py 之身分，`probewinsor_helpers.production_py_digest`）須等於 HEAD 之身分、`anchor_absent_symbols`（非空）所列本票生產符號皆不存在於 HEAD、真實 kline 之 sha256 須等於 `kline_sha256`（其值＝`kline_sha256_authority` 所指之 failopen 凍結基準所記）；產生 baseline 之輸入——`probewinsor_helpers.INPUT_PATHSPECS` 所涵蓋之契約、`tests/feature_engineering/` 下 helper、凍結腳本與 `config/`——須等於 HEAD 之已提交版本，並以 `input_blobs` 記於 baseline）以 `scripts/freeze_probewinsor_baseline.py` 產生 `tests/_golden/probewinsor/baseline.json`；設定格之唯一定義＝`tests/_golden/probewinsor/contract.json`（payload 族、週期、總開關、子開關、平穩化開關、窗、附加層；本 SPEC 不重列格數）。凍結為一次性寫入：baseline 已存在即拒寫；之後只讀。
- **baseline 內容（每格）**：`config_hash`；`output_window` 全欄位；探測 `rounds`（每輪 depth、late_columns）；`probe_late` 之排序清單 sha256 與數量；末輪首個有限值表之 canonical JSON sha256；公開輸出欄名集合（排序清單）；每欄 `{nan, values}` 指紋（`tests/feature_engineering/ffstat_helpers.public_fingerprints` 同式，float32、NaN 以 0 取代）；`stable_start` canonical sha256；`warmup_insufficient_columns` 清單；`quality_status`；牆鐘與峰值 RSS（資訊性，不比對）。另記 §V 邊界 08 所需之呼叫點真值表（同 contract 所列輸入）。文件層另記 `frozen_at_head`、`input_blobs`（`probewinsor_helpers.INPUT_PATHSPECS` 所涵蓋檔於 frozen_at_head 之 blob sha）與 `environment`（Python 與數值套件版本，`probewinsor_helpers.environment_versions`）。
- **通過條件（全部精確相等，無容差）**：見 §V 邊界 01–08、10；任一欄指紋、清單或 sha 不同即列出該格與該鍵 = FAIL。

## §P Phase 與依賴

### Phase 1 — 總開關單一判斷、探測同源、快取身分（依賴：無）
**Task 1.0 — 錨點凍結**
- 目標：於生產碼改動前凍結 §G baseline。　檔案：`scripts/freeze_probewinsor_baseline.py`（新建）、`tests/_golden/probewinsor/contract.json`（TODO 階段寫定）、`tests/_golden/probewinsor/baseline.json`（產出）。　既有 caller：新建無 caller。
- 改法：讀 contract 之每格，逐格於獨立暫存目錄（cwd、`FFACT_FEATURE_REGISTRY_PATH`、`FFACT_CGSA_WORK_DIR`、`FeatureStorage` 根、`tempfile.tempdir`、`FeaturePreprocessor._d_star_cache_dir` 皆指向該格暫存目錄；`tests/feature_engineering/probewinsor_helpers.py` 之 `isolated`）以 `create_feature_factory(cache_dir=<kline dir>, validate_continuity=False).generate_features(..., force_regenerate=True, persist=True)` 生成，自工廠實例讀探測狀態（`_public_warmup_probe`、`_public_warmup_late`、`_public_warmup_first_finite`），自成品讀公開指紋與中繼資料；單組串行；每格完成即刪暫存。`--check` 模式重跑全部格並與既有 baseline 逐鍵比對（rc 0／1），不寫檔。
- **驗證**：於錨點碼態執行 `venv/bin/python scripts/freeze_probewinsor_baseline.py` rc 0，再 `--check` rc 0（凍結可重現）；baseline 之格數等於 contract 之格數；contract 所標 `anchor_expect` 之格（e1h 前處理關＋縮尾開：`rounds` 等於 `[{"depth":374,"late_columns":0}]`、`quality_status` 等於 `partial`）與 §A 收據一致；baseline 單獨提交（先於生產碼提交），§V 邊界 10 綠。
- **邊界**：①寫入模式之來源檢查（`provenance_errors`）任一不合 ⇒ 具名拒絕（rc 2）、不寫檔：工作樹之 `momentum/`、`api/` 之 .py 或凍結輸入（`INPUT_PATHSPECS`）對 HEAD 有改動；`momentum/`、`api/`、`tests/feature_engineering/`、`scripts/` 有未追蹤（含被 `.gitignore` 忽略者）之 .py；HEAD 自身之 `anchor_absent_symbols` 為空、讀不到或 HEAD 已含其任一字面；HEAD 之生產 .py 身分不等於契約 `anchor_production_py_sha256`；kline 之 sha256 不等於契約 `kline_sha256`；任一 git 呼叫或錨點讀取失敗；②baseline 已存在時執行寫入模式 ⇒ 具名拒絕（rc 2）；③某格生成拋例外 ⇒ 整次凍結失敗（rc 2）、不寫部分 baseline。
- **存活至**：本票收案後保留（PROBEWINSOR 驗收之錨點證據）。
- **覆蓋風險**：無（後續 Task 只讀）。
- 不可做：不得以修正後碼態凍結；不得合成資料；不得容差比對。

**Task 1.1 — 前處理總開關單一判斷函式；探測縮尾器同源**
- 目標：前處理總開關只由一個函式判斷；探測（與校準域）之縮尾器於總開關關閉時不縮尾。　檔案：`momentum/FeatureEngineering/feature_config.py`（新增 `l65_enabled(config) -> bool`）；`momentum/FeatureEngineering/feature_factory.py` 之 `_stationarity_config_enabled`、`_build_l7_raw_preprocessing_metadata`、`_resolve_l65_generation_mode`、persist 分支（現 `:3863`）、`_calibration_winsorizer`；`momentum/FeatureEngineering/warmup_window.py` 之 `_collect_l65_stack_bars`；`momentum/FeatureEngineering/config_manager.py` 估欄數（現 `:338`）。　既有 caller：上列函式之全部呼叫者，於 §C 不變範圍內行為不變，列於 manifest `callers_now`。
- 改法：
  - `l65_enabled(config)`：`preprocessing` 屬性缺或為 None ⇒ `ValueError("FactoryConfig.preprocessing is missing; cannot dispatch L6.5 mode (expected explicit Mode A/B/C selection).")`；`preprocessing.enabled` 缺或為 None ⇒ `ValueError("FactoryConfig.preprocessing.enabled is missing; cannot dispatch L6.5 mode (expected bool).")`；否則 `bool(preprocessing.enabled)`。錯誤訊息逐字同現行 `_resolve_l65_generation_mode`。
  - `_resolve_l65_generation_mode` ⇒ `"ic_first_pre" if l65_enabled(config) else "none"`。
  - persist 分支 ⇒ `if l65_mode != "none":`（`l65_mode` 為同函式先前已算出之值）。
  - `_stationarity_config_enabled` ⇒ `l65_enabled(config) and (fracdiff.enabled or adf.enabled)`。
  - `_build_l7_raw_preprocessing_metadata` 之 `config_enabled` ⇒ `l65_enabled(config)`。
  - `_collect_l65_stack_bars` ⇒ `if not l65_enabled(config): return 0`。
  - `ConfigManager` 估欄數 ⇒ `if l65_enabled(config):`。
  - `_calibration_winsorizer` ⇒ `if not l65_enabled(config) or not config.preprocessing.winsorization.enabled: return None`；其餘不變。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_probewinsor.py` rc 0（§V 邊界 01–04、06–08）；manifest `gate_cmd` rc 0；`grep -r "from api\." momentum/` 計數 == 0。
- **邊界**：①`preprocessing=None` 或 `enabled=None` 之設定物件 ⇒ 列於邊界 07 之呼叫點皆拋上列 `ValueError`；②總開關開＋縮尾關 ⇒ 探測不縮尾、公開不縮尾（邊界 02）；③未填起始日 ⇒ 探測不執行，修正前後輸出相同（邊界 06）。
- **存活至**：本票收案後保留。
- **覆蓋風險**：無。
- 不可做：不得於 `_resolve_public_window` 另加總開關判斷（唯一判斷在 `l65_enabled`）；不得改 `FeaturePreprocessor` 內部之子開關語意；不得改縮尾演算法、窗長或原生週期放大；不得改 `_classify_calibration_column`、加倍規則或 `warmup_late_columns`。

**Task 1.2 — 快取身分（off-only 鹽）**
- 目標：修正改變輸出之子空間取得新 `config_hash`，其餘子空間不變。　檔案：`momentum/FeatureEngineering/feature_factory.py` 之 `_compute_config_hash` 與新增模組層常數 `PROBE_L65_GATE_SALT`、方法 `_probe_gate_salt(config) -> Optional[str]`。　既有 caller：`generate_features`、`_generate_features_impl`、`run_ic_first` 經 `generate_features`。
- 改法：`_probe_gate_salt(config)`＝`PROBE_L65_GATE_SALT if (not l65_enabled(config) and bool(config.preprocessing.winsorization.enabled)) else None`；`_compute_config_hash` 於加入 `_warmup_table_sha256` 後、序列化前：鹽非 None ⇒ `config_payload["_probe_l65_gate"] = 鹽`。`PROBE_L65_GATE_SALT = "probe_winsor_follows_public_l65_v1"`。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_probewinsor.py -k boundary_05` rc 0（§V 邊界 05 三條：錨點 hash 相等 2 類、不等 1 類）。
- **邊界**：①總開關開（任何子開關）⇒ hash 等於錨點；②總開關關＋縮尾關 ⇒ hash 等於錨點；③總開關關＋縮尾開 ⇒ hash 不等於錨點，且同設定兩次呼叫相等。
- **存活至**：本票收案後保留。
- **覆蓋風險**：無。
- 不可做：不得改其他鹽或 payload 正規化；不得以清空 `data_cache/cgsa_work` 代替身分改變。

**Task 1.4 — 批次續跑之完成項身分核對**
- 目標：API 批次續跑不沿用身分已不符之完成項（§C C5）。　檔案：`momentum/FeatureEngineering/feature_factory.py` 新增公開方法 `config_identity(symbol, timeframe, config_override=None, start_date=None, end_date=None) -> str`；`api/services/feature_factory_batch_service.py` 之 `resume_batch` 與新增 `_partition_completed_items(checkpoint, identity) -> (retained, requeued)`、`_resume_identity(checkpoint) -> Callable[[str, str], str]`。　既有 caller：`resume_batch` 之呼叫者（`api/routes/feature_factory.py`）；`tests/api/test_feature_factory_batch_resume.py` 等既有續跑測試。
- 改法：
  - `config_identity`＝`self._compute_config_hash(self._resolve_config(config_override), symbol, timeframe, start_date=start_date, end_date=end_date)`（與 `generate_features` 同一身分，不另定義）。
  - `_resume_identity(checkpoint)`：以 `checkpoint["request_payload"]` 之 `config_override`、`start_date`、`end_date`，及與批次生成同一 kline 目錄（`settings.data_cache_path / "feature_klines"`，取不到時同 `_compute_single_body` 之退回）建 `create_feature_factory(cache_dir=…)`，回傳 `lambda symbol, timeframe: factory.config_identity(symbol, timeframe, config_override, start_date, end_date)`。
  - `_partition_completed_items(checkpoint, identity)`：逐完成項——run hash 無法解析 ⇒ 保留（改前行為，不呼叫 identity）；manifest 不在 ⇒ 重排；`identity(symbol, timeframe)` 拋例外或不等於 run hash ⇒ 重排；否則保留。重排項以 `{"symbol", "timeframe"}` 附加至 `queued_items`（同改前 manifest 遺失之處理）。
  - `resume_batch` 以上述兩者取代原保留迴圈；其餘不變。
  - 既有測試之前置（與本 Task 同一提交；只增一行身分替身、不改任何斷言）：`tests/api/test_run_lifecycle_api.py::test_resume_batch_retains_completed_item_with_present_manifest` 與 `tests/api/test_batch_retention.py::test_retention_crash_a_resume_batch_path_marks_pending` 之完成項以假 run hash（`cfg_batch2d`、`cfg_batch_ret`）代表「目前碼所產」，於呼叫 `resume_batch` 前以 `monkeypatch.setattr(service, "_resume_identity", …)` 令身分等於該假 hash（試作補丁 `handoffs/run_receipts/probewinsor_probes/trial_test_setup.patch`）；其餘經 `resume_batch` 之既有測試用不可解析之舊格式路徑或 manifest 不在之路徑，行為不變、不改。
- **驗證**：`venv/bin/python -m pytest tests/api/test_probewinsor_batch_resume.py` rc 0（§V 邊界 09a–09g、M7、M7b）；`tests/api/` 之批次續跑既有測試（`tests/api/test_feature_factory_batch_resume.py`、`test_batch_date.py`、`test_batch_retention.py`、`test_run_lifecycle_api.py`）修正前後結果相同（錨點既有紅 `test_run_lifecycle_api.py` 之 `test_lease_sink_holds_until_release`、`test_generate_warmup_delete_lease_chain` 兩項除外，列於 Task 1.3 收據）。
- **邊界**：①身分相符且 manifest 在 ⇒ 保留；②身分不符 ⇒ 重排；③舊格式項無法解析 run hash ⇒ 保留且不重算身分（§N R3）；④身分重算拋例外 ⇒ 重排；⑤經公開 `resume_batch`：回應之 `skipped_items`／`queued_items` 與實際重算者等於①②之分割。
- **存活至**：本票收案後保留。
- **覆蓋風險**：無。
- 不可做：不得改 checkpoint 格式、`_resolve_completed_run_hash`、`_completed_manifest_exists` 之語意；不得在 API 層另算 hash（只經 `config_identity`）；不得 import `momentum` 以外之服務；不得改 `test_resume_batch_keeps_legacy_completed_item`（FRAMEPATH 處置 OP-116 綁其原文）；不得改既有測試之斷言。

**Task 1.3 — 受影響既有測試與 RATIOUNSAFE 前處理關臂**
- 目標：證明修正只在 §C 子空間造成差異，且差異已逐項歸因。　檔案：無生產碼；收據 `handoffs/run_receipts/probewinsor-affected.json`。
- 改法：於 Task 1.1、1.2、1.4 之後執行。manifest `risk_mitigation` 之 `affected_tests`（`handoffs/run_receipts/probewinsor_probes/affected_scan.py` 機械挑選：前處理總開關設為 False 之寫法、被改符號之直接引用；掃描遇讀檔或語法錯誤即 rc 1；另加批次續跑測試與 RATIOUNSAFE 測試）於錨點碼態與修正後碼態各跑一次（單組串行），逐 nodeid 記結果；`scripts/freeze_ratiounsafe_baseline.py` 之前處理關臂於修正後碼態以其既有比對模式比對 `tests/_golden/ratiounsafe/`。
- **驗證**：收據 `handoffs/run_receipts/probewinsor-affected.json` 中錨點綠而修正後紅之 nodeid 數 == 0，或每一項皆附「屬 §C 刻意差異」之具名歸因且經審碼核可後以 TODO 修訂處置（不得放寬斷言換綠）；RATIOUNSAFE 比對 rc 0，或差異逐鍵列於收據並歸因 §C。
- **邊界**：①錨點即紅之 nodeid ⇒ 記「HEAD 既有紅」不歸本票；②`tests/feature_engineering/test_failopen_correctness.py` 之 V-6 重項（`test_v6_*`）⇒ 不在本票跑（見 §N R1）。
- **存活至**：收據保留至本票收案。
- **覆蓋風險**：無。
- 不可做：不得刪改既有斷言；不得以 skip／xfail 暫避。

## §V 驗證策略與邊界測試目錄
- 測試檔：`tests/feature_engineering/test_probewinsor.py`（真實 kline；`requires_kline`；單一 pytest 程序內同格只生成一次；設定格含平穩化開啟之族，實跑校準前置關卡與 d* 搜尋）、`tests/api/test_probewinsor_batch_resume.py`（邊界 09）。單格之一切寫入經 `probewinsor_helpers.isolated` 導向暫存目錄（含 d* 快取），不寫專案 `data_cache`。比較鍵＝§G baseline 內容（不含牆鐘、峰值）。「設定回顯」＝成品中繼資料之 `preprocessing_config_enabled` 與 `config_payload`，邊界 01／04／06 比較時排除；`config_hash` 只於邊界 02／03／05 比較。
- **邊界目錄**：
  - 邊界 01（總開關關閉時子開關無效果）：contract 每一 payload 族之「總開關關＋縮尾開」與「總開關關＋縮尾關」兩格，於修正後碼態之全部比較鍵相等。
  - 邊界 02（總開關開不變）：contract 全部總開關開之格，修正後全部比較鍵（含 `config_hash`）等於錨點 baseline。
  - 邊界 03（總開關關＋縮尾關不變）：該類全部格，修正後全部比較鍵（含 `config_hash`）等於錨點。
  - 邊界 04（刻意差異釘於錨點）：每一「總開關關＋縮尾開」格之修正後比較鍵等於錨點同族「總開關關＋縮尾關」格（修正前此邊界紅）；且錨點兩格之差異面等於 contract 之宣告——`anchor_differs`（任一比較鍵不同；全部成對族皆是，至少探測輪次或首個有限值表不同）、`anchor_public_differs`（公開輸出鍵 `compare_keys.public` 不同；只 contract 所標之族——短窗單週期、12h 單週期、死欄剔除、平穩化開啟之單週期），防 oracle 空轉。
  - 邊界 05（快取身分）：§P Task 1.2 三條邊界；且每格 `config_identity` 等於 `_compute_config_hash`。
  - 邊界 06（未填起始日）：contract 之未填起始日格（總開關關＋縮尾開），修正後比較鍵等於錨點。
  - 邊界 07（缺鍵）：`preprocessing=None`、`enabled=None` 兩種設定物件對 `l65_enabled`、`_resolve_l65_generation_mode`、`_collect_l65_stack_bars`、`_stationarity_config_enabled`、`_calibration_winsorizer`、`_probe_gate_salt` 之行為：皆拋 `ValueError` 且訊息逐字等於 §P Task 1.1。
  - 邊界 09（批次續跑，Task 1.4）：09a 身分相符保留、09b 身分不符重排、09c manifest 不在重排、09d 舊格式項不解析且保留、09e 身分拋例外重排、09f `_resume_identity` 等於 `config_identity` 等於 `_compute_config_hash`，且「總開關關＋縮尾開」格之身分不等於錨點凍結之 hash、總開關開格之身分等於錨點；09g 經公開 `resume_batch` 且不替換身分函式（完成項之 run hash 一筆取目前碼之真實 `config_identity`、一筆為舊值）：相符者跳過（`skipped_items` 1）、不符者與原待排者重算（`queued_items` 2、生成替身記錄之重算者恰為該兩者），且監聽（不替換）`FeatureFactory.config_identity` 記錄到對兩個可解析完成項各一次、參數依簽章綁定後等於（symbol、timeframe、請求之 config_override、start_date、end_date）。
  - 邊界 10（凍結來源）：baseline 之 `frozen_at_head` 與首次加入 baseline 之提交，皆不含該提交自身契約之 `anchor_absent_symbols` 任一字面（`probewinsor_helpers.absent_symbol_violations` 為空），且 baseline 之 `input_blobs` 等於 `frozen_at_head` 之輸入 blob、`frozen_at_head` 之生產 .py 身分等於契約 `anchor_production_py_sha256`、baseline 之 kline 雜湊等於契約 `kline_sha256` 等於 failopen 凍結基準所記、baseline 之 `environment` 等於目前執行環境（不同即須重凍並經審查）；10b 該檢查對「含本票生產符號」與「讀檔失敗」之輸入必報違反（偵測器非空轉）；10c 實際凍結入口（`freeze_probewinsor_baseline.main` 寫入模式，git 結果依 pathspec 分別以替身決定、錨點讀取與生成以替身代替）八案：HEAD 含本票符號、生產碼與輸入皆有改動、有未追蹤 .py、git 失敗、只有凍結輸入有改動、生產身分不等於契約、kline 不等於契約皆 rc 2 且不寫 baseline，全部乾淨時 rc 0 且寫出；10d（實作後）`anchor_absent_symbols` 所列字面皆存在於工作樹生產檔（清單確為本票符號）。
  - 邊界 08（呼叫點真值表）：contract 所列設定（總開關 × 縮尾 × fracdiff × adf）下 `_stationarity_config_enabled`、`_resolve_l65_generation_mode`、`_collect_l65_stack_bars`（值）、`_build_l7_raw_preprocessing_metadata`（整個回傳字典）、`ConfigManager` 估欄數之結果等於錨點凍結之真值表。
- **mutation（每支皆以 monkeypatch 換入改壞版本，斷言對應邊界之比較器回報非空差異）**：M1 `_calibration_winsorizer` 還原為只看子開關 ⇒ 邊界 01、04 偵出；M2 `_calibration_winsorizer` 恆回 None ⇒ 邊界 02 於 e1h 總開關開格偵出（首個有限值表）；M3 `_resolve_l65_generation_mode` 恆回 `"ic_first_pre"` ⇒ 邊界 01 偵出；M4 `_probe_gate_salt` 恆回 None ⇒ 邊界 05③偵出；M5 `_probe_gate_salt` 恆回鹽 ⇒ 邊界 05①偵出；M6 `_collect_l65_stack_bars` 忽略總開關 ⇒ 邊界 03 偵出；M7 `_partition_completed_items` 改回只看 manifest ⇒ 邊界 09b 偵出；M7b 同一改壞經公開 `resume_batch` ⇒ 邊界 09g 偵出；M7c `_resume_identity` 改為固定值 ⇒ 邊界 09g 偵出；M7d `_resume_identity` 改走私有 `_compute_config_hash`（值相同）⇒ 邊界 09g 之公開方法呼叫紀錄偵出；M9–M12 以凍結腳本原始碼之變體（各只拿掉一臂：本票符號檢查、凍結輸入 diff、生產身分錨點、kline 權威）驅動同一入口 ⇒ 邊界 10c 對應案（a、f、g、h）偵出（變體仍寫出 baseline）。`venv/bin/python scripts/mutation_probe_static.py` 對兩支測試檔皆 rc 0。
- **防假綠**：Task 1.0 提交後、生產碼提交前：邊界 01、04、05、07、09、10d 紅（函式不存在或行為不符），邊界 02、03、06、08、10、10b、10c 綠；不得改寫 baseline 以換綠。
- 測試層級：整合（真實生成）＋單元（邊界 07、08）。可獨立 `pytest tests/feature_engineering/test_probewinsor.py`，不需 `run_api.py`。

## §R 回退
- Task 1.0 之凍結先行提交；Task 1.1、1.2、1.4 同一提交，可整體 revert；revert 後邊界 02、03、06、08 仍綠，01、04、05、07、09 回紅。

## §N N/A 登記與殘留
- mutation：不適用 N/A——本票命中 (a)，mutation 已列 §V。
- R1 V-6 型（12h 主＋1h、前處理關）完整生成與 `test_failopen_correctness.py` 之 `test_v6_*` 五重項 — `為何現在不做: blocked-by:TESTREG 第 3 批 Task 3.2（docs/TICKET_ORDER.md 第 5a 步；V-6 屬 TESTREG 逐檔判定與實跑範圍，單項約 97 分）`；觸發：TESTREG 第 3 批開工；登記處：`docs/TESTREG_SPEC.md` §N R9（本票收案時改指本票提交）。
- R2 前處理開啟時探測與公開 L6.5 各縮尾一次之重複計算 — `為何現在不做: user-ruling:2026-10-11 使用者裁定 FF 生成提速整個專案跑通後再回來優化`；偵察 r1 三方皆判非正確性問題（前處理開啟格修正前後逐位元同）；觸發：FF 生成提速票開工；登記處：`白話說明/還沒做的事.md`「FF 生成提速」列、`docs/TESTREG_SPEC.md` §N R8。
- R3 API 批次續跑對「無法自輸出路徑解析 run hash」之舊格式完成項仍保留、不核對身分（審查 r3 codex 主張改為重排）— `為何現在不做: blocked-by:FRAMEPATH 第 2 批處置 OP-116（tests/_golden/framepath/test_disposition.json；已凍結蓋章，綁 tests/api/test_run_lifecycle_api.py::test_resume_batch_keeps_legacy_completed_item 原文雜湊且全部斷言保留；本票反轉該契約即令 FRAMEPATH 第 2 批凍結驗收失敗，須 FRAMEPATH 先完成其處置）`；實際暴露：只限 run hash 路徑格式啟用前所建之 checkpoint；觸發：FRAMEPATH 第 2 批收批（刪 factory h5 舊格式）後，以 TESTREG 改寫收據將該契約改為重排；登記處：`白話說明/還沒做的事.md`、HANDOFF。
- 非殘留（記錄判定）：①「探測段內全無有限值之欄不觸發加倍」（`feature_factory.py:2648–2650`，FF-STAT v50）——修正後 D₀ 為設定所致延遲之上界（`estimate_max_warmup_bars`），此類只剩資料所致延遲（稀疏輸入、參考標的晚起）與死欄，公開晚到者仍記 `warmup_insufficient_history`；偵察 r1 無反例。②總開關關閉時 `config_hash` 仍含子開關（縮尾開／關兩 hash、輸出相同）——只致重算、不致錯值，不改。③`run_ic_first` 經 `generate_features` 走同一探測（`feature_factory.py:2846–2849`），由 Task 1.1 涵蓋。④API／批次只透傳設定（偵察 r1 codex 讀碼），由 Task 1.1 涵蓋。⑤凍結來源之證明邊界：Task 1.0 之錨點（契約所記改前生產 .py 身分、本票符號清單、kline 權威雜湊、凍結輸入之已提交版本、執行環境）涵蓋影響 baseline 內容之全部來源；刻意構造之規避（例：同時竄改並提交契約錨點與生產碼、或同步竄改 failopen 基準所記之 kline 雜湊）屬蓄意等價，不再加機制（user-ruling:2026-09-11 停在無法收斂處，同 FRAMEPATH §N A15、TESTREG §N R6）。
