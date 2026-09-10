# SPLITUNIFY B2b R3 收斂審 — COMPOSER

task-id: 20260911-SPLITUNIFY-B2-REVIEW-R3  
family: composer  
findings-round: R3  
審查對象: commit `a8474406` — `split_preview.py`、`split_projection.py`、`event_split.py`、`test_splitunify_derive.py`、`handoffs/20260911-splitunify-b2b-mutate.py`

## 必答

### 1. I1–I6 逐條閉合判定

| 群集 | R2 修法 | R3 判定 |
|------|---------|---------|
| **I1** `feature_index` 嚴格遞增 | `assert_epoch_ms_array(..., strictly_increasing=True)` 只套 index 路徑（`:108-117`、`_index_as_ms:91-93`、`holdout_boundary:224-226`） | **閉合** — 探针 F 全同值、R2 ⑨ 重复、⑧ 反序皆 BLOCKED；`test_unsorted_feature_index_is_fail_closed`／`test_duplicate_feature_index_timestamps_is_fail_closed` |
| **I2** NaN 静默转 0 | cast 前 `np.isfinite`（`split_preview.py:80-86`） | **閉合** — R2 探针 cutoff NaN、测试 `test_nan_in_numeric_index_is_fail_closed` |
| **I3** `event_id` 重复 | `event_keys` 与 `manifest.table` 各自验唯一（`split_projection.py:247-253`） | **閉合** — `test_duplicate_event_id_is_fail_closed`；mutation M-SU-23 rc=1 |
| **I4** float `row_index` | `assert_positional_rows` cast 前验整数性（`:133-141`） | **閉合** — R2 探针 ③、测试 `test_float_row_index_is_fail_closed`；M-SU-24 rc=1 |
| **I5** 事件栏完整性 | `_assert_event_keys_wellformed`（`:146-168`） | **閉合** — R2 探针 ⑦、测试 `test_inverted_answer_window_is_fail_closed`；M-SU-25 rc=1 |
| **I6** `bucket_ms <= 0` | `time_cluster_bucket_ms` 正值检查（`event_split.py:54-55`） | **閉合** — R2 探针 ⑤⑥、`test_non_positive_bucket_ms_is_fail_closed`；M-SU-26 rc=1 |

### 2. 换一批负向注入（实跑输出）

命令：`venv/bin/python /tmp/composer_r3_neginject.py`（脚本见 `/tmp/composer_r3_neginject.py`）。

| 注入项 | 结果 | 实跑输出摘要 |
|--------|------|----------------|
| A `symbol=None` | **未挡** | `PASS_THROUGH assignments.symbol=None, summary.n_symbols=0, per_symbol_n={}` |
| B `symbol=''` | **已挡** | `BLOCKED ValueError: multi_symbol_projection_unsupported: 事件 symbol [''] 与 plan symbol ['ETHUSDT'] 不一致` |
| C symbol 混型别 str+int | **已挡** | `BLOCKED ValueError: ... 事件 symbol ['12345', 'ETHUSDT'] 与 plan symbol ['ETHUSDT'] 不一致` |
| D `manifest.summary` 缺 `n_events_raw` | **已挡** | `BLOCKED KeyError: 'n_events_raw'` |
| E `time_bounds` 与 `row_index` 不一致 | **未挡** | `PASS_THROUGH split_label=train`（membership 走 row_index 集合，SPEC C-4 设计） |
| F `feature_index` 全同值 | **已挡** | `BLOCKED ValueError: ... 时间戳非严格递增——第 1 个位置重复（共 99 处）` |
| G 超大 `bucket_ms` | **未挡** | `PASS_THROUGH n_clusters=1 weights=[0.333...,0.333...,0.333...]`（合法：全事件同簇） |
| H cutoff 恰在 `test_start_ms` | **未挡** | `PASS_THROUGH split=['test'] purged=0`（集合成员：恰在 test 第一根 bar） |
| I cutoff 恰在 `train_end_ms` | **未挡** | `PASS_THROUGH split=['train'] purged=0` |
| J 两事件同 `feature_cutoff_ms` | **未挡** | `PASS_THROUGH n_assign=2 splits=['train','train']`（I1 刻意放宽事件栏） |

R2 九条复验（同脚本尾部）：`未如预期者 = 0 / 9`（VERIFY: 与 `handoffs/20260911-probe-splitunify-negative-injection.py` 一致）。

### 3. `strictly_increasing` 只套 `feature_index` 对吗？

**对。** 码证：`split_preview.py:69-71` 注释与 `_assert_event_keys_wellformed:159` 明确事件栏可重复；J 探针两事件同 cutoff 正常产出双 assignment，membership 用 `cutoff in train_ms` 集合语义不受影响。若对事件栏加单调性会误挡「两事件同一根 bar」——主委 R2 实作当场踩到。**未留洞**。

### 4. 可否进 B2c

**可以。** I1–I6 逐条闭合；R2 九条负向注入 9/9 全挡；换批注入无 P0/P1 漏网。残差 `COMPOSER-R3-P2-01`（`symbol=None`）为 P2，不挡 B2c golden 五组。

### 复验（主委命令）

| 命令 | 结果 |
|------|------|
| `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` | **43 passed**, rc=0（须先确保 mutation 未脏化工作区；本轮回 restore 后实跑） |
| `venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` | **UNCOVERED=0**, 21 条 + C0 全 rc=1/0, mutate_rc=0 |
| `venv/bin/python handoffs/20260911-probe-splitunify-negative-injection.py` | **9/9 全挡**（R3 脚本内嵌复验） |
| `bash scripts/check_decoupling.sh` | **R2=1 R3=17 R4=3**（与 baseline 一致；脚本 exit 1 因 R2/R4 既有债，计数匹配 brief） |

---

## COMPOSER-R3-P2-01

**斷言**: `event_keys.symbol=None` 时第三道 symbol 守卫被跳过（`None` 被 filter 掉），derive 可产出 `assignments.symbol=None` 且 `summary.n_symbols=0`，fail-open 而非 fail-closed。

**碼證**: `split_projection.py:214` `if s is not None` 过滤后 `symbols` 为空集，`:235` `if symbols and ...` 不触发；实跑 A `symbol=None: PASS_THROUGH ... n_symbols=0`。RECHECK: `venv/bin/python /tmp/composer_r3_neginject.py` 看 A 行。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#cfd519d61cf8

[MAJOR] 信心度=High；B2c golden 恒有合法 symbol 故不阻 golden 五组；B3 per-symbol 接线上游若漏填 symbol 会静默产出空 `per_symbol_n` 而非 raise。**不挡 B2c**；建议 B3 checklist 补 `symbol.isna()` gate 或把 `None` 视同无效 symbol 参与 exact-set 比对。

---

## Verdict

**可进 B2c。** I1–I6 全闭合；R2 九条 + 换批十项负向注入均无 P0/P1 漏网；`strictly_increasing` 只套 `feature_index` 正确。残差 `COMPOSER-R3-P2-01` 为 P2 记录，不阻 B2c。

STATUS: DONE
