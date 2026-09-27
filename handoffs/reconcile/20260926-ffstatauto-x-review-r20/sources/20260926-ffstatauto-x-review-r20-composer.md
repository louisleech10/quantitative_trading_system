# FF-STAT SPEC v39 審查 r20 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R20  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R20-BRIEF.md`  
標的：`git diff bfb5ad83 fa3d1b85 -- docs/FFSTAT_SPEC.md`；r19 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r19/synth.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針 `/tmp/ffstat-r20-run`（真實 kline 切片，禁合成 fixture）。

## COMPOSER-R20-P3-00

**斷言**: 本輪逐項核對 v39 差分與 r19 採納修法後，未發現新的 P0／P1 SPEC 缺陷；r19 四家群集（含 CODEX P1／P2）之處置字面已併入 v39 正文，本家 r19 sentinel 仍成立。

**碼證**: `git diff bfb5ad83 fa3d1b85 -- docs/FFSTAT_SPEC.md` → 38 行（版本 v39 註記、§C ①② `period_keys` 遞移／`CustomIndicatorDef.outputs`、Task 2.4 CDL 三類映射、§P TODO 同步必含清單）；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`rg -n 'v39|period_keys 指產生|CustomIndicatorDef|CDL pattern|TODO 同步必含' docs/FFSTAT_SPEC.md` → §C:56、Task 2.4:118、§P:152 同輪採納對位；`PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/ffstat-r20-run/numba venv/bin/python /tmp/ffstat-r20-run/probe_l1_r20.py` → rows_12h=1696、entropy 6/6、tail_risk 9/9、microstructure 25/25、pattern 9/9 output↔metadata 齊（現碼 z-score metadata 仍僅 window=21，屬 impl／§G⑦ 實證終審，非 v39 條文缺口）；`CustomIndicatorDef` 現碼尚無 `outputs` 欄，與 v39「定案後 impl」一致。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#676e3fa04e17; handoffs/reconcile/20260926-ffstatauto-x-review-r19/synth.md#a0af3f31eef2; data_cache/feature_klines/kline_cache.h5#b1ee5b9abcc1

---

## 必答

1. **(1a)** 本家 r19 僅 **COMPOSER-R19-P3-00**；v39 已寫入 r19 synth 採納之 CODEX P1-01／P1-02／P1-03 與 P2-04 對位句，**可閉合**。**(1b)** 逐字核對：`§C:56` 含完整遞移 `period_keys`、`outputs` 宣告與 VPIN z-score 上游參數 fail-closed；`Task 2.4:118` CDL raw／frequency／Consensus 三類 K；`§P:152` manifest 必含清單。原 CODEX 反例（custom plain frame、micro metadata 缺 bucket、manifest 漏測、pattern 映射歧義）在**現碼**仍可重現，但 v39 驗收／契約已釘死，屬待 impl，非 v39 新缺口。

2. **(2a)** v39 差分內**無**新 P0／P1。**(2b)** 可重現（spec 層＋只讀探針）：`/tmp/ffstat-r20-run/probe_l1_r20.py` 於 BTCUSDT 12h 1696 根驗 advanced 引擎 output↔metadata 覆蓋；Task 2.3 ① 仍要求 `params={}` 自訂雙窗 fail-closed，v39 以 `outputs` 欄補齊 ABI 敘述。

3. **(3a)** brief **fact-verified** ① L7 不以 NaN 率判死欄、`dead_feature_filter.py:77-82` 為 `notna().sum()`／`nunique` → **成立**。② TA-Lib 經 `TALibWrapper.compute`／`compute_batch` → **成立**（`talib_wrapper.py:316,347`）。**assumed**「同引擎衍生 K＝上游 K 遞推且上游參數可於引擎內取得」→ **條文上成立**（v39 §C ① ＋ Task 2.4 CDL）；entropy／tail_risk 探針無跨輸出衍生欄，契約退化为逐窗 `period_keys`；micro／pattern 衍生規則已寫入 SPEC，現碼 metadata 未達 v39 者由 impl／§G⑦ 收斂，不另列本輪 P1。**(3b)** 見 sentinel **碼證** 與 `probe_l1_r20.py` 摘要行。

4. **(4a)** brief「我沒查」：**①** entropy／tail_risk 引擎內衍生輸出——**未命中** blocking（6/6、9/9 齊，無 output 無 metadata 缺口）。**②** `CustomIndicatorDef.outputs` 必填後既有建構——**未命中** v39 SPEC 缺陷（預設 `custom_indicators: []`，現碼欄位缺 `outputs` 屬 impl 前狀態；v39 已標設定格式變更）。**③** Consensus 稀疏 NaN 下「上游最大 K」——**未命中** v39 條文缺口（v39 只定 K 規則，間歇 NaN 語意留 §G⑦／Task 2.3 驗收，非本輪 v39 差分矛盾）。**(4b)** `entropy_indicators.py:88-106`、`tail_risk_indicators.py:66-91` 欄級 metadata；`feature_config.py:451-457` 現 schema；`pattern_indicators.py:79-88` consensus 自 raw `pattern_df` 聚合。

5. **(5a)** **是**，v39 可 **`VERDICT: proceed`**（r19 阻擋群集已入 v39 正文；本輪無新 P0／P1）。**(5b)** 無。

---

ASSUMPTIONS_VERIFIED: v39 diff 38 行；r19 synth 採納表；R1–R7 rulings；L7／TA-Lib brief 前提；12h rows=1696  
TESTS_RUN: `git diff bfb5ad83 fa3d1b85 -- docs/FFSTAT_SPEC.md`；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → PASS；`rg` spec v39 錨點；`venv/bin/python /tmp/ffstat-r20-run/probe_l1_r20.py` → rc=0；開跑／收尾 `git status --short -- momentum api scripts tests docs templates config` 一致  
FAILURES_SEEN: 收尾 `rm -rf /tmp/ffstat-r20-run` 被環境 safety guard 拒絕，未改寫清理命令；workdir 可能仍在  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）  
產出: `handoffs/20260926-ffstatauto-x-review-r20-composer.md`  
TMP_CLEANUP: `rm -rf /tmp/ffstat-r20-run` denied；`/tmp/claude-501` 保留（未驗證存在）

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R19-P3-00

STATUS: DONE
