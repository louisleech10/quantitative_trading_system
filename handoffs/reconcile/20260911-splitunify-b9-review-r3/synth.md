# Reconcile — 20260911-splitunify-b9-review-r3

**來源** 20260911-splitunify-b9-review-r3-codex.md, 20260911-splitunify-b9-review-r3-composer.md, 20260911-splitunify-b9-review-r3-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

🔴 R2 之閉合狀況：**composer 已 `proceed`**（本輪僅 sentinel）；**grok 兩條全閉**但新開三條 P1；
**codex 零條閉合**、九條 P1 中有四條明指「R2 某條**未閉**」。本輪 15 條歸七群，**全部採納**。

🔴 **主委已逐條自驗四項可機械查證之指控，全部成立**：①探針檔不在 repo（`git ls-files` 追蹤數 0）
②`docs/SPLITUNIFY_TODO.md:470` 仍標 `needs-research` ③`pipeline.py:747` 仍必傳 `selected_timeframe`
④`split_projection.py:441-444` 之 `event_id` 重複 guard 排在同側判定之前。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| 核心目標仍未達成：只改 producer、未改唯一生產 caller——「Task 9.2 宣稱「不可保留預設只取一個 TF」，但實際 canonical pipeline 仍要求並明示傳入 `selected_timeframe`」／「`Task 9.2` 雖寫「producer 停止單選、輸出全量 keyed rows」，但檔案範圍僅 `build_event_keys`」 | P1 | CODEX-R3-P1-04, GROK-R3-P1-02 | 採納（🔴 **主委實跑確認**：`pipeline.py:747` 為 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`，**必傳**。我上一輪自以為補上了核心目標，實際只改了被呼叫端 ⇒ 生產路徑的靜默丟棄**原封不動**。修訂：`Task 9.2` 檔案範圍須含 `pipeline.py` 之 caller 與其設定來源，並配「生產路徑不再丟列」之驗收） |
| 可比時點只要求「先定義」而未定義，且與 §V 驗收句互斥——「D-002-C3 (3.1) 只要求「先定義可比時點」，沒有實際定義、來源、Task 或可驗收欄位」／「`(3.1)` 要求「先定義同一事件之可比時點」卻未給出任何可操作定義」 | P1 | CODEX-R3-P1-03, GROK-R3-P1-01 | 採納（我把問題往後推而非解決：寫下「須先定義」本身不是定義，且 §V 的 ASSERT 仍假設可對各 feature TF 獨立判 train／test，與該義務互斥。修訂：**在本延伸內直接給出可操作定義**（例如以 `decision_at_ms` 為錨、各 feature TF 之 cutoff 皆須映射到同一 split 邊界側），並同步改寫 §V） |
| 投影入口之 `event_id` 重複 guard 排在同側判定之前，使 C3 不可執行——「即使把 `build_event_keys` 改成全量多 TF，現行投影入口的 event_id 重複 fail-closed guard 仍會在 C3 同側判定之前拒絕合法的同事件多 TF rows」 | P1 | CODEX-R3-P1-02 | 採納（**主委實跑確認** `split_projection.py:441-444` 該 guard 存在且位置如其所述。這是**順序**問題，我完全沒想到：不先處理它，C3 的異側 purge 與同側不誤 purge 兩條測試都寫不出來。修訂：`Task 9.2a` 須明定該 guard 改為「複合鍵唯一」判準並指定其與 C3 的先後） |
| `§A` 之 FACT-RECEIPT 不可重現——「D-002 §A 的核心 multi-TF FACT-RECEIPT 不可重現：它宣稱 `venv/bin/python probe_b9_multitf.py` 已輸出四組結果，但 repository 沒有該檔案」 | P1 | CODEX-R3-P1-08 | 採納（🔴 **直接違反驗證保真度鐵律**：receipt 的意義在於別人能重跑，而我把探針留在 session 暫存目錄。**已修**：探針移入 `handoffs/20260911-splitunify-b9-probe-multitf.py` 並改寫 §A 之命令路徑） |
| 驗收面缺口：purged 複合鍵、API／前端接線、golden 平行組生成入口皆未指定——「Task 9.2a 要求 `purged` 加 `feature_timeframe`，C3 要求混側時同一事件「所有列」purged，但 §V 只驗 assignment 複合鍵唯一與 event-level 守恆」／「Task 9.1 要求 discarded 由 projection 傳到 API 與前端終端面板，但任務沒有指定 service／route／response field 的接線」／「§G／Task 9.5 要求新增兩標的交錯平行 golden group，但現有 golden freeze script 與任務檔案清單沒有可生成／驗證該 group 的入口」 | P1 | CODEX-R3-P1-06, CODEX-R3-P1-07, CODEX-R3-P1-09 | 採納（三條同型：我寫了**要達成什麼**卻沒寫**由誰、在哪、如何驗**。修訂：§V 補 purged 複合鍵唯一與 `n_event_tf_rows_purged` 斷言；`Task 9.1` 指名 service／route／response field；`Task 9.5` 指名 `freeze_splitunify_golden.py` 之平行組生成入口） |
| 舊語意殘留與邊界不可機械判定——「D-002-C5 (5.2) 仍把核心 producer 寫成「選定 feature TF 後、event_id 唯一」」／「D-002-C6 (6.2) 對 baseline `n_test` 的例外與 Task 9.4 的廣義改法仍衝突」／「D-002-C0 的「全檔與實作不得再用裸 `timeframe`」仍未與 (0.6) 的既有 wire 欄位保留形成可機械判定的邊界」／「D-002 已宣稱解除 `SU-RESID-2`，但 canonical TODO 仍把同一項列為 `needs-research`」 | P1 | CODEX-R3-P1-01, CODEX-R3-P1-05, CODEX-R3-P2-01, CODEX-R3-P2-02 | 採納（四條皆為「改一處漏一處」：(5.2) 仍描述舊單選語意與 `Task 9.2` 矛盾；(6.2) 的 baseline 例外未在 `Task 9.4` 對應；(0.6) 的邊界需可機械判定（建議以「本延伸新建之欄」清單具名）；TODO 之狀態 SoT 須於本延伸通過後同步並在 §N 寫明時點。**主委實跑確認 TODO:470 仍為 `needs-research`**） |
| `M-SU-D2-19` 方向錯誤——「`M-SU-D2-19` 把「survivor 六鍵雜湊未隨複合鍵調整」列為應紅缺陷，但 `D-002-C5` (5.4) 與現行 `ic_feed.event_context_from_windows` 皆定義 survivor 為**事件級**」 | P1 | GROK-R3-P1-03 | 採納（🔴 我為了「補齊 mutation 覆蓋」而加了一條**方向相反**的條目：survivor 本就是事件級，不該隨複合鍵調整，照該 mutation 改反而是引入缺陷。修訂：`M-SU-D2-19` 改為「survivor 六鍵**被**改成含 feature TF」之反向 mutation） |
| 逐項核對後無 finding——「本輪逐項核對後無 finding——R2 本家已 `proceed`（sentinel）」 | P3 | COMPOSER-R3-P3-00 | 採納（sentinel） |

## 主委自評（如實記）

本輪 15 條**全部採納、零駁回**。最該記的是：**我上一輪宣稱「補上核心目標」的 `Task 9.2`，實際上沒有補到**——
只改了 `build_event_keys`，而唯一的生產 caller `pipeline.py:747` 仍必傳 `selected_timeframe`，
生產路徑的靜默丟棄完全沒變。同型的還有 `(3.1)`：我寫「須先定義可比時點」當成解法，
但**寫下「須先定義」不是定義**，等於把問題往後推一輪。
另有一條是我為了讓 mutation 表看起來完整而加的 `M-SU-D2-19`，方向是**反的**。
以及 §A 的 receipt 指向一個不在 repo 的檔案——receipt 不能重跑就不是 receipt。

## 收斂性判斷（為何不引用「停在無法收斂處」）

三輪 findings 有明確收斂方向且家族間有交集（codex 與 grok 獨立指向同一組：核心目標、可比時點、Task 9.2 範圍），
並非各說各話或無限窮舉；R3 的九條 P1 中有四條是「R2 未閉」，成因是**主委修訂不徹底**而非委員擴張要求。
⇒ 續修，不停輪。

## 誠實邊界

D-002 為規格階段產物，本輪無實作、無數值影響。IC 端到端真實 run 仍未跑。

Verdict: 需修補後合併（D-002 依本收斂七群第四次修訂後重審）

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P1-01

**斷言**：D-002-C5 (5.2) 仍把核心 producer 寫成「選定 feature TF 後、event_id 唯一」，並把 `assignments`／`purged` 寫成僅以 `event_id` 標識；這與 Task 9.2 的「移除單選、輸出全量 `(event_id, feature_timeframe)`」及 Task 9.2a 的兩表加欄直接衝突。R2 `CODEX-R2-P1-04`／`P1-05` 因而不能宣稱已閉。

**碼證**：`docs/SPLITUNIFY_SPEC.D-002.md:76` 保留 selected-only／event-only 形狀，`:145-153` 卻要求全量複合鍵與 `feature_timeframe`；`momentum/Analysis/event_samples/split_projection.py:256-303` 仍在 `:279` 過濾 `selected_timeframe`，`:284-292` 對單鍵做唯一性與 `1:1` merge，輸出 `:300-302` 沒有 `feature_timeframe`。實跑 `rg -n -A8 -B3 '5\.2|Task 9\.2a' docs/SPLITUNIFY_SPEC.D-002.md` 同時命中兩組互斥文字。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;momentum/Analysis/event_samples/split_projection.py#99bfddace904

失敗模式／修補方向／信心度：照 C5 實作會讓 `M-SU-D2-20` 紅且保留 SU-RESID-2 靜默丟列；照 9.2 實作又違反 C5 既有唯一性描述。把 C5 (5.2) 改成 post-D002 的 producer／兩表複合鍵契約，並明確保留 manifest／clusters 的事件級粒度；High。

## CODEX-R3-P1-02

**斷言**：即使把 `build_event_keys` 改成全量多 TF，現行投影入口的 event_id 重複 fail-closed guard 仍會在 C3 同側判定之前拒絕合法的同事件多 TF rows；因此 C3 的異側 purge 與同側不誤 purge 測試不可執行。

**碼證**：`momentum/Analysis/event_samples/split_projection.py:438-455` 對 `event_keys` 逐列禁止重複 `event_id`，並以 event_id set 與 event-level manifest 比對；`:528-556` 目前也只組出 event_id-only `assignments`／`purged`。但 D-002 Task 9.2／9.2a 要求同一 `event_id` 的 1h、4h rows 合法共存。具體輸入 `[(E,1h),(E,4h)]` 會先命中 duplicate guard，而不是到 `:530` 後按 feature TF 判側。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f;momentum/Analysis/event_samples/split_projection.py#99bfddace904

失敗模式／修補方向／信心度：若刪除 guard，會失去 R2 要求的 duplicate protection；若保留，合法複合鍵永遠進不了 C3。需明定 `event_keys` 以 `(event_id, feature_timeframe)` 唯一、manifest 以 event_id 唯一，另做 event-ID 集合對證，再以事件聚合側性與產出兩表；High。

## CODEX-R3-P1-03

**斷言**：D-002-C3 (3.1) 只要求「先定義可比時點」，沒有實際定義、來源、Task 或可驗收欄位；合法的不同 cutoff 因而仍可能天然跨 split side，R2 `CODEX-R2-P1-01` 未閉。

**碼證**：`docs/SPLITUNIFY_SPEC.D-002.md:46` 明說契約只要求各 `feature_cutoff_ms <= decision_at_ms`，卻未指定跨 TF 比較的 anchor；§V `:178` 只有 mixed-side purge 與 same-side paired assertions。現行 `alignment.py:197-213` 對每個 `sub_tf` 個別 as-of 取 cutoff。實跑 `venv/bin/python -c 'rows=[("E","1h",1000,"train"),("E","4h",2000,"test")]; decision=3000; boundary=1500; legal=all(cutoff <= decision for _,_,cutoff,_ in rows); mixed={side for *_,side in rows}; print({"legal_asof": legal, "sides": sorted(mixed), "mixed": len(mixed)>1, "cutoffs": [r[2] for r in rows], "boundary": boundary})'` 得 `legal_asof=True`、`mixed=True`。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;momentum/Analysis/event_samples/alignment.py#(未另改動，本輪行號 197-213)

失敗模式／修補方向／信心度：實作者可在未定義 anchor 時一律 purge，誤刪合法事件，或擅自選一個 side，兩者都無法由現行 SPEC 判真偽。SPEC 必須先寫出可比時點的 SoT 與不同 cutoff 的合法／非法條件，再配一個合法同側與異側成對 fixture；High。

## CODEX-R3-P1-04

**斷言**：Task 9.2 宣稱「不可保留預設只取一個 TF」，但實際 canonical pipeline 仍要求並明示傳入 `selected_timeframe`；因此只改 `build_event_keys` 而不改 caller 時，生產路徑的 silent drop 不會消失。這是 R2 `CODEX-R2-P1-04` 的 caller 層未閉合。

**碼證**：`momentum/Analysis/event_samples/pipeline.py:704-747` 把 `selected_timeframe` 列入四個 canonical 必填參數，並在 `:745-748` 以 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))` 呼叫；D-002 `:145-149` 只描述 producer 的 optional filter，沒有要求該 caller 停止明示單選或給出全量 pipeline assertion。故現況仍會走 `split_projection.py:279` 的 selected filter。這直接回答 brief #4：僅 producer 內部改名不等於實際使用者路徑停止丟列。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;momentum/Analysis/event_samples/split_projection.py#99bfddace904

