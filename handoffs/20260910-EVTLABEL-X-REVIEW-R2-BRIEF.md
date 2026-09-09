# EVTLABEL SPEC/TODO adversarial review R2（閉合輪）

brief-kind: review
task-id: 20260910-EVTLABEL-X-REVIEW-R2
findings-round: R2
標的：`docs/EVTLABEL_SPEC.md`＋`docs/EVTLABEL_TODO.md` **v2**（commit `9c4e9cb7`；尚未實作）
R1 收斂檔：`handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md`（C1–C14，27 條全採納）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 執行；findings 用 canonical ID `## <FAMILY>-R2-P<0-3>-<NN>`。
本輪是**閉合輪**：先逐條判 R1 之 C1–C14 是否真的閉合（CLOSED／NOT-CLOSED＋碼證），再攻 v2 新引入的設計。

## 🔴 本輪最重要的事

1. **主目標不得延後**（SPEC §A 逐字）——同 R1，不再重述；提議延後 P3 ＝ 主委呈使用者否決點。
2. v2 把三個決策點搬了位置，請攻**搬錯位置**與**新縫隙**：
   - `auto` 之 effective mode 現在在 **orchestrator stage3**（切分已知後）決定（C2）；service 只送 map＋值域閘（C14c）。
   - binary 向量以 `ValidatedBinaryLabel(series, digest, rows_frozenset, …)` 交付，stage5 消費前對 selection 子集逐筆 `in` 對證（C4）。**請構造能通過對證卻消費錯資料的反例。**
   - P2 列數改走顯式 kwarg `analyze(..., event_isolation=EventIsolationRows)`，`config_override` 出現該鍵 ⇒ 入口 raise（C8）。
3. 統計設計 v2：效應量閘＝`abs(rank_biserial) >= rank_biserial_min(0.10)`（C1）；p＝MW→BH；倖存者以 **block permutation**（`L = max(1, ceil(label_window_feature_bars / median_event_gap_rows))`，`n_blocks<10 ⇒ unavailable`）重驗（C10）；負對照非零 ⇒ survivor **suppressed**（C3）；置換預算 `n_perm = clamp(200000//K, 200, 1000)`（C14a）。

實作者（Claude）**不自審**。

## ⚠️ 前置說明（勿誤 block）
- **禁改碼、禁改文件**。**不得**跑 `pytest tests/governance`。
- SPEC 引用之新檔（`binary_discrimination.py`、`event_label_mode.json`、`tests/*evtlabel*`、`scripts/evtlabel_phase_gate.sh`、`handoffs/20260910-evtlabel-mutate.py`、`tests/golden/evtlabel/*`）尚不存在＝正常。
- 既有紅：`EA-RESID-6` 四條 golden。

## 本 brief 前提（逐條標）

fact-verified: R1 之三家實跑皆重現 ASSUME-1（probe rc=0）、ICConfig 未知鍵靜默丟、test 段 17/14。
fact-verified: `_assert_event_triple_bound` 現行對 `label_source != "event_label_value"` early-return（`api/services/ic_analysis_service.py:133-135`）——v2 Task 3.3 要點 5 改為依 source 分派。
fact-verified: `_is_event_conditional_consumed` 只認 `event_label_value`（`ic_filter_orchestrator.py:3262-3281`）——v2 Task 3.1 要點 4 以 `is_event_label_consumed` 取代所有呼叫點。

assumed: **block permutation 之 block 定義**（依時間序每 L 個事件一 block，L 由 label 視窗／事件間距中位數導出）足以吸收重疊 label 視窗造成的依賴
← 否證觀測：構造 L 依中位數算為 1、但存在一段密集事件（間距 < 視窗）之 fixture，置換 null 仍過窄（p 偏小）。／我跑了：**沒跑**（設計判斷，請正面攻；替代＝依實際重疊圖分 block、或 max 間距而非中位數）。

assumed: `rows_frozenset` 子集 `in` 對證＋digest 足以保證「驗了＝用的」
← 否證觀測：selection 子集之 `(eid, ts, y)` 全部 ∈ 驗證集合，但子集之**列順序／feature 對應**被換（X 列與 y 錯位而三元組仍合法）。／我跑了：沒跑。🔴 這是 C4 閉合與否的關鍵，請構造。

assumed: `rank_biserial_min=0.10`（AUC 0.55）作為預註冊效應量門檻在 selection 段 ~31 事件下不會把真訊號殺光
← 否證觀測：null SE(rb)≈0.24（grok R1 估）⇒ 0.10 仍近 no-op；或反之真訊號 rb 常 <0.10。／我跑了：沒跑；接受委員給出替代值＋理由。

assumed: stage6b 標 `diagnostic` 且「不得移除 binary 倖存者」可用雙特徵 fixture 機械驗
← 否證觀測：stage6b 之 composite 路徑有別的副作用（如改寫 `passed` 順序或 survivor 欄）未被 fixture 覆蓋。

## 🔴 我沒查的

