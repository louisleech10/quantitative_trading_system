接下來會讀 SPEC r2、RECONCILE 裁決表，並逐一對你 r1 的 findings 做閉合重驗。已對照 r2 全文與 RECONCILE，逐一重跑 r1 反例；完整產出如下（唯讀，編排端落檔）。

---

# IC1C SPEC r2 閉合重驗 — grok

**task-id**: IC1C-SPECREV  
**角色**: r1 原審查委員（章程 §B8：重跑同一反例，不憑「已修」信任）  
**輸入**:
- `docs/IC1C_NETIC_SPEC.md` v0.2 r2
- `handoffs/20260714-IC1C-SPECREV-RECONCILE.md`（17 筆全 ACCEPT）
- `handoffs/20260714-IC1C-SPECREV-grok.md`（r1）
**約束**: 唯讀；未改檔；未跑寫 `data_cache`；產出印 stdout 由編排端落檔  
**RECONCILE sha256**（`shasum -a 256`）: `d94d4c14cfa8f88abea661f72a725ae7a44b45e7c371c8dc945dd61d614b72e7`

---

## 1. r1 Findings 逐一閉合判定

### GROK-1（原 BLOCKING）— factor_returns 來源 / Task 1.2 e2e  
**判定: CLOSED**

| r1 反例 | r2 下是否仍構造得出 |
|---------|---------------------|
| 把 `compute_batch` dict 當 `pd.Series` 餵 `batch_analyze` | **否**。Task 1.2 改寫：不傳 factor_returns；`net_factor_return` 恒 unavailable+reason；依賴矩陣=1c 內不依賴 factor_return 模組（§P L80–82） |
| 用 `long_short_mean_return` scalar 冒充 series | **否**。§A + Task 1.1 明文禁以 `long_short_mean_return`（錯位構造）代填（L22, L78） |
| e2e 要求 `net_mean` 有限 float | **否**。改斷言 `status=="unavailable"` 且 reason 非空；finite net_mean 已刪 |

**r2 落點**: F1 ACCEPT → Task 1.2 fail-closed + 拆票 **1c-FR**（canonical series）。  
**備註**: 相對 r1 建議的「(i) 擴大 export series / (ii) 縮小驗收」，RECONCILE 採更嚴的 (ii)+拆票，並以 CODEX-1 錯位實證否決「先 export 錯位 ls_returns」——**不曲解** GROK-1，是加嚴。

---

### GROK-2（原 BLOCKING）— fail-closed / 5.0 bps 幽靈  
**判定: CLOSED**

| r1 攻擊路徑 | r2 下是否仍構造得出 |
|-------------|---------------------|
| 只送 `modules.net_ic_analysis:true`、不帶 cost → 靜默 5.0 bps | **否**。`cost_enabled` default=False；舊 request=gross-only、無 5bps 幽靈（Task 2.1、§R L126） |
| `config_override` 灌 `default_cost_bps` | **否**。API 層 reject `net_ic_analysis.{default_cost_bps,cost_bps,slippage_bps}`（L91） |
| schema Field default + `cfg.get(...,5.0)` 雙層 fallback | **否**。三處刪除 + analyzer enabled 缺 cost raise + grep `5.0`==0 驗收（L90–94, M5） |
| 硬編碼 scenarios `[1,3,5,10,20]` / NetICChart `useState(5)` | **否**。Task 2.2 刪；Phase 3 階梯改 `{c/2,c,2c,5c}` |

**r2 落點**: F4 ACCEPT → Task 2.1 typed nested + HTTP 邊界 422。

---

### GROK-3（原 BLOCKING）— Case B 後 summary 空洞  
**判定: CLOSED**