失敗模式／修補方向／信心度：直呼 helper 的雙 TF 測試可能全量通過，但 `EventSamplePipeline.run` 仍傳 selected，形成假綠。把 caller 的 default 行為、明示 legacy filter 及 discarded 傳遞寫成明確契約，並補 pipeline-level 兩 TF row/value 守恆測試；High。

## CODEX-R3-P1-05

**斷言**：D-002-C6 (6.2) 對 baseline `n_test` 的例外與 Task 9.4 的廣義改法仍衝突；R2 `CODEX-R2-P1-03` 未閉。

**碼證**：C6 `docs/SPLITUNIFY_SPEC.D-002.md:90-94` 明定 baseline `n_test` 是實際模型輸入樣本數、不可改成 event count；但 Task 9.4 `:166-168` 只說把 `n_train`／`n_test`／`n_purged` 明確定為事件數，沒有列出 baseline 例外或 baseline 新欄名。現行 `momentum/Analysis/event_samples/baseline.py:105-120` 以 test event IDs 與 `features_at_decision` 交集後用 `len(idx)` 寫 `n_test`；多 TF 物化後該 idx 是模型 row/sample 粒度。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;momentum/Analysis/event_samples/baseline.py#38c7ec473653

失敗模式／修補方向／信心度：若照 9.4 改 baseline，會把 1 event×2 TF 的兩個模型輸入報成 1；若照 C6 例外保留，又沒有可直接驗收的名稱／範圍。Task 9.4 應逐項排除 baseline 的 sample `n_test`，另命名 event count 與 `n_event_tf_rows_*`，配一個 1×2 fixture；High。

