# FF 深稽 P0-FF-1/2/4 + BUG-1/BUG-2 — SPEC

> 來源診斷:`handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md`(codex+composer 雙戳記 APPROVED sha256:fa597372)、`...-CLAUDE-LEG.md`、`...-ADV-{codex,composer}.md`
> 日期:2026-06-27　|　對應 TODO:`docs/FF_DEEPAUDIT_P0_TODO.md`(待 TODO_GENERATION_PROMPT 生成)
> 實作者=Composer 2.5;code review=Codex GPT-5.5([[feedback-executor-override-composer-impl]])。測試章程見 §G/§V + `docs/TEST_DESIGN_CHARTER.md`。

## §RISK 風險分級
- **大小**:大。
- **命中高風險原則**:**(a)** 數值/資料品質(改 BETA/CORREL 特徵語義、atomic 公式正確性)、**(b)** 跨模組共用路徑(`talib_wrapper` 為所有 atomic 上游、`generate_features` 全鏈)、**(d)** ML/特徵正確性(GIGO 單點 + 因果無洩漏)。
- 命中 (a)(d) → **§G Golden 必填、SPEC/TODO 雙家族 adversarial 必跑**;**BUG-1/BUG-2 改特徵集 → 三方數據簽核**(Claude+Codex+Composer 皆表「資料正確」才過,用真實 kline)。

## §A 假設與待使用者確認
- **已驗證事實**(附驗證方式 grep/實跑 pytest):
  - TA-Lib `abstract.Function("BETA").input_names = {price0:high, price1:low}`;wrapper 現餵 (close,volume)(兩家真 run:vs high/low maxdiff BETA 7.33 / CORREL 1.95)。
  - 真實 kline = `data_cache/feature_klines/kline_cache.h5`(10 symbol × {1h,4h,12h},OHLCV+taker/quote/trades;三方數據簽核鐵律指定)。
  - `requires_kline` marker 不存在(grep 0);現 10+ 測試缺 kline `pytest.skip` 靜默綠。
  - `test_atomic_indicators.py` 只覆 trend/momentum/volatility/volume/pattern;cycle/statistics/custom 零專測。
  - 鏈入口 `momentum/FeatureEngineering/feature_factory.py::generate_features`(line 237)。warmup 估算 `warmup_window.py::estimate_max_warmup_bars`(實作端須核對真實函式簽名再用)。
- **待使用者確認**:無(BUG-2 簡化變體的「保留並標 variant」走三方簽核技術決策,非使用者意圖)。
- **已確認結果**:**BUG-1 修法 = 兩者都要**(使用者 2026-06-27):補真正標準 BETA/CORREL(high,low)+ 保留改名(**`Beta_CloseVolume`/`Correl_CloseVolume`**,對齊既有 underscore 慣例)的價量相關版 + metadata 標非標準。
- **kline facts 待補實測**(實作端 Task 0.2 凍結 manifest 時補):h5 path/symbols/TFs/row_count/sha256 實跑摘要寫入 DATA_MANIFEST;在此之前「10×3 形狀」視為依治理要求,非已 fact-verified。

## §C 約束
- 解耦 7 條(`momentum/` 不 import `api/`;測試可 standalone pytest)。不弱化 NaN/inf gate;不擅改輸出大小/數值行為。
- 本任務共用路徑:`momentum/FeatureEngineering/atomic/talib_wrapper.py`(全 atomic 上游,改 input map 影響一片)、`momentum/FeatureEngineering/atomic/volume_indicators.py` 等手刻、`momentum/FeatureEngineering/feature_factory.py::generate_features` 全鏈。**BUG-1 改欄名/新增欄 → 影響下游所有以舊欄名消費者(IC/ML/feature_storage metadata)**:實作端須列同步點,不得只改 wrapper。

