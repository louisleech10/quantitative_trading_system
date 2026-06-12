# Handoff
**Agent**: Claude | **Time**: 2026-06-12 | **Branch**: main

## fail-open 統一重構:Batch2-5 已 commit+push,Batch6 最終驗收中
- Batch2(d654237)/Batch3(7427c72)/Batch4(3106537)/Batch5(e9c5459)。
- **Batch6 三方簽核抓到 3 個真缺陷,全數修復(未 commit,在工作樹)**:
  1. CGSA resume 重算已完成 TF→`_2` 重複 group(舊測試永真假測掩蓋;Codex root-cause+修)。
  2. **Batch2 引入 multi-TF 數值漂移**:caller 遷移提早 float32 才餵 L3→少 1 欄+NaN 漂移(委員會實驗定責;round4 `preserve_dtype` 修復,merged_L7 回 Batch0 baseline)。
  3. Batch5 `max_*` 違規進 config_hash(修復,namespace 回 57c47c30)。
- **B 線結案**:round5 的 `np.ascontiguousarray` 改記憶體序致 155 npy byte 漂移(值全同);修掉全部 5 處(registry/preprocessor/storage/factory)後 **V-3 兩 oracle 在嚴格 npy byte 比對下 PASS**。parquet 仍豁免 byte 比對(Batch3 schema_version 設計性嵌入,值由 merged canonical 全覆蓋)。
- 待:最終全套綠→Composer 終簽核→commit。

## 已核准 backlog(使用者 2026-06-12 核准「一二三全修+非CGSA d* cache」)
### 一、資料健康回溯(最優先,中型派工)
- [ ] 掃 data_cache/features 既有 manifest:resume 缺陷受害 run(`_2` 重複 group/feature count 虛胖)。
- [ ] 6/10-6/12 間 multi-TF 生成的正式資料受 Batch2 float32 漂移影響者重生成。
### 二、follow-up 修正(打包一小批)
- [ ] max_nan_ratio artifact 路徑指向 tests/_golden,production 無 tests 目錄 hard-fail(Batch4 N4)。
- [ ] CGSA validation 缺 nan_ratio fallback 1-coverage 含 warmup 誤標 partial(N6)。
- [ ] failed_layers ID 格式不一致:multi-TF `L3:4h` vs manifest `L3`(N7)。
- [ ] validator winsor window=252/min_periods=63 寫死非 config + CGSA/non-CGSA 分支測試(N3)。
- [ ] multi-TF metadata `actual_timeframes`→`present_timeframes`+專用 timeframes producer(Batch3 委員會遺留)。
### 二之二、Run 生命週期 UX(使用者 2026-06-12 提出,中型)
- [ ] 跑完問「保留/丟棄」(丟棄=刪 run 目錄;CGSA 串流寫盤故為事後清理而非事前選擇)。
- [ ] 保留時輸入**別名**存 registry 標籤;目錄實體仍 config_hash(cache/resume/下游引用依賴),UI 顯示別名。
- [ ] 未命名 run 保留策略(最近 N 個或 N 天自動清)→ 同時解「每調參一份 GB 級目錄」爆硬碟問題。

### 三、既有測試紅
- [ ] test_l65_golden tier2a「Synthetic d_star output is empty」(因果化遺留)。
- [ ] optimization_e2e 6 紅(含 SPEC 點名 engine_partial)。
- [ ] 全量 pytest ~44 紅 triage(hardware/phase_d/config defaults)。
### 四、效能(使用者定範圍)
- [ ] **非 CGSA 路徑 d* cache 不可用(missing_context)必修**——大記憶體 tier 走非 CGSA,目前全寬 L6.5 ADF 30+ 分爆炸。
- [ ] **全量+multi-TF(1h+12h)計算時間盤點(2026-06-12 與使用者對齊)**:
  - 改 fracdiff/ADF 參數的冷跑:無大幅空間(冷路徑=數學本身),**不動**。
  - 改其他參數:d* cache v3 key=僅 fracdiff 參數 hash+per-column value_fp(實碼查證 _d_star_cache.py:246-),指標增刪/其他層調參/UI 設定**本來就不該冷**,部分命中——修好非 CGSA 接線(上項)即享受。
  - 純冷跑唯一待驗證槓桿:**16/24/32GB tier 的 per-column ADF/d* 並行度**(8GB 受 OOM 安全約束放不開)。profile 一次全量 run:若已並行→正式結案不動;若單執行緒掃 870 欄→評估多核並行(數值正確性不變的前提)。

## 鐵律教訓(本輪新增)
- 驗收必跑 tests/api/;cursor-agent 卡死/斷線後驗檔案而非信 log;非 CGSA 全寬 ADF 測試要關 preprocessing 或縮 scope。
- artifact byte 級比對要區分「值」與「序列化 metadata」:值靠 canonical(NaN mask 分離),file-sha 受 schema_version/記憶體序影響。
- persistence 邊界鐵則:只 cast dtype,不 ascontiguousarray(會改 npy header/bytes)。

## 待使用者
- templates/optimization_report.html 曾被 Composer 還原(原工作樹刪除狀態)。