## CODEX-R3-P1-06

**斷言**：Task 9.2a 要求 `purged` 加 `feature_timeframe`，C3 要求混側時同一事件「所有列」purged，但 §V 只驗 assignment 複合鍵唯一與 event-level 守恆；沒有 purged 複合鍵唯一、purged row 數或 `n_event_tf_rows_purged` 的可證偽契約。

**碼證**：`docs/SPLITUNIFY_SPEC.D-002.md:151-155` 要求 assignments／purged 兩表加欄，`:177-180` 卻只對 assignments 寫複合鍵唯一、對 purge 寫「全部列」及 event count 守恆；mutation `M-SU-D2-01`～`20`（`:186-205`）沒有 purged schema/row-accounting 專項。現行 `momentum/Analysis/event_samples/split_projection.py:528-556` 每個 event_key 目前只 append `{event_id, reason}`，`:567` 以 `len(purged)` 計數。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;momentum/Analysis/event_samples/split_projection.py#99bfddace904

失敗模式／修補方向／信心度：對 1 event×2 TF 的混側案例，實作可只輸出一筆 event-level purge 仍通過現有 event count assertion，卻丟掉一個 feature-TF row 的 provenance。需補 `purged` 的 `(event_id, feature_timeframe)` uniqueness、逐列 reason、event-level `n_purged` 與 row-level purge count／守恆，以及對應 mutation；High。

