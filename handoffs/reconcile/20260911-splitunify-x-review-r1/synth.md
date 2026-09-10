# Reconcile — 20260911-splitunify-x-review-r1

**來源** 20260911-splitunify-x-review-r1-codex.md, 20260911-splitunify-x-review-r1-composer.md, 20260911-splitunify-x-review-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——SPEC 改 v2、TODO 改 v2，並補做 consult synth 戳記輪，之後才可進 B1。

主委自產版另存 `handoffs/20260911-splitunify-claude-selfreview.md`（`CLAUDE-R1-*`，
依 `feedback_claude_own_version` 與三家平行產出）。下表之「主委補」欄即該檔之條目，
**三家皆未提出者不得因無人附議而降級**（ORCH「Claude 自身不享特權」之對偶：
Claude 的 finding 也不因是自己提的而自動採納，須附碼證；下列每條皆已附）。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **C1 戳記前置未過** | P0 | CODEX-R1-P0-01 | **採納**。consult synth 缺 `## 戳記` 區段，`reconcile_stamps_check.sh` rc=1，主委自跑同輸出。已補區段標題（本體零位元組變動），並派 `20260911-SPLITUNIFY-X-STAMP-R{1,2,3}` 序列化戳記輪。**在三家 APPROVED 之前不派 B1 impl token。** |
| **C2 投影簽名不足** | P0 | COMPOSER-R1-P0-01、GROK-R1-P0-01（主委補 CLAUDE-R1-P1-05 單位斷層） | **採納**。SPEC C-4／Task 2.1 之簽名補 `feature_index: pd.Index`；成員判定＝`ts ∈ feature_index[plan.row_index]` 之**集合**語意，禁 `time_bounds` 區間；`index_kind != "positional"` ⇒ fail-closed；單位歸一復用 `_normalize_ic_time_index`＋`asi8`（`ic_filter_orchestrator.py:3588-3594`），不另寫第二套。 |
| **C3 B3 驗收聚合假綠** | P0 | COMPOSER-R1-P0-02、GROK-R1-P0-02（主委補 CLAUDE-R1-P1-06） | **採納**。刪 `failed <= 20`。改：①B1 一次實跑凍結 `tests/baselines/analysis_known_failures.nodeids`；②`--deselect` 後 rc=0；③失敗集合與清單**集合相等**（多或少皆紅）；④本票新增測試檔不得進清單且須 rc=0。採 composer 之命令形（`awk '/^FAILED /{print $2}'`）＋grok 之集合相等檢查，兩者合併為較嚴版。 |
| **C4 未匹配時間戳未定義** | P1 | COMPOSER-R1-P1-01、GROK-R1-P1-01 | **採納**。Task 2.1 邊界補④：`event_index` 語意＝與 IC 同一 feature_cutoff 時鐘（`ic_feed.py:36` `max_close_ms_le_decision_at`）；不在 `feature_index` 集合內 ⇒ **purged**；**禁 nearest／asof／ffill**；單位未歸一 ⇒ raise（不得靜默 0 命中）。 |
| **C5 clusters／summary 產不出來** | P1 | COMPOSER-R1-P1-02、GROK-R1-P1-02（主委補 CLAUDE-R1-P0-03 之 summary 12 鍵、CLAUDE-R1-P1-04 之 clusters 抽離） | **採納且擴大**。簽名再加 `manifest: EventManifest`。`clusters` 抽成 `build_time_clusters(manifest, bucket_ms)`（行為不變、byte 級一致，保留 `_cluster_weight` 之 M5 mutation seam）。`summary` 之 12 鍵逐鍵來源入 Task 2.1 輸出契約；`insufficient_events_in_test`／`degraded`／`loso_status` 三鍵之投影語意須明寫。 |
| **C6 G-3 golden 會合法化已知錯誤** | P1 | COMPOSER-R1-P1-03、GROK-R1-P1-03 | **採納 grok 之較嚴版**。拆 G-3a／G-3b：G-3a＝一次性遷移報告，落 `handoffs/run_receipts/`，**不進**預設比對綠徑；G-3b＝新投影 vs **獨立 oracle**（`feature_index[plan.row_index]` 直接投影出的 event_id 集合）之集合相等。舊 producer 退出後不得再當正確性參考。composer 之「diff 集合 sha256＋基數上限」併入 G-3a 之報告欄位。 |
| **C7 消費者處置不可執行** | P1 | GROK-R1-P1-04 | **採納**。SPEC Task 3.1 明示：①`split_events` 退出生產呼叫圖（測試釘呼叫點＝0）；②`pattern_bridge`／`baseline`／`tables`／`ic_feed` 為**成員消費者**，型別不變但 G-1／G-3b 須覆蓋其 train／test event_id 集合；③`event_split.py` 可留作 G-3a 對照或 helper 萃取來源，不得再決定邊界。 |
| **C8 mutation 覆蓋不足** | P2 | GROK-R1-P2-01、COMPOSER 必答 7 | **採納聯集**。§D 由 3 條擴為 M-SU-1..12：併入 grok 之 M-SU-4..10 與 composer 之 positional／unmatched／period_trim／unit_normalize 四條，去重後逐條寫「改壞哪一行 → 哪個測試紅」。 |
| **C9 D-002 未寫交叉引用** | P2 | COMPOSER-R1-P2-01 | **採納**。Task 1.1 之 D-002 須寫明「投影所用 `feature_index` 為 **post-trim**（EVTALIGN 裁頭尾之後）之 universe」，並交叉引用 C-2／C-3／C-4。 |
| **C10 投影在事件路徑無落點** | P0 | 主委補 CLAUDE-R1-P0-01（三家皆未提出） | **採納，且為本輪最重之未解項**。碼證：`EventSplitPlan` 唯一 producer ＝ `split_events`，唯一呼叫點 `pipeline.py:691`，唯一生產 caller `case_import_service.py:1610`；該路徑**沒有** `SplitPlan`、也沒有 feature 列 universe（`run_with_params` 不帶 `feature_config` ⇒ `_materialize` 回 `None`）。三家給的簽名都預設呼叫端持有 `feature_index`，但事件掃描端並不持有。⇒ **C-1 需要一個明確的落點裁定**，這是 R2 的唯一必答（見下「R2 待決」）。 |
| **C11 三態＝兩容器，非三值枚舉** | P0 | 主委補 CLAUDE-R1-P0-02 | **採納**。`EventSplitPlan` 本就三態：train／test 在 `assignments`、purged 在獨立 `purged`（`types.py`）。TODO Task 1.2 之 `assignment_states` 改寫為「三態＝兩容器」；purge reason 沿用契約既有字面 `interval_crosses_split_boundary`（`event_import_contract.json:465-467`），**不得**在 `split_unify.json` 另造。 |
| **C12 embargo 兩欄語意懸空** | P2 | 主委補 CLAUDE-R1-P2-07 | **採納**。投影路徑下 `EventSplitConfig.embargo_ms` 與 `embargo_ms_by_symbol` 必須為 `None`，否則 raise；不得靜默忽略（那正是 EVTLABEL `CODEX-R1-P1-02`「算了卻沒人用」的形態）。 |
| **C13 §A 前提不精確** | P2 | 主委補 CLAUDE-R1-P2-08 | **採納**。§A 改寫為「同一批事件、同一次 UAT 會看到兩個互相矛盾的驗證段數字」——兩數分屬兩個 service、兩個 endpoint，不存在單一合併點。 |

