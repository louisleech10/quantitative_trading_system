# Reconcile — 20261001-icpostleak-b1-review-r1

**來源** 20261001-icpostleak-b1-review-r1-codex.md, 20261001-icpostleak-b1-review-r1-composer.md, 20261001-icpostleak-b1-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/manifests/ICPOSTLEAK.json

三家 proceed、無 P0／P1。codex 兩條 P2 皆為實質缺項，主委採納並修補（第 1 批補提交，r2 由 codex 以原反例閉合）：①時間序檢查改相鄰直接比較並把 NaT 視為違規（`time_order.py`），新增 `nat_after_valid`／`nat_first` 兩例，以改前 `np.diff` 寫法為 mutant 兩例皆紅；②產出 Task 1.1 量級收據 `handoffs/run_receipts/20261002-icpostleak-branch-diff.json`（`probe_change_report.py branchdiff`，42 對、不排除格、legacy 為 0 之格另列）。收據顯示 SPEC §N 殘留「各分支 zscore 數值核心不一致」之觸發條件（最大相對差 > 1e-3）成立：主委定位（`probe_branch_diff_locate.py`）差異來源為 float32 輸入之 rank 同值（2 格、一階）經低 std 窗放大，及 registry 之 float32 累積式 zscore 核心對價位級輸入之精度損失（單步 zscore 最大 0.038、p99 0.009；與改前逐格相同，非本批引入）；registry 帶 zscore 之組合經生產分派不可達（pre-IC 與 L7 raw 設定強制關 rank／zscore／gaussian）。殘留之處置交 r2 三家共識。codex 另指盤點收據 sharded 進入條件之誤述（審碼正文未查 1），已更正收據文字。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| NaT 漏擋：時間序檢查會接受「有效時間戳→NaT」之 | P2 | CODEX-R1-P2-01 | 採納（直接比較＋NaT 違規；兩新例＋mutant 紅；r2 閉合） | code-contract |
| 量級收據缺：Task1.1要求的「各分支對legac | P2 | CODEX-R1-P2-02 | 採納（branch-diff 收據已產；殘留觸發成立，處置交 r2） | code-contract |
| 放行：本輪對SPECv4／manifest／` | P3 | COMPOSER-R1-P3-00 | 採納（proceed） | other |
| 放行：本輪逐項核對後無finding；SPEC | P3 | GROK-R1-P3-00 | 採納（proceed；其量測邊界所提收據缺項與 codex 第二條同，已併處） | other |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P2-01

**斷言**: 時間序檢查會接受「有效時間戳 → NaT」之非嚴格遞增 DatetimeIndex，因 int64 差分溢位而漏擋。

**碼證**: `momentum/FeatureEngineering/preprocessing/time_order.py:20-23` 使用 `np.diff(index.asi8) <= 0`。隔離複本實跑 `env PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe_edges.py` → rc=0，`NAT_ACCEPTED False [7519304836854775808]`；False 為 pandas `is_monotonic_increasing`，正差分為溢位後值。probe 輸入為真實 kline 第一個時間戳與 `pd.NaT`，檢查函式正常返回。

**類別**: code-contract

**來源摘要**: momentum/FeatureEngineering/preprocessing/time_order.py#a10b5b85f88a;docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9

可重現序列：`idx = pd.DatetimeIndex([pd.Timestamp('2020-01-01', tz='UTC'), pd.NaT]); assert_strictly_increasing_time_index(idx, where='probe')`。NaT 的 asi8 值為 int64 最小值，減去現代正時間戳後溢位成正值；本函式是 transform／transform_selected 共用之新 gate。建議沿用現有檢查函式，直接相鄰比較而不相減，並把 NaT 視為違規位置；不用新增機制。probe 已實算 `np.flatnonzero(idx.isna() | np.r_[False, idx.asi8[1:] <= idx.asi8[:-1]])`，真實輸入＋NaT 回 `[1]`，輸出 `DIRECT_COMPARISON_FIX [1]`。0／1 長度之既定例外仍可保留。此反例為非法索引漏擋，未證明正常生產資料存在 NaT 或造成某個有限歷史值受未來改動，故列 P2，不升格為已證實之未來洩漏。

## CODEX-R1-P2-02

**斷言**: Task 1.1 要求的「各分支對 legacy」數值量級收據尚未交付，現有改前／改後收據不能替代該比較。

**碼證**: `docs/ICPOSTLEAK_SPEC.md:49` 明列 `icpostleak-branch-diff.json` 的最大絕對差、最大相對差與差異格數；`:100` 的殘留觸發依賴該量級。實跑 `rg --files handoffs/run_receipts | rg 'icpostleak|icpl'` → 清單無 branch-diff；`docs/manifests/ICPOSTLEAK.json:24-55` 的 run_receipts 只有三份初始探針、oracle-unmasked 與 change-report。`handoffs/run_receipts/icpostleak_probes/probe_change_report.py:40-70` 比較的是同一 case 的 before／after，JSON 也沒有對 legacy 之相對差欄。

**類別**: code-contract

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9;docs/manifests/ICPOSTLEAK.json#eef794fc1fa6;handoffs/run_receipts/20261002-icpostleak-change-report.json#597ce3a60deb

這是已定 SPEC 的交付缺項，非要求跨分支統一數值。建議以已通過之 49 組真實輸入輸出，逐組與同開關 legacy 比較，產出既定三個指標與 NaN／有限位置之比較邊界，附命令／rc；接近零分母之相對差須明示，不以排除格或放寬容差掩蓋。現有 35／14 分流只能說明改前到改後之變化來源，無法判定 §N 原定觸發。未把此資料交付缺項當成已證實之新數值缺陷。

### 必答 (1a)／(1b)：逐 Task

(1a) 生產實作主要行為符合，尚不能宣稱 SPEC／manifest 交付完整：Task 1.1 缺跨分支量級收據，Task 1.2 有 NaT 邊界漏擋。兩者見本輪 P2。

(1b) Task 1.1：`stable_mask.py:215` 的新純函式以輸入首 finite＋window−1 遮前綴，形狀檢查、全 NaN、超長窗及空陣列處理均在函式內；`feature_preprocessor.py:2171` 統一四個 registry 快速呼叫點，順序為 rank→gaussian→zscore，三步各遮；`:2827`、`:2848`、`:2872` 為 optimized，`:3009`／`:3033` 為 Polars，`:3965`／`:4009` 為 legacy gaussian／zscore。49 個 branch×combo oracle node 全過；append 兩臂及 chunked node 全過，另補開 rank 的 append 四組獨立 oracle 全等。

Task 1.2：`feature_preprocessor.py:602` 與 `:674` 在 transform／transform_selected 的時間索引入口呼叫 gate；倒序、重複、單點亂序及合法時間序四個 node 全過。registry 儲存的是無 DatetimeIndex 的 ndarray，native 路徑 `:1236` 也建立 RangeIndex；不能把這些入口描述成已驗證了原始 timestamps 的時間序。L7 raw 時間軸另票之既定範圍未在本輪重開；NaT 漏擋見 P2-01。

Task 1.3：三檔既有測試之 commit diff 已逐處核對，沒有新增 skip／xfail、放寬 atol／rtol 或刪掉後段數值比較。凍結清單／斷言數及 skip／xfail 檢查兩個 node 全過。主委的 18 檔 171 passed／2 既有 failed、五項 identity mutant 全紅是 brief／收據所載，非本家重跑；實作 brief 只有總結，沒有逐列重印 18 檔處置。本家未重跑耗時的 18 檔全套，沒有把該兩項既有紅稱為本批新缺陷。

Task 2.1：`momentum/factories.py:236` 組正式 config；`ic_analysis_service.py:2886` 去重、`:2918` 排序主窗、`:2923` 經 factory 取得前處理器並呼叫 transform_selected；三個開關照正式順序回報。七組合因果與同參數正式輸出共 14 node 全過；排序、去重、缺欄、全關、長窗及 mutants 補跑通過。`:2949` 後 HDF5 落盤／attrs 語意未改。

Task 2.2：`ic_analysis_service.py:2897-2911` 排除及全排除 ValueError，`:2985` 填新選填欄；`ic_models.py:451` 只新增回應選填欄。`ApplyTransformsResult.tsx:23` 以 `?? []` 相容缺欄，`:34` 非空才列欄名與原因；hook 與 page state 有型別。本家 vitest 3 passed。build 為主委已驗證事實，本家未重跑已知 checkout 大小寫問題之完整 build。

### 必答 (2a)／(2b)：洩漏與窗未滿

(2a) 對本輪實測真實 kline 及既定入口，沒有重現未來洩漏或窗未滿即出值；沒有作跨所有市場、任意索引與完整 ML 鏈的無條件保證。NaT gate 漏擋已獨立列 P2。

(2b) `_real_frame` 真實 BTCUSDT 1h 前 3000 根 close／volume＋EMA21／RSI14／ATR14＋晚生欄；Phase 1 四臂末列擾動、Phase 2 七組合末列×50之 node 全過，前 2999 列與原輸出 exact array equality（equal_nan=True）。49 組逐步 oracle 與整數首 finite 期望全過。補 probe 的 rank append：legacy／Polars 各 100、252 窗；原 close 的首 finite 是 99／251，rank-derived close 為 350／502，晚生欄是 499／651 與 750／902，四組全陣列與獨立遮罩 oracle 全等。沒有縮小比较區段或增加 tolerance。

誠實邊界：現有測試用 `np.array_equal(..., equal_nan=True)`，這是數值及 NaN 位置精確全等，沒有驗 NaN payload 或 signed-zero 的原始 byte 等同；本家沿用既定測試，沒有宣稱另外做了原始 bytes 掃描。

### 必答 (3a)／(3b)：三項 assumed 與五個未查面

(3a) ①在已交付收據和現行逐步 oracle 的範圍成立；②已讀的核心不新增 float64→float32 語意縮減，未實跑整個下游 ML；③成立。

(3b) ①change-report 的 49 例／35 identical／14 changed 與實作分支一致：只有 registry 的含 zscore／改序及原切片漏 gaussian 會改後段。現行全部 49 case 對原數值核心＋獨立遮罩的 oracle 通過，沒有看到第四種漂移；未獨立重生改前 baseline。②`_numba_transforms.py:31-55` 的 rank 本來直接輸出 float32、`:126-133` 的 rolling mean／std 與 `:465-491` 的融合 zscore 本就 float32 原地運算；`feature_preprocessor.py:3949` 的 gaussian 原來也返回 float32，helper 各步回存未新增更低精度。跨分支量級仍缺收據，不能由此推論分支值相等。③`feature_preprocessor.py:604` 原入口仍以 `_is_ratio_unsafe_column` 丟欄；factory `ratio_unsafe_category` 委回該單一判定，本家混入 unsafe、全 unsafe、重複 unsafe、無 unsafe 的服務 node 全過。

未查 1：`feature_preprocessor.py:1629` 在 gaussian apply_to 非 all 判 requires_slow，`:945-950` 的 can_shard_stream 明確排除 requires_slow，故合法部分欄設定不會進新 helper 的拒絕臂；`feature_factory.py:2973`／`:2982` 的生成設定還關掉 gaussian。盤點收據稱「原 sharded 入口只看 can_use_numba_fast」與現有分派完整條件不符，本輪以程式碼判斷可達性，未重跑完整 FF 批次。

未查 2：transform_selected 的 group_df index 是主軸，對合法嚴格遞增的多週期 ffill 合併軸不會誤擋；native registry 路徑用 RangeIndex 不走該 gate。此為碼證及合法時間序 node，不是本家重新生成多 TF 之實跑。

未查 3：`api/routes/ic_analysis.py:770-773` 把 ValueError 映射 400；probe_edges 對真 route coroutine 注入全排除 ValueError 後取得 `ALL_UNSAFE_HTTP 400`，原服務全排除 node 另行通過。`page.tsx:477-478` 會 setError，訊息由後端 detail 經 requestJson 傳回；未跑瀏覽器點擊。

未查 4：ApplyTransformsResult 的 `?? []` 與 vitest 缺欄案例通過，原摘要繼續渲染，未提供 excluded_features 的舊後端相容。

未查 5：`:4028-4049` 每個 zscore window 各用同一次步驟輸入遮罩；原 append nodes 與本家補 rank 四組全等，窗 100／252 錨點獨立成立。

### 必答 (4a)／(4b)：既有測試是否弱化

(4a) 沒有發現為通過本批而放寬既有數值驗收；更新主要限於新遮罩語意。native warmup 的舊方向性斷言退役為新的暖身下界，不等同繼續驗旧 native>legacy，但該關係被本批遮罩改變的理由成立。

(4b) `git show 95487b67 -- tests/feature_engineering/preprocessing`：l65_v2 `_expected_zscore` 加測試端獨立輸入錨點遮罩，constant window 前兩列 NaN／後段 zero 均驗；single_then_trend 與 nan_prefixed 早值更新，完整 allclose 保留且 tolerance 未改。ff_causal_golden 640→1000 列以保留遮罩後有限樣本，expected gaussian 加獨立遮罩，有限值前提與後段比較保留。native_tf_real_eth 原 1h prefix 279–359、12h prefix 440–520 改為三步遮罩下界 597–677／564–644，寬度各仍 80；原 native>legacy 已不能成立，改驗各自下界，steady-state NaN 位置相等未刪。本家 boundary_08／09 兩測試與 identity／錯錨／錯窗／append漏遮等 mutants 通過；主委五項既有測試 identity mutant 的完整動態結果未本家重跑。

### 必答 (5a)／(5b)：第 1 批

(5a) 生產改動可放行：沒有可重現之 P0／P1；本輪兩項 P2 仍為實質缺項，不能把逐 Task 回答中的未完成項標成已驗收。停輪依據為真實 oracle、因果擾動、append 補驗、mutants 的正反鑑別力及前端相容通過，不是只因「無阻擋 finding」。

(5b) 擋收第 1 批之 P0／P1：none。

### 實跑紀錄與界線

所有產品實跑 cwd 為 `/tmp/review-4d45/work`，先呼叫複本 `_isolate.isolate()` 與 `isolate_dstar_cache(root)`，NUMBA_CACHE_DIR 在自身 workdir；真實 H5 複製至複本後使用，原 data_cache 未寫。測試單組串行，前端使用原 node_modules 唯讀連結，Vite cacheDir 指向本次 tmp。未改任何產品／測試／SPEC／manifest 或 git 狀態。

- `env PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python run_review.py` → rc=0，82 passed／22 warnings，32.55s。pytest node 選擇：Phase1 stepwise oracle 全參數、append、registry chunked append、causal perturb、時間序正反、boundary08／09；Phase2 perturb、formal equality、ratio unsafe／all unsafe、boundary13。
- 同直譯器／環境執行 `probe_edges.py` → rc=0；rank append legacy／Polars×100／252 四組全等，NaT 漏擋與直接比較候選成立，真 route 全排除錯誤映射 400。
- 同直譯器／環境執行 `run_mutants.py` → rc=0，25 passed／97 deselected／13 warnings，5.92s。pytest 對兩 ICPOSTLEAK 檔以 `-k 'mutation or zscore_window_order_insensitive or selected_features_deduplicated or boundary_10 or boundary_11 or boundary_12 or boundary_14 or boundary_15 or response_model'` 選跑；沒有篡改測試本體。
- 複本 frontend：`/Users/louis/Desktop/quantitative_trading_system/frontend/node_modules/.bin/vitest run src/components/ic-analysis/ApplyTransformsResult.test.tsx --config review.vitest.config.ts` → rc=0，1 file／3 tests passed，745ms；設定沿用正式設定，只把 cacheDir 指到自身 tmp。
- 主樹 `git status --short -- momentum api frontend scripts tests docs templates config` 前後檔比較 → cmp rc=1；差異只有原來 dirty 的 docs/ROADMAP.md、scripts/fact_keys.json 兩列消失。期間 HEAD 可讀到主委看板同步提交 3611050f；本家未寫／還原這兩檔，不能聲稱最後狀態逐字相同，其餘產品與既有 cache 髒檔清單相同。

ASSUMPTIONS_VERIFIED: 上列 82＋25 Python nodes、4 append oracle 與 route probe、3 vitest；assumed②限核心 dtype 碼證，完整 ML 未驗證；改前收據未獨立重生。
TESTS_RUN: run_review.py rc=0；probe_edges.py rc=0；run_mutants.py rc=0；vitest rc=0；status cmp rc=1（兩個原 dirty 列消失，非本家寫入）。
FAILURES_SEEN: NaT 非單調索引被接受為本輪 P2 觀測；狀態比較 rc=1 如上；無測試失敗後修補／放寬斷言。
SCOPE_CHANGES: none；本家主樹僅新增指定交件，實跑僅 /tmp 複本。
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查，未改產品數值／schema／輸出大小）。
HANDOFF_NOT_UPDATED: 本輪唯讀，依 AGENTS 規則不另寫狀態交接；根 HANDOFF.md 未改。
產出: handoffs/20261001-icpostleak-b1-review-r1-codex.md

交件檢查：`bash scripts/completeness_check.sh --single handoffs/20261001-icpostleak-b1-review-r1-codex.md --family codex --round-id 4d45deef-1ff6-418f-8768-055d2ee7d2e6` → rc=0，`COMPLETENESS PASS(single)`，2 個 canonical ID。
最後範圍檢查：status-after 與 status-final 的 `diff -u` → rc=0，與上述第一次比較的兩列消失之外沒有額外變動。
清理：`rm -r /tmp/review-4d45` → rc=0；`test ! -e /tmp/review-4d45 && test -d /tmp/claude-501` → rc=0。934MB 本次 workdir 已清除，claude-501 保留；其他程序／其他家族的 workdir 未動。

VERDICT: proceed
BLOCKED-BY:
CLOSED:
## COMPOSER-R1-P3-00

**斷言**: 本輪對 SPEC v4／manifest／`95487b67`＋`47ba1d3e` 全面審碼（後端、前端、測試、收據）後，未發現意外漂移或未修之未來洩漏／窗未滿公開輸出之 P0／P1；brief 攻擊面與 assumed ①②③ 經讀碼與 gate 實跑可支持收批。

**碼證**: `venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py tests/api/test_icpostleak_api.py tests/api/test_ic_la1_degraded_gate.py -q --tb=no` → 150 passed rc=0；`handoffs/run_receipts/20261002-icpostleak-change-report.json` summary 35 例 suffix 全同／14 例 registry 預期差異；`grep -c "rank → zscore → gaussian" api/models/ic_models.py api/services/ic_analysis_service.py api/routes/ic_analysis.py` 各 0；mutant 節點列於 `tests/api/test_icpostleak_api.py`／`test_icpostleak.py`（全樣本排名、gaussian 最後、excluded 不填等）與 §V 對齊。

**類別**: other

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9;handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R1-BRIEF.md#cd65652dc7fb;tests/feature_engineering/test_icpostleak.py#63eb345468c0;tests/api/test_icpostleak_api.py#ae628e582d76;handoffs/run_receipts/20261002-icpostleak-change-report.json#597ce3a60deb

正文：已排除面（SPEC／TODO r1–r8 設計）未重審。主委事實 1（180 passed 擴展節點）本輪以 manifest `gate_cmd` 子集 150 passed 複驗核心契約；事實 2 之 2 failed 對照 brief 為 CGSA／tier 既有紅，不擋 ICPOSTLEAK 收批。registry `apply_to != all` 改 fail-closed 屬實作 brief 已記之既有缺陷修補，非新洩漏。

---

ASSUMPTIONS_VERIFIED: Phase 1/2 commits 存在且與 brief EXPECTED-DELTA 一致；kline 探針收據路徑存在；主委事實 1 gate 子集 150 passed；change-report 35+14 分類與 JSON 一致；R1 decoupling grep=0。  
TESTS_RUN: `venv/bin/python -m pytest tests/feature_engineering/test_icpostleak.py tests/api/test_icpostleak_api.py tests/api/test_ic_la1_degraded_gate.py -q --tb=no` → 150 passed in 96.77s rc=0；`grep`／`git show --stat` 靜讀驗證（見必答 1b）。  
FAILURES_SEEN: none（未重跑 18 檔全量與 2 項既有紅）。  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none（審碼未改碼；實作已新增選填 `excluded_features` 為預期）  
產出: `handoffs/20261001-icpostleak-b1-review-r1-composer.md`

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

STATUS: DONE
## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding；SPEC v4／manifest 五 Task 在 `95487b67`＋`47ba1d3e` 落地，IC 頁與正式後處理之未來洩漏與窗未滿公開輸出已由輸入錨點遮罩與正式 `transform_selected` 關閉，brief assumed ①②③與「我沒查」1–5 經隔離探針與具名測試成立。

**碼證**: 隔離探針 `env PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/qts-icpl-b1r1/numba PYTHONPATH=/tmp/qts-icpl-b1r1 venv/bin/python /tmp/qts-icpl-b1r1/probe.py` rc=0，先 `isolate()`＋`isolate_dstar_cache()`。真實 kline 3000×2。`LEAK_GAUSSIAN_PREFIX_EQ True prefix_diff_cells 0`；`GAUSSIAN_FIRST_FINITE [251, 251]`；`SVC_GAUSSIAN_EQ_FORMAL True`；`ALL_UNSAFE_HTTP 400`；`L65_DROPS_UNSAFE True`；append 窗 100／252 首有限值 99／251；`CAN_SHARD_PARTIAL False` 且直接呼叫快速路徑 `FAST_PARTIAL_RAISED True`；假合併重複時間戳 `TS_MERGED_DUP_RAISED True` 於位置 100；change-report 14 例分類 `UNEXPLAINED []`、identical 列 `IDENT_NONZERO_ROWS 0`。複本 pytest 4 passed in 6.96s rc=0（rootdir `/private/tmp/qts-icpl-b1r1`）。具名函式集 83 passed in 28.65s rc=0。`grep` 全樣本排名與舊序三檔皆 0；`from api.` 於 momentum 0。

**類別**: other

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9;docs/manifests/ICPOSTLEAK.json#eef794fc1fa6;handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R1-BRIEF.md#cd65652dc7fb;tests/feature_engineering/test_icpostleak.py#63eb345468c0;tests/api/test_icpostleak_api.py#ae628e582d76;tests/_golden/icpostleak/contract.json#43860a11061d;momentum/FeatureEngineering/preprocessing/stable_mask.py#613f6f5be2ea;momentum/FeatureEngineering/preprocessing/feature_preprocessor.py#f8086a000344;api/services/ic_analysis_service.py#7805bf12650e;api/routes/ic_analysis.py#dda0361cda66;momentum/factories.py#7c35e4b103dd;frontend/src/components/ic-analysis/ApplyTransformsResult.tsx#41c3a562aca7;handoffs/run_receipts/20261002-icpostleak-change-report.json#597ce3a60deb;handoffs/run_receipts/20261002-icpostleak-branch-inventory.txt#ed57763b37bd

量測邊界（不另立 finding）：manifest `coverage_risk` 所列 `20261002-icpostleak-branch-diff.json` 本批未產；跨分支核心差異仍登記於 SPEC §N needs-research。本輪以 change-report 之 35 例 0 格差與逐步驟 oracle 為通過條件。

---

ASSUMPTIONS_VERIFIED: 輸入錨點遮罩關閉 gaussian 未來洩漏與窗未滿公開值；IC 頁輸出＝`transform_selected`；registry 14 例差異可三原因重現；float32 回存與舊融合出口相容；ratio-unsafe L6.5 丟棄／IC 頁明示排除；sharded 於 gaussian apply_to 非 all 不走快速路徑；時間序對合法單調通過、對重複合併 fail-closed；append 各窗獨立遮罩；前端缺欄 `?? []`。
TESTS_RUN: `/tmp/qts-icpl-b1r1/probe.py` rc=0 `ALL_PROBES_COMPLETE`；複本 pytest 4 passed in 6.96s rc=0；具名函式集 83 passed in 28.65s rc=0。
FAILURES_SEEN: none。
SCOPE_CHANGES: none（唯讀；探針僅 `/tmp/qts-icpl-b1r1`）。
NUMERIC_OR_SCHEMA_IMPACT: none（審碼未改碼；實作已新增選填 `excluded_features` 為預期）。
產出: `handoffs/20261001-icpostleak-b1-review-r1-grok.md`
HANDOFF_NOT_UPDATED: 本輪 brief 唯讀，依 AGENTS 7 不另寫狀態交接；根 HANDOFF 未改。
WORKTREE_CHECK: `git status --short -- momentum api frontend scripts tests docs templates config` 相對開跑快照少 `M docs/ROADMAP.md` 與 `M scripts/fact_keys.json` 兩列（本家未改該二檔；其餘 dirty 列與開跑時一致，含既有 numba cache／golden l65）。

VERDICT: proceed
BLOCKED-BY:
CLOSED:
