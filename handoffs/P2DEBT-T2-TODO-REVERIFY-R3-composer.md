# P2DEBT-T2 TODO R3 re-verify — composer — 2026-07-11

Task-id: `p2debt-t2`  
待審: `handoffs/P2DEBT-T2-TODO-DRAFT-R3.md`（Grok R3 斷路器修訂；對照 `handoffs/P2DEBT-T2-TODO-DRAFT-R2.md` Composer R2 + `handoffs/P2DEBT-T2-TODO-REVERIFY-grok.md` NEW-B1/B2/M1）  
Scope: repo **read-only**（僅本檔）；**未**跑 polluting repo pytest body；**未**寫 `data_cache/`；**未** git checkout/restore。

---

## FACT-RECEIPT（本輪獨立實跑）

### P1 — Task 2.5 pre-impl（repo 現況）

```text
命令: rg -n '_create_e2e_factory\(\)' tests/test_feature_factory_e2e.py
結果: （無匹配）
rg rc=1；| wc -l → 0

命令: rg -n 'create_feature_factory\(\)' tests/test_feature_factory_e2e.py
結果:
36:    factory = create_feature_factory()
49:    factory = create_feature_factory()
61:    factory = create_feature_factory()
78:    factory = create_feature_factory()
93:    factory = create_feature_factory()
124:    factory = create_feature_factory()
138:    factory = create_feature_factory()
| wc -l → 7
rc=0
```

### P2 — Task 2.5 post-impl 靜態模擬（/tmp，非 repo）

```text
模擬: 在 _load_data 前插入
  def _create_e2e_factory():
      return create_feature_factory()
  並將 7 處 body 的 create_feature_factory() → _create_e2e_factory()
  寫入 /tmp/p2debt-t2-ff-sim-composer.py（body_replacements=7）

命令: rg -n '_create_e2e_factory\(\)' /tmp/p2debt-t2-ff-sim-composer.py | wc -l | tr -d ' '
結果: 8
匹配: L15 def 行 + L40,53,65,82,97,128,142（7 call-site）
rc=0

命令: rg -n 'create_feature_factory\(\)' /tmp/p2debt-t2-ff-sim-composer.py | wc -l | tr -d ' '
結果: 1（僅 L16 helper return）
rc=0

命令: set -o pipefail; rg -n '_create_e2e_factory\(\)' /tmp/p2debt-t2-ff-sim-composer.py | rg -v ':def ' | wc -l | tr -d ' '
結果: 7
pipefail_rc=0
```

**結論（P1+P2）**：R3 Task 2.5 字面主 gate 期望 **8**（1 def + 7 call-site）與 `create_feature_factory()` 期望 **1** — **獨立複驗成立**。

### P3 — pytest plugin 作用域（/tmp/p2debt-t2-cscope4；pytest 8.4.2）

```text
架構: tests/fixtures/ic_persist_redirect_plugin.py 提供 ic_persist_redirect fixture
      tests/momentum|api/test_*.py + tests/test_ff.py 各一測試

Case A — 僅 tests/momentum/conftest.py 含 pytest_plugins:
  python3 -m pytest tests/api/test_api.py tests/test_ff.py -q
  → 2 errors（fixture 'ic_persist_redirect' not found）；rc=1

  python3 -m pytest tests/momentum/test_momentum.py -q
  → 1 passed；rc=0

Case B — 僅 tests/conftest.py 含 pytest_plugins（刪 momentum/conftest）:
  python3 -m pytest tests/api/test_api.py tests/test_ff.py -q
  → 2 passed；rc=0
```

**語意補充（非 BLOCK）**：同一 session 若 argv 含 `tests/momentum/...`，nested `pytest_plugins` 會在 import momentum conftest 時 **session-global** 註冊 plugin，使同次 pytest 內 api/root FF 也可能意外 resolve fixture（Grok R3-P2「三檔同跑 1p2e」與本輪「三檔同跑 3 passed」路徑不一致；**hermetic 實際以 V2/V6 api-only、V7 ff-only 子集為準**）。R3 要求 root 無條件掛載仍為正確修法（V2/V6 子集已證 fail-closed）。

### P4 — Final §7 whitelist / root conftest 現況

```text
附錄 A（R3 L735–736）: tests/conftest.py + tests/momentum/conftest.py 無條件列入 whitelist/delta — 文字已改「禁條件 scope」

repo 現況:
  rg -n 'pytest_plugins' tests/conftest.py → rc=1（pre-impl，預期）
  test -f tests/momentum/conftest.py → rc=1（pre-impl，預期）
  tests/api/conftest.py 存在但無 redirect plugin（R3 禁第二掛載點，除非入 whitelist — 未採）
```

### P5 — R2 vs R3 diff + R2 閉合留存

