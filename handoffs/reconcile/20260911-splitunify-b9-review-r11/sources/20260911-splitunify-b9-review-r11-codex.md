# SPLITUNIFY D-002 R11 — CODEX 唯讀閉合審查

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R11
review-scope: docs/SPLITUNIFY_SPEC.D-002.md v11；對照 D-001、TODO §E、R10 synth；未改碼、SPEC、TODO 或 data_cache。

## CODEX-R11-P1-01

**斷言**: R10 M2 的「producer→summary→metadata 值相等」文字已補，但 v11 仍未定義一條可執行的 producer 結果如何到達唯一 metadata caller；因此孤立 builder 單測可綠而真實 `discarded_rows_by_feature_tf` 遺失。

**碼證**: `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '181,184p'` 指向抽象的 `EventSplitPlan.summary → orchestrator → builder`；`nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '1525,1534p'` 顯示 caller 只傳 `n_test`、timestamps、per-symbol counts；`rg -n -g '*.py' '\.run\(' api` 僅命中非 EventSamplePipeline 的 `uvicorn.run`／`asyncio.run`，AST receiver/canonical scan stdout=`AST_CANONICAL_RUN_HITS 0`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1；momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293；momentum/Analysis/event_samples/pipeline.py#55ca7327764f

P1／信心度 High。若只新增 `discarded` 欄位與手塞 builder 測試，IC production path 沒有 `EventPipelineResult` 或 summary context 可供該 caller 取用，值相等斷言不覆蓋資料流。修法須二擇一明寫：把同一 producer result/context 以具名介面傳入唯一 caller，再跑 producer→summary→metadata E2E；或把 metadata 層明確延後到 `SU-RESID-9A-UI`，不宣稱本票已交付。可行性證據是兩個端點已存在（`EventPipelineResult.split_plan.summary` 與 `build_split_unify_disclosure`），缺的是其間的實際接線與參數契約。

## CODEX-R11-P1-02

**斷言**: R10 M7 雖把 register 機械修成 25 列，但重新掃描後，(5.5)/Task 9.4 明列的 split-count consumers 仍未逐列進 C5 register；「25 是唯一施工清單」因此不能證明記帳路徑完整。

**碼證**: `rg -n 'n_test =|n_purged|per_symbol_test_n|tier_min_test_events|summary\["n_train"\]|summary\["n_test"\]|summary\["n_purged"\]' momentum/Analysis/event_samples/{split_projection.py,pipeline.py}` 命中 `split_projection.py:559-569,684-732` 與 `pipeline.py:757-763`；但 `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '90,118p'` 的 C5-01..25 沒有 `EventSplitPlan.summary`／`_build_summary`／pipeline count rows，C5-23 只列 wiring 映射。register rows=25、mutation rows=32 的機械計數均通過，問題是漏面不是算術。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1；momentum/Analysis/event_samples/split_projection.py#99bfddace904；momentum/Analysis/event_samples/pipeline.py#55ca7327764f

P1／信心度 High。複合鍵落地後，`n_test` 與 `per_symbol_test_n` 若仍以列數計，兩個 TF 可把一事件誤算兩件並繞過 `tier_min_test_events`，正是 Task 9.4 自己描述的風險。修法是把這些具名 code surfaces（含 `pipeline` count output 及其 downstream report/model 若仍在 scope）逐列加入 C5，配 event-id 去重的母斷言與 mutation；重新計數標題／§R 回退句。C5-15/16/17 的 `—` 可保留，因文件已明說是具名缺口，不應為湊非空 mutation 捏造覆蓋；但 `—` 不等於已覆蓋，Task 9.3 gate 必須保留其未覆蓋狀態。

## CODEX-R11-P1-03

**斷言**: R10 M5 的 full-universe `row_index`／local→global rebase 二擇一不是窮盡且沒有一個能照現有 D-001 契約直接落在 projection；照任一未補介面的寫法，合法交錯多標的批會被誤拒或以另一 symbol 解讀。

