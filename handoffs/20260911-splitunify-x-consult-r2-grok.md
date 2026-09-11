# SPLITUNIFY 收尾偵察 consult R1 / grok

brief-kind=consult；家族=grok；findings-round=R1；task-id=`20260911-SPLITUNIFY-X-CONSULT-R2`
read-only：禁改碼、禁動 tracked、禁 commit／push、禁跑 `tests/governance` 全套。
標的＝`docs/SPLITUNIFY_SPEC.md` §N／§C-0／§C-1／§G ＋ `docs/SPLITUNIFY_TODO.md` §E ＋投影／契約碼；主委初判 `handoffs/20260912-SPLITUNIFY-CLOSEOUT-RECON-claude.md` 僅作對照，本檔獨立重判。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| # | 陳述 | 判定 | 本輪覆核 |
|---|---|---|---|
| F1 | `_base_universe_hash(index, symbol)` 輸入含 symbol ⇒ 多標的下每 symbol 一份 hash | **fact-verified** | 讀 `ic_filter_orchestrator.py:517-530`；實跑同 index 異 symbol ⇒ hash 不等（`BTCUSDT`/`ETHUSDT` 前綴 `9b4b75dc…`／`eebbe958…`） |
| F2 | `split_per_symbol` 對全部 symbol 灌同一個字面 `base_universe_hash` | **fact-verified** | 實跑 `base_universe_hash='LITERAL_SHARED'` ⇒ AAA／BBB 計畫皆為該字面 |
| F3 | 同源對證只比 plan 首尾兩列 | **fact-verified** | 讀 `split_projection.py:473-484` |
| F4 | `EventAnalyzeRequest` 之 `test_fraction`／`embargo_ms`／`tier_min_test_events` 現況不被使用 | **fact-verified** | `case_import_service.py:1606-1609` 註解＋恆呼叫 `run_event_study_only_with_params` |
| F5 | 前端 `events/.../analyze` 唯一非測試呼叫＝`api.ts:1123` | **fact-verified** | `grep`：唯 `api.ts` 定義＋`EventTablesPanel.tsx:303` 呼叫；無第二 fetch |
| F6 | 測試面 derive 55／disclosure 22／golden 9／contract 8 | **fact-verified（disclosure 路徑更正）** | `test_splitunify_derive.py` 55；`tests/api/test_splitunify_disclosure.py` **22**；golden 9；contract 8 |
| A1 | 主委「唯一性已有定義、問題只在傳遞」可直接當 R-1 設計前提 | **assumed → 本輪部分否證** | 見必答 1／`GROK-R1-P2-01`：`ICSplitAdapter` 對整框算**一個** joint hash 並打在每個 symbol 的 plan 上＝合法共用 |
| A2 | R-5 收窄 `features_ref` 後「前端不改」⇒ 無無法解釋之 capability 狀態 | **assumed（UI 路徑成立；語意易被讀過頭）** | 見必答 2／`GROK-R1-P2-03` |
| A3 | 多 TF 複合鍵不影響 `ic_feed.py:109` 消費端 | **assumed（只讀碼）** | `ic_feed` 已 `per_tf[timeframe==tf].set_index("event_id")`；未實跑多 TF fixture |
| A4 | D1 改條件式＝不推翻設計 ⇒ 可走凍結程序 **D** | **assumed → 本輪挑戰** | 見必答 5／`GROK-R1-P1-01`：與已戳記「恆走」字面互斥時爭議預設 **R** |

---

## 必答（立場＋碼證；正反各一句）

### 1. R-1 研究問題是否已被回答？

**立場：研究問題可回答，但主委「唯一性已定義」表述不完整；真正要解的是投影端多對 plan 語意，不是發明新的 hash 公式。**

①**支持主委「orchestrator 函式含 symbol」的碼證**：`_base_universe_hash` 把 `_normalize_symbol_value(symbol)` 寫進 DataFrame 再 sha256（`ic_filter_orchestrator.py:517-530`）。本輪實跑同 index、異 symbol ⇒ hash 不同。`split_per_symbol(..., base_universe_hash=literal)` 確把**同一字面**打進每個 symbol 的 train/test（`contracts.py:635,671,683`；實跑 `LITERAL_SHARED`）。投影端現況：多 symbol 事件批在 `symbols != plan_symbols` 時 fail-closed（`split_projection.py:424-429`）。⇒ 缺的是「接受 `Mapping[symbol,(train,test)]`＋逐 symbol 投影後縱向合併」，不是切分本體（`split_per_symbol` 已逐 symbol 產 plan）。

