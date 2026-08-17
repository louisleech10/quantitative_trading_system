# Reconcile — 20260817-gap1-x-review-r7

**來源** 20260817-gap1-specadv-r7-codex.md, 20260817-gap1-specadv-r7-composer.md, 20260817-gap1-specadv-r7-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；受限閉合複驗輪 → SPEC R7）

本輪為**範圍受限**之閉合複驗（僅四條 R5 FATAL）。三家共 **3 條** canonical ID
（codex 1 條 OPEN／grok 與 composer 各 1 個 zero-findings sentinel）。下列一群集**引用全部 3 條，0 掉項**。
VERIFY: `grep -c "ledger_result.candidate_ids\|CODEX-R6" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 4（Claude 實跑）；
`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → TEMPLATE PASS。

### 四條 R5 FATAL 之三家 closure 判定
| R5 FATAL | codex | composer | grok | 主委裁定 |
|---|---|---|---|---|
| P0-01 PBO rank 分母 | CLOSED | CLOSED | CLOSED | **CLOSED**（三家一致；數值探針一致：path-local `ω=0.693147` vs 全域 `ω=0.0`） |
| P0-02 snapshot membership | CLOSED | CLOSED | CLOSED | **CLOSED**（`source_artifact_hash ∈ artifact_hashes` 集合成員） |
| P0-03 universe 守衛 | **OPEN** | CLOSED | CLOSED | **本輪修補後 CLOSED**（見 I1；codex 對，另兩家漏） |
| P0-04 ledger Sharpe 單位 | CLOSED | CLOSED | CLOSED | **CLOSED**（尺度探針：混入 annualized 使跨 trial variance 放大 730×，現 row 級 fail-closed） |

### I1 — codex 之 OPEN：守衛有檢查、卻無被檢查之資料欄位（主委承認並修）
**引用**: CODEX-R6-P0-01, GROK-R6-P3-00, COMPOSER-R6-P3-00

codex 判 OPEN 且明確回答「**不可**作具名殘留」，理由＝「同數量、不同候選集合可產生不同 PBO
⇒ 使 B4 產出數值錯誤或不可重現」。主委複核後**認定 codex 正確、另兩家漏判**：
R6 版 Task 4.3 要求「`set(candidate_ids)` 等於 ledger 之 candidate_id 集合」，
但 Task 2.2 之 `LedgerReadResult` **欄位清單中沒有該集合** ⇒ 檢查無資料可比，集合等式不可執行；
composer／grok 判 CLOSED 係只核對「守衛條文存在」而未回查資料流是否齊備（此即 codex 反覆比另兩家
更嚴之處，與前六輪同一模式）。

**處置（SPEC R7，一欄位級修補）**：
1. `LedgerReadResult` 新增 **`candidate_ids: frozenset[str]`**（所有已讀 row 之 `candidate_id` 集合），
   並定不變式 `len(candidate_ids) == n_candidates_considered`（新增驗收 ⑥c，含同 candidate 多 attempt fixture）。
2. Task 4.3 守衛條文 ① 改為 `frozenset(candidate_ids) == ledger_result.candidate_ids`，明示資料來源。
3. 新增驗收 **⑤b2＝codex 本輪指出之「同數量不同集合」反例**（ledger 50 vs 呼叫方 50 但其中 1 個 id 不同，
   count 三方相等且自算 hash 正確 ⇒ 仍 `universe_provenance_unverifiable`）——
   此例正是 count 檢查擋不住、唯集合相等可擋者，故必測。
4. 兩個 sentinel 之複驗結論（四條全 CLOSED、無新 FATAL、殘留 6 項判不影響 B1–B4）一併記錄；
   其對 P0-03 之 CLOSED 判定經本輪裁定為**誤判**，已具名於上表。

### 收斂結論（主委）
- 四條 R5 FATAL：**全數 CLOSED**（P0-03 於本輪一欄位修補後關閉）。
- 收斂軌跡：R1 23 → R2 7 → R3 11 → R4 7 → R5 4 → **R6 1**（且為一欄位級）。
- **SPEC 修訂於此收束**：三家已無滿足受限門檻之未關項；本輪唯一 OPEN 已修。
  進 TODO 攜帶之具名殘留維持 6 項（見 review-r6 收斂檔 H2 後清單），另新增 0 項。

**Verdict**: 需修補後合併 → **已於 SPEC R7 修補完成**（1/1 具名引用，`template_check` PASS）。
下一步＝**白話閘（使用者審閱最終 SPEC，阻塞）**，通過後生成 TODO；
`review-r4`／`r5`／`r6`／`r7` 四份收斂檔之戳記於白話閘期間並行補齊。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R6-P0-01

**斷言**: R6 沒有把 ledger 的 candidate-id 集合（或等價的不可變 membership proof）放進 `LedgerReadResult` dataflow；因此 `ledger_all_candidates` 的集合相等守衛仍不可實作，同數量但不同 candidate IDs 的 PBO 輸入可通過目前可取得的 count/hash 檢查。

