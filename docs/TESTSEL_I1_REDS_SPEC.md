# TESTSEL I1 紅清單、隔離根確認與真紅修 — SPEC

> 來源大綱：`handoffs/20261116-testsel-route-outline.md`（I1；確認輪 `handoffs/reconcile/20261116-testsel-x-consult-r5/synth.md`）　|　日期：2026-11-17　|　對應 TODO：`docs/manifests/TESTSEL_I1.json`（本 SPEC 定稿後生成）　|　原型產出：`runs/testsel_route/i1_proto/red_classified.md`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（改 tests/conftest.py 共用隔離介面、多模組測試；涉 NUMVIEW 收據與 L2 數值量測；清理正式資料）。
- **命中高風險原則**：(a) 測試寫入正式資料根（`data_cache/kline_cache.h5` ETHUSDT/1h 整組為測試下載之不連續 K 線；`data_cache/patterns` 370 檔全為測試假型態）、L2 兩臂 4h 數值未驗；(b) tests/conftest.py 為全部測試共用；(d) 量化測試之紅含釘值／收據，處置錯誤會掩蓋數值錯。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- FACT-RECEIPT: `venv/bin/python -m pytest … $(unreg_args.txt)`（i7b-probe，d1f57180）→ 印出 `157 failed, 96 passed, 4169 warnings in 1613.37s`（主委 實跑 2026-11-17；log `runs/testsel_route/i1_proto/rerun_unreg.log`）
- FACT-RECEIPT: `bash runs/testsel_route/i1_proto/run_in_tree.sh .claude/worktrees/main-probe quant_reds.txt`（9f059c65）→ 68 條中 63 條同紅、5 條通過（主委 實跑 2026-11-17；`main_quant.log`、`c_class.txt`）
- FACT-RECEIPT: `jq -r '.[].node' tests/_golden/prered/allowed_red.json`（main-probe）與 `c_class.txt` 交集 → `0`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `run_in_tree_freshcache.sh i7b-probe f32only.txt <新快取根>` → 印出 `1 passed … in 565.26s`；命中舊快取時 `2 failed in 3.43s`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `cmp_nv_obs.py <舊 pkl> <新 pkl>` → `old compute_all_polars_calls= 8 arms_tf= ['1h', '4h']`、`new … 7 arms_tf= ['1h']`、1h `returned`／`category` 共同欄 536 不等格 0（主委 實跑 2026-11-17）
- FACT-RECEIPT: `remaining_ids.py <整合樹> i7e_deselect.txt` → `selected=2026 remaining=103 deselect_not_done=3`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `inspect_kline_h5.py data_cache/kline_cache.h5` → `ETHUSDT/1h n=1762 first=2024-05-20 20:00:00 last=2025-10-27 12:00:00 gaps=2 dup=0 max_gap_bars=5589`；其餘 4 組 12h `gaps=0`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `data_cache/patterns/PAT_*.json` 規則含 `f0` 者 → `test-signature=367 total=370`；其餘 3 檔名 `a`／`b`／`c`、case `cx`、規則欄 `f`（主委 實跑 2026-11-17）
- 待確認：無
- 已確認結果：2026-11-17 使用者「data_cache你可以刪除，然後用現在專案有的程式經過幣安API再抓需要的真實資料」（Task 1.6）。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條；不弱化 NaN/inf gate；不放寬既有斷言換綠（§V 防假綠）。
- 紅之處置只有兩種終態：修後通過；或登記 `tests/_golden/prered/allowed_red.json`（owner＋`為何現在不做: blocked-by:…|user-ruling:…`，SPEC_TEMPLATE 殘留規則）。不得 skip／xfail 規避。
- 釘值、收據、golden 之改動屬資料正確性範圍 ⇒ 依 CLAUDE.md「三方數據正確性簽核」；改後值須以獨立 oracle（pandas／numpy／TA-Lib 等業界庫）於真實資料（`data_cache/feature_klines/kline_cache.h5`）比對，不得以「改後＝改前」代替。
- 全量期間不在整合樹改檔；施工在整合分支（全量收尾後）或依 I2 清單分流。
- 分類單一真相源：版控 `tests/_golden/prered/allowed_red.json`（處置；原因、驗證之樹與收尾者寫於列之 `trigger`）；已修者之漂移原因寫於提交訊息；各子項實測檔（`runs/` 下，gitignore）為非契約之工作筆記；本 SPEC 不列舉 nodeid（2026-11-17 I1d1 修訂，見 Task 4.1）。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I1-BUDGET-1 | 全量剩餘 106 條於 i7b-probe 補跑 | 段 9 未執行之 103 條＋卡死排除 3 條 | 106 條 | ✅ 已實跑：`103 passed, 3 xfailed … in 6505.94s (1:48:25)`（`runs/testsel_route/i1_proto/i7e_remaining.log`）；跑前 ledger 估快速 386 s＋重型 5,006 s | I7e 段 1–8 結果 |
| TESTSEL-I1-BUDGET-2 | 段 4 前綴依序重放（定位順序污染） | numba_rolling 等 5 數值檔於長行程中之狀態 | 404 檔 | 已實跑一次（帶 `--testmon`、整檔）：`… in 16399.79s (4:33:19)`（`runs/testsel_route/i1_proto/bisect_numba4b.log`，未重現）；不另跑專用重放，併入 I1 收尾全量（Task 2.1，I1c 審 r1 改寫） | 無 |
| TESTSEL-I1-BUDGET-4 | Task 2.4 現存 run 之 L3 skew／kurt 理論界檢查（原「全窗精確驗值」經 I1b 實測不可行，見 Task 2.4 先查；界檢查已對全部 23 run 實跑完成） | 正式資料中全部 L3 skew／kurt 欄之每個存檔值 | 現存 run 中只 BTCUSDT/12h `0729db3a…` 有 L3 skew／kurt：28,528 欄 × 1,951 列（halffloat 27,777／float 751） | 已實跑：`scripts/l3_moment_bound_check.py` 依存檔型別量化端點，0729db3a 量化後 0 越界（`runs/testsel_route/i1b/i1b_facts.md` ③）；單 run 界檢查＋抽欄比對實測 5.65 s | 無 |
| TESTSEL-I1-BUDGET-5 | I1g 施工驗收（manifest `TESTSEL_I1G.json` gate_cmd）：`test_numview_core.py` 27 個落選分支 nodeid（收集期條件跳過）＋`test_prered_allowed_red.py`＋failopen v8 限定版＋`test_numview_criteria.py` 3 條判準檢查 | 落選分支跳過於 fixture 建立前生效、凍結判準檢查不受影響 | 27＋5 節點 | 27 條跳過不建 fixture（`runs/testsel_route/i1g/run_skipif_probe.sh` ⇒ `fixture_built_lines=0`）；其餘 5 節點依 ledger；量級分鐘內 | 無 |
| TESTSEL-I1-BUDGET-6 | I1f 原型：NUMVIEW 格 B 於同一碼態以全新空暫存根各生成一次——排程器平行臂（非主週期於 spawn 子行程）與串行臂（本行程）——比對 raw／processed 逐位元 | 串行臂與平行臂輸出等價（I1f 擬令 spy 一律走串行臂之前提） | 格 B × 2 次生成 | 依 I1f 實測分支全新重跑 565 秒（`runs/testsel_route/i1f/i1f_facts.md`）⇒ 約 2×10 分鐘；不寫正式 data_cache | 無 |
| TESTSEL-I1-BUDGET-7 | I1f 施工驗收（manifest `TESTSEL_I1F.json` gate_cmd）：全新空 session 快取根生成格 A＋B（強制串行），`test_l2_named_matrix_pinned_nonzero_named_and_layers_bitwise`、`test_numview_regen_cache_hit_equals_empty_root`、`test_mutation_l2_spy_skips_non_primary_breaks_two_arm_observation`、`test_mutation_l2_forced_serial_injection_removed_breaks_precondition`（§G 第二層拆至 I1f2） | L2 兩臂逐週期（含 4h）觀測、§G 第一層通過條件、快取命中＝空根 | 格 A＋B 各一次生成＋同 session 命中 | 依原型格 B 串行 317 秒（`runs/testsel_route/i1f/i1f_facts.md` 原型節）與分支全新重跑 565 秒 ⇒ 量級 15–30 分鐘；I1 收尾重型批執行 | 無 |
| TESTSEL-I1-BUDGET-8 | I1f2 原型（已實跑）＋施工驗收：格 B（`B_BTCUSDT_1h_4h`）強制串行生成一次，於 L2 呼叫點擷取 layer1，Cross／Ratio 兩臂各對獨立 numpy oracle 判 (i)(ii) 並記 (iii)；施工驗收之 `test_l2_arms_each_match_independent_oracle` 與 BUDGET-7 同一 gate、共用同 session 之格 B 生成（不另生成） | L2 Polars 臂（float32 輸入）與 category 臂（float64 輸入）逐格對獨立 oracle、含非主週期 4h；Polars 臂對 float64 真值之偏差有可證上界 | 格 B 一次生成（1h 12,256 列、4h 3,064 列 × 536 欄） | ✅ 原型已實跑：生成 272 秒（`[run-watched] exit rc=0（272 秒）`）、分析 48 秒（`[run] analyze rc=0 wall=48s`；`runs/testsel_route/i1f2/run_probe.log`）；施工驗收增量＝分析約 1 分鐘（生成計入 BUDGET-7） | BUDGET-7 之格 B 生成 |
| TESTSEL-I1-BUDGET-3 | 修後受影響測試（含重型）一次 | 本票改動之受影響集 | 依 TEST_SELECTION §5 | 施工後依 ledger 估 | 無 |
- 不降驗證之省法：BUDGET-2 先以最近鄰／涉 numba 之檔試（已試 7 組皆未重現，含段 4 完整前綴整檔重放，見 red_classified.md），重現後才二分；BUDGET-1 改在同 commit 之 probe 補跑而非重開全量。
- 小規模驗不到之理由：順序污染只在長行程前綴出現（單跑、帶 --testmon 單跑、根目錄 47 檔前綴、段 4 完整前綴整檔重放皆未重現）。

