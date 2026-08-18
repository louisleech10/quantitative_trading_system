# GAP-2a／2b SPEC adversarial 審查 R3 — GROK

**task-id**: `20260818-GAP2-X-REVIEW-R3`｜**family**: grok｜**輪次**: R3  
**brief**: `handoffs/20260818-gap2-specadv-r3-BRIEF.md`  
**審查標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`＃`3cfb3336d293`（R2 修訂版）  
**R2 收斂**: `handoffs/reconcile/20260818-gap2-x-review-r2/synth.md`＃`f4d34b65ba51`  
**本家 R2**: `handoffs/20260818-gap2-specadv-r2-grok.md`  
**禁改碼／禁改 SPEC**（只產本檔）

**VERIFY（本輪實跑）**:
- `shasum -a 256 docs/GAP2_MARGINAL_IC_SPEC.md` → `3cfb3336d293…`
- `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`
- O1a（σ=0.866）：rank `var_r≈4.74e-32`；raw `var≈3.80`（≫1e-10，nondeg）、raw_sp≈−0.196
- O1b：rank `var≈0.139`；`|marg|≈0.00018`≤0.02
- O4（σ=0.8）：`Var(y)≈0.991`；margs≈`[0.282,0.274,0.284,0.284]`；`composite≈0.574`；ratio≈0.960 — 三帶全過
- `run_analyze()`（ETHUSDT/12h tail2000 fixture）：stage5 in=14 out=2；stage6 survivors=2 removed=0；`extra_candidates≈0`；metadata `symbol=ETHUSDT`／`timeframe=12h`／`case_id=None`
- `_resolve_case_id` 缺 `metadata.case_id` ⇒ 預設 `"ic_gatekeeper"`（檔名段 SoT）；`_resolve_metadata_symbol_allowlist` 缺 `metadata.symbol` ⇒ raise；fixture `_meta.json` 有 symbol／timeframe、無 case_id

---

## Verdict：需修補後派工

L1／L4／L5 文面＋實跑閉合；L2／L3 主義務已寫進 Task 正文，但 **§C 白名單／Task 1.0 前言／§G-4** 仍殘留與 R2 處置相反的舊句——實作者若依錨點段實作會與 Task 3.1⑮／Task 4.1「不加 reasons」互斥，§G-4 更會在 `run_analyze()` 真路徑（`metadata.case_id=None`）對正確 L3 實作假紅。進 TODO 前須清掉這兩處文件漂移。

**BLOCKING 清單**
1. `GROK-R3-P0-01` — §G-4 仍要求 `case_id` 對報告 metadata exact 相等，與 L3／Task 3.1⑮（檔名段）互斥；真路徑 `case_id=None`

**MAJOR**
2. `GROK-R3-P1-01` — §C L62＋Task 1.0 L106 仍指示 B4 對 `ic_report_contract.json` **加 reasons**，與 L2／Task 1.0 reasons 唯一列舉／Task 4.1「不加 reasons」互斥

---

## 挑戰 brief assumed（§0）

| assumed | verdict | 證據 |
|---|---|---|
| 五群集修訂皆閉合且彼此無新矛盾 | **不成立**（L2／L3 錨點殘句） | → P0-01／P1-01；L1／L4／L5 本輪核對閉合 |
| 報告 `metadata.symbol`／`timeframe` 於正常 holdout 必存在；缺時 fail-closed 已明定 | **成立（本 fixture）**；symbol 於 split 已有 raise；timeframe 由 meta 帶入 | `run_analyze` meta 兩欄皆有；`_resolve_metadata_symbol_allowlist` 缺 symbol raise；Task 4.2／3.1⑮ 缺欄 fail-closed 已寫 |
| 預算預設 200 對 ETHUSDT/12h tail2000 不觸發 `candidate_budget_exceeded` | **成立** | survivors=2、extra≈0 ≪ 200 |

---

## Findings

## GROK-R3-P0-01

**斷言**: R2 L3 已把 `case_id` 對照改為 `report_ref` 檔名段（且不改 report metadata），但 §G-4 仍要求 `symbol`／`timeframe`／`case_id` **皆**與報告 metadata exact 相等；在 `run_analyze()` 真路徑 `metadata.case_id=None`、`_resolve_case_id`→`ic_gatekeeper` 下，依 Task 3.1⑮ 實作的正確 validator 會被 §G-4／V-19 假紅。

**碼證**: SPEC L96（§G-4「與報告 metadata exact 相等」）；對照 L178 Task 3.1⑮（`case_id`＝`ic_report_{case_id}.json` 檔名段，**不**改 report metadata）與 R2 synth L3。VERIFY：`run_analyze()` → `metadata.case_id is None`、`symbol=ETHUSDT`、`timeframe=12h`；`sed -n 3856,3859p momentum/Analysis/ic_filter_orchestrator.py` → 缺 case_id 時回 `"ic_gatekeeper"`。RECHECK: 重跑 `run_analyze()` 印三欄；對照 L96 vs L178。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[BLOCKING] 信心度=High。會怎麼失敗：B3／B4 依⑮做檔名對照 → §G-4 要 `payload.case_id == metadata.case_id`（None）失敗；或為過 §G-4 把 case_id 鏡進 report metadata＝直接違反 L3「不改 report metadata」。  
修法：§G-4 改寫為與 Task 3.1⑮ 同一對照規則（symbol／timeframe↔metadata；case_id↔`report_ref` 檔名段）；V-19「§G-4 轉紅」同步該語意。

---

## GROK-R3-P1-01

**斷言**: R2 L2 已裁定 reason 字面唯一住 `ic_survivor_contract.json#reasons`、B4 **不加** `ic_report_contract.json#reasons`，但 §C 允許改動白名單第 3 項與 Task 1.0「既有 caller」句仍寫 B4 對 report 契約 **加 reasons 兩組／reasons 增鍵**，與 Task 4.1 正文「不加 reasons」及 Task 1.0 reasons「唯一列舉處」互斥。

