# SPLITUNIFY b9 — review-r17 停輪歸類共識決 ＋ D-002 v17 重簽 — grok

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R17`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R17-BRIEF.md`  
**findings-round**: R17  
**brief-kind**: review  
**審查標的**: `git show 0908ffad` 之 SPEC／TODO diff ＋ current block（`Task 9.3` 驗收第 5 點收窄判準／`SU-RESID-C5-TARGETS`；`C5-25`）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（僅允許 append 戳記）。

---

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: body sha256 → `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` ＝ `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`（與 brief 一致）。

fact-verified: mutation 40 列、ID 01–40 連續 → missing=[]；register 29 列。

fact-verified: `bash scripts/doc_format_precheck.sh` 對 SPEC／TODO 皆 rc=0。

fact-verified: 有 `path:line` 錨列＝**10**（含 v17 之 `C5-25`）；無錨＝**19**。探針：`/tmp/grok-r17-work/basename_scan.txt`。

fact-verified: `C5-25` seam `ic_feed.py:56-65` ＝ `rows` 組裝＋`manifest_hash`；caller `pipeline.py:406-408`；兩檔行號皆 ≤ 檔案總行數（162／807）。

assumed（brief #1）: `HANDOFF.md:32` 適用且足以解消 r16 分歧 → **本輪判適用**（見必答 2）；「治理工具」字面未定義，但「同型缺陷降級為具名殘留」半句＋ TODO 已逐字引用，足以支撐 `PROCEED`＋殘留，不必先補 `TARGETS:`。

assumed（brief #2）: 收窄後 basename 判準仍封閉且有鑑別力 → **部分推翻**：19 無錨列中 **15** 列消費面完全無檔名（見必答 3、`GROK-R17-P1-01`）。

---

## 必答

### (1a)(1b) 共識決：進 Task 9.1 或先補 TARGETS

**(1a) `PROCEED`**（進 `Task 9.1`；**不**先補齊 20／19 列 `TARGETS:`）。

理由（委員會共識決，不再交使用者）：
1. r15 停輪判準之「register 錯配」＝ mutation 欄 ID 指錯或條數不一致。本輪四項 fact-verified 皆通；落點不足以撐 receipt 閘屬**驗收腳手架**，非該狹義。
2. `HANDOFF.md:32`：「不再擴建治理工具；同型缺陷降級為具名殘留。」v17 已把精確 `TARGETS:` 降為 `SU-RESID-C5-TARGETS`（`blocked-by`），並以 keyed／basename 兩段式收窄——此為該裁定之直接適用，足以解消 r16 歸類分裂。
3. 依賴序 `9.1 → … → 9.3`：basename／TARGETS 洞擋的是 `Task 9.3` receipt，不擋 `Task 9.1` 產品實作。

**(1b)** 若本結論錯（應 `FIX-FIRST`），爆掉形式：`Task 9.3` 開工時，15 列無檔名消費面無法以真實 `path:line` 之 basename 通過第 5 點 ⇒ 驗收永久紅，或實作者靜默跳過 basename 檢查造成假綠。

可執行觀測：

```bash
python3 - <<'PY'
import re
from pathlib import Path
text = Path('docs/SPLITUNIFY_SPEC.D-002.md').read_text()
no_bn = []
for line in text.splitlines():
    if not re.match(r'^\| `C5-\d+`', line):
        continue
    parts = [p.strip() for p in line.split('|')]
    cid, face = parts[1].strip('`'), parts[2]
    if re.search(r'[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:[0-9]+', face):
        continue  # keyed
    if not re.search(r'[A-Za-z0-9_-]+\.(?:py|tsx|ts|json|md|sh)', face):
        no_bn.append(cid)
bn = 'test_splitunify_derive.py'
# 模擬：對無檔名列填真實測試路徑後做 grep -qF basename
fail = []
for cid in no_bn:
    for line in text.splitlines():
        if line.startswith(f'| `{cid}`'):
            face = line.split('|')[2]
            if bn not in face:
                fail.append(cid)
            break
