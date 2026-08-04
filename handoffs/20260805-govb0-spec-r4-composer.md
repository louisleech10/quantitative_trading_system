# GOVB0-SPEC-R4 — Composer Adversarial Review (R4)

**審查標的**：`docs/GOVB0_FRICTION_SPEC.md`（R4 版）  
**家族**：COMPOSER | **輪次**：R4 | **task-id**：GOVB0-SPEC-R4  
**日期**：2026-08-05

---

## 被當成事實的未驗證假設（§0）

| 標籤 | brief／SPEC 陳述 | 裁定 |
|---|---|---|
| **assumed→大致成立** | `F-1`～`F-7` 全部已在 R4 落實且未引入新矛盾 | **F-1／F-4／F-5／F-6 文本層 CLOSED**；**F-3 主路徑 CLOSED**（stale pid／timestamp 覆蓋 SIGKILL 未收尾）；**F-7 部分 CLOSED**（backlog 有具名殘留，SPEC 未寫入，見 P1-02）；**F-2 heredoc 子項仍缺機械規則**（見 P1-03）。 |
| **assumed→可執行** | `F-2` 四項判定（含遞迴上限 3 層）可機械實作 | **遞迴上限 3 層＋unquoted `-c`＋跳脫引號**：可執行（遞迴計數器＋逐字元狀態機）。**heredoc**：語意已定但**缺 delimiter／body 邊界演算法**（見 Q3）。 |
| **assumed→可生成 TODO** | 本 SPEC 已可生成 TODO | **條件成立**：無新 P0 機制缺口；P1 為交叉引用／驗收覆蓋／契約細化，**修補後可進 TODO，不必開 R5**（見 Q2）。 |
| **fact-verified** | R4 = 4 Phase／11 Task；`template_check.sh spec` rc=0；三處計數一致 | **複核通過**：`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0；`grep -c '^\*\*Task '` → 11；契約條目 awk 計數 → 11；§V `:412` 宣稱 11。 |
| **fact-verified** | `awk` 熱路徑 +5 ms／次 | **複核通過**：`bash handoffs/govb0_probes/awk_hotpath_bench.sh` → 差額 5 ms／200 次。 |
| **fact-verified** | 原型③ 26/26；b15probe6 4/4 | **複核通過**：`bash handoffs/govb0_probes/b15probe5.sh` rc=0；`bash handoffs/govb0_probes/b15probe6.sh` rc=0。 |

---

## §1 必查摘要

| # | 類別 | 結果 |
|---|---|---|
| 1 | 矛盾/互斥 | **有（輕）** — finding ID 交叉引用對調（`:230`／`:387`，見 P1-01）；非機制矛盾。 |
| 2 | 漏項/端到端 | **有（輕）** — `F-7` 具名殘留未入 SPEC（P1-02）；Task 3.3 驗收未覆蓋 E-10 狀態（P2-01）。 |
| 3 | 不可測驗收 | **有（輕）** — heredoc 契約第 10 項無可執行 span 規則（P1-03）；Task 3.3 PROVISIONAL 僅在改法、無驗證句（P2-01）。 |
| 4–8 | quant／OOM／Cache／API | **無** |
| 9 | 測試品質 | **無新增 BLOCKING** — 1b 四條已具名；decision trace 與 audit 分離驗收已到位。 |
| 10 | Agent 可執行性 | **有（輕）** — heredoc 實作者須自行發明 span 規則（P1-03）。 |
| 11 | 必要性/短命工 | **無** |

## §2 範本錨點 + 獵空殼

- §RISK／§A／§C／§P／§V／§R／§N：**齊**；§G N/A 合理。
- §A FACT-RECEIPT：10 條（含 awk bench）；OPEN 項條件已寫。
- 獵空殼：**未發現表頭-only**；各 Task 驗證欄有 ASSERT／狀態斷言 token。

---

## Q1 — 本家族 R3 每一條 finding 關閉判定

| Finding ID | Verdict | 重跑反例與結果 |
|---|---|---|
| `COMPOSER-R3-P0-01`（F-1） | **CLOSED** | `:122-128` 改為 **decision trace** `(rc,kind)` diff 為空；audit 面獨立斷言；`:125` 明文刪除「兩份 audit JSON diff 為空」。`rg '兩份.*JSON diff 為空' docs/GOVB0_FRICTION_SPEC.md` 僅剩否定句（`:125`），無矛盾驗收句。 |
| `COMPOSER-R3-P1-01`（F-4） | **CLOSED** | Task 3.3 `:384-392`：≥50 筆、≥3 session／UTC 日、PROVISIONAL、不得宣稱完工、`B-14` 未定稿；10–19 灰區已消除（「只有達標／未達標」）。`rg '≥50' docs/GOVB0_FRICTION_SPEC.md` → `:384`。 |
| `COMPOSER-R3-P1-02`（F-6） | **CLOSED** | Task 2.1 `:225-232` 列 b15probe6 四條＋mutation「sed 行內替換 → ①② BLOCK」。`bash handoffs/govb0_probes/b15probe6.sh` rc=0。 |
| `COMPOSER-R3-P1-03`（F-3） | **CLOSED** | Task 3.2 `:347-361`：ownership／release（`_emit_family_result` 後必定，不依賴 publish）／stale（pid 死或逾 timeout＋外層閥）／`failed` 後重派放行／被拒不寫 `result_state`；三條防誤拒／防鎖死於 `:358-361`。SIGKILL 邊界 `:369`＋stale pid 規則覆蓋 wrapper 未收尾路徑。 |
| `COMPOSER-R3-P2-01`（F-5） | **CLOSED** | `:192-201` 統一 **11 項**／≥22 語料／11 mutation；`:192` 含機械核對紀律。 |
| `COMPOSER-R3-P2-02`（F-7） | **NOT-CLOSED（部分）** | backlog `B-36` `:1250-1258` 已記「產出端只能擋漏、擋不了錯位」；**SPEC 內無 `票 B-36` 或該殘留**（`rg 'B-36\|錯位' docs/GOVB0_FRICTION_SPEC.md` 僅 `:7` 敘事提及「引用 ID 錯位」，非具名殘留）。見 P1-02。 |

---

## Q2 — 出場判準

| 指標 | 結果 |
|---|---|
| 本輪 findings 總數 | **5 條**（P1×3、P2×2；**新 P0 機制缺口 0 個**） |
| 新 P0 機制缺口（非同步／計數／措辭類） | **0** |
| **判定** | **符合** composer R3 出場判準（≤5 條且新 P0＜2）⇒ **不必開 R5**；P1 修補後可進 TODO 生成。 |

---

## Q3 — `F-2` heredoc 與遞迴上限可實作性

**遞迴上限 3 層**：可機械執行——對 `-c`／`eval`／`$()` 引數內容遞迴套用同一掃描器，`depth` 從 0 起算，進入引數內容 `depth++`，`depth>3` ⇒ BLOCK。與契約第 8 項一致，無歧義。

**heredoc span 界定（建議寫入 Task 2.0 契約第 10 項附錄，否則實作者各做各的）**：

1. **觸發**：在未處於引號 span 內時，匹配 `<<-?`（可選 `-` 表 tab-strip）。
2. **delimiter 詞法**：`<<` 後至行尾（或至 `;`／`|`／`&` 前——heredoc 運算子本身在引號外）讀取 delimiter token；若為 `'WORD'` 或 `"WORD"` 則去引號得 `WORD`（quoted delimiter 時 body 不做變數展開，與 POSIX 一致）。
3. **body 起訖**：自**下一行**起，至**獨立一行**僅含 `WORD`（`<<-` 時允許前導 tab）為止；該區間整段視為**單一引號 span**（內容不掃描命令位置、不作分隔符）。
4. **多個 heredoc**：同一命令列上多個 `<<` 按**左到右**各開一個 span，各自以 delimiter 關閉後才恢復外層掃描。
5. **與 1b 整合**：heredoc span 與 `'`／`"` span 互斥狀態機（`NORMAL | IN_SQUOTE | IN_DQUOTE | IN_HEREDOC(word)`）；未閉合 delimiter（EOF 前未見關閉行）⇒ fail-closed（同契約第 6 項）。
6. **範例**：`cat <<EOF; codex exec x` → heredoc body 內不掃描；`;` 之後的 `codex exec x` 照常 BLOCK（與 R2 誤擋案例一致）。

