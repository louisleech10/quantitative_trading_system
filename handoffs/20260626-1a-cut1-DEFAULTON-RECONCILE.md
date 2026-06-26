# default-ON 語義 — 委員會 reconcile（定案：分因回退）

> Claude 推薦 (A) → Codex A'(顯式 fallback + applied:false + 下游只認 applied===true) → Composer 分因回退(精煉) → 本定案。三方收斂。

## 定案：分因回退（cause-specific）
| OOS 不可行原因 | 行為 | correctness |
|---|---|---|
| **insufficient_data / rolling_warmup_insufficient** | 回退 full-sample + `applied:false` 標記 | legacy==flag-off,**無新洩漏**,僅不可宣稱 OOS |
| **irregular_timestamps / gap**（TimestampDiscontinuityError） | **維持 fail-closed raise,不回退** | C-3 紅線;時間軸壞→full-sample IC 語義錯,比沒 OOS 更糟 |
| 合成/plumbing 測試（假 timestamp） | 顯式 `ic_train_test_split=False`（輔助 C） | 非真時序,本不該做 OOS,測的是管線 |

## metadata 標記（防誤標 OOS,雙家一致）
- OOS 成功：`ic_train_test_split:{requested:true, applied:true, scope:"train_test_holdout", oos_guarantees:true, ...}`、`metadata.scope:"test"`。
- 回退：`ic_train_test_split:{requested:true, applied:false, scope:"full_sample_legacy", oos_guarantees:false, reason:"insufficient_data|rolling_warmup_insufficient", details:{train_rows,test_rows,min_test_rows}}`；**不得**寫 train/test_time_bounds、不得 `scope:"test"`。
- **下游鐵律**：threshold/summary/deep/前端 badge **只認 `applied===true`**,禁用 requested/enabled 推斷 OOS。
- 回退時 summary 列 `eval_status` 維持 legacy（非 OOS）。

## 實作範圍（派 Codex）
1. **analyze() 分因回退**：`_build_holdout_split_plan` 回 SkippedResult(insufficient) 或 stage4 rolling warmup 不足時 → **不 skip 整條**,改走 full-sample(flag-off 既有路徑,fit_mask=None) 並寫 `applied:false` metadata。**TimestampDiscontinuityError 仍 raise（不接 fallback）**。
2. **API plumbing 測試 opt-out**：`tests/api/test_ic_analysis_api.py` 等用合成假 timestamp 的測試,request/config_override 設 `ic_train_test_split=False`（它們測管線非 OOS）。
3. **新測試**：`test_fallback_insufficient_data_marks_applied_false`（小 n + default ON → 有完整 summary_table 且 `applied:false`/`scope:full_sample_legacy`）；`test_irregular_timestamps_still_fail_closed`（假 arange ts + flag on → raise,不 fallback）。
4. **G-NEW 不變**：只凍 applied:true 路徑（BTC/1h 真實,已凍）。

## API timeout 附帶（Codex）
非典型 task 終態 bug；skipped 回不完整 report 害下游。採分因回退後,insufficient 走完整 report 即解;irregular 維持 raise→task failed(快速,非 timeout)。可選:service 對「主分析 skipped」標 `skipped` 而非普通 completed(本刀可不動,§N)。

## 不變
default ON 不退；leakage 契約兩層（applied=true 嚴格 OOS；applied=false legacy 不可當 OOS 證據）。三方已簽的 OOS 路徑正確性不受影響。
