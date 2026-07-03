# G2 pin 斷路器 — Composer 腿

> task-id: `fracdiff-maxlag-g2pin-composer-20260703`  
> 角色：斷路器委員會 Composer 腿（read-only 分析）  
> 輸入：`handoffs/20260703-FRACDIFF-MAXLAG-G2PIN-FACTS.md`  
> 日期：2026-07-03

---

## ① 事實 6 實碼驗證：config_override → FeaturePreprocessor 解析鏈

### 結論：**成立**。`fractional_differencing.max_lag` 在 pydantic 驗證階段被靜默丟棄，`_preprocessing_config_dict` 產出的 dict **不含** `max_lag`；preprocessor 永遠走 auto 分支。

### 解析鏈（附行號）

| 步驟 | 檔案:行號 | 行為 |
|------|-----------|------|
| 1. 入口 | `feature_factory.py:237-251` | `generate_features(..., config_override=...)` → `_resolve_config(config_override)` |
| 2. 合併+驗證 | `feature_factory.py:3686` → `config_manager.py:90-100` | `get_merged_config(api_override)`：`deep_merge(base, user, api_override)` 後 `FactoryConfig.model_validate(merged)` |
| 3. schema 缺口 | `feature_config.py:183-191` | `FractionalDifferencingConfig` **無** `max_lag` 欄位；**無** `model_config extra="allow"`（預設 `extra=ignore`） |
| 4. 巢狀丟棄 | `feature_config.py:241` | `PreprocessingConfig.fractional_differencing: FractionalDifferencingConfig` — 巢狀驗證時未知鍵 `max_lag` 被 ignore |
| 5. dict 化 | `feature_factory.py:2746-2747` | `_preprocessing_config_dict(config)` = `copy.deepcopy(config.preprocessing.model_dump())` — **只 dump 已知欄位** |
| 6. 實例化 | `feature_factory.py:3198-3200`（CGSA persist 路徑）等 | `FeaturePreprocessor(preprocessing_config, ...)` |
| 7. 讀值 | `feature_preprocessor.py:144` | `self.fracdiff_config = self._config.get("fractional_differencing", {})` — 無 `max_lag` 鍵 |
| 8. auto 分支 | `feature_preprocessor.py:3198-3200` | `.get("max_lag", 0)` → 0 → `min(max(2, len(df)//10), 252)` |

補充：`FactoryConfig` 頂層有 `extra="allow"`（`feature_config.py:490`），但**不向下繼承**；`max_lag` 巢狀在 `fractional_differencing` 內，仍被丟棄。

### 實跑驗證（本腿 session）

```text
FractionalDifferencingConfig.model_validate({'enabled': True, 'max_lag': 50}).model_dump()
→ 無 max_lag 鍵；hasattr(fd, 'max_lag') == False

ConfigManager().get_merged_config({'preprocessing': {'fractional_differencing': {'max_lag': 50}}})
→ preprocessing.model_dump()['fractional_differencing'] 無 max_lag

_preprocessing_config_dict 等價輸出：max_lag in fracdiff dict → MISSING
```

與事實檔 #2/#3 一致：G2 freeze script `config["preprocessing"]["fractional_differencing"]["max_lag"]=50`（`freeze_fracdiff_maxlag_golden.py:87-90`）寫入 override dict，但經步驟 2→5 後消失 → d\* payload `max_lag=208`（`2081//10`）。

### 影響升級

- **現行 HEAD 任何 config_override / YAML / API 路徑都 pin 不了 max_lag**（除非繞過 pydantic，如直接 `create_feature_preprocessor(dict)`）。
- 2026-06-29「pin=50 d\* 全同」實驗能成立，因繞過 factory pydantic 鏈（事實檔 #6 假設與本驗證吻合）。
- **Task 1.2 必要性升級**：schema 加欄位前，production「顯式 max_lag」逃生口是幽靈欄位。

---

## ② G2 產法裁決

### 裁決：**選 A**（freeze script dict 層注入 + 強制防呆斷言），並建議採 **D 變體** 作為收斂增強（見下）。