| r1 反例 | r2 下是否仍構造得出 |
|---------|---------------------|
| 刪 `net_ic` 不改 summary → KeyError / 假別名 | **否**。summary 契約重凍：`avg_cost_drag_return` 取代 `avg_ic_loss_pct`；`rank_correlation_gross_vs_net` **刪除**（1c-FR 恢復）；`profitable_count` 只計 evaluable（1c 恒 0）（L75） |
| summary 改了但 §G 未列 → 合法修法被 golden 擋 | **否**。§G G-NEW 全鍵 equality + 必變欄規則含 summary 契約（L57–62） |
| 保留 `avg_ic_loss_pct` 名改算 cost → 標籤謊言 | **否**。欄位更名刪舊名；M6 守 |

**r2 落點**: F5 ACCEPT。刪 rank corr（比 RECONCILE 原文「null+reason」更乾）屬可接受加嚴，不留 IC-vs-IC 殘影。

---

### GROK-4（原 BLOCKING）— §G 選擇性等值可假綠  
**判定: CLOSED**

| r1 反例 | r2 下是否仍構造得出 |
|---------|---------------------|
| rename `net_ic`→`cost_drag_return` 但公式仍 `IC−cost×turn×2` | **否**。canonical 全量重算 `cost_drag=(bps/1e4)×turnover`（**無 ×2**）+ 全樹禁 `net_ic` 鍵 + mutation 恢復混減必紅（L59–63, M1/M2） |
| 新錯欄不進 hash → 假綠 | **否**。全鍵集合 equality，多/少鍵=FAIL（L59） |
| Phase1 固定 cost vs Phase2 使用者輸入 golden 衝突 | **否**。G-OLD / G-NEW / G-NEW2 分層；`cost_bps` 等值僅限 Phase1（L60） |

**r2 落點**: F7 ACCEPT。手算門檻同步改為 10bps×1.5→**0.0015**（去 ×2，§T/F3），與 r1 舊 receipt 0.003 不同——屬 CODEX-2 正確性修正，非假綠缺口。

---

### GROK-5（原 NON-BLOCKING）— consumer-map 漏列  
**判定: CLOSED**

r1 漏列點在 §C 完整 manifest 均已入帳：
- `page.tsx:823`、`FeatureTierPanel:39`、export fixtures、phase24 `default==5`、`factories:505`
- **`compute_net_ic_proxy` 納入 1c scope**（Task 1.3，禁雙重標準）
- `slippage_bps`、NetICChart `0.1` turnover fallback、硬編 scenarios

**可證偽**:「只改 analyzer + 舊短清單」→ 現 consumer-map 強制逐點 red-on-break → **否**。

---

### GROK-6（原 NON-BLOCKING）— M1–M4 紙面 / 舊測固化錯  
**判定: CLOSED**

§V 重寫：M1–M8 各有 Property / Oracle / 具名 test(N|R) / Mutation probe；「新建 vs 改寫」表列 phase25/24/export/turnover 舊斷言為何錯。  
r1 缺口（無禁混減斷言、無 breakeven 數值、無 wiring）→ 現 M1/M3/M4 綁定新建測試名。

---

### GROK-7（原 NON-BLOCKING）— Phase 3 持倉期 vs bps 階梯  
**判定: CLOSED**

| r1 反例 | r2 下是否仍構造得出 |
|---------|---------------------|
| 宣稱「多持倉期」卻只掃 bps | **否**。F11 收斂：文件/UI 禁年化、禁跨 TF 直比；**持有期矩陣不入 1c**（拆 1c-FR）；掃描維度=使用者 cost 階梯 `{c/2,c,2c,5c}` + semantics 標籤（§T, Task 3.1） |
| 階梯未鎖 | **否**。演算法與 clamp 已寫死 |

r1 可選「turnover 乘數情境」未採——主建議為語意收斂，已滿足；**非殘留 BLOCKING**。

---

### GROK-8（原 NON-BLOCKING）— `net_ic` 鍵去留  
**判定: CLOSED**

Task 1.1：**`net_ic` 鍵禁止輸出，含任何別名**（含 cost_sensitivity 內）；F6 裁死。  
反例「別名=gross−cost 換皮存活」→ 全樹禁鍵 + M1 → **否**。

---

