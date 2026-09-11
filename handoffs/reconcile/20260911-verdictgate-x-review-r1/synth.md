# Reconcile — 20260911-verdictgate-x-review-r1

**來源** 20260911-verdictgate-x-review-r1-composer.md, 20260911-verdictgate-x-review-r1-grok.md　|　**roster** composer,grok

## 群集 / 處置

**Verdict**：需修補後合併——composer／grok 皆 `VERDICT: blocked`，5 條全採納並已寫進 SPEC v2；**codex 未交件**（誤依 AGENTS.md Rule 12「reconcile 未核可不動工」——審查不是動工），本輪 roster 只有兩家 ⇒ **不構成三家 quorum**，SPEC v2 須進 R2 由三家全員審。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 Task 2.1 legacy 字面表雙向誤判 ⇒ 整個取消，舊產出一律 `unknown` 不判** | P1 | COMPOSER-R1-P1-01、COMPOSER-R1-P1-02、GROK-R1-P1-01、COMPOSER-R1-P2-01（四條獨立） | **採納，且採比三家提的更徹底的修法**。三家實跑：under-block ≥63 份（「需修補後派工／條件式可進」被判 proceed）、over-block 10 份（閉合輪同區塊含歷史「不可進」被判 blocked）、金標跨批檔反被判 proceed、掃描範圍未定義。任何字面表都會在這三個方向再犯 ⇒ **不推導**：Phase 1 上線前的 621 份一律 `unknown`、不進閘（使用者 2026-08-05「不溯及既往」），Task 2.1 改為透明度報表、取消基準檔；C-4 同步改寫。 |
| **W2 Task 2.2 只讀最新輪 ⇒ 「下一輪改寫 proceed 不寫 CLOSED」即可跨批** | P0 | GROK-R1-P0-01 | **採納**。改讀該批**全部輪**之 `blocked_by` 聯集；每個 `(family, ID)` 須有**同家**後續 `CLOSED:` 含該 ID；`proceed` 本身不解除任何 ID。新增兩條 ASSERT（r1 blocked＋r2 proceed 無 CLOSED ⇒ rc≠0；CLOSED 由他家寫 ⇒ rc≠0）。 |
| **W3 `Ticket-Batch: small` 可連鎖拆分繞過** | P1 | GROK-R1-P1-02 | **採納**。單 commit 層無法判 ⇒ Task 3.3 於 push 時對 `origin/main..HEAD` 全部 small commit 取生產檔**聯集**：> 3 檔或含 `factories.py|protocols.py|config.py` ⇒ 拒 push 並要求改領 `--impl-self`。兩條 ASSERT。 |
| **W4 `--amend -m` 會丟 trailer** | P2 | GROK-R1-P2-01 | **採納**。邊界①改為只有 `--amend --no-edit` 沿用（§A 已有 FACT）；`-m` 視同新訊息須重帶。 |

### 本輪程序問題（記錄，R2 brief 處理）
codex 交空檔並回 `STATUS: BLOCKED — reconcile 未核可`；同時把 brief 檔還原成 HEAD（票 B-50 形態②）——因 brief 已 commit，內容無損。R2 brief 檔頭明寫「brief-kind: review ⇒ Rule 12 不適用」。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## COMPOSER-R1-P1-01

**斷言**: Task 2.1 legacy 字面表將含 `CLOSED`／條件式 `可進` 的「需修補後派工」產出判為 proceed，全庫至少 63 份 false proceed，基準 under-block 導致 2.2 漏擋跨批。

**碼證**: `python3 /tmp/verdictgate-composer-r1/legacy_scan4.py` → `three_value_blocked_legacy_proceed=46`；`conditional_可進_legacy_proceed=15`；`opening_blocked_legacy_not_blocked=2`；例 `20260910-evtlabel-b1-review-r1-codex.md` L21；`docs/VERDICTGATE_SPEC.md` Task 2.1 字面表 L69。

**來源摘要**: docs/VERDICTGATE_SPEC.md#b53b872acadf

[MAJOR→P1] 信心度=High。實作 `verdictgate_baseline.sh --freeze` 會漏凍結 GAP3D2／EVTLABEL 類鍵，上線後仍可能 `debt_clear`→開輪。修法：legacy 先判三值 `需修補後派工|有根本缺陷`⇒blocked；`CLOSED:` 僅在 `VERDICT:` 行或同族 closure 機械塊計入；條件式 `可進…不得` 列入 blocked 字面或 whole-file 掃描開頭摘要。

