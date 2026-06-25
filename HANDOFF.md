# Handoff
**Agent**: Claude | **Time**: 2026-06-25 | **Branch**: main

## ★進行中：IC 修法 Phase 0（大任務 (b)(d)，完整管線施工中）
**狀態**：**IC Phase 0 全完成 + 實機 smoke 通過 + WS regression 修好**。準備 commit。
**實機 smoke（真瀏覽器選 45k run→analyze）**：① 不崩潰（跑過 preprocessing→ic_calculation，以前會崩的路徑）；② 抓到第 3 bug=to_thread 讓 WS 進度回呼從 worker thread 觸發 `create_task` no-running-loop → UI 顯「連線失敗」→ codex 修 `run_coroutine_threadsafe`；③ Claude 自修前端 stale-error（onerror no-op + onmessage 清 error），重跑 smoke「連線失敗」消失、後端 RuntimeError=0、+2 vitest。
**Claude 最終驗收**：全套 IC `97 passed`；前端 vitest 4 passed；diff 防假綠 OK（測試全強化/新增無弱化）；golden 3 baseline 過。
**Composer code review 抓到 BLOCKING（我+adversarial 都漏）**：`config/ic_config.yaml` by_volatility 未同步→預設 grouped 必崩 → codex 已修 yaml→false + 加 guard 測試（load_ic_config 原樣不 raise）。
**postflight**：報 data_cache 縮 6.4MB → **調查為誤報**：真實 kline_cache.h5 未動（mtime Apr 28、ts 1704067200 正確）；縮減全在 gitignored `cgsa_work` FF 測試 scratch，與 IC 無關。
**驗收共抓 2 真 bug 已修**：① _stage5 誤加必填參數（regression）；② yaml by_volatility 未同步（Composer 揪）。
**實作摘要**：6 epic 全落地——crash model_dump / timeaxis 回 DatetimeIndex+單位實測+fail-closed / byvol fail-closed+預設 False / feature_filter `_apply_feature_filter` 預設不截斷+sorted+truncation_mode / decay 移 4 warning+summary(數值不變) / to_thread 兩路徑 + 前端 failed message+poll 狀態機。
**驗收抓到 1 真 bug 已修**：_stage5_statistical_validation 誤加必填 feature_filter_info → analyze:139 漏傳崩 3 測試 → codex 移除誤加參數修好。
**過程留痕**：BRIEF/MANIFEST/SPEC/TODO/ADVERSARIAL-{,TODO-}{CODEX,CURSOR,RECONCILE}/IMPL-*/CODEREVIEW-*。
**preflight/postflight**：`/tmp/agent_dc_snapshot.txt`。

### 已產出（這個 session）
- 白話 brief：`handoffs/20260625-ic-PHASE0-BRIEF.md`（門外漢版）
- manifest（30 ID）：`handoffs/20260625-ic-PHASE0-MANIFEST.md`
- **SPEC v2**：`docs/IC_PHASE0_SPEC.md`（reconcile 後修補；三道機檢 PASS）
- **TODO**：`docs/IC_PHASE0_TODO.md`（4 批；三道機檢 PASS；含派工 prompt B1-B4）
- SPEC adversarial：`...ADVERSARIAL-{CODEX,CURSOR}.md` + `...ADVERSARIAL-RECONCILE.md`（12 項 R-1~R-12 已入 SPEC）
- TODO adversarial（跑中）：`...TODO-ADVERSARIAL-{CODEX,CURSOR}.md`

### SPEC adversarial 收斂重點（已入 SPEC v2）
- IC-TIMEAXIS 真 bug=`_iter_time_groups` AttributeError(回 Series 非 DatetimeIndex)，非靜默 1970
- **IC-BYVOL 收斂=(b) fail-closed + schema 預設 by_volatility 改 False**（兩家獨立一致）
- feature_filter 預設不截斷（前端 max_features 改 undefined）；去 config_override 被 ICConfig 丟棄
- max_features 用 sorted() 穩定序非欄位序；Golden 改結構化 float + per-group row mask

### 親驗事實（鐵律親跑，不信報告）
- IC-CRASH：compute_grouped_ic 單一 caller(orchestrator:1139) 傳 pydantic 給 dict-API → A1 model_dump
- IC-TIMEAXIS：read_klines 回 RangeIndex+timestamp int64 秒(1704067200=2024)；_get_time_index:1025 寫死 unit="ms"→1970，真實路徑必觸發
- IC-BYVOL：schema:80 預設 True，engine 無分支 → 委員會收斂 (a 實作/b fail-closed)，Claude 傾向 b
- IC-FEATURE-GUARD：service:967 寫 metadata、momentum 零消費 → 幽靈全量 45k

### 待辦（接回 adversarial 後）
1. 收 codex(`...ADVERSARIAL-CODEX.md`)+cursor(`...ADVERSARIAL-CURSOR.md`)兩家 findings → reconcile（含 IC-BYVOL 拍板）
2. 改 SPEC（若有 BLOCKING）→ 生 TODO → gate → 派 codex 實作 + composer code review
3. 接回 diff 防假綠 + 自跑 pytest + preflight/postflight

### 使用者新定規則（已存記憶）
- brief 必白話門外漢版（[[feedback_brief_layman]]）
- 任何 agent bug/test/疑問 2 輪解不了 → 一律交委員會（[[feedback_two_round_breaker_all_agents]]）
- IC-BYVOL 照委員會收斂結果執行，不再問使用者

## 背景：IC-Analysis 全覆蓋地圖入口 `handoffs/20260624-ic-map-00-INDEX.md`；定義 `20260624-ic-PHASE0-DEFINITION.md`
