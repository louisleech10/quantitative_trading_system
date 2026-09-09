# Reconcile — 20260910-evtlabel-x-review-r2

**來源** 20260910-evtlabel-x-review-r2-codex.md, 20260910-evtlabel-x-review-r2-composer.md, 20260910-evtlabel-x-review-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**輪次計數**：codex 1（1×P0，**程序性拒審**）、composer 7（1×P0、4×P1、2×P2）、grok 8（1×P0、4×P1、3×P2）＝ **16 條**。
composer／grok 對 C1–C14 逐條判：C1、C2、C5–C9、C11–C14 **CLOSED**；C3 語意 CLOSED／校準 PARTIAL；C4 **NOT-CLOSED**（簽名漂移＋對證指令自相矛盾）；C10 有寫／設計 NOT-CLOSED。
兩家 Verdict 一致：**P1／P2 可凍結動工；P3 須修 P0 後才可凍結；不得延後 P3**。

Verdict: 需修補後合併（P1/P2 凍結；P3 依 D1–D8 修訂後派 R3＝閉合＋戳記合併輪）

---

### D1 🔴 P0 — C4 未閉：stage5 對證指令自相矛盾（全批 digest 相等 vs 子集 `in`）＋`rows_frozenset` 簽名漂移
**ID**：`GROK-R2-P0-01`、`GROK-R2-P1-01`、`COMPOSER-R2-P1-01`
**處置**：唯一守衛定死＝`all((eid,ts,y_i) in vb.rows_frozenset)` **且** `X.index.equals(pd.Index(sel_idx))` 且 `len(y)==len(X)`；刪除「子集 digest == 全批 digest」祈使句；`digest` 只作 stage3 封存／揭露。TODO 3.1 dataclass 與 3.4 建構式補 `rows_frozenset`；契約測試斷言欄位存在；M-P3-5 涵蓋「換 cache」與「對證後 permute X」（grok 2a 反例）。

### D2 🔴 P0（校準）— 負對照 `>0 ⇒ suppressed` 之尺度
**ID**：`COMPOSER-R2-P0-01`、`GROK-R2-P1-04`
**裁定**：composer 之 `E≈α·m≈1969` 為**未校正**期望，**錯**；grok BH 模擬 P(R>0)≈0.03–0.07（獨立近似）為準。但 ≈α 的整批誤殺稅仍真實。**採 grok (B)＋(C) 合併**：(C) consumable 放行＝per-survivor block permutation（特徵級 fail-closed，不把隨機標籤特徵交給 ML，保 codex R1 P0-01 精神）；(B) 整批負對照改 **20 次**置亂取 null 分布，`n_survivors_observed <= q95(n_survivors_shuffled)` 才 suppressed（＝觀測倖存數與 null 無法區分）；單次 `>0` 不再整批殺，只揭露。成本 20×MW（≈16s clean）。

### D3 — block permutation 之 L 於密集段失守；長視窗 `n_blocks<10` 須 loud 標為產品限制
**ID**：`COMPOSER-R2-P1-02`、`GROK-R2-P1-02`、`COMPOSER-R2-P1-03`、`GROK-R2-P1-03`
**處置**：`L = max(1, ceil(W / max(1, min_gap_rows)), ceil(W / median_gap_rows))`（取較大者）；加密集段 fixture `test_dense_cluster_block_len`。`n_blocks<10` ⇒ `permutation_receipt.status=unavailable:insufficient_blocks`、`label_mode.reason` 附註、Task 3.9 banner loud；§N 新增 R-7「長 label 視窗下 binary consumable 可能結構性不可得（預期限制，非 bug）」；`10` 標「預註冊常數，非推導」。

### D4 — 顯式 `imported_binary` 應 fast-fail（僅顯式模式）
**ID**：`COMPOSER-R2-P1-04`、`GROK-R2-P2-03`
**處置**：Task 3.3 新增 `prevalidate_imported_binary_selection_classes(staged, split_preview)`：以與 orchestrator **相同**之 chronological holdout 規則（`oos_test_size`、purge、embargo）預估 test 段類數，`requested=imported_binary` 且不足 ⇒ 立即 422（`class_below_min_selection_preview`）；`auto` 不預擋、仍在 stage3 降級。orchestrator 之 stage3 判定為權威，預檢只是 DX 早擋。

