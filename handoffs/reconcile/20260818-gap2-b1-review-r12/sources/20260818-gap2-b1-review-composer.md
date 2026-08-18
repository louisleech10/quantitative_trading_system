# GAP-2 B1 實作 code review（R12）— COMPOSER

**task-id**: `20260818-GAP2-B1-REVIEW-R12` | **family**: composer | **brief**: `handoffs/20260818-gap2-b1-review-BRIEF.md`
**審查標的**: commit `022650ff`（Task 1.0–1.3；既有檔零改動）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` → **10 passed** rc=0
- `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py -q` → **28 passed** rc=0
- `bash scripts/gap2_mutation_probe.sh --batch B1` → **rc=0**；十條 `RED ✓`＋`RESTORED GREEN ✓`（receipt `handoffs/run_receipts/20260818T152101Z-gap2-B1-probe.log`）
- `grep -nE '"semi_partial_rank_ic"|"rank_normal"' momentum/Analysis/marginal_ic.py` → **0 命中**（字面值經 `_load_literals()`／`_reason()` 讀契約）
- O2／O7／O1b 數值重算見段 D

---

## Verdict：可進 B2

段 A 契約四 Task **逐條符合**；段 B 十項實作期決定經攻擊後**均可接受**（見下表，無需 A1-7 阻擋項）；段 C 探針十條本輪重跑全綠、無廉價 skip；段 D 數值與 SPEC §G 一致；段 E registry 四條觸發**均未成立**。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `COMPOSER-R12-P3-00`）。

---

## 段 A — 契約符合度（Task 1.0–1.3）

| Task | 結論 | 要點 |
|------|------|------|
| **1.0** | **符合** | 頂層 24 鍵＝`SURVIVOR_CONTRACT_TOP_KEYS`／測試①；`_doc` 含 (a)(b)(c) 三句（契約 L3）；各 `*_keys` 帶 `type`/`required`/`nullable`＋`additional_properties:false`；`reasons` 三組唯一列舉；loader 多鍵／少鍵／`allowed≠[false]`／檔缺／JSON 壞皆 `ContractValidationError`。`survivor_contract.py` 之 frozenset 與測試①之 `expected` 為 **TODO 明示之雙鎖**，非完整 schema 複列。 |
| **1.1** | **符合** | `normal_scores` 非有限／n<2 raise；`fit_projection` 空 basis ⇒ `beta=[mean]`、`ss_tot==0` ⇒ `r2_train=0.0`；共線不 raise；三函式無 mask／`fit_on_full`。 |
| **1.2** | **符合** | `_one` L493–495：退化 gate **先於** `_spearman`；`fit_scope` typed、`train`+全 True masks raise；`oos_guarantees`／`pass_class` 恆 `None`；預算 gate L403–416 **先於**矩陣計算、超限整體空輸出；`n_regressions` 僅 `fit_projection` 累計（spy ⑮）；`train_ic` 排序唯一來源；loo 依名稱排除；`extra_candidates` 去重；字面值經 `_load_literals()`，無硬編碼輸出字面。 |
| **1.3** | **符合** | 探針十條 case 目標行存在檢查、`mkdir` 鎖、cp 還原、rc=2 設計錯、B2–B5 未定義 rc=2；本輪十條 RED+RESTORED GREEN。 |

---

## 段 B — 實作期決定複核（十項）

| # | 議題 | 結論 |
|---|------|------|
| **B1** 節級 status | **接受**。`any_ok` 段（L551–558）正確處理「loo/sequential 超預算、removed 空集合 ok」⇒ 節 `not_computed:candidate_budget_exceeded`；B4 前端 `status!="ok"` 不畫表語意正確。removed 空 ⇒ view `ok` 合理（無候選可算，非 NA 語意）。 |
| **B2** views 子 schema | **現狀可進 B3**；`view_status_keys` 可選補強（B3 validator 遞迴物件層已能驗 `{status,reason}`），非 B1 阻擋。 |
| **B3** conditioning_set 等欄 | **不多餘**；已在契約 `per_feature_keys`／`sequential_keys`／`removed_candidate_keys`（`test_to_dict_keys_match_contract` ⑪ 鎖死）。sequential 之 `conditioning_set` 可審計；loo 可由 survivors 推得但輸出欄位契約已定。 |
| **B4** min_test_rows 借用 train 下限 | **合理**；TODO 步驟 4「train 同」且 params 無 `min_train_rows`。B4 orchestrator 顯式傳參即可；A1-7 加 `min_train_rows` 屬錦上添花非必須。 |
| **B5** 常數 label ⇒ NaN 但 status ok | **維持**；契約 feature reasons 僅三個，不宜擅加。`marginal_ic=None`+`status=ok` 可消費端依 `|gross_ic|<ε` 解讀；若未來要 reason 再走 A1 增 `label_degenerate`。 |
| **B6** block_bootstrap_ci | **可接受**；`block_len>n` 截 n、全非有限 ⇒ `None`、`<1` raise，與 TODO 步驟 7 一致。 |
| **B7** MarginalICParams 預設 | **可接受**；鏡像 B4 config、測試用 `FAST` 顯式覆寫；B4 仍會顯式傳，無隱性漂移風險。 |
| **B8** full_sample + masks=None | **不踩禁令**；`fit_scope` 為呼叫方 typed 輸入，None 視全 True 是省略語意非「由 masks 推 fit_scope」。 |
| **B9** with_root 字面 | **B1 可接受**；兩值與 `ic_reporter.normalize_analysis_status` 對齊，root 契約在 report 側。B4 注入時可再集中讀取。 |
| **B10** schema vs SPEC 3.1 | **涵蓋**；逐條對照 SPEC L179：`symbol`/`timeframe`/`case_id`∈`survivor_file_keys`；`sample_scope` 五鍵∈`sample_scope_keys`；`event` 定義∈`event_definition_keys`；cache identity∈`event_identity_keys`（欄位同義、用途分檔內／cache）；`split`+`row_identity`∈`split_keys`+`row_identity_keys`；`provenance` 十三鍵齊；`survivors[]`∈`survivor_record_keys`；OOS 四欄+`statistic` 在 `survivor_file_keys`。24 頂層鍵＝TODO 1.0 步驟 1 pointer 清單。B3 ⑭ checklist 機檢留待 Task 3.1。 |

---

## 段 C — 測試品質

- **mutation 探針**：本輪 `bash scripts/gap2_mutation_probe.sh --batch B1` rc=0；V-1..6／17a／18／21／22a 各 RED+RESTORED GREEN；post-restore 39 passed。
- **V-5** `test_sequential_order_by_train_ic`：`w` 特徵使 train 弱／test 強（L383–393），實測 `names[-1]=="w"` 且 test IC 排序會把 `w` 提前——**能區分** train vs test 排序突變。
- **V-3** `test_o6_rank_invariance`：全域 `_spearman→pearson` 時 `gross_ic`（raw）與 `marginal_ic`（秩殘差）**皆**偏離（本輪重算：O2 變換後 pearson 秩殘差與 spearman 差 **0.0137** > 1e-12）。紅路徑較寬但**仍可證偽**；更窄 oracle 可只斷 `marginal_ic` 鍵（建議性，非阻擋）。
- **檔內探針** `test_mutation_test_fit_projection_breaks_o7`：以 O7 參考 β 注入 test-fit 變體，是**真 seam**（直接對應 V-1 語意）；形狀判斷耦合 O7 fixture，可讀性略差但有效。
- **`_reference_marginal_ic`**：獨立 `rankdata`/`lstsq`/`spearmanr`，**未 import** `normal_scores`/`fit_projection`——真獨立參考。
- **廉價綠燈**：無 skip；容差與 SPEC §G 表一致。**O1b** 本輪走 **`ok` 分支**：`marginal_ic=0.000185`（≤0.02），非 degenerate 分支。

---

## 段 D — 數值正確性

| Oracle | 本輪重算 | 預期 |
|--------|----------|------|
| O2 Δ\|marginal−gross\| | **0.005825** | ≤0.02 ✓（與 brief codex 實跑 −0.0058 一致） |
| O7 train-fit vs test-fit | marginal=**−0.513**；\|train−test\| ref **>0.3** | test_o7 斷言 ✓ |
| O7 insample vs marginal | insample=**−0.0050**；差 **0.508** | >0.3 ✓ |
| ic_retained_ratio | `test_negative_gross_ratio_is_one` 負 gross ⇒ ratio≈1；\|gross\|<1e-12 ⇒ None | ✓ |
| bootstrap | `rng.integers(0,n-b+1)` 起點、串接切 n、成對索引 | moving-block 實作正確 |

---

## 段 E — registry「GAP-2 待補完」

本批僅純函式＋契約 loader＋探針；**未觸發** G2-R1（ML 橋）、G2-R2（forward-stepwise）、G2-R3（xsec）、G2-R5（nested holdout）。「為何現在不做」理由仍成立。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| load 10 passed / marginal_ic 28 passed | fact-verified | **覆核 rc=0** |
| mutation B1 rc=0 十條 | fact-verified | **覆核 rc=0**（receipt 20260818T152101Z） |
| 段 B 十項為合理選擇 | assumed→**verified** | 段 B 表逐項攻擊 |
| schema 涵蓋 SPEC 3.1 | assumed→**verified** | 段 B10 逐條對照 |
| 十條 mutation 最窄 oracle | assumed→**partial** | V-3 略寬但仍可證偽；其餘九條窄 |

---

## Findings（canonical）

## COMPOSER-R12-P3-00

**斷言**: 本輪對 commit `022650ff` 段 A–E 與段 B 十項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` → 10 passed rc=0；`venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py -q` → 28 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B1` → rc=0 十條 RED+GREEN；O2 Δ=0.005825、O7 diff=0.508、O1b 走 ok 分支 marginal=0.000185；`marginal_ic.py` L493–495 退化先於 Spearman、`grep` 無硬編碼 statistic 字面。

**來源摘要**: momentum/Analysis/marginal_ic.py#a5de8252b792；momentum/Analysis/contracts/ic_survivor_contract.json#ed2872020c6e；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

本輪核對依據：契約符合度對照 TODO Task 1.0–1.3 實作要點／不可做／邊界／驗證；段 B 十問獨立重判；mutation 探針與 §G oracle 本機重跑；數值重算與 SPEC 附值交叉驗證。未發現需修補後才能進 B2 之項。

---

## §1 必查（11 類摘要）

1. 矛盾：無。2. 漏項：B1 scope 內無。3. 不可測：各 Task 有 pytest＋探針。4. quant 假設：train-fit 投影、退化先於 Spearman、無 test 排序洩漏——實作與測試鎖住。5–8. 過度工程／OOM／cache／API：N/A 或無問題。9. 測試：28+10 條＋十 mutation，無假綠。10. Agent 可執行：檔案／函式精確。11. 短命工：`block_bootstrap_ci` 搬移已標 Task 2.1，屬計劃內。

STATUS: DONE
