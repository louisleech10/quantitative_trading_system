# P2DEBT-T2 TODO R2 re-verify — grok — 2026-07-11

Task-id: `p2debt-t2`  
待審: `handoffs/P2DEBT-T2-TODO-DRAFT-R2.md`（R2-CLOSURE）  
對照: `handoffs/P2DEBT-T2-TODO-REVIEW-grok.md`（B1/B2 + M1–M6）  
Scope: repo **read-only**（僅本檔）；**未**讀 codex re-verify；**未**跑 polluting pytest body；**未**寫 `data_cache/`；**未** git checkout/restore。

---

## FACT-RECEIPT（本輪獨立實跑）

### P1 — 16-caller（spot-run 1）

```text
命令: rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort | wc -l
結果: 16
EXIT=0
```

### P2 — `create_feature_factory` pre-impl recount（spot-run 2）

```text
命令: rg -n "create_feature_factory\(" tests/test_feature_factory_e2e.py
結果: 7 行（L36,49,61,78,93,124,138；含 multi_tf L78）
rg -c → 7
_create_e2e_factory: 0（pre-impl）
```

### P3 — 解耦 V8 + dual stamp + GEN + hermetic 缺席（spot-run 3）

```text
count=$(grep -r "from api\." momentum/ | wc -l | tr -d ' '); test "$count" -eq 0
→ count=0 rc=0

rg -c "RECONCILE-STAMP APPROVED \(p2debt-t2 SPEC R4" \
  handoffs/P2DEBT-T2-SPEC-REVERIFY-R4-grok.md \
  handoffs/P2DEBT-T2-SPEC-REVERIFY-R4-composer.md
→ 各 1（雙戳齊；header「雙戳已齊」屬實）

GEN 四檔: 皆 EXISTS
scripts/run_ic_persist_hermetic.sh: 不存在（EXIT=1 預期）
HEAD: 241ab91030dcc0cc87876e517f98213130dd5f90
dirty unique paths: 26（R2 寫 25 勿釘死 — 一致於「重存 pre-dirty」）
```

### P4 — pipefail counterexample + proto

```text
false | tail -1; echo bare → bare_tail_exit=0
set -o pipefail; false | tail -1 → pipefail_tail_exit=1
cd /tmp/p2debt-t2-proto && python3 -m pytest -q → 8 passed
```

### P5 — Task 2.5 post-impl 計數靜態模擬（B2 recheck）

```text
模擬檔: def _create_e2e_factory(): return create_feature_factory()
        + 7 處 body 呼叫 _create_e2e_factory()
rg -c 'create_feature_factory\(' → 1  （與 R2 預期 1 一致）
rg -c '_create_e2e_factory\('   → 8  （def 行 + 7 call-site）
R2 Task 2.5 寫: 預期 helper=7（註「不含 def 行」）但命令未排除 def
→ 字面命令與期望不可同時真（假紅）
```

### P6 — pytest conftest 作用域（NEW plugin gap）

```text
/tmp 實驗（非 repo 污染）:
  fixture 只在 tests/momentum/conftest.py
  → tests/momentum/test_m.py PASSED
  → tests/api/test_a.py ERROR（fixture not found）
  根 tests/conftest 註冊後兩側皆 PASSED

結論: 僅 Task 1.2.3 `tests/momentum/conftest.py` 無法供應
  tests/api/* 與 tests/test_feature_factory_e2e.py 的
  ic_persist_redirect / redirect_patch_set。
```

### P7 — export L125–137 / S9 現況

```text
tests/api/test_export_api.py L125: Path("data_cache/features")
L135: h5py.File(filtered_path, "w")
_export_fixture_filtered_path: 不存在（pre-impl；Task 1.0 目標）
```

**本輪未跑** V1/V2/V6/V7 `pytest --collect-only`（R2 已文件化 inventory 副作用；nodeid 計數沿用 R2 receipt，不重複寫 golden）。

---

## 原 finding 閉合表

