# SPLITUNIFY SPEC v3 / TODO v3 — adversarial review R3（grok；收斂輪）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R3  
family: grok  
findings-round: R3  
標的：`docs/SPLITUNIFY_SPEC.md`（sha256 `d851e56dc1bf…`）＋`docs/SPLITUNIFY_TODO.md`（sha256 `a9ec9e1559a8…`），commit `7f040c93`  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`／禁改 reconcile synth  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0＋canonical 四欄  
SPEC-DIGEST: `docs/SPLITUNIFY_SPEC.md#d851e56dc1bf`  
TODO-DIGEST: `docs/SPLITUNIFY_TODO.md#a9ec9e1559a8`  
R2-SYNTH: `handoffs/reconcile/20260911-splitunify-x-review-r2/synth.md`（D1–D11）

### §0 前提宣告（本輪覆核）

fact-verified: SPEC/TODO hash 與 brief 一致 → `shasum -a 256` → `d851e56dc1bf…`／`a9ec9e1559a8…`；HEAD `7f040c93`  
fact-verified: `template_check` SPEC／TODO → 兩檔 `TEMPLATE PASS` rc=0  
fact-verified: `_normalize_ic_time_index` 拒收毫秒 → `ic_filter_orchestrator.py:269-271`  
fact-verified: `run_event_study_only` 現行寫死三鍵為 0 → `pipeline.py:728-734`  
fact-verified: `EventTablesPanel.tsx:352` 仍渲 summary 之 train/test/purge；`fmt(undefined)='—'`（`:41-45`）；全文無 `resp.capability`  
fact-verified: `test_gap3_split_blocked.py` **不斷言** `n_train`／`n_test`／`n_purged`（只斷言 `execution_mode`／`split_plan is None`／表有產出／ci unavailable）→ brief assumed「該測試斷言含三鍵」**否證**  
fact-verified: `EventTablesPanel.test.tsx` **不存在**；既有 vitest 為 `gap3_event_tables.test.tsx` 等，mock 帶三鍵但不 assert 其字面  
fact-verified: `estimand_note` 在 `pipeline.py:598-599`（all-bars 表），**不在** `tables.py`（該檔 371 行）；`event_forward_return_table` 之 `common` 由 `_common_constraint_block`（`tables.py:130-151`）產出  
fact-verified: 事件掃描生產 caller 無 feature universe → `case_import_service.py:1588-1613`／`pipeline.py:654-657`  
fact-verified: `split_purge_reasons` 契約僅一值 `interval_crosses_split_boundary`（`event_import_contract.json:465-467`）  
assumed: B2b 單測可用合成 `SplitPlan` 不依賴 B2a 產出 → 以 Task 2.2 簽名推演；B2a→B2b 依賴為「生產語意／golden 同源」而非編譯依賴  
assumed: 本輪之後不需 R4 → 以 D1–D11 文件層閉合＋本輪無新 P0 推演（見 Verdict）

---

## Verdict：可進 B1

R2 三個 P0（D1 C-0 落點／D2 刪三鍵自相矛盾／D3 G-5 空殼）與八個 P1 在 v3 **文件層皆有可執行落點**；本輪未找到會在 B1–B4 具體擋死的新 P0／P1。  
兩條 P2／P3（Task 3.1 漏列 embargo 檢查要點；`estimand_note` 檔案:行誤引）**不擋 B1**，建議併入施工前小補或 B3 開工 checklist，不必再開 R4。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `shasum -a 256 docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md` | SPEC `d851e56dc1bf…`；TODO `a9ec9e1559a8…` |
| `git rev-parse --short HEAD` | `7f040c93` |
| `bash scripts/template_check.sh spec docs/SPLITUNIFY_SPEC.md` | TEMPLATE PASS rc=0 |
| `bash scripts/template_check.sh todo docs/SPLITUNIFY_TODO.md` | TEMPLATE PASS rc=0 |
| `sed -n '259,277p' momentum/Analysis/ic_filter_orchestrator.py` | 毫秒 → raise「looks like milliseconds…」 |
| `sed -n '728,734p' momentum/Analysis/event_samples/pipeline.py` | 三鍵寫 0 |
| `wc -l momentum/Analysis/event_samples/tables.py` | 371（無 :598） |
| `test -f frontend/.../EventTablesPanel.test.tsx` | 不存在 |

未跑：`pytest tests/governance`（brief 禁）；未改碼。

---

## 必答 1–7（明確立場＋碼證）

### 1. 可否進 B1？

**可以。**  
判準：R2 之 P0（D1／D2／D3）在 v3 皆有具名修法＋驗收命令；本輪介面掃描未再找到「簽名上沒有卻要求 raise／復用會拒收輸入」的 P0／P1。殘留兩條為施工 checklist 級（見 P2-01／P3-01），不擋「B1＝文件／枚舉／既有紅清單、不動生產碼」。

### 2. D1 裁定是否可接受？