## §G Golden / Baseline(高風險必填)
- **凍結時機(兩階段,因 BUG-1/2 必改特徵)**:**v0** 在 B0 後、B1 BUG 修前凍結;**v1** 在 B1 後凍結 + 新舊差異表。固定 symbol+TF(BTCUSDT/12h + ETHUSDT/1h,≥500 列)跑 `generate_features` production preset,存 `tests/_golden/ff_deepaudit/`(路徑寫死、列入 DATA_MANIFEST)。
- **baseline 內容**:feature 名稱集合 sha256 + 數量/schema + 每 feature mean/std/nan_ratio + **全欄 per-column value hash + dtype + index hash + NaN mask hash**(非抽樣——抽樣會漏單列漂移)。
- **通過條件(可證偽)**:nan_ratio exact;未受影響欄 **value hash exact 不變**;mean/std 容差僅用於人讀 diff。超出列出 feature+實際 diff=FAIL。
- **Affected Column Closure(BUG-1/BUG-2 受影響範圍演算法,防旁路污染)**:
  (1) 直接改名/改 source 的 L1 欄(`*_statistics_BETA/CORREL_*`、新 `hl_statistics_BETA_*`、`Beta_CloseVolume`);
  (2) 由 `tests/_golden/batch2d/provenance.json` provenance 圖可追溯至 (1) 的所有 L2–L7 衍生欄 → 列入受影響,更新 golden+差異表;
  (3) 其餘欄 value hash **exact 不變**。受影響欄走「明確記錄新舊差異表 + **三方數據簽核**」非「行為不變」。

## §P Phase 與依賴

### Phase 0 — 治理地基(依賴:無)
**Task 0.1 — `requires_kline` marker + 雙 job**
- 目標:correctness 測試缺指定 kline → FAIL 非 skip。檔案:`pytest.ini`(註冊 marker)、`tests/conftest.py`(fixture/hook)。既有影響面:現用 `pytest.skip("missing kline")` 的測試逐一評估是否改掛 marker。
- 改法:註冊 `requires_kline` marker;提供 `requires_kline_data(symbol, tf)` fixture,缺檔 `pytest.fail(...)` 非 skip。PR job `-m "not requires_kline"` smoke;nightly correctness 不加排除。
- **驗證(可證偽)**:暫時移走某 kline → marker 測試 FAIL(非 skip);`pytest -m "not requires_kline"` 該測試不收集。指令:`pytest tests/feature_engineering/ -m requires_kline`。
- **邊界**:kline 檔存在但列數 < 最小值 → FAIL;marker 未掛的舊測試行為不變。
- 不可做:不把現有正當「無資料環境」開發流程改成硬性全 FAIL——只 correctness 類掛 marker,逃生口 `-m "not requires_kline"` 保留。

**Task 0.2 — `tests/fixtures/DATA_MANIFEST.json` + 校驗**
- 目標:列 correctness 依賴的 10 symbol × 3 TF(symbol,TF,最少列數,sha256/指紋)。檔案:新建 manifest + `tests/fixtures/data_manifest.py` 校驗器。
- 改法:啟動校驗 manifest 與實際 kline 指紋;漂移/缺項 → FAIL。
- **驗證**:改一筆 sha → 校驗 FAIL;缺 symbol×TF → FAIL;row_count below min → FAIL(C4-3 mutation 三種)。
- **邊界**:manifest 多列實際缺的 symbol → FAIL 並明示哪筆。
- 不可做:不把 kline 二進位納入 repo(gitignore);只存指紋。

### Phase 1 — P0-FF-1 atomic differential + BUG-1/BUG-2(依賴:Phase 0 marker)
**Task 1.0 — correctness mode 機制(B1 降級修法落地;Task 1.1 前置)**
- 目標:現 8 個 `momentum/FeatureEngineering/atomic/*_indicators.py` 皆 `except Exception`→`logger.warning` 繼續(fail-open),無 correctness 分支。須**定義機制**讓 correctness 測試下已登錄指標計算失敗 = raise 非 warning。檔案:8 個 `*_indicators.py` 的 `compute_all`、新增開關(建議 `FactoryConfig.fail_open_indicators: bool=True` 或 env `FF_CORRECTNESS_MODE`)。
- 改法:統一 helper 包 try/except;correctness mode=on 時 re-raise。列 8 engine 同步點(statistics/trend/momentum/volatility/volume/cycle/pattern/micro/tail——以實際檔案為準)。
- **驗證(可證偽)**:correctness mode 下刪 MFI from `_INPUT_TYPE_MAP` → `compute_all` raise(`pytest tests/feature_engineering/atomic/test_correctness_mode.py` 斷言 `pytest.raises`),非 warning。
- **邊界**:correctness mode=off 時行為不變(現 warning 流程);未登錄指標仍 skip。
- 不可做:不把 production 預設改成硬 fail(預設 fail-open 維持,只 correctness 測試開 mode)。

