# SPLITUNIFY SPEC v2 / TODO v2 — adversarial review R2（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R2  
family: grok  
findings-round: R2  
標的：`docs/SPLITUNIFY_SPEC.md`（sha256 `84ab732b021b…`）＋`docs/SPLITUNIFY_TODO.md`（sha256 `7d6d4f0c4e90…`），commit `7fd0a255`  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`／禁改 reconcile synth  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0＋canonical 四欄  
SPEC-DIGEST: `docs/SPLITUNIFY_SPEC.md#84ab732b021b`  
TODO-DIGEST: `docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90`  
R1-SYNTH: `handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md`（C1–C13）  
CONSULT-SYNTH: `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`（D1–D8）

### §0 前提宣告（本輪覆核）

fact-verified: 戳記閘 rc=0 → `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` → PASS，body-hash `120b4d042d38…`  
fact-verified: SPEC/TODO hash 與 brief 一致 → `shasum -a 256` → `84ab732b021b…`／`7d6d4f0c4e90…`；HEAD `7fd0a255`  
fact-verified: template_check SPEC/TODO → 兩檔 `TEMPLATE PASS` rc=0  
fact-verified: 事件掃描生產 caller 無 feature universe → `pipeline.py:507-517`（`run_with_params` 不帶 `feature_config`）＋`:654-657`（`_materialize`→`None`）＋`case_import_service.py:1610` 只傳 bars  
fact-verified: `run_event_study_only` **現行**寫入 `n_train/n_test/n_purged = 0` → `pipeline.py:728-734`  
fact-verified: `event_forward_return_table` 支援 `split_plan=None` 且 CI→unavailable、`formal_pooled_inference_allowed=False` → `tables.py:166-172`／`:251`／`:130-149`（**不是**只取 test 段；brief 所引 `:305` 實為 `binary_discrimination_table`）  
fact-verified: `EventTablesPanel` 呼叫 `analyzeEventImport` 但不讀 `resp.capability`；summary 列仍渲染 train/test/purge → `EventTablesPanel.tsx:302`／`:352`；`fmt(undefined)='—'`（`:41-45`）  
fact-verified: L3 reason 字面＝`split_blocked_unverifiable_lookahead`（契約綁定 `l3_lookahead_unverifiable`）→ `lookahead_gate.py:23-30`＋`event_import_contract.json`  
fact-verified: `_degraded_flags` 之 `single_symbol` 唯一下游＝`tables.py:138` 之 `formal_pooled_inference_allowed`  
fact-verified: `holdout_*` 現行只回 row index／split_point，無 ms → `split_preview.py:19-46`  
fact-verified: `extract_event_patterns` 無生產 caller（與 §N R-4 一致）  
assumed: B2 期間 `REDSWEEP` 或本票副作用可能修好既有紅之一 → 未實跑 REDSWEEP；以 Task 1.3／3.1 文字推演（必答 5）  
assumed: 前端目前未顯示 `capability.split` → 以源碼 grep 為證（無渲染點），未開瀏覽器

---

## Verdict：需修補後派工（不可直接進 B1）

v2 已把 R1 之 C1–C13 與 consult D1–D8 **文件層落點對齊**（見必答 7），且 C-0／G-3a/b／12 條 mutation／deselect 驗收等主軸正確。  
但本輪抓到 **1 個 P0**（Task 3.3「沿用既有機制」與「summary 不得出現 n_test」自相矛盾——既有 `run_event_study_only` 正寫入 0）＋數個 P1（事件掃描 UI 不揭露 reason、Task 2.1 ms 契約空、B3 集合相等假紅、G-5 無 oracle）。  
**修補 P0-01＋至少閉合 P1-01／P1-02／P1-04 後才可進 B1**；P1-03／P2-05 可與修補同批寫入 v2.1，不宜留到施工中才發現。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `shasum -a 256 docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md` | SPEC `84ab732b021b…`；TODO `7d6d4f0c4e90…` |
| `git rev-parse --short HEAD` | `7fd0a255` |
| `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` | PASS rc=0 |
| `bash scripts/template_check.sh spec docs/SPLITUNIFY_SPEC.md` | TEMPLATE PASS rc=0 |
| `bash scripts/template_check.sh todo docs/SPLITUNIFY_TODO.md` | TEMPLATE PASS rc=0 |

未跑：`pytest tests/governance`（brief 禁）；未改碼。

---

## 必答 1–8（明確立場＋碼證）

### 1. C-0 落點是否可執行？事件掃描是否永遠走 Task 3.3？`event_forward_return_table` 會怎樣？

