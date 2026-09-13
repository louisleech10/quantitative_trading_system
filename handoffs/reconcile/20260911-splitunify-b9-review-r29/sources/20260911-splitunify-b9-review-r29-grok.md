# SPLITUNIFY b9 — review-r29（N1–N4 閉合再驗證 ＋ v23 重簽）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R29`  
**family**: grok  
**findings-round**: R29  
**brief-kind**: review  
**審查標的**: commit `ddcd66f3`；current block＝N1–N4（`handoffs/reconcile/20260911-splitunify-b9-review-r28/synth.md`）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六路 732 passed | **fact-verified（子集）** | 本輪 `derive`＋`wiring`＋`golden` → **140 passed**；全六路未重跑（brief VERIFY-EXEMPT） |
| brief fact-verified: doc_format 兩份 rc=0 | **fact-verified** | SPEC／TODO 各跑一次 → 皆 rc=0 |
| brief fact-verified: 主委四探針 | **fact-verified（本家重跑）** | 見必答 1b；輸出特徵與 brief 相符 |
| brief fact-verified: r28 `state=CLOSED` | **fact-verified** | `debt_ledger.sh --list \| grep review-r28` → `state=CLOSED` |
| brief fact-verified: body `52efba2e…` | **fact-verified** | `reconcile_body_hash.sh` → 逐字相符；append 戳記後 hash **不變** |
| brief assumed 1: N1 顯式具名 ≡ 任一值改即拒 | 見必答 3① | |
| brief assumed 2: N3 第二欄已消除共因 | 見必答 3② | |
| brief assumed 3: N2 SPEC 錨縮小攻擊面 | 見必答 3③ | |
| brief assumed 4: N4 已窮盡同型 | 見必答 3④／必答 4 | |

---

## 必答 1 — 重跑本家 review-r28 反例（§B8）

### (1a)

本家 review-r28 為**零 finding**（`GROK-R28-P3-00` sentinel），**無**可重跑之 P0／P1／P2 反例 ID。

| 項目 | 判定 |
|------|------|
| 本家 r28 finding 反例 | **N/A（零 finding）** |
| brief 要求之四探針（N1–N4 閉合驗證） | **CLOSED**（見 1b） |

### (1b)

```text
# 探針① N1：未具名改既有鍵值 → 拒
# （閘邏輯複現：prev vs payload，g4_per_symbol_n→{"ETHUSDT":999}，allowed=∅）
CASE1_unauth ['g4_per_symbol_n']  CASE1_would_refuse True

# 探針② N2：拿掉 SPEC §V 錨點行 → ANCHOR MISSING
venv/bin/python scripts/freeze_splitunify_golden.py
# → rc=1
# GOLDEN V8 ANCHOR MISSING: SPEC §V 缺（或有多於一個）逐字 `V8_BASELINE_SHA256=<64-hex>`…
# （還原後 body hash 仍 52efba2e…）

# 探針③ N2：對已存在 v8 再 create_v8_baseline_write_once
# → writeonce_existing_rc 1
# GOLDEN V8 REFUSE: splitunify_golden.v8.json 已存在——v8 基準是 write-once…

# 探針④ N3：每列 decision_at_ms +1 ms
# → plus1_mismatch_count 13；plus1_would_fail_g4e True
# 例：tr0 人手=1700000000000 實際=1700000000001
```

---

## 必答 2 — v23 body 重簽

### (2a)

**APPROVED**（body `52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d`）。

戳記已 append（舊行保留）：
`RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d task:20260911-SPLITUNIFY-B9-REVIEW-R29`

### (2b)

N/A（未 REJECTED）。

---

## 必答 3 — 四條 assumed

### (3a)

① **N1「顯式具名」與 codex「任一值改變即 fail-closed」等效** → **不成立（字面不等效）**；**就「靜默改值」攻擊向量則機械閘有效**。

- 字面：codex 原修法＝任何既有鍵值變動一律拒；現行＝須 `--accept-value-changes` 逐一具名才放行。主委偏離理由成立（「永遠不得改」會讓正當重凍——如新增 `bnd_shift`——不可實作）。
- **習慣性列全鍵繞法**：本家複現——只改 1 鍵卻把全部 15 個既有鍵塞進 allowlist ⇒ `_stale_allow` 拒（`CASE2_would_refuse_stale True`）。未具名改值亦拒（探針①）。
- **誠實邊界**：若某次重凍**真的**改了全部既有鍵、且命令列逐一具名那些已變鍵，該次 write 等價於「全量授權」——這是正當重凍路徑的上界，不是靜默繞法。不升級為 finding。

② **N3 第二欄人手判準已消除共因** → **部分成立**。

