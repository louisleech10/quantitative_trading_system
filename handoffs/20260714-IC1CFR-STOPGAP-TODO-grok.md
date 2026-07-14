# IC1CFR-STOPGAP-TODO adversarial — Grok(2026-07-14)

**task-id**: IC1CFR-STOPGAP-TODO:adversarial  
**對象**: `docs/IC1CFR_STOPGAP_TODO.md`(DRAFT) vs Frozen `docs/IC1CFR_STOPGAP_SPEC.md` v1.0  
**模式**: 唯讀(僅本產出)  
**重點**: ①三態+M1b ②sanitizer 冪等/邊界 ③factory 白名單(R3-NB4) ④gate 離線 ⑤鍵名單複數

---

## 方法(可重現)

| 步 | 證據 |
|----|------|
| 讀 SPEC v1.0 + TODO DRAFT + R3-NB4 自寫 | 文件 |
| factory 呼叫圖 | `rg create_factor_return_analyzer` → def `factories.py:451` + **唯一 caller** `tests/phase26/test_deep_analysis_factories.py` |
| 直例化 | orchestrator `_run_factor_return:1784` / `phase29:30` 皆 `FactorReturnAnalyzer(...)`，**不**呼 factory |
| tier 強制 | `_apply_tier_config:3335` 具名 preset 全 `MODULE_ENABLED_PATHS`→True(`:3371` 區) |
| default-off 控制流 | deep-off 早退 `:1601` 先於 `force_set:1627`；runner 入列 `:1651-1657`；summary setdefault `:1694-1696` |
| gate 腳本 | `mutation_probe_check.sh` 在；`ic1cfr_stopgap_freeze.py` **未建**(Task 0.1)；`check_decoupling.sh` 在 |
| 真-kline | fixture 讀本地 `data_cache/feature_klines/kline_cache.h5`(離線=無外網；本機有檔) |
| 既有斷言撞擊 | `rg long_short_mean_return\|factor_return.enabled is True\|module_summary\["factor_returns"\]` 於 tests/ |

---

## 五點焦點判決

### ① default-off 三態 + M1b → **PASS**(可證偽)

| 契約態(SPEC §C 選項 B) | TODO 測試 | Oracle | 可紅路徑 |
|------------------------|-----------|--------|----------|
| 非顯式(含純 intermediate/advanced) | `test_default_off_not_run` + `test_pure_tier_not_run` | summary=`not_run`+**無** `results.factor_returns` 節 | M1b 拿掉 tier 排除→純 tier 變 enable→跑 runner→`unavailable`→`test_pure_tier_not_run` 紅 |
| 顯式(force 或 override enabled=true **且 deep 開**) | `test_explicit_enable_unavailable`(force+override 兩路徑) | §U union+summary `unavailable`+不入 `deep_analysis_errors`+無有限葉 | M1 恢復 `compute_batch` 直出→紅 |
| deep 全域關 | `test_deep_off_not_run` | force 亦 `not_run`(不跨 `:1601`) | 碼序已釘；假實作 force 繞 deep-off 會紅 |

與 r4 收斂一致；pure-tier **非**佔位。Task 1.1 邊界①–⑤與 §0 三態互斥，無 r3-B1 類矛盾。

**殘差 NB**:pure-tier 構造須**不**帶 `modules.factor_return=true` / store 預設 true 的 API override(否則落入顯式態)。TODO 寫「無 force/override」足夠，執行端勿用完整 frontend payload 當 pure-tier fixture。

### ② sanitizer 冪等 + 邊界 → **PASS 主體 / 驗證枚舉偏軟(NB)**

| 要求 | TODO | 實測對齊 |
|------|------|----------|
| 單一 `sanitize_factor_returns` 冪等 | 有；驗證「佔位再過→不變」 | 可證偽 |
| 節→佔位；summary 三欄→null | 實作要點有(`factor_return_ls_mean/sharpe/max_drawdown`) | 與 reporter `:581-588` 鍵名一致 |
| 掛點 | grep 定位、不寫死行號 | 對齊 SPEC Task1.2 / R2-NB1 |
| 邊界清單 | API/CSV/AI/Markdown/export_all/反序列化/cache `:1633-1637` | 與 SPEC S-F3 同構 |
| M2 | `test_mutation_m2_bypass_sanitizer` | 有牙 |

