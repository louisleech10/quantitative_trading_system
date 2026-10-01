# ICPOSTLEAK 實作第 1 批 審碼 r1

brief-kind: review
task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R1

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading `## <FAMILY>-R1-P<0-3>-<NN>`、零 finding 用 `## <FAMILY>-R1-P3-00`；每條 `**類別**:`；P0／P1 之碼證含 `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`。每家**全面**審（後端、前端、測試、收據皆看，不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱；FF 探針須先呼叫 `handoffs/run_receipts/ffstat_probes/_isolate.py` 之 `isolate()` 與 `isolate_dstar_cache()`。本期委員為 codex、composer、grok 三家。
🔴 **磁碟與時長**：本機 8 GB、8 核；重測試一律單組串行、不得與他家並行；以 node id 選跑；暫存結束前刪除。
🔴 **使用者指示（逐字）**：「嚴謹度和分析模組是必要的，只能多但不能少」；「測試和驗證是必要，但是我不想整個流程再消耗時間在不是必要的測試上」；未來洩漏「絕對修掉不得列殘留」。**不得侷限加密貨幣**；**嚴禁慢閘**。

## 審查標的
- SPEC `docs/ICPOSTLEAK_SPEC.md` v4（凍結）、manifest `docs/manifests/ICPOSTLEAK.json`、戳記收斂檔 `handoffs/reconcile/20261001-icpostleak-x-review-r8/synth.md`。
- commit `95487b67`（Phase 1）與 `47ba1d3e`（Phase 2）：`git show 95487b67`、`git show 47ba1d3e`。
- 實作 brief `handoffs/20261002-ICPOSTLEAK-IMPL-B1-BRIEF.md`（EXPECTED-DELTA 與已知既有問題）。
- 收據 `handoffs/run_receipts/20261002-icpostleak-branch-inventory.txt`、`handoffs/run_receipts/20261002-icpostleak-change-report.json`、`handoffs/run_receipts/20261002-icpostleak-oracle-unmasked.json`。

## 主委事實
1. 主樹實跑 `tests/feature_engineering/test_icpostleak.py`、`tests/api/test_icpostleak_api.py`、`tests/api/test_ic_la1_degraded_gate.py`、`tests/feature_engineering/preprocessing/test_l65_v2_transforms.py`、`tests/feature_engineering/preprocessing/test_ff_causal_golden.py`、`tests/feature_engineering/preprocessing/test_l65_native_tf_real_eth.py`＋`test_l65_parallel` 快速路徑節點：180 passed。
2. 隔離 worktree（HEAD 版 golden 檔）跑 contract 列之 18 檔受影響測試：171 passed、2 failed；兩 failed＝`test_l7_raw_streaming::test_feature_factory_cgsa_generation_routes_to_l7_raw_writer`、`test_l65_parallel::test_tier_auto_selects_workers`，於 FF-STAT 前 `5a148b8e` 即紅。
3. 「`mask_incomplete_window_by_input_2d` 改 identity」mutant 下，改寫之五項既有測試全紅。
4. 改前改後對照：49 例中 legacy／optimized／Polars 全部 35 例遮罩後區段 0 格差異；registry 系列 14 例差異。
5. 前端 `npm run build` rc=0、vitest 3 passed（主樹）。全新 checkout 之 build 因 `Select.tsx`／`Card.tsx` 大小寫失敗，HEAD 前即如此。

## 本 brief 前提
fact-verified: 主委事實 1–5。
assumed: ① registry 系列 14 例差異只來自三個預期原因（改為正式順序 rank→gaussian→zscore、zscore 改 numba 累積式單步核心、切片並行補上原漏掉之 gaussian），非新漂移。② `_registry_fast_transform` 之 float32 逐步回存與舊融合核心之 float32 輸出語意相容（下游讀者不依賴 float64 中間精度）。③ ratio-unsafe 欄於 IC 頁明示排除（而非轉換）與正式 FF L6.5 對 ratio-unsafe 之處理一致。
→ 否證觀測：①任一 registry 例之差異格不能由三原因之一重現；②下游（IC 計算、ML 讀取）有斷言依賴 float64 中間值；③正式 FF 對 ratio-unsafe 欄實際會做 rank／zscore。／我跑了：①change-report 逐例分類；②③僅讀碼，未實跑下游。

## 攻擊面
- **已排除**：SPEC／TODO 設計面（r1–r8 已收斂、三家戳記）。
- **我沒查**：
  1. `_stream_sharded_group_to_sink` 於 gaussian `apply_to` 非 all 時改 fail-closed，是否有生產設定實際走到（會使原本可跑之批次改為報錯）。
  2. `transform_selected` 逐群組時間序檢查對多週期合併後之索引（含 native-tf 對齊後）是否可能誤擋合法資料。
  3. IC 頁 `excluded_features` 全排除時 ValueError 之 HTTP 對應（400 或 500）與前端顯示。
  4. 前端在 `excluded_features` 缺欄（舊後端）時之相容。
  5. append 模式下多 zscore 窗之遮罩錨點是否各窗獨立。

## 必答（成對）
1. **(1a)** 實作是否完整符合 SPEC v4 與 manifest（逐 Task）？**(1b)** 碼證（CODE-ANCHOR）。
2. **(2a)** IC 頁與正式後處理是否仍有任何未來洩漏或窗未滿之輸出？**(2b)** 實跑或可重現之輸入序列。
3. **(3a)** assumed ①②③ 與「我沒查」1–5 是否成立？**(3b)** 碼證或輕量實跑。
4. **(4a)** 改寫之既有測試是否變弱（期望之更新是否只限遮罩所致）？**(4b)** diff 逐處對照。
5. **(5a)** 可否收第 1 批？**(5b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 威脅模型＝**意外漂移與未來洩漏**；每條 P0／P1 須附可重現之輸入或操作序列。
2. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由；不得以放寬容差或移出分母掩蓋問題。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api frontend scripts tests docs templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
