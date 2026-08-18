# GAP-1 B4 戳記 — composer（R19）

task-id: `20260818-GAP1-B4-STAMP-R19`
stamp-target: `handoffs/reconcile/20260818-gap1-b4-review-r18/synth.md`
family: composer

## 判定

**APPROVED**

## body_sha256（實跑）

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap1-b4-review-r18/synth.md
→ c69a22c07dfb1c07929ee36b2781474e505dc460c5b8395844f175d91a43debc
```

## 判準實測

| # | 命令 | rc | 計數／摘要 |
|---|------|-----|-----------|
| 1 | `bash scripts/completeness_check.sh --synth … --lock …` | 0 | codex 6/6、composer 2/2、grok 5/5；0 掉項 |
| 2 | composer 反例重跑 | — | 見下 |
| 3 | `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` | 0 | **280 passed** |
| 4 | mutation 探针（讀 receipt，未並行跑） | 0 | **20 條**全轉紅；baseline/post-restore **277 passed** |
| 5 | `bash scripts/strategy_wiring_check.sh` + `bash -n …` | 0 | `✓ W1..W4`；syntax rc=0 |
| 6 | `python3 scripts/check_decoupling_imports.py --baseline …` + `grep -r "from api\." momentum/` + `bash scripts/gov_check.sh --fast` | 0 | BASELINE OK；api import **0**；gov ✅ |
| 7 | A1-24 與碼一致 | — | 見下 |
| 8 | registry G1-R1..R7／R9／R10／R11 觸發未成立 | — | 見下 |

### 判準 2 — composer R18 反例（原提出方重跑）

| 反例 | 預期 | 實跑 |
|------|------|------|
| ④b 雙冠手算 ω=ln(2/3)／ln(7/3) | 誤取大索引 champion 即紅 | `test_double_champion_takes_smallest_index_hand_computed` passed；`logits_min≈ln(2/3)`、`logits_max≈ln(7/3)`（atol 1e-12） |
| `0.01` 近常數欄 vec==ref 逐位 | 兩路須逐位相同 | `test_vectorized_sharpe_matches_compute_sharpe` passed；col 7／8 用 `==` 斷言；G1-R11 註記近常數仍回巨大有限 SR（B1 語意殘留，非漏修） |

### 肉眼 — composer 2 ID 群集對照

| ID | 群集 | 處置對齊 |
|----|------|---------|
| COMPOSER-R18-P2-01 | N4 | ④b 改 `test_double_champion_takes_smallest_index_hand_computed` 手算可證偽；`sorted(logits)==[ln(2/3), ln(7/3)]` ✓ |
| COMPOSER-R18-P2-02 | N5 | `_sharpe_pp_1d` 逐欄 1-D 縮減；等價測試加 `0.01`／微擾欄 `==`；G1-R11 登記 needs-research ✓ |

### 判準 4 — mutation receipt

`handoffs/run_receipts/20260818T110000Z-gap1-b4-fix-mutation.log`：§V-1..15 共 **20 條**皆 `rc=1 FAILED>=1`；baseline/post-restore **277 passed**；`[gap1-b1-mutation] ✅`；`rc=0`。

### 判準 7 — A1-24 與碼一致

| 群集 | 回歸鎖測試名 | 碼證 |
|------|-------------|------|
| N1 | `test_mutation_n1_non_whitelisted_passthrough_is_unresolved`／`test_mutation_n1_dead_enum_via_unused_constant_or_docstring_is_red` | 存在 |
| N2 | `test_non_champion_oos_degenerate_skips_path_keeps_denominator`／`test_denominator_is_path_valid_count_plus_one` | 存在 |
| N3 | `test_champion_degenerate_in_oos_is_skipped_not_indexerror`（`n_path_exclusions==2`） | 存在 |
| N4 | `test_double_champion_takes_smallest_index_hand_computed` | 存在 |
| N5 | `test_vectorized_sharpe_matches_compute_sharpe`；`pbo._sharpe_pp_1d` | 存在 |
| N6 | `_golden.py`；`test_golden_file_sha256_and_analytic_constants`／`test_hand_constants_match_golden_file`／`test_expected_max_sharpe_factor_matches_golden_file` | 存在 |
| — | `pbo.GuardResult`／`guard.reason` | `pbo.py:77-78,194` |
| — | registry G1-R11 | `needs-research` 三值＋觸發條件具名於 `IC_QUANT_GAP_REGISTRY.md` |

### 判準 8 — registry 觸發未成立

G1-R1（Optuna 接線）／R2（optimization 產出）／R4（C1 繞過）／R9（生產者側完整性）仍 blocked-by 無生產者；R3／R5 為 user-ruling 範圍外；R6／R7 needs-research 無方法；R10 blocked-by 白名單；**R11** 為本輪具名殘留（近常數容差），觸發條件「真實回測近常數且 |SR|>1e6」未成立。Verdict「需修補後收工」與 N1–N6 全修一致，無未修殘留（R11 除外且已登記）。

## Verdict 理由（一句）

B4 修補 commit `00965160` 已關閉 composer 兩條 findings（④b 雙冠廉價綠燈、近常數 sharpe 等價鎖不足），N4／N5 群集與 A1-24 回歸鎖、280 測試及 codex mutation receipt（20 條）均符合 brief，G1-R11 為 B1 語意之具名殘留而非漏修。

## 戳記（已 append）

```
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:c69a22c07dfb1c07929ee36b2781474e505dc460c5b8395844f175d91a43debc task:20260818-GAP1-B4-STAMP-R19
```

## /tmp 收尾

沙箱權限阻擋 `rm`（`Permission denied: Command blocked by permissions configuration`）；**未清**。待清項：`a*.md`、`gap1*.log`、`push*.log`、`pytest-of-louis` 等；應保留 `claude-501`、`cc-socks`、`com.google.Keystone`。

---

ASSUMPTIONS_VERIFIED: body_sha256 與 brief 一致；completeness 0 掉項；composer 兩反例關閉；strategy_validation+API 280 passed；mutation receipt 20 條；wiring W1..W4；decoupling BASELINE OK；grep momentum api import=0；gov_check --fast ✅；A1-24 回歸鎖全存在；registry 觸發未成立
TESTS_RUN: reconcile_body_hash.sh rc=0；completeness_check.sh rc=0；pytest strategy_validation+API -q rc=0 280 passed；composer 反例 2 tests passed；strategy_wiring_check.sh rc=0；bash -n strategy_wiring_check.sh rc=0；check_decoupling_imports.py rc=0；grep api import count=0；gov_check.sh --fast rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 append synth 戳記 + 本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（驗收唯讀 + 戳記 append）

STATUS: DONE
