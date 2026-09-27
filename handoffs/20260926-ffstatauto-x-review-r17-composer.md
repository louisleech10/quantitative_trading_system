# FF-STAT SPEC v36 審查 r17 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R17  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R17-BRIEF.md`  
標的：`git diff bf591b73 3130de9b -- docs/FFSTAT_SPEC.md`；r16 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r16/synth.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針於 `/tmp/ffstat_r17_wd`（真實 `kline_cache.h5`）。

## COMPOSER-R17-P3-00

**斷言**: 本輪逐項核對後無需阻擋 v36 定案之 P0／P1 finding；r16 群集（`CODEX-R16-P1-01` 原因封閉、`CODEX-R16-P2-01` §G⑦ L1 展開單一來源）已在 v36 字面落地，本家 r16 sentinel 仍成立。

**碼證**: `git diff bf591b73 3130de9b -- docs/FFSTAT_SPEC.md`（30 行）→ v36 版註、Task 2.3 ⑦ 增 `reasons` 兩值封閉＋第三種原因即紅＋digest 前拒收；§G⑦ 改「L1 生成路徑參數展開為單一來源」、列 BBANDS／Keltner／SAREXT／MA／STDDEV 多軸、`canonical_parameter_json`、`_estimate_indicator_params` 總和對證。`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS。`venv/bin/python /tmp/ffstat_r17_wd/probe_r17.py` → `rows_12h=1696`、`estimate_max_warmup_12h=2051`、`capacity_default_full_config=false`、`v36_reason_spec=true`、`unknown_reason_probe.v36_would_reject_unknown=true`、`v36_g7_snippet_has_l1_expand=true`。`momentum/FeatureEngineering/utils/dead_feature_filter.py:77-82` → `notna().sum()` 與 `nunique(dropna=True)<2`（與 brief fact-verified 一致，非 NaN 率）。`PYTHONPATH=. venv/bin/python /tmp/ffstat_r17_wd/probe_l1_resolve.py` → `checked=72`、`mismatch_count=11`（現碼 `_resolve_params` 欄數與 `_estimate_indicator_params` 不一致；v36 以測試對證收斂，屬 impl 前預期紅，非 v36 文案新缺口）。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#e99f34daf19a; handoffs/reconcile/20260926-ffstatauto-x-review-r16/synth.md#8f3c2a1b0e9d

---

## 必答

1. **(1a)** 本家 r16 僅 **COMPOSER-R16-P3-00**；v36 未推翻其「v35 層無新 blocking」前提，**可閉合**。r16 群集 **CODEX-R16-P1-01**／**CODEX-R16-P2-01** 之 SPEC 修法已出現在 v36 diff（原因封閉、L1 展開＋對證句），**視為 r16 收斂項在 v36 已字面關閉**（impl 未驗）。**(1b)** **CODEX-R16-P1-01** 原反例：`probe_r17.py` 對 `constant_rule` → `v35_unknown_reason_rejection=false`、`v36_would_reject_unknown=true`（契約重跑）。**CODEX-R16-P2-01**：§G⑦ 已寫 resolved combo 與多軸笛卡兒積；`stoch_combo.digests_equal=false`（raw vs resolved）與 r16 一致，v36 要求 `canonical_parameter_json` 用已解析字典，**缺口已改為 impl 測試義務**。

2. **(2a)** v36 改動區**未發現新的 P0／P1 可證偽 SPEC 矛盾**（未捏造實質 finding）。**(2b)** 真實 kline：`rows_12h=1696`；delta 原因：`probe_r17.py`；現碼展開：`probe_l1_resolve.py`（BBANDS 120 vs 24 等 11 處）；未跑全設定 FF／逐步 A-run F_max。

3. **(3a)** **assumed①** §G⑦「12h 選擇器必終止且終止子集非空含 recursive」：**仍不成立為已保證強命題**（v36 保留「無 recursive ⇒ blocked」，未保證 survivor）；`2051+500>1696`。**assumed②** L1 展開與 `_estimate_indicator_params` 一致：**現碼不成立**（11／72 不一致）；**v36 契約層成立**（單一展開函式＋測試總和對證）。**(3b)** `probe_r17.py`、`probe_l1_resolve.py` 輸出見 sentinel。

4. **(4a)** brief「我沒查」：**①** A-run 步數／耗時——**未命中**本輪 P0／P1（無新反例）。**②** 組合型「週期型鍵」——v36 仍用敘述性「倍數表登記之週期型鍵」，**未在 SPEC 列封閉鍵表**；對照 `warmup_window.py:108-117` 之 combo 鍵列與 r16 ② 同型**殘留 impl 風險**，**不升級為 v36 blocking**。**③** 第三原因——v36 Task 2.3 ⑦ 已拒收，**對 r16 ③ 已關閉**。**(4b)** `docs/FFSTAT_SPEC.md` v36 ⑦ 句；`momentum/FeatureEngineering/warmup_window.py:108-117`；`probe_r17.py`。

5. **(5a)** **是**，v36 可 **`VERDICT: proceed`**（關閉 r16 blocking 之 SPEC 修補已入 diff；現碼對證紅留 impl）。**(5b)** 無。

---

ASSUMPTIONS_VERIFIED: v36 diff；r16 synth；`docs/FFSTAT_SPEC.md` Task 2.3 ⑦／§G⑦；`dead_feature_filter.py:44-90`；真實 HDF5 12h rows  
TESTS_RUN: `git diff bf591b73 3130de9b -- docs/FFSTAT_SPEC.md`；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`venv/bin/python /tmp/ffstat_r17_wd/probe_r17.py` rc=0；`PYTHONPATH=. venv/bin/python /tmp/ffstat_r17_wd/probe_l1_resolve.py` rc=0；`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print(len(kline_frame('BTCUSDT','12h')))"` → 1696；開跑／收尾 `git status --short -- momentum api scripts tests docs templates config` digest=`fd5d5d59a3856032ccd8ce2ba7ab898448064950d07da2093d933fde0febdbbc`  
FAILURES_SEEN: 收尾 `rm -rf /tmp/ffstat_r17_wd` 被環境拒絕（未繞過）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）  
產出: `handoffs/20260926-ffstatauto-x-review-r17-composer.md`  
TMP_CLEANUP: 已嘗試 `rm -rf /tmp/ffstat_r17_wd`；環境 PreToolUse 拒絕 rm-f，未換寫法；`/tmp/claude-501` 未觸碰

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R16-P3-00

STATUS: DONE
