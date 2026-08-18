brief-kind: review

# GAP-2a／2b SPEC adversarial 審查 R4 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R4`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-specadv-r4-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`（R3 M1／M2 修訂版）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| `template_check spec` PASS | fact-verified | **成立** — `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS` |
| 四份 synth `reconcile_stamps_check.sh` 皆 PASS | fact-verified | **成立** — consult-r1／review-r1／r2／r3 各 `RC=0`（三家 APPROVED） |
| §G／§C／Task 條文無 reasons／身分三欄矛盾 | assumed | **成立** — 機械 grep 見必答 2；M1／M2 修訂已寫回 |
| 五批 B1→B5 各批可獨立綠、無 forward dependency | assumed | **成立** — 見必答 3；reason SoT 已住 Task 1.0 survivor 契約，report 增鍵僅 Task 4.1 同 commit |
| R3 P1-01／P2-01 已閉合 | assumed | **成立** — §G-4 L97 與 Task 3.1 ⑮ 同規則；§C L63／L69／L107 與 Task 4.1「不加 reasons」一致 |

---

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對 R2 L1–L5 與 R3 M1／M2 閉合後無實質 finding；條文級 grep 無殘留矛盾；五批批次邊界無新 forward dependency。

**碼證**: M1：`docs/GAP2_MARGINAL_IC_SPEC.md:97`（`symbol`／`timeframe`↔metadata；`case_id`↔`report_ref` 檔名段、不比 metadata）對齊 `:179` ⑮／`:213`；`venv/bin/python /tmp/composer-gap2-specadv-r4/budget_probe.py` → `metadata.case_id=None`、`symbol=ETHUSDT`、`timeframe=12h`。M2：`grep -n 'reasons 加\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md` → 0；`:63`／`:107`／`:200` 皆「只加 marginal_ic 節＋survivor_output_keys；不加 reasons」。L1–L5：O1 raw 刪除（`:87-88`）、σ 表述（`:78-86`）、reason 住 survivor（`:106`）、event_identity cache（`:178,202`）、預算 gate 200（`:130,200`）、V-19 三欄（`:265`）。前置：`bash scripts/reconcile_stamps_check.sh` 四份 synth 皆 PASS；`bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e

[P3] 信心度=High。R4 為收斂確認輪；R3 兩處 MAJOR 文檔漂移已修復，本輪未發現新反例或條文級矛盾。不受理範圍（2a/2b 拆分、橋 blocked、已裁定取捨）未重開。

---

## 必答 1–3

### 1. R2 L1–L5、R3 M1–M2 逐條閉合

| 群集 | Verdict | 核對摘要 |
|---|---|---|
| **L1** O1 raw＋σ | **閉合** | L87-88 刪 raw `>0.10`、O1a 承擔防 raw；噪聲全改 σ（L78-86）；V-2 對映 O1a（L247） |
| **L2** reasons SoT | **閉合（M2）** | L106 reasons 唯一住 `ic_survivor_contract.json`；L63／L69／L107／L200 一致「report 不加 reasons」；Task 1.2 L130 指 Task 1.0 契約 |
| **L3** 身分三欄 | **閉合（M1）** | §G-4 L97＝Task 3.1 ⑮ L179：`symbol`／`timeframe`↔metadata（缺欄 raise）；`case_id`↔檔名段；FACT-RECEIPT L32 與 budget probe 同值 |
| **L4** event_identity | **閉合** | L178 pop 前存 `_ic_cache["event_identity"]`；L202 stage3 規格；契約 `event_identity_keys`＋_doc（L106）；驗證⑱ L179 |
| **L5** 預算 gate | **閉合** | L130／L200 預設 200、`not_computed:candidate_budget_exceeded`；V-19 三欄 L265；V-13 反向 OOS L258 |
| **M1** §G-4 case_id | **閉合** | R3 P1-01 舊文案（三者皆比 metadata）已不存在；L97 已拆分對照來源 |
| **M2** §C reasons | **閉合** | R3 P2-01 舊「reasons 增鍵」已不存在；`grep 'reasons 加\|reasons 增鍵'` → 0 |

### 2. 條文級矛盾 grep 核對

```text
$ bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md
TEMPLATE PASS (spec): docs/GAP2_MARGINAL_IC_SPEC.md 含全部必填錨點，且無明顯空殼。