**Task 1.1 — C1-2 prepare_inputs equivalence + registry 完整性**
- 目標:取代不可實作的「⊆ input_names」。檔案:新建 `tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py` + `TALIB_INPUT_SEMANTICS` 表(indicator→input_type→df 欄位 ordered)。
- 改法:對 `momentum/FeatureEngineering/atomic/talib_wrapper.py` registry 每指標,`_prepare_inputs` 產出 ndarray 與依表直呼 `talib.FUNC(*arrays)` byte 相等。
- **驗證**:mutation 從 `talib_wrapper.py::_INPUT_TYPE_MAP` 刪 ATR → `pytest tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py` 必 FAIL(附 fail 摘要)。
- **邊界**:**`computed_in_adapter=True` 的 price_transform(AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE)`compute()` 回空 DF → 寫死「排除 C1-2 byte 比對」**(L1 不跑 talib);MAVP special periods allowlist。
- 不可做:不用 talib abstract 的 `price/price0` 名硬比 high/low(那是 71/132 假陽來源)。

**Task 1.2 — C1-1 wrapper vs talib differential(含 BUG-1 雙 oracle)**
- 目標:抽樣 differential 驗 wrapper source/param/輸出對位。檔案:`tests/feature_engineering/atomic/test_atomic_differential.py`。
- 改法:抽樣**必含** RSI/ATR/EMA/MACD/STOCH/BOP/OBV/AD/ADOSC + BETA/CORREL(雙 oracle)+ **price_transform AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE(adapter policy:computed_in_adapter 走 adapter oracle 或明示排除)** + cycle/statistics/custom 各≥1。比對 input tuple/params/output names/NaN mask/index,`assert_allclose`。
- **驗證(可證偽)**:mutation 改 wrapper source(close→open)/改一 param → `pytest tests/feature_engineering/atomic/test_atomic_differential.py` 必 FAIL。
- **邊界**:全 NaN 輸入欄;不足 timeperiod 的暖機列 NaN 對齊。
- 不可做:不拿被測 wrapper 自身當 oracle(須直呼 talib)。

**Task 1.3 — BUG-1 修(兩者都要)**
- 目標:`momentum/FeatureEngineering/atomic/talib_wrapper.py` BETA/CORREL 改 `hl`(high,low)= 真正標準;**另**新增改名價量相關欄(`Beta_CloseVolume`/`Correl_CloseVolume`)+ metadata 標非標準。
- 改法:**先產 Consumer Sync Checklist**(`rg 'statistics_BETA|statistics_CORREL|_BETA_|_CORREL_' tests/ api/ momentum/` 逐項分類處置),**至少含**:
  - `momentum/FeatureEngineering/utils/adf_safe_skip.py:55`(`_CORREL_` whitelist、L16 BETA 排除)→ BUG-1 後標準 BETA(high,low) 統計性質變,**重審 whitelist + 更新註解 + 重跑 `tests/feature_engineering/test_adf_safe_skip.py`**
  - `tests/feature_engineering/test_adf_safe_skip.py:48,164,353`(硬編舊欄名)→ migration
  - `tests/_golden/failopen/baseline.json`、`tests/_golden/batch2d/provenance.json`(L2–L7 衍生鍵)→ 走 §G v1 差異表
  - `api/services/feature_factory_service.py:3804`(UI 顯示名)→ 對應新欄/variant
  - `momentum/Analysis/` IC:無硬編,但已選 `statistics_BETA` 的 IC study 數值全變 → **IC 語義漂移 smoke**(固定 1 symbol×TF×horizon,BUG 修前後 IC 符號/量級寫入差異表;要求明示變更+三方簽,非不變)