### 三家一致、無需修補之項（記錄以免下輪重議）

- **必答 3（多 symbol）**：grok 與 composer 立場一致——**維持 fail-closed**，不在 B3 直接接 per-symbol 投影。
  判準：事件路徑仍走單幣 `_build_holdout_split_plan`（`ic_filter_orchestrator.py:1248-1262` 之
  `next(iter(allowed_symbols))`）；`base_universe_hash` 之多標的語意仍 `needs-research`（§N R-1）。
  ⇒ consult D2 維持。
- **必答 6（B1 獨立）**：兩家一致——B1 值得獨立一批；併入 B2 會讓契約錯誤被演算法討論稀釋。⇒ consult D5 維持。
- **必答 8（消費者盤點）**：兩家一致——`grep -rln EventSplitPlan momentum api` ＝ 7 檔，**無第 8 個**生產消費者；
  `api/services/ic_analysis_service.py:835` 只是註解提及，不 import。主委自查亦確認
  `pattern_bridge.py:113-127` 與 `baseline.py:106` 皆為**成員依賴**（不讀 `clusters`）。

### 🔴 R2 待決（唯一必答）

C10 尚無方案。三個候選，須委員會擇一並給碼證判準：

1. **投影上移到 IC 側**：事件掃描端不再自產驗證段數字，`summary.split` 改
   `{"status":"unavailable","reason":"canonical_split_owned_by_ic_analysis"}`；
   代價＝`event_forward_return_table`（`tables.py:305` 只取 test 段）失去切分輸入。
