# FF-STAT SPEC v37 審查 r18 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R18  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R18-BRIEF.md`  
標的：`git diff 3130de9b 5551dc5b -- docs/FFSTAT_SPEC.md`；r17 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r17/synth.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針於 `/tmp/ffstat_r18_wd`（真實 `data_cache/feature_klines/kline_cache.h5`）。

## COMPOSER-R18-P2-01

**斷言**: v37 在 §C 已要求倍數表每指標登記封閉 `period_keys` 且缺鍵 fail-closed（r17 `CODEX-R17-P2-01` 採納修法），但 **Task 2.4** 之 `warmup_table.yaml` 交付與 `test_ffstat_warmup_table.py` 驗收句仍只寫 family／係數，未列 `period_keys` 落點；實作者若只讀 Task 2.4 可能漏登記鍵集合，與 §C 漂移。

**碼證**: `docs/FFSTAT_SPEC.md:57` →「封閉之 `period_keys`…查表時…參數字典缺任一登記鍵 ⇒ fail-closed」。`docs/FFSTAT_SPEC.md:114`（Task 2.4 檔案段）→ `warmup_table.yaml` 僅「每指標記 family、各週期量得值、採用值」，無 `period_keys`。`rg -n 'period_keys' docs/FFSTAT_SPEC.md` → 僅版註與 §C（2 處正文），Task 2.4／2.3 驗收段除 STOCH 範例外無表結構要求。`rg -n '^  STOCH:' momentum/FeatureEngineering/atomic/warmup_table.yaml` → 0 命中（現碼仍缺 STOCH 條目；v37 版註要求補表屬 impl，但 Task 2.4 未綁定 `period_keys` 欄位）。`handoffs/reconcile/20260926-ffstatauto-x-review-r17/synth.md:12` → P2-01 處置明示「Task 2.4：…`period_keys`」。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#91ef7ea7ae63; handoffs/reconcile/20260926-ffstatauto-x-review-r17/synth.md#8f3c2a1b0e9d

修法：在 **Task 2.4** 之 `warmup_table.yaml` 交付句加入「每指標封閉 `period_keys`（與 §C 例示一致）」；驗收增「預設全設定每一 L1 計算呼叫之已解析參數字典，其鍵集合 ⊇ 表登記 `period_keys`，否則 fail-closed」；覆蓋腳本後繼者列印缺鍵指標清單。可行性：`talib_wrapper.py:236-252` 已有 `_PARAM_ORDER` 可作對照表；`parameter_generator.py:133-232` 已產 STOCH／ULTOSC 等已解析 dict，純資料單測即可驗鍵封閉，無需 full FF。

---

## 必答

1. **(1a)** 本家 r17 僅 **COMPOSER-R17-P3-00**（v36 無 blocking）；v37 未推翻其前提。**CODEX-R17-P1-01**／**P2-01** 非本家 ID，依 r17 synth：**P1-01** 以刪 §G⑦ 12h 子集選擇器＋§N 登記 `_estimate_indicator_params` 不一致收斂，**SPEC 層可閉合**；**P2-01** 在 §C 已寫 `period_keys`／STOCH 補表／缺鍵 fail-closed，**部分閉合**（Task 2.4 未同步，見本檔 P2-01）。**(1b)** **COMPOSER-R17-P3-00** 原反例為 v36 文案＋探針；`git diff 3130de9b 5551dc5b` 顯示 v37 改 L1 遮罩與 §G⑦，**不否定** r17 composer sentinel，且 r17 本家已 `proceed`（v36）。**CODEX-R17-P1-01** 原 BBANDS 120/24 探針仍適用於 §N 登記之現碼缺陷，**不再經 §G⑦ 選擇器對證**。**CODEX-R17-P2-01** 原 STOCH 缺表：v37 版註＋§C 要求補表與鍵封閉，Task 2.4 字面未跟進（P2-01）。

2. **(2a)** v37 未見新的 **P0／P1** SPEC 矛盾；主委自查之整指標 `max_period` 遮罩已由 §C「逐計算呼叫」與 Task 2.3 ① EMA_5／EMA_233 分 K mutant 覆蓋 **R3**。**(2b)** 真實 kline：`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print(len(kline_frame('BTCUSDT','12h')))"` → `1696`；`talib_wrapper.py:347-364` `compute_batch` 對 `params_list` 逐項 `compute(..., params, ...)` 後 `concat`，非混參拆欄；`momentum/FeatureEngineering/utils/dead_feature_filter.py:77-82` → `notna().sum()`／`nunique(dropna=True)<2`（與 brief fact-verified 一致）。

3. **(3a)** brief **fact-verified** 兩條：**成立**（死欄門檻；TA-Lib 經 `compute`／`compute_batch`）。brief **assumed**「每 L1 輸出點可取得該次呼叫參數字典」：**對 TA-Lib 與 `compute_batch` 路徑成立**；自訂路徑如 `volatility_indicators.py:47` Keltner 僅 `_compute_keltner(data)` 固定 `window=20`，與 config `ema_periods` 展開不一致屬 §N 既有 preset 問題，**不構成 v37 新缺口**；microstructure 於 `_compute_amihud` 等函式內以 `self.windows` 逐窗產欄，各欄 `window` 在輸出點可得。**(3b)** 見上碼證與 `rows_12h=1696`；未跑 full FF。

4. **(4a)** brief「我沒查」：**①** `compute_batch` 多組參數——**未命中** blocking（逐 `params` 呼叫 `compute`）。**②** 自訂指標參數可得性——**未命中** v37 blocking（Keltner 固定 20 已列 §N；Force Index／microstructure 輸出函式有 period／window）。**③** 刪 12h 選擇器後可證偽性——**未命中** blocking：§G⑦ 改 12h 只出 blocked 收據，§N／Task 2.3 ①（含 12h）②⑤ 覆蓋遮罩單項。**(4b)** `docs/FFSTAT_SPEC.md:86,122`；`talib_wrapper.py:347-364`；`volatility_indicators.py:186-204`；`microstructure_indicators.py:153-165`。

5. **(5a)** **是**，v37 可 **`VERDICT: proceed`**（r17 阻擋群集已在 SPEC 修補；殘留為 P2 文檔同步）。**(5b)** 無 P0／P1；非阻擋：**COMPOSER-R18-P2-01**。

---

ASSUMPTIONS_VERIFIED: v37 diff（53 行）；r17 synth；R1–R7 rulings；`dead_feature_filter.py:44-90`；`talib_wrapper.py:316,347`；真實 12h rows=1696  
TESTS_RUN: `git diff 3130de9b 5551dc5b -- docs/FFSTAT_SPEC.md`；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`rg -n 'period_keys|12h 子集' docs/FFSTAT_SPEC.md`；`rg -n '^  STOCH:' momentum/FeatureEngineering/atomic/warmup_table.yaml` → 0；`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print('rows_12h', len(kline_frame('BTCUSDT','12h')))"` → rows_12h 1696；開跑／收尾 `git status --short -- momentum api scripts tests docs templates config` 與 baseline 一致（含既有 `__pycache__`／golden 變動，無新增 scoped 修改）  
FAILURES_SEEN: none（未遇 PreToolUse hook block）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）  
產出: `handoffs/20260926-ffstatauto-x-review-r18-composer.md`  
TMP_CLEANUP: 已嘗試清理 `/tmp/ffstat_r18_wd`；若 `rm` 被環境拒絕則暫存仍留；`/tmp/claude-501` 未觸碰

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R17-P3-00

STATUS: DONE