### GROK-9（原 NIT）  
**判定: CLOSED（1c 內）**

| 子項 | r2 |
|------|-----|
| `slippage_bps` 幽靈 | Task 2.1 **刪除**（F12） |
| batch 有 series 時 turnover 壓成 scalar | 1c 恒不餵 series / net 路徑 unavailable → 該近似 **N/A** |
| `force_modules` 與「必有 net_mean」衝突 | e2e 已改 unavailable |
| TODO 尚未生成 | 預期內（凍結後） |

---

### GROK-10（原 NIT）— 案 A 封存  
**判定: CLOSED**

§A L23：重提 A 須 σ-PIT + 交叉校準，不得混入 1c（F13）。

---

## 2. RECONCILE 是否曲解 grok findings

| 焦點 | 結論 |
|------|------|
| **F1 fail-closed + 拆 1c-FR** | **未曲解**。GROK-1 要嘛 export series、要嘛縮驗收；裁決=縮驗收+拆票，且用 CODEX-1 否決「export 錯位 series」扶正。方向與 GROK-1 一致並加嚴。 |
| **F3 去 ×2** | **非 grok 主 finding**（屬 CODEX-2）；r1 手算曾用 ×2 描述*現行錯公式*。r2 §T 改 `cost_drag=(bps/1e4)×turnover` 與 quantile 雙腿語意一致；**不推翻** GROK 的 B-strict（禁 IC−報酬），只修正成本倍數。 |
| **F11 持有期矩陣不入 1c** | **未曲解**。對齊 GROK-7「掃描維度=成本 bps，不是持倉期」；矩陣依賴 canonical series → 1c-FR 合理。 |
| **F5 rank_corr** | RECONCILE 寫 null+reason，r2 改**刪除**——比裁決表更嚴，**可接受**，非弱化。 |
| **17 筆全 ACCEPT** | GROK 四 BLOCKING 均落入 F1/F4/F5/F7，無被 REJECT/降級 silently。 |

**RULING-FINAL B-strict**: 與 r1「B + 禁 net_ic 別名」一致；codex fail-closed 收緊為超集。

---

## 3. r2 新引入洞（GROK-R2-*）

### ID: GROK-R2-1  
**嚴重度: NON-BLOCKING**  
**面向**: `net_factor_return` 佔位 schema 形狀不一致

**證據**:
- Task 1.1 白名單寫 `net_factor_return: null+reason`（L73）
- Task 1.2 / e2e 寫 `{"status":"unavailable","reason":"..."}` 且斷言 `.status`（L81–82）
- §A 用語「一律 unavailable+reason」未釘 object vs null+sibling

**殘留反例**: 實作 A 出 `null`+頂層 `reason`；實作 B 出 status 物件——兩者都可稱「符合 SPEC 一句」，但只有 B 過 e2e。

**建議**: Task 1.1 白名單與 types.ts **統一**為 status 物件形（與 1.2 e2e 對齊）；`breakeven`/`profitable` 同步同一 discriminated union。

---

### ID: GROK-R2-2  
**嚴重度: NON-BLOCKING**  
**面向**: `cost_enabled=False` 鍵集合 vs 全量 schema / §G

**證據**:
- Task 1.1 單一共用白名單含 `cost_bps` / `cost_drag_return` / `cost_sensitivity[]`（L73）
- 同 Task 邊界：`cost_enabled=False(無 cost 子樹)`（L77）
- §R：gross-only、無 cost 子樹（L126）
- §G：全鍵集合 equality 未分 profile（L59）

**殘留反例**: 實作永遠吐滿鍵（cost 欄 null）→ 違反「無 cost 子樹」；實作省略 cost 鍵 → 違反單一白名單 equality。

**建議**: 凍 **兩套** 鍵白名單：`SCHEMA_GROSS_ONLY` / `SCHEMA_COST_ENABLED`；§G 依 `cost_enabled` 選集；M4/M5 各綁一 profile。

---

### ID: GROK-R2-3  
**嚴重度: NIT**  
**面向**: `compute_net_factor_return` 公開面是否 1c 內保留

