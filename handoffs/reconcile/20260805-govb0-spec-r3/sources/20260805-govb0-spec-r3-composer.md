# GOVB0-SPEC-R3 — Composer Adversarial Review (R3)

**審查標的**：`docs/GOVB0_FRICTION_SPEC.md`（R3 版）  
**家族**：COMPOSER | **輪次**：R3 | **task-id**：GOVB0-SPEC-R3  
**日期**：2026-08-05

---

## 被當成事實的未驗證假設（§0）

| 標籤 | brief／SPEC 陳述 | 裁定 |
|---|---|---|
| **assumed→未成立** | E-1～E-13 全部已在 R3 落實且無新矛盾 | **未全成立**：E-7（Task 0.1 驗收仍寫全 JSON diff）、E-10（定稿門檻未採 codex ≥50／≥3 session，且缺「不得宣稱完工」）未閉合。其餘 E 群文本層大致到位。 |
| **assumed→部分成立** | Task 2.0 10 項契約＋1b 跨行剝引號涵蓋所有詞法情境 | **契約面擴充到位**（10 項＋1b 明文）；**實作錨點仍偏原型③**（僅涵蓋第 2、3 項），1b 未在 Task 2.1 驗收列具名語料（見 P1-02）。heredoc／`$'…'`／續行 `\` 等屬理論邊界 → P2，不阻擋本批。 |
| **assumed→可接受** | 序列化拒絕（E-6）不會誤拒正常重派 | **逾時後同 `<out>` 重派**的 attempt 生命週期未寫清（見 P1-03）；並發第二 attempt 拒絕本身合理。 |
| **fact-verified** | R3 = 4 Phase／11 Task；`template_check.sh spec` rc=0；Task 數 == §V | **複核通過**：`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0；`grep -c '^\*\*Task '` → 11；§V `:364` 宣稱 11。 |
| **fact-verified** | 原型③ 26/26；b15probe6 awk 跨行 4/4 | **複核通過**：`bash handoffs/govb0_probes/b15probe5.sh` rc=0（26 條全對）；`bash handoffs/govb0_probes/b15probe6.sh` rc=0（TN 2＋TP 2 全對）。 |

---

## §1 必查摘要

| # | 類別 | 結果 |
|---|---|---|
| 1 | 矛盾/互斥 | **有** — Task 0.1 不變式（僅 `(rc,kind)`）vs 驗收「兩份 JSON diff 為空」（P0-01）；Task 3.3 定稿門檻與 R2 收斂 E-10 裁決不一致（P1-01）。 |
| 2 | 漏項/端到端 | **有（輕）** — 1b 跨行剝引號未在 Task 2.1 列 b15probe6 語料（P1-02）；逾時失敗後重派路徑（P1-03）。 |
| 3 | 不可測驗收 | **有** — E-10 定稿門檻漂移使「與 manifest 一致」仍不可執行至 codex 裁決水準（P1-01）。 |
| 4–8 | quant／OOM／Cache／API | **無** |
| 9 | 測試品質 | **有（輕）** — Task 0.1 若照現行驗收寫測試會假紅或假紅（P0-01）。 |
| 10 | Agent 可執行性 | **有** — 見 P0-01／P1-01。 |
| 11 | 必要性/短命工 | **無** |

## §2 範本錨點 + 獵空殼

- §RISK／§A／§C／§P／§V／§R／§N：**齊**；§G N/A 合理；§N 含 R3 不受理範圍表。
- §A FACT-RECEIPT：9 條齊；OPEN 項條件已寫。
- 獵空殼：**未發現表頭-only**；各 Task 驗證欄有 ASSERT／狀態斷言 token。

---

## Q1 — 本家族 R2 每一條 finding 關閉判定

