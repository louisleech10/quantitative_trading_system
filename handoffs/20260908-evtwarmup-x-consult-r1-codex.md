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