②**反面**：存在**合法**兩 symbol共用同一 hash 之情形——`ICSplitAdapter._base_universe_hash(frame, ...)` 對**整份多標的 frame**算一次（`ic_split_adapter.py:55-56,118,189-199`），再把該 hash 打進每個 symbol 的 plan pair（`:97`／`:158`）。本輪實跑：adapter joint `36afad51…`，orchestrator 對 AAA／BBB 分開算則為 `077fe330…`／`6fa82745…` 且互異。另：`_normalize_symbol_value` 去空白後同字面（`'BTCUSDT '`→`'BTCUSDT'`）會同 hash；**大小寫不折叠**（`btcusdt`≠`BTCUSDT`）。⇒ R-1 不得把「每 symbol 的 `base_universe_hash` 字面必須互異」寫成不變式，否則會拒收現行 IC adapter 多標的計畫。

### 2. R-5 收窄案能否避開「請求模型／前端／契約／UAT 全動」？

**立場：能避開「全動」；請求模型加選填 `features_ref`＋後端分支即可讓 None 路徑維持現狀。但不能解讀成「前端不改也能行使 OOS」。**

①**碼證**：`EventAnalyzeRequest` 現有未使用切分欄（`event_import_models.py:301-303`）；分析路徑恆 `run_event_study_only_with_params`（`case_import_service.py:1609`）；capability 固定 `split=unavailable`（`:1620-1624`）。前端唯一 analyze fetch（`api.ts:1123`）＋`EventTablesPanel.tsx:303` 不傳 universe。`splitCapabilityView` 對 `canonical_feature_universe_unavailable` 已有專文案（`splitCapability.ts:65-69`）。None ⇒ 文案與現況一致，UAT／畫面不必為 None 路徑改契約字面。

②**反面**：前端不改時，UI **永遠**走 None ⇒ 永遠 `hasSplit=false`；若文件／API 暗示「R-5 後事件掃描可得 OOS」，使用者在 UI 上看不到切分段、只能 curl 帶 `features_ref` 才看得到——這不是「無法解釋的 capability 字面」（字面仍對），而是**能力與入口不一致**。若實作端另做「伺服器自動找 FF run」而請求仍無 `features_ref`，則 UI 會突然 `hasSplit=true` 且無選 run 的 UI ⇒ 那時才變成無法解釋。收窄案必須釘死：**禁止 auto-discover；唯顯式 `features_ref` 才走 OOS。**

### 3. SU-RESID-3：加 `row_time_fingerprint` vs 永久誠實邊界

**立場：選「producer 側加指紋（接受 IC／golden digest 位移）」——若本輪收尾要做 R-5；若 R-5 再延後，可暫留首尾＋誠實邊界。**

①**選擇與碼證**：現行只比首尾（`split_projection.py:473-484`）。本輪構造同長度、同端點、中間間距不同之兩 index ⇒ 端點相等（首尾閘會放行）。R-5 允許呼叫端塞任意 `features_ref` 時，這是具體錯分面，不是純理論。單位歧異仍在：`_coerce_timestamp_array` 對純數字 `unit="s"`（`contracts.py:425-427`），事件側 ms——改 hash 輸入會動 IC golden（SPEC／TODO 已自承）。⇒ 真解＝plan 隨身帶**毫秒語意**之逐列時刻指紋（或等價），投影端比對；動契約／digest 是付費，不是可省的。

②**反面（未選方案的最強理由）**：維持首尾＋永久誠實邊界，避免動已戳記 IC golden／契約封閉面，且固定頻率宇宙另有 `_validate_expected_frequency`；中間間距攻擊需非均勻網格，生產路徑較少見。代價＝R-5 上線後「錯 run、同端點」仍可能靜默錯分。

### 4. SU-RESID-2 複合鍵會否讓既有 5 組 golden 全部重算？

**立場：不必「五組全部重算」；但 `g1`／`g3b`／`g5_answer_window` 若改成多 TF 成員結構則必須擴維或加平行 golden，否則多 TF 路徑假綠。**

