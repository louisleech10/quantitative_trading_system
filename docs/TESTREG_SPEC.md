# TESTREG：測試清冊自動維護與受影響測試挑選 — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 5a 步；諮詢 r1 收斂 `handoffs/reconcile/20261009-testreg-x-consult-r1/synth.md`（26 條全處置、三家 proceed；主委獨立版 `handoffs/20261009-testreg-x-consult-r1-claude.md`）；靜態盤點 `handoffs/run_receipts/testreg_probes/20261010-test-inventory.json`　|　日期：2026-10-10　|　對應 TODO：`docs/manifests/TESTREG.json`（SPEC 凍結後生成）
> 版本：v2（審查 r1 `handoffs/reconcile/20261010-testreg-x-review-r1/synth.md` 24 條全採納後改版）
> 契約單一真相源：`tests/registry/testreg_schema.json`（欄位、枚舉、證據收據格式、驗證規則 V01–V12、挑選規則皆只定義於該檔；本 SPEC 以鍵名引用，不重列值）。

## §RISK 風險分級
- **大小**：大（`docs/TICKET_ORDER.md` 第 5a 步定案）。
- **命中高風險原則**：(b) 跨模組／共用路徑——記錄器經 `tests/conftest.py` 載入，作用於全部 642 檔、8,342 條測試；挑選器接入 `scripts/framepath_affected_gate.py`，其後各票共用。(c) 多 phase／難回退——四 Phase；淘汰測試為刪檔，回退須 revert。(d) ML／回測正確性——淘汰或隔離若錯，正確性測試即不再守其性質；挑選器若少選，正確性回歸漏驗。
- RISK-HIT: b,c,d

