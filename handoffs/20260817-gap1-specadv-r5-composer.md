# GAP-1 SPEC R4 複審 — COMPOSER（R5 closure 複驗）

**task-id**: `20260817-GAP1-X-REVIEW-R5` | **family**: composer | **brief**: `handoffs/20260817-gap1-specadv-r5-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`f7321c906af7`（commit `85f1a70e`）
**R4 本家**：`handoffs/20260817-gap1-specadv-r4-composer.md`（1 條 finding：`COMPOSER-R3-P1-01`）
**R4 收斂**：`handoffs/reconcile/20260817-gap1-x-review-r4/synth.md`（群集 F1–F4；11/11 具名引用）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS` rc=0
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `f7321c906af7…`
- μ 重算：`0.01/math.sqrt(8760)=1.068434607926721e-04` 與 §G 字面 bit-match（`atol<1e-18`）
- 逐 ID `grep -c`（11 條）：CODEX P0-01=3、P1-01/02/03/04/05 各≥1、COMPOSER-R3-P1-01=1、GROK P1-01/P2-01 各≥1；P2-01/P2-02 修補後無 ID 殘留（`value=nan` grep=0；Task 3.2 標題已改「二態」）
- PBO 軸向探針：`(50,1200)` 合法 T<N 與轉置 `(1200,50)` 在必填 `n_obs`/`n_candidates` 下可判定（§G brief 前提與 Task 4.2:461-463 雙向斷言）

---

## Verdict：可進 TODO 生成

R4 本家唯一 finding（μ 假等式）已在 SPEC R4 **CLOSED**。reconcile F1–F4 對 codex 五條 BLOCKING 之修補經本輪逐條複驗**實質關閉**；brief 四條 assumed 攻擊後無新 BLOCKING。**BLOCKING 清單：無。**

---

## 1. Closure 表（COMPOSER R4 本家）

| R4 ID | 狀態 | 證據摘要 |
|---|---|---|
| COMPOSER-R3-P1-01 | **CLOSED** | §G:106-111 改為唯一推導式＋完整精度 `1.068434607926721e-04`，並要求 golden **測試內重算**（`atol=1e-18`）禁抄字面。本輪：`derived=spec_literal`（`|diff|<1e-18`）；前版假等式 `0.01/93.6` 已移除。 |

---

## 2. Closure 表（reconcile F1–F4 群集 — R4 修補複驗）

| 群集 | 引用 ID | 狀態 | 證據摘要 |
|---|---|---|---|
| F1 PBO 演算法 | CODEX-R3-P0-01 | **CLOSED** | Task 4.2:439-467 必填 `n_obs`/`n_candidates`；逐 path 四步（IS metric／champion 最小索引平手／OOS 平均排名 `r=rank/(N_valid+1)`／`ω=ln(r/(1-r))`）；驗收③ 轉置 raise＋合法 T<N 不 raise；④b 雙冠 tie-break。 |
| F2 μ 假等式 | CODEX/COMPOSER/GROK-R3-P1-01 | **CLOSED** | 同上 §G；三家一致修補已落地。 |
| F3 契約＋DSR snapshot | CODEX-R3-P1-02/03 | **CLOSED（具名殘留）** | Task 2.1:255-259 型別/required/`additional_properties:false`/`reason_conditions`；reasons 擴至 9 值；Task 3.2:345-366 `ledger_result` 綁定、`n_trials` 互斥、snapshot mismatch/degenerate。殘留：`reason_conditions` 表體由實作填入（SPEC 只定義義務）；DSR 之 N 取自 ledger 哪個 `n_field` 未逐字釘死——見 §4。 |
| F4 守衛＋傳遞鏈 | CODEX-R3-P1-04/05, GROK-R3-P2-01, CODEX-R3-P2-01/02 | **CLOSED** | Task 4.3:481-494 `external_declared` 封閉；`candidate_count`/`candidate_set_hash` 重算比對；Task 1.3:197-208 objective 傳遞鏈＋②b；Task 1.2:145-149 雙欄 nan；Task 3.2 標題改「二態」。 |

---

## 3. 是否可進 TODO 生成

**是。** R4 修補已關閉上轮全部實質 BLOCKING；本輪無新 BLOCKING。

**BLOCKING 清單：無。**

---

## 4. 具名殘留可否帶進 TODO（brief 必答 3）

| 殘留項 | 可帶進 TODO？ | 理由 |
|---|---|---|
| OOS「平均排名」平手公式未寫代數式（僅自然語言＋全平手 oracle ④） | **yes** | 驗收 ④/④b 已釘全平手與 IS 平手；partial tie 可在 TODO 以 scipy `rankdata(method='average')` 或等價一句鎖死，不影響 B1–B4 主幹語意。 |
| `candidate_set_hash` 演算法未指定 | **yes** | 守衛語意＝「重算須一致」；hash 函式與 canonical 序列化在 contract/測試一次鎖定即可，不損 PBO 統計正確性。 |
| DSR `ledger_result` 之 N 未明示 `n_valid_metrics` vs `n_evaluated` | **yes** | snapshot 已綁 `valid_sharpe_values` 與 `n_valid_metrics` 上界；TODO 起草時選一欄寫死並加斷言即可，不阻 B3 公式實作。 |
| `reason_conditions` 表體未預填於 SPEC | **yes** | Task 2.1 已列義務＋Task 3.3 斷言④ 24 案例須過 `validate_against_contract`；屬實作產物非規格缺口。 |

---

## 5. 挑戰前提（brief assumed）

| assumed | 本輪 |
|---|---|
| F1 四步演算法足以讓兩實作得相同 PBO | **成立**（軸向＋四步＋oracle 斷言；partial OOS tie 為 MINOR 殘留，非 BLOCKING） |
| F3 `reason_conditions` 使 24 案例對證契約 | **成立**（型別/required/額外鍵三驗＋24×`validate_against_contract`） |
| F4 `candidate_set_hash` 重算比對封閉自我宣告 | **成立**（`external_declared` 一律拒；count/hash 不符同 reason） |
| 剩餘未關項可作具名殘留帶進 TODO | **成立**（見 §4；不損 B1–B4 正確性） |

---

## Findings（本輪新 finding：sentinel）

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
