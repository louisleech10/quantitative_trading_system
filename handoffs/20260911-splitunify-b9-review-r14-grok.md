# SPLITUNIFY b9 — review-r14（R13 三條閉合再驗證 ＋ D-002 v14 重簽；DOCROT 量測第二輪）— grok

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R14`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R14-BRIEF.md`  
**findings-round**: R14  
**brief-kind**: review  
**審查標的**: `git show 9ec33871` 之 SPEC／TODO diff ＋ current block（C5-20／21、M-35／36、B9D、Task 9.2a／9.3）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（僅允許 append 戳記）。

---

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: body sha256 → `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` ＝ `7455b305c6f3c013de84d1941c4d69bc731fb5fa90f6e91d447e14382f0b10e2`（與 brief 一致）。

fact-verified: mutation 36 列、01–36 連續無缺 → `grep -cE '^\| .M-SU-D2-[0-9]+.'`＝36；逐號 python 掃描 missing=[]。

fact-verified: §C-9 認領 36/36 → `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l`＝36。

fact-verified: register 29 列 → `grep -cE '^\| .C5-[0-9]+.'`＝29。

fact-verified: `共 **36** 條` 恰一行（mutation 目錄標題 L274）。

fact-verified: `doc_format_precheck` 對 SPEC／TODO 皆 rc=0。

fact-verified: `reconcile_stamps_check.sh` 對現行 body → FAIL（v13 戳記 sha `06b2d4cb…` ≠ 新 body；預期，本輪重簽）。腳本逐家 `tail -1` 取最新戳記（`scripts/reconcile_stamps_check.sh:102`／`:118`）⇒ 保留舊行不會誤判，只要新行 hash 正確。

fact-verified: R13 diff 落地 → `C5-20`→`M-SU-D2-35`、`C5-21`→`M-SU-D2-36`；Task 9.3 receipt 含 exact ID set＋禁 `wc -l`；B9D 改「九處」具名。

assumed（brief 攻 #1）: `M-SU-D2-35`／`36` 之「欄缺 ⇒ KeyError」足夠 → **部分不成立**。見 `GROK-R14-P2-03`（單 TF＋軟 `subset` 可綠）。

assumed（brief 攻 #2）: 主委只修 C5-20／21 之同型自查已足夠、其餘 27 列無錯配 → **否證**。見 `GROK-R14-P1-01`／`P1-02`（C5-29、C5-25）。

---

## 必答

### (1a)(1b) 重跑 R13 反例

本家 R13 **零 finding**（僅 sentinel `GROK-R13-P3-00`）⇒ 無本家反例可標 CLOSED／STILL-OPEN。

對 brief 表 (A) 三條＋主委自產之**落地核對**（非本家 CLOSED 欄）：

| finding | 判定 | 重跑命令與觀測 |
|---|---|---|
| `CODEX-R13-P1-01` | **修補已落地** | `grep -n 'C5-20\|M-SU-D2-35' docs/SPLITUNIFY_SPEC.D-002.md` → L115 `C5-20`…`M-SU-D2-35`；L312 專條「assignments 不寫 feature_timeframe」；不再指 `M-SU-D2-20`。 |
| `CODEX-R13-P1-02` | **修補已落地** | `awk '/^### Task 9\.3/,/^### Task 9\.4/' docs/SPLITUNIFY_TODO.md \| grep -n 'exact ID set\|wc -l\|TASK:\|COMMIT:'` → 含 exact ID set、`diff <(…)`、明文「不得改用 wc -l」、TASK／COMMIT 標頭。舊「只比行數」字面消失。 |
| `CODEX-R13-P2-03` | **修補已落地** | `grep -n 'B9D' docs/SPLITUNIFY_TODO.md` → L67 寫「九處」＋七模組＋兩支撐面；與 Task 9.3 表九列一致。 |
| 主委 `C5-21`／`M-36` | **修補已落地** | L116 `C5-21`…`M-SU-D2-36`；L313 專條。 |

### (2a)(2b) C5-01..C5-29 mutation 逐列核對

**(2a) 錯配 2 列**（其餘 27 列對應可接受；C5-15／16／17／28 之 `—` 為具名缺口非錯配）：

| ID | 現指 | 應指／動作 |
|---|---|---|
| `C5-29` | `M-SU-D2-06` | **需新增**（建議 `M-SU-D2-37`）：`tables.py:372` 之 assignments 消費**略過去重／fail-closed**（與「甲類 `.loc` 被誤改複合鍵」方向相反） |
| `C5-25` | `M-SU-D2-19` | **需新增**（建議 `M-SU-D2-38`）：survivor **餵入端略過去重**（與「六鍵被改成含 TF」不同缺陷；`M-19` 仍歸 `C5-10`） |

**(2b) 可執行對照**（本輪實跑）：

```bash
# 抽出 register 末欄 mutation ID 與 mutation 表「改壞什麼」並列
python3 - <<'PY'
# （交件內嵌邏輯）對 C5-01..29 逐列印 refs + mutation WHAT 前 110 字
# 判定準則：mutation 破壞的行為是否＝該 C5「改法」之逆操作
PY
```

