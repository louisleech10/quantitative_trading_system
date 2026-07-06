# IC 修法 Phase 0 — SPEC

> 來源 PLAN/診斷：`handoffs/20260624-ic-PHASE0-DEFINITION.md` + `20260624-ic-grouped-crash-perf-ANALYSIS.md` ｜ 日期：2026-06-25
> Manifest：`handoffs/20260625-ic-PHASE0-MANIFEST.md` ｜ 白話 brief：`20260625-ic-PHASE0-BRIEF.md` ｜ 對應 TODO：`docs/IC_PHASE0_TODO.md`（待生成）

## §RISK 風險分級（gate 讀此決定要求強度）
- RISK-HIT: b,d
- **大小**：**大**（接 CLAUDE.md 任務分派規則：多 epic + 命中高風險原則）。 `[M-1]`
- **命中高風險原則**：
  - **(b) 跨模組/共用路徑**：改 `momentum/Analysis/ic_engine.py`、`ic_filter_orchestrator.py`、`ic_config_schema.py`、`api/services/ic_analysis_service.py`、frontend hooks/store——多下游消費者。
  - **(d) ML/回測正確性**：grouped IC 時間軸（秒/毫秒）、by_volatility 契約、feature universe 篩選——直接影響因子有效性判讀。
- 命中 (b)(d) → **§G Golden 必填、adversarial review 必跑**（gate `--adversarial`，雙家族）。 `[M-1]`

## §A 假設與待使用者確認（事故：拿推論代替問人）

### 已驗證事實（每項標 fact-verified=實跑 / code-verified=讀碼 / assumed） `[M-2]`
1. **IC-CRASH 契約不一致**〔code-verified〕：`compute_grouped_ic(self, ..., config: dict)`（ic_engine.py:371）內部 `config.get("method")`（:377）為 dict API。**唯一 caller** `ic_filter_orchestrator.py:1139` 傳 `config.ic_calculation.grouped_analysis`（型別 pydantic `GroupedConfig`，schema:76）。驗證：`grep -rn compute_grouped_ic momentum/ api/` → 僅 orchestrator:1134 一處 caller（排除 test）。pydantic 無 `.get` → AttributeError。觸發條件 `config.report.include_regime_analysis=True`（:1133）。
   - FACT-RECEIPT: [2026-07-06 復驗] `grep -rn compute_grouped_ic momentum/ api/ | grep -v test` → 唯一 caller `ic_filter_orchestrator.py:1668`（def 於 `ic_engine.py:380`）。註：caller 現傳 `config.ic_calculation.grouped_analysis.model_dump()`（dict，orchestrator:1673），AttributeError 已於 commit 11507f5 修復；本項為修法前診斷，保留為歷史。
2. **IC-TIMEAXIS（真 bug=崩潰，非靜默 1970）**〔fact-verified〕：`read_klines`（kline_storage.py:1084,1107）回 **RangeIndex** + `timestamp` int64 秒級欄（實跑 BTCUSDT/1h：`timestamp[0]=1704067200`，`unit=s`=2024、`unit=ms`=1970）。`_get_time_index`（:1024-1025）對 **Series** 呼叫 `pd.to_datetime(values, unit="ms")` → **回傳 Series（非 DatetimeIndex）**。`_iter_time_groups`（:1011）`time_index.to_series()` → **`AttributeError: 'Series' object has no attribute 'to_series'`**（Claude 親跑確認）。即修完 C-1 後 grouped by_year/quarter 在真實 kline 路徑**先崩潰**，1970 錯軸只是次要。**修法須同時 (i) 回傳對齊 raw_data.index 的 DatetimeIndex (ii) 修單位 s/ms**。
   - FACT-RECEIPT: [2026-07-06 復驗] `tests/fixtures/ic_phase0/kline_seconds.csv` timestamp[0]=1704067200 dtype=int64；`pd.to_datetime(ts,unit='s')`→2024-01-01、`unit='ms'`→1970-01-20（單位事實仍成立）。`ICEngine._get_time_index` 現簽名 `-> Optional[pd.DatetimeIndex]`（崩潰已於 commit 11507f5 修復）；本項為修法前診斷，保留為歷史。
