# TEMPLATE_GATE_FIX SPEC — Adversarial Review（Composer 2.5）

審查對象：`docs/TEMPLATE_GATE_FIX_SPEC.md`
PLAN：`handoffs/2026-07-04-template-review-RECONCILE.md`
TODO：N/A（尚未生成）
焦點：完整審查 + §A 可核實斷言實跑驗證

---

## Verdict：需修補後派工

方向與 reconcile 定案高度對齊（U1–U3、U9、U11、Q3/Q4、探針矩陣思路正確），§G 行為 golden 設計可證偽。但存在 **§A 事實錯誤**、**Task 2.2 否定句演算法未定義清楚且實測有誤擋面**、**Task 2.1 觸發範圍不足以覆蓋現役 IC_PHASE0 同款繞過**、**Task 6.2 驗收與邊界自相矛盾**、**RESULT 探針未入矩陣** 等問題；修補前派實作高機率留下新縫隙或假綠驗收。

---

## Findings

### 挑戰前提（§0 優先）

**ID:ADV-P1 [BLOCKING] 信心度:High** — §A「舊錨點共 6 處／§1.4×3、§1.0×3」與 grep 實測不符，屬未驗證卻寫成 FACT-RECEIPT 的「已驗證事實」。
證據：`docs/TEMPLATE_GATE_FIX_SPEC.md` §A 第 12 行。
會怎麼失敗：Task 6.2 驗收以「合計 = 0」為準，但實際殘留 7 行；執行端以錯誤清單收工 → 漏改 1 處 → 治理文件繼續漂移。
修法：更正為「7 處（gate.sh×2 §1.4、CLAUDE×1 §1.0、MULTI×4：§1.4×2、§1.0×2）」；Task 6.2 驗收改 `grep -c` 逐檔列表或附完整行號清單。
VERIFY:
```text
$ grep -n "§1.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md
CLAUDE.md:41:...§1.0...
scripts/gate.sh:9:...§1.4...
scripts/gate.sh:254:...§1.4...
docs/MULTI_AGENT_ORCHESTRATION.md:69:...§1.4...
docs/MULTI_AGENT_ORCHESTRATION.md:101:...§1.4...
docs/MULTI_AGENT_ORCHESTRATION.md:212:...§1.0...
docs/MULTI_AGENT_ORCHESTRATION.md:308:...§1.0...
（7 行；§1.4=4、§1.0=3，非 SPEC 宣稱的 6 處／3+3）
```
RECHECK: `grep -n "§1.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md | wc -l`（應與 SPEC 修正後數字一致）

---

**ID:ADV-P2 [MAJOR] 信心度:High** — §A 宣稱三繞過探針「均 exit 0」已重現，但 **spec_verified_bypass 繞過機制是「已驗證事實段內無 `已確認` 字面」**，非單純 hollow；SPEC Task 2.1 若只加行級 `已驗證` 仍漏 **段標題下子彈行**（現役 IC_PHASE0 同款）。
證據：§A FACT-RECEIPT #3；Task 2.1 改法「含已確認或已驗證」；`docs/IC_PHASE0_SPEC.md` L15–17（`### 已驗證事實` 下 bullet 含 DatetimeIndex/int64 但行內無「已驗證」）。
會怎麼失敗：修完 U1 後 IC_PHASE0 級 SPEC 仍 PASS（`template_check.sh spec docs/IC_PHASE0_SPEC.md` 現仍 exit 0）→ 第三次事故模式存活。
修法：Task 2.1 明訂觸發域 = **整個 §A awk 區塊**（含 `### 已驗證事實` 標題至下一 `###`），凡區塊內含資料結構詞的行均須鄰行 `FACT-RECEIPT:`；驗收加 `docs/IC_PHASE0_SPEC.md` 在 grandfather 政策外的「修後新檔探針」或專用 `spec_ic_phase0_style.md` fixture。
VERIFY:
```text
$ bash scripts/template_check.sh spec /tmp/spec_verified_bypass.md; echo exit=$?
TEMPLATE PASS (spec): /tmp/spec_verified_bypass.md ...
exit=0

$ bash scripts/template_check.sh spec docs/IC_PHASE0_SPEC.md; echo exit=$?
TEMPLATE PASS (spec): docs/IC_PHASE0_SPEC.md ...
exit=0

$ bash scripts/template_check.sh spec /tmp/spec_highrisk_no_g.md; echo todo=$?
TEMPLATE PASS ... exit=0

$ bash scripts/template_check.sh todo /tmp/todo_bad.md; echo exit=$?
TEMPLATE PASS ... exit=0

$ bash scripts/template_check.sh spec /tmp/spec_pending_unresolved.md; echo exit=$?
TEMPLATE FAIL ... exit=1
```
RECHECK: 重建四探針後 `bash scripts/test_template_check.sh --freeze`（Phase 1 完成後）

