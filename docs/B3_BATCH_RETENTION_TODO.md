# B3 批次 Run 保留對話 (Q2-A) TODO
> 版本：DRAFT｜基於 SPEC：docs/B3_BATCH_RETENTION_SPEC.md｜日期：2026-06-19

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | retention 狀態機 + checkpoint 欄位 | Phase1 |
| Task | 1.2 | staging→register 決定端點 + 非阻塞 | Phase1 |
| Task | 1.3 | 磁碟背壓 | Phase1 |
| Task | 2.1 | frontend per-item retention queue + 面板 | Phase2 |
| 不變量 | RETAIN | retention 5 不變量 | §V |
| 不變量 | BACKP | 背壓不死鎖 | §V |
| 不變量 | BYTE | flag 關 byte+register 時機同舊 | §G/§V |
| 風險 | (b)(c) | 共用 register/checkpoint·多phase難回退 | §RISK |
| flag | RETENTION flag 預設關=舊行為 | 護欄 | §R |
- 合計：Task=4、不變量=3、風險=1、flag=1。

## §0 全域規則
- **不改數值(核心)**:staging 只改 register 時機,不改生成/數值;flag 關 `build_l65_golden_baseline.py --check` PASS。
- **feature flag 預設關**:關=完全舊行為(_record_item_result:606 立即 register);開才走 staging/retention。
- **非阻塞**:retention 待決不卡其他 symbol 生成。
- **磁碟背壓**:staging 未決 bytes 達閾值→暫停派新生成,decide 釋放再續(接 T-C)。
- **resume 守恆**:retention_pending item 重啟後狀態還原,不重算成功層,register 不重不漏。
- **diff scope**:不碰 generate_features 生成參數/數值路徑(碰=BLOCK)。
- **防假綠**:不放寬既有 batch 測試;新斷言 retention 5 不變量+背壓+resume+flag關byte。
- **B3 不刪檔**:discard 只標狀態,實刪/tombstone 留 B4。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B3a | 1.1 | 無 | 中(狀態機+checkpoint) |
| B3b | 1.2 + 1.3 | B3a | 中-大(決定端點+非阻塞+背壓) |
| B3c | 2.1 | B3b | 中(前端 per-item 面板+vitest) |
- Gate:B3a 狀態轉移合法測綠+flag關byte;B3b retain==舊register/discard不register/非阻塞/背壓不死鎖;B3c npm build+vitest+多item不彈多modal。

## Phase 1 — backend
### Task 1.1 — retention 狀態機 + checkpoint 欄位
- SPEC ref：1.1　目標:item retention 狀態 generated→retained/discarded/retention_error;flag 開成功 item 進 generated。
- 實作要點:checkpoint item 加 retention 狀態欄(:178-209 區);`_record_item_result`(:586)flag 開→寫 staging(retention_pending,存 hdf5_path)不 register;flag 關→舊 :606 立即 register。
- 修改檔案:feature_factory_batch_service.py。
- 不可做:不改數值;不在此刪檔;不破 flag 關舊行為。
- 邊界:flag 關=舊行為;crash 後載入 retention 狀態正確;非法轉移拒絕不靜默。
- 驗證:狀態轉移合法/非法拒絕;`pytest tests/api/ -k retention_state`;flag 關 `build_l65_golden_baseline.py --check` PASS。
### Task 1.2 — staging→register 決定端點 + 非阻塞
- SPEC ref：1.2　目標:per-item retain/discard endpoint;retain→register+quality(原:606 邏輯),discard→標 discarded;待決不阻塞。
- 實作要點:新 endpoint(api/routes/feature_factory.py)+ service 方法操作 staging item;retain 沿用 _record_item_result:606 register 邏輯(等價挪時機);discard 標狀態;背景 wave 續跑。
- 修改檔案:feature_factory_batch_service.py、api/routes/feature_factory.py、api/models。
- 不可做:不阻塞 wave;retain 行為須與舊 register 等價(browse_task_id/quality)。
- 邊界:重複 decide 冪等;不存在 item→404;並發 decide 安全。
- 驗證:retain 後 browse 可見+quality;discard 不 register;待決時他 symbol 續;`pytest tests/api/ -k retention_decision`。
### Task 1.3 — 磁碟背壓
- SPEC ref：1.3　目標:staging 未決 bytes 達閾值→暫停派新生成,decide 釋放再續。
- 實作要點:wave 派工前估 staging 未決 bytes+reserve(沿用 T-C `_resolve_*_reserve_bytes`/`_estimate_*` 風格);超閾值 wave gate 等待+log;閾值/reserve env 可配。
- 修改檔案:feature_factory_batch_service.py。
- 不可做:超閾值不得崩潰(暫停非 abort);不死鎖。
- 邊界:閾值未設用預設;decide 釋放後續跑;不死鎖。
- 驗證:模擬超閾值→暫停、決定後恢復;`pytest tests/api/ -k retention_backpressure`。

## Phase 2 — frontend
### Task 2.1 — batch per-item retention queue + 面板
- SPEC ref：2.1　目標:completionQueue 擴 batch per-item;可展開面板逐項 retain/discard(非 N modal)。
- 實作要點:featureFactoryStore.ts completionQueue 擴 batch;新 BatchRetentionPanel 或擴 RunRetentionDialog;WS 推 staging item;按鈕呼叫 Phase1 endpoint;狀態用 B2 normalize/`'key' in payload` 權威。
- 修改檔案:frontend featureFactoryStore.ts、retention 元件、types.ts。
- 不可做:不彈多 modal;不破單 symbol 既有保留流程。
- 邊界:空佇列不顯示;decide 中 disable 防重複;WS 斷線 REST 補。
- 驗證:`cd frontend && npm run build` 綠 + **vitest 綠**(渲染/retain/discard/空佇列);多 item 單面板。

### Phase 測試 + Gate
- 行為不變:flag 關 `python scripts/build_l65_golden_baseline.py --check` PASS + register 時機同舊。
- retention 5 不變量 + 背壓不死鎖 + resume 守恆。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B3_BATCH_RETENTION_SPEC.md TODO=docs/B3_BATCH_RETENTION_TODO.md FOCUS=非阻塞/背壓/staging/狀態機/resume守恆/flag預設舊/vitest`
→ **雙家族 adversarial(Codex + Composer 各一,大任務)** reconcile → Composer 實作(backend phase→frontend phase) + Codex review。
