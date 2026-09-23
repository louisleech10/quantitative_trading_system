# ROADMAP — 量化交易系統戰術路線圖

> **這份只回答一個問題：現在在哪、接下來做什麼。** 敘事與歷史在 `docs/ROADMAP_DETAIL.md`。
> 即時任務狀態看 `HANDOFF.md`；決策理由看 memory。
> 維護：**每次 commit 一併更新本檔**（2026-06-26 使用者定）。日期看 git log，手寫日期欄已廢。

當前階段：**V1.0 工具階段** — crypto 單市場研究管線（探索 → 發現 Pattern → ML 優化 → 回測）。
願景 V1→V2→V3 見 `PRODUCT_VISION.md`。

---

## 🔥 現在在哪（狀態表）

> 🔴 **本節狀態一律由 `scripts/fact_keys.json` 生成，禁手改**（DOCROT2 Task 4.1）：改狀態＝改該檔 rows 後跑 `bash scripts/gen_fact_key_blocks.sh --write`。
> 想寫背景、理由、歷史 ⇒ 寫進 `ROADMAP_DETAIL.md`，本節只放狀態、下一步與權威路徑。
> 病根（使用者 2026-08-14 第四次指出）：本檔曾 227 行、其中「進行中／下一步」一節佔 213 行
> ⇒ 要回答「我在哪」得讀 213 行敘事。**主委四次說要改、四次講完就放掉。**
> 改為生成前之手寫狀態表（含各線敘事）見 commit `61aa55b0` 之本檔第 18–44 行。

### 各工作線

