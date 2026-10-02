# FF-STAT 第 6 批 審查 r3（捕獲邊界改函式名判定；r2 閉合）

brief-kind: review
task-id: 20260926-FFSTAT-B6-REVIEW-R3

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading `## <FAMILY>-R3-P<0-3>-<NN>`、零 finding 用 `## <FAMILY>-R3-P3-00`；每條 `**類別**:`；P0／P1 之碼證含 `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只列本家族前綴之 r2 ID）。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。本期委員為 codex、composer、grok 三家。
🔴 **磁碟與時長**：本機 8 GB、8 核；**本輪不得跑生成型 node**。只准讀碼、`--collect-only`、秒級探針與 `tests/feature_engineering/test_ff_truncation_capture_boundary.py`（0.2 秒）。
🔴 **使用者指示（逐字）**：「嚴謹度和分析模組是必要的，只能多但不能少」；「測試和驗證是必要，但是我不想整個流程再消耗時間在不是必要的測試上」。**嚴禁慢閘**。

## 審查標的
- commit `1d09aaa4`（`git show 1d09aaa4`）：`tests/feature_engineering/ff_truncation_mr_helpers.py` 之 `_CAUSAL_GATE_FUNCS`、`_NON_CAUSAL_FUNCS`、`_expect_causal_gate_failure`（traceback 函式名判定）、`_FRACDIFF_PRE_VALUES_GATES`；新增 `tests/feature_engineering/test_ff_truncation_capture_boundary.py`；SPEC v60 Task 4.2 兩處文字。
- r2 收斂檔 `handoffs/reconcile/20260926-ffstat-b6-review-r2/synth.md`。

## 主委事實
1. `test_ff_truncation_capture_boundary.py` 9 passed（0.19 秒）：fracdiff atol 值、warmup NaN mask、metadata、strict 欄集合之真實 gate 失敗被收；經 `_assert_mutation_layer_coverage`、訊息含 `coverage guard failed`、非 gate 拋出而訊息仿值 gate 者被拒；尾擾動 fracdiff 控制拒收值 gate；前史擾動只改起始日之前列。

## 本 brief 前提
fact-verified: 主委事實 1。
assumed: ① pytest `excinfo.traceback` 之 entry 名稱含 helpers 內每一層 gate 函式（即使實際 raise 在 numpy 或 pytest 斷言改寫內部）。② 主 MR 與 fracdiff MR 之 `check()` 路徑中，除表列 gate 外無其他 helpers 函式拋出之 AssertionError 屬因果失敗而被誤拒。③ 對齊 look-ahead 控制之 `_assert_align_coarse_boundary_lookahead_detected`（捕獲區外正向檢查）與 `_values_check` 之 `_assert_truncation_invariants` 內部 align 相關檢查不衝突。
→ 否證觀測：①某 gate 失敗之 traceback 缺該 gate 名（例如經 `pytest.raises` 重寫後截斷）；②某因果失敗由表外函式拋出（如 `_assert_nan_mask_layered`、`_assert_arrays_values_close` 被非表列 caller 呼叫）；③對齊控制於捕獲區內之失敗只由 align oracle 函式拋出而非表列 gate。／我跑了：①以 9 項測試驗 5 種 gate；②③只讀碼。

## 攻擊面
- **已排除**：r1、r2 已閉合之面。
- **我沒查**：
  1. `_assert_values_gate_main` 內部之 coverage guard（`coverage guard failed`）與 sampling guard（`pytest.fail`，非 AssertionError）之分流是否完整。
  2. 「非 gate 拋出」反例之判定是否會因 `check` 本身為 lambda／閉包而有誤（lambda 名為 `<lambda>`）。
  3. 函式名判定對未來新增 gate 之可維護性（新增 gate 未入表 ⇒ 誤拒〔紅〕而非假綠，方向是否正確）。

## 必答（成對）
1. **(1a)** codex、composer、grok：本家 r2 條以原反例（warmup／atol／metadata 真實訊息）重跑是否閉合？**(1b)** 實跑輸出。
2. **(2a)** assumed ①②③ 與「我沒查」1–3 是否成立？**(2b)** 依據。
3. **(3a)** 可否據此全跑（約 6.5 小時，串行、獨占）？**(3b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 威脅模型＝**意外漂移與未來洩漏之漏測**；每條 P0／P1 須附可重現之輸入或操作序列。
2. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由；不得以放寬容差或移出分母掩蓋問題。
3. `CLOSED:` 只准列**本家族前綴**之 ID。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api frontend tests templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
