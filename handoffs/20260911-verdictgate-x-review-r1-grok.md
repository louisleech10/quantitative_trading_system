# VERDICTGATE SPEC v1 adversarial review — GROK R1

task-id: 20260911-VERDICTGATE-X-REVIEW-R1
family: grok
brief: `handoffs/20260911-VERDICTGATE-SPEC-REVIEW-R1-BRIEF.md`
findings-round: R1
review-target: `docs/VERDICTGATE_SPEC.md` v1（sha256[:12]=`b53b872acadf`）

## Verdict：需修補後派工

必答 1–7 皆有立場與實跑／可重現構造。Phase 1／3／4 主骨架對齊偵察收斂 V1–V6；**不得據此直接生成 TODO 並開工 Phase 2**：Task 2.2 判定與 C-3 字面不一致（P0），Task 2.1 legacy 表無法交出 §A 點名的基準鍵（P1），`Ticket-Batch: small` 可被拆 commit 架空 `--impl-self`（P1）。

## 被當成事實的未驗證假設（§0）

| 假設 | 標記 | 判定 | 理由 |
|---|---|---|---|
| 「一家 blocked 即擋」無需人頭門檻 ⇒ 不會被濫用拖死全線 | brief `assumed` | **機制成立、否證未跑** | 單家族永久 `blocked`＋永不 `CLOSED:` 可使所有跨批停擺；本輪**未**跑該家歷史 blocked 比例。屬治理 DoS 風險，不是「繞過閘」，見必答 2 序列 G |
| Task 2.2「讀最新輪 verdict → 對其 blocked_by 查 closed」≡ C-3「只計無後續 closed 的 blocked」 | SPEC 隱含 | **不成立** | 最新輪改寫 `proceed` 且不列 `CLOSED:` 時，先前 `blocked_by` 不再被掃 ⇒ 見 P0-01 |
| Task 2.1 封閉字面表可推出驗證句點名的 EVTLABEL／GAP3D2 鍵 | SPEC Task 2.1 驗證 | **不成立** | 實跑：EVTLABEL B1 codex→`proceed`；GAP3D2 B3 codex 無 `## Verdict`→`none`（見必答 4） |
| `git interpret-trailers` 於 `--amend` 沿用訊息 | brief「我沒查」 | **半成立** | `--amend --no-edit` 保留 trailer；`git commit --amend -m '…'` **丟掉** trailer（本輪實跑） |
| audit `committee_output`「最新」可按 `ts` | brief「我沒查」 | **已由 SPEC 關閉** | §A FACT：同 task 最多 6 次、僅秒級 `ts`；Task 2.2 已改為 append 序。本輪複核：1426 筆事件、307 key 多次 register、例 key 同秒碰撞、append 序單調 |

---

## 必答 1：偵察輪 GROK finding → SPEC 落實

| 偵察 ID | SPEC 落點 | 落實？ |
|---|---|---|
| **GROK-R1-P0-01**（Ticket-Batch 不得抄 G-7 `\|\| true`） | C-2；Task 3.2 fail-closed 獨立呼叫；Task 3.3 `gov_check 1c` | **已落實** |
| **GROK-R1-P1-01**（F5 過寬；病灶＝開放詞彙＋未入 audit） | §A FACT 628/490/152；Task 1.1／1.2 封閉 `VERDICT:`＋audit | **已落實** |
| **GROK-R1-P1-02**（EVTLABEL 跨批） | Task 2.1 基準鍵；Task 2.2 掛 `committee_run`／`gate.sh dispatch` | **意圖已落實；基準鍵會被 legacy 誤判吃掉 → P1-01** |
| **GROK-R1-P1-03**（debt_clear／`--no-verify`） | 2.2 擋在開輪；3.3＋§N 留痕／`push --no-verify` 殘留 | **已落實**（`debt_clear` 本身不讀裁決，但下一 `committee_run` 會擋——與 V3 一致） |
| **GROK-R1-P1-04**（G-4 語意上限） | Task 4.1 四件套；語意列 §N | **已落實** |
| **GROK-R1-P2-01**（只計無後續 closed） | C-3；Task 2.2 | **落實錯誤** → 見 **GROK-R1-P0-01**（演算法≠C-3） |
| **GROK-R1-P2-02**（trailer 共存；cx_run 不 commit） | C-5；Task 3.2 FACT | **已落實** |

