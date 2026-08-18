# GAP-2 TODO adversarial — GROK R7（TODO DRAFT R1 vs SPEC R7 FROZEN）

family: grok｜task-id: 20260818-GAP2-X-REVIEW-R7｜brief: `handoffs/20260818-gap2-todoadv-BRIEF.md`
標的：`docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R1）｜義務來源：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN；不改）

## Verdict：需修補

不可整體 Frozen 進全五批實作。B1 純函式／契約 SoT 多數可執行，但至少 **3 條 P0**（B5 toggle 不可見／具名 preset 靜默丟 enabled；B4 fallback `fit_scope` 偵測未釘死）會讓執行端「自行發明」或驗收假綠。修補後再 Frozen；修補面以 TODO 為主，`persist_suppressed` 建議延伸檔 A1。

---

## GROK-R7-P0-01

**斷言**: Task 5.1 修改檔案清單未含 `FeatureTierPanel.tsx`，而 IC 面板 checkbox 來源是該檔硬編碼 `TOGGLES`（非 store 自動列舉），執行端照清單改 store／types 後 toggle 在 UI 仍不可見。

**碼證**: TODO Task 5.1「修改檔案：上列四檔」＝`types.ts`／`icAnalysisStore.ts`／`MarginalICTable.tsx`／test，無 `FeatureTierPanel.tsx`。VERIFY: `sed -n '20,51p;97p' frontend/src/components/ic-analysis/FeatureTierPanel.tsx` → `const TOGGLES: Array<...>` 24 鍵硬編碼；`已啟用 {enabledCount}/24`。RECHECK: grep Task 5.1 修改檔案是否列入 `FeatureTierPanel.tsx` 且要求 `TOGGLES` 加 `marginal_ic`＋計數改 `/25` 或 `TOGGLES.length`。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。失敗：使用者白話閘「加 toggle」交付物表面完成（wiring R1a/R1b 仍可綠），UI 無開關。修法：Task 5.1 白名單加 `frontend/src/components/ic-analysis/FeatureTierPanel.tsx`；實作要點寫明 `TOGGLES` 加一列（label「邊際 IC／多因子組合」）並改計數。

---

## GROK-R7-P0-02

**斷言**: 具名 preset 路徑下 `getEffectiveConfig` 只送出 `fdr_correction`，Task 5.1 僅把 `marginal_ic` 加進 custom 用的完整 `stageOverrides` 不足以讓「toggle 關 ⇒ `marginal_ic.enabled=false`」在 foundation／intermediate／advanced 成立；後端 `_apply_tier_config` 具名分支也只特殊處理 fdr。

**碼證**: VERIFY: `sed -n '352,375p' frontend/src/store/icAnalysisStore.ts` → `featureTier==='custom'` 才送完整 `stageOverrides`；否則僅 `fdr_correction`。VERIFY: `sed -n '4047,4056p' momentum/Analysis/ic_filter_orchestrator.py` → 具名 preset 只映射 `fdr_correction`。TODO Task 5.1 驗證⑤要求 toggle 關 ⇒ config `marginal_ic.enabled=false`，未要求 mirror fdr 的具名-preset 送出／消費特例。後端 `MarginalICConfig.enabled` 預設 True ⇒ OFF 被靜默忽略。RECHECK: 具名 intermediate 下關 toggle 後抓送出 JSON 是否含 `stage_overrides.marginal_ic=false`，且 `_apply_tier_config` 具名分支有對應消費。

**來源摘要**: frontend/src/store/icAnalysisStore.ts#a7d3936d7b04

[BLOCKING] 信心度=High。失敗：驗收⑤在非 custom tier 假綠或直接紅；產品上預設開＋可關的裁決落空。修法：TODO 明示（1）store 具名 preset 的 `stage_overrides` 必含 `marginal_ic`（同 fdr 模式）；（2）orchestrator `_apply_tier_config` 具名分支消費 `marginal_ic`（或改為通用：具名 preset 也 iterate `STAGE_OVERRIDE_PATHS` 交集送出鍵）；（3）驗證⑤綁定 intermediate／advanced 非僅 custom。

---

## GROK-R7-P0-03

**斷言**: Task 4.1 要求區分「fallback ⇒ `fit_scope=full_sample`」與「無 split 且非 fallback ⇒ `not_applicable:no_holdout_split`」，但 repo 無 `_in_fallback_rerun` 旗標；`_run_full_sample_fallback` 以 `ic_train_test_split=False` 重入 `analyze()`，執行端無法在不發明機制的情況下唯一判定。

**碼證**: BRIEF 假設掛載點仍成立：`analyze` stage6→7 於 `:1039-1059`；`refilter` `:1746-1765`；fallback 包體 `:1065-1152` 內層 `analyze()` `:1109-1117` 設 `ic_train_test_split=False`＋`_suppress_persist=True`。VERIFY: `grep -n '_in_fallback_rerun' momentum/Analysis/ic_filter_orchestrator.py` → 僅註解一行（1108），無實旗標。TODO 4.1 步驟 1 寫「非 fallback」但未定義偵測訊號（禁由 masks 推 `fit_scope`）。RECHECK: TODO 是否寫死（a）fallback wrapper 設 `self._in_fallback_rerun=True` 供 analyze 內 stage6b 讀取，或（b）fallback 重跑後覆寫 `marginal_ic` 節並禁止 analyze 內在 split=None 時走 full_sample。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c

[BLOCKING] 信心度=High。失敗：執行端用 `_suppress_persist` 當 proxy（語意耦合）或把使用者關 holdout 誤算成 full_sample（違反 SPEC D3 禁靜默退化），OOS 標示錯。修法：TODO 釘死唯一偵測／掛載策略＋偽碼；建議顯式 `_in_fallback_rerun`（註解已暗示但未落地）。

---

## GROK-R7-P1-01

**斷言**: Task 4.2 要求於 `_persist_outputs` 計算 `features_source_hash`（h5 檔 bytes）與 `labels_content_hash`（label series），但現行 `_ic_cache`／`_persist_outputs` 簽名不保留 `features_path`，亦不傳入 `label_series`，TODO 未指定要新增哪些 cache／參數。

**碼證**: VERIFY: `_ic_cache` 組裝 `:3449-3464` 鍵集含 `features_df`／`label_series`／`split_context` 等，**無** `features_path`。`_persist_outputs` `:3789-3797` 簽名＝`(features_df, filtered_df, report, metadata, filter_log)`。TODO 4.2 步驟 3 寫「讀檔 bytes／`label_series.to_numpy().tobytes()`」但未寫「analyze 將 `features_path` 存入 `_ic_cache['features_path']`」或擴充 `_persist_outputs` 參數。RECHECK: TODO 是否列出精確 cache 鍵與呼叫點改動。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=High。失敗：執行端卡住或擅自改 `_persist_outputs`／cache 形狀超出可審範圍。修法：Task 4.1／4.2 補「`_ic_cache['features_path']=features_path`（analyze 入口）」＋ persist 讀 `_ic_cache['label_series']`（已有）與 path；或顯式擴簽名並列 caller。

---

## GROK-R7-P1-02

**斷言**: Task 1.2 步驟 1 由 `fit_scope=="train"` 硬編碼 `oos_guarantees=True`／`pass_class="oos"`，與 SPEC D3′／Task 4.1「節上 OOS 欄與 root 一致」在「holdout 仍在但 root=`degraded_full_sample`」（事件不足 fallback）路徑互斥。

**碼證**: SPEC §A D3′：`oos_guarantees` 沿用 root。TODO 1.2：「`fit_scope=="train"` ⇒ `oos_guarantees=True`、`pass_class="oos"`」。orch `_resolve_root_status`：`event_filter.fallback is True` ⇒ `degraded_full_sample` 即使 holdout applied（`:1164-1167`）。此時 stage6b 若仍 `fit_scope=train`＋`oos_guarantees=True`，則 Task 3.1 驗證⑥／⑰（`oos_guarantees=True` ⇔ `analysis_status==ok_oos`）在組 survivor 檔時必炸，或報告節與 root 矛盾。RECHECK: TODO 是否改為「`oos_guarantees`／`pass_class` 由呼叫方傳入／抄 root，禁止函式內由 fit_scope 推導」。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d

[MAJOR] 信心度=High。失敗：事件 fallback 整合測試紅，或報告節謊稱 OOS。修法：`compute_marginal_ic`／`_stage6b` 之 OOS 欄改為 root 注入；`fit_scope` 只描述投影擬合窗。

---

## GROK-R7-P1-03

**斷言**: Task 3.1「輸入／輸出」函式簽名未列 `summary_by_feature`，但實作要點 3 寫「**加此參數**」供 survivors[] IC 快照；執行端簽名與改法互相矛盾。

**碼證**: TODO Task 3.1 輸入／輸出長簽名含 `report_meta, filtered_features, ... report_ref`，無 `summary_by_feature`。同 Task 實作要點 3：「由呼叫方預先抽成 dict 傳入 `summary_by_feature`——**加此參數**」。另簽名亦無 `oos_guarantees`，但驗證⑥／⑰與頂層 OOS 四欄要求該值——來源未釘（自 `report_meta`？自推？）。RECHECK: 簽名與步驟 3 是否同文一致列出完整 kwargs。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=High。失敗：執行端漏參數或自造擷取路徑，C4 身分／IC 快照缺欄。修法：簽名補 `summary_by_feature: dict[str, dict]` 與 `oos_guarantees: bool`（或明文「只從 report_meta 讀、缺則 raise」）。

---

## GROK-R7-P1-04

**斷言**: §V mutation 探針批次對映在 TODO 內不唯一且相對 SPEC 漂移：V-22 同時掛 B1（Task 1.3／1.2）與 B4（4.1／4.3）；V-24 同時掛 B3（3.2）與 B4（4.2／4.3）。SPEC 將 V-22→Task 4.1、V-24→Task 4.2。

**碼證**: SPEC Task 1.3 目標＝V-1..6、V-17 半、V-18、V-21（**無** V-22）；SPEC Task 3.2＝V-10..12、V-17 半、V-19、V-20（**無** V-24）；SPEC §V-22⇒4.1 ⑮；§V-24⇒4.2 ⓪。TODO 1.3 目標加 V-22；TODO 3.2 目標加 V-24；TODO 4.3 亦列 V-22..24。RECHECK: 每條 V-n 是否恰好一個 `--batch` case 列。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=High。失敗：B1 探針對尚不存在的 orch 預算路徑 sed 失敗（rc=2）或重複 case；探針「唯一對映」不可審。修法：V-22 只留 B4（純函式預算可用 Task 1.2 另建 V 編號或標明「1.2 單元＝V-22a、orch＝V-22」）；V-24 移回 B4；與 SPEC §V 表對齊。

---

## GROK-R7-P2-01

**斷言**: Task 4.2 新增契約 reason 值 `persist_suppressed`（改 `ic_survivor_contract.json#reasons.survivor_output`）不在 SPEC R7 義務字面內，屬輕度 SPEC 義務側擴張；宜延伸檔 A1，但**不**阻 B1。