**碼證**: SPEC L62（`reasons` 加 `marginal_ic`／`marginal_ic_feature`）；L106（`report_sections`／`reasons`／`metadata` 增鍵全部移至 Task 4.1）；對照 L105（reasons 唯一列舉、不設 `reasons_ref`、report 不加 reasons）與 L199（**不加 reasons**）。另 L68「既有 … reasons 以 `*_ref` 指向 `ic_report_contract.json`」仍暗示舊 ref 設計。VERIFY：`jq -r '.reasons|keys[]' momentum/Analysis/contracts/ic_report_contract.json` → 僅既有三鍵、無 marginal_*。RECHECK: `grep -n 'reasons 加\\|不加 reasons\\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[MAJOR] 信心度=High。會怎麼失敗：實作者依 §C／L106 於 B4 寫入 report `reasons.marginal_ic*` → 兩處列舉回潮、`test_r6` 要求 orchestrator 對新 reason 鍵有字面、或與「 survivor 契約唯一 SoT」漂移；依 Task 4.1 不加則與 §C 白名單字面衝突、審查／實作各執一段。  
修法：L62 改為只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；L106 刪「reasons 增鍵」；L68 改為僅 `capability_status_ref`（reasons 不再 ref 到 report 契約）。

---

## 必答

### 1. L1–L5 逐群集：閉合？

| 群集 | 閉合？ | 說明 |
|---|---|---|
| L1 O1 raw／O4 σ | **是** | L87 刪 raw>0.10、改 O1a raw 非退化⇒ok 假紅；V-2→O1a；表內 σ 已寫死；本輪 O1a／O1b／O4 實跑落帶 |
| L2 reasons SoT | **否** | Task 1.0／4.1 正文已改住 survivor＋不加 report reasons，但 §C L62／L106／L68 殘留加 reasons／`*_ref` → P1-01 |
| L3 身分對照 | **否** | Task 3.1⑮／4.2 已改檔名段＋缺欄 `identity_missing`，但 §G-4 L96 未跟 → P0-01 |
| L4 event_identity | **是（文面）** | L105 `_doc` 序列化、L177／L201 cache owner、驗證⑬⑱ 齊；簽名仍列 `event_timestamps` 但不另開 finding（改法已釘「只讀 identity」） |
| L5 預算／V-19／V-13 | **是** | `max_*=200`、超限整體 `candidate_budget_exceeded`、驗證⑮⑰、V-13 反向、V-19 三欄皆在 |

### 2. 新引入風險？

- **有**：L2／L3 錨點殘句（上列）。
- 預算 200 對本 fixture 安全；對「>5000 features 且多數過 FDR」之生產設定仍可能觸發整體 `not_computed`（設計如此，非假紅）——建議 TODO 用真實大 fixture 記一筆 receipt，本輪不另開 finding。
- §V 邊界仍寫「k≤數十…OOM 不測」（L269）與預算 200 並存：降載語意已改為計數 gate，該句過時（MINOR 級，併入收斂修訂即可）。

### 3. 預算預設 200 vs 真實 fixture 數量

| 量 | 值 |
|---|---|
| fixture | `ETHUSDT_12h_*_a0_tail2000` via `run_analyze()` |
| stage5 input／output／removed | 14／2／12 |
| stage6 survivors／removed | **2**／0 |
| `extra_candidates`（passed∖survivors）估 | **0** |
| 預設 200 是否觸發 | **否**（2≪200、0≪200） |

### 4. 可進 TODO？BLOCKING 清單

**否——需修補後派工。** BLOCKING＝`GROK-R3-P0-01`；建議同輪修 `GROK-R3-P1-01`（否則 L2 宣告閉合不實）。修完後 §G-4／§C／Task 1.0 前言與 Task 正文一致即可進 TODO（本輪不要求重跑 oracle，L1 已綠）。

---

## §1 必查（11 類）

1. 矛盾／互斥：§G-4↔Task 3.1⑮；§C／L106↔Task 4.1 不加 reasons — 有  
2. 漏項／端到端：L3／L2 主路徑已補；殘在錨點段 — 有  
3. 不可測驗收：§G-4 在真路徑不可與⑮同時綠 — 有  
4. 可疑 quant：L1 本輪實跑無新洞 — 無  
5. 過度工程：無  
6. OOM／並行：L5 計數 gate 已補；L269「k≤數十」過時 — 輕微  
7. Cache：event_identity owner 已寫 — 無新洞  
8. API／型別：無  
9. 測試品質：V-13 反向／V-19 三欄已列 — 無  
10. Agent 可執行性：白名單與 Task 互斥 — 有（P1-01）  
11. 必要性／短命工：無不當白工  

## 被當成事實的未驗證假設（§0）

- 「R2 五群集寫回後全文一致」— **assumption，已被 L96／L62／L106 殘句推翻**  
- 「`run_analyze` metadata 必有 case_id」— **false**（本輪 None；故 L3 改檔名段正確，§G-4 未跟）  
- 「預算 200 會誤傷 golden fixture」— **false**（survivors=2）

STATUS: DONE
