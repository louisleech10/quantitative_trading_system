# GAP3_EVENT_UX_TODO — D 延伸 002（B1 實作期之修訂）

BASE: docs/GAP3_EVENT_UX_TODO.md @ afa70967
PREDECESSOR: docs/GAP3_EVENT_UX_TODO.D-001.md

改什麼: 三條——A-002 更正 TODO Task 4.2 之「S-9 之 6 條驗收」為 SPEC 之 **≥7 條**；
A-003 定死小時命名欄之換算捨入方向（SPEC 未定，取保守方向）；
A-004 具名 Task 2.1b 前端下界值來源之殘留（依賴後批）。
為什麼: A-002 為 TODO 與 FROZEN SPEC **衝突**，依 TODO §層級宣告「以 SPEC 為準並回報」；
A-003 為 SPEC 沉默處之實作決策，會被 B3／B7 消費，必須先寫下否則各批各自解讀；
A-004 為 B1 交付邊界，依「殘留每條必帶為何現在不做」具名。
檔名依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.2（`*.D-NNN.md` 機讀規約）。

## 觸及面宣告

新增: none
覆寫: Task 4.2 之「驗證」欄中「S-9 之 6 條驗收」該字面
依賴: docs/GAP3_EVENT_UX_TODO.D-001.md（A-001 定 B1 含四個 Task，本檔沿用該讀法）

## 內容

### A-002 — Task 4.2「S-9 之 6 條驗收」與 SPEC 之 ≥7 條衝突

- **TODO 原文**（Task 4.2 驗證欄）：`pytest tests/momentum/event_samples/ -q -k horizon_curve` **≥3 條** ＋ **S-9 之 6 條驗收**。
  同一字面亦出現於 `docs/GAP3UX_IMPL_HANDOFF.md` §2 之座標表。
- **SPEC（語意權威，FROZEN）**：§G「S-9 之驗收」明訂
  `pytest tests/momentum/event_samples/ -q -k canonical_serialize` **≥7 條**，並逐條列出 ①–⑦。
- **裁定**：依 TODO §層級宣告「本檔與 SPEC 衝突時**以 SPEC 為準並回報**」⇒ **採 7 條**。
- **這不是抄寫差異，⑦ 是真缺口**：⑦＝`horizons=[1,3,3,7]` 須 raise `ValueError`。
  實跑 `momentum/Analysis/event_samples/tables.py::event_forward_return_table` 之守衛
  只擋 `not horizons or any(h < 1 ...)`，重複 h 會在 `out[str(h)]` 互相覆寫而**靜默通過**。
  若照 TODO 的「6 條」落地，最可能被省掉的就是這條。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k canonical_serialize` 條目數 `>= 7`；
  `grep -c 'canonical_serialize' docs/GAP3_EVENT_UX_SPEC.md` `>= 1`。
- **mutation**：移除 `tables.py` 中重複 h 之守衛 ⇒
  `test_canonical_serialize_07_duplicate_horizon_raises` 須轉紅；還原轉綠。
  receipt：`handoffs/run_receipts/gap3ux-b1-task42-s9-mutation.receipt.json`（`4.2-M1` PASS）。

### A-003 — 小時命名欄換算根數之捨入方向＝**向上取整**

- **SPEC 原文**：`bars_of(c, tf) = c.lookahead_hours ÷ hours_per_bar(tf)`；
  驗收②之 receipt 命令為 `72*3600//TIMEFRAME_SECONDS['1h']` 與 `…['12h']` → `72 6`。
- **SPEC 未定捨入方向**：`72h` 在 `1h`／`12h` 上整除，floor 與 ceil 同值 ⇒ 該例分辨不出。
  但 `future1_close_return`（H=1）在 `12h` 線上，floor 得 **0**——等於宣稱「不必 purge」，
  而該欄確實看到未來 1 小時。
- **裁定**：取 **ceil**。依 §C0「量化正確性只能更嚴、不得放水」——
  在 SPEC 沉默處，只准往保守方向解讀。
  落點＝`momentum/Analysis/contracts/future_column_lookahead.json` 之
  `hours_to_bars_rounding: "ceil"`（loader 對該值 fail-closed，非註解宣稱）＋
  `momentum/Analysis/event_samples/lookahead_registry.py::hours_to_bars`。
