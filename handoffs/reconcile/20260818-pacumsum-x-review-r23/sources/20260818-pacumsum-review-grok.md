# PA-CUMSUM code review / grok | task-id=20260818-PACUMSUM-X-REVIEW-R23

brief-kind=review；家族=GROK；輪次=R23；審查標的 commit `7d516540`；禁改碼／禁 commit。

## Verdict：可合併

段 A 單利／複利語意、持倉空手、`final_return_pct` 百分比、舊鍵消費者掃描皆成立；段 C mutation（`cumprod`→`cumsum`）4 紅／還原 5 綠可證偽。預設複利與使用者「帳戶淨值」敘事一致且 UI 標籤清楚。

附非阻擋 finding：API `final_return_pct` 以裸 `Dict[str,float]` 未機械鎖四鍵（P2）；`y_pred_proba` 非有限值與 `actual_returns` 的 fail-closed 不對稱（P3）；欄位 `Field(description)`／`API_SPECIFICATION` 10.8 仍空殼路徑（P3，摩擦已知）。建議收案前或緊接小修，不構成「不可合併」。

| brief assumed／攻擊點 | 本輪結論 |
|---|---|
| 舊鍵無其他消費者（含 notebooks／docs 範例） | **成立於執行路徑**（`frontend/src`／`tests`／`api`／`momentum` 無舊鍵讀取）；殘留＝`docs/Archived/*`、`.claude/tmp` clone、以及 `docs/ROADMAP.md:72-73`／`docs/IC1D_ATTRIBUTION_SPEC.md:281` 仍用舊敘事描述前置狀態（非 runtime 消費者） |
| 預設複利合理 | **可接受**（見段 B①） |
| `y_pred_proba` NaN 視為空手可接受 | **語意可接受；完整度不足** → P3-01（+inf 會當持倉） |

```
VERIFY: venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q
→ 5 passed, rc=0（baseline）
VERIFY: mutation 將 prediction_analyzer.py 兩行 cumprod(1+r)-1 改為 cumsum(r) 後同測
→ 4 failed, 1 passed, rc=1（紅：hand_case／cumprod對照／threshold／to_dict）
VERIFY: cp 還原後同測 → 5 passed, rc=0；git diff prediction_analyzer.py 空
VERIFY: EquityCurveData(final_return_pct={"strategy":10.0}) 與 final_return_pct={} 皆 pydantic 接受
VERIFY: y_pred_proba=[0.9,nan,0.8] → positions [1,0,1]；[+inf] → [1,1,1]
```

**工作區**：本輪未改產品碼（mutation 已還原）；`/tmp/pacumsum-grok-review-66486` 收尾清除（保留 `claude-501`）。

---

## 段 A — 正確性

### A① 單利＝cumsum／複利＝cumprod(1+r)−1 與標籤 — **正確、無混淆**
- 實碼：`prediction_analyzer.py:174-178` 單利 `np.cumsum`、複利 `np.cumprod(1.0 + …) - 1.0`；dataclass／API docstring／TS 註解／UI `MODE_LABEL`＋`title` 皆對應「固定本金」vs「全額滾入」。
- 手算：`[+0.5,−0.5]` → simple 終值 0、compound −0.25（=−25%）；測試鎖死。
- 曲線序列為小數累積報酬；Y 軸／Tooltip 做 `v*100`%；footer 用已×100 的 `final_return_pct` — **無雙重縮放**。

### A② 持倉語意在複利下 — **合理**
- `strategy_positions = (y_pred_proba > threshold)`；空手期 `strategy_returns=0` ⇒ 複利乘子 `1+0=1`，淨值不變（與 IC1CFR flat=0／cumprod 慣例同型）。
- 閾值測：`proba=[0.9,0.5,0.9]` → compound `[0.1,0.1,0.21]`；基準忽略閾值全持倉。

### A③ `final_return_pct` 百分比 — **正確**
- `_final_pct = curve[-1] * 100.0`；四鍵 `strategy_simple`／`benchmark_simple`／`strategy_compound`／`benchmark_compound`。
- 前端 footer `.toFixed(2)%` 不再 ×100。

