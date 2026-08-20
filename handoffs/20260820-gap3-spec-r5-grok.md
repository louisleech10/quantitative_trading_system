# GAP-3 EVENT SPEC R5 終輪閉合（W1 忠實度＋新錯掃描＋R3 誤判更正認可）— grok

family: grok  
task-id: 20260820-GAP3-X-REVIEW-R5  
scope: `docs/GAP3_EVENT_SPEC.md` @ `a8bb7634`（sha256 `57a429d18129…`）；對照 R4 synth W1；禁改碼  
brief: `handoffs/20260820-gap3-spec-r5-BRIEF.md`  
reconcile: `handoffs/reconcile/20260820-gap3-x-review-r4/synth.md`

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| R4 reconcile completeness PASS（3/3）＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 synth 正文＋SPEC diff 對照為準 |
| R4 修訂版 `template_check spec` PASS | **fact-verified** | 本輪重跑 → `TEMPLATE PASS (spec)`，rc=0 |
| assumed: 三段鏈拆分後無其他條文仍隱含 `entry_at ≤ label_start` | **本輪攻後＝成立** | 全文掃：唯一含該子串處＝D2-1「單一鏈…廢除」敘述；D1-6／AR-1／§G-2 皆改三段鏈或「無強制順序」；Tasks／§V／§N 無殘留強制序 |
| assumed: `label_start` 依 mode 機械定義與 D1-5 label 錨不變式相容 | **本輪攻後＝成立** | `close_to_close` ⇒ `label_start`＝t₀ close＝D1-5 錨；`open_*` ⇒ `label_start`＝entry 時點＝刻意改 mode（D1-3 已要求 `label_price_mismatch`）；D1-5 核心＝decision_offset 不移動 close_to_close 錨，與 W1 模式表不互斥 |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 57a429d18129ad15c0e0eba5d3d6e2a96d820b9b8e335972c22fa23c95879098（＝brief）
git rev-parse／cat-file → a8bb7634…（＝brief）
bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md → TEMPLATE PASS，rc=0
git diff 3b254e2f..a8bb7634 -- docs/GAP3_EVENT_SPEC.md → 9+/5−；恰落 D1-6／D2-1／D2-4／AR-1／§G-2
grep -nE 'entry_at[[:space:]]*[≤<=]+[[:space:]]*label_start' docs/GAP3_EVENT_SPEC.md → 僅 L30「廢除」敘述
```

---

## 1. W1 寫回忠實度表（composer/grok 本職）

| 落點 | synth W1 處置要點 | SPEC 落點 | 忠實？ |
|---|---|---|---|
| D2-1 三段鏈 | PIT／label／持有三段；廢單一鏈；`entry_at`↔`label_start` 無強制序 | D2-1=:30-34 | **忠實** |
| label_start 機械定義 | `close_to_close`⇒t₀ close；`open_*`⇒entry 時點 | D2-1=:32 | **忠實** |
| D1-6 註記 | `entry_at` 對 `label_start` 無強制順序 | D1-6=:27 | **忠實** |
| receipt 三新欄 | `label_start_ms`／`label_end_ms`／`entry_after_label_start` | D2-4=:37 | **忠實** |
| §G-2 組合案例 | 各 mode 之 start/end exact；`next_open`×`close_to_close` ⇒ flag=true＋三段鏈全過 | §G-2=:111 | **忠實** |
| AR-1 指針 | 時間不變式＝D2-1 三段鏈 | AR-1=:75 | **忠實** |
| 禁用組合 | 無（允許兩數並排） | D2-1 明文「合法語意」；無禁組合條 | **忠實** |

**漂移處列出**: 無須阻擋收斂之語意漂移。下列為**非升級**殘差：
- 檔頭來源段仍止於 R3 收斂敘事、未列 R4／W1（呈現層；契約正文 D2-1／D2-4／§G-2 已寫回，不構成反向裁決）。
- B1.0 衍生欄仍寫「六時間欄」總稱、未複列三新 receipt 鍵——D2-4 為唯一列舉處（JSON SoT 鐵律），agent 讀 D2-4 即可。

---

## 2. R3 本家誤判更正（brief 專項）

**認可 W1／CODEX-R4-P1-01 更正；撤回 R3「五語意皆滿足 `entry_at ≤ label_start`」判斷。**

| 項 | 內容 |
|---|---|
| 原誤判出處 | `handoffs/20260820-gap3-spec-r3-grok.md` Y1 特別面：「預設 U4b `close_to_close` 下五語意皆滿足 `decision_at ≤ entry_at ≤ label_start`（含 equality）」 |
| 錯因 | 把 `next_open` 近似成「≈t₀ close」；實則 D1-6：`next_open`＝t₀ **之後下一根**錨定 TF bar 之 open |
| 反碼證（時間序） | t₀ open ＜ t₀ close ＜ next bar open（正長度 bar）；`close_to_close`⇒`label_start`＝t₀ close；`next_open`⇒`entry_at`＝next open ⇒ **`entry_at > label_start`**；舊單一鏈必炸 |
| 本輪手推 | `entry_at > label_start`＝True；`entry_after_label_start` 應為 true——與 D2-1／§G-2 寫回一致 |
| 反碼證？ | **無**——不提出推翻 W1 的反證 |

R4 本家 sentinel 表內「`next_open`≈t₀ close」同屬該誤近似之殘影；本輪一併作廢，以三段鏈＋旗標為準。

---

## 3. 新錯掃描（W1 寫回是否踩 X/Y/Z）

| 面 | 結果 |
|---|---|
| X1 offset／不設 ms 覆寫 | 未破；AR-1 改指三段鏈＋`decision_at ≤ t0_open_ms` |
| X2 label 錨＝t₀ close | `close_to_close` 路徑強化（mode 機械定）；未改 decision 脫鉤 |
| X4／Y2／Y3／Z2 分類 | 未觸及 |
| Y1 entry 映射 | D1-6 保留五語意＋`decision_at ≤ entry_at`；僅解除對 `label_start` 強制序 |
| Z1 兩層 receipt | 事件級**擴**三欄，非刪兩層；§G-2 仍驗兩層 |
| Z3／Z4／M8 | 未觸及 |
| U4b 兩數並排 | W1 明確允許 `next_open`×`close_to_close`＋`entry_after_label_start`——與 U4b 同向 |

§1 十一類（本輪焦點＝W1 寫回面）：矛盾／漏項／不可測／quant／過度工程／OOM／cache／API／測試／agent 可執行／短命工 → **無新 BLOCKING/MAJOR**。

---

## 4. brief 必答

1. **忠實度＋新錯掃描**: 上表；W1 七落點 **忠實**；全文無殘留強制 `entry_at ≤ label_start`；D1-5↔mode 表相容；**認可** R3 誤判被 W1 更正；**無實質新錯**。  
2. **可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？** **可以**——本家 **0 findings**（sentinel 如下）。

---

## Verdict：可進三家 RECONCILE-STAMP＋使用者白話閘

R4 W1 單縫寫回可證偽對照 synth；三段鏈／receipt 三欄／§G-2 組合案例齊備；與 X/Y/Z 無碼證衝突；本家 R3「五語意皆滿足 `entry_at ≤ label_start`」判斷撤回。不需再修補 SPEC 才能 stamp。

---

## GROK-R5-P3-00

**斷言**: 本輪逐項核對後無 finding；W1 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r4/synth.md`（D2-1 三段鏈／receipt 三新欄／§G-2 組合案例），全文無殘留強制 `entry_at ≤ label_start`，D1-5 與 mode 機械 `label_start` 相容，並認可撤回 R3「五語意皆滿足 `entry_at ≤ label_start`」之誤判。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `57a429d18129…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 3b254e2f..a8bb7634 -- docs/GAP3_EVENT_SPEC.md` → 僅 D1-6／D2-1／D2-4／AR-1／§G-2（± header 無關契約）；讀檔錨點 D1-6=:27、D2-1=:30-34、D2-4=:37、AR-1=:75、§G-2=:111；`grep -nE 'entry_at[[:space:]]*[≤<=]+[[:space:]]*label_start'` → 唯 L30「廢除」；手推 `next_open`×`close_to_close` ⇒ `entry_at > label_start`；對照 R3 本家 Y1 特別面原文（`handoffs/20260820-gap3-spec-r3-grok.md`）確認誤判出處並撤回。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#57a429d18129; handoffs/reconcile/20260820-gap3-x-review-r4/synth.md#089874745d80; handoffs/20260820-gap3-spec-r5-BRIEF.md#2be145bd10f8; handoffs/20260820-gap3-spec-r3-grok.md#ae87c4d78ede

sentinel：0 findings（實質）；上列為 R5 W1 忠實度＋殘留單一鏈全文掃＋R3 誤判更正認可之機械複驗摘要。

---

## 被當成事實的未驗證假設（§0 殘列）

| 宣稱 | 判定 |
|---|---|
| 三段鏈後無殘留 `entry_at ≤ label_start` 強制 | 本輪攻後改為 **fact-verified** |
| `label_start` mode 定義 ↔ D1-5 相容 | 本輪攻後改為 **fact-verified** |
| template_check PASS | **fact-verified**（本輪重跑） |
| W1 寫回無語意漂移 | **fact-verified**（無實質漂移） |

ASSUMPTIONS_VERIFIED: SPEC @a8bb7634 sha256=brief；template_check PASS；W1 七落點對照 synth 忠實；殘留單一鏈全文掃僅「廢除」敘述；D1-5↔mode 相容；R3 誤判撤回並無反碼證  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → brief 相符；completeness 見收尾  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（審查 only）