### D5 — SPEC Task 3.2 殘句「auto 解析在 service」
**ID**：`GROK-R2-P2-01`
**處置**：改為「route／service 只透傳 `requested`；effective 在 Task 3.4 stage3」。

### D6 — `rank_biserial_min=0.10` 近 no-op 之揭露；`min_events_per_class=10` 維持
**ID**：`GROK-R2-P2-02`（composer 6a/6b 同向）
**處置**：維持兩數值；Task 3.6 與白話再釘「主閘＝FDR＋置換；0.10 為預註冊地板」。

### D7 — Task 3.11 suppressed 契約措辭；stage6b `label_series` 入參揭露
**ID**：`COMPOSER-R2-P2-01`、`COMPOSER-R2-P2-02`
**處置**：Task 3.11 明寫三種拒收皆為既有 raise 且測試斷言 message 含 reason（HEAD `cfc048b7` 已對齊）；Task 3.6 增「stage6b 入參 label 固定為報酬列；節 metadata 寫 `role=diagnostic`＋`label_source=return_rule_diagnostic`」。

### D8 — Codex 程序性拒審（Rule 12：R1 synth 無 RECONCILE-STAMP）
**ID**：`CODEX-R2-P0-01`
**裁定**：AGENTS.md Rule 12 之字面對象是「動工前」；本專案 SPEC review 輪之慣例（EVTALIGN R1→R2→consult）為 reconcile 於凍結前一次戳記，非每輪戳記。但 codex 之保守讀法可接受且成本低 ⇒ **R3 改為「閉合＋戳記合併輪」**：三家審 v3、並對 R1／R2／R3 三份 synth 各 append `RECONCILE-STAMP`（批次戳記，ORCH「批次戳記」節）。本條**不視為 SPEC 缺陷**；codex 於 R3 須補做 R2 之實質審查（C1–C14 判定＋2a／3a／5a）。

---

### §0 假設裁定
- `rows_frozenset` 子集 `in` 足以防 X↔y 錯位：**部分推翻**（grok：permute X 不被抓）⇒ D1 加 index 對齊斷言。
- median-L 足夠：**推翻** ⇒ D3。
- `>0` 常態觸發：**推翻**（α·m 算錯；BH 下 ≈α）⇒ D2 仍改校準。
- `series.flags.writeable=False` 擋 in-place：**成立**（grok＋Claude 各自實跑 ValueError）。
- `consumed_event_rows` additive 不紅既有 `==`：**成立**（grok 讀 `test_event_label_alignment.py:103` 鍵級比較）。
- stage6b 不 `passed.remove`：**成立**（grok 計數 0；Claude 讀碼同）。

### 不採納
- `COMPOSER-R2-P0-01` 之數量級論證（α·m）不採納；其結論「須校準」採納（D2）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P0-01

**斷言**: R2 不能在目前的 R1 reconcile 上作閉合審查，因為所依 `synth.md` 沒有任何 `RECONCILE-STAMP: ... APPROVED`，僅有 `sources.lock` 的 `closure_state=FROZEN`。

**碼證**: `rg -n '^RECONCILE-STAMP:' handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md` → 無輸出、rc=1；`sed -n '1,40p' handoffs/reconcile/20260910-evtlabel-x-review-r1/sources.lock` → `expected_roster=[codex,composer,grok]`、`closure_state=FROZEN`。RECHECK：同一 `rg` 應取得三家 `APPROVED` 戳記後，才可重開本輪逐條 C1–C14 與 v2 新設計審查。

**來源摘要**: handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md#3894fd9057df

