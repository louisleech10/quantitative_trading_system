# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R8（COMPOSER）

task-id: 20260823-GAP3UX-X-REVIEW-R8  
brief: `handoffs/20260823-gap3ux-x-review-r8-brief.md`  
標的: `docs/GAP3_EVENT_UX_SPEC.md`（sha256 `01cf2468573ff50f9d3933698d2b110824bccc259bb519a1e2f523ca5b151bd0`，1580 行；**尚未實作**）  
家族: COMPOSER | 輪次: R8

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 分類 | 本輪覆核 |
|---|---|---|
| SPEC sha256／行數與 brief 鎖定一致 | **fact-verified** | `shasum -a 256` → `01cf2468…51bd0`；`wc -l` → 1580 |
| 六支機械閘皆 rc=0 | **部分 fact-verified** | `bash scripts/gap3ux_pre_review.sh` → 五閘 rc=0；`patch_locus` 僅傳 patch 時跑（見 **COMPOSER-R8-P1-02**） |
| facts.sh 14 條 rc=0 | **fact-verified** | `bash handoffs/20260823-gap3ux-x-review-r8-facts.sh` → rc=0 |
| 議題一架構調整成立 | **assumption→fact-verified（本輪）** | 碼證支持（見議題一裁定）；但 **SPEC 未改寫**（→ **COMPOSER-R8-P0-01**） |
| R7 十二條處置未引入新矛盾 | **assumption，部分不成立** | R7 文字層多數 CLOSED；議題一使群集 E（7.0b）**須重寫**（→ **COMPOSER-R8-P0-02**） |
| A-6 仍為待確認之有效問題 | **assumption，不成立** | D-3(a) 已被使用者架構調整取代；A-6 應作廢並換新白話閘（見 arch-shift 補丁） |
| `label_value` 分析時計算可由既有 PIT 規則保證 | **assumption，條件成立** | `alignment.py:154-168`＋`ic_feed.py:75-76`＋`pipeline.bars_from_kline_cache` 已具備；缺 §G 分析時 golden（併入 P0-02） |

---

## 議題一裁定（架構調整）

**1. 是否成立？** **成立。** 條件 IC 本質是 IC-Analysis 之一種；事件批次是 t0 條件之事實（`label`＝`positive_case`），答案窗是研究參數。現行 `/search` 把 `horizon_bars`／`label_value` 烤進匯出檔（`search/page.tsx:53-54,526`；`eventExport.ts:81-101`），比較不同 horizon 須重匯出，層次錯誤。

**2. PIT 正確性（分析時計算）？** 可由既有機制保證，但 SPEC 須明訂：  
- 特徵截止：`feature_cutoff_rule = max_close_ms_le_decision_at`（`ic_feed.py:76`）  
- 決策時點：`decision_time_rule = t0_open_minus_k_bars`（`:75`）  
- `label_value` 計算須走 `align_events` 同一 bars 路徑（`alignment.py:154-168`），**禁**讀 `/search` 預算之 `future_{h}bar_return`  
- §G G-2 須新增分析時 fixture（horizon 參數 ＋ exact return／NaN mask／`label_end_ms`）

**3. A-6 是否作廢？** **作廢。** 原 A-6 問的是 D-3(a)「附帶欄多選不改主答案窗」——架構調整後主答案窗不在 `/search`，應替換為新 A-6：「答案窗在 IC 分析頁設定、匯出不帶 `label_value`」之白話閘（仍須使用者確認後 FROZEN）。

**4. 影響面（同步集合）**：見補丁包 `handoffs/patches/20260823-gap3ux-r8-arch-shift.md`（D-3、§A、Task 4.1／4.1c／4.3、7.0b、7.4、7.6、V-6、§G、`search/page.tsx`）。

**5. 主委判斷**：**無需推翻**——碼證與使用者論點一致；缺口在 SPEC 仍寫 D-3(a) 與匯出端 producer，非使用者判斷錯誤。

---

## R7 十二條之 CLOSED／OPEN（反例重跑）

| 群集 | R7 ID | 本輪 | 碼證摘要 |
|---|---|---|---|
| A | COMPOSER-R7-P1-01、GROK-R7-P2-01 | **部分 OPEN** | R7 已補第五閘進 F-14，但 R8 `facts.sh` 仍標「五支」且未包 `gap3ux_pre_review.sh`；`pre_review.sh` 仍指 r7-facts（→ **P1-01／P1-02**） |
| B | CODEX-R7-P1-05、GROK-R7-P1-01 | **CLOSED** | F-2 L1088-1091 純引用 Task 1.1；`rg '15 增為 16' docs/GAP3_EVENT_UX_SPEC.md` → 0 |
| C | CODEX-R7-P1-03、GROK-R7-P1-02 | **CLOSED** | Task 7.7 ① L1429-1432 指向 ④ epoch 秒字串 |
| D | CODEX-R7-P1-04 | **CLOSED** | Task 7.3 L1303-1308 含 `control_kind` |
| E | CODEX-R7-P0-01、COMPOSER-R7-P1-02、GROK-R7-P1-03 | **SUPERSEDED** | R7 文字已補 API（L1164-1194）；議題一要求改 IC 路徑與 bars 計算（→ **P0-02**） |
| F | CODEX-R7-P0-02 | **CLOSED** | Task 1.10 ④ L613-621 含 legacy `lookahead_unknown` |
| G | COMPOSER-R7-P2-01 | **CLOSED** | Task 1.3 L494-505 明引 §G S-9 ＋跨環境 digest |