3. **IC-BYVOL 契約漂移**〔code-verified〕：`GroupedConfig.by_volatility` 預設 `True`（schema:80），但 `compute_grouped_ic` 只有 `by_year`/`by_quarter`/`by_regime` 分支（ic_engine.py:383-400），**無 by_volatility** → 開了靜默忽略。驗證：`grep by_volatility ic_engine.py` → 0 處理邏輯。
4. **IC-FEATURE-GUARD 幽靈（去 config_override 非 metadata）**〔fact-verified〕：`api/models/ic_models.py:8` `FeatureFilterConfig`（include/exclude/pattern/categories/data_sources/families/max_features）→ service.py:967-970 `_build_config_override` 用 `_deep_merge` 放進 **config override**（非 metadata）→ `ICConfig.model_validate` **靜默丟棄**未知頂層鍵（Claude 親跑 `ICConfig.model_validate({'feature_filter':...})` → `has feature_filter attr False`；無 `extra='forbid'`）→ momentum 零消費。實見 run 全量 45,421 特徵。**前端預設 `max_features:30`（icAnalysisStore.ts:187），落地若不設防會把所有 analyze 靜默截成 30**。
5. **IC-DECAY-LOG 熱迴圈**〔code-verified〕：`_fit_exponential_decay`（ic_engine.py:944）`logger.warning("Decay fit quality low...")` 在 per-feature 路徑（compute_ic_decay:331 對 columns 迴圈，:349 呼叫）；單次 run 14,090 條。**修法所需 r2/fit_warning_reason 已在回傳 dict**（:949-）。
6. **IC-UX-ERR event loop 阻塞**〔assumed/委員會來源〕：cursor 揪 service.py:209-216 主 analyze（longitudinal）同步阻塞、cross-sectional `analyze_cross_sectional`（:154-159）同樣同步；前端 useICAnalysis.ts:88-117 onclose 無限重連、failed 不 setError。**未實跑 heartbeat 證據；實作端須先讀碼確認 to_thread 對應點再改**。
   - FACT-RECEIPT: [2026-07-06 復驗] 碼位 read-verified 仍在：`ic_filter_orchestrator.analyze_cross_sectional`（:528）、`useICAnalysis.ts` onclose/setError（:147/:169）。本項為〔assumed〕：event loop 阻塞屬 runtime 行為，未實跑 heartbeat，僅碼位存在經 grep 確認，blocking 假設本身未證。

### 待使用者確認（未確認前不得實作相關 Task）→ 已由委員會收斂 `[M-3]`
- **IC-BYVOL 修法**：使用者 2026-06-25 授權「照委員會收斂結果執行」→ **雙家族 adversarial（GPT-5.x + Composer）獨立一致判 (b) fail-closed + schema 預設 `by_volatility=False` + migration**（reconcile：`handoffs/20260625-ic-PHASE0-ADVERSARIAL-RECONCILE.md`）。**已收斂，Task 2.3 寫死單一路徑**。 `[B-1]`

### 已確認結果
- 已確認：起點=Phase 0、walk-forward 復用 ML 孤島、不碰串流/train-test/case-control（使用者 2026-06-24 baked-in）。
- IC-BYVOL 決策權委派委員會（使用者 2026-06-25）。

## §C 約束（引用 + 只列本任務相關） `[M-4]`
- 解耦 7 條：`grep -r "from api\." momentum/`→0；服務不互 import；momentum 改動經 factories/protocols。
- 不可違反原則：**不靜默截斷特徵**（feature_filter **預設不截斷**、僅顯式套用才生效、metadata 可審計 truncation_mode）、不弱化 NaN·inf gate、**不改 IC 數值計算語義**（僅修錯的 timestamp 軸 T、by_volatility 契約 B；max_features 截斷會改 feature universe → 須穩定排序+可審計+非預設）。
- 本任務共用路徑/下游：`ic_engine` 被 orchestrator + deep analysis 消費；`ICConfig` 被多處建構；前端 store/hook 跨元件。改 `_get_time_index` 影響所有 grouped 分組（year/quarter/regime 皆用）。

