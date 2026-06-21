# FF 一致性 R2 — Claude(ops) 交叉詰問

對 R1 結論無翻案(E/優先序三方+雙審已穩);聚焦釘死 5 開放點。

## 1. E 本輪範圍
**定案:本輪 mandatory = 共用 payload schema + error-class 統一 + 雙路徑 parity tests。薄 Sink 封裝 = 選做(若 ≤半天且不擾現碼則做,否則延)。GenerationRunner adapter = 延後。**
- 理由:防漂移的最低必要是「兩路徑送同 schema/error、有測試鎖住」。Sink 類是組織手段非防漂移必需;不該為抽象擴大本輪面。parity test 才是硬鎖。

## 2. Q3 RSS
**定案:分欄——`process_rss_mb`(單,同進程含 API)、`worker_rss_mb`(batch 子進程該 symbol)。前端各自標籤,不跨路徑比較。** 同欄+註解易被忽略誤讀。
- rolling 10/100 sub-step:**保留在 message 欄**(自由文字),不升為結構欄;結構欄只到 layer 粒度。concurrent>1 不輸出假 current_stage(維持)。

## 3. Q2
- ① **非阻塞**:retention 對話入 queue,batch 續跑下一 symbol(與單路徑一致;暫占磁碟可接受,T-C 預檢已防爆)。
- ② **per-item 複用單的 completionQueue**(逐 item entry),前端呈現為**可清的佇列/清單**而非 N 個強制 modal。統一機制,不另造。
- ③ **MVP 分期:Phase A(P2)=prompt+延後 register+per-item keep/discard+checkpoint `retention_pending/decided`;Phase B(P2.5)=後端交易式 bulk-delete endpoint。** A 先可用,B 補健壯刪除。
- ④ 部分失敗:register/delete 逐 item 結果記 checkpoint;失敗標 `retention_error` 可重試,不靜默。
- ⑤ staging 切點:**先實測** `_record_item_result`/`batch_service:583` 現是否 mid-run register,再定把 register 移到 decision 後(實測 > 假設)。

## 4. #1 原子性
**定案:concurrent=1 下 non-rotating FileHandler 指當日檔(`FFACT_API_LOG_PATH`)即足、先落地;多進程同檔行原子性留待並行(T-A)時以壓測證明,本輪加一個 TODO/註解標記,不阻塞。** 不為尚未啟用的並行先過度工程。

## 5. 優先序
**定案:Q5(P0,最小最安全先落)→#1(P0)→Q3(P1)→Q2-A(P2)→Q2-B(P2.5);E parity tests 隨 #1/Q3/Q2 各自落地時一併寫(不單列)。** Q2-A 可在 Q3 後即做(prompt+延後 register 不依賴更多)。

## 剩餘漏洞自查
- E parity test 最小集(可證偽):兩路徑同 schema+version、同 error class、retention pending→decided 狀態轉移、concurrent>1 無假 current_stage。此 4 條為驗收門檻。
- 無新證據翻案 E。
