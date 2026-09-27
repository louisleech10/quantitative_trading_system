# Reconcile — 20260926-ffstatauto-x-review-r14

**來源** 20260926-ffstatauto-x-review-r14-codex.md, 20260926-ffstatauto-x-review-r14-composer.md　|　**roster** codex,composer

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| manifest 未同步 v33 落點：v33新增的Task2.4warmup- | P1 | CODEX-R14-P1-01 | 採納（SPEC 定案後、b4 實作派工前同步 `docs/manifests/FFSTAT.json` 之 test_files、touches、script_acceptance、gate_cmd，納入 Task 2.4 與 Task 2.3 之新測試、覆蓋收據與 blocked 收據；派工閘要求 `--todo` 為 manifest，未同步即無法派工；TODO 審查輪以此條為必驗項。不於 SPEC 未定案前改 manifest，免與後續 SPEC 修改不同步） | doc-sync |
| 欄集合變更缺機械核可：v33允許死欄規則造成欄集合變更，但只要 | P1 | CODEX-R14-P1-02 | 採納（Task 2.3 ⑦ 與 §G①：收據定義改前／改後欄集合 digest、逐欄原因、delta digest；使用者核可紀錄檔記其原話、日期與所核之 delta digest；gate 斷言核可紀錄之 digest＝本次 delta digest，未變時 delta 為空亦須寫出） | code-contract |
| 12h 子集選法不確定：§G⑦的12h子集條件「預設全設定中K與 | P2 | CODEX-R14-P2-01 | 採納（§G⑦：固定選擇器——以十個指標類別模型全集之預設全設定為起點，依原生列容量逐一移除 K 最大之指標參數實例，至「M_tf＋F_max_tf＋500 ≤ 12h 列數」為止；序列化子集設定、移除清單與設定 digest，收據只收選擇器輸出） | code-contract |
| 死欄門檻未參數化：v33要求L3與L7共用單一死欄純函式， | P2 | CODEX-R14-P2-02 | 採納（§C：純函式以呼叫端門檻為參數——L3 保留 NaN 率 > 0.9 與 `_VARIANCE_FILTER_MIN_EFFECTIVE_N=30`、L7 讀 `l7_dead_feature_drop.min_valid_samples`〔預設 100〕；29／30、99／100 邊界各一負例） | code-contract |
| Task 2.3 ③ 未隨收窄：v33已將§G②與§C公開不變量收窄為「 | P1 | COMPOSER-R14-P1-01 | 採納（Task 2.3 ③ 改為「鏈上無第②③類步驟且未平穩化之基礎欄」才比凍結基準逐位元組；其餘以 §G⑦ 驗） | doc-sync |

**主委補充**：L7 `find_dead_columns`（`utils/dead_feature_filter.py:44-90`）本即以 `notna().sum()` 與 `nunique(dropna=True)` 判定、不計 NaN 率，故遮罩只使其少計未穩定值，與 v33「有效樣本數只計穩定後之值」一致；需改者為 L3 之 NaN 率分母（codex R14-P2-02 之門檻參數化一併處理）。

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R14-P1-01

**斷言**: v33 新增的 Task 2.4 warmup-table gate、coverage receipt 與新測試未同步進 FFSTAT manifest 的檔案範圍與 gate 命令；依 manifest 執行的批次可在未執行新驗收的情況下通過。

**碼證**: `nl -ba docs/manifests/FFSTAT.json` 顯示 `test_files` L9–15 只有既有六支測試，`script_acceptance` L17–20 只有三支舊探針，`batch_card.touches` L35–65 未列 `tests/feature_engineering/test_ffstat_warmup_table.py`、`scripts/verify_l1_warmup_requirements.py`、`momentum/FeatureEngineering/atomic/warmup_table.yaml`、`momentum/FeatureEngineering/atomic/warmup_lookup.py` 或 coverage receipt，`gate_cmd` L84 也只串既有六支測試。對照 `docs/FFSTAT_SPEC.md` L109–112，v33 明定新測試、coverage successor、finite-guard mutant 與缺項 fail-closed。`bash scripts/todofmt_check.sh docs/manifests/FFSTAT.json` → `TODOFMT PASS`，但該檢查只證明 manifest 形狀合規。
CODE-ANCHOR: docs/manifests/FFSTAT.json:9
MUTATION: 將 tests/feature_engineering/test_ffstat_warmup_table.py 與 coverage receipt 留在 v33 SPEC 而從 test_files、touches、gate_cmd 移除，再執行原 batch_card.gate_cmd；新 warmup coverage 不被執行而舊 gate 仍可被宣稱完成。

