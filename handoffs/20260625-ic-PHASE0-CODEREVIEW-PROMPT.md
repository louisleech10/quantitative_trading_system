# IC Phase 0 實作 — Code Review 派工（Composer 2.5，跨家族複查 Codex diff）

你是獨立 code reviewer（與實作者 Codex 不同家族）。審查 **IC Phase 0 實作 diff** 是否正確、忠實 SPEC、無遺漏/假綠/正確性風險。

## 讀
- 實作 diff：`git diff`（已改 tracked）+ 新增檔 `git status`（untracked tests/fixtures）。重點檔：`momentum/Analysis/ic_engine.py`、`ic_filter_orchestrator.py`、`ic_config_schema.py`、`api/services/ic_analysis_service.py`、`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`，及 `tests/momentum/test_ic_*.py`、`tests/fixtures/ic_phase0/`。
- 準則：`docs/IC_PHASE0_SPEC.md`、`docs/IC_PHASE0_TODO.md`、`handoffs/20260625-ic-PHASE0-ADVERSARIAL-RECONCILE.md`(R-1~R-12)、`...TODO-ADVERSARIAL-RECONCILE.md`(T-1~T-12)。

## 聚焦
1. **正確性**：(a) `_get_time_index` 回 DatetimeIndex + 單位實測 + fail-closed 是否真對齊 raw_data.index、邊界(NaN/1e15/年份)無漏；(b) `_iter_time_groups` `.dt.year` 改動正確；(c) by_volatility fail-closed + 預設 False；(d) `_apply_feature_filter` 預設不截斷、sorted 截斷、零特徵 raise、truncation_mode 判定；(e) decay 移 4 warning 後**數值真不變**(非只 golden 過)、summary 一行。
2. **忠實 SPEC/reconcile**：R-1~R-12、T-1~T-12 有無走樣或遺漏。
3. **防假綠**：既有測試斷言有無被放寬/刪除換綠；新測試是否真測核心行為（非 smoke）；golden 是否結構化 float 比對。
4. **跨層/相容**：feature_filter API↔ICConfig↔orchestrator 串接；前端 failed 讀 data.message/poll error + 有限重連 + poll 狀態機；向後相容(feature_filter None 不影響既有)。
5. **遺漏/隱患**：有無未更新的呼叫端、半成品、靜默吞錯、look-ahead。

## 輸出
```
## Verdict：可合併 / 需修補後合併 / 有缺陷需重作
## Findings（[BLOCKING|MAJOR|MINOR] + 證據(檔:行/diff 片段) + 風險 + 修法）
## 正確性/防假綠 專項結論（逐項 1-5）
STATUS: DONE
```
只輸出 findings，不改碼。把完整 findings 寫到 `handoffs/20260625-ic-PHASE0-CODEREVIEW-COMPOSER.md`。
