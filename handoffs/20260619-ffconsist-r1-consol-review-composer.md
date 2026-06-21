# R1 統整審查 — Composer 2.5（read-only）

對照：`r1-{claude,codex,composer}.md` + `r1-xreview-{codex,composer}.md` vs `r1-consolidated.md`。

## ① 漏點檢查
**同意** 互審糾正已納入：E contract+tests、glue 漂移風險、Q5 env 開關、#1 non-rotating/queue 可選、Q3 concurrent>1/RSS 雙語意、Q2 整批 dialog+state machine、staging 需實測 `:583`。
**補充** 仍漏：(a) Composer 子進程 `FFACT_API_LOG_PATH` 沿用 case_search 路徑；(b) xreview-codex「batch rolling 10/100 現 message 是否夠」未進 R2；(c) Composer 假設「保留對話不阻塞下一 symbol」未列 R2；(d) Codex Q2 拆段（prompt+alias 先 vs 批量 delete endpoint 後）統整併成 P2 單塊，R2 宜拆；(e) E 本輪「抽 Sink 類」vs「僅 schema+tests」line7/line23 略歧義，R2 需釘死範圍。

## ② 共識／優先序
**同意** reconcile `Q5(P0)→#1(P0)→Q3(P1)→Q2(P2)→E(contract 隨項)`；優於 Codex「Q3+Q2 同 P0」與自家原 P3/P4；Q5 設開關非硬關亦對齊雙審。
**補充** Q2「使用者已定」與 P2 不矛盾，但 Codex 原 P0 prompt 的急迫性被淡化——R2 應確認是否可 Q3 後即做「僅 prompt+延後 register」MVP，endpoint 後補。

## ③ E 結論
**同意**「不整併 executor、統一觀察契約+contract tests」成立；OOM/TA-Lib/Numba/lease/_df_cache/BLAS cap 論點三方+雙審一致；糾正 Claude「抽層回報低」正確。
**補充** 維持裁決可接受，但本輪至少應有共用 payload schema + 雙路徑 parity tests；Sink 抽象可薄封裝，不必等 GenerationRunner adapter。

## ④ R2 五點夠嗎
**同意** 五點覆蓋 #1 原子性、RSS 語意、Q2/checkpoint 切點、contract 最小集、P0 內序——核心足夠。
**補充** 建議 R2 加 2–3 項：rolling message 是否足夠；retention 是否阻塞 batch 下一 wave；Q2 MVP 與 bulk-delete endpoint 分期；E 本輪 Sink 類是否 mandatory。

## 總評
**同意** 統整為可開 R2 的 reconcile 底稿；E 與優先序大方向正確。
**反對** 無重大方向性反對；上述為實作邊界與 R2 議程補洞，非推翻統整。