- **已關**：`decision_at_ms` 整批 +1 ms、側別不變 ⇒ 探針④ 13 筆時刻對帳全紅（r28 攻擊向量已關）。
- **殘餘共因**：`_hand_decision` 與 `_feature_index()` 仍共用 `BASE`／`H1`（`:57-58`、`:146-151`）。本家把 `BASE += H1` ⇒ G-4e 時刻對帳仍綠（`BASE_shift_g4e_time_still_green True`），但對照凍結主檔出現 **5** 個頂層鍵差異（含指紋與人手／實際時刻表）⇒ 正常模式會 `GOLDEN MISMATCH`，意圖性大修仍須 `--write`＋逐鍵具名，**非靜默放行**。腳本 `:139-144` 已具名此限。不升級為 finding（與「人手同錯仍綠」同屬散文／fixture 常數紀律）。

③ **N2 錨點移入 SPEC 後攻擊面縮小** → **部分成立**。

- **改善**：`grep V8_BASELINE_SHA256 scripts/freeze_splitunify_golden.py` 僅 regex／訊息字串、**無賦值常數**；缺錨探針② rc=1；write-once 探針③ rc=1；臨時目錄複現首次 `O_CREAT|O_EXCL` 成功、第二次 `FileExistsError`。
- **未消**：同一 commit 仍可同時改 SPEC 錨行＋v8 檔＋旁檔。相對 r27「改 helper 常數」多了「SPEC diff 可見 64-hex」與三層 digest／write-once，攻擊面**變小但非零**。不足以擋 B9D。

④ **N4 修補已窮盡該類** → **成立（審查範圍內）**。必答 4 自立詞表無第九處 live 互斥。

### (3b)

① **第三種形狀（可落地、非本輪必做）**：維持顯式具名（已滿足「擋靜默改值」＋「正當重凍可進行」）；可選強化為 `--accept-value-changes KEY:<prev_json_sha12>`，使「只抄鍵名、不核對舊值」也拒——本輪**不**列 finding，因 `_stale_allow` 已否證「習慣性列全鍵」繞法。  
② 可選：把 `_hand_decision` 改成**字面整數**（不引用 `BASE`／`H1`）以斷開下一層共因——本家探針證實字面表在 `BASE` 移位時會 13／13 轉紅；屬 golden helper 強化，**不阻擋** B9D。  
③④ 無需修法。

---

## 必答 4 — 契約面強制掃描（同型第九次）

### (4a)

**本家詞表**（🔴 刻意不用主委／composer r29 之 `train_cutoff|per-cutoff|不在.*index.*purged` 主幹；亦避開 r28 之 `集合成員／SUPERSEDED／feature_cutoff_ms ∈`）：

| 類 | 詞／結構 |
|----|----------|
| 舊 OOB→purged | `落在索引外`／`未命中網格`／`事件不在.*purged`／`不在 feature_index ⇒ purged`／`不在 \`feature_index\` ⇒ purged` |
| 舊判側祈使 | `舊路徑判`／`cutoff 定側`／`cutoff決定側`／`per.cutoff 判` |
| 隔離帶誤收 | `收成 train`／`集合成員給`／`不等式給` |
| 第四條殘跡 | `寫成第四條` |

**命令**（SPEC live＝`:1` 至 `HISTORY-BEGIN`＝`:344` 之前；TODO 全檔）：

```bash
HB=$(awk '/HISTORY-BEGIN/{print NR; exit}' docs/SPLITUNIFY_SPEC.D-002.md)
VOCAB='落在索引外|未命中網格|收成 train|寫成第四條|舊路徑判|集合成員給|不等式給|per.cutoff 判|cutoff 定側|cutoff決定側|事件不在.*purged|不在 feature_index ⇒ purged|不在 `feature_index` ⇒ purged'
awk -v hb="$HB" 'NR<hb' docs/SPLITUNIFY_SPEC.D-002.md | grep -nE "$VOCAB"
grep -nE "$VOCAB" docs/SPLITUNIFY_TODO.md
```

**逐段結論**（是否與「側別＝事件級 `decision_at_ms`；界外 raise；`feature_cutoff_ms` 不參與 `split_label`」**互斥**）：

| 段 | 互斥？ | 說明 |
|----|--------|------|
| SPEC `:170` (G-4) | **無** | 「舊路徑判 train」為換錨差異敘事，非 live 施工祈使 |
| SPEC `:219` | **無** | 三段式 rationale（「集合成員給 purged、不等式給 train」） |
| SPEC `:224` | **無** | 隔離帶 ⇒ purged；「不得收成 train」＝正向契約 |
| SPEC `:225` | **無** | 界外 raise 由步驟 0 ④；禁第四條分支 |
| SPEC `:231` | **無** | 「不可做」禁 per-cutoff |
| TODO `:276-278` | **無（N4 已修）** | ~~不在 index ⇒ purged~~ ⇒ 現行界外 raise |
| TODO `:620`／`:633-634` | **無** | Task 9.2b 現行；禁第四條／禁 per-cutoff |
| diff 夾帶 | **無超範圍契約改動** | `git show ddcd66f3` 契約面＝N1–N4 落點（＋handoffs／site／白話；後者不在審查範圍） |

