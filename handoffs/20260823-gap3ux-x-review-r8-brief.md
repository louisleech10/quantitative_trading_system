# GAP-3 事件型 UAT 缺口修補 SPEC — R8（首次補丁包模式；含一項架構調整之裁定）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0／§1／§2／canonical 四欄／Verdict）。
findings 用 canonical ID `## <FAMILY>-R8-P<0-3>-<NN>`。
零 findings ⇒ `## <FAMILY>-R8-P3-00` sentinel（須含斷言欄與碼證欄）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷／輸入檔**，非 gating 檔；勿 STAMP-BLOCK。

---

## 🔴 本輪之交付物與前七輪不同：請產出**補丁包**

R3 consult 三家裁定之新流程已上線（`docs/GAP3_EVENT_UX_ROLE_CARD.md`）。
**本輪起，findings 不只要寫「該怎麼修」，還要附可直接套用之補丁包**：

`handoffs/patches/20260823-gap3ux-r8-<cluster>.md`
```markdown
# PATCH cluster <名>
AUTHORITY: <哪一處是權威定義>
SYNC-LOCI:
- <檔>#<錨點>
- <檔>#<錨點>
BEFORE/AFTER: <可直接套用之替換或 unified diff>
VERIFY:
- <可跑之命令>
```

**責任歸屬（三家已訂）**：補丁包**漏列** locus ⇒ 補丁包紅、算委員責任；
已列而主委未改齊 ⇒ 算主委。機械對證＝`python3 scripts/patch_locus_check.py <patch.md>`
（主委 diff 觸及集合須 ⊇ SYNC-LOCI）。

**為何改成這樣**：七輪主委自傷 21 條，其中約 14 條同一形態——
「改了某處之權威定義，未同步所有複述它的位置」。R5 起由委員指定修法後，
技術決策零錯誤，但錯誤**轉移到整合**（R6 6/15、R7 7/12）。
⇒ 把「同步集合」由委員先決定並機械對證，主委只做可追蹤之套用。

## 方法論（沿用 R4–R7，實測有效）
- **主委不指定審查方向**：本 brief 不含「請攻」「重點看」之句；各家獨立盤點。
  下方「主委之未證假設」是揭露，非攻擊清單。
- **fact 全為可重跑 receipt**：`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh`（rc=0）。
- **標的 sha256 鎖版**：見下節；審查期間主委不改該檔。

---

## 審查標的（版本鎖定）

- 檔案：`docs/GAP3_EVENT_UX_SPEC.md`
- **sha256：`01cf2468573ff50f9d3933698d2b110824bccc259bb519a1e2f523ca5b151bd0`**（1580 行、42 Task）
- **開工第一件事**：`shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`；不符即停下並在第一條回報。
- 標的性質：**規格**，尚未實作。

---

## 🔴 議題一（本輪主要）：使用者提出之架構調整

**使用者 2026-08-23 逐字**：
> 「那這樣條件 IC 本來就算一種類型的 IC-Analysis，條件給定應該就是要在 IC 分析的頁面，
> 而不是 `/search` 吧」

**主委已查證之碼證（皆可重跑）**：
1. `/search` 之 `label`（0／1）來自 **t0 條件之 `positive_case`**，**完全不看答案窗**；
   `label_value`（連續）才來自 `future_{horizon}bar_return`
   → `sed -n '75,85p' frontend/src/lib/eventExport.ts`
2. `ic_feed.py` 檔頭逐字：「條件 IC 只吃連續 `label_value`（缺任一 ⇒ capability
   unavailable:missing_label_value，**v1 不重算**）」
   ⇒ **「不重算」是版本限制，非能力限制**
   → `sed -n '1,10p' momentum/Analysis/event_samples/ic_feed.py`
3. 事件 pipeline **已能讀真實 K 線**：`bars_from_kline_cache` 之 docstring 為
   「服務端取 bars 的唯一入口」；B8／B8b 兩表即以其於 analyze 當下計算
   → `sed -n '76,82p' momentum/Analysis/event_samples/pipeline.py`