[BLOCKING] 信心度=High。依 `AGENTS.md` Rule 12，`FROZEN` 不等於三家 `RECONCILE-STAMP APPROVED`；在缺少核可戳記時繼續審查會違反本專案的 fail-closed 前置條件。因此本次未對 C1–C14 作 CLOSED／NOT-CLOSED 判定，也未對 brief 指定的 C4、block permutation、負對照期望值與 auto 時序作實質 review；沒有新增推測性 finding。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、AGENTS.md、R2 brief、R1 synth、SPEC、TODO、review template；已核對 R1 synth 無 RECONCILE-STAMP 行；已核對 sources.lock 的 roster 與 FROZEN 狀態。
TESTS_RUN: `rg -n '^RECONCILE-STAMP:' handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md` → no output, rc=1；未執行 brief 的 SPEC/TODO completeness 驗收，因本輪在 Rule 12 前置 gate 停止。
FAILURES_SEEN: reconcile stamp 前置條件未滿足；未進入實質審查，無其他審查失敗。
SCOPE_CHANGES: none；只新增本交件檔。
NUMERIC_OR_SCHEMA_IMPACT: none；未改 SPEC、TODO、程式碼或測試。
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護，本次未改寫。
STATUS: BLOCKED — reconcile 未核可
## COMPOSER-R2-P0-01

**斷言**: v2 沿用 R1 C3 之 `n_survivors_shuffled > 0 ⇒ suppressed`，在 ~39k 特徵、單次置亂、BH α=0.05 下期望值遠大於 0，會使 binary 模式**幾乎永遠**無 consumable survivor，與主目標「找出可分離特徵並交付 ML 輸入」實質衝突。

**碼證**: `docs/EVTLABEL_SPEC.md` Task 3.7「`n_survivors_shuffled > 0` ⇒ fail-closed」；`docs/EVTLABEL_TODO.md` Task 3.7 要點 4 同句；受理 run `jq '.summary_table|length' data_cache/reports/ic_report_ic_gatekeeper.json` → 5909（同批規模）；獨立近似 E[假陽性]≈0.05×39373≈1969。RECHECK：固定 seed 單次置亂 200 合成特徵×165 列，數 `n_survivors_shuffled`。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807, docs/EVTLABEL_TODO.md#e412e40b0e8f

[BLOCKING] 信心度=High。會怎麼失敗：任何通過 MW+FDR 的真倖存者批次，幾乎總被負對照殺掉，使用者只見 `negative_control_failed` banner 與空 ML 輸入。修法：SPEC/TODO Task 3.7/3.8/3.9——負對照改揭露＋per-survivor 置換放行；或門檻改 `> max(ceil(α·n_tests), k_min)`／多次置亂分位。composer 表態見必答 5b。

---

## COMPOSER-R2-P1-01

**斷言**: C4 在 v2 **未閉合**：SPEC 定義 `ValidatedBinaryLabel(..., rows_frozenset, ...)` 供 stage5 子集 `in` 對證，但 TODO Task 3.1/3.4 的 dataclass 簽名與建構式**缺少** `rows_frozenset`，與 Task 3.6 消費敘述矛盾，agent 可能只實作 digest 而漏子集守衛。

**碼證**: `docs/EVTLABEL_SPEC.md:168` `ValidatedBinaryLabel(series, digest, rows_frozenset, n_pos, n_neg)`；`docs/EVTLABEL_TODO.md:217` 僅 `(series, digest, n_pos, n_neg)`；`:286` 建構未賦 `rows_frozenset`；`:324` stage5 卻要求 `vb.rows_frozenset` 子集 `in`。RECHECK：`rg 'rows_frozenset' docs/EVTLABEL_{SPEC,TODO}.md`。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807, docs/EVTLABEL_TODO.md#e412e40b0e8f

[MAJOR] 信心度=High。修法：TODO Task 3.1 要點 1／3.4 要點 4 與 SPEC 对齐，建構時填入 `frozenset((eid,ts,label),...)`；`test_event_label_mode_contract.py` 斷言欄位存在。

---

## COMPOSER-R2-P1-02

**斷言**: block permutation 之 `L = ceil(label_window / median_gap)` 在「局部密集、全局稀疏」事件段會把 L 算得过小，置換 null 過窄，無法吸收 label 視窗重疊依賴，與 C10 宣稱的 dependence-aware 不一致。