| 選項 | 立場 | 理由 |
|------|------|------|
| **A** | ✅ 採用 | 事實 6 已證：HEAD 上無真 config 路徑可產 G2。A 在 **唯一 production 讀值點**（`:3198`）注入 `max_lag=50`，可產 numerically distinct 的 G2 baseline，且不混入 Phase 1 commit。 |
| **B** | 不採 | 先上 Task 1.2 再凍 G2 語意上較乾淨，但 G2 不再是「pre-fix HEAD」；還需額外證明 1.2 在 `max_lag=0` 時零數值影響。對解當前斷路（已燒 40 分鐘）成本偏高。 |
| **C** | 不採 | 放棄 G2 使 §G 條件 1「修後 auto vs 同窗顯式 50」失去 **pre-fix 錨點**；只能事後雙對照，無法直接證明「變更純由窗寬造成」的因果鏈。 |
| **D（建議增強）** | A + 事後交叉驗證 | **Phase 0**：A 產 G2 + 斷言（下節）。**Task 1.2 落地後**：用真 config 路徑重跑 G2'，斷言 G2' digest == G2（A 產物）。一舉驗證注入等價 **且** schema 修復後 config 路徑可用。 |

### A 的風險（自認）

1. **注入層錯誤 → 靜默無效**（本輪已發生）：必須 run 後斷言，不可只靠 override 字串。
2. **多 preprocessor 實例**：factory 內 `:2235`、`:2635`、`:3200` 等多處 `FeaturePreprocessor(...)`；須 wrap `__init__` 或在 **實際跑 fracdiff 的實例** 上注入，不能只改 override dict。
3. **config_hash 不區分 G1/G2**：`max_lag` 不進 hash（`_compute_config_hash` 用 pydantic dump）；靠獨立 d\* cache 目錄隔離（已有），receipt 須記 `resolved_max_lag` / `fracdiff_hash`。
4. **不等價於「完整 production config 語意」**：warmup_window（`:292`）等仍讀 pydantic，不受 dict 注入影響；§G oracle 看 feature 值，Task 1.3 已論證 row count 不受 warmup 252 fallback 主導，**可接受**。

### A 必備防呆（freeze script / helper）

跑完每 symbol 後 **FAIL-FAST**（缺一即 `RuntimeError`）：

1. d\* payload `resolved_max_lag == 50`
2. d\* `fracdiff_hash !=` 同 symbol G1
3. `compare_golden_digests`：`fracdiff_different_count > 0` 且 `non_fracdiff_different_count == 0`（`ff_maxlag_golden_helpers.py:167-174` 已有邏輯，本輪缺的是前置 pin 斷言導致 5626 欄全等才爆）

---

## ③ 挑戰 Claude 腿（A + dict 注入 + 防呆）的等價論證

Claude 核心主張：dict 注入與「config 若通會交付的東西」在 `:3198` **byte 級等價**，等價閉合於單一 read site。

### 可接受的部份

- **fracdiff 數值路徑**：`:3198` 是 `_apply_fractional_differencing` 唯一 `max_lag` 推導入口；注入 `fracdiff_config["max_lag"]=50` 與 Task 1.2 後 `model_dump()` 含 `max_lag: 50` 在該點行為一致。
- **d\* cache / transform**：`max_lag` 自 `fracdiff_config` 傳入（`:3207-3273`），單點注入可覆蓋。

### 漏洞與未閉合點

| # | 挑戰 | 嚴重度 |
|---|------|--------|
| 1 | **「單一 read site」過窄**。`warmup_window.py:292-295` 從 `pp.fractional_differencing.model_dump().get("max_lag")` 讀值；dict 注入不更新 pydantic。Claude 未宣稱 warmup 等價，但若有人把「production 等價」推廣到全鏈，會過度陳述。 | 中（§G 值 oracle 不受影響，但論證範圍須寫死） |
| 2 | **「config 若通」是反事實**。HEAD 上 config **不通**（事實 6）；等價是對 **Task 1.2 之後** 的 config 行為，不是對現行 override 字串。應改述為：「與 **修復後** schema round-trip 交付的 dict 在 `:3198` 等價」。 | 低（表述精確化） |
| 3 | **注入時機 / 物件生命週期**。`_preprocessing_config_dict` 做 `deepcopy`（`:2747`）；在 `config_override` 裡寫 `max_lag` **無效**。須在 `FeaturePreprocessor.__init__` 內對傳入 `config` dict 變異，或 post-init 改 `instance.fracdiff_config`。包 `__init__` 比「factory 建好後、generate 前」更穩——factory 不暴露內部 preprocessor。 | **高**（本輪失敗根因類型） |
| 4 | **防呆斷言必要但不充分**。`max_lag==50` + `fracdiff_hash!=G1` 證明 pin 生效，**不證明**注入點是 `:3198` 而非其他旁路；若未來新增第二推導點，A 可能假綠。Task 1.1 `_resolve_fracdiff_max_lag` seam 落地後，B-2 mutation 覆蓋更完整。 | 中 |
| 5 | **config_hash 相同**。G1/G2 artifact 路徑相同 `config_hash`；依賴獨立 d\* 目錄。若操作者誤共用 cache 目錄，可能 cross-run 污染（非 A 獨有，但 receipt 應標 `g2_injection_method`）。 | 低 |

