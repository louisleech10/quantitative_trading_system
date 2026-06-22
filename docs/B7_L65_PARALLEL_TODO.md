# B7 L6.5 raw-sink 並行（方案 A）TODO
> 版本：DRAFT｜基於 SPEC：docs/B7_L65_PARALLEL_SPEC.md｜日期：2026-06-22

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | 窄/寬分流 + tier worker + RSS budget | Phase1 |
| Task | 2.1 | ThreadPool 並行窄群 compute + 父有序 sink + RSS 背壓 | Phase2 |
| 不變量 | PARITY | serial vs parallel byte 一致(核心) | §V |
| 不變量 | RSSCAP | 並行 RSS ≤ tier budget 不爆 | §V |
| 不變量 | FLAGOFF | flag 關=今日序列不變 | §G/§V |
| 風險 | (b) | L6.5 hot path 併發+sink+RSS | §RISK |
| flag | 預設關=effective_workers=1 | 護欄 | §R |
- 合計：Task=2、不變量=3、風險=1、flag=1。

## §0 全域規則
- **byte-parity(核心)**:flag-on(並行)輸出 == flag-off(序列) 逐欄 allclose≤1e-6+NaN mask+group/row_count 一致。群獨立→順序不影響。
- **父單一有序 sink**:依 group_plan 順序單 writer 寫盤(磁碟/manifest 安全)。
- **RSS 不爆**:Σ inflight peak+current≤tier budget,超→背壓暫停+drain;queued 結果 bytes 計入。
- **窄並行/寬序列**:寬群(高RSS/slow-path fracdiff·ADF·gaussian)序列。
- **flag 預設關=今日 effective_workers=1**。
- **不用 ProcessPool**(pickle/記憶體×N);禁 numba parallel=True+外層 ThreadPool。
- **不改 winsor 數值/sink 順序語意**。
- **hermetic 測試**(tmp+FFACT_CGSA_WORK_DIR,B5 教訓);真實 kline。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B7a | 1.1 | 無 | 中(分群gate+worker+RSS budget,純函式可單測) |
| B7b | 2.1 | B7a | 中-大(ThreadPool並行+有序sink+RSS背壓+parity) |
- Gate:B7a eligibility/worker 數正確;B7b serial==parallel byte一致+RSS不超+flag關golden+hermetic。

## Phase 1
### Task 1.1 — 窄/寬分流 + tier worker + RSS budget
- SPEC ref：1.1　目標:eligibility(working_peak/cols/non-slow)+worker 公式+RSS budget。
- 實作要點:`working_peak=native_rows*cols*4*3+primary_rows*cols*4+idx_map_bytes`;narrow iff `working_peak≤min(512MiB,rss_budget/(workers+1))` & `cols≤split_threshold/2` & 非 slow-path;`cpu_cap=min(max(cpu_count-1,1),8)`;tier_base{8:2,16:4,24:6,32:8};effective=min(tier_base,cpu_cap,floor(rss_budget/p95));rss_budget=tier_gb*0.55-current-reserve{8:2,16:3,24:4,32:5}GiB。
- 修改檔案:feature_preprocessor.py(:440-560)。不可做:寬群不並行。
- 邊界:unknown shape/RSS→serial fail-closed。
- 驗證:已知 shape→eligibility/worker 正確;`pytest tests/ -k l65_parallel_gate`。

## Phase 2
### Task 2.1 — 並行 compute + 有序 sink + RSS 背壓
- SPEC ref：2.1　目標:窄群 ThreadPool 並行 compute,父依 group_plan 順序單 writer sink,提交前 RSS gate。
- 實作要點:`ThreadPoolExecutor(effective)` 跑窄群 compute(回傳 array+meta);父有序 sink;Σ inflight+current>budget→暫停 drain;flag 開且有 narrow→並行,否則今日序列。
- 修改檔案:feature_preprocessor.py(raw-sink 迴圈)。不可做:不改 winsor 數值;sink 單 writer;不用 ProcessPool;禁 numba parallel=True。
- 邊界:numba 釋 GIL;flag 關=今日;寬群序列。
- 驗證:**serial vs parallel byte 一致**(allclose≤1e-6+NaN mask,真實 kline 多窄 L3 群);RSS≤budget(超→背壓不 OOM);`pytest tests/ -k "l65_parallel_parity or l65_parallel_rss"`。

### Phase 測試 + Gate
- flag 關:`build_l65_golden_baseline.py --check` PASS + effective_workers=1 同今日。
- serial==parallel byte + RSS 不超 + 窄寬分流 + hermetic(data_cache diff 空)。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B7_L65_PARALLEL_SPEC.md TODO=docs/B7_L65_PARALLEL_TODO.md FOCUS=serial==parallel byte一致/父有序sink/RSS不爆/窄並行寬序列/flag關序列/真實kline hermetic`
→ **雙家族 adversarial(大,(b)併發+byte-parity,Codex+Composer)** reconcile → Composer 實作(Phase1→2) + Codex review。使用者:完成後手動跑收時間/RSS。
