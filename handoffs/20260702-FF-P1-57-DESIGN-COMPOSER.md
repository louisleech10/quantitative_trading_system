# P1-FF-5 + P1-FF-7 測試設計 — Composer 修訂版（挑戰 Claude 獨立版）

> 藍圖：`handoffs/20260627-FF-AUDIT-RECONCILE.md` 第 5/7 項。  
> 對照：`handoffs/20260702-FF-P1-57-DESIGN-CLAUDE.md`（Claude 獨立版，待戳記）。  
> 方法：逐字讀 Claude 版 + 藍圖 + 讀碼（`feature_factory._reference_data_cache`、`DStarCache`、`talib_wrapper`、`FeaturePreprocessor` 多路徑、`feature_storage` float16）。  
> 真實 kline：`data_cache/feature_klines/kline_cache.h5`；correctness 缺檔 **FAIL 非 skip**（P0-FF-4）。

---

## 0. 對 Claude 版的總判

| 維度 | Claude 版 | Composer 裁決 |
|------|-----------|---------------|
| 方向 | P1-FF-5 三跑 MR + P1-FF-7 wrapper/多路徑/float16 | **保留方向，收斂 scope、補威脅面、硬化探針、降成本** |
| 與現有測試 | 未充分對位 V-7 / P0-FF-1 / P1-FF-6 | **必須寫清「不重測 / 升級 / 另批」邊界，避免雙重或假覆蓋** |
| 探針 | M5.1/M7.x 描述偏抽象 | **不足；需具名 patch 點 + 不對稱注入（align 探針教訓）** |
| 成本 | 3× 全鏈 ~1.5h | **可降：分 tier + 2 慢跑 + 快測補 order** |
| §D 三問 | 留空 | **下方 §1 直接作答** |

**核心修正**：Claude 把 P1-FF-5 當「從零發明 MR」，但 repo 已有 failopen **V-7**（短窗 hash + 同 factory 順序 + cold/hot）。P1-FF-5 的增量價值是 **bar 級 parquet 值 + d* json + manifest schema**（非整表 hash），以及 **production 窗長（600 bar）+ fracdiff-on 子 MR**。若只做 Claude 版三跑全鏈而不升級 V-7 語意，會 **重疊且仍漏 L5 reference / d* 磁碟 alias / batch 並行** 等面。

---

## 1. 答 Claude §D 三問

### D1 — V5.1 三跑可否縮為兩跑（only-A vs [B,A]）仍保威脅覆蓋？

**不能单靠两跑替代三跑；可拆 tier 降成本。**

| 威脅 | only-A vs [B,A] | 三跑（only-A / [A,B] / [B,A]） |
|------|-----------------|----------------------------------|
| B 存在使 A 值漂移（同 factory 先 A 后 B） | ✅ | ✅ |
| B 先跑污染 rolling / cache，再跑 A | ❌ 测不到 | ✅ [B,A] vs only-A |
| 顺序 [A,B] vs [B,A] 对 A 不对称 | ❌ | ✅ run₂ vs run₃ |
| 累积污染（A→B→A 第三遍） | ❌ | 部分；V-7 `test_v7_cross_symbol_same_factory` 已盖 |

**Composer 定案（成本/覆盖折中）**：

1. **慢测（`@slow`，600 bar，排 mutation 后）**：**2 全链 generate** — `run_solo(A)`、`run_batch_same_factory([B,A])`（B 先跑再 A，最强污染序）。  
   - 断言：`solo(A) ≡ batch(B,A) 的 A 工件`（值 / d* / manifest）。  
   - **不再单独跑 [A,B]**：若 solo≡batch(B,A) 且 batch 内 B 在 A 前，已覆盖「B 先污染」；[A,B] 对 A 的额外信息在因果链上弱于 [B,A]。

