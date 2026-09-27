# FF-STAT SPEC v35 審查 r16 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R16  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R16-BRIEF.md`  
標的：`git diff f12e842e bf591b73 -- docs/FFSTAT_SPEC.md`；r15 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r15/synth.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針於 `/tmp/ffstat_r16_wd`（真實 `kline_cache.h5`）。

## COMPOSER-R16-P3-00

**斷言**: 本輪逐項核對後無需阻擋 v35 定案之 P0／P1 finding；r15 之 delta 逐位元組缺口已在 Task 2.3 ⑦ 與 §G⑦ 實例語法修補層關閉。

**碼證**: `git diff f12e842e bf591b73 -- docs/FFSTAT_SPEC.md` → v35 版註、Task 2.3 ⑦ 釘死欄集合 `\n` 連接 UTF-8 升序去重、delta `{"added","removed","reasons"}`＋`json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(',',':'))`、空 delta 物件、置換不變負例、核可紀錄 session id 與誠實邊界；§G⑦ 實例四元組、每步移除全部最大 K、無 recursive 即 blocked。`venv/bin/python /tmp/ffstat_r16_wd/probe_v35.py` → `permute_keys_arrays_equal=true`、`special_chars_stable=true`、`empty_delta_stable=true`、`unsorted_no_sort_keys_differs=true`。`momentum/FeatureEngineering/preprocessing/calibration.py:71-74` 欄集合 digest 與 v35 欄集合 sha256 規則一致（UTF-8 升序、`\n` 連接）。`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print(len(kline_frame('BTCUSDT','12h')))"` → `1696`；`PYTHONPATH=. venv/bin/python /tmp/ffstat_r16_wd/probe_selector.py` → `estimate_max_warmup_12h=2051`（全設定含 L2–L6，非單獨 K_max_tf）。`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#b4d89450c060; handoffs/reconcile/20260926-ffstatauto-x-review-r15/synth.md#97746788f6d8

---

## 必答

1. **(1a)** 本家 r15 僅 **COMPOSER-R15-P1-01**（delta／欄集合缺 canonical bytes）——v35 Task 2.3 ⑦ 已採納 r15 synth 同列修法，**可閉合**。**(1b)** 對 `git diff f12e842e bf591b73` 與 `docs/FFSTAT_SPEC.md:120` 逐字核對：欄集合與 delta 框架、置換不變測試、核可紀錄誠實邊界均落地；原反例（JSON 鍵序 permute 致 digest 漂移）在 v35 規則下 `probe_v35.py` 已不可重現。r15 未列之本家 ID 無。

2. **(2a)** v35 改動區（版註、Task 2.3 ⑦、§G⑦）**未發現新的 P0／P1 可證偽缺陷**。**(2b)** 欄集合／delta：`probe_v35.py`（見 sentinel）；12h 列數：`kline_frame('BTCUSDT','12h')`→1696；未跑全設定 FF run 或逐步選擇器 A run（brief 禁、8GB）。

3. **(3a)** **assumed** v35 逐位元組框架使語意相同 delta 得相同 sha256：**成立（SPEC＋探針）**——鍵序／陣列序 permute 後 digest 相同；未排序 `json.dumps` 仍可漂移，與 v35 要求 `sort_keys` 一致。**assumed** §G⑦ 12h 選擇器必終止且終止子集非空（含 recursive 供 mutant）：**未證成、未否證**——`2051+500>1696` 表示預設全設定在資格式下必 blocked／須子集，但逐步移除與真實 `F_max_tf` 需 A run；本輪未實跑選擇器鏈。**(3b)** 見上探針與 `estimate_max_warmup_12h=2051`、`ROWS_12H=1696`。

4. **(4a)** brief「我沒查」：**①** 逐步 A run 步數上限／耗時——**未命中**為本輪 P0／P1（無實跑反例）。**②** 多參數組合「最大週期」對 STOCH／ADOSC 等——v35 已寫「該實例最大週期」與 JSON 陣列組合實例，**未發現 v35 新文案與 `warmup_lookup.get_warmup_bars(ind, period)` 介面之矛盾**；組合內取 max 之細節仍留 impl。**③** `reasons` 值集合——Task 2.3 ⑦ 仍封閉為 `nan_rate_rule`｜`stable_samples_below_min`，**未命中**第三種原因之 v35 缺口。**(4b)** `docs/FFSTAT_SPEC.md:120`；`momentum/FeatureEngineering/atomic/warmup_lookup.py:80-84`；`venv/bin/python /tmp/ffstat_r16_wd/probe_selector_digest.py` → 選擇器 bundle 若自訂 top-level 鍵名仍可 digest 漂移（`wrapper_key_drift=true`）——屬 **P3 impl 風險**（v34 已有「序列化…sha256」，v35 只收窄 dumps 參數），**不單獨列 blocking ID**。

5. **(5a)** **是**，本版可 **`VERDICT: proceed`**（v35 關閉 r15 唯一 blocking delta 缺口）。**(5b)** 無。

---

ASSUMPTIONS_VERIFIED: `git diff f12e842e bf591b73 -- docs/FFSTAT_SPEC.md`；`handoffs/reconcile/20260926-ffstatauto-x-review-r15/synth.md`；`docs/FFSTAT_SPEC.md` Task 2.3 ⑦／§G⑦；`momentum/FeatureEngineering/preprocessing/calibration.py:71-74`；`momentum/FeatureEngineering/utils/dead_feature_filter.py:44-90`（brief fact）；真實 kline 12h rows  
TESTS_RUN: `git diff f12e842e bf591b73 -- docs/FFSTAT_SPEC.md` rc=0；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`venv/bin/python /tmp/ffstat_r16_wd/probe_v35.py` rc=0；`PYTHONPATH=. venv/bin/python /tmp/ffstat_r16_wd/probe_selector.py` rc=0；`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print(len(kline_frame('BTCUSDT','12h')))"` → 1696；`venv/bin/python /tmp/ffstat_r16_wd/probe_selector_digest.py` → wrapper_key_drift=true；開跑與收尾 `git status --short -- momentum api scripts tests docs templates config` 僅既有 `__pycache__` 變動  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）  
產出: `handoffs/20260926-ffstatauto-x-review-r16-composer.md`  
TMP_CLEANUP: 已嘗試刪除 `/tmp/ffstat_r16_wd`（保留 `/tmp/claude-501`）

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R15-P1-01

STATUS: DONE