**碼證**: `docs/EVTLABEL_SPEC.md` Task 3.7「block 長度…median_event_gap_rows」；`docs/EVTLABEL_TODO.md` Task 3.7 要點 1 同式。反例：前 10 事件落在 10 根 bar（gap=1）、`label_window_feature_bars=12`、後續 gap=12 ⇒ 重疊叢集內依賴未被 block 吸收。RECHECK：密集段 fixture + `L=1` 與 `L≥視窗` 兩組比較置換 p 分布。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807

[MAJOR] 信心度=Medium。修法：Task 3.7 改用 `L=max(ceil(W/median_gap), ceil(W/min_gap))` 或重疊圖分块；加 `test_evtlabel_oracle.py::test_dense_cluster_block_len`。

---

## COMPOSER-R2-P1-03

**斷言**: h=12 open-to-horizon-close（`label_window_feature_bars=156`）且事件間距中位數 ≈1 根時，`n_blocks≈2<10` 使置換恆 `unavailable`，binary 倖存者在長視窗場景**結構性無法**完成依賴感知放行，但文件未 loud 標為預期產品限制。

**碼證**: `docs/EVTLABEL_SPEC.md` Task 3.7「`n_blocks < 10` ⇒ unavailable」；§A ASSUME-1 h12 `label_window_feature_bars=156`；165 事件 ⇒ `ceil(165/156)=2`。RECHECK：探針印 `L,n_blocks,permutation status` on h12 fixture。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807

[MAJOR] 信心度=High。修法：Task 3.9 banner／`label_mode.reason` 增 `permutation_unavailable_insufficient_blocks`；或研究降低 `n_blocks` 下限（需 quant 簽核）。保守 unavailable 本身可接受，须揭露。

---

## COMPOSER-R2-P1-04

**斷言**: 显式 `imported_binary` 在 test 段類數不足時仍须跑完整 preprocessing 才于 stage3 raise，11 分钟级反馈违反 API fail-fast 预期；v2 未采纳 R1 composer 预模拟 split 建议。

**碼證**: `docs/EVTLABEL_SPEC.md` Task 3.4「`requested=imported_binary` 不足 ⇒ raise」；`docs/EVTLABEL_TODO.md` Task 3.3「不在此決定 effective mode」。现网 `_run_event_label_stages` 长链路见 `ic_analysis_service.py:1288+`。RECHECK：mock test 段 18/2 + `imported_binary` 断言 analyze 未被调用或 <1s 返回 422。

**來源摘要**: docs/EVTLABEL_TODO.md#e412e40b0e8f, api/services/ic_analysis_service.py#eb592a4d3d04

[MAJOR] 信心度=Medium。修法：Task 3.3 增 service 端 `prevalidate_binary_selection_classes`（复用 Task 2.2 split 规则）；仅 `requested=imported_binary` 触发。

---

## COMPOSER-R2-P2-01

**斷言**: Task 3.11 边界「suppressed payload ⇒ consumer raise」与 `pattern_bridge._survivor_feature_names` 对空 `survivors[]` 亦 raise 的现网行为需定死，否则测试与 impl 可能对「拒收 vs 空集」理解分叉。

**碼證**: `docs/EVTLABEL_TODO.md` Task 3.11 要点 3「suppressed ⇒ raise／拒收」；`momentum/Analysis/event_samples/pattern_bridge.py:52-64` 空 survivors ⇒ `ValueError`。RECHECK：读 `:52-105` 确认 suppressed stub 是否含 `survivors:[]`。

**來源摘要**: docs/EVTLABEL_TODO.md#e412e40b0e8f, momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2

[MINOR] 信心度=Medium。修法：Task 3.11 明写 suppressed 契约（`status=suppressed` 时 consumer 必须 raise 且 message 含 reason）；测试断言 message。

---

## COMPOSER-R2-P2-02

**斷言**: stage6b 仍喂 `ic_results.get("label_series")`（报酬列，`ic_filter_orchestrator.py:1357-1359`），v2 仅标 `role=diagnostic` 未要求改 `label_series` 来源；若测试遗漏，marginal/composite 诊断可能仍用报酬 estimand 计算，与 binary 主统计并列时易误导报告读者。

