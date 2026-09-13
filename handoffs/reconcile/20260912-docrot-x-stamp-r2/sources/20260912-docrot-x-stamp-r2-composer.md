# DOCROT consult-r4 戳記輪 R2 — composer 交件

**task-id**: `20260912-DOCROT-X-STAMP-R2`  
**family**: composer  
**brief**: `handoffs/20260912-DOCROT-X-CONSULT-R4-STAMP-BRIEF.md`  
**findings-round**: R2  
**stamp-target**: `handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記。

---

## 必答：body hash

**相符。** 實跑：

```text
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md
→ 1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23
rc=0
```

---

## 必答：群集／處置段是否如實反映 consult-r4 三家原文

**是。** 對照本家 `handoffs/20260912-docrot-x-consult-r4-composer.md`、codex／grok 同輪交件與 synth 群集表（`## 附錄` 之前）：

| 檢查點 | 結論 |
|---|---|
| 10/10 finding 全在群集表 | PASS（`reconcile_cluster_attribution_check.sh` rc=0） |
| **R1 Task 1.6** 採 grok 兩 token 版、未採本家 codex 全套 | **接受**——synth 逐字記「未採 composer 之 `ARCH-EDGE`＋`VERIFY:` 必填」；本家 Q1 裁定 (a) codex 機械版已 byte-faithful 留在附錄 COMPOSER-R4-P0-01。兩 token 版對 Task 1.6 三問（擋 D2 純散文 P0/P1／不做再燒 ≥10 條字面 finding／token presence＋HISTORY rc）**等效**；`ARCH-EDGE`／`VERIFY:` 不增加「無 `CODE-ANCHOR:` 之碼證」這條根因的阻擋力，無構造反例 |
| **R2 Task 1.8** 採 codex exact-line＋fence／blockquote | **如實**——與本家 Q2 裁定 (a) 一致 |
| **R3 forward-only** | **如實**——與本家 COMPOSER-R4-P1-01 修法一致；具名殘留「舊交件重跑 `--single` 會紅」已寫 |
| **R4 Task 1.7** 採 grok mechanical、未採本家 reconcile_build grep 閘 | **接受**——synth 記「composer 版會對所有 consult synth 誤擋」與本家 (b) 提案 `grep -qF 'doc_friction_ratio'` 之跨 epic 副作用一致；本家 P2-01 與 (b) 修法仍在附錄，未掉限制 |
| Task 1.1／1.2 pytest 反向 mutation | 如實（r3 測試落點段承載 codex 原文，無新動作） |
| 改後 TODO 仍 8 條、紀律型殘留 0 | 如實（與本家必答 4 一致） |

三種反覆形態抽驗：**未見**把 2:1 寫成「三家一致」（R1 明示 Q1 三家版本不同、依最窄擇 grok）；**未見**整條掉限制（本家 ARCH-EDGE／VERIFY／reconcile_build 閘均具名「未採」）；**未見**採某家版本卻改字面（Task 1.6／1.8 處置欄與 grok／codex 必答表逐字對齊）。

---

## COMPOSER-R2-P3-00

**斷言**: 本輪 stamp 審核 consult-r4 收斂之群集／處置段後無阻擋 finding；body hash 相符；主委六項擇取中涉及本家之四項（R1 未採 codex 全套、R2 採 codex、R3 forward-only、R4 未採 reconcile_build 閘）均如實反映 consult-r4 原文或依 brief「同為機械取最窄」合法裁定。

**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md` → `1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23` rc=0；`bash scripts/reconcile_cluster_attribution_check.sh handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md` → findings=10 全在群集表 rc=0；`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260912-docrot-x-consult-r4/sources.lock --synth handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md` → PASS rc=0；對讀 `handoffs/20260912-docrot-x-consult-r4-composer.md` 必答 1–4 與 synth L11–22。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md#1e6851f26801;handoffs/20260912-docrot-x-consult-r4-composer.md#70660a69b76f

[P3] 信心度=High。本輪 `round-kind: stamp`；非新 finding 輪。

---

## 非本輪範圍

- 本家仍認為 Task 1.7 之 `reconcile_build.sh` grep 閘 (b) 較 grok「一次寫入 SSOT」更能擋主委忘了寫成效句——屬 P2 取捨，synth 已具名未採與誤擋理由，不阻擋戳記。
- `VERIFY:` 必填能否擋「token 填滿但 MUTATION 不可執行」——超出 Task 1.6 所針對之 D2 純散文根因，非本輪 stamp 範圍。

---

## VERDICT

**APPROVED**

戳記已 append 至 stamp-target `## 戳記` 區：

```
RECONCILE-STAMP: composer APPROVED 2026-09-13 sha256:1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23 task:20260912-DOCROT-X-STAMP-R2
```

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 1e6851f2…；10/10 群集歸戶；completeness PASS；本家 consult-r4 必答 1–4 與 synth 群集段逐條對照；R1 兩 token 三問等效、R2/R3 如實、R4 未採 (b) 理由可追溯  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md` → 1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23 rc=0；`bash scripts/reconcile_cluster_attribution_check.sh handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md` → rc=0；`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260912-docrot-x-consult-r4/sources.lock --synth handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md` → PASS rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（僅 append 戳記一行＋本交件檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260912-docrot-x-stamp-r2-composer.md  
TMP_CLEANUP: `/tmp` 無 `*workdir*`；`/tmp/claude-501` 保留  

STATUS: DONE