<!-- BEGIN GENERATED: roadmap-status -->
| 序 | 識別碼 | 工作線 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|---|
| 010 | RM-SEARCH-FIX | `/search` 修復（out-of-epic） | 已完成 | handoffs/reconcile/20260822-searchfix-x-review-r7/synth.md | — |
| 020 | RM-GOV | 治理 epic（使用者 2026-08-14：留現狀、不再擴建） | 停手 | docs/ROADMAP_DETAIL.md | 不再擴建；例外限使用者明示授權之治理票（票狀態見 docs/GOV_TICKET_SOT.md） |
| 030 | RM-P1-6 | P1-6 委員債狀態機 | 停手 | docs/ROADMAP_DETAIL.md | 不排程：線 C 未做，治理不再擴建 |
| 040 | RM-GAP-1 | GAP-1 DSR/PBO/MinBTL 策略層防偽 | 已完成 | docs/GAP1_STRATEGY_OVERFIT_TODO.md | — |
| 050 | RM-PA-CUMSUM | PA-CUMSUM 單利權益改正（小票） | 已完成 | handoffs/reconcile/20260818-pacumsum-x-review-r23/synth.md | — |
| 060 | RM-GAP-2A | GAP-2a 邊際 IC／多因子組合（純 IC 層） | 已完成 | docs/GAP2_MARGINAL_IC_SPEC.md | — |
| 070 | RM-GAP-2B | GAP-2b IC→ML 橋 | 部分完成 | docs/IC_QUANT_GAP_REGISTRY.md #2b | 契約已落地；橋本體等 ML 層穩定（殘留 G2-R1） |
| 080 | RM-GAP-3 | GAP-3 事件型分析（外部正反例匯入→PIT 對齊→條件 IC／ML） | 部分完成 | docs/IC_QUANT_GAP_REGISTRY.md #3 | 使用者 UAT 驗收（排最後；見 SPLITUNIFY 殘留 R-3） |
| 090 | RM-GAP-4 | GAP-4 Pooled/Panel IC | 未開工 | docs/IC_QUANT_GAP_REGISTRY.md #4 | 排程即可開票（Phase 4） |
| 100 | RM-GAP-5 | GAP-5 容量 ADV 接線 | 未開工 | docs/IC_QUANT_GAP_REGISTRY.md #5 | 待觸發：volume 資料源就緒 |
| 110 | RM-GAP-6 | GAP-6 430K 規模防護 | 未開工 | docs/IC_QUANT_GAP_REGISTRY.md #6 | 併 IC-PERF／串流 epic |
| 120 | RM-TICKET-A | 票 A（timing-overlap 診斷） | 未開工 | docs/ROADMAP.md「後續兩票」節 | Phase 4；硬前置 FU-2 |
| 130 | RM-TICKET-B | 票 B（多標的橫截面 attribution） | 未開工 | docs/ROADMAP.md「後續兩票」節 | 待觸發：研究宇宙變多標的；硬前置 FU-2 |
| 140 | RM-FU-1 | FU-1 exposure `fillna` fail-closed | 未開工 | docs/ROADMAP.md「兩筆 follow-up」節 | 待觸發：下一次動 exposure 家族時處理 |
| 150 | RM-FU-2 | FU-2 cache close carrier index 對齊 | 部分完成 | docs/ROADMAP.md「兩筆 follow-up」節 | 對齊與缺席 fail-closed 已隨 LA-2 B3 落地；剩「對齊後整欄 NaN 不擋」一條守衛，票 A／票 B 開工前補 |
| 160 | RM-EVTLABEL | EVTLABEL 事件型 label 三缺陷＋匯入標籤模式 | 已完成 | docs/EVTLABEL_TODO.md | — |
| 170 | RM-TIERTOGGLE | TIERTOGGLE 幽靈開關（具名 preset 之 IC Decay／Grouped IC） | 已完成 | 白話說明/EVTLABEL施工進度.md | — |
| 180 | RM-FU-3 | FU-3 報告逐 stage 耗時揭露（併 EVTLABEL P1） | 已完成 | momentum/Analysis/ic_filter_orchestrator.py（metadata.stage_timings） | — |
| 190 | RM-FU-4 | FU-4 IC 頁說明框：報酬版 vs 標籤版（併 EVTLABEL Task 3.9） | 已完成 | docs/EVTLABEL_TODO.md Task 3.9 | — |
| 200 | RM-GLOBALH | GLOBALH 多 horizon 全算＋逐列標 h／k＋可篩（中票） | 未開工 | 白話說明/接下來要做的票.md | 排序 4（委員會共識：與 ICPATH 分開、排其後，理由＝兩者資料層不同，合併會返工） |
| 210 | RM-DOCROT | DOCROT 文檔多輪根因（治理） | 已完成 | handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md | — |
| 220 | RM-SEARCH2EVENT | SEARCH2EVENT 搜尋條件→事件批接線（純轉接器）— 已作廢，由 RM-EVENTSCAN 取代 | 停手 | docs/SEARCH2EVENT_SPEC.md §SUPERSEDED | 使用者 2026-09-20 裁定方向重定：七輪 SPEC 皆在解「搬運」，而使用者要的是「條件本身能不能用指標」；實查條件掃描無任何均線／RSI／MACD ⇒ 搬運做完也答不了使用者的問題。v7 六條 finding 全數轉為 RM-EVENTSCAN 之輸入事實 |
| 225 | RM-EVENTSCAN | EVENTSCAN 條件掃描→持有 N 根報酬 vs 隨機對照報酬（大票，單標的） | 停手 | 白話說明/EVENTSCAN方向與做法.md | 🔴 **2026-09-22 起暫停**（使用者裁定先做 SPEC／TODO 流程優化；其中 TODO 改格式已於 2026-09-23 由 RM-TODOFMT 完工，何時復工待使用者決定；復工時先依新格式產出本票 manifest）。停手時：SPEC 經兩家對抗審至 R12 收斂、未凍結，R12 末仍 11×P1。以下為停手前之沿革——🔴 **現況＝SPEC 已起草，兩家對抗審至 R8，尚未凍結**（下一步＝收斂 R8 → 逐條白話解釋並由使用者放行 → 凍結 SPEC → 寫 TODO；**不是實作**）。大票完整管線：①寫 SPEC →②兩家對抗審→收斂→凍結 →③寫 TODO →④兩家對抗審→收斂→凍結 →⑤分批實作 →⑥每批審碼→收斂，目前在②。方向與做法已定案（偵察 r1 十一條＋量化方法 consult r2 十四條皆收斂銷帳；使用者九項裁定；方向書 v10 經逐章稽核），但那是 SPEC 之**前置**不是替代。權威＝白話說明/EVENTSCAN方向與做法.md（使用者要的數字、九項裁定、十步做法、八個缺口）。做法十步含：條件引擎吃 FF 欄且欄名打錯要報錯／欄位選擇器（該 run 欄名規模見 SPEC 之 `eventscan-column-selector` 100）／掃描函式接 API／統一持有時鐘／連續成立只進場一次／報酬表補標準差與最好最差／隨機批參數由觸發批帶入＋抽樣四修／比較端點改比報酬＋Δ 之 bootstrap 區間／前端含硬性橫幅／事件版成本歸零點。單標的先做，多標的併 GAP-4 🔴 **使用者 2026-09-21 追加裁定**：寫 SPEC 時**同步建「同一事實只寫一次」（代號 B）**——凡會被 TODO／測試／白話再抄一次的**值**（時鐘定義、first-of-run、隨機對照抽樣四條、報酬欄主顯示、統計欄、breakeven 公式、失敗原因碼、欄名打錯要報錯、使用者七項裁定…約 40–60 條），於寫到該格的**當下**改為 `fact_keys` 生成區塊，不手打；不是獨立的票、不新建工具、不延後 SPEC。BEFORE 基線已記於 handoffs/run_receipts/20260921-eventscan-b-baseline.json（69 輪、251 條 canonical、doc-sync 55 條＝21.9%、每輪 1.00 條），AFTER 用同一支 docrot2_round_metric 比。🔴 **誠實邊界**：B 只管可列舉的**值**（零件型號表），**不管架構對不對、零件怎麼接、為什麼這樣設計**；同一份文件內前後矛盾與論述寫錯外部無解、本專案亦無解，只能靠兩家對抗審且會漏。🔴 **已知洞**：手寫偵測之 status_scope 只含 HANDOFF.md／docs/GOVERNANCE_EXECUTION_ORDER.md／白話說明/，**docs/ 其餘檔不在內** ⇒ SPEC 內貼了標記的格會同步，但在別段落手打同一個值不會被擋；補洞代價未查。🔴 **2026-09-21 進度**：SPEC v1 已寫並經**五輪**兩家對抗審（R1 21 條／R2 19／R3 14／R4 14／R5 10，**全數採納、零駁回**），fact-key 15 組約 130 列。🔴 **R5 曾揭露前提崩塌並已修復**：舊 run 之特徵欄被 fracdiff 轉換且逐週期 d 不同，故 `EMA_5 > EMA_10` 恆為真、1 段。使用者裁定重跑無轉換 FF run。🔴 **第一次重跑（`654bd63b…`）被 R6 抓到漏了全部 12h 欄，該 run 不可用**；主委補 `timeframes.training` 重發後完成，**reference 定版為 `d9935491…`**（規模見 SPEC 之 `eventscan-column-selector` 100；EMA 欄 corr 全 1.0000、該條件 956 段）⇒ **凍結硬前置已解除**。🔴 **R7 推翻主委之欄位選擇器設計本體**：原「以欄名底線切五層」只涵蓋 0.77%，且切分不可靠（來源欄名含底線、指標可多參數）⇒ 改以 manifest `groups` 為結構來源、全程不解析欄名。🔴 **R8 複查該改動，findings 回升至 14 條，回升全數由 R7 之改動引入**：R7 在 020 把不存在的 `timeframe`／`layer`／`category`／`indicator` 寫成 group 物件之結構化欄位（944 個物件中各出現 0 次），050 之群內不變式被否證，分頁只有 smoke 無完整性契約，選擇器與 PIT 成員資格不一致。週期來源改採 `task_record.json`（兩家提案皆不採，見 K-10 030）。🔴 **R9（findings 數自 R1 起 21→19→14→14→10→7→7→14→10）：R8 之十四條 13 CLOSED、1 STILL-OPEN**；主委在 R8 之兩處「與委員提案相左」之裁定**皆被判成立**（週期來源、fixture 不列凍結前置），但兩者契約不完整已補。R9 最重之一條是**主委在 R8 自己製造的邏輯矛盾**——同一輪採納「樹＝PIT 子集」與「守恆＝manifest 全量聯集」，兩者在 allowlist 非整份 944 時不可能同時為真，已改守恆右端為已核准子集。另**主委自改之 `spec_xref_check.sh` 被抓到兩個 fail-open 洞**（未閉合 marker、fence 內 marker），已改為結構驗證並把回歸測試自 18 增至 22。本輪新增 §P **Phase 0**（三個 Task：fixture 產出、055 之 hash 閘、PIT allowlist 產生器）承載原本無處可掛之回填閘。R9 之 10 條全數採納、零駁回，**SPEC 仍未凍結**，待 R10 複查。 |
| 230 | RM-ICPATH | ICPATH 已完成項兩路支援＋區分＋改正（含盤點） | 未開工 | docs/IC_QUANT_GAP_REGISTRY.md「兩路涵蓋宣告」節 | 排序 3（使用者 2026-09-20 裁定：SEARCH2EVENT 與白話整理完成後，另開新 session 起）；盤點為其規格第一段不另開票，粒度六欄；含邊際 IC 事件型補驗收為其 Task |
| 240 | RM-PLAINDOCS | 白話說明整理（內容跟上最新＋該封存的移 Archived） | 已完成 | 白話說明/README.md | 根目錄 29 → 7 份；22 份被取代者 git mv 入 Archived（內容不改）。四份核心檔各答一個問題並各有互補維護規則（整段覆蓋／做完刪行／只增不改／只寫結論），由 scripts/plain_docs_shape_check.sh 機械強制（章節白名單＋行數上限，掛 pre-commit 硬擋；三種繞法實測 rc=1）。README 990 → 49 行。🔴 未走完整管線：兩輪審查 23 條後主委判定封存機制之設計成本遠高於效益（僅約 4–5 份可封存），停修 SPEC 改為直接交付；SPEC 與兩輪收斂檔保留於 docs/PLAINDOCS_SPEC.md 與 handoffs/reconcile/20260920-plaindocs-x-review-r{1,2}/ |
| 250 | RM-AGENTOPS | AgentOps 病因定義與外部解法調查（治理成效歸因） | 已完成 | docs/AGENTOPS_PROBLEM_DEFINITION.md | 病因目錄＋外部方案調查皆完成並收斂（handoffs/reconcile/20260921-docfix-x-consult-r1/synth.md，10 條 findings 全進群集表、機械檢查 rc=0）。三項結論：①外部無通用語意矛盾 blocking gate（consistency-checker ADR-0015 在散文上 254 候選只認 1 條後關掉；PRISMM-Bench 含 GPT-5 高推理 21 模型最好 53.9%；GitHub Spec Kit /analyze 官方明文 non-blocking）②本 repo 現行兩家對抗審已是該路線最強形態（2026-09-20 兩輪實得 23 條），問題是抓不穩不是抓不到 ③唯一結構性解＝同一事實只寫一次，而 fact_keys 只覆蓋 14／216 份 live 文件＝6.5%、18 個 key 全為治理記帳、量化主線為 0。⇒ 行動落在 RM-EVENTSCAN 的 B（寫 SPEC 時同步建），本票不另開治理票。🔴 **B 之實測成效（EVENTSCAN 五輪）**：doc-sync 型 findings 每輪皆有（R2 4／19、R3 8／14、R5 4／10），**比例未下降**——因為修補落在 fact-key 而散文引用點同時增加；且 R5 抓到 `scripts/fact_keys.json` **自身的手寫描述欄位不受 B 保護**。⇒ B 擋得住「貼了標記的格」，擋不住別處手打同一個值，此洞已具名於 EVENTSCAN SPEC §N 之 RESID-9。🔴 **2026-09-21 使用者質問後重算病因分類**：把原先拆散的「掉項 214／編號 52／狀態漂移 42」加總為**文檔類 308 個拒絕點＝已分類者之 62.7%**（全體 35.7%），為壓倒性第一；主委先前未列為重大缺失之兩個原因（拆散不加總、嚴重度錨點錨在「會不會算出錯的數值」）已寫入 docs/AGENTOPS_PROBLEM_DEFINITION.md。 |
| 260 | RM-FFDSTAR | FFDSTAR 每個 FF run 自帶 d* 收據（可追溯性，中票） | 停手 | docs/FFDSTAR_SPEC.md | 起因＝EVENTSCAN R5 追查時發現共用之 d* 快取檔跨 run 覆寫。🔴 **使用者 2026-09-21 裁定「先確認是真的是 bug 還是特殊原因才這樣定義，不要直接修掉」**⇒ 已先跑唯讀定性輪（handoffs/reconcile/20260921-ffdstar-x-consult-r1/synth.md）：主委原判之四型中，**兩型經委員以本 run 實跑判為設計意圖、一型因主委配對錯誤而不成立**，僅 provenance 一項為真缺陷。該裁定直接擋下一次針對非缺陷的修改。⇒ 本票範圍限縮為單一議題：共用 d* 快取跨 run 覆寫、無 per-column 收據 ⇒ 無法追溯任一 run 當下所用之 d*。SPEC v1 已寫（RISK-HIT: none，不改任何數值只加收據）。🔴 **否決點**：本票會讓每個 run 多產一個檔，CLAUDE.md 明訂輸出大小不得未經核可變更 ⇒ 須實作後量出絕對位元組與佔比、**帶數字請使用者核可才能交付**；否決即整票回退。技術選擇（落點／覆蓋率／既有 7 個共用檔處置）依既有裁定交委員會。下一步＝SPEC 對抗審收斂 → 凍結 → 寫 TODO。 |
| 270 | RM-FFTFMETA | FF-TFMETA：同一 run 之 present_timeframes 兩個值（completeness 鏈型別只接單一週期） | 未開工 | docs/FFDEFECT_DECISION.md | 起因＝EVENTSCAN R7／R8 追查欄位選擇器之週期來源時發現。🔴 定性輪（handoffs/reconcile/20260921-ffdefect-x-consult-r1/synth.md）codex＋composer **獨立同判為真缺陷**，零駁回。根因＝`build_completeness_meta_from_layer_results(..., *, timeframe: str)` 型別上只接單一週期，三個寫入點全傳純量；多週期之正確值只存在於 `multi_tf_generator._present_timeframes()` 並流向 `task_record.json`，從未進 manifest。且 `_apply_failed_timeframe_metadata` 開頭即 `if not failed_timeframes: return` ⇒ **只有在有週期失敗時才寫得完整，全部成功時反而是錯的**。實測：18 個 run 中 4 個多週期 run 之 manifest 皆只宣告主週期。嚴重度＝**latent**（生產端零消費者，命中全在測試與 profile 腳本；EVENTSCAN 會是第一個真實消費者）。修法＝producer 產 ordered unique completeness object 同時餵 manifest 與 task record，`expected_timeframes` 須一併改；canonical 來源＝ordered training config 與 skip／failure 集合，**gid 前綴只作 diagnostic cross-check 不得當權威**（codex 修正，同時修正主委與 composer）。**排序＝先於 FF-NAME**（不改欄名、風險低）。不併入 FFDSTAR。清單檔（manifest）範例已備：docs/manifests/FFTFMETA.json（TODOFMT 樣本；開工時依本票 SPEC 覆核，其中標「待 FF-TFMETA 新增」之九個測試名由本票補上）。 |
| 280 | RM-FFNAME | FF-NAME：衍生層欄名未經來源／指標正規化（3,596 欄／0.859%） | 未開工 | docs/FFDEFECT_DECISION.md | 起因＝使用者 2026-09-21 問「FF 的名稱中不能有 `_`，taker_ratio 應該要是 taker-ratio？」🔴 定性輪 codex＋composer **獨立同判為真缺陷**。命名規則明文於 `talib_wrapper.py:36-37`。根因＝`derived_operators.py:816-831` 之 **metadata-hit 分支取 raw、fallback 分支 `:833-851` 取 normalized**（**不是**主委原判之「L2 一律從 raw 重建」——實測 Distance 272／Momentum 8,700／Abs 870／TsRank 2,610 皆用連字號，只有 Cross 1,194／Ratio 1,194／Lag 16 用底線）。週期標記器**不是**缺陷（本 run 走 CGSA 之 `feature_storage.py:862-873`，對合規名行為正確）。修法＝只改 `derived_operators.py:303-306` 與 pandas 路徑 `:549-552` 兩處造名 f-string，**不得改 `FeatureInfo.source` 或 atomic metadata**（`info.source` 是查 kline 欄名之鍵，kline 實有 `taker_ratio` 無 `taker-ratio`；另 entropy 之 `close_return` 與 `ic_analysis_service.py:2472` 之 `data_source` 外送前端皆依賴 raw）。相容性＝**只對新 run 生效**（依使用者 2026-08-05「面向未來不溯及既往」既有裁定；選項 B／C 皆與之相斥），加 manifest `naming_version` 機械防護。須重簽 `tests/_golden/batch2d/` 三檔（已有 `scripts/freeze_batch2d_baseline.py`）。**排序＝後於 FF-TFMETA**。不併入 FFDSTAR。 |
| 290 | RM-PROCOPT | PROCOPT：SPEC／TODO 流程優化（診斷完成，改法已裁定） | 已完成 | docs/PROCOPT_DECISION.md | 🔴 **2026-09-23 使用者裁定**：散文 TODO 廢止一項已由 RM-TODOFMT 實施；「最終改法」四步不做、CLAUDE.md 不改（第 3 步之實質已含於 TODOFMT）；裁定見 docs/PROCOPT_DECISION.md 檔首。以下為診斷沿革——起因＝使用者 2026-09-22 逐字四問（量化主線 SPEC／TODO 為何這麼多輪且無法收斂／業界模式差異／是模式還是主委／花時間在文件但實作仍有 bug 是否正常）。r1→r2→r3 三輪唯讀診斷，兩家零駁回，**未實施任何流程改動**。結論：①「無法收斂」為假——零實質 finding 多次達到，達不到的是「達到後把票停住」②三機制分解：相位大跳（量化 4 次／治理 0 次）＝模式；同文件小回升（7／9 vs 5／9）＝主委編輯紀律；到零不停＝模式 ③委員抽樣 18 個實作缺陷群集：**SPEC 寫對但沒照做 40%、SPEC 根本沒寫到 50%** ⇒ 直接否定「加 SPEC 輪數可換實作品質」。⇒ 四步改法（0 不變式之可執行 owner＋只審 diff／1 薄切片先行／2 切斷 SPEC→TODO 相位串接／3 驗收條件移到測試檔）。🔴 **否決點**：採納哪幾步由使用者裁決；第 2、3 步須改 `CLAUDE.md`。裁決前 RM-EVENTSCAN 之 R13 停手。2026-09-23：其中「TODO 改為五類落點」一項已由 RM-TODOFMT 實施完成；其餘各步仍待使用者逐條裁決。 |
| 300 | RM-TODOFMT | TODOFMT：散文 TODO 廢止，改五類可執行落點＋對應範本與閘門 | 已完成 | 白話說明/TODO優化結論.md | 2026-09-23 收案。起因＝RM-PROCOPT 之診斷（實作缺陷 40% 為「規格寫對但沒照做」、散文 TODO 為測試檔之低保真草稿）。新票之 TODO＝五類落點 manifest（`docs/manifests/<EPIC>.json`；規格 docs/TODOFMT_SPEC.md，SPEC 審 11 輪後設計定案，L＝`f2146e3d`）。自 W（`26048178`）起生效之機制：寫散文 TODO 即擋（PreToolUse）、manifest 寫入當下機檢（PostToolUse）、派工閘門（新 SPEC 須 manifest 且 spec_path 相等；`--impl-self` 須帶 `--spec`）。實作三批皆經三家審碼閉合；收案聚合器 12 項 rc=0（HEAD `d8107deb`）；全套治理測試 78 紅逐條歸因，皆早於本票或屬偶發／環境（見 HANDOFF 坑）。🔴 硬約束沿用：不得引入分鐘級以上之檢查、不得動 pre-push、mutation 靜態擴覆蓋維持 opt-in。被暫停之票何時復工待使用者決定。 |
| 310 | RM-FKPERF | FKPERF：fact-key 生成器之存檔檢查不隨登記規模變慢 | 進行中 | docs/FKPERF_SPEC.md | 2026-09-23 使用者裁定開票（「這會膨脹很快……這無法接受」）。存檔一次之產出端檢查開 4,322 個外部程式、約 10 秒，隨 fact-key 數線性成長（兩天 17→35）；根因＝bash 3.2 無關聯陣列、逐 key 重查 jq。方向：核心移入單一 Python 程序、行為逐位元組不變、以外部程序數與開檔數之規模不變性驗收並寫實測秒數。SPEC v3（r1 十三條、r2 兩條已收斂；使用者裁定比例型時間門檻：規模 10 倍最多慢 20 倍）；SPEC v5（r3 收斂）、r4 三家 proceed；使用者 2026-09-23 白話審閱回「ok」⇒ SPEC 定案（v6 僅更正 NaN 描述）。施工清單（五類落點 manifest）已寫，r5 三家 13 條全採納已修；程式尚未改。下一步：r6 閉合複查後進實作。 |
<!-- END GENERATED: roadmap-status -->