**碼證**: SPEC Task 4.2 只寫「`_suppress_persist` 時不寫」；未定 metadata 五鍵形狀／reason 字面。TODO 4.2：`survivor_output` 為 `not_computed:persist_suppressed` 並「Task 1.0 契約於 B4 增此值」。BRIEF assumed：此增値不構成義務漂移——判：**需 A1 一條**（記錄 reason 枚舉增值＋五鍵形狀），因 SoT 枚舉屬契約義務。鍵集不變故 Task 1.0 ①仍可綠。RECHECK: `docs/GAP2_MARGINAL_IC_AMENDMENTS.md` 是否有 A1 條（檔目前不存在）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MINOR] 信心度=High。失敗：B4 review 爭議「誰有權改 SoT 枚舉」。修法：主委寫 A1；或改 TODO 為 suppress 時省略 `survivor_output` 鍵（若與「五鍵恆存在」衝突則仍須 A1）。

---

## GROK-R7-P2-02

**斷言**: Task 1.2 步驟 6「字面一律 `load_survivor_contract()`、不寫死」與 Task 4.1 ⑫「AST 掃字串常數 ⊆ 契約 reasons」可同時成立，但「或以常數對照」措辭易誘使執行端硬編碼字面（對齊舊 `test_r6` 消費點存在風格），造成與步驟 6 張力。

