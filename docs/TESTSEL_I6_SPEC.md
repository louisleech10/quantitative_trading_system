# TESTSEL I6 移除日常負擔（TESTREG 記錄器不再每次合併 60 MB 摘要）— SPEC

> 狀態：草案 v5（規格審 r4 處置：`handoffs/reconcile/20261119-testseli6-x-review-r4/synth.md`——讀時彙總改標準 `heapq` 每 nodeid 有界 top-k、撤回「超標改增量快取」、補兩條具名舊算法 oracle 測試與邊界格、chunked 移出 fixture 遷移、recorder 合併測具名改寫、E-2 本輪做逐項取捨；施工中實測發現真實 summary 不合法 ⇒ 新讀者照原合法性判定，另列 E-3）。v4（規格審 r3 處置：`handoffs/reconcile/20261119-testseli6-x-review-r3/synth.md`，8 條採納、1 條延後 E-2）。規格審 r1（`handoffs/reconcile/20261118-testseli6-x-review-r1/synth.md`，8 條全採納）與 r2（`handoffs/reconcile/20261119-testseli6-x-review-r2/synth.md`，10 條全採納）處置：TESTREG 各元件互相依附（使用者裁定之清單審由 V 規則產生、V19／V20 有獨有保護、framepath 閘依 ledger 與 catalog quarantine、heavy_run_guard 需新耗時、`--lf` 非 previously_failed 等價）⇒ 不拆 TESTREG，只移除日常負擔主因。v1 之「呼叫端加 `-p`」與 v2 之「整套取捨刪除」皆撤回；現行需記錄之子行程流程（`testreg_helpers.recorded_pytest` 以 `-p testreg_recorder_plugin`＋`PYTHONPATH=tests/fixtures` 載入記錄器）維持不變。
> 來源：大綱 `handoffs/20261116-testsel-route-outline.md` 末節「現行完成計畫」I6 列；事實 `runs/testsel_route/i6/i6_facts.md`（含 2026-11-19 原型）。
> 業界出處（判準 P0）：append-only 事件紀錄＋讀時彙總（event sourcing／read model 讀時投影，https://martinfowler.com/eaaDev/EventSourcing.html）；pytest 本身之 `--durations`／`--junitxml` 亦為每次執行只寫本次結果、不重寫全史。

## §RISK 風險分級
- **大小**：中（`tests/fixtures/testreg_recorder_plugin.py` 收尾不再合併摘要；`scripts/testreg.py` 摘要讀者改由 ledger 讀時彙總；不改產品碼與數值、不改任何 V 規則與閘）。
- **命中高風險原則**：(b) 跨模組共用路徑——記錄器作用於全部 pytest。
- RISK-HIT: b

## §A 假設與待使用者確認
- 已驗證事實：`runs/testsel_route/i6/i6_facts.md`。原型（同命令各 3 次中位）：現行 12.15 秒、只寫 ledger 5.55 秒、不載記錄器 5.11 秒（收據 `runs/testsel_route/i6/proto_*_time.txt`；首次單次量測 real 14.80〔`runs/testsel_route/i4b/step1_before_time.txt`〕／7.12〔`step1_norec_time.txt`〕）。
- 已確認：使用者 2026-11-18 晚「我要睡了，盡可能快速和平行進行，有問題你跟委員共識決定，不要停下來」。
- 待確認：無。

