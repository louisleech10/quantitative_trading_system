# SPLITUNIFY SPEC 延伸 D-001 對抗審 R5（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R5  
family: grok  
findings-round: R5  
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（sha256 `82b4e2b544b0…`）  
BASE：`docs/SPLITUNIFY_SPEC.md` @ `b095cc754cb9de26bbf2dd35564db329aca3c98f`（sha256 `3e39458b00e4…`）  
SCOPE: review-only；禁改碼、禁動 tracked 檔、禁 commit／push、禁跑 `tests/governance` 全套  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄  
D001-DIGEST: `docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0`  
BASE-DIGEST: `docs/SPLITUNIFY_SPEC.md#3e39458b00e4`  
PROC-DIGEST: `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914`

### §0 前提宣告（本輪覆核）

fact-verified: 原檔 Task 3.2 自寫「存活至：per-symbol 投影實作後**改寫**為支援分支」「不得只刪 raise」→ `git show b095cc7…:docs/SPLITUNIFY_SPEC.md` 之 Task 3.2 末段（約 L573-575）

fact-verified: `ICSplitAdapter._base_universe_hash` 對整框算一份 joint hash → `ic_split_adapter.py:189-199`；orchestrator 傳入 `split_per_symbol` → `ic_filter_orchestrator.py:907`

fact-verified: 現行同源對證只比首尾兩列 → `split_projection.py:474-484`

fact-verified: `insufficient_events_in_test` 條件與迴圈變數無關、用整批 `n_test` → `split_projection.py:569`（`[s for s in per_symbol_n if n_test < …]`）

fact-verified: 觸及面覆寫／依賴／不觸錨點（去除 markdown `\`` 跳脫後）皆可在 BASE 找到逐字相同 heading → 對讀 BASE L131／L157／L296／L559／L638／L675／L72／L116

fact-verified: `json.dumps` 拒收 `numpy.int64` → `venv/bin/python` 實跑 `TypeError`；對照 D-001-C2 第 1 點 payload 未寫 `int(...)` 強制

fact-verified: SplitPlan 生產寫入點至少三處無指紋欄 → `ic_split_adapter.py:232-253`、`contracts.py:662-685`、`ic_filter_orchestrator.py:631-642`；Task 8.2 檔案清單未列前兩者／orchestrator

assumed: 指紋「另帶 symbol scope 與 provenance」為**旁路欄位**、不入 sha256 payload ⇒ 否證觀測：D-001-C2 第 1 點把 payload 寫死為 `[[row_pos,ts_ms],…]` 之 dumps，未把 symbol／provenance 納入同一 JSON。／本輪以字面解讀，見 P2-02

assumed: Task 8.1 ASSERT「事件 B／只給 A plan」可與 C1.1 字面並存 ⇒ 否證觀測：C1.1 將 `multi_symbol_projection_unsupported` 限於「未提供 Mapping 結構」，該 ASSERT 場景已提供 Mapping。／見 P1-02

---

## 必答 1–9

### 1. 類別判定（D 延伸？）

**立場：D 成立，不升 R。** Task 3.2 已自寫「存活至…改寫為支援分支」「不得只刪 raise」，本延伸即該預告落地；C-2 標題意圖仍是「邊界必須 per-symbol，禁全域 scalar 冒充」，fail-closed 是「投影完成前」的暫行閘，不是永久設計。

**反面：** 若把 C-2 正文「多 symbol 批…**一律 fail-closed**」讀成無期限字面，則與「以 per-symbol 結構投影」互斥、應升 R。本輪不採此讀法——限定語「投影完成前」＋ Task 3.2 存活至已預先授權改寫；對照 D1「恆走」才是真互斥（三家已判 R）。

### 2. 觸及面宣告

**立場：已宣告之覆寫／依賴／不觸錨點逐字存在於 BASE；新增欄正確標「原檔無」。** 實對讀：`### C-2 …P0**）`、`**Task 3.2 — 多 symbol fail-closed（C-2）**`、`## §N N/A 登記與殘留`、`### C-4 …\`feature_index\` 與 \`manifest\``（D-001 內層 backtick 以 `\`` 跳脫，還原後＝BASE L157）、`## §V …`、`## §G Golden / Baseline`、`### C-0 …`、`### C-1 …`。

