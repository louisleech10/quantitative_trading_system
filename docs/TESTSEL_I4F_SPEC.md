# TESTSEL I4f 全規模層（fullscale marker）— SPEC

> 來源：大綱 `handoffs/20261116-testsel-route-outline.md` I4 拆分列 I4f；事實 `runs/testsel_route/i4f/i4f_facts.md`；前項 I4e 外掛慣例 `tests/fixtures/hardware_gate_plugin.py`（cffc22f9）　|　日期：2026-11-18　|　對應 TODO：`docs/manifests/TESTSEL_I4F.json`

## §RISK 風險分級
- **大小**：中（新增一個收集期外掛、conftest 註冊一行、`pytest.ini` 宣告一個 marker、12 個測試檔之 23 個函式加標記；不改產品碼、數值與任何斷言）。
- **命中高風險原則**：(b) 跨模組共用路徑——`tests/conftest.py` 註冊之外掛作用於全部 pytest 執行。
- RISK-HIT: b

## §A 假設與待使用者確認
- 已驗證事實：見 `runs/testsel_route/i4f/i4f_facts.md`（testmon 遇 `-m` 停用選取、被排除之改動測試仍待跑、d1f57180 全規模清單 23 條現存、既有手寫 slow 有現行消費者）。
- FACT-RECEIPT: `venv/lib/python3.9/site-packages/testmon/configure.py:74-75` → `if options["markexpr"]: return ["-m was used"]`（主委 實讀 2026-11-18）
- 設計決定（我的判斷）：①採 pytest 官方範例〈Control skipping of tests according to command line option〉寫法：測試函式上直接加 `@pytest.mark.fullscale`、`--run-fullscale` 開關、收集期處理；不另立登記表（施工中改：原登記表＋格式驗證屬自建機制，2026-11-18 原 session 轉述使用者「那外掛是垃圾嗎」後對照官方範例刪除）。②與官方範例唯一差異：不加 skip，改以標準 deselect 延後——testmon 會把 skip 當已跑並記下依賴，之後 `--run-fullscale` 不再選中；deselect 不被記錄（原型③）。③預設排除不用 `addopts -m`（帶 `-m` 使 testmon 停用選取）。④marker 用專用名 `fullscale` 不用 `slow`：手寫 `slow`（28 檔 49 處）為「模組內偏慢」語意，被 `scripts/heavy_commands.json:19-20` 重型守衛與 `docs/manifests/TESTSEL_I1A.json:56` gate_cmd 依賴。
- 審 r1／r2 處置之去向（登記表刪除後）：`test_malformed_table_usage_error`（登記表格式錯矩陣，含缺 `nodeid`／`small_scale_gap`、nodeid 無 `::`、類別存在而方法不存在等）隨登記表刪除而移除——標記直接寫在函式上，無表可錯；`test_registered_not_collected_no_effect` 更名為 `test_marked_not_collected_no_effect`；`test_pytest_ini_addopts_has_no_markexpr` 與 `pytest.ini` 之 `fullscale` 說明（`--run-fullscale` 操作提示）保留。
- 待確認：無
- 已確認結果：2026-11-18 使用者「好，I4你做了就有做了，繼續照你的方式做，能完成目標且不拖延就可以」

## §C 約束
- 不改產品碼（`momentum/`、`api/`）、不改任何測試之斷言與函式本體、不動手寫 `slow`。
- d1f57180 `tests/duration_budget_exempt.json` 之 23 條全規模測試，各於函式上直接加 `@pytest.mark.fullscale`，正上方一行註解寫該條 `small_scale_gap`（小規模姊妹未覆蓋者）。
- 外掛 `tests/fixtures/fullscale_layer_plugin.py` 只含：`pytest_addoption`（`--run-fullscale`）、`pytest_collection_modifyitems`（`wrapper=True`，`yield` 後＝晚於 `-k`／`-m`／testmon 等其他選取）、`pytest_terminal_summary`；marker 於 `pytest.ini` 宣告。
- 預設延後：無 `--run-fullscale` 時，帶 `fullscale` 之 item 自 items 移除並 `config.hook.pytest_deselected`；不 skip、不 xfail；終端摘要具名列出（檔、條數、提示加 `--run-fullscale`），屬「未驗」非「通過」。`--run-fullscale` ⇒ 不延後（可再加 `-m fullscale` 只跑全規模層；併用 testmon 時須 `--testmon-forceselect`）。
- `--collect-only` 不延後（nodeid 清單不隨分層而異，同 I4e）。
- 與硬體閘（I4e）共存：同一測試兩者皆命中時，被任一方排除一次、無錯誤。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I4F-BUDGET-1 | 無重型跑 | — | 暫存 repo 兩至三個小測試檔 | 單元層秒級（I4f 原型 6 次子行程共 3.13 秒，`runs/testsel_route/i4f/proto.log`） | 無 |
| TESTSEL-I4F-BUDGET-2 | 無重型跑（受影響回歸之快速層） | conftest 新註冊外掛後，會把 repo conftest／外掛載入暫存根之 16 個測試檔（I4e 施工時同類曾 INTERNALERROR）；其中 3 條單條重型（ledger 共 1089 秒）延至收案重型批 | 13 檔整檔＋3 檔之 20 條非重型 | 實跑 `315 passed, 1 skipped, 1 xfailed … in 597.05s`（`runs/testsel_route/i4f/same_run.log`） | I4e 同批 |

