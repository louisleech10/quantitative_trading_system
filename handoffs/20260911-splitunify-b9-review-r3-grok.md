# SPLITUNIFY D-002 閉合輪 R3 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R3`  
family: grok  
findings-round: R3  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第三次修訂；full sha12 `3930b032710e`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r2/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r3/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉: `GROK-R2-P1-01`、`GROK-R2-P1-02`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: 九群 11 條全部採納零駁回 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r2/synth.md` 群集表；本家兩條皆在「採納」列

fact-verified: 三道閘 rc=0 → 本輪實跑 `obligation_block_check.sh`／`doc_format_precheck.sh` 皆 rc=0（`/tmp/grok-splitunify-b9-review-r3/obl.log`／`fmt.log`）

fact-verified: 本家 R2 兩條落點已寫入修訂版 → summary 鍵＝`discarded_rows_by_feature_tf`（L138）；`Task 9.2a` 明定 `clusters` 不加 `feature_timeframe`（L154）；`(0.6)` 既有欄保留（L38）

fact-verified: `build_event_keys` 唯一生產 caller 為 `pipeline.py:747` 且必傳 `selected_timeframe=str(...)` → `grep -rn 'build_event_keys(' momentum api`

fact-verified: clusters 事件級時 `w=1/n` 同簇權重和＝1；join 到 2×TF 展開列後同簇權重和＝2 → 探針 `probe_clusters_weight.txt`

assumed: `(3.1)`「可比時點」前提已足以讓同側判定不再誤殺  
→ **否證**：`(3.1)` 只寫「須先定義」卻未給可操作定義；§V C3 ASSERT 仍以各 TF 獨立判側為前提（見 P1-01）。我無法在「未定義的前提」下構造合法異側，也無法驗證「前提已足」——前提本身未落地。

assumed: `clusters` 維持事件級不會讓多 feature TF 的簇權重失真  
→ **部分成立**：在 `clusters` 表本身與 `n_events_effective`（manifest 事件數）上成立；若把 `cluster_weight` 加總在 `(event×TF)` 展開列上會失真（探針）。現行消費者讀 `time_cluster_id`／在 clusters 表上驗權重和，**尚未**規定展開列加總 ⇒ 不另開 P1，但見必答 3。

assumed: 20 條 mutation 已覆蓋 16 處＋9A＋Task 9.2  
→ **部分否證**：`M-SU-D2-19` 與 C5 事件級 survivor 語意衝突（P1-03）；`M-SU-D2-20` 有列但 §V Task 9.2 ASSERT 未對應全量 rows（併入 P1-02）。

assumed: `(6.2)` 逐消費者定義不會退化成「各處自己決定」  
→ **本輪成立於字面**：`(6.2)` 具名 `summary`／前端／wiring＝事件數、`baseline.n_test`＝樣本數；Task 9.4 檔案清單不含 `baseline.py`。未另開洞。

---

## 必答 1–5

### 1. 本家 R2 finding 是否閉合

| R2 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R2-P1-01` | **CLOSED** | 讀 L138：`EventSplitPlan.summary["discarded_rows_by_feature_tf"]`（已去裸 `timeframe`）；L38 `(0.6)` 區分既有保留／新增分名；`grep discarded_per_tf_rows_by_timeframe` → 0 命中（僅沿革提及舊名） |
| `GROK-R2-P1-02` | **CLOSED** | 讀 L154：`clusters` 不加該欄、維持事件級、同事件多 TF 共用同一簇列；原「三表各加」句已不存在；與 `tables.py:229` `set_index("event_id")` 相容 |

### 2. 可比時點（`(3.1)`）— 還能誤 purge 合法事件嗎？

**試了什麼：**

1. 重讀 `(3.1)`–`(3.2)` 全文：只有「須先定義可比時點」的**元義務**，沒有「可比時點＝…」的操作定義（無 `decision_at_ms`／trigger cutoff／錨定規則）。
2. 對照資料契約：`alignment.py:197-213` 各 `sub_tf` 獨立 as-of 取 `feature_cutoff_ms`，唯一 PIT 閘＝`cutoff <= decision_at`——**未**要求跨 TF cutoff 對齊（與 R2／CODEX-R2-P1-01 同證）。
3. 試圖在「前提已成立」下構造反例 → **做不到**，因為前提的關鍵詞未被定義，無法判定哪種異側算「定義後仍異側」vs「定義前不該判」。
4. §V L178 仍寫 `ASSERT WHEN 某 event 之 1h 判 train、4h 判 test THEN … purged`——這預設各 TF 可獨立判側，與 `(3.1)`「未定義前不得逕行判定異側」**互斥**。

