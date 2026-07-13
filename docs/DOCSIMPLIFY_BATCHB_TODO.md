# 文檔簡化批次 B TODO　（版本 DRAFT / 基於 docs/DOCSIMPLIFY_BATCHB_SPEC.md v2r14 / 2026-07-13）

> 冷啟動執行端只讀本檔+SPEC 即可逐 Task 執行。reconcile 已三家戳記 PASS（handoffs/DOCSIMPLIFY-B-RECONCILE.md, hash ba01cbc7）。

## §0 全域規則與約束（執行端讀完即可遵守）

- **純文件治理，不改程式邏輯**。RISK-HIT: b（跨模組導航面）。
- **Writable allowlist（SPEC §C，越界→BLOCKED 申請）**：`docs/DEVELOPMENT_GUIDE.md`、`docs/ARCHITECTURE.md`（僅 `## 解耦架構原則` 節+其 TOC 條目;他節 TOC 含 `#feature-factory-架構` 凍結）、`docs/DOCSIMPLIFY_BATCHB_MANIFEST.md`、`docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`、`docs/DOCSIMPLIFY_BATCHB_ARCHVIEW.md`、`scripts/check_doc_manifest_b.py`+其 fixtures。**唯讀**：API_SPEC/CLAUDE.md/TGF/check_doc_anchors.sh。
- **凍結（機檢）**：DEV `## 長時間任務與 API 生命週期` 節正文 L1246-1325 content-hash（B0 修節內 fence 後重取基準）;ARCH `## Feature Factory 架構` 整節;TGF 兩 anchor（checker `--files` 含 TGF+雙 H2 恰一斷言）。
- **fence parser 單一語意=lang_push**（` ```lang `=push、裸 ` ``` `=pop;禁 toggle）——所有 gate/validator/inventory 共用同一函式（SPEC §V）。
- **禁**：為湊行數刪資訊（行數=telemetry）;新增內容型 appendix/新真相源檔（治理產物例外）;放寬既有測試斷言（diff 斷言驗收）;無 manifest disposition 的刪除。
- 引用 SPEC §A manifest ID：[FACT-fence9]（9 處損壞 selector `^(typescript|python)[^ ]`）、[FACT-meta]（L1326-1405 錯置塊）、[FACT-d2gap]（API_SPEC 欄位缺口）、[D1]（八章+First Principle 範圍）、[D2]（先保全後刪）、[D3]（行數 telemetry）、[D4]（不新增 appendix）——原文見 SPEC §A，不整段複製。

## §B 批次執行策略（依賴拓撲 → 最少批次）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| BB-1 | **先 B00.3(parser/validator)→再 B00.1(import 同一 parser 產 view+manifest)→B00.2** | 無 | 同為只讀盤點+工具;內部順序強制,禁 parser 重複實作 | 大 |
| BB-2 | B0.1 | BB-1 review-lock | 單 Task 修損壞,byte gate 獨立 commit | 小 |
| BB-3 | B1.1 | BB-2 | DEV 壓縮單檔 | 大 |
| BB-4 | B2.1 | BB-1（與 BB-3 異檔可並行,但派工序列化以簡化驗收） | ARCH 解耦節單檔 | 中 |

- **派工前置 gate(每批派工前主委必跑)**：`bash scripts/reconcile_stamps_check.sh handoffs/DOCSIMPLIFY-B-RECONCILE.md codex,composer,grok` exit 0(STAMP-BLOCKED 防線)。
- 批次間 Gate：BB-1→BB-2=兩家 review-lock PASS;BB-2→BB-3=`diff docs/DEVELOPMENT_GUIDE.md docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`==0+anchor checker exit 0;BB-3/BB-4 完=validator post-state exit 0+§V 全套。
- 每 Batch 派工 prompt=本檔對應 Phase 全文+SPEC 檔名（gate.sh dispatch --spec --todo）。

## Phase B00 — 只讀盤點+工具（目標：刪前授權基礎全落地;完成後 repo 多四個治理產物,零既有 doc 改動）

