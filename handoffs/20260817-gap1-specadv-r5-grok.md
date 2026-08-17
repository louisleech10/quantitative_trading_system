# GAP-1 SPEC R5 複審 — GROK（R3/R4 findings closure 複驗 vs SPEC R4）

**task-id**: `20260817-GAP1-X-REVIEW-R5` | **family**: grok | **brief**: `handoffs/20260817-gap1-specadv-r5-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`f7321c906af7`（commit `85f1a70e` / 訊息含「SPEC R4」）
**上一輪本家**：`handoffs/20260817-gap1-specadv-r4-grok.md`（finding ID＝GROK-R3-P1-01／P2-01）
**上一輪收斂**：`handoffs/reconcile/20260817-gap1-x-review-r4/synth.md`（F1–F4；body sha256 前 12＝`ad0988e951eb`；本輪不蓋戳記）
**禁改碼／禁改 SPEC／禁蓋戳記**（僅 closure + assumed 攻擊 + 新 finding）
**本輪 finding 輪次**：R4（brief 明定）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS (spec)`
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `f7321c906af7…`
- `shasum -a 256 handoffs/reconcile/20260817-gap1-x-review-r4/synth.md` → full `7c7d6462b96d…`；body 至 `## 戳記` 前 `ad0988e951eb…`（與 brief 一致）
- 本家 ID `grep -c`：GROK-R3-P1-01=1、GROK-R3-P2-01=1
- 十一條 R3 ID 命中：CODEX-R3-P0-01=3、P1-01=1、P1-02=1、P1-03=2、P1-04=1、P1-05=1；COMPOSER-R3-P1-01=1；GROK 如上；CODEX-R3-P2-01/02 字面 ID=0（內容已修，標題「二態」＋`value_per_period` 雙欄，非 ID 回寫義務）
- μ 重算：`0.01/math.sqrt(8760)=1.0684346079267205e-04`；SPEC 列 `1.068434607926721e-04`；`abs(diff)=5e-20 ≤ atol 1e-18`；舊字面 `1.0683760683760685e-04 == 0.01/93.6` 已不在 §G
- 殘字：`grep value=nan` → 0；Task 1.2 退化改雙欄皆 nan＋`reason=degenerate_returns`
- `external_declared`：L481-492 一律 `universe_provenance_unverifiable`（非成功路徑）
- DSR N 歧義量級：`Φ⁻¹(1-1/N)` 於 N=50／100 → 2.0537／2.3263（比約 1.13）——選錯 `n_fields` 會系統性改 SR0
- `reasons` 9 值含 `ledger_snapshot_mismatch`／`universe_provenance_unverifiable`／`degenerate_returns`；頂層鍵表仍寫「僅含 13」且未列 `reason_conditions`

---

## Verdict：可進 TODO 生成

本家 R3 兩條 **CLOSED**。F1–F4 主幹（PBO 四步＋`n_obs`/`n_candidates`、μ 唯一推導、ledger snapshot 綁定骨架、`external_declared` 封閉、objective 傳遞鏈、`value=nan` 雙欄）已落地，足以起草 B1–B4 TODO。

**BLOCKING 清單：無。**

本輪新 finding 2×MAJOR（契約鍵集合自相矛盾；DSR 之 N 取自哪個 `n_fields` 未釘死）皆判定 **可作具名殘留帶進 TODO**（見 §3），不要求再修一輪 SPEC 才准生成 TODO。勿無限迴圈規格細節。

---

## 1. Closure 表（本家 R3 → SPEC R4）

| R3 ID | 狀態 | 證據摘要 |
|---|---|---|
| GROK-R3-P1-01 | **CLOSED** | §G L107-111：刪假等式；唯一式 `mu = σ * target_ann_sr / sqrt(resolve_periods_per_year("1h"))`＝`0.01/sqrt(8760)`＝`1.068434607926721e-04`；golden **測試中重算**斷言 `atol=1e-18`、禁抄字面。本輪 `abs(derived-spec)≤1e-18`；舊 `0.01/93.6` 字面已消失。 |
| GROK-R3-P2-01 | **CLOSED** | Task 1.2 L145-150：退化 ⇒ `value_per_period` **與** `value_annualized` 皆 nan、`sr_estimator_variance` nan、`reason=degenerate_returns`；驗證改 `math.isnan` 雙欄。`grep value=nan`＝0。 |