| Finding ID | Verdict | 重跑反例與結果 |
|---|---|---|
| `COMPOSER-R2-P0-01` | **CLOSED** | `bash handoffs/govb0_probes/b15probe4.sh` → 現行 gate 對 `eval`／`$()`／反引號／子 shell 皆 ALLOW（want=BLOCK）；R3 Task 2.0 第 2–3 項＋Task 2.1 列五條 **ALLOW→BLOCK** 狀態斷言；`b15probe5.sh` 原型③ 26/26。 |
| `COMPOSER-R2-P1-01` | **CLOSED** | R3 `:179-181` 明文「禁止照抄原型」、列第 4／5／7／8／9／10 項**未在原型③實作**；Task 2.0 驗收要求 ≥20 條語料＋10 mutation。 |
| `COMPOSER-R2-P1-02` | **CLOSED** | Task 2.0 契約第 10 項 heredoc＋引號外分號；邊界已納入契約與 ≥20 語料要求。 |
| `COMPOSER-R2-P1-03` | **CLOSED（OUT-OF-SCOPE）** | R3 §N `:403-404` 將 `B-34` 劃入不受理並具名 `票 B-34`；權宜作法已標註。 |
| `COMPOSER-R2-P1-04` | **NOT-CLOSED** | R3 Task 3.3 `:344-347` 僅寫定稿 **≥20 筆**、**<10 筆 PROVISIONAL**；R2 收斂 E-10 已裁「定稿採 codex **≥50 筆＋≥3 session/UTC 日**、≥20 僅 sanity check」且主委裁決「機制上線暫定值但 Task 3.3 **不得宣稱完工**」——**均未寫入 Task 3.3**（見 P1-01）。 |
| `COMPOSER-R2-P2-01` | **CLOSED** | §V `:367-372` 改為「rc 僅輔助護欄、須並列狀態斷言」；Task 1.1 unknown 補四項無副作用斷言（`:142-144`）。 |
| `COMPOSER-R2-P2-02` | **CLOSED（OUT-OF-SCOPE）** | §N `:405` 強制 TODO §0 標「`B-24` 部分完成」；機械面列不受理。 |

---

## Q2 — R3 新矛盾

**① Task 2.0 契約 vs Task 2.1–2.4**  
**無硬矛盾**；Task 2.1–2.4 均引用 Task 2.0。殘留：**1b 跨行剝引號**在契約與 b15probe6 已驗證，但 Task 2.1 驗收未列具名語料（P1-02）。

**② 兩 baseline 分離**  
**文本層已分離**（語料 A／B、各自 snapshot，`:106-109`）。**殘留矛盾**在 Task 0.1 驗收仍要求全 JSON diff 為空（`:117`），與「audit 欄位增加不在不變式內」（`:104-105`）互斥 → P0-01。

**③ 序列化拒絕 vs Task 3.3 逾時重派**  
並發第二 attempt 拒絕（`:320-324`）與 timeout 區間（Task 3.3 `:339`）**無直接衝突**。逾時後 `failed`、attempt 檔殘留（`:352-353`）時，**同 `<out>` 再派**是否仍視為「進行中 attempt」未寫 → P1-03。

---

## Q3 — 跨行剝引號設計裁定

**① 設計正確** — `b15probe6.sh` 實跑：commit 多行訊息（TN）awk 跨行剝=ALLOW、真多行指令（TP）=BLOCK；「正規化為單行」已被 SPEC `:167-168` 明文否決，與實測一致。

**② 熱路徑實作** — `gate_check.sh` 禁 subprocess；`awk` 單次掃描跨行剝引號在 POSIX 環境可接受（b15probe6 已驗邏輯）。純 shell 逐字元狀態機可行但更易錯、維護成本高；**建議 awk 或等價單進程掃描**，勿 `sed` 行內替換。