## §B 四項平衡實測
- 適用於 Task 2.4（改 L3 pandas 臂 skew／kurt）與 Task 1.7（改 `taker_ratio` 計算）；其餘 Task 不改產品計算路徑。
- Task 2.4：代表規模＝真實 BTCUSDT/1h（20,352 列）L1 欄於產品預設窗 `[5, 13, 21]`，成長曲線 3 點＝欄數 64／256／1,024（同一資料，列數固定）；量測改前（pandas rolling）與改後（numpy 兩遍法）之耗時、峰值 RSS（同一量測器）、精度（對精確 oracle 之最大相對差）、輸出大小（L3 欄 bytes）；改後精度須達 ≤1 float32 ulp，耗時與 RSS 增幅逐點列出並與 numba 臂同規模比較，主要模組另比 `tests/_golden/balance/<模組>.json`（`scripts/balance_check.py`）。
- Task 1.7：`taker_ratio` 由 float32 相除改為 float64 相除後捨入，計算量與輸出大小不變（仍 float32）；精度改善以 Task 1.7 之 `decimal` oracle 驗。

## §G Golden / Baseline
- **feature/kline 條件**：Task 3.2 之 L2 兩臂 4h 值驗證用真實 `data_cache/feature_klines/kline_cache.h5`（格 B_BTCUSDT_1h_4h），禁合成；Task 1.6 重抓之 ETHUSDT/1h 以 Binance 實際 K 線驗。
- **凍結時機 / reference**：Task 3.2 修量測後，以全新空 `NUMVIEW_REGEN_BATCH_ROOT` 生成格 A＋B，產出逐週期兩臂；reference＝pandas 獨立重算之公開 L2 類別表。
- **baseline 內容**：每週期之 f32diff 計數、不等格之欄名集合 sha256、每欄 max abs diff、NaN mask hash。
- **通過條件（兩層，比對對象不同、不得混用）**：
  - 第一層＝契約語意（兩產品來源互比，`momentum/FeatureEngineering/contracts/numeric_view.json` 之 `l2_value_sources`）：契約未列之格，Polars 回傳臂與公開類別臂 float32 逐位元相等（f32diff＝0）；具名格（`nonzero_cells`）之每週期 f32diff 計數等於新收據釘值。1h 已實測與現收據逐格相等（536 欄不等格 0）。
  - 第二層＝各臂獨立正確（每臂對獨立 oracle；Task 3.3／大綱 I1f2，2026-11-18 依原型 `runs/testsel_route/i1f2/i1f2_facts.md` 改寫——原文只寫 `abs(np.spacing(ref))` 而未定 oracle 輸入精度）：範圍＝格 B 之 Cross（a−b）與 Ratio（a／遮罩後 b）各 268 欄、1h 與 4h；oracle 只用 numpy、不 import `momentum`；L1 取自 L2 呼叫點擷取之 layer1（原型 §2：與產品 L2 實際輸入 147／147 欄逐位元相同；run 落盤 raw 只 500 列且為 float16／32，不可用）。兩條硬判準皆須 0 格超界、NaN 位置一致：
    - (i) **各臂實際輸入精度、1 ulp**：Polars 臂 oracle 吃 `float32(L1)`（產品 `momentum/FeatureEngineering/operators/derived_operators.py:138` `pandas_to_polars(layer1_df)` 預設 float32），category 臂 oracle 吃 float64 L1；判定式 `abs(out − ref) ≤ abs(np.spacing(ref))`，ref 為 oracle 依該臂輸出 dtype 捨入之值，差以 float64 計——**依臂之 dtype 判**：Polars 臂 out 與 ref 皆 float32；**category 臂 out 與 ref 皆保持 float64，`np.spacing` 取 float64 之 ref，禁止先轉 float32 再判**（原型 `probe_l2_oracle.py` `judge` 一律先 `_f32` 屬 float32 視角，不得照抄；判定函式 `l2_oracle.within_1ulp(out, ref)` 以兩者 dtype 分支、dtype 不同即拒）。原型實測兩臂兩週期皆 0 超界（且 Polars 臂逐位元等於 float32 輸入 oracle、category 臂逐位元等於 float64 oracle）。
    - (ii) **Polars 臂對 float64 真值之可證誤差界**（不用相對誤差式：其把「相對原值」與「相對捨入值」混用、且 a32＝0 時無定義）：oracle 吃 float64 L1；令 `A=float32(a)`、`B=float32(b)`、`Ea=½·|spacing(A)|`、`Eb=½·|spacing(B)|`、`Eo=½·|spacing(out32)|`、真值 `r`（Cross＝a−b、Ratio＝a/b）。Cross 界＝`Ea+Eb+Eo`；Ratio 界＝`(Ea+|r|·Eb)/|B|+Eo`（由恆等式 `A/B−r=((A−a)−r(B−b))/B`，不除以 a，a＝0 有定義；`|A−a|≤Ea` 對正規與次正規皆成立，捨入跨入較大 binade 時 spacing(A) 只會變大）。**適用域**：oracle 與 Polars 臂兩者皆有限之格；遮罩位置（NaN）不一致另計 FAIL；Ratio 之 B＝0 不會出現於有限格（產品遮罩 exact 0）。**機器判定**：以 float64 計 err 與界，`err > 界·(1−2^-30)` 之格改以 `fractions.Fraction` 精確重算 err 與界（輸入皆二進浮點值、可精確表示），精確 err＞精確界才算超界。界公式照此原樣寫入測試、不得近似或加調整係數。實測（`probe_bound_v2.log`）0 超界，max err/界 1h Cross 0.99999976、Ratio 0.99995。
    - (iii) **只記錄、不判定**：Polars 臂對 float64 真值 1 ulp 之超界格數、max abs、max rel 與「Polars 得 0 而真值非 0」格數寫入收據（原型：1h 2,860,203 格、4h 605,933 格；4 格得 0 而真值非 0）。此為產品 D-L2 精度選擇（L1 先轉 float32）之影響面，改否屬產品精度決策、不屬本票；新收據三方簽核時判讀。
    - 超出 (i) 或 (ii) 即列欄名、列、out、ref、界＝FAIL。
  - 新收據（含 4h）經三方資料正確簽核後才可替換舊收據。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 0 — 紅清單完整（依賴：無）
**Task 0.1 — 全量剩餘補跑**
- 目標：I7e 未執行之 106 條於 i7b-probe 補跑，紅併入清單。　檔案：`runs/testsel_route/i1_proto/i7e_remaining.txt`（既有）　既有 caller：無
- **驗證（可證偽）**：補跑 log 末行 summary 之各結果合計＝106；data_cache 標記檔後 `find data_cache -newer` 無新寫入（有則列為 Task 1.2 寫入者）。
- **邊界**：①g7 類單條數百秒無輸出 ⇒ run_watched 判卡死時記為「卡死未判」列入清單，不視為通過；②已知寫正式資料之三條照排除。
- **存活至**：Task 4.1 清單建立後即被吸收。　**覆蓋風險**：無。
- 不可做：不重開整合樹全量；不還原整合樹 golden。

### Phase 1 — 隔離根與狀態外洩（依賴：Phase 0）
**Task 1.1 — 正式資料根寫入偵測擴至整個 data_cache**
- 目標：測試 session 前後對 `data_cache` 遞迴（檔 mtime_ns＋size、目錄項集合）快照比對，任何新增／修改／刪除 ⇒ session 結束狀態非零並具名列出路徑。　檔案：`tests/conftest.py`（`_PROD_WRITE_DIRS`、`prod_write_snapshot`、`pytest_sessionfinish`）　既有 caller：全部測試 session。
- 定位：「測試不寫正式資料」之主路徑＝Task 1.2 之明給暫存根（業界之依賴注入／tmp 根）；本 Task 為其後之安全網，抓漏網者。
- 改法：範圍由兩個頂層目錄改為 `data_cache` 全樹（解析符號連結至實體）；結果由只報改為設 `session.exitstatus` 非零；列出之每個路徑附其 mtime，以對照 TESTREG ledger 各測試起訖時間歸因至單一測試（不做逐測試快照）。
- 執行前提（寫入 `docs/TEST_SELECTION.md` 全量／收案層之執行條件）：全量與受影響集跑時，不得有並行之正式服務寫入 `data_cache`（API／前端／下載排程停止）；session 開始與結束時各查一次正式服務行程（`pgrep -if 'run_api.py|uvicorn|next dev|next start'`）皆為空，任一非空即該次結果不採計、前提滿足後重跑（`lsof` 只反映當下開檔，不作判定依據）；期間之間歇寫入另由列出路徑之 mtime 對 ledger 測試時段歸因（見邊界②）。
- **驗證（可證偽）**：新測試以 pytester 建暫存 repo 根：①測試寫 `data_cache/patterns/x.json` ⇒ rc≠0 且輸出含該路徑；②就地改寫既有 `data_cache/kline_cache.h5`（同大小、mtime 變）⇒ rc≠0；③只讀 ⇒ rc=0。mutation：把範圍改回兩頂層目錄 ⇒ ① 漏抓轉綠。
- **邊界**：①`data_cache` 為符號連結（worktree）⇒ 解析至實體再掃；②執行前提被違反（有並行正式寫入）⇒ 列出之路徑以 mtime 對 ledger 歸因，落在無測試執行之時段者標「非測試寫入」，不計為測試紅，但該次結果須於前提滿足時重跑確認。
- **存活至**：I3 移植至 main 後保留。　**覆蓋風險**：I3 移植 conftest 時須原樣帶入（I2 清單 keep-owner 列）。
- 不可做：不做逐測試快照；不 chmod 正式目錄。