**反面／缺口：** 觸及面是 SPEC heading 層；Task 8.2 實際會動的 **producer 碼面**（`ic_split_adapter`／`contracts.split_per_symbol`／`ic_filter_orchestrator` 建 plan）未進檔案清單——不是 heading 漏宣告，是 Task 可執行面漏列（升級為 P1-01）。未發現「改了 BASE 某 heading 正文卻沒列進覆寫」的第二處。

### 3. hash 不變式

**立場：碼證支持「跨 symbol 共用同一字面 joint hash」；禁「必互異」閘正確。** `ICSplitAdapter._base_universe_hash(frame,…)` 對整框 hash（`:189-199`），orchestrator `:907` 打進各 symbol plan——現行已發生。

**反面：** 放寬後，**僅靠指紋不足以**防同曆同切分的 plan 互冒（payload 不含 symbol 時兩標的可同 hash）。真正防冒充＝C1.3（事件 symbol ↔ plan.symbol）＋逐 symbol 對自己的 `feature_index` 重算指紋。本檔 C1.2 寫「身分保證改由…D-001-C2 承擔」**過歸**，見 P2-02；C1.3 仍在故不升 P0。

### 4. 指紋定義可重算性

**立場：骨架足夠（epoch ms、依 row_index 排序、緊湊 JSON、sha256），但有未定義處會使兩端不一致。** 未定義：①`row_pos`/`ts_ms` 必須是 Python `int`（`numpy.int64` → `json.dumps` TypeError，已實跑）；②重複 `row_pos`／空 plan 是否 fail-closed 還是 hash `[]`；③「既有型別分派規則」未點名 `_index_as_ms`／`assert_epoch_ms_array` vs `contracts._coerce_timestamp_array`（後者數字預設 `unit="s"`）。

**反面（若認為已足夠）：** 若實作強制走 split_projection 的 ms 分派（DatetimeIndex→`asi8//10**6`；純數字過 `assert_epoch_ms_array`、不猜秒／毫秒），則 `_coerce_timestamp_array` 的秒預設**不會**漏進指紋路徑。但規格未點名該函式 ⇒ 不能當已封閉，見 P2-01。

### 5. golden 重凍

**立場：「改前／改後逐值對照、不得只更新 hash」必要且有助審查，但不足以單獨防「錯值一起凍進去」。** 審查者若只看 hash 變了就簽，对照表仍可能整份錯。

**反面／更便宜可證偽：** 對指紋另加 **獨立 oracle**（由同一 fixture 的 `row_index`＋universe 依 C2 規則重算 sha256，與 plan 欄逐值相等）——不必依賴「改前」舊 digest；與既有 G-3b 同形，成本低於全量 IC golden 考古。建議併入 Task 8.2，不擋作 D→R。

### 6. ASSERT 可證偽性

**立場：8.1／8.2／8.3 多數 ASSERT 改壞會紅**（只取首 symbol、跨 symbol hash 互異閘、`single_symbol` 無條件解除、指紋退回首尾、缺欄放行、門檻退回整批 `n_test`）。

**反面／假綠或缺測：** ①8.1「事件 B／只給 A plan ⇒ 訊息含 `multi_symbol_projection_unsupported`」與 C1.1 字面衝突——跟文件則 ASSERT 紅、跟 ASSERT 則文件假（P1-02）；②無 ASSERT／mutation 覆蓋「跨 symbol 錯配 row_index 數字空間」（C1.4；P2-03）；③8.2 重算兩次只證 helper 決定性，不單獨證比對層（但同 Task 首條 middle-diff 有補）。

### 7. mutation 對照

**立場：`M-SU-D1-01`～`06` 皆能對到會紅的 `-k` 軸（在 ASSERT 依 C1／C2 字面實作的前提下）。**

**反面：** 缺「跨 symbol row_index 混用／用 A 的 plan.row_index 解釋 B 的 feature_index」mutation（C1.4 明文不變式卻無對照）。另 8.2 檔案清單漏 producer 時，`M-SU-D1-05` 可能在測試手造 plan 上綠、生產路徑卻全面缺欄——與 P1-01 同根。

### 8. 範圍切割

**立場：排除 `D1`／`R-5`／`SU-RESID-2` 不留下「b8 一上線就不自洽」的中間態。** b8＝R-1＋SU-RESID-3＋門檻修正後，單 TF 多 symbol 投影可自洽；多 TF 續 fail-closed、事件端續 event-study-only、R-5 未接——皆為既有保守態，非新破綻。

