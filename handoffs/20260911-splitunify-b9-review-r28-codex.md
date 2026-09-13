# SPLITUNIFY b9 review-r28 — codex

審查輸入：`handoffs/20260911-SPLITUNIFY-B9-REVIEW-R28-BRIEF.md`、本輪 diff `git show b1ec3d0c`、D-002 v22 current block。`brief-kind: review`，故 reconcile gate 不阻擋本輪審查。

### 1. r27 findings closure

**Codex 七條**：`CODEX-R27-P1-01 CLOSED`（`--write` 既有鍵缺失探針回 `GOLDEN REFUSE`、`legacy_sentinel` 保留）；`CODEX-R27-P1-02 CLOSED`（同步改寫 v8 與旁檔之正常模式回 `rc=1` 並輸出 `同步改寫檔案與旁檔之繞法在此擋下`）；`CODEX-R27-P1-03 CLOSED`（投影與 oracle 同錯仍被 G-4e 擋下）；`CODEX-R27-P1-04 CLOSED`（`test_mapping_plans_are_rejected_with_named_error` 通過且為具名 `ValueError`）；`CODEX-R27-P2-05 CLOSED`（不一致 `label_end_ms` 的 fail-closed 測試通過）；`CODEX-R27-P2-06 CLOSED`（錨點 guard 先於 duplicate-id guard，缺欄／NaN／重複形態皆為 `ValueError`）；`CODEX-R27-P2-07 CLOSED`（Task 2.2 舊點 1/2/4 已標 `SUPERSEDED`）。

**Grok 三條**：`GROK-R27-P1-01 CLOSED`（同一 `SUPERSEDED` 掃描）；`GROK-R27-P1-02 CLOSED`（`SU-RESID-2` live 條目已明示 producer/schema 與側別錨定關閉，剩下 Task 9.3 下游消費面）；`GROK-R27-P2-01 CLOSED`（SPEC §G／§P／§V 與 pipeline docstring 的 9.2b-pre 內容均為歷史／前版標記，未據此重開 finding）。

**Composer 一條**：`COMPOSER-R27-P2-01 CLOSED`（同一 current-block／歷史段掃描結果）。

重跑命令與觀測：

- `venv/bin/python scripts/freeze_splitunify_golden.py` → G-3b、G-4e、G-5、G-1/G-4/G-5 逐值相符，`GOLDEN OK`，rc=0。
- M1 探針（temp golden、`--write`）：`changed-existing-value RC 0 written_value {'ETHUSDT': 999}`；既有鍵遺失探針：`lost-existing-key RC 1` 且輸出 `GOLDEN REFUSE`。
- 同錯 G-4e 探針 → G-3b 綠、G-4e 紅；M4–M6／邊界定向 pytest → `8 passed`。
- `rg -n 'SUPERSEDED|SU-RESID-2|9.2b 前快照|9.2b-pre' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md momentum/Analysis/event_samples/pipeline.py` → 舊點被標記；另發現下列 live TODO 矛盾，列為本輪新 finding。

### 2. 必答 verdict

#### 2a. body verdict

`dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132`：`REJECTED`。四項 P1 均可在一次修訂中關閉；最小閉合集合就是 `CODEX-R28-P1-01` 至 `CODEX-R28-P1-04`。

## CODEX-R28-P1-01

**斷言**: M1 的「既有頂層鍵集合為超集」不等價於 SPEC/TODO 要求的「既有 11 鍵逐值不變、差異只落在 v9 新鍵」；`--write` 可接受並覆寫既有鍵的不同值。

**碼證**: `scripts/freeze_splitunify_golden.py:505-523` 只計算 `_prev_keys - _new_keys`，沒有任何既有值比較或允許差異集合檢查。`CODE-ANCHOR: scripts/freeze_splitunify_golden.py:505`。`MUTATION: monkeypatch _build_actual()` 將 `actual["g4_per_symbol_n"]` 改為 `{"ETHUSDT": 999}`，以既有 main golden 執行 `main()` with `--write`；實跑輸出 `changed-existing-value RC 0 written_value {'ETHUSDT': 999}`。同一探針加入 `legacy_sentinel` 時才輸出 `lost-existing-key RC 1`，證明目前 guard 只擋丟鍵。

**來源摘要**: scripts/freeze_splitunify_golden.py#afc9390cc451; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2; docs/SPLITUNIFY_TODO.md#a6d888654276

P1，信心度 High。修法：在 `--write` 寫入前載入既有 main，逐值比較契約指定的 11 鍵；任一值改變即 fail-closed；新增鍵只允許 `g1_membership_v9`／`g3b_oracle_v9`，並以 mutation 測試證明既有值改動轉紅。可行性證據：目前既有主檔已列出 v9 新鍵與舊鍵，失敗分支可在 `write_text` 前直接判斷，不需改 golden schema。

## CODEX-R28-P1-02