**類別**: doc-sync

**來源摘要**: docs/manifests/FFSTAT.json#cea32416655f; docs/FFSTAT_SPEC.md#6e7ccce64435

修法：同步 manifest 的 `test_files`、`batch_card.touches`、`gate_cmd` 與 script/receipt 落點，並把 v33 的 warmup-table、finite-guard、category-coverage 與 12h blocked receipt 納入同一機械 gate；不改本輪唯讀範圍。可行性證據：所有新增落點已由 SPEC L109–112 明列，現有 manifest schema 接受 path array 與 gate command，現行 `todofmt_check.sh` 已對該 manifest rc=0；這是可由 JSON 落點同步完成的範圍修補，無需改驗收語意。影響：缺項表、測量非有限值與表外指標 fail-closed 可能完全未被 CI/派工 gate 覆蓋，故為 P1 blocker。

## CODEX-R14-P1-02

**斷言**: v33 允許死欄規則造成欄集合變更，但只要求「逐欄列原因並交使用者核可」，沒有定義可機械驗證的核可 artifact、scope digest 或 gate 斷言；因此輸出 schema 變更可能只靠散文收據被收批。

**碼證**: `docs/FFSTAT_SPEC.md:75` 規定欄集合可因 `nan_rate_rule`／`stable_samples_below_min` 改變並須使用者核可；`tests/_golden/ffstat/contract.json:28-59` 只有 packet `column_set_digest` 與決策欄位，沒有改前／改後欄集合、逐欄原因與核可結果的契約欄位；`docs/manifests/FFSTAT.json:22-23` 將該 contract JSON 作為本票 contract_json。真實 BTCUSDT 12h slice probe：前 1,540 列設為 NaN，`rows=1696`、`full_nan_rate=0.908018867925`、首有限列 `1540`、首有限列後 `stable_nan_rate=0`、`stable_valid=156`；舊 L3 `_variance_filter` 因全列 NaN 率而丟欄，L7 `min_valid_samples=100` 則不列 sparse，證明 v33 的欄集合差異不是空想。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:75
MUTATION: 在上述真實 12h slice 的收據只填改前／改後欄集合與 `nan_rate_rule`，不填任何核可結果或 scope digest，再執行 §G gate；若 gate 仍只檢查數值與欄位原因，未授權 schema 變更即可通過。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#6e7ccce64435; tests/_golden/ffstat/contract.json#aca54b48eb3c; docs/manifests/FFSTAT.json#cea32416655f

修法：在本票 receipt contract 中定義必填的欄集合 before/after digest、逐欄 reason、核可決策及核可範圍 digest，並在 §G gate 以 contract assertion 拒絕缺核可或 digest 對不上的 receipt；欄集合未變時也要有明確的 empty delta。可行性證據：現有 contract 已有 JSON metadata、packet `column_set_digest` 與既有 golden gate，可在同一 contract/test harness 增加負例；上面的真實 slice 已產生可驗證的穩定樣本計數，足以構成 deterministic delta，不需要全設定 FF run。影響：本版明確允許欄名／欄數變動，若無機械核可欄位，品質閘與「使用者核准後收批」不具可追溯性，故為 P1 blocker。

## CODEX-R14-P2-01

**斷言**: §G⑦ 的 12h 子集條件「預設全設定中 K 與窗長可容納於 1,696 根者」沒有定義閉包、依賴、多輸出元件、累積型欄或 config digest 的機械選擇規則；不同人可產生不同子集而都聲稱符合。