### A④ 舊鍵消費者 — **執行路徑無殘留；文件敘事有漂移**
- `grep` 於 `frontend/src`、`tests`、`api`、`momentum`：只見本票新鍵與區域變數 `strategy_returns = actual_returns * positions`（非 API 欄）。
- 無 notebook 命中。
- 非消費者但仍寫舊現況：`docs/ROADMAP.md:72-73`（票 A 前置仍寫 `strategy_returns`+`cumsum`）、`docs/IC1D_ATTRIBUTION_SPEC.md:281`；`docs/Archived/*`／`.claude/tmp/*` clone 不計。建議收案時改寫前置句，避免後人以為未修。

---

## 段 B — 攻主委決定

### B① 預設複利 — **可接受**
- 舊圖＝無標籤單利 cumsum（誤導為「累積報酬」）；改預設 compound＝帳戶淨值，與 `vectorized_backtest`／factor LS 的 cumprod 敘事對齊。
- 代價：與舊截圖數值不同；但 tab 明示＋footer 同時顯示另一種終值，可還原對照。**不建議改回預設單利**。

### B② `ValueError` on NaN／`y_pred_proba` — **route 行為不變；引擎不對稱 → P3-01**
- route `actual_return.fillna(0)` 後進引擎 ⇒ 既有 HTTP 路徑不因新 raise 變 500。
- 引擎對 `actual_returns` 非有限 → `ValueError`（正確 hardening）。
- `y_pred_proba`：NaN 比較為 False ⇒ 空手；**`+inf > threshold` 為 True ⇒ 持倉**（實跑確認）。與「禁靜默」精神不一致，但未改 route 合約。建議：`isfinite(y_pred_proba)` 同樣 raise，或至少文件化「非有限＝空手且禁 +inf」。

### B③ 前端 a11y／樣式／filename — **大致一致，可接受**
- 置於 `MonitoringTab` 的 `glass-panel` 內；tab 用 `emerald-400/20` 與同頁 export／強調色系一致。
- `role="tablist"`／`role="tab"`／`aria-selected`／`aria-label` 在場；缺鍵盤方向鍵（同頁其他圖亦無 tab 模式，不升 finding）。
- `ChartExportButton` filename=`strategy_equity_${mode}` — 已帶 mode。

### B④ `Field(description=...)` — **建議補（P3-02）**
- 類 docstring 進 JSON Schema `description`；**各欄 `description=None`**；`final_return_pct` schema 僅 `additionalProperties: number`，OpenAPI 看不到四鍵名。
- 同檔多數模型已用 `Field(..., description=...)` — EquityCurveData 不一致。

### B⑤ `API_SPECIFICATION.md` 10.8 — **現況不足但摩擦已知；可接受暫以 model docstring＋ROADMAP 為準**
- 10.8 仍只有 HTTP 路徑（無欄位表）。
- commit subject 寫「API_SPECIFICATION 10.8 補欄位」但 **該檔不在 `7d516540` diff** — 訊息過度宣稱；實質以 docstring／ROADMAP／TS 為準。閘門不可編時應避免在 commit message 宣稱已補。

---

## 段 C — 測試

### Mutation（本輪實跑，已還原）
- 改 `cum_strategy_compound`／`cum_benchmark_compound` 為 `cumsum` 後：**4 failed／1 passed**（`test_length_mismatch_and_non_finite_raise` 仍綠）。
- 還原後 **5 passed**；工作樹相對於 HEAD 無 diff。
- **可證偽**：把複利改回單利至少四條紅 — 通過。

### 前端單元測試 — **不強制本票補；若補給最小案例**
- 同頁其他 charts 亦無 `*.test.tsx`；本票核心在引擎＋契約，已有 5 條後端測。
- 若要求：`NaiveStrategyEquityChart.test.tsx` 餵固定 `EquityCurveData`（simple 終值 0、compound −25），`defaultMode='compound'` 先見「−25.00%」，click「單利」後主 footer 變「0.00%」且「另一種」互轉 — 可證偽 tab 綁錯序列。

---

## §0／§1 摘要（11 類；code review 適配）

1. 矛盾：commit message 宣稱 API_SPEC 補欄 vs diff 未含 — 見 P3-02。無單利／複利標籤互斥。
2. 漏項：OpenAPI 欄位說明／四鍵強制 — P2-01／P3-02。執行路徑前端已串。
3. 可測：5 條＋mutation 可證偽；前端無測（可選）。
4. quant：cumsum／cumprod 對應正確；空手 `1+0` 合理。
5. 過度工程：無。
6. OOM：無。
7. Cache：無。
8. API／型別：頂層舊鍵已拒；**嵌套 final 鍵未鎖** — P2-01。
9. 測試品質：mutation 有效；缺 proba 非有限測 — 併 P3-01。
10. Agent 可執行：小票已落地，本輪僅審。
11. 短命工：無。

