# Reconcile — 20260818-gap2-x-review-r1

**來源** 20260818-gap2-specadv-codex.md, 20260818-gap2-specadv-composer.md, 20260818-gap2-specadv-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **14 條** findings（codex 5／composer 4／grok 5），下列六個群集**引用全部 14 條，0 掉項**。三家皆判「需修補後派工」（codex 判 P0-01 BLOCKING；grok 判 B3 時序 BLOCKING）；無架構性重作。

Verdict：需修補後派工——六群集全部**接受並寫回 SPEC**（同輪 R1 修訂，不留待實作「自行判斷」）；修訂後派 R2 adversarial 複核。

### K1 — 批次時序：契約 SoT 先行、`report_sections.marginal_ic` 與 orchestrator 同 commit（codex／grok 同判 BLOCKING）
**引用**: CODEX-R1-P1-05, GROK-R1-P0-01

**處置＝接受**。碼證成立：`test_r6_wider_contract_nodes_consistent` 對契約**全部** `report_sections` 鍵要求 orchestrator 字面出現（僅豁免 `net_ic_analysis`），SPEC 前版「B3 只加鍵不加 reason 值」打錯攻擊面。修法（同時消 SoT 重複）：
1. `ic_survivor_contract.json`（含 `marginal_ic_section_keys` 全部子集）**移至 B1 Task 1.1 首件產出**；B1／B2 dataclass `to_dict()` 鍵集直接讀契約對照，**刪除**「先檔內常數後改讀契約」過渡。
2. `ic_report_contract.json` 之 `report_sections.marginal_ic`／`reasons.marginal_ic*`／`metadata.survivor_output_keys` **全部移至 B4 Task 4.1**，與 `_stage6b` 組裝字面同 commit。
3. B3 只剩 `survivor_contract.py`（loader／resolver／validator／`build_survivor_output`）＋conformance／tamper 測試；B3 單獨綠。

### K2 — oracle 假紅／欠釘：O8 符號、O1 gate 順序、O4／O1／O2／O7 產生器參數、O5 Bonferroni、Task 1.2-⑨ 語意（三家）
**引用**: CODEX-R1-P0-01, CODEX-R1-P1-02, GROK-R1-P1-03, COMPOSER-R1-P1-01

**處置＝接受，全部寫回 §G**：
1. O8：`S={f}` ⇒ `composite_ic == sign(train_ic_f)·gross_ic_f`（codex 反例 gross=−1、composite=+1 成立）；Task 1.2-⑨ 改寫為「`|survivors|=1` ⇒ loo 之 S_f=∅ ⇒ `marginal_ic == gross_ic`」（原文「|S|=1」歧義）。
2. O1：**先** `var(r_test) ≤ degenerate_threshold` gate 再算 Spearman 為硬約束（grok 探針：精確單調時 var≈7.8e-31、未 gate 之 Spearman≈−0.69）；`x³`／`tanh` 兩案例分列：`x³` 預期 `residual_degenerate`；`tanh(2s)` 預期 `residual_degenerate` 或 `|·|≤0.02`；加 mutation「移除 gate 順序 ⇒ O1 紅」。
3. O4：產生器釘死＝k=4 iid N(0,1)、`ρ_i=0.3` 全等、`ε~N(0,0.64)`（Var(y)=1）、n=20000、seed=20260818、前 60% train／後 40% test；母體 Pearson 下 `Σmarg²/composite²≡1`（等 ρ 時 `k·Σρ²/(Σρ)²=1`；codex 反例 `[1,.1,.1,.1]` 得 2.50 正是不等 ρ），Spearman 版帶 `[0.90,1.10]`；另斷言 `composite_ic ∈ [0.55,0.61]`（`(6/π)asin(0.3)=0.582`）、各 `marginal_ic ∈ [0.26,0.31]`（`(6/π)asin(0.15)=0.287`）。O1／O2／O7 同樣寫死 seed／n／係數／噪聲／mask 切法於 §G「合成產生器規格表」。
4. O5：統一為 `|stat| < z_{1−α/(2k)}/√n_test`，α=0.05、k＝同測試內檢定之因子數（Bonferroni），刪 `2/√n` 與章程矩陣之矛盾。

### K3 — `fit_scope`／root status 必須是 typed 輸入（codex）
**引用**: CODEX-R1-P1-03

