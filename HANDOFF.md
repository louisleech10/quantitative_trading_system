# Handoff
**Agent**: Claude | **Time**: 2026-06-12 | **Branch**: main

## 結案:fail-open 統一重構(Batch0-6)全部完成並 push
- Batch2(d654237)/3(7427c72)/4(3106537)/5(e9c5459)/6(67c4f28)。三方簽核(V-9)收齊:Codex 實證+Composer CORRECT+Claude 親驗。
- 簽核抓到並修復 3 個真缺陷:①CGSA resume 重算已完成 TF(_2 重複 group);②Batch2 multi-TF 提早 float32 數值漂移;③Batch5 max_* 違規進 config_hash。
- 全管線對 Batch0 凍結 baseline **嚴格 byte-identical**(npy 含記憶體序;parquet 豁免 file-sha——Batch3 schema_version 設計性嵌入,值由 merged canonical 全覆蓋)。
- 缺陷細節/診斷證據:handoffs/20260612-failopen-batch6.md + 各批 commit message。

## 下一步 backlog(使用者 2026-06-12 核准,順序已拍板;執行端:大型=Codex 實作+Composer review,quota 緊時互換)
### 第 1 批:follow-up 小修包 + 非 CGSA d* cache(中型,Composer 實作+Codex 輕審)
- [ ] **非 CGSA d* cache 接線**(missing_context 致大記憶體 tier 全寬 L6.5 ADF 30+分;cache v3 設計本支援 per-column 部分命中,修好接線即享受)。
- [ ] max_nan_ratio artifact 路徑指向 tests/_golden,production 無 tests 目錄 hard-fail(Batch4 review N4)。
- [ ] CGSA validation 缺 nan_ratio fallback 1-coverage 含 warmup 誤標 partial(N6)。
- [ ] failed_layers ID 格式不一:multi-TF `L3:4h` vs manifest `L3`(N7)。
- [ ] validator winsor window=252/min_periods=63 寫死非 config+CGSA/non-CGSA 分支測試(N3)。
- [ ] multi-TF metadata `actual_timeframes`→`present_timeframes`+專用 timeframes producer(Batch3 委員會遺留)。
### 第 2 批:Run 生命週期 UX(中型,動 api+frontend+storage registry,不碰數值)
- [ ] 跑完問「保留/丟棄」(丟棄=刪 run 目錄;CGSA 串流寫盤故為事後清理非事前選擇)。
- [ ] 保留時輸入別名→registry 標籤;實體目錄仍 config_hash(cache/resume/下游引用依賴),UI 顯示別名。
- [ ] 未命名 run 自動清理(最近 N 個/N 天)→解「每調參一份 GB 級目錄」爆硬碟。
### 第 3 批:既有測試紅 triage(先分類半天再決定修哪些)
- [ ] test_l65_golden tier2a「Synthetic d_star output is empty」(因果化遺留)。
- [ ] optimization_e2e 6 紅(含 SPEC 點名 engine_partial)。
- [ ] 全量 pytest ~44 紅(hardware/phase_d/config defaults)——可能含該刪的殭屍測試。
### 效能結論(2026-06-12 與使用者對齊,已定不另開批)
- 改 fracdiff/ADF 參數的冷跑=數學本身,無大幅空間,**不動**。
- 改其他參數本不該冷(d* cache v3 key=僅 fracdiff hash+per-column value_fp);修第 1 批接線即得。
- 純冷跑唯一待驗證:16/24/32GB tier ADF/d* 並行度——第 1 批完成後 profile 一次,已並行→結案;單執行緒→才評估。
### 已作廢
- ~~回溯掃描受害 run~~:使用者確認既有生成資料全為測試,可刪重跑。**待使用者指示後**可清 data_cache/features 與 cgsa_work 舊 run 目錄騰硬碟(勿動 feature_klines/kline_cache.h5!)。

## 鐵律教訓(本輪,新 session 必讀)
- 批次驗收矩陣必含下游消費者測試(ic_first 紅潛伏一批才暴露)。
- persistence 邊界:只 cast dtype,禁 ascontiguousarray(改 npy bytes);registry 分片路徑 L809 的既有 ascontiguousarray 是 Batch0 原始行為,**勿清理**。
- artifact 比對分「值」(canonical,NaN mask 分離)與「序列化 bytes」(受 metadata/記憶體序影響),斷言選對層。
- 非 CGSA 全寬 L6.5 ADF 測試會 30+分:測試關 preprocessing 或縮 scope。
- cursor-agent 偶發卡死/斷線:驗檔案落盤而非信 log;連兩次 infra 敗→換執行端,不三試。

## 待使用者
- templates/optimization_report.html 曾被 Composer 還原(使用者原工作樹為刪除狀態)——要刪回說一聲。
