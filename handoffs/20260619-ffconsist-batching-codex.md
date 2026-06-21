# FF 一致性整併 — Codex 獨立分級/批次評估

依據:HANDOFF.md、CLAUDE.md a-d、20260619-ffconsist-FINAL.md、batching-claude.md。

## 分級判斷
- Q5 access_log env:小。啟動/config/log noise,不碰資料/契約/多下游。
- #1 worker logging+smoke:中。碰 batch worker 入口與多進程 logging,但只觀測、不改資料流;smoke 可局部驗。
- E-normalize:中-大。薄函式本身小,但它是單/多路徑 shared payload contract,命中(b);不能當小。
- Q3 progress/RSS/WS/TS/Zustand:中-大。跨 backend WS + frontend store/UI,命中(b);無數值(a)但契約漂移風險高。
- Q2-A retention nonblocking+backpressure+staging+checkpoint+resume+UI:大+。命中(b)(c),且持久化/磁碟/恢復/前端決策同時變。
- Q2-B bulk-delete:大。命中(b)(c),刪檔+checkpoint/RunManager/quality/tombstone 一致性;不是中-大。

## 對 Claude 批次的評語
- B1=Q5+#1:同意合批。Q5 太小,併入 logging 批可減 ceremony;仍按「中」管線,不可再塞 E/Q3。
- B2=E+Q3:同意功能合批,但不同意標「中」。progress contract 跨雙路徑+WS+前端,應用「中-大/大治理」處理。
- 不建議 B1+B2 再併:terminal logging 與 progress schema 是不同契約面,合併會擴審查面且降低 revert 清晰度。
- Q2-A 不宜整包一次塞完:它比一般大任務更寬,建議拆成 backend core 與 frontend decision 兩批,共享同一大任務設計文件但分 SPEC/TODO。

## 最終批次表
- B1〔中〕Q5 + #1 + multi-process smoke。驗收:access_log env 可開關、batch child log 有[pid sym tf]且無破行/缺行。
- B2〔中-大,按大任務治理〕E-progress normalize + progress parity + Q3 RSS分欄/WS/TS/Zustand。驗收:雙路徑 schema_version/error-class/current_stage/concurrent/RSS互斥分欄一致。
- B3〔大〕Q2-A backend core:retention normalize/parity、defer register staging、checkpoint pending/decided/error、resume rebuild、disk backpressure、API/WS queue contract。
- B4〔中-大〕Q2-A frontend decision:completionQueue 展開面板、per-item keep/discard/error/retry 狀態、與 B3 API/WS contract 對齊;不改 backend state machine。
- B5〔大〕Q2-B transactional bulk-delete:tombstone、checkpoint/RunManager/quality summary/磁碟同步失效、partial failure retry。

## 依賴順序
B1 → B2 → B3 → B4 → B5。
理由:Q5/#1先解 log;Q3 首次改 progress payload 時必帶 E-progress;retention E 在 B3 首次用;B4 依賴 B3 queue/decision contract;B5 必等 retention state/tombstone 語義定型。

## 挑戰點
Claude 低估 B2 風險:按 CLAUDE.md (b),它不是普通中型。Q2-B 也不應稱「大/中-大」,刪除與一致性恢復是實打實大型。
