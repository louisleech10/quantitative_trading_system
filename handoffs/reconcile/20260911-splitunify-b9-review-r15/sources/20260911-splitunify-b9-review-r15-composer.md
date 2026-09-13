# SPLITUNIFY b9 — review-r15 U1–U3 閉合再驗證 ＋ D-002 v15 重簽 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R15`  
**family**: composer  
**findings-round**: R15  
**審查標的**: v14→v15 diff `0de1a17f`；current block＝`C5-24`..`29` 五列、`M-SU-D2-35`..`40`、mutation 目錄標題；`Task 9.2a`／`9.3`／`9.4`  
**禁改碼**：review-only；戳記 append 除外。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: mutation 40 列、01–40 連續 | **fact-verified** | `grep -cE '^\| .M-SU-D2-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` → **40** |
| brief fact-verified: §C-9 認領 40/40 | **fact-verified** | `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md \| grep -oE 'M-SU-D2-[0-9]{2}' \| sort -u \| wc -l` → **40** |
| brief fact-verified: register 29 列 | **fact-verified** | `grep -cE '^\| .C5-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` → **29** |
| brief fact-verified: `共 **40** 條` 恰一處 | **fact-verified** | `grep -c '共 \*\*40\*\* 條' docs/SPLITUNIFY_SPEC.D-002.md` → **1** |
| brief assumed: R14 五列修補後 register 存量無錯配 | **fact-verified（本輪複驗五列）** | `awk -F'\|' '/^\| `C5-/' …` 對 `C5-24`..`29`：24→`05/37`、25→`38`、27→`39`、28→`—`+blocked-by、29→`40` |
| brief assumed: Task 9.3 receipt 兩條內容對證後無繞過 | **部分成立** | 「全填同值」「占位 path」已堵；「照抄第三欄＋全指同一真實行」仍可過 → `COMPOSER-R15-P2-01` |
| brief assumed: M-37/38/40 應紅測試尚不存在可接受 | **成立** | §V L272＋Task 9.3 §驗證已具名建立責任；impl 前不得宣稱 mutation 網已閉 |

---

## 必答 1 — review-r14 反例閉合（本家＋ brief 表 A）

### (1a) verdict

| finding | 提出方 | verdict |
|---------|--------|---------|
| `CODEX-R14-P1-01`／`GROK-R14-P2-03`（M-35/36 軟包） | codex／grok | **CLOSED** |
| `CODEX-R14-P1-02`／`COMPOSER-R14-P2-02`／`GROK-R14-P2-04`（receipt 閘） | 三家 | **CLOSED**（同值／占位／任意 COMMIT 三洞已堵；同 path:line 殘留見 R15-P2-01） |
| `CODEX-R14-P1-03`／`COMPOSER-R14-P2-01`／`GROK-R14-P1-01`／`GROK-R14-P1-02`（register 五列） | 三家 | **CLOSED** |
| `CODEX-R14-P2-04`（doc_friction_ratio 判準） | codex | **N/A 本家**（見必答 4） |
| `COMPOSER-R14-P2-01` | composer | **CLOSED** |
| `COMPOSER-R14-P2-02` | composer | **CLOSED** |

### (1b) CLOSED 者重跑命令與觀測

**M-35/36 軟包（U2）**  
`grep -n 'in df.columns' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` → L312–313、TODO L545–548 明文「刪欄」與「`in df.columns` 包住 guard」皆須 FAIL；`Task 9.2a` §驗證 L534–535 具名兩測試且要求多 TF fixture。

**receipt 閘（U3）**  
`awk '/^  4\./,/^-/' docs/SPLITUNIFY_TODO.md | head -8` → 含「改前分類須與 SPEC 現況相符」與「碼證須指向真實存在的行」；L639–641 要求 `COMMIT:` 對 audit round-start HEAD。  
探針 `scratchpad/r15-composer/receipt_same_line_bypass.txt`（29 唯一 ID＋照抄第三欄＋全 `docs/SPLITUNIFY_SPEC.D-002.md:96`）→ ID set `diff` rc=0、分類對證 rc=0、path 存在 rc=0（**semantic 垃圾仍過**）。

**register 五列（U1）**  
`awk -F'|' '/^\| `C5-2[4-9]/' docs/SPLITUNIFY_SPEC.D-002.md` → 見 §0 表；`grep -cE '^\| .M-SU-D2-3[5-9]|^\| .M-SU-D2-40' docs/SPLITUNIFY_SPEC.D-002.md` → **6** 新列。

