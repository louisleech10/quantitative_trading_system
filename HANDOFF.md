# Handoff
**Agent**: Claude | **Time**: 2026-06-18 | **Branch**: main

## 任務 A ✅ 完成 push (:4109 ref-cache 修正 + 防假綠回歸測試)

## 任務 B ✅ 完成 — L6.5 預處理正確性強化
子項1 移 legacy(IC-First 唯一) + 子項3 釘死 causal True;**子項2 walk-forward d* 三方實證否決**(無下游價值,記憶 project-dstar-walkforward-rejected)。

全程:現況實測 → brief/SPEC/TODO → 雙家族 adversarial reconcile → Codex 實作/Composer review(分批 B0-B3b) → 三方資料正確性簽核。

| 批 | commit | 內容 |
|---|---|---|
| B0 | 751067b | golden baseline builder |
| B1 | e8b62c9 | causal 釘死+傳播測試+6測試重寫 |
| B2 | f6bf409/6d749ba/4d8cae7 | 移 legacy 全棧+F1-F4+frozen-doc |
| B3a | 1cbcd25/d829754 | causal 死碼清理+B2review#1-6+config_hash golden重生 |
| B3b | 7e9d083/9cdf78a | 剩餘死碼清理+三方資料正確性簽核 |

**三方簽核「資料正確」**(真實 kline 10×3,各自獨立腳本):Claude(PIT+隔離)、Composer(byte parity/PIT雙切點/隔離30對/NaN·inf/multi-TF merge值守恆)、Codex(merge 2000值守恆/split無洩漏/30對隔離)。

**驗證**:golden --check PASS(IC-First byte不變);全 feature_engineering suite 622 passed(B3a後);B3b後 my-env 188 passed。

⚠️ **副作用(已知,正確)**:移除 ic_first_pipeline config 欄→default config_hash 變(57c4→1dbe)→現有 data_cache 特徵快取失效需重生。

## Pre-existing(非本線)
- perf smoke test_batch1_followup flaky(負載下偶發,單跑PASS,忽略)。
- joblib/loky slow-path parallel 測試在受限 sandbox(Codex)缺 semaphore 權限 fail;非受限環境 PASS。

## 下一步(任務 B 已完,新方向待使用者指示)
原研究路線:crypto 單市場 FF→IC→ML→回測 完整版;IC Gatekeeper 真實 kline 端到端驗證(79 IC 單元測試全合成資料,從沒真實端到端)。數據源擴充延後。

## 執行端分工
中/大實作 Codex(gpt-5.5,`codex exec -m gpt-5.5`) + Composer(`cursor-agent -p --force --output-format text --model composer-2.5`)review。本任務因實作一致性全程 Codex 實作。派工被擋先查根因(記憶 feedback-dispatch-blocked-investigate-cause)。

## FF 收尾打磨(2026-06-19,T1/T2/T-C 完成)
使用者手動跑 2×2 揭露的 3 點 + log 分析,三方委員會後:
- **#1 UI 接力順序註釋** ✅ commit(header 分「生成階段 vs IC篩選後」)。
- **T1 log 噪音** ✅ commit(消雙記+刪Started+path-filter;**需重啟後端生效**)。
- **T2 批次 layer 觀測性** ✅ commit+Codex review(Composer 實作,5缺陷修畢):worker→layer_metrics.jsonl→父週期tick→WS→前端;補 #2(batch看不到layer)+F1(per-layer RSS落地)。
- **T-C CGSA L3 累積磁碟預檢** ✅ commit+Codex review:L3 persist前估累積footprint,不夠提早abort(env FFACT_CGSA_DISK_PRECHECK/RESERVE_GIB可調)。修磁碟撐爆事故(437K×float32=35.6GB,L3-L6累積)。
- **擱置**:T-A per-layer串流釋放(P1,scaffold已存,砍峰值根本解)、T-B float16暫存(P2需A/B簽核)、T-D 為何以前28GB夠(取證)、.claude/gstack 1GB清理(使用者決定)。
- 重啟後端重跑 2×2:乾淨log(T1)+即時layer進度與RSS(T2)+磁碟不夠提早abort(T-C)。

