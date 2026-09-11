# VERDICTGATE SPEC v1 adversarial review — COMPOSER R1

task-id: 20260911-VERDICTGATE-X-REVIEW-R1  
family: COMPOSER  
brief: `handoffs/20260911-VERDICTGATE-SPEC-REVIEW-R1-BRIEF.md`  
findings-round: R1  
review-target: `docs/VERDICTGATE_SPEC.md` v1

## 被當成事實的未驗證假設（§0）

| 假設 | 標記 | 判定 | 理由 |
|---|---|---|---|
| 「一家 blocked 即擋」不會造成全線停擺 | brief 前提 assumed | **未驗**（本輪未跑歷史 blocked 比例） | 機制上單一家永久 `VERDICT: blocked` 且永不 `CLOSED:` 可阻斷所有跨批；屬治理風險非 SPEC 缺陷，見必答 2 序列 6 |
| legacy 字面表可穩定推導 621 份舊產出 | SPEC Task 2.1 隱含 | **不成立** | 全庫 628 份實跑：至少 46+15 份 false proceed、10 份 false blocked（見必答 4／P1-01／P1-02） |
| `git interpret-trailers` `--amend` 行為 | brief「我沒查」 | **未驗** | 不列 blocking；Task 3.2 邊界 ① 已聲明 amend 沿用 trailer |

---

## 必答 1：偵察輪 COMPOSER finding 落實對照

| 偵察 ID | SPEC 落點 | 落實？ | 說明 |
|---|---|---|---|
| **COMPOSER-R1-P0-01**（G-1 前置） | Phase 1 Task 1.1＋1.2；§P 順序 | **已落實** | `governance_verdicts.json`＋`register-output` fail-closed；§A 引用 628/8 份 `VERDICT:` 統計 |
| **COMPOSER-R1-P1-01**（debt_clear／開輪第三路） | Phase 2 Task 2.2；C-3 | **已落實** | `committee_run.sh` mint 前＋`gate.sh dispatch` 派 review 前呼叫 `verdictgate_check.sh`；只計無後續 `closed` 的 blocked；§A FACT 收錄 GAP3D2／EVTLABEL audit |
| **COMPOSER-R1-P1-02**（F5 樣本／範本≠契約） | Phase 1 Task 1.2；§A FACT-RECEIPT | **已落實** | 全庫 awk 計數寫入 §A；`register-output` 拒收無 `VERDICT:`，非只改範本散文 |
| **COMPOSER-R1-P2-01**（`--no-verify` 第二層） | Phase 3 Task 3.2＋3.3；§N 殘留 | **已落實** | commit-msg fail-closed＋`gov_check 1c` 補 `--no-verify`；`git push --no-verify` 具名 §N user-ruling |
| **COMPOSER-R1-P2-02**（G-4 語意上限） | Phase 4 Task 4.1；§N 殘留 | **已落實** | 群集必列＋quote20＋`disposition_values`；語意蘊涵列 §N needs-research |

---

## 必答 2：Task 2.2「一家 blocked 且無 closed」繞過序列

| # | 構造序列 | 擋得住？ | 為什麼 |
|---|---|---|---|
| 1 | B2 R1 codex `VERDICT: blocked`＋`BLOCKED-BY: CODEX-R1-P1-01`；B3 同批 closure codex `CLOSED: CODEX-R1-P1-01` | **擋得住（放行）** | Task 2.2 查同家後續 `closed`；C-3 合法 GAP-3 型序列 |
| 2 | B2 R2 codex blocked；B3 codex `DEGRADE`／缺席；B3 composer 寫 `CLOSED: CODEX-R1-P1-01` | **擋得住** | Task 1.2 拒收他族 CLOSED ID；blocked 未閉合 |
| 3 | B2 三家皆 blocked、皆無 closure；B3 開下一批 review | **擋得住** | 「一家 blocked 即擋」；`verdictgate_check` rc=1 |
| 4 | B2 blocked 且 ID 在 `verdictgate_baseline.txt` | **擋得住（放行）** | ASSERT `baseline=present THEN rc=0`（C-4 歷史豁免） |
| 5 | B2 blocked；`brief-kind: closure` 開閉合輪 | **擋得住（放行）** | Task 2.2 邊界 ① 閉合輪不受擋 |
| 6 | 同批 B2c R3 blocked（非跨批） | **不擋（by design）** | 邊界 ② 同批內迭代不算跨批 |
| 7 | 某家對所有票永久 `blocked`、永不 CLOSED | **擋得住** | 全線無法跨批；**否證風險＝治理 DoS**，非繞過；SPEC 未要求人頭門檻 |
| 8 | B3 `debt_clear` 後 `committee_round_open` B4（GAP3D2 實例） | **擋得住（若 2.2 落地）** | 現況漏洞在開輪未讀裁決；SPEC 2.2 掛 `committee_run` mint 前。`debt_clear` 本身仍不讀裁決，但下一輪開啟會被擋 |

