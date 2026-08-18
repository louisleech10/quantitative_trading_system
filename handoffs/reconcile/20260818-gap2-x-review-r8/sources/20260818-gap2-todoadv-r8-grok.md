# GAP-2 TODO adversarial — GROK R8（TODO DRAFT R2＋A1-1..3 複核）

family: grok｜task-id: 20260818-GAP2-X-REVIEW-R8｜brief: `handoffs/20260818-gap2-todoadv-r8-BRIEF.md`
標的：`docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R2）｜義務來源：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）＋`docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..3）｜R7 收斂：`handoffs/reconcile/20260818-gap2-x-review-r7/synth.md`（T1–T6）

## Verdict：需修補

不可 Frozen 進 B1。R7 T1／T3／T4／T5／T6 多數寫回可核對；仍有 **2 條 P0**（§0 白名單漏 `FeatureTierPanel.tsx`；Task 4.2 仍從尚未建立的 `_ic_cache` 讀 `event_identity`）會讓執行端卡住或違反冷啟動／§0。另 **2 條 P1**（A1-2 `case_id` 未落入 4.0／4.3；Task 4.1 步驟 1 仍依 `fit_scope` 帶 `pass_class` 與 A1-3 衝突）。修補後再 Frozen。

---

## GROK-R8-P0-01

**斷言**: Task 5.1 要求改 `frontend/src/components/ic-analysis/FeatureTierPanel.tsx`，但 TODO §0「既有檔改動白名單（唯此七處）」未列入該檔；執行端若守 §0 則無法完成 R7 T4 寫回的可見 toggle，若改該檔則違反 §0／派工「白名單外一律不碰」。

**碼證**: TODO §0 L12 白名單⑥＝`types.ts`＋`icAnalysisStore.ts`，無 `FeatureTierPanel.tsx`（VERIFY: `grep -n FeatureTierPanel docs/GAP2_MARGINAL_IC_TODO.md` → 僅 L3 敘事與 Task 5.1 L253，§0 無）。Task 5.1 L253 明示改 `FeatureTierPanel.TOGGLES`；實核面板仍硬編碼 24 鍵、`已啟用 {enabledCount}/24`（`FeatureTierPanel.tsx:20-51,:97`）。SPEC §C 白名單亦無此檔／無 store（§C#6 僅 `types.ts`）→ 標 **SPEC 義務側**（建議 A1-4 擴白名單）。RECHECK: §0 是否把 `FeatureTierPanel.tsx` 列入白名單（並與 SPEC §C／Task 5.1 檔案清單一致）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[BLOCKING] 信心度=High。失敗：B5 再犯 R7 GROK-R7-P0-01（UI 無 checkbox）或 agent 因 §0 拒改／越權。修法：§0 白名單加入 `FeatureTierPanel.tsx`；SPEC §C 以延伸檔同步（store＋panel＋types）。

---

## GROK-R8-P0-02

**斷言**: Task 4.1 已釘死「`_persist_outputs` 在 `_ic_cache` 建立前呼叫 ⇒ `event_identity` 等須**顯式 kwargs、不讀 `_ic_cache`」；Task 4.2 組裝呼叫仍寫 `event_identity=self._ic_cache["event_identity"]`，與 4.1 互斥，執行端照 4.2 會在首跑 persist 讀到未寫入／舊 cache。

**碼證**: TODO Task 4.1 L202：「persist…於 `_ic_cache` 建立前…kwargs `…／event_identity／…` **顯式傳入（不讀 `_ic_cache`）**」。Task 4.2 L220：`build_survivor_output(..., event_identity=self._ic_cache["event_identity"], ...)`。實核 orchestrator：`_persist_outputs` 於 `:3432-3438`，`self._ic_cache = {` 於 `:3449`（之後）。RECHECK: Task 4.2 是否改為使用 4.1 新增之 `event_identity`（及 `stage6b_results`／`features_path`／`label_series`）參數，並刪除對 persist 當下 `_ic_cache[...]` 的依賴。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[BLOCKING] 信心度=High。失敗：`KeyError`／沿用上一次 analyze 的 event_identity／provenance 錯；R7 T3 寫回在 4.1／4.2 未收斂。修法：4.2 偽碼與 4.1 kwargs 對齊；可保留 `self._event_identity` 實例欄作 refilter 備援，但 persist 路徑不得讀尚未建立的 `_ic_cache`。

---

## GROK-R8-P1-01

**斷言**: 延伸檔 A1-2 要求 pre 檔寫入實際 `case_id`（`ic_gatekeeper`）且 `test_gap2_golden.py` 斷言 live `report_ref` 檔名段與 pre 一致；TODO Task 4.0 `--write` 欄位清單與 Task 4.3 驗證皆未納入該義務。

**碼證**: A1-2（`docs/GAP2_MARGINAL_IC_AMENDMENTS.md` L9-11）：寫入 pre 之 `case_id` 欄＋golden 斷言 `report_ref`。Task 4.0 L187：`--write` → `{fixture_sha256, config_hash, canonical_sha, summary_table, filter_log, generated_by, ts}`——**無 `case_id`**；僅「`case_id` 由 helper 決定」。Task 4.3 L234 驗證列無 `case_id`／`report_ref`／A1-2。RECHECK: 4.0 寫檔 schema 加 `case_id`；4.3 加 `report_ref` 檔名段 == pre[`case_id`]；註明不改 helper（A1-2）。

