# FF-STAT SPEC v46 審查 r31 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R31  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R31-BRIEF.md`  
標的：`git show 8e5e55fc`（SPEC v46／manifest／stable_start 測試）、工作樹 `stable_mask.py`／`verify_l1_warmup_requirements.py`／`warmup_table.yaml`、收據 `20260928-ffstat-warmup-measure.json`；唯讀；探針 `/tmp/claude-501/`。

## COMPOSER-R31-P3-00

**斷言**: 本輪逐項核對 v46（R10 實測根數優先）之 SPEC／manifest／測試與量測收據後，未發現需阻擋 v46 放行之新 P0／P1；威脅模型＝意外漂移時，忽略 `k_by_params` 之 mutant 與 KAMA_233 實測優先斷言可證偽。

**碼證**: `git show 8e5e55fc --oneline` → v46 §C `k_by_params` 定義、Task 2.3①／2.4 表欄、R10 裁定列；`venv/bin/python /tmp/claude-501/r31_analyze2.py` → `ROW_COUNT=20535 UNRELIABLE=37 UNRELIABLE_1D_233=36`、`MAX_K=2049 ADXR timeperiod=233`、`KAMA233 measured=1400 formula=4660`；`venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_l1_mask_k_by_params_preferred_over_factor tests/feature_engineering/test_ffstat_stable_start.py::test_mutation_k_by_params_ignored_is_caught tests/feature_engineering/test_ffstat_warmup_table.py -q` → 16 passed in 4.74s、`PYTEST_RC=0`；`momentum/FeatureEngineering/preprocessing/stable_mask.py:141-151` 與 `tests/feature_engineering/test_ffstat_stable_start.py:57-64` 同序（先 `k_by_params` 後比例公式）；`scripts/verify_l1_warmup_requirements.py:471-497` 與 SPEC 不可信週期補值敘事一致。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#f4f843c365d4; tests/feature_engineering/test_ffstat_stable_start.py#ca8298e12fcb; handoffs/run_receipts/20260928-ffstat-warmup-measure.json#6f57491ccb49; momentum/FeatureEngineering/preprocessing/stable_mask.py#65f1546d0967; handoffs/20260927-ffstat-b4-redesign-rulings.md#392c39f6bdf5; docs/manifests/FFSTAT.json#17022e5e9c56

正文：v46 解決比例公式對 KAMA／MACDFIX 類指標之**高估**（遮罩過長）；採用值由跨週期 max 與查無走公式之雙軌組成。brief 假設「1d 週期 233 不可信時係數補值不低估」本輪**未否證亦未證實**（未重跑 `--only` 量測；收據顯示 36 筆 unreliable 為 1d＋period 233 型態）。brief「我沒查」① T3 之 `vfactor` 不在 `period_keys`，預設設定僅整數 `timeperiod` 入表鍵；② 表外參數如 STOCH fastk=377 測試已覆蓋走公式；③ 元件下限僅三組 composite，其餘未逐指標反例實跑——屬覆蓋風險非已證低估。

---

## 必答

1. **(1a)** v46 規則在**已量測且入表之 `k_by_params`** 路徑上取實測 max，較 v45 比例公式不易低估（實務上修正高估）；**查無**或量測管線補值路徑理論上仍可低估 K，但須具體指標＋實測 K 大於採用值之反例。**(1b)** 本輪**無**已跑通之低估反例；KAMA_233 為實測低於公式之正向例（1400 vs 4660）。

2. **(2a)** brief assumed（1d p233 不可信時 `ceil(period×factor_1d)` 不低於真實 K）→ **未否證**（資料前史 3329 根、eval 1000，brief 自述無法拉長 1d 反例窗）。**(2b)** 未重跑 `verify_l1_warmup_requirements.py` 全量（約 8 分鐘）；只讀收據 `UNRELIABLE_1D_233=36`／`UNRELIABLE=37` 與 `r31_analyze2.py` 摘要。

3. **(3a)** brief「我沒查」：**① 預設生產未命中**（`period_keys` 均整數週期；T3 `vfactor` 不參與 K 鍵）；**② 表外參數命中設計**（走比例公式，STOCH 377 有測）但無已證低估；**③ 未命中已證漏列**（COMPONENT_FLOOR 僅 KELTNER／FORCE_INDEX／KLINGER，未發現其他 composite 之實測 K 低於元件之下限反例）。**(3b)** `stable_mask.py:129-137`（非整數→None）；`test_ffstat_stable_start.py:137-138`（表外 STOCH）；`verify_l1_warmup_requirements.py:100-101,526-544`（元件下限三項）。

4. **(4a)** **可證偽**：`_expected_k`／`test_l1_mask_k_by_params_preferred_over_factor` 綁 v46；`test_mutation_k_by_params_ignored_is_caught` 剝除表欄必紅。**(4b)** 16 支 pytest 全綠（含 mutant）；見 sentinel **碼證**。

5. **(5a)** **`VERDICT: proceed`**（v46 文案、manifest Task 2.3／§V mutant 映射、R10 裁定與測試一致，可收斂 SPEC；1d 補值假設殘差記 coverage risk，不升 P0／P1）。**(5b)** 無 P0／P1 blocker。

---

## Coverage risk

- L1／warmup 表相關 pytest 16 支 ~5s；收據 JSON 統計秒級。
- 未重跑五週期×三標的量測全集（brief 允許 ~8 分鐘，本輪未跑）；未做 `--only`＋`--eval-window` 1d p233 否證探針。

ASSUMPTIONS_VERIFIED: 已讀 r31 brief、`8e5e55fc` diff、R10 裁定、stable_mask／adopt 工作樹片段、20535 筆收據 meta；上述命令已實跑  
TESTS_RUN: 見 sentinel **碼證** 與必答  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（審查唯讀）  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r31-composer.md  

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R29-P3-00

STATUS: DONE
