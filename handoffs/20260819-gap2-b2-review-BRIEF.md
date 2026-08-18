# GAP-2 B2 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap2-b2-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–E 之敘述是「請你查證的問句與我的待攻決定」，不是主委的 operational 結論；實際結論在委員產出與收斂檔 `handoffs/reconcile/20260819-gap2-b2-review-r15/synth.md`。
> 🔴 **請勿就地改任何 repo 檔做實驗**（B1 stamp 因此互相污染）；探針 `gap2_mutation_probe.sh` 有互斥鎖，鎖被持有 ⇒ rc=3 請稍後重試或讀 receipt。

brief-kind: review

## 審查標的（commit `d026fbed`；`git show d026fbed --stat`）
- 新模組：`momentum/Analysis/factor_combiner.py`（Task 2.1：`block_bootstrap_ci`（自 `marginal_ic.py` 搬入，簽名不變）／`CompositeResult`／`combine_factors`）
- 既有檔改動：`momentum/Analysis/marginal_ic.py`（**只**移除 `block_bootstrap_ci` 定義、改 `from momentum.Analysis.factor_combiner import block_bootstrap_ci` re-export；`git diff 35bd66a1 d026fbed -- momentum/Analysis/marginal_ic.py`）；`scripts/gap2_mutation_probe.sh`（B2 case 表 V-7／8／9；B1 V-6 目標檔改 `factor_combiner.py`；pytest 目標改跑該批 `ALL_TESTS`）
- 測試：`tests/momentum/Analysis/test_factor_combiner.py`（11 條：§G O4／O8（含 O7 負 IC 案例）／O9＋V-8／V-9 獨立參考＋①–⑦＋`test_mutation_test_sign_breaks_o8`）
- receipts：`handoffs/run_receipts/20260818T222158Z-gap2-B2-probe.log`（V-7／8／9 RED）、`20260818T222311Z-gap2-B1-probe.log`（B1 十條重跑 RED）
- 契約來源：`docs/GAP2_MARGINAL_IC_TODO.md`（FROZEN）Task 2.1／2.2；SPEC §A D5／§G O4／O8／O9；`docs/GAP2_MARGINAL_IC_AMENDMENTS.md` A1-1..A1-7

## 本輪任務（五段皆必答）
**段 A — 契約符合度**：Task 2.1 實作要點 1–6／不可做／邊界／驗證逐條；`CompositeResult.to_dict()` 鍵集 == 契約 `composite_keys`；`fit_scope` 守衛同 1.2；符號／權重**只**在 train；`best_single_test_ic` 只作參考（未當比較基準）；不得提供 OLS／Ridge；Task 2.2 三 case 對映。

**段 B — 🔴 實作期決定（請攻）**：
1. **complete-case 定義**：train 與 test 皆對「全部 survivors＋label 有限」之列（同一 finite mask 分段）——TODO 步驟 2 只寫 test；train 段亦用 complete-case 是否合理？（另一選項：train_ic 逐因子各自 finite 列。）
2. **`test_ic_all` 於符號／權重之前計算**（步驟 5 消費；程式註明「禁用於符號／權重」）——這是為了 V-8 探針有可替換之目標變數；是否構成「test 段統計量出現在 train-only 決策附近」的可讀性／誤用風險？
3. **`train_ic` 用 `_spearman`（常數／n<2 ⇒ NaN ⇒ 排除 `zero_train_ic`）**：NaN 與 0 同歸 `zero_train_ic`——是否需區分？契約 feature reasons 現有四值（`residual_degenerate`／`zero_train_ic`／`insufficient_rows`／`label_degenerate`）。
4. **`top_train_single` tie**：依原 survivors 順序取先者；`best_single_feature` 同法。可接受？
5. **循環 import 解法**：`marginal_ic` 模組層 import `factor_combiner.block_bootstrap_ci`；`factor_combiner.combine_factors` 內 lazy import `marginal_ic` 之 `_spearman`／`normal_scores`／`_finite_or_none`（私有名跨模組）。是否該把 `_spearman`／`_finite_or_none` 升為公開或搬到共用小模組？（TODO 白名單無新模組；升公開不需新檔。）
6. **`composite_ic_train_insample`**：以 train 列 `normal_scores` 重算 z 再套同權重／符號（非用 test 段 z）；符合 TODO 步驟 4 之描述？
7. **`delta_ci95` 統計量**＝`spearman(comp,y) − spearman(f_top,y)` 於同一 block 索引重抽三列——成對性是否正確？
8. **O4 加法性斷言**：`Σ marg²/composite²` 用 `compute_marginal_ic` sequential 視角之 `marginal_ic`（4 因子、`n_bootstrap=20`）——與 SPEC「sequential 之 Σ marginal_ic²」一致？實跑值請自行貼出。