**碼證**: 现网 `ic_filter_orchestrator.py:1357-1359`；`docs/EVTLABEL_SPEC.md` Task 3.6「stage6b…标 diagnostic，不得移除 binary 倖存者」未写 `label_series` 入参。RECHECK：binary run 断言 `marginal_ic` 节 metadata 含 `label_source=return_rule_diagnostic` 或显式 skip。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530, docs/EVTLABEL_SPEC.md#db36e9754807

[MINOR] 信心度=Medium。修法：Task 3.6 增「stage6b 入参 label 固定为报酬列 + 节标题/role 揭露」；测试断章 role 字段。

---

## GROK-R2-P0-01

**斷言**: TODO Task 3.6 要點 1 的祈使句要求 `binary_label_digest(selection_rows) == vb.digest`（全批 digest），與同句括號「digest 定義域＝全批 ⇒ 改用 `rows_frozenset` 子集 `in`」互斥；若 agent 實作第一句，凡 selection⊂full（有 holdout）的 binary 路徑將**恆** `AlignmentViolationError`，主目標交不出報告。

**碼證**: `docs/EVTLABEL_TODO.md:324` 同段先寫 `== vb.digest` 否則 raise，隨後括號改稱子集 `in`；`docs/EVTLABEL_SPEC.md:225` 仍寫「重算 digest…不等 ⇒ raise」且未提子集例外。RECHECK：全批 165、selection 31 之 fixture，digest(子集)≠digest(全批) 恆真 ⇒ 字面第一句必紅。

**來源摘要**: docs/EVTLABEL_TODO.md#b2dad8fbe5a2

[BLOCKING] 信心度=High。會怎麼失敗：Agent 擇一實作——(i) 全量相等 ⇒ 切分路徑全紅；(ii) 只做子集 `in` 但 dataclass 無 `rows_frozenset`（P1-01）⇒ AttributeError。修法：SPEC Task 3.6＋TODO 3.6 要點 1 **刪除**全量 digest 相等祈使句，定死唯一守衛＝`all(triple in vb.rows_frozenset)`（外加 `X.index` 對齊斷言）；M-P3-5 覆蓋「換 cache」與「子集合法但缺 frozenset 欄」。

---

## GROK-R2-P1-01

**斷言**: C4 在 v2 **未閉合**：SPEC Task 3.1 定義 `ValidatedBinaryLabel(..., rows_frozenset, ...)`，TODO Task 3.1／3.4 的簽名與建構式缺少該欄，但 Task 3.6 已消費 `vb.rows_frozenset` ⇒ agent 依 TODO 實作會在 stage5 爆 AttributeError，或靜默只做（錯誤的）digest 相等。

**碼證**: SPEC `:168` 含 `rows_frozenset`；TODO `:217` 僅 `(series, digest, n_pos, n_neg)`；`:286` 建構未賦 frozenset；`:324` 卻讀 `vb.rows_frozenset`。RECHECK：`grep -n rows_frozenset docs/EVTLABEL_{SPEC,TODO}.md`。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807

[MAJOR] 信心度=High。修法：TODO Task 3.1 要點 1／Task 3.4 要點 4 與 SPEC 對齊，建構時 `rows_frozenset=frozenset((eid,ts,int(v))…)`；契約測試斷言欄位存在。修訂位置：TODO 3.1／3.4；與 P0-01 同批。

---

## GROK-R2-P1-02

**斷言**: Task 3.7 以 `L=ceil(label_window_feature_bars / median_event_gap_rows)` 定 block，在「局部密集、全局稀疏」時可得到 L=1，block 置換退化为 iid 置換，無法吸收重疊 label 視窗依賴，與 C10「依賴感知」宣稱不一致。

**碼證**: SPEC／TODO Task 3.7 公式皆用 median gap。反例：前段 gap=1、W=12 高度重疊，後段長間距把 median 抬到 ≥12 ⇒ L=1。RECHECK：密集段 fixture 比較 L=median vs L=max(ceil(W/min_gap),…) 的置換 p 分布。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807