---

## 必查涵蓋面（brief 六項摘要）

**1. 議題一**：成立；SPEC 未落地（P0-01／P0-02）；A-6 須替換。  
**2. R7 逐條**：7 CLOSED、1 部分 OPEN（gate receipt）、1 SUPERSEDED（7.0b 架構）。  
**3. 全棧三欄**：`/search` 仍有 `eventHorizonBars` UI（code✅ 有／應移除）；IC 頁無 horizon 分析參數（UI❌）；7.0b API 設計在錯誤層（wiring❌）。  
**4. 主委未審產物**：`patch_locus_check.py` 反測邏輯合理；`gap3ux_pre_review.sh` 仍指 stale facts（P1-01）；角色卡與 brief 閘數敘述不一致（P1-02）。  
**5. §C0**：無放水；架構調整符合「只能更嚴」。  
**6. Verdict**：需修訂後定版（見下）。

### §1 必查十一類（摘要）

1. 矛盾：有（D-3(a) vs 使用者架構；Task 7.6 禁改 vs IC 頁須設分析參數）  
2. 端到端：有（匯出→IC 之 label_value 路徑錯層）  
3. 不可測：無新增（補丁包已列 VERIFY）  
4. Quant：有（分析時 PIT 須 §G golden，否則靜默洩漏風險）  
5-11. 其餘：無新增 BLOCKING

---

## COMPOSER-R8-P0-01

**斷言**: 使用者 2026-08-23 架構調整（答案窗屬 IC 分析、非 `/search` 匯出）已獲碼證支持，但 SPEC 仍採 D-3(a) 並在 Task 4.1／V-6／A-6 綁定「主答案窗」與匯出時 `label_value`／`horizon_bars`，與已裁定方向互斥。

**碼證**: `nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '113,119p'` → D-3 仍寫「仍綁單一主答案窗」；`nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '841,850p'` → Task 4.1 驗收仍要求 `window.horizon_bars == 4`；`nl -ba frontend/src/app/search/page.tsx | sed -n '53,54,526,1568'` → `/search` 仍有 `eventHorizonBars`；brief 議題一碼證 `sed -n '75,85p' frontend/src/lib/eventExport.ts` → `label` 來自 `positive_case`、`label_value` 來自 `future_{h}bar_return`。RECHECK：套用 `handoffs/patches/20260823-gap3ux-r8-arch-shift.md` 後 `rg '主答案窗' docs/GAP3_EVENT_UX_SPEC.md` 僅剩歷史註記。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f; frontend/src/app/search/page.tsx#01cf2468573f

[BLOCKING] 信心度=High。Agent 依現行 SPEC 實作會固化錯誤層次（匯出時烤答案窗），使用者比較 horizon 仍須重匯出，與使用者裁定及 §C0 相悖。修法：採補丁包 D-3(d) 改寫 §A A-6、Task 4.x、V-6；移除 `/search` 主答案窗 UI。

---

## COMPOSER-R8-P0-02

**斷言**: Task 7.0b 之 `POST /api/v1/case/label-values` 仍設計為 `/search` 匯出時由 `cases` 列讀 `future_{horizon}bar_return` 產生 `label_value`；若議題一成立，producer 須改為 IC 分析路徑、以 `bars_from_kline_cache`＋`align_events` 於分析時計算，並補 §G 分析時 golden，否則 R7 群集 E 之修復在錯誤層次閉合。

**碼證**: Task 7.0b L1162-1163「在矩陣內 ⇒ `label_value` 取 `future_{horizon_bars}bar_return`」；L1167-1169 端點 `POST /api/v1/case/label-values`、request 含 `cases`（`/search` 結果列）；`momentum/Analysis/event_samples/ic_feed.py:4-5` 載明 v1 不重算為版本限制；`pipeline.py:78-82` `bars_from_kline_cache` 為服務端唯一入口；`alignment.py:154-168` 已可由 `horizon_bars`＋bars 推導 `label_end_ms`。RECHECK：改寫後 `rg 'future_\\{horizon_bars\\}bar_return' docs/GAP3_EVENT_UX_SPEC.md` 於 Task 7.0b 區段為 0。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f; momentum/Analysis/event_samples/pipeline.py#01cf2468573f

[BLOCKING] 信心度=High。主委若套用 R7 版 7.0b 而不隨架構調整，會把錯誤 producer 焊死在匯出 API，IC 頁仍無法「同批事件改 horizon 重跑」。修法：見 arch-shift 補丁（IC 端點、`buildEventContractRecords` 不寫 `label_value`、§G 分析時 golden）。

---

## COMPOSER-R8-P1-01