**NB-S1**:驗證只寫「各輸出格式無有限葉」——未**枚舉**七匯出口斷言(API JSON / summary 三欄 null / detailed CSV / AI JSON / Markdown / export_all / cache-hit 出口)。執行端易只測一條序列化路徑假綠。建議 Task 1.2 驗證表列 7 點(或 parametrize 匯出函式名)。

**NB-S2**:orchestrator cache hit 直 `return cached`(`:1629-1632`)；若 sanitizer 只掛 service/reporter、未掛 cache 出口，同進程舊有限 cache 仍可漏(部署後冷 cache 風險低)。TODO 已點名 cache 行，實作勿漏。

### ③ factory 白名單校準(R3-NB4) → **BLOCKING**

TODO Task 1.3:

> 白名單(**執行端據實際 repo 校準**,grok R3-NB4;**預期=factory 定義+analyzer 自身測試+orchestrator runner**)

| 字面預期 | repo 實況(2026-07-14 `rg`) |
|----------|---------------------------|
| factory 定義 | ✓ `momentum/factories.py:451` |
| analyzer 自身測試 | ✗ `tests/phase24/test_factor_return_analyzer.py` 只直例化，**無** `create_factor_return_analyzer` |
| orchestrator runner | ✗ `:1784` 直例化，**不**呼 factory |
| (未列) phase26 factory 測 | ✓ **唯一** factory 測試 caller=`tests/phase26/test_deep_analysis_factories.py` |

**為何「據 repo 校準」不夠明確(對 ③ 的直接答覆)**:

1. 同句雙指令互斥:「據 repo 校準」vs 錯誤「預期=…orchestrator runner」。
2. Task 1.3 邊界明寫「**白名單常數寫死測試**」——執行端會把「預期」抄進 `ALLOWED` 常數；抄錯則：  
   - 漏 `phase26` → 守衛**自紅**(合規 caller 被拒)；或  
   - 為過測放寬 `tests/**` → gate 失牙。  
3. RECONCILE r3 已裁「R3-NB4 交實作/TODO 校準」；TODO 是釘死校準集的最後一站，卻仍留錯預期。
4. factory-grep **本來就擋不到** orchestrator/phase29 直例化——phase29 靠 quarantine 另線；把 orchestrator 寫進 factory 白名單是**語意錯位**，非校準殘差。

**修法(須寫死，勿再委「執行端自查」)**:

```text
ALLOWED_CREATE_FACTOR_RETURN_ANALYZER_CALLERS = {
  "momentum/factories.py",                              # 定義
  "tests/phase26/test_deep_analysis_factories.py",      # 唯一現況 caller
}
# 明示非 factory-grep 範圍:
# - orchestrator._run_factor_return / phase24 analyzer 測 / phase29 → FactorReturnAnalyzer 直例化
# - stopgap 後 runner = raise, 不 new analyzer；phase29 = SystemExit quarantine
```

grep 範圍維持 TODO 的 `momentum/ api/ scripts/ tests/` 可；**常數集合**必須如上(或 rg 等價集合)，刪錯誤「預期=…orchestrator runner」。

### ④ gate 命令離線可執行 → **PASS**(附條件)

| Gate | 命令 | 離線判定 |
|------|------|----------|
| B0→B1 | `python scripts/ic1cfr_stopgap_freeze.py --before` + shasum | 腳本 Task 0.1 新建；fixture 讀**本地** kline h5+conftest Binance stub → 無外網可跑(本機有 `data_cache/.../kline_cache.h5`) |
| B1→B2 | pytest stopgap+deep + `mutation_probe_check.sh` + freeze `--after` + `check_decoupling.sh` | 腳本/venv 路徑齊；mutation 腳本已存在且離線 |
| B2 | `npm --prefix frontend run test -- "NetIC\|FactorReturn\|FactorEquity"` + build + pytest 三樹 | vitest positional filter=檔名 regex；現僅有 `NetICChart.test.tsx`，2.1/2.2 測試檔名須含 `FactorReturn`/`FactorEquity` 否則 0 tests 紅 |

**NB-G1**:B2 filter 未釘測試檔路徑(建議 `FactorReturnChart.test.tsx` / `FactorEquityCurveChart.test.tsx`)。  
**NB-G2**:`freeze.py` 尚未存在屬 Task 0.1 產物，非 TODO 邏輯洞；B0 順序正確。