## §C 約束
- 記錄器每 session 照常寫 ledger（`write_ledger`，`.testreg/ledger/<session>.jsonl`）；不再於收尾讀驗寫 `.testreg/summary.json`。
- 摘要語意不變：每 nodeid 依 started 保留最近 k 筆（k 取 `tests/registry/testreg_schema.json` `summary.k`）；由 ledger 讀時彙總，與現行 `_rebuild` 同一演算法（移入 `scripts/testreg.py` 為唯一實作）。
- 合法性不變：彙總結果以 schema `summary.shape` 驗形（同原 `read_summary`／三讀者），不合法 ⇒ 視同不存在（review 訊號 unknown、previously_failed＝[]、effect 無紀錄）。實測（`runs/testsel_route/i6/why_summary_none.out`）：真實 `.testreg/summary.json` 有 65 個 nodeid 鍵不符 `nodeid_param`（倉庫外暫存檔之 `::test_*`、非 ASCII 函式名、`_tmp_` 探針檔），故現行三讀者在真實資料上一律視為不存在、每 session 收尾皆走 `_rebuild` 全量。本項不改此可觀察行為（改逐筆略過會使 previously_failed 於真實資料由 0 變 310 條／78 檔，`runs/testsel_route/i6/prevfailed_real.out`），列 §N E-3。
- 不改任何 V 規則、catalog、測試變更清單審（使用者裁定；其清單由 pre-commit 之 `testreg.py check --staged` 產生）、framepath 閘之讀取與 quarantine、heavy_run_guard。
- 不以 `--lf` 取代 previously_failed；previously_failed 仍為「各 nodeid 最近一筆 outcome ∈ {failed, error, xpassed}」，來源改為讀時彙總。
- 不改任何既有斷言；只驗「每 session 合併摘要」之既有測試改寫為驗「ledger 照寫＋讀時彙總結果相同」，附 TESTREG 改寫收據。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I6-BUDGET-1 | 無重型跑 | — | tests/registry、tests/governance 受影響檔 | 分鐘級（ledger 加總） | 無 |

## §B 四項平衡實測
- 耗時：判準 S3——同命令改前改後各量 3 次取中位；驗收＝改後對「不載記錄器」之額外 ≤ 1 秒（原型 0.44 秒）。讀時彙總之耗時（實測見下「讀者成本」）只在 `review`／`effect`／framepath 閘／`impact` 時付出，不在提交路徑（`check --staged` 不讀摘要：`grep -n "_review_summary(\|previously_failed_from_summary(\|_summary_nodes(" scripts/testreg.py scripts/framepath_affected_gate.py`）。
- 讀者成本（量測腳本 `runs/testsel_route/i6/reader_cost.py`，真實 `.testreg` 量測時約 11,380 個 ledger 檔（量測後 `ls .testreg/ledger | wc -l` ⇒ 11397），各 3 次中位，`/usr/bin/time -l`，原始輸出 `runs/testsel_route/i6/reader_cost_raw2.txt`）：
  - 現行讀者讀驗 58 MB `summary.json`：real 2.45 秒、峰值 RSS 約 680 MB；現行每 session 收尾合併（讀驗失敗 ⇒ `_rebuild` 全量＋寫 61 MB）：real 6.41 秒、峰值 RSS 約 750 MB。
  - 新讀者 `summary_from_ledger`（標準 `heapq` 每 nodeid 只留 k 筆；鍵格式先短路）：real 4.49 秒、user 2.13 秒、峰值 RSS 約 162 MB。
  - 結論：讀者呼叫一次 real 多 2.04 秒（4.49 對 2.45；新讀者須掃 ledger 全檔，I/O 為主：user 2.13 秒），峰值 RSS 約為現行四分之一（162 對 680 MB）；每 session 收尾之 6.41 秒合併負擔移除。讀者只在 `review`／`effect`／framepath 閘／`impact` 時付出，不在提交路徑。不另設快取層。
  - 檔案大小：`summary.json` 不再重寫（現檔 58 MB 保留不刪、不再成長）；ledger 格式與大小不變。精度：不涉（不改數值）。
- S3 收據（同命令 `/usr/bin/time -p venv/bin/python -m pytest -p no:cacheprovider -q tests/registry/test_conftest_seed.py`，改後與不載記錄器交錯各 3 次，`runs/testsel_route/i6/s3_*_time.txt`）：改後 real 6.90／6.16／6.79（中位 6.79），不載 5.86／5.80／5.92（中位 5.86）⇒ 額外 0.93 秒（≤ 1 秒，判準 S3）。改前同命令中位 12.15 秒（原型收據）。

## §P Phase 與依賴

