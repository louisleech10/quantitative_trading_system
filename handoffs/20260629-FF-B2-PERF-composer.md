# B2 比對效能設計 — Composer 腿（委員獨立）

> 依 `handoffs/20260629-FF-B2-PERF-PROMPT.md` + Claude 腿 `handoffs/20260629-FF-B2-PERF-CLAUDE.md` + 讀碼 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`。**純設計推理，未跑慢全鏈。**

---

## 結論（定案）

**同意 Claude「分層抽樣比對」主軸，附兩項硬性實作前置與一組具體參數。**

| 元件 | 定案 |
|------|------|
| generate | **維持全鏈兩次**（full + trunc，~20min×2，因果 MR 必要） |
| columns gate | **全集**（僅欄名 set，不讀值）— 交集 + `max(100, 0.1%×\|union\|)` |
| values + NaN mask | **分層抽樣**（見下） |
| warmup mask | **與 values 同一抽樣集** |
| fracdiff MR | **不抽樣**（獨立嚴格路徑，欄數小） |
| 必做 perf 前置 | **parquet 按檔 batch 讀**（每檔讀一次，非每欄讀一次） |

預期：`generate ~40min` + `比對 <2min`（抽樣後 + batch 讀），單測可實際跑綠。

---

## 1. 對 Claude 提案：同意 / 修正

### 1.1 同意

- **因果已三方簽核 PASS**；B2 瓶頸是 **比對 I/O 規模**（`_assert_values_gate_main` 對 ~220k 欄逐欄 `read_parquet`），非正確性缺陷。
- **columns 全集 + values 抽樣** 分工正確：掉欄/整層消失由便宜 columns gate 抓；值因果由抽樣 + mutation 抓。
- **確定性抽樣**（sorted + stride / seeded）符合章程 §0 可重現、§B3 防假綠。

### 1.2 修正（Composer 補強）

**修正 A — 必先 batch parquet（與是否抽樣無關）**

讀碼：`_assert_values_gate_main` L485–517 對**每一欄**呼叫 `pd.read_parquet(full_dir / full_fname)`。同一 parquet 含數千欄時等於重複讀檔數千次 — 這是 >20min 的主因，不僅是欄數。

定案：比對前先 `groupby parquet_fname → List[col]`，**每檔 full/trunc 各讀一次**，在記憶體內對抽樣欄取 slice。此改動 **不改 oracle 語義**（章程 §A10 A7 等價），實作應與抽樣同一 PR。

**修正 B — warmup gate 一併抽樣**

`_assert_warmup_nan_masks_equal` 現亦逐欄全掃；抽樣後應共用 `_build_sampled_columns(...)` 結果，避免 warmup 成新瓶頸。

**修正 C — 覆蓋率守衛改基數**

現：`comparable_columns / len(common_cols) ≥ 0.95`。抽樣後改：

- `comparable_columns / len(sampled_cols) ≥ 0.95`
- `len(sampled_cols) ≥ 3000`（下限；約 80+ 分組 × K=40 的量級，防抽樣函式 bug 空轉）

---

## 2. 分層抽樣：分組鍵 + K

### 2.1 分組鍵（每組至少覆蓋一種算法型別）

**原則**：layer 來自 **parquet stem**（與 production `group_id` 一致，見 `feature_factory._persist_*`）；組內語義來自 **stem 尾綴 + 欄名 suffix**。

| Layer | 分組鍵 `group_key` | 解析規則 | 預估組數 |
|-------|-------------------|----------|----------|
| **L1** | `(L1, category, indicator)` | stem `{tf}_L1_{cat}_{ind}` → parts[2], parts[3] | ~500–800 |
| **L2** | `(L2, category, operator)` | stem `{tf}_L2_{cat}`；operator 從欄名 token 推斷（`momentum`/`ts_rank`/`decay_linear`/`ratio` 等，對齊 `derived_operators`） | ~80–150 |
| **L3** | `(L3, agg, window)` | 欄名 suffix `_{aggLabel}_W{window}`（`rolling_aggregator.add_suffix`） | ~150–250 |
| **L4** | `(L4, lag)` | 欄名中 `lag_{n}` 或 `_lag{n}` 整數 token | ~5–15 |
| **L6/L7 前處理** | `(L65, preprocess_type)` | 欄名 substring：`winsor` / `rank` / `zscore` / `gaussian`；無匹配 → `(L65, raw_passthrough)` | ~5–10 × 窗變體 |
| **L5/L6 meta**（若出現） | `(L5, stem_indicator)` / `(L6, stem_indicator)` | MR config `cross_sectional=False`，組數應極小；仍納入抽樣框架 | 少 |

**L3 chunk 檔**（`1h_L3_rolling_2`）：chunk 編號**不**進分組鍵（語義在欄名 suffix）；避免把同一 `(agg, window)` 拆成假多組。

**未解析欄**：fallback `(layer, "unknown", hash(col)%997)` — 單欄自成組，K=1 全取，不靜默丟棄。

### 2.2 K 與抽樣算法

| 參數 | 值 | 理由 |
|------|-----|------|
| **K_default** | **40** | Claude 30–50 中位；~200 組 × 40 ≈ 8k 欄，batch 讀後秒–分鐘級 |
| **K_small_group** | `min(40, group_size)` | 組內欄數 ≤40 全取，防小組被 stride 跳光 |
| **演算法** | `sorted(cols)` 後 `stride = max(1, n // K)` 取 `cols[0::stride][:K]` | 確定性、無 RNG 漂移；分佈均勻 |
| **seed 錨點**（可選紀錄） | `f"B2-MR-v1|{SYMBOL}|{TIMEFRAME}|{config_hash}"` | 文檔化可重現；stride 已足夠 deterministic |

預期抽樣欄數：**5k–12k**（視 L3 組數），遠小於 220k。

### 2.3 與既有 gate 的銜接

抽樣欄必須 **⊆ common_cols（交集）**；columns gate 仍對全集執行。values / NaN mask / 覆蓋率守衛僅對 `sampled_cols`。

---

## 3. 抽樣會不會放走「單欄洩漏」？

### 3.1 風險邊界（誠實）

| 洩漏類型 | 抽樣能否代表 | 兜底 |
|----------|-------------|------|
| **層級算法 look-ahead**（center=True、shift(-1)、全量 winsor） | **能** — 同一算子作用於整層/整組 | 5 支 mutation 必紅 + 三方因果讀碼 |
| **單一 atomic 指標實作錯**（如 B1 BUG-1/2） | **不能保證** — 屬指標級 | **B1 atomic 差分**（P0-FF-1） |
| **單欄參數邊界**（某一 window 特例） | **機率性** — stride 跨組內 spread | K=40 + 多 window 分組；缺口接受為 B2 scope 外 |
| **mask-only 洩漏**（值同、mask 異） | 抽樣欄若高 fill 仍 exact mask | 高 fill≥95% 欄 mask exact（已定案） |

**論斷**：B2 的 claim 是 **「全鏈 bar 截斷 MR / 因果穩定」**（章程 A2 METAMORPHIC），不是 **「每個 atomic 指標數值 golden」**。在此 claim 下，**同層抽樣 = 同算法族代表** 合理；單欄數值錯誤應由 B1 擋。

### 3.2 mutation 硬保證（足夠）

mutation 注入是 **層級** 的，非單欄：

| 探針 | 影響層 | 抽樣保證 |
|------|--------|----------|
| `center=True` L3 | 全部 L3 rolling | 每 `(L3, agg, window)` 組 K≥1；bug 改變整欄向量 → 必紅 |
| `shift(-1)` L4 | 全部 L4 lag | 每 `(L4, lag)` 組全取或 K≥1 |
| 全量 winsor L6.5 | 全部 winsor 欄 | `(L65, winsor)` 組 K≥1 |
| fracdiff ×2 | 獨立 MR | **不抽樣** |

**不需**額外「mutation 注入欄名白名單」：注入點在算子層，抽樣已覆蓋各算子組。建議加 **sanity assert**（非 oracle）：`sampled_cols` 與 `L3/L4/L65_winsor` 組交集非空，防抽樣函式 regression。

---

## 4. columns 全集 + values 抽樣：是否足夠？替代方案

### 4.1 定案分工（足夠）

| Gate | 範圍 | 成本 | 抓什麼 |
|------|------|------|--------|
| columns | 全集 \|union\| | O(n) 字串 set | 整層/大量掉欄 |
| metadata | 單次 | O(1) | row_count / schema |
| values + mask | ~8k 抽樣 | O(sample × rows) | 因果值穩定 + 高 fill mask |
| warmup | 同抽樣集 | 同上 | 暖機區一致 |
| mutation ×5 + c2_2 | 全鏈 generate | 慢但 P0 | 可證偽 |
| fracdiff MR | 全 fracdiff 欄 | 中 | 校準因果 |

此組合滿足章程 **P0 correctness = MR + mutation**；抽樣僅縮 values 路徑，**不削弱** columns / mutation / fracdiff。

### 4.2 評估過的替代方案

| 方案 | 優點 | 缺點 | 裁定 |
|------|------|------|------|
| **A. 向量化全比（每 parquet 矩陣 allclose）** | 無抽樣遺漏 | L3 ~32 檔 × 5k 欄 × 2k rows，仍數分鐘–十分鐘；float16 容差需逐欄或整矩陣廣播，邊界 case 多 | **不採為預設**；可作 nightly `B2_FULL_COMPARE=1` 選項 |
| **B. pyarrow 批次讀 + 全欄** | I/O 優於 pandas 逐欄 | 仍 220k 欄計算 | 與 A 同級，性價比不如 A+B 組合 |
| **C. 僅縮窗 / 減 atomic** | 加快 generate | 改變覆蓋語義，違 B2「全開」設計 | **拒絕** |
| **D. batch 讀 + 分層抽樣（定案）** | generate 語義不變；比對可控 | 單欄 atomic 不保證 | **採用** |

---

## 5. B2-PERF 實作規格（供實作腿）

```text
# 新增常數（建議）
B2_SAMPLE_K_DEFAULT = 40
B2_SAMPLE_MIN_COLUMNS = 3000
B2_SAMPLE_VERSION = "B2-MR-v1"

# 新增函式
_build_strat_group_key(col, parquet_stem) -> tuple
_build_sampled_columns(common_cols, col_to_parquet) -> List[str]  # deterministic
_assert_values_gate_main(..., columns: Optional[List[str]] = None)  # None = legacy full

# 流程
1. columns gate（全集，不變）
2. sampled = _build_sampled_columns(common_cols, full_map)
3. assert len(sampled) >= B2_SAMPLE_MIN_COLUMNS
4. assert mutation-layer coverage sanity
5. batch read parquets → values + mask + coverage on sampled only
6. warmup gate on sampled only
```

**fracdiff / mutation 測試**：不改 config；mutation 仍走 `_assert_truncation_invariants` → 自動用抽樣邏輯，層級 bug 仍紅。

**CI 標記**：維持 `@pytest.mark.slow`；比對變快後總時間仍 dominated by generate，marker 不動。

---

## 6. 對 prompt 四問的直接回答

1. **分層抽樣**：同意；分組鍵見 §2.1；**K=40**（小組全取）。
2. **單欄洩漏**：B2 claim 下可接受；層級因果由組代表 + mutation；單欄 atomic 歸 B1。
3. **columns 全集 + values 抽樣**：足夠；**必先 batch parquet**；全量比對僅作 optional nightly。
4. **定案**：**batch 讀 + 分層抽樣（§2 分組鍵 + K=40 + mutation 層 sanity）**；generate 全鏈不動；fracdiff 不抽樣。

---

## ASSUMPTIONS_VERIFIED

- 讀碼確認 `_assert_values_gate_main` 逐欄重複 `read_parquet`（L492–493）為比對瓶頸主因。
- 讀碼確認 L3 欄名 suffix 為 `_{agg}_W{window}`（`rolling_aggregator.py`）。
- 讀碼確認 parquet stem 層級命名 `{tf}_L{1-6}_...`（`feature_factory._persist_*`）。
- 未跑全鏈；220k 欄 / 20min+ 比對來自 HANDOFF + Claude 腿 + 程式結構推論。

## TESTS_RUN

none（純設計腿）

## FAILURES_SEEN

none

## SCOPE_CHANGES

none（本腿僅設計文件）

## NUMERIC_OR_SCHEMA_IMPACT

無（設計階段）。實作後：比對欄數 220k → ~8k，**不改變 generate 輸出 schema**。

---

`^SIGN-OFF-STAMP: Composer APPROVED 2026-06-29 B2-PERF-DESIGN`

STATUS: DONE
