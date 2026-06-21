# B3 批次 Run 保留對話 (Q2-A) TODO v2
> 版本：v2(雙家族 adversarial reconcile)｜基於 SPEC：docs/B3_BATCH_RETENTION_SPEC.md｜日期：2026-06-21

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | checkpoint retention 狀態 + 成功標 pending(不延後) | Phase1 |
| Task | 2.1 | retain/discard endpoint(原子+重用 delete_run) | Phase2 |
| Task | 2.2 | REST 列 pending + WS 推 pending | Phase2 |
| Task | 3.1 | 真實 free-space 背壓 + wakeup | Phase3 |
| Task | 4.1 | frontend per-item 面板(source 區分,非 deleteRun) | Phase4 |
| 不變量 | RETAIN5 | retention 5 不變量(逐條) | §V |
| 不變量 | CRASH | crash matrix abc | §V |
| 不變量 | CONC | 並發原子性 | §V |
| 不變量 | FLAGOFF | flag 關 spy+byte 同今日 | §G/§V |
| 風險 | (b)(c) | checkpoint/delete_run 多下游·crash 難回退 | §RISK |
| flag | RETENTION 預設關=今日行為 | 護欄 | §R |
- 合計：Task=5、不變量=4、風險=1、flag=1。
- **雙家族 reconcile**:Codex 4 BLOCKING(完成語義/背壓矛盾/crash/並發)+Composer 事實修正(FeatureRegistry.add:3227/checkpoint:889-916/delete_run:103 可重用)→ **轉 post-hoc mark + discard 重用 delete_run**:多下游一致(不延後)、背壓自洽(真刪)、crash matrix、per-item lock。詳見 SPEC v2。

## §0 全域規則
- **不延後任何副作用(核心)**:post-hoc mark——run 照常生成+register+寫盤(FeatureRegistry.add:3227/browse:606/artifact 都不動);retention 純疊加狀態。
- **不改數值**:flag 關 `build_l65_golden_baseline.py --check` PASS。
- **flag 預設關=今日完全行為**:flag-off spy 驗 register/quality 時機同今日(byte 不足)。
- **非阻塞**:pending 待決不卡其他 symbol。
- **真實 free-space 背壓**:`shutil.disk_usage` 非邏輯記帳;低+有 pending→暫停,decision wakeup;低+無 pending→hard-pause+log(非死鎖)。
- **discard 冪等 + 重用 delete_run**:後端呼 `feature_factory_service.delete_run`(非前端 deleteRun action),對已刪 no-op。
- **decision 原子**:per-item lock/CAS,pending→deciding→terminal;先持久化 checkpoint 再回 200。
- **diff scope**:不碰 generate_features 生成參數/數值(碰=BLOCK)。
- **防假綠**:逐條碰真實下游(browse/quality/delete_run/disk),非 smoke。
- **B3 不做 bulk**:transactional 多選刪除留 B4;B3 discard 為 scoped 單 run。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B3a | 1.1 | 無 | 中(checkpoint 狀態+標 pending) |
| B3b | 2.1 + 2.2 | B3a | 中-大(endpoint+原子+delete_run+list/WS) |
| B3c | 3.1 | B3b | 中(真實 free-space 背壓+wakeup) |
| B3d | 4.1 | B3b | 中(前端面板+vitest) |
- Gate:B3a 狀態合法+flag關byte+flag-off spy;B3b retain等今日/discard真刪/並發僅一勝/crash matrix;B3c 低磁碟暫停+discard釋放+無pending不死鎖;B3d npm build+vitest+discard≠deleteRun。

## Phase 1 — checkpoint retention 狀態
### Task 1.1 — retention 狀態欄 + 成功標 pending(不延後)
- SPEC ref：1.1　目標:狀態 pending→deciding→retained/discarded/retention_error;flag 開成功 item 正常 register 後**疊加標 pending**。
- 實作要點:checkpoint(`_build_initial_checkpoint`:889-916)加 retention 結構(per-item identity+state+hdf5_path+error);`_record_item_result`:586 成功尾端 flag 開才標 pending,**不動 :606 register 時機**;retention_error=discard delete_run 拋。
- 修改檔案:feature_factory_batch_service.py。
- 不可做:不延後 register/FeatureRegistry.add;不改數值;flag 關不寫 retention 欄。
- 邊界:flag 關=今日行為;crash 載入狀態正確;非法轉移 raise。
- 驗證:狀態合法/非法 raise;`pytest tests/api/ -k retention_state`;flag 關 `build_l65_golden_baseline.py --check` PASS。