**處置＝接受**：`compute_marginal_ic(..., fit_scope: Literal["train","full_sample"])` 明列；`_stage6b_marginal_ic(..., fit_scope, split_context)`；三條路徑各設 oracle：holdout ⇒ `train`／`oos_guarantees` 隨 root；fallback ⇒ 呼叫方傳全 True masks＋`fit_scope="full_sample"` ⇒ `oos_guarantees=False`；`split_context is None` 且 `fit_scope="train"` ⇒ `not_applicable:no_holdout_split`（禁猜）。

### K4 — 2b 契約補欄：`symbol`／`timeframe`／`case_id`（三家）＋事件 timestamps hash＋`oos_semantics` 消費端語意（codex）＋`ic_retained_ratio` 公式（grok）
**引用**: CODEX-R1-P1-04, COMPOSER-R1-P1-02, GROK-R1-P1-01, GROK-R1-P1-02

**處置＝接受**：Task 3.1 義務清單加 `symbol`／`timeframe`／`case_id`（頂層必填）、`sample_scope.event.timestamps_hash`（於 orchestrator pop 前計算）、頂層 `oos_semantics` 固定字面（契約枚舉唯一值，validator 強制）；validator 加「`symbol`／`timeframe` 與 `report_ref` 之報告 metadata 不符 ⇒ raise」；`ic_retained_ratio = marginal_ic / gross_ic`（保留符號；`|gross|<1e-12 ⇒ null`）＋單元斷言（gross<0、marginal≈gross ⇒ ratio≈1）。Task 3.1「語意描述」改題為「契約檔必須涵蓋之義務項（C4 checklist；鍵名／型別以契約檔為準）」並加驗證⑭＝checklist ⊆ 契約鍵集（機檢）。

### K5 — mutation 補洞：shuffle-S／symbol tamper／feature_set_hash tamper／O1 gate 順序（composer／grok）
**引用**: COMPOSER-R1-P2-01, GROK-R1-P2-01

**處置＝接受**：§V 加 V-18（洗牌 `Z_S` 欄序 ⇒ loo exact 不變、sequential 依序變 ⇒ 若實作依欄序而非名稱則紅）、V-19（`symbol` tamper ⇒ validator 紅）、V-20（`feature_set_hash` tamper ⇒ 紅）、V-21（O1 gate 順序移除 ⇒ 紅）。

### K6 — cache-hit `refilter` 驗收（composer）
**引用**: COMPOSER-R1-P2-02