**總評**：Claude 的 **數值等價**（fracdiff 欄）論證在 §G oracle 範圍內**基本成立**，但「byte 級等價」應限縮為「`:3198` 處 `fracdiff_config.get("max_lag")` 讀到 50」，並明確排除 config/schema/warmup 路徑。最大實務漏洞是 **#3 注入層**——與本輪 G2 失敗一致，非理論問題。

---

## ④ SPEC §G 文字修改建議

### §A 新增已驗證事實

```markdown
10. config_override 中 `preprocessing.fractional_differencing.max_lag` 經
    `ConfigManager.get_merged_config` → `FactoryConfig.model_validate` →
    `_preprocessing_config_dict`（`feature_factory.py:2746-2747`）後 **不在**
    preprocessor dict 中（`FractionalDifferencingConfig` 無該欄位，`feature_config.py:183-191`；
    pydantic 巢狀預設 extra=ignore）。實跑：`get_merged_config({'preprocessing':
    {'fractional_differencing': {'max_lag': 50}}})` → model_dump 無 max_lag
    （Composer G2PIN session 2026-07-03）。
    → 現行 HEAD **無法** 僅靠 config_override pin max_lag；Task 1.2 為必要非裝飾。
```

### §G run contract 修訂

1. **G2 pre-fix 產法**（HEAD 未含 Task 1.2 時）：

```markdown
(G2) 現行 HEAD 計算行為 + 有效 max_lag=50。因 schema 無 max_lag（§A#10），
**不得** 僅依 `config_override` 宣告 G2；須使用核准注入 seam（freeze script 內
`FeaturePreprocessor.__init__` wrapper 或等價）在 preprocessor dict 寫入
`fractional_differencing.max_lag=50`。receipt 必填 `g2_injection_method` 與
`resolved_max_lag`（來自 d* payload，非 override 字串）。
```

2. **G2 pin 生效門檻**（寫入通過條件前段）：

```markdown
G2 凍結每 symbol **前置斷言**（FAIL 則整輪 abort）：
- d* payload `max_lag == 50`
- d* `fracdiff_hash` ≠ 同 symbol G1
- `compare_golden_digests`：`fracdiff_different_count > 0` 且
  `non_fracdiff_different_count == 0`
未過斷言不得寫入 G2 receipt，不得進入 §G 條件 1 對照。
```

3. **條件 1 語意澄清**（避免讀成 G1 vs G2）：

```markdown
條件 1：修後預設（fresh cache，resolved max_lag = calibration-derived）vs **(G2)**
（pre-fix HEAD + 有效 max_lag=50）fracdiff 欄 per-column sha256 全欄一致。
**不是** G1 vs G2 一致——G1（auto len 耦合）與 G2（pin 50）應 **不同**。
```

4. **resolved max_lag 記錄**：

```markdown
(G1) receipt 必記 **實測** resolved max_lag（例：窗 2081 bars → 208），禁止硬編 60。
```

5. **D 變體（可選 Phase 3 條目）**：

```markdown
Task 1.2 完成後：以真 config `max_lag=50` 重跑 G2'，斷言與 pre-fix 注入 G2
canonical digest 全欄一致（交叉驗證注入 seam 與 schema 路徑等價）。
```

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - 事實6 pydantic 丟棄 max_lag：實跑 + 原始碼鏈路追蹤（見 §①）
  - FractionalDifferencingConfig/PreprocessingConfig 預設 extra=ignore（非 allow）
  - _preprocessing_config_dict 僅 model_dump 已知欄位

TESTS_RUN:
  - python3 實跑 FractionalDifferencingConfig / ConfigManager.get_merged_config（見 §①）
  - 原始碼 Read/Grep：feature_config.py, config_manager.py, feature_factory.py,
    feature_preprocessor.py, freeze_fracdiff_maxlag_golden.py, ff_maxlag_golden_helpers.py

FAILURES_SEEN: none（分析任務）

SCOPE_CHANGES: none（read-only）

NUMERIC_OR_SCHEMA_IMPACT: none（分析任務；裁決建議 A 不改 production schema）
```

HANDOFF_NOT_UPDATED: read-only 分析任務，依合約不覆寫根 HANDOFF.md

STATUS: DONE