- **驗證**:標準欄 == `talib.BETA(high,low)`;價量欄 == 舊 (close,volume) 值且 metadata `variant`/非標準標記存在。**三方數據簽核**:新舊特徵差異表三方皆確認語義正確。
- **邊界**:下游硬編舊欄名 → migration 或別名,不得靜默掉欄;ADF whitelist 未重審不得 merge。
- 不可做:不在未產 Consumer Sync Checklist 下只改 wrapper(會讓下游消費錯/掉欄/golden 假綠)。

**Task 1.4 — BUG-2 修 + C1-3 oracle 三級**
- 目標:手刻指標(Klinger/ForceIndex/EOM + entropy/tail/micro 抽樣)建獨立 reference,標 oracle class。檔案:`tests/references/*_ref.py`(不得 import 被測模組)、`momentum/FeatureEngineering/atomic/volume_indicators.py`(+ `entropy_indicators.py`/`tail_risk_indicators.py`/`microstructure_indicators.py` 同目錄)metadata 加 `variant`。
- 改法:oracle 三級(EXACT differential / 文獻獨立 reference / 簡化變體 golden-lock+metadata variant);Klinger/ForceIndex/EOM 標 `variant=simplified` + 欄名/描述明示。**三步防自指(時序)**:(a) 先產文獻 reference 差異表(可 fail)→(b) 三方簽 off →(c) 才寫 golden JSON + metadata `variant=simplified` 綁簽核 commit hash。
- **驗證**:mutation EOM `*`→`/` → `pytest tests/feature_engineering/atomic/test_handcoded_reference.py` 必 FAIL;簡化變體 golden 來自步驟(b)三方簽 off,**非**用現實作輸出 freeze(自指)。
- **邊界**:無外部 oracle 者不得宣稱「公式正確」,只 golden-lock。
- 不可做:不拿現實作輸出當 canonical oracle freeze(自指,會鎖死錯公式)。