## Phase 2 — decision endpoints
### Task 2.1 — retain/discard endpoint(原子+重用 delete_run)
- SPEC ref：2.1　目標:POST per-item retain(清 pending)/discard(deciding→delete_run→discarded);per-item lock 防並發;非阻塞。
- 實作要點:新 endpoint(api/routes/feature_factory.py)+ service decision 方法;CAS pending→deciding;discard 重用 `feature_factory_service.delete_run(symbol,tf,config_hash)`(冪等);先持久化 checkpoint 再回 200(寫失敗→5xx 未提交)。
- 修改檔案:api/routes/feature_factory.py、feature_factory_batch_service.py、api/models。
- 不可做:不阻塞 wave;batch 不呼前端 deleteRun;不碰 B4 bulk。
- 邊界:重複 decide 冪等;404;並發僅一勝(另 409/no-op);delete_run 拋→retention_error。
- 驗證:retain 清 pending;discard 刪檔(`Path.exists()==False`)+browse 不見;並發 retain/discard 僅一勝;`pytest tests/api/ -k retention_decision`。
### Task 2.2 — REST 列 pending + WS 推 pending
- SPEC ref：2.2　目標:GET 列 pending items;WS 完成推 pending(B2 normalize 風格)。
- 實作要點:GET endpoint 回 pending identity/state/hdf5_path/error;`map_batch_progress_ws_data` 擴 retention;types 同步。
- 修改檔案:api/routes/feature_factory.py、feature_factory_ws.py、api/models、frontend types.ts。
- 不可做:不破既有 batch status 欄。
- 邊界:無 pending 回空;WS 斷線 REST list 補。
- 驗證:list 回未決;WS 推 pending;`pytest tests/api/ -k retention_list`。

## Phase 3 — 真實 free-space 背壓
### Task 3.1 — free-space gate + wakeup
- SPEC ref：3.1　目標:wave 前 `shutil.disk_usage` 真實 free<閾值+有 pending→暫停;decision wakeup 續;無 pending→hard-pause+log。
- 實作要點:wave gate 用 shutil.disk_usage(T-C column_group_registry free-space gate 為樣式參考非同符號);閾值/reserve env 可配;decision 後 wakeup 重評。
- 修改檔案:feature_factory_batch_service.py。
- 不可做:不用邏輯記帳替真實 free-space;不死鎖。
- 邊界:閾值未設用 tier 預設;discard 釋放後續;無 pending hard-pause 不死鎖;wakeup 不漏。
- 驗證:低 free-space+pending→暫停;discard 後續;無 pending 不死鎖;`pytest tests/api/ -k retention_backpressure`。

## Phase 4 — frontend
### Task 4.1 — batch per-item 面板(source 區分,非 deleteRun)
- SPEC ref：4.1　目標:completionQueue 加 source;batch 可展開面板逐項 retain/discard 呼 batch endpoint(非 deleteRun);與單 symbol modal 並存明定。
- 實作要點:featureFactoryStore.ts completionQueue 加 `source:'batch'|'single'`;新 BatchRetentionPanel;按鈕呼 Phase2 endpoint;WS pending→面板;`'key' in payload` 權威;斷線 REST 補;page.tsx:510 單 modal 與 batch 面板獨立。
- 修改檔案:frontend featureFactoryStore.ts、BatchRetentionPanel、types.ts、page.tsx。
- 不可做:batch 不呼 deleteRun(/runs DELETE 單flow);不破單 symbol flow;不彈多 modal。
- 邊界:空佇列不顯示;deciding disable 防重複;WS 斷線 REST 補。
- 驗證:`cd frontend && npm run build` 綠 + **vitest 5 案例綠**(渲染/retain/discard/空佇列/**assert discard URL≠deleteRun URL**,多 item==1 面板);`*.test.tsx`。

### Phase 測試 + Gate
- 行為不變:flag 關 `python scripts/build_l65_golden_baseline.py --check` PASS + flag-off spy 時機同今日。
- retention 5 不變量 + crash matrix abc + 並發原子性。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B3_BATCH_RETENTION_SPEC.md TODO=docs/B3_BATCH_RETENTION_TODO.md FOCUS=post-hoc不延後/discard重用delete_run/真實free-space背壓/crash matrix/per-item lock/flag-off spy/vitest`
→ **雙家族 adversarial 確認 pass(v2 大改,Codex+Composer 各複審)** → Composer 實作(Phase1→4) + Codex review。