**碼證**: `docs/FFSTAT_SPEC.md:82` 只要求列出被移除的指標與參數，沒有 selector 演算法、最大／最小子集規則或固定設定 hash。真實 probe 以目前 `kline_cache.h5` 的 BTCUSDT 12h `1696` 根、`K=2051` 證實預設全設定只能 blocked；`AtomicIndicatorConfig.model_fields` 實際列出 `trend, momentum, volatility, volume, cycle, pattern, statistics, microstructure, entropy, tail_risk` 十個模型，顯示可機械取得全集，但 SPEC 沒有指定如何由全集產生 12h 子集。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:82
MUTATION: 將 12h 驗機設定改成只保留任意一個短窗指標並保留其餘移除清單，或改成所有單項可容納但組合窗不可容納的指標，仍以同一 §G⑦ 收據提交；目前文字沒有規則可拒絕其中任一選擇。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#6e7ccce64435; momentum/FeatureEngineering/feature_config.py#d7e5a9fb2df2

修法：指定 deterministic selector：從 `ConfigManager` 的十個 category model universe 出發，依原生列容量計算每個元件的 K/window、遞迴依賴與多輸出閉包，採固定的「全部可容納元件」規則，序列化子集 config、移除清單與 digest；收據只接受該 selector 的輸出。可行性證據：現有 `AtomicIndicatorConfig.model_fields` 已提供全集入口，§G 已要求收據列移除項，新增 selector 與 digest assertion 可在 coverage script 內完成，不需改真實資料或跑全設定。影響主要是 12h 機制驗證的可重現性與抗挑選性，列 P2。

## CODEX-R14-P2-02

**斷言**: v33 要求 L3 與 L7 共用單一死欄純函式，卻沒有定義兩個既有 caller 的有效樣本門檻如何傳入；現行 L3 使用 `30`，L7 `min_valid_samples` 預設為 `100`，單一未參數化預設會悄然改變其中一路的欄集合。

**碼證**: `momentum/FeatureEngineering/operators/rolling_aggregator.py:22-26,819-825` 現行 L3 有 `NaN rate > 0.9` 且 `_VARIANCE_FILTER_MIN_EFFECTIVE_N=30`；`momentum/FeatureEngineering/feature_config.py:466-475` 現行 L7 `min_valid_samples=100`；`docs/FFSTAT_SPEC.md:75` 同時寫「L3/L7 共用」與「有效樣本數只計穩定後」，但未寫 caller-specific threshold contract。真實 BTCUSDT 12h 1,540-leading-NaN probe 得穩定有限值 156，說明 stable-only count 可與 full-frame NaN rule 產生不同結果。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#6e7ccce64435; momentum/FeatureEngineering/operators/rolling_aggregator.py#cf448d635077; momentum/FeatureEngineering/feature_config.py#d7e5a9fb2df2

修法：把純函式的 stable-only count、NaN-rate denominator、constant predicate 與 `effective_min_valid_samples` 參數契約寫死；L3 明確保留其既有門檻語意，L7 明確讀 `nan_strategy.l7_dead_feature_drop.min_valid_samples`，並為 29/30 與 99/100 邊界各加負例。可行性證據：兩個既有 caller 的門檻與呼叫位置已可定位，純函式可接受同一套統計量與 caller threshold；不需改本輪 source。影響是欄集合及輸出 schema 的邊界漂移，列 P2。