**嚴重度裁定**：規則可寫清且可在 awk 狀態機擴充（b15probe6 已有跨行框架）；**不升 P0**——列 **P1**（契約須補明文，見 P1-03），不阻擋本批進 TODO（實作 Phase 2 前補齊即可）。

---

## Q4 — `F-3` lock 失效路徑覆蓋

| 路徑 | SPEC 處置 | 永久鎖死？誤拒？ |
|---|---|---|
| 正常結束 | publish 成功／失敗皆經 `_emit_family_result` 釋放（`:349-350`） | 否 |
| 格式失敗 | `format-failed`＋release（`:343-344`、`:349`） | 否 |
| SIGKILL（CLI） | `:369` 不 publish、`failed`；release 在 `_emit_family_result`；若 wrapper 未及執行 ⇒ stale pid（`:351`）可接管 | 否（stale 覆蓋） |
| 外層 timeout | `:351` 時間戳 > 家族 timeout＋外層閥 ⇒ stale | 否 |
| 跨裝置 rename 失敗 | `:369` fail-closed；release 仍應在 `_emit_family_result` | 否 |
| lock 檔被外部刪除 | **未明文**；存活判定若僅依 lock 檔存在，可能與「並發拒絕」脫鉤 | **理論雙派工風險**（低機率）；列 P2-02，不阻擋本批 |
| `failed` 後同 `<out>` 重派 | `:352`、`:358` 明文放行 | 否 |
| 被拒 attempt | `:353-355`、`:360-361` 不寫 `result_state` | 否 |

