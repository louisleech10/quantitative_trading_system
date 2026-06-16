# Handoff
**Agent**: Claude | **Time**: 2026-06-17 | **Branch**: main

## 本輪完成:#4 batch_alias Phase 1+2(批次一次命名,解 100 symbol 改名 100 次)
完整中-大管線走完,**Codex code review APPROVE**,本 commit 收尾。
- **規格**:SPEC/TODO/MANIFEST V4(docs/BATCH_ALIAS_*.md),經 **4 輪 Codex adversarial**(r1 FAIL 2B/4M/2m → r2 → r3 → r4 PASS),每輪抓真實缺口逐輪收斂:batch_id 跨進程鏈→禁 mutable self 顯式穿透→multi-TF 主路徑遺漏→6 個 _layer7 呼叫點全涵蓋。
- **實作**:Composer 2.5 寫 P1(後端 registry/API/cleanup)+P2(前端 Explorer/Run 管理分組+整批 rename)。
- **協調者驗收抓並修 3 bug(防假綠生效)**:① registry.add 新 entry 無條件 pop batch_alias→僅 batch_id is None 時 pop;② 前端新測試漏 import jest-dom;③ 6 個 test fake factory 的 _layer7 簽名缺 batch_id=None(Codex review 抓到的回歸,跨 8 檔 17 失敗)。
- **驗收**:後端 100 passed(含 test_batch_alias 17+所有 _layer7 回歸+run_lifecycle)、前端 39 passed(新 16)、npm run build 過、解耦 0、Codex review r2 APPROVE。
- **語義**:三態 overwrite(同 batch_id 保留 batch_alias/換 batch_id reset/None merge-preserve);batch_alias 不覆寫 per-run alias;set_batch_alias 對 deleting→409;auto-cleanup 候選+mark_deleting 都護 batch_alias。

## 已知無關問題(非本任務)
- frontend `strategy-components.test.tsx` pre-existing 壞(缺 @/components/strategy/SignalTooltip,commit 6be0862,未碰 strategy)。

## 待辦 ticket(另開)
- float16 strict/training 讀升 float32 可選後續(docs/FLOAT16_STORAGE_EVALUATION.md)。
- CGSA raw-sink ADF/d* tier-gated 並行(需 24/32GB 硬體)。
- batch_alias Phase 3:一等 batch entity(batches.json),目前 batch_id/batch_alias 存 run registry([BA-9])。

## 執行端分工(2026-06-15 使用者定)
- 中/大實作=Composer 2.5 + Codex review;小=Claude 自己做。技術決策走委員會;中途自主 commit。
