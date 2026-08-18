# GAP-1 B3 戳記 — composer（R17）

task-id: `20260818-GAP1-B3-STAMP-R17`
stamp-target: `handoffs/reconcile/20260818-gap1-b3-review-r16/synth.md`
family: composer

## 判定

**APPROVED**

## body_sha256（實跑）

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap1-b3-review-r16/synth.md
→ b367b5722c772db7902138f4cf38bfe090e6f5b95ed9498e8210bc8d2d4c4774
```

## 判準實測

| # | 命令 | rc | 計數／摘要 |
|---|------|-----|-----------|
| 1 | `bash scripts/completeness_check.sh --synth … --lock …` | 0 | codex 4/4、composer 2/2、grok 6/6；0 掉項 |
| 2 | composer 反例重跑 | — | 見下 |
| 3 | `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` | 0 | **224 passed** |
| 3b | `venv/bin/python -m pytest tests/test_phase6_end_to_end.py tests/test_frontend_integration.py -q` | 0 | **9 passed** |
| 4 | mutation 探针（讀 receipt，未並行跑） | 0 | **17 條**全轉紅；baseline/post-restore **221 passed** |
| 5 | A1-22 回歸鎖 | — | 見下 |
| 6 | `python3 scripts/check_decoupling_imports.py --baseline …` + `grep -r "from api\." momentum/` | 0 | BASELINE OK；api import **0** |
| 7 | Verdict／殘留掃描 | — | 無未修項；見下 |

### 判準 2 — composer R16 反例（原提出方重跑）

| 反例 | 預期 | 實跑 |
|------|------|------|
| 裸 `ValueError` 從 reporter | **500**（非 400） | `test_bare_value_error_from_reporter_is_5xx_not_400` passed；log `HTTP 500: strategy_validation reporter internal error` |
| IVA detail | 恰為 `strategy_validation reporter argument error`（無 `Internal error:` 前綴） | `test_wiring_error_negative_t_years_is_5xx_not_reporter_failed`：`resp.json()["detail"] == "strategy_validation reporter argument error`；log `HTTP 500: strategy_validation reporter argument error` |

### 判準 4 — mutation receipt

`handoffs/run_receipts/20260818T093000Z-gap1-b3-fix-mutation.log`：§V-1／2／3／5／7／7b／7c／7d／7e／8／9a／9b／10／11／12／13／15 共 **17 條**皆 `rc=1 FAILED>=1`；baseline/post-restore **221 passed**；`[gap1-b1-mutation] ✅`；`rc=0`。

### 判準 5 — A1-22 與碼一致

| 檢查項 | 結果 |
|--------|------|
| M1 回歸鎖 `test_bare_value_error_from_reporter_is_5xx_not_400` | 存在且 passed |
| M1/M2 回歸鎖 `test_wiring_error_negative_t_years_is_5xx_not_reporter_failed` | 存在；detail 專用字面；`tmp_path.glob('*.json')` 為空 |
| M3 `test_n_one_equals_psr_closed_form_with_exact_skew0_kurt3` | 存在；skew≈0、kurt≈3 先斷言 |
| M4 `_ledger` fixture | `n_failed = n_evaluated - n_valid` + 自檢 assert |
| M5 `test_n_source_values_are_contract_enum_and_validated` | 存在；`test_exactly_seventeen_top_level_keys` 17 鍵 |
| M6 `factories.py` reporter import | `grep` 恰 **2** 處（`:28` TYPE_CHECKING、`:768` lazy factory） |
| route `except HTTPException: raise` | `:284-286`，在 `except ValueError`（`:287`）之前 |
| reporter 先於落盤 | `for_study_trial` `:222`；`pipeline_file` 寫入 `:240-244` |

### 肉眼 — composer 2 ID 群集對照

| ID | 群集 | 處置對齊 |
|----|------|---------|
| COMPOSER-R16-P1-01 | M1 | 裸 `ValueError`→500；`test_bare_value_error_from_reporter_is_5xx_not_400` ✓ |
| COMPOSER-R16-P2-01 | M1 | `except HTTPException: raise`；IVA detail 專用字面 ✓ |

### 判準 7 — Verdict／A1-22 誠實性

- synth Verdict「需修補後進 B4」與 M1–M6 全修、測試全綠一致；未發現「稱已修但碼未改」之殘留。
- A1-22 覆寫 A1-16 第 2 點（reporter `ValueError`→5xx）與 Task 2.1「恰 16」→17 鍵：契約／route／測試三處對齊，非僅文件聲明。

## Verdict 理由（一句）

B3 修補 commit 已關閉 composer 兩條 findings（裸 `ValueError` 誤標 400、IVA detail 被外層重包），M1–M6 群集與 A1-22 回歸鎖、224+9 測試及 codex mutation receipt（17 條）均符合 brief，無殘留未修項。

## 戳記（已 append）

```
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:b367b5722c772db7902138f4cf38bfe090e6f5b95ed9498e8210bc8d2d4c4774 task:20260818-GAP1-B3-STAMP-R17
```

## /tmp 收尾

沙箱權限阻擋 `rm`（`Permission denied: Command blocked by permissions configuration`）；**未清**。待清項：`gap1-b3-stamp-grok-*.log`、`gap1_mut.log`、`push*.log`、`sessions/`、`pytest-of-louis` 等；應保留 `claude-501`、`cc-socks`、`com.google.Keystone`。

---

ASSUMPTIONS_VERIFIED: body_sha256 與 brief 一致；completeness 0 掉項；composer 兩反例關閉；strategy_validation+API 224 passed；e2e 9 passed；mutation receipt 17 條；decoupling BASELINE OK；grep momentum api import=0
TESTS_RUN: reconcile_body_hash.sh rc=0；completeness_check.sh rc=0；pytest strategy_validation+API -q rc=0 224 passed；pytest phase6+frontend -q rc=0 9 passed；composer 反例 2 tests passed；check_decoupling_imports.py rc=0；grep api import count=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 append synth 戳記 + 本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（驗收唯讀 + 戳記 append）

STATUS: DONE
