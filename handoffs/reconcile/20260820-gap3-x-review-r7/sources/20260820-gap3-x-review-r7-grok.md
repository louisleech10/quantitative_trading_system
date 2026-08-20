# GAP-3 TODO 對抗審 R7（抄寫漂移）— grok

family: grok  
task-id: 20260820-GAP3-X-REVIEW-R7  
scope: `docs/GAP3_EVENT_TODO.md` @ `de9623a4`（sha256 `511c3f1b3b84…`）；權威對照 `docs/GAP3_EVENT_SPEC.md` FROZEN（sha256 `544c2922ef2e…`）；禁改碼  
brief: `handoffs/20260820-gap3-todo-adv-r1-brief.md`  
index: `handoffs/20260820-gap3-todo-stage1-index.md`

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| fact-verified: §V M1–M12 與 SPEC §V 370–382 byte-identical | **fact-verified（本輪重跑）** | `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \*\*mutation 條件\*\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → 空輸出，`diff_rc=0` |
| fact-verified: `survivor_contract.py`／`strategy_validation/{pbo,min_btl}.py`／`tests/golden/la0/inputs/`／`ichc_run.run_analyze` 存在 | **fact-verified（本輪重跑）** | `ls` 四路徑皆在；`grep -n 'def run_analyze' tests/momentum/helpers/ichc_run.py` → L30 |
| fact-verified: `doc_format_precheck.sh` TODO rc=0 | **fact-verified（本輪重跑）** | `bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0 |
| assumed: B2 批內序 B2.1→B2.2→〔§G 凍結〕→B2.3→B2.4→B2.5 與「B2.4 升版前不得寫 v2 payload」＝主委推導 | **攻後＝大半有 SPEC 錨，屬合法細化** | 凍結時機＝SPEC §G「B2.3 動工前」明文；「先升版再寫 payload」＝SPEC B2.4／FACT-RECEIPT `additional_properties:false` 明文，非純推導。B2.5 置於 B2.4 後＝編號序序列化，B2.5↛B2.4 依賴，不增行為、不砍並行可能 → 不升級 finding |
| assumed: §G-1「import `gap2_canonical_sha`、不另立 scrub」滿足 SPEC「TODO 列細目」 | **攻後＝成立** | TODO Phase B2 前言列 ①`marginal_ic` ②`survivor_output` ③時戳/路徑鍵 ⑤`scope_id`；對照 `scripts/gap2_freeze_golden.py:11-17` 一致；「不另立」＝復用唯一序列化實作，避免另表漂移 |
| assumed: `ic_feed.py`／`generator.py`／`pipeline.py`／`types.py`／`create_event_sample_pipeline()`／`AlignmentReceipts` 兩層＝V13 細化非改規格 | **攻後＝成立** | SPEC §RISK 末行明文「`create_event_sample_pipeline()`…TODO 階段定簽名」；兩層收據欄＝SPEC D2-4 事件級＋per-TF；其餘檔名＝新建模組之 V13 授權落點，未改驗收語意 |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 544c2922ef2ea09fe21bd6fda514f07e51a7f90f7f78c6409bfe38a7ccd23699
shasum -a 256 docs/GAP3_EVENT_TODO.md
→ 511c3f1b3b8409b13521c9cc12ad4bcac01c61d10093e07dae22ca5711a1fdc9
git log -1 --oneline -- docs/GAP3_EVENT_TODO.md → de9623a4 docs(gap3): TODO v0.1 DRAFT…
diff …SPEC 370-382… vs …TODO mutation… → empty, rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md → rc=0
```

---

## 1. 二十 Task 抄寫漂移比對（brief 必答 1）

| Task | 漂移？ | 摘要 |
|---|---|---|
| B1.0 | **有** | 見 P1-02：`direction`「匯入批內單值」未落地；其餘必填/選填/條件必填/分類 config/驗證①–⑤／邊界／不可做／存活／覆蓋與 SPEC 對得上（契約字面 pointer SoT） |
| B1.1 | **有** | 見 P1-01：D2-1 三段鏈＋D1-6＋§G-2 驗證已抄；**漏** D2-2／AR-1 `decision_at ≤ t0_open_ms` |
| B1.2 | 無 | 檔案／policy／驗證 ASSERT／邊界／不可做一致 |
| B1.3 | 無 | purge／`cluster_weight=1/n`／macro·micro／`atol=1e-12`／不改 `SplitPlan` 一致 |
| B1.6 | 無 | 連續物化／as-of／`atol=1e-12`／因果 invariant／禁固定窗 一致；批內序在 B1.3 後 B1.4 前＝SPEC |
| B1.4 | 無 | `N_perm=1000`／三道硬檢／置亂＋PIT ASSERT 一致 |
| B1.5 | 無 | 公式／四門檻 `0.05/0.0/0.01/0.05` example_default／boundary ±1e-9／不回寫 一致 |
| B2.1 | 無 | D1-6 entry／多 horizon config 化／cluster CI／禁合併總分 一致 |
| B2.2 | 無 | OOS only／`counterexample_kind_effective` 分層／置亂沿 B1.4 一致 |
| B2.3 | 無 | `label_value` 條件必填／A′ 透傳／§G-1 `--check`／禁寫 v2 payload 至 B2.4 前＝SPEC 錨 |
| B2.4 | 無 | 六擴欄字面／顯式版本判別／路徑 `survivor_contract.py` 實測補正 一致 |
| B2.5 | 無 | D4 分母／基率並排／M4 ASSERT／D4-4 不做清單 一致 |
| B3.1 | 無 | AST／角色／digest／future→feature ASSERT 一致 |
| B3.2 | 無 | G1–G6／G6 呼叫 B2.5／`platform_same_trigger_rule` 一致；`generator.py`＝細化 |
| B3.3 | 無 | 五算子落點 `state_counters.py`／因果測試 一致 |
| B4.1 | 無 | train/test 隔離／不改 ML 殼／共同約束 一致 |
| B4.2 | 無 | ledger／AUC↛DSR ASSERT／消費 pbo·min_btl 一致 |
| B5.1 | 無 | legacy 顯式拒／驗證唯一在 momentum／factory 出口＝SPEC 授權細化 |
| B5.2 | 無 | 三頁／兩表僅事件模式／不另開頁 一致 |
| B5.3 | 無 | 目標含 ROADMAP；TODO 補 `docs/ROADMAP.md` 入修改檔＝補 SPEC 檔案列缺口，非越權 |

數值／枚舉抽驗（門檻四值、`N_perm=1000`、seed `20260820` 於 §V fixture、`atol=1e-12`、三段鏈、D1-6 五值映射）— **與 SPEC 一致，無改寫走樣**。

---

## 2. §V M1–M12（brief 必答 2）

**逐字一致：是。**  
RECHECK（本輪）上述 `diff` 空輸出，`diff_rc=0`。歸屬列 B1＝8／B2＝3／B3＝1 與索引 §4 一致。

---

## 3. TODO 新增內容合法性（brief 必答 3）

| 新增 | 判定 |
|---|---|
| B2 批內序＋凍結插隊 | 合法細化（§G＋B2.4 有錨；見前提表） |
| §G-1 復用 `gap2_canonical_sha`、不另立 scrub | 合法細化且滿足「列細目」 |
| `ic_feed`／`generator`／`pipeline`／`types`／`AlignmentReceipts`／`create_event_sample_pipeline` | 合法 V13／SPEC 授權細化 |
| B5.3 顯式改 `ROADMAP.md` | 合法（SPEC 目標已寫同步 ROADMAP） |
| 本輪自找之漏抄（P1-01／P1-02） | **非合法細化**＝SPEC 有、TODO 改法未落地 |

---

## 4. V13 深度紅線與錨點（brief 必答 4）

- 錨點：`## §0`／`## §B`／20×`### Task` 皆含 驗證／邊界／不可做／**存活至**／**覆蓋風險**（本輪 python 掃描 20/20 miss=∅）。
- 深度：每 Task 實作要點 numbered≥3；絕大多數含 `def`／`::` 簽名。B2.4／B5.2／B5.3 無 `def` 碼塊但有檔案＋步驟＋可執行驗證 — 可接受。
- 獵空殼：驗證欄皆含 rc=0／exact／ASSERT／atol 等 token，**未見**「確認正確」式空話。
- §0 含解耦 R1/R5/R6/R7＋白名單＋NaN 不弱化＋防假綠 — 過。
- 殘差：標題宣稱「不必回讀 SPEC」，§0-13 又要求回查 D 系列原文 — 與 P1-01 同源張力（見下）。

