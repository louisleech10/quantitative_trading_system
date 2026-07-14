# IC1C-TODOREV R3 — Grok 閉合重驗

- **Reviewer**: Grok (r1/r2 原委員, family ≠ author)
- **Date**: 2026-07-14
- **Inputs**: r2 `handoffs/20260714-IC1C-TODOREV-R2-grok.md`(REJECT 1B); TODO r3 `docs/IC1C_NETIC_TODO.md`; RECONCILE r2 補記 T-F17~T-F26; SPEC §U v1.1 補裁
- **Scope**: 本檔 + APPROVE 時 RECONCILE 戳記;未改 SPEC/TODO/code
- **Discipline**: 逐 finding 反例重判 CLOSED/STILL-OPEN;核可 SPEC §U v1.1;掃 r3 新洞

## Verdict

**TODO-REVIEW-R3: APPROVE**

r2 **1 BLOCKING + 2 MAJOR + 2 MINOR** 中:BLOCKING 與兩 MAJOR 主訴 **CLOSED**;SPEC §U v1.1(負 turnover→SKIPPED+禁 max clamp;capacity 允許子鍵)**核可**(=R2-3 洞之 SPEC 依據)。  
殘差僅 **非 BLOCKING**:Task 1.3 邊界仍寫「負 turnover clamp」(與 1.1/SPEC 打架,正名路徑風險)、§0 `SCHEMA_SKIPPED` 觸發枚舉漏「負值」、覆蓋表 G-NEW2「獨立 validator」措辭過滿、G-NEW2 URL 仍委執行端確認。  
**0 新 BLOCKING**。可戳記;建議 B1 實作 1.3 前把邊界改對齊 v1.1(刪 clamp 字樣),非再開 r4 必要條件。

---

## SPEC §U v1.1 核可(R2-3 對應)

| 補裁 | 證據(SPEC L36-37) | 判定 |
|------|-------------------|------|
| `turnover<0`→SKIPPED reason=`negative_turnover` | 觸發條件枚舉含**負值**;明禁 `max(0,·)` 靜默 clamp | **APPROVE** |
| capacity 允許子鍵 | `{estimated_capacity_usd: number\|null, capacity_tier, calibration:"uncalibrated"}` | **APPROVE**(閉 COMPOSER-11 子鍵無 oracle 殘差主因) |
| 與 §T 公式 | 仍 `(cost_bps/10000)×turnover` 無 ×2;clamp 只用於 sensitivity 階梯 bps 非 turnover | **一致** |

註:SPEC 檔頭仍標 `v1.0 Frozen`(body 已含 v1.1 補裁語)—**文面版本字串未升**為 MINOR 帳務問題,不阻 TODO 凍結;建議主席標 `v1.1 Frozen` 以免執行端誤讀「未補裁」。

TODO 對齊:Task 1.1 ①+G-NEW canonical 重算(L54/L94)已去 clamp、負→SKIPPED。  
RECONCILE T-F19 認帳 CODEX-1 漏列—**曲解已修**。

---

## r2 Findings 逐條重判

### ADV-GROK-R2-1 [原 BLOCKING] → **CLOSED** (T-F17)

| 項 | 內容 |
|----|------|
| r3 落點 | Task 0.1 ④:`pop("oc_return")`+`summary["hl_range"]["ic_mean"]=nan`;明列 7 欄 FEATURE_NAMES、無 obv/ad |
| 反例是否仍成立 | **否** |
| VERIFY(2026-07-14) | `from tests.fixtures.ic_api_real_kline import FEATURE_NAMES` → 7 名;`oc_return`/`hl_range` True;`obv`/`ad` False |
| RECHECK | 寫死名集合 ⊆ FEATURE_NAMES |

### ADV-GROK-R2-2 [原 MAJOR] → **CLOSED** (T-F18)

| 項 | 內容 |
|----|------|
| r3 落點 | Task 1.1 ④+Task 2.1 ① 統一偽碼:`if cost_bps is not None and (not isfinite or not 0<…): raise`+`if cost_enabled and cost_bps is None: raise`;§0 同構;T2 矩陣 `{false,NaN}`→422 |
| 反例是否仍成立 | **否**(原 enabled-and 短路已刪) |
| 殘差 | T1 具名表未單列 `test_disabled_cost_bps_nan_rejected`(靠 validator 偽碼+T2/T5/M10)—**MINOR**,不升級 |