4. 契約：`label_definition.window` 之 `horizon_bars` ＝「label_end 推導輸入」
   → `python3 handoffs/20260823-gap3ux-x-review-r8-dims.py`

**使用者論點之推論**：事件批次是**事實**（這些 t0 發生、標記為 0／1）；
答案窗是**分析參數**。把答案窗烤進匯出檔 ⇒ 想比較 h=3 與 h=7 必須**重新匯出整批事件**，
而事件本身沒變。且 A-6（「多選附帶欄不改 label」）因此是在**錯誤的層次**發問。

### 必答（本議題）
1. **此架構調整是否成立**？（`/search` 拿掉主答案窗、改由 IC 分析頁給定條件與答案窗）
2. 若成立：`label_value` 改為**分析時計算**，其 **PIT 正確性如何保證**？
   （§C0 量化主線只能更嚴；須明訂特徵截止、不得偷看未來、golden 如何凍）
3. **A-6 是否隨之作廢**？若作廢，§A 該如何改寫；若不作廢，它剩下的範圍是什麼？
4. 影響面：本調整跨 Phase 4（Task 4.1／4.1b）、Phase 7（IC 頁那一區）、
   `ic_feed`／契約。請列**完整同步集合**並產補丁包。
5. 🔴 **不成立的話請直接說**——主委已對使用者表達「你的判斷正確」，
   若你們認為主委判斷有誤，**請以碼證推翻**，不必顧慮。

---

## 🔴 議題二：R7 十二條之修訂複審

R7 三家 12 條全數 ACCEPT，主委已全修（commit `a67f27a7`）。
reconcile：`handoffs/reconcile/20260823-gap3ux-x-review-r7/synth.md`。

| 群集 | 落點 |
|---|---|
| A | `facts.sh` 閘數補為五支；計數閘掃描面放寬至所有檔所有語境 |
| B | §F-2 改純引用、不重述 reason 計數（原「15→16」與 Task 1.1「== 20」互斥） |
| C | Task 7.7 ① 改為指向 ④（原斷言 ISO 字串，而 ④ 已裁 epoch 秒字串） |
| D | Task 7.3 揭露清單補 `control_kind`；4.1b 加「超集須逐項對照驗證」 |
| E | Task 7.0b 補完整 API 契約（`POST /api/v1/case/label-values`）＋端到端 wiring 驗收；刪除空斷言 |
| F | Task 1.10 增「registry 內容正確性」驗收；無數字之 legacy 欄須標 `lookahead_unknown` |
| G | Task 1.3 之 `canonicalSourceText` 明引 §G S-9（浮點 lexeme）＋跨環境 digest 相等斷言 |

**以反例重跑判定閉合**，不以「SPEC 有寫」判定。
🔴 **議題一若成立，群集 E（Task 7.0b 之 API）可能整段須重寫**——請一併裁。

---

## 必查涵蓋面（不指定結論）

1. 議題一之裁定（含 PIT 正確性與同步集合）
2. R7 十二條逐條 CLOSED／OPEN
3. **全棧三欄稽核**（後端 code／前端 UI／wiring），涵蓋 IC 分析頁、Feature Library、`/search`
4. 主委單方產出、未經審查者：`scripts/patch_locus_check.py`、`scripts/gap3ux_pre_review.sh`、
   `docs/GAP3_EVENT_UX_ROLE_CARD.md`、以及 R7 修訂中主委補寫之各驗收條目
5. §C0 是否在全文被遵守；跨 Task 之計數字面／禁令互斥／登記義務是否一致
6. **Verdict**：可定版／需修訂後定版／不可定版

## 🔴 FROZEN 之四條件與硬輪上限（R3 consult 三家已訂）
① 正確性／洩漏／接線類 OPEN **P0＝0、P1＝0**
② 本輪主委自傷**絕對數＝0**
③ **A-6（或其取代裁定）經使用者確認**
④ 六閘 rc=0（`bash scripts/gap3ux_pre_review.sh`）

