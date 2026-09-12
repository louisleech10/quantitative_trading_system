# Reconcile — 20260911-splitunify-b9-review-r11

**來源** 20260911-splitunify-b9-review-r11-codex.md, 20260911-splitunify-b9-review-r11-composer.md, 20260911-splitunify-b9-review-r11-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **N1 producer→metadata 整鏈仍無可執行交接（兩家撞題）**——「R10M2的「producer→summ」「v11把§Vmetadata升級為值相等」 | P1 | CODEX-R11-P1-01, COMPOSER-R11-P2-01 | 採納（主委複驗成立：`build_split_unify_disclosure` 簽名只有五個參數、無 `discarded`，且 `ic_filter_orchestrator` 全檔 `discarded` 命中 **0**。🔴 **但兩家給的修法前半段走不到**——主委實跑全 repo `train_plan=` 呼叫點，唯一同時帶 `feature_index` 與 `selected_timeframe` 的事件投影入口**只在** `tests/momentum/event_samples/test_splitunify_wiring.py`，`ic_filter_orchestrator` 走 `holdout_boundary`、**不呼叫** `build_event_keys` ⇒ §V 不得寫「經 orchestrator 驗值」，否則是第四次指名走不到的落點。採 codex 二擇一之**後者**＋可執行前者：整鏈斷言掛在 `EventSamplePipeline.run` 這條唯一可執行入口，`metadata.split_unify` 層明確併入 `SU-RESID-9A-UI` 殘留，不宣稱本票已交付） |
| **N2 (5.6) register 漏記帳消費面（三家撞題）**——「R10M7雖把register機械修成2」「`(5.6)`register宣稱25條」「(5.6)自稱「唯一計數依據與唯一施工清」 | P1 | CODEX-R11-P1-02, COMPOSER-R11-P1-01, GROK-R11-P1-04 | 部分採納（**採納**補列四處：`pipeline.py:760-762` 之 summary counts、`split_projection.py:559-569` 與 `:716-719` 之 `tier_min_test_events` 門檻路徑、`EventTablesPanel.tsx:361` 之計數顯示、`tables.py:372` 之 `assignments.set_index("event_id")`（後者是**真缺陷**：主委實查 `tables.py` 有 **4 處** `set_index` 而 (5.3) 與 `C5-13` 都寫「兩處」）；同步改標題條數、§RISK 與 §R。🔴 **駁回**兩家同列之「API 計數模型」一列——主委實跑 `api/models/` 全域 grep：`n_purged` **零命中**、`n_test` 只命中 `tier_min_test_events` 與 `n_test_groups`，而 `EventAnalyzeResponse.summary` 為 `Dict[str, Any]` 整包穿透、**無具名計數欄**，補列即製造走不到的落點。另主委自查 `pipeline.py:759` 為整包展開，summary 新鍵**不需**白名單，`C5-15`／`C5-16`／`C5-17` 之 `—` 三家一致認可維持具名缺口） |
| **N3 M5 座標二擇一不窮盡且兩案皆違反 D-001（兩家撞題）**——「R10M5的full-universe`」「`Task9.2b`步驟0③之座標ada」 | P1 | CODEX-R11-P1-03, GROK-R11-P1-03 | 採納（主委自寫探針四案複驗，與 grok **逐格一致**：全域索引＋全域宇宙 PASS／全域索引＋局部宇宙 `IndexError`／局部索引＋局部宇宙 **PASS**／局部索引＋全域宇宙 `CrossSymbolLeakageError` ⇒ 二擇一漏了第三條可行路徑。🔴 **主委另取一條比兩家更強的碼證**：`D-001-C2` (4.10) 逐字「投影端只消費 `row_index_local`；`derive_event_split_from_plans` 內部**一律不得**索引 `row_index`」⇒ 我 v11 寫的兩個方案**都直接牴觸 D-001**，而 SPEC 自己又寫著「本延伸不動座標語意」，屬同檔自相矛盾。改法：validator 改由仍持有 full `ts`／`symbols` 的 producer／adapter 層呼叫，投影端維持只讀 `row_index_local`；並寫死「`row_index` 與 `ts`／`symbols` 須同一座標系、禁混用」） |
| **N4 M6 不可變 baseline 可被繞過（三家撞題）**——「R10M6的`.v8.json`＋`.v」「M6落地順序(i)–(iv)可被`--w」「(G-4d)①落地順序(iii)的「`s」 | P1 | CODEX-R11-P1-04, COMPOSER-R11-P1-02, GROK-R11-P1-02 | 採納（兩條繞過路徑皆成立：①`sha256(檔)==旁檔` 是**自參照**，同時改寫兩檔即通過；②`--write` 仍整檔 `write_text`，只拒 `splitunify_golden.v8.json` 擋不住主檔既有 11 鍵被換錨後值覆蓋。改法採 codex 之 write-once：`.v8.json` 以 `O_EXCL` 建立、既有檔與旁檔一律拒更新，並把期望 digest 錨在**不由同一 helper 改寫**的來源；`--write` 增「主檔既有 11 鍵逐值不變、新成員集只落在 `g1_membership_v9`／`g3b_oracle_v9`」之 fail-closed） |
| **N5 `M-SU-D2-29` 仍寫舊的「v8 鍵」字面**——「v11已把(G-4d)①從「v8**鍵*」 | P1 | GROK-R11-P1-01 | 採納（主委複驗成立：我把 (G-4d)① 改成檔案制、也補了 §V 第 6 條母斷言，**就是沒回寫 mutation 列本身** ⇒ 自證②同型第八次。改壞面改為「刪／覆寫 `splitunify_golden.v8.json`、改內容未同步旁檔、`--write` 寫入該檔未 raise、或主檔既有鍵被覆蓋」，應紅測試對齊 §V 第 6 條） |
| **N6 `M-SU-D2-03` 仍寫「鍵斷言」**——「M2已把§V`metadata.spli」 | P2 | GROK-R11-P2-05 | 採納（主委複驗成立：§V 已升級為值相等，mutation 列未同步 ⇒ 與 N5 同型。改壞面改為「不傳入、或鍵在而值不等於 summary／producer、或改動 `reason` 封閉值集」） |

**主委自產（本輪非委員提出，供追溯）**：①`contracts/split_unify.json` 之 `split_unify_keys` 五鍵陣列是 CONTRACT 唯一來源，而 `tests/api/test_splitunify_disclosure.py:272` 以 `set(su) == set(CONTRACT["split_unify_keys"])` 對證 ⇒ `Task 9.1` 現寫的「實改**三處**」**漏了該 JSON 陣列本身**，實為四處。②`pipeline.py:759` 為 `{k: v for k, v in plan.summary.items() if k != "per_symbol_n"}` 整包展開 ⇒ summary 新鍵零成本穿透報告，**不需**任何白名單（此點使 `Task 9.1` 的 producer→summary→report 段成本低於前估）。

**停輪判斷**：十輪 findings 數 15／11／15／8／11／16／15／14／21／13／12，本輪 12 條**首度全為「我上一版修法本身的缺陷」**（四群是 v11 新寫的 M5／M6／M7／M2 被打穿，兩群是 mutation 舊字面未同步），**非新開面向**；條目具體可閉合、四群皆多家獨立撞題 ⇒ **不符「無法收斂」**，續修。真正訊號是第七種自證形態：**跨既有介面／座標契約的「可實作性」**未驗——M5 兩案皆違反 D-001 即為證據，自證清單須補第七條。

Verdict：需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R11-P1-01

**斷言**: `(5.6)` register 宣稱 25 條為唯一施工清單，但 `(5.5)` 明列之 pipeline summary 計數（`split_projection.py:562` 一帶）、`metadata.split_unify` disclosure 鏈、前端 `splitAuthority.ts` 事件數顯示**均未登記**，實作者按 register 逐條施工會漏改 tier_min 靜默繞過路徑。

**碼證**: `(5.5)` L82 逐字列「`pipeline` 產出之 `n_train`／`n_test`／`n_purged`、其 API 模型、前端事件批面板」；`rg '^\| \`C5-' docs/SPLITUNIFY_SPEC.D-002.md` 僅 **25** 行且無 `:562`／`splitAuthority`／`build_split_unify_disclosure`；Task 9.4 L242 有改法散文但無 register 行。RECHECK: 對讀 (5.5) vs C5-01..25；`nl -ba momentum/Analysis/event_samples/split_projection.py | sed -n '559,570p'`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。複合鍵後 `n_test=2` 而真實事件數=1 可靜默繞過 `tier_min_test_events`（§RISK d）。**修法**：register 增 `C5-26`～`C5-28`（pipeline summary 計數、disclosure `n_test`、前端 splitAuthority），標題改 **28 條**，§R／§RISK 同步；各列 Task 9.4 與既有 §V 去重斷言。**可行性**：純 SPEC 表行擴充；碼側改法已在 Task 9.4 L242 寫死，只需把敘述層升為 register 行。

## COMPOSER-R11-P1-02

**斷言**: M6 落地順序 (i)–(iv) 可被 `--write` 全檔覆寫主 golden **繞過**——SPEC 只寫 `--write` 拒寫 `.v8.json`，未要求 `--write` 不得改動主檔 11 個既有頂層鍵或不得直寫 `g1_membership`。

**碼證**: `sed -n '373,386p' scripts/freeze_splitunify_golden.py` → `golden_path.write_text(json.dumps({**actual}))` 全檔覆寫；`test -f tests/golden/splitunify/splitunify_golden.v8.json` → **MISSING**；§G (G-4d)① (iv) 僅「`--write` 對 `.v8.json` 一律拒寫」。繞過：換錨後不建 v8、直接 `--write` 改 `g1_membership`。RECHECK: 對讀 §G (G-4d)① vs freeze `--write` 分支。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。Task 9.5 重凍可把換錨差異寫進舊鍵而無 v8 錨與 v9 平行鍵，M-SU-D2-29 讀路徑紅但 write 路徑仍可污染。**修法**：§G／§V 增 `ASSERT WHEN --write 會改動 splitunify_golden.json 之 11 個既有頂層鍵任一值 OR 寫入 g1_membership 而非 g1_membership_v9 THEN raise`；`--write` 只允許增 `g1_membership_v9`／`g3b_oracle_v9` 與其他新鍵。**可行性**：freeze `main()` 已有 read 路徑比對骨架；寫入前 diff 舊檔 11 鍵即可機械實作（與 §V #6 對稱）。

## COMPOSER-R11-P2-01

**斷言**: v11 把 §V metadata 升級為值相等，但 Task 9.1 L183 要求的 **producer→summary→metadata 整鏈 E2E** 仍未寫入 §V——實作者可用三個 mock 物件手塞相同 `discarded` 通過 §V，而 `ic_filter_orchestrator.py:1530-1534` 仍不傳 `discarded`。

**碼證**: `rg '整鏈' docs/SPLITUNIFY_SPEC.D-002.md` 僅命中 Task L183 與沿革，§V L253 無「經 orchestrator／pipeline」；`build_split_unify_disclosure`（`split_projection.py:123-180`）簽名仍無 `discarded`；caller `ic_filter_orchestrator.py:1530-1534` 仍只傳 `n_test`／`test_timestamps_ms`／`per_symbol_counts`。RECHECK: 對讀 Task 9.1 L183 vs §V L253；`rg 'discarded' momentum/Analysis/ic_filter_orchestrator.py` → 0。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293

[MAJOR] 信心度=High。R10 COMPOSER/CODEX P1-02 之殘餘：孤立 builder／disclosure 單測可綠，真實 IC 路徑計數仍可在 orchestrator 邊界遺失。**修法**：§V `Task 9.1` 增 `ASSERT 經 ic_filter_orchestrator（或 EventSamplePipeline.run 等價 derive）之 discarded_rows_by_feature_tf 與 metadata.split_unify 同值`；builder 增 `discarded` 參數並改 caller。**可行性**：Task 9.1 L183 已寫 handoff 路徑，§V 只需把「整鏈」從散文降為可執行斷言（與 Task 9.2 端到端句式對齊）。

## GROK-R11-P1-01

**斷言**: v11 已把 (G-4d)① 從「v8 **鍵**」改成獨立檔 `splitunify_golden.v8.json`＋`.sha256`，但 `M-SU-D2-29` 之改壞面與應紅測試仍寫「覆寫 v8 baseline **鍵**／v8 鍵保留」——被取代的舊 mutation 字面未同步，mutation 對新落點不可驗。

**碼證**: `sed -n '301p' docs/SPLITUNIFY_SPEC.D-002.md` → `M-SU-D2-29` 逐字「直接覆寫 v8 baseline **鍵**」「v8 **鍵**保留、只增不覆寫」；對照 L163／§V L263 已改為 `.v8.json` 檔＋`g1_membership_v9` 新鍵、並明寫「**不存在任何 v8 鍵**」。RECHECK: `grep -n 'M-SU-D2-29\|v8.json\|v8 baseline 鍵' docs/SPLITUNIFY_SPEC.D-002.md`；`jq -r 'keys[]' tests/golden/splitunify/splitunify_golden.json`（無 v8 鍵）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1

[BLOCKING] 信心度=High。屬自證②「被取代的舊內容未同步」——主委自證抓到 §V 母斷言，卻漏改 mutation 列本身。不改則 Task 9.5／freeze 實作者可依 mut 29 去找不存在的「v8 鍵」、或寫出測不到 `.v8.json` 拒寫／hash 的空心測試。**修法**：把 `M-SU-D2-29` 改壞面改為「刪／覆寫 `splitunify_golden.v8.json`、或改其內容卻不同步 `.v8.sha256`、或 `--write` 寫入 `.v8.json` 未 raise、或主檔既有 11 鍵被換錨後值覆蓋」；應紅測試對齊 §V 第 6 條三 ASSERT。**可行性**：純 SPEC 字面同步；母斷言已在 L263。

## GROK-R11-P1-02

**斷言**: (G-4d)① 落地順序 (iii) 的「`sha256(.v8.json)==.v8.sha256`」是自參照雜湊，同時改寫兩檔即可繞過；且現行 `--write` 對主檔整檔覆寫，未強制自 `.v8.json` merge 保留既有 11 鍵，可一次換掉舊錨。

**碼證**: L163 (i)–(iv)；§V L263。VERIFY：對竄改內容重算 sha 後「file==sha_file」恆成立（探針示意 sha12=`349a8ca204eb`）；`sed -n '373,386p' scripts/freeze_splitunify_golden.py` 仍 `golden_path.write_text(...)` 無 merge-from-v8、無 `.v8` 拒寫。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r11/m5_m6_probe.txt` 之 M6 段；讀 freeze `--write` 分支。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。不改則 Task 9.2b 重凍可在「綠燈」下換掉換錨前回歸錨。**修法**：①(iii) 改為比對**外部錨**（例如把初次凍結之 sha 寫進 SPEC／lock 檔／已提交 blob，且該錨本身不由同一次 `--write` 更新）；或要求 `.v8.json` 一經創建即 `chmod`／CI 禁改（內容變更須另票）；②Task 9.5／freeze：`--write` 主檔時**必須**先讀 `.v8.json` 把既有 11 鍵逐值拷入再只寫入 v9 新鍵；③mutation 覆蓋「雙檔同改」與「主檔舊鍵被換」。**可行性證據**：現行 write 路徑單一、可加 merge 六行級；外部錨可用「首次 commit 之 sha256 字面」寫進 §V（與 golden byte 閘同型）。