**處置＝接受**：Task 4.1 驗證加 ⑩「cache 命中後 `refilter()` ⇒ `marginal_ic.per_feature` 鍵集 == 新 `filtered_df.columns` 且 `_ic_cache["stage6b_results"]` 已刷新（object id／sha 變）」。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01
**斷言**: §G O8 與 Task 1.2-⑨ 要求的等式在 SPEC 允許的負 IC／非空條件集案例中為假，正確實作會被驗收打紅。
**碼證**: docs/GAP2_MARGINAL_IC_SPEC.md:50,85,109-110；venv/bin/python -c ... → gross_ic=-1.0 train_ic=-1.0 composite_ic=1.0；另一反例 gross_ic=1.000000000000 marginal_ic=-0.960533020035。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；[BLOCKING] 修正 O8 為 sign-adjusted gross 或明確 raw gross，且將 |S|=1 改為 S=∅／附獨立條件；新增非空 S 參考 oracle。
## CODEX-R1-P1-02
**斷言**: O4 的 [0.85,1.15] 並非由所述 y=Σρ_i f_i+ε 模型保證，且 O1/O2/O4/O7 未固定可重現的係數、噪聲、label、seed 與 mask。
**碼證**: docs/GAP2_MARGINAL_IC_SPEC.md:77-84,248；允許係數 [1,.1,.1,.1]、noise=1 的獨立 Spearman probe → sum_sq_ratio=2.497437336413（非 [0.85,1.15]）。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；[MAJOR] 固定完整資料生成器／seed／ρ／噪聲／label 與 mask，或把容差依限定參數推導；「seed 寫在測試」不足以使 SPEC 驗收唯一。
## CODEX-R1-P1-03
**斷言**: D3 的 no-holdout 與 full-sample fallback 在宣告的 compute_marginal_ic／_stage6b_marginal_ic 介面中沒有可傳遞的 fit_scope／root-status 來源，無法依規格同時 fail-closed 地區分 no_holdout_split 與 full_sample。
**碼證**: SPEC :107,109,179-182 的簽名無 fit_scope；實際 fallback ic_train_test_split=False 並注入 preprocessing.fit_mode=full_sample（ic_filter_orchestrator.py:1096-1101），一般 no-holdout 同樣沒有 split_context（:889-920）。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；[MAJOR] 將 root status/fit scope 變成明確 typed input 或唯一 context，並為兩條路徑各設 fail-closed oracle。
## CODEX-R1-P1-04
**斷言**: 2b survivor 契約目前不能讓消費端重建／驗證 exact event rows，且 oos_guarantees=true＋independent_oos_validation=false 仍可被既有消費語意讀成 OOS；C4 要求的 symbol/timeframe/case_id 也未落入列舉。
**碼證**: event_filter.py:66-105 只暫存 timestamps，orchestrator :2773-2776 明確 pop timestamps 只留計數；SPEC :155-158,193 只留 definition hash/counts、test index hash，且 ic_reporter.py:581-611 以 oos_guarantees 推 pass_class=oos；收斂 C4 synth.md:42-44 明列 symbol/timeframe/case_id。
**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；[MAJOR] 保存 event mask/timestamps hash（或可重建 row identity）及 symbol/timeframe/case_id；consumer validator 必須把 independent flag 與 root OOS 語意聯結，不能只驗 oos_guarantees。
## CODEX-R1-P1-05
**斷言**: B3 的「契約 SoT／批次可獨立驗收」與自身規則矛盾：Task 1.2 先用 file-local key constants，Task 3.1 又列同一欄位；且 B3 加 report_sections.marginal_ic 即會使既有 R6 sync 在 B4 前因 marginal_ic 不在 orchestrator 而失敗。
**碼證**: SPEC :68,107,110,155-158；test_ichc_contract_sync.py:59-61 對契約每個 report section 查 orchestrator，當前 rg -n marginal_ic momentum/Analysis/ic_filter_orchestrator.py ... 無輸出；SPEC :156 只預見新 reason 的紅，漏掉新 section 的同一斷言。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；tests/momentum/Analysis/test_ichc_contract_sync.py#c2eb517dd24a；[MAJOR] 先定 schema 再讓 B1/B2 import，或將 B3+B4 設為同一 atomic gate；刪除 prose/temporary key duplication。
## COMPOSER-R1-P1-01

**斷言**: §G O5 標籤置亂門檻（L82 `2/√n_test`）與同節 Oracle 矩陣（L248「多重比較＝Bonferroni 於同測試內多因子」）自相矛盾，實作者無法同時滿足兩處，且按 L82 實作會對多 survivor 場景偏寬（假綠風險）。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:82` vs `:248`；`docs/TEST_DESIGN_CHARTER.md` F-IC-6 要求標籤置亂檢定。RECHECK: `rg -n 'O5|Bonferroni|2/√n' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=High。多因子（k>1）時未 Bonferroni 調整，O5 可能放過非零邊際 IC。修法：統一 O5 為 `|marginal_ic| < (2/√n_test)·α_adj`（`α_adj=0.05/k_features` 或契約寫死 Bonferroni 公式），並刪除 L248 與 L82 之一致性衝突。

---

## COMPOSER-R1-P1-02

**斷言**: 收斂檔 C4 明定倖存者契約須含 `symbol`／`timeframe`（`synth.md` C4-2 欄位聯集），但 SPEC Task 3.1 之 `provenance_keys`／語意描述（L157）與 `build_survivor_output` 參數均未要求兩欄，亦無 §G-4 契約 oracle 驗證——C4 義務被靜默弱化，未來 ML 消費端無法 fail-closed 拒 cross-symbol stale 檔。

**碼證**: `handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md` C4「symbol／timeframe／…」；`docs/GAP2_MARGINAL_IC_SPEC.md:155-157` provenance 列舉無 symbol/timeframe；`rg symbol\|timeframe docs/GAP2_MARGINAL_IC_SPEC.md` 僅 L26 `allowed_symbols` receipt。RECHECK: 對照 synth C4 與 Task 3.1 鍵集。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md#7c72c0aa258d

[MAJOR] 信心度=High。2b 契約無單標的身份欄，僅 `base_universe_hash` 不足以讓消費端區分同 hash 不同 symbol 的誤載。修法：Task 3.1 契約加 `symbol`／`timeframe`（required）＋ validator ⑭ 與 §G-4 tamper（錯 symbol 必 raise）。

---

## COMPOSER-R1-P2-01