| claim | scope_ref | observable_if_false | recheck_cmd | reason_code | run_state |
|---|---|---|---|---|---|
| `validate_event_given` 回傳加 `consumed_event_rows` 後，既有測試對回傳 dict 用 `==` 全等比對而紅 | tests/momentum/**/test_*event_given* | 既有測試紅 | `grep -rn "consumed_event_labels" tests \| grep "==" ` | cost | NOT_RUN |
| `series.flags.writeable=False` 在 pandas Series 上是否真能阻止 in-place 寫 | Task 3.4 要點 4 | `vb.series.iloc[0]=1` 不 raise | 小 python 探針 | cost | NOT_RUN |
| stage6b（`:4609-4649`）是否有路徑會 `passed.remove(...)` | ic_filter_orchestrator.py stage6b | 雙特徵 fixture 之 A 被移除 | 讀碼 | cost | NOT_RUN |
| `pattern_bridge` `survivor_v2` 入口對 suppressed stub 之現行行為（raise／回空） | momentum/Analysis/event_samples/pattern_bridge.py:52-105 | Task 3.11 邊界①② 寫反 | 讀碼＋小探針 | cost | NOT_RUN |
| 前端 `ICSummaryTable` 分頁（ICRESULT_PAGING）對新增 9 欄之 size budget | frontend paging + api size gate | budget 紅 | B5 實跑 | cost | NOT_RUN |

## oracle-artifact
- R1 收斂檔：`handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md`
- 前提探針：`handoffs/20260910-probe-label-rule.py`
- 受理 run 報告：`data_cache/reports/ic_report_ic_gatekeeper.json`

## 必答（逐條 verdict；成對）

1a. **C1–C14 逐條閉合判定**：每條 CLOSED／NOT-CLOSED，附 v2 之對應位置（Task 編號＋要點）與碼證。
1b. 有無 R1 finding 被「處置」成**語意不同**的東西（即 synth 寫的處置與 v2 文件實際寫的不一致）？

2a. **C4 反例**：構造「三元組全部 ∈ `rows_frozenset`、digest 相符，但 stage5 實際消費的 `(X 列, y)` 配對是錯的」。能不能？
2b. 若能，正確的綁定應該綁什麼（列索引？feature index token？）；若不能，說明為何 `in` 對證已足。

3a. **block permutation**：L 由中位數導出對「密集事件段」是否失守？請給反例或證明。
3b. `n_blocks < 10 ⇒ unavailable` 這個 10 的依據；受理 run（165 事件、L=1）下 n_blocks=165 無虞，但 h=12 o2hc（視窗 156 根＝13 個 12h）事件間距中位數若 ≈ 1 根 ⇒ L=13 ⇒ 全批只 ~12 個 block——是否等於 binary 模式在長視窗下**永遠 unavailable**？若是，這是正確的保守，還是設計缺陷？

4a. **auto 決策搬到 stage3**：service 不再知道 effective mode，`_inject_label_rule_disclosure`／`_inject_label_mode`／`_assert_event_triple_bound` 改讀 `event_info`——有沒有 service 端在 analyze **之前**就需要知道 mode 的地方（掃描格 400、UI 預覽）被搬壞？
4b. 顯式 `imported_binary` 在 stage3 才 raise ⇒ 使用者要等 preprocessing（11 分鐘）才看到 422。這是可接受的取捨，還是該在 service 用「預估 test 段」先擋？（R1 三家意見分歧：composer 建議預模擬 split，codex 建議切分後判。）

5a. **負對照 fail-closed 之副作用**：`n_survivors_shuffled>0` 在 39k 特徵、BH α=0.05 下的**期望值**是多少？若期望值本就 >0（多重檢定下置亂仍可能有 1–2 個假陽性通過 q≤0.05），則 suppressed 會**常態觸發**，binary 模式永遠交不出 survivor。請算或估。
5b. 若 5a 成立，正確設計是什麼（例：負對照以 `n_survivors_shuffled > ceil(α·n_tests·k)` 為門檻、或多次置亂取分位、或負對照只作揭露而 per-survivor 置換作放行）？**注意這與 C3（codex R1 P0）直接衝突，請三家明確表態。**

6a. `rank_biserial_min=0.10`：給你的值與理由，或說明「只用 p 閘＋置換」為何較對。
6b. `min_events_per_class=10`（selection 段）：維持或改？理由。

7. 有無 ≥10× 不必要複雜（固定必問）：特別看 `rows_frozenset`＋digest 雙重對證、block permutation、Task 3.11。

8. 可以進 B0/B1 實作嗎（P1 與 P3 設計是否已可凍結）？若 P3 仍有 BLOCKING，P1／P2 可否先凍結動工（Phase 順序不變）？

## 驗收命令
```
bash scripts/template_check.sh spec docs/EVTLABEL_SPEC.md
bash scripts/template_check.sh todo docs/EVTLABEL_TODO.md
bash scripts/completeness_check.sh --lock handoffs/reconcile/20260910-evtlabel-x-review-r1/sources.lock
```

## 停輪條件（可列完）
① 必答 1a 對 C1–C14 每條有 verdict。
② 必答 2a／3a／5a 各有明確結論（反例或證明）。
③ 必答 5b 三家對「負對照 fail-closed vs 揭露」明確表態。
④ 本輪 P0／P1 皆指出 SPEC/TODO 對應修訂位置。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改文件**。收尾清 /tmp workdir（保留 claude-501）。
