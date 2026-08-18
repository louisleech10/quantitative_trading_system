brief-kind: review

# GAP-2a／2b SPEC adversarial 審查 R5 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R5`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-specadv-r5-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`（R4 N1–N3 修訂版）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| `template_check spec` PASS | fact-verified | **成立** — `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS` |
| 五份 synth `reconcile_stamps_check.sh` 皆 PASS | fact-verified | **成立** — consult-r1／review-r1／r2／r3／r4 各 `RC=0`（三家 APPROVED） |
| SPEC 條文無 survivor_output／canonical_sha／預算 oracle 殘留矛盾 | assumed | **成立** — 機械 grep 見必答 2；R4 codex 四項修訂已寫回 |
| 五批 B1→B5 各批可獨立綠、無 forward dependency | assumed | **成立** — 見必答 3；與 R4 composer 判定一致，本輪獨立複核 N1–N3 未發現新依賴破口 |

---

## COMPOSER-R5-P3-00

**斷言**: 本輪逐項核對 R4 N1–N3（codex 四項 schema／oracle 釘死修訂）均已條文級閉合；條文級 grep 無殘留矛盾；五批批次邊界無新 forward dependency。

**碼證**: **N1** — `docs/GAP2_MARGINAL_IC_SPEC.md:211-214`：`metadata.survivor_output` 五鍵 `{status, reason, path, sha256, case_id}` 恆存在；`status!="ok"` ⇒ `path`／`sha256`=null、`reason` 非 null；`ok` ⇒ 反之；Task 4.2 驗證⓪ 三形狀；§V V-24（`:270`）。**N2** — `:76` `gap2_canonical_sha` 唯一序列化＋有序 scrub（含 `filtered_features_path`）；`:203` Task 4.1 ⑮ `max_removed_candidates`／`n_regressions`；`:224` Task 4.3 k=200／n=20000 bench＋`n_regressions==600`；`:273` OOM 邊界改計數 gate ✓；V-22／V-23（`:268-269`）；`PYTHONPATH=. venv/bin/python /tmp/composer-gap2-specadv-r5/canonical_probe.py` → `sha_equal=False`（現碼 `ichc_run.canonical_sha` 仍隨 path 變，與 SPEC 釘死之 `gap2_canonical_sha` 修法方向一致）。**N3** — `:69` JSON SoT 指 Task 1.0 `ic_survivor_contract.json`；`grep 'Task 3\.1 之契約檔'` → 0。交叉：`grep 'reasons 加\|reasons 增鍵'` → 0；五份 stamp PASS；`PYTHONPATH=. venv/bin/python /tmp/composer-gap2-specadv-r5/budget_probe.py` → `ok_oos`、`ETHUSDT`／`12h`、`case_id=None`、stage5 `14→2`、stage6 `input_features=2 output_features=2`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca

[P3] 信心度=High。R5 為收斂確認輪；本輪對 R4 codex 修訂做獨立複核（非沿用上輪 sentinel），未發現新反例或條文級矛盾。觀察（不升格）：§V 章程子句 `:278`「已知不測：OOM」與 `:273`「OOM 降載 ✓」字面易誤讀，但 Task 4.3 receipt／V-22 已釘死可測邊界，不阻 TODO。

---

## 必答 1–3

### 1. R4 N1–N3 逐條閉合

| 群集 | Verdict | 核對摘要 |
|---|---|---|
| **N1** survivor_output 五鍵 | **閉合** | L211-214 五鍵恆存在＋nullable 規則；identity_missing／寫檔失敗不再省略鍵；Task 4.2 ⓪ 三形狀；V-24 |
| **N2** golden scrub＋預算 oracle | **閉合** | L76 `gap2_canonical_sha` 有序 scrub（含 path 欄）；L203 ⑮ `max_removed_candidates`＋`n_regressions` 語意；L224 bench receipt＋`n_regressions==600`；L273 OOM ✓；V-22／V-23 |
| **N3** §C SoT pointer | **閉合** | L69 改指 Task 1.0 `ic_survivor_contract.json`；舊「Task 3.1 之契約檔」已不存在 |