---

## Q5 — 交叉引用紀律（機械核對）

| 宣稱 | 導出命令 | 實測 | 一致？ |
|---|---|---|---|
| Task 總數 11 | `grep -c '^\*\*Task '` | 11 | ✅ |
| §V「全部 11 個 Task」 | 同上 | 11 | ✅ |
| 契約 11 項 | awk 計數 Task 2.0 改法條目 `1`/`1b`/`2`–`10` | 11 | ✅ |
| 驗收 ≥22 語料 | 11 項 ×（TP+TN） | 邏輯一致 | ✅ |
| 11 mutation | `:201` | 與 11 項對齊 | ✅ |
| finding ID `:230` | 語境＝1b 語料（F-6） | 引用 `COMPOSER-R3-P1-01`（實為 E-10，F-4） | ❌ 應為 `COMPOSER-R3-P1-02` |
| finding ID `:387` | 語境＝E-10 門檻（F-4） | 引用 `COMPOSER-R3-P1-02`（實為 1b，F-6） | ❌ 應為 `COMPOSER-R3-P1-01` |
| `票 B-36` 具名殘留 | `rg 'B-36' docs/GOVB0_FRICTION_SPEC.md` | 0 行 | ❌ F-7 要求寫入 SPEC／§N，僅 backlog 有 |

---

## Q6 — §V「有 rc 斷言但無對應狀態斷言」

| Task | `ASSERT … rc` | 同 Task 狀態斷言 | 結果 |
|---|---|---|---|
| 0.1 | `:120-121` | decision trace（`:122-124`）＋ audit schema（`:127-129`） | ✅ |
| 1.1 | `:150-152` | prompt 內容／unknown 四項無副作用（`:153-156`） | ✅ |
| 2.5 | `:299`（附加項非預期 ⇒ rc≠0） | `:297-298` 必要子集＋`:301` sha256 | ✅ |
| 3.2 | `:356`（並發拒絕 rc≠0） | `:342-345`、`:358-361` 檔案／audit 狀態 | ✅ |
| 3.3 | `:399` | `:400-403` result_state／孤兒／manifest | ✅ |

**結論**：**未發現**「有 rc 斷言但完全無對應狀態斷言」的 Task。Task 3.3 的 E-10 **改法**有 PROVISIONAL／不得完工，但**驗證段未覆蓋**（見 P2-01，非 §V rc 缺配對問題）。

---

## Q7 — 可以進 TODO 生成嗎？

**可以（修補後）**。

| # | 阻擋？ | 說明 | 不受理範圍？ |
|---|---|---|---|
| P1-01 | 建議修後再派 | 兩處 finding ID 對調——正是 `B-36`「錯位」病型再現 | 否 |
| P1-02 | 建議修後再派 | F-7 具名殘留未入 SPEC | 否（治理紀錄，非機械 oracle） |
| P1-03 | 建議修後再派 | heredoc 機械規則缺文 | 否 |
| P2-01／P2-02 | 否 | 驗收覆蓋／邊界明文，可進 TODO 後第一輪實作補 | 否 |

---

## Verdict：需修補後派工（符合出場判準，不必開 R5）

R4 已閉合 R3 全部 **P0 機制缺口**（F-1／F-2 主體／F-3／F-4／F-5／F-6）。殘留 5 條均為 **交叉引用紀律、治理殘留記錄、契約細化、驗收覆蓋**——與 R3 收斂「accretion 已中止」一致。**修補 P1-01～P1-03 後即可生成 TODO**，無需 R5。

---

## COMPOSER-R4-P1-01

