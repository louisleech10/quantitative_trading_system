# B3 v2 Adversarial — Composer 2.5 (2026-06-21)

SPEC=`docs/B3_BATCH_RETENTION_SPEC.md`(v2) TODO=`docs/B3_BATCH_RETENTION_TODO.md`(v2) 對照=`handoffs/20260619-b3-adv-composer.md`

## Verdict：需修補（設計轉向 PASS；SPEC 殘缺可小 patch 後派工）

## 逐項確認
① **§A 事實修正已納入** — grep/Read 複核：FeatureRegistry.add `feature_factory.py:3227`、browse `batch_service.py:606`、quality `batch_adapters.py:34`、checkpoint `_build_initial_checkpoint` `889-916`(非 v1 誤標 `resume_batch:178-209`)、`DELETE /runs`→`delete_run` `routes:103`、completionQueue `store:82`、page modal `page.tsx:510`。小瑕疵：§A「deleteRun:546」實指 store `deleteRun:542` URL，非 `RunRetentionDialog.tsx:61`。
② **post-hoc mark 避開多下游不一致** — PASS。三副作用(3227/606/artifact)不延後，retain≈今日；v1 BLOCKING① 根因已解。殘留：pending 窗內 run 在 RunManager/browse/quality **可見可互動**（設計取捨，宜 §A 明示）；使用者經 RunManager 手刪 vs checkpoint pending 需 reconcile（decide 404/terminal）。
③ **背壓真刪+真實 free-space** — PASS。discard 重用 `delete_run` 真釋 bytes；`shutil.disk_usage`+wakeup+無 pending hard-pause 解 v1 記帳死鎖。殘留：`disk_usage` **量測 path** 未定；閾值僅「tier 預設/T-C 樣式」無 batch 預設值；`RunBusyError`(lease) 致 discard 失敗時背壓可能延長。
④ **前端 source+discard≠deleteRun** — 大致足。batch 現不經 `enqueueCompletion`(僅 `GenerationProgress:96-97` 單 flow)。缺口：**未明定** `RunRetentionDialog` 僅 `source==='single'` 才開（若 batch 入隊會誤彈 modal）；`enqueueCompletion` 須預設 `source:'single'`。
⑤ **crash/並發/flag-off** — 較 v1 大幅補齊(abc matrix、per-item CAS、`-k retention_flag_off` spy)。殘留：**flag env 名/預設仍缺**；§C「delete_run 已刪 no-op」與 `service.delete_run` 雙不存在→`KeyError/404` **不符**（冪等應在 decision 層看 checkpoint terminal）；batch `status=completed` 與 item retention pending 並存語意未寫。

## Findings（按嚴重度）
| ID | 級別 | 項 |
|---|---|---|
| F1 | MAJOR | flag env 名+預設值未定（實作/測試 gate 缺口） |
| F2 | MAJOR | `RunRetentionDialog` 須 guard `source==='single'` 或 batch 禁入 completionQueue |
| F3 | MAJOR | §C 冪等表述與 `delete_run` 404 語意衝突→改「decision 層 terminal 冪等」 |
| F4 | MINOR | `shutil.disk_usage` path + 背壓閾值預設需落點 |
| F5 | MINOR | pending 窗可見性+RunManager 手刪 reconcile 宜入 §V |
| F6 | MINOR | batch completed+pending retention 狀態機宜一句 |

HANDOFF_NOT_UPDATED: read-only；本檔為指定交付
STATUS: DONE
