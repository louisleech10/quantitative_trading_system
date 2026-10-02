# FF-STAT 第 6 批 審查 r2（SPEC v60：負控制共用本體與三缺陷改正；r1 閉合）

brief-kind: review
task-id: 20260926-FFSTAT-B6-REVIEW-R2

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading `## <FAMILY>-R2-P<0-3>-<NN>`、零 finding 用 `## <FAMILY>-R2-P3-00`；每條 `**類別**:`；P0／P1 之碼證含 `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只列本家族前綴之 r1 ID）。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱；探針須先呼叫 `handoffs/run_receipts/ffstat_probes/_isolate.py` 之 `isolate()` 與 `isolate_dstar_cache()`。本期委員為 codex、composer、grok 三家。
🔴 **磁碟與時長**：本機 8 GB、8 核；**本輪不得跑生成型 node**（主委將於本輪後獨占機器全跑約 6.5 小時）。只准讀碼、`--collect-only`、秒級探針（payload／窗長解析、捕獲邊界之合成訊息正反例、`_pre_start_rows` 對真實 K 線之列數）。
🔴 **使用者指示（逐字）**：「嚴謹度和分析模組是必要的，只能多但不能少」；「測試和驗證是必要，但是我不想整個流程再消耗時間在不是必要的測試上」。**不得侷限加密貨幣**；**嚴禁慢閘**。

## 審查標的
- commit `d3c8d339`（`git show d3c8d339`）：SPEC `docs/FFSTAT_SPEC.md` v60 Task 4.2；`tests/feature_engineering/ff_truncation_mr_helpers.py` 檔尾之負控制共用本體（`MRScope`、`_assert_mr_preparation`、`_expect_causal_gate_failure`、`_pre_start_rows`／`_patch_kline_pre_start_ohlcv`、`_build_scope_pair`、`run_control_*`）；既有兩檔 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`、`tests/feature_engineering/test_ff_multitf_truncation_mr.py` 之負控制改呼叫共用本體；兩新檔。
- r1 收斂檔 `handoffs/reconcile/20260926-ffstat-b6-review-r1/synth.md`（CODEX-R1-P1-01／02／03、COMPOSER-R1-P1-01、COMPOSER-R1-P2-01）。
- 前置實跑收據 `handoffs/run_receipts/20261002-ffstat-small-mr-prerun.json`。

## 主委事實
1. 前置實跑：縮小設定 C2-1 綠（506 秒）；分母尺度 mutant DID NOT RAISE（464 秒）⇒ 撤除；fracdiff 截斷基線 XPASS（strict）⇒ 改一般測試；尾擾動 fracdiff 基線 XFAIL。
2. `--collect-only` 四檔 41 node；既有兩檔三個 smoke 3 passed；捕獲邊界秒級正反例：值 mismatch、d\* mismatch 被收；`mutation layer coverage failed (sampling design error)`、`coverage guard failed` 被拒；尾擾動 fracdiff 控制拒收值 gate 訊息；`_pre_start_rows` 合成時間戳取到起始日之前 5 列。
3. 校準 K 線經 `_layer0_data_ingestion` → `AdapterRegistry.fetch_aligned`（`feature_factory.py:915`、`:2408-2420`），故 `patch_fetch_full_only` 之 full 側擾動同時作用於校準域與公開域預熱。

## 本 brief 前提
fact-verified: 主委事實 1–3。
assumed: ① 校準擾動控制擾動起始日之前全部前史（不只校準 N 根）可接受——目標為證 d\*／欄集合對前史敏感；公開域預熱同時被改不影響判定，因只承認 strict 欄集合與 d\* 之失敗。② 全量 d\* 控制之 mutant（`_calibration_series` 回傳原序列）於 FF-STAT 後仍使 full 與 trunc 之 d\* 不同（全量序列兩 run 差 10 根）。③ `_CAUSAL_GATE_PREFIXES` 涵蓋各 gate 之實際失敗訊息開頭（含 `_assert_values_gate` 之 atol 版、`_assert_warmup_nan_masks_equal`、`_assert_metadata_gate`）。
→ 否證觀測：①擾動前史使校準前置關卡拋 `CalibrationError`（應傳出為紅，非抓到）或使 full 側生成失敗；②全量 d\* 下兩 run d\* 相同（grid 步距粗於 10 根差異）；③某 gate 之失敗訊息不以表列前綴開頭而被誤拒，或某非因果訊息以表列前綴開頭而被誤收。／我跑了：③以合成訊息驗 4 例；①②未查。

## 攻擊面
- **已排除**：r1 已採納之設計方向（縮小範圍、12h 不納入、遮罩類 mutant 交 §G⑦）。
- **我沒查**：
  1. `_expect_causal_gate_failure` 之 `startswith` 判定對 `_assert_values_gate`／`_assert_warmup_nan_masks_equal`／`_assert_metadata_gate` 實際訊息格式（請逐一對照 helpers 原碼）。
  2. 既有兩檔改呼叫共用本體後，其 mutant 測試之語意是否與改前一致（除三缺陷改正外無其他改變）；`FULL_MULTITF_SCOPE` 之 `fracdiff_payload` 填 values payload 是否有誤用風險（多週期無 fracdiff 控制）。
  3. 長度耦合 mutant 去上限後之 max_lag（334）是否超過 fracdiff 實作之權重或序列長度限制而拋錯（應傳出為紅）。
  4. `_build_scope_pair` 預設選窗改 `_bar_window_dates`（同正常基線），對齊控制顯式用 12h 邊界——是否與既有寫法一致。

## 必答（成對）
1. **(1a)** codex：本家 r1 三條以原反例重跑（秒級）是否閉合？composer：本家 r1 兩條處置是否正確？grok：r1 之放行判斷在 v60 下是否仍成立？**(1b)** 碼證或秒級探針輸出。
2. **(2a)** assumed ①②③ 與「我沒查」1–4 是否成立？**(2b)** 依據。
3. **(3a)** 可否據此全跑（約 6.5 小時，串行、獨占）？**(3b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 威脅模型＝**意外漂移與未來洩漏之漏測**；每條 P0／P1 須附可重現之輸入或操作序列。
2. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由；不得以放寬容差或移出分母掩蓋問題。
3. `CLOSED:` 只准列**本家族前綴**之 ID。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api frontend tests templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