| ID | R1 摘要 | R2 修法位置 | 本輪判定 | 證據 |
|----|---------|-------------|----------|------|
| **B1** | Phase 1 要 S1–S11 probe，helper/manifest 延 Phase 2 | Task **1.0** stub S9/S11；1.1 全 S1–S11（含 S10）；§0 Phase 1 可執行性；Phase 2 wiring-only | **CLOSED** | 1.0.1/1.0.2 import 可 probe；Gate 11 probe；2.1 不再「註冊 8」；R1 互斥句已刪 |
| **B2** | 完工 `create_feature_factory` 預期 **0** 與 helper 內 1 次矛盾 | Task 2.5：create **1**、helper call-site **7**；§0 NEW-R4-1 | **STILL-OPEN（殘）** | create=1 已修；**helper 字面 rg 期望 7，def 行也匹配 → 實為 8**（P5） |
| **M1** | `normalize(result)` 未入 Task 3.2 | Task 3.2 全文 + 禁新增豁免 | **CLOSED** | path/mtime only；禁數值/NaN/count/schema 豁免 |
| **M2** | V7 skip 白名單無執法 | Task 3.1 `assert_skips_allowed` + V1/V7 白名單 + fail-closed | **CLOSED** | 規則字面列出；`run_guard` 呼叫；body `:` 為實作骨架非 oracle 刪除 |
| **M3** | V7 路徑回讀 SPEC | Task 3.1 六檔路徑內嵌 | **CLOSED** | 六路徑完整列出 |
| **M4** | 1.4.1 雙模易常駐紅 | 1.4.1 內 monkeypatch PASSED；1.4.2 排除 Gate | **CLOSED** | 表 1.4.1/1.4.2 + Gate 排除句 |
| **M5** | FF-02→I3 canary 空指 | FF-02「分類-only；不新增 canary」 | **CLOSED** | §COVERAGE FF-02 列 |
| **M6** | header 待戳；dirty=22 | 雙戳已齊；dirty 勿釘死 | **CLOSED** | P3 雙 stamp 各 1；dirty 26≠25 且明文勿釘 |

---

## NEW problems（R2 後新發現）

### NEW-B1 — [BLOCKING] Task 2.5 helper `rg` 期望 7 與字面命令不可兼得（B2 殘）  
**信心度: High**

R2 L447–456 註「不含 def 行」期望 7，但命令：

```bash
rg -n "_create_e2e_factory\(\)" … | wc -l   # 預期：7
```

`def _create_e2e_factory():` **含** `_create_e2e_factory()`，post-impl 靜態模擬 **8**（P5）。  
`create_feature_factory` 側預期 1 **正確**。

**會怎麼失敗:** I3/Phase 2 gate 假紅 → 執行端刪 def 或少改 call-site；或改期望/命令造假綠。

**修法:** 二選一寫死：(a) 期望改 **8** 並註 def+7 calls；或 (b) 命令排除 def（如 `rg … | rg -v ':def '` / AST）期望仍 7。

---

### NEW-B2 — [BLOCKING] Plugin / fixture 作用域：僅 `tests/momentum/conftest.py` 覆蓋不到 API 與 root FF e2e  
**信心度: High**

| 事實 | 來源 |
|------|------|
| Task 1.2.3 只派 `tests/momentum/conftest.py` `pytest_plugins` | R2 L349 |
| root `tests/conftest.py` 僅「**若 FF e2e 需**」條件 scope | R2 L260、L727 |
| Phase 2 對 `tests/api/*` 掛 marker / `usefixtures("ic_persist_redirect")`；session polluter 需 `redirect_patch_set` | Task 2.2.5、2.4、SPEC lifecycle |
| pytest **不**載入 sibling `tests/momentum/conftest` 給 `tests/api` | P6 /tmp 實驗 |
| 附錄 A **無** `tests/api/conftest.py` | 29 路徑列 |
| Final §7 `diff` 要求 delta **==** 完整 whitelist（含條件 conftest） | L666–680 vs L727 互斥 |

**會怎麼失敗:** API/materialize/FF e2e `fixture 'ic_persist_redirect' not found` 或 session 無法 resolve plugin；或為過 scope exact-diff 而假觸 conftest / 漏觸 API 註冊。

