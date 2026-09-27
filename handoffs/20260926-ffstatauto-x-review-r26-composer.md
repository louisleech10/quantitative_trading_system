# FF-STAT TODO 審查 r26 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R26  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R26-BRIEF.md`  
標的：`git show 7fece564`（r25 收斂修補）；唯讀；探針 `/tmp/ffstat-r26-work/`。

## COMPOSER-R26-P3-00

**斷言**: 本輪逐項核對 `7fece564` 之 resume／lease／盤點五類拆分與 manifest「實作前紅」後，未發現超出 TODO 階段設計紅之外、需阻擋 TODO 放行之新 P0／P1。

**碼證**: `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r26-work/inventory.json` → rc=0；`pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete tests/feature_engineering/test_ffstat_stable_start.py::test_index_derived_step_has_no_warmup -q` → 2 passed；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → rc=0；`pytest --collect-only -q tests/feature_engineering/test_ffstat_stable_start.py` → 55 collected；`PYTHONPATH=<repo> venv/bin/python /tmp/ffstat-r26-work/probe_steps.py` → propagating／index_derived／helper／dispatcher／LEASE 抽驗行全出 rc=0；`venv/bin/python /tmp/ffstat-r26-work/ast_dispatch_probe.py` → DISPATCHERS=8 SUSPICIOUS=0；⑪／⑫ 仍紅（CalibrationError／TypeError）與 manifest 第 250 行「實作前紅之預期原因」一致。

**類別**: other

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#43093898d864; docs/manifests/FFSTAT.json#b57e2ccc756a; handoffs/reconcile/20260926-ffstatauto-x-review-r25/synth.md#b55c0d285cf7

正文：r25 synth 駁回本家 P1-01／P1-02（實作前 TypeError／CalibrationError 屬 Task 2.3 待實作）與部分採納 P1-03（SPEC v45 已寫「一切生成皆寫 stable_start」）；`7fece564` 已落地 codex P1-01–04 之測試修補（`:591-602` cache miss＋`resume_from_manifest` spy；`:687-691` `lease.path.name` 與 `finally release`；盤點 JSON 五類＋ AST dispatcher gate＋`test_index_derived_step_has_no_warmup`）。剩餘紅測為 manifest 已列之動工前狀態，非本輪修補引入之契約回歸。

---

## 必答

1. **(1a)** 本家 r25 三條均已閉合（駁回或文件釐清成立）。**(1b)** `COMPOSER-R25-P1-01`／`P1-02`：重跑 `pytest …::test_run_ic_first_requires_start_date_when_stationarizing` 等 → 仍 `TypeError: start_date`；`pytest …::test_paths_same_stable_start_and_masks` → 仍 `CalibrationError field=output_start`，與 manifest「實作前紅」及 synth 駁回理由一致。`P1-03`：`docs/FFSTAT_SPEC.md` v45 已補「一切生成皆寫 stable_start」；⑧ 仍 KeyError 屬實作前設計紅。inventory：`stable_start_receipts.py inventory --out /tmp/ffstat-r26-work/inventory.json` rc=0；`test_nan_propagation_inventory_complete` passed。

2. **(2a)** `7fece564` 未引入超出 manifest 預期紅的新 P0／P1。**(2b)** 否證仍為實作前紅：⑪ `feature_factory.py:2169`；⑫ `ffstat_helpers.py:232` `TypeError`；resume spy 邏輯已寫入 `:591-602` 但⑪ 首段 generate 未綠故本輪未執行到 spy 斷言（非 spy 語法缺陷）。

3. **(3a)** brief assumed「helper／column_filter 不產公開特徵值、dispatcher 輸出＝子步驟聯集」→ **成立**（五類拆分後語意與抽驗一致；原「not_a_data_step 不產值」已改為 dispatcher／index_derived 等明確類別）。**(3b)** `/tmp/ffstat-r26-work/probe_steps.py`：propagating 三例（relative_price first_finite=120、SMA=133、compute_cross=121，前綴 NaN 後才有限）；index_derived `(300,4)` row0 全有限；helper `compute_data_fingerprint` len=2；dispatcher rolling `(800,1)` first_finite=124。

4. **(4a)** brief「我沒查」：**① 未命中缺陷**（`prepare_stat_env` chdir 後 CGSA `work_dir` 在 tmp 下之 `data_cache/cgsa_work`，`resume_allowed` 條件與 L7 manifest gate 見 `feature_factory.py:1154-1198`，實作前⑪ 未跑通故未實證 spy）；**② 未命中**（`run_locks.py:41` 檔名含 64-hex hash，probe `LEASE name_has_hash=True`；⑫ 仍 TypeError 故 lease 斷言未跑）；**③ 未命中**（8 個 dispatcher AST 短名相交探针 SUSPICIOUS=0）。**(4b)** 見上 **碼證** 與 `tests/feature_engineering/test_ffstat_stable_start.py:187-190` AST 規則。

5. **(5a)** **`VERDICT: proceed`**（TODO 修補已收斂，剩餘紅為 manifest 明示之 Task 2.3 實作前狀態）。**(5b)** 無 P0／P1 blocker。

---

ASSUMPTIONS_VERIFIED: 已讀 brief、r25 synth、7fece564 diff、manifest 實作前紅條、SPEC v45；inventory／盤點／index_derived pytest 綠；git scope 未改  
TESTS_RUN: 見 sentinel **碼證**；另 `pytest …::test_paths_same_stable_start_and_masks` → 3 failed CalibrationError（預期）；`pytest …::test_run_ic_first_uses_own_window_not_previous` → 1 failed TypeError start_date（~92s，預期）；`git status --short -- momentum api scripts tests docs templates config` 與開跑前一致（僅既有 pycache／l65 髒）  
FAILURES_SEEN: 上述預期紅測失敗作為 r25 駁回／實作前紅複核證據，非 debug 目標  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r26-composer.md  
TMP_CLEANUP: 已刪 `/tmp/ffstat-r26-work`；保留 `/tmp/claude-501`

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R25-P1-01,COMPOSER-R25-P1-02,COMPOSER-R25-P1-03

STATUS: DONE
