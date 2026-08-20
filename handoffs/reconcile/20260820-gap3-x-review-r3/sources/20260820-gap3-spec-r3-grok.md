# GAP-3 EVENT SPEC R3 閉合驗證（Y1–Y6 忠實度＋新錯掃描）— grok

family: grok  
task-id: 20260820-GAP3-X-REVIEW-R3  
scope: `docs/GAP3_EVENT_SPEC.md` @ `c7ac693e`（sha256 `377c9a39b01e…`）；對照 R2 synth Y1–Y6；禁改碼  
brief: `handoffs/20260820-gap3-spec-r3-BRIEF.md`  
reconcile: `handoffs/reconcile/20260820-gap3-x-review-r2/synth.md`

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| R2 reconcile completeness PASS（8/8） | fact-verified（brief） | 未重跑 `--lock`；以 synth 正文＋SPEC diff 對照為準 |
| R2 修訂版 `template_check spec` PASS | **fact-verified** | 本輪重跑 → `TEMPLATE PASS (spec)`，rc=0 |
| assumed: Y1–Y6 寫回無語意漂移、Y2 預設值忠實於使用者 §2-4 原例 | **本輪攻後＝不成立（漂移）** | 逐條對照 → **無實質漂移**；Y2 預設 `0.05/0.0/0.01/0.05` 對齊 §2-4「漲≥5%／不續漲／上下 1%／跌 x%（x 取 5% 可調）」 |
| assumed: Y6「同一 validator、accepted 三值＋platform_random_bars 恆拒」與 B3.2／§N-7 全文一致 | **本輪攻後＝成立** | B1.0 accepted 三值＋恆拒 reason；B3.2 產 `platform_same_trigger_rule` 過同一 validator；§N-7 仍 `needs-research` 僅涵蓋 random bars |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 377c9a39b01e23b804fe7ea6fc88c9390abd1e992d6d2b47d9167d9abd521c07（＝brief）
git rev-parse HEAD／標的 commit → c7ac693e…（＝brief）
bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md → TEMPLATE PASS，rc=0
git diff 21135434..c7ac693e -- docs/GAP3_EVENT_SPEC.md → R2 修訂面＝Y1–Y6 對應段落
```

---

## 1. Y1–Y6 寫回忠實度表（composer/grok 本職）

| 群集 | synth 處置要點 | SPEC 落點 | 忠實？ | 特別面（brief） |
|---|---|---|---|---|
| Y1 | D1-6 五語意→bar/price；`entry_at`；`decision_at ≤ entry_at`；receipt 增 `entry_at_ms`＋`entry_price_source`；B2.1／§G-2 三形 oracle | D1-6=:27；§G-2=:107；B2.1=:210 | **忠實** | **D1-6 ↔ D2 六欄**：預設 U4b `close_to_close`（label_start≈t₀ close）下五語意皆滿足 `decision_at ≤ entry_at ≤ label_start`（含 equality）。D1-1 值集＝D1-6 值集（五元相等）。D2-4 per-TF brace 未複列 entry 欄——entry 屬事件級、寫在 D1-6／§G-2，**非反向漂移** |
| Y2 | 公式 R0/Rw；a/b/c 門檻；預設 0.05/0.0/0.01/0.05；boundary `=`±1e-9 | B1.5=:184-185 | **忠實** | **vs 使用者 §2-4**：a＝漲≥5%∧不續漲（Rw≤0）；b＝\|R0\|≤1%；c＝跌（預設 5%、可調）。公式／單位／唯一列舉處均在契約路徑 |
| Y3 | 匯入三值；derived 四值含 `unclassifiable`；分層吃 derived；匯入出現 unclassifiable⇒拒 | B1.0=:126；B1.5=:184；B2.2=:221 | **忠實** | **兩值集 vs JSON SoT**：兩閉集皆「字面入契約檔」；非第二 SoT。B2.2 已改 `counterexample_kind_effective` |
| Y4 | 統一 pytest -k M\<n\>；fixture 身分；digest 誠實邊界；TODO 逐字抄 | §V=:359-371 | **忠實** | 不受理「digest 應預寫」——與 brief 不受理範圍一致 |
| Y5 | permutation quantile N_perm=1000；per statistic_kind；M8 恆等排列必紅 | B1.4=:173；M8=:367 | **忠實** | 近似 CI 式已自 M8 移除；§G-3 仍寫「chance-level CI」＝門檻表述層，定式以 B1.4/M8 為準，**不衝突** |
| Y6 | accepted 三值；`platform_random_bars` 恆拒；B1 只產 user_labeled_*；B3.2 同 validator | B1.0=:123；B3.2=:278-279；§N-7=:396 | **忠實** | **vs §N-7**：殘留僅 random bars；`platform_same_trigger_rule` 非殘留、B3.2 可驗收。無 profile 分裂 |

**漂移處列出**: 無須阻擋收斂之語意漂移。下列為**非升級**殘差（對齊 R2 本家對 X6 呈現層級差異之不升級慣例）：
- D4-2=:43 產品層仍寫 `counterexample_kind` 分層（Y3 改法範圍＝B1.0/B1.5/B2.2；表任務已吃 derived）。
- B1.0 衍生欄子彈列=:127 未把 `counterexample_kind_effective` 再抄一次（分類 config 段已定義）。
- B1.5 未另寫「零規則命中 ⇒ unclassifiable」（已有多類／窗不全 ⇒ unclassifiable；§2-4 三原型覆蓋主路徑）。

---

## 2. X1–X13 衝突掃描（Y 寫回是否踩舊裁）

| 面 | 結果 |
|---|---|
| X1 offset／不設 ms 覆寫 | 未改動；Y1 只補 entry 映射，六欄不變式仍在 |
| X2 label 錨＝t₀ close | 未改動；Y2 Rw 錨＝t₀ close 同向 |
| X4 unclassifiable 不猜 | Y2/Y3 強化（derived 值集＋匯入拒），非反向 |
| X8 M1–M12 | Y4/Y5 補強可執行性與 M8 oracle，未刪條 |
| X11 entry 頂層 | Y1 指向頂層 semantic，未嵌回 `label_definition` |
| X13 platform 拆分 | Y6 正是閉合其 validator 殘餘；§N-7 文意保留 |

§1 十一類（本輪焦點＝Y 寫回面）：矛盾／漏項／不可測／quant／過度工程／OOM／cache／API／測試／agent 可執行／短命工 → **無新 BLOCKING/MAJOR**。

---

## 3. brief 必答

1. **Y1–Y6 忠實度＋新錯掃描**: 上表；6/6 **忠實**；特別四面（D1-6↔D2／Y2§2-4／Y3 SoT／Y6§N-7）均通過；**無實質新錯**。  
2. **可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？** **可以**——本家 **0 findings**（sentinel 如下）；剩餘為 stamp／白話閘程序，非契約空洞。

---

## Verdict：可進三家 RECONCILE-STAMP＋使用者白話閘

R2 六群集寫回可證偽對照 synth；D1-6 與六欄不變式在預設標籤路徑相容；Y2 預設值對齊使用者 §2-4；Y3 兩值集仍單一契約 SoT；Y6 accepted／恆拒與 §N-7／B3.2 一致。不需再修補 SPEC 才能 stamp。

---

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding；Y1–Y6 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r2/synth.md` 處置，與 X1–X13 既有條文無衝突，特別面（D1-6↔D2 六欄、Y2↔§2-4、Y3 兩值集 SoT、Y6↔§N-7）未發現新 BLOCKING/MAJOR。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `377c9a39b01e…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 21135434..c7ac693e -- docs/GAP3_EVENT_SPEC.md` 涵蓋 D1-6／B1.0 control_kind＋derived 值集／B1.5 公式與預設／B1.4＋M8 permutation／§V 逐條命令；讀檔錨點 D1-6=:27、D2-1=:30、B1.0=:123-126、B1.5=:184、B2.2=:221、B3.2=:278、§N-7=:396、M8=:367；D1-1 與 D1-6 五元值集相等；accepted 三值 ⊂ schema 四值且 `platform_random_bars` 為唯一恆拒元。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721; handoffs/20260820-gap3-spec-r3-BRIEF.md#03a913b7a5ab

sentinel：0 findings（實質）；上列為 R3 Y1–Y6 忠實度＋新錯掃描之機械複驗摘要。

---

## 被當成事實的未驗證假設（§0 殘列）

| 宣稱 | 判定 |
|---|---|
| Y1–Y6 寫回無語意漂移 | 本輪攻後改為 **fact-verified（無實質漂移）** |
| Y2 預設忠實 §2-4 | **fact-verified**（0.05／0.0／0.01／0.05 對原例） |
| Y6 與 B3.2／§N-7 一致 | **fact-verified** |
| template_check PASS | **fact-verified**（本輪重跑） |

ASSUMPTIONS_VERIFIED: SPEC @c7ac693e sha256=brief；template_check PASS；Y1–Y6 逐群集對照 synth 無實質漂移；D1-6↔D2／Y2§2-4／Y3 SoT／Y6§N-7 四特別面通過  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → brief 相符；completeness 見收尾  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（審查 only）
