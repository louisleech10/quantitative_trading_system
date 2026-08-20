# GAP-3 戳記 hash 補正 — COMPOSER (STAMP-R2)

task-id: `20260820-GAP3-X-STAMP-R2`  
brief: `handoffs/20260820-gap3-specclose2-BRIEF.md`  
stamp-target: `handoffs/reconcile/20260820-gap3-x-review-r6/synth.md`  
標的 SPEC: `docs/GAP3_EVENT_SPEC.md` @ `db85611a`（sha256 `09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f`）  
家族: composer ｜ stamp 輪次: R2（hash 補正）｜ 日期: 2026-08-20  
本家 R1 交件: `handoffs/20260820-gap3-specclose-composer.md`

## Verdict：本體未變＋現行 body hash 補正 → APPROVED

R1 戳記時 `## 戳記` 區尚不存在，`reconcile_body_hash.sh` 邊界＝全檔 ⇒ R1 戳記 sha（`43b0dc14…`）與現行本體（`f833c6b9…`）不符。本輪複核：`## 戳記` 之前內容與 R1 所審一致；SPEC 未動。已 append R2 戳記至 stamp-target（R1 行保留作審計軌跡）。

### 步驟 1 實跑（SPEC sha）

```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f  docs/GAP3_EVENT_SPEC.md
```

### 步驟 2 實跑（現行 body hash）

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260820-gap3-x-review-r6/synth.md
f833c6b9a6578748855a8843085754f601e5c6954f6cd9e3eab7dd9d6f889766
```

### 本體複核（`## 戳記` 之前 vs R1）

| 檢查項 | R1 所審 | 現行 synth L1–56 | 一致？ |
|---|---|---|---|
| 終態確認 V1／全輪閉合帳／§A 兩題 | specclose-composer §複驗摘要 | synth 終態 §1–3＋附錄 | **是** |
| COMPOSER-R6-P3-00 逐字保留 | R6 交件 | synth 附錄 L33–41 | **是** |
| SPEC @ db85611a sha | `09b05b39…` | 步驟 1 實跑相符 | **是** |

---

## COMPOSER-R2-P3-00

**斷言**: 本輪 hash 補正複驗未發現需阻擋收斂的新 finding；synth 本體與 R1 所審一致，R2 戳記 sha 與 `reconcile_body_hash.sh` 現行 stdout 相符。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f`（＝brief）；`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260820-gap3-x-review-r6/synth.md` → `f833c6b9a6578748855a8843085754f601e5c6954f6cd9e3eab7dd9d6f889766`；讀 stamp-target L1–56 與 R1 複驗表 0 漂移；append `RECONCILE-STAMP: composer APPROVED 2026-08-20 sha256:f833c6b9a6578748855a8843085754f601e5c6954f6cd9e3eab7dd9d6f889766 task:20260820-GAP3-X-STAMP-R2`（R1 行未刪未改）。

**來源摘要**: handoffs/reconcile/20260820-gap3-x-review-r6/synth.md#f833c6b9a657; docs/GAP3_EVENT_SPEC.md#09b05b39aa13; handoffs/20260820-gap3-specclose-composer.md

sentinel：0 findings（實質）；上列為 STAMP-R2 本體不變確認＋現行 body hash 補正摘要。

---

```
ASSUMPTIONS_VERIFIED: SPEC sha=brief；synth 本體 L1–56 與 R1 一致；body hash 實跑=f833c6b9…
TESTS_RUN: shasum SPEC；reconcile_body_hash.sh synth；讀檔本體對照 R1
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only；synth.md 僅 append 戳記區一行 R2）
NUMERIC_OR_SCHEMA_IMPACT: none
產出檔: handoffs/20260820-gap3-specclose2-composer.md
TMP_CLEANUP: /tmp 與 /private/tmp 無 *workdir* 目錄；claude-501 已保留
```

STATUS: DONE