**來源摘要**: docs/GAP2_MARGINAL_IC_AMENDMENTS.md#6fdc01cb5613

[MAJOR] 信心度=High。失敗：R7 T2／CODEX-R7-P1-02 之 case_id 漂移在 B4 golden 再現；agent 可能仍寫死 `gap2_golden`。修法：把 A1-2 逐字落進 Task 4.0／4.3。

---

## GROK-R8-P1-02

**斷言**: Task 4.1 步驟 1 仍要求 `_stage6b` 回傳「並帶 `pass_class`（`oos` iff `fit_scope=="train"`）」，與 A1-3／同 Task 步驟 2「`oos_guarantees`／`pass_class` 由 `_stage7_report` 於 root 解析後注入」及 Task 1.2「OOS 欄 `None` 佔位」衝突；事件不足 fallback（holdout 仍在、`fit_scope=train`、root=`degraded_full_sample`）會讓執行端在注入前寫入謊稱 OOS 的 `pass_class`。

**碼證**: TODO L201 步驟 1 末句；L202 步驟 2 注入句；Task 1.2 L79／A1-3 L13-15。實核 root：`event_filter.fallback is True` ⇒ `degraded_full_sample` 即使 holdout applied（`ic_filter_orchestrator.py:1164-1167`）。RECHECK: 刪除步驟 1 之 fit_scope→pass_class 推導；明確 `_stage6b` 只回 `res.to_dict()`（含 `None` 佔位）＋composite，OOS 兩欄只在 stage7 注入。

**來源摘要**: docs/GAP2_MARGINAL_IC_AMENDMENTS.md#6fdc01cb5613

[MAJOR] 信心度=High。失敗：重開 R7 GROK-R7-P1-02；validator ⑰／整合③與節上欄互斥。修法：步驟 1 與 A1-3 對齊刪除該推導句。

---

## 被當成事實的未驗證假設（§0／brief assumed）

| # | 前提 | 判定 | 說明 |
|---|---|---|---|
| A | Task 4.0 獨立化＋Task 4.2 增值 `persist_suppressed` 不構成未登記義務漂移 | **成立（有 A1-1）** | A1-1 已記錄；鍵集不變。非 finding。 |
| B | Task 1.2「字面一律 `load_survivor_contract()`」與 Task 4.1 ⑫ AST 可同時成立 | **成立** | L206：runtime 一律 load；AST 可選／無常數則 vacuous。T6 已收。 |
| C | Task 3.1 參數足以組契約；hash 於 orch 可取得 | **部分不成立** | `summary_by_feature`／`root_analysis_status` 已入簽名；`_features_path`／顯式 `label_series` 已寫。但 `event_identity` 來源見 **P0-02**。 |
| D | 五批可獨立綠；B5 wiring 依 4.1 `STAGE_OVERRIDE_PATHS` | **成立（條件式）** | 批間 gate 已分跑；B3 不動 report 契約。B5 另受 P0-01 白名單阻。 |
| E | Task 4.1 掛載敘述足以定位 | **成立** | 實核 `analyze` stage6 `:1039-1046`→stage7 `:1048`；`refilter` `:1746`→`:1754`；fallback `:1065-1151` 註解已提 `_in_fallback_rerun`。 |
| F | 前端 Task 5.1 與 `ic_wiring_check` R1a／R1b 相容 | **成立（若照做）** | R1a＝PRESET 鍵 ⊆ stageOverrides／moduleOverrides 之 `Boolean(state.featureToggles.*)` ∪ allowlist；加 `marginal_ic` 進 `stageOverrides` map＋`STAGE_OVERRIDE_PATHS` 即可。具名 preset 送出是功能正確性（非 R1a 機械範圍），TODO 已比照 fdr。 |

VERIFY: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → `TEMPLATE PASS` rc=0（本輪實跑）。

---

## R8 必核（逐條）

### T1 Gate 分跑＋B1 十條唯一對映；V-22a／V-24 批次
**PASS。** §B L32：兩條 pytest 分跑（註 R7 COMPOSER／CODEX）。Task 1.3 L99：B1 十條 V-1..V-6／V-17a／V-18／V-21／V-22a 唯一對映；V-22／V-24 只在 B4（L99）。與 R7 T1 處置一致。

### T2 `build_survivor_output` 簽名＋OOS `None`＋A1-3＋golden case_id
**部分 FAIL。** 簽名已含 `summary_by_feature`／`root_analysis_status`（L151）；Task 1.2 OOS `None`＋stage7 注入（L79、L202）＋A1-3 在檔。**A1-2 未落入 Task 4.0／4.3** → **P1-01**。

### T3 兩插入點＋`_in_fallback_rerun`＋persist kwargs＋`_features_path`
**部分 FAIL。** 兩插入點＋旗標 try/finally＋kwargs 清單＋`_features_path`／`_labels_path` 已寫（L202）。**4.2 仍讀 `_ic_cache["event_identity"]`** → **P0-02**。