### Phase 1（依賴：P0a 已提交 7d8cdc88；`tests/fixtures/testreg_recorder_plugin.py` 無並行改動）
**Task 1.1 — 記錄器收尾只寫 ledger**
- 改法：`_finish` 寫 ledger 後不再呼叫 `merge_summary`；讀時彙總之唯一實作為 `scripts/testreg.py` `summary_from_ledger`；記錄器內 `merge_summary`／`read_summary`／`summary_lock`／`_rebuild` 保留（不在收尾呼叫），僅供等價測試以舊演算法對照。
- **驗證**：`tests/registry/test_i6_recorder_optin.py` 改為驗：非巢狀日常 pytest 新增恰 1 個 ledger 檔、`summary.json` mtime 不變；S3 收據（3 次中位，額外 ≤ 1 秒）。改壞對照：恢復收尾呼叫 `merge_summary` ⇒ mtime 斷言轉紅。
- **邊界**：巢狀 session 不寫（`TESTREG_PARENT_SESSION`）；ledger 寫入失敗之 `safe` 吞錯行為不變；`--collect-only` 不受影響。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得停寫 ledger；不得改 ledger 紀錄格式（`testreg_schema.json` `ledger`）。

**Task 1.2 — 摘要讀者改讀時彙總**
- 改法：`scripts/testreg.py` 新增 `summary_from_ledger(repo_root, ledger_dir=None)`（演算法同原 `_rebuild`＋每 nodeid 保留最近 k 筆，以標準 `heapq` 有界 top-k 實作；結果以 schema `summary.shape` 驗形，不合法或 ledger 目錄不存在 ⇒ None）；`_review_summary`（None ⇒ None）、`previously_failed_from_summary`（None ⇒ []）、`_summary_nodes`（None ⇒ {}）改呼叫之；`summary.json` 不再讀寫（既有檔保留不刪）。
- **驗證**（`tests/registry/test_i6_recorder_optin.py`）：
  - `test_i6_summary_from_ledger_equals_legacy_merge`：真實 ledger 子集（`tests/registry/fixtures/i6_ledger_subset/`，自 `.testreg/ledger` 逐位元組複製 24 檔，含一個 nodeid 有 23 筆 > k）逐 session 跑舊 `merge_summary` 累積、以舊 `read_summary` 讀回之 nodes == `summary_from_ledger` 結果，逐鍵逐筆相等。
  - `test_i6_previously_failed_unchanged`：同上之 previously_failed 清單相等且非空。
  - `test_i6_invalid_nodeid_whole_summary_absent_like_legacy`：含不符 `nodeid_param` 之 nodeid ⇒ 舊讀者與新讀者皆視同不存在。
  - `test_i6_summary_boundaries_match_reference`：超 k 留最新、同 started 依 session_id（與檔名序相反）、壞檔／無 session 檔略過、六種 outcome、空目錄 ⇒ {}、不存在目錄 ⇒ None；對不呼叫受測函式之參考計算與舊 oracle 皆相等。
  - 既有 `tests/registry/test_testreg_{recorder,effect,review}.py`、`tests/feature_engineering/test_framepath_disposition.py -k affected_gate` 全綠。
  - 改壞對照（實跑）：top-k 不替換（保留最先讀入之 k 筆）⇒ 2 條轉紅（`runs/testsel_route/i6/mutation_keep_first_k.log`）；拿掉驗形 ⇒ 1 條轉紅（`mutation_no_validate.log`）。
