# TESTREG：測試清冊自動維護與受影響測試挑選 — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 5a 步；諮詢 r1 收斂 `handoffs/reconcile/20261009-testreg-x-consult-r1/synth.md`（26 條全處置、三家 proceed；主委獨立版 `handoffs/20261009-testreg-x-consult-r1-claude.md`）；靜態盤點 `handoffs/run_receipts/testreg_probes/20261010-test-inventory.json`　|　日期：2026-10-10　|　對應 TODO：`docs/manifests/TESTREG.json`（SPEC 凍結後生成）
> 版本：v14（審查 r13 `handoffs/reconcile/20261010-testreg-x-review-r13/synth.md` 3 條處置後改版；契約 version 14）
> 契約單一真相源：`tests/registry/testreg_schema.json`（欄位、枚舉、證據收據格式、驗證規則 V01–V22、挑選規則、閘收據欄皆只定義於該檔；本 SPEC 以鍵名引用，不重列值）。

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
- **淘汰只以碑、只憑收據**：淘汰單位為函式層 nodeid；整檔淘汰＝該檔全部函式各一碑；每碑之收據須依 `receipts` 對應規則機械驗過（V08、V09）。提交年齡、未執行、單次成本不得作證據。E0 須於 HEAD 失敗，且失敗位置為目標測試檔中一個 `from <deleted_module> import <deleted_symbol>`（ImportError 類）或 `<模組名>.<deleted_symbol>`（AttributeError，模組名由本檔模組層 import 綁定）之行，靜態解析到的 (deleted_module, deleted_symbol) 確曾定義於 `receipts.E0.production_roots` 並由 `deleting_commit` 刪除（`receipts.E0.rule`）；於 HEAD 通過之負向守衛、局部變數或 setup 回傳值之屬性錯誤、測試自身 helper、從未存在於生產碼之選用依賴皆不可能持 E0。E1 只限完全重複（函式與 fixture 閉包 AST 相等）；其餘一律 E2。
- **改寫只憑 mutation 收據**：`rewrite` 執行後須有 `receipts.mutation` 格式收據——至少一個 mutant 殺 target（無斷言節點者亦然）、target 每一斷言行（`assertion_nodes`，含 numpy／pandas 之 assert 呼叫與 `pytest.deprecated_call`）至少一個 mutant 於該行使 target 失敗，且每一被 target 殺之 mutant 改寫後至少一條仍殺；對應 `docs/TEST_DESIGN_CHARTER.md` §B1 之可證偽要求。V07 使「改了待改寫檔卻無收據」之提交不可能。
- **斷言面只增不減（全專案）**：任何提交使某測試函式之 `assertion_nodes`（依 `assertion_nodes.inline_rule` 展開 tests/ 下 helper 與 fixture，並含名稱符合 check_／verify_／validate_／expect_ 之呼叫；區域名正規化後比對，故純改名與抽 helper 不算減少，改 helper 刪斷言則每一呼叫者皆算減少）多重集合減少 ⇒ 須同提交立碑或走 rewrite 收據（V19）；刪除或改名測試函式 ⇒ 須同提交立碑（V20）；適用所有票（含 FRAMEPATH b2／b3 之測試處置），由產出端 hook 與 pre-commit 擋。
- **隔離不變綠**：`flaky_quarantine` 之測試照跑；票級閘依 Task 2.3 將其失敗列入 `gate_report.quarantined_failures` 不擋但列報；不得 rerun 取綠；隔離須有 ledger 同 fingerprint 之 passed 與 failed／error 翻轉證據（V12）且未逾期（V11）。
- **退役不留斷鏈**：新碑所指 nodeid／路徑出現在某 manifest，而該 manifest 既非 `manifest_status.manifest_closed`、亦非 `manifest_status.manifest_tombstone_aware` ⇒ 不得立碑（V14）。
- 真實資料重測試單組串行；長跑一律走分段續跑執行器（FRAMEPATH D10 執行器）＋監看，不得被背景上限砍斷重來。
- 跑完測試執行 `bash scripts/restore_golden_inventory.sh`。

## §G Golden／Baseline
- 本票不改數值計算；Golden 對象為「測試行為」與「淘汰／改寫收據」兩者。
- **記錄器不變性基準**（Task 1.3 動工前凍結）：固定樣本＝`tests/feature_engineering/test_framepath_disposition.py`、`tests/governance/test_mutation_scope_extension.py`、`tests/api` 依路徑字典序前 10 檔（凍結時寫死清單於收據）。於動工前 HEAD 以 `-p no:cacheprovider -v` 執行，存：①逐 nodeid outcome 之排序後 sha256；②執行順序（`-v` 輸出之 nodeid 序列）sha256；③rc；④`git status --porcelain --ignored` 之 sha256；收據 `handoffs/run_receipts/testreg-recorder-baseline.json`。通過條件：裝記錄器後同命令之①②③逐項 == 基準；④去除 `.testreg/` 開頭之列後 == 基準。集合比對無數值容差（atol/rtol 不適用）。
- **淘汰／改寫收據**即各自之 golden，由 V07–V09 機械驗。

