# EVTLABEL SPEC/TODO adversarial review R1

brief-kind: review
task-id: 20260910-EVTLABEL-X-REVIEW-R1
findings-round: R1
標的：`docs/EVTLABEL_SPEC.md`＋`docs/EVTLABEL_TODO.md`（**尚未實作**；commit `ef9ef522`）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提、§1 十一類、必答成對）。
findings 用 canonical ID：`## <FAMILY>-R1-P<0-3>-<NN>`（FAMILY ∈ CODEX／COMPOSER／GROK）。

## 🔴 本輪最重要的事（兩件）

1. **使用者主目標不得被延後**（SPEC §A 逐字）：
   > 「我在外面標好正反例（標的＋t₀＋0/1 標籤）匯入，平台找出 t₀ 之前哪些特徵能把正反例分開，再把這些特徵餵 ML。」
   這是本票第二次被規則擠掉後由使用者親自裁定的順序（P1→P2→P3，順序不可調）。
   你可以攻 P3 的**做法**（統計量、門檻、契約、假綠），**不得**提議「P3 另開票／先做別的」——那類 finding 主委會直接呈使用者否決點，不會由我吸收。
2. **P3 是把 0/1 標籤接進 IC gatekeeper 主線**（`ic_filter_orchestrator.py` stage3/stage5/thresholds），不是在 event_samples 側做一張表。
   請以「這樣接會不會讓 `return_rule`／全域路徑逐位元組變動」（G-1／G-4）與「binary 統計會不會被既有門檻（`ic_mean_min`／`icir_min`／`p_value_adj`）錯誤消費」為第一攻擊面。

實作者（Claude）**不自審**。

## 這票在解什麼（實機脈絡）

使用者 2026-09-09 UAT（事件型 B、ETHUSDT 12h 事件 165 筆、1h 特徵 39,373 欄）抓出三件事，三件皆已對證成立（SPEC §A FACT-RECEIPT）：
- 報告沒揭露 label 規則；實際 h=1（＝CSV `future_1bar_return`，單位＝事件週期 12h 一根＝1h 特徵第 12 根）。
- 切分 `purge_gap=5` 是特徵週期 1h 根數（主線 `default_horizon`），label 視窗 12 根被記進 `embargo=144`（`max(深度, 視窗)`）——**現況不洩漏**，但語意錯位。
- CSV `label` 0/1（136／29）在匯入層已解析持久化，IC 路徑**完全沒讀**；IC 對的是規則重算的報酬。

## ⚠️ 前置說明（勿誤 block）
- **禁改碼、禁改文件**（只提出，由 Claude 改）。
- **不得**跑 `pytest tests/governance`（小時級）。
- SPEC 引用之測試檔／腳本（`tests/*/test_evtlabel_*.py`、`scripts/evtlabel_phase_gate.sh`、`handoffs/20260910-evtlabel-mutate.py`、`momentum/Analysis/binary_discrimination.py`、`momentum/Analysis/contracts/event_label_mode.json`）**尚不存在＝正常**（TODO Task 0.1／3.1 產出），不是 BLOCKING 碼證。
- 既有紅（非本票造成）：`EA-RESID-6` 四條 golden（reporter stub 缺 kwarg×2、config_hash 凍結過期、event_timestamps kwarg 正則）。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 受理 run 消費的是規則重算報酬、h=1 c2c
→ `jq '.metadata.event_filter.consumed_event_labels["ETHUSDT:12h:1735776000000"]' data_cache/reports/ic_report_ic_gatekeeper.json` = `-0.004468224…`；CSV 同列 `future_1bar_return=-0.004468221…`。

fact-verified: 分析層 label 視窗來自分析 spec（非匯入檔 `label_definition`），公式依 mode
→ `PYTHONPATH=. venv/bin/python handoffs/20260910-probe-label-rule.py` rc=0：
`[h1_c2c] window_ms=43200000 label_window_feature_bars=12 lookahead_depth_rows=144 purge_lower_bound=518400000 mismatch=0`；
`[h12_seed] window_ms=561600000 label_window_feature_bars=156 lookahead_depth_rows=144 purge_lower_bound=561600000 mismatch=0`。
⇒ `open_to_horizon_close` 視窗＝(h+1)×bar（t₀ open→t₀+h close）。**請自己重跑**。