## §G Golden / Baseline（高風險必填） `[M-5]`
- **凍結時機 / reference（分階段，因 grouped 在 C 修後仍可能 T 崩潰）**：動工前用 `BTCUSDT 1h`（真實 `kline_cache.h5`）+ 固定 ICConfig（regime on、by_volatility=False）。staged artifact：`tests/fixtures/ic_phase0/baseline_grouped_post_timeaxis.json`（修 C+T 後正確基準；修 T 前 grouped 會 crash 無鍵，故不凍錯誤基準）、`baseline_decay.json`、`baseline_feature_filter.json`。
- **baseline 內容**（須抓值重排/局部錯位/index 對齊錯）：
  - **grouped_ic（C/T/B）**：修 C+T 後斷言 by_year 鍵=正確年份（2024…）。**參考實作寫死**：測試內以 `pd.to_datetime(timestamp, unit='s').year` 獨立 groupby 重算 per-group IC mean，`np.isclose` 比對；**並記每 group 的 row index mask hash + group sizes**（抓 index 對齊錯/同值重排，非只年份鍵）。
  - **feature_filter（F）**：篩選前後 features 名稱集合 sha256 + 數量；metadata.feature_count_original/filtered/applied/truncation_mode。顯式 max_features=N 時斷言 filtered==N 且為 `sorted` 確定性子集（同 input 兩次跑 sha256 相同）。
  - **decay（D）**：改 log 前後 `compute_ic_decay` 回傳 dict 逐 feature 的 r2/half_life/decay_rate **結構化 float 比對**（非 byte）：鍵集合 exact + finite floats `np.isclose(atol=1e-6,rtol=1e-4)` + NaN-mask exact。
- **通過條件（可證偽）**：feature 值 nan_ratio exact、mean/std/value `abs≤1e-6 或 rel≤1e-4`（float32 放寬）；超出列該 feature + 實際 diff = FAIL。grouped fixture 用 **RangeIndex+秒級 timestamp 欄**（禁 DatetimeIndex/ms 假綠）。

## §P Phase 與依賴 `[M-7]`（不可做集中於此 + §N）

### Phase 1 — 止血崩潰（依賴：無，最優先）
**Task 1.1 — IC-CRASH 修契約** `[C-1]` `[C-2]`
- 目標：caller 傳 dict 給 dict-API。檔案：`ic_filter_orchestrator.py:1139`。既有 caller/影響面：**僅此一處**（已 grep 驗）→ 不改 engine 簽名。
- 改法：`config.ic_calculation.grouped_analysis` → `config.ic_calculation.grouped_analysis.model_dump()`。
- **驗證**：真 config + `include_regime_analysis=True` 跑 orchestrator，不拋 `AttributeError`，回傳 dict 含 `grouped_ic` 非 None。`pytest tests/.../test_ic_grouped*.py`。
- **邊界**：grouped_analysis 全 False（無任何分組開）→ 回空 dict 不崩；regime off → grouped_ic 為 None（不進分支）。
- 不可做：不改 compute_grouped_ic 簽名（A2）、不加 isinstance band-aid（A3）。

**Task 1.2 — IC-CRASH 真路徑回歸測試** `[C-3]`
- 目標：取代 SimpleNamespace+dict 假綠。檔案：新增/改 `tests/.../test_ic_crash_real_config.py`；**點名取代/平行** `tests/momentum/test_ic_filter_orchestrator.py:535-549`（`test_stage4_ic_calculation_with_kline_reader` 用 SimpleNamespace+dict `grouped_analysis`，不重現 pydantic AttributeError）。
- 改法：用真 `ICConfig`（pydantic，regime on）+ 小真實 features/label/raw_data 打 orchestrator grouped 路徑。
- **驗證（TDD 兩 commit）**：`pytest` 測試在**僅加測試 commit 時 fail（重現 `AttributeError: 'GroupedConfig' object has no attribute 'get'`）→ 修 1.1 commit 後 pass**；diff 確認 :535-549 舊繞過測試移除或標記。
- **邊界**：raw_data=None → 不進 grouped 分支不崩。

