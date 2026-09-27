# Reconcile — 20260926-ffstatauto-x-review-r27

**來源** 20260926-ffstatauto-x-review-r27-codex.md, 20260926-ffstatauto-x-review-r27-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/manifests/FFSTAT.json

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 派發函式之輸出來源未證：r26已把dispatcher的呼叫解析 | P1 | CODEX-R27-P1-01 | 部分採納（採納其核心：派發類不得在函式體內自行產生未穩定值。修法改為機械內聯檢查而非資料流追蹤——宣稱不自產未穩定值之類別〔dispatcher、helper、column_filter〕函式體不得有 rolling、ewm、fillna、ffill、cumsum、where、clip、shift、比較式 astype 等「NaN／未滿窗→有限值」運算，具名豁免 4 步附理由，mutant test_mutation_dispatcher_inline_rolling_is_caught 以真實 compute_all 注入 min_periods=1 之 rolling 必紅。不採納其反例之判定：原樣複製原始 close 之欄無暖機、首個有限值即穩定，不違反遮罩語意，故不列為紅。主委查證時另抓盤點漏列並一併修：polars_adapter 與 L6.5 公開入口／_transform* 未入列、名稱不合前綴者〔_winsorize_2d_legacy_equivalent〕與模組層 if 區塊內之 numba 核心〔_ts_argmax_2d〕漏列 ⇒ 盤點改為公開函式＋前綴種子之呼叫鏈遞移閉包，92 步增為 390 步全數分類附碼證；縮尾五個實作入口列入 risk_mitigation，touches 加 polars_adapter.py 與 _numba_transforms.py） | code-contract |
| 零 finding：本輪逐項核對`22908436`之限定名 | P3 | COMPOSER-R27-P3-00 | 採納（composer 判 proceed，閉合 r26 條目） | other |

Verdict: 需修補後合併

主委補述：codex 必答 (3a) 指出 brief 寫 dispatcher 9 而實為 8，屬 brief 筆誤；本輪閉包後 dispatcher 為 37。codex 回報其 /tmp 暫存三目錄清理被環境拒絕，列入收尾清理清單。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R27-P1-01

**斷言**: r26 已把 dispatcher 的呼叫解析改為限定名，但目前 gate 仍只要求 `called & (set(steps) - {name})` 非空；它沒有證明每條 public return path 的非空輸出都來自已分類 child。故 dispatcher 可以先呼叫一個合法 child，再直接以 `raw_data` 建出 public DataFrame 而仍綠燈，TODO 不能放行。

**碼證**: clean archive 的 `stable_start_receipts.py inventory` → `INVENTORY_RC=0`；clean target 的 `test_nan_propagation_inventory_complete`、`test_dispatcher_call_resolution_is_class_bound`、`test_index_derived_step_has_no_warmup` → `3 passed in 0.41s`。隔離複本把 `DerivedOperatorEngine.compute_all` 改成先呼叫 `self.compute_cross(...)`、再回傳 raw-data-derived `injected` 欄後，上述前兩支測試仍 → `2 passed in 0.40s`；同複本 real `BTCUSDT/1h` 300-row slice 輸出 `shape=[300,1]`、`columns=["injected"]`、首列值等於 `close`。目前 gate 的直接 AST feasibility probe 對該 mutation 找到 `direct_raw_data_return_lines=[69]`、`mutation_rejected=true`、rc=0。
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:190
CODE-ANCHOR: momentum/FeatureEngineering/operators/derived_operators.py:62
MUTATION: 在隔離複本將 DerivedOperatorEngine.compute_all 改為先呼叫 self.compute_cross(layer1_df.iloc[:, 0], layer1_df.iloc[:, 0], "mutation")，再回傳 pd.DataFrame({"injected": raw_data["close"].to_numpy()}, index=layer1_df.index)；執行 inventory 與 class-bound tests，並以 real 1h 300-row slice 驗證 injected 欄。

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#ea03890afd0c; momentum/FeatureEngineering/operators/derived_operators.py#a2dfc9fcfb88; momentum/FeatureEngineering/feature_factory.py#47f362f67de2; momentum/FeatureEngineering/run_locks.py#51e3f55c9a9a; docs/manifests/FFSTAT.json#7a5aad7addf4; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#5e688567450c; handoffs/reconcile/20260926-ffstatauto-x-review-r26/synth.md#d2d74a744271; handoffs/20260926-FFSTATAUTO-X-REVIEW-R27-BRIEF.md#f5425a402dc3

**類別**: code-contract