**斷言**: M2 的三層 runtime 比對仍未完成 current contract：外部 digest 錨實際寫在被審查 helper 的 Python 常數，不在 SPEC §V 的 `V8_BASELINE_SHA256=<64-hex>` literal；且沒有 v8 首次 `O_EXCL` 建立／既存再次建立拒絕流程。

**碼證**: `scripts/freeze_splitunify_golden.py:402-432` 定義 `V8_BASELINE_SHA256` 並在缺檔時直接 return 1，沒有 `O_EXCL`／write-once 建立路徑。`CODE-ANCHOR: scripts/freeze_splitunify_golden.py:405`。`MUTATION: remove both v8 and sidecar, then run venv/bin/python scripts/freeze_splitunify_golden.py --write`；實跑輸出 `GOLDEN V8 MISSING ... (fail-closed)`、`M2_MISSING_RC 1`。同步改寫檔案與旁檔亦回 `M2_SYNC-TAMPERED_RC 1`，但 `rg -n '^V8_BASELINE_SHA256=' docs/SPLITUNIFY_SPEC.D-002.md` 無輸出，故目前只證明阻擋繞法，未證明 SPEC 錨與 write-once 契約已落地。

**來源摘要**: scripts/freeze_splitunify_golden.py#afc9390cc451; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2; docs/SPLITUNIFY_TODO.md#a6d888654276

P1，信心度 High。修法：同一修訂在 SPEC §V 寫入固定 `V8_BASELINE_SHA256=<64-hex>`，helper 只讀該 literal；為 v8 與 sidecar 增加明確 `O_CREAT|O_EXCL` 首次建立，檔案存在時再次建立直接 raise，並補缺檔、同步改寫、二次建立與 SPEC literal 一致性的測試。可行性證據：缺檔與同步篡改兩個現行 probe 已可辨識錯誤分支，新增建立／二次建立測試只需包住目前 `main()` 的 baseline 初始化邏輯。

## CODEX-R28-P1-03

**斷言**: M3 的人手 `expected_side` 是獨立側別字面，但事件時間仍由與投影共用的 `_plans`／`holdout_boundary`／`index` 推導；因此三方側別相等不能檢出 decision timestamp 或 boundary 的共因偏移。

**碼證**: `scripts/freeze_splitunify_golden.py:93-154,179-210` 中 `_event_keys` 以 `index[pos]` 建時間，`_hand_expected_membership` 只攤平 `expected_side`，而 oracle 仍使用同一批 event keys。`CODE-ANCHOR: scripts/freeze_splitunify_golden.py:103`。`MUTATION: monkeypatch _event_keys()` 對每列 `decision_at_ms` 加 1 ms、保持 `expected_side` 與 feature cutoff 不變，再跑 `venv/bin/python scripts/freeze_splitunify_golden.py`；實跑輸出 `M3_DECISION_TIMESTAMP_DELTA 1`、`M3_SAME_SIDE_OUTPUT_ACCEPTED True`，且 golden 仍 `GOLDEN OK`。

**來源摘要**: scripts/freeze_splitunify_golden.py#afc9390cc451; tests/momentum/Analysis/test_splitunify_golden.py#2419bee21dc4; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2

P1，信心度 High。修法：fixture 另以人手 literal 保存每個 event 的 `expected_decision_at_ms`／邊界時間，`main()` 先逐筆比對生成 event key 的 decision timestamp，再做三方 side 比對；保留 `expected_side` 作為獨立側別 judge，並新增 +1 ms mutation 必紅測試。可行性證據：目前 G-4e 已能獨立比對 side，新增欄位只增加一個 fixture 對帳閘，不需讓 hand judge 呼叫投影或 oracle。

## CODEX-R28-P1-04

**斷言**: `docs/SPLITUNIFY_TODO.md:273` 仍有未標 superseded 的 live 邊界規則「事件不在 `feature_index` ⇒ purged」，與 Task 9.2b current contract「`decision_at_ms` 越出 index 範圍必須 raise、不是 purged」互斥；實作者照 TODO 會回退已修正的 fail-closed 行為。

**碼證**: `docs/SPLITUNIFY_TODO.md:271-274` 的 live 邊界列直接要求 out-of-index purged，對照 `tests/momentum/Analysis/test_splitunify_derive.py:1771-1787` 的兩個 raise tests。`CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:273`。`MUTATION: implement the live TODO rule by classifying an out-of-range decision_at_ms as purged; run venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'decision_before_index_start_raises or decision_after_index_end_raises'`；目前正確實作的對照結果為 2 tests passed，該 mutation 應轉紅。

**來源摘要**: docs/SPLITUNIFY_TODO.md#a6d888654276; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2; tests/momentum/Analysis/test_splitunify_derive.py#2419bee21dc4

