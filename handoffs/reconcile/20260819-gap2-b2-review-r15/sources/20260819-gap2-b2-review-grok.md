# GAP-2 B2 實作 code review（R15）— GROK

**task-id**: `20260819-GAP2-B2-REVIEW-R15`｜**family**: grok｜**輪次**: R15  
**brief**: `handoffs/20260819-gap2-b2-review-BRIEF.md`  
**審查標的**: commit `d026fbed`（Task 2.1／2.2：`factor_combiner.py`＋`marginal_ic.py` bootstrap 搬移＋B2 探針／測試）  
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit／push**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → **45 passed** rc=0（~22s）
- `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → **PASS**（`test_mutation_test_sign_breaks_o8` 真跑）rc=0
- `bash scripts/gap2_mutation_probe.sh --batch B2` → **rc=0**；V-7／8／9 各 `RED ✓`＋`RESTORED GREEN ✓`；receipt `handoffs/run_receipts/20260818T222930Z-gap2-B2-probe.log`
- `grep -E "from api\.|import api" momentum/Analysis/factor_combiner.py` → **0 命中**
- import 順序 `marginal_ic→factor_combiner` 與反向皆可載入，且 `marginal_ic.block_bootstrap_ci is factor_combiner.block_bootstrap_ci`
- O4／O7／O8 數值重算見段 D；`to_dict()` 鍵集 == 契約 `composite_keys`（18 鍵）見段 A
- `git diff 35bd66a1 d026fbed -- momentum/Analysis/marginal_ic.py`：僅刪 `block_bootstrap_ci` 定義＋模組層 re-export（50 行／+2−48）

---

## Verdict：可進 B3

Task 2.1／2.2 主路徑與 §G O4／O8／O9 **契約符合、數值落帶、探針可證偽**；段 B 八項實作期決定經獨立攻擊後**均可接受**（無須延伸檔阻擋）；段 E 四條殘留觸發**均未成立**。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `GROK-R15-P3-00`）。

---

## 段 A — 契約符合度（Task 2.1／2.2）

| 要點 | 結論 | 碼證 |
|------|------|------|
| **2.1-1** `fit_scope` 守衛 | **符合** | `factor_combiner.py` L163–184：`fit_scope` ∈ 契約枚舉；`train` 缺 mask ⇒ `not_applicable:no_holdout_split`；全 True ⇒ `ValueError("fit_scope=train with all-True masks")`；`oos_guarantees=None` 佔位 |
| **2.1-2** complete-case test | **符合** | L199–206：`finite_rows = isfinite(X).all(1) & isfinite(y)`；`rows_te = te & finite_rows`；`n_used_test < min_test_rows` ⇒ `insufficient_test_rows`；train 同下限 ⇒ `insufficient_train_rows` |
| **2.1-3** train-only 符號 | **符合** | L213–229：`sign_source_* = X_tr,y_tr`（V-7 目標行）；`sign==0`／非有限 ⇒ `excluded[name]=zero_train_ic`；全排除 ⇒ `all_zero_train_ic` |
| **2.1-4** 權重／合成／insample | **符合** | L231–249：`weight_source_ic = train_ic`（V-8）；`equal→1/k'`、`ic_weighted→|train_ic|/Σ`；`composite=Σ w·sign·normal_scores`；insample 於 `X_tr` 重算 z |
| **2.1-5** 對照／delta CI | **符合** | L251–269：`top_train_single` 只看 `|train_ic|`；`best_single_*` 只輸出、不進 delta；`delta_ci95` 對 `(comp,f_top,y)` 成對 block bootstrap |
| **2.1-6** `to_dict()` 鍵集 | **符合** | 18 鍵 **==** `load_survivor_contract()["marginal_ic_section_keys"]["composite_keys"]["keys"]`（本輪比對 True） |
| **不可做** | **符合** | 無 OLS／Ridge 路徑（`weights_method="ols"` ⇒ `ValueError`，測試 L267）；符號／權重不讀 test IC；`best_single_test_ic` 非比較基準 |
| **邊界** | **符合** | k=1（O8）、全 zero train ic、NaN complete-case、`n_bootstrap=1`、weights 和==1、`block_len=0` raise |
| **註** `selected_on="test"` | **契約優先** | TODO／SPEC 散文提及該欄；契約 `composite_keys` **無**此鍵；實作對齊契約鍵集（SoT），非缺欄 |
| **2.2 三 case** | **符合** | `gap2_mutation_probe.sh` B2：V-7→`test_o8_sign_from_train_negative_case`；V-8→`test_ic_weighted_uses_train_ic_reference`；V-9→`test_delta_ci_uses_block_len_reference`；本輪 rc=0 |
| **marginal_ic 改動** | **符合** | diff 僅 bootstrap 搬移＋re-export；B1 計算契約未被觸動 |