### Phase 2 — 正確性硬閘（依賴：Phase 1 修崩潰後路徑可達）
**Task 2.1 — IC-TIMEAXIS 回 DatetimeIndex + 單位實測 + fail-closed** `[T-1]` `[T-2]`
- 目標：numeric timestamp 修「回傳 Series 導致 `_iter_time_groups` 崩潰」**且**自判秒/毫秒、異常 fail-closed。檔案：`ic_engine.py:_get_time_index`（:1018-1027）。影響面：所有 grouped 分組（by_year/by_quarter 經 `_iter_time_groups`）。
- 改法：numeric 分支 **必須回 `pd.DatetimeIndex`**（如 `pd.DatetimeIndex(pd.to_datetime(values.to_numpy(), unit=unit))`，非對 Series 呼叫），且 index 與 raw_data 對齊；單位依量級判（秒級 ~1.7e9、毫秒 ~1.7e12：`>=1e12` 視 ms、`>=1e15` 非法 raise、否則 s）；解出後 sanity：年份 <1990 或 >今年+1 → `raise ValueError`（明確訊息）。
- **驗證**：`pytest` fixture RangeIndex+`timestamp=1704067200`（秒）→ `_get_time_index` 回 `pd.DatetimeIndex` 且 `_iter_time_groups('year')` 不拋錯、year==2024；構造 1970/2100/1e16 → `raise`。
- **邊界**：已是 DatetimeIndex → 原樣返回；無時間欄 → 返回 None（不崩）；NaN timestamp → 明確處理。
- 不可做：不寫死單位、不回傳 Series、不靜默吞錯軸。

**Task 2.2 — IC-TIMEAXIS kline-shape byte-faithful 回歸** `[T-3]`
- 目標：fixture 重現真實 kline 形狀（**RangeIndex + 秒級 timestamp 欄，禁 DatetimeIndex index**，否則 s/ms bug 假綠）。檔案：`tests/fixtures/ic_phase0/` + 測試。
- **驗證（TDD 兩 commit）**：`pytest` fixture `reset_index()` + `timestamp=[1704067200,...]`（秒，**禁 ms 構造**）；**僅加測試 commit 時重現 `AttributeError`（'Series' no to_series）→ 修 2.1 後 by_year 鍵==2024 pass**。
- **邊界**：跨年資料 → 多個正確年份鍵。

**Task 2.3 — IC-BYVOL fail-closed（委員會收斂：(b) + 預設改 False）** `[B-1]` `[B-2]`
- 目標：by_volatility 不靜默忽略。檔案：`ic_engine.py:compute_grouped_ic` + `ic_config_schema.py:80`。**雙家族收斂：寫死 (b) fail-closed**。
- 改法：(1) `GroupedConfig.by_volatility` 預設 **`True`→`False`**（+ migration note：既有預設 grouped run 不再因未顯式要求 volatility 而 raise）；(2) `compute_grouped_ic` 對 `config.get("by_volatility")` 為 True → `raise NotImplementedError`（訊息：「by_volatility grouped 於 Phase 0 不支援，留待後 Phase」）。
- **驗證**：`pytest` (i) 預設 config（by_volatility=False）跑 grouped 不 raise、有 by_year/by_regime 結果；(ii) 顯式 `by_volatility=True` → `raise` 且訊息含「not supported」。
- **邊界**：by_volatility=False（新預設）→ 不觸發。
- 不可做：不靜默 pass、不假裝實作分組、不保留預設 True。

### Phase 3 — feature_filter 落地（依賴：無，可平行；但碰 schema 需小心 caller）
**Task 3.1 — ICConfig 加 feature_filter 欄（修靜默丟棄）** `[F-1]`
- 目標：momentum 側有承接欄位，且 config_override 不再丟棄。檔案：`ic_config_schema.py` + `load_ic_config` override 套用處。影響面：ICConfig 建構處。
- 改法：加 `feature_filter: Optional[...]` 對應 API `FeatureFilterConfig` 語義；確認 `load_ic_config(api_override 含 feature_filter)` 經 model_validate **不被丟棄**。
- **驗證**：`pytest` 斷言 `load_ic_config({'feature_filter':{'max_features':30}})` 後 `config.feature_filter is not None` 且欄位值相等（**現況親驗 `has feature_filter False`，須轉綠**）。**邊界**：None → ICConfig.feature_filter is None，向後相容。

