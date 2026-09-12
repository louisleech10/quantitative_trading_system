# Reconcile — 20260911-splitunify-x-review-r11

**來源** 20260911-splitunify-x-review-r11-codex.md, 20260911-splitunify-x-review-r11-grok.md　|　**roster** codex,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 舊 attest 斷言殘留，與新判準互斥**——「R10-P1-02尚未閉合；D-001:」 | P1 | CODEX-R11-P1-01 | 採納（**兩家獨立指向同一處**，主委抽驗屬實：改判準時改了敘述段與變異表，卻漏掉驗證段那條舊斷言，仍要求以 frame 序 helper 逐值相等 ⇒ 與「亂序輸入加正確 `row_index_local` 應放行」互斥，且與變異表自相矛盾。修法：刪除該條，並把同段另一條以 helper 語彙描述者改寫為往返語彙） |
| **W1b 同一處之第二來源**——「D-001Task8.2之ASSERT:」 | P1 | GROK-R11-P1-01 | 採納（與 W1 同一修法；該家另實跑亂序單標的證明兩條斷言不可能同時成立） |
| **W2 往返判準可被負索引繞過**——「時間序往返式未明定先驗localordi」 | P2 | CODEX-R11-P2-02 | 採納（主委實跑複驗：`sorted_positions` 為長度 3 時，以 `-1` 作序號取得之值與 `row_index` 相等而判定放行；加一道「整數、值須落在長度範圍內、唯一、嚴格遞增」之前置閘即擋下。修法：明定 attest 與投影入口皆須先跑該合法性閘再做往返比對，並指名複用 `assert_positional_rows`） |
| **W3 主委自產：指紋對排列無感，第二道守衛未入規格**——「時間序往返式未明定先驗localordi」 | P2 | CODEX-R11-P2-02 | 採納（主委於本輪派工後自產並另檔立案（檔名見本輪程序記錄）：指紋依規格先依序號排序再雜湊，故同集合重排指紋不變；擋住重排的是另一道「嚴格遞增」閘，而該閘只存在於碼中、規格全文未提。第二家必答二獨立得出同一結論並補證「同集合且遞增之排列只有恆等」。修法：規格明寫指紋對排列不敏感屬明示邊界、遞增由該閘承擔且 `require_sorted` 不得關閉） |

**Verdict**: 需修補後合併——W1／W1b 為 P1 擋項（規格內部自相矛盾），W2／W3 為 P2 判準邊界缺口；D-001 依上表修訂後須由兩家於 R12 重驗閉合。本輪兩家所附戳記因規格續有實質改動而失效，須重簽。

## 本輪程序記錄

- **本輪是本票首次兩家裁決同向**（皆 blocked）**且指向同一處**。前三輪皆為裁決相反、由主委實跑裁決。
- 主委抽驗 W1：驗證段第 123 行仍為舊判準（以 helper 逐值相等），而第 132 行要求「亂序輸入加正確序號應放行」，第 161 行之變異又要求「把判準改回 helper 應紅」⇒ 同一份文件內三處互斥。此為主委改判準時之遺漏，`spec_xref_check` 只比對跨檔引用，抓不到同檔內部矛盾。
- 主委實跑複驗 W2：`sorted_positions` 為 `[10,20,30]`、`row_index` 為 `[30]` 時，序號寫 `-1` 取得 `[30]`，往返判定為相等（誤放行）；序號寫 `1` 取得 `[20]`，判定不等（正確擋下）。加前置範圍閘後，`-1` 被擋、`2` 放行。
- W3 為主委自產條，立案檔為 handoffs/20260912-SPLITUNIFY-CHAIR-R11-SELFFINDING.md，產生於本輪派工後、兩家交件前；主委依「自產一版」之規矩先自行嘗試否證自己在 R10 的核心主張，結果打中自己。第二家必答二獨立達成同一結論，且補證同集合排列中僅恆等滿足遞增，故指紋與遞增閘**合取**後無缺口——但該合取必須寫進規格才算數。
- 兩家對 `SU-RESID-5` 之延後**皆表接受**，並各自說明不做不會使本批出現可證偽假綠。該殘留維持原登記。
- 兩家皆指出 `object.__setattr__` 可繞過凍結改寫字串欄，屬 Python 已知逃生口，兩家皆不升級為擋項，主委從之。
- 兩家戳記（sha 皆為 `dbb0a67e4553…`）於本輪交件檔內，因 D-001 續改而失效。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R11-P1-01
**斷言**: R10-P1-02 尚未閉合；D-001:69/76/132 採時間序往返，但 D-001:123 仍要求 frame-order `_local_ordinals_for_symbol(...) == row_index_local`，與新判準互斥，且 M-SU-D1-15 又要求該 helper 變異應紅。
**碼證**: 實跑 `split_per_symbol(..., purge_semantic="timedelta")` 於亂序時間 `[2h,0h,3h,1h]` rc=0，producer rows=`[1,3]`/`[0,2]`；時間序 `sorted_positions=[1,3,0,2]`、正確 local=`[0,1]` 往返為 True，但 helper 回 `[1,3]`，不等於 `[0,1]`。若照 :123 驗收，合法亂序輸入會被誤擋。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238:69,76,123,131-132,161；`momentum/core/contracts.py:504-519,656-692`。
必答1：R10-P1-01 的固定 universe 直接竄改 local ordinal 會改變指紋，入口重驗主張在此模型下成立；本 finding 不否定該局部結論。必答2：固定 index 下未找到碰撞；缺欄／空字串應在入口先 fail-closed（D-001:71,81-82），但實作尚未存在，故未宣稱 runtime coverage。必答3：正確亂序往返 True；正向位移 `[1,2]` 產生 `[3,0]` 必不等，能抓真正錯值；另一 symbol 若數值同為 `[0,1]` 會相等但語意已同值。必答4：SU-RESID-5 可延至 b8 後，因投影只讀 local；它仍是既有全框 consumer 風險。必答5：不可進實作，須先刪除 :123 舊判準並使 ASSERT／mutation 同向。