fact-verified: 0/1 在匯入層已持久化
→ `jq '[.records[].label]|group_by(.)|map(length)' data_cache/events/20260909T130533Z-7f73e4c7.json` = `[29,136]`（如你的沙箱讀不到 `data_cache/`，標「未經覆核」）。

fact-verified: `single_feature_binary_baseline`（GAP-3 B1.4）無 caller；`pipeline.py:523` 辨別表恆 `not_computed`。

assumed: `[A-2]` `scipy.stats.mannwhitneyu(axis=0)` 對 39,373×165 單次 < 60s
← 否證觀測：實測 > 60s。／我跑了：**沒跑**（B4 開工前跑 `handoffs/20260910-probe-mw-bench.py`）。

assumed: `[A-3]` `validate_event_given` 可直接吃 0/1（float）之 expected_values
← 否證觀測：binary 進 `validate_consumed_label` raise 或非有限值閘誤擋。／我跑了：**只讀碼**（`contracts.py:1063-1107` 逐值相等＋finite 檢查，0.0/1.0 皆 finite）。

assumed: 把 `rank_biserial` 當主統計餵既有 `ic_mean_min` 閘（SPEC Task 3.6）在語意上站得住
← 否證觀測：存在一組 `(n_pos, n_neg)` 使 `|rank_biserial| ≥ ic_mean_min` 與「特徵能分開正反例」不對應（例：極端不平衡下 rank-biserial 之抽樣分布寬到門檻無意義）。／我跑了：**沒跑**，這是設計判斷，請正面攻。

assumed: P2 只是語意錯位、非洩漏
← 否證觀測：存在情境 `purge+embargo < max(label_window_rows, lookahead_depth_rows)`。／我跑了：讀碼推導（`purge_rows=ceil(max(depth,window)/bar)` 注入 embargo ⇒ 恆 ≥）；G-2 條件 (iii) 會機械驗。

## 🔴 我沒查的

| claim | scope_ref | observable_if_false | recheck_cmd | reason_code | run_state |
|---|---|---|---|---|---|
| 事件路徑 HAC lag（`split_context["effective_horizon"]`=5）對 h=12 根 label 是否低估自相關 | ic_filter_orchestrator.py:3766-3900 | 事件 run 之 `p_value` 系統性偏小 | 以 label 視窗 12 vs 5 跑同一 run 比 p 分布 | needs-research（SPEC §N R-1） | NOT_RUN |
| `ICConfig` schema 是否 `extra=forbid`（決定 Task 2.2 走 pop 或顯式欄位） | momentum/Analysis/ic_config_schema.py | `config_override["event_purge_rows"]` 進 ICConfig 即 422 | `grep -n "extra" momentum/Analysis/ic_config_schema.py` | cost | NOT_RUN |
| summary_table 加欄後 `ICResult` 分頁（ICRESULT_PAGING）之 size budget 是否超標 | api/services + frontend paging | 39k 列 × 8 新欄使 `icresult_size_budget` 紅 | `handoffs/run_receipts/icresult_size_budget.log` 對照 | cost | NOT_RUN |
| test split 之事件列在 165 事件下每類 ≥10 是否常態（`oos_test_size` 下 test 段只剩 ~20% 事件） | ic_train_test_split | binary 主統計常年 `unavailable:class_below_min` | 受理 run 之 test 段事件數與 label 分布 | cost | NOT_RUN |
| `survivor_output` 消費端（`ic_reporter.py:275`、前端）對新鍵 `label_binary` 之容忍 | momentum/Analysis/ic_reporter.py; frontend | 舊消費端 raise | grep 消費端鍵集斷言 | cost | NOT_RUN |

## oracle-artifact
- 前提探針：`handoffs/20260910-probe-label-rule.py`（可重跑）
- 受理 run 報告：`data_cache/reports/ic_report_ic_gatekeeper.json`（`metadata.event_filter`、`metadata.ic_train_test_split`）
- 既有 AUC/置換 oracle 載體：`momentum/Analysis/event_samples/baseline.py`（`permutation_oracle`）
- 既有 split golden：`tests/golden/evtalign/split_baseline.json`＋`handoffs/20260907-probe-split-baseline.py`

