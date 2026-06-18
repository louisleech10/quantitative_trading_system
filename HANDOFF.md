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
