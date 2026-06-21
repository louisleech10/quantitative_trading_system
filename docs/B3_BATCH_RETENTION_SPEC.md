# B3 — 批次 Run 保留對話 (Q2-A) — SPEC v2（雙家族 adversarial reconcile 後）

> 決策依據：handoffs/20260619-ffconsist-FINAL.md(Q2-A,大) + 雙家族 adversarial(handoffs/20260619-b3-adv-codex.md / -composer.md) + 使用者 2026-06-21 選「B3 含 discard 即刪」。日期：2026-06-21｜對應 TODO：docs/B3_BATCH_RETENTION_TODO.md
>
> **v2 設計轉向（解 4 BLOCKING）**：retention 改 **post-hoc mark**——run 照常生成+register（**不延後任何副作用**），retention 是疊加的狀態標記；**discard → 立即重用既有 `delete_run` 刪該單一 run** 釋放磁碟；背壓用**真實 free-space gate**。如此 ① 多下游(browse/quality/RunManager)看到的 run 與今日完全一致(無延後→無不一致) ② discard 真的刪→背壓自洽不死鎖。

## §RISK 風險分級
- **大小**：大。**命中 (b)** 共用路徑(checkpoint + delete_run 多下游) + **(c)** 多 phase·crash-resume 難回退。**不命中 (a)/(d)**——不碰特徵值/ML/回測正確性。
- → §G N/A;以 retention 5 不變量 + crash matrix + 並發原子性 + flag-off spy(`build_l65_golden_baseline.py --check` byte 不足以證時機,需 spy)驗證。**feature flag 預設關=今日行為** 為總護欄。

## §A 假設與待使用者確認（v2 已修正 v1 事實錯誤）
- **已驗證事實**(grep/Read 實測,附行號;v2 修正):
  - **成功時有三個即時副作用**(非 v1 誤以為的單一 register):① `feature_factory.py:3227 self._registry.add(registry_payload)`(生成結束即 FeatureRegistry.add,在 momentum/ 引擎);② `feature_factory_batch_service.py:606 self._browse_registrar.register(...)`(browse);③ 磁碟 artifact(生成時寫)。→ **v2 不延後任一**,故下游一致性不受影響。
  - quality adapter side-effect:`feature_factory_batch_adapters.py:34 register_hdf5_for_browse`(compute 內自帶 register)。post-hoc mark 下不受影響(run 本就 registered)。
  - checkpoint schema:`_build_initial_checkpoint`(feature_factory_batch_service.py:**889-916**,有 schema_version/completed_items/failed_items/queued_items);v1 誤標 :178-209(實為 resume_batch)。
  - **單 run 刪除已存在可重用**:`DELETE /runs/{symbol}/{timeframe}/{config_hash}`(api/routes/feature_factory.py:103)→ `feature_factory_service.delete_run(symbol,tf,config_hash)`(刪 artifact+registry)。B3 discard **後端重用 delete_run**(非前端 deleteRun action)。
  - 前端單 symbol 保留:`completionQueue`(store:82,單筆:479)+ `RunRetentionDialog.tsx`(deleteRun:546 打 DELETE /runs)。batch 需 `source` 區分,不可誤路由到單 flow。
- **待確認**：無。**已確認**(2026-06-21 使用者選「B3 含 discard 即刪該單一 run」;委員會兩輪 FINAL + 雙家族 adversarial 定 post-hoc mark)。

## §C 約束
- 解耦:狀態在 batch service checkpoint;discard 重用 api delete_run;不新增跨域依賴。
- **不可違反**:① 不改特徵值/生成/register 行為(post-hoc mark 純疊加);② **非阻塞**——pending 待決不卡其他 symbol;③ **背壓用真實 free-space**(`shutil.disk_usage`,非邏輯記帳),低於閾值且有 pending→暫停新生成,decision 後 wakeup 重評;低磁碟但無 pending 可 discard→誠實 hard-pause+log(非死鎖);④ **discard 冪等**(delete_run 對已刪 no-op success);⑤ **decision 原子**(per-item lock + deciding 占位,防 retain/discard race);⑥ **flag 預設關=今日完全行為**。
- 注意:transactional **bulk** delete(多選/tombstone)留 B4;B3 discard 為 scoped 單 run。

