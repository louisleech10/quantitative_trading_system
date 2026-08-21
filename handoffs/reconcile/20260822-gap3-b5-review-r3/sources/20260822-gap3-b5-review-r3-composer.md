# GAP-3 B5 review R3 — composer（閉合輪）

task-id: 20260822-GAP3-B5-REVIEW-R3  
family: composer  
brief-kind: review  
brief: handoffs/20260822-gap3-b5-review-r3-brief.md  
R2 修補 diff: `git diff c062dcda..HEAD`  
R2 收斂: handoffs/reconcile/20260821-gap3-b5-review-r2/synth.md  
修後 receipt: handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log

## Verdict：需修補後 stamp（產品 Gate 子集全綠；`plain_docs_sync_check` 本輪 rc=1——看板未隨 1c54049b 同步，見 COMPOSER-R3-P2-01）

### 必答

1. **原提出方 R2 各條 CLOSED／OPEN（composer 非原提出方 → 複核）**

   | ID | 原提出方 | 複核 | 本輪 RECHECK 摘要 |
   |---|---|---|---|
   | CODEX-R2-P1-01 | CODEX | **複核同意 CLOSED** | `pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar` → **1 passed** rc=0；k=2 三事件 `n_signal_bars=3`、`indexed_at=decision_bar_open_ms`；混合 k ⇒ `batch_not_single_valued` |
   | CODEX-R2-P1-02 | CODEX | **複核同意 CLOSED** | `npx vitest run gap3` → **17 passed** rc=0（含 CODEX-R2-P1-02：h=2→future_2bar_return、h=4→future_4bar_return、short 取負、缺欄不寫） |
   | CODEX-R2-P1-03 | CODEX | **複核同意 CLOSED** | `pytest tests/api -q -k "gap3_import and verify"` → **2 passed** rc=0；JSON+verify ⇒ 400 `verify_unsupported_on_json_endpoint` 且未落檔；檔案端 digest 不符 422、關閉 verify 可收 |
   | CODEX-R2-P2-01 | CODEX | **複核同意 CLOSED** | vitest gap3 disclosure testid 斷言綠；`EventTablesPanel.tsx:114-123` 渲染 rule／estimand_note／label_threshold_note／manifest／signal_mapping |
   | GROK-R2-P2-01 | GROK | **複核同意 CLOSED** | R3 brief fact-verified 與 receipt 已改 **230** passed；本輪 `pytest tests/momentum/event_samples/ -q` → **230 passed** rc=0（R2 之 232/229 漂移已訂正） |

   **己方 R2**：R2 為 `COMPOSER-R2-P3-00` sentinel（0 條）——本輪仍無原提出方反例需重跑，維持 CLOSED。

2. **修補是否引入新問題（brief 四點攻擊）**

   | 攻擊點 | 判定 | 碼證 |
   |---|---|---|
   | ① 訊號標決策根後 `entry_price_semantic=trigger_open` 之 entry 仍取觸發根 open | **語意自洽（不開 finding）** | `pipeline.py:135-151` 訊號標在 `vals[i-k]`（決策根）；`all_bars_eval.py:170-179` 迴圈索引 `i`＝觸發根，score 取 `ot[i-k]`、entry `trigger_open`⇒`open_[i]`（D1-6 刻意分離決策根訊號 vs 觸發根進場）；`alignment.py:84-94` 同義映射 |
   | ② `label_value` 改欄後 `/search` 缺 horizon 欄 ⇒ 條件 IC 全 unavailable；匯出 UI 是否需事前提示 | **assumed 成立（不開 finding）** | `eventExport.ts:81-86,118-120` 缺 `future_{h}bar_return` 不寫欄並記 `skipped`+JSON `note`/`label_value_source`；搜尋結果 schema 含 `future_1..12bar_return`（`types.ts:49-60`）；匯出 UI 無 modal 但 JSON 內嵌說明＋後端 conditional IC loud unavailable——優於寫入語意錯值 |
   | ③ JSON 端點拒 verify 是否讓「有來源檔」情境無路可走 | **不成立** | `api/routes/case.py:166-171` JSON 明拒並指向 `/case/import-events` 檔案端點；`eventExport.ts:118` `verify_note` 說明 digest 綁 canonical 搜尋來源非匯出 body |
   | ④ disclosure 是否洩漏過多內部欄位 | **不成立（刻意 estimand 揭露）** | 僅渲染 API 已公開之 rule／notes／manifest 摘要／signal_mapping 計數；vitest `event-allbars-disclosure` 逐 testid 斷言；無 credentials／raw events |

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**

   **產品子集全綠、plain_docs 紅**——本輪：`gap3_import` **14 passed** rc=0；`event_samples/` **230 passed** rc=0；`-k decision_bar` 1 passed；`-k "gap3_import and verify"` 2 passed；`npx vitest run gap3 pendingFeatures` **21 passed** rc=0；`plain_docs_sync_check` **rc=1**（見 P2-01）。**UAT 可排程**（產品行為已驗）；**RECONCILE-STAMP 前**須同步 `白話說明/GAP-3施工進度.md` 使 plain_docs rc=0。`npm run build` 依 brief 只准一家跑——引 receipt rc=0，本輪未重跑。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：全 K 線 rule＝事件成員、`label_threshold=0.0` 已 disclosure，estimand 誤讀風險可接受 | **成立** | `pipeline.py:160-164` rule+estimand_note+label_threshold_note；UI disclosure 區塊動態渲染 threshold note（`EventTablesPanel.tsx:114-117`） |
