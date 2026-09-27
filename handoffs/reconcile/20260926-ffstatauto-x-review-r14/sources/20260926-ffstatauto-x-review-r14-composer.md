# FF-STAT SPEC v33 審查 r14 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R14  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R14-BRIEF.md`  
標的：`git diff 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md`；r13 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r13/synth.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針於 `/tmp/ffstat-r14-wd`（真實 `kline_cache.h5`）。

fact-verified: v33 版註逐條對應 r13 採納項；`git diff 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md` 僅改 `docs/FFSTAT_SPEC.md`；`venv/bin/python -c '...estimate_max_warmup_bars...'` → 12h `max_k=2051 rows=1696 blocked=True`、1h/4h 合資格；coverage 現腳本仍 `76/39 missing`（Task 2.4 要求之繼者尚未落地，屬 impl 前收據，非 v33 條文自相矛盾之唯一阻擋）。

## COMPOSER-R14-P1-01

**斷言**: v33 已將 §G ② 與 §C 公開不變量收窄為「鏈上無第②③類步驟之欄」才要求 `stable_start` 後四 hash／逐位元組與凍結基準相同，但 Task 2.3 ③ 仍要求**每個**未平穩化之欄在 `stable_start` 之後與 §G 凍結基準逐位元組全等——含 L6 trend consensus（第④類）、含 L2 以後遞迴鏈、含 meta 衍生欄；同一 SPEC 內驗收無法同時滿足 ② 與 ③。

**碼證**: `git diff 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md` → §G 通過條件 ② 增「v33 收窄」子句；§C:59 同步收窄；Task 2.3 驗證 ③ 字面未改「每個未平穩化之欄…與 §G 凍結基準逐位元組相同」。靜態對照：`docs/FFSTAT_SPEC.md:82`（§G ②）vs `:118`（Task 2.3 ③ 長條）。操作序列：實作 `test_ffstat_stable_start.py` 依 ③ 對 `meta_Trend_Consensus` 或 `EMA_233` 做凍結 baseline 全等 ⇒ 必紅；依 §G ② 同一欄改走 §G ⑦ 容差 ⇒ ③ 與 ② 互斥。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:118
MUTATION: 保留 v33 §G ② 文案不動，僅執行 Task 2.3 ③ 字面驗收（無起始日、平穩化關、任一未平穩化 L6 共識欄 `stable_start` 後四 hash 對凍結 baseline）⇒ pytest 紅；同一 run 改依 §G ② 子集判斷 ⇒ ③ 斷言仍要求全欄全等而無法綠。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#6e7ccce64435; handoffs/reconcile/20260926-ffstatauto-x-review-r13/synth.md#a60ead21d50f

**修法**: Task 2.3 ③ 與 §G ② 對齊——改為「鏈上無第②③類步驟且未平穩化之基礎欄」才做凍結 baseline 四 hash 全等；其餘（含第④類、L2+ 遞迴、平穩化欄）改列 §G ⑦ 或 ②′ 決策一致。可行性：純 SPEC／測試名分支，不新增生成期秒級以上檢查；與 r13 已採納之 COMPOSER-R13-P1-02 收窄同一語意，僅補 Task 2.3 漏改之一處。

---

## 必答

1. **(1a)** 本家 r13 三條均已於 v33 條文閉合：**COMPOSER-R13-P1-01**（§G ③／Task 2.1 分支 `per_column`）、**COMPOSER-R13-P1-02**（§C／§G ② 收窄＋L1 未遮罩輸入）、**COMPOSER-R13-P2-01**（§A 增 L5/L6/对齐/state_counters FACT）。**(1b)** 逐字對 `git diff 9c37a345 e376b590`：P1-01／P1-02 修法與 reconcile 採納一致；P2-01 採納理由成立（盤點前提與 FACT 已对齐）。codex r13 P1 三條之 SPEC 側亦在同 diff 有對應敘述（finite guard、§G ⑦ 重寫、死欄純函式），本家不列 CLOSED codex ID。

2. **(2a)** 有——**COMPOSER-R14-P1-01**（Task 2.3 ③ 與 v33 §G ②／§C 不變量未同步）。**(2b)** 無需全 FF run：對 `docs/FFSTAT_SPEC.md:82` 與 `:118` 同時讀取即可重現邏輯衝突；impl 時以 ③ 驗 `meta_Trend_Consensus` 或 recursive 欄對 baseline 全等即紅。