### Task B00.1 — target view + ARCH view + disposition manifest
- SPEC ref：Task B00.1（L51-70）　目標：建立刪除授權與比對基準。
- 輸入：`docs/DEVELOPMENT_GUIDE.md`(baseline HEAD)、`docs/ARCHITECTURE.md`。
- 輸出：
  1. `docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`=baseline DEV 依序套：①9 處 [FACT-fence9] fence 修復（語言標記與碼首行分離+補 fence）②L2373-2387 硬體節結構修 ③刪 L1326-1405（含其內 4 個無 pop language fence）④長任務末段/L1259 補閉（若①③後仍 unclosed）。構造後**機檢**：lang_push unclosed==0、nested==0、Python/前端/註釋/測試四章 H2 fence 外可見、FA H2 集=22——任一不滿足=FAIL 重做。每步記入 manifest 附錄「施工圖」（行級可重放編輯步驟表）。
  2. `docs/DOCSIMPLIFY_BATCHB_ARCHVIEW.md`=ARCH `## 解耦架構原則` 節 baseline 原樣快照。
  3. `docs/DOCSIMPLIFY_BATCHB_MANIFEST.md`：範圍=[D1] DEV 八通用章（代碼質量/日誌/錯誤處理/LLM Coding/性能優化/Python/前端/註釋）+First Principle 章+ARCH 解耦節，對 **view 檔** 之**範圍內(=D1 八章+First Principle ∪ ARCH 解耦節;本批不動章不入表,防擴權)** 逐 **H2 章塊/H3/H4/表格/碼塊** 列：`ID | 原 heading | content-hash(必填)+line-span(輔助,基準=view 檔) | 分類{刪|壓縮留|原樣留} | 承載(**壓縮留必填三元組 `source ID → post-state ID → INV-xx 錨句`**;刪/原樣留填 N/A+註明) | 理由`;缺三元組之壓縮留列=validator exit 1。分類決策表與點名必留 8 項照 SPEC L56-68 逐字執行（誤標刪=FAIL）。含「被吞 heading 重現集」（=target_FA − raw_baseline_FA 扣授權刪除區,機器演算）。
- 實作要點：≥3——(a) 用 python 單一 lang_push parser 函式（後續 validator 共用同一實作,置於 `scripts/check_doc_manifest_b.py` 內 import）;(b) block ID=`<原檔名>::<heading path>::<類型+序號>`（同名 -1/-2 消歧）;content-hash=去行尾空白+換行統一 \n+檔尾單換行後 sha256;(c) heading block=fence 外 heading 行起至下一 fence 外 heading 前（fence 內 204 個 `# comment` 不作邊界）。
- 修改檔案：僅新增上列三檔（manifest/兩 view;validator 及其 tests 屬 B00.3 輸出）。既有 caller：無。
- 不可做：改任何既有 doc;無 manifest 就標記刪除;由修復後結果反推重現集。
- 邊界：①同名 heading 兩處（如重複 `### 範例`）→ -1/-2 消歧且 hash 不同塊;②授權刪除區內 4 個被吞 heading→不入重現集、不入 pre 集（SPEC oracle 公式 `authorized_raw ∩ pre_fence_aware`=空集仍成立）。
- 風險緩解：⊘（只讀+新檔）。
- 驗證：target view 機檢四條件全過（附 parser 輸出 receipt）;manifest 經 B00.3 validator coverage 模式 exit 0（missing/duplicate/hash-mismatch 全空）;點名必留 8 項全非「刪」（grep receipt）;≥5 代表塊供委員 calibrate。

### Task B00.2 — 錯置區塊欄位級驗真+保全
- SPEC ref：Task B00.2（§P,L76-80）　目標：D2 先保全後刪的存證。
- 輸入：DEV L1326-1405 錯置塊、`docs/API_SPECIFICATION.md`、runtime truth 鏈（`api/main.py` mount ~L203-206→`api/routes/case_search.py` ~L31/L132-148→`api/models/responses.py` **TaskProgress** L35-41）。
- 輸出：欄位級 mapping 表+缺口欄位契約全文復刻（併入 manifest 附錄）+BLOCKED-scope 申請清單（含 `current/total` vs `current_step/total_steps` 命名裁決需求）。
- 實作要點：(a) 錯置塊逐欄位列（**以實際列出欄位數為準,附計數 receipt**,勿抄任何預設數）;(b) 每列雙 receipt=`rg -n <欄名> docs/API_SPECIFICATION.md`+truth 鏈檔行號;(c) 命中 `api/services/task_manager.py` 等他處=標「非本 endpoint」不算數。
- 修改檔案：manifest 附錄（同 B00.1 檔）。既有 caller：無。
- 不可做：泛 `rg api/`;把錯置草稿欄位直接當應補契約;改 API_SPEC。
- 邊界：①欄位在 API_SPEC 有但 schema 不同（`current_step` vs `current`）→列 drift 待裁決,非缺口非已在;②三態分類:API_SPEC 無+runtime 有=缺口(保全+BLOCKED-scope)/API_SPEC 有+語意不同=drift 待裁決/兩邊皆無=錯置草稿虛構欄(刪,不保全)。
- 風險緩解：[FACT-d2gap] 保全先於刪。
- 驗證：mapping 欄位數==錯置塊實列欄位數（計數 receipt）;缺口保全附錄與正文 `diff`==0（逐字複刻）。