## GROK-R11-P1-03

**斷言**: `Task 9.2b` 步驟 0③ 之座標 adapter「二擇一」只約束 `row_index`、未要求 `ts`／`symbols` 與之同一座標系，且漏列第三條可行路徑（局部宇宙＋局部索引）；照現文實作仍可 IndexError 誤殺，或誤以為二擇一已窮盡。

**碼證**: SPEC L217／§V L264。VERIFY 探針（`purge_semantic=timedelta`）四案：`full+global` PASS；`local_univ+global_idx` → `IndexError: plan.row_index contains positions outside base universe`；`local+local` PASS；`full_univ+local_idx` → `CrossSymbolLeakageError`。RECHECK: 重跑探針；`sed -n '646,647p;676,685p' momentum/core/contracts.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/core/contracts.py#1471cef968a3

[BLOCKING] 信心度=High。R10 M5 採納方向對，定義仍窄。不改則多標的交錯批在 Task 9.2b 接 validator 時重現假紅，或 Agent 選 (a) 只改 row_index 不改宇宙陣列。**修法**：改寫為「座標系一致」三選一寫死——(a) `row_index`＋`ts`/`symbols` 皆 full-universe；(b) local→global rebase 後接 full-universe 陣列；(c) 整條 derive 鏈維持該 symbol 局部宇宙＋局部索引（探針證明可行）；並規定**禁止混用**。§V 母斷言改為涵蓋「全域索引配局部宇宙 ⇒ 必須先適配、不得裸呼叫」。**可行性**：探針四案已給真值表；validator 簽名為 `(train, test, ts, symbols)`，契約可逐字寫死四參數同位系。

## GROK-R11-P1-04

**斷言**: (5.6) 自稱「唯一計數依據與唯一施工清單」共 25 條，但 (5.5) 具名之 pipeline／API／前端事件批面板計數消費面，以及碼上 `tables.py:372` 之 `assignments.set_index("event_id")`，皆不在 register——唯一真相源與敘述／碼點再次分叉。

**碼證**: (5.5) L82 逐字列 `pipeline` 產出之 `n_train`／`n_test`／`n_purged`、API 模型、前端事件批面板；register C5-01..25（L94-118）無 pipeline／API／`EventTablesPanel` 列（C5-15＝`batch_facts`、C5-23＝wiring `dict(zip)`）。`pipeline.py:761-763` 現行以 `assignments[...].sum()` 寫入 summary counts；`EventTablesPanel.tsx:361` 顯示 `s.n_test`；`tables.py:372` `assignments.set_index("event_id")` 而 (5.3) 只寫「tables 兩處」。RECHECK: `grep -nE 'C5-|pipeline\.py:76|EventTablesPanel|tables.py:372' docs/SPLITUNIFY_SPEC.D-002.md momentum/Analysis/event_samples/pipeline.py momentum/Analysis/event_samples/tables.py frontend/src/components/ic-analysis/EventTablesPanel.tsx`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;momentum/Analysis/event_samples/tables.py#843ba7f68172;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[BLOCKING] 信心度=High。此即自證**第七種形態**：新建唯一 register 後未對帳敘述層與碼點。不改則實作者可只掃 25 列自稱合規，卻漏改會讓複合鍵後 `n_test` 膨脹的 pipeline 路徑，或漏掉 assignments 消費面（近丙類）。**修法**：①register 增列 pipeline summary counts、API 計數模型、`EventTablesPanel` 計數顯示、`tables.py:372` assignments 消費（分類建議：前三者隨 Task 9.4 去重／事件數語意；assignments lookup 近丙）；②同步改標題條數與 §R；③(5.3)「兩處」改為與碼一致之列舉。**可行性**：與 M7 同型——加列＋改數字；Task 9.4 已有改法句可掛 Task 欄。

## GROK-R11-P2-05

**斷言**: M2 已把 §V `metadata.split_unify` 升級為與 producer／summary **值相等**，但 `M-SU-D2-03` 應紅測試仍只指向「鍵斷言」——鍵在而值遭手塞空 dict 時 mutation 網不紅。

**碼證**: §V L253 逐字 `ASSERT metadata.split_unify["discarded_rows_by_feature_tf"] == EventSplitPlan.summary[...] == producer 回傳之 discarded`；L277 `M-SU-D2-03` 應紅面逐字「`metadata.split_unify` **鍵斷言**」。RECHECK: `sed -n '253p;277p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1

[MAJOR] 信心度=High。R10 本家 P1-03 修法建議「應紅面加鍵在但值不一致」未落地——又一次「改 §V 沒回寫 mutation」。不改則孤立單測手塞 `{}` 仍可能讓 mut 03 路徑假綠（§V 整鏈若被實作者省略時）。**修法**：`M-SU-D2-03` 應紅面改為「不傳入、或鍵在但值 ≠ summary／producer、或改 reason 封閉值集」；對齊 L253。**可行性**：一字級 SPEC 同步。

---

