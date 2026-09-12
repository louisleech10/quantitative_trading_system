# SPLITUNIFY D-002 閉合輪 R11 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R11`  
family: grok  
findings-round: R11  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第十一次修訂／v11；sha12 `a731f4b623a1`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r10/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r11/`（交件後清除；保留 `/tmp/claude-501*`）  
本家 R10 待閉（敘述用，不入裁決欄）: `GROK-R10-P1-01`～`03`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R10 十三條歸八群、全部採納 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r10/synth.md`

fact-verified: mutation 表列 **32**、ID 01–32 連續無重複、正文宣稱 32 → `grep -oE 'M-SU-D2-[0-9]+' | sort -u | wc -l`＝32；`comm` 缺號／`uniq -d` 皆空

fact-verified: `D-002-C5` (5.6) register 表列 **25**（`grep -cE '^\| \`C5-'`＝25）；標題／§RISK／§R 回退句皆寫 25

fact-verified: `tests/golden/splitunify/splitunify_golden.json` 頂層 **11 鍵**（含 `_doc`／`purge_reasons` 與全部 `g5_*`），**無** v8 鍵；目錄下**無** `.v8.json`／`.v8.sha256` → `jq -r 'keys[]'`＋`ls`

fact-verified: `obligation_block_check`／`doc_format_precheck`（SPEC＋TODO）／`spec_xref_check --synth`（r10）皆 rc=0 → 本輪實跑

fact-verified: `freeze_splitunify_golden.py:373-386` 現行仍 `golden_path.write_text(...)` 整檔覆寫；`--write` 無 `.v8` 拒寫分支 → `sed -n '373,386p'`

fact-verified: `validate_split_pair_integrity` 對「全域 `row_index`＋局部宇宙」→ `IndexError: plan.row_index contains positions outside base universe`；對「局部 `row_index`＋全域宇宙」→ `CrossSymbolLeakageError`；對「全域＋全域」與「局部＋局部」皆 PASS → 探針 `/tmp/grok-splitunify-b9-review-r11/m5_m6_probe.txt`

assumed: (5.6) register 之 25 條涵蓋全部單鍵消費面，且甲／乙／丙分類逐條正確  
→ **否證**：①(5.5) 具名之 `pipeline` summary counts／API 模型／`EventTablesPanel` 計數顯示**不在** C5-01..25；②`tables.py:372` 之 `assignments.set_index("event_id")` 亦不在 register（(5.3) 只寫「tables 兩處」，碼上至少三處）。見必答 3／P1-04。

assumed: (G-4e) 改用 fixture 字面 `expected_side` 後，「三份同錯」風險顯著降低但未消除，殘餘只能靠散文紀律  
→ **部分成立**：比「第三次編碼」強（人手填值與公式編碼脫鉤）；仍可構造「填值者照同一錯誤理解填」；無完全機械解。誠實標註**足夠**。見必答 4（不另開 finding）。

assumed: `baseline` 刪除舊鍵 `n_test` 不會打破任何下游消費者  
→ **本輪複驗未否證**：`baseline.py:120` 仍為唯一生產寫入；呼叫面在 `test_baseline_oracle.py`／`test_mutation_guard.py`；前端／`split_unify` 之 `n_test` 屬別路徑。與 R10 碼證一致。

assumed: M6 落地順序 (i)–(iv) **無法**被繞過  
→ **否證**：①同時改寫 `.v8.json` 與其 `.sha256` ⇒ (iii) 自參照雜湊仍綠；②`--write` 仍整檔 `write_text(actual)`，若未強制「從 `.v8.json` merge 保留既有 11 鍵」，可一次覆寫舊錨。見必答 5／P1-02。

assumed: M5 座標 adapter 二擇一（full-universe `row_index` 或 local→global rebase）**窮盡**  
→ **否證**：①二擇一只寫 `row_index` 座標、未鎖 `ts`／`symbols` 須同座標系（實跑 IndexError）；②第三條可行路徑＝「整條呼叫鏈維持該 symbol 局部宇宙＋局部索引」（探針 case3 PASS），不在二擇一內。見必答 5／P1-03。

