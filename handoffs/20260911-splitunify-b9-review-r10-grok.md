# SPLITUNIFY D-002 閉合輪 R10 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R10`  
family: grok  
findings-round: R10  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第十次修訂；sha12 `2c5a584645ab`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r9/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r10/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉（敘述用，不入裁決欄）: `GROK-R9-P1-01`～`04`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R9 二十一條歸十一群 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r9/synth.md`

fact-verified: 現行 golden fixture 全部事件 `decision == cutoff`（`freeze_splitunify_golden.py:117` 直接複製）→ `sed -n '112,120p'`

fact-verified: `validate_split_pair_integrity` 存在於 `momentum/core/contracts.py:676`，derive 路徑（`split_projection.py`）**零呼叫**；呼叫點在 `ic_filter_orchestrator`／`ic_split_adapter` → `grep -rn validate_split_pair_integrity momentum --include='*.py'`

fact-verified: `discarded_rows_by_feature_tf` 計畫型別為 `Dict[str, int]`；`split_unify.json` 之 `test_segment_count_keys` 判準為「鍵名含 test **且值為整數**」⇒ 該新鍵不落入 deny-by-default 整數桶 → `venv/bin/python` 讀契約

fact-verified: mutation 表列 **31**、ID 01–31 連續、正文宣稱 31 → 探針計數

fact-verified: `obligation_block_check`／`doc_format_precheck` 皆 rc=0 → 實跑

fact-verified: `(6.2)` L92 仍寫 baseline `n_test`＝**樣本數＝事件數**「**等價**」；`Task 9.4` L211 寫須同時輸出 `n_test_events`／`n_test_samples` 且「**不得**宣稱兩者恆等」→ `sed` 對讀

fact-verified: `Task 9.1` L150 要求 producer→summary→metadata **整鏈驗值**；§V L220 對 metadata 僅 `ASSERT … 帶該鍵`（無值相等）→ 對讀

assumed: 第十次修訂十一項每一項都落在該落位置  
→ **部分否證**：L1–L6／L9–L11／mutation 條數落點成立；**L7 之整鏈驗值未進 §V**；**L8 之雙量定案未回寫 (6.2)**。見必答 2。

assumed: (G-4e) 第三份判準不會與 (G-4c) 形成三份同錯  
→ **否證**：第三份若仍是「同一三段式的另一次編碼」，proj＝oracle＝third 同寫 R6 不等式時三者全等、G-4e **綠**、正確側為 purged。見必答 3／P1-01。

assumed: baseline 同時輸出兩量後下游不會再混用  
→ **弱否證／規格缺口**：現行 `baseline.py:120` 只回 `"n_test": len(idx)`；生產呼叫面僅測試；SPEC **未**規定舊鍵 `n_test` 廢除、別名或保留語意 ⇒ 與仍寫「等價」的 (6.2) 疊加後，讀錯那一個的路徑仍開著。見必答 4／P1-02。

assumed: Step 0 補 pair 後三段式確定互斥且窮盡  
→ **本輪在界內成立**（探針 dense scan `decision∈[index0,index_last]` 皆恰命中一條）；界外依 Step 0④ raise。Rule 4 與 Step 0④ 重複，屬冗餘非互斥破壞。見必答 4。

---

## 必答 1–5

### 1. 本家 R9 finding 是否閉合

| R9 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R9-P1-01` | **字面 CLOSED／剩餘洞重開 R10** | (G-4e) 已入 §G L129、§V L227、`M-SU-D2-28`；但第三份仍定義為「同一三段式純函式」⇒ 擋不住三份同錯（探針）⇒ `GROK-R10-P1-01` |
| `GROK-R9-P1-02` | **CLOSED** | §N L281 已有字面 `為何現在不做: blocked-by:…`；改引 `SPEC_TEMPLATE`；BRIEF 僅作「誤引」追溯 |
| `GROK-R9-P1-03` | **CLOSED** | 正文已無「若成本超出…只交付前兩層」逃逸句；L151 鎖定三層 |
| `GROK-R9-P1-04` | **CLOSED** | L138 目標改為「交付至 producer 層；終端可見性見 §N」；舊「終端使用者看得到」句已清 |

（跨輪 ID **不**填入本檔 `CLOSED:` 欄。）

### 2. 檢驗自證步驟（十一項落點）

