# Reconcile — 20260805-govb0-spec-r4

**來源** 20260805-govb0-spec-r4-codex.md, 20260805-govb0-spec-r4-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併 — 8 條全部歸戶，**無未分群 ID**。**全部 8 條已於 SPEC R5 修畢**（逐條對應見下）。

**收斂趨勢**：R1 19（5 P0）→ R2 17（7 P0）→ R3 11（3 P0）→ **R4 8（2 P0）**。

🔴 **兩家對出場判準的判定不一致，主委裁決記錄如下**：
- composer：「**符合出場判準，不必開 R5**……修補 P1-01～P1-03 後即可生成 TODO」
- codex：「**不符合**（3 findings ≤5，但 **2 個新 P0 機制缺口**，不滿足 <2）」
**裁：以 codex 為準，開 R5**（取較嚴者；且 codex 的兩個 P0 皆為實質可執行性缺口，非措辭問題）。
**但 R5 定位為「確認輪」**——R4 的 8 條在收到報告當下即全數修畢，R5 只需逐條確認關閉，**不重新開放已裁決事項**。

**收斂基數**：8 條（codex 3／composer 5）。ID→斷言對照由 `awk` 自附錄機械抽出後才填表（防歷來 6 次錯位）。

**下表「已修」欄的驗證 receipt**（主委實跑 2026-08-05，補 claim backing）：
VERIFY: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0
VERIFY: `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` → `11`（== §V 宣稱值）
VERIFY:govb0-r4-g3-factcount — `grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → `10`（== §A 宣稱值，G-3 已修）
VERIFY:govb0-r4-g4-composer-ids — `grep -n 'COMPOSER-R3-P1-0' docs/GOVB0_FRICTION_SPEC.md` → **Task 2.1（1b 語料）處為 `P1-02`、Task 3.3（timeout 門檻）處為 `P1-01`**（G-4 已修，與 R3 收斂表一致）
VERIFY: `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r4/sources.lock` → rc=0，8/8 ID 全在綜合檔

🔴 **本節不再以行號定位**：R4 初稿曾寫「`:237` 為 `P1-02`、`:398` 為 `P1-01`」，SPEC 後續修訂使其漂移為 `:239`／`:417`
（`20260805T002551Z` 批次 receipt 實跑證實）。**行號是易腐引用**，故一律改以 Task 編號定位。此為 `票 B-17`／`B-13` 同族病型的第 8 次現形。

**G-1／G-2／G-5／G-6 的證據狀態（不主張已自證）**：四者為 SPEC 文字修訂，本收斂檔**未產出可機械複驗的 receipt**，
其正確性**由 R5 確認輪逐條複核**。此處**不援引任何豁免類別**——先前草稿誤寫 `VERIFY-EXEMPT:doc-summary:*`，
而 `doc-summary` **不在 `EXEMPT_RE` 的六個合法類別內**（`typo`／`doc-example`／`migration-note`／`template-drift`／
`tooling-blocked`／`spec-ambiguity`），該 token 自始無效力，等同未標記，屬**假豁免**，已全數移除。

| 群 | 主張 | 對應 finding | 處置（R5 已修） |
|---|---|---|---|
| G-1 | **heredoc「視為引號 span」無可執行的 delimiter／body 邊界契約** ⇒ 合法 heredoc 之後的真派工可被漏掃 | `CODEX-R4-P0-01`／`COMPOSER-R4-P1-03` | **ACCEPT-BLOCKING → 已修**（**證據狀態：待 R5 逐條複核**，本檔不自證）：契約第 10 項補**五條機械規則**（起點＝`<<[-]?\s*(['"]?)IDENT\1` 後的下一個換行／delimiter 去引號／終點＝行首恰為 delimiter（`<<-` 允許 tab 縮排）／多 heredoc **依序消耗**／未閉合 ⇒ fail-closed），並列 5 組驗收語料 |
| G-2 | **lock 生命週期未覆蓋四條路徑**：外部刪 lock、outer-timeout、跨裝置 rename 失敗、**stale takeover 後的 owner-safe release** ⇒ 可能併發重派或**舊 attempt 解掉新 attempt 的鎖** | `CODEX-R4-P0-02`／`COMPOSER-R4-P2-02` | **ACCEPT-BLOCKING → 已修**（**證據狀態：待 R5 逐條複核**，本檔不自證）：新增 **owner-safe release**（釋放前比對 attempt id，不符不得釋放）／wrapper 被 SIGKILL 依 stale 回收／外層 timeout **不直接刪 lock**／跨裝置失敗仍走 `_emit_family_result` 並 owner-safe 釋放／「存活中」判準改為 **lock 檔 ∪ attempt 進程**；驗收由 3 條擴為 **8 條逐路徑狀態斷言** |
| G-3 | **§A 已驗證事實計數與實際 FACT-RECEIPT 數不一致**（寫 9、實 10） | `CODEX-R4-P2-01` | **ACCEPT → 已修**（VERIFY:govb0-r4-g3-factcount；SUPERSEDED: 取代同一 claim 先前「§A 寫 9」的紅燈紀錄）：docs/GOVB0_FRICTION_SPEC.md §A 改 10 並**同行註明導出命令** `grep -c '^- FACT-RECEIPT:'`。**本 SPEC 內第三次計數漂移**（Task 總數／契約項數／本條），同 `票 B-17` 病型 |
| G-4 | **SPEC 內文兩處 composer ID 對調**：Task 2.1（1b 語料）誤引 `P1-01`、Task 3.3（E-10）誤引 `P1-02` | `COMPOSER-R4-P1-01` | **ACCEPT → 已修**（VERIFY:govb0-r4-g4-composer-ids）：Task 2.1 處改 `P1-02`、Task 3.3 處改 `P1-01`（**以 Task 定位，不用易腐的行號**） |
| G-5 | **`F-7` 要求把 `票 B-36` 的具名殘留寫入 SPEC，R4 只寫進 backlog、SPEC 漏記** | `COMPOSER-R4-P1-02` | **ACCEPT → 已修**（**證據狀態：待 R5 逐條複核**，本檔不自證）：§N 不受理表下方補「ID 錯位無機械防線」殘留段 |
| G-6 | **Task 3.3 的 `E-10` 取捨只寫在改法散文，驗證段無對應狀態斷言** ⇒ 不可證偽 | `COMPOSER-R4-P2-01` | **ACCEPT → 已修**（**證據狀態：待 R5 逐條複核**，本檔不自證）：補三項狀態斷言（TODO §0／manifest 含 `PROVISIONAL`；Task 3.3 標未完工；`票 B-14` 標未定稿；任一缺失即 FAIL） |

**`G-4` 的病史（同一錯誤第 6 次，且這次是我修了 A 沒修 B）**

R3 戳記輪三家已指出收斂檔的 `COMPOSER-R3-P1-01`／`P1-02` 對調，主委**修了收斂檔卻沒同步 SPEC 內文**，
於是同一組 ID 在 SPEC 裡仍是錯的，由 composer 在 R4 抓到。
⇒ **與 `G-3` 同根**：交叉引用不同步。本 session 此病共現形 **7 次**（歸錯 ID×3、漏引×1、對調×2、計數×3 有重疊）。
🔴 **本輪起主委改用機械作法**：填群集表前，先以 `awk` 自附錄抽出「ID → 斷言首句」對照表，**照表填**，
不再憑閱讀記憶。本表即以此法產生。**此作法應寫入 `票 B-36`／`B-13` 的修法（產出端骨架同時預列 ID 與斷言首句）。**

**主委兩道自檢（`票 B-36` 盲點的權宜補償）**

①每個來源 ID 是否出現在群集段 ②**逐條回附錄核對 ID 與主張是否配對正確**（第②道為 R4 新增，補「錯位」）。
🔴 兩道皆為人工，**不算解決**；`票 B-36` 已裁定併入 `B-13`、修法在產出端，且「錯位」為具名殘留。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P0-01
**斷言**: F-2 的 heredoc「視為引號 span」沒有可執行的 delimiter/body 邊界契約，valid heredoc 後的真派工可被漏掃。
**碼證**: SPEC:186-191 只定義結果，未定義 `<<EOF`／`<<'X'`／`<<-EOF`、多 heredoc、body 終止行或同一命令行的掃描順序；Task 2.1:211-233 只有引用契約與具名語料。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25; handoffs/govb0_probes/b15probe6.sh#643cf891ab5e
[BLOCKING] 信心度=High；Q3 無法以現文機械驗收。修法需明定 quote-aware 讀取 literal delimiter、`<<-` 僅去前導 tab、按出現順序 queue 多 heredoc、body 僅接受精確 delimiter 行、EOF/展開/歧義 fail-closed，且 body 前後照常掃描。
## CODEX-R4-P0-02
**斷言**: F-3 未閉合外部刪 lock、outer-timeout、跨裝置失敗與 stale takeover 的 owner-safe release，可能併發重派或由舊 attempt 解鎖新 attempt。
**碼證**: SPEC:347-361 定 ownership/release/stale/重派但未要求 release 比對 owner；SPEC:369、380、399-405 只列 SIGKILL/rename/outer timeout 行為，沒有 lock missing、wrapper 被殺後 terminalization 或對應狀態斷言。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25
[BLOCKING] 信心度=High；lock 被外部刪除後第二 attempt 可視為無存活 lock 而啟動；stale 接管後舊 attempt 若無 attempt-id CAS 可能釋放新 lock。修法需對所有失效路徑定 atomic ownership compare-and-release、missing-lock fail-closed、outer-timeout recovery/result_state 與回歸測試。
## CODEX-R4-P2-01
**斷言**: §A 的已驗證事實計數與可導出 FACT-RECEIPT 數量不一致。
**碼證**: `rg -c '^-[[:space:]]*FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → 10；SPEC:36 仍寫「9 條」，SPEC:214、48 又引用第 10 條。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25
[MINOR] 信心度=High；把標題改為 10 條或移除一條，並保留同一導出命令，避免再次發生 A/B 交叉引用漂移。
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

## 戳記