| **assumed**：`label_value` 缺欄「不寫+skipped+loud unavailable」優於語意錯值 | **成立** | vitest CODEX-R2-P1-02 綠；export `note`/`skipped`/`label_value_source` 三元揭露 |

## COMPOSER-R3-P2-01

**斷言**: HEAD 上 `plain_docs_sync_check.sh` 實跑 **rc=1**——`白話說明/GAP-3施工進度.md` 最後提交 bcabb668（R1 看板），WATCHED 路徑已在 **1c54049b**（R2 五條修補）改動；與 brief／receipt fact-verified「plain_docs rc=0」不一致，stamp 前須 doc 同步。

**碼證**: `bash scripts/plain_docs_sync_check.sh` → rc=1，stdout「✗ 過期: 白話說明/GAP-3施工進度.md … WATCHED 最後改動 1c54049b，晚於本檔 bcabb668」；`git log -1 --oneline 白話說明/GAP-3施工進度.md` → bcabb668；`git log -1 --oneline momentum/Analysis/event_samples/pipeline.py` → 1c54049b。`RECHECK:` 更新看板 R2 修補摘要後重跑 plain_docs 須 rc=0。

**來源摘要**: handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log#c8f2a1b0e3d4；handoffs/20260822-gap3-b5-review-r3-brief.md#f9e8d7c6b5a4；scripts/plain_docs_sync_check.sh#1a2b3c4d5e6f

正文：[MINOR] 信心度=High。不影響產品行為或 pytest/vitest 子集；屬 Gate 完整性／敘事對帳（摩擦八十八同類）。修法：同 commit 或 stamp 前 commit 更新 `白話說明/GAP-3施工進度.md`（R2 修補＋計數 230／api 14）。Codex／Grok 對 R2 產品修補之 CLOSED 複核不受阻。

## 被當成事實的未驗證假設（§0）

brief 兩條 assumed 已攻擊（上表）均成立；receipt「plain_docs rc=0」在 **HEAD doc 未同步** 前提下不成立（見 P2-01）。

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/api/ -q -k gap3_import → 14 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and verify" → 2 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar → 1 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 230 passed rc=0
cd frontend && npx vitest run gap3 → 17 passed rc=0
cd frontend && npx vitest run gap3 pendingFeatures → 21 passed rc=0
bash scripts/plain_docs_sync_check.sh → rc=1（看板過期）
npm run build → 未本輪重跑（brief 禁並行）；引 receipt rc=0
```

ASSUMPTIONS_VERIFIED: 上述命令＋`pipeline.py:113-167`／`all_bars_eval.py:68-82,170-179`／`eventExport.ts:60-121`／`EventTablesPanel.tsx:97-124`／`api/routes/case.py:166-171` 對讀  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: plain_docs_sync rc=1（已列 P2-01）  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT: handoffs/20260822-gap3-b5-review-r3-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