---

**ID:ADV-P3 [BLOCKING] 信心度:High** — Task 2.2「否定句不誤判」邊界與 Task 6.2 驗收 **互斥**：邊界要求歷史行保留字面 `§1.0`，驗收卻要求全庫 grep 合計 0。
證據：Task 6.2 驗收 `grep -c ... 合計 = 0`；邊界「MULTI…212/308…改為（V12 舊稱 §1.0，今 §V）註記」。
會怎麼失敗：執行端照邊界加註 → 驗收永遠紅；或為過驗收刪歷史語境 → 與 reconcile U11 意圖衝突。
修法：二選一寫死——(a) 歷史行改寫為不含 `§1.0`/`§1.4` 字面（如「舊稱可測性章，今 §V」）且驗收 = 0；或 (b) 驗收改 `grep` 排除 `docs/MULTI_AGENT_ORCHESTRATION.md` 指定行／或只掃「規範性」章節。
VERIFY:
```text
$ echo '歷史紀錄（V12 舊稱 §1.0，今 §V）' | grep -c "§1\.0\|§1\.4"
1
```
RECHECK: `grep -rn "§1\.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md`

---

**ID:ADV-P4 [BLOCKING] 信心度:High** — Task 2.2 §RISK→§G 聯動的否定排除 **未定義可實作語義**；naive `不命中|未命中` 仍會誤擋常見寫法。
證據：Task 2.2 改法「偵測 (a)/(d)…排除不命中前綴」；邊界僅舉「不命中(a)」一例。
會怎麼失敗：實測「參見 (a) 原則」「| (a) | 否 |」「可能命中 (d) 若改動 ML」均 `hit=1` → 低風險文檔誤強制 §G 或誤擋；執行端無規格可寫 awk。
修法：在 SPEC 附 **偽碼級規則**（建議）：僅當行匹配 `命中.*\(a\)|命中.*\(d\)|\(a\).*數值|\(d\).*ML` 等正向模式，且行首 20 字內無 `不命中|未命中|非命中`；表格列「否」不算命中。Phase 1 增 `spec_risk_false_positive.md` 正樣本入 EXPECTED=0。
VERIFY:
```text
$ # naive 原型（SPEC 未給正式規則）
$ printf '%s\n' '- 參見 (a) 原則' '| (a) | 否 |' '- 命中 (d) ML' | while read l; do
    if echo "$l"|grep -qE '\(a\)|\(d\)|ML|數值|回測' && ! echo "$l"|grep -qE '不命中|未命中|非命中|不碰'; then echo HIT:$l; else echo SKIP:$l; fi
  done
HIT:- 參見 (a) 原則
HIT:| (a) | 否 |
HIT:- 命中 (d) ML
```
RECHECK: Phase 2 後對 false-positive fixture 跑 `bash scripts/test_template_check.sh`

---

**ID:ADV-P5 [MAJOR] 信心度:High** — §G 探針矩陣 **缺 RESULT 分支 fixture**，A-5 無 F-1 對應項，oracle 不可單靠 exit 矩陣證偽 RESULT 修補。   〔REF:handoffs/2026-07-04-TGF-SPEC-ADV-RECONCILE.md〕 〔SUPERSEDED:早期紅燈紀錄已由 TGF epic 修復+stamped reconcile 取代〕
證據：Manifest F-1 僅列 spec/todo 四探針；Task 2.4 驗收「構造 result fixture」但未列入 Phase 1.1 檔名清單／EXPECTED.txt；`template_check.sh result templates/RESULT_TEMPLATE.md` 現 exit 0（RECEIPTS=[] 仍過）。
會怎麼失敗：Task 2.4 實作後無持久回歸 → RUNTIME PASS+空 RECEIPTS 洞復發無人知。
修法：Phase 1 增 `tests/gate_fixtures/result_pass_empty_receipts.md`、`result_notrun_done_in_discussion.md`（PASS）、`result_notrun_done_operational.md`（FAIL）；`test_template_check.sh` 支援 `result` kind。
VERIFY:
```text
$ bash scripts/template_check.sh result templates/RESULT_TEMPLATE.md; echo exit=$?
TEMPLATE PASS (result): templates/RESULT_TEMPLATE.md ...
exit=0
```
RECHECK: `bash scripts/test_template_check.sh` 含 result 列後 diff EXPECTED

---

