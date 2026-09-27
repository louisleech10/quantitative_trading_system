# FF-STAT SPEC v34 審查 r15 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R15  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R15-BRIEF.md`  
標的：`git diff e376b590 f12e842e -- docs/FFSTAT_SPEC.md`；r14 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r14/synth.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針於 `/tmp/ffstat_r15_wd`（真實 `kline_cache.h5`）。

fact-verified: v34 版註與 diff 五項修補與 r14 synth 表一致；`sed -n 44,90p momentum/FeatureEngineering/utils/dead_feature_filter.py` → `notna().sum()`／`nunique(dropna=True)`、不計 NaN 率；Task 2.3 ③ 已與 §G ② 同句收窄（v34 L119）。

## COMPOSER-R15-P1-01

**斷言**: v34 Task 2.3 ⑦／§G ① 要求欄集合與 delta 之 sha256 機械比對，但未定義與 v13 `calibration_source_sha256` 同級之逐位元組框架（欄名排序、diff 陣列序、JSON 鍵序、UTF-8）；同一語意 delta 兩次序列化可得不同 digest，核可 gate 與 CODEX-R14-P1-02 修法在 SPEC 層仍不可重現。

**碼證**: `docs/FFSTAT_SPEC.md:119` ⑦ 只寫「改前與改後欄集合之 sha256…及 delta 之 sha256」，未釘死序列化；對照 `tests/_golden/ffstat/contract.json:40-45` 對校準域有 `calibration_source_sha256` 鍵但無 column-set-delta 欄位定義。`/tmp/ffstat_r15_wd/probe_r15.py`（repo 根執行）→ `DELTA_SHA {"unsorted_keys_differ": true, "sort_keys_stable": true, "spec_defines_sort_keys": false}`：同一 before/after/diff 物件，`json.dumps` 鍵序不同則 sha256 不同，`sort_keys=True` 才穩定。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:119
MUTATION: 對同一組欄集合 delta 先以 `{"before":[...],"after":[...],"diff":[...]}` 寫收據算 sha256，再以鍵序 `diff,after,before` 重寫同一內容算 sha256；若測試只比對「本次收據內自算 digest」而 SPEC 未定框架，兩份收據可一過一紅或雙過但 digest 不一致，機械核可失效。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#85cbf4c2b7c1; tests/_golden/ffstat/contract.json#aca54b48eb3c; handoffs/reconcile/20260926-ffstatauto-x-review-r14/synth.md#1ad38ffc4589

**修法**: 在 Task 2.3 ⑦ 或 `contract.json` 增 column-set-delta 位元組契約（建議：欄名 UTF-8 升序後以 `\n` 連接再 sha256；diff 陣列依 `col` 升序；整份收據 `json.dumps(..., sort_keys=True, separators=(',',':'), ensure_ascii=False)` 後 sha256），並在測試加「鍵序 permute 不變 digest」負例。可行性：`calibration_source_sha256` 已有逐位元組先例；probe 已證 `sort_keys=True` 可消除鍵序漂移；不需全 FF run、秒級單測可覆蓋。

---

## 必答

1. **(1a)** 本家 **COMPOSER-R14-P1-01** 已閉合；r14 他族 ID 由 synth 採納、本輪對 v34 diff 複核。**(1b)** `git diff e376b590 f12e842e`：Task 2.3 ③ 改為「鏈上無第②③類…才凍結 baseline 全等」與 §G ②／§C 同語意（L119），原互斥反例不再成立。**CODEX-R14-P1-01** manifest 同步仍依 synth「SPEC 定案後、實作派工前」——v34 版註 L4 明示、理由仍成立，非 v34 條文缺陷。**CODEX-R14-P1-02／P2-01／P2-02** 分別落在 Task 2.3 ⑦ 機械核可、§G⑦ 固定選擇器、§C 呼叫端門檻（diff L16–25、L76、L83、L119），逐字可對。

2. **(2a)** 有——**COMPOSER-R15-P1-01**（delta／欄集合 digest 缺 canonical bytes）。**(2b)** 執行 `venv/bin/python /tmp/ffstat_r15_wd/probe_r15.py` → `unsorted_keys_differ: true`；無需全設定 FF run。

3. **(3a)** brief **assumed** §G⑦ 選擇器終止且子集非空（含 recursive）：**未否定、未完整實跑 FF**——`probe_r15.py` 在 L1 K_max=266、`estimate_max_warmup_bars` 12h=2051（含 L2–L6）、`ROWS_12H=1696` 下，以 F_max 代理 400 時 `terminated_nonempty: true`、recursive 仍多；真實 F_max 需 run A 重算，本輪未跑全鏈。**assumed** delta sha256 可重現：**不成立（SPEC 層）**——見 finding 與 probe。**(3b)** `probe_r15.py` 輸出見上；`find_dead_columns` 門檻行為見 brief fact-verified。

4. **(4a)** brief「我沒查」：**①** 移除單一 L1 實例後 L2–L6 欄與 F_max 單調性——**未命中為已證 P0/P1**（v34 選擇器僅動 L1 實例，F_max 可能由 L3 窗主導；列為 impl 風險，無全 run 反例）。**②** L3 `_variance_filter` 仍 `df.isna().mean()` 全列（`rolling_aggregator.py:820-825`）vs §C「自首個有限值起」——**impl 落差**，v34 已寫共用純函式＋呼叫端門檻，**非 v34 新文案矛盾**。**③** 核可紀錄寫入者——Task 2.3 ⑦ 定欄位與 gate，未定主委代寫流程，**P3 程序風險**，不單獨阻擋 v34 定案。**(4b)** `momentum/FeatureEngineering/operators/rolling_aggregator.py:820-825`；`docs/FFSTAT_SPEC.md:83`（§G⑦ 選擇器）；Task 2.3 ⑦ 核可 JSON 路徑 L119。

5. **(5a)** **否**，`VERDICT: blocked`（機械核可 digest 未定義）。**(5b)** **COMPOSER-R15-P1-01**。

---

ASSUMPTIONS_VERIFIED: `git diff e376b590 f12e842e -- docs/FFSTAT_SPEC.md`；`handoffs/reconcile/20260926-ffstatauto-x-review-r14/synth.md`；`docs/FFSTAT_SPEC.md` §C/§G/Task 2.3；`momentum/FeatureEngineering/utils/dead_feature_filter.py:44-90`；`/tmp/ffstat_r15_wd/probe_r15.py`  
TESTS_RUN: `git diff e376b590 f12e842e -- docs/FFSTAT_SPEC.md`（38 行）；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`venv/bin/python /tmp/ffstat_r15_wd/probe_r15.py` → ROWS_12H 1696、ESTIMATE_MAX_WARMUP_12H 2051、DELTA_SHA unsorted_keys_differ=true；開跑與收尾 `git status --short -- momentum api scripts tests docs templates config` 僅既有 pycache 變動（與 r14 同型）  
FAILURES_SEEN: `probe_r15.py` 首次 `ConfigManager` import 路徑錯誤已修正後重跑 rc=0；收尾 `rm -rf /tmp/ffstat_r15_wd` 被環境拒絕，未改寫命令繞過  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）；finding 要求未來收據 digest 契約，未改現行輸出  
產出: `handoffs/20260926-ffstatauto-x-review-r15-composer.md`  
TMP_CLEANUP: `/tmp/ffstat_r15_wd` retained（direct `rm -rf` rejected）；`/tmp/claude-501` 未動

VERDICT: blocked
BLOCKED-BY: COMPOSER-R15-P1-01
CLOSED: COMPOSER-R14-P1-01

STATUS: DONE
