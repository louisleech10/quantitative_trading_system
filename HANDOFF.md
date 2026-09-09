# HANDOFF — 當前任務狀態

**更新：2026-09-10 凌晨｜票：`EVTLABEL`（大；RISK a,b,c,d）｜狀態：SPEC/TODO v4 三輪三家審查收斂（R1 27／R2 16／R3 11 條全採納），戳記輪序列化進行中（codex→composer→grok）；白話簡述已寫，等戳記齊後彈窗給使用者否決；**尚未動工**。**

## 使用者本次指示（逐字要點）
> 開工前稽核 HANDOFF/memory vs repo，稽核後直接開票不要再問方向；大任務走完整管線 SPEC+TODO+三家 adversarial+白話否決；三 Phase 順序不可調；主目標原話入 SPEC §A，任何審查延後它＝否決點彈窗；全部做完才重驗 B26–B34；每批 commit 後 push、更新 白話說明/現在做到哪.md。

## 檔案
SPEC `docs/EVTLABEL_SPEC.md`／TODO `docs/EVTLABEL_TODO.md`（v4，commit `24e011dc`，TEMPLATE PASS×2）。
收斂檔 `handoffs/reconcile/20260910-evtlabel-x-review-r{1,2,3}/synth.md`（C1–C14／D1–D8／E1–E5；completeness PASS；`## 戳記` 區已加，body-hash r1 `3894fd90…` r2 `194603b5…` r3 `64a092e4…`）。
白話 `白話說明/EVTLABEL規格白話.md`（頭條＝R-4「餵 ML」邊界須使用者接受）；看板 `白話說明/現在做到哪.md`。
探針 `handoffs/20260910-probe-label-rule.py`（ASSUME-1 rc=0：h1 c2c 視窗 12 根、深度 144）、`handoffs/20260910-probe-mw-bench.py`（31×39373：單次 0.06s、50 次置亂 2.3s）。

## 關鍵裁定（詳見 synth）
效應量閘＝`|rank_biserial|≥rank_biserial_min(0.10)`（不共用 ic_mean_min）；auto 在 orchestrator stage3 依 selection 段每類 ≥10 決定；負對照 N=50 block 置亂、`q95=int(quantile(method="higher"))`、`n_observed==0` 短路；stage5 唯一守衛＝index 對齊＋長度＋`rows_frozenset` 子集（無 digest 比對）；P2 走顯式 kwarg `event_isolation`（config_override 含該鍵 ⇒ raise）；`holdout_test_row_index` 純函式供 orchestrator 與 service 預檢共用；MW 用 `nan_policy="omit"` 向量化；R-7 長視窗 `n_blocks<10` ⇒ unavailable（預期限制）。

## 下一步（順序）
1. 戳記輪：codex（`20260910-evtlabel-x-stamp-r1`，round f6815d54…）→ composer（`-stamp-r2`）→ grok（`-stamp-r3`）；每家完成後 `debt_clear` 再派下一家；用 `handoffs/20260910-EVTLABEL-X-STAMP-R{1,2,3}-BRIEF.md`。
2. 三家 APPROVED ⇒ `reconcile_stamps_check.sh` 驗 ⇒ AskUserQuestion 彈窗＋PushNotification 給使用者否決（白話檔）。
3. 使用者放行 ⇒ SPEC/TODO 標 FROZEN ⇒ B0（scaffold）→ B1（P1）…每批三家 code review、commit+push、更新看板。
4. 全部完成才叫使用者驗收 B26–B34＋新增項目。

## 踩坑（本 session）
committee_run session 名須 `<date>-<epic>-x-<kind>-r<N>`；review 派工不帶 `--spec/--todo`（那是 impl）；`--rebuild` 不接委員檔；synth 加 `## 戳記` 前不得多插 `---`（會破最後一則 finding 的 body-hash）；stamp brief 只准一個 `stamp-target:`（批次戳記其餘檔寫在正文）；hook 在開債期間會擋含 handoffs 路徑之 python 執行；`rm -rf`／heredoc python 被拒。

## 殘留
`EA-RESID-1..6`（EVTALIGN）未變；EVTLABEL R-1..R-7 於 SPEC §N，收案時登記 `docs/IC_QUANT_GAP_REGISTRY.md`。