### 2. 條文級矛盾 grep 核對

```text
$ bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md
TEMPLATE PASS (spec): docs/GAP2_MARGINAL_IC_SPEC.md 含全部必填錨點，且無明顯空殼。

$ grep -n 'Task 3\.1 之契約檔\|k≤數十\|四鍵' docs/GAP2_MARGINAL_IC_SPEC.md
(無輸出；rc=1)

$ grep -n 'reasons 加\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md
(無輸出；rc=1)

$ grep -n 'gap2_canonical_sha\|survivor_output\|n_regressions' docs/GAP2_MARGINAL_IC_SPEC.md | head -12
76:…gap2_canonical_sha…scrub…filtered_features_path…
211:…survivor_output…五鍵恆存在…
214:…驗證⓪ 三種形狀…
224:…n_regressions == 200(loo)+200(sequential)+200(removed) = 600…
268-270:V-22/V-23/V-24 mutation 對應

$ grep -n 'case_id' docs/GAP2_MARGINAL_IC_SPEC.md | head -6
32:…metadata.case_id 為 None…
97:…case_id 與 report_ref 檔名段…
179:⑮ …case_id…
213:…case_id 取 _resolve_case_id…

$ PYTHONPATH=. venv/bin/python /tmp/composer-gap2-specadv-r5/canonical_probe.py
sha_equal=False（path mutation 仍改 sha；實作待 gap2_canonical_sha）
```

**結論**：R4 四項修訂與 §C／§G／Task 4.1／4.2／4.3／§V 一致；無 R4 殘留矛盾句。

### 3. 可進 TODO？BLOCKING 清單

**可進 TODO**（本家族無 BLOCKING finding）。

**批次獨立性（本輪獨立判定）**：

| 批 | 判定 | 依據 |
|---|---|---|
| B1（1.0→1.3） | 可獨立綠 | Task 1.0 survivor 契約先行；reason 枚舉在 survivor 契約；1.2 驗證⑪ 直接讀契約檔 |
| B2 | 可獨立綠（依 B1） | 僅依 1.1／1.2；bootstrap 搬移為批內先後、已列覆蓋風險 |
| B3 | 可獨立綠（依 B1/B2 型別） | Task 3.1 不改 report 契約；validator round-trip 不需 B4 鍵 |
| B4 | 可獨立綠（依 B1–B3） | report 增鍵與 orchestrator 同 commit（L200）；survivor_output 五鍵於 Task 4.2 閉合 |
| B5 | 可獨立綠（依 B4） | 純前端鏡像；§N R4 預設納入 |

---

## Verdict：可派工

R4 N1–N3 修訂均已條文級閉合；五份 reconcile synth 戳記全 PASS；本輪零實質 finding。建議進入 TODO 生成與 B1 派工。

---

ASSUMPTIONS_VERIFIED: 五份 `reconcile_stamps_check.sh` → RC=0；`template_check spec` → PASS；`grep` Task3.1契約檔／reasons增鍵／k≤數十 → 0；`PYTHONPATH=. venv/bin/python /tmp/composer-gap2-specadv-r5/budget_probe.py` → ok_oos／ETHUSDT／12h／case_id=None／14→2／stage6 2→2；`canonical_probe` → sha_equal=False  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md`；`bash scripts/reconcile_stamps_check.sh` ×5；`grep -n` 多組；`PYTHONPATH=. venv/bin/python /tmp/composer-gap2-specadv-r5/{budget_probe,canonical_probe}.py`；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r5-composer.md --family composer`  
FAILURES_SEEN: budget_probe 初版 `run_analyze` unpack 錯誤（已修）  
SCOPE_CHANGES: none（唯讀 SPEC 審查）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-specadv-r5-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap2-specadv-r5`（保留 `/tmp/claude-501`）  
STATUS: DONE