---

## 5. 冷啟動可執行性（brief 必答 5）

多數 Task（B1.2–B1.6、B2.*、B3–B5）單檔可開寫。  
**例外**：B1.1 若只跟 Task 內偽碼、不打開 SPEC D2-2，會漏 `decision_at ≤ t0_open_ms`；B1.0 若只跟「值集與型別全在檔內」而未讀 SPEC 必填括註，會漏 `direction` 匯入批內單值。→ 冷啟動 **未完全** 達 V13 紅線。

---

## 6. 可否 Frozen（brief 必答 6）

**不可直接 Frozen。** 無 P0 BLOCKING，但有 **2×P1 MAJOR** 抄寫漏項，須修進 TODO 後再進 freeze／戳記。Verdict＝需修補後派工。

---

## §1 十一類（無問題標「無」）

1. 矛盾/互斥：無（B2.4 升版前禁寫 payload 與 B2.3 接線可並存；§G 凍結點一致）  
2. 漏項/端到端：有 — P1-01／P1-02（其餘 20 Task 鏈完整）  
3. 不可測驗收：無  
4. 可疑 quant 假設：無（門檻 example_default／置亂 CI／固定分母皆沿 SPEC）  
5. 過度工程：無  
6. OOM/並行：無（萬級牆鐘屬偵察待辦，已標）  
7. Cache 正確性：無（本票新建路徑；§G-1 復用 scrub）  
8. API/型別/相容：無（B5 legacy 顯式拒；survivor v1 顯式判別）  
9. 測試品質：無（mutation／golden／boundary 具名）  
10. Agent 可執行性：有 — 同 P1-01／P1-02  
11. 必要性/短命工：無（存活至／覆蓋風險欄語義與 SPEC 一致；B1.4→B2.2 超集不刪載體）

