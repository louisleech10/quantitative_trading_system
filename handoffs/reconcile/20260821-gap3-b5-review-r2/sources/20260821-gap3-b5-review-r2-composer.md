# GAP-3 B5 review R2 — composer（closure／sentinel）

task-id: 20260821-GAP3-B5-REVIEW-R2  
family: composer  
brief-kind: review  
brief: handoffs/20260821-gap3-b5-review-r2-brief.md  
patch: `git diff eb3f9b4e..HEAD`  
R1 裁決: handoffs/reconcile/20260821-gap3-b5-review-r1/synth.md

## Verdict：可進三家 RECONCILE-STAMP（本家 1/1 CLOSED；本輪無新 finding）

### 必答

1. **原提出方逐條 CLOSED？**

   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | COMPOSER-R1-P3-00 | **CLOSED** | R2 重跑 brief 必答＋§0 assumed 攻擊後仍 0 條 composer finding；他方 10 條修補均已 RECHECK 綠（見下表） |

2. **修補是否引入新問題？**

   **無**（見 sentinel `COMPOSER-R2-P3-00`）。逐項攻擊 brief 五點：

   | 攻擊點 | 判定 | 碼證 |
   |---|---|---|
   | ① 全 K 線 rule＝事件成員＋`label_threshold=0.0` 是否誤導 | **不成立** | `pipeline.py:147-149` 回傳 `rule`／`label_threshold_note` 明寫 estimand；`EventTablesPanel.tsx:214-215` 區塊標「rule＝事件成員」；`AllBarsTable` 並排 `prevalence_full`／`prevalence_learn`（D4-3）；`-k all_bars` API＋momentum 雙綠 |
   | ② `label_value`＝`price_change` 單位／方向 | **正確** | `eventExport.ts:82-83` short 取負、小數非百分比；vitest `GROK-R1-P1-02` 斷言 long 0.052／short -0.052／缺欄不寫 |
   | ③ CSV chunk 解析改欄位語意 | **未改** | `parse_upload` 仍走 `_csv_rows_to_records`（`677-706`），僅外層 `read_csv(chunksize=5000)`；dtype=str＋keep_default_na=False 與改前一致 |
   | ④ `_canon_cols` casefold 誤傷合法欄名 | **未誤傷** | casefold 只用於 `looks_legacy`／`looks_new_schema` 偵測（`631-640`）；實際解析保留原始欄名；`-k case_variants` → 1 passed |
   | ⑤ `elif event_timestamps` 影響 query-only 路徑 | **未影響** | `ic_analysis_service.py:1226-1236` query 分支優先；timestamps-only 才 elif；`-k ic_timestamps` 三態（只 ts／只 query／皆無）→ 1 passed |

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**

   **是（composer 本輪 APPROVED）**——本輪複驗：`gap3_import` 12 passed、`event_samples` 229 passed、`plain_docs_sync` rc=0、`vitest gap3` 17 passed、`pendingFeatures` 4 passed；receipt `20260821T230000Z-gap3-b5-r1-fix-gate.log` 與 `gap3_import_scale.json`（api_path 10k／0.382s／200 OK）一致。

### 他方 R1 複核（非原提出方）

| ID | 複核 | RECHECK 摘要 |
|---|---|---|
| CODEX-R1-P1-01 | **複核同意 CLOSED** | `-k ic_timestamps` → 1 passed；vitest payload 含 `event_timestamps` 序列化 |
| CODEX-R1-P1-02 | **複核同意 CLOSED** | vitest `canonicalSourceText`＋`node:crypto` 獨立重算；`sha256Hex` 無 subtle ⇒ throw |
| CODEX-R1-P1-03 | **複核同意 CLOSED（部分）** | `gap3_import_scale.json` api_path 10k／0.382s／200；G3-R10 殘留 registry＋pendingFeatures 一致；串流未做＝R1 已裁 |
| CODEX-R1-P1-04 | **複核同意 CLOSED** | `-k all_bars` API 1 passed；momentum `test_analyze_tables_includes_all_bars_event_membership` 1 passed；UAT B8b／B9b 已入 checklist |
| CODEX-R1-P2-05 | **複核同意 CLOSED** | `grep -c '^def create_event_\|^def create_condition_'` → **1**；`-k factories` → 1 passed |
| CODEX-R1-P2-06 | **複核同意 CLOSED** | `-k case_variants` → 1 passed（BOM／引號／大寫 marker） |
| GROK-R1-P0-01 | **複核同意 CLOSED** | `bash scripts/plain_docs_sync_check.sh` → rc=0（本輪） |
| GROK-R1-P1-01 | **複核同意 CLOSED** | `grep 'GAP-3 開發前'` → 無命中；G3-R9／G3-R10 入 registry＋pendingFeatures |
| GROK-R1-P1-02 | **複核同意 CLOSED** | 同 CODEX-R1-P1-04＋vitest label_value |
| GROK-R1-P1-03 | **複核同意 CLOSED** | 同 CODEX-R1-P2-05 |
| GROK-R1-P2-01 | **複核同意 CLOSED** | `-k gap3_import` → **12 passed**（敘事已改 receipt 實測） |
| GROK-R1-P2-02 | **複核同意 CLOSED** | `-k ic_seconds` → 1 passed；model description epoch ms＋`event_timestamps_ic_seconds` 秒欄 |