**結論：不是「構造不出誤殺」，而是修訂把誤殺門從「一律 purge」改成「先有定義再 purge」，卻沒給定義。** 不改則 Task 9.x 實作者必須自創定義 → 要嘛仍按 cutoff 獨立判側（誤殺回歸），要嘛無法寫出與 §V 一致的測試。→ **P1-01**

### 3. clusters 維持事件級 — `w=1/n` 與 `n_events_effective`

**碼證（探針 `probe_clusters_weight.txt`）：**

- 兩事件同桶、事件級 `build_time_clusters`：`cluster_weight={0.5,0.5}`，同簇 Σw＝**1.0**（不變式成立）。
- `n_events_effective` 來自 manifest.summary（事件數），與 feature TF 展開無關 → 仍正確。
- 若把同一權重 join 到每事件 2 個 feature TF 的 assignments 列再加總：同簇 Σw＝**2.0**（不變式破）。

**立場：事件級定案對 `clusters` 表與 `n_events_effective` 正確**（修掉 R2 的三表一刀切）。失真只在「錯誤地把 `cluster_weight` 在 `(event×TF)` 列上加總」——現行 `tables.py` 用 `time_cluster_id` 做 bootstrap、權重和測試打在 `plan.clusters` 上，**不是**此路徑。Task 9.3 未要求對展開列加總權重 ⇒ **不開 finding**；實作時禁止該加總即可。

### 4. `Task 9.2` 是否真補上核心（SU-RESID-2 丟棄消失？）

**有寫到的：** L145–149 明定移除預設單選、輸出全量 keyed rows；`M-SU-D2-20` 對應「保留預設單選應紅」。

**仍缺／會讓丟棄存活：**

1. Task 9.2 **檔案範圍只有** `split_projection.build_event_keys`；唯一生產 caller `pipeline.py:747` 仍 `selected_timeframe=str(selected_timeframe)` 必傳——即使 producer 改成 `Optional` 且 `None`→全量，live path 仍永遠走「明示單選」過濾。
2. §V L177 `Task 9.2` ASSERT 仍是「assignments 含 `feature_timeframe` 且複合鍵唯一」＝**Task 9.2a schema**，不是「未傳 selected ⇒ 輸出列數＝per_tf 全量」。
3. Task 9.1 仍保留 `selected=1h` 揭露路徑（合理），但 9B 未指派「多 TF 分析時 caller 不得預設傳 selected」。

**結論：字面有核心句，端到端未閉。** 做完 Task 9.2 檔案清單仍可假綠（函式預設全量＋測試用 None），而 pipeline 繼續丟棄。→ **P1-02**

### 5. 修訂引入的新問題

| 面 | 判定 |
|---|---|
| `(0.6)` vs 本家 P1-01 | 閉合；與 `(0.1)` 並讀時 `(0.6)` 為既有欄例外——可接受 |
| `(3.1)` 前提 | **新洞** P1-01（定義缺失＋§V 互斥） |
| `Task 9.2`／`9.2a` | 9.2a clusters 定案正確；9.2 範圍／§V 錯位 → P1-02 |
| 20 mutation | 表格式＋完整 ID 改善 R2；**`M-SU-D2-19` 與 C5 事件級 survivor 衝突** → P1-03 |
| `(6.2)` vs D-001／Task 9.4 | 未發現互斥；baseline 維持樣本數與 Task 9.4 事件數分母可並存 |
| 與 D-001 封閉 purge 字面 | `(3.2)` 沿用既有字面＝有意取捨；本輪不重開 |

---

## GROK-R3-P1-01

**斷言**: `(3.1)` 要求「先定義同一事件之可比時點」卻未給出任何可操作定義，且 §V 的 `D-002-C3` ASSERT 仍假設可對各 feature TF 獨立判 train／test——與 `(3.1)`「未定義前不得逕行判定異側」互斥；實作者無法同時滿足義務與驗收句。