**反面：** 無「非做不可否則 b8 不自洽」的被排除項。R-1 解封後門檻／`single_symbol` 假前提**已**納入 8.1／8.3，切割正確。

### 9. 可否進入實作？

**不可（`VERDICT: blocked`）。** 阻擋：P1-01（指紋 producer 寫入點未進 Task 8.2 檔案清單 ⇒ b8 只改列名檔會讓生產 plan 缺欄、單標的綠徑全滅或把缺欄改軟而假綠）、P1-02（ASSERT 與 C1.1 理由字面互斥 ⇒ 實作必撞一邊）。P2 不擋，但建議同修。

---

## §1 十一類速查

1. 矛盾／互斥：有（P1-02 ASSERT vs C1.1；P2-02 身分歸屬過歸）  
2. 漏項／端到端：有（P1-01 producer）  
3. 不可測驗收：多數可證偽；缺 C1.4 mutation（P2-03）  
4. 可疑 quant 假設：無新假說；hash 放寬有碼證  
5. 過度工程：無  
6. OOM／並行：無  
7. Cache：無  
8. API／型別／相容：指紋欄為契約擴充；須 default 以免非 derive 的 SplitPlan 呼叫點全炸（producer 清單外之相容面，併 P1-01 修）  
9. 測試品質：有缺口（P2-01／P2-03）  
10. Agent 可執行性：P1-01  
11. 必要性／短命工：無（本批即 R-1／SU-RESID-3 落地，非白工）

## 被當成事實的未驗證假設（§0）

1. 「觸及面四欄錨點皆逐字存在」——brief assumed；本輪對讀後**成立**（還原 `\`` 後）。  
2. 「指紋 payload 足以兩端重算一致」——brief assumed 且標未實跑；本輪以 TypeError／分派歧義**否證「已足夠」**（P2-01）。  
3. 「身分保證只由逐 symbol 同源對證承擔」——D-001 當事實寫；同曆下指紋可碰撞，**過歸**（P2-02）。

---

## GROK-R5-P1-01

**斷言**: Task 8.2 要落地 producer-attested `row_time_fingerprint`，但「檔案」清單只列 `contracts.py`／`split_projection.py`／測試與 golden，**未列**實際寫入 `SplitPlan(...)` 的生產點；b8 若只改列名檔，生產 plan 缺欄會被同 Task「缺欄 ⇒ rc!=0」ASSERT 把既有單標的綠徑全滅，或實作者把缺欄改軟而讓 `M-SU-D1-05` 假綠。

**碼證**: D-001 Task 8.2「檔案：`momentum/core/contracts.py`（plan 攜帶指紋）、`…/split_projection.py`（比對）、tests、golden」；對照現行建 plan 處皆無指紋——`ic_split_adapter.py:232-253` `_build_plan_pair`、`contracts.py:662-685` `split_per_symbol`、`ic_filter_orchestrator.py:631-642` holdout 路徑。D-001-C2 第 1 點自寫「producer-attested」。RECHECK: `grep -n 'SplitPlan(' momentum/Analysis/ic_split_adapter.py momentum/core/contracts.py momentum/Analysis/ic_filter_orchestrator.py`

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0

[BLOCKING] 信心度=High。不改會在 b8 實作／收案失敗：①只改清單內檔 ⇒ IC／投影生產路徑 plan 無欄 ⇒ derive 全 fail-closed，單標的回歸紅；②為保綠給欄位 default 且缺欄放行 ⇒ 違反 Task 8.2 第四條 ASSERT 與 `M-SU-D1-05`。修法：Task 8.2 檔案＋實作要點具名列入上述 producer（至少 adapter＋`split_per_symbol`＋orchestrator holdout）；欄位對非 derive 呼叫點給相容 default，但 **derive 入口缺欄仍 fail-closed**；補一條「生產路徑建出的 plan 必帶指紋」ASSERT。

## GROK-R5-P1-02

**斷言**: Task 8.1 固定 ASSERT「事件 symbol=B 但只給 A 之 plan ⇒ 訊息含 `multi_symbol_projection_unsupported`」與 D-001-C1 第 1 點（該字面**僅**用於「呼叫端未提供 per-symbol Mapping 結構」）字面互斥；該場景已提供 Mapping，屬 C1.3 symbol 不一致，不應強行復用同一 reason。

**碼證**: D-001 L26「呼叫端未提供該結構 ⇒ 維持 `multi_symbol_projection_unsupported`」；L32「事件 symbol 與 plan.symbol 不一致 ⇒ fail-closed」；L54 ASSERT 卻要求 B／只給 A plan 時訊息含 `multi_symbol_projection_unsupported`。RECHECK: 對讀 D-001 L24-34 與 L51-56。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0

[BLOCKING] 信心度=High。不改會在 b8 失敗：實作者依 C1.1／C1.3 寫專用 mismatch 訊息 ⇒ ASSERT 紅；依 ASSERT 復用 `multi_symbol_projection_unsupported` ⇒ 與 C1.1 文件互斥，且「沒給 Mapping」與「給了但 symbol 錯」無法分辨，後續 reason 契約／前端映射會漂。修法：ASSERT 改為要求指名 symbol／plan 不一致（或新 reason 字面並同步 `split_unify.json`）；保留 `multi_symbol_projection_unsupported` 只測「未給 Mapping／給了非 Mapping」。

## GROK-R5-P2-01

**斷言**: D-001-C2 第 1–3 點之指紋 payload 未封閉 `int` 強制、重複 `row_pos`、空 plan、以及「既有型別分派」究指 `_index_as_ms`／`assert_epoch_ms_array` 還是 `_coerce_timestamp_array`（後者數字預設秒），兩端可各自合法實作卻算出不同 sha256 或一邊 TypeError。

**碼證**: D-001-C2 L39-42；`contracts._coerce_timestamp_array` L425-426 `unit="s"`；`split_projection._index_as_ms`／`_plan_bounds_as_ms` 走 ms＋`assert_epoch_ms_array`；`venv/bin/python` 對 `json.dumps([[np.int64(1),np.int64(2)]])` → `TypeError`。RECHECK: 重跑該一行＋對讀上述三函式。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0

[MAJOR] 信心度=High；不擋在 P1 修完後的程序類別，但應在進實作前補進 C2／Task 8.2。修法：payload 元素強制 `int(row_pos), int(ts_ms)`；點名正規化函式＝投影側 ms 分派；重複 row_pos／NaT ⇒ fail-closed；空 plan ⇒ 定義為 `sha256("[]")` 或顯式拒收。

## GROK-R5-P2-02

**斷言**: C1.2 稱「身分保證改由逐 symbol 同源對證承擔」過歸——C2 第 1 點 sha256 payload 僅 `[[row_pos,ts_ms],…]`，同交易曆、同切分位置的兩 symbol 可得到相同指紋；防 plan 互冒仍依賴 C1.3 的 `plan.symbol` 對證，且 symbol／provenance「另帶」是否入比對未釘死。

**碼證**: D-001 L31「身分保證改由…D-001-C2」；L39 payload 定義無 symbol；L32 C1.3 才是 symbol 匹配。joint hash 本就跨 symbol 相同（`ic_split_adapter.py:189-199`）。RECHECK: 構思兩 symbol 相同 `row_index`／相同 ms 序列時 payload 字面相等。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0

[MAJOR] 信心度=High。修法：C1.2 改寫為「指紋證 universe 列時刻；symbol 身分另由 C1.3（Mapping key／plan.symbol／事件 symbol）三角相等承擔」；釘死 provenance／symbol 為比對必查欄（或納入 payload）。

## GROK-R5-P2-03

**斷言**: C1.4 明文「跨 symbol 禁共用 row_index 數字空間」，但 mutation 表 `M-SU-D1-01`～`06` 與 Task 8.1 ASSERT 皆無「用 A 的 row_index 解釋 B 的 feature_index／合併時跨 symbol 比較 row 位置」之應紅對照。

**碼證**: D-001 L33-34 C1.4；L77-86 mutation 六列無 row_index 混用；L51-56 ASSERT 無此負例。RECHECK: `grep -n 'row_index' docs/SPLITUNIFY_SPEC.D-001.md` 對照 mutation 表。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0

[MAJOR] 信心度=Medium。不改則 C1.4 只剩散文，b8 收案可在未測該面時綠燈。修法：加 `M-SU-D1-07`＋`-k per_symbol`／專名 ASSERT（錯配 index ⇒ rc!=0 或 assignments 不靜默錯分）。

---

VERDICT: blocked
BLOCKED-BY: GROK-R5-P1-01,GROK-R5-P1-02
CLOSED:
STATUS: DONE