- **邊界**：ledger 目錄不存在 ⇒ None（同現行「summary 不存在」）；任一行 JSON 損毀 ⇒ 整檔略過（同現行 `tests/fixtures/testreg_recorder_plugin.py` `_rebuild`：整檔 `json.loads` 失敗即 `continue`）；無 session 紀錄之檔略過；同 started 以 session_id 定序。
- **既有測試遷移**：
  - `tests/registry/test_testreg_effect.py`、`tests/registry/test_testreg_review.py`：預寫 `summary.json` 之 fixture 改為預寫等價 ledger 檔（`tests/registry/testreg_helpers.py` `write_summary_nodes_as_ledger`），斷言不變。
  - `tests/registry/test_testreg_recorder.py`：`_summary` 輔助改讀 `summary_from_ledger`；`test_summary_rebuilt_from_ledger`（假 summary 不被讀到）、`test_summary_incremental_merge_keeps_valid_existing`、`test_parallel_sessions_merge_all_records`（並行 session 不丟紀錄）斷言不變；`test_mutation_no_lock_loses_records` 改為以標準 `concurrent.futures.ProcessPoolExecutor` 兩個獨立 PID 行程並行呼叫保留之 `merge_summary`（拿掉鎖、以 `multiprocessing` Barrier 使雙方讀完同一種子後才寫；`Future.result()` 使 worker 例外直接失敗），斷言 `got < 3` 不變；新增正對照 `test_legacy_merge_with_lock_keeps_all_records`（保留鎖 ⇒ `== 3`）。改壞對照實跑：worker 直接拋例外 ⇒ 測試轉紅（`runs/testsel_route/i6/mutation_worker_raises.log`）。
  - `tests/governance/test_run_chunked.py`：不遷移——其 `summary.json` 為 chunked 執行器自身產出，與 TESTREG 無關（`grep -n summary.json tests/governance/test_run_chunked.py`）；僅留 gate_cmd 作回歸。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得改 previously_failed 之判定集合；不得改 review 訊號之語意。

## §V 驗證策略與邊界測試目錄
- 單元：Task 1.1、1.2 所列；回歸：受影響之 tests/registry、tests/governance 檔（依 `docs/TEST_SELECTION.md` §5 選）；時間：S3 三次中位收據。
- 收案機械邊界：manifest `docs/manifests/TESTSELI6.json` 之 `gate_cmd` 涵蓋 Task 1.2 等價測試、`tests/registry/test_testreg_{recorder,effect,review}.py`、`tests/governance/test_run_chunked.py`（回歸）與 `tests/feature_engineering/test_framepath_disposition.py -k affected_gate`；最終程式實跑 168 passed、64 deselected、0 warning、rc=0（`runs/testsel_route/i6/gate_cmd_run3.log`）。
- 防假綠：等價測試以真實 ledger 子集對舊演算法逐鍵比對；改寫之既有斷言附 TESTREG 改寫收據。

## §R 回退
- 單一 commit；回退＝revert。

## §N N/A 登記
- §G：N/A — 不改數值、特徵或 ML 路徑。
- E-2 逐項取捨（本輪做最小取捨，不擴成拆除工程）——結論：本項皆保留，理由逐項：
  | TESTREG 元件 | 業界對應 | 不可直接等價之處 | 處置 |
  |---|---|---|---|
  | catalog＋V 規則（含 V19／V20）產生測試變更清單 | `git diff` 測試檔＋程式碼審查；mutation testing | git diff＋審查無機械標記斷言減少／測試刪除；清單審為使用者裁定須委員審 | 保留 |
  | ledger（每 session 一檔、append-only） | pytest `--junitxml`／`--durations`（每次只寫本次） | 同為每次只寫本次；`heavy_run_guard`（估時）、framepath 閘（`quarantine_match` 讀 ledger 紀錄）依其欄位 | 保留（形態已同業界；S3 額外 0.93 秒） |
  | quarantine（catalog） | `pytest.mark.xfail(strict=True)` | xfail 無到期日、證據紀錄與處置出處；framepath 閘 `scripts/framepath_affected_gate.py:234` 讀之 | 保留 |
  | previously_failed | pytest cacheprovider `--lf` | 本 repo 10 支腳本以 `-p no:cacheprovider` 執行（`grep -rln no:cacheprovider scripts/`），`--lf` 無快取可讀；且實測現行值恆為 []（見 E-3） | 見 E-3 |
- E-3：previously_failed 是否改為逐筆略過格式不符紀錄而真正生效（真實資料由 0 變 310 條／78 檔，含重型測試）——為何現在不做: blocked-by: I4b 以 testmon 原生取代日常選取後，`testreg impact`／framepath 閘之選取來源是否保留由 I4b 實測定，previously_failed 之去留併入 I4b 決定。
- 殘留：`test_timeout_registry` V07 既存診斷（每次推送觸發清單審）——為何現在不做: blocked-by: 其改寫收據須於 main 重跑 m1／m2／m3＋compare（TESTREG 流程，`docs/TESTSEL_I2_MERGELIST_SPEC.md` 整類列更正），排 I6 本項提交後另開子項。