## CODEX-R3-P1-07

**斷言**：Task 9.1 要求 discarded 由 projection 傳到 API 與前端終端面板，但任務沒有指定 service／route／response field 的接線；現行事件分析路徑反而固定 event-study-only，不能從目前指定的 projection 變更自然抵達畫面。

**碼證**：`docs/SPLITUNIFY_SPEC.D-002.md:133-141` 只寫「API 事件切分回應」與「前端事件批面板」，`:166-172` 只列「對應 API 模型」而未列檔案或 caller。現行 `api/services/case_import_service.py:1588-1627` 明確呼叫 `run_event_study_only_with_params` 並產生 `capability.split=unavailable`；`api/models/event_import_models.py:306-318` 只有寬 `summary`，`frontend/src/components/ic-analysis/EventTablesPanel.tsx:347-362` 只讀 summary 且在 split unavailable 時不顯示 split counts。這與 9A 的「缺任一層即未完成」不相容。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;api/services/case_import_service.py#d2571793953f;api/models/event_import_models.py#82c83da611f5;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

失敗模式／修補方向／信心度：只在 `EventSplitPlan.summary` 加鍵會讓直接 pipeline 測試通過，但目前 case API／面板仍沒有明確 field／display path，M-SU-D2-02／03 無法驗證。需在 Task 9.1/9.4 指定 route/service/model/前端元件與測試，或明確把事件掃描端揭露移出本票；High。

