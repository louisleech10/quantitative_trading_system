# GAP-2 B2 實作 code review（R15）— COMPOSER

**task-id**: `20260819-GAP2-B2-REVIEW-R15` | **family**: composer | **brief**: `handoffs/20260819-gap2-b2-review-BRIEF.md`
**審查標的**: commit `d026fbed`（Task 2.1／2.2：`factor_combiner.py`＋`marginal_ic.py` bootstrap 搬移＋B2 探針／測試）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → **45 passed** rc=0
- `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → **PASS** rc=0
- `bash scripts/gap2_mutation_probe.sh --batch B2` → **rc=0**；V-7／8／9 各 `RED ✓`＋`RESTORED GREEN ✓`（receipt `handoffs/run_receipts/20260818T222805Z-gap2-B2-probe.log`）
- `grep -E "from api\.|import api" momentum/Analysis/factor_combiner.py` → **0 命中**
- O4／O7 數值重算見段 D；`composite_keys` 鍵集比對見段 A

---

## Verdict：可進 B3

段 A Task 2.1／2.2 **逐條符合**；段 B 八項實作期決定經攻擊後**均可接受**（無需延伸檔阻擋項）；段 C 探針三條本輪重跑全綠、seam 真、無 skip；段 D 數值落 SPEC §G 帶；段 E registry 四條觸發**均未成立**。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `COMPOSER-R15-P3-00`）。

---

## 段 A — 契約符合度（Task 2.1／2.2）

| 要點 | 結論 | 碼證 |
|------|------|------|
| **2.1-1** `fit_scope` 守衛 | **符合** | `factor_combiner.py` L163–184：契約 `fit_scope_values`；`train`+全 True masks ⇒ `ValueError`；無 split ⇒ `not_applicable:no_holdout_split` |
| **2.1-2** complete-case test | **符合** | L199–206：`finite_rows = isfinite(X).all(axis=1) & isfinite(y)`；`rows_te = te & finite_rows`；`n_used_test < min_test_rows` ⇒ `insufficient_test_rows` |
| **2.1-3** train-only 符號 | **符合** | L213–229：`sign_source_X/y = X_tr/y_tr`（V-7 seam）；`sign==0` 或 NaN ⇒ `zero_train_ic`；全排除 ⇒ `all_zero_train_ic` |
| **2.1-4** 合成與 insample | **符合** | L231–249：`weight_source_ic = train_ic`（V-8 seam）；`equal`／`ic_weighted`；`_composite` 用 `normal_scores`；`composite_ic_train_insample` 於 **train 列**重算 z（`X_tr`） |
| **2.1-5** 對照與 delta CI | **符合** | L251–269：`top_train_single` 依 `|train_ic|`+原序 tie-break；`best_single_*` 只輸出；`delta_ci95` 成對 bootstrap 三陣列同索引 |
| **2.1-6** 結果欄／`to_dict()` | **符合** | `CompositeResult.to_dict()` 18 鍵 **==** 契約 `composite_keys`（本輪 `td==ck` True） |
| **不可做** | **符合** | 無 OLS／Ridge（`weights_method="ols"` ⇒ `ValueError` 測試 L267）；`best_single_test_ic` 未進符號／權重／delta 基準 |
| **邊界** | **符合** | k=1（O8）、全 zero train ic、complete-case NaN 剔除（`test_section_gates_and_scope`）、`n_bootstrap=1`、`weights` 和 ==1 |
| **2.2 探針** | **符合** | `gap2_mutation_probe.sh` B2 三列 V-7／8／9 對映唯一測試；本輪 rc=0 |
| **marginal_ic 改動** | **符合** | `git diff 35bd66a1 d026fbed -- marginal_ic.py`：**僅**刪除 `block_bootstrap_ci` 定義＋加 `from factor_combiner import block_bootstrap_ci` re-export（75 行 diff） |

---

## 段 B — 實作期決定複核（八項）

| # | 議題 | 結論 |
|---|------|------|
| **B1** complete-case 亦用於 train | **接受**。`rows_tr = tr & finite_rows` 與 test 同一 finite mask，保證 train／test 列對齊且與「survivors+label 全有限」語意一致；優於逐因子各自 finite（會造成列數不一致）。TODO 步驟 2 只寫 test 屬省略，非衝突。 |
| **B2** `test_ic_all` 在符號／權重前計算 | **可接受**。L217 僅供步驟 5 之 `top_train_single_test_ic`／`best_single_*`；L216 註明禁用于符號／權重；V-7／8 seam 變數名可機械探針。可讀性風險低——未構成 test 統計量滲入 train-only 決策。 |
| **B3** NaN train_ic 與 0 同歸 `zero_train_ic` | **可接受**。契約 feature reasons 僅三值（無 `label_degenerate`）；常數因子 `_spearman` ⇒ NaN ⇒ `sign=0` 與 B1 決策 B5 一致。區分 NaN vs 真 0 需 A1 增 reason，非 B2 範圍。 |
| **B4** `top_train_single` tie-break | **接受**。`max(kept, key=(abs(train_ic), -survivors.index))` 穩定、可重現；`best_single_feature` 同法。 |
| **B5** 循環 import／私有跨模組 | **可接受（B3 前）**。模組層 `marginal_ic→factor_combiner`、函式內 lazy `factor_combiner→marginal_ic`；兩種 import 順序 `block_bootstrap_ci is` 同一物件。`_spearman`／`_finite_or_none` 跨模組為技術債，升公開或共用小模組可留 B3+，非 B2 阻擋。 |
| **B6** `composite_ic_train_insample` | **符合 TODO 步驟 4**。L247–249：`comp_tr = _composite(X_tr)` 於 train 列 `normal_scores`，非借用 test z。 |
| **B7** `delta_ci95` 成對性 | **正確**。`block_bootstrap_ci` 對 `(comp_te, f_top_te, y_te)` 同一 `idx` 重抽；統計量 `spearman(c,y)-spearman(f,y)` 為成對差，與 SPEC／TODO 步驟 5 一致。 |
| **B8** O4 加法性 vs sequential Σmarg² | **一致**。本輪重算：`composite_ic=0.594695`；sequential margs `[0.308133, 0.280553, 0.297058, 0.297859]`；`ratio=0.991396` ∈ [0.90,1.10]；皆落 SPEC 三家帶（composite 0.574–0.595、margs 0.27–0.29、ratio 0.96–0.99）。測試用 `compute_marginal_ic` sequential 之 `marginal_ic`，與 SPEC「sequential 之 Σ marginal_ic²」字面一致。 |

---

## 段 C — 測試品質

- **mutation 探針**：本輪 `bash scripts/gap2_mutation_probe.sh --batch B2` rc=0；V-7／8／9 各 RED+RESTORED GREEN；post-restore 45 passed。
- **V-7 seam**：探針替換 `sign_source_X, sign_source_y = X_te, y_te`（L214 字面存在）；檔內 `test_mutation_test_sign_breaks_o8` monkeypatch `mic._spearman` 依長度偷換 train→test，O7 負 gross 案例必紅——**真 seam**。
- **V-8 seam**：探針替換 `weight_source_ic = test_ic_all`（L232）；`test_ic_weighted_uses_train_ic_reference` 獨立重算 train 權重並證 test 權重不同——**真 seam**。
- **V-9 seam**：探針強制 `b=1`；`test_delta_ci_uses_block_len_reference` 內 `_ref_block_ci` **未 import** `block_bootstrap_ci`，自寫 moving-block；block_len=7 與 1 對照——**真獨立參考**。
- **O4 容差**：`composite∈[0.55,0.61]`、`marg∈[0.26,0.31]`、`ratio∈[0.90,1.10]` 與 SPEC 附三家實跑同帶；本輪實跑落帶（見段 D），非廉價綠。
- **skip／smoke**：11 條測試無 skip；核心斷言含數值帶、鍵集、mutation、邊界 gate。

---

## 段 D — 數值正確性

| Oracle | 本輪重算 | SPEC／契約 |
|--------|----------|------------|
| O4 `composite_ic` | **0.594695** | ∈ [0.55, 0.61]（三家 0.574–0.595）✓ |
| O4 sequential margs | **[0.308, 0.281, 0.297, 0.298]** | 各 ∈ [0.26, 0.31] ✓ |
| O4 `Σmarg²/composite²` | **0.991396** | ∈ [0.90, 1.10]（三家 0.96–0.99）✓ |
| O7 O8 `S={f}` | train_ic=**0.471** gross=**−0.500** composite=**−0.500** | `== sign(train_ic)·gross`（+1×負 gross）✓ |
| 合成公式 | `Σ w·sign·normal_scores(f)` 等權 1/k′；ic_weighted \|train_ic\|/Σ | 實作 L239–244、測試 `test_ic_weighted_uses_train_ic_reference` ✓ |

---

## 段 E — registry「GAP-2 待補完」

本批僅 `combine_factors`／`CompositeResult`／bootstrap 搬移＋B2 探針；**未觸發** G2-R1（ML 橋）、G2-R2（forward-stepwise）、G2-R3（xsec）、G2-R5（nested holdout）。「為何現在不做」理由仍成立。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| pytest 45 passed | fact-verified | **覆核 rc=0** |
| mutation B2 rc=0 | fact-verified | **覆核 rc=0**（receipt 20260818T222805Z） |
| `marginal_ic` 與 `factor_combiner` import 順序無關 | fact-verified | **覆核** 兩順序 `block_bootstrap_ci is` True |
| 段 B 八項為合理選擇 | assumed→**verified** | 段 B 表逐項攻擊 |
| O4 帶寬非巧合 | assumed→**verified** | 本輪重算落帶 |
| `marginal_ic.py` 僅 bootstrap 搬移 | assumed→**verified** | diff 75 行僅搬移＋import |

---

## Findings（canonical）

## COMPOSER-R15-P3-00

**斷言**: 本輪對 commit `d026fbed` 段 A–E 與段 B 八項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B2` → rc=0 V-7/8/9 RED+GREEN；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS；O4 composite=0.594695 ratio=0.991396 margs∈[0.28,0.31]；O7 composite=−0.499590==sign(train)·gross；`to_dict()` 鍵集==`composite_keys`；`git diff 35bd66a1 d026fbed -- marginal_ic.py` 僅 bootstrap 搬移。

**來源摘要**: momentum/Analysis/factor_combiner.py#2c0dccc7de80；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0

本輪核對依據：Task 2.1 實作要點 1–6／不可做／邊界／驗證逐條對照 `factor_combiner.py`；段 B 八問獨立重判（complete-case、test_ic_all 位置、NaN/0、tie-break、lazy import、insample、成對 bootstrap、O4 加法性）；mutation 探針與 §G oracle 本機重跑；`marginal_ic` diff 確認 B1 契約未被觸動。未發現需修補後才能進 B3 之項。

---

## §1 必查（11 類摘要）

1. 矛盾：無。2. 漏項：B2 scope 內無。3. 不可測：pytest＋三 mutation＋數值帶。4. quant：符號／權重 train-only、complete-case、無 test 洩漏——實作＋V-7／8 鎖住。5–8. 過度工程／OOM／cache／API：N/A 或無問題。9. 測試：11 條＋三探針，無假綠。10. Agent 可執行：檔案／函式精確。11. 短命工：`block_bootstrap_ci` 搬移屬 Task 2.1 計劃內，B1 re-export 保留。

STATUS: DONE