**是「95% 解法就收」，不是把主目標偷偷降級。**  
使用者主目標＝「同一次 UAT 不要看到兩個互相矛盾的驗證段數字」。裁定後：IC 報告保留唯一「驗證段」；事件掃描端明示 `capability.split=unavailable`＋`estimand_scope=full_sample_not_oos`，且畫面禁顯示 train/test/purge 計數（C-0 決議③(a)(b)(c)＋Task 3.3）。矛盾數字的來源（事件端假 OOS 計數）被關掉，不是改名後繼續給。代價＝事件掃描端本票無 OOS——已具名 `R-5`（needs-research），誠實。

### 3. D2 刪三鍵會不會打破既有測試或前端？

**後端既有 `test_gap3_split_blocked.py` 不會因刪鍵而紅；前端現況用 `fmt` 對缺鍵顯示「—」，但 v3 已把 UI／回歸列入修改範圍。**

| 位置 | 現行 | 刪鍵後 |
|---|---|---|
| `pipeline.py:728-734` | 寫三鍵＝0 | Task 3.3 要點 2 **明示刪除**；修改檔含本檔 |
| `test_gap3_split_blocked.py` | 斷言 `execution_mode`／`split_plan is None`／表產出／ci；**無**三鍵 assert（`:72-118`） | **不紅**（否證 brief assumed） |
| `test_pipeline.py:82` | `n_train+n_test+n_purged==5` | 走 `run()` 切分路徑，**不**經 `run_event_study_only` ⇒ 不受影響 |
| `EventTablesPanel.tsx:352` | `fmt(s.n_train,0)` 等 | 缺鍵→「—」不崩；Task 3.3 要點 4 改為 unavailable 時**禁顯示**計數列 |
| 既有 vitest mocks | `gap3_event_tables.test.tsx:14` 等硬編碼三鍵 | mock 自給自足；新檔 `EventTablesPanel.test.tsx` 由 Task 3.3 驗證命令建立（目前不存在＝預期） |

**會紅、且 v3 已列進範圍的**：Task 3.3 新增之 `test_splitunify_event_study_only.py`（兩 reason 皆 `"n_test" not in summary`）＋ vitest 兩 reason 文案。L3 與新 reason **共用新形狀**已寫明，避免「只改新 reason、L3 仍寫 0」。

### 4. G-5 四項 oracle 現在夠不夠可執行？

| 項 | 判定 | 依據 |
|---|---|---|
| ① row fingerprint | **夠** | exact sha256 of `(position, feature_ts_ms, symbol, base_universe_hash)`；失敗指名首個 mismatch position；`SplitPlan` 已有 `base_universe_hash`／`symbol`（`contracts.py:389-390`） |
| ② assignments／purged IDs | **夠** | 獨立 oracle＝`feature_index[plan.row_index]`；互斥＋涵蓋＋reason 字面；失敗輸出 diff event_id |
| ③ answer-window 完整性 | **夠** | 逐 test 事件 `label_start_ms`／`label_end_ms` 兩端在 source bars 存在；缺／跨界⇒purge＋event_id（事件列已有這兩欄，見 `alignment.py`／`dedupe.py`） |
| ④ leakage negative | **夠** | 合成 fixture 推進 `label_end_ms`⇒必進 purged；拿掉斷言⇒mutation rc=1 |

每項綁 nodeid／freeze 子模式（SPEC §G G-5；TODO Task 2.3 要點 4）。相對 v2「只列名」已可派工。

### 5. v3 有沒有引入新的自相矛盾？（介面可執行性掃描）

**R2 抓到的 D7／D8 已閉合；本輪掃描結果：無新的 P0／P1 級介面不可執行。**

| 檢查 | 簽名／落點是否具備 | 判定 |
|---|---|---|
| 禁呼叫 `_normalize_ic_time_index`；自做 ms 歸一 | C-4／Task 2.2 要點 3 明文；函式 `:269-271` 仍拒 ms | **閉合**（不再要求復用會 raise 的函式） |
| `bucket_ms` 進投影 | C-4 簽名有 `bucket_ms`；`build_time_clusters(manifest, bucket_ms)` | **閉合** |
| embargo 須 None 否則 raise | C-5／Task 2.2 要點 7：**呼叫端 Task 3.1**，不在投影內 | **規則閉合**；但 Task 3.1 實作要點／驗證**未複列**該檢查 → 見 **P2-01**（不擋 B1） |
| `holdout_boundary(feature_index,…)` vs 既有 `holdout_*(n_rows,…)` | 要點 1：以既有函式定義自身（`n=len(feature_index)` 即可） | **可執行** |
| `estimand_scope` 放入 `common` | 驗收斷言清楚；「沿用 estimand_note 模式」之**檔案:行誤引** → 見 **P3-01** | **驗收可執行**；引用漂移不擋 |

### 6. 批次拆分後的依賴鏈是否正確？

**正確：B2a→B2b→B2c→B3。**

| 邊 | B2b／B2c 需要上游的什麼 | 有無錯批 |
|---|---|---|
| B2a→B2b | 生產語意上 `SplitPlan` 應來自 `holdout_boundary`；B2b 單測可合成 plan，但 gate 分開避免「有投影無同源邊界」半套放行 | 無 |
| B2b→B2c | G-1／G-3b／G-5 要比對投影產出；無 `derive` 則 golden 無標的 | 無 |
| B2c→B3 | 接線前先凍 oracle，避免接線與首次凍結糾纏 | 無 |
| Task 3.3 與 3.1 同批 B3 | 分派／刪鍵／UI 與接線同批，避免「已接線但仍顯示假 0」窗口 | 無；3.2 fail-closed 同批合理 |