**斷言**: §V 17 條 mutation 未覆蓋收斂 C7／CODEX-R1-P1-06 要求之 `shuffle-S`（條件集列順序／歸屬錯誤）與 `hash/symbol mismatch`（倖存者檔 identity 錯配），存在「改壞條件集或 identity 仍綠」的假綠窗。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:225-242` 列 V-1..V-17 無 shuffle-S／symbol-hash mismatch；`synth.md` C7「shuffle-S／hash mismatch 之 mutation」；`docs/TEST_DESIGN_CHARTER.md` A2 洩漏 MR 要求可證偽 mutation。RECHECK: `rg 'shuffle|symbol mismatch|V-1[0-9]' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=Medium。V-4（loo 含 f）不涵蓋「S 列順序錯誤但集合相同」；契約 oracle ⑫ 只驗 `feature_set_hash`，不驗 symbol。修法：增 §V-18（shuffle `Z_S` 列⇒loo 不變、sequential 變⇒紅）與 §V-19（`symbol` tamper⇒validator 紅）。

---

## COMPOSER-R1-P2-02

**斷言**: Task 4.1 邊界 ④「cache-hit `refilter`」列為邊界卻無可量化驗收，Agent 可能讓 refilter 在 cache 命中時跳過 stage6b 或沿用過期 `stage6b_results`，與 D7「三入口一致」衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:183` 邊界 ④ 無對應「驗證」子句；現行 `refilter()` 僅 stage5→6→7（`ic_filter_orchestrator.py:1736-1765`），stage6b 尚未存在；deep cache-hit 先例見 `:1850-1855`（降級而非靜默 ok）。RECHECK: 讀 Task 4.1 邊界 vs 驗證清單是否成對。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MINOR] 信心度=Medium。refilter 後 `per_feature` 鍵集與 survivors 不一致風險。修法：Task 4.1 驗證增 ⑩「cache 命中後 `refilter()` ⇒ `marginal_ic.per_feature` 鍵 == 新 `filtered_df.columns` 且 `stage6b_results` 已刷新」。

---

## GROK-R1-P0-01

**斷言**: Task 3.1（B3）指示同步把 `report_sections.marginal_ic` 寫入 `ic_report_contract.json`，但既有 `test_r6_wider_contract_nodes_consistent` 會對契約內每一個 `report_sections` 鍵要求 orchestrator 原始碼出現 `"{section}"`（僅豁免 `net_ic_analysis`）；B3 單獨落地必紅。SPEC 宣稱的緩解（B3 只加契約鍵不加 reason 值）打在錯誤攻擊面——現測對新 reason 值根本不做消費點掃描。

**碼證**: SPEC L155 加 `report_sections.marginal_ic`；L156 緩解只談 reason 值延到 B4。`test_ichc_contract_sync.py:56-61` 對 reasons 只查兩常數 `insufficient_events`／`turnover_disabled`，但對 `contract["report_sections"]` 全鍵要求 `"{section}" in orch_src`（豁免僅 `net_ic_analysis`）。VERIFY 模擬：契約臨時加 `marginal_ic` ⇒ `fails ['marginal_ic']`；填滿 `reasons.marginal_ic` 新值不會使該測因新值而紅。RECHECK: `sed -n '43,61p' tests/momentum/Analysis/test_ichc_contract_sync.py`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[BLOCKING] 信心度=High。會怎麼失敗：B3 commit 後 `pytest …test_ichc_contract_sync.py` 紅，五批「B3 可獨立綠」敘事崩解；或實作者為過測提前改 orch／放寬測試＝假綠或越界。  
修法（擇一寫進 SPEC）：(a) B3 不加 `report_sections.marginal_ic`，該鍵與 reason 值皆於 B4 與 `_stage6b`／組裝字串同 commit；(b) 明示 B3+B4 對契約該鍵不可拆 commit；(c) 測試豁免清單加 `marginal_ic`（最弱，需另證不會幽靈節）。

---

## GROK-R1-P1-01

**斷言**: 收斂檔 C4 欄位聯集（codex 最嚴版，已採納）明列 `symbol`／`timeframe`，但 SPEC Task 3.1 的契約頂層鍵清單、`provenance`／`split` 語意段、與 `build_survivor_output(...)` 簽名皆未出現這兩欄；依 brief「對未來 ML 消費端重建 exact rows＋防 stale 足夠」之 assumed，契約集合不足。

**碼證**: synth C4 明列 symbol／timeframe；SPEC L155–157 之 `survivor_file_keys`／`provenance`／`split`／`build_survivor_output(...)` 簽名無此兩欄。本輪掃描 Task 3.1 段 L153–162：`symbol: NO`、`timeframe: NO`（`labels_content_hash`／`row_identity`／`feature_set_hash` 有）。僅靠 `features_path` 或 row hash 不能機器強制跨 symbol 隔離。RECHECK: `grep -n 'symbol\|timeframe' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md#7c72c0aa258d