## §P Phase 與依賴

### Phase 1 — 契約、清冊建檔、記錄器、標記、產出端登記（依賴：無；Task 順序 1.1→1.2→1.3→1.4→1.5）
**Task 1.1 — 契約與 validate**
- 目標：`scripts/testreg.py validate` 依 `tests/registry/testreg_schema.json` 之 `validation_rules` V01–V22 逐條實作。　檔案：`scripts/testreg.py`（新建）。既有 caller：無。
- 改法：每條規則一個具名函式，錯誤訊息帶規則 id；enum 一律讀 schema（含 `items_enum` 所指之 `enums.charter_category` 等）；不另存副本。
- **驗證**：`pytest tests/registry/test_testreg_validate.py`：V01–V22 各一正例一反例（暫存 catalog／暫存 git 倉）；另含收據反例——E0：①目標於 HEAD 通過、②失敗行位於 helper 而非目標測試檔、③缺失符號從未存在於 production_roots、④符號定義於 tests/ 內、⑤失敗行為 `obj.sym`（obj 為 setup 回傳值而非模組 import 綁定）且同名 `sym` 已自生產碼刪除、⑥局部名 NameError、⑦測試或 conftest 先 `monkeypatch.setattr(mod, "sym", …)` 後 delattr 製造 AttributeError，各 ⇒ V08 紅；E1：fixture 定義不同而函式相同、autouse fixture 不同、或函式所引用之模組層常數／pytestmark 不同 ⇒ 紅；收據綁定：E2 收據之 target_nodeid 與碑 nodeid 不同、或本提交新增之收據 head 不等於 HEAD、或 E2／rewrite 收據之 session 於 ledger 不存在或 outcome 不符（一般 pre-commit 即紅，不待 V21）⇒ V07／V08 紅；既有碑改換 replaced_by 而該碑 nodeid 在不安全之 manifest ⇒ V14 紅；V17：收據多一未知欄、head 非 40-hex ⇒ 紅；fixture 斷言：target 之斷言位於 autouse fixture，殺 mutant 於 setup 期失敗且 frame 落在該 fixture ⇒ 計入（綠）；mutation：compare_nodeids 為 replaced_by 之真子集、或 compare_outcomes 多一個未列之 nodeid 鍵、或殺 mutant 之 target 失敗於 setup（無斷言 target 以 import 期破壞冒充）⇒ 紅；E1：所在類別基底類別之 setup_method 不同 ⇒ 紅；mutation binding：compare_outcomes 填 failed 而所指 session 之紀錄為 passed、session 之 diff_digest 與套用 patch 重算值不符、或 session 無該 nodeid 紀錄 ⇒ 紅；V21：disposition=rewrite 而 rewrite_receipt 為 null 時 `validate --require-executed` ⇒ 紅、一般 validate ⇒ 綠；V17：impact_result.selected 為空陣列、summary 某 nodeid 紀錄數超過 k ⇒ 紅；mutation：某斷言行無對應 mutant、`assert_allclose` 或 `pytest.deprecated_call` 行未列入 target_assertion_lines、無斷言 target 而 mutants 為空、mutant patch 改測試檔 ⇒ 紅；V03：map 鍵與 path 欄不同 ⇒ 紅；V17：nodeid 格式錯、expires 非日期、path 含 `..` 段或以 `/` 開頭、quarantine.evidence 元素缺 session_id 或格式錯各 ⇒ 紅；V14：manifest gate_cmd 為 `python scripts/framepath_affected_gate.py && pytest tests/x.py` 或含 `$(pytest tests/x.py)` ⇒ 非 tombstone_aware ⇒ 紅；manifest spec_path 未出現在 handoff-pending ⇒ 非 closed；V16／V18：一般提交新增 entry 含 unclassified、把已分類 entry 改回 unclassified、或改 bootstrap_paths.txt ⇒ 紅；V19：刪一個 `assert`、把 `assert_allclose` 換成較弱斷言、刪一個呼叫 tests/ 內含斷言 helper 之行、刪一個 `validate_*` 生產碼呼叫、改共享 helper 刪其一個斷言（其每一呼叫者皆紅）而無收據 ⇒ 紅；只把區域變數改名、把三個斷言抽成 helper 後呼叫之 ⇒ 綠；V16：`["A1","unclassified"]` 混用 ⇒ 紅；V20：刪除或改名測試函式而無碑 ⇒ 紅；改名兼改內容而附 E2 碑 ⇒ 綠；V14：本票 Phase 3 子批之立碑（閘為 framepath_affected_gate）⇒ 綠；summary：schema_version 不符之舊檔、或某 summary_record 多出未知鍵 ⇒ 重建（Task 1.3 ④同法）；V09：同提交改名之 E1 碑（replacement 只存在於暫存區之樹）⇒ 綠；V14：碑路徑只出現在 manifest 之 contract_jsons 或說明字串 ⇒ 不計；出現在 `affected_must phase=…` 列 ⇒ 計；mutant：任一規則函式改為恆真 ⇒ 其反例紅；`grep -c "A22\|EXACT\|correctness" scripts/testreg.py` == 0（無枚舉副本）。
- **邊界**：catalog 不存在 ⇒ rc≠0 並具名；ledger 目錄不存在而 catalog 有 quarantine ⇒ V12 報 unverifiable、rc≠0。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不在程式內寫死枚舉值。

