# EVTWARMUP consult R1 — grok（量化正確性裁定）

TASK_ID: 20260908-EVTWARMUP-X-CONSULT-R1  
brief-kind: consult  
family: grok  
findings-round: R1  
標的 commit: `8f10d2e1`（HEAD 對證）  
SCOPE: consult／規則裁定；**禁改碼、禁改文件**；未跑 `pytest tests/governance`

---

## GROK-R1-P3-00

**斷言**: 本輪為 consult，無 findings；逐項核對 brief 碼證與「我沒查的」三列後，裁定寫於下方必答 1–6 與 `Verdict:`，不另開實質 finding。

**碼證**: 實讀 `ic_filter_orchestrator.py` `_rolling_warmup_min_rows`／`_precheck_rolling_warmup`／`_stage3_event_filter`／`_stage4_ic_calculation`／`_apply_thresholds`；`ic_engine.py` `__init__`／`_adjust_rolling_windows`；`ICConfig().ic_calculation.model_dump()` 無 `timeframe` 鍵（實跑見下）；`git rev-parse --short HEAD` → `8f10d2e1`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#644bd066457d

本輪核對依據：使用者 log 形狀（`test_rows=34`／`min_test_rows=131`）與預檢以「測試段 ∩ 事件時間戳」計數列一致；規則錯置成立；ICIR 門檻有真實消費者；TF 換算未接線屬另票。

---

## §0 挑戰前提

| 宣稱 | 判定 | 本家複驗 |
|---|---|---|
| 門檻＝`max(adjust([21,63,126]))+horizon`＝131（列數） | **fact-verified** | `_rolling_warmup_min_rows` `:3184-3187`；`ICConfig().min_test_rows` 預設亦 131 |
| 事件 stage3 把列濾成事件列；stage4 test 切片＝測試段事件列 | **fact-verified** | `_stage3_event_filter` `:3326-3331` `.loc[selected_index]`；analyze `:1209-1216` 重算 mask；stage4 `:3496-3504` `len(features_for_ic)<min_required` |
| `ICEngine(config.ic_calculation.model_dump())` 無 timeframe ⇒ 視窗不換算 | **fact-verified** | schema `ICCalculationConfig` 無 `timeframe` 欄；實跑 dump keys 無該鍵；`engine._timeframe is None`；`adjust([21,63,126])→同列`；手動塞 `timeframe=1h` → `[252,756,1512]` |
| assumed：事件 rolling IC 對決策價值低於全樣本條件 IC | **assumed → 推翻（對篩選路徑）** | stage5 `_apply_thresholds` `:4248-4249` 用 `thresholds.icir_min`（預設 0.5）砍特徵；stage6 亦吃 `ic_results["icir"]`。fallback 後仍算 rolling／ICIR 並進門檻 ⇒ **有消費者** |
| 歷史裁決「rolling＝列數非根數」 | **unverified→本輪未找到** | `docs/SCAR_LEDGER.md`／`docs/*IC*` 之 warmup 敘事屬 FR／LA0／PIT，非本 IC rolling 視窗單位裁決；`reference_tf:"12h"` 反而暗示**應**依週期換算連續 bar |

### 本輪實跑（非 governance）

| 命令 | 結果摘要 |
|---|---|
| `git rev-parse --short HEAD` | `8f10d2e1` |
| `ICConfig().ic_calculation.model_dump()` + `ICEngine(...)._adjust_rolling_windows` | dump 無 `timeframe`；預設 adjust 恆等；`timeframe=1h` → `[252,756,1512]` |
| `shasum -a 256` 三檔 | orchestrator `#644bd066457d`；engine `#da4521cf2b82`；schema `#685cc03ad426` |

---

## 必答 1–6

### 1a. 規則錯置是否成立？

**成立（有害）。** 信心度=High。

連續 K 線設計的 `window_126` 假設相鄰列≈固定時間步。事件列經 stage3 變稀疏後，同一視窗變成「最近 126 **個事件**」，時間跨度不定；warmup 門檻卻仍要求測試段 ≥131 **事件列**。使用者實機：測試段 K 線約 20%（數千根）遠超 131，但測試段事件只有 34 → 觸發 `rolling_warmup_insufficient` → 幾乎必降級 full-sample。這是規則錯置，不是資料不足。

### 1b. 反面：何時「以事件數計的 rolling」反而對？

有，但須**顯式 estimand**，不能默認套用現窗：

