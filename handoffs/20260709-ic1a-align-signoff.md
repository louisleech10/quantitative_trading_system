# handoff ic1a-align-signoff — Composer append

**時間**: 2026-07-09

## 正在做
- 1-align 獨立數據正確性簽核完成 → `handoffs/IC1A-ALIGN-SIGNOFF-composer.md`

## 待辦
- 等 Claude + 第三方（若需）簽核後合併裁定

## 阻塞
- none

## 本次決策
- 五項探針全 PASS；golden RCA 比對用 `baseline_old`（full-sample），`baseline_new` 驗 OOS 結構
- production `return_type=simple` → Tier-2 log float32/64 差距不阻擋本次縱向簽核

## 踩坑提醒
- 手算 oracle 必須對齊 `config.labels.return_type`（simple vs log）；不可一律用 log
- `summary_table` 欄名為 `feature_name` 非 `feature`；removed 在 `filter_log.stage5_thresholds`
