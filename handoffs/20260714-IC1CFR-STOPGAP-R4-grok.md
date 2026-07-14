# IC1CFR-STOPGAP SPEC r4 閉合 — Grok(2026-07-14)

**task-id**: IC1CFR-STOPGAP  
**角色**: r3 原 REJECT 委員(grok) r4 重跑  
**對象**: `docs/IC1CFR_STOPGAP_SPEC.md` **v0.4 r4**  
**裁決來源**: `handoffs/20260714-IC1CFR-STOPGAP-RECONCILE.md` r3 輪補記(S-F10~S-F13)  
**模式**: 唯讀(本產出檔 + RECONCILE 戳記行)

---

## 方法(可重現)

| 步 | 證據 |
|----|------|
| 讀 r3 自寫 1B+4NB、RECONCILE r3 補記、SPEC r4 | 文件 |
| 核 pure-tier / force / deep-off 控制流 | `nl` orchestrator:1601-1703、3335-3378 |
| 核 summary 寫入點 | 成功路徑 `:1667`=`completed`；通用 except `:1673-1681`=`skipped`；setdefault `:1694-1696`=`not_run` |
| 核 factory callers | `rg create_factor_return_analyzer` → factories def + `tests/phase26/test_deep_analysis_factories.py` only |
| 核 runner 直例化 | `_run_factor_return:1779-1785` 直 `FactorReturnAnalyzer(...)`，不呼 factory |
| 核 force 在 deep-off 之後 | deep early-return `:1601`；`force_set` 建於 `:1627` 之後 |
| 核 stamp body-hash | `sed -n '1,/^## 戳記$/p' ... \| sed '$d' \| shasum -a 256` → `66db1109…` |

---

## R3-B1 閉合判決 — pure-tier 佔位矛盾 → **CLOSED**

| 檢查項 | r4 文字 | 與碼對齊 |
|--------|---------|----------|
| §C 非顯式開啟 | 含純 intermediate/advanced；tier **不再**是顯式開啟 → `not_run`+無節 | tier 排除 force-true 後 `_is_module_enabled` false → 不入 `run_targets`(:1655-1656) → setdefault `not_run`(:1696) |
| Task1.1 邊界③ | 純 tier→**not_run(非佔位)** | 與上一致；r3 邊界③「tier→佔位」已刪 |
| 顯式開啟僅二途 | `force_modules=["factor_returns"]` 或 override `enabled=true`(**且 deep 開**) | force 在 enabled 檢查前納入 targets；override 走 `config.factor_return.enabled` |
| 測試 oracle | `test_pure_tier_not_run` + M1b mutation drop exclusion→紅 | 可證偽；與選項 B 互斥已消 |
| 不可做 | 不把 pure-tier 當顯式開啟 | 明文 |

**反例複核(構造)**: schema/yaml/API/store 預設 false + tier 排除 `factor_return` 後，`active_preset=intermediate` 無 force/override → 不跑 runner → summary `not_run`、無 `results.factor_returns`。依 r4 寫測會綠；依 r3 邊界③期望佔位會紅——r4 已選前者。

原危害(執行端照字面寫錯測/錯行為)消除。

---

## r3 四 NB 處置

### R3-NB1 — sanitizer 行錨 → **CLOSED**(r3 已關,r4 維持)

Task1.2 仍「`grep -n ...` 定位精確行,r3 不寫死」；覆蓋 API/CSV/AI/Markdown/export_all/反序列化/cache。無回退。

### R3-NB2 — loop `:1667` summary 寫入 → **CLOSED**(升級為可執行機制)

r3 殘差:runner 只 return dict，成功路徑 `:1667` 一律 `completed`。  
r4 定案(S-F11):

1. `_run_factor_return` **raise** `ModuleUnavailableError(reason=...)`（不 compute_batch）
2. 父迴圈在通用 `except Exception`(**`:1673`**) **之前**加專屬 `except ModuleUnavailableError`：寫 §U union + `module_summary=unavailable` + **不** append `deep_analysis_errors` + 不計 completed/skipped

此為唯一觸父迴圈處；與實碼結構相容(專屬 except 先於 BLE001)。`completed_count`/`skipped_count` 現以 status 字串計數(:1698-1702)，`unavailable` 自然不入兩桶。

### R3-NB3 — §A default-off 行錨 → **PARTIAL→殘留 NB**(不升級)