**碼證**: TODO 1.2 步驟 6；TODO 4.1 步驟 6／驗證⑫。既有 `test_r6_wider_contract_nodes_consistent` 對 report 契約 reasons 要求 `literal in orch_src`（存在性），與 TODO ⑫ 的 **⊆** 掃描不同。RECHECK: TODO 4.1 ⑫改寫為「允許 0 個字串常數；若有則 ⊆；執行期必須 load SoT」並禁「為過 AST 而複製字面」。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MINOR] 信心度=Medium。失敗：實作硬編碼 reason 後 SoT 改值不同步。修法：刪「或以常數對照」歧義句；測試改為 load 路徑＋可選 AST ⊆。

---

## 必答 1 — Agent 可執行性

| Task | 可直接寫碼？ | 卡住／需自行判斷 |
|---|---|---|
| 1.0 | 是 | 頂層鍵／reasons 三組已列舉；可對照 SPEC |
| 1.1 | 是 | 偽碼足夠 |
| 1.2 | 大多是 | OOS 欄由 fit_scope 推導 vs root（P1-02）；bootstrap 暫內建 OK |
| 1.3 | 否（探針表） | V-22 不應在 B1（P1-04） |
| 2.1–2.2 | 是 | bootstrap 搬移已標覆蓋風險 |
| 3.1 | **否** | 簽名缺 `summary_by_feature`／OOS 來源（P1-03） |
| 3.2 | 否 | V-24 錯批（P1-04） |
| 4.0 | 是 | scrub 清單有序；獨立化合理 |
| 4.1 | **否** | fallback 偵測未釘（P0-03）；掛載行號足夠（`:1046`／`:1753`） |
| 4.2 | **否** | `features_path` 未入 cache（P1-01）；`persist_suppressed` 待 A1（P2-01） |
| 4.3 | 大多是 | bench 無閾值（SPEC 已知不測）誠實 |
| 5.1 | **否** | 缺 FeatureTierPanel（P0-01）；具名 preset 送出／消費（P0-02） |