抽樣碼證：`C5-20`→`M-35`（不寫欄）✓；`C5-13`→`M-06`（甲類誤改複合鍵）✓；`C5-29`→`M-06` 之 WHAT 仍寫「`.loc[eid]` 被誤改為複合鍵」「應紅於 receipts／clusters」——**抓不到** `:372` 略過去重 ⇒ 錯配；`C5-10`→`M-19`（鍵含 TF）✓；`C5-25`→`M-19` 之 WHAT 不提餵入去重 ⇒ 錯配。

### (3a)(3b) M-35／36「應紅之測試」是否足夠

**(3a) 不足**（見 `GROK-R14-P2-03`）。

**(3b) 可直接貼進該欄的加強字面**：

> `Task 9.2a` 之 `test_assignments_composite_key_unique`（🔴 須用**≥2 feature TF** fixture；先 `assert "feature_timeframe" in assignments.columns`，再無條件 `duplicated(subset=["event_id","feature_timeframe"])`；生產 guard 與測試皆**不得**以 `if "feature_timeframe" in df.columns` 包住）。欄缺 ⇒ 欄存在斷言紅；有欄而重複 ⇒ duplicated 紅。

（`M-36` 對 `test_purged_composite_key_unique` 同文。）

實跑否證：單 TF 無欄＋軟 subset 退回 `["event_id"]` → `any_dup=False`（綠洞）；多 TF 全量無欄時軟 subset 仍因 event_id 重複而紅——故洞在**單 TF fixture＋軟包**。

### (4a)(4b) Task 9.3 receipt 新閘繞過

**(4a) 仍可部分繞過**（見 `GROK-R14-P2-04`）。

試過構造（workdir `/tmp/grok-r14-receipt-sim`）：

1. **同 ID×29** → `sort -u` exact set `diff` **FAIL**（舊洞已堵）。  
2. **正確 29 ID、分類全填 `甲 -> 甲`、碼證 `nowhere:0`** → ID set `diff` **PASS**（語意垃圾仍過機械閘）。  
3. **`COMMIT: deadbeef…` 任意 sha** → 檔案級格式／ID set 仍過；TODO 只寫「驗收時比對 audit」，驗證命令清單未含強制 `audit.log` grep。

**(4b) 最小修補**：於 Task 9.3 驗證段加第 4 點——`COMMIT:` 須等於 `git rev-parse HEAD`（開工時寫入）且 `TASK:` 須命中 `.claude/gate/audit.log` 當輪 `task_id`（給出可複製的 `jq`／`grep` 命令）；另可選：抽樣 `N` 列之「改後分類」須等於 SPEC register 該列分類（擋全填同一值）。

### (5a)(5b) 戳記

**(5a) `REJECTED`**（阻擋＝P1-01／P1-02；一次修訂可關）。

**(5b) 一次修訂閉合集合**：①新增 `M-SU-D2-37`（C5-29 專屬）並改 C5-29 指標；②新增 `M-SU-D2-38`（C5-25 專屬）並改 C5-25 指標；③mutation 條數 36→38、標題與 §C-9 認領同步；④（建議同修）加強 M-35／36 應紅字面＋Task 9.3 receipt 第 4 點。

### (6a)(6b) 可否領 impl token 進 Task 9.1

**(6a) 不可以。**