**Task 1.2 — 寫正式資料之測試改暫存根**
- 目標：已知寫入者及 Task 0.1／1.1 新抓到者，全部改寫暫存根。已知：`tests/momentum/test_la2_lookahead.py::test_pattern_promotion_guard`、`tests/test_append_fix.py::test_multi_range_append`、`tests/api/test_scan_cube.py::test_cube_failure_does_not_kill_scan_results`；型態假資料之名稱（`n`、`nl`、`np`、`f`、`good`、`a`／`b`／`c`）對應之全部測試以 grep 一次找齊。　既有 caller：無（測試本身）。
- 改法：以明給根（`tmp_path`）建構服務／存放；`test_multi_range_append` 直連 Binance 且檔內已有密封姊妹 `test_multi_range_append_isolated_cache_sum_and_revision` ⇒ 原測試改用暫存 `cache_dir`（保留網路路徑覆蓋）。
- **驗證（可證偽）**：各測試於 Task 1.1 偵測下 rc=0 且通過；mutation：把任一條改回預設根 ⇒ Task 1.1 偵測 rc≠0。
- **邊界**：①測試需讀真實 kline（feature_klines）⇒ 唯讀不受影響；②網路不可用 ⇒ 原有行為（不得改為 skip 掩蓋）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改產品預設路徑（Rule 5 之字面路徑屬另案，§N 登記）。

**Task 1.3 — HERMETIC 重導只作用於寫入預設**
- 目標：讀真實 run 之測試不被導向空暫存根。　檔案：`tests/conftest.py`（HERMETIC 段）、`tests/momentum/test_feature_library_row_index.py`、`tests/momentum/Analysis/test_ic_persist_redirect_isolation.py`　既有 caller：全部測試。
- 改法：讀真實 run 之測試明給根；S11 探針之期望根與 HERMETIC 根之關係依該測試原意（探針須落在測試給定根下）修。
- **驗證（可證偽）**：`test_load_real_run_attaches_persisted_axis`、`test_load_real_run_value_conservation`、`test_all_seam_probes_stay_under_root[S11]` 於整合分支通過；main 基準已通過（9f059c65）。
- **邊界**：①未給根之寫入仍落 HERMETIC 根（Task 1.1 偵測 rc=0）；②給根之讀取讀實際 run。
- **存活至**：I3 移植後保留。　**覆蓋風險**：無。
- 不可做：不移除 HERMETIC 重導。

**Task 1.4 — root logger handler 外洩**
- 目標：任一測試新增至 root logger 之 handler 於該測試結束後關閉並移除。　檔案：`tests/conftest.py`（新 autouse fixture，function 範圍）；`tests/momentum/DataExtraction/test_search_download_pagination.py:599,613` 兩測試加 finally 清理。　既有 caller：全部測試。
- **驗證（可證偽）**：依段 5 順序跑 pagination 檔 44 條 ⇒ 全過（現況 11 failed，見 TESTSEL_REMAINING 11-16 20:02 列）；新增兩條單元測試分別驗兩邊界：(i) 測試 A 掛 root handler 且不清理、測試 B 斷言 root handlers 不含之 ⇒ 1 passed；(ii) 使用 `caplog` 之測試於 fixture 清理後 `caplog.records` 仍收到紀錄 ⇒ 1 passed。mutation 分開做：M1 移除 fixture（兩測試 finally 保留）⇒ (i) 1 failed；M2 fixture 改為清除全部 root handlers（含 pytest 自身）⇒ (ii) 1 failed；M3 兩測試 finally 移除而 fixture 保留 ⇒ pagination 44 條仍全過（證 fixture 單獨足夠）。
- **邊界**：①測試刻意測 handler 掛載 ⇒ 於測試內斷言後由 fixture 清理；②pytest 自身 handler（caplog／logging plugin）不得被移除（只移除測試期間新增者）。
- **存活至**：I3 移植後保留。　**覆蓋風險**：無。
- 不可做：不改產品 `_init_worker_file_logging` 語意（子行程用法正確）。

**Task 1.5 — golden 輸入檔不被測試改寫**
- 目標：跑完 la1／la0 相關測試後 `git status --porcelain tests/golden` 為空。　檔案：`tests/golden/la1/gen_baseline.py`（`INPUTS_DIR`／`OUTPUT_DIR` 由呼叫端可給）、呼叫之測試　既有 caller：`tests/momentum/test_la1_lookahead.py`、`tests/api/test_ic_la1_degraded_gate.py`、`tests/momentum/test_ic_golden_inputs_names_opaque.py`。
- 閘門 1.5a（定位，先於任何改碼）：對 `grep -rln 'golden/la1\|golden/la0\|gen_baseline' tests` 之每個測試檔逐檔單跑，前後比對 `tests/golden/**` 全部檔之 sha256，產出 `runs/testsel_route/i1_golden_writers.json`（{測試 nodeid: [被改檔]}）。通過條件＝每個被改檔都有歸因之測試、候選檔全數跑過；未過不得進 1.5b。（ETHUSDT_12h `_fallback_tail100.h5` 之寫入者目前推測為 la1 相關，未查證——即由本閘門查。）
- 1.5b（修）：僅修 1.5a 列出之寫入者，令其寫暫存複本；改法依 1.5a 結果定（`gen_baseline.py` 可給輸出根為候選之一）。
- **驗證（可證偽）**：1.5a 清單中每條測試跑後 `tests/golden/**` 之 sha256 與跑前相同；mutation：任一寫入者改回寫 repo 路徑 ⇒ sha256 不同。
- **邊界**：①重生 golden 之正式命令（人工執行 gen_baseline）仍寫 repo；②測試讀 golden 仍讀 repo。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以「跑完再 git checkout」作修法。

**Task 1.6 — 正式資料之測試污染清除與真實資料重抓**
- 目標：清除測試寫入正式資料之全部假資料，並以專案既有下載程式經 Binance API 重抓被測試污染之真實 K 線。　檔案：`data_cache/patterns/`（370 檔全為測試假型態＋`_index.json`）、`data_cache/ic_scan_cubes/t1/`、`data_cache/kline_cache.h5` 之 ETHUSDT/1h　既有 caller：PatternManagementService、IC scan cube、`momentum/Indicators/data_source_manager.py:60`（預設 K 線庫）。
- 改法：①備份至 `runs/testsel_route/datacache_backup/`（已做，h5 sha256 前綴 950f3dca 一致）；②以產品 `delete_pattern`／`delete_all_patterns`（`api/services/pattern_management_service.py:545,555`）刪除測試簽章之型態並同步索引；③刪 `ic_scan_cubes/t1/`；④ETHUSDT/1h 以 `KlineDownloadService`＋`BinanceProvider` 下載同時段（2024-05-20 20:00～2025-10-27 12:00）連續 K 線，`KlineStorageManager.write_klines`（覆寫模式，`momentum/DataExtraction/kline_storage.py:742`）取代整組。
- **驗證（可證偽）**：`data_cache/patterns` 無規則含 `f0`／`f` 之測試簽章檔、`_index.json` 合法且不含已刪 id；`ic_scan_cubes/t1`、`task-scan` 不存在；ETHUSDT/1h `inspect_kline_h5.py` 得 `gaps=0 dup=0`、筆數＝(末−首)/1h＋1（實測 12,593）；`cmp_kline_groups.py <備份> data_cache/kline_cache.h5` 其餘 4 組「逐位元相同」、ETHUSDT/1h 與備份重疊 1,762 筆 OHLCV 不等欄＝無。
- `taker_ratio` 1 ulp 差（重疊 1,762 筆中 534 筆，max_abs 5.96e-08，NaN 不一致 0）之處置：同源 Binance 資料經 append 路徑與一次下載路徑之 float32 結果應逐位元相同 ⇒ 列 I1 子項 Task 1.7 定因，不在本 Task 放行或忽略。
- **邊界**：①`_index.json` 其他條目不變；②重抓期間網路失敗 ⇒ 保留原組（write_klines 原子 swap）、不留半寫入狀態。
- **存活至**：永久。　**覆蓋風險**：Task 1.2 未完成前再跑相關測試會再污染 ⇒ Task 1.2 完成後以 Task 1.1 偵測確認。
- 不可做：不動 `data_cache/feature_klines/kline_cache.h5`（量化主線之真實 K 線來源）；不刪測試簽章以外之檔。

**Task 1.7 — K 線寫入路徑之 taker_ratio 決定性**
- 目標：產品內 `taker_ratio` 有兩個計算點且算法不同——`momentum/DataExtraction/providers/binance_provider.py:472–482`（volume、taker_buy_volume 先轉 float32 再相除，結果 float32）與 `momentum/DataExtraction/kline_storage.py:491–495`（舊快取匯入：float64 相除後轉 float32）；兩者對同一原始值可差 1 float32 ulp（實測 1,762 筆中 534 筆）。先以備份 h5 之 ETHUSDT/1h metadata／寫入紀錄定位舊組由哪一路徑產生（定位結果寫入 `runs/testsel_route/i1_reds.json` 該項 evidence），再統一兩計算點為單一函式。　既有 caller：KlineDownloadService、`_import_from_legacy_cache`、data_source_manager。
- 定義（單一正解）：`taker_ratio`＝Binance 原始字串欄 `taker_buy_base_asset_volume` 與 `volume` 以 float64 解析後相除，一次捨入為 float32，再 clip 至 [0,1]；volume＝0 ⇒ 0.5（現行兩計算點之既有約定，`_validate_kline_dataframe` 要求 [0,1] 且拒 NaN）。此定義較現行 provider 之 float32 先除精確（只捨入一次）；改後 provider 輸出可能有 1 ulp 變動，屬產品值改動 ⇒ §G 三方簽核範圍。
- 錄製物：Binance `GET /api/v3/klines` 之原始 JSON 回應（數值欄為字串，於 provider `_convert_to_dataframe` 之 `astype('float32')`（`binance_provider.py:472–473`）之前擷取），存 `tests/fixtures/` 下；不得存經 provider 轉型後之 DataFrame。
- **驗證（可證偽）**：新測試以上述錄製之原始 JSON（非合成）分別走 provider 路徑與舊快取匯入路徑，`taker_ratio` 逐位元相同（`tobytes()` 相等）且等於上列定義之獨立計算（Python `decimal` 自原始字串計算後轉 float32）；mutation：provider 改回 float32 先除 ⇒ 1 failed。
- **邊界**：①volume＝0 ⇒ 兩路徑皆 0.5；②taker_buy_volume > volume（資料異常）⇒ clip 為 1.0，兩路徑相同；③既有庫內資料不重寫（只修路徑；`data_cache/feature_klines/kline_cache.h5` 之既有值是否重抓另依 §G 簽核決定）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以容差斷言掩蓋。