### Task B00.3 — `scripts/check_doc_manifest_b.py` validator + fixtures
- SPEC ref：§P B00.1 驗證段+§V（L69-73/L99）　目標：manifest 機檢工具。
- 輸入：manifest+兩 view 檔。輸出：`scripts/check_doc_manifest_b.py`+`tests/docs_tooling/test_check_doc_manifest_b.py`+`tests/docs_tooling/fixtures_b/`（獨立於批次 A fixtures）。
- 實作要點：(a) coverage 模式=三參（manifest,DEV view,ARCH view），對 view 取**範圍內(=D1 八章+First Principle ∪ ARCH 解耦節)全類別(H2/H3/H4/表格/fenced)** block 與 manifest 比對;**block ID 檔名段一律原檔名**(`DEVELOPMENT_GUIDE.md`/`ARCHITECTURE.md`),view 僅取塊來源，missing/duplicate/hash-mismatch 任一非空 exit 1;(b) `--post-state` 模式=block ID 檔名段映射讀 live `docs/DEVELOPMENT_GUIDE.md`/`docs/ARCHITECTURE.md`，四項機檢：雙向刪除等式（標刪塊 live 必不存在+live 刪除⊆manifest{刪}）/「原樣留」live hash 不變/「壓縮留」INV 錨句限定於綁定 post-state block 內 rg≥1/新增封閉（live−baseline IDs ⊆ 預登記 post-state IDs;壓縮 source ID 消失=mapping 內授權）;(c) parser/normalization 函式與 manifest 產製共用（單一實作）。
- 修改檔案：新增上列兩處。既有 caller：無。
- 不可做：動 `scripts/check_doc_anchors.sh`;弱化為 heading-line-only hash。
- 邊界：①空白/換行差異→同 hash（normalization fixture）;②同 ID 正文改寫丟 INV 錨句→post-state exit 1。
- 風險緩解：⊘。
- 驗證：≥10 fixture 全過且可證偽——漏列/重複 heading/hash 不符/空白同 hash/換行同 hash/正文被改 mismatch/篡改 live 原樣留/未授權刪除/授權刪除故意保留/新增未登錄 block/**INV 錨句移至非綁定 block(全域 rg 仍命中)→exit 1**/**綁定 block 內丟錨句→exit 1**（後六項必 exit 1,附實跑 receipt;共 ≥12 fixture）;`pytest tests/docs_tooling/ -q` 全綠（批次 A 11 tests 不回歸）。

### Phase B00 測試+Gate：validator coverage exit 0;target view 四條件機檢;fixtures 全過。**Gate=composer+grok review-lock 雙 PASS**（實作端 Codex 不自審）。

## Phase B0 — 修損壞（目標：DEV 與 target view byte 一致;完成後 DEV 無損壞 fence、錯置塊消失）

### Task B0.1 — 依施工圖修復
- SPEC ref：Task B0.1（L84-85）　目標：DEV=target view。
- 輸入：B00 施工圖+TARGETVIEW。輸出：修復後 `docs/DEVELOPMENT_GUIDE.md`+TOC 同步。
- 實作要點：依施工圖四步逐一執行（①fence 分離補閉 ②硬體節修 ③刪錯置塊+假 H2 ④補閉）;TOC 刪假 H2 條目。
- 修改檔案：`docs/DEVELOPMENT_GUIDE.md`。既有 caller：TGF anchor（`#長時間任務與-api-生命週期`,由 check_doc_anchors.sh exit 0 確認不斷）。
- 不可做：任何施工圖外的內容變動（byte gate 會抓）;動 L1246-1325 正文（僅節內 fence 修屬施工圖步驟）。
- 邊界：①修復後原被吞 heading 重現→須 ⊆ 重現集（機檢）;②TOC 行號/條目與正文 H2 同步（anchor checker 驗）。
- 風險緩解：atomic commit 可 revert;B0 獨立成立（缺口已保全）。
- 驗證：**主 gate `diff docs/DEVELOPMENT_GUIDE.md docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`==0**;再確認：selector==0、`grep -c '^## GET /api'`==0、lang_push unclosed==0+nested==0、heading 差分 oracle（SPEC L85 公式）、`expected_target_H2_set`(22)==live FA H2 集、anchor checker（含 TGF）exit 0;長任務節修後重取 hash 記入 manifest。

### Phase B0 測試+Gate：上列全過+composer/grok review 雙 PASS。