## 被當成事實的未驗證假設（§0）

無新增。brief 三條 assumed 經攻後兩條成立、一條「大半有錨＋合法序列化細化」。

---

## Verdict：需修補後派工

修 P1-01／P1-02 後可再進對抗收斂／Frozen；其餘 assumed 細化與 M1–M12／數值枚舉 **無** 阻擋項。

---

## GROK-R7-P1-01

**斷言**: TODO Task B1.1 推導偽碼列了 D2-1 三段鏈與 D1-6，但未落地 SPEC D2-2／AR-1 要求的獨立不變式 `decision_at ≤ t0_open_ms`，冷啟動 agent 只讀 TODO 會漏做該 validator 檢。

**碼證**: SPEC `docs/GAP3_EVENT_SPEC.md` D2-2（約 L37）「validator 增 `decision_at ≤ t0_open_ms`」；AR-1（約 L82）同文。TODO B1.1（L84）偽碼不變式集合＝PIT／label／持有三段鏈＋`entry_after_label_start`＋as-of cutoff，全文 `grep t0_open|decision_at ≤ t0` 於 TODO → **0 命中**。§0-13 對 D2 的摘要亦只寫「三段鏈＋兩層收據＋失敗枚舉」，未點該檢。RECHECK：`grep -n 't0_open\|decision_at ≤ t0' docs/GAP3_EVENT_TODO.md` 須出現於 B1.1 改法／驗證。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MAJOR] 信心度=High。會怎麼失敗：執行端按偽碼實作對齊時不寫 `decision_at ≤ t0_open_ms` 守恆檢（推導式在 k≥0 時雖常自然成立，但缺防 regress／缺 bar 錯錨時的 loud 拒）；與「D2 全落地」／AR-1 不符。修法：在 B1.1 偽碼三段鏈旁顯式加入該檢＋對應 failures reason，並於 `test_alignment.py` 加負例。

---

## GROK-R7-P1-02

**斷言**: TODO Task B1.0 將 SPEC 必填列之 `direction ∈ {long, short}`（U1：匯入批內單值）縮成欄名 `direction`＋「值集與型別全在檔內定義」，未把「匯入批內單值」寫進改法／驗證／契約要求，屬漏抄。

**碼證**: SPEC Task B1.0 必填（約 L134）原文含「`direction ∈ {long, short}`（U1：一次只研究一向，匯入批內單值）」。TODO B1.0（L55）required_fields 列 `direction` 但無「批內單值」；驗證欄①–⑤亦無跨列 direction 唯一斷言。RECHECK：`grep -n '匯入批內單值\|批內單值' docs/GAP3_EVENT_TODO.md` 須非空，且落在 B1.0 改法或 `test_import_contract.py` 斷言描述。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MAJOR] 信心度=High。會怎麼失敗：契約 JSON／validator 只做枚舉閉集、允許同一匯入批 long+short 混入，下游 U1「一次只研究一向」與分層表假設被靜默打破。修法：B1.0 改法與驗證補「單批 `direction` 唯一值，否則拒」；字面規則可住契約檔 `_doc`／validator 規則，仍遵守不複列鍵表。

---

STATUS: DONE