**碼證**: `nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '290,315p;522,555p'` 顯示 `LedgerReadResult` 回傳欄位含 `n_candidates_considered`、`snapshot_hash`、`artifact_hashes`、`valid_sharpe_values`，未列 candidate-id 集合；同處 `SPEC:531-535` 卻要求 `set(candidate_ids)` 等於 ledger candidate-id 集合。`rg -n "candidate_id|candidate_ids|LedgerReadResult" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 的命中只涵蓋 ledger row schema、PBO signature、guard 文字與測試文字，沒有 `LedgerReadResult` 的 candidate-id 欄位。原始問題的可重跑數值 probe：`venv/bin/python -c 'from hashlib import sha256; ids=[f"top-{i}" for i in range(10)]; candidate_count=10; n_candidates=10; ledger_n_candidates_considered=10; supplied_hash=sha256(",".join(sorted(ids)).encode()).hexdigest(); count_checks=(candidate_count==ledger_n_candidates_considered==n_candidates==len(ids)); hash_checks=(supplied_hash == sha256(",".join(sorted(ids)).encode()).hexdigest()); print("P0-03 same-size count_checks=%s supplied_hash_self_consistent=%s supplied_hash=%s" % (count_checks, hash_checks, supplied_hash))'` → `count_checks=True supplied_hash_self_consistent=True supplied_hash=f1b33d9a0562c54e0b3fb5e70ba62488126c5b9205b43b066c7da32a69ad626b`, rc=0. 這代表若 ledger 真實集合是另一組同數量 IDs，現有 typed 輸入仍沒有可比較的值；需要在 `LedgerReadResult` 增加 canonical candidate-id 集合／不可變 membership proof，並讓 guard 以它完成 ①。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#503fd8a184f2

[BLOCKING] 信心度=High；這是上一輪 `CODEX-R5-P0-03` 的 closure 未完成，不是新的一般性 SPEC 議題。即使原始 50→10 top-K fixture 會被 count mismatch 擋下，同數量不同 universe 仍可通過自算 hash；PBO 會在未被 ledger 證明的候選宇宙上計算，數值不可接受。不可作具名 RESIDUAL-OK 帶進 TODO，因為直接影響 B4 的 selection-free／PBO 正確性。

## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對 R5 四條 FATAL（`CODEX-R5-P0-01`～`04`）於 SPEC R6 之修補與 codex 原始反例重跑後，無達 **FATAL** 門檻之未關項或新缺陷。

**碼證**: `template_check` PASS；SPEC sha `503fd8a184f2`；`grep -c "13 個頂層"`→0；四 FATAL ID grep≥1；P0-01 `SPEC:490-492,509-510`＋ω 探針；P0-02 `SPEC:165-166,297-298,391-393`；P0-03 `SPEC:471-474,531-535,551-553`＋hash 探針；P0-04 `SPEC:231-237,309-311,283-284`＋730× 尺度探針。RECHECK：同上命令＋`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '165,166p;231,237p;283,311p;391,393p;471,474p;488,510p;531,553p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#503fd8a184f2

[P3] 信心度=High。核對依據＝§1 closure 表四條狀態＋§4 assumed 表；刻意不捏造 finding 湊數。

---

## GROK-R6-P3-00

**斷言**: 本輪逐項核對 `CODEX-R5-P0-01`～`04` 於 SPEC R6 之修補後，四條皆 **CLOSED**；重跑 path-local rank 分母、snapshot 集合成員、top-K 50→10 集合相等、Sharpe 單位尺度四類反例後，無剩餘會使 B1–B4 產出數值錯誤或不可重現之 finding；6 項具名殘留仍為 RESIDUAL-OK。

**碼證**: (1) `template_check` PASS；(2) SPEC sha `503fd8a184f2`（commit `56cfb961`）；(3) 四 ID grep-c ≥1；(4) `13 個頂層` count=0、頂層鍵 15；(5) `SPEC:489-510` `N_valid_on_path`＋④c；(6) `SPEC:165-166,297-298,391-393` `source_artifact_hash`／`artifact_hashes` 集合成員；(7) `SPEC:471-473,530-554` `candidate_ids`＋`ledger_result`＋⑤b；(8) `SPEC:243-247,309-311` `metric_unit`／`valid_sharpe_values` 只收 `per_period`；(9) 數值 probe：path N=2 rank=2 → ω≈0.693 vs 全域 N=3 → ω=0；50≠10 set equality False。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '160,175p;230,315p;370,410p;469,555p'`；`python3` 重跑 rank／hash／set probe。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#503fd8a184f2

[P3] 信心度=High。核對依據＝§1 closure 表＋§3 殘留二分＋§4 assumed 攻擊＋上列實跑命令；本輪逐項核對後無 finding（sentinel）。刻意不捏造實質 finding 湊數。

---


## 戳記

RECONCILE-STAMP: grok APPROVED 2026-08-17 sha256:ad4c5c535461276f43c9a577f22502d76b0399d819727d9a63c7bd227840ab63 task:20260817-GAP1-X-STAMP-R8

RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:ad4c5c535461276f43c9a577f22502d76b0399d819727d9a63c7bd227840ab63 task:20260817-GAP1-X-STAMP-R8
RECONCILE-STAMP: codex APPROVED 2026-08-17 sha256:ad4c5c535461276f43c9a577f22502d76b0399d819727d9a63c7bd227840ab63 task:20260817-GAP1-X-STAMP-R8
