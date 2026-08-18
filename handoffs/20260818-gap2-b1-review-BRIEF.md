# GAP-2 B1 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap2-b1-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–E 之敘述是「請你查證的問句與我的待攻決定」，不是主委的 operational 結論；
> 實際結論在委員產出與收斂檔 `handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md`（含各家實跑 rc）。

brief-kind: review

## 審查標的（commit `022650ff`；`git show 022650ff --stat`）
- 新模組（皆白名單外新檔）：`momentum/Analysis/contracts/ic_survivor_contract.json`（Task 1.0；24 頂層鍵）、
  `momentum/Analysis/survivor_contract.py`（Task 1.0；只有 `load_survivor_contract`）、
  `momentum/Analysis/marginal_ic.py`（Task 1.1 `Projection`／`normal_scores`／`fit_projection`／`apply_residual`；
  Task 1.2 `MarginalICParams`／`MarginalICResult`／`compute_marginal_ic`／`block_bootstrap_ci`）
- 測試：`tests/momentum/Analysis/test_survivor_contract.py`（`-k load` 10 條＋探針 `test_mutation_missing_top_key_raises`）、
  `tests/momentum/Analysis/test_marginal_ic.py`（28 條：Task 1.1 ①–⑤＋§G O1a／O1b／O2／O3／O5／O6／O7／O9＋⑧–⑮＋兩條檔內探針）
