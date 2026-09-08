# Reconcile — 20260908-evtwarmup-x-consult-r1

**來源** 20260908-evtwarmup-x-consult-r1-codex.md, 20260908-evtwarmup-x-consult-r1-composer.md, 20260908-evtwarmup-x-consult-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**本輪性質**：consult（量化規則裁定），三家各交 `P3-00` sentinel；重點在必答 1–6 與 Verdict 行。三家 §0 皆獨立實讀碼證，
grok 另實跑 `ICConfig().ic_calculation.model_dump()`（無 `timeframe` 鍵；手塞 `1h` → `[252,756,1512]`）。

### W1 — 規則錯置成立且有害（三家一致，信心 High）
126 是連續 K 線視窗；stage3 後只剩事件列，門檻「131 列」實際＝「測試段 131 個事件」；使用者 34 事件 ⇒ 幾乎必然 full-sample、失去 OOS。
**非資料不足，是單位錯置。** brief 之 assumed「事件 rolling 決策價值低」被三家**推翻**：`icir_min`（stage5 `:4248`）與 stage6 冗餘真實消費 ICIR。

### W2 — 事件模式 OOS 之定義（三家一致）
holdout 仍在 **K 線時間軸**切最後 20%（purge／embargo 不動、預處理只 fit train）；條件 IC＝**測試段事件上的 pooled 點 IC＋HAC／FDR**；
**不以 bar-rolling warmup 作 OOS 門檻**。事件模式之 rolling／ICIR 只作明示診斷或 `unavailable`，**不得**再以 `icir_min` 硬篩（否則豁免 warmup 後
ICIR 全 NaN → 全滅，grok／composer 4b 同指）。測試段事件數另設統計地板 `min_test_events`（建議 30；codex 提醒 30/100/200 只是 tier 非證明，
以 HAC p／FDR 表達不確定性）；不足 ⇒ **loud** `oos_guarantees=false`／reason `insufficient_test_events`，禁再改算 full-sample 假裝 holdout。

### W3 — `_adjust_rolling_windows` 從未生效（三家一致：另票）
orchestrator 建引擎只傳 `ic_calculation.model_dump()`，無 timeframe ⇒ 12h 設計的 [21,63,126] 直接套 1h。修＝接線 `metadata.timeframe`，
1h 變 [252,756,1512]、warmup 1517 ⇒ **全域 IC 數值語意變更（RISK a/d）**，需獨立 golden 與裁定，**禁夾帶**進本修法。
不修只揭露＝**尺度假 ICIR**（三家同判）：短期報告須標 `window_unit=bars_unadjusted`／`timeframe_adjustment=not_applied`。

### W4 — 最小修法（三家同形）
分流鍵＝**產生者標記** `label_source=event_label_value`／`sample_scope_kind=event`（codex：只看 `event_filter.enabled` 會讓主線 label 逃掉 bar gate），
於 `_precheck_rolling_warmup` 與 stage4 安全網跳過 bar warmup；改用 `min_test_events`；stage5 事件路徑跳過 `icir_min`（主閘＝ic_mean／HAC p／FDR）；
stage6 tiebreaker 無 ICIR 走既有 fallback 鍵並釘測試。全域路徑一字不改。測試：34 事件正例、低於地板反例、global golden 不變、mutation「刪豁免 ⇒ 34 事件再 fallback」。
scan cube 事件格由「幾乎必 degraded」變「可 holdout」＝預期修正，格契約字串同步。

Verdict: 可合併——採三家一致之「事件路徑豁免 bar-rolling warmup／ICIR 硬門檻，OOS＝K 線 holdout 上之測試段事件 pooled IC＋HAC，
`min_test_events` 統計地板 loud 揭露；timeframe 接線另票」。實作走中任務管線（SPEC＋TODO＋adversarial；命中 RISK d）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P3-00

**斷言**: 本輪為 consult，無 findings；裁定如下，且所有量化主張均以 HEAD `8f10d2e1` 的碼證核對。

**碼證**: `ICFilterOrchestrator.__init__`（`ic_filter_orchestrator.py:985-990`）只傳 `config.ic_calculation.model_dump()`；`_adjust_rolling_windows`（`ic_engine.py:1333-1345`）無 timeframe 即原樣回傳；`_precheck_rolling_warmup`／stage4（`ic_filter_orchestrator.py:3196-3219,3495-3515`）以事件列數套 `max(window)+horizon`。實跑 `rg` 顯示 rolling ICIR 進 summary（:3552,3773-3781,4182-4198）並由 `icir_min` 篩選（:4248-4250）；既有 timeframe 測試只直接建構帶 timeframe 的 `ICEngine`（`tests/momentum/test_ic_engine.py:56-70,421-429`）。

**來源摘要**: `handoffs/20260908-EVTWARMUP-X-CONSULT-R1-BRIEF.md#80a350b48d20`；`momentum/Analysis/ic_filter_orchestrator.py#644bd066457d`；`momentum/Analysis/ic_engine.py#da4521cf2b82`；`docs/IC_QUANT_GAP_REGISTRY.md#cce4be593a2d`。

本輪為 consult，無 findings。

1a. 規則錯置成立且有害：126 是連續 K 線 row window；stage3 後的 `event_label_value` 序列只有測試段事件列，34<131 遂觸發 full-sample fallback，失去 OOS；126 事件的時間跨度也不固定，故不是原設定的 bar-time warmup。

1b. 反例成立：若 estimand 明確是「最近 N 個事件」、事件頻率高且事件序列才是抽樣單位，event-count rolling 可正確；但它必須另標 event-time、揭露事件涵蓋時間，不能冒充 K 線 rolling。高頻一事件一 bar 只是特殊情況。

