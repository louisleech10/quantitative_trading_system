# SPLITUNIFY b9 — review-r13 三條閉合再驗證 ＋ D-002 v14 重簽（DOCROT 成效量測第二輪）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R14`  
**family**: composer  
**findings-round**: R14  
**審查標的**: `docs/SPLITUNIFY_SPEC.D-002.md` 之 `C5-20`／`C5-21`、`M-SU-D2-35`／`36`、mutation 目錄標題；`docs/SPLITUNIFY_TODO.md` 之 `B9D`、`Task 9.2a`／`9.3`；diff `9ec33871`  
**禁改碼**：本輪只產 review 檔；戳記 append 除外。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: mutation 36 列、01–36 連續 | **fact-verified** | `grep -cE '^\| .M-SU-D2-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` → **36**；`seq -f '%02g' 1 36` 與 `grep -oE 'M-SU-D2-[0-9]{2}'` 逐號比對無缺 |
| brief fact-verified: §C-9 認領 36/36 | **fact-verified** | `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md \| grep -oE 'M-SU-D2-[0-9]{2}' \| sort -u \| wc -l` → **36** |
| brief fact-verified: register 29 列 | **fact-verified** | `grep -cE '^\| .C5-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` → **29** |
| brief fact-verified: doc_format_precheck rc=0 | **fact-verified** | 兩檔皆 rc=0（brief 已列；本輪未重跑差異） |
| brief assumed: M-SU-D2-35/36 之 KeyError 路徑 | **部分成立** | `python -c '…duplicated(subset=[...])'` 缺欄確為 `KeyError`；但 production／test 可用 `in columns` 靜默跳過（見必答 3） |
| brief assumed: 僅 C5-20/21 錯配、其餘 27 列未查 | **已攻** | 本輪逐列核對（見必答 2）；發現 **1** 列錯配（`C5-25`，非本輪 diff 引入） |

---

## 必答 1 — review-r13 反例閉合（composer 本家）

### (1a) verdict

| finding | 提出方 | verdict |
|---------|--------|---------|
| `CODEX-R13-P1-01` | codex | **CLOSED** |
| `CODEX-R13-P1-02` | codex | **CLOSED** |
| `CODEX-R13-P2-03` | codex | **CLOSED** |
| 主委自產 `C5-21`→`M-SU-D2-36` | 主委 | **CLOSED** |
| composer review-r13 本家 finding | composer | **N/A**（R13 為 `COMPOSER-R13-P3-00` 零 finding，無本家反例可重跑） |

### (1b) CLOSED 者重跑命令與觀測

**`CODEX-R13-P1-01`**  
`grep -n '| `C5-20`' docs/SPLITUNIFY_SPEC.D-002.md` → 第 115 行 mutation 欄為 `` `M-SU-D2-35` ``（非 `M-SU-D2-20`）。  
`grep -n 'M-SU-D2-35' docs/SPLITUNIFY_SPEC.D-002.md` → 第 312 行 mutation 表具名「assignments 組裝時**不寫** `feature_timeframe` 欄」。

