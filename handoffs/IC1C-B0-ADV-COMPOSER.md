# IC1C-TODOREV-R5 — Composer 閉合重驗

> SPEC=`docs/IC1C_NETIC_SPEC.md` v1.1(內文;banner 仍 v1.0 Frozen) | TODO=`docs/IC1C_NETIC_TODO.md` **DRAFT r5** | 重驗基線=composer R3 REJECT(1B)+3 MAJOR | reviewer=composer | 2026-07-14

## Verdict：R3 四條反例全 CLOSED；r5 新洞 0 BLOCKING / 2 MINOR → 可 Frozen

r5 已承接 composer R3-1~4 與 codex r3/r4 修訂(負 turnover 具名測試+G-NEW2 排除集+B0 字面雙跑+capacity 鍵集合+collect-only 入 §B B2)。**不蓋 RECONCILE 戳記**(見末行;body 定稿後統一補戳)。

---

## composer R3 四條反例重跑

| ID | r3 嚴重度 | 判定 | r5 證據 / 反例重跑 |
|----|-----------|------|-------------------|
| ADV-COMPOSER-R3-1 | BLOCKING | **CLOSED** | Task 1.3 L78 `負/非有限 turnover→raise ValueError(…**禁 clamp**)`；`rg '負 turnover clamp' docs/IC1C_NETIC_TODO.md`→0。Task 1.1 L55/§0/G-NEW canonical 同向 SKIPPED+禁 `max(0,·)` |
| ADV-COMPOSER-R3-2 | MAJOR | **CLOSED** | Phase2 L125 **兩段式 bootstrap 偽碼**：①`POST /api/v1/ic/analyze`→completed `task_id`；②`POST .../deep-analysis/{task_id}`+`net_ic:10bps`；③輪詢 GET result；點名 `completed_ic_task`+`ic_persist_redirect`。實讀 `tests/api/test_ic_deep_analysis.py:72-97` 同序 |
| ADV-COMPOSER-R3-3 | MINOR | **CLOSED** | Phase3 L139 Gate=`pytest tests/momentum/ tests/api/ tests/phase26/ -q`；與 §B B3 L33 一字對齊 |
| ADV-COMPOSER-R3-4 | MINOR | **CLOSED** | Task 3.1 L137 `npm --prefix frontend run build`；`rg 'npm run build' docs/IC1C_NETIC_TODO.md`→0；root 無 `package.json`(實測) |

---

## codex r3/r4 殘留項快判(r5 是否閉合)

| 來源 | 判定 | r5 證據 |
|------|------|---------|
| CODEX-1 負 turnover 無 oracle | **CLOSED** | §0 L8 列負值；T1 `test_negative_turnover_skipped`+`test_mutation_m11_restore_clamp`；G-NEW 注入 `zscore_20 turnover=-0.2` |
| CODEX-7 G-NEW2 注入不對稱 | **CLOSED** | L125 比對集排除 `oc_return/hl_range/zscore_20` 三注入特徵，寫死腳本常數 |
| R2-NEW-1 B0 雙跑非字面 | **CLOSED** | §B B0 L30 `h1=…; h2=…; [ "$h1" = "$h2" ]` 可複製 |
| R4-CODEX-1 capacity 鍵集合 | **CLOSED** | §0 L9 恰等三子鍵+calibration 恒 `uncalibrated`；T1 `test_finite_invariants` 具名 |
| R4-CODEX-2 collect-only 漂移 | **CLOSED** | §B B2 L32 含 `--collect-only` |

---

## r5 新洞掃描

### ADV-COMPOSER-R5-1 [MINOR] — G-NEW2 首句與 bootstrap 偽碼雙重 ① 漂移

- **證據**: Phase2 L125 開頭仍寫「POST deep-analysis→取 task_id」；正確流程在緊接「兩段式 bootstrap 偽碼」①②③。
- **反例**: 粗讀首句、略過偽碼塊→冷啟動 404(與 R3-2 同類,文面殘留)。
- **修法**: 刪除首句舊 ① 或改為「見下方 bootstrap 偽碼」；避免兩套步驟編號。

### ADV-COMPOSER-R5-2 [MINOR] — Task 1.3 nan turnover 仍「raise 或 0.0 擇一」

- **證據**: L75 `test_net_ic_proxy_nan_turnover` 仍寫擇一；L78 邊界 ② 已釘 raise。
- **反例**: T3 實作若選 0.0→與 analyzer 非有限→SKIPPED 語意分叉(僅影響 proxy 刪除前的 rename 路徑)。
- **修法**: L75 改唯一規則「非有限→raise ValueError」(與 L78 一致)；首選刪 proxy 則連帶刪該測試句。

### NOTE(非 Blocking)

- M11 clamp probe 在 T1 具名但 SPEC §V 矩陣僅 M1–M10——追溯缺口,不阻 B0。
- SPEC L3 banner v1.0 vs TODO 標 v1.1——建議 SPEC 同步 banner,不阻 TODO Frozen。

---

## 覆蓋追溯重算(r5)

| 錨點 | r5 | 判定 |
|------|-----|------|
| composer R3 四反例 | 4/4 CLOSED | PASS |
| codex r3/r4 五殘留 | 5/5 CLOSED | PASS |
| G-OLD/G-NEW/G-NEW2 | 三模式+validator+bootstrap+排除集 | PASS |
| §B Gate 可執行 | 全帶參+字面雙跑+collect-only | PASS |
| §C 16 + Task 1.4 | 未回退 | PASS |

---

ASSUMPTIONS_VERIFIED: `FEATURE_NAMES` 7 欄含 oc_return/hl_range(讀 fixture L27+);`completed_ic_task` 先 analyze 後 deep-analysis(讀 test L72-97);root 無 package.json;mutation_probe 無參 exit 1(用法提示)
TESTS_RUN: `rg '負 turnover clamp|npm run build|phase26' docs/IC1C_NETIC_TODO.md`; `rg FEATURE_NAMES tests/fixtures/ic_api_real_kline.py`; `test ! -f package.json`; `bash scripts/mutation_probe_check.sh`(無參→用法)。唯讀審查,未跑產品測試。
FAILURES_SEEN: none
SCOPE_CHANGES: none；產出 `handoffs/20260714-IC1C-TODOREV-R5-composer.md`；RECONCILE 未 append stamp
NUMERIC_OR_SCHEMA_IMPACT: none(唯讀)

STATUS: DONE

TODO-REVIEW-R5: APPROVE(0 BLOCKING)