**碼證**: D-001 明定 `feature_index_by_symbol` 是 local、D-002 projection 只讀 `row_index_local`（`nl -ba docs/SPLITUNIFY_SPEC.D-001.md | sed -n '45,53p;71,82p'`）；既有 `validate_split_pair_integrity(train_plan,test_plan,ts,symbols,...)` 在 `momentum/core/contracts.py:676-700` 直接以全域 `plan.row_index` 索引 `ts/symbols`。本輪實跑 probe stdout=`global row_index + local universe: IndexError plan.row_index contains positions outside base universe`、`local row_index + interleaved universe: CrossSymbolLeakageError SplitPlan row_index must contain exactly its declared symbol`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f；docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1；momentum/core/contracts.py#1471cef968a3

P1／信心度 High。以全域 row 直接餵 local `ts` 產生第一個錯誤；把 local row 假裝 global 在 A/B/A/B universe 產生第二個錯誤。修法應改寫 Task 9.2b 的母斷言位置：在仍持有 full `ts`/`symbols` 的 producer/adapter 先呼叫既有 validator，再把已驗證的 local plans 交給 projection；若堅持 derive 內呼叫，必須新增明確、型別化且不違反 D-001「projection 不收全框輸入／不做轉換」的 validation context。可行性證據是 validator 已有完整全域介面，缺的是合法的呼叫層與上下文，不是再造第三份判定算法。

## CODEX-R11-P1-04

**斷言**: R10 M6 的 `.v8.json`＋`.v8.sha256` 只要求「檔案 digest 等於旁檔」，沒有 write-once 或外部錨定 digest；一個錯誤 baseline 與同步重寫的旁檔即可通過全部明文母斷言，且現有 `--write` 沒有可供拒絕的 target path。

**碼證**: `nl -ba scripts/freeze_splitunify_golden.py | sed -n '337,406p'` 顯示 CLI 只有 boolean `--write`、固定 `golden_path=.../splitunify_golden.json`，寫入使用 `golden_path.write_text`；`ls -l tests/golden/splitunify/splitunify_golden*` stdout 只有 current JSON，`venv/bin/python -c '...'` stdout 列出 11 keys、無 v8。具體 bypass：重凍 helper 將錯誤 current snapshot 寫入 `.v8.json` 後同步重算 `.v8.sha256`，(iii) 的相等檢查為真；沒有 `O_EXCL`、已提交 digest 或拒絕既有 v8 的母斷言能區分這次覆寫。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1；scripts/freeze_splitunify_golden.py#e331623163d2；tests/golden/splitunify/splitunify_golden.json#f270e007ca98

P1／信心度 High。修法須把 baseline 建立設成 write-once（例如既有檔以 `O_EXCL` 建立且既有檔／digest 不得更新），或把預期 digest 錨定在另一個不可由同一 helper 同步改寫的已提交來源；CLI 另設 current-only write，對明確 v8 target fail-closed。可行性證據是 Python/OS 已提供 exclusive-create primitive，現行缺陷落點也已精確在 `main()` 的固定 path 與 `write_text`。

# 必答 1–6

