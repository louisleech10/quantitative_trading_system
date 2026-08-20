# GAP-3 B1 批 code review R2 閉合輪 — COMPOSER

family: composer  
task-id: 20260821-GAP3-B1-REVIEW-R2  
scope: 修補 diff `df45bc82..e0cecf7c`（`momentum/`＋`tests/`）；R1 synth `handoffs/reconcile/20260821-gap3-b1-review-r1/synth.md`；權威 `docs/GAP3_EVENT_TODO.md` FROZEN＋`docs/GAP3_EVENT_SPEC.md`；禁改碼  
brief: `handoffs/20260821-gap3-b1-review-r2-brief.md`  
R1 本家: `handoffs/20260821-gap3-b1-review-r1-composer.md`

RECONCILE-STAMP: composer APPROVED 2026-08-21 sha256:6f8d8418dbe09effe8dd55bd900beed3ec02cc200ce4191e63406309cefa775c task:20260821-GAP3-B1-REVIEW-R2

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R2 複核結論 |
|---|---|---|
| 修補後 `pytest tests/momentum/event_samples/ -q` → 98 passed | fact-verified（brief） | **本輪重跑** → 98 passed in 10.82s，rc=0 |
| R1 synth completeness 全層 PASS＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 R1 synth 正文＋修補 diff 對照 |
| assumed: X1 union-find gap 語意（事件 i 自身答案窗 duration 為預設 gap，對所有 j>i 檢查）與 TODO「cluster_gap 預設＝答案窗 duration」一致 | **攻後＝成立** | TODO B1.2 L105「UTC duration（預設＝答案窗 duration）」；`dedupe.py:67-75` 對每對 (i,j) 以 `gap_i=ends[i]-starts[i]`（`cluster_gap_ms is None`）判定 `starts[j]-starts[i]<=gap_i`；探針 e1 dur=100／e2 +150ms ⇒ 2 簇；e1 dur=1000／e2 +800ms ⇒ 1 簇（見碼證）。舊鏈式用 i-1 duration 已廢，屬修補意圖內語意澄清非越權 |
| assumed: X6 baseline NaN fail-closed 較嚴且與 B1.6 一致 | **非本家 scope** | brief composer 義務不含 X6；未重判 |

VERIFY（本輪實跑）:
```
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 98 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q → 8 passed rc=0
PYTHONPATH=. venv/bin/python /tmp/composer_r2_recheck.py → A/C/B 三者 c0/1 簇；a/b/c 三者 c0/1 簇
shasum -a 256 momentum/Analysis/event_samples/dedupe.py → 6f8d8418dbe0…
git rev-parse e0cecf7c → e0cecf7cd0cf…
```

---

## 1. 本家 R1 finding 閉合（章程 §B8）

| R1 ID | 原斷言摘要 | 重跑反例／RECHECK | 判 |
|---|---|---|---|
| COMPOSER-R1-P1-01 | 鏈式掃描僅比前一事件，A/C/B 夾心反例 A/B 被拆開不同簇 | R1 RECHECK 腳本（A[0,100]、C[30,35]、B[40,50]，`cluster_gap_ms=0`）→ **修補前** A:c0、C:c0、B:**c1**；**修補後** A/C/B 皆 **c0**，`n_clusters=1`，`uniqueness_weight` A=1/3、C=B=0.5；`test_transitive_overlap_union_find_composer_counterexample` 綠 | **CLOSED** |

union-find 實作順掃（brief 指派）:

| 檢查項 | 結果 | 碼證 |
|---|---|---|
| O(n²) 事件級可承受 | **成立** | `dedupe.py:67-75` 雙層 `for i… for j in range(i+1,n)`；註解 L53 明示 |
| 決定性簇編號 | **成立** | `root_order` 依 union-find root 首次出現序（L77-84）；同輸入兩次 `cluster_ids` 一致 |
| gap 語意＝事件 i 自身窗 duration | **成立（攻 assumed 後）** | 見 §0；非對稱雙向 gap 但 TODO 未要求對稱，sorted (i,j) 以左端點 i 的 UTC duration 為 gap 單位合理 |
| overlap ∨ gap 連通 | **成立** | `_overlap` L23-24 標準半開區間；與 CODEX a/b/c 反例同簇（`test_transitive_overlap_union_find_codex_counterexample` 綠） |

---

## 2. brief 必答

1. **原提出方逐條 CLOSED？** composer 1/1 **CLOSED**（COMPOSER-R1-P1-01）；codex 7 條由 codex 自跑，本輪不代判。
2. **修補新引入問題？** **无** — union-find 掃描未發現新 BLOCKING/MAJOR；98 passed 含兩家反例回歸；未捏造湊數 finding。
3. **可蓋 RECONCILE-STAMP 進 B2 嗎？** **composer 側可** — 本家 R1 反例已閉合、無新 finding；**待 codex 7 條＋grok sentinel 同輪 CLOSED 後** 三家 quorum 戳記 synth → 進 B2（非本家單獨蓋章即動 B2）。

---

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；COMPOSER-R1-P1-01 原 A/C/B 夾心 RECHECK 與 union-find 順掃（O(n²)、決定性編號、per-event-i gap 語意）均已 CLOSED，修補 diff 未引入新的 dedupe／manifest 可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q` → 8 passed rc=0；`PYTHONPATH=. venv/bin/python /tmp/composer_r2_recheck.py` → A/C/B 同簇 c0/1、a/b/c 同簇 c0/1；gap 探針 150>100→2 簇、800<=1000→1 簇；`momentum/Analysis/event_samples/dedupe.py:51-84` union-find＋`root_order`；`git diff df45bc82..e0cecf7c -- dedupe.py test_dedupe.py` 含兩家反例測試。

**來源摘要**: momentum/Analysis/event_samples/dedupe.py#6f8d8418dbe0; tests/momentum/event_samples/test_dedupe.py#3290a1d85bf2; docs/GAP3_EVENT_TODO.md#df04bdabf37d

---

## Verdict：可進 B2（待 codex/grok R2 閉合＋三家 quorum 戳記）

本家 R1 一條 **CLOSED**；union-find 修補與 TODO B1.2 interval overlap 連通分量語意一致；98 passed 含反例回歸。composer 無阻擋項。

---

ASSUMPTIONS_VERIFIED: 98 passed 本輪重跑；R1 A/C/B RECHECK 修補後同簇；union-find O(n²)/決定性/gap 探針；dedupe 8 測全綠  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q` → 8 passed rc=0；`PYTHONPATH=. venv/bin/python /tmp/composer_r2_recheck.py` → 反例 CLOSED（見上）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）  
HANDOFF_OUTPUT: `handoffs/20260821-gap3-b1-review-r2-composer.md`

STATUS: DONE