**同型第九次**：**未發作**（本家詞表下 live 互斥＝0）。

### (4b)

N/A。

---

## 必答 5 — 可否進 `Task 9.3`（B9D）

### (5a)

**可以（本家側）**。無本家 P0／P1；四探針 CLOSED；v23 body APPROVED；四 assumed 無須先修之阻擋項。

### (5b)

已檢查：本家 r28 無反例可重跑；N1–N4 四探針＋N1 全鍵 stale 拒＋N3 `BASE` 移位（G-4e 綠但主檔 MISMATCH）；自立詞表無第九處；140 pytest＋`GOLDEN OK`；body hash 相符；write-once 首次建立路徑於臨時目錄複現成功。**誠實邊界**：正式測試對 v8「首次建立成功」半邊覆蓋仍薄（已存在拒絕有測）——不擋 B9D。**不重開** `Task 9.3`–`9.5` 設計。進 B9D 仍須三家戳記齊＋領 impl token。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：換詞表無第九處 live 互斥；N4 邊界②已改 raise。  
2. 漏項：無本輪新增。  
3. 不可測：無。  
4. 可疑 quant：不重開。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：無本輪契約回退。  
9. 測試品質：四探針＋140 passed 有鑑別力；v8 首次建立成功半邊為誠實邊界。  
10. Agent 可執行：N1–N4 條文可據以開工。  
11. 必要性／短命工：無本輪新增短命工。

---

## 攻擊面補答（brief「我沒查」）

| 面向 | 本家結論 |
|------|----------|
| N1 `--accept-value-changes` 繞法 | 習慣性列全鍵被 `_stale_allow` 擋；真全改且逐一具名＝正當重凍上界（見必答 3①） |
| N2 同 commit 改 SPEC＋碼 | 攻擊面縮小非零；三層＋write-once 仍在（見必答 3③） |
| N3 `BASE`／`H1` 共因 | G-4e 不擋常數同移；主檔 MISMATCH 仍擋靜默（見必答 3②） |
| N4 第九處 | 詞表掃描＝0 |
| write-once 首次建立 | 臨時目錄 `O_EXCL` 成功半邊可走通；正式測覆蓋偏拒寫側 |
| diff 夾帶 | 契約面限 N1–N4 |

---

## GROK-R29-P3-00

**斷言**: 本輪逐項核對後無 finding——本家 r28 為零 finding sentinel 無反例可重跑；N1–N4 四探針皆轉紅如預期；assumed ①字面不等效但 `_stale_allow` 否證全鍵繞法、②③ 殘餘共因／同 commit 面已具名且非靜默放行、④ 自立詞表無第九處 live 互斥；v23 body 可重簽；可進 `Task 9.3`（B9D）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d`；`doc_format_precheck` SPEC／TODO → rc=0／0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py` → **140 passed**；`venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`；N1 未具名改值 refuse＝True、全鍵 allowlist stale refuse＝True；N2 缺錨 rc=1、write-once 再建 rc=1；N3 +1ms mismatch＝13、`BASE` 移位 G-4e 綠但主檔 MISMATCH keys＝5；詞表 `grep` live 互斥＝0（見必答 4 表）。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R29-BRIEF.md#3788979f5e94; docs/SPLITUNIFY_SPEC.D-002.md#52efba2e077a; docs/SPLITUNIFY_TODO.md#df8037f51f4a; scripts/freeze_splitunify_golden.py#c8c5a46f6804; handoffs/reconcile/20260911-splitunify-b9-review-r28/synth.md#ef36f3052935

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d task:20260911-SPLITUNIFY-B9-REVIEW-R29
```

（舊戳記行已保留；composer 本輪 APPROVED 行亦已在檔內。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body 52efba2e…；doc_format 0/0；r28 CLOSED；四探針＋N1 stale 全鍵拒＋N3 BASE 移位；四 assumed 逐條；詞表無第九處；可進 B9D（本家側）
TESTS_RUN: `reconcile_body_hash.sh` → 52efba2e…；`doc_format_precheck` SPEC／TODO → rc=0；`pytest …derive+golden+wiring…` → 140 passed；`freeze_splitunify_golden.py` → GOLDEN OK；N1/N2/N3/N4 探針見必答 1b／3
FAILURES_SEEN: none（首輪 pytest 誤指 `tests/momentum/Analysis/test_splitunify_wiring.py` 不存在，改 `event_samples/` 後 140 passed）
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r29-grok.md
STAMP_APPENDED: docs/SPLITUNIFY_SPEC.D-002.md（舊戳記保留；APPROVED）

STATUS: DONE
