# IC 修法 Phase 0 — 定義（ready for SPEC 管線，新 session 直接接）

> 2026-06-24 使用者定案:起點 Phase 0;另開新 session 實作。本檔=Phase 0 完整範圍,新 session 一進來照這份走完整 SPEC 管線(manifest→SPEC→雙家族 adversarial→TODO→gate→派工→接回 code review)。
> 上層:`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`(七 Phase);地圖:`20260624-ic-map-00-INDEX.md`。

## Phase 0 目標
止血 + 正確性硬閘:讓 IC analysis **跑得完、不靜默算錯、且修掉後面 Phase 的前置**。使用者實測「選 run 跑 analyze 卡死+崩潰」即此。

## 範圍（epic 來源 + 委員會新增）
來源 `handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`(三方 reconcile)+ 分階段委員會新增(timestamp/by_volatility)。

| Epic | 內容 | 命中風險 |
|---|---|---|
| **IC-CRASH** | GroupedConfig 崩潰修(orchestrator:1139 傳 pydantic 給 dict-API ic_engine:377)→ caller 傳 `.model_dump()`;**補真 config + include_regime_analysis=True 回歸測試**(現有測試用 SimpleNamespace+dict 沒打到真路徑) | (d) 正確性 |
| **IC-FEATURE-GUARD** | feature_filter 幽靈落地(前端送 max_features 後端真生效;ICConfig 加欄、orchestrator 真消費)+ 大 run 警示 + metadata 記原始/篩後數(**不靜默截斷**);**preview_limit 改名**(需 API schema 版本化) | (b)(d);**是 Phase 2 前置**(輸入 universe 正確) |
| **IC-UX-ERR** | 主 analyze 改 `asyncio.to_thread`(解 event loop 阻塞→WS 假死)+ WS failed 顯真錯誤(非無條件「連線失敗」)+ 停無限重連 + HTTP poll fallback | 體感/正確性傳遞 |
| **IC-TIMEAXIS(委員會新增)** | `_get_time_index` numeric timestamp 當 ms 但實為秒(codex 實讀 HDF5=1716235200 秒)→ grouped IC by_year/quarter 軸錯;改實測判斷 + sanity check(1970/未來日期 fail-closed) | (d) 正確性 |
| **IC-BYVOL(委員會新增)** | `by_volatility` schema 預設 true 但 compute_grouped_ic 無此分支(契約漂移)→ 實作 or fail-closed(不靜默忽略) | 契約正確性 |
| **IC-DECAY-LOG** | decay `_fit_exponential_decay` 熱迴圈逐特徵 warning(14090 條)→ 聚合一行摘要(回傳 r2/reason,結尾統計) | 效能/違規 |

## 已定決策（baked in，新 session 不必再問）
- **起點=Phase 0**(使用者 2026-06-24)。
- **walk-forward/purged CV 复用現有 ML 孤島**(PurgedTimeSeriesSplit/CPCV 在 model-enhancement),非重寫(省 3-5× 工時)——此決策主要影響 Phase 2A/4,但先記。
- **不在舊 materialized 路徑硬補大尺度**(留 Phase 1/3 contract-first);Phase 0 只止血+硬閘,不碰串流重寫。

## 正確性紅線（Phase 0 必守）
- 不靜默截斷特徵/不弱化 NaN·inf gate/不改 IC 數值計算語義(除了修錯的:timestamp 軸、by_volatility)。
- feature_filter 落地須 metadata 可審計;事件不足/篩選須明確不靜默。
- IC-CRASH 回歸測試須打真實 config 路徑(非合成 fixture 假綠)。

## 不可做
- 不做串流重寫(Phase 3)、不做 train/test(Phase 1)、不做 case-control(Phase 2)——Phase 0 只止血+硬閘。
- 不順手改 API 大契約(除 feature_filter/preview_limit 版本化)。

## 新 session 起手式
1. 讀本檔 + `ic-grouped-crash-perf-ANALYSIS.md` + `CLAUDE.md` 任務分派規則。
2. 級別:大(命中 (b)(d) + 多 epic)→ 走完整管線:manifest(扁平 ID)→ SPEC(§A 事實附碼證、§G golden:GroupedConfig 真 config 回歸 + feature_filter 落地前後 metadata)→ 雙家族 adversarial → TODO → gate → 派工(實作端)→ 接回 diff 防假綠 + 另一家 code review。
3. preflight/postflight 快照(data_cache)。
