# SPLITUNIFY D-002 延伸檔找碴 R1 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R1  
family: composer  
findings-round: R1  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md` @ `c4bf6229`（BASE `1be5be3f`、PREDECESSOR D-001）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 跨 TF 不 fail-closed、未選 TF 靜默丟棄 | **fact-verified（本輪複驗）** | 探針 `input_per_tf_rows 4 output_rows 2 UNSELECTED_ROWS_DROPPED 2`（見複驗表） |
| brief fact-verified: 15 處觸及面已碼證 | **assumption，本輪否證** | 記帳／報告鏈另有三處把 assignment **列數**當事件數，未入 15 處表（見 P1-01） |
| brief assumed: 15 處＝全部單鍵消費面 | **否證成立** | 第 16–18 處：`pipeline.py:760-762`、`EventTablesPanel.tsx:361`、`test_splitunify_wiring.py:103-104,113` |
| brief assumed: Phase 9A 可獨立回退 | **assumption，部分成立** | 現行無 `discarded_per_tf_*` 消費者 ⇒ 回退技術可行；但 Task 9.1 未規定 API/前端揭露路徑，9A 單獨上線可能「有欄無人看」（P2-01） |
| brief assumed: 同事件不同 TF 應同簇 | **fact-verified（反例構造失敗）** | 探針：同 `e1` 之 1h=train／4h=test 仍 `time_cluster_id=0`；`event_level` 僅一個 `decision_at_ms`，無法在現架構下構造「應分簇」之誠實反例 |
| brief assumed: `g5` 不受複合鍵影響 | **fact-verified** | `build_row_time_fingerprint` payload 無 `timeframe`；同輸入重算 `same_inputs_same_fp True` |

## 必答 1–5（成對立場）

**1. 觸及面完整性** — **不完整**。15 處表涵蓋 pandas `set_index("event_id")` 主鏈，但漏掉**記帳／報告**把 assignment 列數當事件數的三處（檔案:行見 P1-01）。掃描範圍：`rg 'set_index\("event_id"\)'` 全 repo；`rg 'event_id' api/services/*.py` 過濾 dict/len 模式；`frontend/src` 之 `byEventId`／`n_train`；`tests/golden/splitunify/*`；`momentum/Analysis/event_samples/*.py` 全檔名列表（17 檔含 `keys.py`／`alignment.py`，非單鍵消費）。

**2. 兩階段切分** — **方向正確，但 9A 規格不完整**。9A→9B 順序合理（先揭露靜默丟棄再改 schema）。9A **可**技術性獨立回退（新 summary 鍵尚無下游硬依賴）。中間不一致路徑：9A 後 summary 有 `discarded_per_tf_rows_by_timeframe` 但 assignments 仍單 TF 投影——屬**刻意**揭露，不是缺陷；風險在 9A 若未接 API/前端則使用者仍看不到丟棄（P2-01）。

**3. cluster 語意** — **支持 D-002「同事件同簇」**。反例嘗試：①同事件 1h train／4h test ⇒ 仍同 `time_cluster_id`；②假設 per-TF 不同 `decision_at_ms` ⇒ 與現行 `event_level` 一事件一列矛盾，需先改 alignment 模型，超出本延伸前置。結論：在「一經濟事件一 decision interval」前提下，分簇無反例。

**4. 事件數 vs 列數** — 除 D-002 已列處外，**至少**還有：`pipeline.py:760-762`（`n_train`/`n_test`/`n_purged`＝assignment 列和）、`EventTablesPanel.tsx:356-361`（無單位標註顯示上述三數）、`test_splitunify_wiring.py:113`（`n_train+n_test+n_purged == len(records)` 假設事件級）、`split_projection.py:562,569`（`n_test` 與 `per_symbol_test_n` 取自 assignment 列數）、`ic_feed.py:115`（`n_events=len(keep)` 為 manifest 事件行數，9B 後若 manifest 展開會漂移）、`baseline.py:120`（`n_test=len(idx)` 為交集列數）。複合鍵後 `records=2`、assignment_rows=4 時探針 `wiring_assert_would_fail False`（列數≠事件數）。

**5. §G 與 mutation** — ①`g5` 判斷**正確**（payload 無 TF，本輪實跑未位移）。②`M-SU-D2-01`～`06` **不足**：未覆蓋記帳鏈（`pipeline`/`wiring`/`EventTablesPanel`）、`ic_feed` survivor 六鍵雜湊（觸及面 #13）、`test_splitunify_wiring.py:103-104` 之 `dict(zip(event_id))` 靜默覆蓋。靜默面 #5／7／8／9／10／11／12／14 在 Task 9.3 有 per-site 測試要求，但 mutation 表未對應到報告／接線層。

## COMPOSER-R1-P1-01

**斷言**: D-002「15 處單鍵消費面」清單漏列記帳／報告鏈三處；9B 落地後 `n_train`/`n_test`/`n_purged` 將變成 (event,TF) **列數**卻仍被當**事件數**顯示與斷言，與 §C「不得混用」直接衝突且 Task 9.3 未指派修改。

**碼證**: `pipeline.py:758-762` `n_train`/`n_test`/`n_purged` 皆對 `plan.assignments`/`purged` **行數**求和；`EventTablesPanel.tsx:356-361` 無單位地顯示三數；`test_splitunify_wiring.py:113` `assert res.summary["n_train"]+...+== len(records)`。VERIFY 探針：2 事件×2 TF ⇒ `records=2 assignment_rows=4 wiring_assert_would_fail False`。RECHECK: 重跑上述 python 片段＋讀三處行號。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[BLOCKING] 信心度=High。Task 9.x 實作若只改 15 處表，pipeline 摘要與前端事件表仍會把列數當事件數——使用者看到 train/test 數字膨脹一倍而無標註。**修法**：觸及面表增第四層「記帳／報告」三行；Task 9.2 同時提供 `n_event_tf_rows` 與事件級 `n_events`，Task 9.3/9.4 改 `pipeline._base_summary` 鍵名或加 `_rows` 後綴＋前端 `MetricLabel` 標單位；`test_splitunify_wiring.py:113` 改為對 `n_events` 或複合鍵列數斷言。**可行性**：`EventTablesPanel` 已有 `MetricLabel` 模式；pipeline summary 為 dict 可加鍵不破舊 API（新鍵必填、舊鍵標 deprecated 一個 phase）。

## COMPOSER-R1-P1-02

**斷言**: `M-SU-D2-01`～`06` 未覆蓋 9B 後仍會靜默錯的接線與 survivor 路徑；尤其 `test_splitunify_wiring.py:103-104` 以 `dict(zip(event_id,...))` 對 cutoff／split_label 建映射，同 `event_id` 多 TF 時後者覆蓋前者，mutation 無對應項。

**碼證**: `test_splitunify_wiring.py:103-104` `cutoffs=dict(zip(per_tf event_id,...))`、`labels=dict(zip(assignments event_id,...))`；觸及面 #13 `ic_feed.py:142-145` survivor `manifest_hash` 仍按排序後 `event_id` 列雜湊，多 TF manifest 語意會變但無 `M-SU-D2-*`。§V mutation 僅列 `01`～`06`（`docs/SPLITUNIFY_SPEC.D-002.md:131`）。RECHECK: 讀 wiring 103-104 與 §V 表；對 #13 構造雙 TF 同 event 之 hash 前後對照（實作前標 needs-research）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617;momentum/Analysis/event_samples/ic_feed.py#741f697b3964

[BLOCKING] 信心度=High。實作者照 §V 做完 6 條 mutation 自證即可標綠，但 wiring 接線與 IC survivor hash 仍可靜默錯／假綠。**修法**：增 `M-SU-D2-07`（wiring dict-zip 改回單鍵應紅 `test_splitunify_wiring`）、`M-SU-D2-08`（`pipeline` 用列數填 `n_train` 應紅記帳測試）、`M-SU-D2-09`（`ic_feed` survivor hash 改回 event_id-only 應紅 conditional_ic 契約測試）；各指名應紅測試名。**可行性**：b8 已有 22 條 `M-SU-D1-*` 自證先例；wiring 測試已存在，mutation 只需改一行 zip 邏輯即可觸發。

## COMPOSER-R1-P2-01

**斷言**: Task 9.1 只列 `split_projection` 與 `EventSplitPlan.summary`，未規定 API 模型／前端型別如何揭露 `discarded_per_tf_rows_by_timeframe`，9A「消除靜默丟棄」在目標使用者（事件批 UI）可能達不成。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:103-107` Task 9.1 檔案清單無 `api/`／`frontend/`；`EventTablesPanel.tsx` 現只顯示 `n_train`/`n_test`/`n_purged`（`:356-361`），無 discarded 欄位；`frontend/src/lib/types.ts` 之 event summary 型別亦無該鍵（grep 0 命中）。RECHECK: `rg discarded_per_tf` 全 repo 僅 D-002 規格檔。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[MAJOR] 信心度=High。9A 合併後 momentum 有欄、API 未透傳 ⇒ 產品層仍靜默。**修法**：Task 9.1 增子任務——`api/models`＋event pipeline 回傳 summary 透傳該鍵；`types.ts`＋`EventTablesPanel` 或 `EventBatchDisclosurePanel` 顯示「未選 TF 丟棄 N 列（按 TF 分組）」；驗收加 API test 斷言 JSON 含鍵。**可行性**：`tests/api/test_splitunify_disclosure.py` 已有 split_unify 揭露測試骨架，可平行加 case。

## 主動攻擊面（停輪③）

1. **15 處完整性**：`set_index("event_id")` 掃描＋`api/services` dict 模式＋前端 Map ⇒ 發現記帳鏈三處（P1-01）。
2. **9A 回退**：`rg discarded_per_tf` 無消費者 ⇒ 回退可行；風險在 9A 揭露未接 UI（P2-01）。
3. **cluster 反例**：同事件異 TF 異 split_label 探針仍同簇；改 `decision_at_ms` 需動 alignment ⇒ 無誠實反例。
4. **列數當事件數**：pipeline／前端／wiring 探針（必答 4）。
5. **g5 位移**：`build_row_time_fingerprint` 簽名＋同輸入重算 ⇒ 不位移。
6. **§N 殘留**：`api/services/` 未逐檔讀已在 D-002 §N 誠實邊界具名 ⇒ 不另開 finding，但記帳鏈已用程式碼否證。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| 多 TF `build_event_keys` 探針 | `input_per_tf_rows 4 output_rows 2 UNSELECTED_ROWS_DROPPED 2` |
| 列數≠事件數探針 | `records 2 assignment_rows 4 wiring_assert_would_fail False` |
| cluster 混側探針 | 同 `e1` 1h train／4h test ⇒ 皆 `time_cluster_id=0` |
| `g5` 指紋探針 | `same_inputs_same_fp True` |
| `rg 'set_index\("event_id"\)'` momentum+tests | 10 生產檔（與 D-002 表大體一致）+ 測試檔 |
| `rg discarded_per_tf` | 僅 `docs/SPLITUNIFY_SPEC.D-002.md` |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R1-P1-01,COMPOSER-R1-P1-02
CLOSED:

ASSUMPTIONS_VERIFIED: 多 TF 探針／列數探針／cluster 探針／g5 探針／rg 掃描（見表）  
TESTS_RUN: 見「複驗」表（review 未改碼）；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r1-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查；指出 SPEC 缺記帳鏈與 mutation 缺口）

STATUS: DONE
