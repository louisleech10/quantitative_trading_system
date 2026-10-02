# FF-STAT 第 6 批 審查 r1（SPEC v59 Task 4.2 本機縮小版全鏈截斷 MR：設計＋測試本體）

brief-kind: review
task-id: 20260926-FFSTAT-B6-REVIEW-R1

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading `## <FAMILY>-R1-P<0-3>-<NN>`、零 finding 用 `## <FAMILY>-R1-P3-00`；每條 `**類別**:`；P0／P1 之碼證含 `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱；探針須先呼叫 `handoffs/run_receipts/ffstat_probes/_isolate.py` 之 `isolate()` 與 `isolate_dstar_cache()`。本期委員為 codex、composer、grok 三家。
🔴 **磁碟與時長**：本機 8 GB、8 核；**本輪不得跑兩新檔之生成型 node**（單週期一對約 9 分鐘、多週期一對約 37 分鐘、3–4GB 峰值；主委將於本輪後獨占機器全跑）。只准：讀碼、`--collect-only`、秒級探針（如 `_required_window_bars`、payload 解析、monkeypatch 是否命中模組全域名稱之靜態／匯入期檢查）。
🔴 **使用者指示（逐字）**：「嚴謹度和分析模組是必要的，只能多但不能少」；「測試和驗證是必要，但是我不想整個流程再消耗時間在不是必要的測試上」。**不得侷限加密貨幣**；**嚴禁慢閘**。

## 審查標的
- SPEC `docs/FFSTAT_SPEC.md` v59：版本頭與 Phase 4 **Task 4.2**（`git diff HEAD -- docs/FFSTAT_SPEC.md`）。
- manifest `docs/manifests/FFSTAT.json`（`git diff HEAD -- docs/manifests/FFSTAT.json`；`TODOFMT PASS`）。
- 測試本體：`tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py`、`tests/feature_engineering/test_ff_multitf_truncation_small_mr.py`、`tests/feature_engineering/ff_truncation_mr_helpers.py` 新增之 `_apply_small_mr_scope`／`_small_values_gate_mr_config_payload`／`_small_fracdiff_mr_config_payload`。
- 可行性收據：`handoffs/run_receipts/20261002-ffstat-small-mr-probe-1h.json`、`handoffs/run_receipts/20261002-ffstat-small-mr-probe-1h4h.json`；探針 `handoffs/run_receipts/ffstat_probes/small_mr_probe.py`。
- 依據：諮詢 r4 `handoffs/reconcile/20260926-ffstat-b5-consult-r4/synth.md`（較嚴版：收案前補本機縮小版；codex 該輪所提設計要點）。
- 大機器清單：`scripts/fact_keys.json` RM-FULLSCALE 列增 ④⑤（`git diff HEAD -- scripts/fact_keys.json`）。

## 主委事實
1. 可行性實測（獨占機器、外層 `/usr/bin/time -l`）：單週期縮小設定一對 519.9 秒、峰值 RSS 3.01GB、窗 3,594、37,709 欄，基線綠；多週期 1h＋4h 一對 2,249 秒、4.12GB、窗 12,786、75,416 欄，基線綠。
2. 1h＋4h＋12h 縮小設定需窗 37,266（只開 trend 34,302），本機 BTCUSDT 1h 20,352 根、長歷史快取無 1h（4h 19,963、12h 6,656）⇒ 既有多週期檔目前於 `requires_kline` 即 fail。
3. `--collect-only`：兩新檔 20 node；`TODOFMT PASS`。
4. 分母尺度之全部呼叫者（`polars_adapter.py:58,343`、`derived_operators.py:395` 經 `safe_denominator`）皆經 `numeric_guards.causal_near_zero_mask` 以模組全域名稱呼叫 `causal_denominator_scale`。
5. （本輪派出時進行中）單週期基線＋分母尺度 mutant 實跑；結果將於收斂檔附上。

## 本 brief 前提
fact-verified: 主委事實 1–4。
assumed: ① 既有測試函式以模組全域名稱取設定（`_values_gate_mr_config_payload`、`_fracdiff_mr_config_payload`、`TRAINING_TFS`、`ALIGN_COARSE_TFS`、`EXPECTED_TRAINING_TFS`、`_multitf_config_payload`），autouse monkeypatch 換掉後函式本體即用縮小版，無遺漏之直接參照（如預設參數於定義時綁定、或 helpers 內部自行呼叫原 payload）。② 縮小範圍仍使既有三個生成層 mutant 之 seam 在場且被抽樣（L3 `fused_rolling_stats_multi_window`、縮尾 `_apply_winsorization`、L4 `LagProcessor.compute_all`；`_assert_mutation_layer_coverage` 之層覆蓋守衛照常）。③ 截斷 MR 之 full 與 trunc 同起點，故 L1 遮罩刪除、縮尾完整窗遮罩刪除、第④類前綴遮罩刪除三類 mutant 兩邊同錯而不可見，交 §G⑦ 雙起點對證負責屬正確分工。
→ 否證觀測：①任一既有函式之某呼叫點仍拿到全設定（例：`_build_truncation_pair` 內 `window_bars is None` 時以全設定估窗）；②縮小設定下某 mutant 之 seam 未被呼叫或其層無抽樣欄；③存在某遮罩 mutant 使 full 與 trunc 之前綴不同。／我跑了：①②只讀碼；③未查。

## 攻擊面
- **已排除**：既有兩檔之 gate／容差／抽樣規則（不改）；FF-STAT 第 1–5 批之生產碼。
- **我沒查**：
  1. 縮小範圍是否使 strict xfail 兩項（既有 codec 精度路徑）轉為 XPASS——若是，依 SPEC 須改一般測試；判斷縮小設定是否仍觸及該 codec 路徑。
  2. 分母尺度 mutant 在縮小設定下是否真能使 full 與 trunc 前綴不同（若窗內無近零分母或尺度差不跨門檻則存活）——主委正實跑。
  3. 多週期 `_bar_window_dates_at_12h_boundary` 與 `_primary_indices_at_12h_boundaries` 以 12h 邊界為 oracle 列，對粗週期 4h 是否仍足以使對齊 look-ahead 被偵測（4h 有更多邊界未被 oracle 檢查是否減弱鑑別力）。
  4. 資料源只 close＋volume 是否使 L2 之跨來源組合（如 close 對 volume 之 Ratio）仍存在。
  5. 「不證全欄覆蓋」之誠實邊界是否足夠，或另需於 FF-STAT 收案條件寫明縮小版不得作為全設定之放行證據。

## 必答（成對）
1. **(1a)** Task 4.2 之設計是否足以作為 FF-STAT 收案前置（相對諮詢 r4 之較嚴版要求）？**(1b)** 依據（含 codex r4 所列之設計要點逐項對照）。
2. **(2a)** assumed ①②③ 與「我沒查」1–5 是否成立？**(2b)** 碼證或秒級探針。
3. **(3a)** 兩新檔之寫法（直接呼叫既有函式本體＋autouse 換全域）是否會造成假綠或漏測？**(3b)** 具體反例或證明。
4. **(4a)** 可否據此實跑（全套約 6.5 小時，串行、獨占）？**(4b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 威脅模型＝**意外漂移與未來洩漏之漏測**；每條 P0／P1 須附可重現之輸入或操作序列。
2. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由；不得以放寬容差或移出分母掩蓋問題。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api frontend tests templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
