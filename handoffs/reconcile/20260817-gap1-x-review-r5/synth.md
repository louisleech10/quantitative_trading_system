# Reconcile — 20260817-gap1-x-review-r5

**來源** 20260817-gap1-specadv-r5-codex.md, 20260817-gap1-specadv-r5-composer.md, 20260817-gap1-specadv-r5-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；SPEC R4→R5）

三家共 **7 條** canonical ID（codex 4／grok 2／composer 1 個 zero-findings sentinel）。
下列三群集**引用全部 7 條，0 掉項**。
VERIFY: 逐 ID `grep -c <ID> docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 6/6 新 finding 皆 ≥1（Claude 實跑 2026-08-17）；
`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → TEMPLATE PASS。

### 家族 Verdict 與殘留判斷（brief 必答 3 之回覆）
- **composer：可進 TODO，BLOCKING 無**（其唯一 R3 finding μ 已 CLOSED；F1–F4 逐條複驗實質關閉）。
- **grok：可進 TODO，BLOCKING 無**；兩條新 MAJOR **明確判定可作具名殘留帶進 TODO**
  （原話：「勿無限迴圈規格細節」）。
- **codex：4 條 BLOCKING，且對「可否作具名殘留」明確回 no**（並區分：§N 既有之接線/adaptive 殘留
  可以，但本四項不行）。
**主委裁決＝全採 codex（較嚴版），且不動用「95% 就收」條款**——理由：本輪四條之修補**皆為局部、
可在 SPEC 內一次寫死**（非需另開研究），成本低於再一輪爭辯；其中兩條與 grok 之 MAJOR 為同一缺陷。

### G1 — 契約自相矛盾與 row 型別（codex+grok 同一缺陷）
**引用**: CODEX-R4-P1-01, GROK-R4-P1-01

主委前版同時要求「JSON **僅含** 13 個頂層鍵」與「另須提供 `reason_conditions` 對照表」⇒ **互斥**，
實作者無法同時滿足；且 `ledger_record_keys`／`n_fields` 只有名稱、無型別/必填/額外鍵規則，
非法 ledger row 要求記 reason 但 9 值 enum 無對應者。
**處置**：① 頂層鍵 13→**14**，`reason_conditions` 明列為第 14 鍵，並定義其為
`{reason: {condition, assertion_ref}}` 且 key 集合須與 `reasons` **雙向相等**（測試斷言）
② `ledger_record_keys` 由字串陣列改**物件**（逐鍵 `type`＋`required`）＋`additional_properties: false`
③ reasons 9→**10** 值（新增 `ledger_row_invalid`）；另因 G3 再增 `all_paths_degenerate` ⇒ 共 **11** 值。

### G2 — DSR 之 N 取值與 snapshot identity 未釘死（codex+grok 同一缺陷）
**引用**: CODEX-R4-P1-02, GROK-R4-P1-02

`LedgerReadResult` 有五個 n 欄位而 SPEC 未規定 DSR 用哪一個（三者可互不相等 ⇒ 兩實作皆自洽卻得出
不同 DSR）；亦未規定 snapshot identity 如何與 `period_returns` 比對；且 Task 3.2 驗收⑤ 仍引用
已從簽名移除之 `cross_trial_sr_values`。
**處置**：① `LedgerReadResult` 新增 **`n_for_dsr`**，契約釘死 `n_for_dsr == n_candidates_considered`
（語意＝「試過幾個不同候選」＝多重檢定 N；為契約非慣例，附驗收⑥）
② 新增 **`snapshot_hash`**（＝所有已讀 row 之 `input_artifact_hash` 集合＋`dataset_key`＋
`research_session_id` 之 canonical sha256；重讀同組 ⇒ 同值，多一列 ⇒ 變值，附驗收⑦）
③ DSR 之 N **恆取** `ledger_result.n_for_dsr`，`n_trials` 在 `ledger_result` 在場時必須為 `None`（否則 raise）；
須驗 `period_returns` 之 artifact 屬 `snapshot_hash` 涵蓋集合，不符 ⇒ `ledger_snapshot_mismatch`
④ 驗收⑤ 改引用 `ledger_result.valid_sharpe_values`，新增 ⑤b（同傳 `n_trials` ⇒ raise；snapshot 不涵蓋 ⇒ mismatch）。

### G3 — PBO path 級退化與 universe provenance（codex BLOCKING；後者採比 grok 更嚴之版本）
**引用**: CODEX-R4-P0-01, CODEX-R4-P1-03, COMPOSER-R4-P3-00