### Phase 2 — 順序污染（依賴：Phase 1）
**Task 2.1 — 定位並修段 4 數值檔叢集**
- 目標：`test_numba_rolling`（19 條 skew／kurt 類）、`test_multi_window_rolling`、`test_polars_phase4`、`test_talib_wrapper`、`test_winsorize_partition_opt` 於段 4 長行程紅之污染源定位並修。　檔案：待定位　既有 caller：待定位。
- 重放（2026-11-18 I1c 審 r1 改寫，`handoffs/reconcile/20261118-testseli1c-x-review-r1/synth.md`）：既有 7 組重放（含段 4 完整前綴 404 檔，`runs/testsel_route/i1_proto/bisect_numba4b.log` `16399.79s`）皆未重現（`runs/testsel_route/i1_proto/red_classified.md:36-48`）⇒ 不另跑專用重放；重放＝I1 收尾全量本身（整合樹、正確性層同參數 `-m "not perf"`、`--testsel-tier close`、testsel 外掛、`MallocSpaceEfficient=1`），讀其中本 Task 五檔之結果。收尾全量重現 ≥1 failed ⇒ 以該次順序二分至單一污染測試並修（下列驗證）；未重現 ⇒ 依邊界①結案。依據：使用者 2026-11-17「你跟委員就不能全部修到好，只跑一次嗎？」；原 ①（同 commit 樹 4.5 小時級）③（並行記憶體壓力）不另跑。
- **驗證（可證偽）**：I1 收尾全量（log 存 `runs/testsel_route/`）重現 `tests/test_numba_rolling.py` ≥1 failed → 二分至單一污染測試 → 修後同命令 `tests/test_numba_rolling.py` 0 failed；並以「污染測試＋受害測試」兩條最小重現作為新回歸測試（`pytest <污染>::… tests/test_numba_rolling.py` 修前 failed≥1、修後 0）。
- **邊界**：①既有 7 組與 I1 收尾全量皆未重現 ⇒ 不得單以「重現條件」收案：另以獨立 oracle 證 `rolling_skew_kurt` 值正確後才可列追蹤項。oracle＝逐窗精確有理數計算（Python `fractions.Fraction`，樣本偏態／超額峰度，定義同 `scipy.stats.skew(bias=False)`／`scipy.stats.kurtosis(fisher=True, bias=False)`）；**不得以 pandas rolling 作 oracle**——原型實測（`runs/testsel_route/i1_proto/arbiter_kurt.py`，BTCUSDT/1h close）pandas `rolling(5).kurt()` 對精確值最大差 36.5（例 row 9401：精確 −2.37908、pandas 34.1022、產品 −2.37908），為 pandas 線上累積演算法於大均值序列之數值抵消。逐窗全部分類、無遺漏：(i) 產品與 oracle 皆有限 ⇒ `abs(out − ref) ≤ abs(np.spacing(np.float32(ref)))`（產品輸出 float32；原型實測產品對精確值於 w=5／13／21 各 2,000 抽樣窗之最大相對差 5.83e-8／5.88e-8／5.86e-8，可達）；(ii) 兩者皆 NaN（樣本數不足、常數窗，產品約定見 `tests/test_numba_rolling.py` 之 `test_numba_rolling_skew_kurt_constant_is_nan`、`test_numba_rolling_n_less_than_window_all_nan`）⇒ 相符；(iii) 其餘任何組合（一方有限一方 NaN）⇒ FAIL。路徑覆蓋（非重複資料格）：一個真實 kline 格（`data_cache/feature_klines/kline_cache.h5` BTCUSDT/1h）之 close（大均值）與 log return（小均值）兩序列 × 產品預設窗長 `[5, 13, 21]`（`momentum/FeatureEngineering/feature_config.py:451`）；第二資料格僅於結果確實隨資料而變時加（CLAUDE.md「測試／量測設計＝路徑覆蓋」）。全過且收尾全量未重現 ⇒ Task 2.1 結案（不列 allowed_red；結案紀錄附 7 組重放與收尾全量 log 路徑），之後由 I5 週期全量以失敗明細追蹤；oracle 斷言紅（例：近零值超 1 float32 ulp）⇒ 停工 BLOCKED：不放寬、不 skip、不改容差、不改 allowed_red，保留紅並回報明細（nodeid、窗、產品值、精確值、ulp 差），產品修正與任何登記另案核准（I1c 審 r2）；②污染源為產品模組狀態（非測試）⇒ 升級為產品修正並補產品層測試。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以 xdist／隨機順序掩蓋。

**Task 2.4 — L3 pandas 臂 skew／kurt 數值錯（產品）**
- 目標：`momentum/FeatureEngineering/operators/rolling_aggregator.py` 中以 pandas `rolling().skew()`／`.kurt()` 計算之四處——`_compute_all_streaming_pandas` :313、`_compute_all_streaming_numba_single_window` :459（numba 單窗路徑之 skew／kurt 亦走 pandas）、`_apply_vectorized_aggregators_with_cache` :878–883、`_compute_skew`／`_compute_kurt` :950–954——於大均值欄（價位類 L1 指標，如 `close_1h_trend_BBANDS-Lower_13`）之 kurt 與精確值差達 36.5（原型實測同 Task 2.1；I1b 實測真實 BTCUSDT/1h close 窗 5 kurt 20,348 窗中 19,035 窗超 1 float32 ulp，`runs/testsel_route/i1b/i1b_facts.md` ①），常數窗輸出 skew 0／kurt −3（產品約定為 NaN，同檔 ②）。生效情形：`FFACT_USE_NUMBA_ROLLING=0`（`memory_budget.py:154,169`，預設 "1"）、numba 臂拋例外後備（`rolling_aggregator.py:221–232`）、`FFACT_L3_MULTI_WINDOW=0`（`memory_budget.py:153,168`，預設 "1"；走 :459）、`FFACT_L3_STREAMING=0`（`memory_budget.py:152,167`，預設 "1"；`rolling_aggregator.py:137` 分流至非串流之 :878–883 與 :950–954）。預設（多窗 numba 路徑 `fused_rolling_stats_multi_window`→`rolling_skew_kurt`）本 Task 不改：於 close／log return 窗 5／13／21 全窗 fail＝0；另 64 欄真實 L1 × 3 窗之量測有 kurt 1 窗超 1 float32 ulp（正確值近 0，`runs/testsel_route/i1b/sec_b/precision_results.json`），I1 收尾前定處置。
- 改法：上列四處之 skew／kurt 改為單一**獨立於 numba 之** numpy 逐窗兩遍法函式（float64，先減窗均值再算二／三／四階中心矩；`numpy.lib.stride_tricks.sliding_window_view`），不呼叫任何 `@njit` 函式——numba 臂失敗而後備時，後備仍可用。退化約定（樣本數不足、窗內任一非有限值、常數窗 max＝min ⇒ NaN）與 numba 臂一致。I1b 實測：此實作於真實 BTCUSDT/1h close 與 log return、窗 5／13／21 全部窗對精確 oracle 皆 ≤ 1 float32 ulp（fail＝0），每欄每窗長 2.4–3.4 ms。
- 先查（施工前，已於 I1b 實測完成，`runs/testsel_route/i1b/i1b_facts.md` ③）：現行 provenance 只記 L6.5 預處理臂（`run_provenance.py:596` `group_arm_values`），無 L3 臂紀錄；原定「自存檔 L1 輸入逐窗精確驗值」實測不可行——存檔 L1 為 float32、L3 由存檔前 float64 計算，以存檔輸入重算對大量級欄幾乎全窗不符（OBV 窗 5 kurt 1,696／1,696 窗，max_rel 420），非產品錯而為輸入精度已失。改為**理論界檢查**（必要條件、全量、無抽樣；`scripts/l3_moment_bound_check.py`）：對 `data_cache/features` 每個現存 run 之每個 L3 skew／kurt 欄之每個值，檢查 |skew| ≤（n−1 等值＋1 離群之值）、（最平均兩點分佈之值）≤ kurt ≤（n−1 等值＋1 離群之值），端點放寬相對 1e-5 後**依欄位實際存檔型別量化**（產品 `feature_storage._select_parquet_storage_array` 於往返安全時存 float16；捨入單調 ⇒ 合法存檔值必在量化端點內）。實跑結果：23 個 run 中只 BTCUSDT/12h `0729db3a…` 有 L3 skew／kurt（28,528 欄，halffloat 27,777／float 751）；量化後 **0 越界**。（I1b 初版未量化而報 61,242 值越界，經審查 r1 指出並實測證實全部等於精確界值之 float16 量化，非錯值；該 run 不需重生。）界內之錯值無法由存檔值判出（存檔精度不足），本 Task 之正確性保證由修後程式之 oracle 驗收承擔。
- **驗證（可證偽）**：新測試於真實 BTCUSDT/1h（`data_cache/feature_klines/kline_cache.h5`）之 close 欄（大均值）與 log return（小均值），窗 `[5, 13, 21]`，分別於四種情形——`FFACT_USE_NUMBA_ROLLING=0`、`FFACT_L3_MULTI_WINDOW=0`、`FFACT_L3_STREAMING=0`、numba 臂注入例外（monkeypatch `fused_rolling_stats`／`fused_rolling_stats_multi_window` 拋例外）——產 L3 skew／kurt，逐窗對 Task 2.1 精確 oracle（實作 `tests/references/exact_moments.py`：整數滑動冪次和，中心矩以 `fractions.Fraction` 導出）依 (i)–(iii) 規則全過；且 pandas 臂與 numba 臂輸出每窗差 ≤ 1 float32 ulp（兩臂演算法不同，不要求逐位元）。mutation：M1 任一 pandas 計算點改回 `rolling().kurt()` ⇒ 1 failed（實測差 36.5）；M2 pandas 臂改呼 `numba_rolling.rolling_skew_kurt`，且注入例外範圍涵蓋 `numba_rolling` 模組全部公開 numba 入口（含 `rolling_skew_kurt`、`fused_rolling_stats`、`fused_rolling_stats_multi_window`）⇒ 1 failed（證後備不依賴任何 numba 函式）。
- **邊界**：①小均值欄（log return）兩臂同值（≤1 ulp）；②低基數欄之既有排除（`_columns_for_agg`）不變；③窗長 > 樣本數 ⇒ 全 NaN；④常數窗（max＝min）⇒ NaN（現行 pandas 臂輸出 skew 0／kurt −3，I1b 實測②）；⑤窗內含 ±inf 或 NaN ⇒ NaN（兩臂現行皆 NaN，須維持）。- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改 numba 臂；不改 `tail_risk_indicators.py` 之 returns 序列計算（原型實測 log return 上 pandas 對產品相對差 ≤ 1.18e-5，屬另一議題，於 Task 4.1 清單登記其 oracle 比對）。