## 必答 2 — 義務覆蓋

- **D1–D7／D3′／D3″**：D1–D5／D7 落在 1.1／1.2／2.1／4.1，方向大致一致。**D3′ 漂移**：OOS 欄改由 fit_scope 推導（P1-02）。D3″（完整 df＋名稱 survivors）在 4.1 步驟 1 有落點。D6 在 1.0／3.1。
- **§G 1–4**：4.0／4.3／1.2／2.1／3.1 有落點；Task 4.0 獨立化≠義務漂移。
- **§V 24**：條目皆有 pointer，但批次對映漂移（P1-04）。
- **§C 白名單**：§0 七處對齊；B5 實需第八檔 `FeatureTierPanel.tsx`（UI 清單，SPEC §C-6 只寫 types——建議 TODO 明示為 B5 必要新改檔，或 A1 擴白名單）。
- **§N R1／R2／R3／R5**：registry「GAP-2 待補完」G2-R* 與三值理由一致；R4 已收回→Task 5.1。殘留「為何現在不做」成立（本輪不收回）。

## 必答 3 — 批次獨立性／forward dependency

- **B1**：不碰 report 契約 → OK。
- **B2**：依賴 B1；bootstrap 搬移同票標明 → OK。
- **B3**：不動 `ic_report_contract.json`；gate 要求 `test_ichc_contract_sync` 仍綠 → OK。
- **B4**：4.0→4.1（契約增鍵同 commit）→4.2→4.3 順序正確。4.2 改 survivor 契約**值**不改鍵集 → 與 1.0 ①相容。**缺口**：fallback／path cache（P0-03／P1-01）。
- **B5**：依賴 4.1 之 `STAGE_OVERRIDE_PATHS["marginal_ic"]` → 拓撲 OK；實作面 P0-01／P0-02 阻收案。
- **Task 4.0**：§G 凍結時機獨立化 → 非義務漂移。
- **4.2 `persist_suppressed`**：見 P2-01（建議 A1）。