① **path 級退化（P0-01）**：`sharpe` metric 在某 path 之切片上遇 `std==0` 會回 NaN，
而 F1 四步未定義 champion／rank／剔除／fail-closed ⇒ 由 NumPy 之 NaN 排序決定結果（不可重現）。
**處置**：新增步驟 3b——該候選於**該 path** 剔除（計 `n_path_exclusions`）；
該 path 剩餘有效候選 <2 ⇒ 跳過該 path（計 `n_paths_skipped`，不入分母）；
所有 path 皆跳過 ⇒ status 非 ok、`reason=all_paths_degenerate`、`value=nan`；
PBO 分母改為 `n_paths_used`；新增驗收⑦⑧（含刻意構造之常數切片 fixture）。
② **universe provenance（P1-03）**：`full_grid` 允許呼叫方自備 `candidate_set_hash`
⇒ 「先 top-K 再對同一子集自算 hash」可通關（codex 反例），PBO 反而給出虛假低過擬合機率。
grok 判此為純統計層邊界、宜具名殘留；**主委採較嚴版**：
**唯一成功路徑＝`ledger_all_candidates`**（須同時傳 `ledger_result`，並驗 hash 由 ledger 之
candidate_id 集合重算、`candidate_count == n_candidates_considered == n_candidates`）；
`full_grid` 與 `external_declared` **一律非成功路徑**（`universe_provenance_unverifiable`），
枚舉保留僅為可辨識地拒絕。新增驗收④b⑤。
③ composer 之 zero-findings sentinel 記錄其複驗結論（F1–F4 實質關閉、brief 四條 assumed 攻擊後無新 BLOCKING）。

### 未採納 / 部分採納
- **grok 對 GROK-R4-P1-01／P1-02 之「可具名殘留」判斷未採用**（改為當輪修完）：理由＝兩條之修補
  各為單處契約條文，成本遠低於留待 TODO 階段再回頭改契約（契約一旦被實作消費，改動面會擴大）。
  此非否決其技術判斷（其判斷正確：確實不損 B1–B4 正確性），而是選擇更便宜的時機。
- **grok 對 `full_grid` 之「具名殘留」建議未採用**：改採 codex 之封閉方案（見 G3②），
  理由＝該路徑正是本票要防的污染面，留為殘留等於留下與目的相反的成功路徑。

**Verdict**: 需修補後合併 → **已於 SPEC R5 逐條修補完成**（6/6 新 finding 具名引用，`template_check` PASS）。
收斂趨勢：R1 23 → R2 7 → R3 11 → R4 7（其中 composer 已連兩輪零 finding、grok 連兩輪判無 BLOCKING）。
**下一輪為 closure 複驗**；若 codex 再產出之新項屬「同型細節且另兩家維持通過」，
主委將依「95% 解法就收・殘留先記錄」具名殘留後進 TODO。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P0-01

**斷言**: PBO 逐 path 的 `sharpe` metric 對 finite 但局部 `std==0` 的候選會回 NaN，而 SPEC 沒有定義 champion、OOS rank、path 排除或 fail-closed reason；因此 F1 的四步演算法仍不足以讓獨立實作得到相同結果。

**碼證**: `SPEC:446-455` 只把整個候選含 NaN/inf 視為 invalid，未處理 path slice 的退化；`SPEC:145-146` 又明定 `std==0` 的 Sharpe 為 NaN。實跑 `venv/bin/python -c 'import numpy as np; ...'` → `global finite [True, True]`、`candidate0 IS std 0.0 sharpe nan per Task 1.2`、`candidate1 ... sharpe finite 2.1213203435596424`；同一規則下 `max`/rank 遇 NaN 未定義。RECHECK：重跑該命令，或以 `s_blocks=2` 使 IS/OOS 各只有一筆，直接觸發 `n_obs<2`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；這不是「函式尚不存在」問題，而是已寫死的輸入邊界與 PBO 演算法互相留下未定義分支。修法：明定 path-level metric 退化的拒絕/剔除與分母、全 path 不可算時的 status/reason，並以包含局部常數 slice 的 reference oracle 驗證；不能默默讓 Python/NumPy NaN 排序決定結果。

## CODEX-R4-P1-01

**斷言**: Task 2.1 的機器 contract 仍不可唯一實作：它要求「僅 13 個頂層鍵」卻另要求 `reason_conditions`，未說明其巢狀位置；`ledger_record_keys`/`n_fields` 仍只有名稱而無 row 型別/required 規則；非法 ledger row 要記 reason，但 9 值 enum 沒有對應非法列 reason。

**碼證**: `SPEC:230-233` 寫 JSON 含且僅含 13 個頂層鍵；`SPEC:251-259` 才另要求 `reason_conditions`、型別/必填與額外鍵；若 `reason_conditions` 放頂層即違反 13-key，放巢狀則 schema 未定義。`SPEC:235-238` 僅列 ledger/n_fields 名稱，`SPEC:278-289` 要求非法列「記 reason」；`SPEC:251-254` 的 reasons 沒有 `invalid_ledger_record` 或等價字面。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '230,259p;274,289p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；Agent 可自行選 schema 形狀、任意 ledger 型別或把非法列折疊成錯誤 reason，24 案例仍可能與同一份不完整 contract 自洽通過，正中 F3 要防的自洽假綠。修法：在唯一 JSON SoT 明定 `reason_conditions` 的實際層級與 schema，補 ledger row/n_fields 的 type/required/additional-properties，並為每個要求記錄的非 ok 路徑提供唯一 reason。

