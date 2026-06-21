# B1 batch worker logging (#1) TODO
> 版本：DRAFT｜基於 SPEC：docs/B1_WORKER_LOGGING_SPEC.md｜日期：2026-06-19

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | 父設 FFACT_API_LOG_PATH 當日檔 | Phase1 |
| Task | 2.1 | worker init_worker_logging non-rotating + smoke | Phase2 |
| 不變量 | BYTE | logging 不污染特徵值 | §G/§V |
| 風險 | (b) | batch worker 共用入口 | §RISK |
| flag | FFACT_API_LOG_PATH 不設=回舊 | 天然 flag | §R |
- 合計：Task=2、不變量=1、風險=1。

## §0 全域規則
- **不改數值(核心)**:純 logging;B1 前後 `build_l65_golden_baseline.py --check` PASS。
- **non-rotating**:worker 用 `logging.FileHandler`(非 TimedRotating)避免跨進程 rotate 競態。
- **fail-open**:worker logging setup 全包 try/except,失敗不中斷生成(只 debug)。
- **不吞生成例外**:只吞 logging setup 自身錯,生成例外照拋。
- **防假綠**:不放寬既有 batch 測試;新斷言子進程 momentum.* 真進檔 + smoke 無破行 + byte 不變。
- 路徑取 settings.logs_path 非硬編。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| 單批 | 1.1 + 2.1 | 2.1 依 1.1 | 中(同檔/同 PR,一起驗 smoke) |
- Gate:子進程 momentum.* 進當日檔 + smoke 父+1-4子無破行 + golden --check PASS。

## Phase 1 — parent 設 env
### Task 1.1 — 父傳當日 log 路徑
- SPEC ref：1.1　目標:父派 worker 前設 FFACT_API_LOG_PATH=當日 case_search_api_{date}.log 絕對路徑。
- 實作要點:
  1. feature_factory_batch_service.py `_run_batch` wave 前,仿 FFACT_CHILD_METRICS_PATH 設/還原 env。
  2. 路徑=settings.logs_path / f"case_search_api_{date}.log"(對齊 logging.py:88 命名)。
- 修改檔案:feature_factory_batch_service.py。
- 不可做:不改 setup_logging 父行為;不硬編路徑。
- 邊界:還原 previous env;當日檔不存在時 worker 會建(FileHandler)。
- 驗證:env 設且指當日檔;`pytest tests/api/ -k worker_log_env`。

## Phase 2 — worker init logging + smoke
### Task 2.1 — _compute_single init_worker_logging (含 Codex adv 6 修補)
- SPEC ref：2.1　目標:worker 掛 non-rotating FileHandler,momentum.*/api.* 進當日檔帶 [pid sym tf]。
- 實作要點:
  1. 新 helper `init_worker_logging(path, symbol, tf)`(api/core/logging.py):讀 path→`logging.FileHandler(path)` non-rotating 掛 root,setFormatter 同 :60,filter 注入 pid/sym/tf。全包 try/except fail-open。
  2. **(adv#1) idempotent**:掛前以 marker attr 檢查既有 worker handler,已掛不重複加。
  3. **(adv#2) 不衝突**:只 add 自己 handler,**不清既有 root handlers、不改 root level、不動 caplog/第三方**。
  4. `_compute_single`(**:1146**)入口呼叫(讀 FFACT_API_LOG_PATH)。
- 修改檔案:api/core/logging.py(helper) + feature_factory_batch_service.py(_compute_single 呼叫)。
- 不可做:不用 TimedRotatingFileHandler;不清/改既有 handler;不改數值;**(adv#5)不碰 `_compute_single` 的 generate_features 呼叫參數/cache path/config_override(碰=BLOCK)**;不吞生成例外。
- 邊界:env 未設→不掛回舊;setup 失敗→生成照常;連續 init idempotent;既有 handler 不動;多子進程 append。
- 驗證:① 子進程 momentum logger 寫到該檔;② **(adv#1)** 連續 init 兩次→只一行;③ **(adv#2)** 既有 StreamHandler/caplog 不被移除/改 level;④ **(adv#4 fail-open 兩測)** logging setup raise→生成仍返;generate_features raise→原 failure 不被吞;⑤ **(adv#6 env)** previous None/value 兩態 restore + ProcessPool 失敗也還原;⑥ **smoke(mandatory,adv#3)**:父+1~4子用真 FileHandler 各寫唯一 JSON line→每行 json.loads 可解、id set 完整、無 dup/partial;`pytest tests/api/ -k worker_logging`。

### Phase 測試 + Gate
- 行為不變:`python scripts/build_l65_golden_baseline.py --check` PASS。
- smoke 父+1-4子無破行/缺行(committee mandatory P0 門檻)。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B1_WORKER_LOGGING_SPEC.md TODO=docs/B1_WORKER_LOGGING_TODO.md FOCUS=non-rotating避競態/smoke無破行/byte不變/fail-open`
→ 一家 adversarial(Codex)reconcile → Composer 實作 + Codex review。