**③ 仍可能漏網（P2，不阻擋本批）** — 續行反斜線 `\`、ANSI-C `$'…'`、heredoc 引號變體、巢狀 heredoc；屬「理論可能、repo 內少實例」，契約第 10 項已列 heredoc 組合，實作須補測試即可。

---

## Q4 — E-10 未達門檻時主委取捨

**接受**。理由與 brief 一致：`B-14` 根因是無 timeout 空等 2h20m；「暫定 timeout 上線＋標 PROVISIONAL、Task 3.3 不宣稱完工」嚴格優於無 timeout。  
**但** R3 Task 3.3 **尚未寫入**「不得宣稱完工／`票 B-14` 未定稿」與 codex 定稿門檻 → 屬 P1-01 文本缺口，非否定取捨本身。

---

## Q5 — `票 B-36`（群集表盲點）

① **嚴重度：MAJOR**（治理收斂工具缺陷，非本批 SPEC 內容錯誤）。  
② **歸屬**：宜**併入 `票 B-13`**（搬遷／收斂填表漏填不會被擋）或獨立 `票 B-36` 子項；與 `B-34` 不同（那是角色語意）。  
③ **修法**：同意主委傾向**產出端**——`reconcile_build.sh` 生成群集骨架時**預列全部來源 finding ID**，只准填處置不准刪列；檢查端可加「群集段須覆蓋 union ID」但無法單靠 `completeness --lock`（附錄 byte-faithful 使 ID 必然存在）。

---

## Q6 — §V 驗收可證偽性

| 檢查 | 結果 |
|---|---|
| `ASSERT … rc` 無對應狀態斷言 | **Task 0.1／1.1／3.3** 均有並列狀態斷言；**Task 2.5** 的 `rc≠0`（`:272`）綁定「非預期附加項」狀態斷言，符合 §V `:371-372`。 |
| mutation 恆真 | **未發現**；各 Task 列 revert→轉紅。 |
| 假綠風險 | **Task 0.1** 若實作者照 `:117` 做全 JSON diff，Phase 0 新增 audit 欄位會**永遠 FAIL** 或被迫偷刪欄位比對 → 證偽性損壞（P0-01）。 |

---

## Q7 — 可否進 TODO 生成？

**需修補後派工**。

| # | BLOCKING | 修法方向 | 不受理範圍？ |
|---|---|---|---|
| B1 | **是** | Task 0.1 驗收改為僅 diff **decision trace**（`(rc,kind)` 序列或專用 JSON），與 `:104-105` 一致；刪「兩份完整 JSON diff 為空」 | 否 |
| B2 | **是** | Task 3.3 補齊 E-10：定稿 **≥50 筆＋≥3 session/UTC 日**（codex 較嚴者）、≥20 標 sanity check、暫定值上線但 **Task 3.3 不得宣稱完工**、`票 B-14` 未定稿直至達標 | 否 |
| B3 | **否（MAJOR）** | Task 2.1 驗收列 `b15probe6` 四條（commit 多行 TN×2、真多行 TP×2） | 否 |
| B4 | **否（MAJOR）** | 明文逾時 `failed` 後釋放 attempt 鎖／允許同 `<out>` 重派 | 否 |
| B5 | **否（OUT-OF-SCOPE 記錄）** | `票 B-36`／併入 `B-13`；`B-34`／`B-24` 機械面／截斷 oracle／FP-2 | 是 |

---

## Verdict：需修補後派工

---

## COMPOSER-R3-P0-01

**斷言**: Task 0.1 將不變式收窄為 `(rc, kind)` 序列相等，但驗收仍要求「兩份 JSON diff 為空」，與「audit 新增欄位不在不變式內」**互斥**，實作者無法同時滿足。

**碼證**: `:104-105` 不變式僅 `(rc,kind)`；`:117`「逐項比對輸出兩份 JSON 並 diff 為空」。Phase 0 必增 `gate_deny` 欄位 ⇒ 完整 JSON diff 不可能為空。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[BLOCKING] 信心度=High。E-7 文本修訂未閉合驗收句。修法：分離 decision trace diff 與 audit schema 斷言（`:112-113` 方向），刪 `:117` 全 JSON 要求。

---

## COMPOSER-R3-P1-01

**斷言**: R2 收斂 E-10 已定「定稿門檻採 codex **≥50 筆＋≥3 session/UTC 日**、主委暫定值上線但 Task 3.3 **不得宣稱完工**」，R3 Task 3.3 僅寫 **≥20** 與 **<10 PROVISIONAL**，**未落實收斂裁決**。

**碼證**: `handoffs/reconcile/20260805-govb0-spec-r2/synth.md` E-10 段（≥50／≥3 session／不得宣稱完工）；SPEC Task 3.3 `:342-347` 無 ≥50、無 ≥3 session、無「不得宣稱完工」。`grep ≥50 docs/GOVB0_FRICTION_SPEC.md` → 0 行。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MAJOR] 信心度=High。`COMPOSER-R2-P1-04` 仍 NOT-CLOSED。修法：Task 3.3 定稿規則與 synth E-10 逐字對齊；TODO §0 引用同一門檻。

---

## COMPOSER-R3-P1-02

**斷言**: 契約 **1b 跨行剝引號**為主委 R3 新增且 b15probe6 已驗，但 Task 2.1 驗收**未列具名語料**，實作者可能只抄原型③（不含 1b）即過 Task 2.1。

**碼證**: Task 2.0 `:163-168` 1b；`bash handoffs/govb0_probes/b15probe6.sh` → commit 多行 TN 須 ALLOW。Task 2.1 `:197-205` 列 eval／`-c` 等，**無** b15probe6 四條。原型③（b15probe5）**未測**多行引號 TN。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MAJOR] 信心度=High。修法：Task 2.1 增四條狀態斷言對齊 b15probe6；納入語料 B。

---

## COMPOSER-R3-P1-03

**斷言**: 序列化拒絕後，逾時 `failed`（attempt 檔殘留、`<out>` 不存在）時**同 `<out>` 重派**的生命週期未寫，可能誤拒合法重派或永久鎖死路徑。

**碼證**: Task 3.2 `:320-324` 拒絕「進行中」第二 attempt；Task 3.3 `:352-353` 逾時後 attempt 殘留；**無**「terminal `failed` 後釋放鎖／允許重派」句。邊界 `:329` SIGKILL 亦未寫鎖釋放。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MAJOR] 信心度=Medium。修法：明文 `result_state=failed`／逾時後 attempt registry 進入 terminal、允許同 `<out>` 新 attempt；並發仍拒絕。

---

## COMPOSER-R3-P2-01

**斷言**: Task 2.0 驗收稱契約「**10 項**」，但條目含 **1** 與 **1b** 及 2–10，計數與 `票 B-17` 漂移同型，TODO 生成易漏項。

**碼證**: `:161-178` 列 1、1b、2–10（11 個編號點）；`:183`「契約 **10 項**」；`:185`「10 個 mutation」。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MINOR] 信心度=High。修法：統一計數（1b 併入 1 或改稱 11 項／mutation 數）。

---

## COMPOSER-R3-P2-02

**斷言**: `票 B-36`（群集表盲點）應記為 MAJOR 治理債，產出端預列 ID 優於僅靠委員人工發現。

**碼證**: R2 synth `:37-41` 實證 `COMPOSER-R2-P1-01` 漏群集表、`completeness --lock` rc=0；brief Q5 待 R3 裁定。

**來源摘要**: handoffs/reconcile/20260805-govb0-spec-r2/synth.md#8b8d0a948782

[MINOR] 信心度=High。建議併入 `票 B-13` 或開 `票 B-36`；`reconcile_build.sh` 預列全部 ID。

---

ASSUMPTIONS_VERIFIED: template_check rc=0；Task count=11=§V；b15probe5 26/26；b15probe6 4/4；b15probe4 fail-open 現行 gate；SPEC sha256=c4448d67356ff0fd80a99491754986dc98079700969a6220896511617e0ffc57
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` PASS rc=0；`grep -c '^\*\*Task '` → 11；`bash handoffs/govb0_probes/b15probe{4,5,6}.sh` rc=0；`grep -c ≥50 SPEC` → 0
FAILURES_SEEN: none（探針預期 BLOCK/ALLOW 為證據）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查禁改碼）

產出檔: handoffs/20260805-govb0-spec-r3-composer.md
/tmp 清理: 無 `govb0*` 工作目錄；保留 `claude-501`

STATUS: DONE