### T4 B5：FeatureTierPanel、具名 preset、`_apply_tier_config`、驗證⑤三路徑
**部分 FAIL。** Task 5.1 L253／L262 已含 panel、具名 preset 送出、④ 消費於 4.1、⑤ 三路徑。**§0 白名單漏 panel** → **P0-01**。

### T5 警語子字串；bench 觀測
**PASS。** L256 警語「…非獨立驗證」；`「獨立 OOS 驗證」 in 該句` → False（本輪 python 實核）。L236 bench＝觀測、OOM 僅計數上界。

### T6 reason＝`load_survivor_contract()`；`persist_suppressed`＝A1-1
**PASS。** L206 runtime 一律 load；A1-1 已存在且 Task 4.2 L220 指向增值。

### 可 Frozen？
**否。** BLOCKING＝P0-01、P0-02；修補後再派 stamp／Frozen。

---

## 必答 1–6

### 1. Agent 可執行性
- **卡住／自行判斷**：P0-01（§0 vs Task 5.1）；P0-02（4.1 vs 4.2 event_identity）；P1-02（pass_class 雙來源）。
- 其餘 Task 1.0–1.3／2.x／3.1 簽名與偽碼大致可直接寫碼；掛載行號實核可用。
- Task 4.0／4.3 缺 A1-2 欄位 ⇒ golden 身分 agent 需猜（P1-01）。

### 2. 義務覆蓋
- D1–D7／D3′／D3″、§G 1–4、§V 24、§N 四殘留：追溯表 L271–298 有落點；殘留 registry G2-R1／R2／R3／R5 三值理由仍成立（本輪抽讀，不重議）。
- **漂移**：A1-2 未進 TODO 正文；A1-3 與 Task 4.1 步驟 1 殘句衝突；§0／SPEC §C 白名單未覆蓋 Task 5.1 必要既有檔（panel；SPEC §C 亦漏 store）。

### 3. 批次獨立性／forward dependency
- B1→B2 gate 分跑 OK；B3 不動 report＋既有 sync 綠 OK；B4 契約增鍵與 orch 同 commit OK；Task 4.0 為 B4 首件 OK。
- B5→4.1 `STAGE_OVERRIDE_PATHS["marginal_ic"]` 依賴已明示。
- `persist_suppressed` 增值在 B4／A1-1，不阻 B1。

### 4. 取巧面
- bench 已降級為觀測（不可再當 OOM 通過證明）—已標明，OK。
- oracle 容差沿 SPEC §G—未放寬。
- toggle：若只改 store 不改 FeatureTierPanel／具名 preset／`_apply_tier_config` → 假綠（P0-01 即此門）。
- `n_regressions==600` 只鎖呼叫次數—已知邊界。

### 5. 測試設計
- B1 十條 V↔test 對映唯一；V-22a／V-24 分批清楚。
- 各新測試檔要求 `test_mutation_*` 或 MUTATION-PROBE n/a—§0 紀律在。
- A1-2 缺測項使 case_id／report_ref 無 falsification（P1-01）。

### 6. 可 Frozen？BLOCKING 清單
- **不可 Frozen**。
- BLOCKING：`GROK-R8-P0-01`、`GROK-R8-P0-02`。
- 建議同輪修：`GROK-R8-P1-01`、`GROK-R8-P1-02`（否則下一輪仍易炸）。

---

## §1 十一類（摘要；無則「無」）

1. 矛盾/互斥：P0-01、P0-02、P1-02（有）
2. 漏項：P1-01 A1-2 未落地（有）；其餘義務表大致齊
3. 不可測：bench 已誠實降級（無新 BLOCKING）
4. 可疑 quant：無新增（D1–D4 未改）
5. 過度工程：無
6. OOM/並行：bench 觀測邊界已標（無）
7. Cache：event_identity／persist 順序見 P0-02
8. API/型別：wiring 路徑相容（條件式 PASS）
9. 測試品質：A1-2 缺斷言（P1-01）
10. Agent 可執行性：P0-01／P0-02
11. 必要性/短命工：無（1.0 loader→3.1 增量；4.0 保留）

## §2 錨點／獵空殼／§N
- TODO 有 §0／§B／每 Task 驗證／邊界／不可做／存活至／覆蓋風險；`template_check todo` PASS。
- 非空殼：Task 偽碼具體；本輪缺陷是**互斥／漏寫回**，非標題空段。
- §N G2-R1／R2／R3／R5：`為何現在不做` 三值＋觸發仍成立；不收回為 Task。

---

ASSUMPTIONS_VERIFIED: R7 T1–T6 寫回抽核；orchestrator persist-before-cache 行號；FeatureTierPanel 硬編碼 TOGGLES；store 具名 preset 僅 fdr；wiring R1a 鍵抽取；A1-1..3 檔案；警語子字串；template_check todo PASS
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS rc=0；行號／子字串／sha 前綴實核（見上）
FAILURES_SEEN: none
SCOPE_CHANGES: none（只產 review；建議 SPEC §C 白名單走 A1-4，未改碼）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