2. **canonical 邊界下傳**：`EventSplitConfig` 增 `canonical_test_start_ms`／`canonical_train_end_ms`，
   由呼叫端以共用純函式自同一 universe 算出；代價＝兩端 universe（features vs bars）可能不同 ⇒
   邊界仍可能分歧，該分歧須由 G-3a 量出來。
3. **事件掃描端載入同一 feature universe**：代價最大，且 `EventImportService` 目前不碰 FF run。

主委傾向 **2**（最小改動且保留兩端可用），但**必須**先量出「features vs bars universe 的邊界差」——
沒量之前選 2 就是把 C-2 禁止的「第二份算術」換個名字留下來。R2 brief 須帶這條實測要求。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01

**斷言**: 本輪 adversarial review 不具備可啟動的 reconcile 前置條件：所依 consult synth 沒有任何 `RECONCILE-STAMP ... APPROVED`，因此依 `AGENTS.md` Rule 12 必須停止，不能宣稱 SPEC/TODO 已可審或可進 B1。

**碼證**: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` 實跑輸出 `RECONCILE-STAMP FAIL: ... 缺『## 戳記』區段標題(無法界定本體雜湊範圍)`、rc=1；`rg -n 'RECONCILE-STAMP|## 戳記' handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` 無輸出。RECHECK：完成同一 consult session 的核可戳記後重跑上述命令，需 rc=0，再重新派發本輪 review。

**來源摘要**: `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md#409d0d5f01f7`（sha256 `409d0d5f01f7d2af0d37a2308ca5d9849c51c943a78c046d703d9c8046237c8b`）；`AGENTS.md#e4155485e69c`（sha256 `e4155485e69c103c543120c7438797108dae60c9ea64a2fef68507996439c754`）

[BLOCKING] 信心度=High；沒有 `## 戳記` 邊界與三家 APPROVED provenance，機械 gate 無法證明所依設計共識已核可；繼續審查會違反 `STAMP-BLOCKED` 合約。修法：由主委／委員完成合法 reconcile stamp 並通過 `reconcile_stamps_check.sh` 後，再對 SPEC/TODO 逐項產出 R1 findings；本檔不對未完成審查給出零-finding sentinel。

## COMPOSER-R1-P0-01

**斷言**: SPEC C-4／Task 2.1 将投影签名定为 `(train_plan, test_plan, event_index)`，但生产 holdout 的 `SplitPlan.index_kind="positional"`，`row_index` 为 `features_df` 行号；缺 `feature_index` 时 Agent 无法无歧义实现三态归属。

**碼證**: `ic_filter_orchestrator.py:603-619`（`index_kind="positional"`）；`contracts.py:382-383`（`index_kind` 枚举）；SPEC `docs/SPLITUNIFY_SPEC.md:76-77,142` 签名无 `feature_index`。RECHECK: `rg 'index_kind.*positional' momentum/Analysis/ic_filter_orchestrator.py`；对照 orchestrator 事件∩测试段范式 `:3588-3594`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[BLOCKING] 信心度=High。失败模式：实现者把 `row_index` 当 epoch ms 或当 event 序号 ⇒ train/test/purged 全错且 G-1 可能「稳定地错」。修法：签名加 `feature_index: pd.Index`（或 `feature_timestamps: np.ndarray`），文档写明 positional 解析规则；与 `_time_bounds_for_rows`（`:553-558`）一致。

---

## COMPOSER-R1-P0-02

**斷言**: TODO Task 3.1 验收「`tests/momentum/Analysis` failed 数 <= 20」是聚合期望数，允许本票改坏一条测试同时另一条既有红变绿而总数不变 ⇒ 假绿；与 brief 红线及 TODO §0「防假绿」自相矛盾。