---

## 必答 2：Task 2.2 繞過序列（可重現構造）

判定原文（Task 2.2）：讀前批**最新 review 輪**各家 `verdict`；**對每個 `blocked_by` ID**查同家後續是否 `closed`。ASSERT 僅覆蓋單輪 `prev_verdict=blocked`×`closed=absent/present`，無多輪。

| # | 構造 | 擋得住？ | 為什麼 |
|---|---|---|---|
| A | B1-R1：`VERDICT: blocked`＋`BLOCKED-BY: GROK-R1-P0-01`；B1-R2 同家：`VERDICT: proceed`（**不**寫 `CLOSED:`）；開 B2 | **擋不住** | 最新輪無 `blocked_by` ⇒ 迴圈空轉；C-3 要求的「歷史 blocked 且無後續 closed」未被檢查 |
| B | B1-R2 blocked；B1-R3 該家 `DEGRADE`／缺席；閉合輪他族寫 `CLOSED: <該 ID>`；開 B2 | **擋得住** | Task 1.2 拒收他族 `CLOSED`；最新仍為 blocked 且無同家 closed |
| C | 同 ID 字面出現在 **不同 root**（票 X blocked 未閉；開票 Y-B2） | **不擋（by design）** | `verdictgate_check.sh <root> <N>` 只看同 root |
| D | 同批 B1-R2 blocked 後開 B1-R3（非跨批） | **不擋（by design）** | 邊界 ②；`N=1` 時 `prev_round=absent` ⇒ rc=0 |
| E | B1 blocked；`brief-kind: closure` 開閉合輪 | **不擋（by design）** | 邊界 ① |
| F | B1 blocked 且鍵在 `verdictgate_baseline.txt`；開 B2 | **放行（by design）** | ASSERT `baseline=present THEN rc=0` |
| G | 某家對所有票永久 `blocked`、永不 `CLOSED:` | **擋得住＝全線停** | 不是繞過；是 brief assumed 的 DoS 面。SPEC「不數人頭」未給挑戰／升格機制 |

**序列 A 是本輪 P0**：實作者若照 Task 2.2 字面實作，會在實作批用「下一輪改 proceed」合法清空閘，重現今日跨批帶傷前進。

---

## 必答 3：Task 3.2 `Ticket-Batch: small` 拆 commit 繞過

**現文判準**：單次 commit、staged 含生產路徑時，`small` ⇒ 檔數 ≤3 且 basename 不含 `factories.py|protocols.py|config.py`。

| 繞過 | 結果 |
|---|---|
| 連續 N 個 `Ticket-Batch: small`，每個 ≤3 個 `momentum/*.py` | **擋不住** — 每 commit 獨立過閘；9 檔＝3 commit，全程無 `impl.<root>-bN.token`、不觸 `verdictgate_check` |
| 大改動中把 `config.py` 單獨一 commit 走 `<root>/bN`，其餘 `small` | **部分擋** — 僅含三膨脹檔之名的那次需 token；其餘生產檔仍 `small` |
| 改名／新檔避開三個 basename（例 `config_settings.py`） | **擋不住 basename 字面** |
| 單 commit >3 生產檔或直接碰三檔 | **擋得住**（ASSERT files=5） |
| 只改 `docs/` | **不要求 trailer**（ASSERT；治理票可無 batch） |

**我認為做得到的最強判準（仍機械）**：
1. `origin/main..HEAD` 內所有 `Ticket-Batch: small` 且觸及生產路徑的 commit，**累計 unique 生產檔 ≤3**（Task 3.3 已遍歷該 range，可重用）；超出 ⇒ 拒 push／拒新 `small`。
2. 若存在未過期 `impl.<root>-bN.token` 或 audit 有未閉合 ticket batch，禁止再標 `small` 碰同 root 生產樹。

**做不到的部分**：無法在無語意審查下證明「多個 small 是否同一功能」；無法防蓄意 `--no-verify`（已 §N）。現文 per-commit ≤3 **不足以**承擔 Phase 3「領權限才改生產碼」目標 ⇒ **P1-02**。

---

## 必答 4：Task 2.1 legacy 字面表全庫實跑

