# GAP-3 TODO 對抗審 R8 閉合輪 — COMPOSER（sentinel 全檔重掃）

family: composer  
task-id: 20260820-GAP3-X-REVIEW-R8  
scope: `docs/GAP3_EVENT_TODO.md` v0.2（sha256 `b7bbe799d905…`）；R7 12 群集寫回複驗；權威 `docs/GAP3_EVENT_SPEC.md` FROZEN；禁改碼  
brief: `handoffs/20260820-gap3-todo-adv-r2-brief.md`  
R7 synth: `handoffs/reconcile/20260820-gap3-x-review-r7/synth.md`

RECONCILE-STAMP: composer APPROVED 2026-08-20 sha256:b7bbe799d9051e3e5b469d4e261167ee30041a10e2e4b7319f5d42a74aa11684 task:20260820-GAP3-X-REVIEW-R8

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R8 複核結論 |
|---|---|---|
| R7 synth completeness 全層 PASS＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 R7 synth 正文＋本輪 v0.2 實檔 grep/diff 為準 |
| v0.2 M1–M12 仍與 SPEC byte-identical | **fact-verified（本輪重跑）** | `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \*\*mutation 條件\*\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → 空輸出，`diff_rc=0` |
| `doc_format_precheck.sh` v0.2 rc=0 | **fact-verified（本輪重跑）** | `bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0 |
| assumed: 12 群集寫回全部到位、無漏寫 | **攻後＝成立** | W1–W12 各 RECHECK 探針均命中（見下表）；未見寫回遺漏 |
| assumed: W7 五算子精確語意自洽 | **攻後＝成立（實作要點層）** | `d=0` 不計交叉、`cross_count` 無交叉⇒0 於 L353–359 明定且互斥於其他算子之 NaN 語意；B3.3「邊界①」仍寫「窗內無交叉⇒NaN/哨兵（非0）」為 W7 寫回前 boilerplate，與 `cross_count` 特例矛盾——實作要點已覆蓋，不升級 finding |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_TODO.md
→ b7bbe799d9051e3e5b469d4e261167ee30041a10e2e4b7319f5d42a74aa11684
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 544c2922ef2ea09fe21bd6fda514f07e51a7f90f7f78c6409bfe38a7ccd23699
diff M1–M12 vs SPEC §V → empty, rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md → rc=0
rg -c '^### Task ' docs/GAP3_EVENT_TODO.md → 20
test -d tests/momentum/feature_engineering → no（W14 預期）；test -d tests/feature_engineering → yes
```

---

## R7 十二群集寫回 RECHECK（composer 旁證；codex/grok 原提出方閉合由各家自跑）

| 群集 | 對應 ID | composer 旁證 | 狀態（旁證） |
|---|---|---|---|
| W1 SoT genesis＋優先序 | CODEX-R7-P1-01 | L5 層級宣告＋B1.0/B2.4 genesis 註記＋「檔建立後以契約檔為準」 | 寫回到位 |
| W2 白名單 ⑦⑧ | CODEX-R7-P1-02 | §0-6 ⑦ `factories.py` B5.1、⑧ 收尾文件 B5.3 | 寫回到位 |
| W3 conditional-IC 置亂 | CODEX-R7-P1-03 | B2 Gate L37；B2.3 驗證 L259；B1.4 oracle 參數化 L168 | 寫回到位 |
| W4 digest tamper | CODEX-R7-P1-04 | B1.0 驗證⑥ L69 | 寫回到位 |
| W5 B1.6 failures 通道 | CODEX-R7-P1-05 | 三元輸出 L136–145；記帳守恆 L152 | 寫回到位 |
| W6 B3.1 role context | CODEX-R7-P1-06 | `expression_role` 簽名 L315–322；雙案例驗證 L330 | 寫回到位 |
| W7 B3.3 算子語意 | CODEX-R7-P1-07 | 五算子公式/閉區間/NaN L353–359 | 寫回到位 |
| W8 B4.2 exit 輸入 | CODEX-R7-P1-08 | `label_definition`＋`receipts` L402–407；D1-6 驗證 L416 | 寫回到位 |
| W9 可執行命令 | CODEX-R7-P2-09/10 | B1.2 ASSERT 全文 L110；vitest `gap3` L40/460；UAT checklist L468 | 寫回到位 |
| W10 萬級記錄型驗收 | CODEX-R7-P2-11 | B5.1 邊界②＋receipt 三欄 L443–445 | 寫回到位 |
| W11 `decision_at ≤ t0_open_ms` | GROK-R7-P1-01 | B1.1 偽碼 L84；驗證負例 L90 | 寫回到位 |
| W12 direction 批內單值 | GROK-R7-P1-02 | B1.0 偽碼 L63；驗證⑦ L69 | 寫回到位 |

---

## W14 裁決（composer 原 SPEC-AMENDMENT 提案）

| 項 | R7 裁決 | composer verdict |
|---|---|---|
| B3.3 測試路徑 `tests/momentum/feature_engineering/` | 免 amendment；B3.3 明示新建目錄 | **同意** — SPEC/TODO 命令字面一致（SPEC L301＝TODO L365）；repo 現況 `tests/feature_engineering/` 存在、`tests/momentum/feature_engineering/` 不存在；新建目錄使 Gate 命令可跑且不動既有 FF 測試，優於改 SPEC 或 symlink  hack；實作時須補 `__init__.py` 使 pytest collection 正常（施工細節，非 TODO BLOCKING） |

---

## §1 必查（11 類摘要 — v0.2 全檔重掃）

| 類 | 結果 |
|---|---|
| 1 矛盾/互斥 | 无 — W1 優先序消解 SoT 複列；§0-6 標題仍寫「唯此六項」但已列 ①–⑧（W2 寫回遺留標題用語，語意以 ①–⑧ 為準，非 BLOCKING） |
| 2 漏項/端到端 | 无 — 20 Task＋五批 Gate＋§G 六項仍完整 |
| 3 不可測驗收 | 无 — W9/W10 寫回後各 Task 驗證含可執行 pytest/vitest/receipt |
| 4 可疑 quant 假設 | 无 — D1/D2/D3/D4 鐵三角未因寫回漂移 |
| 5 過度工程 | 无 |
| 6 OOM/並行 | 无 — W10 記錄型驗收不捏門檻，符合 SPEC §V T-3 |
| 7 Cache 正確性 | 无 |
| 8 API/型別/相容 | 无 |
| 9 測試品質 | 无 — mutation M1–M12 仍逐字；新增 oracle 均有 `-k` 錨點 |
| 10 Agent 可執行性 | 无 — 寫回均落在既有 Task 欄位，未引入「自行判斷」空話 |
| 11 必要性/短命工 | 无 |

## §2 範本錨點＋獵空殼

- §0/§B/§V/20 Task 五欄：仍實填；寫回為增補非刪空
- §V M1–M12：RECHECK diff 空（未因寫回觸碰）
- 獵空殼：未見寫回後新空殼段

---

## 必答（brief 三問）

1. **原提出方逐條 CLOSED？** codex 11 條＋grok 2 條——本委員旁證寫回均到位；**正式 CLOSED 須 codex/grok 各自重跑 RECHECK**（本輪 composer 不代跑他族命令）。
2. **v0.2 新引入問題？** **无** BLOCKING/MAJOR。寫回未引入新 SPEC 衝突或越權；M 表仍 byte-identical；W7 邊界① boilerplate 與 `cross_count` 0 合法之表面矛盾已由實作要點 L358–359 覆蓋。
3. **可凍結 TODO FROZEN＋三家戳記？** **可** — 待 codex/grok R8 閉合無 NOT-CLOSED 後，composer 無阻擋項；建議 reconcile R8 synth → 三家戳記 → TODO FROZEN。

---

## COMPOSER-R8-P3-00

**斷言**: 本輪對 v0.2 全檔重掃（漂移/空殼/寫回引入之新矛盾）後無需阻擋收斂的實質 finding；R7 十二群集寫回旁證全命中；W14 免 amendment 裁決同意；§V M1–M12 仍 byte-identical。

**碼證**: `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \*\*mutation 條件\*\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → 空輸出 rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0；`grep -n 't0_open\|批內單值\|digest 篡改\|expression_role\|gap3_import_scale\|npx vitest run gap3'` TODO 均命中對應 Task；`shasum -a 256 docs/GAP3_EVENT_TODO.md` → `b7bbe799d9051e3e5b469d4e261167ee30041a10e2e4b7319f5d42a74aa11684`；`test ! -d tests/momentum/feature_engineering`（W14 新建預期）。

**來源摘要**: docs/GAP3_EVENT_TODO.md#b7bbe799d905; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

## Verdict：可凍結（待 codex/grok R8 閉合確認後進 TODO 三家 reconcile＋戳記）

無 BLOCKING/MAJOR。W14 同意免 amendment。殘留觀察（不計 finding）：§0-6 標題「唯此六項」與 ⑧ 項白名單用語不同步；B3.3 邊界① boilerplate 可於施工前順手改寫對齊 W7（非凍結阻擋）。

---

ASSUMPTIONS_VERIFIED: M1–M12 diff 空；doc_format_precheck rc=0；12 群集 grep 旁證；W14 目錄探針；W7 算子語意攻後自洽  
TESTS_RUN: `bash scripts/completeness_check.sh --single handoffs/20260820-gap3-x-review-r8-composer.md --family composer` → COMPLETENESS PASS，1 canonical ID，rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-x-review-r8-composer.md`

STATUS: DONE
