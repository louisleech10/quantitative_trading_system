# GAP-3 EVENT SPEC R4 終輪閉合（Z1–Z4 忠實度＋新錯掃描）— grok

family: grok  
task-id: 20260820-GAP3-X-REVIEW-R4  
scope: `docs/GAP3_EVENT_SPEC.md` @ `3b254e2f`（sha256 `d65745d4962b…`）；對照 R3 synth Z1–Z4；禁改碼  
brief: `handoffs/20260820-gap3-spec-r4-BRIEF.md`  
reconcile: `handoffs/reconcile/20260820-gap3-x-review-r3/synth.md`

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| R3 reconcile completeness PASS（6/6）＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 synth 正文＋SPEC diff 對照為準 |
| R3 修訂版 `template_check spec` PASS | **fact-verified** | 本輪重跑 → `TEMPLATE PASS (spec)`，rc=0 |
| assumed: Z2 fail-closed（`drop_threshold` 未設 ⇒ c 不啟用）不使 a/b/unclassifiable 覆蓋歧義 | **本輪攻後＝成立** | 見下表 Z2 特別面：殘差路徑明確落入 `unclassifiable`；預設 a/b 在 R0 軸互斥 |
| assumed: Z1 兩層 receipt schema 與 §G-2 三形 oracle 對得上 | **本輪攻後＝成立** | D2-4 事件級含 entry 欄；§G-2 手算 per-TF `feature_cutoff`＋三形含 `entry_at_ms`／`entry_price_source`；D2-4 明文「§G-2 驗兩層」 |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ d65745d4962bca23b27b5d373bdc281bc47f3724e0cf0898a85f6aa86f2d5ec6（＝brief）
git rev-parse 標的 commit → 3b254e2f…（＝brief）
bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md → TEMPLATE PASS，rc=0
git diff c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md → 12 行／6±；恰對 Z1–Z4 四落點
```

---

## 1. Z1–Z4 寫回忠實度表（composer/grok 本職）

| 群集 | synth 處置要點 | SPEC 落點 | 忠實？ | 特別面（brief） |
|---|---|---|---|---|
| Z1 | D2-4 兩層：事件級＋per-TF；兩層入 SoT；§G-2 驗兩層 | D2-4=:33；§G-2=:107；D1-6=:27 | **忠實** | **兩層 vs 六欄**：事件級持 `decision_at_ms`／`entry_at_ms`；per-TF 持 `feature_cutoff_ms`；六欄不變式仍在 D2-1=:30。預設 `close_to_close` 下 `entry_at ≤ label_start`（含 equality；`next_open`≈t₀ close）。§G-2 三形（k=0／k>0／`next_open`）＋手算 cutoff＝兩層可證偽 |
| Z2 | `drop_threshold` 無預設／`default=null`；未設 ⇒ c 不啟用；a/b＋unclassifiable 覆蓋；x 入白話閘 | B1.5=:184 | **忠實** | **fail-closed 覆蓋**：c 規則整條跳過（不發明 x）；命中 a→a、b→b、多類／窗不全／零規則命中→`unclassifiable`（「僅由 a/b 與 unclassifiable 覆蓋」）。預設 `trigger=0.05` vs `range=0.01` ⇒ a∩b＝∅，無 a/b 搶答歧義。使用者可手標 `c_drop`（B1.0 匯入值集仍含 c）。**不受理**再攻 x 無預設（brief） |
| Z3 | D4-2 改 `counterexample_kind_effective`＋`n_unclassifiable` | D4-2=:43 | **忠實** | 與 B1.0=:126／B2.2=:221 全局 derived 消費一致；無殘留「按原始 `counterexample_kind` 分層」契約正文 |
| Z4 | B1.4＋M8：三道硬檢（非退化／非恆等／經驗分位）；恆等排列必觸發 (i)(ii) | B1.4=:173；M8=:367 | **忠實** | **M8 vs B1.4**：M8 明文「B1.4 定式」＋同三道；`n_unique>1`＝`n_unique_perm_stats > 1` 縮寫，定式不分裂；假綠路徑「觀測值∈觀測值」已封 |

**漂移處列出**: 無須阻擋收斂之語意漂移。下列為**非升級**殘差（對齊 R3 呈現層級不升級慣例）：
- B1.1 標題仍寫「per-TF 收據」、改法寫「逐事件逐 TF」——Z1 處置範圍＝D2-4；B1.1 目標句「D2 全落地」已涵蓋兩層，agent 讀 D2-4 即可，不構成反向裁決。
- B1.5 驗證仍寫「手造三類／每門檻」——c 邊界在測試內顯式設 `drop_threshold` 即可；與 `default=null` 不互斥。
- §A「待確認：無」與 B1.5「x 列入白話閘」分屬不同閘（實作前 vs stamp 後白話閘）；brief 不受理重開 x 預設，不升級。

---

## 2. 新錯掃描（Z 寫回是否踩舊裁／十一類焦點）

| 面 | 結果 |
|---|---|
| X1 offset／六欄 | 未破；Z1 只補 receipt 分層持久化 |
| X2 label 錨＝t₀ close | 未改動 |
| X4 unclassifiable 不猜 | Z2 強化 fail-closed（禁發明 drop x），非反向 |
| X8 M1–M12 | Z4 補強 M8 牙力；未刪條 |
| Y1 entry 映射 | Z1 把 Y1 欄位寫進 D2-4 事件級，閉合 R3 殘縫 |
| Y2／Y3／Y5 | Z2／Z3／Z4 各收窄縫；無反向 |

§1 十一類（本輪焦點＝Z 寫回面）：矛盾／漏項／不可測／quant／過度工程／OOM／cache／API／測試／agent 可執行／短命工 → **無新 BLOCKING/MAJOR**。

---

## 3. brief 必答

1. **Z 寫回忠實度＋新錯掃描**: 上表；4/4 **忠實**；特別三面（D2-4 兩層↔六欄／§G-2、Z2 fail-closed 覆蓋、M8↔B1.4）均通過；**無實質新錯**。  
2. **可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？** **可以**——本家 **0 findings**（sentinel 如下）；`drop_threshold` 之 x 屬白話閘議題（已在 B1.5 掛單），非本輪契約空洞。

---

## Verdict：可進三家 RECONCILE-STAMP＋使用者白話閘

R3 四群集寫回可證偽對照 synth；兩層 receipt 與六欄／§G-2 三形對得上；Z2 fail-closed 下 a/b/unclassifiable 覆蓋自洽；M8 三道硬檢與 B1.4 定式一致。不需再修補 SPEC 才能 stamp。

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；Z1–Z4 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r3/synth.md` 處置，特別面（D2-4 兩層 receipt↔六欄不變式／§G-2 三形、Z2 fail-closed 下 a/b/unclassifiable 覆蓋、M8 三道硬檢↔B1.4）未發現新 BLOCKING/MAJOR。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `d65745d4962b…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md` → 僅 header／D2-4／D4-2／B1.4／B1.5／M8 六處 ±；讀檔錨點 D2-1=:30、D2-4=:33、D4-2=:43、B1.4=:173、B1.5=:184、M8=:367、§G-2=:107；`drop_threshold=0.05` 字面＝0 命中；D4 分層僅 `counterexample_kind_effective`；M8 引用「B1.4 定式」＋三道硬檢與 B1.4 (i)(ii)(iii) 同構；Z2 覆蓋＝c 跳過＋a/b 互斥（0.05 vs 0.01）＋殘差 `unclassifiable`。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d65745d4962b; handoffs/reconcile/20260820-gap3-x-review-r3/synth.md#fd7610553bcf; handoffs/20260820-gap3-spec-r4-BRIEF.md#2a424870a0d3

sentinel：0 findings（實質）；上列為 R4 Z1–Z4 忠實度＋新錯掃描之機械複驗摘要。

---

## 被當成事實的未驗證假設（§0 殘列）

| 宣稱 | 判定 |
|---|---|
| Z2 fail-closed 不生 a/b/unclassifiable 歧義 | 本輪攻後改為 **fact-verified** |
| Z1 兩層 schema ↔ §G-2 三形 | 本輪攻後改為 **fact-verified** |
| template_check PASS | **fact-verified**（本輪重跑） |
| Z1–Z4 寫回無語意漂移 | **fact-verified**（無實質漂移） |

ASSUMPTIONS_VERIFIED: SPEC @3b254e2f sha256=brief；template_check PASS；Z1–Z4 逐群集對照 synth 無實質漂移；兩層↔六欄／§G-2、Z2 覆蓋、M8↔B1.4 三特別面通過  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → brief 相符；completeness 見收尾  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（審查 only）
