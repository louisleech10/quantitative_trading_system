# SPLITUNIFY b9 — review-r17 共識決 ＋ D-002 v17 重簽 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R17`  
**family**: composer  
**findings-round**: R17  
**審查標的**: v16→v17 diff `0908ffad`；current block＝`Task 9.3` 驗收第 5 點（收窄兩段式判準＋`SU-RESID-C5-TARGETS`）、`C5-25` 一列  
**禁改碼**：review-only；戳記 append 除外。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 無錨列 19 | **fact-verified** | `awk` 掃 register 29 列：`anchor=1` 共 **10** 列、`anchor=0` 共 **19** 列（`/tmp/r17-register-scan.tsv`） |
| brief fact-verified: mutation 40／ID 01–40 連續／register 29 | **fact-verified** | `awk` 計數 mutation 表 **40** 列、ID 01–40 無缺口；register **29** 列 |
| brief fact-verified: doc_format rc=0 | **fact-verified** | `bash scripts/doc_format_precheck.sh` 兩檔 **rc=0** |
| brief assumed: HANDOFF.md:32 適用且足以解消分歧 | **fact-verified（本輪）** | TODO L665-667 已逐字引用該裁定於本爭點；見必答 2 |
| brief assumed: basename 判準封閉可執行 | **推翻（部分）** | 19 個 no-anchor 列中 **15** 列消費面無 `.py`/`.tsx`/`.json` 字面 ⇒ basename 對該 15 列不可執行（見必答 3、`COMPOSER-R17-P1-01`） |
| brief assumed: `C5-25` seam `ic_feed.py:56-65` 正確 | **fact-verified** | 實讀 `ic_feed.py:56-65`＝`rows` 組裝＋雜湊；`pipeline.py:406-408`＝caller；行號 ≤ 檔案總行數 |

---

## 必答 1 — 共識決：進 Task 9.1 還是先補 TARGETS

### (1a)

**`PROCEED`**（進 `Task 9.1` 實作；**不**先補齊 20 列 `TARGETS:`）。

理由（委員會共識決，不再交使用者）：
1. r15 停輪判準之「register 錯配」＝**mutation 欄 ID 指錯或條數不一致**（R14 已窮舉 `C5-01`..`29`；本輪四項 fact-verified 皆通）。「落點欄不足以支撐 receipt 閘」**不屬**該狹義，屬 receipt 腳手架缺口。
2. `HANDOFF.md:32`（2026-09-12 定）逐字：「不再擴建治理工具；同型缺陷降級為具名殘留。」v17 已將「補 20 列精確 `TARGETS:`」降級為 **`SU-RESID-C5-TARGETS`**（`blocked-by`），並以 10 keyed ＋ 19 basename 兩段式收窄——此為該裁定之直接適用，足以解消 r16 三家歸類分裂。
3. 維持 r16 composer 立場：此為 P2／治理腳手架字面，非停輪級 register 錯配。

### (1b)

若本結論錯（應 `FIX-FIRST`），爆掉形式：**`Task 9.3` register-rescan receipt 以模組名占位碼證全過 basename 閘，但與實際消費面無對應，產品 impl 在錯誤假設下開工。**

可執行觀測（寫 receipt 後跑）：

```bash
python3 - <<'PY'
import re, pathlib, os
spec = pathlib.Path("docs/SPLITUNIFY_SPEC.D-002.md").read_text()
no_ext = []
for line in spec.splitlines():
    m = re.match(r'\| `(C5-\d+)` \| (.+?) \|', line)
    if not m: continue
    cid, cons = m.group(1), m.group(2)
    keyed = bool(re.search(r'\.(?:py|tsx|ts|json):[0-9]', cons))
    if keyed: continue
    if not re.search(r'\.(?:py|tsx|ts|json)', cons):
        no_ext.append(cid)
# 模擬：15 列全填 tests/momentum/Analysis/test_splitunify_derive.py:1
bn = "test_splitunify_derive.py"
fail = [c for c in no_ext if bn not in spec.split(f"`{c}`")[1].split("|")[0]]
print("no_ext_rows", len(no_ext), no_ext)
print("basename_fail_if_proof_is_derive", len(fail), fail)
PY
```