## 必答（逐條 verdict；成對）

1a. **P3 統計設計**：以 Mann-Whitney U／AUC／rank-biserial 為主統計、BH-FDR 對 MW p、倖存者置換自檢，這組合對「哪些特徵能分開正反例」是不是正確 estimand？
1b. 若不是，你的替代是什麼，且它在 165 事件（136／29）與 test 段 ~33 事件下仍可算？

2a. **既有門檻消費**：Task 3.6 讓 `ic_mean_min` 閘讀 `rank_biserial`、p 閘讀 `mw_p_value_adj`、`icir`／`hit_rate`／`monotonicity` 記錄不剔除——哪一條會把 binary 結果錯誤剔除或錯誤放行？
2b. `return_rule`／全域路徑：請逐一指出 Task 3.4／3.6／3.8 哪個改動點**可能**碰到非 binary 路徑（欄集、排序、`_apply_thresholds` 預設參數、survivor payload），G-1／G-4 的斷言能不能抓到。

3a. **P2 語意**：purge＝label 視窗（feature 根數）、embargo＝max(config, look-ahead 深度)，兩者相加為總隔離。這個拆法在「深度 < 視窗」（route seed h=12 o2hc：156 vs 144）與「深度 > 視窗」（h=1 c2c：12 vs 144）兩情境下各給出什麼數字？有沒有情境使總隔離**小於**改前？
3b. 改前 `embargo=max(config, max(深度,視窗))` 在任一情境下是否曾洩漏？若曾，SPEC §A「現況不洩漏」須改寫。

4a. **auto 解析**（Task 3.3）：批有 0/1 兩類各 ≥ `min_events_per_class`（預設 10）⇒ 自動走 `imported_binary`。這個預設對使用者是「驗過就預設開」的正確落實，還是會讓不知情的使用者拿到與上次不同語意的報告？
4b. `min_events_per_class=10` 之依據？請給你認為正確的值與理由（或改為由 test 段事件數決定）。

5a. 🔴 **三元組綁定**：binary 向量以 `validate_event_given(expected_values=0/1, event_owners)` 驗、`consumed_event_binary_labels` 另開鍵回綁——請構造一個「報酬 label 綁對、binary label 錯位」的反例，看 SPEC 之檢查能否抓到。
5b. 反過來：有沒有辦法讓 binary 通過驗證但實際消費的是另一份（EVTALIGN 的「驗了就丟」形態）？逐 stage 指出消費點。

6. **有無 ≥10× 不必要複雜**（固定必問）：特別看 Task 3.7 置換自檢＋負對照、Task 3.1 JSON SoT、Task 3.10 真實 kline e2e。

7. **§N 殘留 R-1..R-6 之三值理由**是否成立？尤其 R-4（「餵 ML」＝交付倖存者檔、ML 殼不在本票）——這是主委判斷非使用者裁定，請正面回答它是否偷換了主目標。

8. 可以進實作嗎，還是有 BLOCKING 必須先改 SPEC？

## 驗收命令
```
bash scripts/template_check.sh spec docs/EVTLABEL_SPEC.md
bash scripts/template_check.sh todo docs/EVTLABEL_TODO.md
PYTHONPATH=. venv/bin/python handoffs/20260910-probe-label-rule.py
```

## 停輪條件（可列完）
① 必答 1a/1b–5a/5b 每格皆有碼證或實跑（雙向）。
② 四條 assumed 各有明確 verdict（成立／推翻／無法判定＋為什麼）。
③ 本輪 P0／P1 皆指出 SPEC/TODO 對應修訂位置。
④ 必答 7 對 R-4 有明確 verdict。

## 附錄：已排除（跑過）
| claim | 查證 |
|---|---|
| CSV 0/1 兩類皆存在（136／29） | awk 實跑 |
| 受理 run h=1 c2c、label 未用 0/1 | jq 對證 consumed_event_labels vs CSV |
| 分析層視窗公式（c2c h×bar；o2hc (h+1)×bar） | 探針 rc=0 |
| SPEC/TODO 過機檢 | TEMPLATE PASS ×2 |

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改文件**。收尾清 /tmp workdir（保留 claude-501）。