**ID:ADV-P6 [MAJOR] 信心度:Medium** — Mutation oracle **僅綁 Task 2.1**，§V 宣稱「機檢擋探針」但 2.2/2.3/2.4 無對等 mutation 步驟 → 單點改壞可假綠。
證據：§V「mutation=Task 2.1 附加步驟」；Task 2.2/2.3 驗收無「改壞一字元須轉紅」。
會怎麼失敗：§RISK 聯動或 per-Task awk 被改壞，矩陣仍綠（若只測 2.1 探針）。
修法：§V 要求每個 A-* 規則至少一條 mutation case 寫入 `tests/gate_fixtures/MUTATION.txt` 或 test_template_check.sh `--mutate`。
RECHECK: 故意破壞 template_check.sh 中 §G 段後 `bash scripts/test_template_check.sh; echo $?` 應非 0

---

**ID:ADV-P7 [MAJOR] 信心度:High** — Task 6.1 gate 輕檢 **未指定 reconcile 檔路徑契約**，與現行 `gate.sh` 參數不閉合。
證據：Task 6.1「reconcile 檔（--adversarial 同目錄或指定）」；`gate.sh` L190–226 僅 `--adversarial` 單一路徑，無 `--reconcile`。
會怎麼失敗：實作者不知 grep 哪份 reconcile；或 adversarial 與 reconcile 分檔時 D-1 永不觸發。
修法：增 `gate.sh --reconcile <path>` 或規定 adversarial 檔內嵌 `RECONCILE_REF:`；驗收三 fixture 寫死路徑。
RECHECK: `bash scripts/gate.sh dispatch --help` 或讀 gate.sh 參數段

---

