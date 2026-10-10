# TESTREG：測試清冊自動維護與受影響測試挑選 — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 5a 步；諮詢 r1 收斂 `handoffs/reconcile/20261009-testreg-x-consult-r1/synth.md`（26 條全處置、三家 proceed；主委獨立版 `handoffs/20261009-testreg-x-consult-r1-claude.md`）；靜態盤點 `handoffs/run_receipts/testreg_probes/20261010-test-inventory.json`　|　日期：2026-10-10　|　對應 TODO：`docs/manifests/TESTREG.json`（SPEC 凍結後生成）
> 版本：v1（初稿，待審查 r1）
> 契約單一真相源：`tests/registry/testreg_schema.json`（欄位、枚舉、證據等級、挑選理由碼皆只定義於該檔；本 SPEC 以鍵名引用，不重列值）。

## §RISK 風險分級
- **大小**：大（`docs/TICKET_ORDER.md` 第 5a 步定案）。
- **命中高風險原則**：(b) 跨模組／共用路徑——記錄器經 `tests/conftest.py` 載入，作用於全部 642 檔、8,342 條測試；挑選器接入 `scripts/framepath_affected_gate.py`，其後各票共用。(c) 多 phase／難回退——四 Phase；淘汰測試為刪檔，回退須 revert。(d) ML／回測正確性——淘汰或隔離若錯，正確性測試即不再守其性質；挑選器若少選，正確性回歸漏驗。
- RISK-HIT: b,c,d