①**碼證（讀檔）**：`splitunify_golden.json` 頂鍵＝`g1_membership`／`g3b_oracle`／`g4_per_symbol_n`／`g5_row_fingerprint_*`／`g5_answer_window`／`purge_reasons`。`g1`／`g3b`／`g5_answer_window` 皆為 **event_id 字串清單**（無 TF 維）。`g4` 是 per-symbol 計數；`g5_row_fingerprint_*` 是 feature 列指紋（position／首尾 ms／sha256），與 event 複合鍵無直接耦合。`build_event_keys` 現況：selected TF 下 `event_id` 重複 ⇒ raise（`split_projection.py:284-288`）。單 TF fixture 下改實作若仍只餵一 TF，既有集合值可保留；**結構**若改成 `(event_id,timeframe)` 則比對器與 freeze 腳本要改。

②**反面**：若不重算／不擴多 TF fixture，測試面繼續只跑「每事件一列」——複合鍵路徑從未被打紅，多 TF 下同一 `event_id` 兩列可能被 `event_id` 唯一性閘誤殺或被集合相等吃掉重複 ⇒ **假綠**（舊 golden 仍綠，新洞不紅）。

### 5. D1 改條件式是否推翻設計？走 R 還是 D？

**立場：表面字「恆走」與「條件式」互斥 ⇒ 不得逕標「純 D、無爭議」；程序上爭議預設 R。若嚴格限縮為「落地 §N 已預留之 R-5 對照路徑、不刪 Task 3.3、不碰 C-0 決議③原則句」，才可主張 D 延伸。**

①**是否推翻／走哪條**：C-0 決議③原文是「**沒有** canonical feature universe … 只能明示 event-study-only」（`SPLITUNIFY_SPEC.md` C-0），原則本就是條件式。R2 之 D1／§N R-5 把**本票落點**寫成事件掃描端**恆走**該分支，因當時不新增供給路徑。主委把「恆」改成「拿不到才走」＝啟用 §N 已寫的「新增對照路徑、不得刪 Task 3.3」。凍結程序（v1 §1／v2 §2.1）：與原檔**互斥**⇒不是 D；**爭議一律預設 R**。⇒ 本家裁：**至少按爭議預設走 R 審該觸及節**；或寫 D 延伸時觸及面宣告必須能證明只覆寫「本票落點／R2 D1」句、且與決議③原則句**不互斥**——做不到就升 R。

②**反面（若判純 D）**：如何說明「恆」不被改變？只能主張「恆」＝「在 R-5 完成前／無 `features_ref` 時恆走」，而 §N R-5 已預告對照路徑——即「恆」是**範圍凍結**不是產品永態。此讀法須在延伸檔／R 重開稿裡寫死，不能只靠主委偵察散文。

### 6. 批次切法與依賴

**立場：主委「R-5 依賴 R-1 與 SU-RESID-3」正確；`b8=R-1、b9=SU-RESID-2＋3、b10=R-5＋D1` 可接受但非最省。**

①**依賴**：R-5 把外部 `features_ref` 接進投影 ⇒ 必須先有 per-symbol 投影（R-1）與比首尾更強的同源閘（SU-RESID-3），否則錯 run／錯 symbol 邊界會以 OOS 姿態出門。D1 條件化文件面應與 R-5 **同批或緊隨**（同一驗收：「有 ref ⇒ OOS；無 ref ⇒ 仍 Task 3.3」）。SU-RESID-2（多 TF 鍵）**不**在 R-5 資料依賴鏈上。

②**反面（更省輪次、不犧牲 fail-closed）**：`b8=R-1＋SU-RESID-3`（投影完整性一包）、`b9=R-5＋D1 文件條件化`、`b10=SU-RESID-2`（或並入 b9 若審容量允許）。把 SU-RESID-2 從 R-5 前置拿開，少一次「不必要的串行」，fail-closed 不減。

### 7. 主委漏掉的殘留／風險

**有，兩條（非第三套切分本體）：**

1. **`ICSplitAdapter` joint-hash 與 orchestrator per-symbol hash 雙源**（見必答 1）——R-1 設計文件若只引用 orchestrator 函式會誤導實作。  
2. **`lgb_cv_universe`／`xgb_cv_universe` 假 hash**（`lightgbm_analyzer.py:377`、`xgboost_analyzer.py:1162`）用於 OOF receipt，**本輪未看到**流入 `derive_event_split_from_plans`（api 無該呼叫）。風險＝日後有人把 CV fold plan 當事件投影輸入；屬 brief「我沒查」面，建議在 R-1／R-5 驗收加「投影入口拒絕非 positional／拒絕對白名單外 hash 前綴」或至少文件點名。  