修法與可行性證據：把目前的 existential call check 改為 dispatcher return-path provenance/data-flow check。AST/data-flow model 應將限定名 child call 的回傳值標成已分類 provenance，追蹤 local、list append／concat 及 pandas／Polars 組合至每個 return；非空 public DataFrame／Series／column 若直接取自 `raw_data`、未分類 call 或未取得已分類 provenance，則拒絕。保留空結果只含 index 的合法分支，並新增本 finding 的「合法 child call + raw-data injected frame」mutation regression。隔離複本的 AST probe 已對實際 mutation 唯一命中 `return` 第 69 行，證明該修法所需的禁止構造可被機械辨識；clean target 的三支 canonical tests 與 real dispatcher output 均仍通過／產出，未要求改變 production schema。

# 必答

1. **(1a)** 本家 r26 的 `CODEX-R26-P1-01` 已閉合。**(1b)** 原反例在 mutation archive 重新執行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete -q --tb=short` → assertion fail、`MUTATED_INVENTORY_RC=1`；同複本 real `test_derived_operators_distance_cross_ratio_momentum_binary` → `AttributeError: 'DerivedOperatorEngine' object has no attribute '_compute_low_cardinality_cols'`、`MUTATED_DISPATCH_RC=1`。clean target 的限定名／index-derived／inventory 三測 → `3 passed in 0.41s`，所以 r26 的跨 class short-name defect 已被實際修補收斂。

2. **(2a)** 有新 P1：限定名修補解決了 r26 的解析錯綁，但沒有把「呼叫 child」提升成「public output provenance」契約。**(2b)** provenance mutation 的操作序列是：在隔離複本修改 `compute_all`，先呼叫已列入 inventory 的 `self.compute_cross`，再用 real `raw_data["close"]` 建立 `injected` DataFrame；`test_nan_propagation_inventory_complete` 與 `test_dispatcher_call_resolution_is_class_bound` → `2 passed in 0.40s`，real slice probe → `{"shape":[300,1],"columns":["injected"],"first_value_matches_close":true}`。這是 gate 綠燈與 public 輸出繞過分類 child 同時存在的可重現反例。

3. **(3a)** helper（15）與 column_filter（2）的抽樣支持 brief assumption「不產生公開特徵值」；dispatcher assumption 不成立為可驗收契約，因上述 provenance mutation 可繞過。現存 inventory／AST 實際 dispatcher 計數為 8，brief 文字為 9；未把未證明的第 9 筆臆列成額外 finding。**(3b)** real `BTCUSDT/1h` 300-row HDF5 slice 的 propagating 抽驗：`compute_cross` shape `[300]` first finite `39`、`compute_ratio` `[300]`/`39`、`compute_momentum` `[300]`/`17`、`compute_beta` `[300]`/`60`、rolling mean `[300,1]`/`4`。對應 `not_in_generation_path` 抽驗 4 步：`_aligned` 回傳 `None` 且 index match、`_rolling_count` shape `[300]` first finite `5`、`_rolling_zscore_2d` `[300,2]`、`_rolling_rank_2d_v2` `[300,2]`。helper 抽驗的 schema/data fingerprint 長度均 `32` 且 data fingerprint `weak=false`、alignment tuple 為 `[3600000000000,3600000000000,"open_time"]`；兩個 column filter 均為 `[300,2]`、欄為 `close/volume`、`values_preserved=true`；index-derived 為 `[300,4]` 且 row 0 全 finite；clean dispatcher outputs 為 derived `[300,111]`、rolling `[300,1]`。

4. **(4a)** brief「我沒查」① 未命中：single-TF real resume acceptance 在第一次生成後 `work_dir_exists=true`、`manifest_count=1`、`l7_manifest_count=1`；強制 `_try_load_cache` miss 的第二次 run `resume_calls` 命中、`second_result=true`、`same_config_hash=true`，`1 passed in 18.69s`。② 未命中：lease probe 輸出 `path_name=BTCUSDT_1h_<64-hex>.lock`、`hash_in_path=true`、`str_includes_hash=false`、`active_before_release=true`，finally release 後 inactive。③ 命中新 P1（不是 r26 舊 short-name defect）：限定名 class-bound test 會綠，但 provenance mutation 仍綠且產生 injected public column。**(4b)** ① 碼證為 `feature_factory.py:392-406` 的 cache miss 後進入 `_prepare_cgsa_registry`，以及 `feature_factory.py:1154-1198` 的 `manifest_path.exists() and not force_fresh`／L7 manifest gate／`resume_from_manifest`；② 碼證為 `run_locks.py:41` 將完整 config hash 放入 lock filename；③ 碼證為 `test_ffstat_stable_start.py:190` 的 existential intersection 與 `derived_operators.py:62` 的 dispatcher return surface。

5. **(5a)** **`VERDICT: blocked`**；本版 TODO 尚不可進實作。**(5b)** 唯一 P0/P1 blocker 為 `CODEX-R27-P1-01`。

# Coverage risk

- routine checks：inventory rc=0、`mutation_probe_static.py` rc=0、`template_check.sh todofmt` PASS、collect-only `56 tests collected`；canonical 三測 `3 passed in 0.41s`，均在隔離 archive 複本／real data slice 之外不改 source tree。
- acceptance／real-slice：resume single-TF probe `1 passed in 18.69s`；real operator／dispatcher／helper／filter／not-in-generation probes 使用 HDF5 真實 1h×300 切片。未跑全設定 FF run、§G⑦ 雙起點全設定測試。
- 覆核差異：dispatcher receipt/class count 實際為 8、brief 為 9；本輪只記為 coverage observation，未把未證明的第 9 筆當成 finding。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、r27 brief、r26 reconcile；clean target inventory、static mutation、template、collect-only、canonical tests 與 real 1h slice 均按上述命令實跑；r26 original mutation 已紅；provenance mutation 已重現 gate false-pass；resume／lease ①② 均有 real probe evidence。
TESTS_RUN: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r27-review/inventory.json` → `INVENTORY_RC=0`; `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → `MUTATION_STATIC_RC=0`; `bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → `TODOFMT PASS`; `... pytest ... test_nan_propagation_inventory_complete test_dispatcher_call_resolution_is_class_bound test_index_derived_step_has_no_warmup -q --tb=short` → `3 passed in 0.41s`; original r26 mutation → `MUTATED_INVENTORY_RC=1` and `MUTATED_DISPATCH_RC=1`; provenance mutation → `PROVENANCE_INVENTORY_RC=0`, class-bound `2 passed in 0.40s`; provenance guard → `PROVENANCE_GUARD_RC=0`; resume → `RESUME_SMALL_RC=0`; lease／real-slice probes → outputs above.
FAILURES_SEEN: 初次 temp `probe_r27.py` 因 Python 3.9 未加 future annotations 而在 type hint 產生 `TypeError`；只修正 `/tmp` probe 後重跑 rc=0，未改 repository。收尾清理命令 `rm -rf -- /tmp/ffstat-r27-review /tmp/ffstat-r27-mutation /tmp/ffstat-r27-provenance /tmp/ffstat-r27-probe.log /tmp/ffstat-r27-resume-small.log` 被環境安全閘拒絕，未改寫指令繞過；三個 workdir 仍在，`/tmp/claude-501` 確認保留。
SCOPE_CHANGES: none；未修改 momentum、api、scripts、tests、docs、templates、config、SPEC、manifest、data_cache 或 git history；只寫本指定 family 產出與 append-only 狀態交接。
NUMERIC_OR_SCHEMA_IMPACT: none；production 數值、schema、cache 與輸出大小未改；`injected` 僅存在於隔離 mutation probe。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r27-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R27.md
TMP_CLEANUP: cleanup was attempted with the exact explicit targets above and rejected by the environment safety gate; `/tmp/claude-501` was not targeted and remains present.