## §G Golden / Baseline
- N/A(移 §N)。行為不變:flag 關 → `python scripts/build_l65_golden_baseline.py --check` PASS **且 spy 驗 register/quality 時機與今日一致**(byte 不足以證時機)。

## §P Phase 與依賴

### Phase 1 — checkpoint retention 狀態 + post-hoc mark(依賴:無)
**Task 1.1 — retention 狀態欄 + 成功標 pending**
- 目標:checkpoint item retention 狀態 `pending→deciding→retained/discarded/retention_error`;flag 開時成功 item(已正常 register 後)**疊加標 pending**(存 symbol/tf/config_hash/hdf5_path)。`retention_error` 觸發定義=discard 的 delete_run 拋例外。
- 檔案:feature_factory_batch_service.py(checkpoint schema :889-916 加欄 + `_record_item_result`:586 成功尾端標 pending;**不動 :606 register 時機**)。
- 驗證:狀態轉移合法/非法拒絕;flag 關不寫 retention 欄;`pytest tests/api/ -k retention_state`;flag 關 `build_l65_golden_baseline.py --check` PASS。
- 邊界:flag 關=今日行為(無 pending);crash 後載入狀態正確;非法轉移不靜默(raise/4xx)。　不可做:不延後 register/不改數值。

### Phase 2 — decision endpoints + 原子 + 重用 delete_run(依賴:Phase 1)
**Task 2.1 — retain/discard endpoint(per-item,非阻塞,原子)**
- 目標:POST 決定 endpoint:retain→pending 清除(run 已 registered,無他事);discard→`deciding` 占位→重用 `feature_factory_service.delete_run(symbol,tf,config_hash)` 刪該 run→標 discarded。per-item async lock/CAS 防並發。**待決不阻塞 wave**。
- 檔案:api/routes/feature_factory.py(新 batch retention decision endpoint)+ feature_factory_batch_service.py(decision 方法+lock)+ api/models。
- 改法:decision 先 CAS pending→deciding;discard 呼 delete_run(冪等);decision 結果**先持久化 checkpoint 再回 200**(寫失敗→回 5xx,decision 未提交,可重試)。
- 驗證:retain 清 pending;discard 刪檔+browse 不見+標 discarded;並發 retain/discard 僅一勝(另 409/no-op);重複 discard 冪等;不存在 item→404;待決時他 symbol 續;`pytest tests/api/ -k retention_decision`。
- 邊界:重複 decide 冪等;404;並發安全;delete_run 拋→retention_error 不靜默。　不可做:不阻塞 wave;不碰 B4 bulk。
**Task 2.2 — REST 列 pending + WS 推 pending**
- 目標:GET 列 batch pending items(identity/state/hdf5_path/error);WS 完成時推 pending item(B2 normalize 風格)。
- 檔案:api/routes/feature_factory.py + feature_factory_ws.py(`map_batch_progress_ws_data` 擴 retention)+ api/models + frontend types。
- 驗證:list 回未決 items;WS 推 pending;`pytest tests/api/ -k retention_list`。
- 邊界:無 pending 回空;WS 斷線靠 REST list 補。

### Phase 3 — 真實 free-space 背壓 + wakeup(依賴:Phase 2)
**Task 3.1 — free-space 背壓 gate**
- 目標:wave 派新生成前 `shutil.disk_usage` 取真實 free bytes(T-C `column_group_registry` 的 free-space gate 為樣式參考,非同符號);< 閾值+有 pending→暫停;decision(retain/discard)後 wakeup 重評續跑;< 閾值且無 pending 可釋放→hard-pause+log(誠實,非死鎖)。閾值/reserve env 可配。
- 檔案:feature_factory_batch_service.py(wave gate + decision 後 wakeup)。
- 驗證:模擬低 free-space+pending→暫停;discard 釋放後續跑;無 pending→hard-pause 不死鎖;`pytest tests/api/ -k retention_backpressure`。
- 邊界:閾值未設用 tier 預設;不死鎖;wakeup 不漏。　不可做:不用邏輯記帳替真實 free-space。