**ID:ADV-P8 [MAJOR] 信心度:Medium** — Phase 4 Task 4.1 與 Phase 5 Task 5.2 **同檔雙向改** `SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`，無合併順序／衝突解決規則。
證據：Task 5.2「與 Task 4.1 同檔，後執行合併 diff」；§P 寫 Phase 5「與 Phase 3/4 無互依」但 5.2 依賴 4.1 同檔。
會怎麼失敗：並行派工或 revert 單 Phase 時 prompt 缺 §2 解耦查或缺 ID/RECHECK。
修法：合併為單 Task「C+E prompt 更新」或 Phase 5 明訂「必在 Phase 4 commit 之上 cherry-pick」。
RECHECK: `git log -1 -- templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 單 commit 含 C-1..C-5 與 E-3

---

**ID:ADV-P9 [MINOR] 信心度:High** — reconcile U11 與 Codex C2（已確認結果標籤繞過）在 SPEC 有 Task 2.1 A-2，但 **未要求 grandfather 現役 IC_PHASE0 的「已確認結果」空殼行**。
證據：IC_PHASE0 L26–28「已確認結果」無日期+來源結構；Task 2.1 邊界未列 grandfather。
會怎麼失敗：新機檢誤擋現役 epic SPEC（F-3 盤點有提但 Task 2.1 驗收未列正樣本含鬆散已確認結果）。
修法：spec_good_full 明確含鬆散/嚴格兩種 §A 樣式 + GRANDFATHER 政策交叉引用。
RECHECK: `bash scripts/template_check.sh spec docs/IC_PHASE0_SPEC.md` 修後 vs GRANDFATHER 清單

---

**ID:ADV-P10 [MINOR] 信心度:Medium** — Task 5.1 驗收「無條件讀不含 ARCHITECTURE」靠 **人工 diff**，不可機械驗收。
證據：Task 5.1 驗證第三條。
會怎麼失敗：執行端留「無條件讀 ARCHITECTURE」變體句 → adversarial 漏掃 → token 黑洞未消除。
修法：增 `grep -n "無條件讀" templates/TODO_GENERATION_PROMPT.md` 白名單斷言（僅 AGENTS.md、CLAUDE 三節）。
RECHECK: `grep -n "無條件讀" templates/TODO_GENERATION_PROMPT.md`

---

**ID:ADV-P11 [MINOR] 信心度:Low** — reconcile 降級的 C-6（ASSUMPTIONS↔RESULT 映射）**未入 manifest/SPEC**，與「不可砍 RESULT 枚舉」並存但雙軌未閉合。
證據：RECONCILE「Composer C-6…修法收窄為映射一行+sync」；SPEC 僅 A-5 RESULT 機檢，無 ASSUMPTIONS 映射。
會怎麼失敗：執行端仍只寫 ASSUMPTIONS 塊過合約 sync，RESULT 機檢不跑 → 與 reconcile 精神漂移（非主線阻擋）。
修法：Task 6.x 或 §N 登記二期；或 RESULT_TEMPLATE 頭部一行映射表。
RECHECK: `grep -r "ASSUMPTIONS_VERIFIED" AGENTS.md templates/RESULT_TEMPLATE.md`

---

### §1 必查十類（摘要）

| 類別 | 結論 |
|------|------|
| 1 矛盾/互斥 | **有** — ADV-P3（6.2 驗收 vs 邊界）、ADV-P8（Phase 4/5 同檔） |
| 2 漏項/端到端 | **有** — ADV-P5（RESULT fixture）、ADV-P7（reconcile 路徑）、TODO 未生成 |
| 3 不可測驗收 | **有** — ADV-P6（mutation 單點）、ADV-P10（人工 diff） |
| 4 可疑 quant 假設 | **無** — 本 epic 不碰數值路徑；§G 行為 golden 恰當 |
| 5 過度工程 | **無** — 分 phase revert 合理 |
| 6 OOM/並行 | **無** |
| 7 Cache 正確性 | **無** |
| 8 API/型別/相容 | **有（輕）** — grandfather 政策已述；ADV-P9 |
| 9 測試品質 | **有** — ADV-P2/P5/P6 oracle 缺口 |
| 10 Agent 可執行性 | **有** — ADV-P4 Task 2.2 awk 缺偽碼；ADV-P2 觸發域模糊 |

### §2 範本錨點 + 獵空殼

- **錨點**：§RISK/§A/§C/§G/§P/§V/§R/§N 齊全；§G 為行為 golden（exit 矩陣）非口號，含 `diff … exit 0` 可證偽條件。**通過**。
- **獵空殼**：§P 各 Task 含檔案、改法、驗證命令、邊界、不可做 — **非空殼**。Task 2.2 改法仍偏標籤級（見 ADV-P4）。
- **coverage_check**：28/28 ID presence PASS（**僅字串存在**，語義深度靠本 review）。

### §3 不可違反原則

- SPEC §C 明訂「只加強機檢、不得放寬」；§V 禁回填 EXPECTED。**無違反**。

### Reconcile 忠實度（專項）

| Reconcile 項 | SPEC 覆蓋 | 備註 |
|--------------|-----------|------|
| U1 BLOCKING | Task 2.1 [A-1][A-2] | 觸發域不足 → ADV-P2 |
| U2 BLOCKING | Task 2.2 [A-3] | 否定句/誤擋 → ADV-P4 |
| U3 MAJOR | Task 2.3 [A-4] | 對齊 |
| CL-2 / C-1 | Task 4.1 | 對齊 |
| U9 / D-1 D-2 | Task 6.1 | reconcile 路徑未閉合 → ADV-P7 |
| U11 | Task 6.2 | 計數錯誤 + 驗收矛盾 → ADV-P1/P3 |
| RESULT MAJOR | Task 2.4 [A-5] | 無 F-1 fixture → ADV-P5 |
| Q3 §V charter | Task 3.2 [B-4] | 對齊 |
| Q4 憲法瘦身 | Phase 5 | 對齊；驗收偏弱 → ADV-P10 |
| 三方 kline §G | Task 3.2 [B-3] | 對齊 |
| U13 regex | Task 2.4 [A-6] | 實測擬議 regex 可 MATCH「待使用者確認：本任務無」 |
| C-6 收窄 | **未覆蓋** | ADV-P11 |

---

## 被當成事實的未驗證假設（§0）

1. **「舊錨點 6 處」** — 實為 7 處（ADV-P1，已 VERIFY）。
2. **「Task 2.2 否定句排除可行」** — 僅一則邊界例 + 未定義 awk；實測多種誤擋（ADV-P4，已 VERIFY）。
3. **「Task 2.1 加行級已驗證即可堵 U1」** — IC_PHASE0 反證：段標題下 bullet 無「已驗證」字面仍繞過（ADV-P2，已 VERIFY）。
4. **「Phase 1 探針可依 composer handoff 重建」** — 合理但 **repo 內尚無 `tests/gate_fixtures/`**（`Glob` 0 files）；屬計劃假設，Phase 1 前非 fact。
5. **「本 SPEC 自身修後仍 exit 0」** — Task 2.2 自驗宣稱合理（§RISK 含「不命中 (a)/(d)」）；現行已 PASS：`bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md` → exit 0。

---

## §A 其餘 FACT-RECEIPT 覆核

| 宣稱 | 判定 | VERIFY 摘要 |
|------|------|-------------|
| regex 誤擋「待使用者確認：本任務無」 | **fact** | `grep -qE ...` → NO MATCH |
| 三繞過探針 exit 0 | **fact** | bypass/highrisk/todo_bad=0；pending=1（見 ADV-P2） |
| copilot 分叉 | **fact** | `TODO_GENERATION_PROMPT.md` L23 仍 `copilot-instructions`；`ls` 四檔存在 |
| 四檔存在 | **fact** | `ls` 四路徑均存在 |

---

HANDOFF_NOT_UPDATED: read-only adversarial review；根 HANDOFF 由 Claude 維護。

STATUS: DONE