---

## COMPOSER-R1-P1-02

**斷言**: legacy 表 blocked 字面優先，使 10 份閉合輪（同區塊含歷史「不可進」＋「CLOSED」）被判 blocked，基準 over-block 使 2.2 對已閉合 ID 永久誤擋。

**碼證**: `python3 /tmp/verdictgate-composer-r1/legacy_scan4.py` → `closure_language_but_legacy_blocked=10`；例 `20260826-gap3ux-b4-review-r3-grok.md`；Task 2.1 L69 blocked 優先無 closure 例外。

**來源摘要**: docs/VERDICTGATE_SPEC.md#b53b872acadf

[P1] 信心度=High。實作後合法「R2 不可進→R3 CLOSED」序列在基準中仍為 blocked，與 C-3 矛盾。修法：閉合輪或含 `CLOSED:` 機械行時以最新輪 `VERDICT`／三值為準；或 blocked 字面僅掃 `## Verdict` 首段不含 RECHECK 子句。

---

## COMPOSER-R1-P2-01

**斷言**: Task 2.1 未規定 `--legacy` 掃描範圍（整檔／`## Verdict`／tail40），實作者必須猜，導致同一表在不同 parser 下結果不一致。

**碼證**: Task 2.1 僅列字面表無區域算法；`20260905-gap3d2-b3-review-r1-codex.md` 開頭「不可進 B-D4」在 tail40 外⇒proceed；`legacy_dist unknown=284`（近半無法判定）。

**來源摘要**: docs/VERDICTGATE_SPEC.md#b53b872acadf

[MINOR] 信心度=High。實作若各用 whole-file vs tail40，基準 SHA 不可比。修法：在 Task 2.1 寫死 `verdict_parse.sh --legacy` 算法（優先 `## Verdict` 至下一 `##`；無則前 12 行＋`## Verdict` 行；仍 unknown 則 whole-file）並 ASSERT 固定样例。

---

```
VERDICT: blocked
BLOCKED-BY: COMPOSER-R1-P1-01,COMPOSER-R1-P1-02
```

---

ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0；legacy 掃描 628 份；SPEC §P／§N／偵察 synth V1–V6 對照。
TESTS_RUN: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` → PASS rc=0；`python3 /tmp/verdictgate-composer-r1/legacy_scan4.py` → 見必答 4。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查＋/tmp 掃描腳本）
NUMERIC_OR_SCHEMA_IMPACT: none（建議變更 Task 2.1 legacy 演算法，未改檔）
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-x-review-r1-composer.md

STATUS: DONE
## GROK-R1-P0-01

**斷言**: Task 2.2 只以「最新 review 輪」的 `blocked_by` 為掃描起點，與 C-3「只計無後續 closed 的 blocked」不等價——同家下一輪改 `VERDICT: proceed` 且不寫 `CLOSED:` 即可開下一批。

**碼證**: `docs/VERDICTGATE_SPEC.md` L79 改法句＋L81–83 ASSERT 皆為單輪 `prev_verdict=blocked`；無 `R1 blocked → R2 proceed closed=absent` 反例。構造見必答 2 序列 A。RECHECK: 讀 L33 C-3 與 L79；對照 ASSERT 列表確認缺多輪。

**來源摘要**: docs/VERDICTGATE_SPEC.md#b53b872acadf

[BLOCKING] 信心度=High。不改則實作者照字面實作後，閘在實作批出現與今日相同的「帶傷跨批」。修法：對前批**所有** review／closure 輪做 per-family 時間線，凡曾出現於 `blocked_by` 且之後同家任何產出之 `closed` 未含該 ID（且不在 baseline）⇒ rc≠0；並加 ASSERT 覆蓋序列 A。

---

## GROK-R1-P1-01

**斷言**: Task 2.1 legacy 字面表（`不可進|不可收票|不可直接進`／`可進|可收票|已全數閉合|CLOSED`）在 Verdict 區域實跑下，把金標跨批阻擋檔判成 proceed／none，無法支撐驗證句要求的 `EVTLABEL b1:codex` 與 `GAP3D2-b3:codex` 鍵。

**碼證**: 當次 `python3 /tmp/verdictgate-grok-r1/scan3.py` → 類別 blocked=28 proceed=107 unknown=460 none=34；`20260910-evtlabel-b1-review-r1-codex.md` → proceed（含「可進 B2 前不得」）；`20260905-gap3d2-b3-review-r1-codex.md` → none（無 `## Verdict`，檔首「不可進 B-D4」）；Task 2.1 L71–72 驗證句點名該二鍵。RECHECK: 重跑同等 Verdict 區域＋blocked-first 掃描；`grep -n Verdict handoffs/20260905-gap3d2-b3-review-r1-codex.md`。