**Task 1.2 — bootstrap 建檔**
- 目標：642 檔全數有 entry（V02 綠），使 Task 1.5 掛載時 catalog 已完整。　檔案：`scripts/testreg.py`（子命令 `bootstrap`）、`tests/registry/catalog.json`。
- 改法：`ticket` 依 `bootstrap.ticket_rule`；其餘欄依 `bootstrap.defaults`；同時寫出 `bootstrap.paths_file`（V16、V18 之依據）。
- **驗證**：bootstrap 後 `testreg.py validate` rc=0；entry 數 == `git ls-files 'tests/test_*.py' 'tests/**/test_*.py' | sort -u | wc -l`；重跑 bootstrap ⇒ catalog sha256 不變（冪等）；`ticket=unknown` 之筆數列於收據 `handoffs/run_receipts/testreg-bootstrap.json`。
- **邊界**：首次提交無票標記 ⇒ `unknown`；改名檔 ⇒ `--follow` 取最早加入提交。
- **存活至**：票收案後保留。　**覆蓋風險**：Phase 3／4 只改委員欄，`ticket` 受 V04 保護。
- 不可做：不為導不出之欄捏造值。

**Task 1.3 — 記錄器**
- 目標：每次 pytest session 自動寫 `ledger` 與增量 `summary`。　檔案：`tests/fixtures/testreg_recorder_plugin.py`（新建）、`tests/conftest.py`（`pytest_plugins` 加入）、`.gitignore`（`.testreg/`）。既有 caller：全部測試經 `tests/conftest.py`。
- 改法：`pytest_sessionstart` 依 `ledger.session_record` 計算各欄（kline 全檔 sha256 依快取鍵；鍵相同才沿用），設 `TESTREG_PARENT_SESSION`；`pytest_runtest_logreport` 累積 setup/call/teardown 為一筆 `test_record`（含 `order`、`exception_type`、`exception_head`、`exception_origin`、`fail_line`）；`pytest_collectreport` 之失敗收集寫 `ledger.collect_record`；`pytest_sessionfinish` 一次原子寫 `<session_id>.jsonl`，並於 `summary.lock` 獨占鎖內合併 `summary`（k 依 schema）。
- **驗證**：§G 不變性基準；`pytest tests/registry/test_testreg_recorder.py`：①暫存測試檔含 pass/fail/skip/xfail/xpass/error（setup 失敗）/teardown 失敗而 call 通過、call 為 skip 或 xfail 而 teardown 失敗 ⇒ 各 outcome 依 `ledger.outcome_aggregation` 逐條對應（call 未失敗而 teardown 失敗 ⇒ error；call 與 teardown 皆失敗 ⇒ failed 且 teardown_failed=true）；summary 某 nodeid 紀錄超過 k 筆或 started 非 ISO-UTC ⇒ 重建、`exception_type`／`exception_origin`／`fail_line` 對應；②巢狀 pytest ⇒ ledger 檔數不變；③monkeypatch 使寫檔丟例外 ⇒ 被測 session rc == 未裝記錄器時；④summary 毀損 ⇒ 下一 session 重建且逐 nodeid 筆數 == min(k, ledger 筆數)；⑤同參數兩次執行 ⇒ `fingerprint` 相等；改 `-p`、`-k`、位置參數順序、`PYTEST_ADDOPTS` 或 `NUMBA_DISABLE_JIT` ⇒ 不等；只改 `-q`、或 `--tb=short` 改寫為 `--tb short`、或 `-rA` 改寫為 `-r A` ⇒ 相等；ledger 中 duration_s 為負值或 NaN ⇒ V17 紅；⑥兩個 session 並行結束 ⇒ summary 含兩者全部紀錄；⑦暫存 kline 檔以同 size 覆寫內容並以 `os.utime` 回設 mtime ⇒ `kline_sha256` 改變；⑧雜湊進行中改寫檔（注入）⇒ 不寫快取；兩 session 並行寫快取 ⇒ 快取為合法 JSON 且鍵值正確；⑨暫存測試檔 import 不存在之模組 ⇒ ledger 有一筆 `collect_record` 且 path 正確。mutant：記錄器上拋例外 ⇒ ③紅；巢狀判斷移除 ⇒ ②紅；`argv_norm` 不去 `-q` ⇒ ⑤紅；去鎖 ⇒ ⑥紅（以注入延遲使交錯必現）；快取鍵去 ctime ⇒ ⑦紅。
- **邊界**：`kline_cache.h5` 不存在 ⇒ `kline_sha256=absent` 仍記錄；session 被 SIGKILL ⇒ 無半寫 jsonl（暫存檔由下一 session 清除）。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不改 `pytest_collection_modifyitems` 既有清冊寫入；不在每條測試後寫檔。