2. **快测（分钟级，同窗，同 factory）**：从 V-7 升级 — **三序** `[A]`、`[A,B]`、`[B,A]`，断言 A 的 **canonical hash + 抽 20 栏 parquet 值**（非仅 hash）。补慢测遗漏的 order 对称性，成本 ≪ 全链。

3. **不可**把三跑全链缩成两跑且 **删除** 快测 order 三元组 — 会漏 D1 表第二、三行。

### D2 — V7.2「路径证据断言」用什么机制最不脆？

**不用 log capture**（格式变、级别、async worker 会假绿/假红）。

**定案：monkeypatch 入口 sentinel counter + config 强制 + 输出等价（三层）**

```python
# 示例：L6.5 polars 路径
_calls = {"polars": 0, "numba_fast": 0, "pandas_slow": 0}

def _counting_polars(self, df):
    _calls["polars"] += 1
    return _orig_polars(self, df)

monkeypatch.setattr(FeaturePreprocessor, "_transform_single_polars", _counting_polars)
# config: fracdiff off, polars_enabled()=True
result = pre.transform(frame)
assert _calls["polars"] >= 1
assert _calls["numba_fast"] == 0  # 互斥路径
```

| 层 | 入口（具名） | 用途 |
|----|-------------|------|
| L3 rolling | `RollingAggregator._compute_*` → `fused_rolling_stats` | numba vs pandas fallback |
| L6.5 fast | `FeaturePreprocessor._transform_single` 内 numba shard 分支 | `can_use_numba_fast=True` |
| L6.5 polars | `FeaturePreprocessor._transform_single_polars` | `polars_enabled()` 且 fracdiff off |
| L6.5 slow | `_apply_fractional_differencing_serial` | fracdiff on 时 polars **必须不走** |

**Mutation M7.2**：patch sentinel 目标为 no-op，但 config 声称 polars → `assert _calls["polars"]==0` **必须在 raises 外**（verify-gate v2 定式）。

**禁止**：patch 引擎选择函数令其返回固定值却不跑真实计算 — 那只测 patch，不测 prod  wiring。

### D3 — Claude 漏了哪些跨 symbol 污染面？

读码后 **至少 8 面**，Claude §A 仅隐含 cache key / rolling，§D 点 L5/registry 但未入设计：

| # | 污染面 | 代码锚点 | Claude 覆盖 | 本修订 |
|---|--------|----------|-------------|--------|
| 1 | L5 reference fetch 缓存 | `feature_factory._reference_data_cache[(ref_symbol, tf)]` | ❌ | V5.5 + M5.2 |
| 2 | d* 磁盘路径 / payload | `DStarCache._build_path` → `d_star_{symbol}_{tf}_{fhash}.json` | 部分 V5.2 | V5.2 + M5.1 |
| 3 | d* value_aliases 跨栏重用 | `DStarCache._value_aliases[strong_fp]` | ❌ | V5.2b + M5.3 |
| 4 | 同 factory `_d_star_cache_shared` 跨 TF chunk | `feature_preprocessor` L1647–1698 | ❌ | 快测 fracdiff-on 子 case |
| 5 | CGSA work_dir / shard 串路 | `ColumnGroupRegistry(tmp_path / f"{symbol}_{tf}")` | V5.4 弱 | V5.6 path 断言 |
| 6 | batch API 并行 worker 共享 env | `FFACT_MULTI_TF_PARALLEL`、subprocess worker | ❌ | V5.7 optional nightly |
| 7 | L5 启用时 A 的 reference= B | `cross_sectional.reference_symbol` | ❌ | V5.8 独立 case |
| 8 | 类级 registry 突变 | `TALibWrapper.INDICATOR_REGISTRY`（mutable class dict） | ❌ | 归 P1-FF-7 / 静态 audit |

**不纳入 P1-FF-5 主 MR**（另批/已有）：`test_cgsa_multi_symbol_isolation` 纯 shard 合成；P1-FF-6 专责 d* cache key mutation 与 P0-FF-2 fracdiff xfail 闭环。