## CODEX-R11-P2-02
**斷言**: 時間序往返式未明定先驗 local ordinal 範圍；Python 負索引可使錯誤 `row_index_local` 通過「等值」attest，故「錯寫必不等」不是普遍成立。
**碼證**: 隔離探針 `sorted_positions=np.array([10,20,30]); row_index=np.array([30]); row_index_local=np.array([-1])` → `sorted_positions[row_index_local]=[30]`，比較為 True；同一探針正向位移 `[1,2]` 對 `[1,3]` 為 False。需在索引前以 `0 <= local < len(sorted_positions)`（並驗整數、唯一、時間序）fail-closed。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md:67,69,78-81,131；`momentum/core/split_preview.py:123-176` 的既有 positional guard 可供複用。
必答1：R10-P1-01 的指紋仍可抓固定 feature index 下的 local 變更；本 finding 是 producer attest predicate 的邊界缺口。必答2：固定 payload 下無位置碰撞實例，但負索引在入口前已令 roundtrip 相等，若不先做範圍閘即繞過。必答3：正向位移會紅；負值反例會通過；另一 symbol 的同值 local 不能證明來源，但不造成數值差異。必答4：SU-RESID-5 與此獨立；其延後不改變本 finding。必答5：需補明確範圍閘後才可 proceed。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF、CLAUDE、R11 brief、D-001、SPLITUNIFY TODO、template、R10 synth；中間網格 probe returned；亂序 timedelta producer 與 time-order/helper 對照已實跑。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238`；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/core/test_split_contract.py` → 83 passed；隔離 probes rc=0。
FAILURES_SEEN: 亂序 probe 首次以 epoch-ms 數字餵既有 contracts 正規化而得 OutOfBoundsDatetime；改用 Datetime 值後同一案例 rc=0；未跑 governance 全套。
SCOPE_CHANGES: 僅新增本交件檔；未改 tracked code/data、未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；review only，未改產品數值、schema、golden 或輸出大小。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r11-codex.md
TMP_CLEANUP: `find /tmp -maxdepth 1 -mindepth 1 -iname '*workdir*'` 無候選；已保留 `/tmp/claude-501`。
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238 task:20260911-SPLITUNIFY-X-REVIEW-R11
VERDICT: blocked
BLOCKED-BY: CODEX-R11-P1-01,CODEX-R11-P2-02
CLOSED:
STATUS: DONE
## GROK-R11-P1-01

**斷言**: D-001 Task 8.2 之 ASSERT :123 仍要求 `_local_ordinals_for_symbol(...)` 逐值等於 `row_index_local`，與同節 :132（亂序輸入＋正確 local ⇒ rc=0）及 C2 第 4 點「不得以 helper 當 attest 判準」互斥；保留則 b8 無法同時滿足兩條 ASSERT，且會把 R10 已刪之 frame 序閘變相加回。

**碼證**: `docs/SPLITUNIFY_SPEC.D-001.md:123` 原文 vs `:69`／`:132`／`:161`（`M-SU-D1-15`＝把判準改回 helper 應紅）。實跑亂序單標的：`train_local=[0,1,2,3,4]`、`train_rows=[1,3,5,7,0]`、`helper_locals=searchsorted(frame_pos, train_rows)=[1,3,5,7,0]` ⇒ `helper==train_local` 為 False；往返 `sorted_positions[train_local]==train_rows` 為 True。`contracts.py:504-519`（helper＝frame 序）、`:657-661`（先 `sort_values` 再取 local）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#dbb0a67e4553；handoffs/reconcile/20260911-splitunify-x-review-r10/synth.md#c8f4e5dd23ef；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md#8d8ec08a18ba；momentum/core/contracts.py#642aecf26b32

修法：刪除或改寫 :123，使唯一 attest ASSERT 與時間序往返（:131-132）一致；不得再把 helper 相等寫成正向綠徑義務。

---

RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238 task:20260911-SPLITUNIFY-X-REVIEW-R11

VERDICT: blocked
BLOCKED-BY: GROK-R11-P1-01
CLOSED:
STATUS: DONE

ASSUMPTIONS_VERIFIED: brief／HANDOFF／R10 synth／修訂後 D-001；指紋同集合／遞增合取；缺欄閘序；亂序往返 vs helper；shift／位移偵錯；derive 單一路徑無 fingerprint；SU-RESID-5 消費點行號；ASSERT :123↔:132 互斥實跑。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `dbb0a67e4553…`；venv 探針（指紋篡改矩陣、setattr 逃生、缺欄閘、亂序往返、helper 衝突、same_fp∩increasing 僅恆等）；completeness 見下。
FAILURES_SEEN: 探針首跑末段 `datetime64`→`int` 轉型錯，改用 int64 epoch 後重跑通過。
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r11-grok.md
TMP_CLEANUP: 見收尾；保留 `/tmp/claude-501`。