### 治理票

票狀態唯一來源＝`docs/GOV_TICKET_SOT.md` 生成區塊（VERDICTGATE＝`B-62`、DOCROT2＝`B-63`、委員同輪重派＝`B-64`）。DOCROT2 之批次：

<!-- BEGIN GENERATED: docrot2-batch-status -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 010 | D2A | 已完成 | docs/DOCROT2_TODO.md §B | — |
| 020 | D2B | 已完成 | docs/DOCROT2_TODO.md §B | — |
| 030 | D2C | 已完成 | docs/DOCROT2_TODO.md §B | — |
| 040 | D2D | 已完成 | docs/DOCROT2_TODO.md §B | — |
<!-- END GENERATED: docrot2-batch-status -->

### SPLITUNIFY 事件切分與 IC 時間切分統一

批次與 Task 狀態見 `docs/SPLITUNIFY_TODO.md` §B／§C-9 生成區塊；殘留：

<!-- BEGIN GENERATED: splitunify-residual-status -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 010 | R-1 | 已完成 | docs/SPLITUNIFY_TODO.md §E | — |
| 020 | R-2 | 已完成 | docs/SPLITUNIFY_TODO.md §E | — |
| 030 | R-3 | 未開工 | docs/SPLITUNIFY_TODO.md §E | UAT 排在最後一次做（使用者裁定） |
| 040 | R-4 | 未開工 | docs/SPLITUNIFY_TODO.md §E | 另開接線票；本票只保證 assignments 語意不變 |
| 050 | R-5 | 已完成 | docs/SPLITUNIFY_SPEC.md Phase 10 | — |
| 060 | SU-RESID-2 | 已完成 | docs/SPLITUNIFY_TODO.md §E | — |
| 070 | SU-RESID-V8-ATTEST | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：專案導入 commit 簽章或受保護分支 |
| 080 | SU-RESID-PAUSED-NO-RESULT | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：audit 出現同輪同家 failed 且無產出之結果列 |
| 090 | SU-RESID-COMMITTEE-MODEL-EVIDENCE | 未開工 | docs/SPLITUNIFY_TODO.md §E | 實測兩 CLI 非互動輸出之型號與 effort 欄位 |
| 100 | SU-RESID-9A-UI | 未開工 | docs/SPLITUNIFY_SPEC.md R5-C5 | 隨 R-5 實作批交付（規格 R5-C5） |
| 110 | SU-RESID-1 | 部分完成 | docs/SPLITUNIFY_TODO.md §E | 待觸發：出現可由收斂檔附錄證明之處置掛錯意見事故 |
| 120 | SU-RESID-3 | 已完成 | docs/SPLITUNIFY_TODO.md §E | — |
| 130 | SU-RESID-4 | 未開工 | docs/SPLITUNIFY_SPEC.md §N | 待觸發：下一次動 IC 切分契約 |
| 140 | SU-RESID-5 | 未開工 | docs/SPLITUNIFY_SPEC.md §N | 待觸發：下一次動 SplitPlan 欄位契約 |
| 150 | SU-RESID-C5-TARGETS | 未開工 | docs/SPLITUNIFY_TODO.md Task 9.3 | 待觸發：Task 9.3 驗收段兩條觸發條件 |
<!-- END GENERATED: splitunify-residual-status -->