**Task 2.5 — skew／kurt 守衛之 kurt 下界依窗長奇偶取可達最小值（產品）**
- 目標：`momentum/FeatureEngineering/operators/numba_rolling.py` `_compute_kurt`（下界 `lower = -2.0 * (n - 1.0) / (n - 3.0)`）與 `momentum/FeatureEngineering/operators/rolling_moments_numpy.py`（同式）對所有 n 用偶數 n 之可達最小值；奇數 n 之可達最小值較高（−2n/(n−2)），守衛偏寬——n=5 寬 20%（−4 對 −3.333），數值錯誤值落於兩式之間時不被擋。產品預設窗 `[5, 13, 21]` 全為奇數。
- 依據（`runs/testsel_route/i1e/i1e_facts.md`）：b2＝nΣd⁴/(Σd²)² 之最小值，偶數 n＝1（b2−1＝Var(Z²)≥0）；奇數 n＝(n²+3)/(n²−1)——n≥7 解析證明（正負分組＋Hölder＋Cauchy–Schwarz）、n=5 Lagrange 限縮＋有理數精確證書、n=3 恆等；數值另驗奇數 n≤10001 `violations=0`。換算超額峰度：偶數 n 下界 −2(n−1)/(n−3)，奇數 n 下界 −2n/(n−2)；對任意 n 成立，不設窗長上限。
- 改法：兩臂共用同一下界式（依 n 奇偶），容差 `_MOMENT_BOUND_TOL` 與越界 ⇒ NaN 之約定不變；上界與偏態界不變。
- **驗證（可證偽）**：①奇數 n（5、7、13、21、233）平衡兩點窗（以真實 BTCUSDT/1h close 之兩相異值排成 k／k+1）兩臂 kurt 有限且等於 −2n/(n−2)（numpy 臂 float64 ≤1e-9 相對；numba 臂 `rolling_skew_kurt` 輸出 float32，≤1 float32 ulp）；②直接呼叫守衛：奇數 n 之結果落於 (−2(n−1)/(n−3), −2n/(n−2)·(1+tol)) ⇒ NaN，恰於 −2n/(n−2) ⇒ 保留；容差 tol＝1e-9 不變：兩臂於下界 L 之相對 0.5e-9 外推保留、2e-9 外推 ⇒ NaN（numpy 臂以真實平衡窗之實際值 g 與置於其兩側之下界驗實際比較）；③偶數 n 行為不變（平衡兩點 ⇒ −2(n−1)/(n−3) 保留）；④既有 I1b 驗收（真實資料全窗對精確 oracle ≤1 float32 ulp）不變。mutation：任一臂下界改回偶數式 ⇒ ② 1 failed。
- **邊界**：①n=4（偶數最小可用窗）不變；②n=5（解析證明不涵蓋、由精確證書涵蓋）納入 ①②。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改上界、偏態界與容差；不改預設臂之其餘計算。

**Task 2.2 — `test_multi_tf_generator` 順序相依**
- 目標：該檔 5 條（`test_canonical_completeness_three_paths_four_cases[cgsa_*]`、`test_boundary_19_*`）於 `bisect_numba1.txt` 順序紅、段 4 順序下通過 ⇒ 定位並修。（2026-11-18 I1c 實測：此 5 條已登記 `tests/_golden/prered/allowed_red.json` owner FFPROD——FFTFMETA 非主週期失敗語意被 FFSTAT 預熱恆開〔d229336e〕之 `_resolve_public_window` 提前載入全部 training 週期破壞，屬產品缺陷之常駐紅、非順序污染；段 4 之「通過」待 I1 收尾全量核對該 5 條實際結果）
- **驗證（可證偽）**：①`jq '.[] | select(.node|test("test_multi_tf_generator"))' tests/_golden/prered/allowed_red.json` 得此 5 條、owner＝FFPROD、trigger 為上述產品缺陷；②I1 收尾全量此 5 條之 FAILED ⊆ allowed_red（Task 4.1 驗證之子集）；轉綠歸 FFPROD 修補後刪列。
- **邊界**：①本票不改產品、不刪此 5 條登記列；②收尾全量此 5 條若通過 ⇒ 依 Task 4.1「已修者 passed」處置並通知 FFPROD 核對。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：同 Task 2.1。

**Task 2.3 — 其餘乾淨行程通過之紅**
- 目標：`clean_pass_funcs.txt` 其餘函式逐一歸因（污染源或不穩）。
- **驗證（可證偽）**：Phase 1 修後之全量（I5 週期全量）log 中 `clean_pass_funcs.txt` 所列 46 個函式之 FAILED／ERROR 計數＝0；仍紅者依 Task 2.1 法定位。
- **邊界**：同 Task 2.1。　**存活至**：永久。　**覆蓋風險**：無。　不可做：同 Task 2.1。

### Phase 3 — 整合分支才紅（依賴：無）
**Task 3.1 — 結構重凍收據鏈**
- 目標：`test_structural_refreeze_receipt_proves_strip_equals_frozen` 接受後續重凍鏈。　檔案：`tests/feature_engineering/test_numview_acceptance.py:1565–1579`
- 改法：NUMVIEW 收據 `sha256_after` 須等於現行檔，或存在後續重凍收據使 before／after 逐段相接至現行檔（FRAMEPATH v2：`tests/_golden/framepath/refreeze_provenance_v2_receipt.json:14–15`）。
- **驗證（可證偽）**：測試通過；mutation：竄改 v2 收據 `baseline_sha256_before` ⇒ 紅。
- **邊界**：①無後續收據且 sha 不符 ⇒ 紅；②鏈斷於中段 ⇒ 紅。
- **存活至**：永久。　**覆蓋風險**：無。　不可做：不改凍結檔、不改收據值。

