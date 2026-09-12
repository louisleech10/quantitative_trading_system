# SPLITUNIFY D-001 閉合確認 R10（grok）

brief-kind: closure  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R10  
family: grok  
findings-round: R10  
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（R9 後修訂版；`bash scripts/reconcile_body_hash.sh` → `84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c`）  
SCOPE: 只讀 closure；禁改碼、禁動 tracked 檔、禁 commit/push、禁跑 `tests/governance` 全套。  
**範本**：`templates/COMMITTEE_FINDING_TEMPLATE.md`（canonical finding 四欄＋末段 VERDICT／BLOCKED-BY／CLOSED；零 findings 用 `## GROK-R10-P3-00` sentinel）。

### §0 前提

fact-verified: R9 群集 W1＝`CODEX-R9-P1-01`、W2＝GROK 必答二前提缺口，皆採納並落入 D-001 → `handoffs/reconcile/20260911-splitunify-x-review-r9/synth.md`  
fact-verified: 凍結只擋整欄改綁、陣列可原地改寫、無 defensive copy → 主委實跑；本輪複驗現行 `SplitPlan` 仍 `p.row_index[0]=99` 成功且來源別名滲入 → 輸出 `[99, 6]`、`writeable=True`（碼尚未改，屬預期）  
fact-verified: D-001-C2 第 4 點已寫入 `__post_init__` 對兩欄 copy＋`setflags(write=False)`；Task 8.2 三條 ASSERT（:125-127）；mutation `M-SU-D1-13`／`14`／`15` → D-001:72-73／:125-127／:153-155  
fact-verified: 單調性保證只在 `purge_semantic=="rows"` → `contracts.py:562-568`；`:930` 路徑 `purge_semantic="timedelta"` → `ic_filter_orchestrator.py:923-934`  
fact-verified: `split_per_symbol` 呼叫 splitter 前對每標的 `sort_values(ts_col)` → `contracts.py:657`  
assumed: defensive copy＋唯讀足以封住兩欄脫鉤 → 否證觀測見必答 2（pickle／deepcopy 還原後 writeable；生產 derive 路徑未見 SplitPlan pickle）  
assumed: 新增 fail-closed 不影響現行綠徑 → 否證觀測見必答 3（已實查：from_product 形 MultiIndex 下 `train_local==helper`）

---

## 必答 1–5

### 1. `CODEX-R9-P1-01` 是否已閉合？

**已閉合（規格面）。**

R9 擋項＝producer 一次性 attest 後，`frozen=True` 仍允許 numpy 原地改寫／來源別名，使 `row_index` 與 `row_index_local` 脫鉤。修訂後 D-001 已逐條對上：

| 落點 | 碼證 |
|---|---|
| 根因寫明（整欄改綁≠深層不可變；無 defensive copy） | D-001:72 |
| 修法：`__post_init__` 對兩欄各自 copy＋`setflags(write=False)` | D-001:72；Task 8.2 檔案清單:105 |
| ASSERT 原地寫入應丟例外 | D-001:125 |
| ASSERT 改來源陣列後 plan 不變 | D-001:126 |
| 變異 `M-SU-D1-13`／`14` | D-001:153-154 |
| attest 前提＋timedelta 非時間序 fail-closed（W2） | D-001:73；:127；`M-SU-D1-15` |

現行碼 `contracts.py:377-403` **尚未**實作該 `__post_init__`（本輪複驗仍可原地改寫）——屬 b8 實作範圍，不構成「規格未閉合」。

### 2. 深層不可變性是否真的封住？

**對 D-001 明列的兩條（原地寫入、來源別名）＋ brief 點名的 asarray／切片／replace：在「已落地 copy＋唯讀」的假設下可封住；另找到 pickle／deepcopy 第三路徑，但生產 derive／三 producer 路徑未見 SplitPlan 序列化往返。**

本輪以等價 `__post_init__`（copy＋`setflags(write=False)`）實跑：

| 路徑 | 結果 |
|---|---|
| 原地 `p.row_index[0]=…` | `ValueError`（read-only） |
| 改建構時傳入之來源陣列 | plan 不變 |
| `np.asarray(p.row_index)` | 同物件但 `writeable=False`，寫入被擋 |
| 切片視圖 `p.row_index[:2]` | `writeable=False`，寫入被擋 |
| `dataclasses.replace(...)` | 走 `__post_init__`，新 plan 仍唯讀 |
| `.copy()` 後改副本 | 只改副本；寫回需 `object.__setattr__`（frozen 故意逃生口）或 replace（會再 freeze） |
| **`pickle.loads(pickle.dumps(p))`** | **不呼叫 `__post_init__`，還原後 `writeable=True`，可再原地改寫** |
| **`copy.deepcopy(p)`** | 同上，`writeable=True` |

結論：copy＋唯讀封住 brief 所列之原地／別名／asarray／切片／replace；**pickle／deepcopy 是第三條脫鉤路徑**。靜態搜尋：`momentum/` 內無對 `SplitPlan` 的 pickle 進出（`checkpoint_manager` 的 pickle 不載 SplitPlan）；derive／三 producer 為記憶體內建構。故**不升級為本輪擋項**，但 b8 若日後把 plan 序列化進 cache，須在 load 後重跑 freeze 或改 `__setstate__`。`object.__setattr__` 屬 Python frozen 已知逃生口，不計入契約缺口。

### 3. fail-closed 新增面是否打到現行綠徑？

