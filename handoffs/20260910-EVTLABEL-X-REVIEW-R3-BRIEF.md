# EVTLABEL SPEC/TODO adversarial review R3（閉合輪；戳記另派序列化）

brief-kind: review
task-id: 20260910-EVTLABEL-X-REVIEW-R3
findings-round: R3
標的：`docs/EVTLABEL_SPEC.md`＋`docs/EVTLABEL_TODO.md` **v3**（commit `fe53734f`；尚未實作）
R1 收斂：`handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md`（C1–C14；body-hash `3894fd90…`）
R2 收斂：`handoffs/reconcile/20260910-evtlabel-x-review-r2/synth.md`（D1–D8；body-hash `194603b5…`）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`；findings 用 `## <FAMILY>-R3-P<0-3>-<NN>`。
本輪是**閉合輪**：逐條判 D1–D8 是否閉合；再攻 v3 新引入的三個設計（stage5 唯一守衛、20 次置亂 q95、顯式模式 fast-fail 預檢）。

## 🔴 給 Codex 的程序說明（回應 `CODEX-R2-P0-01`，收斂 D8）
- AGENTS.md Rule 12 之字面對象＝「**動工**前」；本輪是 SPEC review，**不動工**。本專案慣例（EVTALIGN R1→R2→R3→consult，見 `handoffs/reconcile/20260908-evtalign-x-review-r3/synth.md`）＝reconcile 於**凍結前**一次戳記，非每輪。
- 已為 R1／R2 synth 加 `## 戳記` 區；戳記將於本輪收斂後**序列化**派工（ORCH「同檔並發序列化」：codex→composer→grok 逐一 append，不並發寫同檔）。**本輪不要 append 戳記**。
- 🔴 Codex 於本輪須補做 R2 未做之實質審查：C1–C14 逐條判定、R2 必答 2a（X↔y 錯位反例）、3a（block L）、5a（負對照期望值）——composer／grok 已交，codex 之獨立判定仍是 quorum 必要條件。

## 🔴 本輪最重要的事
1. 主目標不得延後（SPEC §A 逐字）。
2. **D1 唯一守衛**（Task 3.6）：`X.index.equals(sel_idx)` ∧ `len(y)==len(X)` ∧ `all((owner[ts],ts,y_i) in vb.rows_frozenset)`，**無** digest 相等比對。請再構造一個能過此三條卻消費錯配的形狀（grok R2 之 `X.iloc[perm]` 已被斷言①擋）。
3. **D2 負對照校準**（Task 3.7）：20 次 block 置亂取 `q95(counts)`，`n_observed <= q95` ⇒ suppressed；consumable 放行仍靠 per-survivor block permutation。請攻：(a) 20 次是否足以估 q95（離散小整數分布）；(b) `<=` 在 `counts` 全 0、`n_observed=0` 時 ⇒ suppressed（倖存者 0 本就無可寫，是否該改 `n_observed==0 ⇒ 不判 suppressed、只記 no_survivors`）；(c) 成本 20×MW 於 39k×31。
4. **D3 block L**＝`max(1, ceil(W/max(1,min_gap)), ceil(W/median_gap))`：min_gap=1 時 L=W——受理 run（W=12、事件間距 ≥1 根 12h＝12 根 1h ⇒ min_gap=12）⇒ L=1；但**任兩事件相鄰一根**（12h 事件連續兩根）就把 L 拉到 12、n_blocks=165/12≈14——仍 ≥10。請算：受理批實際 min_gap 是多少（`data_cache/events/20260909T130533Z-7f73e4c7.json` 之 t0 差）、L、n_blocks。
5. **D4 預檢**：service 以「相同規則」預估 test 段——規則有兩處來源（orchestrator `_build_holdout_split_plan` 與 service 新函式），**會漂**。請判：是否應抽成 `momentum/core` 純函式供兩端共用（單一實作），或接受預檢只是 DX 早擋、以 stage3 為權威＋`preview_mismatch` 揭露。

