# FF-STAT SPEC v47 審查 r32 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R32  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R32-BRIEF.md`  
標的：`git show a0f1182e`（SPEC v47／manifest／v47 測試）、r31 `synth.md` 兩 P1 採納、工作樹 `stable_mask.py`／`verify_l1_warmup_requirements.py`／`warmup_table.yaml`／`l1_output_points.py`／`compute_guard.py`、收據 `20260928-ffstat-warmup-measure.json`；唯讀；探針 `/tmp/ffstat-r32-probe/`。

## COMPOSER-R32-P3-00

**斷言**: 本輪逐項核對 v47（r31 兩 P1 修補＋工作樹實作）之 SPEC／manifest／測試、收據對表不變量與預設設定 `build_catalog`→`instance_k` 全路徑後，未發現需阻擋 v47 放行之新 P0／P1；r31 反例 DX／ADA／1d／144 與 MA matype=4 已按 v47 契約收斂。

**碼證**: `git show a0f1182e --oneline` → v47 文案＋`test_table_k_ge_every_converged_measurement`／`test_mutation_adopted_k_below_measurement_is_caught`／`test_l1_mask_unmeasured_nonperiod_variant_fails_closed`；`venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_warmup_table.py -q` → 16 passed in 3.52s、`PYTEST_RC=0`；`venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py -k 'l1_mask or mutation_k_by_params or mutation_adopted or table_k_ge' -q` → 10 passed in 12.05s；`PYTHONPATH=. venv/bin/python scripts/verify_l1_warmup_requirements.py --only DX --timeframes 1d --symbols ADAUSDT --eval-window 1000 --no-write --receipt /tmp/ffstat-r32-probe/measure-dx.json` → rc=0、`k=1138`；`instance_k` 探針 → `DX144_K 1138`、`MA233_matype4 UnmeasuredVariantError`；`/tmp/ffstat-r32-probe/probe_variants.py`（`build_catalog` 1369 組）→ `OK=1369 UNMEASURED=0`；`compute_guard` 對 `StableMaskError` → `RE_RAISE_OK`。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#c5392ff5720f; momentum/FeatureEngineering/preprocessing/stable_mask.py#52a48a9fecdc; scripts/verify_l1_warmup_requirements.py#f7a6134dabb3; tests/feature_engineering/test_ffstat_warmup_table.py#8d96b3364bb3; handoffs/run_receipts/20260928-ffstat-warmup-measure.json#32bdf0d6d0e4; handoffs/reconcile/20260926-ffstatauto-x-review-r31/synth.md#cd80c7042149

正文：v47 將 r31 兩 P1 落地為（①採用值 ≥ 任一已收斂量測、②全參數鍵＋`variants` fail-closed）；工作樹 `adopt`／`canonical_params`／`check_variant` 與 committed 測試一致。brief「我沒查」③ `canonical_params` 對 list／字串參數之正規化與 ② 進階引擎使用者改窗長——本輪無已證誤擋或低估反例，記 coverage risk。

---

## 必答

1. **(1a)** r31 兩 P1（`CODEX-R31-P1-01`／`P1-02`）於工作樹已閉合：表 DX `timeperiod=144`→1138、MA 僅 `matype=0` 變體入表；`test_table_k_ge_every_converged_measurement` 與 `test_l1_mask_unmeasured_nonperiod_variant_fails_closed` 綁定。**(1b)** DX／ADA／1d／144 重跑量測 `k=1138`；MA `matype=4` 於 `instance_k` 拋 `UnmeasuredVariantError`（不再誤用 K=233）。

2. **(2a)** v47 修補未觀測到新契約缺口；預設設定 1369 組 catalog 參數皆通過 `instance_k`（無 `UnmeasuredVariantError`）。**(2b)** 無新可重現低估反例；r31 反例重放見 sentinel **碼證**。

3. **(3a)** brief **assumed**（採用值不低於已收斂量測、係數取已收斂最大）→ **成立**於現行收據＋表（逐筆不變量測試全綠）。**(3b)** `test_table_k_ge_every_converged_measurement` 實跑 PASS；未另跑全量五週期量測（主委 fact-verified 收據已重跑）。

4. **(4a)** brief「我沒查」：**① 未命中誤擋**（`build_catalog`×`instance_k` 0 失敗）；**② 未命中已證誤擋**（自訂／進階固定參數登記，未跑使用者改 `cvar_alphas` 等反例）；**③ 未命中已證正規化 bug**（MAVP 等 list 參數未實跑）。**(3b)** ① 碼證：`probe_variants.py` 摘要；②③ 碼證：`stable_mask.py:148-168`、`verify_l1_warmup_requirements.py:359-370`（自訂條目寫死參數）。

5. **(5a)** **`VERDICT: proceed`**（v47 SPEC／manifest／測試與工作樹實作一致，r31 P1 修補可收斂；殘差 coverage 不升 P0／P1）。**(5b)** 無 P0／P1 blocker。

---

## Coverage risk

- warmup_table 16 支 ~3.5s；L1 遮罩選定 10 支 ~12s；`probe_variants` ~2s；DX `--only` 子集 ~1.3s。
- 未逐引擎審 b4 其餘未提交改動（brief 另輪）；未跑全量 `verify_l1_warmup_requirements.py`（~8 分鐘）。

ASSUMPTIONS_VERIFIED: 已讀 r32 brief、r31 synth、`a0f1182e`、工作樹 stable_mask／adopt／compute_guard 片段；上述命令已實跑  
TESTS_RUN: 見 sentinel **碼證** 與必答  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（審查唯讀）  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r32-composer.md  

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R31-P3-00

STATUS: DONE