**碼證**: SPEC L46 `(3.1)` 只有「須先定義…實作不得在未定義可比時點前逕行判定異側」，全文無「可比時點＝decision_at_ms／trigger cutoff／…」；L178 `ASSERT WHEN 某 event 之 1h 判 train、4h 判 test THEN … purged`；`alignment.py:197-213` 各 TF 獨立 as-of cutoff、僅 `cutoff<=decision_at`。RECHECK: `sed -n '46,52p;178p' docs/SPLITUNIFY_SPEC.D-002.md`＋讀 alignment 上列。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/alignment.py#0da3c48b2668

[BLOCKING] 信心度=High。不改則 Task 9.x 實作 C3 時：①自創「以各 cutoff 判側」→ 合法異側 cutoff 事件整批誤 purge（R2 已證之洞回歸）；②自創「以 decision_at 廣播同側」→ 與 §V L178 字面不符、成對 ASSERT 無法寫；③乾脆不做同側檢查 → 非法 OOS 靜默回來。**修法**：在 `(3.1)` **寫死**可比時點操作定義（建議：以該事件之 `decision_at_ms` 相對 train／test 邊界定側，再廣播到所有 feature TF 列；`feature_cutoff_ms` 只做 PIT 閘、不參與側別）。同步改寫 §V C3 ASSERT 與 `M-SU-D2-14`／`15` 使「定義後仍異側」僅在定義被違反時可觸發（或刪除「1h train／4h test」這種 cutoff 異側例句）。**可行性**：投影端已有 per-event `decision_at_ms` 與 per-row cutoff（`split_projection` 迴圈）；側別改由事件級一次判定再廣播，不需新資料欄。

---

## GROK-R3-P1-02

**斷言**: `Task 9.2` 雖寫「producer 停止單選、輸出全量 keyed rows」，但檔案範圍僅 `build_event_keys`、唯一生產 caller `pipeline.py:747` 仍必傳 `selected_timeframe`，且 §V 對 Task 9.2 的 ASSERT 驗的是 9.2a schema 而非全量列——完成字面 Task 9.2 後 live path 的 `SU-RESID-2` 丟棄行為仍可原封不動。

**碼證**: SPEC L145–149（Task 9.2 改法／檔案＝`build_event_keys`）；L177 §V Task 9.2 ASSERT＝`assignments` 含 `feature_timeframe` 且複合鍵唯一（＝9.2a）；L205 `M-SU-D2-20` 指向「全量 keyed rows 測試」但該 ASSERT 未出現在 §V；`pipeline.py:747`：`build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`；`grep -rn 'build_event_keys(' momentum api` → **僅此一處**生產呼叫。RECHECK: 重跑該 grep＋讀 L145–149／L177／`:747`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。Agent 可把 `selected_timeframe` 改成 `Optional`、單測傳 `None` 綠燈、§V schema ASSERT 靠 9.2a 過關，但 pipeline 繼續傳 selected ⇒ 未選 TF 列仍被丟棄，第 9 批核心目標假完成。**修法**：①Task 9.2 檔案清單加上 `pipeline.py`（及日後若有的其他 caller），明定多 TF 分析路徑必須 `selected_timeframe=None`（或不再傳）才輸出全量；單 TF／使用者明示單選才走過濾＋Task 9.1 揭露。②§V 新增／改寫 Task 9.2 ASSERT：`WHEN per_tf 含 1h+4h 且 selected is None THEN 輸出列數＝per_tf 列數且兩 TF 皆在`；schema 唯一性 ASSERT 歸 `Task 9.2a`。③`M-SU-D2-20` 的「應紅之測試」改指上述全量 ASSERT（含經 pipeline 的一條）。**可行性**：全 repo 僅一處生產呼叫；改 signature 預設 `None`＋改 pipeline 一行即可落地，9A 單選揭露路徑仍保留。

---

## GROK-R3-P1-03

**斷言**: `M-SU-D2-19` 把「survivor 六鍵雜湊未隨複合鍵調整」列為應紅缺陷，但 `D-002-C5` (5.4) 與現行 `ic_feed.event_context_from_windows` 皆定義 survivor 為**事件級**（排序後 `event_id`＋label 窗雜湊、不含 feature TF）——照 mutation 字面「調整」成複合鍵會改錯身分語意。

