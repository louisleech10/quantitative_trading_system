# GAP-3 B1 批 code review R4 閉合輪 — COMPOSER

family: composer  
task-id: 20260821-GAP3-B1-REVIEW-R4  
scope: 修補 diff `HEAD~1..HEAD`（`momentum/`＋`tests/`）；R3 synth `handoffs/reconcile/20260821-gap3-b1-review-r3/synth.md`；權威 `docs/GAP3_EVENT_TODO.md` FROZEN＋`docs/GAP3_EVENT_SPEC.md`；禁改碼  
brief: `handoffs/20260821-gap3-b1-review-r4-brief.md`  
R3 本家: `handoffs/20260821-gap3-b1-review-r3-composer.md`

RECONCILE-STAMP: composer APPROVED 2026-08-21 sha256:38c7ec4736536aa928874157fe221f6a2d923d71bd23a1fa18bc10d35ce165bf task:20260821-GAP3-B1-REVIEW-R4

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R4 sentinel 複核 |
|---|---|---|
| suite 100 passed | fact-verified（brief） | **本輪重跑** → 100 passed in 11.09s，rc=0 |
| R3 completeness PASS＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 R3 synth＋修補 diff 對照 |
| assumed: 全 CLOSED 後 B1 收斂（R1 8 → R2 3 → R3 1 → R4 0），可進 stamp 輪 | **攻後＝成立（composer 側）** | 本輪修補僅 `baseline.py:98-102` hex 字元集＋`test_baseline_oracle.py:104` 兩反例；sentinel 未見新 alignment/baseline 矛盾；**codex R4 一條 probe CLOSED 待 codex 交件** |

VERIFY（本輪實跑）:
```
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 100 passed rc=0
PYTHONPATH=. venv/bin/python /tmp/composer_r4_sentinel.py → nonhex_rejected=True; uppercase_rejected=True; valid_lowercase_accepted=True
git diff HEAD~1..HEAD -- momentum/ tests/ → baseline hex set check + test 非 hex／大寫反例
shasum -a 256 momentum/Analysis/event_samples/baseline.py → 38c7ec473653…
```

---

## brief 必答

1. **codex 一條 CLOSED？** composer **不代判** codex R4 重跑 `CODEX-R3-P2-01` probe；修補 diff 已落地 `set(feature_manifest_hash) - set("0123456789abcdef")` 檢查，`"g"*64`／`"AB"*32` 皆 `ValueError`（match `feature_manifest_hash`），合法 `"a"*64` 仍入 receipt；`test_feature_manifest_hash_in_receipts_and_required` 綠。**待 codex R4 交件獨立 CLOSED。**
2. **新引入問題？** **无** — 修補範圍極小（一處條件式＋測試反例擴充），未改 alignment/uint64/有限值閘；caller 仍僅 `baseline.py` 定義＋兩測試檔且皆傳合法 lowercase hex。
3. **可進三家 RECONCILE-STAMP 輪？** **composer 側可** — 本家 sentinel 0 finding；**待 codex R4 一條 CLOSED＋grok R4 sentinel＋三家 quorum synth 戳記** 後 B1 收斂。

---

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；R3 採納之 `feature_manifest_hash` 逐字元 hex 驗證（`baseline.py:98-102`）＋非 hex／大寫反例（`test_baseline_oracle.py:104`）未引入新的 baseline provenance 或 alignment 可證偽缺陷——malformed 64 字元 fail-closed、合法 lowercase hex 行為不變、R2 三修補（uint64 int64 化、有限值閘、hash 必填）語意未回退。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 100 passed rc=0；`PYTHONPATH=. venv/bin/python /tmp/composer_r4_sentinel.py` → `nonhex_rejected=True`／`uppercase_rejected=True`／`valid_lowercase_accepted=True`；`baseline.py:98-104` 三條件（type/len/hex set）合一 `ValueError`；`test_baseline_oracle.py:104` `for bad in (None, "", "short", "g"*64, "AB"*32)` 全拒；`rg -l single_feature_binary_baseline momentum/ tests/` → 僅 baseline 定義＋兩測試檔；`git diff HEAD~1..HEAD -- momentum/ tests/` → 2 files +7/-3。

**來源摘要**: momentum/Analysis/event_samples/baseline.py#38c7ec473653; tests/momentum/event_samples/test_baseline_oracle.py#6e2fad4b8285; handoffs/reconcile/20260821-gap3-b1-review-r3/synth.md#ea8f6c8f7ba1

---

## Verdict：可進 B1 stamp 輪（待 codex R4 一條 CLOSED＋grok R4 sentinel＋三家 quorum）

本家 sentinel **0 finding**；hex 修補與 TODO B1.6 provenance 契約（64-char lowercase sha256 hex）一致；100 passed 含 R3 反例擴充。composer 無阻擋項。

---

ASSUMPTIONS_VERIFIED: 100 passed 本輪重跑；g*64/AB*32 拒、合法 lowercase 放行；修補 diff 僅 baseline+test；caller 未擴散  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 100 passed rc=0；`PYTHONPATH=. venv/bin/python /tmp/composer_r4_sentinel.py` → 三探針 OK  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；修補本身為 R3 採納之 fail-closed 強化，本輪僅 sentinel 複驗）  
HANDOFF_OUTPUT: `handoffs/20260821-gap3-b1-review-r4-composer.md`

STATUS: DONE
