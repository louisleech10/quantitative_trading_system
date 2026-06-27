## 任務1:章程驗證

### 漏項(原版有最終稿無)
- Codex 原版的 `correctness / contract / regression / smoke / perf` 分級語義被改寫成 Oracle + P0-P3，但「`perf` 不可替代 correctness」與「`contract` 不宣稱量化正確」語義變弱；最終稿容易讓 P2 contract 被誤算為資料/數值正確性。
- A1 漏掉原版明列的 metadata 血緣最低欄位：`source/version/row_count/time_range/schema hash`。最終稿只寫 config_hash/manifest，追溯性較弱。
- 回測細項被壓縮過度：原版明列 same-bar stop/take-profit 優先序、unknown exit timestamp 不可 silent、MAE/MFE、逐 trade oracle；最終稿只在 §E 摘要提成本/延遲/MDD，執行門檻不足。
- CI 分層漏掉原版「correctness-real-data blocking on data host」的強語義；最終稿有 marker/quarantine，但沒有把真實資料 correctness job 的 blocking 條件講清楚。
- 「partial confidence」語義漏掉：原版說資料/洩漏/數值若缺真實 run + mutation + 三方 review，只能標 partial confidence；最終稿多處寫 BLOCKING，但沒有統一信心等級。

### 錯誤/誤併
- §0 把 `EXACT` 的例子含「schema / exception / 解耦 exit 0」並列為計入正確性，需補限定：這些只保證 contract/architecture，不保證量化數值正確。
- §0 `TOLERANCE abs≤1e-9 或 rel≤1e-7` 被寫成通用門檻，不專業；可作 IC golden 既有 budget，但跨回測、feature matrix、float32/float64 路徑應由 SPEC 或既有 frozen budget 定義。
- §A3 說 float 不可裸 sha256，但 §17 又說 kline sha256；這不矛盾但需明確：資料檔/JSON artifact 可 sha256，浮點計算表不可只靠整表 hash 當唯一 oracle。
- §B1「P0 正確性必須有 mutation probe」與 §A8 G-NEW/G-OLD golden 被列為正確性之間語義需釐清：golden 是 P1 regression，沒有 mutation probe 時不能升格為 P0。
- §H 把「IC 1a leakage/split/oos/golden」列可當範本是合理，但若讀者理解為全 P0 完備會誤導；其中 golden 是 P1，部分契約是 P2，rolling IC 算法仍缺 A15 專門 differential。

### 仍遺漏/門檻問題
- Fixture 審計還未要求在每個測試檔/fixture 旁實際標 `FAITHFUL|SYNTHETIC|MOCK`，只是章程要求，缺落地檢查。
- Hypothesis 基建被列為待補，但沒有最低引入策略或 marker，容易長期停在「需補」。
- Mutation probe 沒有要求留下證據格式，例如 patch 摘要、哪個測試紅、錯誤摘要；後續驗收難審。
- 統計章程夠完整，但未區分「測統計公式正確」與「策略/因子真的有 alpha」兩種 claim，容易把統計公式 golden 誤當投研結論。

## 任務2:差距稽核(優先序)

### 必補(正確性高風險,附模組+為何+建議測試類別)
- `momentum.Analysis.ic_engine.compute_rolling_ic`：1a cut1 的 OOS/rolling warmup 測了 scope、長度、purge mutation，但沒有 rolling IC vs `scipy.stats.spearmanr` 的逐窗 differential。既有 `tests/momentum/test_ic_engine.py` 只對 `compute_ic` 對 scipy，rolling 測試多為存在性/方向性。建議補 A15 TOLERANCE：小表逐 window/stride 對 scipy，含 NaN、短窗、test slicing 邊界。
- 1a mutation 證據治理：`test_winsor_bounds_from_train_only`、standardize/coverage/constant、purge label mutation 是 METAMORPHIC 強測，但沒有留下人工 mutation probe 證據。建議補 B1 記錄或最小 mutation harness，證明拿掉 `fit_mask`/purge slice 必紅。
- 1-contract baseline：`test_baseline_exists` 只驗 baseline 檔存在、sha、meta，屬 P1/P3 之間，不能算 correctness；`test_split_leakage_golden` 是較強 EXACT/METAMORPHIC 契約。建議補 baseline replay 測試或把 baseline_exists 明確降級為 registry/golden governance，不列正確性。
- Phase0 timestamp：`test_ic_timeaxis.py` 和 `test_feature_factory_timestamp_filter.py` 覆蓋秒/ms與 implausible timestamp fail-closed，但多為小 fixture；建議補 A8 真實 `kline_cache.h5` timestamp 單位 contract，避免再次 ms/s 假綠。
- Phase0 GroupedConfig/by_volatility：已有 `test_compute_grouped_ic_rejects_explicit_by_volatility` 和預設 config false，屬 P2 EXACT；缺對 config load / API override 把 `by_volatility=True` 傳入時的端到端 fail-closed。建議補 A6/A12。
- Phase0 L65 benchmark：`test_l65_phase0_gate*` 是 synthetic smoke/perf harness，不能支撐輸出等價或數值正確。若任何後續 claim 是 L6.5 correctness，必補 A7/A15 fast-vs-reference 或 golden tolerance。

### 可延後
- 1a G-OLD/G-NEW golden 已有 `test_flag_off_deep_equal_baseline`、`test_flag_on_matches_new_golden`，屬 P1 regression；短期可接受，但需補 manifest/golden 更新治理。
- 1a fallback/irregular timestamp/OOS metadata 測試覆蓋不錯，屬 P2 EXACT，可延後到前端/榜單契約一起補 `applied:false` 不進 FDR/排序。
- Phase0 feature_filter sorted subset、empty fail-closed、大欄位 stable subset已有 P2/P1 覆蓋；可延後補真實 registry replay。
- dead_feature_filter invariants 覆蓋充足，含 numpy/DataFrame differential 與 performance guard；可延後 Hypothesis 化。
- 1-contract `split_per_symbol_golden` 已覆蓋跨 symbol 隔離與 purge local order；可延後擴到更多 symbols/TF。

HANDOFF_NOT_UPDATED: read-only sandbox；未寫 `HANDOFF.md` 或新增 handoff 檔。  
ASSUMPTIONS_VERIFIED: 已讀 `HANDOFF.md`、`CLAUDE.md`、指定 handoff、最終章程、Codex/Composer 原版、1a cut1 測試、1-contract golden、Phase0 timestamp/feature_filter/by_volatility/L65/dead_feature_filter 相關測試。  
TESTS_RUN: 未跑 pytest；本任務為 read-only 稽核。執行 `sed`/`rg` 實讀文件與測試碼。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
STATUS: DONE