P1，信心度 High。修法（可直接貼入）：`- 邊界：① event_keys 為空 ⇒ 三態皆空（不 raise）；② manifest.table.decision_at_ms 落在 [index_ms[0], index_ms[-1]] 之外 ⇒ fail-closed raise（訊息含 event_id），不是 purged；feature_cutoff_ms 不參與 split_label；③ train_last_ms < decision_at_ms < test_start_ms ⇒ assignments 空而 purged 為全集（隔離帶合法且預期）。` 可行性證據：現有兩個 out-of-range raise tests 與 728 路回歸已對應 ②，現有 golden 對隔離帶 purged 對應 ③。

### 3. assumed 四條

- M1「處置等效」：**不成立**。上列 P1-01 探針實際寫入既有鍵新值；可落地修法是既有 11 鍵逐值相等＋v9 允許鍵白名單。
- M3「第三份判準」：**不成立**。side 是第三份字面，但 timestamp／boundary 不是；上列 P1-03 的 +1 ms probe 仍接受。
- M6「移動 guard 未改錯誤型別」：**成立**。`venv/bin/python -m pytest -q ...` 8 tests passed；另以缺少 `decision_at_ms`、單欄 NaN、重複 event 混合 NaN 的 malformed manifest probe 均觀測到 `ValueError`，未出現非預期 `AlignmentViolationError`。
- M5「唯一性不擋合法多 TF」：**成立**。`build_event_keys` 的 extreme many-to-one probe 輸出 `M5_MANY_TO_ONE_LABEL_END_VALUES [20, 20]`、`M5_LEGAL_MULTI_TF_UNIQUE True`；不一致值仍由唯一性 guard fail-closed。

### 4. 強制自立詞表掃描

自立詞表：`decision_at_ms`, `feature_cutoff_ms`, `cutoff`, `split_label`, `train_last_ms`, `test_start_ms`, `feature_index`, `index_ms`, `side`, `purged`, `assignments`, `不參與`, `錨定`, `三段式`, `界外`, `SUPERSEDED`。

命令：`{ awk 'NR<335{print}' docs/SPLITUNIFY_SPEC.D-002.md; sed -n '1,$p' docs/SPLITUNIFY_TODO.md; } | rg -n 'decision_at_ms|feature_cutoff_ms|cutoff|split_label|train_last_ms|test_start_ms|feature_index|index_ms|side|purged|assignments|不參與|錨定|三段式|界外|SUPERSEDED'`，再逐段讀取命中行並排除 brief 明定的 HISTORY／沿革／前版標記。

逐段結論：SPEC D-002-C3、§P Task 9.2b、§V 與 §G current block 均以事件級 `decision_at_ms` 定側，明示 `feature_cutoff_ms` 不參與 `split_label`；TODO Task 2.2 的點 1/2/4 已 `SUPERSEDED`，Task 9.2b 與 §E `SU-RESID-2` 亦為 current 語意。唯一未標 superseded 且互斥的 live 命中是 `docs/SPLITUNIFY_TODO.md:273`，即 CODEX-R28-P1-04；其餘命中為 current 相容敘述或歷史追溯。

### 5. Task 9.3 gate

不能進 Task 9.3。最小閉合集合：`CODEX-R28-P1-01`、`CODEX-R28-P1-02`、`CODEX-R28-P1-03`、`CODEX-R28-P1-04`；四項各自有一次修訂內可執行的修法與反向驗證。728 路回歸通過不抵銷四個規格／golden gate 缺口。

### 收尾

VERDICT: blocked
BLOCKED-BY: CODEX-R28-P1-01,CODEX-R28-P1-02,CODEX-R28-P1-03,CODEX-R28-P1-04
CLOSED: CODEX-R27-P1-01,CODEX-R27-P1-02,CODEX-R27-P1-03,CODEX-R27-P1-04,CODEX-R27-P2-05,CODEX-R27-P2-06,CODEX-R27-P2-07
ASSUMPTIONS_VERIFIED: M1 不成立；M3 不成立；M5 成立；M6 成立；M1/M2/M3 探針與 current source anchors 已實跑；詞表掃描定位 TODO:273。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` → 728 passed in 69.06s; 定向 8 tests → 8 passed; `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`; `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → expected hash、rc=0; both `doc_format_precheck.sh` targets → rc=0。
FAILURES_SEEN: 初版 M1/M2 temp harness 曾有 harness-only `relative_to`／cleanup traceback，未影響產品判定；改用 repo-independent temp harness 後取得上述 rc/output。一次錯誤 pytest node 名稱造成 collection rc=4，已改用存在的 8 個測試 node 並 rc=0；completeness 首次抓到 P1-01 缺 `CODE-ANCHOR:`，補字面後以同組參數重跑 rc=0；無產品測試 failure。
SCOPE_CHANGES: 未改程式碼、SPEC 正文或 TODO；僅新增本報告、append D-002 戳記、及新增本 task 交接檔；未觸碰 data_cache/。
NUMERIC_OR_SCHEMA_IMPACT: 無；本輪為 review，未改 runtime、數值、schema 或 golden artifacts。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r28-codex.md
STATUS: DONE