🔴 **優先序（2026-08-14 使用者明示「現在開始就是要回去做量化主線」）**：
量化主線 **優先於** 治理。此句覆蓋兩條舊裁決——P0 之「完成後才回 IC」（2026-07-05）、
「治理優先於產品線」（2026-08-04）。

---

## 量化主線（IC 分析）

**已完成**：`ic-la0` → `ic-la1` → `ic-la2`（前瞻整治三站）→ `ic-1c`（Net IC 量綱）→
`ic-1cfr`（canonical 因子報酬序列 F0–F5.2）→ `ic-1d`（factor attribution 六批 B0–B5）→
`ic-1e+1b`（HAC 顯著性＋FDR 接線＋xsec p 值；**本行 2026-08-17 補記，原漏列**）。
🔴 `ic-1d` **B4／B5 亦已完工**（2026-08-14 逐項查證：7 支 mutation 探針＋cache/force 兩測、
`FactorExposureRadar.test.tsx`、Radar 契約地雷殘留 0、ExportButtons 舊判斷殘留 0、前端 triage 檔皆在）。

**✔ IC 全棧健檢 epic 已收工（2026-08-17）**——四步全走完（偵察四方 reconcile→SPEC/TODO 凍結
→六批實作 3×P0 修復＋契約 SoT＋wiring 閘門→三家 code review 全 CLOSED 三家戳記）。
原定四步（存檔備查）：

