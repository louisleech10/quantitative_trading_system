# FF R1 consolidated review — Codex

範圍:對照 r1-claude/r1-codex/r1-composer + r1-xreview-codex/composer;未改 source。

## ① 是否漏重點
同意:未漏三方主軸;E 不整併 executor、Q5 config 化、#1 worker logging、Q3 canonical progress、Q2 retention state machine 都有收進。
補充:consolidated 把「error classification」放在 E contract 內但未展開;R2/實作應明確列入 contract tests,否則 #1/Q3/Q2 仍可能各自分類錯。
補充:Q2 漏寫「batch 繼續跑時 retention 不阻塞下一 item」是否接受;Composer 提過,會影響 UX 與暫占磁碟預期。

## ② 共識/優先序
同意:Q5(P0)→#1(P0)→Q3(P1)→Q2(P2)→E contract tests 的 reconciled order 合理。
補充:Q3 在 Codex 版原列 P0,但互審後降 P1 可接受;理由是 Q5/#1 是低風險基礎,且 Q3 需先處理 RSS 語意差。
同意:#1 與 Q5 並列 P0 成立;Q5 可先落因改動最小,#1 是批次除錯盲區,不應降到 P2/P3。

## ③ E 結論
同意:「不整併 executor,但做 contract+tests」成立。
理由:subprocess 保留 OOM/crash 隔離、wave gc/BLAS cap/per-symbol RSS;thread 保留 callback/lease/warmup/_df_cache/低延遲。
補充:adapter/GenerationRunner 可列未來選項,本輪不應為抽象而改執行模型;本輪最低必要是 Sink/schema/error/retention contracts + tests。

## ④ R2 詰問 5 點
同意:現有 5 點覆蓋主要未知:append 原子性、RSS 語意、Q2 checkpoint、contract test 最小集、P0 排序。
補充:第 3 點應拆清「整批一次 dialog vs per-item queue」與「delete/register 部分失敗如何回滾或標記」,不只 _record_item_result 切點。
補充:第 4 點需要求可證偽最小集:兩路徑同 schema/version、同 error class、retention pending/decided 狀態轉移、concurrent>1 不輸出假 current_stage。

## 總裁決
同意 consolidated 作為 R1 定案基礎;以上補充應帶入 R2,無需推翻 E 或優先序。

STATUS: DONE