**立場：現行生產 EventImport 路徑在本票完工後實質永遠走 Task 3.3（event-study-only），直到另票載入 canonical feature universe。**  
碼證：`case_import_service.py:1608-1613` 只呼叫 `run_with_params`（無 feature universe）；`pipeline.py:512-516`／`:654-657`；本票無 Task 讓 EventImport 載 FF run。Task 3.1 僅把 `pipeline.run` 參數改為選填——給定才投影，未給定→3.3。

**對 `event_forward_return_table`：** brief assumed「退回全樣本會被誤讀為 OOS」**不成立**。該表本來就算**全事件**報酬（`tables.py:210-237` 遍歷 `manifest.table`），**不**過濾 `split_label=="test"`（那是 `binary_discrimination_table` at `:305`）。`split_plan=None` 時：CI→`"unavailable"`（`:251`）、`formal_pooled_inference_allowed=False`＋`reason=no_event_split_plan`（`:130-149`）——方向更保守。事件管線之辨別表本就 `not_computed`（`pipeline.py:542-544`）。

**v2 寫清楚了規則（C-0 決議③／Task 3.3），但沒寫清兩件操作後果：**  
(a) 現行 caller **不會**在本票取得 universe ⇒ 事件掃描端 OOS 數字永久停產；  
(b) 「沿用」之 `run_event_study_only` 現況寫 `n_test=0`（見 P0-01），這才是會被誤讀的假數字，不是 forward-return 表本身。

### 2. Task 2.1 `holdout_boundary` 的 ms 邊界算不算第二份算術？`M-SU-11` 擋得住嗎？

**立場：row index 若嚴格委派既有兩支＝不是第二份切分算術；但 ms 回傳是新產物，缺導出契約時會變成第二份可漂的數字。`M-SU-11` 只擋「不呼叫既有兩支」，擋不住「rows 對、ms 錯」。**  
碼證：既有 `holdout_split_point`／`holdout_test_row_index` 只回 int／`np.ndarray`（`split_preview.py:19-46`）；orchestrator 另用 `_time_bounds_for_rows`（`:553-558`）從 index 物化。Task 2.1 要回 `(…, train_end_ms, test_start_ms)` 卻未寫＝`feature_index[train_rows[-1]]` 還是 `feature_index[test_rows[0]]`、purge 空隙如何表達。驗證只要求 `test_row_index` 與既有函式 `np.array_equal`＋年份窗；`M-SU-11` 目標測試 `-k same_source`。  
⇒ 實作者可用正確 rows＋錯誤 ms（例如忽略 purge 用 `split_point` 兩側）通過 mutation。**修法見 P1-02。**

### 3. C-5 summary 12 鍵在投影下 `single_symbol` 恆亮——正確揭露還是誤導？

**立場：在 Task 3.2 多 symbol fail-closed 期間，`n_symbols` 恆 1 ⇒ `single_symbol` 恆亮是正確的保守揭露，不是 bug；但若不寫進 SPEC，實作端可能「修好」它而放寬 `formal_pooled_inference_allowed`。**  
碼證：`event_split.py:21-30`；下游唯讀 `tables.py:138`（`degraded` 非空 ⇒ `formal_pooled_inference_allowed=False`）。  
⇒ 方向保守＝可接受；缺文件化＝P2-05。

### 4. Task 3.3 新 reason 與既有 `lookahead_split_blocked` 會混淆嗎？v2 寫夠了嗎？

**立場：後端 reason 字面可並存且不同；前端事件掃描頁目前無法區分——v2 不夠。**  
碼證：既有 reason＝`split_blocked_unverifiable_lookahead`（`lookahead_gate.py`＋契約綁定）；新 reason＝`canonical_feature_universe_unavailable`（Task 1.2／3.3）。`types.ts:3189-3190` 有 `capability.reason`，但 `EventTablesPanel.tsx` **零處**讀 `resp.capability`；`:352` 只渲 summary 的 train/test/purge。Task 4.1 只改 IC 分析頁（`ic_filter_orchestrator`＋`ic-analysis/` metadata），**不含**事件 analyze 回應之 capability 揭露。  
⇒ 使用者看到的是「train 0／test 0／purge 0」（現行）或「train —／…」（若真刪鍵），兩種 unavailable **看起來一樣**。見 P0-01＋P1-01。

### 5. Task 1.3 清單時序陷阱：特性還是會卡住施工？

