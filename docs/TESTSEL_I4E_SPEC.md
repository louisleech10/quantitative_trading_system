# TESTSEL I4e 硬體閘 — SPEC

> 來源：大綱 `handoffs/20261116-testsel-route-outline.md` I4 拆分列 I4e（拆分審 r1／r2 已確認：`handoffs/reconcile/20261118-testseli4split-x-review-r2/synth.md`）；事實 `runs/testsel_route/i4e/i4e_facts.md`；設計輸入 `runs/testsel_route/i4/i4_design.md` §13、`handoffs/reconcile/20261118-testseli4-x-review-r5/synth.md`（選取器報告 `hardware_blocked` 欄歸 I4a 一條）　|　日期：2026-11-18　|　對應 TODO：`docs/manifests/TESTSEL_I4E.json`

## §RISK 風險分級
- **大小**：中（恢復一個既有共用模組、新增一個收集期外掛、conftest 註冊一行、framepath 閘改回委派；不改產品碼與數值）。
- **命中高風險原則**：(b) 跨模組共用路徑——`tests/conftest.py` 註冊之外掛作用於全部 pytest 執行。
- RISK-HIT: b

## §A 假設與待使用者確認
- 已驗證事實：見 `runs/testsel_route/i4e/i4e_facts.md` 七條 FACT-RECEIPT（d1f57180 唯一實作、main 缺模組與收集期排除、8 GiB SIGKILL 實證、舊排除語意與驗收用例）。
- FACT-RECEIPT: `sysctl -n hw.memsize` → 印出 8 GiB 等值位元組（主委 實跑 2026-11-18）
- 待確認：無
- 已確認結果：2026-11-18 使用者「好，I4你做了就有做了，繼續照你的方式做，能完成目標且不拖延就可以」

## §C 約束
- 不改產品碼（`momentum/`、`api/`）、不改任何既有測試之斷言；登記表 `tests/hardware_requirements.json` 格式與內容不變。
- 登記表讀取與記憶體判斷只有一份實作（`scripts/hardware_requirements.py`，大綱共用介面④）；`scripts/framepath_affected_gate.py` 委派之，不留複本。
- 排除＝pytest 標準 deselect（`config.hook.pytest_deselected`），不 skip、不 xfail；被排除者於終端具名列出，視為「未驗」非「通過」（大綱共用介面⑤）。
- `--collect-only`（只收集不執行）不排除：nodeid 清單（golden inventory、framepath 閘 nodeid 表、ledger 估時等以 collect-only 產生者）不隨本機記憶體而異；登記表仍於 `pytest_configure` 驗格式（施工發現：初版 collect-only 亦排除，`tests/feature_engineering/test_framepath_disposition.py::test_mutation_d11_7_inventory_hand_edit_is_red` 實跑轉紅——inventory 重生 collect 登記檔得 rc=5）。
- 本機記憶體足夠者照常收集執行（判定為嚴格小於：本機 < 需求才排除）；登記表不存在或 entries 為空 ⇒ 不排除（偏多跑）；登記表格式錯 ⇒ 共用模組拋 `HardwareTableError`，外掛於 `pytest_configure` 轉為 `pytest.UsageError`（訊息以「硬體閘」起首並含登記表路徑；pytest 結束碼 4，`_pytest/config/__init__.py:109` USAGE_ERROR）。
- 測試注入錨點契約：`machine_memory_bytes()` 本體保留為單行 `return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))`；驗收測試以改寫暫存副本之此行注入記憶體（生產碼不加測試旗標）；此行若改寫，驗收以具名訊息失敗、須同步錨點。
- 選取器報告欄 `hardware_blocked` 由 I4a 骨架落地後讀同一模組接上，不在本項。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I4E-BUDGET-1 | 無重型跑 | — | 暫存 repo 兩至三個測試檔 | 單元層秒級（子行程 pytest，每例 < 5 秒，依 d1f57180 `tests/registry/test_testsel_ops.py` 硬體用例同型） | 無 |

## §B 四項平衡實測
- N/A：不涉計算路徑與使用者操作；收集期每 item 一次字串比對。

## §P Phase 與依賴

