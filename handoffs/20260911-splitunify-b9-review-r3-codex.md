本輪為 D-002 closure review。R2 自家 closure：`CODEX-R2-P1-01` 未閉（可比時點，重開 `CODEX-R3-P1-03`）；`CODEX-R2-P1-02` 已閉（C3.2 已指定既有 `interval_crosses_split_boundary`，且 obligation gate rc=0）；`CODEX-R2-P1-03` 未閉（重開 `CODEX-R3-P1-05`）；`CODEX-R2-P1-04` 未閉（重開 `CODEX-R3-P1-01`、`CODEX-R3-P1-04`）；`CODEX-R2-P1-05` 已閉於 cluster 粒度（重開的 purged row 契約另見 `CODEX-R3-P1-06`）；`CODEX-R2-P1-06` 已閉於 20 條完整 ID／測試欄與 survivor hash 條目；`CODEX-R2-P2-07` 未閉（重開 `CODEX-R3-P2-01`）；`CODEX-R2-P1-08` 已閉，實跑 `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` 得 rc=0。

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