## 必答 4 — 取巧面

- Oracle 容差寫死於 SPEC → 難取巧；O1a 求值順序有 mutation → 佳。
- **`n_regressions`**：TODO 定義＝實際 `fit_projection` 次數；超限視角不計入——須防「先算再丟仍++」；V-22 應對此，但批錯誤置。
- **Bench receipt 無閾值**：SPEC 已知不測；只斷言 `n_regressions==600`＋檔存在 → 誠實，非假綠源。
- **Toggle 只改前端不送 config**：P0-02 即此取巧／缺口；wiring R1a/R1b **不會**抓具名 preset 送出洞。
- **disabled 裸 `{}`**：有 V-14／wiring R3 → 有防。
- **重新凍結 pre 檔**：TODO 禁做 → OK。

## 必答 5 — 測試設計

- 各新測試檔要求 `test_mutation_*` 或 MUTATION-PROBE n/a → 合規。
- 探針 case 對映**不唯一**（P1-04）→ 須修。
- O7 獨立參考實作、O5 Bonferroni、洗牌 loo → 真實可證偽。
- Task 5.1 vitest ≥4 條不覆蓋「具名 preset 送出 enabled=false」→ 假綠風險。

## 必答 6 — 可 Frozen 進 B1？BLOCKING 清單

**否（整體 Frozen）**。若只開 B1 實作閘，P0-01／P0-02 屬 B5、可不擋 B1 **開工**，但仍建議先修 P1-04（V-22 勿入 B1 探針）再派 B1。

**BLOCKING（必須修才整體 Frozen）**
1. P0-01 FeatureTierPanel／TOGGLES 未入 Task 5.1
2. P0-02 具名 preset toggle→config 送出／消費未釘
3. P0-03 fallback vs no_holdout `fit_scope` 偵測未釘

**建議同輪修的 MAJOR**：P1-01 path/hash 配線；P1-02 OOS 欄跟 root；P1-03 `summary_by_feature` 簽名；P1-04 V-22／V-24 批次。

**A1（SPEC 義務側）**：P2-01 `persist_suppressed`。

---

## §1 十一類摘要

1. 矛盾／互斥：有（OOS 欄；V 批次；3.1 簽名 vs 步驟）  
2. 漏項／E2E：有（FeatureTierPanel；features_path cache；具名 preset 送出）  
3. 不可測：無新增；⑤在現況下不可在具名 preset 成立  
4. 可疑 quant：無新增；D3′ 揭露漂移見 P1-02  
5. 過度工程：無  
6. OOM／並行：計數 gate＋receipt 無閾值＝SPEC 已知  
7. Cache：event_identity／stage6b 有寫；features_path 漏  
8. API／相容：契約增鍵同 commit OK；persist reason 增值→A1  
9. 測試品質：探針對映不唯一  
10. Agent 可執行性：4.1／4.2／5.1／3.1 不足  
11. 短命工：無（4.0 非短命；bootstrap 搬移已標）

## 被當成事實的未驗證假設（§0）

| BRIEF 前提 | 本輪判定 |
|---|---|
| template_check／crosscheck PASS | 未重跑；標 assumed（不影響 findings） |
| SPEC R7 FROZEN／B5 裁決 | fact（文件＋registry） |
| Task 4.0＋`persist_suppressed` 不構成義務漂移 | **部分否**：4.0 OK；persist_suppressed → 建議 A1（P2-01） |
| 1.2 不寫死 vs 4.1 AST ⊆ 同時成立 | **可成立**，措辭有誘捕（P2-02） |
| 3.1 參數足以組契約；hash 於 orch 可取 | **否**（P1-01／P1-03） |
| 五批獨立綠／B5 依賴 STAGE_OVERRIDE | 拓撲 **是**；B5 實作仍缺 UI／送出（P0） |
| 4.1 掛載敘述可定位 | **行號是**；fallback 語意 **否**（P0-03） |
| 5.1 與 wiring R1a／R1b 相容 | R1a／R1b 三點配線 **是**；UI／具名 preset **否**（P0-01／02） |

STATUS: DONE