**碼證**: `docs/SPLITUNIFY_TODO.md:129-130`（`failed 数 **<= 20**`）；`HANDOFF.md:26-28`（基线 20 failed，三类根因）；brief 必答 5 明文禁止聚合期望数。RECHECK: 读 TODO Task 3.1 验证段；对照必答 5 deselect 方案。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[BLOCKING] 信心度=High。修法：改为 `tests/baselines/analysis_known_failures.nodeids` + `--deselect` 后 rc=0（见必答 5 命令）；并 `diff` 失败集合防清单漂移。

---

## COMPOSER-R1-P1-01

**斷言**: SPEC／TODO Task 2.1 未定义「事件时间戳不在任何 train/test 特征列」时的三态归属，也未要求 ms↔datetime 归一；实现者可能用最近邻 bar 或默认 train，破坏 C-3 与 EVTALIGN 裁切语义。

**碼證**: SPEC `docs/SPLITUNIFY_SPEC.md:144` 仅写「∈ train 列／∈ test 列／皆不在 ⇒ purged」，未写「不在」判定算法；`ic_filter_orchestrator.py:3588-3594` 已有 `asi8` 精确匹配范式但未引用；`alignment.py:87-93` as-of 不保证 post-trim 列存在。RECHECK: 读 Task 2.1 边界栏与 orchestrator `:1210-1213` trim 路径。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[MAJOR] 信心度=High。修法：Task 2.1 边界增「无精确匹配 ⇒ purged；禁最近邻」；实现复用 `_normalize_ic_time_index` + `asi8` 集合比较；加 `test_splitunify_derive.py -k unmatched_timestamp` 与 `period_trim` fixture。

---

## COMPOSER-R1-P1-02

**斷言**: Task 3.1 修改清单未点名 `pattern_bridge.py` 与 `event_split.py`（clusters 源），但 `tables.binary_discrimination_table` 与 `event_forward_return_table` 依赖 `EventSplitPlan.clusters`（`tables.py:194-208,352`）；投影若留空或抄旧 clusters 会使 cluster CI 假绿。

**碼證**: TODO `docs/SPLITUNIFY_TODO.md:124-125` 仅列 pipeline／orchestrator／ic_feed／tables／baseline；`pattern_bridge.py:187-189` 调用 `binary_discrimination_table`；`event_split.py:134-140` 为 clusters 唯一生产公式。RECHECK: `grep -n clusters momentum/Analysis/event_samples/tables.py pattern_bridge.py event_split.py`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[MAJOR] 信心度=High。修法：Task 2.1 明确 `clusters` 由 `manifest.table` + bucket 规则生成（与 assignments 解耦）；Task 3.1 增「验证 pattern_bridge／tables cluster CI 在投影后仍 ok」；mutation M-SU-7。

---

## COMPOSER-R1-P1-03

**斷言**: G-3「双 producer 差集」golden 若只记录「有差」而无 diff 集合 sha256／基数上限，会把「已知不等价」变成「任意差都可接受」，削弱 B3 回归。

**碼證**: SPEC `docs/SPLITUNIFY_SPEC.md:99-100,165-166`（G-3 + 预期有差）；TODO Task 2.2 `:104-105` 同旨但未规定差集比对语义（集合相等 vs 子集）。RECHECK: 读 `freeze_splitunify_golden.py` 实现时要求 `set(diff_ids) == frozen`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[MAJOR] 信心度=Medium。修法：G-3 JSON 存 `diff_event_ids` 排序列表 + `sha256`；比对模式集合不等 ⇒ rc=1；B3 后以 G-1 为主回归。

---

## COMPOSER-R1-P2-01

**斷言**: B1 独立批价值成立，但 SPEC Task 1.1 未要求 D-002 延伸档写明「投影需 post-trim `feature_index`」交叉引用，文件批无法单独消除 P0-01 实现风险。

**碼證**: TODO §B `:33-34`（B1 可独立审）；SPEC Task 1.1 `:116-124` 仅要求 C-1/C-2/C-3 交叉引用，未含索引／trim。RECHECK: `grep feature_index docs/SPLITUNIFY_SPEC.md` → 0。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[MINOR] 信心度=Medium。修法：D-002 增一小节指向 Task 2.1 签名与 EVTALIGN trim；不阻 B1，但应在 B2 前合入 SPEC 修补。