**碼證**: SPEC L204 `M-SU-D2-19`；L80 C5 (5.4)「survivor 六鍵（以排序後 `event_id` 列雜湊）」；`ic_feed.py:57-65` 只序列化 `event_id`／`label_start_ms`／`label_end_ms`。本家 R2 主動攻擊亦判定 survivor **不應**複合鍵化。RECHECK: `sed -n '80p;204p' docs/SPLITUNIFY_SPEC.D-002.md`＋讀 `ic_feed.py:43-74`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/ic_feed.py#741f697b3964

[BLOCKING] 信心度=High。mutation 自證若依字面要求「隨複合鍵調整」，會逼實作把 `feature_timeframe` 打進 manifest hash ⇒ 同事件多 TF 改變 survivor 身分／快取鍵，與 C5 事件級定義及「分析時事件集合身分」契約衝突；若測試其實想鎖「複合鍵落地後仍保持事件級、不得因 TF 展開而漂」，則現行 mutation 措辭寫反。**修法**：重寫 `M-SU-D2-19` 為反向／正向其一——例如「改壞：把 `feature_timeframe` 納入 survivor 雜湊」應紅於「hash 必須仍僅依事件窗」；或刪除該條並在 Task 9.3 註明 survivor／`event_context` 維持事件級、不在複合鍵範圍。**可行性**：`event_context_from_windows` 已是純事件窗；改 mutation 文案零碼阻礙，只需與 C5 對齊一句。

---

## 11 類快掃（§1）

1. 矛盾／互斥：`(3.1)`↔§V C3 ASSERT（P1-01）；`M-SU-D2-19`↔C5 survivor（P1-03）；Task 9.2 正文↔§V ASSERT／caller（P1-02）  
2. 漏項：Task 9.2 未列 pipeline caller  
3. 不可測：可比時點無操作定義 ⇒ C3 成對 ASSERT 不可實作  
4. quant：同側紅線仍正確，但門檻未操作化  
5. 過度工程：無  
6. OOM：無  
7. Cache：survivor 誤複合鍵化會污染身分（P1-03）  
8. API／型別：`(0.6)`＋新鍵名 OK  
9. 測試：20 表改善；上列三處仍會假綠或逼錯修  
10. Agent 可執行：`(3.1)`／Task 9.2 範圍不足  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R2 兩條逐條對修訂 → **皆 CLOSED**  
2. `(3.1)` 可比時點操作化 → **開洞 P1-01**  
3. clusters 權重探針 → 事件級正確；展開加總失真但非現行規定路徑  
4. Task 9.2 端到端（函式＋唯一 caller＋§V）→ **開洞 P1-02**  
5. mutation 20 逐條對 C5／9A／9.2 → **`M-SU-D2-19` 開洞 P1-03**  
6. `(0.6)`／`(6.2)`／obligation 閘 → 未再開洞  
7. 三閘 rc=0 → 確認（不代表語義可實作）

不改就進 Task 9.x：①C3 無法一致實作／驗收；②pipeline 繼續單選丟棄使 9B 假完成；③survivor mutation 逼錯修或假綠。

---

## 被當成事實的未驗證假設（§0 彙總）

1. 「九群修訂已消掉 R2 洞」——對**本家兩條**成立；修訂**新引入** P1-01／02／03。  
2. 「可比時點前提已足」——被否證（定義缺失）。  
3. 「clusters 事件級權重不失真」——在 clusters 表上成立。  
4. 「Task 9.2 已補核心」——正文有、端到端無。  
5. 「IC e2e」——仍未跑（§N 同限）。

ASSUMPTIONS_VERIFIED: 本家 R2 兩條 CLOSED（鍵名／clusters 定案）；三閘 rc=0；clusters Σw 探針；build_event_keys 唯一 caller＝pipeline:747；survivor 雜湊欄位僅事件窗  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；探針 `probe_clusters_weight.txt`／`probe_c3_and_92.txt`；`grep -rn 'build_event_keys(' momentum api`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r3-grok.md --family grok`  
FAILURES_SEEN: none（本輪為規格複驗，無實作失敗）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r3-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R3-P1-01,GROK-R3-P1-02,GROK-R3-P1-03
CLOSED: GROK-R2-P1-01,GROK-R2-P1-02
STATUS: DONE
