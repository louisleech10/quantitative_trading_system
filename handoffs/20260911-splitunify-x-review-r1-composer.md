brief-kind: review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R1
family: composer
findings-round: R1
標的：`docs/SPLITUNIFY_SPEC.md`（commit `08391e4c`）＋ `docs/SPLITUNIFY_TODO.md`（同 commit）

## Verdict：需修補後派工 — **B1 可進**（文件＋枚舉不動生產碼）；**B2 開工前**须修补 Task 2.1 投影簽名（补 `feature_index`／单位归一）与 Task 3.1 验收（禁 `failed<=20` 聚合假绿）。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| positional `row_index` 可在投影内安全还原时间戳 | **assumption，未在 SPEC 钉死** | brief assumed；`_build_holdout_split_plan` 产 `index_kind="positional"`（`ic_filter_orchestrator.py:603`）；EVTALIGN `period_alignment` 裁头尾会移位（`:1210-1213`） |
| `baseline`／`pattern_bridge` 换投影后数值不变 | **assumption** | 两者只读 `assignments.split_label`（`baseline.py:105-107`、`pattern_bridge.py:125-127`）；边界变则 test 成员变 ⇒ OOS 必变；SPEC §N R-2 已登记但未写进 B3 验收 |
| `failed 数 <= 20` 足以挡回归 | **推翻** | 聚合期望数；brief 必答 5 与 `docs/` 红线冲突；见 P0-02 |
| 事件时间戳恒落在特征列上 | **部分 fact** | `alignment.py:87-93` as-of 选 bar；`ic_feed.py:129` 用 `last_bar_open_ms`；与 `features_df.index` 比较须单位归一（orchestrator 已有范式 `:3588-3594`）但未写入 SPEC Task 2.1 |

---

## 必答 1–8（明確立場）

### 1. 投影索引语意／确定签名

**立场：现行 `(train_plan, test_plan, event_index)` 不够；必须同时传入 `feature_index`（或等价的时间戳数组）并在函数内做与 orchestrator 一致的单位归一。**

- `SplitPlan.row_index` 在生产 holdout 为 **positional**（`ic_filter_orchestrator.py:603-604,613-619`），语义是 `features_df` 行号，不是事件 `decision_at_ms`。
- `event_index` 在 IC 路径实为 ms 整数（`ic_feed.py:129` `last_bar_open_ms`）；orchestrator 已用 `pd.to_datetime(..., unit="ms")` + `_normalize_ic_time_index` + `asi8` 交集（`:3588-3594`）——**投影应复用同一范式，不得另写一套**。
- **确定签名（建议写入 SPEC C-4 / Task 2.1）**：

```python
def derive_event_split_from_plans(
    train_plan: SplitPlan,
    test_plan: SplitPlan,
    event_index: pd.Index,      # decision 时间；允许 int64 ms 或 DatetimeIndex
    feature_index: pd.Index,    # features_df.index；positional plan 的 universe
    *,
    manifest: EventManifest,    # clusters 沿用 event_split 时需 decision_at_ms 表
) -> EventSplitPlan:
```

- 实现要点：`train_ts = feature_index[train_plan.row_index]`（positional 时）；`test_ts` 同理；事件经 `_normalize_ic_time_index` 后与 `train_ts`/`test_ts` 的 `asi8` 做集合归属；**同时命中 train 与 test ⇒ raise**（SPEC 已有，保留）。

### 2. 三态边界：事件时间戳不在任何特征列

**立场：归 `purged`（fail-closed 第三态），不是 train/test；须在 SPEC Task 2.1 边界栏与 TODO 2.1 ③ 明示。**

- 上游**不保证**每个事件时间戳都是 `features_df.index` 的成员：EVTALIGN 裁切后 index 宇宙变短（`ic_filter_orchestrator.py:1210-1213`），事件 ms 可能落在被裁掉的 bar 或 as-of 与 holdout 列集无交集。
- `event_split.py` 旧路径用 ms 比较（`:111-117`），不依赖特征列存在；投影若只做 `∈ train列` 而无「无匹配」分支，实现者会误用 `searchsorted` 最近邻 ⇒ **泄漏或错分**。
- **码证**：`alignment.py:87-93` 只保证 `decision_at` 对应某 bar cutoff，不保证该 bar 仍在 post-trim `features_df`；`tables.py:305` test 段只取 `split_label=="test"` 的 event_id——无匹配事件不应静默进 train。

### 3. fail-closed vs 直接走 `split_per_symbol`

**立场：B3 **维持 fail-closed**（与 consult D2 一致），不在 B3 直接接 per-symbol 投影。**

- **判准**：多 symbol 不等价已有 receipt（`20260910T150504Z-splitunify-multisymbol`）；`split_per_symbol` 虽存在于 `ic_filter_orchestrator.py:903-914`，但仅 **`analyze_cross_sectional`** 分支，事件路径仍 `next(iter(allowed_symbols))` 单币 holdout（`:1248-1262`）。
- 直接支援的代价：B3 须同时交付 per-symbol `derive` 循环、`base_universe_hash` 多标的语义（§N R-1 needs-research）、以及 G-4 golden——**超出当前 TODO B3 范围**，且与 Task 3.2「先 raise 后改写」矛盾。
- 更省一次改写？表面是，但会把 D2 的「未证 per-symbol 前禁跑」换成「边做边猜」，回归面更大。**B3 fail-closed 是正确分期；per-symbol 跟 R-1 票。**

### 4. golden G-3 设计