## 被當成事實的未驗證假設（§0）
1. 「舊鍵無其他消費者」— **執行路徑 fact-verified**；docs 舊敘事仍在（非消費者）。
2. 「預設複利合理」— **可接受**（敘事對齊，非數學必然）。
3. 「`y_pred_proba` NaN＝空手可接受」— **部分成立**；未覆蓋 +inf → P3-01。

---

## GROK-R23-P2-01

**斷言**: `api.models.pattern_analysis_models.EquityCurveData.final_return_pct` 型別為裸 `Dict[str, float]`，不強制四鍵；舊鍵或空 dict 皆通過 pydantic，前端讀 `strategy_simple` 會在缺鍵時 runtime 爆。

**碼證**: `venv/bin/python` 實例化 `final_return_pct={"strategy": 10.0}` 與 `{}` 皆成功；`model_json_schema()["properties"]["final_return_pct"]`＝`additionalProperties: number`、無 `required` 四鍵。對照 `test_to_dict_matches_api_model_and_has_no_unlabeled_keys` 只鎖 producer `to_dict`，不鎖 API 入模約束。RECHECK: 同上兩行構造＋讀 schema。

**來源摘要**: api/models/pattern_analysis_models.py#8c41e1a2fbc3

[P2/MAJOR] 信心度=High。失敗模式：未來手組 response／部分 mock／過渡客戶端漏鍵 → 200 但 UI `toFixed` TypeError。修法：嵌套 `FinalReturnPct(BaseModel)` 四必填 float，或 `Field(..., json_schema_extra=…)`／validator 檢查 key set；TS 已具名，Python 應對齊。不擋本票 producer 正確路徑，但 breaking rename 後契約應機械封閉。

---

## GROK-R23-P3-01

**斷言**: 引擎對 `actual_returns` 非有限 raise，但 `y_pred_proba` 含 NaN 時靜默空手、含 `+inf` 時靜默視為持倉；與本票「禁靜默當 0」敘事不對稱。

**碼證**: `prediction_analyzer.py:168-170` 只 `isfinite(actual_returns)`；實跑 `proba=[0.9,nan,0.8]` → positions `[1,0,1]`；`[0.9,+inf,0.8]` → `[1,1,1]`。route `:1049` 未 `fillna` proba。RECHECK: 同上三行探針。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#60defe07cff8

[P3/MINOR] 信心度=High（行為）；Medium（是否本票必修）。NaN→空手常可辯「缺訊號不交易」；+inf→滿倉不可辯。修法：`not np.all(np.isfinite(y_pred_proba))` 同樣 ValueError，或 clip／文件化；補一測。route 已 fillna returns，HTTP 主路徑不受益於僅引擎 raise。

---

## GROK-R23-P3-02

**斷言**: EquityCurve 欄位無 `Field(description=…)`，且 `docs/API_SPECIFICATION.md` §10.8 仍僅 HTTP 路徑；commit `7d516540` subject 宣稱「API_SPECIFICATION 10.8 補欄位」但該檔不在 diff。

**碼證**: `EquityCurveData.model_fields[*].description` 全 `None`；`docs/API_SPECIFICATION.md:621-624` 只見 GET 路徑；`git show 7d516540 --name-only` 無 `API_SPECIFICATION.md`。RECHECK: 同上。

**來源摘要**: api/models/pattern_analysis_models.py#8c41e1a2fbc3

[P3/MINOR] 信心度=High。OpenAPI／外部讀者看不到單利／複利語意（只靠 class docstring 一段）。摩擦六十七若禁改 API_SPEC，應：(1) 至少補 `Field(description=…)`；(2) commit message 勿宣稱已補規格檔。不擋合併。

---

ASSUMPTIONS_VERIFIED: 單利 cumsum／複利 cumprod−1 與標籤一致；空手複利乘 1；final_pct×100；舊鍵無 runtime 消費者；mutation 4 紅後還原 5 綠；Dict 四鍵未強制；proba NaN/inf 行為如上
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → baseline 5 passed；mutation 4 failed／1 passed；restore 5 passed
FAILURES_SEEN: mutation 預期紅（已還原）；none unexpected
SCOPE_CHANGES: none（唯讀＋臨時 mutation 已還原）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）；指出 schema 缺口供後續加固
STATUS: DONE