---

## 1b. Closure 表（R4 synth F1–F4／codex 五條 BLOCKING — 複驗）

| 群集／ID | 狀態 | 證據摘要 |
|---|---|---|
| F1 CODEX-R3-P0-01 | **CLOSED**（演算法主幹） | Task 4.2：必填 `n_obs`/`n_candidates`；shape 恰 `(n_obs,n_candidates)`；四步＝IS metric（sharpe→`value_per_period`／mean_return→算術平均）→ champion 平手最小索引 → OOS 平均排名 `r=rank/(N_valid+1)` → `ω=ln(r/(1-r))`；驗收③ 轉置 raise **且** 合法 T&lt;N 不 raise；④／④b 平手。本輪攻擊 assumed「足以雙實作同 PBO」→ **主幹成立**（見 §2）。 |
| F2 μ 三家 | **CLOSED** | 同上 GROK-R3-P1-01。 |
| F3 CODEX-R3-P1-02 | **PARTIAL** | 型別／`required|optional`／`additional_properties:false`／`reason_conditions` **文字義務**已寫（L255-259）；但 `reason_conditions` **不在**「僅含 13 頂層鍵」清單，與邊界④「未知頂層鍵拒」衝突 → 見 GROK-R4-P1-01。24 案例仍只笛卡兒 status，不直接證 reason 一對一表內容。 |
| F3 CODEX-R3-P1-03 | **PARTIAL** | `ledger_result` typed、在場時 `n_trials is None`、len≤`n_valid_metrics`、`input_artifact_hash` 一致、`ledger_snapshot_mismatch`／`degenerate_returns` 已寫。**未釘** SR0 公式之 N ∈ {`n_candidates_considered`,`n_evaluated`,`n_valid_metrics`} → GROK-R4-P1-02。驗收⑤ 仍寫舊名 `cross_trial_sr_values`（殘字，併入 P1-02 碼證，不另立）。 |
| F4 CODEX-R3-P1-04 | **CLOSED**（`external_declared`）／**殘留**（`full_grid`） | `external_declared` 成功路徑已封（L481-492）。`full_grid`＋自備 `candidate_set_hash` 在「識別集合＝矩陣所帶集合」時仍可自洽通關（純統計層無外部宇宙 SoT）——**具名殘留**，不重開 BLOCKING；`ledger_all_candidates` 可對 ledger 重算，較硬。 |
| F4 CODEX-R3-P1-05 | **CLOSED** | Task 1.3 L198-208：`evaluate()` 傳 `timeframe` 入 `run_backtest`；`:113` 用 `result.annualization["periods_per_year"]`；斷言 ②b 與 engine 直呼同值且 ≠ None。 |
| GROK-R3-P2-01／標題三態 | **CLOSED** | 見上；Task 3.2 標題已「二態」。 |

---

## 2. 挑戰 brief assumed

| assumed | 本輪 |
|---|---|
| F1 四步演算法足以雙獨立實作同 PBO | **成立（攻後仍立）**。metric／tie-break／平均排名／`r`／`ω`／invalid 全剔除寫死；軸向＋T&lt;N 雙向驗收堵住轉置假說。殘餘：`selection_metric=sharpe` 時 `periods_per_year`/`rf` 未在 PBO 簽名出現，但 `value_per_period` 排名在固定 rf 下與年化無關，golden 相對序可重現。 |
| F3 `reason_conditions`＋`additional_properties:false` 使 24 案例「對證契約而非自洽」 | **不充分（攻破）**。`additional_properties`／型別／必填有助；但 `reason_conditions` 與 13 鍵封閉集互斥（P1-01），且 24 案例不覆蓋 reason 觸發表內容 → 契約完備性義務**半落地**。 |
| F4 `candidate_set_hash` 重算使宇宙守衛不可靠自我宣告通關 | **對 `external_declared` 成立；對 `full_grid` 不充分**。後者在「count+hash 皆對自己的子集」時仍可通；`ledger_all_candidates` 才有外部集合。屬純統計交付邊界，宜具名殘留而非再開 BLOCKING。 |
| 剩餘未關項皆可具名殘留進 TODO、不損 B1–B4 正確性 | **成立（攻後仍立）**。見 §3：兩條 MAJOR 皆 yes；補鍵／釘 N 在 TODO Task 2.1／3.2 即可，不需重做 phase 切分或公式族。 |

