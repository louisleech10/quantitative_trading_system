# Handoff
**Agent**: Claude | **Time**: 2026-06-16 | **Branch**: main

## 結案:backlog #1/#2/#3 三批全完成(自主執行,本輪一次 push)
### #1 既有測試紅 triage（完成）
- 43 紅分類解決:3 我的回歸(frozen 守門+phase2)、委員會三方 Q1-Q5 裁定、~30 殭屍滯後對齊。Composer redfix code review **APPROVE**。
- 文件 docs/BATCH3_TEST_TRIAGE.md;commit d1a6146/1cb31bd/935b24f。
### #2 d* / FracDiff 非 CGSA 對齊（完成,選 A 修復）
- 根因:非 CGSA frame path fracdiff 因 regex `^(L\d+)_` 對裸欄名全 unparsed→靜默 no-op。修法:factory `_build_column_layer_map`+preprocessor filter 優先序(ALL→map→regex fallback),CGSA source_layer 分支未動。
- 管線:設計委員會雙家族三方一致→SPEC/TODO/MANIFEST V3(4 輪 adversarial,核心 reframe **d* parity 為主 oracle** 化解 CGSA/非 CGSA 不同儲存格式)→Composer 寫 P4+跨家族 review production APPROVE→Codex review P4+跑 slow gate APPROVE。
- **三方資料正確性裁定:d* parity 達成**(T3 3458/3458 exact,0 mismatch);**T4 value 差異=既有結構差異 out-of-scope**(CGSA float16 vs frame float32+index dtype+L7 dead-drop,非 #2 bug,fracdiff-OFF baseline 同 delta 證 pre-existing)。
- 驗收:P4 4 passed(774s,T3/control L3-L6 127744 exact/CGSA SHA exact)+回歸 bundle 78+解耦 0;tier2a 修(L1-L5→L1/L2 only)。commit ca87829/245bf6a/55a433f。
- freeze 崩潰排障:根因 control phase Polars 路徑 OOM(非 CGSA),關 Polars+chunked+subprocess-per-phase 解;**使用者 UI 能跑線索關鍵**(證 production 健康、崩潰係 freeze script 特有)。
### #3 tier ADF/d* 並行度 profile（完成,結論=單執行緒 by design,評估另立 ticket）
- CGSA 主路徑(raw-sink L7_raw)L6.5 ADF/d* **所有 tier 強制 serial**(disk-safety,feature_preprocessor.py:428-435 effective_workers=1)。tier worker 表只作用 in-memory frame 路徑非 raw-sink。
- 本機 8GB 無法實測高 tier(強制即 OOM);依「實測>假設」以程式+8gb log 定論。
- 「才評估」→獨立 perf ticket(24/32GB 並行 raw-sink/計算寫盤解耦,需高 tier 硬體+SPEC),本批不動。文件 docs/BATCH3_TIER_PARALLELISM_PROFILE.md。

## 待使用者 / 待辦 ticket(本批刻意不做,另開)
- **float16 精度 ticket**:CGSA raw 將 L1/L2 存 float16(vs frame float32),調查意外撈到,值得評估是否該存 float32(與 #2 無關)。見 BATCH2D manifest 三方裁定節。
- **CGSA raw-sink ADF/d* tier-gated 並行 ticket**(#3 才評估,需 24/32GB 硬體)。
- 第 1 批殘留 MINOR:真 kline 測試 glob→rglob;SPEC :185 錨點勘誤。

## 執行端分工(2026-06-15 使用者改定,已入 memory)
- **中、大型實作=Composer 2.5 實作 + Codex review**(先前大=Codex 實作對調);小=Claude 自己做;其餘流程不變。
- 技術決策委派委員會(非使用者);中途自主 commit;本輪全做完才一起 push。

## 鐵律教訓(本輪新增)
- 儲存層命名/格式現實連續打臉假設 3 次(不同格式→誤判 CGSA 裸名→實為兩路同 tag)→改數值對齊任務,§A 必先實測儲存層欄名/dtype 真相。
- 大型數值對齊「exact value parity」常不可達(float16/storage/topology 差異);主 oracle 該選**格式無關的語義不變量**(此處 d* per-column),value 差異歸既有結構分案,不寬容差掩蓋。
- 同進程連跑兩次全特徵生成→第二次 OOM-kill(faulthandler 抓不到=SIGKILL);profile/freeze 一律分 subprocess。
- 委員會 cursor-agent 偶發斷線無報告→驗檔案落盤;斷線換手或自己決定性蒐證(CGSA-alone 測試)定位。