1. **高頻／近稠密事件批**（事件間隔≈1 根或固定少數根）→ 事件序≈時間序，單位近似可互換。  
2. **研究問題本就是「跨相繼事件的 IC 穩定度」**（event-order ICIR）→ 視窗應另定（常見數十事件級），並在報告標 `window_unit=event_count`，**不得**沿用 `[21,63,126]`＋`reference_tf=12h` 的 bar 語意。

對本 UAT 量級（~170 事件、測試段 ~34）即使改成「事件數視窗」，預設 126 仍不合理；1b 不能為現行行為辯護。

### 2a. 事件模式 OOS 該怎麼定？

**可行且應採：** holdout 仍切最後 20% **K 線時間**（現有 `oos_test_size`／purge／embargo 不動）；stage3 後 mask 重投影到事件列；條件 IC（點估計＋HAC／FDR）**只在測試段事件**上算；**不**用 bar-rolling warmup 當 OOS 門檻。

洩漏風險（須守、非否決）：

| 風險 | 處置 |
|---|---|
| 特徵看未來 | 既有 PIT／對齊契約；本裁定不放寬 |
| 事件 label 非 forward-return | `label_source=event_label_value` 已是橫截條件 IC；OOS＝「未來事件」上的可泛化，不是 bar-path return OOS |
| 測試段事件過少 → 檢定力不足 | 另設 `min_test_events`（統計地板，見 2b）；不足 → **loud** `oos_guarantees=false`／ICIR unavailable，**不要**默默改估計量還假裝 holdout |
| 事件時間叢集在尾端 | 揭露 `test_rows`（事件計）；不改切分定義 |

### 2b. 若保留 rolling，單位與最小事件數？

若保留，視窗單位優先序：

1. **時間跨度**（或等價的 K 線數映射後再對事件時間戳取窗）— 與 `reference_tf` 設計一致；  
2. **顯式事件數** — 僅當 estimand＝event-order，且 defaults 重訂；  
3. **禁止**繼續用「為 12h bar 寫的 126」直接當事件列數。

最小可用事件數（統計依據，非拍腦袋）：

- **點條件 IC（Spearman）**：粗 SE≈`1/sqrt(n-1)`。要讓 `|IC|≈0.1` 與噪聲有粗區隔，n 需數百量級；實務篩選軟地板常取 **n≥30**（CLT／相關估計經驗下限），並靠 HAC p／FDR 表達不確定性，而非用 rolling warmup 偽裝樣本充足。  
- **Rolling ICIR**：還要 `n ≳ window + 足夠窗端點估 σ(IC)`；在測試段只有 O(10¹) 事件時，**統計上不該產出可門檻化的 ICIR** → 應標 unavailable，而不是用 126 去擋整條 OOS。

本票建議：**事件模式預設不算／不門檻 rolling ICIR**；OOS 主錨＝測試段事件上的點 IC＋HAC。

### 3a. `_adjust_rolling_windows` 從未生效：修了對全域 1h 的影響？

**裁定：另票修，不併進本 warmup 小修。**

碼證：production `ICEngine(config.ic_calculation.model_dump())`（`:988`）永遠吃不到 run `metadata.timeframe`；schema 亦無該欄。引擎單測 `test_rolling_window_adjustment_by_timeframe` 在**手動**傳 `timeframe=4h` 時預期 `window_30`（10×3）——證明函式本身可用，是接線缺失。

若在 orchestrator 接上 `1h`：`[21,63,126]→[252,756,1512]`，warmup≈1512＋horizon。對本次 ~20k 根 1h、測試段數千根**可能仍過得了**，但會：

- 改全域 rolling／ICIR **數值語意**（RISK a/d）；  
- 打紅依賴未換算窗鍵的測試（例 `test_oos_ic_rolling_warmup` 斷言 `window_5`）；  
- 縮短歷史／更大 factor 的 run 新誤擋面上升。

⇒ **可接受為正確化方向，但必須另票**（golden＋呼叫點接 `metadata.timeframe`＋分階段），禁止夾帶在事件 warmup 熱修裡靜默 12×。

### 3b. 不修、只揭露「未依週期換算」＝假 ICIR？

**對「宣稱／暗示已按 `reference_tf` 換算」的 ICIR：是（尺度假）。** 不是捏造亂數，而是**錯尺度仍當可比較的 ICIR 門檻**（`icir_min=0.5`）。只揭露而不改數值／門檻＝使用者仍可能用錯尺度做篩選。短期可接受的誠實態：報告寫死 `window_unit=bars_unadjusted` + `timeframe_adjustment=not_applied`，且 ideally **放寬或停用**把未換算 ICIR 當硬門檻——仍次於另票真正接線。