## ⚠️ 前置說明
- **禁改碼、禁改文件、禁 append 戳記**。不得跑 `pytest tests/governance`。
- SPEC 引用之新檔尚不存在＝正常。既有紅：`EA-RESID-6`。

## 前提（逐條標）
fact-verified: R2 三家實跑——`series.to_numpy().flags.writeable=False` 後 `iloc[...]=` raise ValueError；`test_event_label_alignment.py:103` 鍵級 `==`（additive 不紅）；orchestrator `passed.remove` 計數 0；BH 獨立 null 模擬 P(R>0)≈0.03–0.07（grok）。
fact-verified: v3 相對 v2 之改動＝D1–D8（`git diff 9c4e9cb7..fe53734f -- docs/EVTLABEL_SPEC.md docs/EVTLABEL_TODO.md`）。
assumed: 20 次置亂足以估 q95 ← 否證觀測：同 seed_base 不同起點之 q95 差 ≥1。／我跑了：沒跑。
assumed: `n_observed <= q95` 的離散比較不會把「真倖存 3、null q95=3」誤殺 ← 否證觀測：null counts 常態達 3。／我跑了：沒跑（依 grok 模擬 E[R]≈0.07，q95 多為 0 或 1）。
assumed: 受理批之 min_gap ≥ 12 根 1h（事件週期 12h 不可能更密）← 否證觀測：同一 t0 重複或跨 symbol 混批。／我跑了：沒跑（本輪必答 4 請算）。

## 🔴 我沒查的
| claim | scope_ref | observable_if_false | recheck_cmd | reason_code | run_state |
|---|---|---|---|---|---|
| 20×MW 於 39k×31 之耗時 | Task 3.7 要點 4 | > 60s | 同形隨機矩陣 benchmark | cost | NOT_RUN |
| `_build_holdout_split_plan` 規則可否無副作用抽成純函式 | ic_filter_orchestrator.py:478-540 | 依賴 `config`／`features_df` 以外之狀態 | 讀碼 | cost | NOT_RUN |
| `sel_idx_ms → owner[ts]` 在 fallback（無切分）路徑之 owner 鍵集是否完整 | Task 3.4／3.6 | KeyError | 讀碼 | cost | NOT_RUN |

## 必答（成對）
1a. D1–D8 逐條 CLOSED／NOT-CLOSED＋v3 位置＋碼證。
1b. 有無處置與 v3 文件不一致者。
2a. D1 三條守衛之反例（能／不能）。 2b. 若能，補什麼；若不能，是否有多餘守衛可刪。
3a. 20 次置亂 q95 之統計充分性；`n_observed=0` 邊界之正確處置。 3b. 你的替代（含 N 與比較符）。
4a. 受理批 min_gap／L／n_blocks 實算。 4b. `n_blocks<10` 在受理批是否觸發；若觸發，這票交不出 consumable，你怎麼裁。
5a. D4 預檢規則之單一實作 vs 揭露式容忍，選哪個、為什麼。 5b. 若單一實作，函式簽名與落點。
6. ≥10× 不必要複雜（固定必問）。
7. **Codex 補做**：C1–C14 判定＋R2 必答 2a／3a／5a（composer／grok 已交者可只標「同意／不同意＋理由」）。
8. 可否凍結 P3 並進 B0？P1／P2 已由 R2 兩家判可凍結，codex 請表態。

## 驗收命令
```
bash scripts/template_check.sh spec docs/EVTLABEL_SPEC.md
bash scripts/template_check.sh todo docs/EVTLABEL_TODO.md
bash scripts/completeness_check.sh --lock handoffs/reconcile/20260910-evtlabel-x-review-r2/sources.lock
```

## 停輪條件（可列完）
① 必答 1a 對 D1–D8 每條有 verdict。② 必答 2a／3a／4a 有反例或實算。③ 必答 8 三家皆有明確表態（含 codex 之 C1–C14 補做）。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改文件、禁 append 戳記**。收尾清 /tmp workdir（保留 claude-501）。