### Phase 1 — 硬體閘（依賴：無）
**Task 1.1 — 恢復共用模組**
- 目標：`scripts/hardware_requirements.py` 為登記表讀取與本機記憶體判斷之唯一實作。檔案：`load_hardware_requirements(repo)`、`machine_memory_bytes()`、`hardware_blocked(entries, memory_bytes)`、`HardwareTableError`。既有 caller：`scripts/framepath_affected_gate.py:538-579`、`:1935`。
- 改法：以 `git show d1f57180:scripts/hardware_requirements.py` 為準恢復（檔頭呼叫端改為 framepath 閘與 `tests/fixtures/hardware_gate_plugin.py`）；framepath 閘之三函式改為委派（同 d1f57180 版第 540–575 行寫法），`GateError` 包裝 `HardwareTableError`。
- **驗證**：`pytest tests/feature_engineering/test_framepath_disposition.py -k hardware` 全綠；`tests/registry/test_hardware_gate.py::test_framepath_delegates_single_impl` 通過（framepath 閘之 `hardware_blocked`／`load_hardware_requirements` 結果與共用模組於 8／24／64 GiB 逐值相等，且 framepath 檔內無 `os.sysconf` 記憶體讀取）；`test_table_validation_rejects`（重複路徑／路徑不存在／需求非正整數 ⇒ `HardwareTableError`）。
- **邊界**：登記表不存在 ⇒ 空清單；條目格式錯（路徑不存在、ticket 非 RM-FULLSCALE、需求非正整數、重複路徑）⇒ `HardwareTableError`。
- **存活至**：I4 全部子項完成後仍保留（I4a 選取器報告讀同一模組）。
- **覆蓋風險**：無。
- 不可做：不另寫第二份讀表或記憶體判斷。

**Task 1.2 — 收集期具名排除外掛**
- 目標：所有 pytest 執行中，本機記憶體低於登記之 `min_memory_gib` 之檔，其全部測試於收集後被 deselect 並具名列出。檔案：新建 `tests/fixtures/hardware_gate_plugin.py`（`pytest_collection_modifyitems` 以 `@pytest.hookimpl(wrapper=True)` 於 `yield` 後排除＝晚於 `-k`／`-m`／testmon 等其他選取，同 d1f57180 舊外掛 hookwrapper 語意；審 r2 實測 trylast 先於 testmon 執行、會把 testmon 本即不選之登記檔算入摘要，見 `runs/testsel_route/i4e/i4e_facts.md` 審 r2 後補測；`pytest_terminal_summary`）；`tests/conftest.py` 之 `pytest_plugins` 加一行。既有 caller：新建無 caller。
- 改法：比對鍵＝測試檔（`item.path`）相對外掛所屬 repo 根之 POSIX 路徑等於登記 path（不用 nodeid：nodeid 相對 rootdir，`--rootdir tests` 等合法用法下會與登記表之 repo 相對鍵不同而漏排；repo 外之檔不視為登記檔）；命中者自 items 移除並呼叫 `config.hook.pytest_deselected`；終端摘要每檔一行：路徑、ticket、item、min_memory_gib、本機 GiB、被排除條數。
- **驗證**：`pytest tests/registry/test_hardware_gate.py` 全綠，其中：`test_enough_memory_not_excluded`（32 GiB ⇒ 登記檔 2 條皆執行）、`test_equal_memory_not_excluded`（24 GiB ⇒ 不排除）、`test_insufficient_memory_excluded_named`（8 GiB ⇒ `2 deselected`、摘要同一行含路徑／ticket／item／24／8.0／「排除 2 條」、登記檔未執行、未登記檔照跑）、`test_mutation_plugin_absent_runs_blocked`（改壞對照：不載外掛 ⇒ 登記檔照跑）、`test_registered_file_not_collected_no_summary`（只指定 small 檔或 `-k test_s` ⇒ 無摘要）、`test_parametrized_nodeid_excluded_by_file`（`3 deselected`）、`test_missing_table_excludes_nothing`、`test_empty_table_excludes_nothing`、`test_malformed_table_fails_collection`（rc=4、含 `ERROR: 硬體閘`〔pytest UsageError 之輸出前綴，審 r2 實測〕與登記表路徑、無 INTERNALERROR）、`test_testmon_coexist_excludes_only_would_run`（暫存 repo 32 GiB `--testmon` 記錄後改動登記檔與未登記檔、8 GiB 再跑 ⇒ 只未登記改動檔執行、`4 deselected`、摘要只列改動之登記檔「排除 2 條」不列 testmon 本即不選之穩定登記檔；再 32 GiB ⇒ 被硬體排除之登記檔仍被 testmon 選中執行）、`test_conftest_registers_hardware_gate_plugin`（正式 conftest 之 `pytest_plugins` 含本外掛；漏註冊即紅）、`test_collect_only_not_excluded`（8 GiB `--collect-only` ⇒ 登記檔 nodeid 照列、無 deselect、無摘要）、`test_real_repo_collect_lists_all_and_run_applies_gate`（原名 `test_real_repo_collect_applies_gate`〔審 r1 處置〕，施工發現 collect-only 不應排除後改名改寫；真實 repo 正式外掛鏈對一個登記檔：`--collect-only` rc=0 不排除；本機不足時 `--setup-plan`〔收集＋排除、不執行任何測試或 fixture〕⇒ rc=5、全 deselect 且具名列出；與既有外掛及收集鏈共存之整合驗證，不跑重型測試）。
- **定位**：共用模組與登記表取自外掛所屬 repo（外掛檔位置上兩層），不取 `config.rootpath`——有測試以暫存目錄為 rootdir、經 `-p tests.conftest` 載入本 repo 外掛（施工發現：初版取 rootpath ⇒ `tests/hermetic/test_prod_writers_tmp_root.py` INTERNALERROR）；驗收 `test_foreign_rootdir_uses_plugin_repo`（他處 rootdir、`-p` 載入外掛 ⇒ 無 INTERNALERROR；該處之檔在 repo 外，即使相對路徑與登記檔同名亦非登記檔、照常執行）。
- **邊界**：登記檔未被收集（`-k` 過濾或指定其他檔）或被其他選取（testmon）排除 ⇒ 不報錯、摘要只列硬體閘實際排除者；testmon 執行須保留 cacheprovider（停用即 testmon INTERNALERROR，與本外掛無關，審 r2 實測）；參數化 nodeid（`file::test[x]`）以檔案部分比對亦排除。
- **存活至**：永久。
- **覆蓋風險**：無（I4f 全規模層另以 marker 處理，共用同一掛載點但不改本外掛之排除語意）。
- 不可做：不以 skip 代替 deselect；不為測試注入記憶體而在生產碼加環境變數或 CLI 旗標（測試於暫存 repo 改寫模組副本之 `machine_memory_bytes`，同 d1f57180 用例）。