**來源摘要**: docs/VERDICTGATE_SPEC.md#b53b872acadf

[MAJOR] 信心度=High。不改則 `--freeze` 要麼驗收紅、要麼手寫鍵（無 SPEC 授權）→ 2.2 baseline 豁免集錯誤。修法：legacy 先對範本三值／檔首摘要映射（`需修補後派工|有根本缺陷|不可進…`⇒blocked；`可派工`⇒proceed）；`CLOSED` 僅計機械 `CLOSED:` 行；寫死掃描區域與 BOTH 優先序；ASSERT 釘死上述二金標檔。

---

## GROK-R1-P1-02

**斷言**: Task 3.2 的 `Ticket-Batch: small`（單 commit ≤3 檔＋三 basename）可被連續多個 small commit 拆開，使生產碼變更全程不領 `--impl-self`、不經 `verdictgate_check`。

**碼證**: Task 3.2 L104 判準＋ASSERT L107–108 只約束**單次** staged 檔數；無跨 commit 累計。構造：3×`Ticket-Batch: small`各 3 個 `momentum/*.py`＝9 檔。RECHECK: 讀 L104–110；確認 Task 3.3 只驗 trailer／token 曾存在，不累計 small 檔數。

**來源摘要**: docs/VERDICTGATE_SPEC.md#b53b872acadf

[MAJOR] 信心度=High。不改則 Phase 3「不論誰實作皆觸發」對主委自寫生產碼在 small 路徑空轉。修法：採必答 3 之累計 unique 生產檔上限，或禁止與未閉合 ticket 並行的 `small`；並加 ASSERT「兩 commit small 累計 4 檔 ⇒ 第二 commit 或 push 拒」。

---

## GROK-R1-P2-01

**斷言**: Task 3.2 邊界①寫「`--amend` 沿用原訊息之 trailer」過寬——`git commit --amend -m` 會丟 trailer，僅 `--no-edit` 沿用。

**碼證**: 本輪於臨時 git repo：`commit` 含 `Ticket-Batch`＋`Governance-Scope` → `--amend --no-edit` 後 `git interpret-trailers --parse` 兩鍵仍在；再 `--amend -m 'feat: amended without trailers'` 後 parse 為空。RECHECK: 重做該兩步。

**來源摘要**: docs/VERDICTGATE_SPEC.md#b53b872acadf

[MINOR] 信心度=High。不改則實作者誤以為 amend 永不掉 trailer，3.3 才在 push 爆。修法：邊界改為「`--amend --no-edit` 沿用；改訊息須重附 trailer」，ASSERT 覆蓋 `-m` 丟 trailer ⇒ rc≠0。

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P0-01,GROK-R1-P1-01,GROK-R1-P1-02

---

ASSUMPTIONS_VERIFIED: 偵察 GROK 七條對照 SPEC；template_check spec PASS；legacy scan3 629 檔；amend trailer 兩路徑；audit committee_output 多次 register／同秒；Task 2.2／3.2 原文與 ASSERT 缺口。
TESTS_RUN: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` → PASS rc=0；legacy Verdict 區域掃描 → blocked=28 proceed=107 unknown=460 none=34 BOTH=23；amend-test interpret-trailers 見必答／P2-01；`bash scripts/completeness_check.sh --single handoffs/20260911-verdictgate-x-review-r1-grok.md --family grok` → PASS rc=0（4 IDs）。
FAILURES_SEEN: (1) `cd /Users/...` 觸發 permission deny，改專案相對路徑；(2) macOS case-insensitive 下誤用 `…REVIEW-R1-grok.md` 短交接覆寫產出，已還原全文。
SCOPE_CHANGES: none（唯讀審查；/tmp 掃描腳本已清）
NUMERIC_OR_SCHEMA_IMPACT: none（提案改 Task 2.1／2.2／3.2 演算法，未改庫內檔）
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-x-review-r1-grok.md
STATUS: DONE
