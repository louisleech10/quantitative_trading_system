# FF-STAT TODO 審查 r28 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R28  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R28-BRIEF.md`  
標的：`git show ca1f9586`（盤點 92→390、`_ast_step_functions` 種子＋遞移閉包、`_inline_nan_filling_calls`／`test_mutation_dispatcher_inline_rolling_is_caught`、manifest 縮尾五入口）；唯讀；探針 `/tmp/ffstat-r28-work/`。

## COMPOSER-R28-P3-00

**斷言**: 本輪逐項核對 `ca1f9586` 對 r27 reconcile 部分採納之內聯檢查與盤點閉包後，未發現超出 manifest「實作前紅」之外、需阻擋 TODO 放行之新 P0／P1。

**碼證**: `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r28-work/inventory.json` → `INVENTORY_RC=0`（390 步、`unclassified: []`）；`pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py -k "inventory or class_bound or index_derived or dispatcher_inline or inventory_closure" -q` → 5 passed in 24.60s；`pytest …::test_mutation_dispatcher_inline_rolling_is_caught -q` → 1 passed；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → `MUTATION_STATIC_RC=0`；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；`PYTHONPATH=. venv/bin/python /tmp/ffstat-r28-work/probe_steps.py` → rc=0（真實 BTCUSDT 1h×300：polars `polars_l2_derived_momentum` 前 5 列 null、`first_finite=5`；`causal_preprocessing` 強制 True）。

**類別**: other

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#37264a8e234a; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#5e688567450c; docs/manifests/FFSTAT.json#29af82d8ad7c; handoffs/reconcile/20260926-ffstatauto-x-review-r27/synth.md#459083a99bc8

正文：`ca1f9586` 以 `_ast_step_functions`（`:359-379`）做公開函式＋前綴種子與 `_called_qualified` 遞移閉包，`test_inventory_closure_reaches_off_prefix_and_nested_steps`（`:335-346`）鎖 `_winsorize_2d_legacy_equivalent`、`_ts_argmax_2d`、`polars_l2_derived_momentum`、`transform_array_fast` 等漏列修補。r27 `CODEX-R27-P1-01` 之機械修法已落地：`_NO_INLINE_CLASSES`＋`_inline_nan_filling_calls`（`:191-230`）與 `test_mutation_dispatcher_inline_rolling_is_caught`（`:233-249`）——rolling 注入必紅、原樣 `to_numpy` 搬移與 reconcile 理由一致不列紅。盤點 class 計數與 brief assumed 一致（propagating 86、not_in_generation_path 37、incomplete_window 9、dispatcher 37）。manifest `risk_mitigation` 已列縮尾五入口（`:230`）。

---

## 必答

1. **(1a)** 本家 r27 僅 `COMPOSER-R27-P3-00`，經本輪對 `ca1f9586` 複核可閉合。**(1b)** inventory rc=0；五支 canonical 測綠；r27 codex 反例之重跑語意——inline rolling 版：`test_mutation_dispatcher_inline_rolling_is_caught` 鎖 `(close>0).astype` 與 `rolling(min_periods=1)` 命中／`to_numpy` 不命中，與 synth「部分採納、原樣複製 close 不列紅」一致；舊 provenance「合法 child + raw close DataFrame」仍不在 inline 集合內，屬 reconcile 已接受之殘差，非本輪新 blocker。

2. **(2a)** `ca1f9586` 未引入可重現之新 P0／P1；閉包與內聯檢查與收據／golden 同步。**(2b)** 否證：`test_mutation_dispatcher_inline_rolling_is_caught` 對 AST 注入 rolling 必 assert；clean target `test_nan_propagation_inventory_complete` 對 390 步分類全過。

3. **(3a)** brief assumed（298 步新增分類、propagating／not_in_generation_path／incomplete_window 語意）→ **成立**（收據與 `nan_propagation_classes.json` 對齊、unclassified 0；`feature_preprocessor.py:168-176` 強制 causal，`winsorize_array` 非因果分支在預設生成不可達）。**(3b)** 抽驗（`/tmp/ffstat-r28-work/probe_steps.py`）：propagating——`compute_cross` 首有限 0（輸入 finite）、`compute_ratio` 首有限 1（shift）、`polars_l2_derived_momentum` 首有限 5（lag=5）；not_in_generation_path——`OperatorRegistry.default_registry` 僅 `tests/momentum/feature_engineering/test_state_counters.py` 呼叫、生成路徑無引用；`transform_array_fast` rank 窗 20 首有限 24（pre-IC 關 rank 時不進預設 FF 生成，inventory 碼證 `feature_factory.py:2830-2835`）。

4. **(4a)** brief「我沒查」：**① 未命中**（operators 派發／helper 無 `transform_context[…]` 動態取函式；閉包以 `_called_qualified` 覆蓋模組 import／self 路徑，未發現可繞過 inventory 之實例）；**② 未命中**（`_NAN_FILLING` 含 `map_batches`／`convolve`／`lfilter`，FeatureEngineering 樹無 `nancumsum`／`scipy.signal` 命中；polars `map_batches` 在 `polars_l65_rank_transform` 步驟本體，屬 not_in_generation_path 非 dispatcher 內聯）；**③ 未命中**（pre-IC `_layer6_5_pre_ic` 關閉 rank／zscore／gaussian，收據對 polars L65 rank／zscore 與 numba `transform_array_fast` 均標 not_in_generation_path 並附同一碼證）。**(4b)** `test_ffstat_stable_start.py:191-230`；`feature_factory.py:2830-2835`；`polars_adapter.py:539`；`grep OperatorRegistry` 僅 `operator_registry.py`＋單測。

5. **(5a)** **`VERDICT: proceed`**（r27 阻擋項已由 `ca1f9586` 內聯＋390 步盤點收斂；TODO 可進實作，剩餘紅為 manifest 明示實作前狀態）。**(5b)** 無 P0／P1 blocker。

---

# Coverage risk

- 盤點＋五支 `-k inventory…` → ~25s（含 index_derived 真實切片）；mutation 靜態器秒級；`template_check.sh todofmt` 秒級；`probe_steps.py` ~3s。
- 未跑全設定 FF run、§G⑦ 雙起點、⑪ resume 18s 級探針（r27 已驗，本輪未重跑）。

ASSUMPTIONS_VERIFIED: 已讀 r28 brief、r27 synth、`ca1f9586` diff、manifest touches／risk_mitigation、inventory 收據；上述命令已實跑  
TESTS_RUN: 見 sentinel **碼證**；`git status --short -- momentum api scripts tests docs templates config` 與開跑前一致  
FAILURES_SEEN: probe 初版 API 誤用（DerivedOperatorEngine 缺 config、`transform_array_fast` 參數）僅修 `/tmp/ffstat-r28-work/probe_steps.py` 後 rc=0；`rm -rf /tmp/ffstat-r28-work` 被環境安全閘拒絕，未改寫指令繞過；`/tmp/claude-501` 未列入刪除  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r28-composer.md  

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R27-P3-00

STATUS: DONE