**現行綠徑不受影響；病理「frame 序≠時間序」才會被新擋下。**

碼證鏈：

1. `:930` 呼叫 `split_per_symbol(..., purge_semantic="timedelta")`（`ic_filter_orchestrator.py:923-934`）。
2. `split_per_symbol` 在呼叫 splitter **之前**對每標的 `group.sort_values(ts_col, kind="mergesort")`（`contracts.py:657`）⇒ splitter 所見之 `train_local`／`test_local` **恆為時間序**。
3. `_local_ordinals_for_symbol` 以 `np.flatnonzero(symbol_arr == symbol)` 取 **frame 序** local（`contracts.py:510-519`）。
4. 故 `train_local == helper` **當且僅當**原 frame 內該標的列已按時間遞增。

實查（非只讀規格）：

- 以測試慣例 `MultiIndex.from_product([timestamps, symbols])` → `_cross_sectional_to_split_frame` → 同 `:930` 的 timedelta splitter：兩標的 train／test 皆 `train_local == helper`（`ALL_EQ True`）；within-symbol flat 時刻嚴格遞增。
- 人為打亂 MultiIndex 後：within-symbol 非遞增，`train_local != helper`（會被新 fail-closed 擋住）——此形**不是**現行 fixture／`from_product` 綠徑。
- `analyze_cross_sectional` **未**對 `features.index` 做 `is_monotonic_increasing` 檢查（僅 `labels_path` 有，`:751`）；docstring 要求 `(timestamp, symbol)` MultiIndex（`:1968-1969`）。綠徑依賴「呼叫端／FF 送來的 index 已是 lex 序」；亂序輸入本就會在新 attest 下紅——符合「交由上游修正排序」，不是弄紅既有通過的 from_product／單調路徑。

### 4. （R9 本家 proceed）是否接受主委對凍結斷言的更正？

**接受。** R9 必答三寫「`SplitPlan` 為 `frozen=True`，欄位不能被就地改寫」**錯誤**——主委實跑與本輪複驗皆證明 numpy 欄可原地改寫且無 defensive copy。該句不採；W1 成立。

在該事實更正後：**R9 的 `proceed` 裁決應改為當時應 `blocked`**（與 codex 同向）。本輪因 D-001 已落入 copy＋唯讀＋ASSERT／mutation，改判規格可進實作（見必答 5），**不是**為 R9 錯判辯護。

### 5. 可否進入實作？

**可以。`VERDICT: proceed`。**

- `CODEX-R9-P1-01` 規格已閉；b8 實作 Task 8.2 之 `__post_init__`／三 ASSERT／`M-SU-D1-13..15`。  
- 必答 2 之 pickle／deepcopy 殘留不在現行生產路徑，不擋 b8。  
- 必答 3 確認 timedelta 綠徑（時間序 MultiIndex）不受新 fail-closed 誤傷。  
- 文件殘跡：D-001:74 對 code docstring 的改寫指示仍含「入口轉換後之 symbol-local ordinal」字樣（設計段 :68-73 已改為 producer attest）——屬 b8 改 docstring 時一併改成「以 `row_index_local` 索引」即可，不重開 P1。

---

## GROK-R10-P3-00

**斷言**: 本輪逐項核對後無 finding；`CODEX-R9-P1-01` 已由 D-001 之 defensive copy＋唯讀＋ASSERT／mutation 閉合，timedelta 綠徑實查不受新 fail-closed 誤傷，可進 b8 實作。

**碼證**: 對讀 D-001:72-73／:105／:125-127／:153-155；R9 synth W1／W2；現行 `contracts.py:377-403` 仍無 copy／setflags（待 b8）；`contracts.py:562-568`／:657／:510-519；`ic_filter_orchestrator.py:923-934`／:1968-1969／:751；等價 `__post_init__` 探針（原地／別名／asarray／切片／replace 封住；pickle／deepcopy 還原 writeable）；`from_product`→`_cross_sectional_to_split_frame`→timedelta splitter 實跑 `ALL_EQ True`；打亂 index 對照 `eq=False`。`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#84942a34e86c；handoffs/reconcile/20260911-splitunify-x-review-r9/synth.md#249fe2729b18；handoffs/20260911-splitunify-x-review-r9-grok.md#8f07b4076af9；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a；momentum/Analysis/event_samples/split_projection.py#98ee62905643；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R10-BRIEF.md#4938b6cb6e1e

本輪為閉合確認：必答 1–5 皆有立場與碼證；零實質新 finding，故以 sentinel 收斂，未捏造擋項。R9 本家對 frozen 的錯誤事實斷言已在必答 4 接受更正。

---

RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c task:20260911-SPLITUNIFY-X-REVIEW-R10

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE

ASSUMPTIONS_VERIFIED: brief／HANDOFF／R9 synth／修訂後 D-001／現行 SplitPlan 可變性／split_per_symbol 排序／helper frame 序／:930 timedelta 路徑／from_product 綠徑與打亂對照／deepcopy+pickle 探針已核對。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `84942a34e86c…`；venv python 現行 SplitPlan 原地＋別名 → `[99, 6]` writeable；等價 post_init 探針；from_product timedelta `ALL_EQ True`；completeness 見下。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r10-grok.md
TMP_CLEANUP: `find /tmp -maxdepth 1 -mindepth 1 -iname '*workdir*'` → 無候選；已保留 `/tmp/claude-501`。