ASSUMPTIONS_VERIFIED: #1 在真實 BTCUSDT 1h（20,352 rows）與 12h（1,696 rows）的 trend consensus、momentum divergence、volume-price divergence 小切片上，mask_end 延長至 base+55 後，首有限值只向後移且首有限值後 NaN rate 均為 0；#2 在真實 BTCUSDT 1h 代表性 L1 子集上 K=2051、F=2051、M=4102，7 欄各有 14,199 個絕對時間戳重疊列、最大差均為 0 且全過 0.005 tolerance，L1-mask mutant 在 K 前仍有 2,018–2,044 個有限值可辨識；12h 1,696 根依規格 blocked，未宣稱完整全設定已跑。
TESTS_RUN: `venv/bin/python probe.py`（tmp copy，rc=0；real-data MASK/WARMUP/DEAD_COLUMN/AB probes）；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md`（rc=0，TEMPLATE PASS）；`bash scripts/todofmt_check.sh docs/manifests/FFSTAT.json`（rc=0，TODOFMT PASS）；`git diff --check 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md`（rc=0）；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r14-codex.md --family codex --round-id 650b8e94-6f28-4fbe-93f8-af04a0745a28`（rc=0，COMPLETENESS PASS(single)，4 個 canonical ID）。
FAILURES_SEEN: 清理命令 `rm -rf /tmp/ffstat-r14-KvNByA` 被環境以 rm-f style policy 拒絕；依 brief 未改寫命令形式或繞過。兩個額外診斷曾以不支援的參數呼叫並退出用法錯誤，未作驗收依據，未改任何 source。
SCOPE_CHANGES: none；未改 code、SPEC、manifest、templates、CLAUDE.md、git 或 data_cache；只新增本交件與必要狀態交接檔。
NUMERIC_OR_SCHEMA_IMPACT: 未實作任何數值或 schema 變更；本審查確認 v33 允許欄集合變更，並將其未機械核可列為 P1。
TMP_CLEANUP: `/tmp/ffstat-r14-KvNByA` retained because direct cleanup was rejected; `/tmp/claude-501` verified present and untouched。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r14-codex.md

VERDICT: blocked
BLOCKED-BY: CODEX-R14-P1-01,CODEX-R14-P1-02
CLOSED: CODEX-R13-P1-01,CODEX-R13-P1-02,CODEX-R13-P1-03,CODEX-R13-P2-01
STATUS: DONE
## COMPOSER-R14-P1-01

**斷言**: v33 已將 §G ② 與 §C 公開不變量收窄為「鏈上無第②③類步驟之欄」才要求 `stable_start` 後四 hash／逐位元組與凍結基準相同，但 Task 2.3 ③ 仍要求**每個**未平穩化之欄在 `stable_start` 之後與 §G 凍結基準逐位元組全等——含 L6 trend consensus（第④類）、含 L2 以後遞迴鏈、含 meta 衍生欄；同一 SPEC 內驗收無法同時滿足 ② 與 ③。

**碼證**: `git diff 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md` → §G 通過條件 ② 增「v33 收窄」子句；§C:59 同步收窄；Task 2.3 驗證 ③ 字面未改「每個未平穩化之欄…與 §G 凍結基準逐位元組相同」。靜態對照：`docs/FFSTAT_SPEC.md:82`（§G ②）vs `:118`（Task 2.3 ③ 長條）。操作序列：實作 `test_ffstat_stable_start.py` 依 ③ 對 `meta_Trend_Consensus` 或 `EMA_233` 做凍結 baseline 全等 ⇒ 必紅；依 §G ② 同一欄改走 §G ⑦ 容差 ⇒ ③ 與 ② 互斥。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:118
MUTATION: 保留 v33 §G ② 文案不動，僅執行 Task 2.3 ③ 字面驗收（無起始日、平穩化關、任一未平穩化 L6 共識欄 `stable_start` 後四 hash 對凍結 baseline）⇒ pytest 紅；同一 run 改依 §G ② 子集判斷 ⇒ ③ 斷言仍要求全欄全等而無法綠。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#6e7ccce64435; handoffs/reconcile/20260926-ffstatauto-x-review-r13/synth.md#a60ead21d50f

**修法**: Task 2.3 ③ 與 §G ② 對齊——改為「鏈上無第②③類步驟且未平穩化之基礎欄」才做凍結 baseline 四 hash 全等；其餘（含第④類、L2+ 遞迴、平穩化欄）改列 §G ⑦ 或 ②′ 決策一致。可行性：純 SPEC／測試名分支，不新增生成期秒級以上檢查；與 r13 已採納之 COMPOSER-R13-P1-02 收窄同一語意，僅補 Task 2.3 漏改之一處。

---