**Task 1.4 — 標記**
- 目標：`pytest.ini` 註冊 `flaky_quarantine` 與 `timeout`（後者描述註明「需 pytest-timeout，現未安裝故不生效」）；9 處 `pytest.mark.timeout` 宣告保留不動；`scripts/testreg.py markers` 對未註冊標記 rc≠0。　檔案：`pytest.ini`、`scripts/testreg.py`。
- 改法：`markers` 以 AST 掃描 `pytest.mark.<name>` 屬性存取，對照 `pytest.ini` 註冊集合與 pytest 內建集合（`parametrize/skip/skipif/xfail/usefixtures/filterwarnings`）。`timeout` 之處置依 §N Q1 定案（保留並註冊）。
- **驗證**：`pytest tests/registry/test_testreg_markers.py`：暫存樹加一未註冊標記 ⇒ rc≠0；註解或字串內之 `pytest.mark.x` ⇒ 不計；現行樹於本 Task 後 `testreg.py markers` rc=0；`git diff` 於含 `pytest.mark.timeout` 之 9 處測試檔為空（`grep -c "pytest.mark.timeout"` 改前改後 == 9）。
- **邊界**：`pytestmark = [pytest.mark.a, pytest.mark.timeout(…)]` 清單形式 ⇒ 兩者皆計入掃描、皆須已註冊。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不安裝新 pytest 外掛。