---

## 2. P1-FF-5 修订 — 跨 symbol 计算值隔离 MR

**新档**：`tests/feature_engineering/test_ff_cross_symbol_isolation_mr.py`  
**helpers**：`tests/feature_engineering/ff_cross_symbol_helpers.py`（复用 `ff_truncation_mr_helpers` 的 B2 gate、`_bar_window_dates`、`read_d_star_json`）

### 2.1 威胁模型（扩充）

多 symbol **顺序/共存** 改变 symbol A 的：

- L1–L7 **特征值**（非仅 hash）
- L6.5 **d\***（磁盘 json + 内存 export）
- **manifest**（行数、栏集、dtype 声明）
- **工件路径** 不含 B 的 symbol 串（弱）；**数值** 不含 B 价格语义（强）

**合法共享**：全局 config、TA-Lib 只读公式、跨 run 相同 kline 窗定义。

**非法**：A 的 rolling 状态、cache 命中 B 的 d*、reference 缓存错 symbol、CGSA 写错 work_dir。

### 2.2 符号与窗

- A=`BTCUSDT`，B=`ETHUSDT`，tf=`1h`
- 窗长：**600 bar**（对齐 B2 `FRACDIFF_MIN_BARS`；主 MR config **fracdiff off** 降时；fracdiff 子 MR **fracdiff on**）
- 每 run **独立** `tmp_path / run_id / {symbol}/d_star/`（防磁盘串档假绿）

### 2.3 Config 分轨

| 轨道 | config | 目的 | 标记 |
|------|--------|------|------|
| **主 MR** | `_values_gate_mr_config_payload()`（与 B2 相同：全 atomic、L6.5 winsor/rank/zscore/gaussian，**fracdiff off**） | 值隔离，~20min/run | `@slow` |
| **d* 子 MR** | `_fracdiff_mr_config_payload()` | d* 跨 symbol 隔离 | `@slow` + 可合并进 P1-FF-6 探针套件 |
| **快测 order** | `_fast_cross_symbol_config()`（V-7 同源 `_fast_config_payload`，14d 窗） | order 三元组 | default |

### 2.4 不变量（对 A 的工件）

**V5.1 值（主 MR）**  
- 对比 `solo(A)` vs `batch_same_factory([B,A])` 的 A：  
- 复用 B2 `_assert_values_gate_main` 逻辑：**交集栏 × [warmup:end) × both-non-NaN**，`rtol=2e-3, atol=1e-12`；float16 栏用 `FLOAT16_RTOL`。  
- **禁止**整表 hash 作唯一 oracle（章程 A3）。

**V5.2 d\***（d* 子 MR）  
- 读 `d_star_{A}_{tf}_*.json` 的 `entries` → `{column: d_star}` dict，两跑 **键集相等 + 值 abs≤1e-12**。  
- 断言 cache 文件名含 `BTCUSDT` 且 **不含** `ETHUSDT`。

**V5.2b value_aliases 不交叉**  
- 若 B 跑完再跑 A：A 的 json 内 `value_aliases` 的 `source_column` 不得出现 B 专属栏名前缀（`ETH` 相关 L1 栏）。

**V5.3 metadata**  
- `FeatureStorage` manifest：列数、schema_hash、primary_tf **相等**（manifest 时间戳栏位列入 allowlist，与 V-7 一致）。

**V5.4 无渗漏（加强）**  
- 工件路径 / parquet 栏名 / json 键：不含 `ETHUSDT` 字串。  
- **加**：A 的 L1 `close` 衍生栏与 solo run 逐值一致（防 B 价格数学渗入）。

**V5.5 L5 reference（条件）**  
- config：`cross_sectional.enabled=True`, `reference_symbol=B`（当 A≠B）。  
- 断言：A 的 L5 栏 **存在且** solo(A) with ref=B 与 batch 内 A 一致（测 reference cache 不错配）。