1. **discovery sweep**：Claude＋三委員平行，產「後端產出／前端消費／wiring／空態」四欄表
2. **quant gap analysis**：現況 vs 業界；複審 4 個 deferred（funnel／capacity／regime IC／walk-forward+CPCV）
3. **建 typed 契約 SoT ＋ wiring 閘門**（順手修 #1 幽靈＝原 `1f`）
4. 跑閘門確認閉合，之後自動守

設計原則（使用者洞察）：①audit 先天不完整 ⇒ time-box ②**手動快照會腐爛 ⇒ 把發現做成機器閘門**
③分層防禦。底稿＝`handoffs/20260624-ic-map-WHOLEMAP.md`（**6/24 版，已隔月過時，須逐條複核**）。

✅ **底稿複核已完成**（2026-08-17，四方獨立＋reconcile）：28 條逐條標定＝已修/部分修/變形 ≥15、
未修 7、未查具名 6；三個 P0 仍活（分位圖巢狀 schema 空圖／xsec 硬編空殼／事件 silent fallback）。
白話版＝`白話說明/IC健檢偵察結果.md`；技術收斂＝`handoffs/reconcile/20260817-ichc-x-consult-r1/`（本地）。

🔴 **本節曾整段消失十天**：`aae04295`（2026-08-05）把 ROADMAP 由 393 → 111 行、「敘事移出 Archived」，
連同量化主線的下一步一起砍掉，直到 2026-08-14 使用者追問才發現。完整敘事仍在
`docs/Archived/ROADMAP_P16_NARRATIVE_20260805.md:139-157`。