期望：輸出 `basename_fail_if_proof_is_derive 15 [...]`（15 列 FAIL）——證明現行 basename 閘對多數 no-anchor 列仍不可執行，但 receipt 其他檢查可讓其「假過」。

**若本立場未被採用，最該保留成具名殘留**：`SU-RESID-C5-TARGETS` 須附**機械觸發條件**（見必答 4b），不得無限期 `blocked-by`。

---

## 必答 2 — HANDOFF.md:32 適用範圍

### (2a)

**適用。**「為 `Task 9.3` 驗收收據閘再補 20 列 `TARGETS:` 錨點」＝ TODO L665 自認之「為驗收收據的閘再補一層腳手架」，與 DOCROT consult 時「不再擴建治理工具」同型（出處：`handoffs/20260912-docrot-x-consult-r1` 新裁定段：治理擠掉主目標三次 ⇒ 同型降級殘留）。v17 收窄＋`SU-RESID-C5-TARGETS` 已按該裁定落地，**足以解消 r16 分歧**（codex 廣義停輪 vs composer／grok 狹義進 impl）。

### (2b)

N/A（本家判適用）。機械分界線（供後續票引用）：

| 類別 | 判準（機械） | 本爭點 |
|------|-------------|--------|
| **擴建治理工具** | 改動**只**為讓 receipt／閘／戳記鏈可執行；需動已戳記 register 並觸發**整輪三家重簽**；**不改** `momentum/`／`frontend/` 產品行為 | 補 20 列 `TARGETS:` ✓ |
| **補既有 SPEC 產品欄位** | 改動描述 `Task 9.x` 施工落點／行為；可隨 impl token 與生產碼同批交付；不需為 receipt 單獨開重簽輪 | `C5-25` v17 具名 seam（產品語意）✓ |

與 r15 停輪判準**不衝突**：r15 管 mutation 錯配／條數；HANDOFF.md:32 管治理腳手架擴建——**後者不觸發停輪回報使用者**，觸發降級殘留。

---

## 必答 3 — basename 判準：無檔名列

### (3a)

**15 列**（19 個 no-anchor 列之子集；消費面文字**完全無** `.py`／`.tsx`／`.ts`／`.json` 字面）：

`C5-01` `C5-02` `C5-03` `C5-04` `C5-05` `C5-06` `C5-07` `C5-08` `C5-09` `C5-10` `C5-11` `C5-12` `C5-20` `C5-22` `C5-24`

**另有 4 列** no-anchor 但消費面**含檔名**（basename 可執行）：`C5-15` `C5-16` `C5-17` `C5-18`。

**另有 1 列計數漂移**：v17 修 `C5-25` 後 keyed 列由 brief 所述 9 → 實測 **10**（見 `COMPOSER-R17-P2-01`）。

### (3b)

**最小處置**（不補 20 列 `TARGETS:`、不阻 `Task 9.1`）——在 `Task 9.3` 驗收第 5 點後增第 6 點字面：

> 對 `SU-RESID-C5-BASENAME-EXCEPT` 白名單所列 **15** 列（`C5-01`..`12`／`20`／`22`／`24`）：碼證須為該列 mutation 欄所掛 `M-SU-D2-NN` 在 §V 應紅欄之**第一個** `tests/…py` 或 `momentum/…py` 路徑（行號須存在且 ≤ 檔案總行數），**不**走 basename 對證。其餘 no-anchor 列（`C5-15`..`18`）仍走 basename。keyed 列（現行 **10** 列）仍走精確 keyed。

可行性：`M-SU-D2-04`→`test_feature_materialization.py`、`M-SU-D2-18`→`test_splitunify_derive.py` 等 §V 已具名，無新腳本。

---

## 必答 4 — `SU-RESID-C5-TARGETS` 觸發條件

### (4a)

**不可執行。**現行字面「`Task 9.3` 開工時 basename 判準出現誤判」未定義：誰判定、何時、何命令、何輸出特徵 ⇒ 殘留可無限期擱置。

### (4b)

可貼進 TODO 之替代觸發條件字面：

> **`SU-RESID-C5-TARGETS` 升級觸發（機械）**：`handoffs/run_receipts/<UTC>-splitunify-task-9.3-register-rescan.txt` 存在且通過 receipt 第 1–4 點後，執行 `Task 9.3` 動工前置之同一套 register 重掃，逐列比對 receipt 之 `<改前分類> -> <改後分類>` 與重掃結果；**任一 `C5-NN` 分類不一致** ⇒ 同一修訂批次須為全 29 列補 `TARGETS:` 欄（codex `CODEX-R16-P1-01` 修法）並觸發 SPEC 重簽；不得以 basename 白名單掩蓋。