## CODEX-R3-P1-08

**斷言**：D-002 §A 的核心 multi-TF FACT-RECEIPT 不可重現：它宣稱 `venv/bin/python probe_b9_multitf.py` 已輸出四組結果，但 repository 沒有該檔案；因此「第三次修訂 gates」不能以可重跑證據支撐。

**碼證**：實跑 `venv/bin/python probe_b9_multitf.py` 得 `can't open file .../probe_b9_multitf.py: [Errno 2]`、`probe_rc=2`；同一檢查確認 `frontend/src/lib/eventId.ts` 存在且 `rg -n 'canonicalEventId' frontend/src/lib/eventId.ts` 得 line 26。D-002 `:105-111` 仍把不存在的 probe 當 FACT-RECEIPT，且 Codex Probe A 沒有 path/receipt。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e

失敗模式／修補方向／信心度：reviewer 無法區分主委自產敘述與 repo 中可重跑的 probe 結果；若直接相信，可能把 selected-only 假綠當成全量支持。應提交 probe 到明確 repo path 並附實際輸出 receipt，或把兩條改標未驗證後重跑 closure gate；High。

## CODEX-R3-P1-09

**斷言**：§G／Task 9.5 要求新增兩標的交錯平行 golden group，但現有 golden freeze script 與任務檔案清單沒有可生成／驗證該 group 的入口；`M-SU-D1-23` 不能僅靠手改 JSON 宣稱解除。

