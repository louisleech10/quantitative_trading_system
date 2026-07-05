# TEMPLATE_GATE_FIX — Grandfather 盤點（現役 docs/ SPEC/TODO）

> 掃描時間：2026-07-05（TGF-B4 Task 6.2）  
> 掃描器：`scripts/template_check.sh`（B2 硬化後版本）  
> 政策：**僅新文件適用新機檢；本表所列 FAIL 為 grandfather，不回頭追殺。**

## 政策聲明

1. 2026-07-05 前已存在且通過當時 gate 的 SPEC/TODO，**不因 template_check 加嚴而強制 retrofit**。
2. 新建或重大修訂的 SPEC/TODO **必須**通過現行 `template_check.sh`（含 FACT-RECEIPT、RISK-HIT、per-Task 三欄等）。
3. `docs/IC_PHASE0_SPEC.md` 為已知繞過探針（FACT-RECEIPT／§A 標題繞過），列 grandfather；新 IC epic 應寫新 SPEC 或另開修補 epic，不在此表自動升級。

## SPEC 掃描結果（`bash scripts/template_check.sh spec <file>`）

| 檔案 | exit | 備註 |
|------|------|------|
| docs/B7_L65_PARALLEL_SPEC.md | 1 | grandfather |
| docs/FF_DEEPAUDIT_P0_SPEC.md | 1 | grandfather |
| docs/FRACDIFF_MAXLAG_SPEC.md | 1 | grandfather |
| docs/GOV_O3EXT_R7_SPEC.md | 1 | grandfather |
| **docs/IC_PHASE0_SPEC.md** | **1** | **grandfather（缺 RISK-HIT、§A FACT-RECEIPT 等；TGF 探針標的）** |
| docs/IC_PHASE1_1a_CUT1_SPEC.md | 1 | grandfather |
| docs/IC_PHASE1_CONTRACT_SPEC.md | 1 | grandfather |
| docs/IC_RUN_SELECTOR_SPEC.md | 1 | grandfather |
| docs/TEMPLATE_GATE_FIX_SPEC.md | 0 | 現役合規（本 epic） |
| docs/VERIFY_GATE_SPEC.md | 1 | grandfather |

## TODO 掃描結果（`bash scripts/template_check.sh todo <file>`）

| 檔案 | exit | 備註 |
|------|------|------|
| docs/B7_L65_PARALLEL_TODO.md | 0 | 現役合規 |
| docs/FF_DEEPAUDIT_P0_TODO.md | 0 | 現役合規 |
| docs/FRACDIFF_MAXLAG_TODO.md | 0 | 現役合規 |
| docs/GOV_O3EXT_R7_TODO.md | 0 | 現役合規 |
| docs/IC_PHASE0_TODO.md | 0 | 現役合規 |
| docs/IC_PHASE1_1a_CUT1_TODO.md | 0 | 現役合規 |
| docs/IC_PHASE1_CONTRACT_TODO.md | 0 | 現役合規 |
| docs/IC_RUN_SELECTOR_TODO.md | 0 | 現役合規 |
| docs/TEMPLATE_GATE_FIX_TODO.md | 0 | 現役合規（本 epic） |
| docs/VERIFY_GATE_TODO.md | 0 | 現役合規 |

## 重現命令

```bash
for f in docs/*_SPEC.md; do
  bash scripts/template_check.sh spec "$f" >/dev/null 2>&1
  echo "spec $f exit=$?"
done
for f in docs/*_TODO.md; do
  bash scripts/template_check.sh todo "$f" >/dev/null 2>&1
  echo "todo $f exit=$?"
done
```