- **對 SPEC 驗收②之相容性**：整除情形不受影響，`72 6` 仍成立（已實跑）。
- **驗證**：`pytest tests/api -q -k gap3_lookahead_depth` 之②仍以
  `72*3600//TIMEFRAME_SECONDS[tf]` 為期望值且通過；
  `pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete` 之
  `test_lookahead_registry_complete_07_hours_to_bars_is_ceil` 斷言 `hours_to_bars(1,'12h') == 1`。
- **mutation**：把 `hours_to_bars` 之回傳改為直接取 `lookahead_hours` ⇒
  `test_gap3_lookahead_depth_02_hour_named_resolves_per_tf` 與 `…_03_…` 轉紅；還原轉綠。
  receipt：`handoffs/run_receipts/gap3ux-b1-task21b-mutation.receipt.json`（`2.1b-M2` PASS）。

### A-004 — 具名殘留：Task 2.1b 前端下界**值來源**未於 B1 接上

- **B1 已交付**：`momentum/Analysis/event_samples/lookahead_depth.py::depth_by_timeframe()`
  （唯一 exported 深度函式）＋ `frontend/src/lib/lookaheadDepthLock.ts`（鎖定與阻擋）
  ＋ `frontend/src/app/search/page.tsx` 之選單 disable 與匯出前守衛
  （阻擋發生在任何網路動作**之前**，vitest 斷言 `fetch` call count `== 0`）。
- **未接上的是「下界值從哪來」**：`lookaheadLowerBound` 現恆為 `null`（＝尚無約束）。
- **為何現在不做**（三值理由：**blocked-by**）：
  ① 會引用未來欄之**篩選面板**是 **Task 2.1（B5）**，B1 時不存在
    ——現行搜尋條件（price_change／volume_multiplier／closing_strength／
    taker_buy_ratio／price_position）一個未來欄都沒引用，導出下界恆等於宣告值；
  ② 把導出值送到前端之**傳輸點**是 **Task 1.3（B2）**所建之
    「case 鏈內既有回應欄位承載點」（不新增 route）。
- **為何不在前端自算**：TODO Task 2.1b 明訂 `depth_by_timeframe()` 為
  **唯一 exported 深度函式**（Task 1.9 與 V-12 一律引用本式，禁第二份）。
  在 TS 重寫＝第二份副本，兩條路徑必然漂移。
- **owner**：主委。**觸發**：Task 2.1（B5）與 Task 1.3（B2）皆落地後，於 B5 收尾一併接線。
- **不得宣稱已解決**：B1 交付的是鎖定機制，不是下界值。

### A-005 — 🔴 SPEC Task 1.10 對 `future{1,2,4,6}_close_return` 之單位敘述**與 producer 不符**

- **SPEC 原文**（Task 1.10 內容欄）：「**小時命名**（`future{H}_close_return`／`future72_max_return`／
  `future72_max_drawdown`，H ∈ {1,2,4,6,24,48,72}）：`H` 是**小時**」。
- **producer 實況**（`momentum/DataExtraction/case_search_engine.py`）：
  - `df['future{N}_close_return'] = (df['close'].shift(-N) - df['close']) / df['close']`，
    **N ∈ {1,2,4,6}** ——裸整數 shift，就是**根數**，與 timeframe 無關。
  - 只有 `df['future{H}_close_return'] = (df['close'].shift(-periods_{H}h) - …)`，
    **H ∈ {24,48,72}** 才是小時。
- **後果（若照 SPEC 登記）**：12h 線上 `future6_close_return` 實際看 **6 根**，
  registry 卻回 `ceil(6/12) = 1` 根 ⇒ 答案窗下界被低估 **六倍**，purge 不足 ⇒ **標籤洩漏**。
  屬 §C0「資料正確性類缺口」，**不得**降級為具名殘留。