1. R10 自家 finding：`R10-P1-01`（G4e 第三份）已閉合為 literal `expected_side`＋禁止共用 helper，但其人手誤填可同錯的邊界仍誠實保留；`R10-P1-04`（baseline 舊鍵）已在 (6.2)/Task 9.4/§V 三處定為 exact delete；`R10-P1-06`（C5 算術）與 `R10-P2-07`（窄 regex）已分別由 25 列 register、AST 觸發規則閉合。`R10-P1-02`、`R10-P1-03`、`R10-P1-05` 分別由本輪 P1-01/P1-03/P1-04 重開；確認依據是上述實跑 scan、validator probe、current CLI/golden 檢查。
2. 六條 self-cert：①新增落點（G4e/G4d/Task9.2b/§V）有；②正文中的 16→25、old `n_test` 作廢有同步，TODO §E 的 SU-RESID-2 是明示待三家戳記後同步，非漏改；③32 個 mutation 均有對應 §V 母斷言或明示缺口；④mutation rows=32、C5 rows=25 均相符；⑤主要 Task/§V 對稱。⑥沒有把明示 residual 當完成，但 C5 rescan 仍漏掉本輪 P1-02。漏掉的第七種形態是「跨既有介面／座標契約的可實作性」，不是單純文字位置；M5 是反例。
3. C5 register 的 25/25 算術正確，三分類大方向未找到可證明的錯列；但涵蓋不完全，至少漏 `split_projection` summary/threshold 與 pipeline count。C5-15/16/17 的 dash 作為具名缺口比捏 mutation 誠實，但不得被當作 mutation coverage；本輪 P1-02 要求補列真正的 count consumers。
4. `expected_side` 比第三次公式編碼好：R10 probe `cat handoffs/run_receipts/20260912-splitunify-b9-probe-g4e-triple.log` 實測獨立期望錯時 `g4e_pass=False`，三份同錯時 `g4e_pass=True`；literal 人手欄能切斷程式共因，但若人手也把 `decision=250, cutoff=200, train_last=200, test_start=300` 填成 train，三方仍可全等。沒有不依賴可信第三來源的機械解；v11 把此標為非機械保證是足夠誠實，不能宣稱已完全閉合。
5. M6 可由同步重寫 v8 檔與 sidecar 繞過，見 P1-04。M5 兩選項均非完整解：global row + local universe 會 `IndexError`，local row + interleaved universe 會 symbol mismatch；合法落點需把既有全域 validator 放回持有 full context 的 producer/adapter，或補明確 validation context，見 P1-03。
6. 新衝突為 P1-01 的抽象 producer→orchestrator handoff 與現行唯一 caller/無 production `EventSamplePipeline.run`；P1-02 的 register 與實際記帳 consumers；P1-03 的 D-001 local-only 與既有全域 validator；P1-04 的「immutable」用語與可同步改寫 sidecar。G4e 人手邊界、TODO §E 的 delayed sync、既有 golden 11-key 現況本身均已被文件明示，未另列 finding。

# 機械收尾

ASSUMPTIONS_VERIFIED: `handoffs/reconcile/20260911-splitunify-b9-review-r10/synth.md` 確認 R10 13 findings/8 groups 全採納；`venv/bin/python` 計數確認 mutation rows=32、C5 rows=25；current golden keys=11、無 v8；`bash scripts/debt_ledger.sh --round-state 6b721c53-aed2-4f3e-bc11-fe3186c99018` → CLOSED；AST canonical run scan → 0。
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；R1–R10 `bash scripts/spec_xref_check.sh --synth ... docs/SPLITUNIFY_SPEC.D-002.md` 全部 rc=0；M5 two-case validator probe 輸出上述兩個錯誤；G4e receipt probe 4 tests passed。
FAILURES_SEEN: 初次 AST probe 因 shell quoting 得 SyntaxError，改用 stdin script 後 rc=0；review 期間未改 repo code、SPEC、TODO 或 data_cache。
SCOPE_CHANGES: none；僅新增本交件檔 `handoffs/20260911-splitunify-b9-review-r11-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: 未修改任何執行輸出；本報告指出 future `discarded`/baseline/golden schema、event-vs-row count 與 C5 coverage 風險。
VERDICT: blocked
BLOCKED-BY: CODEX-R11-P1-01,CODEX-R11-P1-02,CODEX-R11-P1-03,CODEX-R11-P1-04
CLOSED: CODEX-R10-P1-01,CODEX-R10-P1-04,CODEX-R10-P1-06,CODEX-R10-P2-07
STATUS: DONE