### 4a. 最小修法（本票範圍；優先不動全域 IC 數值語意）

**方案名：事件路徑豁免 bar-rolling warmup，OOS 改以測試段事件點 IC 為主（E）。**

一批內可落地：

1. **預檢／stage4 安全網**：當本次為事件條件 IC 路徑（`event_timestamps` 非空且 filter 將／已產出事件列；或 `event_info.sample_scope_kind=="event"`／`label_source=="event_label_value"`）→ **跳過** `max(rolling_windows)+horizon` 之 `rolling_warmup_insufficient` fallback。  
2. **改用** `min_test_events`（建議預設 30，config 可調；不足 → 保留 holdout 計算點 IC，但 `oos_guarantees`／rolling／ICIR 標 unavailable 或降級理由改為 `insufficient_test_events`，**禁止**再走「假裝資料不夠所以 full-sample」除非事件總數也低於絕對下限）。  
3. **門檻**：事件路徑 `_apply_thresholds` **跳過 `icir_min`**（或上游令 `icir` 全 NaN 且 removed 不計 icir）；主閘改 ic_mean／HAC p／FDR 等仍適用者。stage6 tiebreaker 若無 ICIR 則走既有 fallback 鍵（`ic_mean` 等）——須單測釘死。  
4. **全域／非事件路徑**：一字不改（含未接線的 TF adjust）。

測試策略：

- 單元：`_precheck_rolling_warmup` 在 `event_timestamps` 使 test 事件數=34、windows 含 126 時 **回 None**（不再 details）。  
- stage4：事件列稀疏＋holdout mask 不回 `skipped/INSUFFICIENT_DATA`。  
- stage5：事件路徑 summary 可缺／NaN icir 且**不**因 `icir_min` 全滅。  
- 回歸：無事件／全域路徑既有 warmup／fallback 行為位元組或既有測試不變。  
- mutation：把豁免條件刪掉 → 34 事件再變 fallback。  

Golden 影響：事件 UAT／會走 fallback 的事件報告 metadata（`fit_mode_source=fallback`、`degraded_full_sample`）會變；**須更新事件路徑 golden／契約測試**。全域 IC golden **不應**動。SCANCUBE 事件格：由「幾乎必 degraded」變「可 holdout OOS」——屬預期修正，格契約若寫死 fallback reason 要同步。

### 4b. 新誤擋／新漏？

| 風險 | 評估 |
|---|---|
| 只豁免 warmup、仍用 126 窗算 ICIR 再套 `icir_min` | **新誤擋**（ICIR NaN／窗不足 → 全滅）⇒ 4a 步驟 3 必搭配 |
| 測試事件&lt;30 仍報高信心 OOS | **新漏** ⇒ 要 `min_test_events`＋揭露 |
| fallback 一槍 guard | 事件路徑不再因 warmup 進 fallback ⇒ 較少踩；guard 邏輯可留 |
| scan cube 110 格 | 非事件格無感；事件格 status／reason 字串可能變 → 對契約測試，非整格數值語意 |
| 與「另票 TF 換算」交互 | 本方案不接 TF，避免 1512 誤擋夾帶 |

### 5. ≥10× 不必要複雜？

**無。** 不要在本票做：事件時間窗重寫引擎、密度自適應窗、同時接上全域 TF 換算、新分散式／queue。E 是呼叫點門閘＋門檻分流，複雜度約 1×。

### 6. Verdict

**Verdict: 採方案 E（事件路徑豁免 bar-rolling warmup／ICIR 硬門檻，保留 K 線 20% holdout 上的條件點 IC＋HAC；`_adjust_rolling_windows` 接線另票），因為現行 126 列門檻在稀疏事件上量化無意義且幾乎強制 full-sample，而 ICIR 仍被 `icir_min` 真實消費——錯的是規則單位，不是資料量。**

---

## 被當成事實的未驗證假設（§0）

1. brief assumed「事件 rolling 決策價值低」→ **本輪否證**：`icir_min`＋stage6 消費 ICIR（見上）。  
2. 「歷史已裁 rolling＝列數」→ **未找到**；`reference_tf` 指向相反設計意圖。  
3. 「另票接 TF 後 1h warmup=1512 對所有全域 run 可接受」→ **assumed**；本家只確認公式與本機 20k 根情境，不在本票批准全域語意翻轉。

STATUS: DONE