---

ASSUMPTIONS_VERIFIED: `EventSplitPlan` 生产 7 档（`grep -rln`）；holdout `index_kind=positional`（`ic_filter_orchestrator.py:603`）；`split_per_symbol` 仅 cross_sectional（`:903`）；事件路径单 symbol（`:1248`）；orchestrator 已有 ms/datetime 交集范式（`:3588-3594`）
TESTS_RUN: `sha256sum docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md` → 见 **來源摘要** 短 hash；`grep -rln EventSplitPlan momentum api tests` → 7 生产 + 6 测试（与 brief 一致）；**未跑** `tests/momentum/Analysis` 全套（十分鐘級；基线采 HANDOFF 20 failed）
FAILURES_SEEN: none（唯读 review）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: 无（未改码）；建议修补将影响 Task 2.1 函数签名与 B3 gate 命令

STATUS: DONE
## GROK-R1-P0-01

**斷言**: SPEC C-4／Task 2.1 簽名 `(train_plan, test_plan, event_index) -> EventSplitPlan` 不足以實作「事件時間戳 ∈ train／test 之列」：`SplitPlan.row_index` 是對某一 `features_df` 的 positional 索引，plan 本身不帶完整 timestamp 集合（只有首尾 `time_bounds`）；缺 `feature_index`（或等價已還原之 train／test timestamp Index）時無法與現行 IC 選樣（set membership）對齊，且會踩 ms↔DatetimeIndex 靜默錯位。

**碼證**: `contracts.py:378-390`（欄位集）；`ic_filter_orchestrator.py:603-620`（`index_kind="positional"`）；同檔 `:1298` 已必須用 `features_df.index[test_plan.row_index]` 物化 `test_timestamps`；`split_preview.py:63-79` 明文：binary 鍵是 epoch ms、特徵索引常為 DatetimeIndex，不換算則計數恆 0 且不 raise。RECHECK：只傳兩個 `SplitPlan`＋`event_index`、不傳 universe index ⇒ 無法從 `row_index` 還原集合；若改用 `time_bounds` 閉區間，與 `:1298`／`count_binary_classes_in_rows` 的**集合**語意分歧。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[BLOCKING] 信心度=High。會怎麼失敗：Agent 用 `time_bounds` 區間或錯誤單位做 ∈ 判定 → 驗證段成員漂、與 selection_preview／OOS 事件數不一致；或接線時臨時讀 `features_df` 破壞「純函式／單一算術」。  
**確定簽名（本輪立場）**：

```text
derive_event_split_from_plans(
    train_plan: SplitPlan,
    test_plan: SplitPlan,
    event_index: pd.Index,          # 與 feature 同一時鐘；鍵語意＝feature_cutoff（非裸 decision_at）
    feature_index: pd.Index,        # 即 SplitPlan.row_index 所索引之同一 universe
) -> EventSplitPlan
```

成員判定：`ts ∈ feature_index[train_plan.row_index]` → train；`∈ feature_index[test_plan.row_index]` → test；否則 purged。`index_kind != "positional"` ⇒ fail-closed。單位：若 `feature_index` 為 DatetimeIndex，event 鍵須與 `split_preview.py:77-78` 同一換算（asi8//10**6）。等價替代：呼叫端先物化 `train_timestamps`／`test_timestamps`（與 orchestrator `:1298` 同形）再傳入——仍須在 SPEC 寫死，不得只留三參數。

---

## GROK-R1-P0-02

**斷言**: TODO Task 3.1 驗收「`tests/momentum/Analysis` failed 數 **<= 20**」是聚合期望數，無法證偽「本票未新增失敗」——本票改壞 A、既有紅 B 偶然變綠時總數仍 ≤20 會假綠；且觸碰 brief／範本紅線（禁聚合期望數）。

**碼證**: TODO Task 3.1 驗證段原文「failed 數 **<= 20**」；`templates/BRIEF_REVIEW_TEMPLATE.md` §4「禁寫聚合期望數」；brief 必答 5 與 assumed 否證觀測同型。RECHECK：人為讓一條新測試紅、同時 skip／修好一條既有紅 ⇒ 聚合計數可不變。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[BLOCKING] 信心度=High。  
**替代判準（可執行）**：