### R1 閉合逐條（原提出方重跑）

**Closure P3-00（原 ID COMPOSER-R1-P3-00）— CLOSED**

- R1 sentinel 聲稱 composer 視角 0 條實質 finding；R2 重跑同一必答框架＋brief 五點攻擊後仍 0 條新 finding。
- 他方 R1 十條修補均已獨立 RECHECK 綠；R1 時 composer 已標「B 段 conditional_ic／全 K 線缺口（非 BLOCKING）」——現已由 X4 修補（all_bars＋label_value＋UAT B8b／B9b），不構成 OPEN。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：全 K 線以「事件成員」為 rule 是唯一可得訊號；`prevalence_full` vs `prevalence_learn` 並排即 D4-3 揭露 | **成立（攻擊不推翻）** | 匯入管線無模型分數（G3-R9 已登記）；`pipeline.py:133-149` score=1@t0；前端並排兩率＋區塊標 rule；後端 `rule`／`label_threshold_note` 欄供 API 消費者 |
| **assumed**：串流／async worker 以 G3-R10 登記即足 | **成立（攻擊不推翻）** | W10 記錄型不設門檻；CSV 分塊＋API 10k 0.382s receipt 已入 `gap3_import_scale.json`；route 仍 `file.read()` 全檔——屬 G3-R10 明示殘留，非本輪修補引入 |

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R1-P3-00 閉合；他方 10 條 R1 修補複核皆 CLOSED；修補 diff 五點攻擊均不成立；本輪無 R2 新 P0–P2 缺陷。

**碼證**: B5 Gate 子集本輪複驗：`pytest tests/api/ -q -k gap3_import` → **12 passed** rc=0；`pytest tests/momentum/event_samples/ -q` → **229 passed** rc=0；`bash scripts/plain_docs_sync_check.sh` → rc=0；`cd frontend && npx vitest run gap3` → **17 passed** rc=0；`npx vitest run pendingFeatures` → **4 passed** rc=0。專項：`-k ic_timestamps` 1 passed、`-k all_bars` 1 passed、`-k case_variants` 1 passed、`-k ic_seconds` 1 passed、`-k factories` 1 passed；`grep -c '^def create_event_\|^def create_condition_' momentum/factories.py` → 1；`gap3_import_scale.json` api_path n_records=10000 wall_clock_s=0.382 http_status=200。

**來源摘要**: handoffs/reconcile/20260821-gap3-b5-review-r1/synth.md#8a1f2e3b4c5d；handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log#f1a2b3c4d5e6；momentum/Analysis/event_samples/pipeline.py#9c8d7e6f5a4b；frontend/src/lib/eventExport.ts#3e4f5a6b7c8d；handoffs/20260821-gap3-b5-review-r2-brief.md

正文：閉合義務本家 1/1 CLOSED；他方 10/10 複核同意；§0 兩條 assumed 攻擊不推翻。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief 兩條 assumed 已攻擊（上表），均成立。

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/api/ -q -k gap3_import → 12 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and ic_timestamps" → 1 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and all_bars" → 1 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and case_variants" → 1 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and ic_seconds" → 1 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 229 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k all_bars → 1 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k factories → 1 passed rc=0
bash scripts/plain_docs_sync_check.sh → rc=0
cd frontend && npx vitest run gap3 → 17 passed rc=0
cd frontend && npx vitest run pendingFeatures → 4 passed rc=0
grep -c '^def create_event_\|^def create_condition_' momentum/factories.py → 1
read gap3_import_scale.json api_path → 10000 records, 0.382s, 200 OK
```

ASSUMPTIONS_VERIFIED: 上述命令＋`pipeline.py:112-149`／`eventExport.ts:19-94`／`ic_analysis_service.py:1226-1236`／`case_import_service.py:631-706` 對讀  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT: handoffs/20260821-gap3-b5-review-r2-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