### 後續兩票（皆 Phase 4，不插隊）

- **票 A — 策略 timing-overlap／clone score 診斷**：回答「ML 是否只在做簡單因子規則」。
  **開票前置＝先修 equity curve 契約**（**已於 2026-08-18 PA-CUMSUM 完成**：`EquityCurveData` 改單利／複利四序列＋四鍵終值、多標的逐 timestamp 等權組合、缺值 fail-closed）；
  殘餘：`prediction_analyzer.calculate_strategy_equity_curve` 只有 long/flat 無做空、
  `api/routes/pattern_analysis.py` 之 `actual_return.fillna(0)` 仍在（缺報酬視為 0，`predicted_proba` 缺值已改 4xx）。
- **票 B — 真·多標的橫截面 attribution**：**條件觸發，只有宇宙變多標的才成立**。
  前置＝CS factor-return 管線（`factor_return_analyzer.py:272-287` 現僅收單一 `future_returns: pd.Series`）
  ＋持倉權重 canonical 定義＋`analyze_cross_sectional` 與 deep 棧整合。
- **根因備忘（防未來重撞）**：單標的下 `ls_returnᵢ=positionᵢ⊙r`、組合報酬＝`position_p⊙r`，
  共用同一 `r` ⇒ OLS 只識別 **position 重疊度**非風險曝險。β 可誠實命名 timing-overlap，
  **禁冒充 Barra attribution**。

