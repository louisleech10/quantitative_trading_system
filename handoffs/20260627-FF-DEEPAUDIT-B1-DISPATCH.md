# 派工:FF 深稽 B1 實作(Composer 2.5)— atomic differential + correctness mode + 修 BUG-1/2

讀 `docs/FF_DEEPAUDIT_P0_SPEC.md` §P Phase 1 + `docs/FF_DEEPAUDIT_P0_TODO.md` Task 1.0~1.4(已過兩輪雙家族 adversarial+戳記)。本批做 Task 1.0/1.1/1.2/1.3/1.4。**不碰 B2/B3**。

## §0 鐵律
- `momentum/` logging 用 `from momentum.core.logging import get_logger`(禁 import api.core.logging)。
- kline 用 `create_kline_storage_manager(cache_dir='data_cache/feature_klines')` 讀(非 pd.HDFStore)。禁合成 fixture 代 correctness。
- **mutation TDD-first**:每個聲稱驗正確性的測試,先寫 failing mutation probe 證明改壞會 FAIL,再寫實作;驗收報告附 fail 摘要(SPEC §B4 矩陣列了 8 個 mutant 的 patch 點)。
- 防假綠:不放寬既有斷言。完整檔案路徑。env 已修(numpy 1.26.4+tables);測試 `source venv/bin/activate`。

## Task 1.0 correctness mode → 1.1 prepare_inputs 等價 → 1.2 atomic differential
- 照 SPEC Task 1.0/1.1/1.2 改法。1.2 抽樣必含 RSI/ATR/EMA/MACD/STOCH/BOP/OBV/AD/ADOSC + BETA/CORREL(雙 oracle)+ price_transform(adapter policy)+ cycle/statistics/custom 各≥1。

## Task 1.3 修 BUG-1(BETA/CORREL,兩者都要)— 最高風險
- **先產 Consumer Sync Checklist**:`rg 'statistics_BETA|statistics_CORREL|_BETA_|_CORREL_' tests/ api/ momentum/` 逐項處置。SPEC Task 1.3 列了必含同步點(adf_safe_skip.py:55+其測試、golden baseline/provenance、feature_factory_service.py:3804 UI、IC 語義漂移 smoke)。
- talib_wrapper BETA/CORREL 改 hl(high,low)=標準;新增 `Beta_CloseVolume`/`Correl_CloseVolume`(舊價量語義)+ metadata 標非標準。
- **產新舊差異表**(供三方數據簽核):受影響欄(Affected Column Closure:L1+provenance 衍生)的新舊值差異。
- ADF whitelist 重審 + 重跑 test_adf_safe_skip。
- **注意**:三方數據簽核由 Claude 接回後另跑(你產差異表 + 雙 oracle 測試即可);不要自己宣稱簽核通過。

## Task 1.4 修 BUG-2(手刻指標)
- 照 SPEC:tests/references/*_ref.py 獨立 reference(不 import 被測模組);Klinger/ForceIndex/EOM 標 variant=simplified;三步防自指(reference 差異表→簽核→才寫 golden)。

## 收尾
- 交接寫 `handoffs/20260627-FF-DEEPAUDIT-B1-RESULT.md`(跑哪些測試/測什麼/通過條件/mutation fail 摘要/Consumer Sync Checklist/新舊差異表路徑)。
- 跑 test_l65_golden 等會寫 tests/golden/ 的測試後,git checkout 還原那些 artifacts(勿入 diff)。
- 完成 STATUS: DONE 或 BLOCKED。兩輪解不了→BLOCKED 不 solo。
