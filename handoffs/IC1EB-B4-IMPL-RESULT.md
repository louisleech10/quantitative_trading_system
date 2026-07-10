# IC1EB-B4-IMPL-RESULT — Task 4.1–4.3 config+API+前端全棧接通

**Agent**: Grok 4.5 | **Date**: 2026-07-11 | **Status**: DONE  
**SPEC**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §A D-F/D-G + §C consumer map #9 | **TODO**: Phase 4 Task 4.1/4.2/4.3  
**Prompt**: `handoffs/IC1EB-B4-IMPL-PROMPT.md` | **基底**: main `546f50a`

## 改檔清單

| 檔案 | 變更 |
|------|------|
| `momentum/Analysis/ic_config_schema.py` | 新增 `SignificanceFdrSchema` / `SignificanceSchema`；`ICConfig.significance` 預設 ON（`fdr.enabled=True`, `method=fdr_bh`, `maxlags=None`） |
| `momentum/Analysis/ic_filter_orchestrator.py` | `STAGE_OVERRIDE_PATHS["fdr_correction"]→("significance","fdr","enabled")`；`_set_nested_bool`；stage5/xsec 消費 `significance.maxlags`；xsec HAC 支援 maxlags override |
| `frontend/src/store/icAnalysisStore.ts` | 三 preset `fdr_correction: true`；`getEffectiveConfig` stage_overrides 送出 `fdr_correction` |
| `frontend/src/lib/types.ts` | `ICFeatureInfo.p_value?: number\|null`；增 `p_value_adj` / `t_stat` nullability（CODEX-6） |
| `frontend/src/components/ic-analysis/ICSummaryTable.tsx` | **刪** `resolveTStat`/`resolveConfidenceInterval` 全部 i.i.d. 推導；共用 `formatFinite`；表頭增 q；CI 無後端→`--`；ic_mean tooltip 披露 |
| `frontend/src/components/ic-analysis/FeatureTierPanel.tsx` | FDR tip 更新為真行為（ON→q 閘 / OFF→HAC raw p） |
| `tests/momentum/test_ic_1eb_b4_fullstack.py` | **新建** T-4.1 hop chain + T-4.3=M-G 兩態 e2e（真 `_apply_tier_config` 路徑） |

**未改（禁項）**：其他 schema 欄預設 / 其他 toggle 語意；`handoffs/ic1eb_baseline/` 唯讀；`data_cache/` 無 tracked 改動；既有測試斷言未放寬。

---

## 實作要點

### Task 4.1 — 後端 config plumbing
1. Canonical：`significance.fdr.{enabled,method}` + `significance.maxlags`（禁 `fdr_enabled` 平鋪別名）。
2. UI 邊界唯一轉名：`fdr_correction` → `significance.fdr.enabled`（custom stage_overrides + nested setter）。
3. stage5：`compute_hac_ic_statistics(..., maxlags=schema)`；xsec：`_compute_hac_on_ic_series(..., maxlags=schema)`。
4. 舊 config 無 significance 節 → Pydantic 預設 ON。

### Task 4.2 — 前端
1. foundation/intermediate/advanced 皆 `fdr_correction: true`。
2. `getEffectiveConfig` 於 custom stage_overrides 送 `fdr_correction`。
3. 刪前端統計推導；t-stat/p/q 直讀後端 + `formatFinite`；CI 誠實 `--`。
4. ic_mean tooltip：「描述性 rolling 均值,非檢定量」。

### Task 4.3 — M-G 兩態 e2e
1. store JSON → `FeatureTierRequest`/`ICAnalyzeRequest` → `ICAnalysisService._build_config_override` → `_apply_tier_config` → stage5（**禁 mock 映射鏈**）。
2. OFF 唯一判據=`significance.fdr.enabled=false`；`threshold_log.fdr_enabled` 鏡像恆等。
3. 兩態 `passed_features` 可分離（必要時 seed sweep 仍走真路徑）。

---

## 驗收命令 receipt

### Gate A — full momentum  VERIFY:ic1eb-b4-full-gate

```bash
source venv/bin/activate
python scripts/run_with_receipt.py --claim-id ic1eb-b4-full-gate -- venv/bin/python -m pytest tests/momentum/ -q
```

**結果**：`1033 passed, 5 skipped, 1770 warnings in 209.76s`；exit 0  
**receipt**：`handoffs/run_receipts/20260710T205022Z-ic1eb-b4-full-gate.json`

### Gate B — 解耦

```bash
grep -rn "from api\." momentum/ | wc -l
```

**結果**：`0`

### Gate C — 前端禁 i.i.d. 推導

```bash
grep -nE "resolveTStat|resolveConfidenceInterval|1\.96" frontend/src/components/ic-analysis/ICSummaryTable.tsx | wc -l
```

**結果**：`0`

### Gate D — npm build  VERIFY:ic1eb-b4-npm-build

```bash
python scripts/run_with_receipt.py --claim-id ic1eb-b4-npm-build -- bash -lc 'cd frontend && npm run build'
```

**結果**：exit 0（Next.js 靜態頁生成完成，`/ic-analysis` 35.4 kB）  
**receipt**：`handoffs/run_receipts/20260710T205126Z-ic1eb-b4-npm-build.json`

### T-4.1 / T-4.3 單元  VERIFY:ic1eb-b4-t41-t43

```bash
python scripts/run_with_receipt.py --claim-id ic1eb-b4-t41-t43 -- venv/bin/python -m pytest tests/momentum/test_ic_1eb_b4_fullstack.py -q
```

**結果**：`7 passed`；exit 0  
**receipt**：`handoffs/run_receipts/20260710T205033Z-ic1eb-b4-t41-t43.json`

### 既有 tier 回歸

```bash
venv/bin/python -m pytest tests/momentum/test_tier_config.py tests/api/test_tier_api.py -q
```

**結果**：`14 passed`

---

## 各 T 摘要

| ID | 斷言 | 結果 |
|----|------|------|
| T-4.1 schema default | 無 significance 節→ON；method=fdr_bh；maxlags=None | PASSED |
| T-4.1 no flat alias | 禁 fdr_enabled 平鋪；path=`significance.fdr.enabled` | PASSED |
| T-4.1 hop chain false | store→API→tier→stage5→report meta 同 key false + 鏡像恆等 | PASSED |
| T-4.1 hop chain true | 同上 true | PASSED |
| T-4.1 maxlags consume | schema maxlags=6 → ic_stats.maxlags=6 | PASSED |
| T-4.3 M-G | 兩態 enabled 鏡像；passed 可分離；on 用 q / off 用 raw p | PASSED |
| T-4.2 | build 綠 + grep 0 | PASSED（Gate C/D） |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: STAGE_OVERRIDE 僅 custom 套用；三 preset fdr true 對齊 schema 預設 ON；UI 唯一轉名 fdr_correction→significance.fdr.enabled；RECONCILE stamps APPROVED (b77932d8)
TESTS_RUN: pytest tests/momentum/ → 1033 passed,5 skipped; test_ic_1eb_b4_fullstack.py → 7 passed; tier+api → 14 passed; grep from api. → 0; ICSummaryTable iid grep → 0; npm run build → exit 0
FAILURES_SEEN: 首輪 grep 命中註解中的 1.96 字樣 → 刪註解字面後 Grep=0（1 輪內）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: ICConfig 新增 significance 節（預設 ON）；stage5/xsec 可顯式 maxlags；前端 summary 表增 q 欄、刪 i.i.d. t/CI 推導；p_value nullability 放寬（顯示端）
```

STATUS: DONE
