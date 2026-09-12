# SPLITUNIFY D-001 閉合確認 R12（grok）

brief-kind: closure  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R12  
family: grok  
findings-round: R12  
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（R11 後修訂版；`bash scripts/reconcile_body_hash.sh` → `3f8c2c4590ffcb4cf3bace21da25f9282c67276efb2b223c5a1efef59fbb48d3`）  
SCOPE: 只讀 closure；禁改碼、禁動 tracked 檔、禁 commit/push、禁跑 `tests/governance` 全套。  
**範本**：`templates/COMMITTEE_FINDING_TEMPLATE.md`（canonical finding 四欄＋末段 VERDICT／BLOCKED-BY／CLOSED）。

### §0 前提

fact-verified: R11 三條皆採納並落入 D-001 → `handoffs/reconcile/20260911-splitunify-x-review-r11/synth.md` W1／W1b／W2／W3  
fact-verified: 舊 helper 正向 ASSERT 已刪；前置合法性閘＋指紋／遞增合取已寫入 → D-001:70-71／:133-135／`M-SU-D1-18`～`20`  
fact-verified: `assert_positional_rows` 預設 `require_sorted=True`，空陣列直接放行 → `split_preview.py:123-166`  
assumed: 前置合法性閘已窮盡 predicate 邊界 → 否證見必答 2（長度／zip 空轉）  
assumed: D-001 已無其他內部互斥 → 否證見必答 4（`symbol_positions`／「先轉換」殘句）

---

## 必答 1–5

### 1. R11 三條是否已閉合？

| R11 條 | 規格面 | 碼證 |
|---|---|---|
| **CODEX-R11-P1-01／GROK-R11-P1-01**（舊 helper 正向 ASSERT） | **點名條已閉合** | 全文 `_local_ordinals_for_symbol` 僅餘「為何不採」:68、禁改回判準:71、`M-SU-D1-15`:165；**無** `ASSERT … helper … THEN rc=0` 正向綠徑。亂序下 helper 語意仍與往返互斥之實跑見下方 P1-01（證明刪 ASSERT 不夠——:81 又以 `symbol_positions` 重寫同一公式）。 |
| **CODEX-R11-P2-02**（負索引繞過） | **已閉合（閘文字）** | :70 明定前置閘＋複用 `assert_positional_rows`＋不得關 `require_sorted`；ASSERT :133-134；`M-SU-D1-18`。實跑 `assert_positional_rows([-1], n=3)` → ValueError 含負值。 |
| **主委自產（指紋對排列無感）** | **已閉合（合取文字）** | :71 明示邊界＋合取＋面板／local 順序不得混淆；ASSERT :135；`M-SU-D1-19`／`20`。實跑同集合 6 個 perm 皆同指紋、其中嚴格遞增僅恆等。 |

### 2. 前置合法性閘是否還有其他繞過？

對 `assert_positional_rows`（`split_preview.py:123-166`）實跑：

| 案例 | 結果 |
|---|---|
| ①空陣列 `[]`、`n=3` | **放行**（回 `[]`）。兩端皆空時往返合法；**空 local × 非空 `row_index`**：`np.array_equal`→False、`np.all(==)`→broadcast ValueError，但 **`zip` 截斷 → `all(...)` 為 True（空轉誤放行）**。閘本身不驗與 `row_index` 等長。 |
| ②非整數 dtype | `0.5`→ERR 非整數；`0.0/1.0`→OK 轉 int；`object '0','1'`→OK 靜默轉 int；**`bool True` 單元素→`[1]` 放行**（經 float 整數性路徑）。 |
| ③超大／無號 | `uint64(2**63)`／`uint64.max` 經 `dtype=int` 變成負值後被 `min < 0` 擋下（fail-closed，訊息寫「負值」）。 |
| ④`row_index` 與 `row_index_local` 長度不同 | **閘不查**；`array_equal` 能紅；**`zip` 截斷可對齊前綴後誤綠**（例 local=`[0]`、ri 三元且首值碰巧相等 → zip all True）。規格僅有「逐位對應」:67，無獨立 ASSERT／前置等長閘。 |

**第五種繞過（找到）**：長度不相等＋以 `zip` 實作往返時，空／短 `row_index_local` 可空轉或截斷放行。見 `GROK-R12-P2-03`。

### 3. 指紋與遞增閘之合取是否真的完整？

固定集合 `{0,2,4}`：6 個排列指紋全同；其中 `strictly increasing` **只有** `(0,2,4)`。集合一改（換元／增刪）指紋必變。  
⇒ 在「指紋比對 ∧ 嚴格遞增 ∧ 同 payload 形狀」下，**不可能**既過兩閘又改變投影所用之有序 ordinal 序列——過兩閘的排列必為恆等，成員集合與順序皆不變。  
**但** D-001:75 仍寫「建構後竄改 `row_index_local` **必被該比對擋下**」，與 :71「指紋單獨擋不住重排」字面衝突；重排竄改靠遞增閘而非指紋比對。見 `GROK-R12-P2-04`。合取機制本身完整，缺的是把 :75 收斂到與 :71 同向。

### 4. 全文掃內部互斥

通讀 D-001（非只 grep `_local_ordinals_for_symbol`），殘句如下（皆與 R8／R10／R11 定案互斥或未刪之舊條款）：

1. **:81** `symbol_positions[row_index_local] == row_index`——此即 `contracts.py:510-517` helper 內部之 **frame 序**往返；與 :69 `sorted_positions[...]`（時間序）互斥。亂序單標的實跑：時間序往返 True、`symbol_positions` 往返 False。  
2. **:79**「新增任何消費 `row_index` 之處，一律**先轉換再使用**」——與 :71／:72「投影端不再轉換／只消費 `row_index_local`」互斥（R7 入口轉換殘句）。  
3. **:114** Task 8.2 檔案清單仍寫「比對端＋**無損轉換 helper**」——投影端不應再有轉換 helper。  
4. **:52** C1 第 4 點仍寫「以自己的 `feature_index` **解釋 `row_index`**」——投影應解釋／索引 `row_index_local`。  
5. **:75**「竄改 local **必被該（指紋）比對擋下**」——與 :71 合取邊界互斥（重排同指紋）。  
6. **:65** 小標仍稱「無損轉換層」——內容已改 producer attest；屬標題殘跡（建議同修，不另開 ID）。

找不到與上列等量之其他互斥對（hash 不變式、缺欄不回退、mutation 表與新 ASSERT 同向）。

### 5. 可否進入實作？

**不可。`VERDICT: blocked`。**  
若不改：b8 若照 :81 實作 attest 會把 R10／R11 已刪之 frame 序判準加回，亂序綠徑與 :136 互斥；若照 :79 在投影端加轉換則違反 R8 契約並可能再引入全框輸入。P2 不單獨擋，但應與 P1 同修以免收案時再回頭。

---

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