**Task 3.2 — NUMVIEW 批次快取與 L2 量測**
- 實測（2026-11-18 I1f，`runs/testsel_route/i1f/i1f_facts.md`）推翻原前提：①快取根 `tests/feature_engineering/numview_helpers.py:164-172` `regen_batch_root()` 預設 `$TMPDIR/numview-regen-batch`，跨 session、跨工作樹沿用、無鎖；鍵不含測試自身 `_generate`、conftest 與套件版本；②spy 漏記 4h 之真因**不是**「是否新持久化 L2 群組」，而是記憶體預算排程器（`momentum/FeatureEngineering/timeframe/multi_tf_generator.py:633-642`）准入時非主週期於 spawn 子行程計算、spy 看不到——故原驗證之 mutation「spy 改回依持久化與否」為空心；③原型（SPEC §B BUDGET-6）：同一碼態格 B 串行臂與平行臂 raw 7264 欄、processed 5943 欄逐位元相等（不等 0 欄），但串行臂使 run 之 `route_identity` 由契約空值變非空（產品契約 `momentum/FeatureEngineering/contracts/numeric_view.json` 之 `route_switch_points` 未登錄 scheduler）。
- 目標（改寫）：①批次共用生成快取根改為 session 暫存（`tmp_path_factory` 或 conftest 於 `pytest_configure` 設 `NUMVIEW_REGEN_BATCH_ROOT`），不跨 session 沿用；②量測 spy 安裝時令 multi_tf_generator 之排程器走產品既有串行臂（注入點 `momentum.factories.create_memory_budget_scheduler`，傳產品既有參數 `aux_startup_envelope=None`；不用契約標為 value_affecting 之 `FFACT_MULTI_TF_PARALLEL`），使每實例每週期兩臂皆可觀測；③`route_identity` 隨排程臂改變之處置（I1f 審 r1 定為 (a)）：量測 run 只供 L2 量測、不作共用快取之身分基準，比對排除 `route_identity`，其差異保留於收據；「run 身分隨排程分工改變」另立產品子項（產品契約 `route_switch_points` 依實際 caller／分支逐一取證、定既存身分相容策略後三方簽核；格 B 一例不足以認證整個 scheduler 換臂點——另兩個 pool 未驗）。我的判斷：使用者 2026-10-25「分工設定不算進指紋」原文範圍為批次分工鍵對 config_hash／raw 指紋（`tests/feature_engineering/test_numview_identity.py:1895`），可作該產品子項之方向參考，非本 Task 之直接依據；④`tests/api/test_numview_ic_page.py` 共用同一快取根，改 session 暫存後每 session 真生成——將其納入 `scripts/heavy_commands.json` 之 `pytest_heavy` regex（與 test_numview_core／acceptance／policy 對齊）；⑤依 §G 重量 4h 並驗證。
- **驗證（可證偽）**：§G 通過條件；`pytest tests/feature_engineering/test_numview_core.py::test_l2_named_matrix_pinned_nonzero_named_and_layers_bitwise` 於全新空快取根 1 passed，且新增「主實例每週期（含 4h）皆有兩臂觀測」斷言，並以前提斷言證強制串行**注入**生效：排程器 route 紀錄 `point=="scheduler"` 之 `reason=="no_aux_receipt"`（只於注入 `aux_startup_envelope=None` 時出現；自然不准入之串行為 `admission:budget`——`runs/testsel_route/i1f/i1f_facts.md` 原型與舊快取實錄）且 spy 有 4h 兩臂紀錄；另 `test_mutation_l2_forced_serial_injection_removed_breaks_precondition`：實際關閉 `FORCE_MTF_SERIAL` 於私有根重生格 B ⇒ reason 不為 `no_aux_receipt` ⇒ 前提斷言 1 failed（與機器准入無關之確定性；I1f 審 r3、審碼 b1 r1）；多週期格之強制串行觀測生成一律於測試私有根，共用快取 run 另以自然排程生成、不掛觀測器，兩者 raw／processed 逐位元與生成身分相等後才寫回觀測（`_generate` 之 `force_private`；審碼 b1 r1，落實方向 (a)「量測 run 不作共用快取身分基準」）；§G 第二層（兩臂各對獨立 oracle）**拆至子項 I1f2**（2026-11-18 施工中實測 `runs/testsel_route/i1f/l2_oracle_scope.md`：L2 無任何獨立於產品之逐格 oracle，須新寫；Polars 臂先將 L1 轉 float32〔`momentum/FeatureEngineering/operators/derived_operators.py:138`〕，判準輸入精度待定→已於 Task 3.3 定案），本 Task 不含該測試；新增 `test_numview_regen_cache_hit_equals_empty_root`（同 session 快取命中與空根結果逐位元相同）；mutation（I1f 審 r2 改寫——「強制平行准入」須繞過記憶體保護、無不改產品碼之確定接縫）：`test_mutation_l2_spy_skips_non_primary_breaks_two_arm_observation`——spy 略過非主週期之紀錄 ⇒ 兩臂觀測斷言 1 failed（確定性、與機器准入無關）；`scripts/heavy_commands.json` 之 `pytest_heavy` regex 含 `test_numview_ic_page`（gate 以 grep 驗）。gate 屬重型（經 `scripts/run_watched.py`、背景、估時收據對 §B TESTSEL-I1-BUDGET-7），於 I1 收尾重型批執行；新收據（含 4h）三方簽核後替換舊收據。
- **邊界**：①快取命中與不命中結果相同；②mutant 生成不讀寫共用快取（既有規則）；③串行臂與平行臂值逐位元相同為前提（原型已證，施工時保留探針收據）；④本 Task 不改產品契約 `momentum/FeatureEngineering/contracts/numeric_view.json`、不重凍 `tests/_golden/numview/*`（方向 (a)；若日後產品子項改走登錄 scheduler，須另列重凍與重簽範圍：`numeric_view.json`、`tests/_golden/numview/*`、依共用 run 比對 `route_identity` 之 identity 測試）。
- **存活至**：永久。　**覆蓋風險**：新收據替換舊收據須三方簽核。
- 不可做：不在簽核前改契約 `l2_value_sources.f32diff`。

**Task 3.3 — L2 Cross／Ratio 兩臂各對獨立 oracle（§G 第二層；大綱 I1f2）**
- 實測（2026-11-18，`runs/testsel_route/i1f2/i1f2_facts.md` 13 條 FACT-RECEIPT；SPEC §B TESTSEL-I1-BUDGET-8）：①格 B 強制串行生成，1h 與 4h 兩臂皆於本行程觀測（route `reason=no_aux_receipt`）；②L2 呼叫點之 layer1 與 category 臂輸入同一物件、147 欄 float64，與同 run 產品 L1 生成函式回傳逐位元相同；③§G 第二層 (i) 兩臂兩週期皆 0 超界（實為逐位元相等）；(ii) 原型之舊相對界亦 0 超界（max err/tol＝1.0000），該界經審 r1 改為現行絕對誤差界，以⑦為準；④(iii) Polars 臂 1h 2,860,203 格、4h 605,933 格、1h 有 4 格得 0 而真值非 0；⑤遮罩分支：格 B 之 Ratio 88 個分母欄只觸發「非有限」與「窗未滿」，exact 0 與相對近零 0 格（`probe_mask_paths.log`）；全部 147 個 L1 欄各自當分母亦 0 欄觸發（`runs/testsel_route/i1f2/probe_mask_all_l1.log`：`hit_cols=0`，1h／4h）⇒ 該兩分支在格 B 真實配對中無法算出值；⑥主委補查（審 r1 期間，`i1f2_facts.md` §6）：真實 BTCUSDT/1h（20352 列）之 TA-Lib `STOCHRSI` fastk 有 exact 0 5,240 格、相對近零 1 格（列 3682，值 5.19e-14），fastd 相對近零 1,046 格；窗內有限非零計數偶 10,085／奇 9,996 列（fastk）；產品 `causal_denominator_scale`／`causal_near_zero_mask` 對 oracle 於 12 欄 × float64／float32 共 24 組逐位元相等 ⇒ 四分支皆可由真實資料觸發；⑦(ii) 改絕對誤差界後重判（`probe_bound_v2.log`）0 超界。
- 目標：
  ①**重型** `tests/feature_engineering/test_numview_core.py::test_l2_arms_each_match_independent_oracle`：L2 觀測器於 L2 呼叫點另存 layer1 之拷貝（主實例、非校準；新增 `CellRun` 欄位，不改 `l2_arms` 之形狀與既有使用者）；對格 B 每週期之 Cross 與 Ratio，Polars 回傳臂與 category 臂各依 §G 第二層判 (i)，Polars 臂另判 (ii)（category 臂吃 float64，其 (ii) 即 (i)），(iii) 之計數、max abs、max rel、「得 0 而真值非 0」格數寫入測試輸出供收據；前提斷言：每週期 Cross、Ratio 各 268 欄，兩臂欄集相等，每欄由輸出欄名 `^(前綴)_(參數1)~(參數2)_(Cross|Ratio)$` 拆出之兩輸入皆在擷取之 layer1。
  ②**快速單元** 新檔 `tests/feature_engineering/test_l2_cross_ratio_oracle.py`，**純真實資料、不置入任何值**：經 `requires_kline_data` 唯讀取真實 BTCUSDT/1h，以 TA-Lib（業界標準指標庫）`STOCHRSI`（預設參數，同 `runs/testsel_route/i1f2/probe_osc_branches.py`）fastk 與 fastd 為 Ratio 分母、close 為分子（Cross 用 fastk−fastd 與 close 對 TA-Lib `EMA` 兩組真實欄）。Polars 臂（`pandas_to_polars` 預設精度後 `polars_l2_derived_ratio`／`polars_l2_derived_diff`）與 category 臂（`DerivedOperatorEngine.compute_ratio`／`compute_cross`）各依 (i) 對 oracle 比、NaN 位置一致；前提斷言四分支（非有限、exact 0、窗未滿、相對近零）於所用真實欄各至少 1 格命中（實測⑥），並具名斷言 fastk 列 3682 之 oracle 遮罩為 True。（`test_ratio_mask_branches_both_arms_match_oracle_on_real_stochrsi`、`test_cross_both_arms_match_oracle_on_real_kline`）。另**尺度值測試** `test_causal_scale_product_bitwise_equals_oracle_on_real_columns`：產品 `numeric_guards.causal_denominator_scale` 對 `l2_oracle.causal_scale` 於上述真實欄 × float64／float32 輸入逐位元相等（含 NaN 位置與起算點）、前提斷言窗內計數奇偶兩路徑皆命中；「窗內全無⇒尺度 0」路徑真實資料 0 列（且依定義該列本身為 0 或非有限、遮罩不受影響，`i1f2_facts.md` §6）⇒ 具名記為未覆蓋、不宣稱已驗。另 **(ii) 界之精確驗證** `test_bound_formulas_cover_exact_error_with_fractions`：以 `fractions.Fraction` 對上述真實欄之少量格（含 a＝0、次正規、跨 binade 捨入之真實格；無則具名記未覆蓋）驗 `l2_oracle.bound_cross`／`bound_ratio` ≥ 精確 err。`tests/feature_engineering/test_numeric_guards.py` 只驗 category 臂之 `safe_denominator` 期望值、`tests/test_polars_phase4.py::TestPolarsDivisionByZero` 只比兩臂互比且其「oracle」呼叫產品 `safe_denominator`，皆非對獨立 oracle。
  ③oracle 單一來源 `tests/feature_engineering/l2_oracle.py`：只依標準庫（含 fractions）與 numpy（不 import `momentum`、不呼叫產品遮罩／尺度函式），含 Cross、Ratio、因果尺度（第 t 列含之前 252 列窗內有限且非零值之絕對值中位數；窗未滿 NaN、窗內無此類值為 0）、遮罩（非有限、exact 0、尺度非有限、`|b| < 1e-6·scale`）、依 dtype 判定之 `within_1ulp`（§G (i)）、(ii) 之界與 Fraction 精確重判；①②共用。