## §A 假設與待使用者確認
- **已驗證事實**（FACT-RECEIPT 共 8 條）：
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/testreg_probes/inventory.py` → `handoffs/run_receipts/testreg_probes/20261010-test-inventory.json`：`total_files` 642、`total_tests` 8342；逐檔欄位 `path/dir/tests/markers/prod_modules/real_kline/lines/first_commit/last_commit/commits`（主委 實跑 2026-10-10）。
  - FACT-RECEIPT: `sed -n 120,146p tests/conftest.py` → `pytest_collection_modifyitems` 只在 `config.option.collectonly` 時呼叫 `write_test_inventory_from_nodeids(nodeids, out_path=Path(TEST_INVENTORY_PATH))`，寫 git 追蹤之 `tests/golden/l65/test_inventory.txt`；`pytest_configure` 於 cacheprovider 啟用時預設 `--ff`（主委 實跑 2026-10-10）。⇒ 任何 `--collect-only` 皆有追蹤檔副作用。
  - FACT-RECEIPT: `cat pytest.ini` → `markers` 註冊 slow/integration/legacy/asyncio/perf/ic_run_selector/backward_compat/disambig/analyze_real_run/list_features/requires_kline/slow_stat；無 `flaky_quarantine`、無 `timeout`（主委 實跑 2026-10-10）。`docs/TEST_DESIGN_CHARTER.md:43`（第 18 類）要求 `flaky_quarantine` 等註冊進 `pytest.ini`。
  - FACT-RECEIPT: `grep -rhoE "pytest\.mark\.[a-z_]+" tests | sort | uniq -c` → `timeout` 9 處（例 `tests/momentum/Analysis/test_icfirstalign_cache.py:28` `pytestmark = pytest.mark.timeout(600)`）；`venv/bin/pip show pytest-timeout` → 無輸出（未安裝）（主委 實跑 2026-10-10）。⇒ 該 9 處逾時宣告現無效力。
  - FACT-RECEIPT: `venv/bin/python --version` → `Python 3.9.6`；`venv/bin/pip show pytest` → `Version: 8.4.2`（主委 實跑 2026-10-10）。
  - FACT-RECEIPT: `jq -r '.hooks.PreToolUse[], .hooks.PostToolUse[] | select(.matcher=="Edit|Write") | .hooks[].command' .claude/settings.json` → 12 支既有產出端 hook（`verify_pretooluse.sh`…`todofmt_manifest_guard.sh`），無測試清冊類（主委 實跑 2026-10-10）。
  - FACT-RECEIPT: `head -c 1500 tests/_golden/prered/allowed_red.json` → 逐 nodeid 列 `node/owner_ticket/reason/state/trigger`（主委 實跑 2026-10-10）。⇒ 「已知紅」已有權威檔；不穩定隔離另立，不併入。
  - FACT-RECEIPT: `grep -n "V-6" docs/FRAMEPATH_SPEC.md` → `:268` 記「V-6 單項於錨點碼態即 1:39:36，非本票造成；慢因未定…交 TESTREG 分段計時」；b1 閘之 junit 中 `test_v6_asof_oracle_boundary_cases` `time="0.002"`（主委 實跑 2026-10-10）。⇒ 慢者為同檔其他 `test_v6_*` 項，具名待 Task 3.4 實測。
  - 宣告——IC 兩路涵蓋：本票不改 IC 路徑；全域序列型／事件型皆不涉及。
- **待使用者確認**：待確認：無
- **已確認結果**：
  - `2026-10-09 使用者`：插入第 5a 步（「做；FRAMEPATH 第一批收尾後插入」）；「我完全不懂程式碼，所以要如何分類和存放和建議清冊以及決定去留等，你跟委員決定」；「你跟委員要參考軟體業界是如何做的」。
  - `2026-10-10 使用者`：核可設計方向（`白話說明/TESTREG設計方向審閱.md`，選「同意」）。
  - `2026-10-09 使用者`：「不要莫名被什麼時間上限砍掉，然後又重來，不允許這種事情。還有卡住沒動或跑太久也不知道也不允許」。
  - `2026-09-28 使用者`（嚴謹只能多不能少）：提速只准砍流程浪費，不得少驗路徑。
  - `2026-09-22 使用者`（嚴禁慢閘）：新增每次都跑之檢查須秒級並擋在產出端。

## §C 約束
- 不改 `momentum/`、`api/`、`frontend/` 生產碼。
- **只加不減**：清冊與挑選器只得對既有必跑集合（各票 manifest `affected_tests`／`affected_must`、SPEC 具名驗收）作加法與排序；唯一得自挑選結果扣除者＝已立碑（`catalog.tombstones`）且其測試已不存在者。`derived.review_needed_signals` 任一值不得導致少跑。
- **記錄器不改測試行為**：不改 outcome、不改執行順序、不改 rc；記錄器自身之例外一律攔截並以單行 stderr 告知，不上拋。巢狀 pytest（環境帶 `TESTREG_PARENT_SESSION`）不寫帳本。
- **產出端秒級**：產出端 hook 與 pre-commit 檢查只讀 `catalog.json`、`testreg_schema.json` 與變更檔清單；禁呼叫 pytest（含 `--collect-only`）、禁全量讀 ledger。單次執行牆鐘上限 1 秒（Task 1.4 驗收）。
- **catalog 只存無法導出之欄**：可由程式導出者（耗時、大小級、標記、生產模組、測試數、最近執行）只存於 ledger／summary 或查詢時計算；`catalog.forbidden_fields` 列者寫入即 schema 錯。
- **淘汰須證據**：`disposition=retire` 之執行（刪檔或刪函式）須同提交立碑，碑之 `retire_evidence.level` 屬 `enums.retire_evidence_level`；無證據不得刪。提交年齡、未執行、單次成本不得作證據。
- **隔離不變綠**：`flaky_quarantine` 之測試照跑；票級閘將其失敗列「隔離失敗」不擋，但不得 rerun 取綠；正確性路徑之隔離須有 ledger 同指紋翻轉證據（`quarantine_record.evidence_ref`）且帶 `expires`。
- 真實資料重測試單組串行；長跑一律走分段續跑執行器（FRAMEPATH D10 執行器）＋監看，不得被背景上限砍斷重來。
- 跑完測試執行 `bash scripts/restore_golden_inventory.sh`。

## §G Golden／Baseline
- 本票不改數值計算；Golden 對象為「測試結果集合」與「淘汰等價證據」兩者。
- **記錄器不變性基準**（Task 1.2 動工前凍結）：取固定樣本集合＝`tests/feature_engineering/test_framepath_disposition.py`、`tests/governance/test_mutation_scope_extension.py`、`tests/api` 中依路徑字典序前 10 檔（凍結時寫死清單於收據），於動工前 HEAD 以 `-p no:cacheprovider` 執行，存逐 nodeid outcome 集合、其排序後 sha256 與 rc 於 `handoffs/run_receipts/testreg-recorder-baseline.json`。通過條件：加入記錄器後同命令之逐 nodeid outcome 集合 sha256 相同、rc 相同（無數值容差：atol/rtol 不適用，集合須逐項全等）；`git status --porcelain` 前後相同。
- **淘汰等價**：每一碑之證據檔即其 golden（E0＝AST 掃描收據；E1＝逐斷言對照表；E2＝mutation 收據，逐 mutant 列原測試紅與替代測試紅）。

## §P Phase 與依賴

### Phase 1 — 記錄器、清冊骨架、產出端登記（依賴：無）
**Task 1.1 — 契約定稿**
- 目標：`tests/registry/testreg_schema.json` 為唯一契約；新增 `scripts/testreg.py validate` 依之驗 catalog。　檔案：`tests/registry/testreg_schema.json`、`scripts/testreg.py`（新建，子命令 `validate`）。既有 caller：無。
- 改法：validate 檢 required／write_once（比對 `git show HEAD:tests/registry/catalog.json` 之同鍵值）／forbidden_fields／枚舉／`required_when`／tombstone 證據檔存在。
- **驗證**：`pytest tests/registry/test_testreg_schema.py`；mutant①刪某 entry 之 `ticket` ⇒ validate rc≠0；mutant②寫入 `owner` 欄 ⇒ rc≠0；mutant③tombstone 之 `retire_evidence.ref` 指不存在檔 ⇒ rc≠0；mutant④已提交之 `ticket` 被改 ⇒ rc≠0。
- **邊界**：catalog 不存在 ⇒ rc≠0 並具名；catalog 為空物件 ⇒ 對任何存在之 `tests/**/test_*.py` 報缺登記。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不在 SPEC 或 validate 程式內另寫枚舉值副本（一律讀 schema）。

**Task 1.2 — 記錄器**
- 目標：每次 pytest session 自動寫 ledger 與增量 summary。　檔案：`tests/fixtures/testreg_recorder_plugin.py`（新建）、`tests/conftest.py`（`pytest_plugins` 加入）、`.gitignore`（`.testreg/`）。既有 caller：全部測試經 `tests/conftest.py`。
- 改法：`pytest_sessionstart` 計算 `ledger.session_record`（git 子程序各一次）、設 `TESTREG_PARENT_SESSION`；`pytest_runtest_logreport` 累積 setup/call/teardown 為一筆 `test_record`；`pytest_sessionfinish` 一次寫 `<session_id>.jsonl`（暫存檔＋rename 原子化）並增量合併 `summary.json`（原子寫；毀損視同不存在並由 ledger 重建）。
- **驗證**：§G 不變性基準；`pytest tests/registry/test_testreg_recorder.py`：①執行一個含 pass/fail/skip/xfail/error 之暫存測試檔 ⇒ ledger 五種 outcome 各一筆；②巢狀 pytest（設 `TESTREG_PARENT_SESSION`）⇒ 不新增 ledger 檔；③以 monkeypatch 使寫檔丟例外 ⇒ 被測 session rc 與未裝記錄器時相同；④summary 毀損 ⇒ 下一 session 重建且筆數等於 ledger 全量。mutant：記錄器改為上拋例外 ⇒ ③紅；巢狀判斷移除 ⇒ ②紅。
- **邊界**：`kline_cache.h5` 不存在 ⇒ `kline_identity=absent` 仍記錄；session 被 SIGKILL ⇒ 無半寫檔（只有暫存檔殘留，下一 session 清除）。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不改 `pytest_collection_modifyitems` 之既有清冊寫入；不在每條測試後寫檔；不讀 kline 全檔雜湊。

**Task 1.3 — 標記註冊**
- 目標：`pytest.ini` 註冊 `flaky_quarantine`；新增標記完整性檢查。　檔案：`pytest.ini`、`scripts/testreg.py`（子命令 `markers`）。
- 改法：`markers` 以靜態掃描 `pytest.mark.<name>` 對照 `pytest.ini` 註冊集合與 pytest 內建集合，未註冊者 rc≠0；`timeout` 之處置見 §N 委員審議項 Q1。
- **驗證**：`pytest tests/registry/test_testreg_markers.py`：暫存樹內加一個未註冊標記 ⇒ rc≠0；現行樹（Q1 定案後）rc=0。
- **邊界**：字串內出現 `pytest.mark.x`（註解或 docstring）⇒ 以 AST 判定，不計。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不安裝新 pytest 外掛（Q1 定案前）。

**Task 1.4 — 產出端登記檢查**
- 目標：新增或改名 `tests/**/test_*.py` 而 catalog 無登記 ⇒ 寫檔當下報錯；Bash 建檔之漏網由 pre-commit 同檢查擋。　檔案：`scripts/testreg_write_guard.sh`（新建，PostToolUse `Edit|Write`）、`.claude/settings.json`、pre-commit 掛載、`docs/GOV_ENFORCEMENT_REGISTRY.md`。
- 改法：hook 讀工具輸入之檔路徑；命中 `tests/**/test_*.py` ⇒ 呼叫 `scripts/testreg.py check --paths <p>`（查 catalog 鍵、validate 該 entry、quarantine 逾期）；pre-commit 以暫存區新增／刪除／改名之測試檔清單呼叫同一命令，另驗孤兒（catalog 有、檔不在、且無碑）。
- **驗證**：`pytest tests/registry/test_testreg_write_guard.py`：①新測試檔無登記 ⇒ hook rc≠0、訊息含路徑；②登記後 ⇒ rc=0；③刪檔未立碑 ⇒ pre-commit rc≠0；④quarantine `expires` 早於今日 ⇒ rc≠0；⑤以全量 catalog（642 entries）量測 hook 牆鐘，10 次中位數 <1 s（收據）。mutant：hook 改為恆 rc=0 ⇒ ①紅。
- **邊界**：`tests/registry/` 內非測試檔 ⇒ 不檢；`conftest.py`、`fixtures/` ⇒ 不檢。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：hook 內不跑 pytest、不跑 git log 全史。

### Phase 2 — 全檔機械建檔與首批分類（依賴：Phase 1）
**Task 2.1 — bootstrap**
- 目標：642 檔全數有 catalog entry。　檔案：`scripts/testreg.py`（子命令 `bootstrap`）、`tests/registry/catalog.json`。
- 改法：`ticket` 由該檔首次提交之訊息與 trailers 中票代號導出（封閉規則：取 `Ticket-Batch:` root、否則 conventional commit scope 大寫、否則 `unknown`）；`guarantee=["unclassified"]`、`oracle=unclassified`、`disposition=keep`。
- **驗證**：bootstrap 後 `testreg.py validate` rc=0；entry 數＝`git ls-files 'tests/**/test_*.py' 'tests/test_*.py'` 行數；再跑一次 bootstrap ⇒ catalog 位元相同（冪等）。
- **邊界**：首次提交無票標記 ⇒ `unknown`；改名檔 ⇒ 以 `git log --follow` 首次提交。
- **存活至**：票收案後保留。　**覆蓋風險**：Task 2.2／4.1 只改 `guarantee/oracle/disposition` 等委員欄，不覆寫 `ticket`。
- 不可做：不為導不出之欄捏造值。

**Task 2.2 — 首批分類：Feature Factory 相關**
- 目標：`tests/feature_engineering/` 全部與根層 `tests/test_*.py` 中 `prod_modules` 含 `momentum.FeatureEngineering` 者，逐檔定 `guarantee/oracle/disposition`。　檔案：`tests/registry/catalog.json`；分類收斂檔 `handoffs/reconcile/<session>/synth.md`。
- 改法：三家各自獨立逐檔判定（brief 附每檔 inventory 列、ledger 既有耗時、`allowed_red` 列、`review_needed_signals`）；一致者直接採；不一致者逐項依碼證裁決；FRAMEPATH 諮詢 r4 已判之 30 檔結果直接併入。`rewrite`／`merge`／`retire` 於本 Phase 執行，除非依賴後續票（以 `blocked-by` 登 §N 殘留並在 catalog `disposition_ref` 指之）。
- **驗證**：每一 `retire` 有碑且證據檔存在、validate rc=0；每一 `rewrite` 依 `docs/TEST_DESIGN_CHARTER.md` 防假綠——提交訊息列「原斷言所守性質＋改寫後仍守之 mutant」；執行後受影響測試走 FRAMEPATH D10 執行器跑完，本 Phase 造成之紅＝0。
- **邊界**：三家皆判 `retire` 但無一級證據 ⇒ 不得 retire，改 `keep` 並記 `needs-research`；某檔屬 `allowed_red` 之 owner 票 ⇒ 不得 retire，`disposition_ref` 指該票。
- **存活至**：票收案後保留。　**覆蓋風險**：Phase 4 不重判本 Phase 已判之檔。
- 不可做：不以「未執行過」「年代久」「慢」為 retire 理由。

**Task 2.3 — 成效報告**
- 目標：產出「淘汰幾檔幾條、理由分布、以 ledger 中位耗時計之每次全跑節省秒數（無紀錄者列 unknown 不估）」。　檔案：`handoffs/run_receipts/testreg-phase2-effect.json`。
- **驗證**：`venv/bin/python scripts/testreg.py effect --recompute handoffs/run_receipts/testreg-phase2-effect.json` 由 catalog 碑與 summary 重算，逐數字 == 報告值則 rc=0；unknown 筆數單列。
- **邊界**：summary 無任何紀錄 ⇒ 節省秒數欄為 unknown，不得寫 0。
- **存活至**：票收案。　**覆蓋風險**：Task 4.2 產全庫版，不覆寫本檔。
- 不可做：不外插估算。

### Phase 3 — 複查訊號、挑選器接線、V-6 慢因（依賴：Phase 1；Task 3.2 另依賴 Task 2.1）
**Task 3.1 — review_needed 訊號**
- 目標：`scripts/testreg.py review` 輸出 `derived.review_needed_signals` 之逐檔逐訊號清單。　檔案：`scripts/testreg.py`。
- 改法：`prod_symbol_gone` 重用 FRAMEPATH dead-scan 之 AST 解析（測試檔 import 之生產符號於 HEAD 不存在）；`duration_regression`＝同 `kline_identity` 與 `env` 下最近一筆耗時 >3×歷史中位且 >10 s；`outcome_flip_same_fingerprint`＝同 `head+diff_digest+kline_identity+env` 下 outcome 不同；`collect_error`＝ledger 最近 session 該檔收集錯；`allowed_red_owner_closed`＝`allowed_red.json` 之 `owner_ticket` 於 `docs/TICKET_ORDER.md` 已標收案；`quarantine_expired`。
- **驗證**：`pytest tests/registry/test_testreg_review.py`：每一訊號一正例一反例（以暫存 ledger／catalog／暫存樹構造）；mutant：任一訊號判定反轉 ⇒ 對應正例紅。
- **邊界**：summary 不存在 ⇒ 需 ledger 之四訊號輸出 `unknown`，不輸出「無訊號」。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：訊號不寫回 catalog；不接到任何「略過」邏輯。

**Task 3.2 — impact 挑選器與 FRAMEPATH 閘接線**
- 目標：`scripts/testreg.py impact --changed <paths> --manifest <m> --phase <n>` 輸出 `impact.output_fields`；`scripts/framepath_affected_gate.py plan` 將其作加法輸入。　檔案：`scripts/testreg.py`、`scripts/framepath_affected_gate.py`。既有 caller：FRAMEPATH b2／b3 之 gate 計畫。
- 改法：集合為 `enums.select_reason` 各來源之聯集：`must`＝manifest 必跑；`changed_test`＝變更之測試檔；`static_taint`＝沿用 `_TaintGraph`；`dynamic_hit`＝summary 中同指紋紀錄顯示之覆蓋（無則空，不影響其他層）；`previously_failed`＝summary 最近一筆非 passed/skipped/xfailed 者；`registry_unresolved`＝變更檔無 catalog entry、catalog validate 失敗、或靜態分析對某變更檔回報無法解析 ⇒ 擴大至該變更檔所在頂層 domain 之全部測試檔，domain 無法判定 ⇒ 全部測試檔。gate 計畫之選中集合＝原計畫 ∪ impact 輸出；每一未選檔寫 `enums.exclude_reason` 之一。
- **驗證**：`pytest tests/registry/test_testreg_impact.py`：①變更一個無 catalog entry 之生產檔 ⇒ 輸出含該 domain 全部檔、理由 `registry_unresolved`；②任何輸入之輸出 ⊇ manifest 必跑；③構造使各來源皆空 ⇒ 輸出仍非空（至少 must 或擴大）；④gate 計畫 ∪ 後之選中集合 ⊇ 原計畫（以 b1 收據 `handoffs/run_receipts/framepath-b1-affected-plan.json` 重放）。mutant：聯集改交集 ⇒ ②④紅；擴大分支移除 ⇒ ①紅。
- **邊界**：manifest 不含 `affected_tests` ⇒ rc≠0 拒跑（不得視為空）；變更檔為已立碑之測試 ⇒ 理由 `tombstoned` 排除且附碑 ref。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不實作覆蓋率收集（見 §N 殘留 R1）；不以 `size_class` 排除。

**Task 3.3 — 執行器接續指紋修正**
- 目標：FRAMEPATH D10 執行器接續時 `inputs_digest` 不受本次輸出目錄內 junit 變動影響。　檔案：`scripts/framepath_affected_gate.py`。
- 改法：digest 之未追蹤內容排除執行器自身 `--out` 目錄（以路徑前綴比對，前綴由參數導出，不寫死）。
- **驗證**：`pytest tests/feature_engineering/test_framepath_disposition.py -k digest`：新增案例——分段一跑完後於 out 目錄新增 junit ⇒ 接續之 `inputs_digest` 不變；工作區新增一個非 out 目錄之未追蹤原始碼 ⇒ digest 改變。mutant：排除前綴改為空 ⇒ 第一案紅。
- **邊界**：`--out` 位於 repo 外 ⇒ 本來就不在未追蹤集合，結果不變；`--out` 為 repo 根 ⇒ rc≠0 拒跑。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不放寬其他 digest 成分。

**Task 3.4 — V-6 慢因**
- 目標：確定 `tests/feature_engineering/test_failopen_correctness.py` 中耗時 1:39:36 之 `test_v6_*` 項具名與慢因。　檔案：收據 `handoffs/run_receipts/testreg-v6-profile.json`。
- 改法：以 D10 執行器跑該檔（記錄器開），取逐項耗時；對最慢項以 `cProfile` 單項執行取前 30 累計熱點；歸類為「測試端重複計算」或「生產端本身耗時」。前者之修正若改測試，須證不減驗證力（同 mutant 集合仍紅），交委員審；後者登 §N。
- **驗證**：`handoffs/run_receipts/testreg-v6-profile.json` 含逐項耗時（秒）、前 30 熱點表、歸類與碼證 `file.py:line`；若改測試，改前改後逐 nodeid outcome sha256 相同且附 mutant 收據。
- **邊界**：該項於本機記憶體不足而被終止 ⇒ 改以 `watch_run.sh` 收峰值記憶體並記錄，不重試超過一次。
- **存活至**：票收案。　**覆蓋風險**：無。
- 不可做：不以縮小資料窗、降低 symbol 數等減少驗證範圍之方式提速（樣本 symbol 數、資料窗長度 == 現行值）。

### Phase 4 — 其餘目錄分類與收案（依賴：Phase 2、Phase 3）
**Task 4.1 — 其餘分類**
- 目標：Phase 2 未涵蓋之全部測試檔完成分類。　改法同 Task 2.2；分批順序依各目錄被量化主線票之 manifest `affected_tests` 引用次數由高到低（由 `docs/manifests/*.json` 機械計數，收據附）。
- **驗證**：同 Task 2.2 三項（`testreg.py validate` rc=0、rewrite 逐處 mutant、本 Phase 造成之紅＝0）；另 `jq '[.[]|select(.guarantee==["unclassified"])]|length' tests/registry/catalog.json` 對本 Phase 範圍＝0。
- **邊界**：同 Task 2.2 兩項。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：同 Task 2.2。

**Task 4.2 — 全庫成效報告與收案**
- 目標：全庫版成效報告（同 Task 2.3 格式）；`unclassified` entry 數＝0。　檔案：`handoffs/run_receipts/testreg-final-effect.json`。
- **驗證**：`testreg.py validate --require-classified` rc=0；報告數字可重算。
- **邊界**：任一檔分類被阻於後續票 ⇒ 其 `guarantee` 仍須填（分類與處置分離），處置以 `blocked-by` 登 §N。
- **存活至**：票收案。　**覆蓋風險**：無。
- 不可做：不以收案為由跳過任一檔。

## §V 驗證策略與邊界測試目錄
- mutation：各 Task 驗收已列 mutant；本票測試宣稱守「只加不減」「記錄器不改行為」「無證據不刪」三性質，每一性質至少一 mutant 必紅（Task 1.2③、3.2②④、1.1③）。
- 測試層級：單元（schema、訊號、impact 規則）／整合（暫存樹內真實 pytest 子程序；記錄器不變性於真實測試樣本）／回放（b1 gate 計畫收據）。全部可獨立 `pytest tests/registry/` 跑，不需 `run_api.py`。
- 防假綠：既有測試之斷言僅 Task 2.2／4.1 之 `rewrite` 可改，且逐處附性質＋mutant；`merge`／`retire` 附證據。
- 邊界目錄：空 catalog（1.1）、毀損 summary（1.2）、巢狀 session（1.2）、SIGKILL 半寫（1.2）、無登記新檔（1.4）、逾期隔離（1.4、3.1）、各來源皆空（3.2）、manifest 缺欄（3.2）、out 在 repo 根（3.3）、記憶體不足（3.4）。

## §R 回退
- 每 Phase 獨立提交；記錄器以 `-p no:testreg_recorder` 或自 `pytest_plugins` 移除即停用，不影響任何測試結果。
- 淘汰為刪檔：以 revert 該提交回復；碑保留證據 ref，回退時同提交刪碑。
- 挑選器接線回退＝gate 計畫不讀 impact 輸出，原計畫不變（加法性質保證回退不減選）。

## §N N/A 登記與殘留
- **委員審議項**（審查 r1 由三家判定，主委提案附後）：
  - Q1：`pytest.mark.timeout` 9 處無外掛而無效。主委提案：不安裝 `pytest-timeout`（安裝即改變該 9 處之執行行為，屬他票範圍），改由 Task 1.3 將 `timeout` 列入「已知無效標記」並於該 9 檔 catalog 之 `disposition=rewrite`（移除無效宣告；逾時保護由 D10 執行器之監看承擔），於 Task 2.2／4.1 執行。
  - Q2：`summary` 保留筆數 K 與 `duration_regression` 閾值（3×中位且 >10 s）為主委初值，請以 b1 收據之 277 項耗時分布驗其合理性。
- **殘留**：
  - R1 完整動態覆蓋對照表（逐行覆蓋率→測試）— `為何現在不做: blocked-by:Task 1.2 記錄器上線後之 ledger 累積（無歷史資料即無對照）`；觸發：summary 中 ≥80% 測試檔具 ≥3 筆同指紋紀錄；登記處：`白話說明/還沒做的事.md` 第四節。
  - R2 定期全套自動執行 — `為何現在不做: user-ruling:2026-08-13 使用者刪除全部 CI（.github/workflows/）`；觸發：使用者恢復 CI；登記處：同上。
  - R3 測試前提過期之自動偵測（斷言所守規則已被改寫）— `為何現在不做: needs-research:前提與規則之機械對應無既有業界做法`；觸發：研究得出可證偽判準；登記處：同上。
  - R4 名稱層級之陳舊（測試名與所測行為不符）— `為何現在不做: needs-research:無可機械判定之訊號`；觸發：同上；登記處：同上。
