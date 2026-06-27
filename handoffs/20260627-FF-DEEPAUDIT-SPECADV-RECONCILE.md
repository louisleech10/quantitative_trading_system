# FF 深稽 SPEC+TODO adversarial — reconcile(採納 Codex+Composer)

> 被審:`docs/FF_DEEPAUDIT_P0_SPEC.md` + `_TODO.md`;審查:`...-SPECADV-{codex,composer}.md`(皆真 grep)。
> 兩家均「須修補後派工」。本 reconcile 逐條採納;Claude 據此修 SPEC+TODO 後,委員 R2 戳記方可派實作。

## 收斂 BLOCK(兩家都抓 → 必修)
1. **BUG-1 消費者清單空殼**:SPEC/TODO「列所有舊欄名消費者」零路徑。兩家 grep 出真實未列同步點 → SPEC Task 1.3 須附 **Consumer Sync Checklist**:
   - `momentum/FeatureEngineering/utils/adf_safe_skip.py:55`(`_CORREL_` whitelist、L16 BETA 排除)+ 其測試 `tests/feature_engineering/test_adf_safe_skip.py:48,164,353`(硬編 `close-volume_12h_statistics_BETA_5` 等)
   - `tests/_golden/failopen/baseline.json`、`tests/_golden/batch2d/provenance.json`(數百 L2–L7 衍生鍵)
   - `api/services/feature_factory_service.py:3804`(UI 顯示名 `"BETA":"Beta 係數"`)
   - `momentum/Analysis/`(IC)**無硬編**,風險在 golden/已凍結特徵集 + 語義漂移(見 BLOCK-5)
   - 實作時須 `rg 'statistics_BETA|statistics_CORREL|_BETA_|_CORREL_' tests/ api/ momentum/` 產物入 checklist。
2. **§G「未受影響欄 byte 不變」無可操作定義**:須增 **Affected Column Closure** 演算法:(1) 直接改名/改 source 的 L1 BETA/CORREL 欄;(2) provenance 圖(`tests/_golden/batch2d/provenance.json`)可追溯至 (1) 的所有 L2–L7 衍生欄 → 更新 golden+差異表;(3) 其餘欄 `nan_ratio exact` + **全欄 value hash 不變(非抽樣)**。
3. **correctness mode 機制未定義**:8 個 `*_indicators.py` 皆 `except Exception`→warning,無 mode 分支。SPEC 須**定義機制**(如 `FactoryConfig.fail_open.indicators` 或 `PYTEST_FF_CORRECTNESS=1`)+ 列 8 engine patch 點 + mutation「刪 MFI from map → compute_all raise 非 warning」。

## Composer 獨有 BLOCK(採)
4. **price_transform 掉項**:reconcile C1-1 必含 AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE;SPEC Task 1.2 漏。補入必含清單 + Task 1.1 明訂 `computed_in_adapter=True` 指標**排除 C1-2 byte 比對 或 adapter 層獨立 oracle**(二選一寫死:排除,因 compute() 回空 DF)。
5. **章程 §B4 追溯矩陣缺**:SPEC §V 須增 `|性質ID|類別|Oracle|測試檔:函式|Mutation probe|` 矩陣(≥7 列:C1-1/C1-2/C2-1/C2-2/C4-3/BUG-1/BUG-2)。

## Codex 獨有(採)
6. **檔案路徑不完整**:所有 Task 改檔用完整路徑 `momentum/FeatureEngineering/atomic/talib_wrapper.py` 等(冷啟動合約)。
7. **C2 metadata 驗收自相矛盾**:截斷後 `row_count/data_range` 本就該不同。拆兩 gate:(a) values/NaN/index 在共同 index `[warmup:]` exact(**不在交集後再 `:-k`**);(b) metadata gate 只比應不變欄位(feature schema/config_hash/symbol/timeframe),`row_count/data_range` 改 assert「符合截斷後預期」非 ==full。
8. **TODO logging 違解耦**:§0 `from api.core.logging` → `momentum/` 內須 `from momentum.core.logging import get_logger`。

## MAJOR(採)
9. **C2-1 warmup 區仍跳過**:Task 2.1 自身須加 `[0:warmup)` 顯式 assert(NaN mask/值一致),不只靠 2.2。
10. **C2-1 mutation probe 模糊**:列 3 個具體 patch 點(檔:行):rolling 模組 `center=True`、`preprocessing/causal_winsor.py` 全量 fit、L4 lag `shift(-1)`(若存在);各附 pytest 指令。
11. **BUG-2 golden 時序矛盾**:Task 1.4 拆三步:(a) 文獻 reference 差異表(可 fail)→(b) 三方簽 off →(c) 才寫 golden + metadata `variant=simplified` 綁簽核 commit hash。防自指 oracle。
12. **欄名統一**:`Beta_CloseVolume`/`Correl_CloseVolume`(對齊既有 underscore 慣例;reconcile §一原寫 Beta_CloseVolume,SPEC 誤作 BetaCloseVolume)。
13. **§A kline facts 補實測輸出**:h5 path/symbols/TFs/row_count/sha256 實跑摘要,否則降為「依治理要求」非 fact-verified。
14. **Task 0.1 skip→marker 遷移表**:列 10+ 處(`test_failopen_correctness.py:75`、`test_failopen_matrix.py:90,200`、`test_b6_warmup_trim.py:87,400`、`test_mtf_align_golden.py:190` 等)是否 correctness/掛 marker/保留理由。
15. **§G 凍結時機**:改「B0 後 B1 修前凍 v0;B1 後凍 v1+差異表」。
16. **polars/numba 掉項**:reconcile §四說併 P0-FF-1;SPEC 未落地 → §N 明示降 P1-FF-7 另批(不在本批)。
17. **(d) IC 語義漂移 smoke**:Task 1.3 增固定 1 symbol×TF×horizon BUG 修前後 IC 符號/量級差異表(要求明示變更+三方簽,非不變)。
18. **(a) ADF whitelist 重審**:Task 1.3 子項重跑 adf_safe_skip 測試 + 更新 whitelist 註解。

## OK(兩家確認忠實落地,不動)
- C1-2 prepare_inputs equivalence、C1-1 雙 oracle、C1-3 三級、C2 warmup config-driven+columns gate、C4 marker+manifest、mutation TDD-first+§B8、BUG-1 兩者都要+三方簽核、P0-FF-3 範圍解、9 Task 覆蓋、`estimate_max_warmup_bars(config, primary_tf, training_tfs)` 簽名可用。

## 戳記(委員 R2 審修正後 SPEC+TODO + 本 reconcile 後 append;v2 須 sha256 綁定)
（Claude 採納全部;待修 SPEC/TODO 後委員 R2 確認真關閉。append 前 `bash scripts/reconcile_body_hash.sh <本檔>`)
RECONCILE-STAMP: codex APPROVED 2026-06-27 sha256:6b75220205f6a23b12ca1c29cdc708448a3f061408c8f0d65e165f7684233e8a task:ff-specadv-r2b
RECONCILE-STAMP: composer APPROVED 2026-06-27 sha256:6b75220205f6a23b12ca1c29cdc708448a3f061408c8f0d65e165f7684233e8a task:ff-specadv-r2