**Task 3.2 — orchestrator 真消費 feature_filter + 穩定排序（預設不截斷）** `[F-2]` `[F-3]`
- 目標：篩選**僅在顯式套用時**真生效，預設全量不截斷。檔案：`ic_filter_orchestrator.py`（features_df 載入後、IC 計算前）。
- 改法：依 include/exclude/pattern/categories/data_sources/families 篩 columns；**max_features 截斷排序用 `sorted(remaining_columns)`**（穩定可移植，after include/exclude）；**禁** HDF5 欄位順序（兩次 materialization 不穩）、**禁** label 衍生 IC 排序（look-ahead）；不得暗示 top/best（命名/呈現為 deterministic cap）。**前端預設 `max_features` 改 undefined（icAnalysisStore.ts:187），後端僅在顯式套用才截斷**。
- **驗證**：`pytest` (i) 無顯式 filter → 全量（不截斷）；(ii) 顯式 max_features=30 於 45k → 算 30，`sorted` 子集，同 input 兩次 sha256 相同。**邊界**：篩後=0 → 明確 error 不靜默；max_features>總數 → 全留不報錯。
- 不可做：不靜默截斷、不用不穩定/look-ahead 排序、不預設截斷。

**Task 3.3 — metadata 審計（truncation_mode）+ 大 run 警示** `[F-4]` `[F-5]`
- 目標：可審計、不靜默。檔案：orchestrator + metadata 組裝處。
- 改法：metadata 記 `feature_count_original` / `feature_count_filtered` / `feature_filter_applied` / **`truncation_mode: preview|none`** / `truncation_order: sorted_column_name`；總特徵 > **5000**（寫死）→ `logger.warning` 一行（**僅警示不阻擋**）。
- **驗證**：`pytest` 斷言 `metadata["feature_count_original"]`/`["feature_count_filtered"]`/`["feature_filter_applied"]`/`["truncation_mode"]` 存在且 `filtered <= original`。**邊界**：無篩選 → original==filtered、applied=False、truncation_mode=none。

**Task 3.4 — preview_limit（確認幽靈欄→併入 F-3 truncation_mode）** `[F-6]`
- 目標：澄清範圍。檔案：無（preview_limit grep api/momentum/frontend 全 0，**Claude 親驗不存在**）。
- 改法：**移出實作範圍**——無欄位可改名；預覽 vs 正式篩選語義改由 F-3 `metadata.truncation_mode` 表達。
- **驗證**：`grep -rn preview_limit api/ momentum/ frontend/src` → 0（確認無遺留）。**邊界**：N/A。
- 不可做：不為幽靈欄新建 alias/schema。

**Task 3.5 — feature_filter 回歸測試** `[F-7]`
- **驗證**：`pytest` 斷言落地前後 `metadata` 計數正確；篩選真生效（`assert` 算的 feature 數==篩後數，非全量）。

### Phase 4 — 效能/體感（依賴：無）
**Task 4.1 — IC-DECAY-LOG 聚合** `[D-1]` `[D-2]`
- 目標：熱迴圈零 log，結尾一行。檔案：`ic_engine.py:_fit_exponential_decay`（:944 移除 warning）+ `compute_ic_decay`（:331 結尾聚合）。
- 改法：`_fit_exponential_decay` 仍回傳 r2/fit_warning_reason（不變），移除其內 logger.warning；compute_ic_decay 迴圈收集 reason，結尾 `logger.info("Decay: N/total 特徵 R2<0.5 ...")` 一行。
- **驗證**：`pytest` 跑多特徵 decay，熱迴圈零 warning；結尾恰一行摘要；**回傳 dict 逐 feature 值結構化 float 比對不變**（Golden D：鍵集合相等 + finite floats `np.isclose(atol=1e-6,rtol=1e-4)` + NaN-mask exact + scalar typed；**禁純 json byte compare**）。
- **邊界**：全部 fit 成功 → 摘要顯示 0 低品質；features=0 → 不崩。
- 不可做：不改 decay 數值/不做 R2 early-skip。

