# SPLITUNIFY 收尾偵察（consult R1）：四條殘留怎麼做、D1 要不要重審、走哪條修訂程序

brief-kind: consult
task-id: 20260911-SPLITUNIFY-X-CONSULT-R2
findings-round: R1

🔴 **這是偵察／諮詢（consult），不是實作、不是審碼。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（`gate_check` 會誤判為派工）。
🔴 交件檔末段必含三行機械裁決塊（`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`，只准值集；`BLOCKED-BY` 只列本家 P0/P1 ID）；**`STATUS: DONE` 逐字**。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。

## 背景（一句話）
`SPLITUNIFY`（事件切分與 IC 時間切分統一）B1–B4 已收，**未收票**：`R-1`／`R-5`／`SU-RESID-2`／`SU-RESID-3` 四條具名殘留仍在，且 `D1` 範圍裁定當初曾以**已廢止**之「95% 就收」被接受、從未重審（`handoffs/reconcile/20260911-splitunify-b7-review-r1/synth.md:20` 自承）。本輪要決定：**每條怎麼做、做的順序、以及動已戳記 SPEC 要走哪條程序**。

**主委已自產一版**：`handoffs/20260912-SPLITUNIFY-CLOSEOUT-RECON-claude.md`（含碼證與初判）。🔴 **請各自獨立產完整版，不要只審我的**——我的初判可能整段錯，特別是 §2 與 §4。

## 審查對象（原文，非我的轉述）
- `docs/SPLITUNIFY_SPEC.md` §N（殘留原文）、§C-0 決議③與 C-1（D1 裁定）、§G（golden 五組）
- `docs/SPLITUNIFY_TODO.md` §E 殘留表
- 碼：`momentum/Analysis/event_samples/split_projection.py`（投影本體；`build_event_keys` 255-302、多標的 fail-closed 385/402/406/426、同源對證 474-486）、`momentum/core/contracts.py`（`split_per_symbol` 625-695、`_coerce_timestamp_array` 418）、`momentum/Analysis/ic_filter_orchestrator.py:517`（`_base_universe_hash`）、`api/models/event_import_models.py:295-303`、`api/routes/case.py:488`、`api/services/case_import_service.py:1588-1613`、`frontend/src/lib/api.ts:1123`
- 契約：`momentum/Analysis/contracts/split_unify.json`；golden：`tests/golden/splitunify/splitunify_golden.json`
- 程序：`docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` §0／§1／§2

## 🔴 必答（每題都要「立場＋碼證」，且正反兩面各給一句）
1. **R-1 之研究問題是否已被回答？** 主委判「`_base_universe_hash` 輸入含 symbol ⇒ 唯一性已有定義；真正的洞是 `split_per_symbol` 對全部 symbol 傳同一個字面 hash」。①支持此判的碼證；②**反面**：是否存在兩 symbol 合法共用同一 hash 之情形，或 symbol 正規化使兩者碰撞？
2. **R-5 收窄案**（`EventAnalyzeRequest` 加選填 `features_ref{features_path, config_hash}`，None ⇒ 維持現行 event-study-only）是否真能避開「請求模型／前端／契約／UAT 全動」？①碼證；②**反面**：前端不改時 capability 字面／畫面是否會出現無法解釋的狀態？
3. **SU-RESID-3**：加 `row_time_fingerprint` 欄（動 IC 契約與既有 golden digest）vs 維持首尾對證＋把「中間間距」列為永久誠實邊界。①你的選擇與碼證；②**反面**：你沒選的那個方案，最強的理由是什麼？
4. **SU-RESID-2**：`(event_id, timeframe)` 複合鍵之改法，會不會讓既有 5 組 golden 全部重算（＝失去「改壞會紅」的基準）？①實跑或讀碼佐證；②**反面**：若不重算，舊 golden 在多 TF 下是否變成假綠？
5. **D1**（事件掃描端**恆走** event-study-only）：主委提案改寫為**條件式**（拿不到 universe 才走）。①這算不算「推翻既有設計」⇒ 須走 `FROZEN_DOC_AMENDMENT_PROCEDURE` 的 **R（推翻）**而非 **D（延伸）**？②**反面**：若判為 D 延伸，如何說明 C-0 決議③之「恆」字不被改變？
6. **批次切法與依賴**：主委初擬 b8＝R-1、b9＝SU-RESID-2＋SU-RESID-3、b10＝R-5＋D1。①依賴是否正確（我主張 R-5 依賴 R-1 與 SU-RESID-3）？②**反面**：有沒有更省輪次、但不犧牲 fail-closed 的切法？
7. **你認為主委漏掉的殘留／風險**（開放題；若無，明講「無」並說你查了哪些面）。

## 停輪條件
①必答 1–7 皆有立場且正反兩面各有一句；②必答 1、4 附實跑或逐行碼證；③**禁以「三家零 finding」當停輪**；④P0/P1 須說明「不改會在後續批次具體怎麼失敗」。

## 前提
fact-verified: `split_per_symbol` 每 plan 帶 `symbol` 且逐對跑 `validate_split_pair_integrity` → 讀 `momentum/core/contracts.py:625-695`（主委 2026-09-12 自跑）
fact-verified: `_base_universe_hash` 之輸入含 symbol（多標的下每 symbol 一份 hash） → 讀 `momentum/Analysis/ic_filter_orchestrator.py:517-530`
fact-verified: 同源對證只比 plan 首尾兩列 → 讀 `momentum/Analysis/event_samples/split_projection.py:474-486`
fact-verified: `EventAnalyzeRequest` 之 `test_fraction`／`embargo_ms`／`tier_min_test_events` 現況不被使用 → 讀 `api/services/case_import_service.py:1588-1613` 註解自承
fact-verified: 測試面 derive 55／disclosure 22／golden 9／contract 8 → `grep -c '^def test_'` 四檔
fact-verified: 派工前無委員債 → `bash scripts/debt_ledger.sh --has-open` rc=0（派工後預期值: rc=1——本輪 OPEN，非 2）
assumed: `frontend/src/lib/api.ts:1123` 是事件分析之**唯一**前端呼叫點 ⇒ 否證觀測：`grep -rn "events/.*analyze" frontend/src` 出現第二處非測試呼叫。／我跑了：**跑了**（只這一處 fetch，其餘為測試檔）
assumed: 多 TF 複合鍵不影響 `ic_feed.py:109` 之消費端（它已自行依 timeframe 過濾） ⇒ 否證觀測：該檔在複合鍵下需改欄名或改 merge 鍵。／我跑了：**只讀碼、未實跑**

## 攻擊面
- **已排除**（我查過）：切分本體（`split_per_symbol` 已支援多 symbol）、reason 字面來源（封閉集合住契約 JSON）、前端呼叫點數量。
- **我沒查**：多標的真實資料下的 `feature_index` 長度分布；`dedupe.py` 在多 TF 下對 `(label_start_ms, event_id)` 重排是否與複合鍵衝突；golden 重算對 `g5_row_fingerprint_*` 的影響；`lightgbm_analyzer.py:377`／`xgboost_analyzer.py:1162` 之 `"lgb_cv_universe"`／`"xgb_cv_universe"` 假 hash 是否會流進投影路徑。

## ⚠️ 前置
禁改碼；禁在本 repo commit／push；只跑你點名之單檔測試；收尾清 /tmp workdir（保留 `claude-501`）。
