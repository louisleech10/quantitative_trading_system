# GAP-3 EVENT SPEC R2 閉合驗證＋殘餘 sweep — grok

family: grok  
task-id: 20260820-GAP3-X-REVIEW-R2  
scope: `docs/GAP3_EVENT_SPEC.md` @ `21135434`（sha256 `9f63e290e89a…`）；對照 R1 synth X1–X13；禁改碼  
brief: `handoffs/20260820-gap3-spec-r2-BRIEF.md`  
R1 本家: `handoffs/20260820-gap3-spec-r1-grok.md`  
reconcile: `handoffs/reconcile/20260820-gap3-x-review-r1/synth.md`

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| R1 reconcile completeness PASS | fact-verified（brief） | 未重跑 `--lock`；本輪以 synth 正文＋SPEC 寫回對照為準 |
| 修訂版 `template_check spec` PASS | **fact-verified** | 本輪重跑 → `TEMPLATE PASS (spec)`，rc=0 |
| assumed: X1–X13 寫回無語意漂移／漏寫 | **本輪攻破結果＝不成立（漂移）** | 逐群集對照 → **無實質漂移**（見下表）；assumed 被證偽為「寫回忠實」 |
| assumed: AR 裁決（offset int≥0／unclassifiable 不猜／cluster_weight=1/n）與各家 R1 原意相容 | **相容（含對 grok AR-6 少數意見之多數裁）** | 見 AR 相容段；不重開已裁 |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 9f63e290e89a1dde96b44c217866d01d0113b0dc47f19b5acd0a7e356459f5bf（＝brief）
git rev-parse HEAD → 21135434dbf6…（＝brief commit）
bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md → TEMPLATE PASS
```

---

## 1. 本家 R1 findings 閉合表（章程 §B8）

| R1 ID | 群集 | 重跑反例摘要 | 判 |
|---|---|---|---|
| GROK-R1-P1-01 | X2 | `sed`/`grep`：D1-5 寫死「label 錨＝t₀ close、與 decision_at 永遠脫鉤；禁止以 decision_at 列 join 主線 return_N」；B2.3 邊界③＝t₀−k 手算錨不隨 decision 移動 | **CLOSED** |
| GROK-R1-P1-02 | X10 | Phase B3 標題＝「依賴：**B1＋B2.5**」；B3.2「G6＝呼叫 B2.5 `evaluate_all_bars`，禁平行實作」＋G6 整合測試 | **CLOSED** |
| GROK-R1-P1-03 | X11 | D1-1＋B1.0：`entry_price_semantic` 為**頂層**；`label_definition{…}` **不含** entry；`grep 'label_definition{[^}]*entry'` → 無命中 | **CLOSED** |
| GROK-R1-P2-04 | X12 | Phase B4 腳註：「K6 落批以 R2 **C9 為準（B4）**，覆寫 C7 正文之 B3 批號」 | **CLOSED** |
| GROK-R1-P2-05 | X12 | B3.2 驗證展開 G1–G6 六條逐項斷言（含 G2 多組 label、G3 方向/情境/答案窗/規則摘要、G5 合規檔、G6 綁 B2.5） | **CLOSED** |

碼證錨點（修訂版行號）: D1-5=:26；B3 依賴=:260；B3.2 G6/G1–G6=:277-278；entry 頂層=:22,:122；C9 腳註=:297；B2.3 錨案例=:233。

---

## 2. X1–X13 寫回忠實度（synth 處置 vs SPEC）

| 群集 | synth 處置要點 | SPEC 落點 | 漂移？ |
|---|---|---|---|
| X1 | `t0`＋`decision_offset_bars` int≥0；**不設** ms 覆寫；`decision_at_ms` 推導；`missing_bar`；§G-2 k=0/k>0 oracle | D2-2=:30；AR-1=:70；§G-2=:106 | **無** |
| X2 | label 錨＝t₀ close；禁 decision_at join `return_N`；B2.3 手算 | D1-5=:26；B2.3=:233 | **無** |
| X3 | `conditional_ic` 缺 label ⇒ `unavailable:missing_label_value`；v1 不重算；AR-6 維持 §N-8 | D1-3=:24；§N-8=:396；AR-6=:75 | **無**（採多數，見下） |
| X4 | classifier config；user 優先；多類 ⇒ `unclassifiable` 不猜 | B1.0=:125；B1.5=:183-185；M10=:368 | **無** |
| X5 | T8/T9/T10 條件必填 | B1.0=:124；M12=:370 | **無** |
| X6 | `event_split_plan` 為 B2.1/2/3/5＋B4.1 必需輸入；禁未 cluster formal pooled | Phase B2 共同約束=:203；B4.1=:303；M11=:369 | **無實質漂移**（共同約束寫在 Phase 區塊而非每 Task 改法欄逐條複寫；語意覆蓋五 Task＋「各 Task 驗證含此共同約束斷言」指令在場） |
| X7 | 新增 B1.6；B1.4 吃 B1.6；`state_counters.py` 寫死 | 批內順序=:115；B1.6=:190-199；B1.4=:170；B3.3=:286 | **無** |
| X8 | M1–M8 補強＋M9–M12 | §V=:358-370 | **無** |
| X9 | `cluster_weight=1/n_events_in_time_cluster`；弃 1/sqrt | B1.3=:160；M5=:363 | **無** |
| X10 | B3 依賴 B1＋B2.5；G6 禁平行 | =:260,:277-278 | **無** |
| X11 | entry 頂層化 | =:22,:122 | **無** |
| X12 | C9 腳註＋G1–G6 展開 | =:297,:278 | **無** |
| X13 | `platform_same_trigger_rule`→B3.2；`platform_random_bars` 留 §N-7 needs-research | B3.2=:277-278；§N-7=:395；B1.0=:122 | **無** |

**漂移處列出**: 無須阻擋收斂之語意漂移。X6 呈現形式＝Phase 級共同約束而非五處逐 Task 複寫——與 synth「各 Task 改法/驗證欄補斷言」字面略異，但強制範圍與驗收指令等價，**不列 finding**。

---

## 3. 殘餘 sweep（brief 重點面）

| 面 | 結果 |
|---|---|
| D1-5 label 錨 vs D2-2 offset 表示法 | **內部一致**：匯入＝offset bars；receipt 推導 `decision_at_ms`；label 錨永遠 t₀ close、與 decision 脫鉤；六欄 `decision_at ≤ entry_at ≤ label_start` 在 t₀−k 下仍可滿足 |
| B1 批內順序（B1.6 插入後） | **正確**：B1.0→B1.1→B1.2→B1.3→**B1.6**→B1.4→B1.5；B1.4 輸入明寫 B1.6 產出 |
| X6 共同約束 vs 各 Task 驗證 | Phase 區塊強制＋M11 守門；B4.1 改法顯式；可執行 |
| M1–M12 可證偽性 | 每條含 baseline/mutation/預期 rc；M1 已改 failures 記帳形（非 raise）；M5 綁 1/n；M8 有恆等排列反證；M9–M12 覆蓋 X1/X4/X6/X5 |
| §N-7/8 三值理由 | §N-7=`needs-research`（隨機 bar estimand）成立且循環已拆；§N-8=`needs-research`（探針族範圍）＋D1-3 配套硬規則——與 X3 多數裁一致 |

§1 十一類（殘餘）: 矛盾／漏項／不可測／quant／過度工程／OOM／cache／API／測試／agent 可執行／短命工 → **本輪無新 BLOCKING/MAJOR**。B1.0「不可做：不得實作 `platform_*` 抽樣」屬 **B1.0 Task 邊界**（同段已註 `platform_same_trigger_rule`＝B3.2），與 X13 不衝突。

AR 相容（攻 brief assumed）:
- `decision_offset_bars` int≥0、無負號、無 ms 覆寫 — 與本家 R1 AR-1 **同型**。
- `unclassifiable` 不猜 — 與本家 R1 AR-2 **同向**（較嚴版被採）。
- `cluster_weight=1/n` — 與本家 R1 未異議；composer 公式收斂，相容。
- AR-6 維持 §N-8 — **否決本家 R1「B1 可選 task」少數案**；屬已裁多數，**不重開**（非 RULING-CONFLICT 碼證衝突）。

---

## 4. brief 必答

1. **R1 閉合表**: 上表；5/5 **CLOSED**，0 NOT-CLOSED。  
2. **X1–X13 忠實嗎？** 是；漂移＝無實質（X6 呈現層級差異已說明、不升級 finding）。  
3. **新引入錯誤？** 本輪逐項核對後 **無** BLOCKING/MAJOR；未捏造湊數 finding。  
4. **可否進三家 RECONCILE-STAMP＋使用者白話閘？** **可以**——無須再修一輪 SPEC 才能 stamp；剩餘為 stamp／白話閘程序，非契約空洞。

---

## Verdict：可進三家 RECONCILE-STAMP＋使用者白話閘

R1 本家五條與 X1–X13 寫回均可證偽閉合；D1-5↔D2-2、B1.6 順序、M1–M12、§N-7/8 殘餘 sweep 無新阻擋項。不需再修補後才 stamp。

---

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；R1 本家五條（P1-01..03／P2-04..05）對修訂版 SPEC 皆 CLOSED，X1–X13 寫回無實質語意漂移，殘餘 sweep（D1-5↔D2-2、B1.6 順序、X6 共同約束、M1–M12、§N-7/8）未發現新 BLOCKING/MAJOR。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `9f63e290e89a…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`；`grep`/讀檔：D1-5=:26、B3 依賴 B1＋B2.5=:260、entry 頂層=:22/:122、G1–G6=:278、C9 腳註=:297、`cluster_weight = 1/n_events_in_time_cluster`=:160、`unclassifiable`=:183、B1.6=:190、M9–M12=:367-370、§N-7/8=:395-396；`grep 'label_definition{[^}]*entry'` → 無命中。對照 `handoffs/reconcile/20260820-gap3-x-review-r1/synth.md` X1–X13 處置原文。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a; handoffs/reconcile/20260820-gap3-x-review-r1/synth.md#a4d0025eb1f8; handoffs/20260820-gap3-spec-r1-grok.md#a89aacb71ff9

---

## 被當成事實的未驗證假設（§0 殘列）

| 宣稱 | 判定 |
|---|---|
| X1–X13 寫回無漂移 | 本輪攻後改為 **fact-verified（無實質漂移）** |
| AR 與 grok R1 原意相容 | **相容**（AR-6 為多數否決少數，非碼證衝突） |
| template_check PASS | **fact-verified**（本輪重跑） |

ASSUMPTIONS_VERIFIED: SPEC @21135434 sha256=brief；template_check PASS；本家 R1 五條反例重跑 CLOSED；X1–X13 逐群集對照無實質漂移；D1-5/D2-2/B1.6/M1–M12/§N-7/8 sweep  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → 9f63e290e89a…；targeted grep/sed probes → 見碼證  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（只產 review 檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r2-grok.md`

STATUS: DONE