§A:15 仍寫 `:1603-1610` 為「模組未啟用」——該段實為 **deep 整包 off** 全模組 `not_run` 表。同句已補 runner 不入列 `:1651-1657`，且 §C 已對齊 `:1601-1700` 全流。契約正確、錨點措辭仍略混；**不阻實作**。

### R3-NB4 — factory 白名單字面 → **PARTIAL→交實作**(RECONCILE 已裁)

實測 `rg create_factor_return_analyzer`:

- 定義:`momentum/factories.py:451`
- 唯一測試 caller:`tests/phase26/test_deep_analysis_factories.py`
- orchestrator / phase29:**直例化** `FactorReturnAnalyzer`，**不**呼 factory

Task1.3 仍寫「analyzer tests+orchestrator runner」字面偏；RECONCILE r3 補記已裁「factory 白名單字面對 repo 校準(grok R3-NB4 交實作查)」。意圖(阻新 production factory caller + quarantine phase29)可讀；守衛測試實作時白名單應含 phase26 factory 測、勿假稱 orchestrator 呼 factory。**非契約互斥，不 BLOCKING**。

---

## codex r3 四 B 交叉(非本家原訴,r4 連帶核)

| ID | r4 | 判決 |
|----|-----|------|
| CX-1 tier→佔位 | =本家 B1 | **CLOSED** |
| CX-2 unavailable 無寫入者 | ModuleUnavailableError + 父 except | **CLOSED** |
| CX-3 force 跨 deep-off | 收窄:force **不**繞過；deep 關→`not_run`；`test_deep_off_not_run` | **CLOSED**(碼:1601 早於 force_set) |
| CX-4 §G before=`enabled` | 改 before.json 實凍值(成功 fixture=`completed`→`not_run`) | **CLOSED** |

---

## r4 新洞掃描

| 焦點 | 裁定 |
|------|------|
| pure-tier vs 前端 store intermediate 仍 `factor_return:true`(:107/:133/:151) | Task1.1 三處改 false；若只改後端未改 store，UI 仍可能以 modules override 走「顯式開啟→unavailable」(仍無有限葉，fail-close 安全)。不開 B。 |
| `ModuleUnavailableError` 定義檔未釘 | 執行端可放 orchestrator 同檔或既有 errors 模組；測試綁行為即可。**NB 級**。 |
| 專屬 except 後 progress 仍發 `"completed"` 文案(:1684-1689) | cosmetic；summary 已 unavailable。不開洞。 |
| cache hit 後 `module_summary` 仍可能 `completed` 而 results 被 sanitizer 佔位 | composer R3-NB4 殘；M2 以無有限葉為主。**NB 級**，建議 sanitizer 順手映 summary 或 Task1.2 一句。 |
| §G Phase0 / 改寫表未枚舉 | composer 既有 NB；RECONCILE 裁「改寫表草案入 TODO」。TODO=凍結後生(SPEC:3)，**不因缺 TODO 拒 SPEC**(反對 codex R4 以 TODO 缺失作 SPEC REJECT 前置)。 |
| Equity curve 同病 | 複核成立(monotonicity 丟 timestamp + chart 位置 high-low/drawdown)；Task2.2 必要。 |
| long_short 出 scope / analyzer 本體不動 | 維持。 |
| 四處預設 true 行 | schema:173 / yaml:115-116 / ic_models:22 / store:107,133,151 仍真。 |
| singular config vs plural results | 維持警示；force 鍵 `factor_returns` 對 runner 表正確。 |

**新 BLOCKING: 0**

---

## 總評

r4 **完整收下** grok r3 的 1 BLOCKING(pure-tier=not_run)與控制流精化(專屬 except / force 不跨 deep-off / §G 實凍值)。r1→r3 原訴求無復開。殘留皆 NB/實作校準，不阻 freeze。

```
ASSUMPTIONS_VERIFIED: pure-tier not_run 與 :1655-56/:1696 對齊;force 於 deep-off 後;:1667 completed / 專屬 except 可插在 :1673 前;§G completed→not_run;factory callers=phase26 only;phase29 直例化;store 107/133/151;schema:173;stamp body sha256=66db1109…
TESTS_RUN: 靜態 nl/sed/rg/shasum(未跑 pytest;審查票)
FAILURES_SEEN: none
SCOPE_CHANGES: none(唯讀+本產出+RECONCILE 戳記 append)
NUMERIC_OR_SCHEMA_IMPACT: none(審查)
產出檔: handoffs/20260714-IC1CFR-STOPGAP-R4-grok.md
RECONCILE_STAMP: appended (see below)
```

SPEC-REVIEW-R4: APPROVE