3. **(3a)** brief **fact-verified**（遮罩只延長開頭 NaN 段）：在 v33 §C 定義下**成立**（L1/L1 输出遮罩、①④ 类、校準列均明寫只作用于開頭段）。brief **assumed**（死欄 NaN 率自首個有限值起算與遮罩長度無關）：在「遮罩不引入首個有限值之後的新 NaN」前提下**成立**（§C 死欄純函式段）；現碼 `rolling_aggregator.py:819` 仍全列計率，屬 impl 落差，非 v33 條文新矛盾。**assumed**（M_tf＝K_max＋F_max 使 A/B 可偵測）：**部分成立**——`estimate_max_warmup_bars` 對 12h 已判 blocked（1696 < 2051+500）；1h/4h 列數足；本輪**未**跑完整 A/B 收斂差分或「刪 L1 遮罩」mutant 數字（brief 亦標未跑）。**(3b)** `venv/bin/python -c '...'` → `tf=12h max_k=2051 rows=1696 blocked=True`；`tf=1h rows=20352 blocked=False`。

4. **(4a)** brief「我沒查」：**①** v33 已列第④类與 Task 2.3 ② 驗收，但 `consensus_features.py:52-57` 之 `skipna=True` 與「開頭遮罩後間歇 NaN 不變」仍靠 impl 證明，**未形成新 P1**（spec 已要求只遮開頭）。**②** L7 `min_valid_samples` 現碼仍數全列 `notna`（`dead_feature_filter.py:82`），v33 要求只计稳定后——**impl 契約**，spec 已写纯函数，**未单列 v33 文案缺陷**。**③** §G ⑦ 12h 子集「可容納於 1,696 根者」**无机械选法**（禁用指标顺序、窗长未绑定），可能使对证子集为空——**P3 风险**，不单独挡 SPEC 若 blocked 已有 P1-01。**④** Task 2.4 要求 coverage 类別全集，现脚本仍六类（`20260927-warmup-table-coverage.py:13`）——v33 已指「之後繼者」，属 impl 任务，**非 v33 新 defect**。**(4b)** `momentum/FeatureEngineering/meta_features/consensus_features.py:52-57`；`momentum/FeatureEngineering/utils/dead_feature_filter.py:78-87`；`docs/FFSTAT_SPEC.md:82`（§G ⑦ 12h 子集句）；`handoffs/run_receipts/20260927-warmup-table-coverage.py:13-19`。

5. **(5a)** **否**，`VERDICT: blocked`（Task 2.3 ③ 与 §G ② 不可同真）。**(5b)** **COMPOSER-R14-P1-01**。

---

ASSUMPTIONS_VERIFIED: `git diff 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md`；`handoffs/reconcile/20260926-ffstatauto-x-review-r13/synth.md`；r13 composer 交件；`docs/FFSTAT_SPEC.md` 现行 §C/§G/Task 2.3；真實 HDF5 列數探针。  
TESTS_RUN: `git diff 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md`（112 行）；`venv/bin/python handoffs/run_receipts/20260927-warmup-table-coverage.py | head -1` → `total_indicators=76 in_table=37 missing=39`；`venv/bin/python -c '...estimate_max_warmup_bars+load_klines...'` → 12h blocked、1h/4h ok；开跑与收尾 `git status --short -- momentum api scripts tests docs templates config` 一致。  
FAILURES_SEEN: `/tmp/ffstat-r14-wd/probe_r14.py` 首次 `IndicatorTest.compute` AttributeError，未改写成绕过路径，改以已验证之 `estimate_max_warmup_bars` 一行探针代替 warmup finite 重跑。收尾 `rm -rf /tmp/ffstat-r14-wd` 被執行環境拒絕，未改寫命令繞過；`/tmp/claude-501` 保留。  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯读审查）；v33 已披露之栏集合／死栏规则变更属使用者待核可范围，本 finding 不弱化 gate。  
產出: `handoffs/20260926-ffstatauto-x-review-r14-composer.md`

VERDICT: blocked
BLOCKED-BY: COMPOSER-R14-P1-01
CLOSED: COMPOSER-R13-P1-01,COMPOSER-R13-P1-02,COMPOSER-R13-P2-01

STATUS: DONE