---

## 3. 具名殘留 → TODO？（brief 必答 3）

| 項 | 可殘留進 TODO？ | 理由 |
|---|---|---|
| GROK-R4-P1-01（13 鍵 vs `reason_conditions`） | **yes** | 只動契約 JSON 形狀（第 14 鍵或嵌套 schema）；不改 B1 頻率／Sharpe／B3–B4 統計公式。TODO Task 2.1 寫死鍵集合後實作即可。 |
| GROK-R4-P1-02（DSR 之 N 欄位） | **yes** | 一行 SoT：`N := ledger_result.n_valid_metrics`（或主委另選）＋驗收；不改 DSR 公式結構。未釘前兩實作可能差 Φ⁻¹ 量級 ~13%（N=50 vs 100），故須在 **Task 3.2 動工前**於 TODO 釘死，但**不擋 TODO 生成**。 |
| `full_grid` 自洽通關 | **yes**（建議 §N 一句） | 純統計層無全宇宙 artifact 時之誠實邊界；`external_declared` 已封；接線批再綁不可變宇宙 SoT。 |
| 驗收⑤ `cross_trial_sr_values` 舊名 | **yes** | 用語對齊 `ledger_result.valid_sharpe_values`；不改語意。 |

---

## Findings（僅新 R4）

## GROK-R4-P1-01

**斷言**: Task 2.1 同時要求 (a) JSON **僅含**固定 13 個頂層鍵，且邊界④拒絕未知頂層鍵，與 (b) 同檔必須提供頂層語意之 `reason_conditions` 一對一對照表——二者互斥；實作者無法同時滿足而不違反其一。

**碼證**: `docs/GAP1_STRATEGY_OVERFIT_SPEC.md` L230-233 列死 13 鍵（至 `reasons` 止，**無** `reason_conditions`）；L255-259 又要求「提供 `reason_conditions` 對照表」＋`additional_properties: false`；L268 驗收⑤「13 個頂層鍵齊備」；L269 邊界④「未知頂層鍵 ⇒ validate rc!=0」。RECHECK：`grep -n '僅含\|reason_conditions\|13 個頂層' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`。若把表塞進 `reasons` 則與「`reasons`＝9 個 reason **字串**唯一來源」（L251-254）衝突。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[MAJOR] 信心度=High。會怎麼失敗：① 加第 14 鍵 → 觸「僅含／未知鍵」；② 不加表 → 違反 F3 完備性義務，reason 一對一無法機器對證；③ 改寫 `reasons` 結構 → 全檔 reason 字面契約漂移。  
**不列 BLOCKING**：不阻止 TODO 生成；TODO 可改「14 鍵含 `reason_conditions`」或規定其嵌套位置並同步驗收⑤。  
修法建議（供 TODO，非本輪改 SPEC）：頂層鍵集合改 14，或明定 `reason_conditions` 為獨立副檔／`reasons` 旁之 schema 節，並改邊界④白名單。

---

## GROK-R4-P1-02

**斷言**: Task 3.2 在 `variance_source="ledger_cross_trial"` 時要求 N 與 values 同屬 `LedgerReadResult`，但未規定 SR0 公式之整數 N 取自 `n_fields` 哪一欄（`n_candidates_considered`／`n_evaluated`／`n_valid_metrics` 三者可互不相等）；兩實作可自洽綠燈卻產出不同 DSR。