| 群 | 落點是否到位 | 證據 |
|---|---|---|
| L1 (G-4e) | **字面到位、效力不足** | §G L129／§V L227／mut 28 皆有；但定義本身被探針否證 ⇒ P1-01 |
| L2 (G-4d)→§V＋mut 27–31 | **到位** | §V L225–229 五條；mut 27–31 表列存在 |
| L3 目標句 | **到位** | L138；舊句 grep 無命中 |
| L4 §N 強制欄 | **到位** | L281 含 `為何現在不做:`；TODO §E L471 同步 |
| L5 擇定三層 | **到位** | 正文無逃逸句；L151 鎖定；逃逸字樣僅殘於沿革 |
| L6 L127 | **到位** | 「(G-4d) 允許之差異集合內…除外」 |
| L7 資料流交接 | **Task 有、§V 漏** | L150 整鏈驗值；§V L220 metadata 只驗鍵 ⇒ P1-03 |
| L8 baseline 雙量 | **Task 有、(6.2) 漏** | L211 雙量＋不得恆等；L92 仍「等價」⇒ P1-02 |
| L9 Step 0 pair | **到位** | L184①–③＋`validate_split_pair_integrity`；§V L230；mut 30 |
| L10 TODO §E | **到位** | `docs/SPLITUNIFY_TODO.md:471` 含 owner／recheck／觸發 grep |
| L11 early／late | **到位** | §V L228–229 |

主委自稱只自查了 mutation 條數——本輪複驗確認：**mutation 31 正確**；另抓到 **兩處「改 Task／§G 沒回寫依賴段」**（L7→§V、L8→(6.2)），與近三輪「寫了要做卻沒做」同型。

### 3. 攻 (G-4e)

**(G-4e) 若第三份＝「同一三段式的另一次編碼」，則三份同錯時仍然全綠。**

探針 `/tmp/grok-splitunify-b9-review-r10/probe_g4e_l9.txt`：

| 角色 | 公式 | gapX(`decision=250,train_last=200,test_start=300`) |
|---|---|---|
| 正確三段式 | `<=train_last`／`>=test_start`／其間 purged | **purged** |
| 錯（R6 不等式） | `decision < test_start ⇒ train` | **train** |

若投影、oracle、第三份**同寫** R6 不等式：`proj==oracle==third==train` ⇒ G-3b 綠、**(G-4e) 亦綠**；正確側為 purged。

另：`(G-4e)` 正文**沒有**「不得與投影／oracle 共用實作」紀律（對照 (G-4c) 對 oracle 有「不 import 投影」）；實作者可抽共用 `_side()` 餵三處，結構上保證三份同錯。

**誠實標註**：現文 (G-4e) 只能抓「三份之間轉錄不一致」，**不能**抓「同一次對 SPEC 的錯誤解讀寫進三份」。要擋後者，第三份必須是**與公式編碼獨立**的期望——例如 fixture 內預先寫死的 `expected_side` 字面（人手依三段式對新 `decision!=cutoff` 事件填好），再 ASSERT `proj == oracle == fixture.expected_side`。探針對照：`literal_expected="purged"` 時 `all_wrong_r6` 會紅。

⇒ **P1-01**

### 4. 攻 L8／L9 修法

**L8 不足／且自相矛盾：**

- `(6.2)` L92 仍宣稱落地後 `n_test`＝樣本數＝事件數「**等價**」；`Task 9.4` L211 否證並要求雙量——同檔互斥（閘看不到同檔矛盾）。
- `Task 9.4` L208 仍寫「依 (6.2) 將 `n_test`…定為事件數」，與 L211 雙量定案互相拉扯。
- 下游：`baseline.py:120` 現行唯一鍵 `"n_test"=len(idx)`（＝樣本數）；呼叫面主要在 `tests/momentum/event_samples/test_baseline_oracle.py`。SPEC **未**規定舊 `n_test` 刪除／改名／保留為 samples alias ⇒ Agent 可保留 `n_test`＝samples，同時讀 (6.2) 的人把它當事件數。

**L9 在補完 pair＋不變量後，界內互斥且窮盡成立**（探針 dense OK）。`decision==train_last`→train、`==test_start`→test；隔離帶開區間。界外由 Step 0④ raise。Rule 4 與 Step 0④ 語意重複——建議刪 Rule 4 或標「已由 Step 0 涵蓋」，不升 P1。

⇒ L8 **P1-02**；L9 本輪不開 finding。