---

## 必答 5 — v17 body `d42b3f14…`

### (5a)

**`APPROVED`**（附 `COMPOSER-R17-P1-01`、`COMPOSER-R17-P2-01`、`COMPOSER-R17-P2-02`；不阻領 impl token）。

### (5b)

N/A（非 REJECTED）。

---

## COMPOSER-R17-P1-01

**斷言**: v17 basename 收窄判準對 **15/19** 個 no-anchor 列不可執行——消費面無任何 `*.py`／`*.tsx`／`*.json` 字面，填真實測試路徑之 basename 無法 `grep -qF` 命中，receipt 仍可能假過。

**碼證**: `awk` 掃 register → `/tmp/r17-register-scan.tsv`：`no_fname_in_no_anchor=15`（`C5-01`..`12`／`20`／`22`／`24`）；`docs/SPLITUNIFY_TODO.md:659-660` basename 判準；模擬 `test_splitunify_derive.py` basename 對 15 列全 FAIL。  
CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:96  
MUTATION: 對 `C5-01` receipt 填 `tests/momentum/Analysis/test_splitunify_derive.py:1` 且消費面仍為 `` `receipts.event_level` `` ⇒ basename `grep -qF` FAIL 但檔存在檢查 PASS。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d42b3f14c4e3

[P1] 修法：見必答 3b（`SU-RESID-C5-BASENAME-EXCEPT` 白名單 15 列 ＋ mutation-first-test-path 第 6 點）。可行性：§V 已具名各 `M-SU-D2-NN` 應紅檔，無新腳本。信心度=High。不阻 v17 戳記（與 v17 收窄＋`SU-RESID-C5-TARGETS` 殘留同向）。

---

## COMPOSER-R17-P2-01

**斷言**: `Task 9.3` 驗收第 5 點仍寫「有 path:line 的 **9** 列／其餘 **20** 列」，但 v17 修 `C5-25` 後 register 實測為 keyed **10** 列、no-anchor **19** 列，字面與機械掃描不一致。

**碼證**: `docs/SPLITUNIFY_TODO.md:656-659`（9／20）；`docs/SPLITUNIFY_SPEC.D-002.md:120`（`C5-25` 已含 `ic_feed.py:56-65`）；`/tmp/r17-register-scan.tsv`：`C5-25 anchor=1`；keyed 列＝`C5-13`/`14`/`19`/`21`/`23`/`25`/`26`/`27`/`28`/`29`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#d42b3f14c4e3

[P2] doc-literal-only。修法：將 L656-659 改為「**10** 列 keyed／**19** 列 basename」，keyed 清單加入 `C5-25`。可行性：單次字面替換。信心度=High。

---

## COMPOSER-R17-P2-02

**斷言**: `SU-RESID-C5-TARGETS` 觸發條件「basename 判準出現誤判」無機械觀測，殘留可永久 `blocked-by` 而不升級 `TARGETS:`。

**碼證**: `docs/SPLITUNIFY_TODO.md:667-668`；無對應 `scripts/` 或 `pytest` 節可判定「誤判」。

**來源摘要**: docs/SPLITUNIFY_TODO.md#d42b3f14c4e3

[P2] doc-literal-only。修法：見必答 4b（register 重掃分類不一致即觸發）。可行性：重用既有 `Task 9.3` 動工前置重掃流程，無新腳本。信心度=High。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R16-P2-01,COMPOSER-R16-P2-02

ASSUMPTIONS_VERIFIED: body sha256 `d42b3f14…`；register 29／keyed 10／no-anchor 19／no-filename 15；mutation 40 ID 01–40；`C5-25` seam 56–65 實讀正確；HANDOFF.md:32 適用  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `d42b3f14…`；`bash scripts/doc_format_precheck.sh` 兩檔 rc=0；`awk` register 掃描 → `/tmp/r17-register-scan.tsv`；`python3` basename 模擬 15 列 FAIL  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（`docs/SPLITUNIFY_SPEC.D-002.md` 戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）

STATUS: DONE