**立場：會卡住施工，不是可接受的「特性」。**  
碼證：Task 1.3 邊界②「變綠 ⇒ 必須主動移出」＋Task 3.1 驗證 (B)「FAILED 集合與清單 **集合相等**，多或少皆 rc=1」。修好一條既有紅而未同步改清單 ⇒ B3 紅；與「本票弄壞一條」在 rc 上不可分。  
**判準／處置：** 改為方向性——實際 FAILED ⊆ 清單（只准變短）；變短須 commit 具名移出。變長＝真迴歸。見 P1-03。

### 6. §G G-5 四項是否可執行？請給具體 oracle

**立場：現行 v2 不可執行——只有名字。** 提案 oracle（可證偽）：

| 項 | 具體 oracle | 可證偽 |
|---|---|---|
| 逐 row test fingerprint | `sha256(json.dumps(sorted(int64 ms of feature_index[test_plan.row_index]), separators=(',',':')))` | 改一員 ⇒ hash 變 ⇒ rc=1 |
| 逐 event assignments／purged IDs | 兩集合各自 `sorted(event_id)` 後 sha256；並斷言互斥且聯集＝event universe | 漏 purge／誤標 ⇒ 集合不等 |
| answer-window 完整性 | ∀ test 事件：`label_end_ms <= max(close_ms of test feature rows)`（或等價：事件 feature_cutoff ∈ test 集合 ⇒ 其答案窗不跨入未隔離區——與既有 event embargo 對照列 diff） | 植入跨界事件仍標 test ⇒ 紅 |
| leakage negative case | 人造：train 側事件之 `label_end_ms` 推進 test 段 ⇒ 必須進 `purged`（reason=`interval_crosses_split_boundary`），不得留 train | 改壞投影把 purged 併 train ⇒ 紅 |

碼證缺口：SPEC §G G-5 全文僅列名；對照 G-1／G-2／G-3b 皆有集合／sha256／獨立 oracle。見 P1-04。

### 7. R1 C1–C13 有無漏落或降級？

| 群集 | v2 落點 | 判定 |
|---|---|---|
| C1 戳記 | 過程項；本輪 stamps rc=0 | CLOSED（前置） |
| C2 簽名＋集合＋單位 | C-4；Task 2.2 | CLOSED |
| C3 deselect／集合相等 | Task 1.3／3.1 | CLOSED（文件）；執行判準過嚴見 P1-03 |
| C4 未匹配⇒purged | C-4 | CLOSED |
| C5 clusters／summary／manifest | C-5；Task 2.2 | CLOSED |
| C6 G-3a／G-3b | §G；Task 2.3 | CLOSED |
| C7 消費者／呼叫點＝0 | Task 3.1 | CLOSED |
| C8 mutation×12 | SPEC §V／TODO §D | CLOSED |
| C9 D-002 post-trim＋入口 | Task 1.1 | CLOSED |
| C10 投影落點／C-0 | C-0；Task 2.1／3.1／3.3 | CLOSED（規則）；執行自相矛盾見 P0-01 |
| C11 兩容器 | C-3；Task 1.2 禁 assignment_states | CLOSED |
| C12 embargo 須 None | C-5；Task 2.2 要點 7 | CLOSED |
| C13 §A2 兩入口 | §A2 | CLOSED |
| consult D1–D8 | C-1…C-9／C-0 | CLOSED（D6＝C-0） |

**未發現 R1 群集被整條漏掉或降級**；新洞來自 v2 新寫的 C-0／3.3／2.1／G-5 可執行性，不是歸屬錯置重演。

### 8. B2 是否仍成立？要不要拆？

**立場：維持 B2 三 Task 同批，不拆。**  
理由：2.1→2.2→2.3 是同一條因果鏈（builder→投影→golden）；拆開會在「有函式無 golden」窗口放行半套。規模標「大」已誠實。依賴鏈若被迫拆：`2.1` → `2.2` → `2.3`（嚴格串行），成本＞收益。B3 三 Task（接線／fail-closed／event-study-only）同理維持。

---

## GROK-R2-P0-01

**斷言**: Task 3.3 同時要求「沿用既有 `run_event_study_only`」與「`summary` 不得出現 `n_train`／`n_test`／`n_purged`」，但既有實作正把這三鍵寫成 `0`——兩條約束互斥，Agent 無法同時滿足。