另已查：`dedupe.py` 以 `(label_start_ms, event_id)` 排 event_level（`:46`），複合鍵衝突面在 `build_event_keys`／投影唯一性，不在 dedupe 重排本身——與主委「未查」方向一致，但本輪判斷**不是**獨立新殘留 ID。

查過、確認無須新開殘留的面：reason 封閉集合、前端 analyze 呼叫點數量、切分本體 `split_per_symbol` 多 symbol 支援。

---

## Findings

## GROK-R1-P1-01

**斷言**: 將 D1「事件掃描端恆走 event-study-only」改寫成「有 universe／`features_ref` 才走 OOS、否則才 event-study-only」，與已戳記 SPEC 之「恆走」落點句字面互斥；主委偵察若逕標「不推翻、純改寫」而未走凍結程序之 R（或嚴格限縮觸及面的 D），後續 b10 文件修訂會在戳記／互斥檢查被打回或留下雙源措辭。

**碼證**: SPEC C-0 決議③原則句＝「沒有 canonical feature universe … 只能明示 event-study-only」；同節 R2 D1／§N R-5＝本票事件掃描端**恆走**＋日後 R-5「不得刪 Task 3.3、只能新增對照路徑」（`docs/SPLITUNIFY_SPEC.md` C-0／§N；`docs/SPLITUNIFY_TODO.md` §E R-5）。凍結程序：D＝不推翻；與原檔互斥⇒非 D；爭議預設 R（`docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` §1；v2 §2.1 同語意）。主委偵察 §3 寫「D1 不推翻，改寫為條件式」未處理「恆」字互斥。RECHECK：寫出擬議條文後對讀 C-0 決議③／R2 D1／§N R-5 三句，標「覆寫／新增／不觸」；若任一「恆走」句被改成相反義務且未升 R ⇒ 本 finding 仍開。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[BLOCKING] 信心度=High。不改會在 b10 具體失敗：延伸檔／重開稿無法通過「與原檔不互斥」對讀，或文件仍寫「恆走」而碼已條件化 ⇒ 下一批 agent 依文件實作又砍掉 OOS 路徑。修法：b10 開工前 brief 明示 **R** 或 **D＋觸及面只覆寫本票落點句並保留決議③原則**；爭議未消則 R。

## GROK-R1-P2-01

**斷言**: 主委「`_base_universe_hash` 含 symbol ⇒ 唯一性已有定義」忽略生產路徑 `ICSplitAdapter` 對多標的整框使用**單一 joint hash**並打在每個 symbol 的 plan 上——兩 symbol 合法共用同一 hash 字面；R-1 若把「跨 symbol hash 必互異」寫成閘，會拒收現行 IC 多標的計畫。

**碼證**: `ICSplitAdapter.split_cpcv`／`split_wf` 先 `base_hash = self._base_universe_hash(frame, ...)` 再逐 symbol `_build_plan_pair(..., base_universe_hash=base_hash)`（`ic_split_adapter.py:55-97,118,189-199`）。對照 orchestrator `_base_universe_hash(index, symbol)`（`ic_filter_orchestrator.py:517-530`）同 index 異 symbol 實跑 hash 不同。Adapter 實跑 joint≠per-symbol。RECHECK：多標的 frame 經 `ICSplitAdapter` 產兩對 plan，斷言兩 symbol 之 `base_universe_hash` 字面相等且 `symbol` 欄不同。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#c2dd93482826

[MAJOR] 信心度=High。失敗模式：b8 實作按主委字面加「跨 symbol hash 碰撞 ⇒ fail-closed」⇒ IC 多標的接線紅。修法：R-1 不變式改為「同一 symbol 之 train/test hash 一致；跨 symbol 允許共享 joint-universe hash；事件 symbol 必須匹配 plan.symbol；逐 symbol 做同源對證」。

## GROK-R1-P2-02

**斷言**: 主委批次 `b9=SU-RESID-2＋SU-RESID-3` 把多 TF 複合鍵與逐列指紋綁成 R-5 前置，但 SU-RESID-2 不在 R-5 的 fail-closed 依賴鏈上；綁在一起會無謂串長收尾，或讓 R-5 被無關的 golden／TF 結構爭議擋住。

**碼證**: R-5 風險＝錯 `features_ref`／錯 symbol 邊界（依賴 R-1 逐 symbol 投影＋SU-RESID-3 指紋）。SU-RESID-2 原文＝selected TF 下 event_id 多列 raise（`split_projection.py:270-288`；SPEC §N／TODO §E）。`ic_feed.py:109` 已按 timeframe 過濾。RECHECK：畫依賴圖——刪掉 SU-RESID-2 後 R-5 錯-run 攻擊是否仍被 R-1＋SU-RESID-3 擋住（應為是）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#e44da6448b01