## FF 一致性整併 — 實作中(兩輪三方委員會定案後)
觀測性層完成:
- **Q5**(P0a)✅ uvicorn access_log env 開關(terminal 噪音預設關,FFACT_UVICORN_ACCESS_LOG=1 恢復)。
- **B1 #1**(P0b)✅ batch worker non-rotating FileHandler 進當日檔(FFACT_API_LOG_PATH)+[pid sym tf]+smoke。Codex review PASS(minor:idempotent T-A 再收緊)。
- **B2 E-normalize+Q3**(P0c+P1)✅ 共用 FeatureProgressEvent+normalize 單一出口+RSS 互斥分欄(process_rss_mb/worker_rss_mb,current_rss_mb 雙寫過渡)+schema_version int+parity5。Codex review 攔3 BLOCKING+#4 全修。**教訓:前端驗收須跑 vitest。**
- **B3 Q2-A**(P2,大)✅ 批次保留對話。使用者選「discard 即刪」→ **post-hoc mark**(run 照常生成+register 不延後→多下游一致)+ discard 重用 `delete_run` 即刪(背壓自洽)+ 真實 `shutil.disk_usage` 背壓+wakeup+hard-pause observable + crash matrix abc + per-item lock + flag `FFACT_BATCH_RETENTION` 預設關 + 前端 BatchRetentionPanel(source 區分,非 N modal,不打 deleteRun)。**兩輪雙家族 adversarial**(4 BLOCKING→post-hoc 轉向)+Codex review 兩次抓假綠修真。後端 31 pytest + 前端 21 vitest + byte PASS。非阻塞 hardening note:RunRetentionDialog 未來可改 find(non-batch) 防 starve(現不可達)。
- **B5**(大)✅ 批次日期 bug 修復:跨棧加 date(Pydantic+前端 hook+threading+checkpoint resume+7 mock)。strict-window(止血)。hermetic 測試(B5 教訓:整合測須重導 tmp data_cache_path+FFACT_CGSA_WORK_DIR)。詳 [[project_batch_date_bug]]。
- **B6**(大)✅ warmup-then-trim(**選項1**:使用者定,不承諾全範圍 parity,目標前段可用+run自洽)。max_warmup全源(L1 advanced/L2/L3/L4/**L5 cross-sectional**/L6.5/native-tf/validator)+OutputWindow+per-TF載warmup+單trim choke 5路徑+warmup不足警示(needed/available/affected_bars)。**排除parity表**:cumulative(OBV/AD/ADOSC/VWAP burn_in未實作)/fracdiff d*(first-500,[[project_dstar_first500_optionA]])/ADF/post-IC/labels horizon。flag `FFACT_WARMUP_TRIM`=0(僅開時納hash)。後端16+前端 vitest+hermetic+golden PASS。多輪委員會(d* Option A三方+Option-1設計三方+v1/v2雙家族+後端review兩輪)。
留待(優先序,使用者 2026-06-21 定):
- **L6.5 並行研究**(B5/B6 已完→**下一個**)委員會方案 handoffs/20260622-l65-parallel-*:先 read-only profile 證 CPU vs I/O(winsor sliding 已 O(n),native-tf 32x 疑為 per-group 開銷)→窄L3並行/寬L2序列+tier worker公式+RSS gate+ThreadPool+byte parity。native-tf gate 否決見 [[project_nativetf_gate_rejected]]。
- **B4 Q2-B**(大,最後)交易式 bulk-delete(tombstone+失效 checkpoint/RunManager/quality/磁碟)。B3 已備單 run delete_run;B4 做多選/原子/批量。
- 既有壞測試(非本批):`frontend/src/__tests__/strategy-components.test.tsx` import 缺 `strategy/SignalTooltip`(d250c83 起壞,可另開小修)。
- **E 執行模型維持現狀**;normalize 薄函式已落地。
重啟後端:terminal 乾淨(Q5)+batch worker log 進檔(B1)+單/批進度帶 RSS(B2)+批次 retain/discard(B3,FFACT_BATCH_RETENTION=1)+批次尊重日期(B5)+選日期 warmup 前段可用(B6,FFACT_WARMUP_TRIM=1)。