**`CODEX-R13-P1-02`**  
`awk '/register 重掃 receipt/,/在上表測試實際存在之前/' docs/SPLITUNIFY_TODO.md | head -12` → 含「exact ID set」「`diff <(…) <(…)` rc=0`」「**不得**改用 `wc -l`」與 TASK／COMMIT 首兩行要求。  
繞過探針：`scratchpad/receipt_dup.txt` 寫 29 行全為 `C5-01` → `sed -n '3,$p' … \| grep -oE '^C5-[0-9]+' \| sort -u` 僅 **1** 個 ID，`diff` rc≠0（舊「只比行數」繞過已關）。

**`CODEX-R13-P2-03`**  
`sed -n '67p' docs/SPLITUNIFY_TODO.md` → `B9D` 欄寫「**九處**」並逐列具名七模組＋兩支撐面。  
`awk '/^### Task 9.3/,/^### Task 9.4/' docs/SPLITUNIFY_TODO.md | grep -c '^| `'` → 表內資料列 **9**（與 `B9D` 一致）。

**主委自產 `C5-21`**  
`grep -n '| `C5-21`' docs/SPLITUNIFY_SPEC.D-002.md` → 第 116 行 mutation 為 `` `M-SU-D2-36` ``；第 313 行 mutation 表描述 purged 不寫欄，與 `M-SU-D2-24`（purge 逐列判定）分離。

---

## 必答 2 — register 逐列 mutation 對應

### (2a)

**錯配列數：1**（其餘 28 列含「—」無 mutation 者視為 intentionally 無專屬 mutation）。

| ID | 現指 | 應指或說明 |
|----|------|------------|
| `C5-25` | `M-SU-D2-19` | **需新增**（建議 `M-SU-D2-37` 或同型編號）：缺陷＝survivor 餵入端**未先去重**即算雜湊；`M-SU-D2-19` 描述的是「六鍵雜湊**含 feature TF**」（對應 `C5-10`），與本列「重複三元組改變雜湊」是不同破壞面 |

其餘 28 列（含 `C5-15`／`16`／`17`／`28` 之 `—`）與 mutation 表「改壞什麼」一致；`C5-20`／`C5-21` v14 修補後指向 `M-SU-D2-35`／`36` 成立。

### (2b) 逐列對照命令（可重跑）

```bash
awk -F'|' '/^\| `C5-/ {
  gsub(/`/,"",$2); gsub(/^[ \t]+|[ \t]+$/,"",$2);
  gsub(/`/,"",$4); gsub(/^[ \t]+|[ \t]+$/,"",$4);
  gsub(/`/,"",$7); gsub(/^[ \t]+|[ \t]+$/,"",$7);
  print $2, $4, $7
}' docs/SPLITUNIFY_SPEC.D-002.md
```

本輪將上式輸出與 mutation 表各 ID 之「改壞什麼」逐字對照；僅 `C5-25`（丙類「先去重再算雜湊」）與 `M-SU-D2-19`（「雜湊含 TF」）語意不交疊。`C5-29` 與 `C5-13` 共用 `M-SU-D2-06` 屬同一 `tables` 防誤改族，不另列錯配。

---

## 必答 3 — `M-SU-D2-35`／`36`「應紅之測試」欄

### (3a)

**足夠**（對 v14 收斂而言；非完美封死所有實作捷徑）。

### (3b)

`in df.columns` 靜默跳過在**單獨**存在時可讓 production guard 不 raise；但 `Task 9.2a` 要點 (1) 明文要求兩表**各加** `feature_timeframe` 欄，且 §驗證逐字要求 `test_assignments_composite_key_unique`／`test_purged_composite_key_unique` 存在；mutation 自證（TODO `:542-544`）把 `M-SU-D2-35`／`36` 綁到這兩條。實作者若 production 用 `if "feature_timeframe" in df.columns` 跳過 guard，測試仍應對輸出表斷言欄位存在（否則違反要點 1）——雙重靜默才會假綠，已超出合理「照 Task 施工」範圍。  
`venv/bin/python -c 'import pandas as pd; …'` 已證缺欄 `duplicated(subset=[...])` → `KeyError`（與 mutation 表字面一致）。

可選加強（非阻擋）：mutation 表欄可增「測試須先 `assert "feature_timeframe" in …columns`，guard 不得以 `in columns` 包住 `duplicated`」——本輪不強制。

---

## 必答 4 — `Task 9.3` receipt 閘繞過

### (4a)

**仍可繞過**（較 R13 已大幅收緊，但非 intent-complete）。

### (4b) 試過的構造

| 構造 | 結果 |
|------|------|
| 29 行全寫 `C5-01`（舊行數閘） | **FAIL**（unique set 僅 1 個 ID） |
| 29 個唯一 ID 各寫一行，分類全為 `甲 -> 甲`，path 填 `foo:1` | **PASS** exact ID set（`scratchpad/receipt_bypass.txt` + `diff` rc=0） |
| 多寫 `C5-99` | **FAIL**（set 含多餘 ID） |
| `COMMIT: deadbeef` 任意 sha | 機械閘**未驗** commit 與 worktree 一致（僅要求字面存在 + task-id 對 audit） |

最小修補（若下輪要關）：在 receipt 驗收加 (4)「至少一列之 `<改前> -> <改後>` 非恆等 **或** `<碼證 path:line>` 須 resolve 為 repo 內存在檔案」；(5) `COMMIT:` 須等於該 task 開工時 `git rev-parse HEAD` 並寫入 audit 事件。本輪 **P2** 記錄，不阻 v14 重簽。

---

## 必答 5 — v14 body `7455b305…`

### (5a)

**APPROVED**（附 **1** 條 P2 殘留：`C5-25` 錯配為 v13 前既有，非 v14 diff 引入；一次修訂可新增專屬 mutation 關閉）。

### (5b)

`Task 9.1` 實作當下最可能先紅：`M-SU-D2-01`／`02`／`03`（summary 鍵、`metadata.split_unify` 值相等、disclosure exact-key）——皆綁定 producer 揭露面，與 `B9A` 首批一致。

---

## 必答 6 — impl token

### (6a)

**本輪交件後尚不可**；待三家對 `7455b305…` 皆 append APPROVED 且 `reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0 後**可**領 `Task 9.1`。

### (6b)

已檢查：R13 三條 + 主委 `C5-21` 修補 **CLOSED**；body hash 實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `7455b305…`；v13 舊戳記保留時 `reconcile_stamps_check` **正確 FAIL**（雜湊不符），不會误取舊行當通過；`B9A` 前置仍要求 rc=0 新戳記。

最小閉合集合：①三家 v14 戳記 ②（建議下輪）`C5-25` 專屬 mutation ③（可選）receipt 閘 (4)(5)。

---

## DOCROT 第二輪 — `doc_friction_ratio` 與封閉字面集合

- 本輪 canonical finding 預計 **2** 條 P2（≤20 ✓）。
- 兩條碼證均锚 `docs/SPLITUNIFY_SPEC.D-002.md:120`、`docs/SPLITUNIFY_TODO.md:636`，**非** `HISTORY-BEGIN..END`。
- 斷言用詞未命中 r13 集合 `多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張` ⇒ **doc_friction_ratio 機械值＝0/2＝0.00**（與 r13 的 0/5 同級）。
- **r13 `CODEX-R13-P2-03` 判準過窄：是。** B9D「六個」vs 表列九列屬「兩處敘述數量不一致」，未命中現行集合。建議**可直接替換**之擴充集合（仍封閉、可 grep）：

```text
多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張|表列.*不符|與.*表列.*不符|\d+\s*(個|處|列|條).*\d+\s*(個|處|列|條)
```

---

## §B 其餘批次（brief 攻擊面）

| 列 | 結論 |
|----|------|
| `B9A` | 與 `Task 9.1`、依賴 `B4`+戳記 rc=0 一致 |
| `B9B` | 與 `9.2`+`9.2a` 不可拆批敘述一致 |
| `B9C` | 與 `9.2b` 依賴 `9.2a` guard 先後一致 |
| `B9E` | 與 `Task 9.4` 記帳鏈一致 |
| `B9F` | 與 `B9D`+`B9E` 後 golden 一致 |

---

## COMPOSER-R14-P2-01

**斷言**: `C5-25` 之 mutation 欄指 `M-SU-D2-19`，但該 mutation 描述「survivor 六鍵雜湊含 feature TF」，與本列處置「餵入端先去重否則重複三元組改變雜湊」不是同一可紅缺陷。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:120`（register `C5-25`）對照 `:296`（`M-SU-D2-19` 改壞什麼）；`momentum/Analysis/event_samples/ic_feed.py:142-145` 為餵入端雜湊（dedupe 語意），與 TF 入鍵無關。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7455b305c6f3

[P2] doc-literal-only 否（影響 mutation 網覆蓋）。修法：新增專屬 mutation（例：餵入 `keep` 未 `drop_duplicates` 即算 hash）並改 `C5-25` 指向之；可行性＝`ic_feed.py:142-145` 為單一 hash 輸入點。信心度=High。v13 前既有，不阻本輪 v14 三處修補收斂。

---

## COMPOSER-R14-P2-02

**斷言**: `Task 9.3` 新 receipt 閘驗 exact ID set 後，仍可提交 29 行唯一 ID 但分類全為 `甲 -> 甲`、碼證填占位 path，不證明逐條重掃。

**碼證**: `docs/SPLITUNIFY_TODO.md:636-640` 僅要求 ID set 與格式；探針 `scratchpad/receipt_bypass.txt`（29 唯一 ID + 全 `甲 -> 甲`）→ `diff <(grep register IDs) <(receipt IDs)` rc=0。

**來源摘要**: docs/SPLITUNIFY_TODO.md#5738e9c63f6f

[P2] 修法：驗收加「至少一列改前≠改後 **或** path 須為 repo 內存在之檔」；可行性＝`test -f` 迴圈即可。信心度=High。相較 R13 行數閘已關重大繞過，本條為殘留摩擦。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body sha256 7455b305…；36/36 mutation；29 register；R13 三條+主委 C5-21 CLOSED；receipt dup 繞過 FAIL、全甲 bypass PASS；pandas KeyError 路徑  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`；`grep -cE` 計數；receipt 繞過探針（scratchpad）；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=1（預期，待 v14 戳記）；收尾 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r14-composer.md --family composer`  
FAILURES_SEEN: none（stamps_check rc=1 為預期）  
SCOPE_CHANGES: none（戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；v14 body 已由 9ec33871 引入）

STATUS: DONE