**立场：G-3「双 producer 差集」**有效但仅作 **B2 一次性建档**；不能是无上界的「任何差都合法」。**

- C-2 已证旧事件切分与新投影**不等价** ⇒ 差集 golden 记录的是**已知、有界**的差异，不是把错误合法化。
- 风险：若 golden 只存 diff 而不钉 **diff 集合的 sha256 + 基数 + 逐 event_id 清单**，B3 接線后投影再漂 ⇒ 比对仍绿。
- **替代／加强**：G-3 比对模式要求 `diff_event_ids` 集合与 frozen `tests/golden/splitunify/g3_diff.json` **集合相等**（`==`，非 `<=20`）；B3 之后回归以 **G-1 成员集合** + `test_splitunify_derive.py` 为主，G-3 降级为只读档案（改 diff 须显式 `--write` + commit 说明）。

### 5. B3 验收判准（可执行替代）

**立场：废除 `failed 数 <= 20`；改为「冻结 nodeid 清单 deselect 后 rc=0」+「本票新测全绿」。**

```bash
# 一次性（B1 或 REDSWEEP 收案前）冻结 HANDOFF 20 条 nodeid：
venv/bin/python -m pytest tests/momentum/Analysis --tb=no -q 2>&1 \
  | awk '/^FAILED /{print $2}' | sort -u \
  > tests/baselines/analysis_known_failures.nodeids

# B3 主 gate（逐条可证伪：清单外任一失败即 rc≠0）：
venv/bin/python -m pytest tests/momentum/Analysis tests/momentum/event_samples \
  $(sed 's/^/--deselect=/' tests/baselines/analysis_known_failures.nodeids) \
  -q --maxfail=1

# 本票增量（必须 rc=0，无 deselect）：
venv/bin/python -m pytest -q \
  tests/momentum/Analysis/test_splitunify_contract.py \
  tests/momentum/Analysis/test_splitunify_derive.py \
  tests/api/test_splitunify_disclosure.py

# G-2 不变：
venv/bin/python scripts/freeze_evtlabel_survivor_golden.py
```

- 另加：`diff` 当前失败集合与 `analysis_known_failures.nodeids`（防「一红一绿总数仍≤20」假绿）。

### 6. B1 是否独立一批

**立场：值得独立 B1，不并入 B2。**

- B1 零生产码、可过 `doc_format_precheck` + 契约 JSON 测，review 面纯文档／枚举。
- 并入 B2 的损失：diff 混「SPEC 链 + 纯函数 + golden」，三家 review 无法先钉 SoT 再审算法；违背 TODO §B「可独立审」与 consult D4「先 D-002 延伸档」。

### 7. mutation 表补充（缺项）

| ID | 改坏什么 | 应红测试 |
|---|---|---|
| M-SU-4 | 投影省略 `feature_index`，positional 当下标当 ms | `test_splitunify_derive.py -k positional`（新增） |
| M-SU-5 | 未匹配事件时间戳默认归 `train`（非 `purged`） | `test_splitunify_derive.py -k unmatched_timestamp`（新增） |
| M-SU-6 | B3 生产路径仍调用 `split_events` | `test_splitunify_wiring.py::test_production_calls_split_events_zero`（Task 3.1 已要求钉 0，需 mutation 行） |
| M-SU-7 | `clusters` 未从 manifest 重算、抄旧 plan | `test_splitunify_derive.py -k clusters` + `test_tables.py` cluster CI |
| M-SU-8 | EVTALIGN 裁切后仍用裁前 positional index | `test_splitunify_derive.py -k period_trim`（对照 `period_alignment` fixture） |
| M-SU-9 | 事件 ms 与 feature index 单位未归一（秒/ms 混用） | `test_splitunify_derive.py -k unit_normalize` |

### 8. 漏掉的消费者

**立场：无第 8 个 `EventSplitPlan` 生产 import；但 `pattern_bridge.py` 与 `event_split.py` 处置不够明确。**

- VERIFY：`grep -rln EventSplitPlan momentum api tests` → 生产 7 档（brief fact-verified），与 SPEC 列举差 `pattern_bridge.py`、`event_split.py`（producer／clusters 源）。
- `pattern_bridge.py` 读 `assignments.split_label`（`:125-127`）并经 `binary_discrimination_table` 读 `clusters`（`tables.py:352`）——Task 3.1 应写明「投影后 clusters 仍由 manifest 按 `event_split.py:134-140` 生成，与 assignments 来源解耦」。
- `api/services/ic_analysis_service.py` 仅注释 `split_events`（`:835`），**不** import `EventSplitPlan` ⇒ 非第 8 消费者。

---

## §1 必查摘要

| # | 类 | 结果 |
|---|---|---|
| 1 | 矛盾 | Task 2.1 签名 vs 生产 positional plan（P0-01） |
| 2 | 漏项 | 非特征列事件／pattern_bridge／clusters（P1-02、P1-01） |
| 3 | 不可测 | B3 `failed<=20`（P0-02） |
| 4 | quant | 裁切后 index 漂移、ms/datetime 归一（P1-01） |
| 5 | 过度工程 | 无 |
| 6 | OOM | 无 |
| 7 | cache | 无 |
| 8 | API/型别 | 无 |
| 9 | 测试 | G-3 需有界差集（P1-03）；mutation 表过短（必答 7） |
| 10 | Agent | B2 可执行性受签名缺口影响 |
| 11 | 短命工 | Task 3.2 raise 分支预期被 R-1 改写（SPEC 已写） |

---

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
