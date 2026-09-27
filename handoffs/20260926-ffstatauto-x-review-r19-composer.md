# FF-STAT SPEC v38 審查 r19 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R19  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R19-BRIEF.md`  
標的：`git diff 5551dc5b bfb5ad83 -- docs/FFSTAT_SPEC.md`；r18 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r18/synth.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針未建獨立 worktree（碼證以 repo 讀取＋ `ffstat_helpers` 小切片）。

## COMPOSER-R19-P3-00

**斷言**: 本輪逐項核對 v38 差分與 r18 採納修法後，未發現新的 P0／P1 SPEC 缺陷；r18 三家採納之三條在 v38 正文已對位閉合。

**碼證**: `git diff 5551dc5b bfb5ad83 -- docs/FFSTAT_SPEC.md` → 40 行，僅 §C「L1 輸出點契約」、Task 2.4 `period_keys` 交付／驗收、Task 2.3 ① 之 12h 逐輸出點與 `params={}` 自訂指標 fail-closed；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`rg -n 'L1 輸出點契約|12h 逐輸出點|period_keys' docs/FFSTAT_SPEC.md` → §C:55、Task 2.4:115-116、Task 2.3:123 同輪採納字面齊；`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print(len(kline_frame('BTCUSDT','12h')))"` → 1696；`entropy_indicators.py:88-106`、`tail_risk_indicators.py:66-91` 皆具 `get_feature_metadata` 欄級 `params`（對齊 §C microstructure 範例）；`atomic/warmup_table.yaml:387` `pattern_default_warmup_bars: 5` 與 Task 2.4「無參數指標 `period_keys` 空集合、K 取表內登記」一致。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#7fac252e8abb; handoffs/reconcile/20260926-ffstatauto-x-review-r18/synth.md#e0710db20b29

---

## 必答

1. **(1a)** 本家 r18 僅 **COMPOSER-R18-P2-01**；v38 已在 Task 2.4 檔案段與驗證段寫入「封閉之 `period_keys`」、鍵集合 ⊇ 表登記與缺鍵 fail-closed，**可閉合**。另複核 r18 本家 **COMPOSER-R17-P3-00**（r18 已 CLOSED）：v38 未改 §G 雙起點框架與 R1–R7 裁定前提，**仍閉合**。**(1b)** **COMPOSER-R18-P2-01** 原反例為 Task 2.4 缺 `period_keys` 字面——`docs/FFSTAT_SPEC.md:115-116` 已逐字補齊，無需重跑 full probe。**CODEX-R18-P1-01**／**P2-02** 非本家 ID；逐字核對：§C v38 段落覆蓋 output-to-params 契約與 blocked 收據欄位，Task 2.3 ① 增 12h 逐輸出點與自訂指標 fail-closed 驗收，與 r18 synth 採納處置一致（現碼仍未實作契約，屬 impl，非 v38 新缺口）。

2. **(2a)** v38 差分內**無**新 P0／P1。**(2b)** 可重現路徑（spec 驗收層，未改 repo）：Task 2.3 ① 要求真實 BTC 12h（1696 根）對預設合併設定之每 L1 輸出點驗 origin＋K；負例為 `params={}` 自訂函式回傳 `rolling(5)`／`rolling(233)` 兩欄且未逐輸出宣告 period keys ⇒ 輸出前 fail-closed（對應 r18 P1 反例序列，v38 已寫入驗收句）。

3. **(3a)** brief **assumed** ①「L1 輸出點契約在不改數值／產欄數下可實作」→ **成立**（§C 只增逐欄參數對應與遮罩；TA-Lib 已有 `compute`/`compute_batch` 參數快照；microstructure／entropy／tail_risk 已有 `get_feature_metadata` 可收斂為契約來源，無需拆欄改 schema）。②「`params={}` 自訂多窗反例於契約下必 fail-closed」→ **成立**（Task 2.3 ① v38 明文＋§C「未逐輸出宣告即 fail-closed」）。**(3b)** `talib_wrapper.py:316-335` params 快照；`custom_indicators.py:12-33` 現行 plain concat（impl 前仍缺契約，但 v38 驗收已釘死）；`microstructure_indicators.py:93-115` metadata 與 `_compute_amihud` 多窗欄一致。

4. **(4a)** brief「我沒查」：**①** entropy／tail_risk 欄級參數來源——**未命中** blocking（兩引擎皆有 `get_feature_metadata`，與 §C 範例同型）。**②** CDL `period_keys` 空集合與 K——**未命中** blocking（Task 2.4 定空集合＋表內 K；`warmup_lookup.py:64-66` 讀 `pattern_default_warmup_bars: 5`，與無週期 pattern 語意一致）。**③** 12h 逐輸出點驗收耗時——**未命中** SPEC 缺陷（屬 pytest 驗收成本，非「每次都跑」生成期檢查；brief 停輪紀律 #1 不適用驗收測試）。**(4b)** 見 sentinel **碼證** 所列路徑與 1696 根切片。

5. **(5a)** **是**，v38 可 **`VERDICT: proceed`**（r18 阻擋群集已入 SPEC；本輪無新 P0／P1）。**(5b)** 無。

---

ASSUMPTIONS_VERIFIED: v38 diff 40 行；r18 synth 三條採納；R1–R7 rulings；`dead_feature_filter.py:77-82`；`talib_wrapper.py:316,347`；12h rows=1696  
TESTS_RUN: `git diff 5551dc5b bfb5ad83 -- docs/FFSTAT_SPEC.md`；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → PASS；`rg -n 'period_keys|L1 輸出點契約|12h 逐輸出點' docs/FFSTAT_SPEC.md`；`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print('rows_12h', len(kline_frame('BTCUSDT','12h')))"` → rows_12h 1696；開跑／收尾 `git status --short -- momentum api scripts tests docs templates config` 與 `/tmp/ffstat_r19_git_before.txt` 一致  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查；v38 為 SPEC 文案）  
產出: `handoffs/20260926-ffstatauto-x-review-r19-composer.md`  
TMP_CLEANUP: 已刪本輪 `/tmp/ffstat_v38_diff.txt`、`/tmp/ffstat_r19_git_before.txt`；`/tmp/claude-501` 保留；未改寫被 deny 之 `rm` 形式

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R18-P2-01

STATUS: DONE