### Phase 4 — frontend per-item retention 面板(依賴:Phase 2/3)
**Task 4.1 — batch per-item 面板(source 區分,非 N modal,不打 deleteRun)**
- 目標:completionQueue 加 `source:'batch'|'single'` 區分;batch 用**可展開面板**逐項 retain/discard,呼 Phase2 batch endpoint(**非單 flow deleteRun**);與 page.tsx:510 單 symbol modal 並存關係明定(batch 面板獨立元件,不互搶)。
- 檔案:frontend featureFactoryStore.ts(completionQueue 加 source)、新 BatchRetentionPanel、types.ts、page.tsx。
- 改法:WS pending→面板;按鈕呼 batch decision endpoint;狀態用 B2 normalize/`'key' in payload` 權威;斷線 REST list 補。
- 驗證:`cd frontend && npm run build` 綠 + **vitest 5 案例綠**(渲染/retain/discard/空佇列/**assert discard URL≠deleteRun URL**,多 item==1 面板非 N modal);對應 `*.test.tsx`。
- 邊界:空佇列不顯示;deciding 中 disable 防重複;不破單 symbol 既有 flow。　不可做:batch 不呼 deleteRun(/runs DELETE 單flow)。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(狀態機/lock/背壓估算)/整合(真實小 batch flag 開:標 pending→retain 留/discard 刪+browse 不見;resume)/前端(vitest)/行為不變(flag 關 spy+byte)。
- **防假綠**:不放寬既有 batch 測試;新斷言逐條碰真實下游(browse/quality/delete_run/disk),非 smoke。
- **retention 5 不變量(逐條 fixtures/commands/assertions,可證偽)**:
  ① 狀態轉移僅合法(pending→deciding→retained/discarded/error;非法 raise)——`-k retention_state`,assert 非法轉移拋。
  ② retain==今日:flag 開 retain 後 run 的 browse_task_id/quality 與 flag 關時相同(spy 比對)——`-k retention_retain_equiv`。
  ③ discard:delete_run 被呼且該 run artifact 不存在(`Path.exists()==False`)+browse list 不含——`-k retention_discard_delete`。
  ④ 非阻塞:A pending 未決時 B symbol 跑完(整合,assert B 完成 timestamp)——`-k retention_nonblock`。
  ⑤ resume 守恆(crash matrix,見下)。
- **crash matrix(injected-crash tests,可驗 crash points)**:(a)成功 register 後標 pending 前 crash→resume 對「已 registered 未標」reconcile 成 pending(不重算/不重 register);(b)discard delete_run 後標 discarded 前 crash→resume 見 artifact 已無→冪等收斂 discarded;(c)decision checkpoint 寫失敗→回 5xx 未提交→重試冪等。idempotency key=(symbol,tf,config_hash)。`-k retention_crash`。
- **並發原子性**:同 item 並發 retain/retain、retain/discard、discard/discard→僅一 terminal,無重複 delete_run/register——`-k retention_concurrent`。
- **flag-off spy(Codex#7/Composer#4)**:flag 關時 spy registrar/quality→`_record_item_result` 同步立即 register(call count/timing 同今日)、不寫 retention 欄、browse_task_ids 舊時機出現——`-k retention_flag_off`。
- **行為不變 + diff scope**:flag 關 `build_l65_golden_baseline.py --check` PASS;**diff 不碰 generate_features 生成參數/數值路徑→BLOCK**。
- **邊界目錄**:flag 關=今日行為/crash matrix abc/重複 decide 冪等/404/並發/背壓 hard-pause 不死鎖/wakeup 不漏/前端空佇列/discard URL≠deleteRun/WS 斷線 REST 補。

## §R 回退
- **feature flag**(env,預設關=今日立即 register 行為)總護欄;關閉即完全回退。每 Phase 獨立 commit。discard 重用既有 delete_run(無新刪除邏輯)降風險。byte 變(flag 關)或 flag-off spy 失敗=立即 revert。

## §N N/A 登記
- §G Golden:**N/A — 工作流疊加,非數值**;改以 flag 關 `python scripts/build_l65_golden_baseline.py --check` PASS(abs≤1e-6,byte 不變)+ **flag-off spy 驗 register/quality 時機同今日** + retention 5 不變量 + crash matrix + 並發原子性 驗證。