**V5.6 CGSA path**  
- `FFACT_USE_CGSA=1` 时，A 的 shard 路径必须在 `.../BTCUSDT_1h/` 下，不得 under `ETHUSDT_1h`。

**V5.7 并行 batch（nightly，可选）**  
- 模拟 batch API：`FFACT_MULTI_TF_PARALLEL=1`，两 symbol worker 交错；断言 V5.1 仍成立。PR 不挡，nightly 挡。

**V5.8 快测 order 三元组**  
- 同 factory、同窗：`[A]`、`[A,B]`、`[B,A]` 三次 `generate_features`；A 的 hash + 20 栏 sample 全等。

### 2.5 Mutation 探针（≥3，章程 B1）

**形状**：正向断言在 `pytest.raises` **外**；探针过 `mutation_probe_static` + receipt。

| ID | 注入（不对称） | 预期 |
|----|----------------|------|
| **M5.1** | `monkeypatch.setattr(DStarCache, "_build_path", lambda cd, ctx, fh: cd / "d_star_shared.json")` — **仅去 symbol** | V5.2 必红 |
| **M5.2** | wrap `FeatureFactory._layer5` 内 cache：key 改为 `(timeframe,)`  drop symbol | V5.5 或 V5.1 必红 |
| **M5.3** | `DStarCache.set` 时把 `context.symbol` 覆写为 B | V5.2 必红 |
| **M5.4**（可选） | L3 `fused_rolling_stats` 用 global list 累积上一 symbol 末值 | V5.1 必红 |

**禁止**对称注入（full+trunc 双端同偏置）— P0-FF-3 align 探针无牙教训。

### 2.6 与现有测试关系

| 现有 | 关系 |
|------|------|
| failopen V-7 | 快测 **升级** 为 V5.8；保留 V-7 hash 测试不删 |
| `test_cgsa_multi_symbol_isolation` | 纯 shard 合成；**不替代** 本 MR |
| P1-FF-6 | d* key mutation **专责**；本档 M5.1 与 P1-FF-6 共享 helper，避免双实现 |
| B2 truncation MR | 复用 gate 常数与 `_assert_values_gate_main`；**不**混跑同一 pytest 模块（OOM） |

### 2.7 成本

| 项 | Claude | 修订 |
|----|--------|------|
| 慢测全链 | 3× ~1.5h | **2× ~1h**（solo + batch(B,A)）+ d* 子 MR 2× ~40min |
| 快测 | 无 | 3× ~3min（同窗） |
| 序列 | mutation 后 | **不变** |

---

## 3. P1-FF-7 修订 — wrapper / 多路径 / float16

**新档**：`tests/feature_engineering/test_ff_wrapper_paths.py`  
**原则**：**不重复 P0-FF-1**（`test_atomic_differential` 已 16 指标 talib 对照）；本批补 **残余 + 多引擎 + 存储层 float16**。

### 3.1 威胁模型（收紧）

1. **Wrapper 残余**：registry 中 **未** 进入 P0-FF-1 `_DIFF_CASES` / `C12` 表的指标 — source/price 映射错。  
2. **多路径静默分歧**：L3 numba、pandas；L6.5 polars、numba fast、serial slow — **同输入** 输出超容忍。  
3. **float16 未明示**：`feature_storage._coerce_persistence_array` roundtrip 超 `FLOAT16_MAX_REL_ERROR` 仍写 float16。

### 3.2 V7.1 残余 wrapper audit（静态 + 动态）

**静态**  
- `TALibWrapper.list_indicators()` − P0-FF-1 已测集 − `C12_EXCLUDED`（price_transform）− `computed_in_adapter=True` → **残余集 R**。  
- 对 R 中每个 `input_type != single`：assert `_prepare_inputs` 使用的 OHLC 列与 `talib_input_semantics` 表一致（已有 `test_prepare_inputs_equivalence` 模式，**parametrize R**）。