### 兩筆 follow-up（2026-07-22 三方 IN-SCOPE-PASS 後登記，防丟）

- **FU-1 exposure 家族 `fillna` fail-closed 化**：`factor_exposure_analyzer.py:111-307` 三函式壞值靜默
  `fillna(0.0)`。嚴重度中（預設 `enabled=False`、僅餵 Radar 診斷非交易決策）。修法＝比照 `1d` B2。
- **FU-2 cache close all-NaN carrier index 對齊**：kline `RangeIndex` vs features `DatetimeIndex` 對不齊。
  **是票 A／票 B 的硬前置**（全 NaN carrier 上無法接真歸因）。
  🔴 **2026-09-19 狀態更正（使用者質疑「這我印象有做完了」後以碼複查，本列原標「未開工」為錯）**：
  **已落地的半**＝carrier 對齊（`ic_filter_orchestrator.py:4257-4264`，`reindex(features_df.index)`，
  隨 LA-2 B3 交付）＋缺 carrier 時 fail-closed（`:3031`，禁 silent fallback 到 `label_series`）。
  **未關閉的半**＝**對齊後整欄 NaN 不擋**：`label_series` 有全 NaN 守衛（`:3366`），`close_series` **沒有**；
  現行測試逐字載明此行為（`tests/momentum/Analysis/test_ic1d_baseline.py:228`「production 僅拒 None，
  不拒 reindex 後 NaN」）⇒ 索引型別對不上時仍會安靜產出全 NaN carrier，正是本 FU 點名之症狀。
  **落地時之驗收錨點**：`close_series` 全 NaN ⇒ fail-closed，且 mutation（把 carrier 灌成全 NaN）須轉紅。