---

## 必答 1–6

### 1. 本家 R10 finding 是否閉合

| R10 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R10-P1-01` | **CLOSED** | §G (G-4e) L162 改 fixture 字面 `expected_side`＋明禁共用 helper；§V 第 3 條 L260 同步；殘餘誠實邊界已登記 |
| `GROK-R10-P1-02` | **CLOSED** | (6.2) L125 刪「等價」、定 exact schema、刪舊鍵 `n_test`；`Task 9.4` L241／L244 三處同向；`M-SU-D2-32`＋§V Task 9.4 母斷言 |
| `GROK-R10-P1-03` | **字面 CLOSED／剩餘洞重開 R11** | §V L253 metadata 已升級**值相等**；但 `M-SU-D2-03` L277 應紅面仍寫「**鍵斷言**」⇒ 見 `GROK-R11-P2-05` |

（跨輪 ID **不**填入本檔 `CLOSED:` 欄。）

### 2. 檢驗自證六條（十項改動落點）

| 項 | 落點是否到位 | 證據 |
|---|---|---|
| M1 (G-4e) literal | **到位** | §G L162／§V L260／禁共用 helper；舊「純函式第三份」作廢句在場 |
| M2 metadata 值相等 | **§V 到位、mutation 漏** | L253 值相等；`M-SU-D2-03` 仍「鍵斷言」⇒ P2-05（自證②） |
| M3 baseline 雙量＋刪舊鍵 | **到位** | (6.2)／Task 9.4／mut 31–32；「等價」活性句已清（沿革除外） |
| M4 §V Task 9.4 | **到位** | L268 三條母斷言 |
| M5 座標 adapter | **字面到位、效力不足** | L217／§V L264 有二擇一；未鎖宇宙陣列同位系、未列第三路徑 ⇒ P1-03 |
| M6 v8 不可變檔 | **§G／§V 到位、mutation 漏＋可繞過** | L163／L263 指定 `.v8.json`；`M-SU-D2-29` 仍寫「v8 **鍵**」⇒ P1-01；順序 (iii) 自參照 ⇒ P1-02 |
| M7 (5.6) register 25 | **標題／條數到位、涵蓋不全** | 25 列一致；但 (5.5) 與 `tables.py:372` 未入表 ⇒ P1-04（**第七種形態**） |
| M8 AST 觸發式 | **到位** | SPEC §N L317 與 TODO §E L471 同步廣義 call-site；禁窄 regex 零命中 |
| 自產 A Rule4 刪 | **到位** | L221「本條於 v11 刪除」＋字面保留 |
| 自產 B mut 32 | **到位** | 表列 32、ID 連續、正文宣稱 32 |

**自證六條漏掉的第七種形態**：引入「唯一 register」後，未驗 **敘述層（(5.1)–(5.5)）具名消費面是否逐條落入 register**（以及碼上多一處 `set_index` 是否超出「兩處」宣稱）。屬「新建唯一真相源後，舊敘述／碼點未對帳」。

### 3. 攻 (5.6) register

- **條數**：表列 25＝標題 25＝§RISK／§R 25 → 計數自洽。
- **涵蓋**：不全。碼證：
  - (5.5) L82 具名 `pipeline` 之 `n_train`／`n_test`／`n_purged`、API 模型、前端事件批面板 → register **無**對應 C5 列（僅 C5-23＝wiring `dict(zip)`）。
  - `pipeline.py:761-763` 現行 `n_test = (assignments["split_label"]=="test").sum()`（複合鍵後會膨脹）——Task 9.4 有改法，但 (5.6) 自稱「唯一施工清單」卻漏列。
  - `EventTablesPanel.tsx:361` 顯示 `s.n_test`——不在 register（C5-15 只覆蓋 `batch_facts`）。
  - `tables.py:372` `assignments.set_index("event_id")`——(5.3) 寫「tables **兩處**」，碼上至少 event_level／clusters／assignments **三處**；assignments 消費面複合鍵後近 **丙類**，卻無 C5 列。
- **分類**：已列 25 條之甲／乙／丙與 (5.1) 敘述大致一致；問題在**漏列**，不在已列錯分。
- **mutation `—`（C5-15／16／17）**：作為「不動」面之**具名缺口**可接受；但與同屬甲類不動的 C5-01..03（有 `M-SU-D2-18` 反向）／C5-18（有 `M-11`）**不對稱**。建議補反向 mutation（誤改為複合鍵即紅），或在 register 註明「由 Task 9.5 舊值不變斷言覆蓋、故允許 `—`」。現狀不升 P1（已具名），記於建議。

⇒ **P1-04**

### 4. 攻 (G-4e) 殘餘誠實邊界

- **人手填是否優於第三次編碼**：**是**。第三次編碼與投影／oracle 同屬「公式→側別」函數空間，同一次誤解可三份全等；字面 `expected_side` 把第三份移出該空間（主委探針／R10 已證）。
- **人手同錯具體情境**：換錨後把隔離帶事件（正確＝`purged`）全填成 `train`（沿用 R6 不等式直覺），同時投影／oracle 也被寫成同一不等式 ⇒ 三份仍全等、G-4e 綠。殘餘真實存在。
- **機械解？** 無「不靠人手、也不靠第四次編碼」的完解。可強化但非機械閉合：①`expected_side` 須在改投影／oracle **之前**單獨 commit；②CI 禁 `expected_side` 由 `_oracle_membership`／投影 import 產生；③每個 `decision!=cutoff` 事件強制雙人核對清單。皆仍是紀律。
- **標註是否夠誠實**：**夠**——L162 已寫「散文紀律、非機械保證」。本輪不另開 finding。

### 5. 攻 M6／M5（具體構造）

**M6 繞過：**

1. **雙檔同改**：`splitunify_golden.v8.json` 改成被竄改成員集，同步重算並覆寫 `splitunify_golden.v8.sha256` ⇒ (iii) `sha256(file)==sha_file` 仍成立（自參照；探針 sha12=`349a8ca204eb` 示意）。缺外部錨（例如 git blob／獨立 lock digest）。
2. **整檔 `--write`**：現行 `freeze:373-386` 對主檔 `write_text({"_doc", **actual})`；若實作只加 v9 鍵卻讓 `actual` 的 `g1_membership` 已是換錨後值、又未先自 `.v8.json` merge 舊 11 鍵，一次 `--write` 即覆寫舊錨——(iv) 只拒寫 `.v8.json`，**不擋**主檔舊鍵被換。

⇒ **P1-02**

**M5 二擇一不窮盡（實跑）：**

| 構造 | `row_index` | `ts`/`symbols` | 結果 |
|---|---|---|---|
| 正確 (a) | 全域 `[0],[2]` | 全域 4 列 | PASS |
| (a) 不完整 | 全域 `[0],[2]` | 局部 2 列 | **IndexError**（＝codex 反例） |
| 第三路徑 | 局部 `[0],[1]` | 局部 2 列 | **PASS**（二擇一未列） |
| 錯向 rebase | 局部 `[0],[1]` | 全域 4 列 | **CrossSymbolLeakageError** |

⇒ 須改為「`row_index` 與 `ts`/`symbols` **同一座標系**」三選一寫死：(a) 皆全域；(b) local→global 後接全域宇宙；(c) 皆維持該 symbol 局部宇宙。只寫 row_index 二擇一會讓 Agent 選 (a) 卻忘改宇宙陣列 → 誤殺合法批。

⇒ **P1-03**

### 6. 修訂引入的新問題／衝突

1. `M-SU-D2-29` 仍「v8 **鍵**」vs 檔案制 (G-4d)① ——P1-01（與 D-001／既有 golden 無直接衝突，但 mutation 不可執行）
2. M6 自參照雜湊／整檔 write ——P1-02
3. M5 座標契約不完整 ——P1-03
4. (5.6)「唯一」vs (5.5)／`tables.py:372` 漏列 ——P1-04
5. M2 升級 §V 未回寫 `M-SU-D2-03` ——P2-05
6. M8／TODO §E 與 SPEC §N 同向；mutation 32 計數正確；與 D-001 座標語意「不動」句（L13）相容——前提是 adapter 寫清楚（目前未清）

不改就進 Task 9.x：①mutation 29 按「鍵」寫測會空心／假綠；②v8 錨可被雙檔同改或整檔 write 換掉；③derive 接 validator 時座標／宇宙不一致 → 誤殺或多標的交錯批假紅；④Agent 只掃 register 會漏改 pipeline／面板計數與 `tables` assignments 消費面。

---

## Findings

## GROK-R11-P1-01

**斷言**: v11 已把 (G-4d)① 從「v8 **鍵**」改成獨立檔 `splitunify_golden.v8.json`＋`.sha256`，但 `M-SU-D2-29` 之改壞面與應紅測試仍寫「覆寫 v8 baseline **鍵**／v8 鍵保留」——被取代的舊 mutation 字面未同步，mutation 對新落點不可驗。

**碼證**: `sed -n '301p' docs/SPLITUNIFY_SPEC.D-002.md` → `M-SU-D2-29` 逐字「直接覆寫 v8 baseline **鍵**」「v8 **鍵**保留、只增不覆寫」；對照 L163／§V L263 已改為 `.v8.json` 檔＋`g1_membership_v9` 新鍵、並明寫「**不存在任何 v8 鍵**」。RECHECK: `grep -n 'M-SU-D2-29\|v8.json\|v8 baseline 鍵' docs/SPLITUNIFY_SPEC.D-002.md`；`jq -r 'keys[]' tests/golden/splitunify/splitunify_golden.json`（無 v8 鍵）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1

[BLOCKING] 信心度=High。屬自證②「被取代的舊內容未同步」——主委自證抓到 §V 母斷言，卻漏改 mutation 列本身。不改則 Task 9.5／freeze 實作者可依 mut 29 去找不存在的「v8 鍵」、或寫出測不到 `.v8.json` 拒寫／hash 的空心測試。**修法**：把 `M-SU-D2-29` 改壞面改為「刪／覆寫 `splitunify_golden.v8.json`、或改其內容卻不同步 `.v8.sha256`、或 `--write` 寫入 `.v8.json` 未 raise、或主檔既有 11 鍵被換錨後值覆蓋」；應紅測試對齊 §V 第 6 條三 ASSERT。**可行性**：純 SPEC 字面同步；母斷言已在 L263。

## GROK-R11-P1-02

**斷言**: (G-4d)① 落地順序 (iii) 的「`sha256(.v8.json)==.v8.sha256`」是自參照雜湊，同時改寫兩檔即可繞過；且現行 `--write` 對主檔整檔覆寫，未強制自 `.v8.json` merge 保留既有 11 鍵，可一次換掉舊錨。

**碼證**: L163 (i)–(iv)；§V L263。VERIFY：對竄改內容重算 sha 後「file==sha_file」恆成立（探針示意 sha12=`349a8ca204eb`）；`sed -n '373,386p' scripts/freeze_splitunify_golden.py` 仍 `golden_path.write_text(...)` 無 merge-from-v8、無 `.v8` 拒寫。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r11/m5_m6_probe.txt` 之 M6 段；讀 freeze `--write` 分支。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。不改則 Task 9.2b 重凍可在「綠燈」下換掉換錨前回歸錨。**修法**：①(iii) 改為比對**外部錨**（例如把初次凍結之 sha 寫進 SPEC／lock 檔／已提交 blob，且該錨本身不由同一次 `--write` 更新）；或要求 `.v8.json` 一經創建即 `chmod`／CI 禁改（內容變更須另票）；②Task 9.5／freeze：`--write` 主檔時**必須**先讀 `.v8.json` 把既有 11 鍵逐值拷入再只寫入 v9 新鍵；③mutation 覆蓋「雙檔同改」與「主檔舊鍵被換」。**可行性證據**：現行 write 路徑單一、可加 merge 六行級；外部錨可用「首次 commit 之 sha256 字面」寫進 §V（與 golden byte 閘同型）。

