# GAP-2 B1 實作 code review（R12）— GROK

**task-id**: `20260818-GAP2-B1-REVIEW-R12`｜**family**: grok｜**輪次**: R12  
**brief**: `handoffs/20260818-gap2-b1-review-BRIEF.md`  
**審查標的**: commit `022650ff`（Task 1.0–1.3；`git show --stat` 僅新增檔）  
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit／push**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` → **10 passed** rc=0
- `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py -q` → **28 passed** rc=0
- `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py` → **PASS**（3 探針真跑）rc=0
- `bash scripts/gap2_mutation_probe.sh --batch B1` → 本輪首兩次遇鎖 rc=3；其後讀取並行實例完成之 receipt `handoffs/run_receipts/20260818T152334Z-gap2-B1-probe.log` → **十條 RED ✓ + RESTORED GREEN ✓**、post-restore 39 passed、腳本結語 ✅（等同 rc=0 路徑）
- `bash scripts/gap2_mutation_probe.sh --batch B2` → **rc=2**（未定義，符合 Task 1.3）
- `bash -n scripts/gap2_mutation_probe.sh` → rc=0
- `grep -n "from api\.\|import api" momentum/Analysis/marginal_ic.py momentum/Analysis/survivor_contract.py` → 0
- `grep -nE '"semi_partial_rank_ic"|"rank_normal"' momentum/Analysis/marginal_ic.py` → 0（輸出字面經 `_load_literals()`）
- O1b／O2／O7／V-3／節級 status 邊角重算見段 C／D／B1

---

## Verdict：需修補後進 B2

Task 1.0–1.3 主路徑與 §G oracle **數值正確、契約符合、探針可證偽**；段 E 四條殘留觸發未成立。但段 B-1 節級 `status` 聚合在「loo／sequential 超預算且 removed 非空」時會讓 `status="ok"` 搭配 `per_feature={}`，與 B5「`status!="ok"` 才不畫表」語意衝突（→ `GROK-R12-P1-01`）。另 V-3 探針紅燈來自 raw `gross_ic`，**不能**證明 `marginal_ic` 走秩相關（→ `GROK-R12-P2-01`）。建議先熱修節級 status 規則（或書面改 B5 消費端閘門）再進 B2；P2 可於後續探針收斂。

---

## 段 A — 契約符合度（Task 1.0–1.3）

| Task | 結論 | 要點 |
|------|------|------|
| **1.0** | **符合** | 頂層 24 鍵＝`SURVIVOR_CONTRACT_TOP_KEYS`／測試①；`_doc` 含 (a) 事件樣本訓練／(b) OOS 四欄同讀／(c) timestamps canonical＋`separators=(",",":")`；各 `*_keys`＝`{additional_properties:false, keys:{…:{type,required,nullable}}}`；`reasons` 三組唯一列舉；loader 檔缺／JSON 壞／多鍵／少鍵／`allowed≠[false]` 皆 `ContractValidationError`。`SURVIVOR_CONTRACT_TOP_KEYS`＋測試① `expected` 為 TODO 明示冷啟動雙鎖，非 schema 全表複列。 |
| **1.1** | **符合** | `normal_scores` 非有限／n<2 raise；空 basis ⇒ `beta` 長度 1（截距＝mean）、`ss_tot==0` ⇒ `r2_train=0.0`；共線不 raise；三函式無 mask／`fit_on_full`。 |
| **1.2** | **符合（主路徑）** | `_one` L493–495：`var(r_te)<=thr` **先於** `_spearman`；`fit_scope` typed、`train`+全 True raise；OOS 兩欄恆 `None`（`with_root` 測試 helper）；預算旗標於矩陣前設定、超限視角空輸出且 `n_regressions` 不含略過視角；排序唯一 `train_ic`；loo 依名稱排除；`extra` 去重減 survivors；statistic／projection／reason 字面經契約。**例外**：節級 `status` 聚合見 P1-01。 |
| **1.3** | **符合** | 目標行 `grep -cF` 缺 ⇒ rc=2；`mkdir` 鎖 rc=3；`$BACKUP_DIR` cp 還原；rc=2 collection＝設計錯；B2–B5 未定義 rc=2；receipt 十條 RED+RESTORED GREEN。 |

---

## 段 B — 實作期決定複核（十項）

| # | 議題 | 結論 |
|---|------|------|
| **B1** 節級 status | **不完整（MAJOR）**。空 removed＋loo 超限 ⇒ 節 `not_computed` 正確（L552–554）。但 **removed 非空且 loo 超限** 時 `views.removed_candidates=ok` ⇒ 節 `status=ok`、`per_feature={}`（本輪重算見碼證）——B5 若只看節 status 會畫空表。封閉方案：節 `ok` **僅當** `loo` 或 `sequential` 為 `ok`（removed 成功不抬升節 status）；或 B5 改閘 `views.loo.status=="ok"`。removed 空集合標 view `ok`（無「no_removed」reason）可維持。→ P1-01 |
| **B2** views 子 schema | **B1 可接受**；B3 前可選加 `view_status_keys`（A1-7 可見），非阻擋。 |
| **B3** conditioning_set／feature／step | **保留**；已在契約 `per_feature_keys`／`sequential_keys`／`removed_candidate_keys`，⑪ 鎖死。sequential 之 `conditioning_set` 可審計必要。 |
| **B4** 借用 `min_test_rows` 當 train 下限 | **可接受**；TODO「train 同」、params 無 `min_train_rows`。A1-7 非必須。 |
| **B5** 常數 label → IC=`None` 但 status=`ok` | **維持**（契約僅三 feature reason）。本輪重算：全常數 label ⇒ `status=ok`、四 IC 欄皆 `None`。消費端以 `None` 解讀；若要 reason 再走 A1（`label_degenerate`）。 |
| **B6** bootstrap | **可接受**；`block_len>n` 截 n、全非有限 ⇒ `None`、`n_bootstrap<1` raise。 |
| **B7** Params 預設 | **可接受**；鏡像 B4；測試 `FAST` 顯式覆寫。 |
| **B8** `full_sample`+masks=`None` | **不踩禁令**；`fit_scope` 為輸入，None＝省略全 True。 |
| **B9** `with_root` 字面 | **B1 可接受**；`"oos"`／`"full_sample_research_only"` 寫死於 helper（L244–246），對齊 root／`normalize_analysis_status`，非 survivor 契約列舉。B4 注入時宜單一讀取點。 |
| **B10** schema vs SPEC L179 | **涵蓋**。`survivor_file_keys` 24 鍵含身分三欄／OOS 四欄／`sample_scope`／`split`／`provenance`／`survivors`／`composite`／`removed_candidates`；`sample_scope_keys`＝`{kind,event,n_samples_total,n_samples_test,degraded}`；`event_definition_keys`≡`event_identity_keys`（檔內 vs cache，鍵集同）；`split_keys`+`row_identity_keys`、`provenance_keys`（含 `algorithm_version`）、`survivor_record_keys`（IC 快照＋marginal 欄）均對上 L179 義務清單。B3 ⑭ checklist ⊆ 鍵集機檢仍待 Task 3.1。 |

---

## 段 C — 測試品質

- **mutation 探針**：receipt `20260818T152334Z-gap2-B1-probe.log` 十條 V-1／2／3／4／5／6／17a／18／21／22a 皆 RED+RESTORED GREEN；baseline／post-restore 39 passed。
- **V-5**：O7+`w`（train 弱／test 強）⇒ sequential 末位=`w`，且 `test_ic["w"]>test_ic["f"]`——**能區分** `order_key_ic=_rank_ic(test)` 突變。
- **V-3**：本輪將 `_spearman` monkeypatch 為 `pearsonr` 後重跑 O6 變換對——**唯一**超過 1e-12 的鍵為 `s1.gross_ic`（Δ≈0.067）與 `s1.ic_retained_ratio`（Δ≈0.288）；**所有** `*.marginal_ic`／`marginal_ic_train_insample` Δ=0。紅燈證明 raw gross 用了秩相關，**不**證明殘差路徑 `marginal_ic` 用秩相關。→ P2-01
- **檔內** `test_mutation_test_fit_projection_breaks_o7`：形狀判斷耦合 O7 fixture，但是真 seam（注入 test-fit β ⇒ 參考斷言紅）；可接受，非阻擋。
- **`_reference_marginal_ic`**：自寫 `rankdata`/`lstsq`/`spearmanr`，**未** import 待測原語——真獨立。
- **廉價綠燈**：無 skip。**O1b** 本輪走 **`ok` 分支**：`marginal_ic≈1.85e-4`（≤0.02），非 `residual_degenerate`。

---

## 段 D — 數值正確性

| 項目 | 本輪重算 | 判定 |
|------|----------|------|
| `normal_scores` | `norm.ppf(rank_avg/(n+1))` 與手工一致 | ✓ |
| `fit_projection` `ss_tot==0` | `r2_train==0.0` | ✓ |
| O2 Δ(marginal−gross) | **−0.00582505**（marginal≈0.38526，gross≈0.39108） | 與 SPEC／brief −0.0058 一致；\|Δ\|≤0.02 ✓ |
| O7 vs train-fit ref | absdiff **0**（atol 1e-12） | ✓ |
| O7 vs test-fit ref | absdiff **≈0.503** >0.3 | ✓ |
| O7 insample vs marginal | absdiff **≈0.508** >0.3 | ✓ |
| 負 gross ratio | gross≈−0.391，`ic_retained_ratio==1.0` | ✓ |
| bootstrap | `starts=rng.integers(0,n-b+1,size=n_blocks)`、串接切 n、成對索引 | 正確 moving-block |

---

## 段 E — registry「GAP-2 待補完」

本批僅契約 loader＋純函式＋探針；**未**接 ML、未做 forward-stepwise 選擇、未接 xsec、未改 holdout／`independent_oos_validation_allowed`。G2-R1／R2／R3／R5 觸發條件**均未成立**；「為何現在不做」理由仍成立。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 本輪 |
|------------|------|
| load 10／marginal_ic 28 passed | **覆核 rc=0** |
| mutation B1 十條 RED+GREEN | **覆核**（receipt 20260818T152334Z；本家遇鎖後讀並行完成件） |
| 段 B 十項皆契約內合理 | **B1 不成立**（P1-01）；其餘九項接受 |
| schema 涵蓋 SPEC 3.1 | **成立**（B10 逐條） |
| 十條 mutation＝最窄 oracle | **V-3 不成立**（P2-01）；其餘九條可接受 |

---

## Findings（canonical）

## GROK-R12-P1-01

**斷言**: `compute_marginal_ic` 在 `loo`／`sequential` 因 `max_survivors_for_loo` 整體 `not_computed`、但 `removed_candidates` 視角仍標 `ok`（removed 非空）時，節級 `status` 會成為 `"ok"` 且 `per_feature={}`；此與 B5「節 `status!="ok"` 才不畫 survivor 表」的消費語意衝突，且作者只特殊處理了 removed **空集合** 情況。

**碼證**: `momentum/Analysis/marginal_ic.py` L551–558（`any_ok`；僅當 `not (loo_budget_ok or removed_names)` 才把空 removed ok 打回）。VERIFY：`MarginalICParams(max_survivors_for_loo=2)`、survivors=`[s1,s2,f]`、extra=`[z]`（O2 資料加與 y 弱相關之 z）→ `status=="ok"`、`reason is None`、`views.loo.status=="not_computed"`、`per_feature=={}`、`removed_candidates["z"]["status"]=="ok"`、`n_regressions==1`。對照空 removed 同預算：`status=="not_computed"`（`test_budget_survivors_whole_not_computed`）。RECHECK: 重跑上列構造。SPEC Task 5.1：節 `status!="ok"` ⇒ 不畫表。

**來源摘要**: momentum/Analysis/marginal_ic.py#a5de8252b792

[MAJOR] 信心度=High。會怎麼失敗：B5／報告消費端只讀節 status → 顯示「ok」空表，誤以為 loo 已算。  
修法（擇一寫死）：(a) 節 `ok` **僅當** `views["loo"]` 或 `views["sequential"]` 為 `ok`（removed 成功不抬升節 status；超預算理由仍可留在 views）；(b) 維持現狀但 B5／契約 `_doc` 明定消費端必須閘 `views.loo.status`（並加測試鎖死「loo 超限＋removed 非空 ⇒ 節 not_computed 或前端不畫」）。建議 (a) 在 B1 熱修，成本低於前端分叉。

---

## GROK-R12-P2-01

**斷言**: B1 mutation V-3（`_spearman` 內 `spearmanr→pearsonr`）對映之 `test_o6_rank_invariance` 在突變下轉紅，**唯一**逾 1e-12 的鍵是 raw 路徑的 `s1.gross_ic`／派生 `ic_retained_ratio`；所有特徵的 `marginal_ic`（與 `marginal_ic_train_insample`）在 base vs `f×c`／`s1³` 變換下差值仍為 0——因此該探針**不能**證明「`marginal_ic` 使用秩相關」。

**碼證**: `scripts/gap2_mutation_probe.sh` L42（V-3）；`tests/.../test_marginal_ic.py` L236–248（O6 斷言含 `marginal_ic` 與 `gross_ic`）。VERIFY：monkeypatch `mic._spearman`→`pearsonr` 後重跑 O2 O6 變換對，失敗鍵僅 `[('s1','gross_ic',≈0.067),('s1','ic_retained_ratio',≈0.288)]`；`*.marginal_ic` 全 0。原因：投影後已是秩常態殘差，Pearson≈Spearman，單調變換不破 `marginal_ic` 不變性。RECHECK: 同上 monkeypatch 實驗。

**來源摘要**: tests/momentum/Analysis/test_marginal_ic.py#60860d0762d5

[MINOR] 信心度=High。會怎麼失敗：日後有人把殘差改回 raw／在殘差路徑改用 pearson，V-3／O6 仍可能綠（假陰性於 marginal 路徑）。  
修法：收窄 oracle——例如構造「秩常態殘差上 Spearman≠Pearson」之合成（重尾／非單調 tie 結構），只斷言 `marginal_ic`；或另增 mutation 目標專打 `_one` 內 `marginal_ic = _spearman(r_te, y_te)` 一行並以該窄測對映。V-3 現況仍能證 raw gross 路徑，可保留作輔測。

---

## §1 必查（11 類摘要）

1. 矛盾：節級 status 與 B5 消費假設衝突（P1-01）；其餘 A–D 無。  
2. 漏項：B1 scope 內無（B2–B5 未做屬計劃）。  
3. 不可測：各 Task 有 pytest＋探針命令。  
4. quant：train-fit、退化先於 Spearman、train 排序——實作＋探針鎖住；V-3 對 marginal 路徑證明力不足（P2-01）。  
5–8. 過度工程／OOM／cache／API：本批 N/A 或無問題；Python 3.9.6 相容。  
9. 測試：28+10＋十 mutation；O1b 雙條件實際走 ok 支；無 skip。  
10. Agent 可執行：檔案／函式／驗證明確。  
11. 短命工：`block_bootstrap_ci` 搬至 Task 2.1——計劃內，標註清楚。

STATUS: DONE