**Task 1.5 — 產出端登記檢查**
- 目標：新增、改名或刪除 `tests/**/test_*.py` 而 catalog 不一致 ⇒ 寫檔當下報錯；Bash 建檔與 `git mv`／`git rm` 之漏網由 pre-commit 同檢查擋。　檔案：`scripts/testreg_write_guard.sh`（新建，PostToolUse `Edit|Write`）、`.claude/settings.json`、pre-commit 掛載、`docs/GOV_ENFORCEMENT_REGISTRY.md`（產出端列）。
- 改法：hook 取工具輸入檔路徑；命中測試檔樣式或 `catalog.json` ⇒ `testreg.py check --paths <p>`（V02、該 entry 之 V03、V05、V06、V11、V15、V16、V17，及該檔相對 HEAD 之 V19、V20）；命中 `docs/manifests/*.json` ⇒ `check --manifest <p>`（對該 manifest 跑 V22）；命中 `tests/` 下其他 `.py`（conftest、fixtures、helper 模組）⇒ `check --helpers <p>`：以 `assertion_nodes.inline_rule` 找出受影響之全部呼叫者測試函式，對其逐一跑 V19；pre-commit 於暫存區含任一 `tests/**/*.py`、`catalog.json` 或 `docs/manifests/*.json` 變更時呼叫 `check --staged`（V01–V20 與 V22，V19 含 helper 反推之呼叫者；V21 只於 `validate --require-executed` 收尾時跑，pre-commit 不跑，故分類後尚未執行之 rewrite 可正常提交）。
- **驗證**：`pytest tests/registry/test_testreg_write_guard.py`：①新測試檔無 entry ⇒ hook rc≠0、訊息含路徑；②補 entry 但分類欄為 unclassified ⇒ rc≠0（V16）；補完整分類 ⇒ rc=0；③`git rm` 測試檔而無碑 ⇒ pre-commit rc≠0；④quarantine 逾期 ⇒ rc≠0；⑤待改寫檔有暫存變更而無收據 ⇒ pre-commit rc≠0（V07）；⑥新碑所指路徑在未收案且閘不解析碑之 manifest ⇒ rc≠0（V14）；⑦Edit 刪除已登記 keep 檔之一個斷言 ⇒ hook rc≠0（V19）；⑦b Edit 刪除 keep 檔內整個測試函式（檔仍留）⇒ hook 當下 rc≠0（V20）；⑦c Edit 刪除 `tests/conftest.py` 或 `tests/fixtures/` 內某 helper 之一個斷言 ⇒ hook 當下 rc≠0 並列出受影響呼叫者；只改該 helper 之區域變數名 ⇒ rc=0；⑦d 只把斷言所用之區域常數 `tol = 1e-9` 改為 `1e-3` ⇒ rc≠0（常數摺疊後元素改變）；⑦e `check(actual, 3)` 改 `check(actual, 4)`（helper 以該參數為門檻）⇒ rc≠0；⑦f `assert result == expected` 改 `assert result == result` ⇒ rc≠0；⑦g 把 `tol = 1e-9; assert abs(d) < tol` 抽成 `check(d, tol)`（helper `assert abs(x) < t`）⇒ rc=0；⑦h `assert a < b` 改 `assert b < a` ⇒ rc≠0；⑦i 刪除同模組 autouse fixture 內之一個斷言 ⇒ 該模組每一測試 rc≠0；⑦j 刪除以 `*args` 呼叫之 helper 內一個斷言 ⇒ 呼叫者 rc≠0；⑦k 在斷言前插入一行無關區域賦值 ⇒ rc=0；⑦l autouse fixture 所依賴之普通 fixture 內刪一個斷言 ⇒ 受影響測試 rc≠0；⑦m 把 `tests/helpers/tolerances.py` 之模組層 `TOL = 1e-9` 改 `1e-3`（測試以 `from tests.helpers.tolerances import TOL` 或 `import tests.helpers.tolerances as tol` 後 `tol.TOL`、或 `from tests.helpers import tolerances` 後 `tolerances.TOL` 使用、或 helper 以 `def check(x, t=TOL)` 預設值使用）⇒ 使用該常數之測試 rc≠0；⑦n 某 open 且閘不解析碑之 manifest 新增一列含既有碑之 nodeid，暫存區只含該 manifest（無 tests 或 catalog 變更）⇒ Edit 當下 hook rc≠0 且 pre-commit rc≠0（V22）；⑧642 entries 下 hook 牆鐘 10 次中位 <1 s（收據）。mutant：hook 恆 rc=0 ⇒ ①紅；pre-commit 不查刪除 ⇒ ③紅；V07 只查 rewrite_receipt 非 null 方向 ⇒ ⑤紅；V19 只比斷言數不比多重集合 ⇒「換成較弱斷言」案紅。
- **邊界**：`tests/` 外之檔 ⇒ 不檢；`tests/registry/` 之非 .py 契約檔 ⇒ 只跑 validate；編輯既有且已登記之測試檔或 helper 而斷言多重集合不減 ⇒ rc=0（不阻正常工作）；新增斷言 ⇒ rc=0；hook 對 helper 反推呼叫者之牆鐘同列入⑧之 <1 s 量測。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：hook 內不跑 pytest、不讀 git 全史。

### Phase 2 — 複查訊號、挑選器、閘接線、V-6 慢因（依賴：Phase 1）
**Task 2.1 — review 訊號**
- 目標：`scripts/testreg.py review` 輸出 `derived.review_signals` 逐檔逐訊號。　檔案：`scripts/testreg.py`。
- 改法：`prod_symbol_gone`＝測試檔 import 之生產符號於 HEAD AST 不存在（同 FRAMEPATH dead-scan 解析）；`duration_regression` 依 `derived.duration_regression_rule`；`outcome_flip_same_fingerprint`＝summary 中同 fingerprint 不同 outcome；`collect_error`＝最近一個收集過該檔之 session 有該檔之 `ledger.collect_record`；`allowed_red_owner_closed`＝`allowed_red.json` 之 `owner_ticket` 於 `scripts/fact_keys.json` 狀態為已完成（不以 `docs/TICKET_ORDER.md` 判定：其無機讀狀態欄）；`quarantine_expired`＝V11 反例。
- **驗證**：`pytest tests/registry/test_testreg_review.py`：每訊號一正例一反例；mutant：任一訊號判定反轉 ⇒ 對應正例紅；summary 不存在 ⇒ 依賴 ledger 之訊號輸出 `unknown`（斷言字面）。
- **邊界**：同一檔多訊號 ⇒ 全列；無 ledger ⇒ 只出 AST 類訊號＋其餘 `unknown`。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：訊號不寫回 catalog；不接任何略過邏輯。

