# B3 — 批次 Run 保留對話 (Q2-A) — SPEC

> 決策依據：handoffs/20260619-ffconsist-FINAL.md(Q2-A,P2,大;委員會兩輪定案,等同決策簡述)｜日期：2026-06-19｜對應 TODO：docs/B3_BATCH_RETENTION_TODO.md

## §RISK 風險分級
- **大小**：大。
- **命中**：**(b) 共用路徑**(batch register/checkpoint 多下游:browse/quality/RunManager) + **(c) 多 phase·難回退**(checkpoint 狀態機 + staging + resume)。**不命中 (a)/(d)**——不碰特徵值/ML/回測正確性,純工作流。
- → §G N/A;以 retention 5 不變量 + resume 守恆 + byte 不變(`build_l65_golden_baseline.py --check`)驗證。**feature flag 預設舊行為**(立即 register)護欄。

## §A 假設與待使用者確認
- **已驗證事實**(grep/Read 實測,附行號):
  - 批次成功即時 register:`_record_item_result`(feature_factory_batch_service.py:586)→`:606 browse_task_id = self._browse_registrar.register(symbol, timeframe, hdf5_path)`。**這是 staging 切點**(改為「先 staging,retention 決定後才 register」)。
  - checkpoint 結構:`completed_items`/`queued_items`/`status`(:178-209);resume 由 completed/queued 驅動。
  - 前端單 symbol 保留:`completionQueue`(store:82,單筆:479)+ `RunRetentionDialog.tsx`(用 completionQueue[0]、deleteRun:61)。**擴成 batch per-item queue**(非 N 個 modal)。
  - browse_registrar/quality_computer 為注入(:81-90);DI 邊界清楚。
- 待確認：無。**已確認**(2026-06-19 使用者明示「批次加保留對話」+委員會兩輪 FINAL 定:batch 加保留、非阻塞、背壓、staging、狀態機、resume、前端 per-item)。

## §C 約束
- 解耦:狀態/邏輯在 batch service + 注入介面;不新增跨域依賴;前端走既有 store/WS。
- **不可違反**:① 不改特徵值(staging 只改 register 時機,不改生成/數值);② **非阻塞**——retention 待決不卡其他 symbol 生成;③ **磁碟背壓**——staging 未決堆積達閾值須暫停新生成(防 disk full,接 T-C 磁碟教訓);④ **resume 守恆**——retention_pending 的 item resume 後不重算已成功的層、不漏不重 register;⑤ feature flag 關閉=完全舊行為(立即 register)。
- 注意:partial-failure(部分 symbol 成功部分失敗)retention 各自獨立;tombstone/實刪留 B4。

## §G Golden / Baseline
- N/A(移 §N)。行為不變:flag 關 → `python scripts/build_l65_golden_baseline.py --check` PASS 且 register 時機與舊一致(byte+流程不變)。

## §P Phase 與依賴

### Phase 1 — backend:staging + retention 狀態機(依賴:無)
**Task 1.1 — retention 狀態機 + checkpoint 欄位**
- 目標:checkpoint item 加 retention 狀態:`generated`(staging,待決)→`retained`(register 完成)/`discarded`(放棄)/`retention_error`;成功 item 預設進 `generated`(flag 開時)。
- 檔案:feature_factory_batch_service.py(checkpoint 讀寫:178-209 區 + _record_item_result:586)。
- 改法:flag 開→`_record_item_result` 成功不立即 register,改寫 staging 狀態 + hdf5_path 入 checkpoint(retention_pending);flag 關→舊行為(:606 立即 register)。
- 驗證:狀態轉移合法(generated→retained/discarded/error,非法轉移拒絕);`pytest tests/api/ -k retention_state`。
- 邊界:flag 關=舊行為;crash 後 checkpoint 載入 retention 狀態正確;非法轉移不靜默。　不可做:不改數值;不在此刪檔(B4)。

