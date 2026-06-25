**分階段 — Contract-First**

不同意 Claude §0 的二分法：我同意「不要 streaming-first 大重寫先行」，但也不同意「小尺度正確性全修完再接串流」；正確排序應是 **止血 → split/mask/artifact contract → 小尺度正確性 kernel → 串流化承載 → case-control 主戰場整合**。

**1. §0 核心排序**
Claude 的方向大致對，但 Phase 1 太像「在舊 materialized 路徑上補正確性」。這有返工風險。

不會白做的部分：
- FDR BH / p-value schema / q-value 定義
- Net IC 量綱公式
- HAC / block bootstrap 的統計 kernel
- factor attribution 真實作或 UI 正名
- event fail-closed、顯式事件表、matching 語義

可能白做或重接的部分：
- 把 FDR 硬接進舊 Stage5 全 DataFrame 路徑
- 對舊 report JSON 做大量前端接線，之後 API 改 top-N + artifact URI
- 在 `_materialize_features_for_ic` 上修 train/test/winsor 流程，之後 direct L7 會繞過
- 大量 deep module 舊路徑整線

scale-dependent 必須等串流或至少先定 contract：
- 430K 全量 FDR 的 p-value collection 與 `not_evaluated/scope=top_k`
- train-only winsor 分位，若 feature universe 430K，需 exact two-pass 或 L7 processed artifact contract
- cross-sectional exact gate，不能先 per-symbol survivor 粗篩當正式答案
- redundancy/VIF/corr cap 與 deterministic truncation metadata
- output contract：full metric table artifact，不是巨 JSON

所以我的判斷：**contract-first，不是 streaming-first，也不是 old-path correctness-first。**

**2. Phase 2 vs Phase 3**
不要把「case-control」和「430K streaming」視為互斥先後。case-control 是產品主戰場，但 full case-control 若直接吃 430K×百 symbol，仍會撞上同一個矩陣爆點。

我會切成：
- **Phase 2A 先做事件研究語義 kernel**：事件清單、正反標籤、pre-event window、matching、事件不足 fail-closed、purged split。用小尺度真資料驗證研究語義。
- **Phase 3 接著做串流承載**：direct L7、chunk iterator、row mask plan、metric sink、candidate set。
- **Phase 2B 再做事件研究大尺度整合**：event mask + streaming feature chunks + artifact output + FDR。

這比 Claude 的「Phase 2 主戰場完整先於 Phase 3」更穩。事件列數小，不代表欄數小；主戰場仍會被 430K feature universe 打爆。

**3. Phase 內依賴**
Claude 說 1a train/test 是 1b FDR、1e 顯著性的前提，太絕對。

更準確：
- FDR 不必等完整 train/val/test，但必須知道 **selection scope**。最低要求是「q-value 是在哪個 universe、哪個 split、哪些 evaluated features 上算的」。
- 顯著性也不必等完整 1a，但必須先停止「rolling IC 當 i.i.d.」假設。HAC/block bootstrap 可以先做成 kernel。
- train/test 是 feature selection、winsor fit、FDR selection reporting、event OOS 的前提，不是所有統計功能的前提。
- Phase 2 不需 1a 全部完成，但必須有 split/mask contract。否則事件 OOS 和 matching 會重做。

**4. 漏排與切 phase 問題**
漏排最大的是 **timestamp 秒/毫秒 fail-closed**。CONVERGED 把 B7 列 P0，但 Claude roadmap 沒放進 Phase 0/1。這是正確性，不只是大尺度。

還漏了：
- `by_volatility` schema 預設 true 但未實作，應 fail-closed 或接實作
- persistent task registry / resume exactly-once，若 streaming 後任務變長，不能靠 memory `_tasks`
- API versioning/top-N + artifact URI 決策，這會影響前端接線是否返工
- `not_evaluated` 語義，這是 staged screening 的防假綠核心
- golden suite 應貫穿，不該只放 Phase 3 的 E7

工時判斷：
- Phase 0 是小到中，不是純小，因為含前後端 WS/to_thread/error handling。
- Phase 1 若包含 train/test 主路徑、FDR、HAC、Net IC、attribution、前端圖表，已經是大，不是中。
- Phase 2 是大，但應拆 2A/2B。
- Phase 3 是大，而且會改 API/data contract，不能當「平行後置基礎軌」輕描淡寫。

**5. 我的排序**
1. **P0 止血**：GroupedConfig crash、feature_filter 真落地但不可靜默截斷、to_thread + WS 真錯誤、decay log 聚合、timestamp 秒/毫秒 fail-closed、`by_volatility` fail-closed。
2. **P1 正確性 contract**：SplitPlan、RowMaskPlan、SelectionScope、EvaluatedScope、Artifact/metric table schema、`not_evaluated` 語義、API versioning 決策。
3. **P2 小尺度統計 kernel**：FDR、Net IC、HAC/block bootstrap、train-only winsor/selection 規則、factor attribution 真實作或 UI 正名。避免深綁舊 materialized route。
4. **P3 事件研究 2A**：顯式事件表、正反標籤、pre-window 對齊、matching、事件不足 fail-closed、purged OOS。先用小尺度驗證主戰場語義。
5. **P4 大尺度 streaming spine**：direct L7、column chunks、metric sink、candidate set、resume、chunk checksum、cross-sectional exact gate。
6. **P5 事件研究 2B + 430K 整合**：event row masks × streaming columns、全量 FDR scope、artifact output、前端 top-N/report 讀 artifact。
7. **P6 多因子/ML/Agent**：IC→ML bridge、多因子組合、marginal/residual IC、DSR/PBO/MinBTL、Agent 顧問層。

關鍵主張：**先修「語義與 contract」，再修「kernel」，再建「scale spine」；不要在舊全矩陣管線上把所有正確性補滿。**

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、roadmap phasing、whole map、optimization converged、grouped crash analysis；本回合未讀程式碼，判斷限於指定規劃文件  
TESTS_RUN: none, read-only planning review  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: 建議新增/明確化 split scope、evaluated scope、not_evaluated、artifact URI/API versioning；未改檔  
HANDOFF_NOT_UPDATED: read-only sandbox 且使用者要求 read-only 規劃委員會  
STATUS: DONE