**碼證**：D-002 `:123-127` 要求交錯兩標的組且 g5 與單標的不同、各自穩定，`:170-181` 只列 `tests/golden/splitunify/*`、frontend 檔案。現行 `scripts/freeze_splitunify_golden.py:55-90` 固定 `SYM = "ETHUSDT"`、單一 feature index，`:337-352` CLI 只有 `--write`，沒有 symbol/group 參數或 parallel oracle；目前 generator 無法產出 §G 的新 case。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;scripts/freeze_splitunify_golden.py#e331623163d2

失敗模式／修補方向／信心度：只更新 golden JSON 會缺少可重跑的 g2/g3b/g5 來源，且可能覆蓋單標的回歸錨；Task 9.5 應列 generator/oracle/receipt 的具體修改與兩組獨立 assertion，保留舊值後再 freeze；High。

## CODEX-R3-P2-01

**斷言**：D-002-C0 的「全檔與實作不得再用裸 `timeframe`」仍未與 (0.6) 的既有 wire 欄位保留形成可機械判定的邊界；R2 `CODEX-R2-P2-07` 只得到部分修補。

**碼證**：`docs/SPLITUNIFY_SPEC.D-002.md:26-38` 一方面在 (0.1) 下全檔禁令，另一方面在 (0.6) 保留 `per_tf.timeframe`、契約既有鍵，且 (0.2) 範例仍使用 canonical API 的既有 `timeframe` 參數。現行 `alignment.py` 與 `split_projection.py:279-302` 仍依賴 legacy `timeframe` 欄位；新建 projection output 則尚未有 `feature_timeframe`。只有「本延伸是否新建」的抽象邊界，沒有逐欄表或 lint 可判定哪些 bare name 是 frozen legacy。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;momentum/Analysis/event_samples/alignment.py#(未另改動，本輪行號 197-213);momentum/Analysis/event_samples/split_projection.py#99bfddace904

失敗模式／修補方向／信心度：literal rename 會破壞既有 receipts wire shape，不 rename 又違反 (0.1)，造成實作者選擇性解讀。明定「新增識別字」與 frozen legacy 欄位／函式參數清單，並加 round-trip schema 測試；Medium。

## CODEX-R3-P2-02

**斷言**：D-002 已宣稱解除 `SU-RESID-2`，但 canonical TODO 仍把同一項列為 `needs-research`，且理由仍描述「每事件恰一個 selected per_tf row」；治理文件的狀態 SoT 未同步。

**碼證**：D-002 `:3-9` 宣稱本延伸落地 SU-RESID-2、`:211-214` 宣稱解除；`docs/SPLITUNIFY_TODO.md:461-470` 仍將 `SU-RESID-2` 列 `needs-research`，理由明寫本票以 selected single row fail-closed。兩份文件對同一項的完成狀態與現行行為描述相反。

**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#3930f032710e;docs/SPLITUNIFY_TODO.md#e44da6448b01

失敗模式／修補方向／信心度：實作者若依 TODO 會維持單選，若依 D-002 會改全量，且不知哪份應更新。實作前需同步 TODO 狀態／理由或在同一治理入口明定 D-002 覆寫並留下可追溯變更；Medium。

答覆 brief #2：目前不能證明合法事件不被誤 purge，因為 cutoff 可各自合法但跨 side，且可比時點未定；見 `CODEX-R3-P1-03`。
答覆 brief #3：cluster 粒度本身已閉合為 event-level：`event_split.py:59-74` 逐 manifest event 產一列，`cluster_weight=1/n` 以 event rows 計數；同一事件兩 feature TF 若複製 cluster rows，會把 parent event 誤當兩列，故 D-002 的「clusters 不加欄」是正確收斂。purged row contract 仍未閉，見 `P1-06`。
答覆 brief #4：只有直接 helper 改成全量不足；`EventSamplePipeline.run` 目前仍明示 selected，故 silent drop 仍可能存在，見 `P1-04`。
答覆 brief #5：核心衝突集中在 C5／9.2 的 producer schema、C3 的比較 anchor、9.2a／C6 的 purged 與 count 粒度、Task 9.1 API/前端接線、§G generator，以及 C0 legacy naming；本報告已逐項列證。

