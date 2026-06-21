# FF 一致性 FINAL 審查 — Composer 2.5（read-only）

對照：FINAL vs 我 R2、Codex/Claude R2、雙向 xreview。

## ① R2 重點遺漏？
**無重大遺漏。** ✎ 三校正（E 薄 normalize mandatory、Q2 磁碟背壓、#1 smoke P0 門檻）與 xreview 裁決一致。我 R2 第 5 條 parity（batch 無 `browse_task_id` 直至 retention decided）已納入。Codex 背壓、tombstone、`retention_error`、Phase A/B、Dialog 擴展、T-A 留後均齊。

## ② 三校正統整
**同意。** mandatory = 共用 schema/error enum + **單一 normalize 薄函式**（非僅 TypedDict）；拒厚 Sink/runner adapter 與我 xreview 一致。Q2 soft 閾值+暫停 wave 與非阻塞並存正確。#1 父+1~4 子 assert 無破行/缺行 = P0 完成門檻正確。

## ③ parity / RSS / staging / 優先序
**同意，一處補充。** 5 條 parity 可證偽、互斥 `process_rss_mb`/`worker_rss_mb`、deprecate `current_rss_mb`、Q5→#1→E(P0c)→Q3→Q2-A(含背壓)→Q2-B 均正確。staging 切點語意對（`_record_item_result` 成功即 register→改 checkpoint 後/register 前），**檔名應為 `feature_factory_batch_service.py:581-583`**，非 `batch_service`。

## ④ 可否作實作依據？
**同意作為依據**；實作前建議補兩行非阻塞細節：(a) parity 覆蓋 register 延後路徑須在 Q2-A 前或同 PR；(b) Q3 event 明示 `schema_version`（parity ① 已含，payload 定義可再寫死）。

**裁決：同意（含上述兩點補充，非反對）。**

STATUS: DONE