## GROK-R11-P1-03

**斷言**: `Task 9.2b` 步驟 0③ 之座標 adapter「二擇一」只約束 `row_index`、未要求 `ts`／`symbols` 與之同一座標系，且漏列第三條可行路徑（局部宇宙＋局部索引）；照現文實作仍可 IndexError 誤殺，或誤以為二擇一已窮盡。

**碼證**: SPEC L217／§V L264。VERIFY 探針（`purge_semantic=timedelta`）四案：`full+global` PASS；`local_univ+global_idx` → `IndexError: plan.row_index contains positions outside base universe`；`local+local` PASS；`full_univ+local_idx` → `CrossSymbolLeakageError`。RECHECK: 重跑探針；`sed -n '646,647p;676,685p' momentum/core/contracts.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/core/contracts.py#1471cef968a3

[BLOCKING] 信心度=High。R10 M5 採納方向對，定義仍窄。不改則多標的交錯批在 Task 9.2b 接 validator 時重現假紅，或 Agent 選 (a) 只改 row_index 不改宇宙陣列。**修法**：改寫為「座標系一致」三選一寫死——(a) `row_index`＋`ts`/`symbols` 皆 full-universe；(b) local→global rebase 後接 full-universe 陣列；(c) 整條 derive 鏈維持該 symbol 局部宇宙＋局部索引（探針證明可行）；並規定**禁止混用**。§V 母斷言改為涵蓋「全域索引配局部宇宙 ⇒ 必須先適配、不得裸呼叫」。**可行性**：探針四案已給真值表；validator 簽名為 `(train, test, ts, symbols)`，契約可逐字寫死四參數同位系。

## GROK-R11-P1-04

**斷言**: (5.6) 自稱「唯一計數依據與唯一施工清單」共 25 條，但 (5.5) 具名之 pipeline／API／前端事件批面板計數消費面，以及碼上 `tables.py:372` 之 `assignments.set_index("event_id")`，皆不在 register——唯一真相源與敘述／碼點再次分叉。

**碼證**: (5.5) L82 逐字列 `pipeline` 產出之 `n_train`／`n_test`／`n_purged`、API 模型、前端事件批面板；register C5-01..25（L94-118）無 pipeline／API／`EventTablesPanel` 列（C5-15＝`batch_facts`、C5-23＝wiring `dict(zip)`）。`pipeline.py:761-763` 現行以 `assignments[...].sum()` 寫入 summary counts；`EventTablesPanel.tsx:361` 顯示 `s.n_test`；`tables.py:372` `assignments.set_index("event_id")` 而 (5.3) 只寫「tables 兩處」。RECHECK: `grep -nE 'C5-|pipeline\.py:76|EventTablesPanel|tables.py:372' docs/SPLITUNIFY_SPEC.D-002.md momentum/Analysis/event_samples/pipeline.py momentum/Analysis/event_samples/tables.py frontend/src/components/ic-analysis/EventTablesPanel.tsx`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;momentum/Analysis/event_samples/tables.py#843ba7f68172;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[BLOCKING] 信心度=High。此即自證**第七種形態**：新建唯一 register 後未對帳敘述層與碼點。不改則實作者可只掃 25 列自稱合規，卻漏改會讓複合鍵後 `n_test` 膨脹的 pipeline 路徑，或漏掉 assignments 消費面（近丙類）。**修法**：①register 增列 pipeline summary counts、API 計數模型、`EventTablesPanel` 計數顯示、`tables.py:372` assignments 消費（分類建議：前三者隨 Task 9.4 去重／事件數語意；assignments lookup 近丙）；②同步改標題條數與 §R；③(5.3)「兩處」改為與碼一致之列舉。**可行性**：與 M7 同型——加列＋改數字；Task 9.4 已有改法句可掛 Task 欄。

## GROK-R11-P2-05

**斷言**: M2 已把 §V `metadata.split_unify` 升級為與 producer／summary **值相等**，但 `M-SU-D2-03` 應紅測試仍只指向「鍵斷言」——鍵在而值遭手塞空 dict 時 mutation 網不紅。

**碼證**: §V L253 逐字 `ASSERT metadata.split_unify["discarded_rows_by_feature_tf"] == EventSplitPlan.summary[...] == producer 回傳之 discarded`；L277 `M-SU-D2-03` 應紅面逐字「`metadata.split_unify` **鍵斷言**」。RECHECK: `sed -n '253p;277p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1

