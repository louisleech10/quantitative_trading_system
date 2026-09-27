# FF-STAT TODO 審查 r30 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R30  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R30-BRIEF.md`  
標的：r29 synth 對 `CODEX-R29-P1-01` 之駁回、`git show efb4c96e` 寫入 `docs/manifests/FFSTAT.json` 之 risk_mitigation 界線；唯讀；探針暫存 `/tmp/claude-501/`。

## COMPOSER-R30-P3-00

**斷言**: 本輪逐項核對 r29 駁回理由與現行盤點契約後，未發現需阻擋 TODO 放行之新 P0／P1；威脅模型＝意外漂移時，閉包意外縮小仍必紅，三者同步縮小須手動改 golden／重產收據，歸蓄意等價。

**碼證**: `python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/claude-501/ffstat-r30-work/inventory.json` → `INVENTORY_RC=0`（391 步）；`venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete -q` → 1 passed in 15.24s、`PYTEST_RC=0`；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；`/tmp/claude-501/ffstat_r30_sim.py` → `accidental_only ast_vs_receipt=False`（僅 AST 少 `_winsorize_2d_legacy_equivalent` 時與收據 391 不等）、`triple_sync_green True 390`（三者同步刪同一步可相等，屬手動協調）；`rg -l nan_propagation_classes\\.json scripts tests handoffs/run_receipts/ffstat_probes` → 僅讀路徑＋`stable_start_receipts.py:110` 只寫 `--out` 收據；`test_ffstat_stable_start.py:171-182` 三元 `set(steps)==expected==golden`；manifest `risk_mitigation` 第 231 行與 r29 synth 駁回敘事一致（`efb4c96e`）。

**類別**: other

**來源摘要**: handoffs/reconcile/20260926-ffstatauto-x-review-r29/synth.md#3614e638e572; docs/manifests/FFSTAT.json#cfdf0e220780; tests/feature_engineering/test_ffstat_stable_start.py#0785e104efde; tests/_golden/ffstat/nan_propagation_classes.json#91481e1f1af5; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#9a209731e1c7; handoffs/run_receipts/ffstat_probes/stable_start_receipts.py

正文：複核主委駁回 `CODEX-R29-P1-01` 之理由——golden 分類表無 repo 內產生器、刪列必現於 commit diff；凍結清單可同樣四方同步刪改，與 codex 所提獨立 frozen contract 同屬無限回歸，與使用者 2026-09-11「無法收斂即停、歸蓄意等價」一致。意外漂移：收據檔為版本化產物，AST  alone 縮小即 `assert set(steps)==expected` 失敗；`test_inventory_closure_reaches_off_prefix_and_nested_steps`（`:342-355`）另鎖 `_winsorize_2d_legacy_equivalent` 等六名須在 `_ast_step_functions()` 內。

---

## 必答

1. **(1a)** **接受** r29 synth 對 `CODEX-R29-P1-01` 之駁回理由；本家 `COMPOSER-R29-P3-00` 與駁回後界線一致，列入 `CLOSED`。**(1b)** 無非蓄意可重現序列使 AST、收據、golden 三者同步縮小且測試仍綠——同步須手動刪 golden 列、重跑 `stable_start_receipts.py inventory` 寫新收據，並改動閉包實作或種子，皆屬可審 diff 之蓄意協調。

2. **(2a)** `efb4c96e` 之 risk_mitigation 與現行測試／腳本未引入新 P0／P1。**(2b)** 無可重現反例（意外僅 AST 縮小已上列模擬必紅）。

3. **(3a)** brief assumed（不存在非蓄意序列使三者同步縮小）→ **成立**。**(3b)** `rg nan_propagation_classes\\.json` 全 repo 僅 manifest／測試讀取、`stable_start_receipts.py:29-37` 讀 golden、`main:110` 只寫 `--out`；`scripts/` 零引用該檔名。

4. **(4a)** brief「我沒查」：**① 未命中**（無腳本／測試寫入 `tests/_golden/ffstat/nan_propagation_classes.json`）；**② 未命中**（`inventory` 子命令不寫 golden，只合併讀取後輸出收據）。**(4b)** `handoffs/run_receipts/ffstat_probes/stable_start_receipts.py:23-37,103-111`；`tests/feature_engineering/test_ffstat_stable_start.py:179-180` 只讀 golden。

5. **(5a)** **`VERDICT: proceed`**（駁回理由成立、界線已入 manifest，可戳記後進 b4）。**(5b)** 無 P0／P1 blocker。

---

ASSUMPTIONS_VERIFIED: 已讀 r30 brief、r29 synth、`efb4c96e` manifest 差分、盤點測試與 inventory 腳本；上述命令已實跑  
TESTS_RUN: 見 sentinel **碼證**；`git status --short -- momentum api scripts tests docs templates config` 與開跑前一致  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（審查唯讀）  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r30-composer.md  

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R29-P3-00

STATUS: DONE