1. B2／B3 開工前凍結 nodeid 清單（一次實跑產出，不得手抄凑 20）：
   ```bash
   venv/bin/python -m pytest -q tests/momentum/Analysis --tb=no \
     | tee handoffs/run_receipts/splitunify-analysis-baseline.stdout
   # 由 stdout 之 FAILED 行寫入：
   # tests/golden/splitunify/known_analysis_failures.txt   # 每行一個 nodeid
   ```
2. B3 驗收（非事件路徑另跑 G-2）：
   ```bash
   # A) 扣除既有紅後必須全綠
   venv/bin/python -m pytest -q tests/momentum/Analysis tests/momentum/event_samples \
     $(awk '{printf "--deselect %s ", $0}' tests/golden/splitunify/known_analysis_failures.txt)
   # 期望：rc=0（逐條 deselect，不是「failed<=N」）

   # B) 既有紅集合不得默默消失或被替換（集合相等，不是計數）
   venv/bin/python -m pytest -q --collect-only $(cat tests/golden/splitunify/known_analysis_failures.txt) >/dev/null
   venv/bin/python -m pytest -q --tb=no $(cat tests/golden/splitunify/known_analysis_failures.txt) \
     | tee /tmp/splitunify-known-red.stdout
   # 解析 FAILED nodeid 集合 == known_analysis_failures.txt 集合；多或少皆 rc=1
   ```
3. 本票**新增**測試檔（`test_splitunify_*.py`）不得出現在 known 清單，且必須 rc=0。

---

## GROK-R1-P1-01

**斷言**: SPEC／TODO Task 2.1 寫「∈ train／test 之列，皆不在 ⇒ purged」，但未定義事件時間戳**不落在任何特徵列**（兩根 bar 之間、或單位錯位）時的契約；亦未指名 `event_index` 應為 `feature_cutoff` 還是裸 `decision_at_ms`——上游**不保證** decision 落在 bar 上。

**碼證**: SPEC Task 2.1 實作要點／邊界①②③無「非 bar 對齊」條；`ic_feed.py:36` `FEATURE_CUTOFF_RULE = "max_close_ms_le_decision_at"`；`split_preview.py:63-64` 鍵＝feature_cutoff_ms；EVTALIGN 裁頭尾後特徵 universe 可變（`ic_filter_orchestrator.py:362+`／`:1209-1213`）。RECHECK：餵 `decision_at` 落在兩 bar 之間的 ms ⇒ 集合 ∈ 判定進 purged；若 Agent 用 nearest／asof 會改成員且無測試擋。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[MAJOR] 信心度=High。修法：Task 2.1 邊界加④——`event_index` 語意＝與 IC 相同之 feature_cutoff 時鐘；**不在** `feature_index` 集合內 ⇒ **purged**（第三態），禁止 nearest／ffill；單位錯（未換算）⇒ fail-closed raise（對齊 `split_preview` 已踩過的靜默 0 命中坑）。不是「上游保證不會發生」。

---

## GROK-R1-P1-02

**斷言**: Task 2.1 要求產出完整 `EventSplitPlan`（含 `clusters`／`summary`），但公開簽名只有 plans＋`event_index`，不足以重算 `event_split.py` 的 time-cluster（需要 `decision_at_ms`、`timeframe`／`bucket_ms` 與整表事件列）。

**碼證**: SPEC Task 2.1「`clusters`…沿用既有 `event_split.py` 之連通分量，只換輸入」；實際 clusters 建於 `event_split.py:126-140`（讀 table 之 `decision_at_ms`／`timeframe`）；`tables.py:351-359` 消費 `clusters` 做 macro／micro／CI。RECHECK：只給 `event_index`（無 symbol／tf／decision 欄）⇒ 無法得到與現行相同之 `time_cluster_id`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[MAJOR] 信心度=High。修法：簽名再加 `manifest: EventManifest`（或 `events: pd.DataFrame` 最小欄位集）；clusters／summary.degraded 由同一 helper 重算，**只把 split 邊界來源換成投影**；並在 Task 3.1 寫明 `tables.py` 路徑不得因 clusters 空殼而假 `ci.status=ok`（既有 guard `:194-205` 須仍紅）。

---

## GROK-R1-P1-03