**Task 2.2 — impact 挑選器**
- 目標：`scripts/testreg.py impact --changed-from <git-range|worktree> --manifest <m> --phase <n>` 依 `impact` 契約輸出（單位依 `impact.output_unit`）。　檔案：`scripts/testreg.py`。
- 改法：`must`＝manifest 必跑；`changed_test`＝變更之測試檔；`static_taint`＝呼叫 `framepath_affected_gate._TaintGraph`；`previously_failed`＝summary 中最近一筆 outcome∈{failed,error,xpassed} 之 nodeid 所在檔；`registry_unresolved` 依 `impact.registry_unresolved_rule`、`impact.domain_rule`、`impact.shared_test_infra`。生產檔變更本身不觸發 unresolved（catalog 只登記測試檔）。
- **驗證**：`pytest tests/registry/test_testreg_impact.py`：①改 `tests/conftest.py` ⇒ selected == 全部測試檔；②改 `tests/feature_engineering/conftest.py`（暫存）⇒ selected ⊇ 該目錄全部測試檔；③生產檔可被 taint 解析 ⇒ 不出現 `registry_unresolved`；④生產檔含 `importlib.import_module(var)` 不可定 ⇒ selected ⊇ domain 且 domain 依 `domain_rule` 之重算 ==；④b 暫存樹中測試只經 `momentum/factories.py` 之函式內 import 間接到達變更模組 ⇒ 該測試 ∈ domain；④c 測試 import 含不可定動態 import 之模組 ⇒ 該測試 ∈ 任何 domain；⑤任何輸入 selected ⊇ manifest 必跑；⑤b 同 changed_paths／must_resolved 下 previously_failed 參數新增一 nodeid ⇒ 其檔進 selected 且理由含 previously_failed；⑤c 只改 `tests/helpers/` 下某 helper 模組 ⇒ selected ⊇ import 閉包含該模組之全部測試檔；⑤d `affected_must` 含已立碑且跨檔 E1 之 nodeid ⇒ must_resolved 為其 replaced_by 之 nodeid、replacement 所在檔以理由 must 進 selected、原已刪路徑不在 selected／excluded；⑤e must_resolved 只含 nodeid，manifest_groups 之 B/C 候選檔不以 must 理由出現；⑥構造各來源皆空 ⇒ selected 非空或 rc≠0（不輸出空集合）；⑦catalog validate 失敗 ⇒ rc≠0。mutant：聯集改交集 ⇒ ⑤紅；domain 改取一層 ⇒ ④紅；閉包改只取直接 import ⇒ ④b 紅；shared_test_infra 移除 ⇒ ①紅。
- **邊界**：manifest 不含 `affected_tests` ⇒ rc≠0；變更檔為已立碑之測試 ⇒ `tombstoned` 且附碑。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不實作覆蓋率收集（§N R1）；不以 `size_class` 排除。