**动态（真 kline 短窗，单指标）**  
- 对每个 r ∈ R：`swap(high, low)` → 输出 **must change**（finite 区至少 1% 点）；`swap(close, open)` 对 close-only 指标 must change。  
- 餵错 `input_type`（如 BETA 用 close,volume 当 hl）→ 与 canonical oracle **不等**。

**Mutation M7.1**：patch `_prepare_inputs` 对 RSI 返回 `open` 数组 → differential 必红（**raises 外** assert 失败）。

**不重测**：BETA/CORREL/BUG-1 双 oracle — 引用 `test_bug1_beta_correl.py`。

### 3.3 V7.2 多路径等值（矩阵，非全链）

**显式矩阵**（每格：unit/integration，分钟级）：

| 域 | Path A | Path B | 已有 | 本批 |
|----|--------|--------|------|------|
| L3 rolling | numba `fused_rolling_stats` | pandas `RollingAggregator` fallback | `test_numba_rolling.py` | 补 **9-window × 10 agg** 一条参数化 smoke 指向 prod wiring |
| L6.5 winsor/rank/zscore | numba fast | serial pandas | `test_causal_winsor`, `test_perf_winsor_identical` | **integration**：真 kline 500 行，config 强制 `can_use_numba_fast` |
| L6.5 无 fracdiff | polars | legacy pandas | `test_causal_winsor` L258 | sentinel + 逐值 atol=1e-6 |
| L6.5 fracdiff on | serial | parallel joblib | 部分 | **仅断言 polars 未调用**（fracdiff 禁 polars） |

**路径证据**：§1 D2 sentinel；每个 test **必须** `assert calls[target] >= 1`。

**Mutation M7.2**：强制 `polars_enabled=True` 但 patch `_transform_single_polars` 为 `lambda s,f: f`（走 pandas）且 sentinel 计数 polars=0 → 测试 **必须 fail**（证明 sentinel 有效）。

**禁止**：Claude 版「每个有多引擎的计算全链逐值」— 范围爆炸且与 P0-FF-1/L3 现有 differential 重复；**矩阵缺格 = BLOCKING spec 缺陷**，非 silent skip。

### 3.4 V7.3 float16 lossy 明示

**测点**：`FeatureStorage` 持久化层，非特征公式。

- 从真 kline 生成 **短窗** 特征，`persist=True`，读 parquet metadata dtype。  
- 对 dtype=float16 的栏：`abs(stored - float32_source) / max(abs(source), 1e-12) <= 1e-3`（对齐 `FLOAT16_MAX_REL_ERROR`）。  
- 对超界栏：必须 fall back float32（`feature_storage` 已有逻辑）— assert metadata 为 float32。  
- **文件化**：测试 docstring 引用 `FLOAT16_MAX_REL_ERROR` 为合约，非 doc-only。

**Mutation M7.3**：patch `FLOAT16_MAX_REL_ERROR = 1.0` → 半数栏应 fail tolerance assert。

### 3.5 白名单（合法差异）

| 差异 | 理由 |
|------|------|
| polars vs pandas NaN 位置 off-by-1 于 window 边界 | min_periods 实现差；**仅限 warmup 区** |
| skew/kurt atol=1e-4 | 已有 `test_numba_rolling` 先例 |
| fracdiff 启用时 polars 路径缺失 | **设计如此**；测「未调用」非「相等」 |

---

## 4. 验证策略（共通）

### 4.1 分级

| Tier | 内容 | CI |
|------|------|-----|
| PR | V5.8 快测、V7.1 静态、V7.2 单元矩阵、M7.1 | 必跑 |
| Nightly | P1-FF-5 慢测 2×、d* 子 MR、V5.7 并行 | `run_with_receipt` |
| Post-mutation | 同上 + 全部 M5/M7 | 序列，4h timeout |

### 4.2 verify-gate 接線