**斷言**: G-3「凍結新舊兩套 producer 的差集」若成為長期 CI golden（可比對通過），是把 C-2 已宣告的**已知不等價**合法化成可 `--write` 吸收的基線，無法區分「差集與遷移報告一致」與「投影又漂了一次」。

**碼證**: SPEC §G G-3；TODO Task 2.2 要點 2「**預期有差**…本 golden 記錄的是『差在哪』」；C-2 已證全域≠per-symbol。RECHECK：接線後成員再漂但差集檔同步 `--write` ⇒ 比對模式仍 rc=0。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[MAJOR] 信心度=High。替代：  
- **G-3a（一次性遷移報告）**：舊 `split_events` vs 新投影之差集寫入 `handoffs/run_receipts/`，**不**進預設比對綠徑。  
- **G-3b（長期 golden）**：新投影 vs **獨立 oracle**——`feature_index[train_plan.row_index]`／`[test_plan.row_index]` 集合投影出的 event_id 成員（整數／集合相等）。舊 producer 退出生產後不得再當正確性參考。

---

## GROK-R1-P1-04

**斷言**: 7 個生產端中，SPEC／TODO 對 `pattern_bridge.py` 與 `event_split.py` 的處置不夠可執行：前者是 assignments 消費者（會吃到投影後的 train／test 成員變化），後者仍是 `pipeline.py:691` 的現行邊界 producer；「保留歷史路徑、生產呼叫點＝0」只寫在 TODO 要點，未進 SPEC Task 3.1 修改檔／驗證釘選。

**碼證**: `pattern_bridge.py:114-127` 只讀 `assignments`；`baseline.py:105-107` 同；`tables.py` 另讀 `clusters`；`pipeline.py:691` `plan = split_events(...)`；TODO 3.1 要點 2「呼叫點數＝0」、SPEC Task 3.1 修改檔未列 `event_split.py`／`pattern_bridge.py`。`grep -rln EventSplitPlan momentum api` ⇒ 仍 7 檔，無第 8 個生產消費者。RECHECK：接線後若漏改 `pipeline.py:691` ⇒ 雙邊界仍在；若只改 pipeline 但未測 pattern_bridge 數值差 ⇒ UAT 看到的 pattern OOS  silently 變。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[MAJOR] 信心度=High。修法：SPEC Task 3.1 明示 (1) `event_split.split_events` 退出生產呼叫圖（測試釘 `pipeline`／orchestrator 對 `split_events` 呼叫次數＝0）；(2) `pattern_bridge`／`baseline`／`tables`／`ic_feed` 為**成員消費者**，型別不變但 G-1／G-3b 必須覆蓋其 test／train event_id 集合；(3) `event_split.py` 可留作 G-3a 對照或 helper 萃取，但不得再決定邊界。

---

## GROK-R1-P2-01

**斷言**: TODO §D mutation 僅 M-SU-1..3，擋不住「用 time_bounds 區間取代集合」「缺 train 變二態」「golden 自動 --write」「報告雙 n_test」「非事件路徑 bytes 變」等本票真實失敗模式。

**碼證**: TODO §D 表三列；對照 P0-01／P0-02／C-5／G-2。RECHECK：下列改壞應對應測試紅。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[MINOR] 信心度=High。建議補：

| ID | 改壞哪一行 | 應紅 |
|---|---|---|
| M-SU-4 | 投影只用 `test_plan`（purged∪train 併一側） | `test_splitunify_derive.py -k three_state` |
| M-SU-5 | 成員改 `time_bounds` 閉區間而非 `feature_index[row_index]` 集合 | `test_splitunify_derive.py -k membership_set`（需新增） |
| M-SU-6 | 同時落兩態時靜默取 train | `test_splitunify_derive.py -k dual_membership` |
| M-SU-7 | `freeze_splitunify_golden.py` 比對失敗自動 `--write` | freeze 腳本自證（改一員仍須 rc=1） |
| M-SU-8 | `pipeline.py` 仍呼叫 `split_events` | 呼叫點釘選測試 |
| M-SU-9 | metadata 同時寫舊事件 `n_test` 與 canonical `n_test` | `test_splitunify_disclosure.py` |
| M-SU-10 | 非事件 run 報告 bytes 變 | `freeze_evtlabel_survivor_golden.py`／G-2 |

---

