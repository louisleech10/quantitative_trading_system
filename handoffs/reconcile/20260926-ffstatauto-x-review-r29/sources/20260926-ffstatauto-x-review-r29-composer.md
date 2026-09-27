# FF-STAT TODO 審查 r29 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R29  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R29-BRIEF.md`  
標的：`git show a8ab8994`（r28 收斂：盤點三者完全相等、from-import 類別方法解析、391 步 golden／收據）；唯讀；動態探針 `/tmp/ffstat-a8ab-work/`。

## COMPOSER-R29-P3-00

**斷言**: 本輪對 `a8ab8994` 複核 r28 reconcile 採納修法後，未發現超出 manifest「實作前紅」之外、需阻擋 TODO 放行之新 P0／P1。

**碼證**: `source venv/bin/activate && python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-a8ab-work/inventory.json` → `INVENTORY_RC=0`（391 步、`unclassified` 空）；`pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py -k "inventory or class_bound or index_derived or dispatcher_inline" -q` → 5 passed in 25.42s；`python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → `MUTATION_STATIC_RC=0`；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；r28 原 mutation 重放（`scratchpad/ffstat_r29_mutation_p1_pytest.py`：對 `_ast_step_functions` 剔除 `_winsorize_2d_legacy_equivalent`）→ `failed_checks ['ast_vs_receipt']`、`SIM_RC=0`（第一條 equality 必紅，收據仍 391 步）；`python -c` 實測 `ast_count=391`、`TimeframeAligner._timeframe_seconds_keys` 在閉包內。

**類別**: other

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#0785e104efde; tests/_golden/ffstat/nan_propagation_classes.json#91481e1f1af5; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#9a209731e1c7; docs/manifests/FFSTAT.json#b8a89eeb15c8; handoffs/reconcile/20260926-ffstatauto-x-review-r28/synth.md

正文：`test_nan_propagation_inventory_complete`（`:171-182`）改為 `set(steps)==expected==golden` 三元相等，取代 r28 前之單向子集；`_called_qualified`（`:320-324`）以 `as_module.exists()` 區分 `from pkg import mod` 與 `from pkg.mod import Class`，閉包計 391 步；`test_inventory_closure_reaches_off_prefix_and_nested_steps`（`:353-354`）鎖 `_timeframe_seconds_keys`。inventory 腳本仍自 `_ast_step_functions()` 迭代（`stable_start_receipts.py:26-37`），與測試共用同一閉包實作。manifest `run_receipts` 已更新 391 步說明（`:48-51`）。

---

## 必答

1. **(1a)** 本家 r28 僅 `COMPOSER-R28-P3-00`，對 `a8ab8994` 複核可閉合；委員會採納之 `CODEX-R28-P1-01`／`P2-02` 機械修法已於同 commit 落地。**(1b)** P1-01：mutation 重放後 AST 集合 390、收據 391，模擬 `test_nan_propagation_inventory_complete` 之 `ast_vs_receipt` 失敗（見 sentinel **碼證**）；乾淨樹上該測試 17s 級通過。P2-02：`_timeframe_seconds_keys` 入 golden、閉包與專項斷言。

2. **(2a)** `a8ab8994` 未引入可重現之新 P0／P1。**(2b)** 否證：r28 mutation 不再使 inventory gate 假綠；`test_mutation_dispatcher_inline_rolling_is_caught` 仍通過（r27 內聯殘差未回歸）。

3. **(3a)** brief assumed（inventory 391／unclassified 0；mutation 後 inventory complete 必紅；from-import 類別解析）→ **成立**。**(3b)** 見 sentinel **碼證**；未實跑「name 同時為子模組檔與類別名」之合成反例，碼審 `as_module.exists()` 分支與 r28 synth 一致。

4. **(4a)** brief「我沒查」：**① 未命中**（三者同步縮小且仍相等時，`test_inventory_closure_reaches_off_prefix_and_nested_steps` 仍硬編碼要求 `_winsorize_2d_legacy_equivalent` 等六名在 `_ast_step_functions()` 內，與 golden 檔解耦，意外縮閉包仍紅）；**② 未命中**（盤點來源樹無 `ast.Import` 之內部 `import pkg.mod as m` 呼叫步驟函式；僅 numpy／pandas／polars 等外部別名，不在 `defined` 閉包域）。**(4b)** `test_ffstat_stable_start.py:342-355`；`rg 'ast\\.Import\\(' momentum/FeatureEngineering` → 0。

5. **(5a)** **`VERDICT: proceed`**（r28 阻擋項已收斂；TODO 可進實作，剩餘紅為 manifest 明示實作前狀態）。**(5b)** 無 P0／P1 blocker。

---

## Coverage risk

- 盤點 inventory ~13s；五支 `-k inventory…` ~25s；`test_nan_propagation_inventory_complete` 單獨 ~17s；mutation 靜態器與 TODOFMT 秒級；mutation 重放腳本 ~12s。
- 未跑全設定 FF run、§G⑦ 雙起點、真實 K 線分類抽驗探針（r28 已跑，本輪未重跑）。

ASSUMPTIONS_VERIFIED: 已讀 r29 brief、r28 synth、`a8ab8994` diff、manifest／收據／golden；上述命令已實跑  
TESTS_RUN: 見 sentinel **碼證** 與必答；`git status --short -- momentum api scripts tests docs templates config` 與開跑前一致（未改 scope 內檔）  
FAILURES_SEEN: 初版 `rm -rf /tmp/ffstat-a8ab-work` 被環境安全閘拒絕，改 `mkdir -p` 沿用目錄；無 hook 擋指令  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（審查唯讀）  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r29-composer.md  

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R28-P3-00

STATUS: DONE