**命令**：`python3 /tmp/verdictgate-grok-r1/scan3.py`（區域＝`VERDICT:` 行，否則 `## Verdict` 至下一 `##`／空段；**blocked 字面優先**於 proceed 字面；腳本已隨 workdir 清理，下方數字為當次 stdout）

**語料**：`handoffs/*-review-*-{codex,composer,grok}.md` → **629** 檔（與偵察 628 差 1，屬 glob 邊界，不影響誤判機制）。

| 類別 | 數量 |
|---|---|
| blocked | 28 |
| proceed | 107 |
| unknown | 460 |
| none（無 Verdict 區） | 34 |
| 同區同時命中 blocked+proceed 字面（BOTH） | 23 |

**範本三值 × 表**：
- `可派工` → **不在** proceed 字面（表為 `可進|可收票|…`）⇒ 本掃描 **22 unknown / 6 proceed**
- `需修補後派工` → **110 unknown / 10 blocked / 7 proceed**

**誤判（對人類「不可進／需修補擋跨批」金標）**：

| 類型 | n（本掃描） | 機制 | 例 |
|---|---|---|---|
| **blocked → proceed** | ≥5＋金標 | 條件句含 `可進`、無 `不可進\|不可收票\|不可直接進` | `20260910-evtlabel-b1-review-r1-codex.md`：`需修補後派工（…可進 B2 前不得帶著兩項 P1）` → **proceed** |
| **blocked → proceed** | 2 | 區內有 `CLOSED` 字樣、無 blocked 三字組 | `20260821-gap3-b4-review-r3-codex.md` |
| **blocked → none** | 1（金標） | 檔首寫「不可進 B-D4」、**無** `## Verdict` 標題 | `20260905-gap3d2-b3-review-r1-codex.md` → **none** |
| **可進 → blocked** | 0（本區域＋blocked-first） | — | — |
| EVTLABEL B3 grok | 正確 blocked | 含 `不可直接進` | `20260910-evtlabel-b3-review-r1-grok.md` |

**對 Task 2.1 驗證句的直接衝擊**：驗證要求基準含 `EVTLABEL b1:codex`、`GAP3D2-b3:codex`。依現文字面表＋Verdict 區域：前者 proceed、後者 none ⇒ **freeze 無法從 parser 產出這兩鍵**（除非另寫死白名單——SPEC 未授權）。BOTH 23 份若改 proceed-first 會整批翻轉——SPEC **未定優先序**。

（若把掃描窗放到 RECHECK／正文，`CLOSED` 假 proceed 會再膨脹；根因相同：字面表≠範本三值，且 `可進`／`CLOSED` 多義。）

---

## 必答 5：Phase 依賴

| 題 | 立場 |
|---|---|
| Phase 4 依賴 Phase 1 而非 Phase 2？ | **對**。Task 4.1 消費 `disposition_values`／finding ID 契約（Phase 1），不讀跨批 `verdictgate_check`。 |
| Phase 3 依賴 Phase 2 必要？ | **對 Task 3.1 必要**（必須呼叫 `verdictgate_check`）。Task 3.2／3.3 的 trailer／檔數邏輯可與 Phase 2 **技術並行**；現文整包「Phase 3 依賴 Phase 2」是切批方便，不是 3.2 的資料依賴。 |

---

## 必答 6：§N 三條殘留

| 殘留 | 是否真「已定義他處／現階段不可能」？ |
|---|---|
| `git push --no-verify` 客戶端繞過 | **成立**（user-ruling 删 CI；客戶端無伺服端鉤子） |
| 決議是否語意處理 finding | **成立**（三家偵察一致；無機械蘊涵） |
| 舊產出不強制 `VERDICT:` | **成立**（面向未來）；**但** Task 2.1 字面表必須修到能凍金標鍵——那是 Task 內缺陷，**不是**把殘留收回成新 Task |

本輪**不**把任一 §N 標成「其實做得到」的 P1。

---

## 必答 7：可否生成 TODO？

**否（blocked）**。骨架可寫 TODO 草稿，但 Phase 2 開工前必須先修 P0-01／P1-01／P1-02，否則實作批會：(1) 用 proceed 空清 blocked；(2) 基準缺 EVTLABEL／GAP3D2 鍵或靠手塞；(3) small 拆 commit 繞過領權限。

---

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