```text
命令: diff -u handoffs/P2DEBT-T2-TODO-DRAFT-R2.md handoffs/P2DEBT-T2-TODO-DRAFT-R3.md
變更僅限（抽樣）:
  - NEW-B1: Task 2.5 期望 7→8 + 可選 rg -v ':def '
  - NEW-B2: Task 1.2.3 root pytest_plugins 無條件；1.2.4 momentum 新建非唯一；刪「條件 scope」
  - NEW-M1: Task 1.1.9 nested xref 1.3.9→1.3.12
  - 附錄 A conftest 無條件入 delta
  - R2-CLOSURE 表 B2/B5 補「字面 rg=8」註記（未重開 B1/M1–M6/codex B1–B9）
  - 新增 R3 FACT-RECEIPT 段；基線 receipt R1–R7 **全文保留**

R2 錨點 spot（repo）:
  16-caller=16；decoupling count=0；pre-impl create_feature_factory=7；GEN 四檔 EXISTS；hermetic.sh 未建
```

---

## grok re-verify finding → R3 閉合對照

| ID | grok R2 re-verify | R3 修法 | 本輪判定 | 證據 |
|----|-------------------|---------|----------|------|
| **NEW-B1** | Task 2.5 字面 rg 期望 7 與 def 行矛盾（實 8） | §0 + Task 2.5 TRUE 期望 **8**；create **1**；可選 call-site rg **7** | **CLOSED** | P1 pre=0/7；P2 post-sim=8/1/7 |
| **NEW-B2** | momentum-only plugin 不及 api/root FF；條件 conftest vs §7 exact-diff | Task 1.2.3 root 無條件；1.2.4 非唯一；附錄 A 無條件 conftest | **CLOSED** | P3 api+ff fail / root pass；P4 whitelist 文字 |
| **NEW-M1** | Task 1.1.9 xref 1.3.9 過時 | → **1.3.12** | **CLOSED** | R3 L338 |
| **grok B1** | Phase 1 cold-start | R2 Task 1.0+1.1（R3 未重開） | **CLOSED** | R2-CLOSURE intact |
| **grok B2 / codex B5** | create=0 矛盾 + helper 計數殘 | create=1 + 字面 8 | **CLOSED** | P2 |
| **grok M1–M6** | normalize/skip/V7/1.4/FF-02/header | R2 閉合（R3 未重開） | **CLOSED** | R2-CLOSURE 表 |
| **codex B1–B9** | mutation/collect/pipefail/whitelist/… | R2 閉合（R3 未重開） | **CLOSED** | R2-CLOSURE 表 |

---

## NEW problems（R3 後本輪新 hunt）

### NEW-C1 — [MINOR] nested `pytest_plugins` session-global 可掩蓋 momentum-only 漏掛（非 TODO 矛盾）

**信心度: Medium**

當同一 pytest 進程 argv 含 `tests/momentum/**` 時，momentum conftest 的 `pytest_plugins` 可能 session-global 註冊 fixture，使同次 run 內 api/root FF 意外通過（與 Grok R3-P2「三檔 1p2e」收據路徑不一致；本輪三檔同跑曾得 3 passed）。**hermetic 實際以 V2/V6（api-only）子集 fail-closed**（P3 Case A）。

**影響**: 若實作端偷懶只掛 momentum、只靠 `--set all` 混跑，可能假綠；V2/V6 仍會抓出。

**建議（非阻 stamp）**: 實作時 Task 1.2.4 優先 **空檔/註解** momentum conftest，避免重複 `pytest_plugins`；可選在 Task 3.1 加「V2 必須在無 momentum 路徑下通過」煙測註記。

**判定**: **STILL-OPEN（MINOR 實作提醒）** — 不阻 R3 TODO stamp。

---

## CLOSED / STILL-OPEN 總表

| ID | 狀態 |
|----|------|
| NEW-B1 | **CLOSED** |
| NEW-B2 | **CLOSED** |
| NEW-M1 | **CLOSED** |
| grok B1 | **CLOSED**（R2 閉合，R3 intact） |
| grok B2 / codex B5 | **CLOSED** |
| grok M1–M6 | **CLOSED**（R2 閉合，R3 intact） |
| codex B1–B9 | **CLOSED**（R2 閉合，R3 intact） |
| NEW-C1 | **STILL-OPEN（MINOR）** — 不阻 approve |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: Task2.5 post-impl 字面 rg _create_e2e_factory=8（1def+7calls）；create_feature_factory=1；pre-impl 0/7；root conftest plugin 為 api+ff 必要掛載（P3）；Final§7 whitelist 含 conftest 無條件；R2→R3 diff 僅 NEW-B1/B2/M1 + FACT-RECEIPT；R2-CLOSURE 未重開
TESTS_RUN: P1 rg repo；P2 /tmp static sim rg；P3 /tmp conftest-scope pytest（0 repo body）；P5 diff+spot grep；pytest 8.4.2
FAILURES_SEEN: P3 Case A 2 errors 為預期反例（momentum-only 不及 api/ff）
SCOPE_CHANGES: none（僅 handoffs/P2DEBT-T2-TODO-REVERIFY-R3-composer.md）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: handoffs/P2DEBT-T2-TODO-REVERIFY-R3-composer.md
```

RECONCILE-STAMP APPROVED (p2debt-t2 TODO R3, composer, 2026-07-11)

**Verdict: APPROVE**

STATUS: DONE
