# PRE-RED：既有紅測試逐支歸因與修正＋允許仍紅名稱集合 — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 2 步；`handoffs/20261003-ticketorder-prework-steps2-4.md`；`handoffs/run_receipts/20261003-fkperf-govsuite.json`　|　日期：2026-10-03　|　對應 TODO：`docs/manifests/PRERED.json`
> 版本：v6（實作期修正，待審碼輪一併審：Task 1.1 改為「現行入口＋靜態器掃 W 版量化測試檔」——v5 之函式層篩選經實跑推翻〔12 支 W 時即存在之 truncation MR mutant 於 W 後被改寫為委派 helper 而遭啟發式誤判〕；Task 3.1 參數化節點以實際收集之參數 id 列）；v5（主委依實測更新，待下一輪審查：多週期於 `d229336e` 後本機受 F-2 擋——單獨執行亦被看門狗於磁碟剩 3.3 GB 時終止——改列 blocked-by F-2、重凍限單週期四單元；寫入多週期至 `d229336e^` 之分段收據與 BTCUSDT/12h 消融結果〔U＝0〕；新增發現 F-3；審查 r4 因磁碟滿致 codex 交件失敗、帳本未記結果而卡債，待使用者裁定）；v4（審查 r3 `handoffs/reconcile/20261003-prered-x-review-r3/synth.md` 三條全數採納：C2 之 reference 依賴域須已驗——上游欄為 C1-full（全 ingest 窗）或遞迴已驗 C2，否則 U；新增負控制 mutant③；探針交付物明列 C1-public／C1-full／C2／C3／U 與 summary.U）；v3（審查 r2 `handoffs/reconcile/20261003-prered-x-review-r2/synth.md` 六條全數採納：Task 2.0 消融改為「舊版同公開起點、只注入 L0 載入起點」之可執行步驟並斷言兩版公開時間戳相等、C2 改綁同一產物之獨立 reference、Task 1.1 mutant③ 改為 W 時已存在函式改空心、manifest 之 coverage_risk 與 SPEC 同步）；v2（審查 r1 `handoffs/reconcile/20261003-prered-x-review-r1/synth.md` 十五條全數採納：基準切片改用生成時之原生時間軸並驗公開窗逐元素相等、新增 Task 2.0 重凍前歸因補全（多週期分段＋L2–L6 消融歸類）、v7 補「續跑不重算已完成週期」觀測、F-2 改列資源安全缺陷並新增 Task 2.5 分段量測、重凍可重現性改兩次全新生成之確定性投影、Task 1.1 改名出口、l1_direct 兩 oracle 不等之明文、允許仍紅集合改精確集合、manifest 補兩種驗收模式與約束）；v1（主委起草；歸因收據全數於 `handoffs/run_receipts/20261003-prered-attribution.json`，探針於 `handoffs/run_receipts/prered_probes/`）

## §RISK 風險分級
- **大小**：中（`docs/TICKET_ORDER.md` 定案）。不改 `momentum/`、`api/`、`frontend/` 生產碼；只改測試、測試輔助、凍結工具 `scripts/freeze_failopen_baseline.py` 與凍結基準檔、允許仍紅集合。
- **命中高風險原則**：(a) 數值／資料品質——fail-open 凍結基準 `tests/_golden/failopen/baseline.json` 為 FF 數值回歸之 oracle，重凍即改 oracle；(d) ML 正確性——後續 FRAMEPATH／FF-NAME／PRE-PROV／FFSTORE 以本票之基準與允許仍紅集合判回歸。
- RISK-HIT: a,d