**碼證**: `momentum/Analysis/event_samples/pipeline.py:728-734`（`summary.update({"n_train": 0, "n_test": 0, "n_purged": 0, ...})`）；SPEC／TODO Task 3.3 實作要點 2「`summary` 不得出現 `n_train`／`n_test`／`n_purged`」＋要點 3「沿用既有機制…不新造」＋驗證 `assert "n_test" not in summary`；C-0 決議③亦寫「沿用既有機制」。RECHECK：`sed -n '728,734p' momentum/Analysis/event_samples/pipeline.py`；對照 TODO Task 3.3 驗證段。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[BLOCKING] 信心度=High。會怎麼失敗：實作端 (A) 原樣沿用 ⇒ 驗收 `not in summary` 恆紅；或 (B) 刪三鍵 ⇒ 改變既有 L3（`lookahead_split_blocked`）路徑之 summary 形狀，卻被「不新造／沿用」文案擋嘴，且未規定是否連 L3 一併改。前端 `EventTablesPanel.tsx:352` 今日對 L3 顯示「train 0／test 0／purge 0」——正是 C-0 要禁的假 OOS 數字。  
**修法**：在 Task 3.3（與 C-0）明示三選一並寫進驗證——① 修改 `run_event_study_only` **刪除**三鍵（L3 與新 reason 共用新形狀；附回歸測試：兩 reason 皆 `"n_test" not in summary`）；② 保留三鍵但改為 `null` 且前端不得當計數渲染（較弱，不推薦）；③ 新 reason 走專用 summary 形狀、L3 暫留 0 並登記 §N 殘留。推薦①。同步要求事件掃描 UI 顯示 `capability.reason`（見 P1-01）。

---

## GROK-R2-P1-01

**斷言**: v2 宣稱「前端事件掃描頁只讀 `capability`、兩條 unavailable reason 並存即可區分」，但事件 analyze 的 UI（`EventTablesPanel`）從不渲染 `capability.split`／`reason`；Task 4.1 只覆蓋 IC 報告 metadata，擋不住事件掃描端混淆。

**碼證**: `frontend/src/lib/types.ts:3189-3190`（型別有 reason）；`EventTablesPanel.tsx:302` 收 `analyzeEventImport` 回應、`:352` 只渲 summary 計數、全文無 `resp.capability`；既有 reason 字面 `split_blocked_unverifiable_lookahead` vs 新 `canonical_feature_universe_unavailable`；Task 4.1 修改檔＝`ic_filter_orchestrator.py`＋`frontend/.../ic-analysis/`（disclosure），無事件 analyze 面板。RECHECK：`grep -n capability frontend/src/components/ic-analysis/EventTablesPanel.tsx`（僅 table-level `capability_status`）。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MAJOR] 信心度=High。會怎麼失敗：Task 3.3 後端測過 reason 字面，使用者畫面仍無法分辨「深度不可證」vs「無 feature universe」；若再疊 P0-01 的 `n_test=0`，更像「切了但測試段為空」。  
**修法**：Task 3.3 或 4.x 增「事件掃描頁必顯 `capability.split`＋`reason`（兩 reason 各一條 vitest）」；`EventTablesPanel` 在 `split==unavailable` 時改標「未執行切分／原因＝…」，禁再顯示 train/test/purge 計數列。

---

## GROK-R2-P1-02

**斷言**: Task 2.1 的 `holdout_boundary` 回傳 `train_end_ms`／`test_start_ms` 未定義由 row index 如何導出；`M-SU-11` 只驗證「呼叫既有兩支／row 逐值相同」，擋不住 ms 第二套算術。

**碼證**: TODO／SPEC Task 2.1 簽名與驗證（row `np.array_equal`＋年份 ∈[2015,2035]）；`split_preview.py:19-46` 既有兩支無 ms；`M-SU-11`「不呼叫既有兩支」；對照 orchestrator `_time_bounds_for_rows`（`ic_filter_orchestrator.py:553-558`）已有「由 rows＋index 物化」先例卻未被 Task 2.1 引用為唯一公式。RECHECK：假設 rows 正確但 `test_start_ms=feature_index[split_point]`（略過 purge）⇒ `-k same_source` 仍綠。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=High。會怎麼失敗：接線端若誤用 ms 做成員判定（違反 C-4 集合語意）或當 boundary_hash 輸入，會與 row 集合分歧且 mutation 不紅。  
**修法**：寫死 `train_end_ms = as_ms(feature_index[train_rows[-1]])`（空 train⇒`None`）、`test_start_ms = as_ms(feature_index[test_rows[0]])`（空 test⇒`None`）；ms **僅揭露／hash**，禁止回流做 ∈ 判定；驗證加 `assert ms == derived_from_rows`；`M-SU-11` 擴成 rows＋ms 同源。

---

## GROK-R2-P1-03

**斷言**: Task 1.3 凍結之 known-failure 清單與 Task 3.1 驗證 (B)「集合相等」合起來，會把「B1→B3 期間修好一條既有紅」判成與「本票新增失敗」相同的紅——卡住施工並誘導改驗收。