### ADV-GROK-R2-3 [原 MAJOR] → **CLOSED**(主因)+**殘差 MINOR-MAJOR**

| 項 | 內容 |
|----|------|
| r3 落點 | SPEC §U v1.1+Task 1.1 禁 max+負→SKIPPED+G-NEW 內嵌 oracle 同構;RECONCILE T-F19 補裁 |
| 原反例(1.1/G-NEW max) | **否** |
| 殘差 | Task 1.3 **邊界** L77 仍 `②負 turnover clamp`——與 1.1/SPEC 衝突;若走「正名」proxy 路徑可能再發明 clamp |
| 為何不 BLOCKING | 1.3 首選=**刪除** proxy;`grep net_ic_proxy==0` 為完成定義;主成本路徑(1.1/G-NEW)已閉;殘差屬正名分支文面 |
| 建議 | B1 動 1.3 前改邊界為「負→raise 或由 caller SKIPPED,禁 clamp」 |

### ADV-GROK-R2-4 [原 MINOR] → **CLOSED(主)+殘差 MINOR**

| 項 | 內容 |
|----|------|
| r3 落點 | G-NEW2:POST→task_id→**輪詢 GET**(0.5s/60s timeout)+等值 sha256(T-F20) |
| 反例「直接取 features dict」 | **否** |
| 殘差 | URL/入口仍「執行端自 `ic_analysis.py` 確認寫註解」;現碼為 `POST /deep-analysis/{task_id}`+`GET .../result`(且 deep 需既有 IC task)—可執行但非 copy-paste 級 |
| 判定 | 不升級;B2 實作腳本時釘死 path 即可 |

### ADV-GROK-R2-5 [原 MINOR] → **STILL-OPEN (MINOR)**

| 項 | 內容 |
|----|------|
| r3 覆蓋行 L141 | 仍寫 G-OLD/G-NEW/G-NEW2「皆…+**獨立 validator**」 |
| 事實 | G-OLD 有 `ic1c_validate_baseline.py`;G-NEW2 是 vs G-NEW 等值比對(合理),非獨立內容 validator |
| 修法 | 覆蓋表改「G-OLD 獨立內容 validator;G-NEW2=vs G-NEW 等值」 |

---

## r1 回顧(r2 已 CLOSED 者)—抽樣不重開

r2 已判 CLOSED 的 ADV-GROK-1..12(3B+6MAJOR+3MINOR)在 r3 **未回歸**:Task 1.4/帶參 mutation/G-NEW2 命令/SCHEMA 專檔/T1b/T-F7 精神/雙 override 等字面仍在。不重開。

---

## r3 新洞掃描

### ADV-GROK-R3-1 [MAJOR] 信心度 Medium — Task 1.3 邊界殘留「負 turnover clamp」

- **證據**:TODO L77 `邊界:…②負 turnover clamp` vs L54/SPEC L36 禁 clamp。
- **反例**:正名 `compute_cost_drag_proxy` 時 agent 依邊界靜默 max→第二混路徑/假合法 cost_drag。
- **修法**:刪 clamp;對齊 v1.1(raise 或文件化「僅在 batch 層 SKIPPED,本函禁收負值」)。
- **不升 BLOCKING**:見 R2-3 殘差理由。

### ADV-GROK-R3-2 [MINOR] 信心度 High — §0 SCHEMA_SKIPPED 觸發枚舉漏負值

- **證據**:§0 L8 `turnover 缺或非有限/gross_ic 非有限`—**無負值**;SPEC L36+Task 1.1 有。
- **反例**:只讀 §0 的 profile 分派可能把 `turnover=-0.2` 送進 GROSS/COST 算 drag(G-NEW oracle 會抓,非靜默過 Gate)。
- **修法**:§0 補「/負值(reason=`negative_turnover`)」;Task 1.1 邊界 L57 同步列負→SKIPPED。

### ADV-GROK-R3-3 [MINOR] 信心度 Low — SPEC 檔頭版本字串仍 v1.0

- body 已 v1.1 補裁;檔頭 `v1.0 Frozen`+舊 stamp 敘事易誤導。建議 `v1.1 Frozen` 註明 delta=負 turnover+capacity 子鍵。

