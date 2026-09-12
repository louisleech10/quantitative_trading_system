# Reconcile — 20260911-splitunify-x-review-r12

**來源** 20260911-splitunify-x-review-r12-codex.md, 20260911-splitunify-x-review-r12-grok.md　|　**roster** codex,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 全文仍混用兩套座標語彙**——「D-001仍把全框`row_index`」 | P1 | CODEX-R12-P1-01 | 採納（抽驗屬實：多處仍以全框列號描述投影端行為，含 C1 第 4 點之「解釋」句、獨立 oracle 之重算來源、per-symbol 斷言。**且跨檔亦然**：BASE 檔仍以全框列號索引該標的索引，而本延伸原宣告「BASE 其餘段落原文仍有效」⇒ 兩檔對同一動作給出不同座標。修法：全文統一為 `row_index_local`，並於觸及面新增**唯一例外條款**明示 BASE 之座標語彙由本延伸取代，其餘義務不受影響） |
| **W1b 舊判準以別名殘留**——「D-001:81之往返測試仍寫`symb」 | P1 | GROK-R12-P1-01 | 採納（**這是同一判準第二次以別名復活**：R11 才刪掉以 helper 逐值相等之斷言，往返測試那行卻以 `symbol_positions` 寫了同一個 frame 序公式。該家實跑亂序資料證明照該行驗收會誤擋正確輸入。修法：改為 `sorted_positions`，並明文禁止再以 `symbol_positions` 作 attest 判準） |
| **W1c 投影端轉換條款殘留**——「D-001仍殘留「投影端轉換／用`row」 | P1 | GROK-R12-P1-02 | 採納（三處 R7 時代殘句：封閉清單之「先轉換再使用」、施工檔案清單之「無損轉換 helper」、C1 第 4 點之「解釋」句，皆與「轉換只在產生端、投影端只消費」互斥。修法：三處逐句改寫為只讀 `row_index_local`、禁再引入轉換） |
| **W2 等長與空序列未設前置閘**——「前置合法性閘未要求`len(row_in」 | P2 | GROK-R12-P2-03 | 採納（該家實跑證明：既有閘對空陣列直接放行且不查與全框列號等長；若往返以 `zip` 實作，空或過短之序號會空轉或對齊前綴而誤放行。修法：比對前先驗等長、明文禁 `zip` 而須用 `np.array_equal`，並補三條斷言與兩條變異） |
| **W3 dtype 語意未釘死**——「D-001所稱前置閘「`row_inde」 | P2 | CODEX-R12-P2-02 | 採納（該家實跑證明既有閘之強度不足：整數值浮點、布林、物件型數字與數字字串皆被靜默轉型放行，僅非整數值浮點與超大無號型被擋。修法：明定序號須為整數型，非整數型即 fail-closed，不得靠轉型救） |
| **W4 絕對句與合取邊界互斥**——「D-001:75稱建構後竄改`row_i」 | P2 | GROK-R12-P2-04 | 採納（我在 R10 寫的絕對句「竄改必被指紋比對擋下」與 R11 才寫入的「指紋對重排不敏感、須與遞增閘合取」字面衝突；保留則實作者可能只做指紋重驗而略過遞增閘。修法：改寫為「改集合由指紋擋、改順序由遞增閘擋，兩者合取後無法既通過又改變歸屬」） |

**Verdict**: 需修補後合併——W1／W1b／W1c 為 P1，性質皆為**前幾輪修訂後未清除之舊條款**，非新機制缺陷；W2／W3／W4 為判準邊界與敘述精確性。D-001 依上表修訂後須由兩家於 R13 重驗閉合。本輪兩家所附戳記因規格續有實質改動而失效，須重簽。

## 本輪程序記錄

- 🔴 **本輪性質與前五輪不同**：六條之中**沒有一條**攻擊 R11 所定之機制本身。兩家在必答二、三分別對往返判準與「指紋∧遞增」合取發動攻擊，結論一致——**找不到既能通過兩閘又能改變投影歸屬之竄改**；一家並補證同集合之排列中僅恆等滿足嚴格遞增。擋項全部落在**我前幾輪改寫後殘留的舊句子**。
- 主委據此判定：機制面已收斂，未收斂的是文件內部一致性。故本輪不再逐條打補丁，改為**一次統一全文座標語彙**，並把跨檔（BASE 檔）之同類矛盾一併以例外條款釘死。
- 🔴 **同一判準第二次以別名復活**：R11 刪除「以 helper 逐值相等」之斷言後，往返測試那行仍以 `symbol_positions` 寫著同一個 frame 序公式。⇒ 刪除某個**名稱**不等於刪除該**判準**；此教訓已寫入本輪修法（明文禁止該別名再作判準）。
- 主委對 W2／W3 之複驗：兩家探針結論一致且與主委先前之負索引探針同向；此三者合起來顯示「前置合法性閘」必須明列所涵蓋之邊界，不能只指名複用既有函式了事——既有函式的強度與規格所需並不相同。
- 兩家對 `object.__setattr__` 之 Python 逃生口立場一致、皆不升級，主委從之。
- 兩家戳記（sha 皆為 `3f8c2c4590ff…`）於本輪交件檔內，因 D-001 續改而失效。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R12-P1-01
**斷言**: D-001 仍把全框 `row_index` 與 symbol-local `row_index_local` 混在同一契約：C1.4 的「以 feature_index 解釋 row_index」、oracle 的 `row_index`、per-symbol ASSERT 的 B `row_index` 與 local-only 規則互斥；`symbol_positions` 也未定義為時間序列。
**碼證**: `docs/SPLITUNIFY_SPEC.D-001.md:44,52,65-73,81,85,99-100` 對讀；D-001:20 宣稱 BASE C-4 其餘段落仍有效，而 `docs/SPLITUNIFY_SPEC.md:165,224-225,307` 仍寫 `feature_index[row_index]`；`momentum/core/contracts.py:504-519` 的 `symbol_positions` 實際是 frame 序。這使 b8 可同時被導向全框索引與 local 索引，交錯 symbol 的投影／oracle 會失去單一座標契約。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3f8c2c4590ff

## CODEX-R12-P2-02
**斷言**: D-001 所稱前置閘「`row_index_local` 為整數」若包含 dtype fail-closed，指定複用的 helper 並未實現該強度；且「逐位對應」未明定長度閘。
**碼證**: `momentum/core/split_preview.py:131-166`；`venv/bin/python -c` dtype/uint/length probe 觀測：integral float、bool、object 數字與數字字串皆 PASS 並轉成 `[0,1]`，fractional float、`uint64(2**63)`、object `2**100` REJECT；`np.array_equal` 對四種長度不等組合皆為 `False`。因此未見改變投影歸屬的長度繞過，但 dtype 語意仍未釘死。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3f8c2c4590ff

必答1: R11 W1/W2/W3 均閉合；`rg` 精確掃描 `_local_ordinals_for_symbol.*==|==.*_local_ordinals_for_symbol` → `NO_POSITIVE_HELPER_EQUALITY`，目前只剩「不採 helper」敘述與 M-SU-D1-15 反向 mutation；:69-71 已是時間序往返、前置閘、指紋與遞增合取。
必答2: 空 train 陣列由 helper 返回空 int 陣列，與 :83/:122 的合法 `sha256("[]")` 一致；空 test 在現行 derive :460-462 fail-closed。非整數值 float 會拒絕，但 integral float/bool/object 會靜默轉型；超大 unsigned/object 觀測均拒絕；長度不等以 `array_equal` 不相等，未找到成功放行。
必答3: fingerprint probe：原集合 `[0,2,4]`；重排 `[4,2,0]` 同 hash 但 strict guard=False；改集合 `[0,2,3]`、位移 `[1,3,4]` hash 均不同且 guard=True；五元素排列交集只剩原集合。故只改 local 不可能同時過兩閘；`object.__setattr__` 同時重綁 local 與 digest 是 R11 已接受的 Python frozen 逃生口，不列新 finding。
必答4: 全文掃描後唯一 P1 互斥是 P1-01 所列 :20/:44/:52/:65-73/:81/:85/:99-100 及 base C-4 舊索引語彙；P2-02 是 helper predicate 落差。其餘 R11 修法、空陣列語意、不可變性之序列化誠實邊界、SU-RESID-5 延後彼此一致；SU-RESID-5 不使本批投影 ASSERT 產生可證偽假綠。
必答5: 不可進實作；P1-01 未釐清時，b8 可能讓 producer 寫 local、oracle／projection 讀 global，交錯 symbol 造成錯分或錯誤 IndexError。
ASSUMPTIONS_VERIFIED: `HANDOFF.md`、`CLAUDE.md`、R12 brief、D-001、R11 synth、template 已讀；helper reference scan、時間序往返、dtype/unsigned/length 邊界、fingerprint∩strict-increasing 探針與全文逐句對讀均完成。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/core/test_split_contract.py` → 83 passed；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `3f8c2c4590ffcb4cf3bace21da25f9282c67276efb2b223c5a1efef59fbb48d3`；指定 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r12-codex.md --family codex` → PASS、rc=0；`bash scripts/restore_golden_inventory.sh` rc=128（`.git/index.lock` 不可建立，既有 inventory dirty 未改寫）。
FAILURES_SEEN: completeness 首次被 PreToolUse 的 OPEN debt dispatch gate 擋下，重跑指定原命令 PASS rc=0；restore golden inventory 受 sandbox 的 `.git` 寫入限制而失敗；未修改 tracked 檔，未跑 governance 全套。
SCOPE_CHANGES: 僅新增本交件檔；無越界、無 code/SPEC/TODO/data 變更、無 commit/push。 NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r12-codex.md；TMP_CLEANUP: `/tmp` 無 `*workdir*` 候選，保留 `/tmp/claude-501`。
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:3f8c2c4590ffcb4cf3bace21da25f9282c67276efb2b223c5a1efef59fbb48d3 task:20260911-SPLITUNIFY-X-REVIEW-R12
VERDICT: blocked
BLOCKED-BY: CODEX-R12-P1-01
CLOSED:
STATUS: DONE
## GROK-R12-P1-01

**斷言**: D-001:81 之往返測試仍寫 `symbol_positions[row_index_local] == row_index`，與 :69 時間序 `sorted_positions[...]` 互斥，且公式等同 `_local_ordinals_for_symbol` 內部 frame 序往返；R11 刪掉 helper 正向 ASSERT 後，同一判準以別名殘留。

**碼證**: `docs/SPLITUNIFY_SPEC.D-001.md:69` vs `:81`；`momentum/core/contracts.py:510-517`（`symbol_positions = flatnonzero(...)` 後 `symbol_positions[local]==row_index`）。實跑亂序 ts=`[30,10,40,20]`、`row_index=[1,3]`、`row_index_local=[0,1]` → `sorted_positions[local]==row_index` True；`symbol_positions[local]==row_index` False（得 `[0,1]`）。若照 :81 驗收，正確時間序 local 會被誤擋。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#2630eb48ddce；handoffs/reconcile/20260911-splitunify-x-review-r11/synth.md#86e13c32b9fd；momentum/core/contracts.py#642aecf26b32；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R12-BRIEF.md#a4ca3b3929ac

修法：:81 改為與 :69 同形之 `sorted_positions[row_index_local] == row_index`（或刪 :81 因 :69／:132 已覆蓋）；禁再出現 `symbol_positions` 作 attest 判準。

---

## GROK-R12-P1-02

**斷言**: D-001 仍殘留「投影端轉換／用 `row_index` 解釋」條款（:79「先轉換再使用」、:114「無損轉換 helper」、:52「解釋 `row_index`」），與 R8／:71-72「轉換只在 producer、投影只消費 `row_index_local`」互斥；b8 若照殘句實作會重開入口轉換或全框索引。

**碼證**: 逐句對讀 `:52`／`:71-72`／`:79`／`:114`；同檔已釘死「投影端不再轉換」「一律不得索引 `row_index`」「不另傳全框 symbol 向量」。:79 後半 docstring 改寫指示已正確指向 `row_index_local`，與前半「先轉換」自我打架。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#2630eb48ddce；handoffs/reconcile/20260911-splitunify-x-review-r11/synth.md#86e13c32b9fd；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R12-BRIEF.md#a4ca3b3929ac

修法：:79 改為「新增消費點一律只讀 `row_index_local`，禁再引入對 `row_index` 的轉換」；:114 刪「無損轉換 helper」改「比對端（只消費 `row_index_local`）」；:52 改「解釋／索引 `row_index_local`」。

---

## GROK-R12-P2-03

**斷言**: 前置合法性閘未要求 `len(row_index_local)==len(row_index)`；`assert_positional_rows` 對空陣列直接放行；若往返以 `zip` 實作，空／短 local 可對非空 `row_index` 空轉或截斷而誤綠。

**碼證**: `split_preview.py:132-134`（`size==0` → return）；探針：local=`[]`、ri=`[10,20,30]` → `zip` all True、`array_equal` False；local=`[0]`、ri 三元且 `ri[0]==sp[0]` → zip 截斷 all True。規格 :67「逐位對應」未落成獨立 ASSERT／閘條件。

**來源摘要**: momentum/core/split_preview.py#cedf0a5156c3；docs/SPLITUNIFY_SPEC.D-001.md#2630eb48ddce；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R12-BRIEF.md#a4ca3b3929ac

修法：往返前先驗等長（或明定必須 `np.array_equal`／禁 zip）；補 ASSERT「長度不等 ⇒ rc!=0」。

---

## GROK-R12-P2-04

**斷言**: D-001:75 稱建構後竄改 `row_index_local`「必被該（指紋）比對擋下」，與 :71「指紋對重排不敏感、須與遞增閘合取」互斥；保留則實作者可能只做指紋重驗而關掉／漏接遞增閘。

**碼證**: `:71` vs `:75` 逐字；同集合重排探針指紋不變；ASSERT :135 已寫「指紋相同，由遞增閘擋下」——與 :75 絕對句衝突。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#2630eb48ddce；handoffs/reconcile/20260911-splitunify-x-review-r11/synth.md#86e13c32b9fd

修法：:75 改為「改集合必被指紋擋；改順序由遞增閘擋；兩者合取後竄改無法既過閘又改歸屬」。

---

RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:3f8c2c4590ffcb4cf3bace21da25f9282c67276efb2b223c5a1efef59fbb48d3 task:20260911-SPLITUNIFY-X-REVIEW-R12

VERDICT: blocked
BLOCKED-BY: GROK-R12-P1-01,GROK-R12-P1-02
CLOSED: GROK-R11-P1-01
STATUS: DONE

ASSUMPTIONS_VERIFIED: brief／HANDOFF／R11 synth／修訂後 D-001 全文；helper 正向 ASSERT 已刪；負索引閘；指紋∧遞增僅恆等；空／dtype／uint／長度／zip 探針；`symbol_positions` vs `sorted_positions` 亂序對照；轉換殘句通讀。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `3f8c2c4590ff…`；venv 探針（assert_positional_rows 邊界、zip 空轉、指紋 perm、亂序 symbol_positions）；completeness 見下。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r12-grok.md
TMP_CLEANUP: 清 `/tmp/workdir*`；保留 `/tmp/claude-501`。