[MAJOR] 信心度=Medium。失敗模式：b9 卡在 golden TF 維度審，b10 R-5 整批空轉。修法：`b8=R-1（±SU-RESID-3）`→`b9=R-5＋D1 程序`→`b10=SU-RESID-2`；或 SU-RESID-3 進 b8、SU-RESID-2 獨立殿後。

## GROK-R1-P2-03

**斷言**: 「`features_ref` 選填、前端不改」只能保證 UI 繼續走 event-study-only 且 capability 文案可解釋；不能等同「避開跨棧後 UI 也能用 OOS」。若收尾驗收以「前端零 diff」為成功條件，會把 R-5 做成僅 API 暗門。

**碼證**: `analyzeEventImport` body 型別無 features 欄（`api.ts:1119-1127`）；`EventTablesPanel` 呼叫不傳（`:303`）；`splitCapabilityView` 在 `hasSplit=true` 時面板顯示 train／test／purge（`EventTablesPanel.tsx:360-361`）。RECHECK：前端零改＋僅 API 帶 `features_ref` 跑通 ≠ 產品驗收通過；若要產品面 OOS，須另開前端選 run 或明示「本殘留只交付 API 能力」。

**來源摘要**: frontend/src/lib/api.ts#4a54c9918781

[MAJOR] 信心度=High。失敗模式：b10 標 done、UI 仍永顯示「取不到特徵宇宙」，使用者以為 R-5 沒做。修法：R-5 scope 一句寫死——(A) API-only＋文件誠實邊界，或 (B) 最小前端 `features_ref` 入口；禁止用「前端不改」同時暗示產品 OOS 已通。

---

## 對主委初判的總表（非 finding，供 synth）

| 題 | 主委 | 本家 |
|---|---|---|
| R-1 | 唯一性已定義，洞在傳遞 | **同意洞在投影多對 plan**；補正：adapter joint hash＝合法共用（P2-01） |
| R-5 收窄 | 前端不改可避開全動 | **同意避開全動**；補正：UI 不能行使 OOS（P2-03） |
| SU-RESID-3 | 傾向加指紋／請委員裁 | **選加指紋（若做 R-5）**；否則誠實邊界 |
| SU-RESID-2 golden | 怕五組全重算 | **不必五組全重算**；g1／g3b／answer_window 要擴維否則多 TF 假綠 |
| D1 程序 | 不推翻，條件化 | **爭議預設 R**；僅限縮覆寫本票落點句才可能 D（P1-01） |
| 批次 | b8 R-1／b9 2+3／b10 R-5+D1 | **R-5←R-1+SU-RESID-3 正確**；SU-RESID-2 應殿後（P2-02） |

---

## 11 類必查（consult 對 SPEC／TODO 殘留面；無則「無」）

1. 矛盾／互斥：見 P1-01（「恆走」vs 條件化）  
2. 漏項：R-5 前端／API-only 未在主委偵察釘死（P2-03）  
3. 不可測驗收：無新增空殼驗收主張  
4. 可疑 quant：無（本輪不改數值定義）  
5. 過度工程：R-5 收窄方向同意；反對為 R-5 重造 `features_run_id`  
6. OOM／並行：無  
7. Cache：無  
8. API／相容：`features_ref` None 預設同意  
9. 測試：SU-RESID-2 缺多 TF 紅燈 ⇒ 假綠風險（必答 4）  
10. Agent 可執行性：D1 程序類別未寫死 ⇒ P1-01  
11. 必要性／短命工：無（殘留皆為終態缺口，非將刪之過渡碼）

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P1-01
CLOSED:
STATUS: DONE

<!-- 主委正規化（2026-09-12）：①原檔 findings 用 `### ` 三級標題，而 completeness 抽取器與 verdict_parse 之 `BLOCKED-BY` ID 對證皆要求 `## ` 二級（brief 已明寫）⇒ 三度受阻（抽 0 條／清債 sha／註冊拒收）。②僅改 heading 層級，內容一字未動。③交件當下 sha=3242c601ddddcae5（audit committee_family_result 記錄），本次正規化後之 sha 以 register-output 寫入之 committee_output.output_sha256 為權威。 -->