- 全部慢测 / 探针：`run_with_receipt` + claim checker。  
- 探针：`mutation_probe_static` 扫描 raises 外断言。  
- 先单测快验再全套（align oracle 教训）。

### 4.3 副作用还原

- `git checkout -- tests/golden/l65/test_inventory.txt` + tier2 还原。  
- 长测后清 pytest 旧轮次（HANDOFF 33GB 事故）。  
- 不动 production；不放宽既有断言。

### 4.4 依赖与顺序

```
P0-FF-3 mutation 探针真红 → P1-FF-5/7 慢测 → P1-FF-6 d* epic（max_lag 修复后可收紧 V5.2）
```

P1-FF-5 d* 子 MR 在 **max_lag epic 完成前** 可 `xfail(strict=True)` 仅 **跨 symbol 同值** 部分，理由须写「已知 max_lag(len) 耦合，非隔离失败」— 与 P0-FF-2 d* gate 区分。

---

## 5. Claude 版逐条挑战摘要

| Claude 条目 | 问题 | 修订 |
|-------------|------|------|
| A 三跑全链 | 成本高；[A,B] 信息冗余 | 2 慢跑 + 快测三元组 |
| A M5.1 模糊 | 「patch 缓存键或 rolling」不可执行 | M5.1–M5.3 具名 + 不对称 |
| A V5.4 字串 | 无牙；漏数值污染 | V5.4 + L1 close 衍生 |
| A 未列 L5 | §D 提到未设计 | V5.5 |
| B V7.1 diff B1 | 手工 diff 易漏 | 自动化 `list_indicators − tested` |
| B V7.2 全链 | 与 P0-FF-1/L3 重复；polars/fracdiff 互斥未写 | 显式矩阵 + sentinel |
| B V7.2 log 证据 | 脆 | sentinel counter |
| B V7.3 未锚定 | 未引用 storage 常数 | 锚定 `FLOAT16_MAX_REL_ERROR` |
| C 慢测 1.5h | 可优化 | §2.7 |

---

## 6. 验收命令（实现后）

```bash
# PR 快径
pytest tests/feature_engineering/test_ff_cross_symbol_isolation_mr.py -k "fast or order" -q
pytest tests/feature_engineering/test_ff_wrapper_paths.py -k "not slow" -q

# 慢测 + receipt（mutation 后）
run_with_receipt --task-id ff-p1-57-slow -- \
  pytest tests/feature_engineering/test_ff_cross_symbol_isolation_mr.py -m slow -q
run_with_receipt --task-id ff-p1-57-wrapper-slow -- \
  pytest tests/feature_engineering/test_ff_wrapper_paths.py -m slow -q

# 探针
mutation_probe_static tests/feature_engineering/test_ff_cross_symbol_isolation_mr.py
mutation_probe_static tests/feature_engineering/test_ff_wrapper_paths.py
```

---

## 7. 待 Codex / Claude 反挑战

1. V5.5（L5 ref=B）是否应并入主 MR config 还是永远独立 case？  
2. d* 子 MR 在 max_lag epic 前 xfail 是否削弱 P1-FF-5 签核？建议：主 MR（fracdiff off）仍可先签，d* 随 P1-FF-6 闭环。  
3. V5.7 并行 batch 是否提升为 PR 必跑（真实 batch API 路径）？

---

ASSUMPTIONS_VERIFIED: DStarCache._build_path 含 symbol token（`_d_star_cache.py:327-331`）；V-7 已有同 factory 三序但仅 hash（`test_failopen_correctness.py:988-1061`）；B2 values gate 常数（`ff_truncation_mr_helpers.py:45-62`）；fracdiff 启用时 polars 不走（`feature_preprocessor.py:224-226`）；float16 合约在 `feature_storage.FLOAT16_MAX_REL_ERROR=1e-3`  
TESTS_RUN: none（设计-only）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（设计-only）

STATUS: DONE