## §V 驗證策略與邊界測試目錄
- 單元：`tests/registry/test_hardware_gate.py`（暫存 repo＋子行程 pytest；記憶體以暫存副本改寫注入）；回歸：`tests/feature_engineering/test_framepath_disposition.py -k hardware`。
- mutation：`test_mutation_plugin_absent_runs_blocked`（拿掉外掛 ⇒ 登記檔照跑）；施工時實跑改壞對照各一並記錄：比對鍵改為整個 nodeid ⇒ `test_parametrized_nodeid_excluded_by_file` 紅；`<` 改 `<=` ⇒ `test_equal_memory_not_excluded` 紅；正式 conftest 移除註冊 ⇒ `test_conftest_registers_hardware_gate_plugin`、`test_real_repo_collect_lists_all_and_run_applies_gate` 紅；外掛不轉 UsageError（如改 `pytest.exit(..., returncode=4)` 或直接拋 `HardwareTableError`）⇒ `test_malformed_table_fails_collection` 紅；外掛改 trylast（先於 testmon）⇒ `test_testmon_coexist_excludes_only_would_run` 紅；collect-only 亦排除 ⇒ `test_collect_only_not_excluded`、`test_real_repo_collect_lists_all_and_run_applies_gate` 紅；改取 `config.rootpath` ⇒ `test_foreign_rootdir_uses_plugin_repo` 紅；比對鍵改回 nodeid 檔案部分 ⇒ `test_rootdir_variants_still_exclude`（`--rootdir tests`／repo 父目錄）紅。
- 改壞對照實跑收據（2026-11-18 施工）：`runs/testsel_route/i4e/i4e_facts.md`「施工改壞對照」節（M1–M7 各一，皆轉紅；還原後 19 passed）。
- 防假綠：不改既有斷言；`test_framepath_disposition.py::test_mutation_affected_gate_d14_hardware_blocked` 原斷言不動。
- 邊界目錄：空登記表／不存在／格式錯／參數化 nodeid／登記檔未收集／testmon 共存／他處 rootdir／collect-only。

## §R 回退
- 單一 commit；回退＝revert 該 commit（外掛移出 conftest 即恢復現況）。

## §N N/A 登記
- §G：N/A — 不改數值、特徵或 ML 路徑。
- §B 四項平衡：N/A — 見上。
- 殘留：無。
