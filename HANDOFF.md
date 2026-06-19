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
