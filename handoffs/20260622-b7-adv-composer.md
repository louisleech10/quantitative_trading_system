# B7 L6.5 raw-sink 並行 — Adversarial Review (Composer, 2026-06-22)

## Verdict：需修補後派工

SPEC/TODO 方向正確（父有序 sink + byte-parity + 窄並行），但多處把未驗證假設當事實、RSS/門檻與實作錨點矛盾、驗收測試名不存在，直接派工高機率 OOM 或假綠。

## Findings

1. **[BLOCKING|High] 未命名 env flag** — §R「feature flag(env,預設關)」無變數名；Agent 無法實作護欄。修法：明訂如 `FFACT_L65_RAW_SINK_PARALLEL=0` + 讀取點。
2. **[BLOCKING|High] 驗收測試不存在** — §V/TODO 引用 `l65_parallel_gate|parity|rss`；repo 僅有舊 `tests/test_l65_parallel.py`（`_transform_registry_parallel` 記憶體路徑，非 raw-sink/native-tf）。修法：TODO 列新建檔+必測場景，禁止沿用舊測名暗示覆蓋。
3. **[BLOCKING|High] 有序 sink 重排緩衝未規格化** — §C/2.1 要求父依 `group_plan` 序寫入，但未限制「已完成但未輪到」暫存上限；慢群在前時快群全完成→峰值 RSS≈Σ 結果 bytes（99 窄群可數 GB），與 §C③ 背壓矛盾。修法：規定 reorder buffer（僅保 next K 或逐序 submit+單 inflight/群）。
4. **[MAJOR|High] GIL 釋放前提錯** — §A 引用 numba `@njit` 釋 GIL；實際 native-tf 走 `_maybe_run_native_l65_to_sink`→`native_pp._transform_single`（`:827`），非 `transform_array_fast`；winsor 經 `rolling_quantile_2d` numba 段釋 GIL，但 pandas/float64 包裝仍可能讓 ThreadPool 加速遠低於 profiling 外推 8×。修法：§V 加 wall-time gate 或先把 native compute 對齊 numba fast path。
5. **[MAJOR|High] `working_peak` 低估實測 RSS** — Task1.1 公式 `native_rows*cols*4*3`；profile 寬 L2 ~1.4GB/2111欄（handoffs/20260622-l65-profile-composer），130欄 L2 仍可能僅估 ~32MB 卻 eligible。修法：納入 scaled_window×cols scratch、或 profile 實測 p95/group 代入 `p95_task_peak`（現未定義）。
6. **[MAJOR|High] `p95_task_peak` 空殼** — worker=`floor(rss_budget/p95_task_peak)` 無來源/預設/測法→Agent 自填。修法：§P1.1 寫死測量腳本或 conservative 常數+表格。
7. **[MAJOR|High] 8GB multi-TF 兄弟進程未入 budget** — handoffs/20260622-l65-parallel-composer 扣 ~1.5GB；SPEC `rss_budget=tier*0.55-current-reserve` 未扣 sibling pipeline。8GB tier `_MULTI_TF_MAX_WORKERS=1` 仍可能 主+1 子 ~6GB+。修法：§C 明列 multi-TF 疊加項或 fail-closed 偵測。
8. **[MAJOR|Medium] 門檻與 stage1 設計漂移** — handoff `native_rows×scaled_winsor_w>2e6→序列`、eligible `<256MB`、tier×0.85；SPEC 用 512MiB、tier_base{8:2}、0.55。1h→12h 主熱群（window 3024）SPEC 仍 narrow。修法：reconcile 並寫入 §A 已驗證。
9. **[MAJOR|Medium] slow-path 漏排風險** — eligibility 寫「非 slow-path」但未綁 `_group_requires_slow_transform`（`:1184-1223`）同邏輯；native-tf 路徑本身不查 slow（`:545-549` 先跑 native）。IC-first L1/L2+fracdiff 時 L3 仍 narrow 正確，但 gaussian `apply_to!=all` 或 config 漂移可誤並行。修法：Task1.1 明確 reuse `_group_requires_slow_transform` + native 專用 guard。
10. **[MINOR|High] d_star/registry 並發** — winsor-only 不寫 d_star；並行僅 read `load_data_native`（`:431` `_buffer_lock`）。若未來 fracdiff 開啟，每群 `native_pp` 獨立 cache（`:820-822`）仍需禁止跨群共享寫。修法：§C 註明 winsor-only scope；fracdiff 一律 wide。
11. **[MINOR|Medium] float32 非結合** — winsor numba 逐列因果、群內確定序；並行不改群內演算法→byte-parity 風險低。manifest 由父序 sink 保證（`:386-388 defer_manifest`）。
12. **[MINOR|Medium] 簡化替代未評估** — 方案 A 未對照「僅 L3+winsor+numba fast」或維持 serial 先做算法層（profile 主因 O(n×window)）。非 blocking，建議決策表一行。

## 被當成事實的未驗證假設
- numba GIL 釋放 ⇒ raw-sink ThreadPool 近線性加速（實際走 `_transform_single` DataFrame 路徑）。
- `working_peak` 公式可防 OOM（與 1.4GB 寬群實測不符）。
- `p95_task_peak` 已知。
- 列出的 pytest -k 已存在且覆蓋 raw-sink。
- tier_base{8:2} 與 profile 建議 workers≈6 一致。

## §1 十類快檢
矛盾(⑧⑨)/漏項(②③⑦)/不可測(②⑥)/quant(⑨)/過度工程(無)/OOM(③⑤⑦)/Cache(⑩)/相容(①)/測試(②)/Agent(③⑥)/範本錨點(有§)/獵空殼(⑥ p95 空)。

HANDOFF_NOT_UPDATED: read-only adversarial review.

STATUS: DONE