- **驗證（可證偽）**：快速層 `pytest tests/feature_engineering/test_l2_cross_ratio_oracle.py` 全 passed，重型 `test_numview_core.py` 3 個 nodeid 1 passed／改壞對照各 1 failed：
  - 快速層：`pytest tests/feature_engineering/test_l2_cross_ratio_oracle.py` 全 passed；mutation `test_mutation_near_zero_term_removed_breaks_ratio_oracle`——monkeypatch `momentum.FeatureEngineering.utils.numeric_guards.causal_near_zero_mask` 為去掉 `abs_d < rel_eps * scale` 項之版本（兩臂共用此函式：`polars_adapter.py:58-61`、`numeric_guards.py:139`）⇒ 真實相對近零列（fastk 列 3682、fastd 1,046 列）兩臂皆非 NaN ⇒ 1 failed；`test_mutation_category_judged_in_float32_misses_f64_error`——category 臂某真實有限格加 `2·spacing(ref64)`（仍小於 float32 半 ulp），`within_1ulp` 依 float64 判須報超界、改以 float32 視角判則漏報 ⇒ 證 (i) category 臂確為 float64 判定；`test_l2_oracle_module_imports_numpy_only`——解析 `l2_oracle.py` 之 import 只含標準庫與 numpy。
  - 重型：`test_l2_arms_each_match_independent_oracle` 1 passed；判定器改壞對照（用已觀測之格 B 資料、不重生成）：`test_mutation_l2_oracle_one_cell_beyond_bound_detected`——Polars 臂某 Cross 格加 2 倍 (ii) 界 ⇒ (ii) 回報恰該格；`test_mutation_l2_oracle_wrong_input_precision_detected`——Polars 臂改對 float64 oracle 判 (i) ⇒ 超界格數 > 0（證 (i) 確依臂輸入精度、非空判）。**共用生成之落實**：`runs` 為 module 範圍 fixture、`_Runs._cache` 只在同一 pytest 行程內共用 ⇒ 本 Task 之重型 gate 於**同一 `run_watched` 子命令、同一 pytest 行程**列齊 Task 3.2（BUDGET-7）之 4 個 nodeid 與本 Task 之 3 個 nodeid；I1 收尾重型批以此合併命令取代分別執行 I1F 與 I1F2 兩 gate（manifest `TESTSEL_I1F2.json` gate_cmd 為唯一收尾命令）。施工首步先於 `test_numview_core.py` 建此 3 個重型 nodeid 之紅樁（`pytest.fail`，不取 fixture），使 gate 於施工前可收集。
- **邊界**：①NaN 位置一致（含 Ratio 窗未滿前 251 列）；②Ratio 分母遮罩四分支與尺度中位數奇偶兩路徑（快速單元以真實 STOCHRSI 逐一命中）；③非主週期 4h（重型，依 Task 3.2 強制串行）；④Cross「得 0 而真值非 0」只入 (iii)、不判定。
- **存活至**：永久。　**覆蓋風險**：(iii) 為產品 D-L2 精度選擇之影響面，新收據三方簽核時判讀；改不改屬產品精度決策（`pandas_to_polars(use_float64=True)` 會改 L5／L6 輸入、須重凍），不屬本 Task。
- 不可做：不改產品碼與契約；不改 Polars 臂輸入精度；oracle 不得 import `momentum` 或呼叫產品遮罩／尺度函式；不寫正式 data_cache；不置入或改寫任何真實觀測值；不放寬既有斷言與 NaN／inf 閘（§C）。
- 範圍外（§N）：配對集合規則（哪些欄成對）之獨立重推；Distance、Momentum 等其餘 L2 算子之值 oracle；尺度「窗內全無⇒0」路徑（真實資料 0 列、對輸出無可觀測影響）。

### Phase 4 — main 既有紅 63 條與分類單一真相源（依賴：Phase 1）
**Task 4.1 — 紅之逐條處置（allowed_red 單一真相源）**
- 目標：main 既有 63 條逐條修或登記。處置單一真相源＝既有 `tests/_golden/prered/allowed_red.json`（精確集合由 `tests/governance/test_prered_allowed_red.py` EXPECTED 釘死、owner 已完成由 `scripts/testreg.py` `signal_allowed_red_owner_closed` 標出）；登記列之原因、驗證之樹與收尾者寫於該列 `trigger`（`reason` 為封閉值），已修者之漂移原因寫於提交訊息；`runs/testsel_route/i1d/i1d_table.md`（gitignore 之 `runs/`）為非契約之工作筆記。（2026-11-17 I1d1 修訂：原定另建 `runs/testsel_route/i1_reds.json` 與檢查腳本，與既有登記表職責重複，不建；原因落點改為版控檔。）
- 初判（原型，逐條施工前須再查證）：測試過時（`test_meta_features` 3＝FF-NAME 欄名、`test_feature_factory_optimization_e2e` 6＝`ent_`／`ms_` 前綴族已由 category 段取代 `momentum/FeatureEngineering/feature_naming.py:20`、`test_preprov_acceptance` 1＝變異現被產品 `ProvenanceError` 更早擋、`test_memory_chunking` 5＝NUMVIEW windows 政策）；資料缺件（`data_cache/numview_postic_core_runs/20261024T065025Z/outputs/pandas_optimized__chunked__a` 不存在 ⇒ 依使用者「資料不足就要補齊」重生）；釘值／行號漂移（`test_probewinsor` 20、`test_ichc_p2_golden`、`test_icperf_gate`、`test_ic_persist_redirect_inventory`）——每條改前須查證漂移原因，釘值改動走 §G 與三方簽核。
- 範圍另含：整合分支 `tests/_golden/prered/allowed_red.json` 中 `owner_ticket` 為 TESTSEL 之既有登記（2026-11-17 `jq '[.[] | select(.owner_ticket=="TESTSEL")] | length'` 實查 30 條）——TESTSEL 收案後即無此 owner，每條須修後自登記移除，或改歸實際負責之產品票（owner 與 `為何現在不做: blocked-by:…|user-ruling:…`）；收案時 owner＝TESTSEL 之條目數須為 0。
- **驗證（可證偽）**：I1 收尾全量須正常結束，collection 與 setup／teardown ERROR＝0；原紅中宣稱已修之 node 於同次全量 outcome＝passed（非 skipped／xfailed／deselected）；失敗 nodeid 須為 `allowed_red.json` 之 node 子集（全量 summary 之 FAILED 行與 `jq -r '.[].node'` 比對，差集為空）；`allowed_red.json` 中 `owner_ticket=="TESTSEL"` 之條目數 == 0；移交他票之列附 `為何現在不做`。mutation：`test_prered_allowed_red.py` 既有精確集合比對——增刪一列而未同改 EXPECTED ⇒ 紅。
- **邊界**：①測試過時但產品值未經獨立 oracle 比對 ⇒ 修測試同時補 oracle 斷言（如 entropy 欄值以獨立算法驗）；②資料重生改變凍結值 ⇒ 三方簽核。
- **存活至**：I1 收案。　**覆蓋風險**：無。
- 不可做：不以放寬斷言換綠；不整批改釘值。

**Task 4.2 — owner TESTSEL 之定案後死碼測試退役（大綱 I1g）**
- 目標：`allowed_red.json` 中 owner TESTSEL 之 28 列歸零：①`tests/feature_engineering/test_numview_core.py` 落選分支測試 27 條（21 函式）——NUMVIEW 決定紀錄（`tests/_golden/numview/decisions.json`）d_mtf／d_memmap／d_winsor_dtype／d_codec／d_l2 皆 `retain`，落選臂（provenance／unify／decouple）於 `momentum/`、`api/` 無實作，`_require_decision` 使其永紅；②`tests/feature_engineering/test_failopen_frozen_diff.py`（範圍 `d654237..HEAD`）——同斷言之限定範圍版已存在 `tests/feature_engineering/test_failopen_matrix.py` `test_v8_frozen_doc_covers_every_existing_assertion_change`（範圍至 FAILOPEN 結案提交 `e4228777`），收案後之測試斷言變更由 TESTREG V19／V20 逐提交審。依據 `runs/testsel_route/i1g/i1g_facts.md`。
- 改法（I1g 審 r1 改寫，`handoffs/reconcile/20261118-testseli1g-x-review-r1/synth.md`）：①NUMVIEW 21 個落選分支函式（27 nodeid）**不刪**——刪除會使 `tests/feature_engineering/test_numview_criteria.py` 之凍結判準檢查（`mutant_rows_violations`、`_path_registry_ledger_violations`：`preregistered_criteria_v9.json` 所列 mutation_test 須存在、錨點上下文須於現行碼恰一次）轉紅；改為各函式加收集期條件跳過 `pytest.mark.skipif(nh.decision(<key>) != <該分支值>, reason=…)`（pytest 官方條件跳過；reason 載決定鍵、選定值與「落選分支未實作」），於 fixture 建立前生效；函式本體 `_require_decision` 保留；決定紀錄日後改選該分支即自動恢復執行。②刪 `test_failopen_frozen_diff.py` 整檔（範圍至 HEAD 恆紅、與限定範圍版重複），並刪 `tests/registry/catalog.json` 之該檔條目、`docs/TESTREG_SPEC.md` §N R14 註記此條改由本 Task 刪除（限定版保留）。③`allowed_red.json` 刪 28 列、`tests/governance/test_prered_allowed_red.py` EXPECTED 同步刪 28 列。提交產生之測試刪改待審清單（新增 skipif 於 V19 視為斷言歸零、刪檔為 V20）由委員逐條審、`scripts/test_change_review.sh mark` 後放行；不假造 TESTREG 收據。
- **驗證（可證偽）**：①jq 計 `allowed_red.json` 中 `owner_ticket=="TESTSEL"` 之列數 ⇒ 0；②`pytest tests/governance/test_prered_allowed_red.py` 通過（EXPECTED 與登記表精確集合相等）；③以原 27 個 nodeid 執行 `pytest -rs` ⇒ 27 skipped、0 failed／passed／error，每條 reason 含其決定鍵；④`test_failopen_matrix.py::test_v8_frozen_doc_covers_every_existing_assertion_change` 通過；⑤`test_numview_criteria.py::test_estimate_b4_mutant_generations_listed_and_costed`、`::test_estimate_path_registry_closed_and_complete`、`::test_boundary_06_criteria_unchanged_after_receipts_defect_recorded` 通過（判準檢查不受影響）；⑥`git diff -- tests/feature_engineering/test_numview_core.py` 只含 skipif 裝飾（與必要之 import）之新增行、無刪除行，`ruff check --select F821,F811` 通過。mutation：任一 skipif 條件改為恆假 ⇒ ③ 該條 failed；只刪 allowed_red 列不加 skipif ⇒ ③ 27 failed。
- **邊界**：①retain 分支測試（函式名含 `_retained` 之 11 條等）與 helper 不改；②`docs/manifests/NUMVIEW.json`、`decisions.json`、`preregistered_criteria_v9.json` 為已收案票之紀錄，不改。
- **存活至**：永久。　**覆蓋風險**：落選分支函式與其專用 helper 留存於檔（死碼）；v8 由限定版與 TESTREG V19／V20 涵蓋。
- 不可做：不改 NUMVIEW 決定紀錄與判準檔；不改 retain 分支測試；不以本體內 `pytest.skip` 代替收集期 skipif（本體跳過會先建重型 fixture）；不以 xfail 代替。