### 🔴 票 MEM-RSS：Feature Factory 之記憶體閘以 RSS 為判準，在 macOS 上可能**漏擋**（2026-08-27 登記；**不插隊**，使用者裁定先做完 B9／IC-Analysis）

**觸發**：GAP-3 B9 之 Task 6.2 實跑量測時，同一時刻實測 **RSS 72MB vs Physical footprint 5.7GB（差 79 倍）**。
機制：macOS 之 memory compression 會把不常碰的頁**就地壓縮**，壓縮後**不再算 resident**
⇒ 記憶體壓力愈大、RSS 反而愈小，**方向是反的**。

**受影響之處（讀碼所得，逐條可查）**：
- `momentum/FeatureEngineering/feature_factory.py:2215`
  `if float(ic_memory.peak_rss_gb) > peak_budget_gb: raise MemoryError(...)`
  ——**這是會真的擋下執行的閘**，判準為 RSS ⇒ 真正快爆時 `peak_rss_gb` 反而變小、閘門讓它過去。
- `feature_factory.py::_check_ic_memory_budget_after_raw_persist`
  以 `rss_before - rss_after` 當「gc 釋放了多少」⇒ 頁面只是被**壓縮**時也會得出好看的正數。
- `memmap_utils.py:213` 之 RSS 僅供 log，不做決策 ⇒ 不受影響（但同樣會誤導讀 log 的人）。

🔴 **誠實邊界**：以上為**讀碼＋機制推論**，**未對 Feature Factory 實跑對照量測**。
要斷定「該閘實際漏擋過」，須拿真實大 run 同時量 RSS 與 footprint 對照。
另：Linux 無預設記憶體壓縮，影響顯著較小（RSS 僅少了 swap 部分）——**本票之嚴重度綁 macOS**。

**修法（順序不得顛倒）**：①先做對照量測，**證明現行閘會漏擋**；②再把判準換成
macOS＝`sample`／`footprint` 之 Physical footprint、Linux＝`smaps_rollup` 或 cgroup 統計；
③保留 `_available_ram_gb()`（判系統可用 RAM，不受本問題影響）。
🔴 **先證明再改**——那是一道會 `raise` 的閘，憑推論就動它可能把正常的 run 擋掉。

**可複用**：`scripts/measure_ic_footprint.sh`（B9 產出，已含單一 pid 判定與安全閥）。

---

## 測試策略（2026-08-14 使用者定：「邊走邊建立」）

**建測試時的優先序**（前三類的紅綠，使用者可在**不讀程式碼**的前提下採信；第四類不可）：

1. **性質檢驗**（`t` 不得依賴 `t+1`、跨 symbol 換料另一標的輸出不變、合併前後守恆）
   ——**不需要凍結期望值，所以不會過期**
2. **真實 kline**（`data_cache/feature_klines/kline_cache.h5`；禁合成 fixture，既有鐵律）
3. **與第三方實作對照**（`scipy`／`statsmodels` 等）——量尺不是本專案產的
4. ⚠️ **凍結 golden 比對**：能不用就不用；非用不可時**改行為的當下必須重凍**

**病根（使用者 2026-08-14 指出，邏輯上無反駁餘地）**：基準與測試**兩側都是 Claude 產的**，
拿一個量另一個是循環論證 ⇒ 使用者無法判斷紅綠真假。**只有非本專案產生的量尺逃得出這個圈。**

**既有 32 個失效基準／40 個疑似孤兒＝不大清**（`scripts/golden_staleness_check.sh` 的歸屬判定
**已實測有兩個 bug**——檔名碰撞與動態組路徑，其輸出**不得用於刪檔**，詳見該檔頭）。
處置＝**碰到才處理**：動到某模組而其 golden 炸了，當場決定重凍或作廢。

---

## ✅ 已完成

歷史條目移至 `docs/ROADMAP_DETAIL.md`（**搬走不等於作廢**；要作廢請明寫）。
