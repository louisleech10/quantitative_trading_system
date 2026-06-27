# FF 深稽 P0-FF-1/2/4 + BUG-1/BUG-2 — TODO

> 狀態 DRAFT　|　基於 SPEC `docs/FF_DEEPAUDIT_P0_SPEC.md`　|　日期 2026-06-27
> 實作者=Composer 2.5;code review=Codex GPT-5.5。冷啟動執行端逐 Task 寫碼,不需回讀其他檔。

## §0 全域規則與約束
- **解耦 7 條**:`momentum/` 不 import `api/`;測試可 standalone `pytest tests/...`(不需 run_api.py)。
- **資料品質**:不弱化 NaN/inf gate;不擅改輸出大小/數值行為(BUG-1/BUG-2 除外,且須三方數據簽核 + 新舊差異表)。
- **真實 kline**:`data_cache/feature_klines/kline_cache.h5`(10 symbol × {1h,4h,12h})。**禁合成 fixture 代替** correctness 測試。
- **防假綠**:不得放寬/刪除既有測試斷言換綠;新斷言對應新行為;columns gate 先於 values 比對。
- **mutation TDD-first(章程 §B 硬門檻)**:每個聲稱驗正確性的測試,**先寫 failing mutation probe** 證明「改壞會 FAIL」,再寫實作;每 mutant 附具體 patch 點 + 驗收命令;驗收報告附 fail 摘要。
- **§B8 閉合再驗證**:Block/Bug 修後由原提出方(codex/composer)重跑同一反例確認真關閉。
- **Logging(解耦)**:`momentum/` 內一律 `from momentum.core.logging import get_logger`(**不可** import `api.core.logging`,違反解耦 Rule 1);`api/` 內才用 `api.core.logging`。熱迴圈不 log。
- **Error 分類**:retryable(rate_limit/timeout)vs non-retryable(invalid_symbol/logic/格式)。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B0 治理地基 | 0.1, 0.2 | 無 | marker+manifest 為後續 correctness 測試前置 | 中 |
| B1 atomic+BUG | 1.0, 1.1, 1.2, 1.3, 1.4 | B0 | 同檔域(talib_wrapper/atomic),BUG 修與 differential 測試互相依賴;1.0 correctness mode 為 1.1 前置 | 大 |
| B2 全鏈 MR | 2.1, 2.2 | B0(marker) | 與 B1 獨立可並行;同檔 test_ff_fullchain_truncation_mr | 中 |
| B3 分級收尾 | 3.1 | B1, B2 | config 分級依賴前兩批測試存在 | 小 |

- **批次間 Gate**:
  - B0 過 → `pytest tests/feature_engineering/ -m requires_kline`(marker 生效);**§G v0 baseline 凍結在 B0 後、B1 前**。
  - B1 過 → `pytest tests/feature_engineering/atomic/ -v` 全綠 + **§G v1 重凍 + 新舊差異表** + **BUG-1/2 三方數據簽核 checklist**(Claude+Codex+Composer 各一行「資料正確」+差異表路徑)。
  - B2 過 → `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -v`(若 B2 先 merge,§G v1 仍須在 B1 後重凍)。
  - B3 過 → fast/production 分級各自收集正確。
- **每 Batch 派工 prompt**:派 Composer 時附「前置狀態 + 本批 Task 列表 + §0 規則 + 驗證命令 + mutation probe 要求」;完成 STATUS: DONE/BLOCKED。

## Phase 0 — 治理地基(完成後:correctness 測試缺資料會 FAIL 非靜默綠;manifest 校驗就緒)

### Task 0.1 — requires_kline marker + 雙 job
- 改法:`pytest.ini` 註冊 `requires_kline` marker;`tests/conftest.py` 提供 `requires_kline_data(symbol, tf)` fixture,缺檔 `pytest.fail(...)` 非 `pytest.skip`。
- **skip→marker 遷移表(實作端逐項判定 correctness/掛 marker/保留理由)**:`tests/test_atomic_indicators.py`、`tests/test_talib_wrapper.py`、`tests/feature_engineering/test_failopen_correctness.py:75`、`test_failopen_matrix.py:90,200`、`test_b6_warmup_trim.py:87,400`、`test_mtf_align_golden.py:190`、`test_ff_causal_golden.py:131` 等(實作時 `rg 'pytest\.skip.*kline' tests/` 補全);非 correctness(純環境/外部依賴)者列保留理由,不一次全改。
- **驗證**:暫移走某 kline → 掛 marker 測試 FAIL(非 skip);`pytest -m "not requires_kline"` 不收集該測試。指令 `pytest tests/feature_engineering/ -m requires_kline`。
- **邊界**:kline 存在但列數 < 最小 → FAIL;未掛 marker 舊測試行為不變。
- **不可做**:不把無資料開發流程改成硬性全 FAIL;逃生口 `-m "not requires_kline"` 必保留。