**`COMPOSER-R14-P2-01`（C5-25）**  
`grep 'C5-25' docs/SPLITUNIFY_SPEC.D-002.md` → mutation 欄 `M-SU-D2-38`；L315 WHAT＝餵入端未 `drop_duplicates`。

**`COMPOSER-R14-P2-02`（receipt）**  
v15 第 4 點已落地（見上）；舊「全甲＋`foo:1`」繞過需改前分類逐列對 SPEC 第三欄，不再 PASS。

---

## 必答 2 — `M-SU-D2-01`..`40`「應紅之測試」維度

### (2a)

**零條「有問題的引用」**（不存在且屬 Task 交付物、或尚未開工之具名測試＝可接受狀態，見下）。

| 類別 | ID 範圍 | 說明 |
|------|---------|------|
| 尚未建立、TODO 已具名 | `01`–`03`、`11`、`14`–`17`、`20`–`22`、`24`–`25`、`30`–`34`、`35`–`36`、`39` | §V L272／各 Task §驗證已列 node id；impl 前不得宣稱 mutation 網已閉 |
| 尚未建立、Task 9.3 具名 | `37`、`38`、`40` | 檔存在但**無**對應具名測試（`test_pattern_bridge.py` 11 支、`test_gap3_conditional_ic.py` 8 支、`test_tables.py` 8 支皆無 brief 所述名稱）⇒ **可接受**，建立責任在 Task 9.3 |
| 描述性、將於 Task 9.3 落地 | `04`–`10`、`18`、`19` | 指向檔內「值斷言／綁定測試」描述，非錯引他檔測試 |
| 既有測試可覆蓋（impl 後） | `12` 等 | `test_splitunify_wiring.py` 存在；多 TF 案例屬 Task 9.4 交付 |

**不存在「今日已存在但不會因該破壞而紅」之錯引**：本輪對照現有 `tests/` 與 mutation WHAT，未發現應紅欄指向**錯誤 node id**（例如把 M-39 指到 unrelated 既有測試）。

### (2b) 可重跑對照（零條問題之機械證據）

```bash
# 1) 抽出 40 條應紅欄
awk -F'|' '/^\| `M-SU-D2-/ {gsub(/`/,"",$2); gsub(/^[ \t]+|[ \t]+$/,"",$2); gsub(/`/,"",$3); print $2, substr($3,1,80)}' \
  docs/SPLITUNIFY_SPEC.D-002.md > scratchpad/r15-composer/mutations.tsv

# 2) 具名 pytest node 是否存在（應全為「未建」直到 Task 9.x）
for t in test_assignments_composite_key_unique test_purged_composite_key_unique \
  test_tier_min_test_events_counts_unique_event_ids test_baseline_splits_n_test_into_events_and_samples \
  test_baseline_dict_has_no_legacy_n_test_key test_event_count_conservation; do
  rg -l "def $t" tests/ || echo "MISSING_EXPECTED $t"
done
# 實跑摘要：上述 6 個 node → 全部 MISSING_EXPECTED（符合 §V「測試實際存在之前不得宣稱已閉」）

# 3) M-37/38/40 描述性關鍵字在目標檔零命中
rg -n '唯一側去重|餵入去重|assignments 消費去重' tests/momentum/event_samples/test_pattern_bridge.py \
  tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/event_samples/test_tables.py; echo rc=$?