## Phase B1 — DEV 八章壓縮（目標：通用教條→3-8 條 invariant+pointer+≤1 正反例;First Principle 170→~30）

### Task B1.1 — 依 manifest 壓縮
- SPEC ref：Task B1.1（L88-90）　目標：壓縮不失契約。
- 輸入：LOCKED manifest+B0 後 DEV。輸出：壓縮後 DEV。
- 實作要點：(a) 逐章依 disposition——「刪」刪、「壓縮留」改寫為 INV-ID 條列（錨句字面保留!）+pointer+≤1 正反例、「原樣留」不動;(b) needles（SPEC §V **L104** needles 表：可重試/不可重試/循環內大量log/硬體自適應/L0|L1|L2/真實 kline/sanitized 等）錨句字面必須保留可移位;(c) 壓縮塊 post-state ID 須在 manifest mapping 預登記內。
- 修改檔案：`docs/DEVELOPMENT_GUIDE.md`（八章+First Principle 範圍;其餘章不動）。既有 caller：TGF anchor 不動。
- 不可做：動長任務節（hash 凍結）/數據真實性章/測試規範章/其餘非範圍章;刪 needle 錨句;登記外新增 block。
- 邊界：①「壓縮留」章內混有「原樣留」子塊→子塊原文保留嵌入;②正反例超過 1 組→只留 manifest 指定那組。
- 風險緩解：validator post-state 四項+needles。
- 驗證：`python scripts/check_doc_manifest_b.py --post-state docs/DOCSIMPLIFY_BATCHB_MANIFEST.md docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md docs/DOCSIMPLIFY_BATCHB_ARCHVIEW.md` exit 0（四項全過）;§V needles(SPEC §V L104 表) DEV 條逐一 rg≥1;anchor checker exit 0;長任務節 hash 不變;DEV 新增假綠裸命中==0;行數 telemetry 記錄。

### Phase B1 測試+Gate：上列+composer/grok review 雙 PASS（含 manifest diff 對抗抽驗）。

## Phase B2 — ARCH 解耦節收斂（目標：枚舉→pointer,契約全留）

### Task B2.1 — 依 manifest 收斂
- SPEC ref：Task B2.1（L93-95）　目標：Protocol/Factory 長清單→pointer（protocols.py/factories.py 權威），CLAUDE.md 重複枚舉→pointer。
- 輸入：LOCKED manifest+ARCHVIEW。輸出：收斂後 ARCH 解耦節+TOC（僅本節條目）。
- 實作要點：(a) 依 disposition 執行;(b) 點名留=誠實現況表（R2=5/R3=12/R4=1、R8 殘留）+scanner 編號語意差+V2/V3 why 三條+Artifact Contract Table+呼叫流程圖 L349-364;(c) `0 violation` 命中維持恰 2 處且在 scanner-pointer 表內。
- 修改檔案：`docs/ARCHITECTURE.md` 解耦節。既有 caller：`#解耦架構原則` anchor（TGF 第三列指向,不得改 H2 名）。
- 不可做：動 FF H2 節/他節 TOC 條目;刪點名留項;新增假綠裸命中。
- 邊界：①誠實現況表行號因收斂漂移→內容保留即可（needle 驗內容非行號）;②pointer 指的 protocols.py/factories.py 符號→抽 3 個實跑 rg 驗真存在。
- 風險緩解：validator post-state（ARCH 側）。
- 驗證：`python scripts/check_doc_manifest_b.py --post-state docs/DOCSIMPLIFY_BATCHB_MANIFEST.md docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md docs/DOCSIMPLIFY_BATCHB_ARCHVIEW.md` exit 0;§V needles(SPEC §V L104 表) ARCH 條逐一 rg≥1;`rg -n '0 violation' docs/ARCHITECTURE.md` 恰 2 處且於解耦節表內;anchor checker（DEV,ARCH,TGF）exit 0+FF/長任務 H2 恰一;TOC diff 斷言他節條目不變;行數 telemetry。

### Phase B2 測試+Gate：上列+composer/grok review 雙 PASS。全批完成後：§V 全套重跑+`bash scripts/check_decoupling_phase4.sh` exit 0+`pytest tests/docs_tooling/ -q` 全綠;view 檔此時才可刪（或保留供審計）。

---
### 階段 4 handoff
SPEC=docs/DOCSIMPLIFY_BATCHB_SPEC.md TODO=docs/DOCSIMPLIFY_BATCHB_TODO.md FOCUS=manifest 分類授權完整性+validator 可證偽性+批次 A 產物凍結
（Internal Frozen;待 adversarial review 過後 Frozen。）