[MAJOR] 信心度=High。R10 本家 P1-03 修法建議「應紅面加鍵在但值不一致」未落地——又一次「改 §V 沒回寫 mutation」。不改則孤立單測手塞 `{}` 仍可能讓 mut 03 路徑假綠（§V 整鏈若被實作者省略時）。**修法**：`M-SU-D2-03` 應紅面改為「不傳入、或鍵在但值 ≠ summary／producer、或改 reason 封閉值集」；對齊 L253。**可行性**：一字級 SPEC 同步。

---

## §1 十一類（摘要）

1. 矛盾：mut 29「v8 鍵」↔ 檔案制；(5.6) 唯一 ↔ (5.5) 具名漏列  
2. 漏項：register 漏 pipeline／面板／tables assignments；M5 宇宙同位系；M6 外部錨  
3. 不可測：mut 29 按舊字面不可對新落點應紅  
4. quant：tier_min／n_test 膨脹路徑若只依 register 施工可能漏改  
5. 過度工程：無（G-4e 殘餘不要求第四 oracle）  
6. OOM：無  
7. Cache：無  
8. API／型別：baseline 舊鍵刪除本輪未否證下游  
9. 測試：mut 03 鍵級；mut 29 空心風險  
10. Agent 可執行：M5 二擇一歧義；register 自稱唯一卻漏列  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R10 三條 → 01／02 閉；03 剩洞 → P2-05  
2. 自證六條 → ②③ 漏 mut 同步；**第七形態** register↔敘述 → P1-01／P1-04／P2-05  
3. 攻 (5.6) → P1-04  
4. 攻 (G-4e) → 殘餘誠實成立，不開 finding  
5. 攻 M6／M5 → P1-02／P1-03  
6. 新衝突 → 上列；M8／計數 32／gates 本輪綠