print('no_basename_rows', len(no_bn), no_bn)
print('basename_fail_count', len(fail))
PY
```

期望：`no_basename_rows 15 [...]` 且 `basename_fail_count 15`。

**若本立場最後未被採用，最該保留成具名殘留**：`SU-RESID-C5-TARGETS` 須附機械觸發（見 4b），並具名 15 列無檔名例外（見 3b）——不得只留「誤判」散文。

### (2a)(2b) HANDOFF.md:32 是否適用

**(2a) 適用。**「為驗收收據閘再補 `TARGETS:`」＝ TODO 自認之「再補一層腳手架」；與「主目標被治理擠掉」同型。v17 收窄＋殘留已按「降級為具名殘留」落地，**足以解消** r16「停輪 vs 進 9.1」分歧（不必再交使用者）。

**(2b)** N/A（判適用）。仍給可機械套用之界線供後續票引用：

| 類 | 機械判準 |
|---|---|
| **擴建治理工具** | 新增／擴充 `scripts/`／`.claude/`／`templates/` 檢查器，或為讓 receipt／gate／戳記鏈可跑而單獨開重簽輪、且不改 `momentum/`／`api/`／`frontend/` 產品行為 |
| **補既有 SPEC 產品欄位** | 描述 `Task 9.x` 施工落點／行為；可隨 impl token 與生產碼同批交付 |

「補 20 列 `TARGETS:`」落在左欄（為 receipt 閘單獨重簽）⇒ 適用 `HANDOFF.md:32` 之降級殘留處置。與 r15 停輪判準不衝突：r15 管 mutation／條數；本裁定管治理腳手架擴建。

### (3a)(3b) basename 判準：無檔名列

**(3a) 15 列**（19 無錨列之子集；消費面**完全無** `*.py`／`*.tsx`／`*.ts`／`*.json`／`*.md`／`*.sh` 字面）：

`C5-01` `C5-02` `C5-03` `C5-04` `C5-05` `C5-06` `C5-07` `C5-08` `C5-09` `C5-10` `C5-11` `C5-12` `C5-20` `C5-22` `C5-24`

另 4 列無錨但**有**檔名（basename 可執行）：`C5-15` `C5-16` `C5-17` `C5-18`。  
另：keyed 實測 **10** 列（TODO 仍寫 9／20，見 `GROK-R17-P2-01`）。

**(3b) 最小處置**（不補全表 `TARGETS:`、不阻 `Task 9.1`）——在 `Task 9.3` 驗收第 5 點後增一段：

> 對白名單 **15** 列（`C5-01`..`12`／`20`／`22`／`24`）：碼證改對該列 mutation 欄所掛 `M-SU-D2-NN` 在 §V 應紅欄之**第一個**真實 `tests/…py` 或 `momentum/…py` 路徑（檔存在、行號 ≤ 總行數），**不**走 basename `grep -qF`。其餘無錨列（`C5-15`..`18`）仍走 basename；keyed 列（現行 **10**）仍走精確 keyed。並將本白名單具名掛入 `SU-RESID-C5-TARGETS` 觸發前之例外。

### (4a)(4b) `SU-RESID-C5-TARGETS` 觸發條件

**(4a) 不可執行。**「basename 判準出現誤判（receipt 通過但重掃實際未做）」未定義：誰判定、何時、何命令、何 stdout 特徵 ⇒ 殘留可無限期擱置。

**(4b)** 可直接貼進 TODO 之替代字面：

> **`SU-RESID-C5-TARGETS` 升級觸發（機械）**：當 `handoffs/run_receipts/*-splitunify-task-9.3-register-rescan.txt` 存在且通過 receipt 第 1–4 點後，以與 `Task 9.3` 動工前置**同一套** register 重掃命令再跑一次；對每個 `C5-NN` 比對 receipt 之 `<改前分類> -> <改後分類>` 與重掃結果。**任一列分類不一致**，或第 5 點 basename／例外白名單檢查對任一列無法執行（`grep -qF` 目標字面不存在於消費面且該列不在 3b 白名單）⇒ 同一修訂批次須為全部無精確錨列補 `TARGETS: <repo-relative-path>:<start>-<end>`（codex `CODEX-R16-P1-01` 修法）並觸發 SPEC 重簽。判定人＝`Task 9.3` 驗收執行者；判定命令＝上述重掃＋`diff` 分類欄。

### (5a)(5b) v17 body 重簽

**(5a) `APPROVED`**（body `d42b3f14…`）。附本輪 P1／P2；不阻領 impl token 進 `Task 9.1`。

**(5b)** N/A（非 REJECTED）。

---

## 攻擊面補答

| 面向 | 結論 |
|---|---|
| 無檔名列數 | **15**（清單見 3a）；basename 對其不可執行 → `GROK-R17-P1-01` |
| `SU-RESID-C5-TARGETS` 觸發 | 現行不可執行 → `GROK-R17-P2-02`；替代字面見 4b |
| HANDOFF.md:32 vs r15 | 適用；管腳手架降級，不觸發停輪回報 |
| `C5-25` seam | 行號正確（實讀）；`GROK-R16-P2-02` **CLOSED** |
| TODO 9／20 字面 | 與實測 10／19 漂移 → `GROK-R17-P2-01` |

## §1 必查（11 類；範圍＝v17 diff／current block）

1. 矛盾/互斥：TODO「9／20」vs register 實測「10／19」（P2-01）  
2. 漏項：15 列無 basename 落點（P1-01）  
3. 不可測驗收：殘留觸發「誤判」無命令（P2-02）；basename 對 15 列不可執行（P1-01）  
4. 可疑 quant：無  
5. 過度工程：無（收窄＋殘留符合 HANDOFF.md:32）  
6. OOM/並行：無  
7. Cache：無  
8. API/型別：無  
9. 測試品質：無（本輪未動測試契約）  
10. Agent 可執行性：3b／4b 已給可貼字面  
11. 必要性/短命工：無  

## 被當成事實的未驗證假設（§0）

1. 「其餘 20 列可走 basename」——**否證**（15 列無檔名；且 `C5-25` 已入 keyed ⇒ 無錨實為 19）。  
2. 「觸發條件（可執行）」——**否證**（無命令／無觀測特徵）。

---

## GROK-R17-P1-01

**斷言**: v17 basename 收窄判準對 15 個無錨列不可執行——該列消費面無任何檔名副檔名字面，真實碼證之 basename 無法 `grep -qF` 命中，Task 9.3 驗收第 5 點對該 15 列無法完成（或被迫跳過檢查變成假閘）。

**碼證**: 探針 `/tmp/grok-r17-work/basename_scan.txt`：`UNANCH_NO_BASENAME=15`（`C5-01`..`12`／`20`／`22`／`24`）；`docs/SPLITUNIFY_TODO.md:659-660` 要求 basename 出現在消費面；模擬 `bn=test_splitunify_derive.py` ⇒ 15／15 FAIL；對照有檔名之 4 列（`C5-15`..`18`）可執行。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:659
MUTATION: 對 `C5-01` receipt 填 `tests/momentum/event_samples/test_splitunify_derive.py:1` 且消費面仍為 `` `receipts.event_level` `` ⇒ 檔存在檢查可 PASS，但 basename `grep -qF test_splitunify_derive.py` 對消費面 FAIL。

**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c

[P1] 信心度=High。修法＝必答 3b（15 列改對 mutation 應紅測試路徑、不走 basename）。可行性：§V 各 `M-SU-D2-NN` 已具名應紅檔，無新腳本、不需先補全表 `TARGETS:`。不阻 `Task 9.1`；擋的是 `Task 9.3` 第 5 點可完成性。非空殼。

---

## GROK-R17-P2-01

**斷言**: `Task 9.3` 驗收第 5 點仍寫「有 path:line 的 9 列／其餘 20 列」，但 v17 修 `C5-25` 後 register 實測 keyed＝10、無錨＝19，且無錨清單仍含已有錨之 `C5-25`。

**碼證**: `docs/SPLITUNIFY_TODO.md:653-659`（9／20 與清單含 `C5-25`）；`docs/SPLITUNIFY_SPEC.D-002.md:120`（`C5-25` 已含 `ic_feed.py:56-65`／`pipeline.py:406-408`）；探針 `ANCHORED=10` 含 `C5-25`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c

[P2] doc-literal-only。信心度=High。修法：改為「**10** 列 keyed（清單加入 `C5-25`）／**19** 列走 basename 或例外白名單」；殘留文「20 列」同步改 19。可行性：單次字面替換。

---

## GROK-R17-P2-02

**斷言**: `SU-RESID-C5-TARGETS` 觸發條件「basename 判準出現誤判」無機械觀測（無執行者／無命令／無輸出特徵），殘留可永久 `blocked-by` 而不升級 `TARGETS:`。

**碼證**: `docs/SPLITUNIFY_TODO.md:667-668`；repo 內無對應 `scripts/` 或 pytest 節可判定該「誤判」。

**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c

[P2] doc-literal-only。信心度=High。修法＝必答 4b（重掃分類不一致或 basename 不可執行即觸發）。可行性：重用 `Task 9.3` 動工前置重掃，無新治理腳本。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R16-P2-01,GROK-R16-P2-02

ASSUMPTIONS_VERIFIED: body sha `d42b3f14…`；mutation 40 連續；register 29；keyed 10／無錨 19／無檔名 15；`C5-25` seam 56-65 實讀正確；doc_format 雙綠；HANDOFF.md:32 適用 → PROCEED
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `d42b3f14…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；python basename 探針 → 15 no-filename／basename_fail=15；`wc -l ic_feed.py pipeline.py` → 162／807
FAILURES_SEEN: none
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅 append APPROVED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r17-grok.md

STATUS: DONE