### Phase 2 — P0-FF-2 全鏈截斷 MR(依賴:Phase 0 marker;與 Phase 1 獨立可並行)
**Task 2.1 — C2-1 全鏈 bar 級截斷不變量**
- 目標:真 kline 跑 `generate_features()`,截斷尾端 k bars,截斷點前(扣 warmup)feature matrix+NaN mask+columns 不變。檔案:`tests/feature_engineering/test_ff_fullchain_truncation_mr.py`。
- 改法:**warmup = config-driven `estimate_max_warmup_bars(config, primary_tf, training_tfs)`,禁 data-dependent 首全填列**。四段斷言:① columns gate `assert list(full.columns)==list(trunc.columns)`(先於值);② values gate 對齊共同 index 比 `full` 在 `common_index[warmup:]`(到 trunc 末列止)vs `trunc[warmup:]` values+NaN mask+index timestamps **exact**(**不在交集後再 `:-k`**);③ warmup 區 gate `[0:warmup)` 兩 run NaN mask 一致(與 2.2 共用 helper);④ metadata gate 只比應不變欄(feature schema/config_hash/symbol/timeframe),`row_count/data_range` assert「符合截斷後預期」非 ==full。單 primary-TF + production preset 全欄。
- **驗證(可證偽,具體 patch 點)**:3 個 mutant 各跑 `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 必 FAIL:① 實際 L3 rolling(如 `momentum/FeatureEngineering/operators/numba_rolling.py`)改 `center=True`;② `momentum/FeatureEngineering/preprocessing/causal_winsor.py` 全量 fit;③ L4 lag `shift(-1)`(若存在)。各附 fail 摘要。
- **邊界**:k 大於資料量;截斷後不足 warmup;preprocessing on(L6.5)。
- 不可做:**不宣稱取代 P0-FF-3**(MultiTF 粗→細高頻截斷另批);不用 fast config 冒充 production 覆蓋。

**Task 2.2 — C2-2 尾端擾動 MR(同檔)**
- 目標:尾 k bar OHLCV ±1e6 擾動 → 截斷點前列不變。
- **驗證**:mutation `shift(-1)` 在 L3 rolling 必紅。
- **邊界**:擾動為 NaN/Inf;擾動單一 bar。
- 不可做:不只比 post-warmup 而漏 warmup 區洩漏——warmup 區另斷言不得有非 NaN 差異。

### Phase 3 — config 分級 + 收尾(依賴:Phase 1,2)
**Task 3.1 — C2 config 分級**:`test_ff_causal_mr_production`(requires_kline,nightly,全欄)vs `_fast`(smoke)。驗證:fast 不冒充 production 覆蓋。

## §V 驗證策略與邊界測試目錄
- 層級:單元(prepare_inputs/differential)/整合(全鏈 MR)/Golden 對照(baseline)/邊界。皆 standalone pytest。
- **mutation TDD-first(章程 §B 硬門檻)**:每個 correctness 測試**先寫 failing mutation probe**確認改壞會 FAIL,再寫實作;每 mutant 列具體 patch 點+驗收命令;驗收報告附 fail 摘要。**§B8**:Block/Bug 修後由**原提出方(codex/composer)**重跑同一反例確認真關閉。
- **防假綠**:diff 既有測試斷言,不得放寬換綠;columns gate 先於 values 比對。
- 邊界目錄打勾:空DF / 全NaN列 / Inf / std=0 / 重複·亂序 timestamp / 大尺度浮點 reduction / 截斷不足 warmup。

### §B4 覆蓋追溯矩陣(章程 §B4;缺=BLOCKING)
| 性質ID | 類別 | Oracle | 測試檔:函式 | Mutation probe(patch 點) |
|---|---|---|---|---|
| C1-1 | atomic differential | talib direct call EXACT | test_atomic_differential.py | wrapper source close→open |
| C1-2 | prepare_inputs 等價 | byte-equal vs TALIB_INPUT_SEMANTICS | test_prepare_inputs_equivalence.py | 刪 ATR from `_INPUT_TYPE_MAP` |
| C1-0 | correctness mode | raise 非 warning | test_correctness_mode.py | 刪 MFI from map → 須 raise |
| BUG-1 | 特徵語義 | talib.BETA(high,low) 雙 oracle | test_atomic_differential.py::test_beta_correl | 標準欄回退餵 (close,volume) |
| BUG-2 | 手刻變體 | 文獻獨立 reference | test_handcoded_reference.py | EOM `*`→`/` |
| C2-1 | 全鏈截斷 MR | 截斷不變量 EXACT | test_ff_fullchain_truncation_mr.py | numba_rolling `center=True` |
| C2-2 | 尾端擾動 MR | 擾動不變量 | test_ff_fullchain_truncation_mr.py | causal_winsor 全量 fit |
| C4-3 | manifest 校驗 | 指紋比對 | test_data_manifest.py | 改 sha256 / 缺 symbol×TF |

## §R 回退
- 每 Phase/Task 獨立 commit 可單獨 revert。BUG-1/BUG-2 改特徵集 → 新欄走 feature flag 或別名,舊欄保留至下游遷移完成;三方簽核未過不 merge。Golden FAIL(未受影響欄漂移)→ 不 merge。

## §N N/A 登記
- P0-FF-3(MultiTF 高頻截斷+production multi-TF 全欄矩陣)、P1-FF-5(跨 symbol 值隔離)、P1-FF-6(d-star mutation probe):N/A 本批,另批(reconcile §四)。
- **polars/numba 多路徑 differential**:N/A 本批 → **降 P1-FF-7 另批**(reconcile §四原註「併 P0-FF-1」,經 SPEC adversarial 評估範圍過大,明示移出本批,不靜默掉項)。
- 不全重測 V-6/L6.5/L3:N/A — 已 P0(`test_numba_rolling`/`test_causal_winsor`/`test_failopen_correctness` V-6),不重做。