未發現 Task 放錯批。

### 7. 殘留清單是否誠實？

| ID | 類別 | 判定 |
|---|---|---|
| R-1 | needs-research | **誠實**——`base_universe_hash` 多標的語意未定；先 fail-closed |
| R-2 | blocked-by | **誠實**——待 G-3a 實跑才有差集數字 |
| R-3 | user-ruling | **誠實**——UAT 一律最後 |
| R-4 | blocked-by | **誠實**——`extract_event_patterns` 無 caller |
| R-5 | needs-research | **誠實**——跨棧 `features_run_id` 超出本票；委員會裁定 event-study-only。非偷懶：探針已否證「共用公式即可」 |
| SU-RESID-1 | needs-research | **誠實**——attribution checker 語意對應屬治理工具研究 |

無「其實現在就能做卻掛殘留」項。

---

## §1 十一類速掃（無則標無）

1. 矛盾／互斥：R2 之 D2／D7／D8 已修；殘留見 P2-01／P3-01（不擋 B1）  
2. 漏項／端到端：C-0→Task 3.3 含前端；Task 4.1 覆蓋 IC 報告——無新漏  
3. 不可測驗收：G-5／deselect／方向性清單／ms_same_source 皆有命令——無  
4. 可疑 quant 假設：D1 降級為 study-only 已標 R-5；containment 未證⇒不刪 guard——無新  
5. 過度工程：無  
6. OOM／並行：無  
7. Cache：無  
8. API／型別：capability／estimand_scope 有契約化字面——無  
9. 測試品質：mutation 12 條＋兩 reason 回歸——無  
10. Agent 可執行性：見 P2-01（Task 3.1 checklist 缺口）  
11. 必要性／短命工：Task 1.3 清單存活至 REDSWEEP——已標；無白工

## 被當成事實的未驗證假設（§0）

- brief assumed「`test_gap3_split_blocked.py` 斷言三鍵」→ **本輪否證**（見必答 3）。  
- brief「我沒查的」：`EventTablesPanel.test.tsx` 不存在→ Task 3.3 驗證命令即建檔契約，**非**漏項。  
- `tables.py:598-599` estimand_note → **誤引**（見 P3-01）。

---

## GROK-R3-P2-01

**斷言**: C-5／Task 2.2 要點 7 把「`EventSplitConfig.embargo_ms`／`embargo_ms_by_symbol` 須為 `None` 否則 raise」的落點指定在 Task 3.1 接線處，但 Task 3.1 的實作要點（僅 1–3）與驗證 (A)–(D) **都未列入該檢查**——B3 實作端只讀 Task 3.1 時會漏做。

**碼證**: SPEC C-5（約 L196-201）與 TODO Task 2.2 要點 7 明文「住呼叫端（Task 3.1）」；對照 SPEC／TODO Task 3.1 實作要點只有 holdout_boundary 接線／pipeline 選填／`split_events` 呼叫點＝0，驗證無 embargo None 之 pytest nodeid。RECHECK：`awk '/Task 3.1 —/,/Task 3.2 —/' docs/SPLITUNIFY_SPEC.md` 與同段 TODO。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf

[MAJOR] 信心度=High；**不擋 B1**（B1 不動生產碼）。會怎麼失敗：B3 接線後仍可能靜默忽略上游 `embargo_applied`（EVTLABEL 已踩過的形態），且無 mutation／驗收命令會紅。  
**修法**：Task 3.1 實作要點增「投影路徑呼叫前 assert config.embargo_* is None」＋一條 `-k embargo_must_be_none`；可施工前小補進 SPEC／TODO，不必 R4。

---

## GROK-R3-P3-01

**斷言**: Task 3.3／C-0 決議③(b) 寫「沿用 `tables.py:598-599` 之 `estimand_note` 模式」，但 `tables.py` 僅 371 行、該模式實際在 `pipeline.py:598-599`（且掛在 all-bars 表，不是 `event_forward_return_table["common"]`）。

**碼證**: `wc -l momentum/Analysis/event_samples/tables.py` → 371；`pipeline.py:598-599` 有 `rep["estimand_note"]=...`；`event_forward_return_table` 之 `common` 來自 `tables.py:130-151` `_common_constraint_block`（L279 掛上）。驗收句 `event_forward_return_table["common"]["estimand_scope"] == "full_sample_not_oos"` 本身可執行。RECHECK：對上述行號 `sed -n`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf

[MINOR] 信心度=High；**不擋 B1**。失敗模式：Agent 搜 `tables.py:598` 找不到而短暫迷惑；依驗收斷言仍會改對 `_common_constraint_block`／common。  
**修法**：把引用改為「沿用 `pipeline.py:598-599` 之揭露欄位模式，欄位寫入 `_common_constraint_block`」。

---

STATUS: DONE
