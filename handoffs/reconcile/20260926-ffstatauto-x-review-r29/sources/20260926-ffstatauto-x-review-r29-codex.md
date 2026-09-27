## CODEX-R29-P1-01

**斷言**: r28 的 AST 閉包、盤點收據與 golden 分類表 exact-set gate，仍可在三者同步刪除同一既有步驟時保持綠燈；因此 stable-start 盤點覆蓋可無聲縮小，TODO 可能在不完整盤點下放行。

**碼證**: `tests/feature_engineering/test_ffstat_stable_start.py:176-182` 先把 receipt rows 壓成 set，再只比較 `expected` 與 `golden`。隔離複本操作序列：移除 `_ast_step_functions()` 的 `_winsorize_2d_legacy_equivalent`、重產 receipt（390 steps）、從 `tests/_golden/ffstat/nan_propagation_classes.json` 刪除同一 key；`venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete -q` → `1 passed`、rc=0。相同 AST mutation 未同步刪 golden 時，該測試 → `FAILED`，指出 golden 缺少該 key；r28 原 mutation 單獨重跑亦使 inventory rc=0 但測試 rc=1。CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:182
MUTATION: isolated copy：刪除 `_ast_step_functions()` 回傳集合中的 `momentum.FeatureEngineering.preprocessing.feature_preprocessor:FeaturePreprocessor._winsorize_2d_legacy_equivalent`，重產 inventory receipt，並刪除 golden 同名步驟後重跑 `test_nan_propagation_inventory_complete`。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#0785e104efde; tests/_golden/ffstat/nan_propagation_classes.json#91481e1f1afe; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#9a209731e1c7; docs/manifests/FFSTAT.json#b8a89eeb15c8

本家 r28 條目核對：**(1a)** `CODEX-R28-P1-01` 與 `CODEX-R28-P2-02` 均已閉合。**(1b)** 目標 commit 基線在隔離複本中 `stable_start_receipts.py inventory` 為 rc=0、391 steps；`pytest ... -k "inventory or class_bound or index_derived or dispatcher_inline" -q` 為 5 passed、53 deselected、24.77s；直接呼叫 `_called_qualified` 已解析 `momentum.FeatureEngineering.timeframe.tf_aligner:TimeframeAligner._timeframe_seconds_keys`。

**(2a)** 修補後仍有新缺陷，即本 finding。**(2b)** 上述三方同步縮小的可重現序列使 inventory rc=0、盤點測試 rc=0、golden 僅剩 390 steps；這不是 r28 單邊 mutation，故 exact equality 無法偵測。

**修法**：將 391-step inventory 的「預期全集」改由一份獨立、版本化且機讀的 frozen contract（含完整步驟清單或其逐位元組 digest）承載；AST 閉包、receipt、golden 都只作為被驗證的衍生輸出，不能再共同縮小後互相證成。現有 manifest 的 391 仍在 `honest_bounds` 散文字串中，未形成此獨立機器斷言。可行性證據：同一隔離複本同步縮小後 `jq '.steps | length'` 為 390；對固定基準 391 執行的 count guard rc=1，能拒絕本次 mutation。影響限於盤點契約與實作放行判定，未改數值計算或輸出 schema。

**(3a)** assumed 的類別／模組判定在本輪實際 import 形狀下成立，但不是對未來同名 module/class 的一般保證。**(3b)** `from ... import TimeframeAligner` 的實際解析與閉包測試均通過；`from ... import _worldquant_numba as _wq_nb` 之 module file 亦依 `src.imported.py` 規則可解析。選定 5 測試全通過，未觀察到誤分類。

**(4a)** 未查項①有命中：三方同步刪除時測試仍綠。未查項②在本版實際生成來源沒有命中。**(4b)** `tests/feature_engineering/test_ffstat_stable_start.py:266-278` 的 `_import_map` 只收 `ast.ImportFrom`；但對所有本輪 audited source roots 做 AST 掃描，`ast.Import` 目標以 `momentum.FeatureEngineering` 開頭者為 `0`，所以沒有現存 `import pkg.mod as m; m.f()` 生成步驟被本輪漏列。此形狀仍是未覆蓋邊界，不另列實質 finding。

**(5a)** 本版 TODO 不可放行實作。**(5b)** 唯一阻擋項為 `CODEX-R29-P1-01`；r28 的兩條本家 finding 已閉合，import-as 未命中現存生成路徑。

VERDICT: blocked
BLOCKED-BY: CODEX-R29-P1-01
CLOSED: CODEX-R28-P1-01,CODEX-R28-P2-02