- 探針：`scripts/gap2_mutation_probe.sh --batch B1`（十條唯一對映）＋receipt `handoffs/run_receipts/20260818T151415Z-gap2-B1-probe.log`
- 契約來源：`docs/GAP2_MARGINAL_IC_TODO.md`（**FROZEN**）Task 1.0–1.3＋§0；`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）§A D1–D4／§G；
  `docs/GAP2_MARGINAL_IC_AMENDMENTS.md` A1-1..A1-6（衝突以延伸檔為準；本批直接相關＝A1-3 OOS 欄 root 注入）
- **既有檔零改動**（`git show 022650ff --stat` 只有新增檔）。

## 本輪任務（五段皆必答）
**段 A — 契約符合度（逐 Task）**：Task 1.0／1.1／1.2／1.3 之實作是否**逐條**滿足 TODO「實作要點／不可做／邊界／驗證」？特別查：
- 1.0：頂層鍵集恰為 TODO 步驟 1 之 24 鍵；`_doc` 逐字含 (a)(b)(c) 三句；每 `*_keys` 為 `{additional_properties:false, keys:{k:{type,required,nullable}}}`（沿 GAP-1 `strategy_validation_contract.json` 精神）；`reasons` 三組唯一列舉；loader 多鍵／少鍵／`allowed≠[false]`／檔缺／JSON 壞皆 raise；**程式／測試是否有任何處複列鍵表**（TODO §0 JSON SoT：只准 pointer）。
- 1.1：`normal_scores` 非有限／n<2 raise；`fit_projection` 空 basis ⇒ `beta=[mean]`；共線不 raise；三函式**無** mask／`fit_on_full` 參數。
- 1.2：**求值順序**——`var(r_te)<=thr` 判退化**先於**任何 Spearman（`_one` 內 `_spearman` 呼叫位置）；`fit_scope` typed、禁由 masks 猜（`fit_scope=train` 且 masks 全 True ⇒ raise）；`oos_guarantees`／`pass_class` 恆 `None` 佔位（A1-3）；預算 gate 先於任何計算、超限整體 not_computed 無部分值；`n_regressions` 只累計實際 `fit_projection` 呼叫；`train_ic` 為排序唯一來源；loo 依名稱排除；`extra_candidates` 去重＋減 survivors；字面值一律 `load_survivor_contract()` 讀出（grep `"semi_partial_rank_ic"`／`"rank_normal"`／reason 字面於 `marginal_ic.py` 應**零命中**——`_reason()` 只做成員檢查）。
- 1.3：十條 case 目標行存在檢查（缺 ⇒ rc=2 不留髒檔）；`mkdir` 鎖（rc=3）；`$BACKUP_DIR` cp 還原（非 git checkout）；rc=2 collection error 判設計錯；每條 RED＋RESTORED GREEN；B2–B5 未定義 ⇒ rc=2。

**段 B — 🔴 實作期決定之複核（我自己下的決定，請攻）**：
1. **節級 status 規則**：`status="ok"` iff 至少一視角 `ok`；但「loo／sequential 超預算而 removed 只是空集合 ok」⇒ 節整體 `not_computed:candidate_budget_exceeded`（`marginal_ic.py` `any_ok` 段）。removed 視角於 `extra=[]` 時標 `ok`（空 dict）而非 `not_applicable`——契約 reasons 無「no_removed_candidates」字面，我選不加 reason。**請答**：這規則對 B4 報告消費端（前端 `status!="ok"` 不畫表）語意是否正確？有無更好的封閉方案（如 removed 空 ⇒ view status `not_applicable` 但 reason 為 null）？
2. **`views` 結構**＝`{loo|sequential|removed_candidates: {status, reason}}`；契約 `section_keys.views` type=object，**未**另立 `view_status_keys` 子 schema。是否應補（B3 validator 會遞迴驗物件層）？若補，走 A1-7 增鍵（頂層鍵集變動 ⇒ 測試①須改，可見）。
3. **per_feature／sequential／removed 之欄位**：我加了 `conditioning_set`（list）與 sequential 之 `feature`／`step`；TODO Task 1.2 步驟 4 未列 `conditioning_set`（契約 SoT 決定鍵集）。是否多餘／該砍？（我認為 sequential 之 `conditioning_set` 是可審計必要欄；loo 之可由 survivors 推得。）
4. **列數 gate**：全域 `n_test<min_test_rows` ⇒ 節 `insufficient_test_rows`、`n_train<min_test_rows` ⇒ `insufficient_train_rows`（**借用** `min_test_rows` 當 train 下限，因參數無 `min_train_rows`）；候選級 `need=max(min_test_rows, min_rows_per_regressor·|S|)` 同時對 train／test（TODO 寫「train 同」）。借用是否合理？要不要 A1-7 加 `min_train_rows`？
5. **`_spearman` 對常數／n<2 回 NaN → 值轉 `None` 但 status 仍 `ok`**（如 test 段 label 常數）。是否該給 reason？契約 feature reasons 只有三個；我不擅加字面。請判是否需 A1 增 reason（如 `label_degenerate`）或維持。
6. **`block_bootstrap_ci`**：`block_len>n` 截為 n（單 block）；全部統計量非有限 ⇒ 回 `None`（`ci95=null`）；`n_bootstrap<1` raise。可接受？
7. **`MarginalICParams` 給了預設值**（鏡像 B4 `MarginalICConfig`；`block_len=5`）；TODO 只列欄位未定預設。是否應**不給預設**逼呼叫方顯式傳（B4 orchestrator 會顯式傳；測試用 `FAST`）？
8. **`fit_scope="full_sample"` 且 masks 為 `None` ⇒ 視為全 True**。這是否踩「由 masks 推」禁令？（我判不是——fit_scope 是輸入，masks 只是省略值。）
9. **`with_root(analysis_status)`**：`ok_oos ⇒ (True,"oos")`，其他 ⇒ `(False,"full_sample_research_only")`；`pass_class` 字面在 `marginal_ic.py` 寫死（root 兩值契約住 `ic_reporter.normalize_analysis_status`，非 survivor 契約）。是否該改讀既有 root 契約來源？
10. **契約 schema 決策（供 B3 前先攻）**：`event_definition_keys` 與 `event_identity_keys` 內容相同（一為檔內物件、一為 cache 物件）；`sample_scope_keys`＝`{kind, event, n_samples_total, n_samples_test, degraded}`；`split_keys`／`provenance_keys`／`survivor_record_keys` 之欄位是否**涵蓋 SPEC Task 3.1 全部義務項**（請逐條對照 SPEC L179）；`survivor_file_keys` 24 鍵是否對得上 TODO 1.0 步驟 2 之 pointer 清單。**現在指出比 B3 再改便宜**。

**段 C — 測試品質（可證偽性）**：
- **請自己重跑** `bash scripts/gap2_mutation_probe.sh --batch B1`（約 2 分鐘，會自我還原；🔴 **不可與他人並行**，鎖被持有 ⇒ rc=3 請稍後重試或讀 receipt）並回報 rc 與十條 RED／GREEN。
- V-5 探針（排序改用 test IC）之 fixture：`test_sequential_order_by_train_ic` 以 O7 資料加 `w`（train 弱／test 強）使 train／test 順序不同——是否真能區分？（mutant 為 `order_key_ic = _rank_ic(test_rows_mask)`。）
- V-3 探針把 `_spearman` 內 `stats.spearmanr`→`stats.pearsonr`：`test_o6_rank_invariance` 之紅來自 `gross_ic`（raw `s1³`）而非 `marginal_ic`（rank-normal 殘差對 Pearson 亦不變）——這算不算「證明 marginal_ic 用秩相關」？若不算，提議更窄 oracle。
- 檔內探針 `test_mutation_test_fit_projection_breaks_o7` 以「依形狀判斷是否為 f 之擬合」注入 test-fit 變體——這是不是真 seam？有更乾淨寫法？
- `test_o7_train_fit` 之獨立參考實作 `_reference_marginal_ic`（≤20 行）是否**真獨立**（未 import 待測模組之原語）？
- 有無廉價綠燈（只驗不 crash／容差過寬／`skip`）？O1b 之「degenerate 或 |marginal|≤0.02」雙條件是否被實際走到哪一支（請印出）。

**段 D — 數值正確性（本票命中 (a)(d)）**：
- `normal_scores`＝`norm.ppf(rank_avg/(n+1))`；`fit_projection` 含截距 lstsq、`r2_train` 於 `ss_tot==0` 為 0.0；`apply_residual` 欄數檢查。
- `compute_marginal_ic` 對 O2 實跑 Δ=−0.0058（與 SPEC 附之 codex 實跑一致）；O7 之 test-fit 差、train-insample 差皆 >0.3——請自行重算並貼值。
- `ic_retained_ratio` 保留符號、`|gross|<1e-12 ⇒ None`；負 gross 案例 ratio==1。
- bootstrap 起點 `rng.integers(0, n-b+1, size=n_blocks)`、串接切 n、成對索引——是否為正確 moving-block？

**段 E — registry「GAP-2 待補完」四條之觸發是否已成立**（每批必審；表逐字如下）：
| # | 待補完項 | 為何現在不做 | 觸發條件 |
|---|---|---|---|
| G2-R1 | IC→ML 橋本體 | user-ruling: 2026-08-18 橋本體 blocked-by ML 層 | ML 層重寫或宣告穩定 |
| G2-R2 | 以邊際 IC 做 forward-stepwise 選擇 | needs-research: post-FDR 二次選擇多重比較政策無認可方法 | 委員會定出政策 |
| G2-R3 | xsec 路徑之邊際 IC | blocked-by: registry #4 Pooled/Panel IC | #4 完工 |
| G2-R5 | nested／frozen final test | blocked-by: IC 主路徑切分 holdout-only | 主線切分升級 |
請答：本批有無任何實作使上述觸發成立、或使「為何現在不做」失效？（預期：無。）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 之 §0／§1／§3 與 canonical 四欄格式。
ID＝`## <FAMILY>-R12-P<0-3>-<NN>`（gap2 review 計數延續；**本輪＝R12**）。零 findings 用 sentinel `## <FAMILY>-R12-P3-00`（body 須實質）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO／延伸檔、禁 commit／push**；只產你自己的 review 檔。
- 可自由跑測試（`venv/bin/python -m pytest …`）與探針；跑完貼 rc。venv 為 **Python 3.9.6**（3.10+ 語法即 bug）。
- 使用者裁決不受理重議（2a／2b 拆分；橋 blocked；B5 表格＋toggle 預設開；`marginal_ic.enabled` 預設 True）。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` → 10 passed；`venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py -q` → 28 passed（Claude 實跑 2026-08-18）
fact-verified: `bash scripts/gap2_mutation_probe.sh --batch B1` → rc=0，十條 `RED ✓`＋`RESTORED GREEN ✓`（receipt `handoffs/run_receipts/20260818T151415Z-gap2-B1-probe.log`）
fact-verified: `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py` → PASS（3 探針真跑）
fact-verified: `grep -n "from api\.\|import api" momentum/Analysis/marginal_ic.py momentum/Analysis/survivor_contract.py` → 0 命中（R1）
assumed: 段 B 十項實作期決定為契約內合理選擇而非漂移 ← 請攻
assumed: 契約 schema（段 B-10）已涵蓋 SPEC Task 3.1 全部義務項，B3 不需再改鍵集 ← 請逐條對照
assumed: 十條 mutation 各對應之測試確為「該 mutation 唯一能紅」之最窄 oracle（非同一測試對多條都紅的寬 oracle）← 請攻

## Time-box
優先序＝段 B（實作決定）＞ 段 D（數值）＞ 段 C（測試品質）＞ 段 A（契約符合度）＞ 段 E。
**不受理**：使用者裁決、TODO 已 Frozen 之契約本身（要改請走延伸檔提案並說明為何非改不可）、B2–B5 尚未實作之部分、治理機制。

## 產出
Verdict（可進 B2／需修補後進 B2／有根本缺陷需重作）＋段 A–E 各段結論＋canonical findings。
收尾清 /tmp workdir（保留 claude-501）。