## CODEX-R4-P1-02

**斷言**: typed `LedgerReadResult` 的加入尚未完成 DSR snapshot binding：Task 2.2 沒有規定五個 N 欄位中哪一個是 DSR 的 N，也沒有規定如何保留/聚合 `input_artifact_hash` 供與 `period_returns` 比對；Task 3.2 驗收仍引用已從 signature 移除的 `cross_trial_sr_values`。

**碼證**: `SPEC:278-283` 的 LedgerReadResult 只明列五個 `n_fields`、`n_semantics`、`valid_sharpe_values`、status/reason，未選定 `n_candidates_considered`／`n_evaluated`／`n_valid_metrics`；`SPEC:345-364` 要求 DSR 驗 `input_artifact_hash` 一致，但 `PeriodReturns` 與 LedgerReadResult 的定義沒有可比較的 hash/snapshot identity；`SPEC:369-377` 仍寫 `len(cross_trial_sr_values)`，而 signature `SPEC:345` 已無此參數。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '274,289p;343,377p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；呼叫方仍可在同一 typed 物件內用錯 N 欄位，或無法證明 `valid_sharpe_values` 與被檢驗報酬是同一 snapshot，導致 SR0 deflation 與跨 trial variance 不屬同一統計物件；測試還沒有可直接呼叫的參數契約。修法：在 `LedgerReadResult` 寫死 `n_for_dsr`、canonical snapshot identity/hash 及 values 的 provenance/一致性規則，並把驗收改用 `ledger_result`，不用已刪除的參數名。

## CODEX-R4-P1-03

**斷言**: `candidate_set_hash` 重算目前仍不是可信 universe provenance：PBO signature 沒有 candidate ID 集合或 `LedgerReadResult`，而 `full_grid` 沒有獨立 expected hash/source；因此先做 top-K 再把同一 50 個 ID 自算 hash、宣稱 `source="full_grid"` 仍可通關。

**碼證**: `SPEC:439-441` 的 PBO signature 只有 `returns_matrix`、N/S、metric、`universe_provenance`；`SPEC:477-486` 的 dataclass 僅列 `selection_free`、`source`、`candidate_set_hash`、`candidate_count`，卻要求由「候選識別集合」重算 hash，該集合不在輸入。`ledger_all_candidates` 只在文字中指向 LedgerReadResult，但 signature 沒有該 result；hash 演算法/ canonical ordering 也未定義。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '437,486p'`，並構造 top-K ID list 自算同 hash 後代入四欄即可滿足現行書面條件。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；這直接保留 F4 要關閉的污染路徑，PBO 可在被挑過的 universe 上給出看似合格的結果。修法：讓 guard 收到可信、不可變且可重算的 candidate ID artifact（或 ledger snapshot），以 canonical hash 演算法與獨立 expected universe identity 比對；只有 count/hash 自洽不足以證明 selection-free。

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對 R4 closure（本家 μ、reconcile F1–F4 共 11 條引用修補）與 brief 四條 assumed 攻擊後，無達 BLOCKING/MAJOR 門檻之新缺陷。

**碼證**: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS；μ 重算與 §G:108-109 一致；11 ID grep≥1（P2 修補項以行為驗證：`grep value=nan`→0、Task 3.2 標題「二態」）；PBO/契約/守衛段落對照 `SPEC:255-259,345-366,439-494`。RECHECK：同上命令＋讀 Task 4.2/2.1/4.3 改法節。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[P3] 信心度=High。核對依據＝closure 表 §1–§2 逐條狀態＋§5 assumed 表；刻意不捏造 finding 湊數。

---

ASSUMPTIONS_VERIFIED: template_check PASS；μ bit-match；11 ID grep；P2 行為驗證；F1–F4 段落對照
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS rc=0；`venv/bin/python -c "import math; ..."` μ 重算；11× `grep -c`；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r5-composer.md --family composer` → `COMPLETENESS PASS(single)` rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC）
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r5-composer.md`
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留未動
STATUS: DONE
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


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:c72955983ab77bebbfffa45eabfa9e6572b07cc7bc5b04114104f5b74888acc6 task:20260817-GAP1-X-STAMP-R6
RECONCILE-STAMP: grok APPROVED 2026-08-17 sha256:c72955983ab77bebbfffa45eabfa9e6572b07cc7bc5b04114104f5b74888acc6 task:20260817-GAP1-X-STAMP-R6
RECONCILE-STAMP: codex APPROVED 2026-08-17 sha256:c72955983ab77bebbfffa45eabfa9e6572b07cc7bc5b04114104f5b74888acc6 task:20260817-GAP1-X-STAMP-R6
