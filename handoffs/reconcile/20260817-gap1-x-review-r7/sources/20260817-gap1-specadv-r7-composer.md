# GAP-1 SPEC R6 受限閉合複驗 — COMPOSER

**task-id**: `20260817-GAP1-X-REVIEW-R7` | **family**: composer | **brief**: `handoffs/20260817-gap1-specadv-r7-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`503fd8a184f2`（R6 修補後）
**上一輪 FATAL 來源**：`handoffs/20260817-gap1-specadv-r6-codex.md`（`CODEX-R5-P0-01`～`04`）
**R6 收斂處置**：`handoffs/reconcile/20260817-gap1-x-review-r6/synth.md`（H1 四條全採）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS` rc=0
- `sha256sum docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `503fd8a184f2…`
- `grep -c "13 個頂層" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 0
- 四條 FATAL ID `grep -c`：P0-01=1、P0-02=2、P0-03=1、P0-04=2（皆 ≥1）
- P0-01 數值探針（codex 原始）：全域 `N=3,rank=2` → `ω=0.0`；path-local `N=2` → `ω=0.693147…`；SPEC 現釘 `N_valid_on_path`（`SPEC:490-492`）⇒ 後者為唯一定義
- P0-03 hash 探針：`sha256(sorted 10 ids)` ≠ `sha256(sorted 50 ids)`（前綴 `b7b73ec1…` vs `b16bfc28…`）⇒ top-K 子集 hash 不可冒充全集
- P0-04 尺度探針：`annualized/per_period` 變異數比＝730（`periods_per_year=730` fixture）⇒ `metric_unit` 釘死有必要性

---

## Verdict：可進 TODO 生成

四條 R5 FATAL 修補經本輪逐條複驗**全部 CLOSED**；重跑 codex 原始反例／探針後無 **OPEN**／**PARTIAL**。**BLOCKING 清單：無。**

---

## 1. 四條 FATAL closure 表（本輪唯一任務）

| FATAL ID | 狀態 | 複驗證據（重跑同一反例） |
|---|---|---|
| CODEX-R5-P0-01（PBO rank 分母） | **CLOSED** | `SPEC:488-492` 改 `r = rank/(N_valid_on_path + 1)`，明示 `scipy.stats.rankdata(method="average")`；**無** `rank/(N_valid+1)` 殘留（`rg 'rank/\(N_valid[^_]'` → 0）。驗收 ④c（`SPEC:509-510`）構造 5 vs 3 有效候選雙 path，以 champion 名次相同而 `ω` 不同證明 path-local 分母。數值探針重跑：path-local `ω=0.693147…` 為契約值，全域分母 `ω=0.0` 已排除。 |
| CODEX-R5-P0-02（snapshot membership） | **CLOSED** | `PeriodReturns.source_artifact_hash` 必填（`SPEC:165-166`）；`LedgerReadResult.artifact_hashes: frozenset[str]`（`SPEC:297-298`）；DSR 改 **集合成員** `source_artifact_hash ∈ artifact_hashes`（`SPEC:391-393`），非 digest 反推。原反例「digest 無法 membership」已不可成立——typed dataflow 欄位齊備且可機械實作。 |
| CODEX-R5-P0-03（universe 守衛缺輸入） | **CLOSED** | PBO 簽名新增 `candidate_ids`＋`ledger_result`（`SPEC:471-474`）；守衛驗 ① `set(candidate_ids)` 集合相等 ② count 三方相等 ③ `sha256(",".join(sorted(candidate_ids)))`（`SPEC:531-535`）。驗收 ⑤b（`SPEC:551-553`）重述 codex 原始 top-K 反例：ledger 50 候選、只傳績效最佳 10 個且自算 hash 正確 ⇒ 仍 `universe_provenance_unverifiable`（集合相等檢查擋下）。`full_grid`／`external_declared` 成功路徑仍封（`SPEC:537-540,547-548`）。 |
| CODEX-R5-P0-04（ledger Sharpe 單位） | **CLOSED** | `ledger_record_keys` 新增必填 `metric_unit`；頂層鍵 14→**15**（`SPEC:231-237,283-284`）；`metric_unit_values`＝`per_period`／`annualized`；`valid_sharpe_values` **只**收 `metric_unit="per_period"`（`SPEC:309-311`），`annualized` row ⇒ `ledger_row_invalid` 且不進樣本。與 DSR per-period 鎖定（`SPEC:382-383,397`）一致。尺度探針：混入 annualized 會使跨 trial 變異數放大 730×，現契約以 row 級拒收封閉。 |

---

## 2. 是否可進 TODO 生成？（必答 2）

**是。** 四條 FATAL 均已 CLOSED；無滿足「不修則 B1–B4 數值錯誤或不可重現且附可執行反例」之新 BLOCKING。

**BLOCKING 清單（僅 FATAL）：無。**

---

## 3. 若仍 OPEN：可否作具名殘留帶進 TODO？（必答 3）

**不適用**（四條皆 CLOSED）。若僅剩 reconcile synth 所列 6 項具名殘留（§N 接線、C1 bypass、ml_pipeline 展示、adaptive N、MinBTL 誤差、`universe_provenance` dataclass 欄位列舉）⇒ **yes**，理由＝皆不影響 B1–B4 純統計核心之數值正確性，可在 TODO 任務級釘死。

---

## 4. 挑戰前提（brief assumed）

| assumed | 本輪 |
|---|---|
| 四條修補皆已使兩個獨立實作得到相同數值，且 top-K 污染路徑已封閉 | **成立**（§1 四條 CLOSED；⑤b＋集合相等＋path-local 分母＋`metric_unit` 拒收） |
| 6 項具名殘留皆不影響 B1–B4 正確性 | **成立**（未發現可執行反例推翻；本輪不受理新一般性 SPEC 議題） |

---

## Findings（本輪新 finding：sentinel）

## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對 R5 四條 FATAL（`CODEX-R5-P0-01`～`04`）於 SPEC R6 之修補與 codex 原始反例重跑後，無達 **FATAL** 門檻之未關項或新缺陷。

**碼證**: `template_check` PASS；SPEC sha `503fd8a184f2`；`grep -c "13 個頂層"`→0；四 FATAL ID grep≥1；P0-01 `SPEC:490-492,509-510`＋ω 探針；P0-02 `SPEC:165-166,297-298,391-393`；P0-03 `SPEC:471-474,531-535,551-553`＋hash 探針；P0-04 `SPEC:231-237,309-311,283-284`＋730× 尺度探針。RECHECK：同上命令＋`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '165,166p;231,237p;283,311p;391,393p;471,474p;488,510p;531,553p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#503fd8a184f2

[P3] 信心度=High。核對依據＝§1 closure 表四條狀態＋§4 assumed 表；刻意不捏造 finding 湊數。

---

## 被當成事實的未驗證假設（§0）

無（本輪僅複驗四條已修 FATAL；brief 兩條 assumed 經 §1／§4 攻擊後仍成立）。

---

ASSUMPTIONS_VERIFIED: template_check PASS；SPEC sha 503fd8a184f2；四 FATAL ID grep≥1；13鍵殘字=0；四條段落對照＋三組數值探針
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS rc=0；`sha256sum`；5× `grep -c`；`venv/bin/python -c`（ω／hash／variance 探針）；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r7-composer.md --family composer` → `COMPLETENESS PASS(single)` rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC）
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r7-composer.md`
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留未動
STATUS: DONE
