# B1 — batch worker per-layer log 進檔 (#1) — SPEC

> 來源：handoffs/20260619-ffconsist-FINAL.md(#1, P0b)｜日期：2026-06-19｜對應 TODO：docs/B1_WORKER_LOGGING_TODO.md

## §RISK 風險分級
- **大小**：中。
- **命中**：**(b) 跨模組共用路徑**(batch worker `_compute_single` 是所有 batch symbol 入口)。**不命中 (a)/(d)**——純 logging,不碰特徵值/數值。
- → §G N/A;以 `python scripts/build_l65_golden_baseline.py --check` PASS(abs≤1e-6,byte 不變)+ smoke 子進程 log 無破行 驗證。

## §A 假設與待使用者確認
- **已驗證事實**(grep/Read 實測,附行號):
  - `setup_logging`(api/core/logging.py:32):root logger + **TimedRotatingFileHandler**(:91)→ `logs/case_search_api_{date}.log`(:88);formatter(:60)。
  - batch worker `_compute_single`(feature_factory_batch_service.py:1129)在 ProcessPool 子進程跑(:442/464);**子進程不繼承父 root file handler** → 實測單 symbol(thread,23:14-23:22)momentum.* 366 行進檔、batch(子進程,23:31-23:36)幾乎只 api.*(根因)。
  - worker 已讀 `FFACT_CHILD_METRICS_PATH`/`FFACT_LAYER_METRICS_PATH` env(:31-32)→ FFACT_API_LOG_PATH 同模式。
- **待確認**:無。**已確認**(2026-06-19):做 B1(委員會 FINAL P0b)。

## §C 約束
- 解耦:純 momentum/api logging,不引新跨域依賴。
- **不可違反**:不改特徵值/數值;worker logging setup 失敗不得中斷生成(fail-open try/except)。
- 注意:**non-rotating FileHandler**(非 TimedRotating)避免多進程跨檔 rotate 競態;當日檔路徑由父經 env 傳。

## §G Golden / Baseline
- N/A(移 §N)。行為不變:開 B1 前後 `python scripts/build_l65_golden_baseline.py --check` PASS(logging 不污染數值)。

## §P Phase 與依賴

### Phase 1 — parent 設 env(依賴:無)
**Task 1.1 — 父進程傳當日 log 路徑**
- 目標:父在派 worker 前設 `FFACT_API_LOG_PATH`=當日 case_search_api_{date}.log 絕對路徑(沿用 setup_logging 的 log_dir+命名)。
- 檔案:feature_factory_batch_service.py(_run_batch wave 前,仿 FFACT_CHILD_METRICS_PATH 設/還原)。
- 驗證:env 設了且指向存在的當日檔;`pytest tests/api/ -k worker_log_env`。
- 邊界:① 還原 previous env(仿 child_metrics);② 路徑取自 settings.logs_path 非硬編。
- 不可做:不改 setup_logging 父行為。

### Phase 2 — worker init logging(依賴:Phase 1)
**Task 2.1 — _compute_single init_worker_logging + smoke**
- 目標:worker 入口掛 non-rotating FileHandler,momentum.*/api.* log 進當日檔,帶 `[pid sym tf]` context。
- 檔案:feature_factory_batch_service.py `_compute_single`(**:1146**,adv 修正行號) + 新 helper `init_worker_logging(path,symbol,tf)`(api/core/logging.py)。
- 改法:讀 FFACT_API_LOG_PATH→`logging.FileHandler(path)`(**non-rotating**)掛 root,setFormatter 同 setup_logging:60,加 context(filter 注入 pid/sym/tf);全包 try/except fail-open。
  - **(adv#1 idempotent)**:掛前檢查既有 worker handler(以 marker attr/path+pid 識別),已掛則不重複加(防同 process 多次 init 累加 handler→重複 log)。
  - **(adv#2 不衝突)**:**不得清除既有 root handlers、不得改 root level、不得移除 caplog/第三方 handler**——只 add 自己的 worker handler。
- 驗證:① 單元 worker logging 後 momentum logger 寫到該檔;② **(adv#1)** 連續 init 兩次→只寫一行(無重複 handler);③ **(adv#2)** 已有 StreamHandler/caplog/父 handler 時 init→既有 handler 不被移除/不改 level;④ **(adv#4 fail-open 兩測)**:logging setup raise→`generate_features` 仍被呼叫且結果照返;`generate_features` raise→仍回原 compute failure(不被 logging except 吞);⑤ **(adv#6 env)**:FFACT_API_LOG_PATH previous None/value 兩態 restore + ProcessPool 建構/submit 失敗也還原;⑥ smoke(見 §V)。`pytest tests/api/ -k worker_logging`。
- 邊界:① env 未設→worker 不掛(回舊);② setup 失敗→生成照常(fail-open);③ 多子進程同檔 append(smoke 1-4 子,concurrent>1 全壓測留 T-A);④ 連續 init idempotent。
- 不可做:不用 TimedRotatingFileHandler;不清/改既有 handler;不改數值;不吞生成例外。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(env 設置/worker handler idempotent/不衝突/fail-open)/ smoke(多進程 append)/ 整合(真實小 batch→子進程 momentum.* 進檔)/ 行為不變(byte)。
- **防假綠**:不放寬既有 batch 測試;新斷言子進程 momentum.* 真進檔 + smoke 完整 + byte 不變 + fail-open 兩測 + idempotent。
- **行為不變 + diff scope 限制(adv#5)**:`build_l65_golden_baseline.py --check` PASS;**diff 只允許 env 設置/helper/worker 入口呼叫/測試**——**若改到 `_compute_single` 的 `generate_features` 呼叫參數/cache path/config_override → BLOCK**(本批純 logging)。
- **smoke(committee mandatory,adv#3 強化)**:父+N子(N=1~4)用**真 `logging.FileHandler`**各寫唯一 JSON line(行長覆蓋實際 formatter+context)→ assert 每行可 `json.loads`、id set 完整無缺、**無 duplicate/partial**。
- **邊界目錄**:env 未設/None/value restore(adv#6)/setup 失敗 fail-open(adv#4)/生成例外不被吞(adv#4)/連續 init idempotent(adv#1)/既有 handler 不動(adv#2)/多進程 append 無破行(adv#3)/byte 不變(adv#5)。

## §R 回退
- 單 commit 可 revert;`FFACT_API_LOG_PATH` 不設即回舊行為(worker 不進檔)——天然 flag。byte 變=立即 revert。

## §N N/A 登記
- §G Golden:**N/A — 純 logging 不碰數值**;改以 `python scripts/build_l65_golden_baseline.py --check` PASS(abs≤1e-6)+ smoke 無破行 驗證。