- **裁定**：**以 producer 為準**，`future{1,2,4,6}_close_return` 登記為 `kind: bar`、
  `lookahead_bars = N`。此為 FROZEN SPEC 與實況衝突之回報（TODO §層級宣告要求「衝突以 SPEC 為準
  並回報」；但此處 SPEC 之敘述是**對實況的事實陳述**且該陳述可被實跑否證，
  照抄會製造洩漏 ⇒ 取實況並在此具名，不動 SPEC 本體）。
- **發現者**：`CODEX-R1-P1-01`（B1 code review 第一輪），主委實跑覆核成立。
  三輪 SPEC 對抗審與 TODO 三輪審**都沒抓到**——因為它們比對的是文件之間，沒有回讀 producer。
- **連動更正 A-003**：A-003 舉的例子（`future1_close_return` 在 12h 線上 floor 得 0）
  **建立在錯誤分類上**，該例作廢。ceil 之裁定**維持**（保守方向），但更正其現況說明：
  修正後 hour 類只剩 `{24,48,72}`，對現行全部 timeframe 皆整除
  ⇒ **ceil 與 floor 目前無任何活的欄位差異**，本決策現為對函式本身之防禦性釘死。
- **另記（不改行為）**：`future_max_return`／`future_max_drawdown` 之 producer 窗為寫死之
  `standard_lookahead = 6`（根）。仍依 SPEC 標 `lookahead_unknown: true`、不得給預設深度
  ——保守方向；該事實只記入 registry 之 `classification_evidence`，**不得**被解析為深度。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete` **≥14 條**，
  其中 `test_lookahead_registry_complete_05_registry_content_correct` 之 oracle 改為
  **producer-backed 表**（不再由欄名 regex 導出）、
  `…_05b_producer_oracle_covers_every_non_bar_column` 防該表漏欄、
  `…_05c_shift_named_columns_are_bar_kind` 為定向回歸鎖。
- **mutation**：把 `future6_close_return` 改回 `{"kind":"hour","lookahead_hours":6}`
  ⇒ `…_05_registry_content_correct` 與 `…_05c_shift_named_columns_are_bar_kind` 轉紅；還原轉綠。
  receipt：`handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json`（`1.10-M4`）。
- 🔴 **具名殘留（R-A005-1）**：producer-backed 表為**人工稽核**所得，非執跑探針
  ——producer 若改算式而未同步該表，本閘看不見。
  **為何現在不做執跑探針**：三值理由 `needs-research`
  ——要真正量測「這一欄看多遠」須把 `CaseSearchEngine` 之未來欄計算段抽成可獨立呼叫之純函式，
  那是對搜尋引擎之重構，超出 B1（契約與深度根基）之範圍，且會動到 GAP-3 以外之呼叫端。
  **owner**：主委。**觸發**：下次動到 `case_search_engine.py` 之未來欄計算段時一併做。

### A-006 — S-9 ⑦ 之對照組過寬（假綠）

- **原寫法**：不重複之 `horizons=[1,3,7]` 只斷言「例外訊息**不含**『不得重複』」。
- **失效**：一個「所有 horizons 一律 raise `ValueError`」之壞實作，訊息不同 ⇒ 照樣全綠
  （codex 實跑該 mutant 得 `9 passed`／rc=0）。完整曲線可被靜默禁用而無人察覺。
- **修法**：改為斷言控制流**真的走過了 horizon 驗證區**——`manifest=None` 之下一步
  `t = manifest.table` 必然 `AttributeError` ⇒ 對照組期望 `AttributeError` 且訊息含 `table`。
  任何在該點之前 raise 的壞法都會轉紅。
- **發現者**：`CODEX-R1-P1-02`。
- **mutation**：把重複守衛之條件改為 `if True`（所有 horizons 一律被擋）
  ⇒ `test_canonical_serialize_07_duplicate_horizon_raises` 轉紅；還原轉綠（`4.2-M2`）。

### A-007 — Task 2.1b 前端守衛之**真實呼叫點**未被覆蓋（假綠）

- **失效**：`frontend/src/lib/lookaheadDepthLock.test.ts` 用的是自建之 `exportGuarded` 雙胞，
  註解寫「與 `search/page.tsx` 同一形態」卻**不 import page**
  ⇒ 把 `page.tsx` 之匯出守衛整段刪掉，該檔仍 7 passed（grok 實跑）。
  與本 epic 犯過四次之「比對範圍過寬」同族：錨點落在**像目標的東西**上，不是目標本身。
- **修法**：新增 `frontend/src/lib/lookaheadDepthLock.page.test.ts`，以 **TypeScript AST**（非 grep）
  對 `page.tsx` 之 `exportSearchResultsToEventJson` 斷言三件事：
  ①確實呼叫 `isHorizonBelowLowerBound` ②該呼叫位於帶 `return` 之 `if` 內
  ③該守衛之位移**小於**該函式第一個 `await` 之位移（阻擋早於任何網路動作）。
- **發現者**：`GROK-R1-P2-01`。
- **mutation**：刪掉 `page.tsx` 之匯出守衛 ⇒ 上列①②③三條全部轉紅；還原轉綠（`2.1b-M4`）。

### A-008 — AST 測試 ④ 用「呼叫次數」代替「綁定」（假綠，R2）

- **原寫法**：只數 `isHorizonBelowLowerBound` 在 `page.tsx` 全檔之呼叫次數 `>= 2`。
- **失效**：把 `<option>` 之 `disabled={…}` 綁定整段刪掉，次數仍達標 ⇒ 測試照樣綠
  （codex 實跑 rc=0／4 tests passed）。**計數不是綁定**——這是「比對範圍過寬」在同一批內的第三次。
- **修法**：在 AST 上鎖住那個屬性本身——找 `<option>` 之 `disabled` 屬性，
  斷言其 initializer 為對 `isHorizonBelowLowerBound` 之呼叫，且**引數逐字**為
  `['h', 'lookaheadLowerBound']`（換掉任一引數即紅），並斷言這樣的綁定**恰一處**。
- **發現者**：`CODEX-R2-P2-01`。
- **mutation**：刪掉該 `disabled` 綁定 ⇒ ④ 轉紅；還原轉綠（`2.1b-M5`）。

### A-009 — S-9 ⑦ 對照組把 CPython 例外當控制流契約（脆弱，R2）

- **A-006 之修法**（期望 `AttributeError` 且訊息含 `table`）**控制力有效**
  ——「所有非空 horizons 一律 raise」之 mutant 實跑 rc=1（8 passed／1 failed）。
- **但**它把**例外型別與直譯器訊息**當成控制流契約：`event_forward_return_table` 首段
  之合法重構（例如先取 `manifest`、或改用 `getattr`）會使該對照組偽陰。
- **修法**：改用**本檔自己的哨兵**——傳入一個只在被讀 `.table` 時丟 `_ReachedManifestTable`
  之 probe 物件，並斷言 `probe.table_reads == 1`。
  「有沒有走過 horizon 驗證區」由此變成**我們自己定義的事實**，不依賴 CPython 行為。
- **發現者**：`CODEX-R2-P2-02`。
- **mutation**：`4.2-M2`（所有 horizons 一律被擋）在新對照組下仍轉紅（已實跑重驗）。

### A-010 — 🔴 前端守衛之驗收由「檢查原始碼長相」改為「檢查行為」（R3 三條合併）

R3 三家各自實跑，證明 A-007／A-008 之 **AST 做法本身**擋不住四種壞法：

| 壞法 | 提出方 | 舊 AST 為何綠 |
|---|---|---|
| 函式開頭插誘餌守衛 `if (isHorizonBelowLowerBound(999,1)) return;`，真守衛移到 `await` 之後 | `GROK-R3-P2-01` | ①②③ 判準都是「**第一個**命中之位移」，誘餌就是第一個 |
| handler 之 `return` 換成 `(() => { return; })();` | `CODEX-R3-P2-02` | ② 只要求 then 子樹**任一** `ReturnStatement`，巢狀函式的也算 |
| 把 `disabled` 綁定搬到別的 `<select>` 之 `<option>` | `CODEX-R3-P2-01` | ④ 掃**全檔**之 `<option>`，未錨定目標 `<select>` |

⇒ **問題不在漏了哪一條斷言，而在「用原始碼形狀去證明執行期性質」這件事本身**：
形狀有無限多種等價寫法，逐一列舉是黑名單，永遠列不完
（同 `docs/SCAR_LEDGER.md`「文字問題用白名單機械卡」之判準）。

**裁定：改設計，不是加檢查。**
新增 `frontend/src/lib/lookaheadDepthLock.ts::withHorizonLowerBoundGuard(selected, lowerBound, {notify, proceed})`
——**把整段匯出邏輯包進 `proceed`**。於是：

- 「阻擋早於任何網路動作」**不再是需要檢查的性質**，而是**結構上保證**的事實
  ：`proceed` 沒被呼叫，裡面的 `await` 就不可能發生。
- 該性質因此可用**真正的行為測試**驗：`proceed` 呼叫次數 `== 0`（`lookaheadDepthLock.test.ts`）。
- `page.tsx` 之 AST 測試（`lookaheadDepthLock.page.test.ts`）縮小為**只驗接線**：
  ①委派恰一處（誘餌即紅）②引數逐字 ③**該函式內每一個 `await` 都落在 `proceed` 之內**
  （由位移包含關係判定，不是先後順序）④`disabled` 綁定錨定到
  `data-testid="export-gap3-horizon"` 之 `<select>` 子樹內、引數逐字。
- **mutation**：`2.1b-M4`（守衛選值被架空）／`M6`（await 跑到守衛外）／`M7`（誘餌）／`M8`（綁定引數被換）
  ——四條各自轉紅。

### A-011 — 偵測器沒有負例：空集可以來自「沒漏」也可以來自「沒在看」

- `CODEX-R3-P2-03`：`unregistered_future_columns` 只有「未登記集合 `== set()`」這個**正例**
  ⇒ 把該函式直接 `return set()` 也全綠（實跑 14 passed）。
- `GROK-R3-P2-02`：把過濾器由 `startswith("future")` 窄成 `startswith("future_")`
  ⇒ 小時命名活欄（`future72_*`／`future24_*`）整批退出檢查範圍，`== set()` 仍成立
  ⇒ 以**縮篩後之空集**冒充完整集合相等（實跑 16 passed）。
- **修法**：新增 `…_01b`（五種未登記形態逐一須被抓到）、`…_01c`（無底線形態之定向負例，
  並斷言實際欄集中確實存在該形態——否則負例只是打空氣）、`…_01d`（非 future 欄不得誤報）。
- **mutation**：`1.10-M5`（偵測器掏空）、`1.10-M6`（過濾器窄化）。

### A-012 — 參數面只取單一值：`N=4`、`provenance="trust_me"`

- `CODEX-R3-P2-05`：CSV 標題形態只測 `N=4` ⇒ 正規化若只支援 `4bar` 仍全綠（實跑 14 passed）。
  **修法**：`N ∈ {1,2,3,4,7,11,12}` × `{Return, Drawdown}` × 三形態全參數化，且每組同時驗 `1h`／`12h`。
- `CODEX-R3-P2-04`：未知 provenance 只測 literal `"trust_me"` ⇒ 實作若寫成
  `if provenance == "trust_me": raise`（只拒那一個字串）仍全綠（實跑 13 passed）。
  **修法**：九個值參數化 ＋ 新增 `…_05` 對**封閉集合字面本身**斷言（悄悄放寬即紅），
  並含兩個合法值之正例（防恆紅型假保證）。
- **mutation**：`1.10-M7`（只支援 4bar）、`1.10-M8`（只拒一個字串）。

### A-013 — 共用 traversal 使 baseline 側自我配對

- `CODEX-R3-P2-06`：⑧(a) 之 `pre_names` 與 `now_names` 都由**同一支** `flatten_receipt_schema` 產生。
  共用是 SPEC ⑧(e) 明訂的（validator 與驗收須同一函式參考），但副作用是：
  list 分支若壞掉（改回 `[]`），兩側**一起**變形而自我配對，baseline 根本沒被驗到（實跑 16 passed）。
- **修法**：新增 `…_08a2` —— baseline 側之**獨立 oracle**，不呼叫共用函式，
  直接以 fixture 原始結構逐鍵展開後與共用 traversal 之輸出比對，並附三個字面錨點
  （首欄名／`per_tf.row_id` 存在／改前不得有 `batch.` 前綴）。
  ⑧(e) 之共用函式參考斷言**維持不變**——兩者不衝突：一個驗「同一支」，一個驗「那一支是對的」。
- **mutation**：`1.1-M7`（list 分支掏空）。

### A-014 — 文案斷言以子字串代替逐字

- `COMPOSER-R3-P2-01`／`GROK-R3-P3-01`（同一處，兩家各以不同壞法命中）：
  `expect(msg).toContain('7')` ⇒ 把 `horizonLowerBoundMessage` 改成硬編碼「17 根」
  或改成 `return String(lowerBound)`，兩者都仍全綠（「17」含子字串「7」）。
- **修法**：**逐字**比對整串期望文案；另加「不同下界須得不同字串」（防硬編碼／忽略參數）；
  「不得含『label 正確』」維持。
- **mutation**：`2.1b-M9`（文案硬編碼忽略參數）。

### A-015 — R4 七條：代理物之最後一批（全部便宜機械修法，無設計改變）

R4 之主目的（R3 十條閉合）**全數確認關閉**（codex 逐條重跑 ＋ composer 重跑 mutation
`all_pass=true`）。新出七條，全部附委員實跑存活之壞法，全部成立、全部落地：

| 條 | 代理物形態 | 委員實跑之壞法 | 修法 |
|---|---|---|---|
| `CODEX-R4-P2-01` | ⑥單一參數值 | external／system 任一分支特殊化成只認 `future_4bar_return` ⇒ 13 passed | 兩分支各以 bar／hour／unknown／未登記／CSV 標題形多欄參數化 |
| `CODEX-R4-P2-02` | ①原始碼代替執行期 | loader 改以 `("te"+"sts")` 動態路徑讀 tests 側同 bytes 副本 ⇒ 17 passed | 改行為判準：`load_event_import_contract()` 之輸出須 `== production` 且 `!= baseline`，並斷言兩者確實不同（否則該判準無鑑別力） |
| `CODEX-R4-P2-03` | ①名字綁定代替執行路徑 | validator 內放等價 copied type checker ⇒ 17 passed | 加 monkeypatch **spy**，斷言 helper 被呼叫且**每個宣告欄位各一次** |
| `CODEX-R4-P2-04`＋`GROK-R4-P2-02` | ③子字串＋測孤立函式代替配線 | 守衛改 `deps.notify('7')`／`deps.notify(String(lowerBound))`（根本不呼叫文案函式）⇒ 14 passed | notify 收到者須**逐字等於** `horizonLowerBoundMessage(下界)`；另加「換下界須換文案」 |
| `CODEX-R4-P2-05` | ⑥單一參數值 | 判定改成 `selectedBars === 5 && lowerBound === 7` ⇒ 14 passed | 5 組阻擋 × 5 組放行參數化 |
| `GROK-R4-P2-01` | ③子字串 ＋ ①第一命中（兩層疊加） | 真 select 前插一個 testid **含**該子字串之誘餌 select，再改壞真綁定 ⇒ 4 passed | testid 改 **exact** 比對，且符合者須**恰一個** |

**mutation**：`1.10-M9`／`1.1-M8`／`1.1-M9`／`2.1b-M10`／`2.1b-M11`／`2.1b-M12`，各自轉紅並還原轉綠。

🔴 **一件主委自己抓到、必須記下的事**：為 `CODEX-R4-P2-03` 寫的回歸鎖 `1.1-M9`，
**第一版是無效的**——主委讓「副本」再去呼叫本尊，spy 照樣命中，mutation 沒轉紅。
是因為判準要求「轉紅集合逐一等於預期」、而實跑得到**空集**才被發現。
若判準是「有紅就算過」或「不看紅集合內容」，這條無效的 mutation 會被當成通過。
⇒ **「轉紅集合逐一等於預期」這個判準本身，在本輪救了一次。**

🔴 **另記**：R4 補測後，四條**既有** mutation 之預期紅集合**擴大**
（`1.1-M5`／`1.1-M6`／`1.10-M3`／`2.1b-M9`）——同一壞法多紅幾條，
因為新測試更強。已更新為實測值；**這是收緊，不是放寬**。

## 修訂索引

| 編號 | 標的 | 一句話 | 日期 |
|---|---|---|---|
| **A-002** | Task 4.2 驗證欄 | 「S-9 之 6 條」與 SPEC 之 ≥7 條衝突，以 SPEC 為準；⑦是真缺口 | 2026-08-24 |
| **A-003** | 小時命名欄換算 | SPEC 未定捨入 ⇒ 取 ceil（保守方向），寫進 registry 並 fail-closed | 2026-08-24 |
| **A-004** | Task 2.1b 前端 | 下界**值來源**待 B2／B5 接線；B1 只交鎖定機制 | 2026-08-24 |
| **A-005** | Task 1.10 registry | 🔴 SPEC 把 `future{1,2,4,6}_close_return` 說成小時欄，producer 是 `shift(-N)`＝根；照抄會低估 purge 六倍。以 producer 為準 | 2026-08-24 |
| **A-006** | §G S-9 ⑦ 對照組 | 只驗訊息不含關鍵字 ⇒「全部 horizons 都 raise」照樣綠；改驗控制流走過驗證區 | 2026-08-24 |
| **A-007** | Task 2.1b 前端測試 | vitest 測的是雙胞不是 page；改用 TypeScript AST 鎖真實呼叫點 | 2026-08-24 |
| **A-008** | AST 測試 ④ | 用呼叫次數代替綁定 ⇒ 刪 `<option disabled>` 仍綠；改鎖屬性本身與引數字面 | 2026-08-24 |
| **A-009** | §G S-9 ⑦ 對照組 | 把 CPython 例外型別／訊息當控制流契約；改用自訂哨兵 probe | 2026-08-24 |
| **A-010** | Task 2.1b 前端 | 🔴 用原始碼形狀證明執行期性質＝黑名單，永遠列不完；改設計把匯出包進 `proceed`，性質變成結構保證、可行為測試 | 2026-08-24 |
| **A-011** | Task 1.10 偵測器 | 只有正例 ⇒ 掏空／窄化過濾器皆全綠；補負例與過濾面斷言 | 2026-08-24 |
| **A-012** | Task 1.10 參數面 | CSV 形態只測 N=4、未知 provenance 只測一個字串；改全參數化＋封閉集合字面斷言 | 2026-08-24 |
| **A-013** | Task 1.1 ⑧(a) | 共用 traversal 使 baseline 側自我配對；補獨立 oracle（不與 ⑧(e) 衝突） | 2026-08-24 |
| **A-014** | Task 2.1b 文案 | `toContain` 子字串 ⇒「17」含「7」；改逐字＋不同下界須不同字串 | 2026-08-24 |
| **A-015** | B1 全測試面 | R4 七條代理物（單一參數值／原始碼代執行期／名字綁定代執行路徑／子字串＋第一命中疊加）全數收緊；另記一條無效 mutation 之自查 | 2026-08-24 |

## 戳記

（委員於此 append；格式：
`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>`）

RECONCILE-STAMP: grok APPROVED 2026-08-24 sha256:04482ecab25b2ef3e3e98f34d36f56eacf0712b3a66349ec659b3dbc805b2cf1 task:20260824-GAP3UXTODOD002-X-STAMP-R1
RECONCILE-STAMP: composer APPROVED 2026-08-24 sha256:04482ecab25b2ef3e3e98f34d36f56eacf0712b3a66349ec659b3dbc805b2cf1 task:20260824-GAP3UXTODOD002-X-STAMP-R1
RECONCILE-STAMP: codex APPROVED 2026-08-24 sha256:04482ecab25b2ef3e3e98f34d36f56eacf0712b3a66349ec659b3dbc805b2cf1 task:20260824-GAP3UXTODOD002-X-STAMP-R1