[MAJOR] 信心度=Medium。修法：TODO／SPEC Task 3.7 改 L 公式（納入 min gap 或重疊圖）；加 `test_dense_cluster_block_len`。

---

## GROK-R2-P1-03

**斷言**: 長視窗（W=156）且 median_gap≈1 時 `n_blocks≈2<10` ⇒ 置換結構性 `unavailable`，binary consumable survivor 交不出；v2 未要求 UI／banner 將此標成預期產品限制，易被讀成實作 bug。

**碼證**: SPEC Task 3.7 `n_blocks<10`；§A h12 `label_window_feature_bars=156`；`ceil(165/156)=2`。RECHECK：h12 fixture 印 `L,n_blocks,permutation status`。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807

[MAJOR] 信心度=High。修法：Task 3.9／`permutation_receipt` loud 揭露 `insufficient_blocks`；§N 或白話寫「長視窗可能無法 consumable」。不建議私下把 10 改小充綠。

---

## GROK-R2-P1-04

**斷言**: C3 的 `n_survivors_shuffled>0 ⇒ suppressed` 把 FWER 風格整批殺疊在 BH-FDR 主閘上，獨立 null 下會以 ≈α（數個百分點）機率誤殺整批 consumable survivor；文件未預註冊這筆稅，也未給多次置亂分位／改由 per-survivor 置換放行的定案。

**碼證**: SPEC／TODO Task 3.7 `>0`⇒suppressed；本輪 BH 模擬 P(R>0)≈0.03–0.07（**不是** α·m≈1969）。RECHECK：B4 用真實 39k×31 單次／多次置亂估 P(suppressed)。

**來源摘要**: docs/EVTLABEL_TODO.md#b2dad8fbe5a2

[MAJOR] 信心度=High（獨立近似）；特徵相依下之精確率 Medium。修法：見必答 5b（A/B/C 三選一寫死）。**反對**用 α·m 主張「永遠交不出」；**反對**降回 warning-only。

---

## GROK-R2-P2-01

**斷言**: SPEC Task 3.2 仍寫「`auto` 之解析在 service（Task 3.3）」，與 C2／Task 3.3「不決定 effective mode」矛盾，Agent 可能把 mode 決策又寫回 service。

**碼證**: SPEC `:181` vs SPEC Task 3.3／TODO 3.3「不決定 effective mode」。RECHECK：修訂後 grep「解析在 service」應為 0。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807

[MINOR] 信心度=High。修法：SPEC Task 3.2 改為「route／service 只透傳 `requested`；effective 在 Task 3.4 stage3」。

---

## GROK-R2-P2-02

**斷言**: `rank_biserial_min=0.10` 在 selection 17/14 下對 null 近 no-op（SE(rb)≈0.21），真實篩選幾乎只靠 MW→BH＋置換；若實作者誤以為效應量閘有 power 意義，會低估多重檢定風險。

**碼證**: SPEC Task 3.1 已寫「非 power 校準」；Var(AUC)=(n⁺+n⁻+1)/(12 n⁺ n⁻) ⇒ SE(rb)≈0.212。RECHECK：null 重抽通過 `|rb|≥0.10` 比率。

**來源摘要**: docs/EVTLABEL_SPEC.md#db36e9754807

[MINOR] 信心度=High。修法：白話／Task 3.6 再釘一句「主閘＝FDR＋置換；0.10 近地板」。維持數值 0.10。

---

## GROK-R2-P2-03

**斷言**: 顯式 `imported_binary` 在 selection 類數不足時仍須跑完整 preprocessing 才於 stage3 raise，DX 差；v2 未採納「僅顯式模式預模擬 split」的窄域 fast-fail。

**碼證**: SPEC Task 3.4 不足⇒raise；TODO 3.3 不在 staging 決 mode。RECHECK：mock test 18/2＋`imported_binary` 應 <1s 422（修後）。

**來源摘要**: docs/EVTLABEL_TODO.md#b2dad8fbe5a2

[MINOR] 信心度=Medium。修法：TODO Task 3.3 增 optional `prevalidate_imported_binary_selection_classes`；只擋顯式模式。

---