**(6b) 最小閉合**：上列 (5b) 修訂 → 三家對新 body 重簽 → `reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0 → 再領 token。本輪已確認 v13 戳記因 body 變更失效；P1 錯配未關前不得 APPROVED。

---

## 攻擊面補答

| 面向 | 結論 |
|---|---|
| 其餘 27 列 mutation | 2 錯配（C5-29、C5-25）；餘可接受 |
| Task 9.3 receipt | exact set 堵住重複 ID；分類恒值／假 COMMIT 仍過 |
| B9A–F vs Task | B9D 已與九列對齊；B9A＝9.1、B9B＝9.2+9.2a、B9C＝9.2b、B9E＝9.4、B9F＝9.5 描述與 Task 相符 |
| 舊戳記保留 | `tail -1` 取最新 ⇒ 不誤判 |

## DOCROT 摩擦字面集合（brief 順帶問）

**過窄。** `CODEX-R13-P2-03` 斷言含「六個下游…九列…不一致」，未命中現行  
`多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張`  
（該斷言無「原寫／多落點／共 N 條.*兩」等 token）。

**可直接替換的封閉集合**（仍可 grep、不靠語意）：

```text
多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|與表列|表列.*不符|描述與.*不符|批次 scope|前版修法|原寫|已作廢主張
```

（本條為量測判準建議，**不**列為 SPEC finding。）

---

## §1 必查（11 類；範圍＝v14 diff／current block）

1. 矛盾/互斥：C5-29／C5-25 與所繫 mutation 互斥（P1）  
2. 漏項：兩丙類缺專屬 mutation（P1）  
3. 不可測驗收：M-35／36 應紅字面可被單 TF＋軟包繞過（P2）；receipt 語意閘不足（P2）  
4. 可疑 quant：無（本輪不重審數值契約）  
5. 過度工程：無  
6. OOM/並行：無  
7. Cache：無  
8. API/型別：無  
9. 測試品質：見 P2-03  
10. Agent 可執行性：P1 阻擋重簽／領 token  
11. 必要性/短命工：無  

## 被當成事實的未驗證假設（§0）

1. 「KeyError 必紅」——單 TF＋軟 subset 可綠（已實跑）。  
2. 「只修 C5-20／21 即無同型錯配」——C5-25／29 仍錯配（已逐列對照）。

---

## GROK-R14-P1-01

**斷言**: `C5-29`（`tables.py:372` assignments 消費須去重／fail-closed）仍指向 `M-SU-D2-06`，而該條破壞的是甲類 `.loc[eid]` **被誤改為複合鍵**且應紅於 receipts／clusters——與「略過 :372 去重」不同缺陷，屬與 R13 `C5-20`／`C5-21` 同型的 mutation 錯配。

**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 保留 `assignments.set_index("event_id")["symbol"].reindex(idx)` 不去重、不 fail-closed；多 TF 下索引重複時靜默取錯 symbol——現行 `M-SU-D2-06` 之應紅測試只覆蓋 receipts／clusters 誤改複合鍵，不會因此轉紅。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#39f981a4a636

[BLOCKING] 信心度=High。修法：新增 `M-SU-D2-37`（WHAT＝`:372` 略過去重／fail-closed；應紅＝`test_tables.py` 具名「assignments 消費去重」測試），`C5-29` 改指之；`M-06` 仍歸 `C5-13`。可行性：`:372` 已存在且 SPEC 已標丙類真缺陷；與 R13 新增 M-35／36 同形手術。條數 36→37（若併 P1-02 則→38）。

---

## GROK-R14-P1-02

**斷言**: `C5-25`（survivor 餵入端須先去重）仍指向 `M-SU-D2-19`，而該條破壞的是六鍵**被改成含 feature TF**——與「餵入略過去重致重複三元組改雜湊」不同；`M-19` 應只覆蓋 `C5-10`。

**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/ic_feed.py:143
MUTATION: 多 TF 下把含重複 `event_id` 之窗列直接餵入 `event_context_from_windows`／survivor 六鍵組裝且**不**先 `drop_duplicates(event_id)`，鍵集仍不含 TF——雜湊漂移但 `M-SU-D2-19`（鍵含 TF）之測試仍可綠。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#39f981a4a636

[BLOCKING] 信心度=High。修法：新增 `M-SU-D2-38`（餵入略過去重；應紅＝Task 9.3／`test_gap3_conditional_ic.py` 具名「餵入去重後雜湊穩定」），`C5-25` 改指之；`M-19` 留 `C5-10`。可行性：`(5.1)`／`(5.4)` 已明文要求餵入去重；缺的是專屬反向 mutation。

---

## GROK-R14-P2-03

**斷言**: `M-SU-D2-35`／`36` 之「應紅之測試」只寫欄缺 ⇒ `duplicated(...KeyError)`，未禁止 `in df.columns` 軟包、未要求多 TF fixture——單 TF＋軟 subset 可對欄缺維持綠。

**碼證**: 實跑 `python3`：單 TF `DataFrame(event_id=[1,2])` 無 `feature_timeframe`，`subset=["event_id"]+([..] if in columns else [])` ⇒ `any_dup=False`；對照無條件 subset ⇒ `KeyError`。SPEC L312–313 現文字面僅提 KeyError。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#39f981a4a636

[MAJOR] 信心度=High。doc 面可修：把應紅欄換成必答 (3b) 字面。非空殼。

---

## GROK-R14-P2-04

**斷言**: Task 9.3 新 receipt 閘在 exact ID set 之後，仍可用「正確 ID 集合＋分類全填同一值」或「任意 COMMIT sha」通過檔案級機械條件。

**碼證**: `/tmp/grok-r14-receipt-sim/bypass-sameclass.txt`：`diff` ID set rc=0 且每列 `甲 -> 甲 nowhere:0`；對照 duplicate-ID 檔 `diff` 非 0（證明只堵了 R13 具名洞）。TODO L632–639 無 audit／HEAD 強制命令。

**來源摘要**: docs/SPLITUNIFY_TODO.md#5738e9c63f6f

[MAJOR] 信心度=High。修法見必答 (4b)。不阻擋「是否掃過 29 ID」之主目標，但可假完成語意重掃。

---

VERDICT: blocked
BLOCKED-BY: GROK-R14-P1-01,GROK-R14-P1-02
CLOSED:

ASSUMPTIONS_VERIFIED: body sha `7455b305…`；mutation 36 連續；§C-9 認領 36；register 29；doc_format 雙綠；R13 三條＋C5-21 字面落地；stamps 對新 body FAIL（預期）；stamp 腳本 `tail -1`；C5 逐列對照得 2 錯配；KeyError／軟 subset 實跑；receipt 兩構造實跑
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `7455b305…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=1（hash mismatch）；receipt sim ID-set／dup 構造；pandas KeyError／軟 subset 探針
FAILURES_SEEN: none
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅將 append REJECTED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r14-grok.md

STATUS: DONE