**Task 2.3 — FRAMEPATH 閘接線**
- 目標：`scripts/framepath_affected_gate.py` 之 plan 吃 impact 聯集、解析碑、判隔離失敗、修接續指紋。　檔案：`scripts/framepath_affected_gate.py`。既有 caller：FRAMEPATH b2／b3 之 gate。
- 改法：①plan 依 `impact.gate_feed` 三步（collect 前以碑之 `replaced_by` 取代並保留原組別、E0 碑記 `tombstoned` → 檔層聯集整檔執行 → collect 後逐一核對原 must nodeid 皆在）；②verdict：`caused` 失敗之 nodeid 若有未逾期 quarantine ⇒ 列入 `gate_report.quarantined_failures`，不擋 verdict；逾期 ⇒ 照擋；碑之取代列入 `gate_report.tombstone_resolutions`；③`inputs_digest` 之未追蹤內容排除本次 `--out` 目錄（前綴由參數導出）；`--out` 為 repo 根 ⇒ rc≠0；④`ENV_PREFIXES` 改讀 schema `ledger.env_prefixes`（單一來源）；⑤impact 依 `impact.gate_wiring` 於 plan 行程內呼叫，輸出存入 plan 收據，catalog 與 previously_failed 納入 inputs_digest。
- **驗證**：`pytest tests/feature_engineering/test_framepath_disposition.py -k "affected_gate"`（新增案例）：①manifest 之 A 組列已立碑 E1 nodeid、其 replacement 位於另一檔且原檔已刪 ⇒ plan 不拒跑、replacement 於 A 組、`tombstone_resolutions` 有該列；②有效隔離之 caused 失敗 ⇒ verdict pass 且 `quarantined_failures` 含該 nodeid；逾期 ⇒ verdict fail；③分段一後於 out 目錄新增 junit ⇒ 接續 digest 不變；新增非 out 之未追蹤原始碼 ⇒ digest 變；④以 `handoffs/run_receipts/framepath-b1-affected-plan.json` 重放 ⇒ 新計畫 nodeid 集合 ⊇ 原計畫 must nodeid 集合；⑤刪除某 must nodeid 而無碑 ⇒ collect 後核對 rc≠0；⑥有效隔離之 nodeid 出現與 evidence 不同之例外特徵、或同類型同訊息但失敗位置（exception_origin／fail_line）不同 ⇒ verdict fail（`gate_report.quarantine_match` 不成立）；⑥b quarantine.evidence 引用他 nodeid 之紀錄 ⇒ validate V12 紅；⑥c plan 收據之 testreg_impact 為空 object 或缺 selected ⇒ 閘 rc≠0 不寫收據；⑦plan 收據含 `plan_receipt_fields` 三欄且同輸入兩次 plan 之三欄位元相同；⑧只改 `scripts/testreg.py` 或 schema ⇒ inputs_digest 改變；分段一後 timing_dirs 之本次 --out 新增 junit ⇒ digest 不變；⑩gate_cmd 為 `venv/bin/python scripts/framepath_affected_gate.py --help`、含 `--plan`、`--out` 缺值、或 `--max-seconds` 重複 ⇒ 非 tombstone_aware；同一碑路徑出現於兩個 manifest、其一安全另一不安全 ⇒ V14 紅；閘以無引數裸呼叫時 plan 收據含 `tombstone_resolutions` 與 must 核對結果；同 manifest 路徑而 plan 收到之 manifest 物件內容不同 ⇒ inputs_digest 不同；⑪已全數立碑而刪除之測試檔不出現於 impact 之 selected／excluded 亦不致閘拒跑；⑨impact 回傳漏一個測試檔或同檔同時出現於 selected 與 excluded ⇒ 閘 rc≠0（`gate_report.impact_universe`）；變更一個非 tests/ 之生產檔 ⇒ changed_paths 含該檔。mutant：碑解析移到 collect 之後 ⇒ ①紅；不查 expires ⇒ ②逾期案紅；排除前綴改空 ⇒ ③紅；略過 collect 後核對 ⇒ ⑤紅。
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
- **驗證**：`testreg.py validate` rc=0；範圍內 `jq` 計「guarantee、oracle、claim 任一含 unclassified」之 entry 數 == 0（依 V16 之已分類判定）（收據附命令）；三家原始判定檔與裁決列皆在 synth。
- **邊界**：三家皆擬淘汰但無可得之證據等級 ⇒ `keep`，登 §N `needs-research`；某檔只部分函式擬淘汰 ⇒ 只列該些函式。
- **存活至**：票收案後保留。　**覆蓋風險**：Task 3.2 只增碑與 rewrite_receipt，不改分類欄。
- 不可做：不以「未執行過」「年代久」「慢」為擬淘汰理由。

**Task 3.2 — 執行（分子批，每子批 ≤20 個目標檔）**
- 目標：依 Task 3.1 執行 rewrite 與立碑刪除。　檔案：目標測試檔、`tests/registry/catalog.json`、收據 `handoffs/run_receipts/testreg-retire/<nodeid-slug>.json` 與 `testreg-rewrite/<slug>.json`。
- 改法：子批之閘一律為 `scripts/framepath_affected_gate.py`（tombstone_aware，V14 據此放行本票之立碑；本票 manifest 不列 Phase 3／4 之淘汰對象）。每子批：產生收據 → `validate` → 經 FRAMEPATH D10 執行器跑該子批之 impact 選中集合 → 子批造成之紅＝0 → 單一提交（可單獨 revert）。
- **驗證**：每子批 `testreg.py validate` rc=0（V07–V10）；執行器 verdict pass；子批提交訊息列子批編號與收據清單。
- **邊界**：收據驗不過 ⇒ 該 nodeid 退回 `keep` 並登 §N；執行中暫停 ⇒ 依 D10 分段續跑，不重來。
- **存活至**：票收案後保留。　**覆蓋風險**：無。
- 不可做：不跨子批合併提交；不改 FRAMEPATH manifest。

