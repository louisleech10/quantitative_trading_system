# IC1CFR-STOPGAP-TODO r3 閉合審查 — Grok(2026-07-14)

**task-id**: IC1CFR-STOPGAP-TODO  
**對象**: `docs/IC1CFR_STOPGAP_TODO.md`(DRAFT r3) vs Frozen SPEC v1.0 + RECONCILE T-S1~T-S12  
**模式**: 唯讀(僅本產出 + APPROVE 時 RECONCILE 戳記行)  
**依據**: r1 grok REJECT(2B)=B1 factory 白名單 / B2 M3·M4 正名

---

## 方法(可重現)

| 步 | 證據 |
|----|------|
| 讀 TODO r3 + RECONCILE + r1 grok + SPEC §V/§G | 文件 |
| factory callers | `rg create_factor_return_analyzer momentum api scripts tests` → def `factories.py:451` + **唯一 caller** `tests/phase26/test_deep_analysis_factories.py` |
| direct `FactorReturnAnalyzer(` | `factories.py:454` / `orchestrator:1784` / `phase24/test_factor_return_analyzer.py` / `phase29:30`(待 quarantine) |
| M3/M4 落點 | TODO Task 2.1/2.2 + 覆蓋追溯 L86 |
| 前端 gate 命令 | 三檔具名路徑(L21);vitest 4.1.5 整串 literal 問題已避開 |
| body-hash | `sed -n '1,/^## 戳記$/p' ...RECONCILE.md\|sed '$d'\|shasum -a 256` → `7bf42307…e8bd` |

---

## r1 兩條 BLOCKING 閉合核對

### B1 factory allowlist 凍死 → **CLOSED**

| r1 要求 | r3 落點 | 實測對齊 |
|---------|---------|----------|
| 勿「執行端自由校準」 | Task 1.3「allowlist 凍死勿留執行端自由校準」+ B0 凍 `factory_allowlist.txt` | 文字釘死 |
| factory caller={phase26 唯一} | Task 1.3:`factory caller allowlist={tests/phase26/test_deep_analysis_factories.py}`(定義不算 caller) | `rg` 唯一 caller=phase26 ✓ |
| 勿把 orchestrator 寫進 **factory** 白名單 | Task 1.3 不可做:「不把 orchestrator 寫進 factory 白名單」 | 語意分離 ✓ |
| direct consumer 另掃 | 允許=`factories.py:454`+orchestrator `_run_factor_return`(:1780-1785)+phase24 analyzer 測 | `rg FactorReturnAnalyzer(` 命中集一致(另 phase29 走 quarantine) ✓ |
| B0/測試共用正規化 | Task 1.3 scanner 規則 B0 artifact 與測試同一份 | 可執行 |

與 RECONCILE T-S7 + r3 T-S11(補 :454)一致。r1 互斥指令(錯預期 orchestrator∈factory 白名單 + 據 repo 校準)已消除。

### B2 M3→Task2.1 / M4→Task2.2 正名 → **CLOSED**

| SPEC §V | r1 洞 | r3 落點 |
|---------|-------|---------|
| M3 FactorReturnChart + `test_mutation_m3_render_legacy` | Task 2.1 無 probe | Task 2.1 驗證:**同檔 M3 probe `test_mutation_m3_render_legacy`**(恢復畫 legacy→紅) |
| M4 equity + probe | Task 2.2 誤掛 M3 號 | Task 2.2:**`test_mutation_m4_render_legacy_equity`**(T-S3 正名) |
| 覆蓋追溯 | 「M3→Phase1/2」錯位 | L86:**M3→Task 2.1、M4→Task 2.2** |

---

## r3 新洞掃描(T-S9~T-S12 與全域)

| 主題 | 判決 | 說明 |
|------|------|------|
| T-S9 sanitizer 路徑+七掛點具名 | PASS | 檔定死 `momentum/Analysis/factor_return_sanitizer.py`;七類+冪等具名測試表列(a–g) |
| T-S10 `--check-nodeids` | PASS | B2 機械差集;suite=`tests/momentum|api|phase26` 與 B0 同規則;禁人工豁免 |
| T-S11 direct allowlist +454 | PASS | 見 B1 |
| T-S12 前端 vitest 分檔 | PASS | 三獨立路徑;含將新增的 FactorReturn/FactorEquity test 檔 |
| T-S1~T-S8(r2 保留項) | PASS | canonical hash/M3-M4/types 真改/after-explicit/§V 改寫表/factory 凍死/nodeid 皆在 r3 可見 |
| 三態+M1b/鍵名單複數 | PASS | §0+Task1.1 邊界①–⑤;config 單數/results 複數未混 |
| long_short / analyzer 本體不動 | PASS | §0 不動清單 |

### NON-BLOCKING(不阻 APPROVE)

1. **NB-P29**:Task 1.3「刪除 **或** 頂部 SystemExit」—若保留 `FactorReturnAnalyzer(` 行,驗證 `rg consumer⊆凍結集` 與固定允許集(無 phase29)可能互斥。建議實作優先**刪檔**,或 B0/scanner 對 quarantine 腳本有共用豁免規則(寫進 freeze 正規化,勿執行端臨場發明)。
2. **NB-AFTER-DEFAULT**:Task 0.1 正文詳述 `--before`/`--after-explicit`,`--after-default` 比對語意依 SPEC §G(非 FR path 等值+FR 節缺席+summary `not_run`+計數排除)。Gate 已要求 exit 0;執行端須以 Frozen SPEC §G 為 oracle,勿只 dump 不比。
3. **NB-CACHE-MERGE**:§0 點名 full cache-hit return(:1632)必 sanitize;force 非空時 `:1635-1636` 併舊 base 後 `:1707` 返回未單列。default-off 後新 cache 無有限 FR;殘留 in-proc legacy 仍靠 API/reporter 邊界。實作可一併 sanitize 最終 return 更穩,非 TODO 必改條件。
4. **NB-DRIFT-Wording**:canonical 仍有「等漂移欄」;T-S1 已舉 time/generated_at/error timestamp,SPEC §G 另列 completed_count 等。實作凍精確 JSON-path 排除表即可。

未發現等同 r1 級、會迫使自由校準或假綠的 **新 BLOCKING**。

---

## 總評

r1 **2 BLOCKING 全關**;r3 對 T-S9~T-S12 與 factory/M3-M4 正名可證偽且與 2026-07-14 repo `rg` 一致。殘差皆 NB,可進實作。

```
ASSUMPTIONS_VERIFIED: factory caller 唯一=phase26; direct consumers=factories:454+orchestrator:1784+phase24+phase29; M3→2.1/M4→2.2 文字+覆蓋追溯; sanitizer 路徑+七測名; check-nodeids 機械差集; 前端三檔 gate; RECONCILE body sha256=7bf423071cb5d04454916f234b3c168d91724542c992e5aca98b5b8a8722e8bd
TESTS_RUN: 靜態 rg/sed/shasum(未跑會寫 baseline 的 pytest/freeze;審查票)
FAILURES_SEEN: none
SCOPE_CHANGES: 產出本檔 + RECONCILE 戳記一行;未改 docs runtime tests data_cache HANDOFF.md
NUMERIC_OR_SCHEMA_IMPACT: none(審查)
產出檔: handoffs/20260714-IC1CFR-STOPGAP-TODO-R3-grok.md
```

TODO-REVIEW-R3: APPROVE