**段 C — 測試品質**：**請自己重跑** `bash scripts/gap2_mutation_probe.sh --batch B2`（約 1 分鐘）並貼 rc；V-7 探針 seam（`sign_source_X, sign_source_y = X_te, y_te`）與檔內探針 `test_mutation_test_sign_breaks_o8`（monkeypatch `_spearman` 依長度判 train 段）是否為真 seam；V-9 之獨立參考 `_ref_block_ci` 是否真獨立（未 import 待測 bootstrap）；O4 帶寬容差是否過寬（廉價綠）；有無 skip／只驗不 crash。

**段 D — 數值正確性**：`composite = Σ w·sign·normal_scores(f)`（等權 1/k′；`ic_weighted` |train_ic|/Σ）；O4 實跑：composite_ic、四個 sequential marginal、ratio 請貼值並與 SPEC 附之三家實跑（ratio 0.96–0.99／composite 0.574–0.595／margs 0.27–0.29）對照；O8 `S={f}` 於 O7 資料 composite_ic == (+1)·負 gross（請重算）。

**段 E — registry「GAP-2 待補完」四條之觸發是否已成立**（每批必審）：
| # | 待補完項 | 為何現在不做 | 觸發條件 |
|---|---|---|---|
| G2-R1 | IC→ML 橋本體 | user-ruling: 2026-08-18 橋本體 blocked-by ML 層 | ML 層重寫或宣告穩定 |
| G2-R2 | 以邊際 IC 做 forward-stepwise 選擇 | needs-research: post-FDR 二次選擇多重比較政策無認可方法 | 委員會定出政策 |
| G2-R3 | xsec 路徑之邊際 IC | blocked-by: registry #4 Pooled/Panel IC | #4 完工 |
| G2-R5 | nested／frozen final test | blocked-by: IC 主路徑切分 holdout-only | 主線切分升級 |
請答：本批有無實作使觸發成立或使理由失效？（預期：無。）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1／§3 與 canonical 四欄。ID＝`## <FAMILY>-R15-P<0-3>-<NN>`（gap2 計數延續；**本輪＝R15**）。零 findings 用 sentinel `## <FAMILY>-R15-P3-00`（body 須實質）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO／延伸檔、禁 commit／push、禁就地改檔實驗**（實驗一律 in-memory monkeypatch）；只產你自己的 review 檔。
- 可跑測試／探針（貼 rc）。venv **Python 3.9.6**。使用者裁決不受理重議。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed（Claude 實跑 2026-08-19）
fact-verified: `bash scripts/gap2_mutation_probe.sh --batch B2` → rc=0（V-7／8／9 RED＋還原綠）；`--batch B1` → rc=0（十條 RED；V-6 目標改指 `factor_combiner.py`）
fact-verified: `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS；`grep "from api\.\|import api" factor_combiner.py` → 0 命中
fact-verified: `import marginal_ic` 與 `import factor_combiner` 兩種順序皆可載入且 `marginal_ic.block_bootstrap_ci is factor_combiner.block_bootstrap_ci`
assumed: 段 B 八項實作期決定為契約內合理選擇 ← 請攻
assumed: O4 帶寬（`composite∈[0.55,0.61]`、marg∈[0.26,0.31]、ratio∈[0.90,1.10]）於本實作一次落帶非巧合（SPEC 三家實跑同帶）← 請重算對照
assumed: `marginal_ic.py` 之改動只有 bootstrap 搬移（B1 契約未被觸動）← 請 diff 逐行看

## Time-box
優先序＝段 B ＞ 段 D ＞ 段 C ＞ 段 A ＞ 段 E。**不受理**：使用者裁決、TODO 已 Frozen 之契約本身（要改走延伸檔提案）、B3–B5 未實作部分、治理機制。

## 產出
Verdict（可進 B3／需修補後進 B3／有根本缺陷需重作）＋段 A–E 結論＋canonical findings。收尾清 /tmp workdir（保留 claude-501）。