## §B 四項平衡實測
- N/A：不涉計算路徑與使用者操作；收集期每 item 一次 marker 查詢。

## §P Phase 與依賴

### Phase 1 — 全規模層（依賴：I4e 已提交 cffc22f9）
**Task 1.1 — 標記與收集期外掛**
- 目標：全規模測試以官方寫法帶 `fullscale`；預設層（無 `--run-fullscale`）具名延後、不執行；`--run-fullscale` 時照常執行。檔案：新建 `tests/fixtures/fullscale_layer_plugin.py`；`tests/conftest.py` 之 `pytest_plugins` 加一行；`pytest.ini` markers 加 `fullscale` 說明（預設延後、加 `--run-fullscale` 執行、預設層勿以 -m 篩、與 slow 不同概念）；12 個測試檔之 23 個函式加標記與註解。既有 caller：新建無 caller。
- **驗證**：`pytest tests/registry/test_fullscale_layer.py` 全綠，其中：`test_default_defers_marked_named`（無 `--run-fullscale` ⇒ 參數化 2 條 deselect、同檔未標記者照跑、摘要同一行含檔路徑與「延後 2 條」並提示 `--run-fullscale`）、`test_plugin_absent_runs_marked`（不載外掛 ⇒ 照跑）、`test_run_fullscale_runs_marked`、`test_marker_filter_with_run_fullscale`（`-m fullscale`／`-m "not fullscale"`）、`test_handwritten_slow_untouched`（`-m "not slow"`／`-m slow` 語意不變）、`test_marked_not_collected_no_effect`（只指定他檔或 `-k` ⇒ 無延後）、`test_collect_only_lists_all`、`test_testmon_coexist`（延後晚於 testmon；被延後之改動者之後仍被選中）、`test_hardware_and_fullscale_both_registered`、`test_conftest_registers_fullscale_plugin`、`test_pytest_ini_declares_fullscale`、`test_pytest_ini_addopts_has_no_markexpr`、`test_d1f57180_fullscale_list_all_marked`（d1f57180 清單 23 條於現行檔皆直接帶 `@pytest.mark.fullscale`，AST 查裝飾器）。
- **邊界**：參數化；登記檔未收集；`--collect-only`；testmon；與硬體閘重疊；同檔手寫 slow。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不以 skip 代替 deselect；不在 `pytest.ini` addopts 加 `-m`；不動既有手寫 `slow`；不另立登記表。

## §V 驗證策略與邊界測試目錄
- 單元：`tests/registry/test_fullscale_layer.py`（暫存 repo＋子行程 pytest）；整合：`test_conftest_registers_fullscale_plugin`、`test_pytest_ini_declares_fullscale`、`test_d1f57180_fullscale_list_all_marked`。
- mutation（施工時實跑改壞對照各一並記錄）：不載外掛 ⇒ `test_plugin_absent_runs_marked` 對照；延後移到 `yield` 前（先於 testmon）⇒ `test_testmon_coexist` 紅；改為 skip ⇒ `test_testmon_coexist` 紅；collect-only 亦延後 ⇒ `test_collect_only_lists_all` 紅；延後條件改看 `slow` ⇒ `test_handwritten_slow_untouched` 紅；拿掉任一檔之標記 ⇒ `test_d1f57180_fullscale_list_all_marked` 紅。
- 防假綠：不改既有斷言；I4e 之 `tests/registry/test_hardware_gate.py` 全綠。
- 邊界目錄：參數化／未收集／collect-only／testmon 共存／與硬體閘重疊／同檔手寫 slow／正式 addopts 無 `-m`。

## §R 回退
- 單一 commit；回退＝revert 該 commit。

## §N N/A 登記
- §G：N/A — 不改數值、特徵或 ML 路徑。
- §B 四項平衡：N/A — 見上。
- 殘留：E-1（blocked-by：原 session 測試耗時計畫）——`tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 之 11 條全規模測試，其 gap 文字本即寫未證實全寬有獨有路徑，小規模姊妹檔已有同本體正負控制（含 parallel）；存廢屬測試內容決定、非本項分層機制範圍，由原 session 逐條對映後定。本項只將 d1f57180 既有清單原樣遷為 marker，該 11 條預設延後、不增日常耗時。