## 被當成事實的未驗證假設（§0 彙總）

1. 「25 條涵蓋全部消費面」——被 (5.5)／`tables.py:372` 否證。  
2. 「M6 (i)–(iv) 不可繞過」——被自參照雜湊＋整檔 write 否證。  
3. 「M5 二擇一窮盡」——被局部＋局部第三路徑與宇宙同位系反例否證。  
4. 「(G-4e) 殘餘只能散文」——成立；標註夠誠實。  
5. 「baseline 刪 `n_test` 無下游破口」——本輪未否證。

ASSUMPTIONS_VERIFIED: R10 三條對讀；十項落點逐項 grep；mutation 32／C5 25 計數；golden 11 鍵無 v8；obl／fmt／xref_r10 rc=0；M5 四案探針；M6 自參照構造；freeze --write 整檔；pipeline:761／EventTablesPanel:361／tables.py:372 碼點；mut 29／03 字面  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_TODO.md` → rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-b9-review-r10/synth.md docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；venv 探針 → `/tmp/grok-splitunify-b9-review-r11/m5_m6_probe.txt`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r11-grok.md --family grok`  
FAILURES_SEEN: none（探針 TypeError 一次因 kwargs 誤用 `symbol_arr`，改 `symbols=` 後四案落地）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r11-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R11-P1-01,GROK-R11-P1-02,GROK-R11-P1-03,GROK-R11-P1-04
CLOSED:
STATUS: DONE