Task 1.1 刪 `compute_net_ic`，未寫 `compute_net_factor_return` 去留。若 factory 直呼仍可算「有 series 的 net return」，與「1c 恒 unavailable」敘事並存時易誤導。建議：1c 內方法保留但 `batch_analyze` **忽略**注入的 factor_returns 並固定 unavailable，或標 `@deprecated` 至 1c-FR。

---

### ID: GROK-R2-4  
**嚴重度: NIT**  
**面向**: Task 1.2 用語「來源不存在」

模組 `FactorReturnAnalyzer` **存在**；缺的是 canonical time-aligned series export。建議改「canonical series 未建立（1c-FR）」，避免實作者誤刪整個 factor_return 模組。

---

## 4. 面向總表（r2）

| r1 ID | 嚴重度(r1) | r2 判定 | 殘留可構造反例 |
|-------|------------|---------|----------------|
| GROK-1 | BLOCKING | **CLOSED** | 無 |
| GROK-2 | BLOCKING | **CLOSED** | 無 |
| GROK-3 | BLOCKING | **CLOSED** | 無 |
| GROK-4 | BLOCKING | **CLOSED** | 無 |
| GROK-5 | NON-BLOCKING | **CLOSED** | 無 |
| GROK-6 | NON-BLOCKING | **CLOSED** | 無 |
| GROK-7 | NON-BLOCKING | **CLOSED** | 無 |
| GROK-8 | NON-BLOCKING | **CLOSED** | 無 |
| GROK-9 | NIT | **CLOSED** | 無 |
| GROK-10 | NIT | **CLOSED** | 無 |
| GROK-R2-1 | — | 新 | schema 形狀歧義（非原反例復活） |
| GROK-R2-2 | — | 新 | cost on/off 雙 profile 未凍 |
| GROK-R2-3/4 | — | 新 NIT | 用語/死碼面 |

**原 BLOCKING 復開數: 0**  
**新 BLOCKING: 0**（R2-1/2 為可在 TODO 微修的起草歧義，不阻擋 B-strict 主路徑凍結）

---

## 5. Verdict

r1 四條 BLOCKING 反例在 r2 條文下均**無法再構造**；RECONCILE 對 grok 無曲解或弱化；F3 去 ×2 / F11 拆持有期 / F1 拆 1c-FR 與 B-strict 一致。新洞僅 NON-BLOCKING/NIT 起草對齊項，建議 TODO 生成前順手釘死 schema 形狀與雙 profile，**不構成 REJECT**。

```
ASSUMPTIONS_VERIFIED: r1 GROK-1..10 反例逐條對 r2 §A/§T/§C/§G/§P/§V 重跑；RECONCILE F1/F3/F11 與 grok 意圖交叉比對；turnover_analyzer.quantile 仍為 top-mask abs(diff)（雙腿語意與 §T 一致）；proxy 仍為 IC−λ×turn（Task 1.3 覆蓋）；RECONCILE sha256=d94d4c14cfa8f88abea661f72a725ae7a44b45e7c371c8dc945dd61d614b72e7
TESTS_RUN: 未跑 pytest（唯讀閉合重驗）；shasum -a 256 handoffs/20260714-IC1C-SPECREV-RECONCILE.md
FAILURES_SEEN: none
SCOPE_CHANGES: none（審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）；註：r2 成本公式相對 r1 receipt 去 ×2（0.003→0.0015）屬 F3 已裁
HANDOFF_NOT_UPDATED: 唯讀，使用者要求 stdout 交卷、編排端落檔
OUTPUT_PATH_EXPECTED: handoffs/20260714-IC1C-SPECREV-R2-grok.md
```

STATUS: DONE

SPEC-REVIEW-R2: APPROVE
RECONCILE-STAMP APPROVED — grok 2026-07-14 sha256:d94d4c14cfa8f88abea661f72a725ae7a44b45e7c371c8dc945dd61d614b72e7