**硬輪上限：自 R3 consult 起 ≤2 輪**（本輪為第 1 輪）。
🔴 逾上限時只裁補丁包品質／漏 locus，**不開新 scope**、**不得裁「先 Frozen」**。

---

## 本 brief 前提

### fact-verified（每條可重跑）

fact-verified: 標的 sha256 `01cf2468573ff50f9d3933698d2b110824bccc259bb519a1e2f523ca5b151bd0`、1580 行、42 Task
  → `bash handoffs/20260823-gap3ux-x-review-r8-facts.sh`（F-01）

fact-verified: `/search` 之 `label` 來自 `positive_case`（t0 條件），`label_value` 來自 `future_{h}bar_return`
  → `sed -n '75,85p' frontend/src/lib/eventExport.ts`

fact-verified: `ic_feed.py` 檔頭載明條件 IC 只吃 `label_value` 且「v1 不重算」
  → `sed -n '1,10p' momentum/Analysis/event_samples/ic_feed.py`

fact-verified: `pipeline.bars_from_kline_cache` 為「服務端取 bars 的唯一入口」，事件端已能讀真實 K 線
  → `sed -n '76,82p' momentum/Analysis/event_samples/pipeline.py`

fact-verified: 六支機械閘現況皆 rc=0（含本輪新增之 `patch_locus_check`）
  → `bash scripts/gap3ux_pre_review.sh`

fact-verified: `patch_locus_check.py` 之反測——漏改 locus ⇒ rc=2、空 SYNC-LOCI ⇒ rc=2；
  首版曾有 fail-open（`git diff HEAD --name-only` 不含 untracked），已改 `git status --porcelain -uall`
  → 讀該檔 `changed_files()` 之註解；自建 fixture 重跑

fact-verified: 42 Task 之出處分佈——使用者直接要求 20、衍生自使用者一次糾正 5、
  委員七輪長出而未問使用者 17；使用者已裁**一個都不砍**
  → `白話說明/GAP-3規格42個Task勾選表.md`

fact-verified: 主委自傷之絕對數為 3→5→6→7（R4→R7），佔比 16%→58%；
  委員找到之真缺口約 16→8→9→5
  → 各輪 `handoffs/reconcile/*/synth.md` 之「輪次事實」段

### assumed（主委之未證假設；揭露用，非攻擊清單）

assumed: 議題一之架構調整成立（主委已對使用者表達「你的判斷正確」——**若有誤請以碼證推翻**）。
assumed: `label_value` 改為分析時計算後，PIT 正確性可由既有 `decision_time_rule`／
  `feature_cutoff_rule` 保證，不需新機制。
assumed: R7 十二條之處置皆對症，未引入新的內部矛盾（**R5／R6／R7 此假設連三輪被推翻**）。
assumed: 新流程（補丁包＋locus 閘）能把主委自傷絕對數壓到 0；本輪即該假設之首次實測。
assumed: `patch_locus_check.py` 之涵蓋面（只驗宣告的 locus 有無被觸及）足夠；
  委員漏列之 locus 本閘看不見，屬已具名之誠實邊界。

---

## 不受理範圍

- **砍 Task／縮範圍**（使用者已裁 42 個一個不砍）
- 純事件研究模式、#9b 規模防護本體、標籤方法論討論（皆使用者裁定另立）
- `tests/api` 既有紅 10 failed + 3 errors
- G-7 scope 淨差之既有紅（使用者 2026-08-14 裁定治理不再擴建）
- 實作細節之程式碼審查（標的是尚未實作的規格）

---

## 產出

canonical 四欄 findings ＋ **每個 OPEN 群集一份補丁包**（`handoffs/patches/20260823-gap3ux-r8-*.md`）
＋ **Verdict**。
**禁改碼、禁改 SPEC**（補丁包只是「可套用之文字」，實際套用由主委做）。
收尾只清你自己的 workdir（**勿動 `/private/tmp/claude-501/`**）。