**Task 4.3 — V07 改寫登記殘留之逐目標已審處置（大綱 I1h）**
- 目標：`tests/registry/catalog.json` 中 disposition＝rewrite、無改寫收據、而已被 testsel 提交改動之 3 檔使提交之測試變更清單恆附 V07：`tests/feature_engineering/atomic/test_handcoded_reference.py`、`tests/feature_engineering/preprocessing/test_fast_adf_gate.py`（2a7b378e）、`tests/performance/test_memory_pressure.py`（003d1da3）。依據 `runs/testsel_route/v07/v07_facts.md`：infrastructure_repair（目標檔須零差異）與 additive_rewrite（舊函式須一字不動）皆不成立；handcoded 之 mutation 收據結構上不可能（目標函式之期望值以 8 根 bar 算 talib EMA34／55 恆為全 NaN）。
- 改法：依 `docs/TESTREG_SPEC.md:198` Task 4.4（v53，使用者 2026-10-17 業界裁定：逐目標已審處置、不再要求逐目標收據）——①列處置表 `handoffs/run_receipts/testsel-i1h-dispositions.tsv`（逐目標：處置、理由、驗證 nodeid 與結果；置於施工樹自身之 `handoffs/run_receipts/`，以 `git add -f` 入版控〔同 I1d1 收據先例〕，gate 以 repo 根相對路徑驗）；②`test_handcoded_reference.py::test_klinger_kvo_ema_from_golden_vf`（空心目標）依 Task 4.4 刪除——其意圖（KVO 之 EMA 段）已由同檔真實資料獨立 oracle 測試覆蓋（`v07_facts.md` 所列 9a30f621 新增者）；③三檔 entry 改 `disposition=keep`、`rewrite_targets=[]`、`rewrite_receipt=null`、`disposition_ref` 指本項審碼收斂檔；claim／guarantee／oracle／ticket 不動；舊 additive 收據檔保留作歷史證據。`test_fast_adf_gate.py` 目標函式「未掛 requires_kline」登為後續修正候選（處置表列，不在本項改）。
- **驗證（可證偽）**：①`venv/bin/python scripts/testreg.py validate` 之輸出中，指名本項三檔之違規列只得為「V20 …test_klinger_kvo_ema_from_golden_vf」（預期之刪除，走清單審）——施工實跑（2026-11-18）顯示 validate 於整合樹恆非零（既存 V07 timeout_registry、他項未提交之 V02／V19），「rc=0」不可達，故以過濾判定（`bash runs/testsel_route/v07/validate_filter_probe.sh` ⇒ 正例 rc=0；三檔出現 V07、V19 或其他 V20 之反例皆 rc=1）；②三檔全部 nodeid 執行通過（被刪之空心函式除外），覆蓋 handcoded 之 oracle 測試 outcome＝passed；③其後任一提交改動此三檔不再產生 V07 行（以本項提交之測試變更清單驗：只得有 V20 刪空心函式 1 行與既存 timeout 行）；④處置表每列之驗證 nodeid 於②之結果中為 passed；⑤三筆 entry 終態以 jq 機械斷言（`disposition=="keep"`、`rewrite_targets==[]`、`rewrite_receipt==null`、`disposition_ref`＝本項審碼收斂檔）——`testreg.py validate` 不檢此一致性（I1h 審 r1 三家指出），故入 manifest gate_cmd，並含空心函式已刪與處置表存在。mutation：entry 改 keep 而保留 `rewrite_targets` 非空、或任一筆仍為 rewrite ⇒ ⑤ rc=1（`bash runs/testsel_route/v07/jq_gate_probe.sh` 已實跑：current rc=1、good rc=0、bad_targets rc=1、bad_disp rc=1）。
- **邊界**：①catalog 其餘 disposition＝rewrite 之 entry（W 現 `jq '[.entries[] | select(.disposition=="rewrite")] | length'` ⇒ 65，含本項 3 檔）不在本項範圍（未被 testsel 改動；日後被改動時同法處置）；②不改三檔任何其他測試函式。
- **存活至**：永久。　**覆蓋風險**：handcoded 空心函式刪除後其意圖由 oracle 測試承擔（處置表附其 nodeid 與 passed 紀錄）。
- 不可做：不假造 mutation／additive 收據；不改 claim／guarantee／oracle；不擴及其他 rewrite entry。

## §V 驗證策略與邊界測試目錄
- mutation：各 Task 已列；Task 1.1／1.4／3.2 之 mutation 為必跑。
- 測試層級：單元（pytester 隔離偵測）、整合（依序重放）、Golden（§G）。
- 防假綠：diff 既有斷言；釘值改動須附漂移原因與獨立 oracle；不 skip／xfail。
- 邊界目錄：並發寫（Task 1.1）、符號連結根（Task 1.1）、空快取／命中快取（Task 3.2）、Ratio 分母遮罩四分支與非主週期 4h（Task 3.3）、長行程狀態（Phase 2）、網路失敗（Task 1.6）。

## §R 回退
- 每 Phase 獨立提交可單獨 revert；Task 1.1 改為 session 非零若誤擋並行正式寫入，可單獨 revert 該提交回到只報；Task 1.6 以備份還原。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- 殘留：產品碼 `data_cache` 字面路徑未經 `MomentumConfig.data_cache_path`（Rule 5）— `為何現在不做: blocked-by:I1 範圍為測試隔離；改產品預設路徑屬跨模組改動（命中 b），須另開票走大任務流程`；觸發：I1 收案時開票；登記處：`docs/ROADMAP.md` pointer。
- 殘留：治理測試依賴未入版控之本機檔（約 92 條）— `為何現在不做: blocked-by:大綱 I7（治理分層）已定義`；觸發：I7 開工；登記處：大綱 I7 列。
- 殘留：testsel 推送前之測試變更清單（E13 遺留 19 份）——fc38ec98 之 51 條 V19 須逐條矩陣（檔×nodeid×{等價拆分｜加強｜放寬}，源於 testsel 7a9ca3e1 之 S3 計時斷言拆分，main 無對應已審標記）、2a7b378e 兩條 V07 與 I1d1 tests/performance/test_memory_pressure.py 之 V07 須以 `scripts/testreg.py` 產 TESTREG 收據（2026-11-18 實查 `runs/testsel_route/v07/v07_facts.md`：infrastructure_repair 與 additive_rewrite 皆不成立 ⇒ 改依 Task 4.3〔大綱 I1h〕逐目標已審處置、entry 改 keep；`scripts/test_change_review.sh:39` 之 mark 只記錄委員已審清單、不驗收據）— 逐條矩陣部分已完成（E13 r2 三家零 finding、19 份已 mark，`handoffs/reconcile/20261118-testsele13-b1-review-r2/synth.md`）；V07 三檔 `為何現在不做: blocked-by:Task 4.3〔大綱 I1h〕審查與施工進行中`；觸發：I1h 提交並經清單審 mark；登記處：`runs/testsel_mon/TESTSEL_REMAINING.md`。
- 殘留：L2 多數算子無獨立值 oracle（Distance、Momentum、BinarySignal、SignedStrength、WorldQuant 9 子算子；分母遮罩之尺度中位數已移入 Task 3.3 尺度值測試；格 C 43,394 格差只比過兩臂；`runs/testsel_route/i1f/l2_oracle_scope.md`）；另含配對集合規則（哪些欄成對）之獨立重推（Task 3.3 之 oracle 由輸出欄名反推配對、只驗每欄值）— `為何現在不做: blocked-by:大綱 I1f2（Task 3.3 定 Cross／Ratio 之 oracle 方法與判準輸入精度，施工中），其餘算子沿用同方法另立產品驗值項`；觸發：I1f2 提交；登記處：`runs/testsel_mon/TESTSEL_REMAINING.md`。