# → rc=1（零命中＝尚未建，非錯引）
```

---

## 必答 3 — `Task 9.3` receipt 閘（同 path:line 繞過）

### (3a)

**仍可繞過**（窄殘留）：在 v15 第 1–4 點全過後，實作者可提交 29 行唯一 `C5-NN`、每行 `<改前>` 照抄 SPEC register 第 3 欄、`<改後>` 填同值（重掃結論「全未變」時合法）、29 行 `<碼證>` **全部**填同一真實 `docs/SPLITUNIFY_SPEC.D-002.md:96`（或任一存在行），不證明逐條觸碼重掃。

### (3b) 試過的構造與最小加強字面

| 構造 | 結果 |
|------|------|
| 29×`C5-01` | **FAIL**（exact ID set） |
| 29 唯一 ID＋全 `甲 -> 甲`＋`nowhere:0` | **FAIL**（v15 分類／path 對證） |
| 29 唯一 ID＋照抄第三欄＋全 `docs/SPLITUNIFY_SPEC.D-002.md:96` | **PASS**（`scratchpad/r15-composer/receipt_same_line_bypass.txt`） |
| `COMMIT: deadbeef` | **FAIL**（v15 須對 audit round-start HEAD） |

**最小加強（建議 Task 9.3 驗收第 5 點）**：

> 逐列 `<碼證 path:line>` 之 `path` 須為 **repo 內 `momentum/`／`frontend/`／`tests/` 下之 `.py` 或 `.tsx`**（不得為 `docs/`）；且 29 列之 `path:line` **去重計數須 ≥ 8**（或明文禁止「29 列共用同一 path:line」）。任一列違反即 FAIL。

可行性：`test`/`rg` 迴圈即可；不阻擋本輪 v15 規格收斂（P2 記錄）。

---

## 必答 4 — `CODEX-R14-P2-04`（doc_friction_ratio 雙報）

### (4a)

**可接受**。量測進行中由被量測對象單方改判準會污染 DOCROT 實驗；同時報「現行封閉集合」與「codex 加強集合」兩數字、並在 synth 標誠實邊界（指標指錯類病變量不到），符合已蓋章 SSOT。

### (4b)

判準變更權在 **主委＋使用者**（DOCROT epic 收斂後、量測兩輪完整入帳後）；未結束前改集合＝被量測者自行放寬，故 R15 不應改判準字面。

---

## 必答 5 — v15 body `c674086e…`

### (5a)

**APPROVED**（附 **1** 條 P2 殘留：`COMPOSER-R15-P2-01` receipt 同 path:line；一次修訂可關，不阻擋領 `Task 9.1` impl token）。

### (5b)

`Task 9.1` 實作當下最可能先紅：`M-SU-D2-01`／`02`／`03`（summary 鍵、`metadata.split_unify` 值相等、disclosure exact-key）——皆綁 `B9A` producer 揭露面；與 R14 判斷一致。

---

## 必答 6 — impl token 與收斂

### (6a)

**本輪交件後、三家對 `c674086e…` 皆 APPROVED 且 `reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0 後，可領 `Task 9.1` impl token。**

### (6b)

已檢查：R14 本家兩條 P2＋brief 表 A 四簇修補 **CLOSED**；五列 register 複驗；40/40 mutation 與 §C-9 認領；body hash 實跑一致；receipt 三類舊繞過已堵、第四類記 P2。

**收斂判斷：已進入窮舉遞減報酬。** 判準：① R14 已窮舉 `C5-01`..`29` mutation **對應**存量；② R15 新發現僅 receipt **語義**殘留（非 register 錯配、非 ID 缺口）；③ 若 R16 再出「第五列 register 錯配」或「mutation 條數不一致」→ 判未收斂並停輪；若僅 P2 級 receipt 字面 → 允許進 impl 並在 Task 9.3 驗收補洞。

---

## COMPOSER-R15-P2-01

**斷言**: `Task 9.3` receipt 閘 v15 第 4 點之「碼證須指向真實行」仍允許 29 列全部填同一 `docs/SPLITUNIFY_SPEC.D-002.md:<n>`，在改前分類照抄 SPEC 第三欄時可假完成重掃。

**碼證**: `docs/SPLITUNIFY_TODO.md:647-651`（僅驗檔存在與行號範圍）；探針 `scratchpad/r15-composer/receipt_same_line_bypass.txt` → `diff` ID set rc=0、29 行同碼證仍過機械閘。

**來源摘要**: docs/SPLITUNIFY_TODO.md#c674086e5f66

[P2] doc-literal-only。修法：見必答 3b 第 5 點（path 須為源碼樹＋去重計數下限）；可行性＝shell 迴圈。信心度=High。不阻 v15 戳記與 `Task 9.1` 開工。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R14-P2-01,COMPOSER-R14-P2-02

ASSUMPTIONS_VERIFIED: body sha256 c674086e…；40/40 mutation；29 register；五列 register 複驗；receipt 同-line bypass PASS；M-37/38/40 測試缺失為 Task 9.3 預期狀態  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`；grep/awk 計數與五列複驗；receipt 探針 `scratchpad/r15-composer/receipt_same_line_bypass.txt`；`rg` 具名測試存在性掃描  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；v15 body 已由 0de1a17f 引入）

STATUS: DONE