**修法（TODO 層，不改 SPEC 契約）:**  
明定 **必**在 `tests/conftest.py`（或白名單內等價頂層）註冊 `pytest_plugins` 以供應 API+FF+momentum；**禁止**標成僅 FF 條件。Final §7：delta ⊆ whitelist（或條件檔自 whitelist 動態剔除），禁 exact-equality 強迫假改 conftest。若採 `tests/api/conftest.py` 註冊 → **列入附錄 A**。

---

### NEW-M1 — [MINOR] Task 1.1.9 交叉引用「nested 見 Task 1.3.9」過時  
1.3.9 現為 S11 bypass；nested 為 **1.3.12**。不阻 stamp  alone。

---

## 冷啟動可執行性（R2 後）

| 區段 | 判定 |
|------|------|
| Phase 1（1.0 stub + 1.1–1.4） | **可** — B1 已閉 |
| Phase 2 wiring 表 | **部分** — NEW-B1 錯 rg；NEW-B2 fixture 不可見 |
| Phase 3 harness | **可**（M1–M3 已閉；assert_skips 骨架待填 body） |
| Final §1–§8 獨立步驟 | **結構可**；§7 exact-diff + 條件 conftest **互斥**（併入 NEW-B2） |

---

## 10 類速檢（殘）

1. 矛盾：**有** — helper 7 vs rg=8；whitelist 完整 vs 條件 conftest  
2. 漏項：**有** — API 樹 plugin 註冊路徑未派死  
3. 不可測 gate：**有** — NEW-B1  
4–8. quant/OOM/cache/API/schema：無新增弱化  
9. 測試品質：mutation 表仍完整；skip 執法已入稿  
10. Agent 可執行性：Phase 1 可；Phase 2 **被 NEW-B1/B2 擋**

未發現 digest/NaN/schema 主動弱化；collect-only 副作用與 pipefail 已正確吸收。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: R2 Task1.0+1.1 閉原 B1；create 期望1 閉原 B2 主矛盾；normalize/skip/V7六檔/1.4/FF-02/header 閉 M1–M6；helper rg 期望7 與 def 匹配矛盾（NEW-B1）；momentum-only plugin 不及 api/FF（NEW-B2）；16-caller=16；create pre=7；解耦0；雙戳齊；proto 8p；dirty=26 勿釘
TESTS_RUN: 靜態 rg/grep/git；/tmp/p2debt-t2-proto pytest -q → 8 passed；/tmp conftest scope 實驗；post-impl rg 模擬 create=1 helper=8；0 polluting body；0 collect-only（避 inventory 副作用）
FAILURES_SEEN: none unexpected
SCOPE_CHANGES: none（僅本 re-verify 產物）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: handoffs/P2DEBT-T2-TODO-REVERIFY-grok.md
```

---

## CLOSED / STILL-OPEN 總表

| ID | 狀態 |
|----|------|
| grok B1 | **CLOSED** |
| grok B2 | **STILL-OPEN**（create=0 已修；helper count 殘 → NEW-B1） |
| grok M1 | **CLOSED** |
| grok M2 | **CLOSED** |
| grok M3 | **CLOSED** |
| grok M4 | **CLOSED** |
| grok M5 | **CLOSED** |
| grok M6 | **CLOSED** |
| NEW-B1 | **STILL-OPEN** |
| NEW-B2 | **STILL-OPEN** |
| NEW-M1 | **STILL-OPEN**（minor） |

---

## Verdict

**Verdict: BLOCK — Task 2.5 `_create_e2e_factory` 字面 rg 期望 7 與 def 行匹配後實為 8（B2 殘/NEW-B1）；plugin 僅掛 `tests/momentum/conftest` 無法供應 `tests/api/*` 與 root FF e2e fixture，且 root conftest 被標條件 + Final §7 exact-diff 互斥（NEW-B2）。**

不附 `RECONCILE-STAMP APPROVED`。

TODO R3 至少閉合 NEW-B1 + NEW-B2；NEW-M1 可同輪順手。

STATUS: DONE