VERDICT: blocked
BLOCKED-BY: CODEX-R3-P1-01,CODEX-R3-P1-02,CODEX-R3-P1-03,CODEX-R3-P1-04,CODEX-R3-P1-05,CODEX-R3-P1-06,CODEX-R3-P1-07,CODEX-R3-P1-08,CODEX-R3-P1-09
CLOSED:
STATUS: DONE
## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——R2 本家已 `proceed`（sentinel），第三次修訂九群修訂落點均已對位，且對 (3.1) 誤 purge、(6.2) 粒度、Task 9.2 核心、clusters 權重、20 mutation 完整性之主動攻擊未構造出需阻擋實作之 P0／P1。

**碼證**: ①九群表逐段對照（上節＋必答 1）②(3.1) 混側反例 `alignment.py:197-213`＋`split_projection.py:530-553`＋`feature_materialization.py:93-130` ③clusters `event_split.py:33-36,66-74`＋Task 9.2a L154 ④Task 9.2 `split_projection.py:279-303` vs SPEC L145-149＋`M-SU-D2-20` ⑤(6.2) `baseline.py:120` vs `test_splitunify_disclosure.py:282-300` ⑥`obligation_block_check.sh` rc=0 ⑦mutation 20 列 `rg 'M-SU-D2-'`。RECHECK: 重讀上述行號＋重跑 obligation 閘＋`pytest -k build_event_keys_picks_selected_timeframe_only`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/split_projection.py#99bfddace904;momentum/Analysis/event_samples/event_split.py#943d0721b059

P3 sentinel；信心度=High。誠實邊界：IC 端到端真實 run 未跑；(3.1)「可比時點」三字未獨立 prose 定義，但 §V L178 與投影落側邏輯已給 operational 定義——不足以另開 blocking。

## GROK-R3-P1-01

**斷言**: `(3.1)` 要求「先定義同一事件之可比時點」卻未給出任何可操作定義，且 §V 的 `D-002-C3` ASSERT 仍假設可對各 feature TF 獨立判 train／test——與 `(3.1)`「未定義前不得逕行判定異側」互斥；實作者無法同時滿足義務與驗收句。

**碼證**: SPEC L46 `(3.1)` 只有「須先定義…實作不得在未定義可比時點前逕行判定異側」，全文無「可比時點＝decision_at_ms／trigger cutoff／…」；L178 `ASSERT WHEN 某 event 之 1h 判 train、4h 判 test THEN … purged`；`alignment.py:197-213` 各 TF 獨立 as-of cutoff、僅 `cutoff<=decision_at`。RECHECK: `sed -n '46,52p;178p' docs/SPLITUNIFY_SPEC.D-002.md`＋讀 alignment 上列。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/alignment.py#0da3c48b2668

[BLOCKING] 信心度=High。不改則 Task 9.x 實作 C3 時：①自創「以各 cutoff 判側」→ 合法異側 cutoff 事件整批誤 purge（R2 已證之洞回歸）；②自創「以 decision_at 廣播同側」→ 與 §V L178 字面不符、成對 ASSERT 無法寫；③乾脆不做同側檢查 → 非法 OOS 靜默回來。**修法**：在 `(3.1)` **寫死**可比時點操作定義（建議：以該事件之 `decision_at_ms` 相對 train／test 邊界定側，再廣播到所有 feature TF 列；`feature_cutoff_ms` 只做 PIT 閘、不參與側別）。同步改寫 §V C3 ASSERT 與 `M-SU-D2-14`／`15` 使「定義後仍異側」僅在定義被違反時可觸發（或刪除「1h train／4h test」這種 cutoff 異側例句）。**可行性**：投影端已有 per-event `decision_at_ms` 與 per-row cutoff（`split_projection` 迴圈）；側別改由事件級一次判定再廣播，不需新資料欄。

---

## GROK-R3-P1-02