### ⑤ 鍵名單複數不混 → **PASS**

| 側 | 鍵 | TODO/SPEC | repo |
|----|-----|-----------|------|
| config/API/store/modules | **單數** `factor_return` | §0 + Task1.1 `ic_models:22` | `ic_models.py:22`、`MODULE_ENABLED_PATHS`、store:107/133/151 |
| results/summary/force_modules | **複數** `factor_returns` | §0 + 邊界 force `["factor_returns"]` | orchestrator:1604/1639/1731 |
| reporter summary 欄 | `factor_return_*` 前綴 | Task1.2 三欄 | reporter:139-141/581-588 |

未見 TODO 內把 API 欄寫成 `factor_returns: bool` 或 force 用單數之混用。

---

## 額外 finding(五點外)

### B2 — §V 前端 mutation 錯位/缺漏 **BLOCKING**

| SPEC §V | 要求 | TODO 落點 |
|---------|------|-----------|
| **M3** | FactorReturnChart：legacy 有限不畫 + 同檔 `test_mutation_m3_render_legacy` | Task **2.1** 僅 vitest 兩斷言，**無** mutation probe |
| **M4** | Equity curve 恒空態 + 同檔 probe | Task **2.2** 有 probe 但命名為 **`test_mutation_m3_render_legacy`**(M3 號被占用) |

反例:2.1 的 `legacy_finite_payload_not_rendered` 可寫成永遠 empty 的弱斷言；無「恢復畫 legacy→紅」探針則假綠。2.2 誤用 M3 id 使覆蓋追溯表「M3→Phase1/2」與 SPEC 表不一致。

**修法**:Task 2.1 加同檔 `test_mutation_m3_render_legacy`；Task 2.2 probe 改 `test_mutation_m4_*`(或對齊 SPEC M4 名)；覆蓋追溯同步。

### NB-R1 — 改寫表未逐筆(SPEC §V/§C⑦)

§0 只寫「逐條附舊斷言為何錯」，未列 grep 命中。已知必撞(非完整):

- `tests/phase24/test_deep_analysis_config.py:33` enabled is True  
- `tests/momentum/test_tier_config.py:31` tier 後 enabled is True  
- `tests/phase26/test_deep_analysis_integration.py` force→`completed` 多處  
- `tests/api/test_ic_deep_analysis.py` 注入 finite `factor_returns`+samples  
- `tests/momentum/test_export_formats.py:154` / `tests/api/test_export_api.py:96` long_short_mean_return  
- `tests/phase26/test_ic_reporter_deep_analysis.py` 有限節  

Gate B2 會自暴露；假綠風險靠 §0 理由條款。建議 TODO 附最小改寫表，非再開條件若 B1/B2 已關。

### 已掃不開洞

- 四處預設 false 行錨(schema/yaml/models/store)與 SPEC 一致；`:193` trend 不動  
- ModuleUnavailableError + 父 except 先於 BLE001 + 不計 completed/skipped — 與碼結構相容  
- long_short_analysis / analyzer·monotonicity 本體不動  
- Equity 獨立同病(位置 high-low)Task 2.2 必要  
- phase29 quarantine 字串足夠  

---

## 總評

三態+M1b、鍵名、gate 離線主路徑、sanitizer 契約主體**可執行且可證偽**。不可 APPROVE 的兩洞:

1. **factory 白名單**:「據 repo 校準」+錯誤預期+「常數寫死」三者打架；R3-NB4 未在 TODO 閉合。  
2. **§V M3/M4**:FactorReturn 缺 probe；Equity 誤掛 M3 號。

```
ASSUMPTIONS_VERIFIED: factory callers= factories def + phase26 only; orchestrator/phase29 直例化; deep-off:1601 before force:1627; tier force-true loop; singular factor_return vs plural factor_returns; reporter 三欄鍵; mutation_probe_check 存在; freeze 腳本未建; kline h5 本地在
TESTS_RUN: 靜態 rg/sed/nl 與 vitest --help(未跑 pytest 全套;審查票)
FAILURES_SEEN: none
SCOPE_CHANGES: none(唯讀+本產出)
NUMERIC_OR_SCHEMA_IMPACT: none(審查)
產出檔: handoffs/20260714-IC1CFR-STOPGAP-TODO-grok.md
```

TODO-REVIEW: REJECT(2 BLOCKING)