## §A 假設與待使用者確認
- **已驗證事實**（FACT-RECEIPT 共 8 條）：
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/testreg_probes/inventory.py` → `handoffs/run_receipts/testreg_probes/20261010-test-inventory.json`：`total_files` 642、`total_tests` 8342；逐檔欄位 `path/dir/tests/markers/prod_modules/real_kline/lines/first_commit/last_commit/commits`（主委 實跑 2026-10-10）。
  - FACT-RECEIPT: `sed -n 120,146p tests/conftest.py` → `pytest_collection_modifyitems` 只在 `config.option.collectonly` 時呼叫 `write_test_inventory_from_nodeids(nodeids, out_path=Path(TEST_INVENTORY_PATH))`，寫 git 追蹤之 `tests/golden/l65/test_inventory.txt`；`pytest_configure` 於 cacheprovider 啟用時預設 `--ff`（主委 實跑 2026-10-10）。⇒ 任何 `--collect-only` 皆有追蹤檔副作用。
  - FACT-RECEIPT: `cat pytest.ini` → `markers` 註冊 slow/integration/legacy/asyncio/perf/ic_run_selector/backward_compat/disambig/analyze_real_run/list_features/requires_kline/slow_stat；無 `flaky_quarantine`、無 `timeout`（主委 實跑 2026-10-10）。`docs/TEST_DESIGN_CHARTER.md:43`（第 18 類）要求 `flaky_quarantine` 等註冊進 `pytest.ini`。
  - FACT-RECEIPT: `grep -rhoE "pytest\.mark\.[a-z_]+" tests | sort | uniq -c` → `timeout` 9 處（例 `tests/momentum/Analysis/test_icfirstalign_cache.py:28` `pytestmark = pytest.mark.timeout(600)`）；`venv/bin/pip show pytest-timeout` → 無輸出（未安裝）（主委 實跑 2026-10-10）。⇒ 該 9 處逾時宣告現無效力（pytest 未知標記只發警告）。
  - FACT-RECEIPT: `venv/bin/python --version` → `Python 3.9.6`；`venv/bin/pip show pytest` → `Version: 8.4.2`（主委 實跑 2026-10-10）。
  - FACT-RECEIPT: `jq -r '.hooks.PreToolUse[], .hooks.PostToolUse[] | select(.matcher=="Edit|Write") | .hooks[].command' .claude/settings.json` → 12 支既有產出端 hook（`verify_pretooluse.sh`…`todofmt_manifest_guard.sh`），無測試清冊類（主委 實跑 2026-10-10）。
  - FACT-RECEIPT: `head -c 1500 tests/_golden/prered/allowed_red.json` → 逐 nodeid 列 `node/owner_ticket/reason/state/trigger`（主委 實跑 2026-10-10）。⇒ 「已知紅」已有權威檔；不穩定隔離另立，不併入。
  - FACT-RECEIPT: `grep -n "V-6" docs/FRAMEPATH_SPEC.md` → `:268` 記「V-6 單項於錨點碼態即 1:39:36，非本票造成；慢因未定…交 TESTREG 分段計時」；b1 閘之 junit 中 `test_v6_asof_oracle_boundary_cases` `time="0.002"`（主委 實跑 2026-10-10）。⇒ 慢者為同檔其他 `test_v6_*` 項，具名待 Task 2.4 實測。
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
- **只加不減**：清冊與挑選器只得對既有必跑集合（各票 manifest `affected_tests`／`affected_must`、SPEC 具名驗收）作加法與排序；唯一得自挑選結果扣除者＝已立碑（`catalog.tombstones`）且其函式已不存在者，且 manifest 指向之碑依 Task 2.3 解析為其 `replaced_by`。`derived.review_signals` 任一值不得導致少跑。
- **記錄器不改測試行為**：不改 outcome、執行順序、rc；除 `.testreg/` 外不新增、不改任何檔；記錄器自身之例外一律攔截並以單行 stderr 告知，不上拋。巢狀 pytest 依 `ledger.nested_rule` 不寫。
- **產出端秒級**：產出端 hook 與 pre-commit 檢查只讀 `catalog.json`、`testreg_schema.json`、變更檔清單與其 AST；禁呼叫 pytest（含 `--collect-only`）、禁全量讀 ledger。單次牆鐘以 642 entries 量測 10 次中位 <1 s。
- **catalog 只存無法導出之欄**：`catalog.entries.forbidden_fields` 列者寫入即 V03 錯。
- **淘汰只以碑、只憑收據**：淘汰單位為函式層 nodeid；整檔淘汰＝該檔全部函式各一碑；每碑之收據須依 `receipts` 對應規則機械驗過（V08、V09）。提交年齡、未執行、單次成本不得作證據。於 HEAD 通過之測試不得持 E0（`receipts.E0.rule`），負向守衛因此不可能以 E0 淘汰。
- **改寫只憑 mutation 收據**：`rewrite` 執行後須有 `receipts.mutation` 格式收據（原測試殺之 mutant，改寫後至少一條仍殺；對應 `docs/TEST_DESIGN_CHARTER.md` §B1 之可證偽要求）。
- **隔離不變綠**：`flaky_quarantine` 之測試照跑；票級閘依 Task 2.3 將其失敗列 `quarantined_failure` 不擋但列報；不得 rerun 取綠；隔離須有 ledger 同 fingerprint 翻轉證據（V12）且未逾期（V11）。
- 真實資料重測試單組串行；長跑一律走分段續跑執行器（FRAMEPATH D10 執行器）＋監看，不得被背景上限砍斷重來。
- 跑完測試執行 `bash scripts/restore_golden_inventory.sh`。

## §G Golden／Baseline
- 本票不改數值計算；Golden 對象為「測試行為」與「淘汰／改寫收據」兩者。
- **記錄器不變性基準**（Task 1.3 動工前凍結）：固定樣本＝`tests/feature_engineering/test_framepath_disposition.py`、`tests/governance/test_mutation_scope_extension.py`、`tests/api` 依路徑字典序前 10 檔（凍結時寫死清單於收據）。於動工前 HEAD 以 `-p no:cacheprovider -v` 執行，存：①逐 nodeid outcome 之排序後 sha256；②執行順序（`-v` 輸出之 nodeid 序列）sha256；③rc；④`git status --porcelain --ignored` 之 sha256；收據 `handoffs/run_receipts/testreg-recorder-baseline.json`。通過條件：裝記錄器後同命令之①②③逐項 == 基準；④去除 `.testreg/` 開頭之列後 == 基準。集合比對無數值容差（atol/rtol 不適用）。
- **淘汰／改寫收據**即各自之 golden，由 V07–V09 機械驗。

## §P Phase 與依賴

### Phase 1 — 契約、清冊建檔、記錄器、標記、產出端登記（依賴：無；Task 順序 1.1→1.2→1.3→1.4→1.5）
**Task 1.1 — 契約與 validate**
- 目標：`scripts/testreg.py validate` 依 `tests/registry/testreg_schema.json` 之 `validation_rules` V01–V12 逐條實作。　檔案：`scripts/testreg.py`（新建）。既有 caller：無。
- 改法：每條規則一個具名函式，錯誤訊息帶規則 id；enum 一律讀 schema（含 `items_enum` 所指之 `enums.charter_category` 等）；不另存副本。
- **驗證**：`pytest tests/registry/test_testreg_validate.py`：V01–V12 各一正例一反例（暫存 catalog／暫存 git 倉）；mutant：任一規則函式改為恆真 ⇒ 其反例紅；`grep -c "A22\|EXACT\|correctness" scripts/testreg.py` == 0（無枚舉副本）。
- **邊界**：catalog 不存在 ⇒ rc≠0 並具名；ledger 目錄不存在而 catalog 有 quarantine ⇒ V12 報 unverifiable、rc≠0。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不在程式內寫死枚舉值。

**Task 1.2 — bootstrap 建檔**
- 目標：642 檔全數有 entry（V02 綠），使 Task 1.5 掛載時 catalog 已完整。　檔案：`scripts/testreg.py`（子命令 `bootstrap`）、`tests/registry/catalog.json`。
- 改法：`ticket` 依 `bootstrap.ticket_rule`；其餘欄依 `bootstrap.defaults`。
- **驗證**：bootstrap 後 `testreg.py validate` rc=0；entry 數 == `git ls-files 'tests/test_*.py' 'tests/**/test_*.py' | sort -u | wc -l`；重跑 bootstrap ⇒ catalog sha256 不變（冪等）；`ticket=unknown` 之筆數列於收據 `handoffs/run_receipts/testreg-bootstrap.json`。
- **邊界**：首次提交無票標記 ⇒ `unknown`；改名檔 ⇒ `--follow` 取最早加入提交。
- **存活至**：票收案後保留。　**覆蓋風險**：Phase 3／4 只改委員欄，`ticket` 受 V04 保護。
- 不可做：不為導不出之欄捏造值。

**Task 1.3 — 記錄器**
- 目標：每次 pytest session 自動寫 `ledger` 與增量 `summary`。　檔案：`tests/fixtures/testreg_recorder_plugin.py`（新建）、`tests/conftest.py`（`pytest_plugins` 加入）、`.gitignore`（`.testreg/`）。既有 caller：全部測試經 `tests/conftest.py`。
- 改法：`pytest_sessionstart` 依 `ledger.session_record` 計算各欄（kline 全檔 sha256 依快取鍵；首算後同檔不再算），設 `TESTREG_PARENT_SESSION`；`pytest_runtest_logreport` 累積 setup/call/teardown 為一筆 `test_record`（含 `order`、`exception_type`、`exception_head`）；`pytest_sessionfinish` 一次原子寫 `<session_id>.jsonl` 並原子合併 `summary`（k 依 schema）。
- **驗證**：§G 不變性基準；`pytest tests/registry/test_testreg_recorder.py`：①暫存測試檔含 pass/fail/skip/xfail/error ⇒ ledger 五種 outcome 各一筆、`exception_type` 對應；②巢狀 pytest ⇒ ledger 檔數不變；③monkeypatch 使寫檔丟例外 ⇒ 被測 session rc == 未裝記錄器時；④summary 毀損 ⇒ 下一 session 重建且逐 nodeid 筆數 == min(k, ledger 筆數)；⑤同參數兩次執行 ⇒ `fingerprint` 相等；改 `-p` 或 `PYTEST_ADDOPTS` ⇒ 不等；只改 `-q` ⇒ 相等。mutant：記錄器上拋例外 ⇒ ③紅；巢狀判斷移除 ⇒ ②紅；`argv_norm` 不去 `-q` ⇒ ⑤紅。
- **邊界**：`kline_cache.h5` 不存在 ⇒ `kline_sha256=absent` 仍記錄；session 被 SIGKILL ⇒ 無半寫 jsonl（暫存檔由下一 session 清除）。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不改 `pytest_collection_modifyitems` 既有清冊寫入；不在每條測試後寫檔。

**Task 1.4 — 標記**
- 目標：`pytest.ini` 註冊 `flaky_quarantine`；移除 9 處無效 `pytest.mark.timeout`；`scripts/testreg.py markers` 對未註冊標記 rc≠0。　檔案：`pytest.ini`、`scripts/testreg.py`、含 `pytest.mark.timeout` 之測試檔（以 `grep -rln "pytest.mark.timeout" tests` 列出者）。
- 改法：`markers` 以 AST 掃描 `pytest.mark.<name>` 屬性存取，對照 `pytest.ini` 註冊集合與 pytest 內建集合（`parametrize/skip/skipif/xfail/usefixtures/filterwarnings`）。移除 timeout 宣告依 §N Q1 定案。
- **驗證**：`pytest tests/registry/test_testreg_markers.py`：暫存樹加一未註冊標記 ⇒ rc≠0；註解或字串內之 `pytest.mark.x` ⇒ 不計；現行樹於本 Task 後 `testreg.py markers` rc=0。移除 timeout 之檔：以 `-p no:cacheprovider --collect-only -qq` 於暫存 worktree 收集，改前改後 nodeid 集合 sha256 ==（收據 `handoffs/run_receipts/testreg-timeout-removal.json`）。
- **邊界**：`pytestmark = [pytest.mark.a, pytest.mark.timeout(…)]` 清單形式 ⇒ 只移除 timeout 元素。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不安裝新 pytest 外掛。

**Task 1.5 — 產出端登記檢查**
- 目標：新增、改名或刪除 `tests/**/test_*.py` 而 catalog 不一致 ⇒ 寫檔當下報錯；Bash 建檔與 `git mv`／`git rm` 之漏網由 pre-commit 同檢查擋。　檔案：`scripts/testreg_write_guard.sh`（新建，PostToolUse `Edit|Write`）、`.claude/settings.json`、pre-commit 掛載、`docs/GOV_ENFORCEMENT_REGISTRY.md`（產出端列）。
- 改法：hook 取工具輸入檔路徑；命中測試檔樣式 ⇒ `testreg.py check --paths <p>`（V02、該 entry 之 V03–V07、V11）；pre-commit 以暫存區新增／刪除／改名之測試檔與 `catalog.json` 變更呼叫 `check --staged`（另加 V01、V08–V10）。
- **驗證**：`pytest tests/registry/test_testreg_write_guard.py`：①新測試檔無 entry ⇒ hook rc≠0、訊息含路徑；②補 entry ⇒ rc=0；③`git rm` 測試檔而無碑 ⇒ pre-commit rc≠0；④quarantine 逾期 ⇒ rc≠0；⑤642 entries 下 hook 牆鐘 10 次中位 <1 s（收據）。mutant：hook 恆 rc=0 ⇒ ①紅；pre-commit 不查刪除 ⇒ ③紅。
- **邊界**：`conftest.py`、`tests/fixtures/`、`tests/registry/` 非測試檔 ⇒ 不檢；編輯既有且已登記之測試檔 ⇒ rc=0（不阻正常工作）。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：hook 內不跑 pytest、不讀 git 全史。

### Phase 2 — 複查訊號、挑選器、閘接線、V-6 慢因（依賴：Phase 1）
**Task 2.1 — review 訊號**
- 目標：`scripts/testreg.py review` 輸出 `derived.review_signals` 逐檔逐訊號。　檔案：`scripts/testreg.py`。
- 改法：`prod_symbol_gone`＝測試檔 import 之生產符號於 HEAD AST 不存在（同 FRAMEPATH dead-scan 解析）；`duration_regression` 依 `derived.duration_regression_rule`；`outcome_flip_same_fingerprint`＝summary 中同 fingerprint 不同 outcome；`collect_error`＝最近 session 該檔 outcome=error 且 phase_failed=setup 於收集期；`allowed_red_owner_closed`＝`allowed_red.json` 之 `owner_ticket` 於 `scripts/fact_keys.json` 狀態為已完成（不以 `docs/TICKET_ORDER.md` 判定：其無機讀狀態欄）；`quarantine_expired`＝V11 反例。
- **驗證**：`pytest tests/registry/test_testreg_review.py`：每訊號一正例一反例；mutant：任一訊號判定反轉 ⇒ 對應正例紅；summary 不存在 ⇒ 依賴 ledger 之訊號輸出 `unknown`（斷言字面）。
- **邊界**：同一檔多訊號 ⇒ 全列；無 ledger ⇒ 只出 AST 類訊號＋其餘 `unknown`。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：訊號不寫回 catalog；不接任何略過邏輯。

**Task 2.2 — impact 挑選器**
- 目標：`scripts/testreg.py impact --changed-from <git-range|worktree> --manifest <m> --phase <n>` 依 `impact` 契約輸出（單位依 `impact.output_unit`）。　檔案：`scripts/testreg.py`。
- 改法：`must`＝manifest 必跑；`changed_test`＝變更之測試檔；`static_taint`＝呼叫 `framepath_affected_gate._TaintGraph`；`previously_failed`＝summary 中最近一筆 outcome∈{failed,error,xpassed} 之 nodeid 所在檔；`registry_unresolved` 依 `impact.registry_unresolved_rule`、`impact.domain_rule`、`impact.shared_test_infra`。生產檔變更本身不觸發 unresolved（catalog 只登記測試檔）。
- **驗證**：`pytest tests/registry/test_testreg_impact.py`：①改 `tests/conftest.py` ⇒ selected == 全部測試檔；②改 `tests/feature_engineering/conftest.py`（暫存）⇒ selected ⊇ 該目錄全部測試檔；③生產檔可被 taint 解析 ⇒ 不出現 `registry_unresolved`；④生產檔含 `importlib.import_module(var)` 不可定 ⇒ selected ⊇ domain 且 domain 依 `domain_rule` 之重算 ==；⑤任何輸入 selected ⊇ manifest 必跑；⑥構造各來源皆空 ⇒ selected 非空或 rc≠0（不輸出空集合）；⑦catalog validate 失敗 ⇒ rc≠0。mutant：聯集改交集 ⇒ ⑤紅；domain 改取一層 ⇒ ④紅；shared_test_infra 移除 ⇒ ①紅。
- **邊界**：manifest 不含 `affected_tests` ⇒ rc≠0；變更檔為已立碑之測試 ⇒ `tombstoned` 且附碑。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不實作覆蓋率收集（§N R1）；不以 `size_class` 排除。

**Task 2.3 — FRAMEPATH 閘接線**
- 目標：`scripts/framepath_affected_gate.py` 之 plan 吃 impact 聯集、解析碑、判隔離失敗、修接續指紋。　檔案：`scripts/framepath_affected_gate.py`。既有 caller：FRAMEPATH b2／b3 之 gate。
- 改法：①plan 依 `impact.gate_feed`；②manifest 指向之 nodeid／檔若已立碑 ⇒ 以碑之 `replaced_by` 取代（E0 碑無 replaced_by ⇒ 列 `tombstoned` 排除且附碑），不再因 collect 不到而拒跑；③verdict：`caused` 失敗之 nodeid 若有未逾期 quarantine ⇒ 歸 `quarantined_failure`，不擋 verdict、列報；逾期 ⇒ 照擋；④`inputs_digest` 之未追蹤內容排除本次 `--out` 目錄（前綴由參數導出）；`--out` 為 repo 根 ⇒ rc≠0。
- **驗證**：`pytest tests/feature_engineering/test_framepath_disposition.py -k "affected_gate"`（新增案例）：②manifest 列已立碑 E1 nodeid ⇒ plan 含其 replaced_by、不拒跑；③有效隔離之 caused 失敗 ⇒ verdict pass 且報告列 `quarantined_failure`；逾期 ⇒ verdict fail；④分段一後於 out 目錄新增 junit ⇒ 接續 digest 不變；新增非 out 之未追蹤原始碼 ⇒ digest 變；①以 `handoffs/run_receipts/framepath-b1-affected-plan.json` 重放 ⇒ 新計畫 selected ⊇ 原計畫。mutant：②之取代移除 ⇒ 拒跑而紅；③不查 expires ⇒ 逾期案紅；④排除前綴改空 ⇒ digest 案紅。
- **邊界**：碑之 replaced_by 指向亦已立碑之 nodeid ⇒ 遞迴解析，循環 ⇒ rc≠0；quarantine 之 nodeid 參數化 ⇒ 以函式層比對。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不放寬其他 digest 成分；不改 FRAMEPATH 已凍結之 manifest 內容。

**Task 2.4 — V-6 慢因**
- 目標：具名 `tests/feature_engineering/test_failopen_correctness.py` 中耗時 1:39:36 之 `test_v6_*` 項並定慢因。　檔案：收據 `handoffs/run_receipts/testreg-v6-profile.json`。
- 改法：D10 執行器跑該檔（記錄器開），取逐項耗時；最慢項以 `cProfile` 單項執行取前 30 累計熱點；歸類「測試端重複計算」或「生產端本身耗時」。前者改測試須附 `receipts.mutation` 收據證不減驗證力，交委員審；後者登 §N。
- **驗證**：`handoffs/run_receipts/testreg-v6-profile.json` 含逐項耗時（秒）、前 30 熱點、歸類與碼證 `file.py:line`；若改測試，改前改後逐 nodeid outcome sha256 == 且附 mutation 收據。
- **邊界**：記憶體不足被終止 ⇒ 以 `watch_run.sh` 記峰值，重試至多一次。
- **存活至**：票收案。　**覆蓋風險**：無。
- 不可做：不以縮小資料窗、降低 symbol 數等減少驗證範圍之方式提速（樣本 symbol 數、資料窗長度 == 現行值）。

### Phase 3 — Feature Factory 相關測試分類與執行（依賴：Phase 1、Phase 2）
**Task 3.1 — 分類（只改 catalog 委員欄）**
- 目標：`tests/feature_engineering/` 全部、根層 `tests/test_*.py` 與 `tests/momentum/feature_engineering/` 中 inventory `prod_modules` 含 `momentum.FeatureEngineering` 者，逐檔定 `guarantee/oracle/claim/disposition`，並列擬立碑之 nodeid 與擬用證據等級。　檔案：`tests/registry/catalog.json`；收斂檔 `handoffs/reconcile/<session>/synth.md`。
- 改法：三家各自獨立逐檔判定（brief 附 inventory 列、summary 耗時、`allowed_red` 列、review 訊號）；一致者採；不一致者依碼證裁決；FRAMEPATH 諮詢 r4 已判之 30 檔併入。屬 `allowed_red` 且 owner 票未收案之 nodeid 不得擬淘汰。
- **驗證**：`testreg.py validate` rc=0；範圍內 `jq` 計 `guarantee==["unclassified"]` == 0（收據附命令）；三家原始判定檔與裁決列皆在 synth。
- **邊界**：三家皆擬淘汰但無可得之證據等級 ⇒ `keep`，登 §N `needs-research`；某檔只部分函式擬淘汰 ⇒ 只列該些函式。
- **存活至**：票收案後保留。　**覆蓋風險**：Task 3.2 只增碑與 rewrite_receipt，不改分類欄。
- 不可做：不以「未執行過」「年代久」「慢」為擬淘汰理由。

**Task 3.2 — 執行（分子批，每子批 ≤20 個目標檔）**
- 目標：依 Task 3.1 執行 rewrite 與立碑刪除。　檔案：目標測試檔、`tests/registry/catalog.json`、收據 `handoffs/run_receipts/testreg-retire/<nodeid-slug>.json` 與 `testreg-rewrite/<slug>.json`。
- 改法：每子批：產生收據 → `validate` → 經 FRAMEPATH D10 執行器跑該子批之 impact 選中集合 → 子批造成之紅＝0 → 單一提交（可單獨 revert）。
- **驗證**：每子批 `testreg.py validate` rc=0（V07–V10）；執行器 verdict pass；子批提交訊息列子批編號與收據清單。
- **邊界**：收據驗不過 ⇒ 該 nodeid 退回 `keep` 並登 §N；執行中暫停 ⇒ 依 D10 分段續跑，不重來。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不跨子批合併提交；不改 FRAMEPATH manifest。

**Task 3.3 — 成效報告**
- 目標：「淘汰幾函式、幾檔、證據等級分布、以 summary 中位耗時計之每次全跑節省秒數（無紀錄列 unknown 不估）」。　檔案：`handoffs/run_receipts/testreg-phase3-effect.json`。
- **驗證**：`venv/bin/python scripts/testreg.py effect --recompute handoffs/run_receipts/testreg-phase3-effect.json` 由 catalog 碑與 summary 重算，逐數字 == 報告值則 rc=0。
- **邊界**：summary 無紀錄 ⇒ 節省秒數 unknown，不寫 0。
- **存活至**：票收案。　**覆蓋風險**：Task 4.3 產全庫版，不覆寫本檔。
- 不可做：不外插估算。

### Phase 4 — 其餘目錄分類、執行與收案（依賴：Phase 3）
**Task 4.1 — 其餘分類**
- 目標：Phase 3 未涵蓋之全部測試檔完成分類。改法同 Task 3.1；目錄順序依 `docs/manifests/*.json` 中 `affected_tests` 引用次數由高到低（機械計數，收據附）。
- **驗證**：`testreg.py validate` rc=0；全庫 `guarantee==["unclassified"]` 計數 == 0。
- **邊界**：同 Task 3.1。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：同 Task 3.1。

**Task 4.2 — 其餘執行**
- 目標：同 Task 3.2，對 Task 4.1 之結果。
- **驗證**：同 Task 3.2（每子批 validate rc=0、verdict pass）。
- **邊界**：同 Task 3.2。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：同 Task 3.2。

**Task 4.3 — 全庫成效報告與收案**
- 目標：全庫版報告（同 Task 3.3 格式）。　檔案：`handoffs/run_receipts/testreg-final-effect.json`。
- **驗證**：`testreg.py effect --recompute` rc=0；`testreg.py validate` rc=0。
- **邊界**：任一檔處置阻於後續票 ⇒ 分類仍須填，處置以 `blocked-by` 登 §N。
- **存活至**：票收案。　**覆蓋風險**：無。
- 不可做：不以收案為由跳過任一檔。

## §V 驗證策略與邊界測試目錄
- mutation：各 Task 驗收已列 mutant；本票三性質「只加不減」「記錄器不改行為」「無收據不刪」各至少一 mutant 必紅（Task 2.2⑤、Task 1.3③與 §G、Task 1.1 V08／V09 反例）。
- 測試層級：單元（schema 規則、訊號、impact 規則）／整合（暫存樹內真實 pytest 子程序；記錄器不變性於真實測試樣本）／回放（b1 gate 計畫收據）。全部可獨立 `pytest tests/registry/` 跑，不需 `run_api.py`。
- 防假綠：既有測試斷言只可經 Task 3.2／4.2 之 rewrite（附 mutation 收據）或立碑（附證據收據）改變。
- 邊界目錄：空／缺 catalog（1.1）、冪等（1.2）、毀損 summary（1.3）、巢狀 session（1.3）、SIGKILL 半寫（1.3）、清單式 pytestmark（1.4）、無登記新檔與刪檔無碑（1.5）、逾期隔離（1.5、2.1、2.3）、各來源皆空（2.2）、碑循環（2.3）、記憶體不足（2.4）。

## §R 回退
- 每 Phase、每子批獨立提交；記錄器以 `-p no:testreg_recorder` 或自 `pytest_plugins` 移除即停用，不影響任何測試結果。
- 淘汰為刪檔：revert 該子批提交即同時回復測試與刪碑。
- 閘接線回退＝plan 不讀 impact 輸出、不解析碑；原計畫不變（加法性質保證回退不減選）。

## §N N/A 登記與殘留
- **委員審議項（v2 主委定案，請 r2 判定）**：
  - Q1（`timeout` 標記）：移除 9 處無效宣告（Task 1.4）。理由：未安裝外掛，宣告無任何效力，移除為行為恆等（以改前改後 nodeid 集合相等驗）；安裝外掛則會改變該 9 處執行行為（新增逾時失敗），屬引入新行為而非清冊範圍。卡住偵測於閘級執行由 D10 監看承擔；一般手動 pytest 無逾時保護，此為現況（未因本票變差）。
  - Q2（k 與複查閾值）：k＝20、`duration_regression_rule` 如 schema。現無同設定多次執行之耗時資料可校準（b1 收據每項僅一次）；此訊號只標記不影響挑選，誤設之代價為複查清單噪音，不減驗證。
- **殘留**：
  - R1 動態覆蓋對照表（逐行覆蓋率→測試，原 `dynamic_hit`）— `為何現在不做: blocked-by:Task 1.3 記錄器上線後須另收覆蓋邊（ledger 無檔案觸及欄）`；觸發：summary 中 ≥80% 測試檔具 ≥3 筆同 env_class 紀錄；登記處：`白話說明/還沒做的事.md` 第四節。
  - R2 定期全套自動執行 — `為何現在不做: user-ruling:2026-08-13 使用者刪除全部 CI（.github/workflows/）`；觸發：使用者恢復 CI；登記處：同上。
  - R3 測試前提過期之自動偵測（斷言所守規則已被改寫）— `為何現在不做: needs-research:前提與規則之機械對應無既有業界做法`；觸發：研究得出可證偽判準；登記處：同上。
  - R4 名稱層級之陳舊（測試名與所測行為不符）— `為何現在不做: needs-research:無可機械判定之訊號`；觸發：同上；登記處：同上。
  - R5 E2 之 mutant 集合是否足以代表原測試所守性質 — `為何現在不做: needs-research:mutant 充分性無機械判準`；現由每子批審碼之委員判定；觸發：出現可機械產生充分 mutant 之工具；登記處：同上。