**碼證**: TODO Task 1.3 邊界②；Task 3.1 驗證 (B)「多或少皆 rc=1」；HANDOFF「既有紅盤點」非本票造成且另立 `REDSWEEP`。RECHECK：清單含 A；B2 期間 A 變綠且未改清單 ⇒ (B) 實際 FAILED ⊂ 清單 ⇒ rc=1。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=High。  
**修法**： (B) 改為實際 FAILED ⊆ 清單（只准變短）；變短必須同步改清單＋commit 具名；變長＝fail。Task 1.3「覆蓋風險：只准變短」與驗收指令對齊。

---

## GROK-R2-P1-04

**斷言**: SPEC §G 之 G-5 四項（row fingerprint／event IDs／answer-window／leakage negative）只有名稱，沒有 oracle 與可證偽命令，Agent 無法實作 Task 2.3 之 G-5，亦無法滿足 C-1 附帶約束②。

**碼證**: SPEC §G G-5 全文僅列舉；對照 G-1（成員集合）、G-2（sha256）、G-3b（獨立 oracle 集合相等）皆有比對方式；consult D1／`CODEX-R1-P1-02` 要求此四項。RECHECK：讀 Task 2.3 要點 4——同樣只列名。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MAJOR] 信心度=High。RISK-HIT 含 a,d ⇒ §G 不可空殼。  
**修法**：把本檔必答 6 之四列表寫進 §G G-5 與 Task 2.3（含負向植入步驟與期望 reason 字面）。

---

## GROK-R2-P2-05

**斷言**: 投影路徑在多 symbol fail-closed 期間 `summary.degraded` 之 `single_symbol` 恆亮；SPEC／TODO 未聲明此為預期，實作端可能誤「修正」而放寬 formal pooled 閘。

**碼證**: `event_split.py:21-30`；Task 3.2 多 symbol⇒raise ⇒ 存活路徑 `n_symbols==1`；`tables.py:138`；Task 2.2 要點 6 只要求 12 鍵齊全與 docstring，未寫恆亮預期。RECHECK：`grep -rn single_symbol momentum/Analysis/event_samples`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MINOR] 信心度=High。效果保守（`formal_pooled_inference_allowed` 恆 False）⇒ 非行為 bug。  
**修法**：Task 2.2 補一句「fail-closed 期間 `single_symbol` 恆亮為預期；不得為讓 `formal_pooled_inference_allowed=True` 而清空 degraded」。

---

## 被當成事實的未驗證假設（§0）

1. brief assumed「無 universe ⇒ forward-return 表失去 OOS／被誤讀為 OOS」→ **本輪否證**（表本就全樣本＋`None` 計畫已 fail-closed；真風險在 summary 的 `n_test=0` 與 UI 不顯示 reason）。  
2. brief assumed「Task 1.3 清單 B1→B3 不變」→ **保留為風險**；處置見 P1-03（改判準，不是假設它不變）。  
3. C-0／Task 3.3「沿用既有機制」被寫成彷彿現況已符合「無假 n_test」→ **不成立**（`pipeline.py:728-734`）；見 P0-01。

## §1 十一類摘要

1. 矛盾/互斥：P0-01（Task 3.3 自相矛盾）  
2. 漏項/端到端：P1-01（事件掃描 capability UI）  
3. 不可測驗收：P1-04（G-5）；P1-03（集合相等假紅）  
4. 可疑 quant：P1-02（ms 第二算術風險）；single_symbol 恆亮＝保守（P2-05）  
5. 過度工程：無（B2 維持三 Task）  
6. OOM/並行：無  
7. Cache：無  
8. API/型別：P1-01（型別有、UI 無）  
9. 測試品質：P1-03／P1-04；mutation 12 條文件層 OK、ms 洞見 P1-02  
10. Agent 可執行性：P0-01／P1-02／P1-04  
11. 必要性/短命工：無（Task 存活至／覆蓋風險欄位與語意大致相符）

---

ASSUMPTIONS_VERIFIED: stamps rc=0；SPEC/TODO digest＝brief；template_check 兩檔 PASS；`run_event_study_only` 寫 n_test=0；forward-return 表支援 None 計畫；EventTablesPanel 不渲染 capability；holdout_* 無 ms；single_symbol 唯一下游 tables.py:138  
TESTS_RUN: shasum／stamps_check／template_check×2（上表）；未跑 pytest governance／Analysis 全套  
FAILURES_SEEN: none（唯讀）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: 無（未改碼）；建議修補將改 Task 3.3／§G G-5／Task 2.1 契約與事件 UI 驗收  

STATUS: DONE