**Task 4.2 — IC-DECAY-LOG 回歸測試** `[D-3]`
- **驗證**：`pytest` caplog `assert` 熱迴圈 per-feature warning 數==0 + 結尾摘要恰一行。

**Task 4.3 — IC-UX-ERR 後端 to_thread（兩條主計算路徑）** `[U-1]`
- 目標：解 event loop 阻塞。檔案：`api/services/ic_analysis_service.py` **longitudinal `analyze`（:209-216）+ cross-sectional `analyze_cross_sectional`（:154-159）**（codex 揪：兩條都同步）。
- 改法：兩條主計算改 `await asyncio.to_thread(...)`（比照 deep analysis）。**先讀碼確認對應點**。
- **驗證（可測）**：`pytest` mock 慢 analyze + `asyncio.wait_for`/`assert` 背景跑時主 loop 仍能完成 N 次 `await asyncio.sleep(0)`（heartbeat callback 被調度）。**邊界**：analyze 拋錯 → 錯誤經 WS 傳遞非吞掉。

**Task 4.4 — IC-UX-ERR 前端錯誤處理 + poll 狀態機** `[U-2]` `[U-3]` `[U-4]` `[U-5]`
- 目標：真錯誤 + 有限重連 + poll fallback。檔案：`frontend/.../useICAnalysis.ts`（:88-117 onclose 無限重連、:194-212 已有 fetchTaskStatus/fetchResult）、`icAnalysisStore.ts`。
- 改法：failed → `setError(status.error 真訊息)`；**狀態機：onclose retry≤3 → 改 poll `/task/{id}` 直到 terminal（completed/failed）→ `fetchResult`；terminal 後停輪詢**；不與 WS 雙寫狀態。
- **驗證**：`vitest` + `npm run build` PASS；模擬 failed 顯真訊息（`expect` setError 帶 status.error）；模擬 WS 斷 → poll 接管到 terminal。**邊界**：連續斷線 → retry 3 次後 poll，非無限轉圈。

## §V 驗證策略與邊界測試目錄
- 測試層級：單元（_get_time_index 單位、decay 聚合）/ 整合（orchestrator grouped 真 config）/ Golden 對照（decay 值不變、feature 篩選確定性）/ 邊界。皆可獨立 `pytest tests/...` 跑，不需 run_api.py。
- **防假綠**：diff 既有測試斷言，不得放寬/刪除換綠燈。**C-3/T-3 走 TDD 兩 commit**：同一 PR 內須可展示「僅加測試 commit 紅（重現 bug）→ 修 code commit 綠」；bug 重現腳本/fixture 入 `tests/fixtures/ic_phase0/`。
- **邊界目錄**（本任務適用打勾）：✅空DF（features=0/篩後0）✅全NaN列（decay）✅std=0（decay low_variance）✅重複·亂序/異常 timestamp（1970/2100 fail-closed）✅大尺度（45k 特徵篩選）✅並發/重連（前端 WS）。

## §R 回退 `[M-6]`
- 每 epic（C/T/B/F/D/U）獨立 commit，可單獨 revert。
- 高風險改動（T 時間軸、F 篩選、B 預設改 False）Golden FAIL → 不 merge。
- B by_volatility 預設改 False 附 migration note，回退單 commit。

## §N N/A 登記
- 無必填段省略（§RISK/§A/§C/§G/§P/§V/§R 全填）。
- **明確不做**（接 `[M-7]`）：串流重寫（Phase 3 epic）、train/test split（Phase 1 epic）、case-control（Phase 2 epic）、decay R2 early-skip（改語義）、decay/grouped 向量化（IC-PERF-DEEP，需獨立 golden）、不在舊 materialized 補大尺度。
- **IC task resume/retry 留後 Phase，本 Phase 不實作**（IC 長 run 失敗仍全量重算可接受，不阻 Phase 0 派工；agent 不得自行加 checkpoint）。
- **by_volatility 分組實作**留後 Phase（Phase 0 僅 fail-closed）。
