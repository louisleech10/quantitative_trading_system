# IC Phase 0 TODO — 雙家族 Adversarial Reconcile-2（Claude 綜合）

> 2026-06-25 ｜ 來源 `...TODO-ADVERSARIAL-CODEX.md` + `...TODO-ADVERSARIAL-CURSOR.md`。兩家 Verdict「需修補後派工」，強烈收斂。SPEC v2 主幹/30 ID/引用行號獲認可，修補集中在 TODO 精度。

## 收斂 + Claude 親核
| # | Finding（家族） | 親核 | 處置（補進 TODO v2） |
|---|---|---|---|
| T-1 | **Golden [M-5] 無 owner Task**（兩家 BLOCKING） | 屬實 | 擴 Task 2.2/3.5/4.2 各自 owner baseline + 新增 `tests/momentum/test_ic_phase0_golden.py`；Phase Gate 引用具體測試 |
| T-2 | **decay 熱迴圈有 4 處 warning**（:904/:918/:944/:958，cursor BLOCKING） | 親核屬實（見下） | Task 4.1 改：移除/聚合**全部 4 處** per-feature warning；Task 4.2 caplog==0 |
| T-3 | **feature_filter 欄位精確名**（兩家 MAJOR） | 親核屬實（include_features 等 7 欄） | Task 3.1/3.2 貼 7 欄 1:1 表，偽碼用真名 |
| T-4 | **WS failed 用 `message` 非 `error`**（cursor MAJOR） | 親核（見下） | Task 4.4：WS `data.status==='failed'`→`setError(data.message)`；poll→`setError(response.error)`；補 onmessage failed 分支 + onerror 僅 transport |
| T-5 | **truncation_mode 判定未定義**（cursor MAJOR） | 屬實 | Task 3.3：`preview` 僅當 max_features 顯式設定且生效；其餘 `none`+applied=True |
| T-6 | **B2/B3 同改 ic_config_schema.py**（兩家 MAJOR） | 親核屬實 | §B：B3 依賴 B2（同檔序列） |
| T-7 | Task 4.3 測試檔未指定 + heartbeat 實測（cursor MAJOR） | 屬實 | 寫死 `tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop`(long+cross) |
| T-8 | poll 狀態機偽碼不足（cursor MAJOR） | 屬實 | Task 4.4 補偽碼：retryCountRef/pollIntervalMs=2000/terminal→clearInterval+close |
| T-9 | 45k fixture 來源（cursor MINOR） | 屬實 | Task 3.2：pytest factory n=45000 named cols，sha256 比欄名集合 |
| T-10 | Task 1.2 點函式名非行號（cursor MINOR） | 屬實 | 改點 `test_stage4_ic_calculation_with_kline_reader` + 禁裸 dict |
| T-11 | onclose :110-118 / onerror :106-108（cursor MINOR） | 屬實 | Task 4.4 加區分 transport vs backend failed |
| T-12 | §0 未摘 §A 六項（cursor MINOR） | 屬實 | §0 加 6 行事實摘要 |

## 親核紀錄（Claude 自驗，不只信報告）
- decay 4 warning：ic_engine.py:904 insufficient_points、:918 low_variance、:944 low_r2、:958 fit_exception——已 grep 確認皆在 `_fit_exponential_decay` 熱路徑。
- WS failed payload：`_notify_callbacks` 用 `"message": str(exc), "status":"failed"`（service:246-251）；`ICTaskStatusResponse` 才有 `error` 欄——前端 setError 須讀對欄位。
- 欄位精確名：`FeatureFilterConfig`（ic_models.py:8-15）確為 include_features/exclude_features/include_pattern/include_categories/include_data_sources/include_families/max_features。
- B2/B3 同檔：Task 2.3 與 3.1 皆改 ic_config_schema.py（grep 確認）。

## 去向
補 TODO v2 → 重跑三道機檢 → gate → 派 codex 實作（B1→B4）+ composer code review。