---

## 必答 3：Task 3.2 `Ticket-Batch: small` 繞過

**最強可行判準（SPEC 現文）**：單次 commit staged 生產碼 ≤3 檔且路徑不含 `factories.py|protocols.py|config.py`。

| 繞過 | 可行性 | 說明 |
|---|---|---|
| 連續多個 `small` commit（每 commit ≤3 檔） | **高** | 每 commit 獨立過閘；10 檔改動＝4 commit，無累計上限 |
| 拆成多 commit 各 3 檔，其中一批含 `config.py`、其餘 `small` | **高** | 含 config 那 commit 必走 `<root>/b<N>` token；其餘仍 `small` |
| 只改 `docs/`／`tests/` 避開生產碼路徑 | **高** | ASSERT `staged=docs` trailer absent rc=0；治理改動可無 batch |
| 單 commit 4 檔其中 1 個 `momentum/x.py` | **擋** | ASSERT files=5（實為 >3）rc!=0 |
| **做不到的部分** | — | 無法在**單次** commit 塞 >3 生產檔或碰三個膨脹信號檔仍用 `small`；無法無 token 冒充 `<root>/b<N>`（token 檔＋900s） |

**建議（非本輪 blocking）**：若需限制「票級」改動量，須另計 rolling 檔數／行數或綁 task-id，超出 `small` 字面判準。

---

## 必答 4：Task 2.1 legacy 字面表全庫實跑（628 份）

**命令**：`python3 /tmp/verdictgate-composer-r1/legacy_scan4.py`（模擬 Task 2.1：`## Verdict` 區塊，否則 tail40；blocked 字面優先於 proceed 字面）

**分布**：blocked=43，proceed=301，unknown=284。

| 誤判類型 | 數量 | 機制 | 代表例 |
|---|---|---|---|
| **blocked 被判 proceed**（`需修補後派工`＋區塊內 `CLOSED`） | **46** | `CLOSED` 命中 proceed 字面、未命中 blocked 三字組 | `20260821-gap3-b4-review-r3-codex.md` |
| **blocked 被判 proceed**（條件式「可進…前不得」） | **15** | `可進` 命中、無 `不可進｜不可收票｜不可直接進` | `20260910-evtlabel-b1-review-r1-codex.md` L21「可進 B2 前不得帶著兩項 P1」 |
| **blocked 被判 proceed**（開頭摘要有 `不可進`、區塊未含） | **2** | 無 `## Verdict` 用 tail40 丟失開頭 | `20260905-gap3d2-b3-review-r1-codex.md` L2「不可進 B-D4」 |
| **可進被判 blocked**（閉合輪同區塊既有 `不可進`＋`CLOSED`） | **10** | blocked 優先 | `20260826-gap3ux-b4-review-r3-grok.md` |
| **三值 `可派工` 被判 blocked** | **0** | — | — |

**合計**：false proceed **63**（46+15+2，互斥分類）、false blocked **10**。不改 Task 2.1 演算法即上線 ⇒ Phase 2 基準 under-block 63 鍵、over-block 10 鍵，2.2 對新票判定亦繼承誤差。

---

## 必答 5：Phase 依賴

| 問題 | 立場 |
|---|---|
| Phase 4 依賴 Phase 1 而非 Phase 2——對嗎？ | **對**。Task 4.1（attribution／disposition）只需 finding ID 穩定（Phase 1 範本＋register-output），不需跨批 verdict 閘。 |
| Phase 3 依賴 Phase 2——必要嗎？ | **部分必要**。Task 3.1 `--impl-self` 必須呼叫 `verdictgate_check`（2.2）⇒ 硬依賴。Task 3.2 commit-msg **可與 Phase 2 並行**（只驗 token／檔數，不讀 audit verdict）；現文統一「Phase 3 依賴 Phase 2」為實務切批順序，非技術硬耦合。 |

---

## 必答 6：§N 三條殘留

| 殘留 | 判定 | 說明 |
|---|---|---|
| `git push --no-verify` 客戶端繞過 | **成立** | user-ruling 2026-08-13 刪 CI；客戶端無法擋 |
| 決議語意是否處理 finding | **成立** | 無機械蘊涵判準；Task 4.1 已明示不驗 |
| 舊產出不回溯 `VERDICT:` | **成立** | user-ruling＋Task 2.1 legacy；但 legacy 表誤判率高（必答 4）⇒ 應修表非收回殘留 |

**其實現階段可做**：無——三條殘留理由成立；legacy 問題應在 Task 2.1 內修演算法，非改 §N。

---

## 必答 7：可否據此生成 TODO？

**可**，結構完整（§P 四 Phase、ASSERT 文法、§V mutation、§R 回退）。**但 Phase 2 開工前須先修 Task 2.1 legacy 規則**（見 P1-01／P1-02），否則基準與 2.2 判定失真。

---

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