**斷言**: `scripts/gap3ux_pre_review.sh` 之 `FACTS` 仍指向 `handoffs/20260823-gap3ux-x-review-r7-facts.sh`，而 R8 brief／facts 已為 `…-r8-facts.sh` ⇒ 計數稽核閘掃描 stale receipt，與 R6/R7「加閘未同步清單」同型整合自傷。

**碼證**: `grep '^FACTS=' scripts/gap3ux_pre_review.sh` → `FACTS=handoffs/20260823-gap3ux-x-review-r7-facts.sh`；`ls handoffs/20260823-gap3ux-x-review-r8-facts.sh` 存在；`grep r7-facts scripts/narrow_check_router.sh` → 仍引用 r7。RECHECK：套用 gate-receipt 補丁後兩處皆為 r8。

**來源摘要**: scripts/gap3ux_pre_review.sh#01cf2468573f; handoffs/20260823-gap3ux-x-review-r8-facts.sh#01cf2468573f

[MAJOR] 信心度=High。不直接改壞 SPEC，但派審前閘可能漏掃 R8 facts 內新增字面，下一輪 fact-verified 不可信。修法：`handoffs/patches/20260823-gap3ux-r8-gate-receipt.md`。

---

## COMPOSER-R8-P1-02

**斷言**: brief fact-verified 宣稱「六支機械閘」（含 `patch_locus_check`），但 R8 `facts.sh` F-14 標題仍寫「五支」且只跑四支獨立腳本＋count_audit，未以 `gap3ux_pre_review.sh` 為唯一入口 ⇒ 與角色卡／brief 閘數敘述漂移（R7 群集 A 同型再現）。

**碼證**: brief L151「六支機械閘」；`handoffs/20260823-gap3ux-x-review-r8-facts.sh` L75 標「五支」；F-14 命令無 `gap3ux_pre_review.sh`、無 `patch_locus_check`；`bash scripts/gap3ux_pre_review.sh` 無參數時跳過 locus（預期行為，但 brief「六支」易誤讀為預設即六）。RECHECK：F-14 改跑 `gap3ux_pre_review.sh` 並更新標題為「五閘＋可選 locus」。

**來源摘要**: handoffs/20260823-gap3ux-x-review-r8-brief.md#01cf2468573f; handoffs/20260823-gap3ux-x-review-r8-facts.sh#01cf2468573f

[MAJOR] 信心度=High。違反「fact 全可重跑」之閘清單一致性；委員只信 F-14 會誤判 locus 閘狀態。修法：gate-receipt 補丁。

---

## COMPOSER-R8-P1-03

**斷言**: Task 7.6 邊界寫「不允許在 IC 頁修改批次設定」，與議題一裁定（答案窗為 IC 分析參數、應在 IC 頁給定）直接衝突；若只改 D-3 不改 7.6，Agent 會在 IC 頁只做唯讀揭露而無處設定 `horizon_bars`。

**碼證**: Task 7.6 L1416-1417「**不允許**在 IC 頁修改批次設定」；brief 議題一要求答案窗改由 IC 分析頁給定。RECHECK：7.6 邊界改為「五維度契約唯讀；分析參數（horizon 等）可於 IC 頁設定、不寫回匯出檔」。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f

[MAJOR] 信心度=High。架構調整後 IC 頁必須有分析參數 UI；現行禁令會阻擋合法實作路徑。修法：併入 arch-shift 補丁 Task 7.6 邊界段。

---

## Verdict：需修訂後定版

議題一之架構調整**成立**且應優先於 D-3(a) 落地；R7 十二條在**文字層**多數已 CLOSED，但群集 E 之 7.0b 須隨架構重寫。尚餘 **2×P0**（SPEC 未改寫架構；7.0b 錯層）＋ **3×P1**（gate receipt 漂移）。補丁包：`handoffs/patches/20260823-gap3ux-r8-arch-shift.md`、`handoffs/patches/20260823-gap3ux-r8-gate-receipt.md`。新 A-6 白話閘確認前不得 FROZEN。

---

ASSUMPTIONS_VERIFIED: SPEC sha256=01cf2468…51bd0、1580 行；`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh` rc=0；`bash scripts/gap3ux_pre_review.sh` 五閘 rc=0；議題一碼證（eventExport label vs label_value、ic_feed v1 註解、pipeline bars 入口）  
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md; wc -l`；`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh`；`bash scripts/gap3ux_pre_review.sh`；`grep FACTS= scripts/gap3ux_pre_review.sh`；`rg '15 增為 16|主答案窗' docs/GAP3_EVENT_UX_SPEC.md`  
FAILURES_SEEN: none（review-only）  
SCOPE_CHANGES: none（產出補丁包文字，未改 SPEC／碼）  
NUMERIC_OR_SCHEMA_IMPACT: 指出架構調整將改變匯出 schema（移除匯出端 `label_value`／`horizon_bars`）與 IC API 形狀；未實際改檔  

產出檔：`handoffs/20260823-gap3ux-x-review-r8-composer.md`；`handoffs/patches/20260823-gap3ux-r8-arch-shift.md`；`handoffs/patches/20260823-gap3ux-r8-gate-receipt.md`

STATUS: DONE