VERDICT: blocked
BLOCKED-BY: CODEX-R27-P1-01
CLOSED: CODEX-R26-P1-01
STATUS: DONE
## COMPOSER-R27-P3-00

**斷言**: 本輪逐項核對 `22908436` 之限定名派發修補與 r26 reconcile 採納項後，未發現超出 manifest「實作前紅」之外、需阻擋 TODO 放行之新 P0／P1。

**碼證**: `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r27-work/inventory.json` → rc=0；`pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete tests/feature_engineering/test_ffstat_stable_start.py::test_index_derived_step_has_no_warmup tests/feature_engineering/test_ffstat_stable_start.py::test_dispatcher_call_resolution_is_class_bound -q` → 3 passed in 0.45s；`pytest --collect-only -q tests/feature_engineering/test_ffstat_stable_start.py` → 56 collected；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → rc=0；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；隔離複本（git archive 至 `/tmp/ffstat-r27-mut`）將 `DerivedOperatorEngine.compute_all` 改為 `return self._compute_low_cardinality_cols(layer1_df, [])` 後 inventory test → `1 failed`（`AssertionError` on `DerivedOperatorEngine.compute_all`），clean target 同測仍綠；`venv/bin/python /tmp/ffstat-r27-work/probe_steps.py` → propagating／index_derived／column_filter／dispatcher 抽驗行 rc=0。

**類別**: other

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#ea03890afd0c; docs/manifests/FFSTAT.json#7a5aad7addf4; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#5e688567450c; handoffs/reconcile/20260926-ffstatauto-x-review-r26/synth.md

正文：`22908436` 以 `_called_qualified`（`tests/feature_engineering/test_ffstat_stable_start.py:193-214`）取代短名集合，dispatcher gate 改為 `called & (set(steps) - {name})`（`:186-190`）；新增 `test_dispatcher_call_resolution_is_class_bound`（`:217-225`）鎖 L2／L3 同名 `_rolling_last_rank_pct` 不跨類。manifest Task 2.3 條已登記該具名測試。r26 `CODEX-R26-P1-01` 之 mutation 反例現可被 inventory 拒絕，與 reconcile 採納修法一致。

---