---

## 段 B — 實作期決定複核（八項；優先攻）

| # | 議題 | 結論 |
|---|------|------|
| **B1** train 亦用 complete-case | **接受**。同一 `finite_rows` 切 `rows_tr`／`rows_te`，使符號／權重列宇宙與合成「survivors+label 全有限」一致。逐因子 finite 會讓各 `train_ic` 列數不同，且與 composite 聯合列不一致。本輪 NaN 注入（s2 前 200 列）：per-factor `ic_s1` n=3000 vs complete-case n=2800、IC 差 ~0.003；combiner `n_used_train=2800` 仍 `ok`。TODO 步驟 2 只寫 test＝省略，非互斥。 |
| **B2** `test_ic_all` 於符號／權重前算 | **可接受**。L217 註明「禁用於符號／權重」；消費僅步驟 5 之 `top_*_test_ic`／`best_single_*`。變數名 `weight_source_ic`／`sign_source_*` 使 V-7／8 可機械替換。可讀性風險低，未構成 test 統計量滲入 train-only 決策。 |
| **B3** NaN 與 0 同歸 `zero_train_ic` | **可接受**。契約 feature reasons 含四值（含 `label_degenerate`，A1-7）；combiner 對常數因子 `_spearman→NaN→sign=0→zero_train_ic`，與 B1 常數處置一致。細分 NaN vs 真 0／label 退化需消費語意＋測試，非 B2 阻擋。 |
| **B4** tie 依原 survivors 序 | **接受**。`max(..., key=(abs(ic), -survivors.index))` 決定性；`best_single_feature` 同法。 |
| **B5** 循環 import／私有跨模組 | **可接受**。模組層 `marginal_ic→factor_combiner.block_bootstrap_ci`；`combine_factors` 內 lazy import `_spearman`／`normal_scores`／`_finite_or_none`。兩種 import 順序 identity 成立。升公開或抽共用小模組屬可選整潔項（TODO 白名單無新模組）；非 B2 阻擋。 |
| **B6** `composite_ic_train_insample` | **符合 TODO 步驟 4**。`comp_tr=_composite(X_tr)`：train 列 `normal_scores`＋同 w／sign，非套用 test z。 |
| **B7** `delta_ci95` 成對性 | **正確**。`block_bootstrap_ci` 對三陣列共用同一 `idx`；統計量 `spearman(c,y)−spearman(f,y)`＝成對差，對齊 TODO 步驟 5／SPEC D5。 |
| **B8** O4 加法性視角 | **與 SPEC 一致**。測試取 `compute_marginal_ic(...).sequential[*].marginal_ic` 再 `Σmarg²/composite²`；本輪 ratio=**0.991396**、composite=**0.594695**、margs∈[0.2806,0.3081]，皆落 SPEC 三家帶與測試帶。 |

---

## 段 C — 測試品質

- **mutation 探針（本輪重跑）**：`bash scripts/gap2_mutation_probe.sh --batch B2` → **rc=0**；receipt `20260818T222930Z`：V-7／8／9 皆 RED＋RESTORED GREEN；baseline／post-restore 45 passed。
- **V-7 seam**：檔內目標行 `sign_source_X, sign_source_y = X_tr, y_tr` 可被換成 `X_te,y_te`；檔內 `test_mutation_test_sign_breaks_o8` 於 lazy-import 後 monkeypatch `mic._spearman`（長度==n_train 時偷換 test 段）⇒ O7 負 gross 之 O8 斷言紅——**真 seam**（長度耦合可接受；權威 seam 仍是檔案字面替換）。
- **V-8 seam**：`weight_source_ic = train_ic` → `test_ic_all`；測試獨立重算 `|train_ic|/Σ` 且證與 test 權重差 >0.02——**真 seam**。
- **V-9**：`_ref_block_ci` 測試內自寫 moving-block，**未** import 待測 `block_bootstrap_ci`；`block_len=7` exact、`=1` 不等——**真獨立參考**＋參數被消費。
- **O4 容差**：帶寬對齊 SPEC 已附三家實跑；本輪一次落帶（段 D），非過寬廉價綠。
- **skip／smoke**：11 條無 `pytest.skip`／`@pytest.mark.skip`；核心含數值帶、鍵集、gate、mutation。

---

## 段 D — 數值正確性