**Task 1.2 — staging→register 決定端點 + 非阻塞**
- 目標:retain/discard 決定 endpoint(per-item):retain→`browse_registrar.register`(原 :606 邏輯)+quality;discard→標 discarded(不 register,實刪留 B4 由 tombstone)。**待決不阻塞其他 symbol**。
- 檔案:feature_factory_batch_service.py + api/routes/feature_factory.py(新 endpoint) + api/models。
- 改法:decision 操作 staging item;非阻塞(背景 wave 繼續);register 沿用既有 _record_item_result:606 邏輯(行為等價,只挪時機)。
- 驗證:retain 後 browse 可見、quality 算;discard 不 register;待決時其他 symbol 續跑;`pytest tests/api/ -k retention_decision`。
- 邊界:重複 decide 冪等;decide 不存在 item→404;並發 decide 安全。　不可做:不阻塞 wave。

**Task 1.3 — 磁碟背壓**
- 目標:staging(generated 未決)累積 hdf5 bytes 達閾值→暫停派新生成,待 retain/discard 釋放再續(接 T-C cumulative disk 模式)。
- 檔案:feature_factory_batch_service.py(wave 派工前檢查)。
- 改法:估 staging 未決 bytes + reserve;超閾值→wave gate 等待(非崩潰),log 提示;閾值/reserve 可配(env,沿用 T-C `_resolve_*_reserve_bytes` 風格)。
- 驗證:模擬 staging 超閾值→新生成暫停、決定後恢復;`pytest tests/api/ -k retention_backpressure`。
- 邊界:閾值未設用預設;背壓中 decide 釋放後續跑;不死鎖。

### Phase 2 — frontend:per-item retention queue(依賴:Phase 1)
**Task 2.1 — batch retention queue + 面板**
- 目標:擴 completionQueue 成 batch per-item(多 symbol×tf 待決),用**可展開面板**(非 N 個 modal)逐項 retain/discard,接 Phase 1 endpoint。
- 檔案:frontend featureFactoryStore.ts(completionQueue 擴 batch)、RunRetentionDialog.tsx 或新 BatchRetentionPanel、WS/REST 接 retention 狀態。
- 改法:WS 推 staging item;面板列待決 item + retain/discard 按鈕呼叫 endpoint;狀態用 B2 normalize/`'key' in payload` 權威清除。
- 驗證:`cd frontend && npm run build` 綠 + **vitest 4 案例綠**(面板渲染/retain/discard/空佇列,assert 多 item==1 面板非 N modal);對應 `*.test.tsx`。
- 邊界:空佇列不顯示;decide 中 disable 按鈕防重複;WS 斷線 REST 補。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(狀態機/背壓估算)/整合(真實小 batch flag 開:staging→retain→browse 可見;discard 不見;resume 守恆)/前端(vitest 面板)/行為不變(flag 關 byte)。
- **防假綠**:不放寬既有 batch 測試;新斷言 retention 狀態轉移 + 非阻塞 + 背壓 + resume 守恆 + flag 關 byte 不變。
- **retention 不變量(可證偽)**:①狀態轉移僅合法路徑(generated→retained/discarded/error);②retain==舊 register 結果(browse_task_id/quality 等價);③discard 不 register、不在 B3 刪檔;④待決不阻塞其他 symbol(整合:A 待決時 B 完成);⑤resume:retention_pending item 重啟後狀態還原、不重算成功層、register 不重不漏。
- **背壓不變量**:staging bytes 超閾值→wave 暫停;decide 釋放→續;不死鎖。
- **行為不變 + diff scope**:flag 關 `build_l65_golden_baseline.py --check` PASS + register 時機同舊;**diff 不碰 generate_features 生成參數/數值路徑→BLOCK**。
- **邊界目錄**:flag 關=舊行為/crash-resume 狀態還原/重複 decide 冪等/404 不存在 item/並發 decide/背壓不死鎖/前端空佇列/WS 斷線 REST 補。

## §R 回退
- **feature flag**(env,預設關=舊立即 register 行為)為總護欄;關閉即完全回退。每 Phase 獨立 commit。狀態機/背壓/前端分離可逐 Phase revert。byte 變(flag 關)=立即 revert。

## §N N/A 登記
- §G Golden:**N/A — 工作流/register 時機改動,非數值**;改以 flag 關 `python scripts/build_l65_golden_baseline.py --check` PASS(abs≤1e-6,byte 不變)+ retention 5 不變量 + 背壓 + resume 守恆 驗證。
