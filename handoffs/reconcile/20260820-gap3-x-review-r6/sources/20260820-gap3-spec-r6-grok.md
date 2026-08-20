# GAP-3 EVENT SPEC R6 終輪閉合（V1 忠實度＋新錯掃描）— grok

family: grok  
task-id: 20260820-GAP3-X-REVIEW-R6  
scope: `docs/GAP3_EVENT_SPEC.md` @ `db85611a`（sha256 `09b05b39aa1380…`）；對照 R5 synth V1；禁改碼  
brief: `handoffs/20260820-gap3-spec-r6-BRIEF.md`  
reconcile: `handoffs/reconcile/20260820-gap3-x-review-r5/synth.md`

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| R5 reconcile completeness PASS（3/3）＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 synth 正文＋SPEC diff 對照為準 |
| R5 修訂版 `template_check spec` PASS | **fact-verified** | 本輪重跑 → `TEMPLATE PASS (spec)`，rc=0 |
| assumed: mode-scoped 錨定義與 D2-1 label 鏈、D1-3 條件必填、§G-2 oracle 全文一致 | **本輪攻後＝成立** | D1-5 三 mode 錨表＝D2-1 `label_start` 機械表；D1-3 `≠close_to_close`⇒`label_price_mismatch` 仍成立；§G-2「各 mode exact」＋`next_open×close_to_close` 旗標案例未破 |
| assumed: §A 兩題登記足以擋「裁決前偷跑實作」 | **本輪攻後＝成立** | §A 標題「未確認前不得實作」＋題②明文「裁決前 B1.0 契約不得凍結」；題① `drop_threshold default=null` fail-closed（B1.5 同文） |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f（＝brief）
git rev-parse／cat-file → db85611a…（＝brief）
bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md → TEMPLATE PASS，rc=0
git diff a8bb7634..db85611a -- docs/GAP3_EVENT_SPEC.md → 恰三處：D1-2／D1-5／§A（±「已確認結果」標頭無關契約）
```

---

## 1. V1 寫回忠實度表（composer/grok 本職）

對照 `handoffs/reconcile/20260820-gap3-x-review-r5/synth.md` V1 處置三點：

| 落點 | synth V1 處置要點 | SPEC 落點 | 忠實？ |
|---|---|---|---|
| D1-5 mode-scoped 錨 | `label_return_mode` 機械唯一；c2c⇒t₀ close；open_*⇒entry 進場價；與 decision_offset／entry 語意脫鉤選規則；同一輸入起點唯一；join 禁限 c2c 路徑 | D1-5=:26 | **忠實** |
| D1-2 scope 註記 | 「一律相對 t₀ close」＝**預設模式下**；U4b「一律」是否全禁＝§A② | D1-2=:23 | **忠實** |
| §A 兩題白話閘 | ①`drop_threshold` x；②U4b 一律範圍；裁決前 B1.0 不得凍結 | §A=:71-73 | **忠實** |

**漂移處列出**: 無須阻擋收斂之語意漂移。下列為**非升級**殘差（不列 finding）：
- 檔頭來源段仍止於 R3 收斂敘事、未列 R4／R5／V1（呈現層；契約正文 D1-2／D1-5／§A 已寫回）。
- D1-4 誠實揭露仍寫「標籤基準（t₀ close）」——屬 U4b／§2-2 預設路徑之兩數並排敘事；open_* 是否保留＝§A② 白話閘議題（brief 不受理替使用者作答）；與 D1-5 機械唯一不構成可執行雙起點。

---

## 2. 消歧後同一輸入 label 起點唯一（V1 原反例面）

| 輸入（mode × entry） | D1-5 錨 | D2-1 `label_start` | 唯一？ |
|---|---|---|---|
| `close_to_close` × `next_open` | t₀ close | t₀ bar close_time | **唯一**；`entry_at`=next open ＞ `label_start` ⇒ `entry_after_label_start=true`（W1） |
| `close_to_close` × `trigger_open` | t₀ close | t₀ bar close_time | **唯一**（entry≠label 起點，兩數並排） |
| `open_to_close` × `next_open`（若 §A②裁保留） | entry 進場價 | entry bar entry 時點 | **唯一**（與上列不同 mode＝不同契約輸入） |
| `open_to_horizon_close` × 任一 entry | entry 進場價 | entry bar entry 時點 | **唯一** |

原 V1 衝突（D1-5 無條件 t₀ close **同時** D2-1 open_*＝entry）已消：同一 `(label_return_mode, …)` 不再可讀出兩個起點。RULING-CONFLICT 面（U4b「一律」是否全禁非 c2c）已登記 §A② 轉白話閘——本家判此登記方式**可接受**（fail-closed：未裁前不得實作／不得凍 B1.0）。

---

## 3. 新錯掃描（V1 寫回是否踩 X/Y/Z/W）

| 面 | 結果 |
|---|---|
| X2 label 錨脫鉤 decision | 保留並收窄：c2c 路徑禁 `decision_at` join；錨不隨 `decision_offset_bars` 移動（B2.3 邊界③） |
| W1 三段鏈／receipt 三欄／§G-2 | diff **未觸**；D2-1／D2-4／§G-2 原文仍在 |
| Y1 entry 映射 D1-6 | 未觸 |
| Z1 兩層 receipt | 未觸 |
| Z2 `drop_threshold` | 升格為 §A① 明文白話閘題；B1.5 仍 `default=null` fail-closed |
| D1-3 條件必填／mismatch | 與 mode-scoped 相容：`≠close_to_close` 沿用主線 ⇒ `label_price_mismatch=true` |
| U／AR／X／Y／Z／W 已裁 | 無碼證直接衝突；不重開 |

§1 十一類（本輪焦點＝V1 寫回面）：矛盾／漏項／不可測／quant／過度工程／OOM／cache／API／測試／agent 可執行／短命工 → **無新 BLOCKING/MAJOR**。

---

## 4. brief 必答

1. **忠實度＋新錯掃描**: 上表；V1 三落點 **忠實**；mode-scoped 與 D2-1／D1-3／§G-2 一致；§A 兩題＋B1.0 凍結閘足以擋偷跑；與 X/Y/Z/W **無新碼證衝突**；**無實質新錯**。  
2. **可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？** **可以**——本家 **0 findings**（sentinel 如下）。§A 兩題本身即白話閘議題，不阻擋 stamp 流程啟動。

---

## Verdict：可進三家 RECONCILE-STAMP＋使用者白話閘

R5 V1 單縫寫回可證偽對照 synth；D1-2 scope／D1-5 mode-scoped／§A 兩題齊備；消歧後同一輸入 label 起點唯一；RULING-CONFLICT 面已合法轉白話閘。不需再修補 SPEC 才能 stamp。

---

## GROK-R6-P3-00

**斷言**: 本輪逐項核對後無 finding；V1 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r5/synth.md`（D1-2 預設模式 scope／D1-5 mode-scoped 錨／§A 兩題＋B1.0 不得凍結），消歧後同一輸入之 label 起點唯一，mode-scoped 與 D2-1 label 鏈／D1-3／§G-2 全文一致，與 X/Y/Z/W 無新碼證衝突。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `09b05b39aa1380…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff a8bb7634..db85611a -- docs/GAP3_EVENT_SPEC.md` → 僅 D1-2／D1-5／§A（±「已確認結果」標頭）；讀檔錨點 D1-2=:23、D1-5=:26、D2-1 label 鏈=:32、D1-3=:24、§A=:71-73、§G-2=:113；手推 `close_to_close`×`next_open` ⇒ `label_start`=t₀ close 唯一且 `entry_after_label_start=true`；`open_*`×entry ⇒ `label_start`=entry 時點唯一（與 c2c 不同 mode）；對照 synth V1 三處置 0 漂移。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#09b05b39aa13; handoffs/reconcile/20260820-gap3-x-review-r5/synth.md#4df00ce824b6; handoffs/20260820-gap3-spec-r6-BRIEF.md#34b671f7a4ca

sentinel：0 findings（實質）；上列為 R6 V1 忠實度＋同一輸入唯一性手推＋D2-1／D1-3／§G-2 相容攻擊＋X/Y/Z/W 新錯掃描之機械複驗摘要。

---

## 被當成事實的未驗證假設（§0 殘列）

| 宣稱 | 判定 |
|---|---|
| mode-scoped ↔ D2-1／D1-3／§G-2 一致 | 本輪攻後改為 **fact-verified** |
| §A 兩題足以擋偷跑實作 | 本輪攻後改為 **fact-verified**（文面閘；實作遵守屬後續 gate） |
| template_check PASS | **fact-verified**（本輪重跑） |
| V1 寫回無語意漂移 | **fact-verified**（無實質漂移；D1-4／檔頭為非升級殘差） |

ASSUMPTIONS_VERIFIED: SPEC @db85611a sha256=brief；template_check PASS；V1 三落點對照 synth 忠實；同一輸入 label 起點唯一；mode-scoped↔D2-1/D1-3/§G-2；§A 凍結閘在場；X/Y/Z/W 未破  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → brief 相符；completeness 見收尾  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（審查 only）