## §A 假設與待使用者確認
- **已驗證事實**（逐條收據彙整於 `handoffs/run_receipts/20261003-prered-attribution.json`；`<S>`＝主委 scratchpad）：
  - FACT-RECEIPT: `venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_mutation_scope_extension.py::test_true_positive_i_quant_fatal_set_is_the_named_12 tests/governance/test_todofmt_sample_fftfmeta.py tests/governance/test_todofmt_constitution_sync.py::test_step1b_no_new_exception_clause_outside_allowlist` → 印出 `12 failed, 8 passed in 3.15s`（主委 實跑 2026-10-03，HEAD `c89f32de`）。首紅 commit 沿用 FKPERF 收據之 worktree 對照與 `git bisect`：`3adc84d9`（1 項）、`5156d074`（10 項）、`7cdbca15`（1 項）。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/l1_segments.sh <S> d829754a 04176c18^ 04176c18 2247c394^ 2247c394 d229336e^ d229336e HEAD` → BTCUSDT/12h 直跑 L1 canonical：`d829754a`～`2247c394^`＝`b092a651`（＝凍結值；`04176c18` 不變）；`2247c394`～`d229336e^`＝`cb398514`；`d229336e`～HEAD＝`4f457390`（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/full_at_commits.sh <S> d829754a 2247c394^ 2247c394 d229336e^ d229336e HEAD`（`_single_tf_record` 本體）→ BTCUSDT/12h 之 L1–L6、final_L7 七雜湊於 `d829754a` 七項全等於基準；改變點只有 `2247c394` 與 `d229336e`；L5 恆不變。同腳本 `PRERED_SYMBOL=ETHUSDT PRERED_TF=1h` → 同兩改變點、L5 恆不變（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/prered_probes/full_coldiff.py <S>/full_d6de3ba6.json <S>/full_2247c394.json 'BETA|CORREL|Klinger|ForceIndex'`（BTCUSDT/12h；ETHUSDT/1h 同）→ L1–L4、final_L7 各層改變欄之 `changed_not_matching_pattern`＝0；L1：18 欄 `close-volume_statistics_{BETA,CORREL}_*` → `hl_statistics_*`、`hlcv_volume_Klinger_34_55` 數值、`hlcv_volume_ForceIndex` 首值列 1→13；L6 不變（主委 實跑 2026-10-03）。⇒ `2247c394` 之改變完全落在深稽 BUG-1／BUG-2 修正範圍（三方簽核）。
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/prered_probes/l1_prefix_only.py <S>/l1_1cbc93f4.npz <S>/l1_d229336e.npz`（直跑 L1）→ `identical 138, prefix_mask_only 601, added_nan_total 68145, violations 0`（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/prered_probes/l1_tolerance.py <S>/dump_L1_1cbc93f4.npz <S>/dump_L1_d229336e.npz`（全量 run 之 L1；新版 registry 末 731 列對舊版 731 列；只比兩邊皆有限之格）→ 逐欄最大相對差 p90：輸出窗前 1/4＝0.28、中 1/2＝0.0012、末 1/4＝7.8e-7；末 1/4 > 0.005 之 18 欄＝`close-volume_volume_OBV`、`hlcv_volume_AD`（累積型）與 144／233 週期遞迴型（CMO、TRIX、TEMA、ADX、ADXR、MINUS-DM、DEMA、DX、ATR、NATR）（主委 實跑 2026-10-03）。⇒ 差異沿窗遞減，為舊版自輸出窗首列冷啟動之未收斂；屬 FF-STAT 第 4 批「預熱恆開」之已核准行為改變。
  - FACT-RECEIPT: `full_suffix.py`（`d229336e`）→ registry 群組列數 1695＝預熱 964＋輸出窗 731；凍結腳本 `_single_tf_record` 以 `raw = _layer0_data_ingestion(start, end)`（731 列）之 index 呼叫 `_hash_registry_table`，而該函式讀 `registry.load_data_native` 全部列 ⇒ 雜湊涵蓋預熱列、`rows` 卻報 731（主委 實跑 2026-10-03）。⇒ 凍結工具之單週期雜湊範圍於 FF-STAT 後過期；預熱深度依記憶體探測定案（`feature_factory.py` `_resolve_public_window`），含預熱列之雜湊於不同機器可不同。
  - FACT-RECEIPT: `l1_segments.sh` HEAD 直跑 L1＝`4f457390`；`full_at_commits.sh` HEAD 全量 run 之 L1＝`02ae6fa3`（主委 實跑 2026-10-03）。⇒ contract 兩支以直跑路徑比對基準之全量 L1，於預熱恆開後兩者必不等；單純重凍不能使其綠。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/light_at_commit.sh <S> 28596e1e^ tests/api/test_batch_alias.py::test_patch_batch_alias_deleting_returns_409` → `1 passed`；同 `28596e1e` → `1 failed`（主委 實跑 2026-10-03）。`28596e1e` 使 `FeatureRegistry.get` 對 deleting 條目回 None（`feature_registry.py:196-201`），另有 `get_internal`（:203-206）。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/bisect_light.sh <S> 935b24fd c89f32de tests/test_cgsa_resume.py::test_cgsa_config_hash_passed_correctly` → `04176c18 is the first bad commit`；`04176c18` 單跑 → `AttributeError: 'types.SimpleNamespace' object has no attribute …`（主委 實跑 2026-10-03）。HEAD 單跑 → `check_l1_warmup_coverage(config)`（`feature_factory.py:279`）之 `config.atomic_indicators` AttributeError。
  - FACT-RECEIPT: `bisect_light.sh <S> 67c4f28e 5a148b8e tests/feature_engineering/test_failopen_correctness.py::test_v7_cgsa_resume_matches_fresh` → `cb53ff19 is the first bad commit`；`node_at_commit.sh` 於 `3d26adda`（`cb53ff19^`）→ `1 passed`、於 `cb53ff19` → `AssertionError: CGSA resume_from_manifest was not invoked`，log `[CGSA] Skipping resume … L7 run_status=partial`（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/v7_seed_at.sh <S> 3d26adda|cb53ff19`（重現 v7 種子 run：12h＋1h、14 天、persist）→ 兩版 `result.metadata` 皆 `partial`；L7 `feature_manifest.json` 之 raw `quality_status`：`3d26adda`＝`complete`、`cb53ff19`＝`partial`（`failure_reasons: ["nan_ratio=0.178736601689>max_nan_ratio=0.16346106472"]`）（主委 實跑 2026-10-03）。⇒ 種子 run 本即品質 partial；`cb53ff19` 修正「L7 manifest 與 run 結果不一致」後續跑閘依 `consumer_gate.is_run_status_cacheable`（只 `complete`）拒絕。
  - FACT-RECEIPT: HEAD 種子 run（同上設定）`/usr/bin/time -l` → 1h 週期 `92617 cols × 20329 rows ≈ 7.53 GB → disk-backed`、`peak memory footprint 29027358608`、程序被系統終止（rc=1，無 traceback）；改 12h＋4h → 完成、`quality_status partial`（`warmup_insufficient_history:111`）、peak footprint 27.5 GB、1135 秒；改精簡 L1（EMA8、SMA13，同 `tests/feature_engineering/ff_artifact_compare_helpers.fast_config_payload`）、L2–L4 預設、12h＋1h → `complete`、33.7 秒、peak footprint 0.65 GB（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/multi_at_commits.sh <S> d829754a 2247c394^ 2247c394 d229336e^`（`_multi_tf_record` 本體，BTCUSDT 12h＋1h）→ merged_L7／group_set／feature_count：`d829754a`＝`b74e57c3`／`8852c5ad`／181173（＝凍結值）；`2247c394^` 同；`2247c394`＝`cf1e912c`／`46b1b6fe`／181158；`d229336e^` 同（主委 實跑 2026-10-03，每點約 590 秒）。⇒ 多週期至 `d229336e^` 只有 `2247c394` 一個改變點；特徵數少 15 之逐欄歸因列 Task 2.0。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/watch_run.sh <S>/watch_multi_d229336e.log -- … multi_record.py`（`d229336e`，單獨執行、無委員並行）→ 1h 自最早資料起算（20329 列×92617 欄，memmap 7.53 GB），換頁檔升至 18.1 GB、磁碟剩 3.3 GB 時看門狗終止（rc=143，最後完成段＝合併第 5／5 段）（主委 實跑 2026-10-03）。⇒ 本機（8 GB）於 `d229336e` 之後無法完成多週期凍結單元；屬 F-2。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/ablation_pair.sh <S> BTCUSDT 12h`＋`ablation_c2.py`＋`ablation_c3.py`＋`c3_lowcard.py`（消融，SPEC v4 Task 2.0 步驟）→ C1-full 82479、C1-public 1445（皆 L3）、D 6042（皆 L3：Mean 3552、Kurt 749、Std 569、ZScore 567、Skew 443、Slope 162）→ C2 6042、U 0（向量化 reference 與 `_l3_oracle` 逐格對照 5 欄一致）；only_old 1743（新版無）＝dead_reasons 1462（nan_rate_rule 1353、stable_samples_below_min 88、constant 21）＋低基數閘 281（上游非 NaN 相異值 0 或 1）；only_new 0；L1、L2、L4、L6 全 C1-full。負控制：改壞產物一欄 ⇒ 該欄 U；改壞上游前史一格 ⇒ 依賴該上游之 8 欄 U（主委 實跑 2026-10-03）。兩段式（尾段雜湊）流程 `ablation_big.sh` 於同單元逐項重現上列計數。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/ablation_big.sh <S>/abl_<T> <sym> <tf> <S>`（`ablation_c2.py` 之 Kurt 界改為與 `_l3_oracle` 逐字同式之相對容差並於邊界窗以 scipy 逐窗重算後）→ ETHUSDT/12h：C1-full 82530、C1-public 1181、C2 6263、U 0、only_old 1740（dead_reasons＋低基數 281，U 0）；ETHUSDT/1h：C1-full 74812、C1-public 818、C2 16137、U 0、only_old 4（皆有 dead_reasons）；BTCUSDT/1h：新版生成於合併第 5／5 段被系統終止（rc=137，F-2，1h 自 2019 起之全史預熱）（主委 實跑 2026-10-03）。修正前 ETHUSDT/1h 之 9 欄（MIDPOINT／MIDPRICE Kurt）判 U，經 `c2_inspect.py` 以測試原版 `_l3_oracle` 重算：新版與原版 0 格不符，差異只在主委向量化 reference 之界判式（絕對 1e-9 vs 原版相對 1e-9）——屬探針缺陷，已修並重驗遮罩逐格一致。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/multi_cols_pair.sh <S>`（多週期 L7 逐欄，`2247c394^` vs `2247c394`，看門狗包住）→ 舊 181173 欄／新 181158 欄；只舊 4968、只新 4953、數值 268、遮罩 268、型別 119，**全部**屬 BETA|CORREL|Klinger|ForceIndex 家族（範圍外 0）（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `quality_probe.py BTCUSDT 12h`（HEAD，凍結腳本之 365 天健康設定、persist）→ L7 `resolve_run_status`＝partial，`failure_reasons: ["warmup_insufficient_history:5239"]`（主委 實跑 2026-10-03）。⇒ 「生產 max_nan_ratio 門檻凍於 FF-STAT 前而過期」之疑點不成立（nan_ratio 未觸發）；但證實 F-1：含 12h 深週期之正常 run 恆 partial。
  - 審查 r1 實查：`OutputWindow.ingest_start`（`momentum/FeatureEngineering/warmup_window.py:291-314`）為生成時主週期之 L0 載入起點；`_output_row_slice`（`feature_factory.py:859-864`）只依傳入 index 定位 ⇒ 以公開窗 index 求切片會得 `slice(0,731)` 而切到預熱段首 731 列（codex 座標探針：完整 ingest index 得 `slice(964,1695)`）。
  - 審查 r1 實查：`test_v7_cgsa_resume_matches_fresh` 之現行斷言（續跑命中次數、canonical hash、group 集合、feature_count）於「續跑後仍全部重算」時仍可全過；跳過已完成週期由 `MultiTFGenerator._has_resume_checkpoint_for_timeframe`（`multi_tf_generator.py:152`）決定。
  - 宣告——IC 兩路涵蓋：本票不改 IC 路徑；**全域序列型**／**事件型**皆不涉及（僅 FF 測試與基準）。
- **待使用者確認**：fail-open 凍結基準重凍（Task 2.4 之重凍步驟）——使用者 2026-10-03 指示「刻意修正導致基準要重凍的，先帶證據問我」；核可前不執行，Task 2.4 之其餘步驟與其他 Task 照常。**重凍批准包**（向使用者提出時必附，缺一不提）＝①Task 2.0 之多週期分段收據；②Task 2.0 之 L2–L6 消融歸類收據（未解釋欄＝0）；③本 SPEC §A 之單週期分段與 `2247c394` 逐欄收據；④Task 2.4 ①② 完成後未重凍狀態下 6 支之失敗分量對照。
- **已確認結果**（2026-10-03 使用者指示與既往使用者裁定）：
  - `2026-10-03 使用者`：「照 docs/TICKET_ORDER.md 的順序與完整管線做…逐支判斷是『測試前提過期』還是『程式真的錯』再修；刻意修正導致基準要重凍的，先帶證據問我」；同日「我先睡了，有問題你跟委員共識決定」。
  - `2026-10-02 使用者`：全票排序定案；「到該票時再問：…failopen 基準重凍」列於 FF-NAME。本票之重凍為既有兩次改變（`2247c394`、`d229336e`）之追認，與 FF-NAME 改名後之重凍為不同兩次。
  - `2026-09-28 使用者`：刪除 frame 產生路徑、不再花時間於 frame 測試。
  - `2026-09-26 使用者`（FF-STAT v19）：某欄湊不滿 N 只該欄不平穩化＋標記＋整批 partial。

## §C 約束
- 不改 `momentum/`、`api/`、`frontend/` 生產碼。
- 防假綠：不得刪除或放寬斷言換綠；每處改寫須於 commit 訊息與各 Task 之驗收欄列出「原斷言所守之性質＋改寫後仍守之 mutant」；不新增 skip／xfail。
- 基準只能由凍結腳本本體產生，禁手改 JSON；重凍收據列出各分量舊值→新值，並逐項對應 §A 之歸因。
- FF 重測試單組串行，`-o log_cli=false --log-level=WARNING`；真實 kline `data_cache/feature_klines/kline_cache.h5`；不得並行跑兩組。
- 錨點取版本一律由 git 內容機械推導（`_todofmt_anchor`、`git log` 之規則），不得在測試內寫死 commit sha。

## §G Golden／Baseline
- 現行基準：`tests/_golden/failopen/baseline.json`（凍結 `bbb44533`／`d829754a`；環境 commit `f1714e49`；窗 2025-04-27～2026-04-27；kline sha256 `b1ee5b9a…`，與現檔相同）。探針於 `d829754a` 重現 BTCUSDT/12h 與 ETHUSDT/1h 之全部七雜湊 ⇒ 探針即凍結腳本本體之忠實重放。
- 重凍（Task 2.4，使用者核可後）之通過條件：①以 HEAD 之凍結腳本本體產生；②新舊基準之每一差異分量，皆落在 §A 與 Task 2.0 之逐欄歸類內（`2247c394`：`changed_not_matching_pattern`＝0；`d229336e`：消融後每欄屬 Task 2.0 之封閉類別，未解釋欄＝0）；③可重現性：於 HEAD 以 `--no-resume` 對兩個獨立輸出目錄（各自全新工作目錄）各凍結一次，**確定性投影**逐位元組相同——投影＝每生成單元之各層與 final／merged 之 `canonical_sha256`、五分量 sha256、`rows`、`columns`、`groups`、`nan_count`、`cell_count`、`index_metadata`、`group_set_sha256`、`feature_count`、`config_hash`、`artifacts` 之資料檔 sha256；排除 `perf` 全部欄位與絕對路徑字串（`merged_L7_source.manifest_path`／`raw_path`／`feature_run_dir`），排除項另存收據；④mutant：把 `hl_statistics_BETA` 之輸入改回 `(close, volume)` ⇒ `test_l1_baseline_hash_matches_frozen` 與 `test_layer_golden_matches_baseline` 紅；把 L3 一個滾動統計輸出乘 1.01 ⇒ `test_layer_golden_matches_baseline` 紅。

## §P Phase 與依賴

### Phase 1 — 治理既有紅 12 項（依賴：無）
**Task 1.1 — mutation 靜態名單快照（首紅 `3adc84d9`）**
- 目標：`tests/governance/test_mutation_scope_extension.py::test_true_positive_i_quant_fatal_set_is_the_named_12` 只比對 TODOFMT 定案時已存在之測試。　檔案：同檔。既有 caller：無（入口依 `docs/TODOFMT_SPEC.md:219` 只手動呼叫）。
- 判定：測試前提過期。其後 FF-TFMETA／FF-STAT 新增之 mutation 測試把動作委派給共用 helper（`run_control_*`、`h.dual_start_report`、golden helper `g.*`），靜態啟發式看不到 monkeypatch 或待測符號而列入 fatal；此名單依該檔 docstring 為「現行啟發式之 fatal 名單，不是空心探針」。
- 改法（v6，實作期修正）：以**現行**入口 `scripts/mutation_scope_static.sh` 與靜態器，掃「W（`_todofmt_anchor.effective_commit()`）時之量化三層測試檔」所組之隔離 mini repo（`git ls-tree` 列出 W 樹中 `tests/momentum`／`tests/api`／`tests/feature_engineering` 之 `.py`，取含 `def test_mutation_` 者之 W 版內容）；斷言量化層集合等於 `QUANT_FATAL` 且 `len(QUANT_FATAL) == 12`。治理層（`test_true_positive_ii_…`）現綠，不動。v5 之「W 存在函式或屬 QUANT_FATAL」篩選經實作實跑推翻：12 支 W 時即存在之 `test_mutation_*`（`test_ff_fullchain_truncation_mr.py` 七支、`test_ff_multitf_truncation_mr.py` 五支）於 W 後被 FF-STAT（`d3c8d339`、`ab94ec28`）改寫為委派 `run_control_*` helper（helper 內有 `monkeypatch.setattr`，屬真探針），靜態啟發式誤判 ⇒ v5 篩選仍紅（收據 `handoffs/run_receipts/prered_probes/task11_extras.py`）。
- **驗證**（v6）：`pytest tests/governance/test_mutation_scope_extension.py` 整檔綠；mutant①「靜態器 `mutation_probe_static.py` 之 fatal 列印改為不印」⇒ 集合為空而紅；mutant②「入口不掃 `tests/momentum`」⇒ 紅（收據 `handoffs/run_receipts/prered_probes/task11_mutants.py`）。W 之後之新增、改名、重構與「HEAD 上函式被改空心」皆不在本快照之職責內——HEAD 上之靜態偵測力由同檔 `test_boundary_02`／`04`／`05` 之 mini repo 情境承擔。
- **邊界**（v6）：①W 樹中無含 `def test_mutation_` 之量化檔 ⇒ 集合空而紅；②`effective_commit()` 為 None ⇒ fail-closed（斷言失敗）；③HEAD 上 W 時之測試被改名或刪除 ⇒ 不影響本快照（輸入取 W 版）。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得改 `scripts/mutation_probe_static.py`；不得把新名稱抄進 `QUANT_FATAL`。

**Task 1.2 — FF-TFMETA 樣本 manifest（首紅 `5156d074`；10 項）**
- 目標：`tests/governance/test_todofmt_sample_fftfmeta.py` 驗 TODOFMT Task 3.2 之樣本版，而非其後之正式施工清單。
- 判定：測試前提過期。`5156d074` 起 `docs/manifests/FFTFMETA.json` 由 TODOFMT 樣本（`spec_path`＝`docs/FFDEFECT_DECISION.md`、`callers_now`＝[]、測試標「（待 FF-TFMETA 新增）」）改為 FF-TFMETA 正式施工清單（`spec_path`＝`docs/FFTFMETA_SPEC.md`、`callers_now` 5 條）。
- 改法：樣本版之取得規則＝`git log --format=%H -- docs/manifests/FFTFMETA.json` 中最新一個 `spec_path`＝`docs/FFDEFECT_DECISION.md` 之 commit（現值 `738b05d9`）；結構斷言讀該版內容；「宣告之測試存在 ⇔ 未標待新增」之判定改對該 commit 之樹（`git show <c>:<path>`）。`test_manifest_passes_template_check_todofmt` 與 gate 路由兩支仍指工作樹（現綠）。
- **驗證**：整檔綠；mutant「取版規則改為取最新 commit」⇒ 10 項紅；既有 `test_declared_test_truthfulness_discriminates` 保持綠。
- **邊界**：①找不到符合規則之 commit ⇒ fail-closed（AssertionError 說明）；②該版之 `coverage_risk` 行數不等於四情況＋五等式 ⇒ 紅。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得改 `docs/manifests/FFTFMETA.json`；不得刪任一斷言。

**Task 1.3 — `.cursorrules` 第 12 條例外條款（首紅 `7cdbca15`）**
- 目標：`tests/governance/test_todofmt_constitution_sync.py::test_step1b_no_new_exception_clause_outside_allowlist` 綠。
- 判定：測試前提過期（規則依設計觸發）。該條款於 L 已存在；`7cdbca15` 只把句尾「逐字理由見 `AGENTS.md:40`」改為「理由全文見 `AGENTS.md`「執行任務時」第 12 條」，語意與適用範圍不變；整行改寫故成相對 L 之新增行。
- 改法：依步驟 1b 之裁決出口，把該行之 sha256 加入 `tests/governance/fixtures/constitution_exception_allowlist.txt`，上一行註解寫出處 commit 與本票審查輪。
- **驗證**：`pytest tests/governance/test_todofmt_constitution_sync.py` 整檔綠；mutant「白名單移除該雜湊」⇒ `test_step1b_no_new_exception_clause_outside_allowlist` 紅；mutant「該行再改一字」⇒ 同測試紅。
- **邊界**：①舊行（`AGENTS.md:40` 版）不得加入白名單；②白名單只增此一列。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得改關鍵詞 regex；不得改 `.cursorrules`。

### Phase 2 — 特徵工廠既有紅（依賴：無；Task 2.4 之重凍步驟依賴 Task 2.0 與使用者核可）
**Task 2.0 — 重凍前歸因補全（多週期分段＋`d229336e` 之 L2–L6 消融歸類）**
- 範圍（v5）：單週期 BTCUSDT/12h、ETHUSDT/12h、ETHUSDT/1h 三單元完整消融（收據見 §A，U＝0）；BTCUSDT/1h 單元與多週期兩單元之 `d229336e` 歸因與重凍於本機受 F-2 擋（§A：BTCUSDT/1h rc=137、多週期看門狗收據）⇒ `為何現在不做: blocked-by:F-2 修復（全票排序第 4 步 ICFIRSTALIGN 乙 MEM-RSS）或 RM-FULLSCALE 大記憶體機器`；多週期至 `d229336e^` 之分段與 `2247c394` 逐欄歸因之收據見 §A。BTCUSDT/1h 單元不被任何既有測試斷言，其基準記錄原樣保留。
- 目標：凡要被重凍改寫之基準分量，逐欄有可證偽之來源類別；未解釋欄＝0 才可組重凍批准包。　檔案：`handoffs/run_receipts/prered_probes/`（探針）、`handoffs/run_receipts/<日期>-prered-attribution-l2l6.json`、`handoffs/run_receipts/<日期>-prered-attribution-multi.json`。既有 caller：無。
- 改法：①多週期：完成 `multi_at_commits.sh` 六點，判定與單週期同法（凍結 commit 重現基準、改變點、逐欄 `full_coldiff` 樣式）。②消融（可執行步驟）：(1) 於 `d229336e` 生成（`start_date`／`end_date`＝凍結窗），收據記錄 `OutputWindow` 之 `ingest_start`、`output_start`、`output_end`、`max_warmup_bars` 與公開窗時間戳；並另存**全列**（含預熱）之上游欄值供 C2 參考實作；(2) 於 `d229336e^`（`1cbc93f4`）之隔離複本，`generate_features` 之 `start_date`／`end_date` **與新版相同**（公開起點），設 `FFACT_WARMUP_TRIM=1`，並把 `feature_factory` 模組內之 `resolve_output_window` 替換為回傳 `OutputWindow(ingest_start=<收據值>, output_start=<收據值>, output_end=<收據值>, max_warmup_bars=<收據值>, warmup_enabled=True)`，使舊演算法以同一 L0 載入起點計算；**禁止**把 `start_date` 改成 `ingest_start`；(3) 兩邊皆斷言 registry 列數＝同起點 L0 ingest index 列數，兩邊 ingest 時間戳逐元素相等（任一缺 ⇒ 拋錯），公開窗以時間戳逐列對齊；兩版皆輸出**全 ingest 窗**（含預熱列）之逐欄值；(4) 逐欄比對。逐欄封閉類別：**C1 預熱**＝新版有限之格與消融值逐位元組相同，且新版多出之 NaN 只在其首個有限值之前——判定域分兩級：`C1-public`（只公開窗）與 `C1-full`（全 ingest 窗）；**C2 具名演算法變更**＝消融後仍不同，且通過**綁定同一份產物之獨立參考實作**：以新版全 ingest 窗之上游值、該欄之窗與遮罩，用測試端獨立 reference（沿用 `tests/feature_engineering/test_ffstat_stable_start.py` 之 `_l3_exact_checks`／`_slope_checks` 所用之 reference 算法；分母因果化以 SPEC FF-STAT 之定義獨立重算）重算該欄之公開窗值，與新版待判值依該 reference 測試之同一判準相符，且有限值位置相同；**且 reference 實際讀到之每一上游時間格（含公開窗前之依賴列）須已驗**：該上游欄為 `C1-full`，或其本身為依同法驗過之 C2（依賴順序遞迴至 L0），否則該下游欄為 U；欄名只用於選 reference，不構成判定；無對應 reference 之欄 ⇒ U；**C3 欄集合**＝只單側存在之欄，逐欄附 L3 剔除原因（新版之 L3 aggregator 剔除記錄與 `_l7_dead_reasons`）；**U 未解釋**＝其餘。探針交付物（本 Task 之實作）：`ablation.py` 輸出全 ingest 窗逐欄值與時間戳；`ablation_classify.py` 輸出 `C1-public`／`C1-full`／`C2`／`C3`／`U` 逐欄判定與 `summary.U`，C2 逐欄附 reference 名稱與上游依賴之判定。
- **驗證**：收據之 `U` 計數＝0；mutant①「於新版待判產物把一個具名 L3 mean／std／slope 欄之有限值乘 1.01（欄名與 NaN 遮罩不變）」⇒ 該欄 C2 參考比對失敗而落入 U；mutant②「舊版不注入視窗、沿用其自然預熱」⇒ (3) 之列數或時間戳斷言拋錯，或 U 增加（不得歸 C1）；mutant③（負控制）「於新版收據把一個 `C1-public` 上游欄、位於公開起點前且落在某具名 L3 mean 第一個公開窗內之一格乘 1.01，並以改壞之上游重算該 mean 之受影響公開值」⇒ 該上游欄不再為 `C1-full`，該 mean 落入 U；所沿用之 reference 對應之 FF-STAT 測試（`test_ffstat_stable_start.py::test_l3_rolling_exact_and_start_independent`、`::test_l3_slope_exact_and_start_independent`、`::test_l3_slope_fallback_path_exact_and_start_independent`）於 HEAD 實跑 `pytest` 綠，作為 reference 本身之對照。
- **邊界**：①`U` 非 0 ⇒ 不組批准包，該欄具名回報並交委員判定是否為缺陷；②registry 列數≠同起點 ingest index 列數 ⇒ 探針拋錯（不靜默取末 N 列）；③兩版公開時間戳不等 ⇒ 拋錯。
- **存活至**：收據永久保存。**覆蓋風險**：無。
- 不可做：不得以容差吸收 C1 判定（C1 只認逐位元組相同）；不得以 commit 定位代替逐欄歸類。

**Task 2.5 — F-2 資源安全缺陷之分段量測與修復歸屬**
- 判定：**程式缺陷**（資源安全），非測試前提過期：12h＋1h、14 天窗之 `generate_features` 於 8 GB 本機被系統終止，未 fail-closed（審查 r1 codex）。
- 改法：於隔離複本以原設定重播 `v7_seed_manifest.py`，以 RSS 取樣記錄 `_resolve_public_window`（校準域讀取）、各週期 L1–L6、memmap 合併、L6.5、L7 各段之峰值與 footprint；產 `handoffs/run_receipts/<日期>-prered-f2-memory.json`。修復落點＝全票排序第 4 步 ICFIRSTALIGN 乙之 MEM-RSS（「證明漏擋才改閘」，本收據即漏擋證明），其驗收寫入該票：原設定須完成，或於超出記憶體預算前以具名錯誤 fail-closed；被系統終止不算通過。
- **驗證**：收據含各段峰值與終止點；`docs/ROADMAP.md` RM-ICFIRSTALIGN 與 HANDOFF 待辦列出本收據與上述驗收字面（`grep -c prered-f2-memory docs/ROADMAP.md` ≥ 1）。
- **邊界**：①量測本身被終止 ⇒ 收據記錄最後完成之段與當時 RSS；②不得以精簡設定之結果代替原設定。
- **存活至**：收據永久；修復於第 4 步。**覆蓋風險**：無。
- 不可做：本票不改 `momentum/` 生產碼；不得把 F-2 寫成測試前提過期。

**Task 2.1 — alias 409（首紅 `28596e1e`）**
- 判定：測試前提過期——`28596e1e` 起公開 `get` 隱藏 deleting 條目。改法：`tests/api/test_batch_alias.py:283` 之 `registry.get(...)` 改 `registry.get_internal(...)`，斷言該條目存在且無 `batch_alias`。
- **驗證**：綠；mutant「`FeatureRegistry.set_batch_alias` 刪除 deleting 檢查」⇒ 紅（409 斷言或 alias 斷言）。
- **邊界**：①條目確實存在（`get_internal` 非 None 為前置斷言）；②`get` 仍回 None（另一行斷言公開隱藏行為）。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得改 `feature_registry.py`。

**Task 2.2 — resume config_hash（首紅 `04176c18`）**
- 判定：測試前提過期（stub 不全）——`04176c18` 起 `_prepare_cgsa_registry` 之前之輸出窗解析、其後之預熱覆蓋檢查與校準關卡讀取 config 其他欄位。改法：`tests/test_cgsa_resume.py:126` 之 `SimpleNamespace` 改為 `feature_factory._resolve_config(<training=["1h"] 之最小 override>)` 之真實設定；其餘 stub（hash、cache、prepare、layer0）不變。
- **驗證**：`pytest tests/test_cgsa_resume.py` 整檔綠；mutant「`_generate_features_impl` 傳空字串給 `_prepare_cgsa_registry`」⇒ `test_cgsa_config_hash_passed_correctly` 紅。
- **邊界**：①`start_date=None` 路徑（無校準 I/O）；②layer0 被 stub 拋錯前不得讀 kline 以外之資料（以 `FFACT_CGSA_WORK_DIR` 指 tmp 驗不落盤）。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得 stub `check_l1_warmup_coverage` 或 `resolve_output_window`。

**Task 2.3 — v7 resume（首紅 `cb53ff19`）**
- 判定：測試前提過期——種子 run 本即品質 partial（14 天窗 NaN 比例 0.1787 > 0.1635），`cb53ff19` 之前 L7 manifest 誤記 complete，續跑閘因而放行；`cb53ff19` 修正後如實記 partial，續跑閘依「只 complete 可續跑」拒絕。另 `d229336e` 後原設定之 1h 全史預熱使本機記憶體不足而被終止。
- 改法：v7 之 `config` 改為精簡 L1（EMA8、SMA13；L2–L4 維持預設；12h＋1h；14 天窗）；新增前置斷言「種子 run 之 L7 manifest `resolve_run_status` 為 `complete`」（使日後品質變動以明確訊息現形）；**新增觀測**：`resume_factory` 之 `_layer1_atomic_indicators` 以與 `_fail_lower_tf` 同法包裝計數（依 `_current_timeframe`），斷言續跑期間 12h 之 L1 計算次數＝0、1h 之 L1 計算次數≥1；其餘斷言（中斷 checkpoint、續跑命中、續跑＝一次跑完之 canonical hash、group 集合、feature_count）不變。完整設定之原輸入另由 Task 2.5 量測（精簡設定不代替之）。
- **驗證**：`pytest tests/feature_engineering/test_failopen_correctness.py::test_v7_cgsa_resume_matches_fresh` 綠且峰值記憶體 < 2 GB（`/usr/bin/time -l` 收據）；mutant①「`consumer_gate.is_run_status_cacheable` 恆 False」⇒ 紅（續跑未命中）；mutant②「`MultiTFGenerator._has_resume_checkpoint_for_timeframe` 恆 False」⇒ 紅（12h L1 計算次數 > 0）。
- **邊界**：①種子品質非 complete ⇒ 前置斷言紅並印 failure_reasons；②中斷 run 之 checkpoint 只含 12h 群組（既有斷言）。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得 stub 品質判定或續跑閘；不得放寬 hash 相等。

**Task 2.4 — fail-open 凍結基準：雜湊範圍、直跑 L1 記錄、重凍（涉 6 支：contract ×2、correctness v3 ×3、layers golden ×1；重凍後必綠者為其中五支單週期，多週期一支歸允許仍紅）**
- 判定：測試前提過期——自凍結起只有 `2247c394`（三方簽核之 BUG-1／BUG-2 修正）與 `d229336e`（FF-STAT 第 4 批，已核准）兩改變點，逐欄歸因見 §A；另凍結工具之單週期雜湊範圍與 contract 直跑比對於 FF-STAT 後過期。
- 改法：①`scripts/freeze_failopen_baseline.py` 之 `_single_tf_record`（生成後）：(1) 取 `window = factory._current_output_window`；(2) `window is not None and window.warmup_enabled` ⇒ 以 `factory._layer0_data_ingestion(symbol, timeframe, config, start_date=window.ingest_start, end_date=<現行 end>)` 取 **ingest index**（＝生成時 registry 之原生時間軸），否則 ingest index＝現行公開 `raw.index`；(3) 每個 group 斷言 `load_data_native(...).shape[0] == len(ingest index)`，不等即拋錯；(4) `row_slice = factory._output_row_slice(ingest index)`，斷言 `ingest_index[row_slice]` 與公開 `raw.index` 逐元素相等；(5) `_hash_registry_table` 增 `row_slice` 參數，只雜湊 `data[row_slice]`，`index` 用公開 `raw.index`；(6) `row_slice is None` 時行為與修前逐位元組相同。②基準增 `single_tf.<sym>.<tf>.l1_direct`：由凍結腳本內新增之函式錄製（鏡像 `tests/feature_engineering/test_failopen_contract.py` 之 `_compute_l1_canonical_sha256` 流程；腳本不得 import `tests/`），contract 兩支改比對之。**`l1_direct` 與 `layers.L1` 為兩獨立 oracle**：直跑 L1 不經公開域預熱，與全量 run 之 L1（預熱後公開窗）可長期不等（§A：`4f457390` vs `02ae6fa3`）；禁止任何驗收要求兩者相等。③凍結 CLI 增 `--out-dir`（預設仍為 `tests/_golden/failopen/`），供 §G ③ 兩次獨立凍結；④Task 2.0 完成且使用者核可後，以 HEAD 重凍單週期 BTCUSDT/12h、ETHUSDT/12h、ETHUSDT/1h 三單元（`--no-resume`；凍結 CLI 增 `--units <sym>/<tf>,…`，未列單元〔BTCUSDT/1h、多週期兩單元〕之記錄原樣保留，基準 `environment` 逐單元記錄凍結 commit）並寫重凍收據；`test_v3_multi_tf_btc_matches_frozen_baseline` 轉為允許仍紅（owner ICFIRSTALIGN，blocked-by F-2）。
- **驗證**：①②③完成後於未重凍狀態，五支單週期基準測試（`test_failopen_contract.py::test_l1_baseline_hash_matches_frozen`、`::test_required_fail_returns_result`、`test_failopen_correctness.py::test_v3_healthy_full_run_matches_frozen_baseline`、`::test_v3_ethusdt_1h_matches_frozen_baseline`、`test_failopen_layers.py::test_layer_golden_matches_baseline`，逐節點明列、單組串行）仍紅且失敗訊息之差異分量與 §A 一致（證明修工具未改變判讀）；④後此五支綠；`test_v3_multi_tf_btc_matches_frozen_baseline` 不在必綠集合——其多週期基準不重凍、於本機受 F-2 擋，依 Task 3.1 列允許仍紅（ICFIRSTALIGN，blocked-by），不改其測試本體、不加 skip／xfail；§G ③④；mutant「步驟 (2) 改用公開 `raw.index`」⇒ (3) 拋錯。
- **邊界**：①預熱未啟用之設定 ⇒ 雜湊與修前逐位元組相同（以 `d829754a` 版設定重放驗）；②registry 列數不等於 ingest index ⇒ 拋錯；③ingest index 切片後與公開 index 有任一元素不同 ⇒ 拋錯。
- **存活至**：永久（FF-NAME 再依其票重凍一次）。**覆蓋風險**：FF-NAME 改欄名會再改 `column_order_sha256`，屬該票之已登記重凍。
- 不可做：不得手改基準 JSON；不得移除任何分量比對。

**Task 2.6 — config_hash 釘值測試（實作期新發現，v6）**
- 判定：測試前提過期。`tests/feature_engineering/test_failopen_producer.py::test_quality_gate_max_ratios_do_not_change_config_hash` 寫死 `1dbe534e…`（＝凍結基準多週期 BTCUSDT 之 config_hash）；config_hash 依設計隨設定結構變動，實跑 `cfghash_at.sh`：`2247c394^`＝`1dbe534e`、`2247c394`＝`ce0f178c`、`5a148b8e`＝`56327766`、`d229336e^`＝`d6d186f1`、`d229336e`＝`2cf3a4cc`、HEAD＝`8c3dcc25`；首個偏離 commit 經 `bisect_cfghash.sh` 定為 `2247c394`。本支不在 HANDOFF 原「FF-STAT 前 9 支」名單（該名單漏列，`5a148b8e` 實跑即紅）。
- 改法：第一斷言（加品質門檻不改 config_hash）不變；釘值改讀凍結基準 `multi_tf.BTCUSDT.config_hash`（並斷言其 primary／training 與本測試設定相同），不再手寫字面值。多週期單元受 F-2 不重凍 ⇒ 本支歸允許仍紅（ICFIRSTALIGN，blocked-by），多週期重凍後自動轉綠。
- **驗證**：`pytest tests/feature_engineering/test_failopen_producer.py` 除本支外全綠；本支之失敗訊息為「HEAD 值 ≠ 基準多週期值」。
- **邊界**：①基準多週期之 primary／training 若被改 ⇒ 前置斷言紅；②字面值不得再出現於本測試。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得移除釘值斷言。

**Task 2.7 — 直跑 L3 存活欄數快照（實作期新發現，v6）**
- 判定：測試前提過期。`test_failopen_correctness.py::test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor` 之 `MTF_12H_L3_SURVIVOR_COUNT` 寫死 65483；`d229336e^` 1 passed、`d229336e` 起 59962（`mtf_count_at.sh`）。逐欄歸因（收據 `handoffs/run_receipts/20261003-prered-mtf-l3-count.json`）：只舊 5524＝dead_reasons 4603（nan_rate_rule 4376、stable_samples_below_min 160、constant 67）＋低基數閘 921（上游非 NaN 相異值 ≤2，逐欄驗）；只新 3（233 期 `Skew_W3`）經 `_l3_oracle` 驗算有限值位置全等、數值 ≤1e-5；未解釋 0。直跑與保型執行逐位元組相同之前段斷言於 HEAD 通過。
- 改法：常數改 59962，註解寫出處與收據；使用者 2026-10-03 已核可以現行算法重新產生標準答案。
- **驗證**：`pytest tests/feature_engineering/test_failopen_correctness.py::test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor` 綠（18.6 秒、峰值 2.18 GB）。
- **邊界**：①L3 剔欄規則再變 ⇒ 本支紅並須附逐欄歸因；②前段位元組相等斷言不得改。
- **存活至**：永久。**覆蓋風險**：FF-NAME 改名不改欄數。　不可做：不得移除數量斷言。

### Phase 3 — 允許仍紅名稱集合（依賴：Phase 1、2）
**Task 3.1 — `tests/_golden/prered/allowed_red.json`**
- 內容：陣列，每列 `{node, owner_ticket, reason, trigger, state}`；`reason` 只准 `blocked-by`／`user-ruling`／`needs-research`；`state` 只准 `pending-approval`／`owned-by-later-ticket`。初始精確集合（10 列，v5 設計）：走 frame 兩支（FRAMEPATH，user-ruling，owned-by-later-ticket）；`tests/feature_engineering/test_b6_warmup_trim.py::test_warmup_trim_ic_first`、`::test_warmup_trim_ic_first_public_window_init`（ICFIRSTALIGN，blocked-by，owned-by-later-ticket）；Task 2.4 之 6 支（PRE-RED，user-ruling，pending-approval）。**v6 實作終態（44 列）**：依 red census 實跑（收據 `handoffs/run_receipts/20261003-prered-red-census.txt`，由 `handoffs/run_receipts/prered_probes/build_allowed_red.py` 機械產生）——①`test_failopen_producer.py::test_four_generator_paths_fail_closed_integration` 全部參數實跑通過，**不列入**（原「走 frame 兩支」之一已過期）；②frame manifest 一支（FRAMEPATH）；③IC-first 兩支、多週期基準一支、Task 2.6 一支、v6 三支五個 node id（`test_v6_independent_asof_oracle_matches_multi_tf_columns`、`test_v6_backend_output_matches_independent_oracle[False|True]`、`test_v6_close_time_oracle_matches_pipeline[False|True]`；HEAD 峰值 footprint 約 71 GB 被系統終止，`d229336e^` 同測試 1 passed、峰值 0.80 GB＝F-2；參數化兩支以函式整體單跑被終止，未逐參數單跑）（ICFIRSTALIGN，blocked-by）；④使用者 2026-10-03 核可刪除全部舊算法特徵 run 後，直接引用被刪 run 之 22 檔中 34 支轉紅（FFSTORE，user-ruling：以新算法產新快照後改寫資料參照）。重凍已核可並完成，`pending-approval` 列為 0。誠實邊界：census 只涵蓋**直接引用被刪 run hash** 之檔；間接依賴（未寫出 hash 而讀 registry 最新 run）之測試須全套量化測試方能盡數，屬小時級，本票未跑，列 §N。
- 轉移：使用者核可並完成單週期重凍之 commit 同時刪除 5 支 `pending-approval` 列（contract ×2、v3 healthy、v3 ETH、layers golden），並把 `test_v3_multi_tf_btc_matches_frozen_baseline` 一列改為（ICFIRSTALIGN，blocked-by，owned-by-later-ticket），同步更新測試內之期望集合；各後續票收案時刪其列。
- **驗證**：`tests/governance/test_prered_allowed_red.py`：①JSON 之 `(node, owner_ticket, reason, state)` 集合**精確等於**測試內具名期望集合（與本 Task 初始集合相同；不以子字串比對）；②每列 node 經 `pytest --collect-only -q` 可收集，參數化 id 須實際出現於收集結果；③`owner_ticket` 為 `docs/TICKET_ORDER.md` 表內之票名或 `PRE-RED`；mutant「清空列表」「加入 `tests/api/test_batch_alias.py::test_patch_batch_alias_deleting_returns_409`（合法 metadata）」「加入不存在之 node」「把某參數化 id 改為不存在之參數」各使其紅。凍結前先提交必敗骨架（`assert False`，訊息「Task 3.1 未實作」），使未實作時驗收必紅。
- **邊界**：①node 含參數化 id（含空白或非 ASCII）⇒ 以收集結果之 node id 字串精確比對；②同一 node 重複列 ⇒ 紅。
- **存活至**：永久（各票收案時刪其列）。**覆蓋風險**：無。　不可做：不得把未歸因之紅加入。

## §V 驗證策略
- 每支修正：HEAD 改後綠＋§P 具名 mutant 轉紅；首紅 commit 之前一版原測試綠（§A 收據）證明改寫不改原意。
- 回歸（逐檔明列、單組串行）：`tests/feature_engineering/test_failopen_contract.py`、`test_failopen_correctness.py`、`test_failopen_layers.py`、`tests/test_cgsa_resume.py`、`tests/api/test_batch_alias.py`、Phase 1 三檔整檔、`tests/governance/test_prered_allowed_red.py`。
- 測試設計審：mutant 清單列入審碼 brief，由委員確認未變弱。

- 兩種驗收模式：**待核模式**（重凍未核可；manifest `gate_cmd`）＝治理三檔、`test_prered_allowed_red.py`、alias、resume config_hash、v7 全綠，另 6 支基準測試不在此命令內（其狀態由 allowed_red 之 `pending-approval` 列與 Task 2.4 驗證之失敗分量對照收據承擔）；**已核模式**（重凍後）＝待核模式加五支單週期基準測試全綠，並逐節點（各自獨立行程，同行程連跑會累積記憶體被系統終止）跑 `test_failopen_correctness.py` 中除 `test_v3_multi_tf_btc_matches_frozen_baseline` 與 v6 三支（五個 node id，F-2）外之其餘節點全綠（命令見 manifest `risk_mitigation`）；`test_v3_multi_tf_btc_matches_frozen_baseline` 屬允許仍紅（Task 3.1），以具名仍紅報告承擔、不入必綠集合（審查 codex 戳記輪 R1）。

## §R 回退
- Phase 1、Phase 2（Task 2.1–2.3）、Task 2.4①②、Task 2.4③重凍、Phase 3 各自獨立 commit；重凍可單獨 revert 回舊基準。

## §N N/A 與殘留
- 走 frame 之 `tests/feature_engineering/test_failopen_manifest.py::test_persist_false_generate_features_metadata` — `為何現在不做: user-ruling:2026-09-28 使用者裁定刪除 frame 產生路徑、不再花時間於 frame 測試`；觸發：FRAMEPATH（第 5 步）刪除或遷移；登記處：`tests/_golden/prered/allowed_red.json`。（v6：`test_failopen_producer.py::test_four_generator_paths_fail_closed_integration` 實跑全參數通過，移出殘留。）
- 刪除舊特徵 run 所致之 34 支紅 — `為何現在不做: user-ruling:2026-10-03 使用者核可刪除全部舊算法特徵 run；資料須以新算法重產`；觸發：FFSTORE（第 14 步）產新快照；登記處：`tests/_golden/prered/allowed_red.json`。
- 間接依賴已刪 run 之測試未盡數 — `為何現在不做: needs-research:全套量化測試（小時級）一次性盤點，排於下次動 FF 共用路徑且收 epic 前`；觸發：FRAMEPATH 或 FFSTORE 收 epic 前之全套量化測試；登記處：本 SPEC 與 `docs/ROADMAP.md` RM-PRERED。
- 發現 F-1（交委員裁定歸屬）：`consumer_gate.is_run_status_cacheable` 只認 `complete`，與 FF-STAT v19「前史不足即整批 partial」並存 ⇒ 本資料上含 12h 深週期之 run 恆為 partial、永不命中工廠快取與 CGSA 續跑（每次重算；不致算錯）— `為何現在不做: needs-research:partial 之可快取條件（哪些 failure_reasons 可視為穩定可重用）`；觸發：FFSTORE（第 14 步）定快取與快照語意時；登記處：`docs/ROADMAP.md` RM-FFSTORE。
- 發現 F-3（觀測缺口，交委員裁定歸屬）：L3 低基數閘（`rolling_aggregator._compute_low_cardinality_cols`，上游非 NaN 相異值 ≤ `skip_higher_moments_max_cardinality`）略過之 skew／kurt 欄**不寫入** `dead_reasons`，故 FF-STAT 之 `column_set_reasons` 不含此類剔除（BTCUSDT/12h 實測 281 欄）— `為何現在不做: blocked-by:FFSTORE（全票排序第 14 步）定欄集合與快照記錄語意；本票不改生產碼`；觸發：FFSTORE 或任何以 column_set_reasons 判欄集合差異之驗收；登記處：`docs/ROADMAP.md` RM-FFSTORE。
- 缺陷 F-2（資源安全，審查 r1 改判）：HEAD 上 12h＋1h、14 天窗之生成，1h 預熱自最早資料起算（20329 列×92617 欄、合併 7.53 GB 磁碟映射、peak footprint 29 GB），8 GB 本機被系統終止而非 fail-closed。本票做分段量測（Task 2.5）；修復 — `為何現在不做: user-ruling:2026-10-02 全票排序定案，記憶體閘之改動（MEM-RSS「證明漏擋才改閘」）排於第 4 步 ICFIRSTALIGN 乙，本票限測試與基準不改生產碼`；觸發：第 4 步開工即以 Task 2.5 收據為漏擋證明；驗收（寫入該票）：原設定完成或於超出預算前以具名錯誤 fail-closed；登記處：`docs/ROADMAP.md` RM-ICFIRSTALIGN。