### Task 0.2 — DATA_MANIFEST.json + 校驗器
- 改法:新建 `tests/fixtures/DATA_MANIFEST.json`(10 symbol × 3 TF:symbol/TF/最少列數/sha256 指紋)+ `tests/fixtures/data_manifest.py` 校驗器;啟動比對實際 kline 指紋。
- **驗證**:改一筆 sha256 → FAIL;缺 symbol×TF → FAIL;row_count below min → FAIL(三 mutation);`pytest tests/fixtures/test_data_manifest.py`。
- **邊界**:manifest 多列實際缺的 symbol → FAIL 並明示哪筆。
- **不可做**:不把 kline 二進位納 repo(gitignore);只存指紋。

## Phase 1 — P0-FF-1 atomic differential + BUG-1/BUG-2(完成後:atomic wrapper source/param/公式有可證偽 oracle;2 bug 修且三方簽核)

### Task 1.0 — correctness mode 機制(1.1 前置)
- 改法:8 個 `momentum/FeatureEngineering/atomic/*_indicators.py` 現 `except Exception`→`logger.warning`(fail-open),無 correctness 分支。定義開關(建議 `FactoryConfig.fail_open_indicators: bool=True` 或 env `FF_CORRECTNESS_MODE`),correctness mode=on 時已登錄指標計算失敗 re-raise。統一 helper 包 try/except,列 8 engine 同步點。
- **驗證**:correctness mode 下刪 MFI from `momentum/FeatureEngineering/atomic/talib_wrapper.py::_INPUT_TYPE_MAP` → `pytest tests/feature_engineering/atomic/test_correctness_mode.py`(`pytest.raises`)非 warning。
- **邊界**:mode=off 行為不變;未登錄指標仍 skip。
- **不可做**:不把 production 預設改硬 fail(預設 fail-open;只 correctness 測試開 mode)。

### Task 1.1 — C1-2 prepare_inputs equivalence + registry 完整性
- 改法:新建 `tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py` + `TALIB_INPUT_SEMANTICS` 表(indicator→input_type→df 欄位 ordered);對 `momentum/FeatureEngineering/atomic/talib_wrapper.py` 每指標,`_prepare_inputs` ndarray 與依表直呼 `talib.FUNC(*arrays)` byte 相等。
- **驗證**:mutation 從 `talib_wrapper.py::_INPUT_TYPE_MAP` 刪 ATR → `pytest tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py` 必 FAIL(附 fail 摘要)。
- **邊界**:`computed_in_adapter=True` 的 price_transform(AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE)`compute()` 回空 DF → **寫死排除 C1-2 byte 比對**;MAVP special periods allowlist。
- **不可做**:不用 talib abstract 的 `price/price0` 名硬比 high/low(71/132 假陽來源)。

### Task 1.2 — C1-1 wrapper vs talib differential(含 BUG-1 雙 oracle)
- 改法:新建 `tests/feature_engineering/atomic/test_atomic_differential.py`;抽樣**必含** RSI/ATR/EMA/MACD/STOCH/BOP/OBV/AD/ADOSC + BETA/CORREL(雙 oracle)+ **price_transform AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE(adapter policy)** + cycle/statistics/custom 各≥1;比對 input tuple/params/output names/NaN mask/index(`assert_allclose`)。
- **驗證**:mutation 改 wrapper source(close→open)/改一 param → `pytest tests/feature_engineering/atomic/test_atomic_differential.py` 必 FAIL。
- **邊界**:全 NaN 輸入欄;不足 timeperiod 暖機列 NaN 對齊。
- **不可做**:不拿被測 wrapper 自身當 oracle(須直呼 talib)。

### Task 1.3 — BUG-1 修(兩者都要)
- 改法:`momentum/FeatureEngineering/atomic/talib_wrapper.py` BETA/CORREL 改 `hl`(high,low)=標準;**另**新增改名價量相關欄(**`Beta_CloseVolume`/`Correl_CloseVolume`**)+ metadata 標非標準。**先產 Consumer Sync Checklist**(`rg 'statistics_BETA|statistics_CORREL|_BETA_|_CORREL_' tests/ api/ momentum/` 逐項處置),至少含:
  - `momentum/FeatureEngineering/utils/adf_safe_skip.py:55`(`_CORREL_` whitelist、L16 BETA 排除)→ 重審 whitelist+更新註解+重跑 `tests/feature_engineering/test_adf_safe_skip.py`
  - `tests/feature_engineering/test_adf_safe_skip.py:48,164,353`(硬編舊欄名)→ migration
  - `tests/_golden/failopen/baseline.json`、`tests/_golden/batch2d/provenance.json`(L2–L7 衍生鍵)→ §G v1 差異表
  - `api/services/feature_factory_service.py:3804`(UI 顯示名)→ 對應新欄/variant
  - IC 語義漂移 smoke(固定 1 symbol×TF×horizon,BUG 修前後 IC 符號/量級差異表,明示變更非不變)
- **驗證**:標準欄 == `talib.BETA(high,low)`;價量欄 == 舊 (close,volume) 值且 metadata `variant`/非標準標記存在。**三方數據簽核**(Claude+Codex+Composer)確認差異表語義正確。
- **邊界**:下游硬編舊欄名 → migration 或別名,不得靜默掉欄;ADF whitelist 未重審不得 merge。
- **不可做**:不在未產 Consumer Sync Checklist 下只改 wrapper。

### Task 1.4 — BUG-2 修 + C1-3 oracle 三級
- 改法:手刻指標(Klinger/ForceIndex/EOM + entropy/tail/micro 抽樣)建 `tests/references/*_ref.py` 獨立 reference(不得 import 被測模組);metadata `variant` 改於 `momentum/FeatureEngineering/atomic/volume_indicators.py`(+ `entropy_indicators.py`/`tail_risk_indicators.py`/`microstructure_indicators.py`)。oracle 三級。**三步防自指**:(a) 先產文獻 reference 差異表(可 fail)→(b) 三方簽 off →(c) 才寫 golden + metadata `variant=simplified` 綁簽核 commit hash。Klinger/ForceIndex/EOM 欄名/描述明示變體。
- **驗證**:mutation EOM `*`→`/` → `pytest tests/feature_engineering/atomic/test_handcoded_reference.py` 必 FAIL;簡化變體 golden 來自步驟(b)三方簽 off,非實作反推。
- **邊界**:無外部 oracle 者不得宣稱「公式正確」,只 golden-lock。
- **不可做**:不拿現實作輸出當 canonical oracle freeze(自指鎖死錯公式)。

## Phase 2 — P0-FF-2 全鏈截斷 MR(完成後:全鏈無未來洩漏有可證偽不變量;與 Phase 1 可並行)

### Task 2.1 — C2-1 全鏈 bar 級截斷不變量
- 改法:新建 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`;真 kline 跑 `generate_features()`,截斷尾 k bars;**warmup = `estimate_max_warmup_bars(config, primary_tf, training_tfs)`,禁 data-dependent 首全填列**。四段斷言:① columns gate(先於值);② values gate 共同 index `[warmup:]`(到 trunc 末列止)values+NaN mask+index exact,**不在交集後再 `:-k`**;③ warmup 區 `[0:warmup)` NaN mask 一致(與 2.2 共用 helper);④ metadata gate 只比應不變欄(schema/config_hash/symbol/tf),`row_count/data_range` assert 截斷後預期非 ==full。單 primary-TF + production preset 全欄。
- **驗證**:3 mutant 各跑 `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 必 FAIL:① `momentum/FeatureEngineering/operators/numba_rolling.py` 改 `center=True`;② `momentum/FeatureEngineering/preprocessing/causal_winsor.py` 全量 fit;③ L4 lag `shift(-1)`(若存在)。
- **邊界**:k > 資料量;截斷後不足 warmup;preprocessing on(L6.5)。
- **不可做**:不宣稱取代 P0-FF-3;不用 fast config 冒充 production 覆蓋。

### Task 2.2 — C2-2 尾端擾動 MR(同檔)
- 改法:尾 k bar OHLCV ±1e6 擾動 → 截斷點前列不變;**warmup 區另斷言不得有非 NaN 差異**(防只比 post-warmup 漏 warmup 洩漏)。
- **驗證**:mutation `shift(-1)` 在 L3 rolling 必紅。
- **邊界**:擾動為 NaN/Inf;擾動單一 bar。
- **不可做**:不只比 post-warmup 而漏 warmup 區。

## Phase 3 — config 分級收尾(完成後:fast/production 覆蓋不混淆)

### Task 3.1 — C2 config 分級
- 改法:`test_ff_causal_mr_production`(requires_kline,nightly,production preset 全欄)vs `_fast`(smoke);標記分流。
- **驗證**:`pytest -m "not requires_kline"` 不收集 production;fast 不冒充 production 覆蓋。
- **邊界**:nightly 缺 manifest → FAIL(接 Task 0.2)。
- **不可做**:不把 production 全欄 MR 降級成 fast 充數。

## 覆蓋追溯(SPEC Task ID → TODO)
SPEC Task 0.1→T0.1、0.2→T0.2、1.0→T1.0(correctness mode)、1.1→T1.1、1.2→T1.2、1.3→T1.3、1.4→T1.4、2.1→T2.1、2.2→T2.2、3.1→T3.1(10/10 全覆蓋;§G v0/v1 baseline 見 §B Batch Gate;§B4 矩陣見 SPEC §V;§N FF-3/polars-numba/P1 另批不在本 TODO)。
