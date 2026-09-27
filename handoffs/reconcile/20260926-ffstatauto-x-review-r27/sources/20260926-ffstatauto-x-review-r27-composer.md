# FF-STAT TODO 審查 r27 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R27  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R27-BRIEF.md`  
標的：`git show 22908436`（r26 收斂：`_called_qualified`、manifest 一條、`test_dispatcher_call_resolution_is_class_bound`）；唯讀；探針 `/tmp/ffstat-r27-work/`、`/tmp/ffstat-r27-mut/`。

## COMPOSER-R27-P3-00

**斷言**: 本輪逐項核對 `22908436` 之限定名派發修補與 r26 reconcile 採納項後，未發現超出 manifest「實作前紅」之外、需阻擋 TODO 放行之新 P0／P1。

**碼證**: `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r27-work/inventory.json` → rc=0；`pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete tests/feature_engineering/test_ffstat_stable_start.py::test_index_derived_step_has_no_warmup tests/feature_engineering/test_ffstat_stable_start.py::test_dispatcher_call_resolution_is_class_bound -q` → 3 passed in 0.45s；`pytest --collect-only -q tests/feature_engineering/test_ffstat_stable_start.py` → 56 collected；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → rc=0；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；隔離複本（git archive 至 `/tmp/ffstat-r27-mut`）將 `DerivedOperatorEngine.compute_all` 改為 `return self._compute_low_cardinality_cols(layer1_df, [])` 後 inventory test → `1 failed`（`AssertionError` on `DerivedOperatorEngine.compute_all`），clean target 同測仍綠；`venv/bin/python /tmp/ffstat-r27-work/probe_steps.py` → propagating／index_derived／column_filter／dispatcher 抽驗行 rc=0。

**類別**: other

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#ea03890afd0c; docs/manifests/FFSTAT.json#7a5aad7addf4; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#5e688567450c; handoffs/reconcile/20260926-ffstatauto-x-review-r26/synth.md

正文：`22908436` 以 `_called_qualified`（`tests/feature_engineering/test_ffstat_stable_start.py:193-214`）取代短名集合，dispatcher gate 改為 `called & (set(steps) - {name})`（`:186-190`）；新增 `test_dispatcher_call_resolution_is_class_bound`（`:217-225`）鎖 L2／L3 同名 `_rolling_last_rank_pct` 不跨類。manifest Task 2.3 條已登記該具名測試。r26 `CODEX-R26-P1-01` 之 mutation 反例現可被 inventory 拒絕，與 reconcile 採納修法一致。

---

## 必答

1. **(1a)** 本家 r26 僅 `COMPOSER-R26-P3-00` sentinel，經本輪複核可閉合（r26 proceed 前提在派發限定名修補後成立）。**(1b)** inventory 重跑：`stable_start_receipts.py inventory` rc=0；`test_nan_propagation_inventory_complete`／`test_dispatcher_call_resolution_is_class_bound` 綠；codex r26 mutation（錯類 `_compute_low_cardinality_cols`）在 `/tmp/ffstat-r27-mut` 現為 inventory 紅。

2. **(2a)** `22908436` 未引入新 P0／P1；修補收斂 r26 P1-01。**(2b)** 否證：mutation 複本 inventory `1 failed`；clean target `3 passed`（盤點＋index_derived＋class_bound）。⑪／⑫ 仍為 manifest 明示之實作前紅（本輪未重跑長測）。

3. **(3a)** brief assumed：helper／column_filter 不直接產公開特徵欄、dispatcher 輸出來自其所呼叫之已分類步驟 → **成立**（限定名 gate ＋ mutation 否證後可驗收；brief「dispatcher（9）」與收據 class=dispatcher 計數 8 之落差仍僅文數不一致，測試未鎖 count，不臆列 finding）。**(3b)** `/tmp/ffstat-r27-work/probe_steps.py`（真實 1h×300）：propagating `cross=1`、`momentum=5`、`ratio=1` 等；index_derived `(300,4)` row0 全 finite；column_filter `dead_n=0`；helper 盤點抽樣三函式名；dispatcher `derived (300,0)`、`rolling (300,270)`（derived 空欄因輕量 k 無 L1 特徵配置，非 gate 缺陷）。

4. **(4a)** brief「我沒查」：**① 未命中**（r26 codex 已實跑 resume spy；本輪未重跑 ~24s probe）；**② 未命中**（`run_locks.py:41` 檔名含 `config_hash`；r25 測試讀 `lease.path.name`）；**③ 未命中**（短名誤過缺陷已由 `_called_qualified`＋具名測試與 mutation 反例收斂）。**(4b)** `test_ffstat_stable_start.py:193-225`；`run_locks.py:41`；r26 synth 對 ①② 之 codex 碼證仍有效。

5. **(5a)** **`VERDICT: proceed`**（r26 reconcile 修補已落地，TODO 可進實作階段；剩餘紅為 manifest Task 2.3 實作前狀態）。**(5b)** 無 P0／P1 blocker。

---

# Coverage risk

- collect-only → 56 tests in ~0.04s。
- 盤點三測（inventory＋index_derived＋class_bound）→ ~0.45s；mutation 靜態器秒級；mutation 複本 inventory → ~2.9s。
- `probe_steps.py` 真實切片 → ~3.1s。未跑全設定 FF、§G⑦、⑪ resume 全參或 ⑫ 長測。

ASSUMPTIONS_VERIFIED: 已讀 r27 brief、r26 synth、22908436 diff、manifest 增補條、composer/codex r26 交件；inventory／class_bound／mutation 反例／probe 已實跑  
TESTS_RUN: 見 sentinel **碼證**；`git status --short -- momentum api scripts tests docs templates config` 與開跑前一致（僅既有 pycache／l65 髒）  
FAILURES_SEEN: 預期 mutation 複本 inventory fail；probe 內 rolling numba fallback 日誌（仍產出 270 欄）；`/tmp` workdir 刪除指令被安全閘拒絕  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r27-composer.md  
TMP_CLEANUP: `rm -rf /tmp/ffstat-r27-work /tmp/ffstat-r27-mut` 被環境安全閘拒絕，目錄仍待清理；`/tmp/claude-501` 未列入刪除

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R26-P3-00

STATUS: DONE