### ADV-GROK-R3-4 [MINOR] — G-NEW2 前置 IC task 未寫明

- 現 route deep-analysis path 需既有 `{task_id}`;TODO 只寫 POST deep-analysis 取 task_id。執行端讀 route 可解,但冷啟動易漏「先跑 analyze」。併 R2-4 殘差,不升。

**無新 BLOCKING**(無 B0 KeyError/三層 validator 互斥/發明 max 於主路徑)。

---

## T-F17~T-F26 落點勾稽(對我方 r2)

| T-F | 主題 | r3 落點 | 判定 |
|-----|------|---------|------|
| T-F17 | 真 fixture 名 | 0.1 oc_return/hl_range | **忠實 CLOSED R2-1** |
| T-F18 | validator 統一 | 1.1/2.1 偽碼 | **忠實 CLOSED R2-2** |
| T-F19 | 負 turnover SKIPPED | SPEC v1.1+1.1/G-NEW;認 CODEX-1 | **忠實;1.3 邊界殘字** |
| T-F20 | G-NEW2 async | POST→poll GET | **忠實 CLOSED R2-4 主訴** |
| T-F21~26 | npm prefix/reporter 裸 number/UI 三態/phase26/docs/B0 shasum | §B/1.4/2.2/3.1/0.1 | **字面到位**(非我方 r2 主訴,抽樣 OK) |

RECONCILE 曲解:r2 對我方 **無新曲解**;T-F5 7bps vs 10bps 舊漂移仍在歷史行、r3 正文以 10bps 為準—可接受。

---

## 覆蓋表機械勾稽(r3)

| SPEC 錨點 | r3 TODO | 判定 |
|-----------|---------|------|
| Task 0.1–3.1+1.4 | 齊 | OK |
| M1–M10 | Phase1/2+§B 分層 | OK |
| G-OLD/NEW/NEW2 | 三模式+async+shasum 雙跑 | OK(程序) |
| §U 三 profile+負 turnover | 1.1/G-NEW/SPEC;§0 漏枚舉 | 主路徑 OK |
| §C #4/#16 | Task 1.4 裸 number | OK |
| capacity 子鍵 | SPEC v1.1+1.1 calibration | OK |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - FEATURE_NAMES has oc_return/hl_range; no obv/ad (python import fixture)
  - Task 0.1 uses oc_return/hl_range (rg/read TODO L40)
  - Task 1.1/2.1 validator: non-None domain first (no enabled-and short-circuit)
  - max(0.0,turnover) absent from primary 1.1/G-NEW paths; ban max explicit
  - SPEC §U L36-37 v1.1 negative_turnover + capacity subkeys present
  - Task 1.3 L77 still "負 turnover clamp" (residual)
  - §0 SCHEMA_SKIPPED triggers omit negative
  - deep-analysis routes: POST /deep-analysis/{task_id}, GET .../result
  - root has no package.json; §B uses npm --prefix frontend
TESTS_RUN:
  - python: FEATURE_NAMES membership (oc_return/hl_range True; obv/ad False)
  - rg: max/clamp/negative/validator/obv patterns on TODO+SPEC
  - read: RECONCILE T-F17~26; routes ic_analysis.py deep-analysis
  - body hash: sed -n '1,/^## 戳記$/p' RECONCILE | sed '$d' | shasum -a 256
    → 6c2a230df7f952069af7d1779d235f47e3a17bcdcc88e44fda53d2e95d4affe0
FAILURES_SEEN: none (review-only)
SCOPE_CHANGES: none — handoffs R3 + RECONCILE stamp only
NUMERIC_OR_SCHEMA_IMPACT: none (docs/review only; §U v1.1 content approved not re-authored)
RECONCILE_DISTORTIONS: none new vs r2 findings
STAMP: APPENDED (APPROVE)
RESIDUALS_NON_BLOCKING:
  - R3-1 Task 1.3 boundary "clamp" (MAJOR residual)
  - R3-2 §0 SKIPPED trigger enum miss negative (MINOR)
  - R2-5 coverage wording independent validator (MINOR)
  - R3-3 SPEC header still v1.0 (MINOR)
  - R2-4/R3-4 G-NEW2 path discovery (MINOR)
```

STATUS: DONE

TODO-REVIEW-R3: APPROVE