**Task 3.3 — 成效報告**
- 目標：「淘汰幾函式、幾檔、證據等級分布、以 summary 中位耗時計之每次全跑節省秒數（無紀錄列 unknown 不估）」。　檔案：`handoffs/run_receipts/testreg-phase3-effect.json`。
- **驗證**：`venv/bin/python scripts/testreg.py effect --recompute handoffs/run_receipts/testreg-phase3-effect.json` 由 catalog 碑與 summary 重算，逐數字 == 報告值則 rc=0；`testreg.py validate --require-executed` rc=0（V21：本 Phase 之 rewrite 皆已執行並附收據）。
- **邊界**：summary 無紀錄 ⇒ 節省秒數 unknown，不寫 0。
- **存活至**：票收案。　**覆蓋風險**：Task 4.3 產全庫版，不覆寫本檔。
- 不可做：不外插估算。

### Phase 4 — 其餘目錄分類、執行與收案（依賴：Phase 3）
**Task 4.1 — 其餘分類**
- 目標：Phase 3 未涵蓋之全部測試檔完成分類。改法同 Task 3.1；目錄順序依 `docs/manifests/*.json` 中 `affected_tests` 引用次數由高到低（機械計數，收據附）。
- **驗證**：`testreg.py validate` rc=0；全庫「三欄任一含 unclassified」之 entry 數 == 0。
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
- **驗證**：`testreg.py effect --recompute` rc=0；`testreg.py validate --require-executed` rc=0。
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
  - Q1（`timeout` 標記）：保留 9 處宣告並於 `pytest.ini` 註冊（Task 1.4）。理由：移除只在「未安裝外掛」之環境下行為恆等，於已安裝外掛之環境會喪失作者所設之逾時保護，非行為恆等；保留則兩種環境皆不改變現行行為。不安裝外掛（安裝會使該 9 處開始逾時失敗，屬引入新行為）。卡住偵測於閘級執行由 D10 監看承擔；一般手動 pytest 現無逾時保護，此為現況（未因本票變差）。
  - Q2（k 與複查閾值）：k＝20、`duration_regression_rule`（取樣、中位數、門檻皆封閉定義於 schema）。現無同設定多次執行之耗時資料可校準（b1 收據每項僅一次）；此訊號只標記不影響挑選，誤設之代價為複查清單噪音，不減驗證。
- **殘留**：
  - R1 動態覆蓋對照表（逐行覆蓋率→測試，原 `dynamic_hit`）— `為何現在不做: blocked-by:Task 1.3 記錄器上線後須另收覆蓋邊（ledger 無檔案觸及欄）`；觸發：summary 中 ≥80% 測試檔具 ≥3 筆同 env_class 紀錄；登記處：`白話說明/還沒做的事.md` 第四節。
  - R2 定期全套自動執行 — `為何現在不做: user-ruling:2026-08-13 使用者刪除全部 CI（.github/workflows/）`；觸發：使用者恢復 CI；登記處：同上。
  - R3 測試前提過期之自動偵測（斷言所守規則已被改寫）— `為何現在不做: needs-research:前提與規則之機械對應無既有業界做法`；觸發：研究得出可證偽判準；登記處：同上。
  - R4 名稱層級之陳舊（測試名與所測行為不符）— `為何現在不做: needs-research:無可機械判定之訊號`；觸發：同上；登記處：同上。
  - R5 E2 之 mutant 集合是否足以代表原測試所守性質 — `為何現在不做: needs-research:mutant 充分性無機械判準`；現由每子批審碼之委員判定；觸發：出現可機械產生充分 mutant 之工具；登記處：同上。
  - R6 刻意構造之不自然碼繞過（例：以動態字串組名之 setattr、經 importlib 間接寫入模組屬性後再刪、為通過規則而特製之測試碼）— `為何現在不做: user-ruling:2026-09-11 使用者裁定「與委員判定無法收斂／無限窮舉／落地成本太高就不鑽」，繞過成本 ≥ 合規成本者歸蓄意等價`；本票之機檢擋意外與自然寫法，蓄意構造由每子批審碼委員判；觸發：發現自然寫法（非為繞過而寫）落入此類；登記處：同上。
  - R7 斷言結構不變之語意弱化（例：改變 fixture 回傳資料或經計算得出之斷言輸入；直接寫在斷言、以單次賦值常數傳入、或經 helper 引數傳入之門檻值，以及 `a == b` 改 `a == a` 類名稱互換，已由 `assertion_nodes.normalize` 之常數摺疊、斷言內序號化與 `inline_rule` 引數代入擋下，不在本殘留內）— `為何現在不做: needs-research:測試語意等價不可機械判定（任意程式之行為等價為不可判定問題），可行之完整機械替代僅有「任何非純新增之測試修改皆須 mutation 收據」，其成本落在所有票之每次測試修改，須另研究成本與收益`；現行防線＝每批三家審碼逐條讀測試 diff（CLAUDE.md「diff 既有測試斷言防假綠」）；觸發：研究得出成本可接受之機械判準，或審碼抓到一次此類漏網；登記處：同上。