$ grep -n 'reasons 加\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md
(無輸出；rc=1)

$ grep -n 'case_id' docs/GAP2_MARGINAL_IC_SPEC.md | head -8
32:…metadata.case_id 為 None（故 case_id 對照走 report_ref 檔名）
97:…case_id 與 report_ref 檔名段 ic_report_{case_id}.json 相等（不比 report metadata）
179:⑮ …case_id 與 report_ref 檔名段…相等（不改 report metadata）
213:…case_id 取 _resolve_case_id(metadata)（與 ic_report_{case_id}.json 檔名一致）

$ grep -n 'event_identity' docs/GAP2_MARGINAL_IC_SPEC.md
106:…event_identity_keys＋_doc…
178:…_ic_cache["event_identity"]…
179:⑱ event_identity 序列化規格…
202:…event_identity 存 _ic_cache…

$ grep -n '不加 reasons' docs/GAP2_MARGINAL_IC_SPEC.md
63:…不加 reasons…
107:…不加 reasons…
200:…不加 reasons…
```

**結論**：reasons／case_id／event_identity 敘述跨 §C／§G-4／Task 1.0／3.1／4.1／4.2 一致，無 R3 殘留矛盾。

### 3. 可進 TODO？BLOCKING 清單

**可進 TODO**（本家族無 BLOCKING finding）。

**批次獨立性（brief assumed，本輪獨立判定）**：

| 批 | 判定 | 依據 |
|---|---|---|
| B1（1.0→1.3） | 可獨立綠 | Task 1.0 不動 `ic_report_contract.json`；reason 枚舉在 survivor 契約；1.2 驗證⑪ 直接讀契約檔 |
| B2 | 可獨立綠（依 B1） | 僅依 1.1／1.2；bootstrap 搬移為批內先後、已列覆蓋風險 |
| B3 | 可獨立綠（依 B1/B2 型別） | Task 3.1 明確不改 report 契約；validator round-trip 不需 B4 鍵 |
| B4 | 可獨立綠（依 B1–B3） | report 增鍵與 orchestrator 同 commit（L200），消除舊 `reasons_ref` forward dependency |
| B5 | 可獨立綠（依 B4） | 純前端鏡像；§N R4 預設納入 |

預算探針：`venv/bin/python /tmp/composer-gap2-specadv-r4/budget_probe.py` → stage5 `input=14 output=2`、stage6 `input=2 output=2 removed=[]` ≪ `max_survivors_for_loo=200`。

---

## Verdict：可派工

R2 五群集與 R3 M1／M2 修訂均已條文級閉合；四份 reconcile synth 戳記全 PASS；本輪零實質 finding。建議進入 TODO 生成與 B1 派工。

---

ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS；四份 `reconcile_stamps_check.sh` → RC=0；`grep 'reasons 加\|reasons 增鍵'` → 0；`venv/bin/python /tmp/composer-gap2-specadv-r4/budget_probe.py` → survivors=2、case_id=None、ETHUSDT/12h  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md`；`bash scripts/reconcile_stamps_check.sh` ×4；`grep -n` reasons/case_id/event_identity；`venv/bin/python /tmp/composer-gap2-specadv-r4/budget_probe.py`；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r4-composer.md --family composer`  
FAILURES_SEEN: budget_probe 初版 unpack 錯誤（已修）  
SCOPE_CHANGES: none（唯讀 SPEC 審查）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-specadv-r4-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap2-specadv-r4`（保留 `/tmp/claude-501`）  
STATUS: DONE
