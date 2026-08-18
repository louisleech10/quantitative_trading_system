brief-kind: review

# GAP-2a／2b SPEC adversarial 審查 R6 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R6`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-specadv-r6-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`（R5 P1–P2 修訂版）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| `template_check spec` PASS | fact-verified | **成立** — `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS` |
| 六份 synth `reconcile_stamps_check.sh` 皆 PASS | fact-verified | **成立** — consult-r1／review-r1..r5 各 `RC=0`（三家 APPROVED） |
| SPEC 條文無 survivor_output／canonical_sha／預算 oracle 殘留矛盾 | assumed | **成立** — 機械 grep 見必答 2；R5 P1–P2 修訂已寫回 |
| 五批 B1→B5 各批可獨立綠、無 forward dependency | assumed | **成立** — 見必答 3；本輪獨立複核 R5 P1–P2 未發現新依賴破口 |

---

## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對 R5 P1–P2 修訂均已條文級閉合；條文級 grep 無殘留矛盾；五批批次邊界無新 forward dependency。

**碼證**: **P1** — `docs/GAP2_MARGINAL_IC_SPEC.md:213`：`identity_missing`／`write_failed` 兩個 failure literal 皆為完整五鍵 `{status, reason, path:null, sha256:null, case_id:<…>}`，與 L211 五鍵恆存在契約一致；L214 驗證⓪ 三形狀 exact-key gate；V-24（L270）mutation 省略 `path`／`sha256` 鍵 ⇒ ⓪ 轉紅。**P2** — L278「已知不測：**無**」——OOM 由 L273 計數 gate（`max_survivors_for_loo`／`max_removed_candidates` 預設 200 ⇒ ≤600）＋Task 4.3 receipt（L224 `n_regressions==600`、receipt 只記錄不設閾值）覆蓋；並發由 L214 驗證⑦（兩執行緒同 case_id ⇒ 完整 JSON）＋L278 原子寫敘述覆蓋；L273 邊界目錄「並發寫 ✓」「OOM 降載 ✓」與章程不再互斥。交叉：`grep -n 'Task 3\.1 之契約檔\|k≤數十\|四鍵\|reasons 加\|reasons 增鍵'` → 0 輸出；六份 stamp PASS；`template_check` PASS。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#ab24897d5bb2

[P3] 信心度=High。R6 為收斂確認輪；本輪對 R5 reconcile 兩處修訂做獨立複核（非沿用上輪 sentinel），未發現新反例或條文級矛盾。觀察（不升格）：L211 正文誤寫「Task 4.2 驗證⑦ 三形狀」而 L214 實際為 ⓪（三形狀）／⑦（並發）分開編號，V-24 已指 ⓪——實作者以 L214 為準，不阻 TODO。

---

## 必答 1–3

### 1. R5 P1–P2 逐條閉合

| 群集 | Verdict | 核對摘要 |
|---|---|---|
| **P1** Task 4.2 失敗形狀五鍵 literal | **閉合** | L213 兩個 failure literal 皆含 `{status, reason, path:null, sha256:null, case_id}` 五鍵；L214 ⓪ exact-key gate；V-24 L270 mutation 對應 |
| **P2** §V「已知不測」＋OOM／並發覆蓋 | **閉合** | L278「已知不測：**無**」；OOM＝L273 計數 gate＋L224 Task 4.3 receipt（`n_regressions==600`）；並發＝L214 ⑦＋L278 原子寫敘述；與 L273 邊界目錄一致 |

### 2. 條文級矛盾 grep 核對

```text
$ bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md
TEMPLATE PASS (spec): docs/GAP2_MARGINAL_IC_SPEC.md 含全部必填錨點，且無明顯空殼。

$ grep -n 'Task 3\.1 之契約檔\|k≤數十\|四鍵\|reasons 加\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md
(無輸出；rc=1)

$ grep -n 'identity_missing\|write_failed' docs/GAP2_MARGINAL_IC_SPEC.md
178:…computation_failed:identity_missing…
202:…computation_failed:identity_missing…
213:…{status:"computation_failed", reason:"identity_missing", path:null, sha256:null, case_id:…}
213:…{status:"computation_failed", reason:"write_failed:<exc class>", path:null, sha256:null, case_id:…}
214:…三種形狀（ok／identity_missing／寫檔失敗）皆恰五鍵…

$ grep -n '已知不測' docs/GAP2_MARGINAL_IC_SPEC.md
278:…已知不測：**無**——OOM 由計數 gate…並發寫由 Task 4.2 原子寫…

$ grep -n 'gap2_canonical_sha\|n_regressions\|survivor_output' docs/GAP2_MARGINAL_IC_SPEC.md | head -10
63:…metadata.survivor_output_keys…
76:…gap2_canonical_sha…scrub…filtered_features_path…
211:…survivor_output…五鍵恆存在…
213:…五鍵恆存在——R5 CODEX-R5-P0-01…
224:…n_regressions == 200(loo)+200(sequential)+200(removed) = 600…
268-270:V-22/V-23/V-24 mutation 對應
```

**結論**：R5 兩處修訂與 §C／§G／Task 4.1／4.2／4.3／§V 一致；無 R5 殘留矛盾句。

### 3. 可進 TODO？BLOCKING 清單

**可進 TODO**（本家族無 BLOCKING finding）。

**批次獨立性（本輪獨立判定）**：

| 批 | 判定 | 依據 |
|---|---|---|
| B1（1.0→1.3） | 可獨立綠 | Task 1.0 survivor 契約先行；reason 枚舉在 survivor 契約；批內順序 1.0→1.1→1.2→1.3 |
| B2 | 可獨立綠（依 B1） | 僅依 1.1／1.2；bootstrap 搬移為批內先後 |
| B3 | 可獨立綠（依 B1/B2 型別） | Task 3.1 不改 report 契約；validator round-trip 不需 B4 鍵 |
| B4 | 可獨立綠（依 B1–B3） | report 增鍵與 orchestrator 同 commit（L200）；survivor_output 五鍵於 Task 4.2 閉合 |
| B5 | 可獨立綠（依 B4） | 純前端鏡像；§N R4 預設納入 |

---

## Verdict：可派工

R5 P1–P2 修訂均已條文級閉合；六份 reconcile synth 戳記全 PASS；本輪零實質 finding。建議進入 TODO 生成與 B1 派工。

---

ASSUMPTIONS_VERIFIED: 六份 `reconcile_stamps_check.sh` → RC=0；`template_check spec` → PASS；`grep` Task3.1契約檔／reasons增鍵／k≤數十／四鍵 → 0；P1 failure literal 五鍵 grep 命中 L213；P2「已知不測：無」僅 L278 一處  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md`；`bash scripts/reconcile_stamps_check.sh` ×6；`grep -n` 多組；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r6-composer.md --family composer`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 SPEC 審查）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-specadv-r6-composer.md`  
TMP_CLEANUP: 無本輪 `/tmp` workdir（保留 `/tmp/claude-501`）  
STATUS: DONE