### 5. 修訂引入的新問題／衝突

1. **(G-4e) 定義不夠強**（P1-01）——L1 字面閉、效力未閉  
2. **(6.2)↔Task 9.4 L211** 正面衝突（P1-02）——L8 自證漏網  
3. **L150 整鏈驗值 ↔ §V L220 只驗鍵**（P1-03）——L7 自證漏網  
4. L9／L3／L4／L5／L6／L10／L11／mutation 計數本輪對讀一致  
5. D-001 更正義務、TODO §E 與 §N 同向；無新的 epic 級互斥

不改就進 Task 9.x：①重凍時三份同寫錯公式仍全綠；②Agent 依 (6.2) 可只輸出單一 `n_test` 並自稱等價，或依 L211 輸出雙量——兩邊都「有依據」；③metadata 可手塞鍵通過 §V 而真實 discarded 值未交接。

---

## Findings

## GROK-R10-P1-01

**斷言**: (G-4e) 將第三份判準定義為「以 Task 9.2b 三段式從 fixture 欄位再編碼一次的純函式」時，**擋不住**投影／oracle／第三份被同一次改動寫入同一錯誤語意——三者仍全等而放行。

**碼證**: SPEC L129 (G-4e)、L227、`M-SU-D2-28`。VERIFY 探針：`decision=250,train_last=200,test_start=300` 正確＝`purged`；三份同寫 `decision < test_start ⇒ train` ⇒ `proj=oracle=third=train`，G-3b 與 (G-4e) **皆綠**。L129 對第三份**無**「不得與投影／oracle 共用實作」句（對照 L128 oracle「不 import 投影」）。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r10/probe_g4e_l9.txt` 之 G-4e 段；`sed -n '129p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。這是 R9 `GROK-R9-P1-01`／L1 採納後的**剩餘洞**：方向對（要第三份），定義弱（第三份仍是同公式）。不改則 Task 9.2b 落地＋重凍可把「忘記隔離帶」同時寫進三處並通過 G-3b／(G-4e)。**修法**：①第三份改為 fixture **字面** `expected_side`（或獨立 expected-membership 表），對每個 `decision!=cutoff`／隔離帶／邊界事件預先填好；ASSERT `proj == oracle == fixture.expected_side`；②明令第三份**不得**與投影／oracle 共用函式／import；③保留現有「三段式純函式」最多當開發期輔助，**不得**單獨充當 (G-4e) 閘。**可行性證據**：同一探針顯示 `literal_expected="purged"` 時 `all_wrong_r6` 會紅；freeze 已有 per-event 欄位可加一欄；新邊界事件本就要進 fixture（§V L226 前置），填 expected_side 為同批一行成本。

## GROK-R10-P1-02

**斷言**: L8 修訂只改了 `Task 9.4` L211（雙量＋不得恆等），**未**回寫 `(6.2)` L92（仍寫樣本數＝事件數「等價」）與 L208「依 (6.2)…定為事件數」——同檔義務互斥，實作者可選任一側自稱合規。

**碼證**: L92 逐字「故其 `n_test`＝**樣本數＝事件數**，兩者在本延伸落地後**等價**」；L211 逐字「須**同時輸出** `n_test_events`…與 `n_test_samples`…**不得**宣稱兩者恆等」；L208「依 (6.2) 將 `n_train`／`n_test`／`n_purged` 明確定為事件數」。`baseline.py:120` 現行 `"n_test": int(len(idx))`。RECHECK: `sed -n '92p;208p;211p' docs/SPLITUNIFY_SPEC.D-002.md`；`sed -n '118,121p' momentum/Analysis/event_samples/baseline.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。屬本輪必答 2 之自證漏網（主委改 L211 沒 grep 回 (6.2)）。不改則：①Agent 依 (6.2) 可拒絕雙量；②或輸出雙量卻保留語意不明的舊 `n_test`，讀報告者混用。**修法**：①(6.2) 刪「等價」句，改寫為「`baseline` 必須同時輸出 `n_test_events` 與 `n_test_samples`；物化失敗時兩量可不等」；②L208 改為「summary／報告鏈之 `n_test` 為事件數；`baseline` 見 L211 雙量，**不**再使用單一 `n_test` 充當兩者」；③明定舊鍵 `n_test` 在 baseline 回傳中：**刪除**或**僅作 `n_test_samples` 之暫時別名並在 §V／mutation 限期移除**（擇一寫死）；④§V／`M-SU-D2-31` 已指向物化失敗 fixture——保持，並加 ASSERT 兩鍵皆在。**可行性**：純 SPEC 同步；碼側只多兩個 int 鍵；測試呼叫面已盤為 `test_baseline_oracle.py`／`test_mutation_guard.py`。

## GROK-R10-P1-03

**斷言**: L7 在 `Task 9.1` L150 已要求 producer→summary→metadata **整鏈驗值**，但 §V L220 對 `metadata.split_unify` 僅 ASSERT「**帶該鍵**」，未要求與 producer／summary **值相等**——孤立欄位單測仍可過 §V。

**碼證**: L150 逐字「驗收須為 **producer→summary→metadata 整鏈**測試（驗**值**相等，非只驗鍵存在）」；L220 逐字「`ASSERT metadata.split_unify 帶該鍵且其 reason 封閉值集未被改動`」（summary 句有「值與 producer 回傳相同」，metadata 句無）。`build_split_unify_disclosure` 簽名仍無 discarded（`split_projection.py:123-180`）；唯一 caller `ic_filter_orchestrator.py:1530-1534` 仍不傳。RECHECK: `sed -n '150p;220p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab

[BLOCKING] 信心度=High。屬本輪必答 2 之第二處自證漏網（改 Task 正文、§V 沒跟上）。不改則 L7 採納名存實亡：Agent 寫 `test_…_disclosure` 手塞 `discarded_rows_by_feature_tf={}` 即可滿足「帶該鍵」。**修法**：§V `Task 9.1` 改為 `ASSERT metadata.split_unify["discarded_rows_by_feature_tf"] == EventSplitPlan.summary["discarded_rows_by_feature_tf"] == producer.discarded`（值相等）；`M-SU-D2-03` 之應紅面加「鍵在但值與 summary 不一致」。**可行性**：L150 已寫交接路徑（summary → orchestrator → builder 參數）；§V 只差把「帶該鍵」升級為值相等——與既有 summary 值斷言對稱。

---

## §1 十一類（摘要）

1. 矛盾：(6.2)↔L211；L150↔§V L220；(G-4e) 宣稱擋兩邊同錯↔探針三份同錯仍綠  
2. 漏項：§V 整鏈值； (6.2) 未隨 L8 更新  
3. 不可測：現文 (G-4e) 對「同公式三編碼」不可區分  
4. quant：隔離帶成員可被三份同錯凍結  
5. 過度工程：無（反而是第三份應改為字面期望）  
6. OOM：無  
7. Cache：無  
8. API／型別：baseline 舊 `n_test` 鍵命運未鎖  
9. 測試：§V metadata 值斷言缺；mut 28 依現文 (G-4e) 可能假綠  
10. Agent 可執行：(6.2)／L211 二選一  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R9 四條 → 02／03／04 閉；01 字面閉剩洞 → P1-01  
2. 自證十一項 → L7／L8 漏網 → P1-03／P1-02  
3. 攻 (G-4e) 三份同錯 → P1-01  
4. 攻 L8／L9 → L8 開 finding；L9 界內成立  
5. 新衝突 → 上列三條；其餘 L 群落點本輪成立

## 被當成事實的未驗證假設（§0 彙總）

1. 「十一項都落在該落位置」——被 L7／L8 漏網否證。  
2. 「(G-4e) 純函式第三份 ⇒ 不會三份同錯」——被同公式三編碼探針否證。  
3. 「雙量輸出後下游不會混用」——舊 `n_test` 命運未寫死，與 (6.2) 殘留等價句疊加後仍可混用。  
4. 「Step 0＋pair 後三段式互斥窮盡」——界內探針**未否證**（本輪成立）。

ASSUMPTIONS_VERIFIED: R9 四條對讀；十一群落點逐項 grep／計數；G-4e 三份同錯探針；L9 界內 dense scan；obl／fmt rc=0；mutation 31；fixture decision==cutoff；validate_split_pair 呼叫面；split_unify Dict 不入整數桶；TODO §E L471；baseline.py n_test 單鍵  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`venv/bin/python` G-4e／L9 探針 → `/tmp/grok-splitunify-b9-review-r10/probe_g4e_l9.txt`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r10-grok.md --family grok`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r10-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R10-P1-01,GROK-R10-P1-02,GROK-R10-P1-03
CLOSED:
STATUS: DONE