[MAJOR] 信心度=High。會怎麼失敗：事件型／多標的消費端無法 fail-closed 驗「此倖存者檔屬於哪顆 symbol/tf」；stale 或錯掛 features 時只靠 path 慣例。  
修法：Task 3.1 契約必填 `symbol`／`timeframe`（頂層或 `sample_scope`／`provenance` 擇一釘死）；`build_survivor_output` 簽名加入並加驗證⑫類 hash／相等斷言；同步 §V 一條 mutation（錯 symbol ⇒ raise）。

---

## GROK-R1-P1-02

**斷言**: Task 1.2 輸出 `ic_retained_ratio` 但 SPEC 只規定 `|gross|<1e-12 ⇒ null`，未釘比值定義（`marginal/gross` vs `|marginal|/|gross|` vs 符號對齊後），兩實作可自洽綠燈而前端「retained」欄語意相反。

**碼證**: SPEC L109：`ic_retained_ratio`（`|gross|<1e-12` ⇒ null）— 無等式。B5 L213 表格要顯示 `retained`。D1／§G 無 O-numeric 定義該比值。  
RECHECK: `grep -n 'ic_retained_ratio\|retained' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=High。會怎麼失敗：`train_ic<0` 或 marginal 與 gross 異號時，signed vs abs 比值差到變號；B5 與契約消費者解讀分裂。  
修法：釘死 `ic_retained_ratio = marginal_ic / gross_ic`（保留符號； `|gross|<1e-12 ⇒ null`），並加一條單元斷言（構造 gross<0、marginal≈gross ⇒ ratio≈1）。

---

## GROK-R1-P1-03

**斷言**: §G O1 寫 `|marginal_ic|≤0.02` 或 `residual_degenerate` 二擇一；但對嚴格單調冗餘（`tanh(2s)`／`x³`），vdW 分數與基底分數逐點相等，殘差數值噪聲之 Spearman 可達 `|ρ|≈0.7`（n=5000），絕對值容差分支 alone 必然假紅；正確性完全依賴「先 `var(r)≤degenerate_threshold` 再算 IC」的求值順序，而 Task 1.2 改法未把該順序寫成硬約束。

**碼證**: SPEC L78 O1；L109 敘事有先後但未列入不可做／驗證必須先 gate。VERIFY n=5000／`tanh(2s)`：`max|zf-zs|=0`、`var_r≈7.8e-31≤1e-10`、未 gate 之 `spearman(r,y)≈-0.693`；raw 殘差≈0.104>0.10。RECHECK: 重跑文首 O1 探針。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=High。會怎麼失敗：實作先算 Spearman 再看 abs≤0.02 → O1 假紅；或放寬 0.02／關掉 raw>0.10 反向斷言換綠＝削弱 D1 防退回 raw。  
修法：O1／Task 1.2 明定必須先 degenerate gate；`|·|≤0.02` 僅適用近單調／非精確共線；加 mutation：刪除 gate 先後 ⇒ O1 紅。

---

## GROK-R1-P2-01

**斷言**: 收斂 C7 要求 mutation 覆蓋含 hash mismatch／shuffle-S；§V 17 條有 feature_set_hash 的**測試斷言**（Task 3.1 ⑫）但無對應 §V mutation 編號，shuffle-S（條件集列洗牌應不變）亦缺，抗回歸網比 C7 窄一截。

**碼證**: synth C7「hash mismatch」；§V L225–242 列 V-1..V-17——無「打亂 S 欄序仍 exact」「`feature_set_hash` 篡改必紅」之 mutation 條（⑫ 是測試斷言非 probe 腳本 case）。  
RECHECK: `grep -n 'shuffle\|hash mismatch\|feature_set_hash' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md#7c72c0aa258d

[MINOR] 信心度=Medium。不阻 TODO 生成；建議 §V 加 V-18／V-19 或於 Task 1.3／3.2 probe 具名納入。不列 BLOCKING。

---