**斷言**: Task 2.1 `:230` 與 Task 3.3 `:387` **交叉引用對調**——前者（1b 語料）誤引 `COMPOSER-R3-P1-01`（E-10），後者（E-10）誤引 `COMPOSER-R3-P1-02`（1b），正是 R3 戳記輪 `B-36`「錯位」病型在本 SPEC 內再現。

**碼證**: `docs/GOVB0_FRICTION_SPEC.md:230`（F-6 語境＋`P1-01` ID）；`:387`（F-4 語境＋`P1-02` ID）。R3 synth F-4↔F-6 對照表可核。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25

[MAJOR] 信心度=High。修法：`:230` → `COMPOSER-R3-P1-02`；`:387` → `COMPOSER-R3-P1-01`。code review 機械 grep finding ID 與 F 群集表交叉核對。

---

## COMPOSER-R4-P1-02

**斷言**: `F-7` 要求 `票 B-36` 併入 `B-13` 並在 SPEC **補具名殘留**（產出端只能擋「漏」、擋不了「錯位」），但 R4 SPEC **未記載**（backlog `:1250-1258` 已有）。

**碼證**: `rg 'B-36' docs/GOVB0_FRICTION_SPEC.md` → 0；`handoffs/20260801-GOV-AMEND-BACKLOG.md:1250-1258` 有完整殘留敘事。brief F-7 表宣稱 R4 已補。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25

[MAJOR] 信心度=High。修法：§N 不受理表或 §A 增一條「已知治理殘留」pointer 至 backlog `B-36`／`B-13` 錯位限制；避免實作者以為 reconcile 產出端修法已全解。

---

## COMPOSER-R4-P1-03

**斷言**: 契約第 10 項 heredoc「本體視為引號 span」**未定義可機械執行的 delimiter／body 起訖規則**（`<<EOF`／`<<'X'`／`<<-EOF`／多 heredoc 併存），Task 2.0 驗收要求該項 TP/TN 但無具名語料或演算法。

**碼證**: `:189-190` 僅語意描述；`rg 'heredoc|<<EOF' docs/GOVB0_FRICTION_SPEC.md` 無 span 演算法；`b15probe5.sh` 26 條不含 heredoc 向量。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25

[MAJOR] 信心度=High。修法：將 Q3 六條規則写入 Task 2.0 契約第 10 項；增 ≥2 條具名語料（heredoc 內 TN、heredoc 外 TP）。**不升 P0**——可在 Phase 2 實作前補文，遞迴上限等其他 F-2 項已可執行。

---

## COMPOSER-R4-P2-01

**斷言**: Task 3.3 **改法** `:390-392` 定義 PROVISIONAL／不得宣稱完工／`B-14` 未定稿，但**驗證段** `:398-404` 無對應狀態斷言，E-10 取捨無法證偽。

**碼證**: `rg 'PROVISIONAL|不得宣稱' docs/GOVB0_FRICTION_SPEC.md` 僅出現在改法（`:391-392`），Task 3.3 驗證區無匹配。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25

[MINOR] 信心度=High。修法：驗證增「未達 ≥50 筆時 TODO §0／manifest 含 `PROVISIONAL` 標記且 Task 3.3 標記 incomplete」狀態斷言。

---

## COMPOSER-R4-P2-02

**斷言**: lock 生命週期未覆蓋 **lock 檔被外部刪除** 而 attempt 進程仍存活之路徑——若「存活中」僅檢查 lock 檔存在，可能允許第二派工與第一 CLI 並存。

**碼證**: Task 3.2 `:356-357` 並發拒絕依「存活中 attempt」；`:347-351` 定義 ownership／stale，**無**「lock 遺失但 pid 仍活」分支。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25

[MINOR] 信心度=Medium。修法：存活判定應以 **pid／attempt registry** 為準、lock 為輔；或邊界明列「lock 遺失 ⇒ 以 pid 探測決定是否拒絕」。低機率，不阻擋 TODO。

---

ASSUMPTIONS_VERIFIED: template_check rc=0；Task=11=§V；契約項=11；b15probe5 26/26；b15probe6 4/4；awk +5ms；SPEC sha256=9f59e2618d25f59aca50974563583849904bb1253f26c1264ce28965fcda62dc
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` PASS rc=0；`grep -c '^\*\*Task '` → 11；`bash handoffs/govb0_probes/b15probe{5,6}.sh` rc=0；`bash handoffs/govb0_probes/awk_hotpath_bench.sh` rc=0；`rg 'B-36' docs/GOVB0_FRICTION_SPEC.md` → 0
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查禁改碼）

產出檔: handoffs/20260805-govb0-spec-r4-composer.md

STATUS: DONE