2a. 可行：先在完整、連續 K 線上做最後 20% holdout＋label-horizon purge/embargo，再用 timestamp/key mask 取測試事件，conditional IC/HAC/FDR 只消費 test events。現有切分先於 stage3（`:1086-1127`）且 stage3 後重導 mask（`:1209-1221`），可保留；preprocess 仍只 fit train。事件數不足時回 `conditional_ic unavailable/degraded`，不得改算 full-sample 後宣稱 OOS。

2b. 保留 rolling 時：event-time estimand 用事件數，calendar-time estimand 用事件 timestamp 的時間跨度；不可用 K 線數映射稀疏事件。最小可用事件數應由目標效果量、alpha/FDR、power 與 HAC/自相關得到 `n_eff`、CI 或 power gate；現有 30/100/200 僅 tier（`event_filter.py:183-195`），不能直接當統計證明；`:125-127` 的 HAC floor 也只是計算可行性。

3a. 應修，但另開裁定／批次：`ICConfig` 的 `ICCalculationConfig` 沒有 timeframe（`ic_config_schema.py:78-88`），故 1h run 不會用 `reference_tf=12h` 換算。若該設定的語意是固定時間跨度，修後窗口為 `[252,756,1512]`；horizon=5 時現行 warmup 實際為 1517，不是 1512。這會改 global 1h 的數值、warmup、耗時與 golden，需獨立 baseline/golden，不與事件修法綁定。

3b. 只揭露不修不足以誠實：結果數學上仍是 63 個 1h row 的 ICIR，但若報告契約宣稱 12h reference，selection 使用的是錯尺度 ICIR，屬語意上的假 ICIR；揭露不能修正門檻或選擇。

4a. 一批最小方案：以 `label_source=event_label_value`／`sample_scope_kind=event` 作唯一分流；只在該分流跳過 bar rolling warmup，保留原 holdout、purge、train-fit；以 test-event pooled IC＋既有 HAC/FDR 作 conditional selection，rolling/ICIR 僅診斷或明確 not_applicable；不足則 loud unavailable/degraded。測試含 34-event 正例、低於統計 gate 反例、train 擾動不變、global/no-event byte golden 不變、event label 三元組不洩漏；另為 1h timeframe wiring 寫 `[10]→[120]`/`[21,63,126]→[252,756,1512]` 的獨立測試。事件報告 golden/schema 必須明載預期變更，global golden 不變。

4b. 新誤擋／新漏：分流若只看 `event_filter.enabled` 會讓 mainline label 逃掉 bar gate，故必綁實際 `label_source`；若不設 event statistical gate，會放行 underpowered IC。若 110 格 scan cube 各格事件數不同，逐格保留 capability/status，Tier A/B 不共用判定；現有 `scan_cube.py:16-17,199-232` 已以逐格實測 rows/bytes fail-closed，修後應重跑 110 格並更新受影響的 event golden/byte receipt。

5. 無 ≥10× 複雜度必要性：不需把稀疏事件 label 展開成 K 線、另造一套 rolling engine，或為每格建新時間軸；一個 label-source 分流＋既有 pooled/HAC/FDR 足夠，timeframe wiring 獨立小變更。

Verdict: 採「事件 conditional IC 只在 test events 做 pooled/HAC，bar rolling warmup 不作 gate、rolling 只作明示診斷；timeframe 傳遞另票修正」，因為現行 126 bar 規則套在 34 稀疏事件列造成非資料不足的 full-sample fallback，而直接放寬全域 gate 會製造 OOS 漏洞。
## COMPOSER-R1-P3-00

**斷言**: 本輪為 consult（非 adversarial review），逐項核對 brief 必答 1–6 與四條碼證後**無獨立實質 finding**；規則錯置與 `_timeframe` 未注入已由讀碼確認，裁定收斂於「事件模式 bypass K 線 rolling warmup 門檻 + timeframe 修正另票」。

**碼證**: ① `sed -n '3184-3221p;3496-3515p' momentum/Analysis/ic_filter_orchestrator.py` — warmup 與 stage4 skip 同一規則、事件預檢以 test 段事件列計數；② `sed -n '988p;3327-3350p' momentum/Analysis/ic_filter_orchestrator.py` — engine 無 timeframe、stage3 稀疏化；③ `sed -n '1333-1345p' momentum/Analysis/ic_engine.py` — `_timeframe` None 時 early return；④ `grep -n "icir_min" momentum/Analysis/ic_filter_orchestrator.py` → `:4248` stage5 門檻仍讀 rolling 衍生 summary。

**來源摘要**: handoffs/20260908-EVTWARMUP-X-CONSULT-R1-BRIEF.md#consult-r1; momentum/Analysis/ic_filter_orchestrator.py#644bd066457d; momentum/Analysis/ic_engine.py#da4521cf2b82; config/ic_config.yaml#b2c5917df9ee

---

## GROK-R1-P3-00

**斷言**: 本輪為 consult，無 findings；逐項核對 brief 碼證與「我沒查的」三列後，裁定寫於下方必答 1–6 與 `Verdict:`，不另開實質 finding。

**碼證**: 實讀 `ic_filter_orchestrator.py` `_rolling_warmup_min_rows`／`_precheck_rolling_warmup`／`_stage3_event_filter`／`_stage4_ic_calculation`／`_apply_thresholds`；`ic_engine.py` `__init__`／`_adjust_rolling_windows`；`ICConfig().ic_calculation.model_dump()` 無 `timeframe` 鍵（實跑見下）；`git rev-parse --short HEAD` → `8f10d2e1`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#644bd066457d

本輪核對依據：使用者 log 形狀（`test_rows=34`／`min_test_rows=131`）與預檢以「測試段 ∩ 事件時間戳」計數列一致；規則錯置成立；ICIR 門檻有真實消費者；TF 換算未接線屬另票。

---