**碼證**: L237 `n_fields` 五欄並列；L345-365 snapshot 綁定只寫 `ledger_result` 在場、`n_trials is None`、`len(valid_sharpe_values) <= n_valid_metrics`、hash 一致——**無** `N = ledger_result.<field>`。Task 2.2 斷言⑤ 明示同 candidate 兩 attempt ⇒ `n_candidates_considered==1` 且 `n_evaluated==2`（三欄本就可分叉）。本輪：`Φ⁻¹(1-1/100)/Φ⁻¹(1-1/50)≈1.133`。另 L375 驗收⑤ 仍寫 `len(cross_trial_sr_values)`（簽名主路徑已是 `ledger_result`）——用語殘留，證 dataflow 改寫未完全掃驗收字面。RECHECK：`grep -n 'n_valid_metrics\|n_trials\|cross_trial_sr_values\|ledger_result' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[MAJOR] 信心度=High。會怎麼失敗：呼叫方／實作取較大 N 做 SR0 deflation、卻用較短 `valid_sharpe_values` 估 V，統計物件仍「同 snapshot」但 N 語意漂移（原 CODEX-R3-P1-03 未關完之核）。  
**不列 BLOCKING**；**可殘留 TODO**：Task 3.2 動工前釘死一行（建議與 values 對齊：`N := n_valid_metrics`，且 `N == len(valid_sharpe_values)` 或另寫允許 `n_is_lower_bound` 時之關係）＋參數化驗收；並把⑤之 `cross_trial_sr_values` 改名。

---

## BLOCKING 清單（進 TODO 前）

**無。**

建議 TODO 起草時吸收（非阻擋）：
1. GROK-R4-P1-01 — 契約鍵集合與 `reason_conditions` 安置
2. GROK-R4-P1-02 — DSR 之 N 欄位 SoT ＋驗收⑤ 舊名
3. （可選 §N）`full_grid` 在無外部宇宙 artifact 時之誠實邊界

---

## 必答對照

1. **closure**：本家 2/2 CLOSED；F1／F2／P1-05／`external_declared`／`value=nan` CLOSED；F3 契約完備性與 DSR-N **PARTIAL**（升本輪兩 MAJOR）；`full_grid` 殘留可名。
2. **可否進 TODO**：**是** — BLOCKING 空。
3. **殘留可否進 TODO 不損正確性**：兩 MAJOR 皆 **yes**（見 §3）；須在對應 Task 動工前於 TODO 釘死，而非實作中「自行判斷」。

---

## 被當成事實的未驗證假設（§0）

| 陳述位置 | fact / assumed | 本輪 |
|---|---|---|
| brief：F1 四步 ⇒ 雙實作同 PBO | assumed | 攻後**成立**（主幹） |
| brief：F3 reason 表 ⇒ 24 案例非自洽 | assumed | **不成立**（鍵集合衝突＋案例不覆蓋表） |
| brief：hash ⇒ 宇宙不可自我宣告 | assumed | **部分成立**（封 external；full_grid 仍弱） |
| brief：剩餘皆可殘留進 TODO | assumed | **成立** |
| SPEC R4「reason_conditions 已使契約完備」語氣 | 呈述為已修 | 義務有、安置無 → 見 P1-01 |

---

ASSUMPTIONS_VERIFIED: 本家 R3 兩條 closure 重跑；μ IEEE vs 字面 atol；value=nan 清零；external_declared 封閉；PBO 四步原文；13 鍵 vs reason_conditions 互斥；DSR N 欄未釘＋Φ⁻¹ 量級；synth body sha ad0988e951eb；template PASS
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS；python μ／Φ⁻¹；逐 ID grep-c；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r5-grok.md --family grok`（交件前自跑，見下）
FAILURES_SEEN: none（本輪無改碼）
SCOPE_CHANGES: none（只讀審查＋本 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC／碼）；finding 建議契約 14 鍵或嵌套、以及 N 欄 SoT
OUTPUT_ARTIFACT: handoffs/20260817-gap1-specadv-r5-grok.md

STATUS: DONE