**斷言**: `Task 9.2` 雖寫「producer 停止單選、輸出全量 keyed rows」，但檔案範圍僅 `build_event_keys`、唯一生產 caller `pipeline.py:747` 仍必傳 `selected_timeframe`，且 §V 對 Task 9.2 的 ASSERT 驗的是 9.2a schema 而非全量列——完成字面 Task 9.2 後 live path 的 `SU-RESID-2` 丟棄行為仍可原封不動。

**碼證**: SPEC L145–149（Task 9.2 改法／檔案＝`build_event_keys`）；L177 §V Task 9.2 ASSERT＝`assignments` 含 `feature_timeframe` 且複合鍵唯一（＝9.2a）；L205 `M-SU-D2-20` 指向「全量 keyed rows 測試」但該 ASSERT 未出現在 §V；`pipeline.py:747`：`build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`；`grep -rn 'build_event_keys(' momentum api` → **僅此一處**生產呼叫。RECHECK: 重跑該 grep＋讀 L145–149／L177／`:747`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。Agent 可把 `selected_timeframe` 改成 `Optional`、單測傳 `None` 綠燈、§V schema ASSERT 靠 9.2a 過關，但 pipeline 繼續傳 selected ⇒ 未選 TF 列仍被丟棄，第 9 批核心目標假完成。**修法**：①Task 9.2 檔案清單加上 `pipeline.py`（及日後若有的其他 caller），明定多 TF 分析路徑必須 `selected_timeframe=None`（或不再傳）才輸出全量；單 TF／使用者明示單選才走過濾＋Task 9.1 揭露。②§V 新增／改寫 Task 9.2 ASSERT：`WHEN per_tf 含 1h+4h 且 selected is None THEN 輸出列數＝per_tf 列數且兩 TF 皆在`；schema 唯一性 ASSERT 歸 `Task 9.2a`。③`M-SU-D2-20` 的「應紅之測試」改指上述全量 ASSERT（含經 pipeline 的一條）。**可行性**：全 repo 僅一處生產呼叫；改 signature 預設 `None`＋改 pipeline 一行即可落地，9A 單選揭露路徑仍保留。

---

## GROK-R3-P1-03

**斷言**: `M-SU-D2-19` 把「survivor 六鍵雜湊未隨複合鍵調整」列為應紅缺陷，但 `D-002-C5` (5.4) 與現行 `ic_feed.event_context_from_windows` 皆定義 survivor 為**事件級**（排序後 `event_id`＋label 窗雜湊、不含 feature TF）——照 mutation 字面「調整」成複合鍵會改錯身分語意。

**碼證**: SPEC L204 `M-SU-D2-19`；L80 C5 (5.4)「survivor 六鍵（以排序後 `event_id` 列雜湊）」；`ic_feed.py:57-65` 只序列化 `event_id`／`label_start_ms`／`label_end_ms`。本家 R2 主動攻擊亦判定 survivor **不應**複合鍵化。RECHECK: `sed -n '80p;204p' docs/SPLITUNIFY_SPEC.D-002.md`＋讀 `ic_feed.py:43-74`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/ic_feed.py#741f697b3964

[BLOCKING] 信心度=High。mutation 自證若依字面要求「隨複合鍵調整」，會逼實作把 `feature_timeframe` 打進 manifest hash ⇒ 同事件多 TF 改變 survivor 身分／快取鍵，與 C5 事件級定義及「分析時事件集合身分」契約衝突；若測試其實想鎖「複合鍵落地後仍保持事件級、不得因 TF 展開而漂」，則現行 mutation 措辭寫反。**修法**：重寫 `M-SU-D2-19` 為反向／正向其一——例如「改壞：把 `feature_timeframe` 納入 survivor 雜湊」應紅於「hash 必須仍僅依事件窗」；或刪除該條並在 Task 9.3 註明 survivor／`event_context` 維持事件級、不在複合鍵範圍。**可行性**：`event_context_from_windows` 已是純事件窗；改 mutation 文案零碼阻礙，只需與 C5 對齊一句。

---