| Oracle | 本輪重算 | 判定 |
|--------|----------|------|
| O4 `composite_ic`（equal） | **0.594694902760858** | ∈[0.55,0.61]；三家 0.574–0.595 ✓ |
| O4 `ic_weighted` 差 | **1.29e-4** | ≤1e-3 ✓ |
| O4 sequential margs | **[0.30813, 0.28055, 0.29706, 0.29786]** | 各 ∈[0.26,0.31]；約落三家 0.27–0.29 鄰近 ✓ |
| O4 `Σmarg²/composite²` | **0.9913957350617214** | ∈[0.90,1.10]；三家 0.96–0.99 ✓ |
| O8／O7 `S={f}` | train_ic=**+0.47125**；gross=**−0.49959**；composite=**−0.49959**；sign=+1 | `composite == (+1)·負 gross`（atol 1e-12）✓ |
| 合成公式 | `Σ w·sign·normal_scores(f)`；equal 1/k′；ic_weighted \|train_ic\|/Σ | 實作 L239–244＋V-8 測試 ✓ |

母體對照：Spearman≈`(6/π)asin(0.3)≈0.582`；本輪 0.595 落預期帶。

---

## 段 E — registry「GAP-2 待補完」

本批只落地 `combine_factors`／`CompositeResult`／`block_bootstrap_ci` 搬移＋B2 三探針；**未**接 ML 橋、**未**做 forward-stepwise 選擇、**未**接 xsec、**未**改 holdout／`independent_oos_validation_allowed`。G2-R1／R2／R3／R5 觸發條件**均未成立**；「為何現在不做」理由仍成立。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 本輪 |
|------------|------|
| pytest 45 passed | **覆核 rc=0** |
| mutation B2／B1 聲稱 | B2 **覆核 rc=0**（本家 receipt 20260818T222930Z）；B1 本輪未重跑（非本批必答；assumed 保留） |
| mutation_probe_check／R1=0 | **覆核 PASS／0 命中** |
| import 雙序 identity | **覆核 True** |
| 段 B 八項契約內合理 | **逐項攻擊後接受**（見段 B） |
| O4 帶寬非巧合 | **本輪重算落 SPEC 三家帶** |
| `marginal_ic.py` 僅 bootstrap 搬移 | **diff 逐段確認** |

---

## Findings（canonical）

## GROK-R15-P3-00

**斷言**: 本輪對 commit `d026fbed` 段 A–E（含段 B 八項實作期決定）逐項核對後無 finding。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B2` → rc=0（V-7／8／9 RED+RESTORED GREEN；receipt `handoffs/run_receipts/20260818T222930Z-gap2-B2-probe.log`）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS；O4 composite=0.594695、ratio=0.991396、margs∈[0.2806,0.3081]；O7/O8 composite=−0.499590 == sign(train_ic)·gross；`CompositeResult.to_dict()` 鍵集 == 契約 `composite_keys`（18）；`git diff 35bd66a1 d026fbed -- momentum/Analysis/marginal_ic.py` 僅 bootstrap 搬移＋re-export；雙 import 序 `block_bootstrap_ci` identity；R1 grep 0 命中。

**來源摘要**: momentum/Analysis/factor_combiner.py#2c0dccc7de80；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0；tests/momentum/Analysis/test_factor_combiner.py#becfc45d514f；scripts/gap2_mutation_probe.sh#65fea620d5af

核對依據：Task 2.1 要點 1–6／不可做／邊界／驗證對照源碼；段 B 八問獨立重判（complete-case train、test_ic_all 位置、NaN/0、tie-break、lazy import、insample、成對 bootstrap、O4 加法性視角）；mutation 與 §G oracle 本機重跑；registry 四殘留觸發未成立。未發現需修補後才能進 B3 之項。

---

## §1 必查（11 類摘要）

1. 矛盾：無（契約鍵集／散文 `selected_on` 以契約為準）。  
2. 漏項：B2 scope 內無（B3–B5 未做屬計劃）。  
3. 不可測：pytest＋三 mutation＋數值帶＋鍵集。  
4. quant：train-only 符號／權重、complete-case、成對 bootstrap——實作＋V-7／8／9 鎖住。  
5–8. 過度工程／OOM／cache／API：本批 N/A 或無問題；Python 3.9 相容。  
9. 測試：11 條＋三探針；無 skip；O4 非廉價綠。  
10. Agent 可執行：檔案／函式／驗證明確。  
11. 短命工：`block_bootstrap_ci` 搬移屬 Task 2.1 計劃內覆蓋風險，B1 re-export 保留。

STATUS: DONE
