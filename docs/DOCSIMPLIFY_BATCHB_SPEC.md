# 文檔簡化 批次 B — SPEC (v2，經三家 adversarial 審修訂)

> 來源 PLAN/診斷：handoffs/DOCDRIFT-SIMPLIFY-RECONCILE.md（三家收斂+使用者定案「A+B 都做」）　|　日期：2026-07-13　|　對應 TODO：待 TODO_GENERATION_PROMPT 生成（**B00 派工前置=reconcile 戳記核可+TODO 生成**，見 §P）
> v1→v2：codex(15)+composer(4)+grok(4 類) 三家 adversarial 全 BLOCK。本版逐項修：fence gate 廢偶數改 stack 平衡/D2 欄位級驗真+保全先於刪/可刪判準複用批次 A canonical+重生命令/必留補 7 漏項/8 章範圍不擴權/content-hash 取代 line-span/拓撲寫死/anchor 保護加 TGF 斷言/假綠 allowlist 落實 file+line/manifest validator 命令化。審查檔 handoffs/DOCSIMPLIFY-B-SPECREVIEW-{codex,composer,grok}.md。
> 方法論沿批次 A（commit 7992498）：**inventory-first、manifest-gated、先修後刪**。複用 `scripts/check_doc_anchors.sh`。

## §RISK 風險分級
- **大小**：中（文件治理，不改程式邏輯；判斷面大——沿批次 A 拆「只讀 manifest review-lock 先行」）。
- **命中高風險原則**：(b) 跨模組/共用路徑——DEV 為多文件引用的 how-to 導航面；TGF 第二列指 `docs/DEVELOPMENT_GUIDE.md#長時間任務與-api-生命週期`；ARCH 解耦節為 CLAUDE.md canonical 的 how-to 層。非 (a)/(d)。
- **RISK-HIT 宣告**（機檢依據）：
RISK-HIT: b
- 未命中 (a)/(d) → §G Golden N/A（§N 登記）。等效客觀基準 = §V disposition manifest gate + anchor checker。

## §A 假設與待使用者確認
- **FACT-RECEIPT（實測,2026-07-13；v2 依三家 receipt 修正）**：
  - `wc -l docs/DEVELOPMENT_GUIDE.md → 2435`；H2=23。
  - **損壞 fence 9 處（selector 修正版）**：`grep -nE '^(typescript|python)[^ ]' docs/DEVELOPMENT_GUIDE.md → L1279/1299/1302/1307/1311/1316/1319/1384/2379`。⚠️ 無 `[^ ]` 的 grep 得 11 處,誤傷 L2327 `python --version`/L2330 `python -m venv venv` 合法 shell 行（codex/grok receipt）——**驗收 selector 一律帶 `[^ ]`**。
  - **fence 偶數≠健康（grok receipt）**：現況 ``` 計數 136=偶數,但 stack 掃描 unclosed=2、巢狀錯 27——偶數 gate 現在就假綠,v2 廢棄（見 §V）。另 composer receipt：L2373-2387 硬體節另有結構損壞,B0 一併修。
  - **錯置 meta-指示區塊**：L1326-1405 為「修文檔操作指示」誤貼正文+假 H2 `## GET /api/v1/search/task/{task_id}`(L1334)。**長任務真節正文=L1246-1325**（v2r3 邊界裁定:實讀 L1326-1333 已是 meta 指示殘渣開頭(`---`+`### 📄 docs/API_SPECIFICATION.md`+「位置3」),故凍結止於 L1325,刪除自 L1326 起——消 freeze/delete 重疊自撞,codex N1/composer receipt）。
  - **D2 欄位級缺口已實測（codex/grok receipt）**：API_SPEC 已有 `GET /api/v1/search/task/{task_id}`(L159-161 有 `current_step/total_steps/percentage/current_symbol`)；錯置塊多出 `step_description/processed_symbols/estimated_remaining_seconds/errors/warnings` 等欄位,且 runtime 用 `current/total` 與 API_SPEC `current_step/total_steps` 命名不一致——**缺口存在,已觸發 BLOCKED-scope 路徑,不得整段當垃圾刪**（見 D2 保全程序）。
  - DEV L4 規範權威 banner 存在；`## 長時間任務與 API 生命週期`=DEV L1246（批次 A 產物,TGF 指向）。
  - ARCH `## 解耦架構原則` 節=L151-551 前後；假綠命中實位=**ARCH L160(Rule 1)/L166(Rule 7) `0 violation`**（D1/D2 據實化 scanner-pointer 表內,此即 §V allowlist 的落實清單）。
  - anchor checker 已入庫（11 tests,mutation 可證偽）。
- **使用者已確認(僅此,勿擴張)**：`2026-07-12 ① 兩批都做(A+B)`；`2026-07-13 先做批次 B,完成後再研究解耦 triage`。
- **主委(Claude)設計裁決(非使用者逐字確認;reviewer 可挑戰)**：
  - D1（v2 收斂,不擴權）：**B1 壓縮範圍=上游明定八通用章**——`代碼質量規範`、`日誌規範`、`錯誤處理規範`、`LLM Coding規範`、`性能優化規範`、`Python開發規範`、`前端開發規範`、`註釋規範`——加上游 reconcile 明文的 `First Principle…` 章(170→~30)。**數據真實性規範、測試規範=原樣留**（上游明定保留）;其餘章（核心原則/Git/審查Checklist/安全/環境/硬體/持續改進/總結/長任務）**本批不動**（僅 B0 修其內損壞 fence）。壓縮判準=每類 3-8 條專案 invariant+pointer+≤1 正反例。
  - D2（v2 補保全程序）：錯置區塊處置=**先保全後刪**：B00.2 產出**欄位級 mapping 表**（錯置塊欄位 × API_SPEC 現況 × runtime 實際）→缺口欄位契約全文**先復刻進 manifest 附錄**（保全,不可逆刪除前的存證）→B0 才刪正文錯置塊;缺口清單=BLOCKED-scope 申請補 API_SPEC（唯讀不擅補）。runtime 命名以 `api/` 程式碼實跑為準,錯置草稿欄位不得直接當應補契約（codex receipt:`current/total` vs `current_step/total_steps` 不一致須先裁決再申請）。
  - D3：行數一律 **telemetry 非 pass**;hard gate=manifest coverage+link validity+contract assertion。
  - D4（v2 修措辭）：**不新增內容型 appendix/新真相源檔**;治理產物（manifest/TODO/handoffs 交接）例外。
- **待使用者確認：無**（D1-D4 走 reconcile-stamp 委員核可;委員判需使用者則升級再問）。

## §C 約束
- 純文件治理,**不改程式邏輯**。
- **Writable allowlist(執行端只准改;越界→BLOCKED)**：
  `docs/DEVELOPMENT_GUIDE.md`、`docs/ARCHITECTURE.md`(僅 `## 解耦架構原則` 節;TOC 僅准改與本節相關之條目——`#feature-factory-架構` 等他節 TOC 條目**凍結不得動**)、`docs/DOCSIMPLIFY_BATCHB_MANIFEST.md`(新增)、`docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`(新增,B00 DEV target view 快照)、`docs/DOCSIMPLIFY_BATCHB_ARCHVIEW.md`(新增,B00 ARCH 解耦節 baseline 快照——ARCH 無損壞,原樣快照即基準,v2r11 codex NB11)、`scripts/check_doc_manifest_b.py`+其 fixtures(新增,B00 validator 交付物)。
  **唯讀**：`docs/API_SPECIFICATION.md`、`CLAUDE.md`、`templates/TODO_GENERATION_PROMPT.md`、`scripts/check_doc_anchors.sh`+`tests/docs_tooling/`(複用不改;需擴功能→BLOCKED)。
- **批次 A 產物凍結（v2 強化,機檢見 §V）**：DEV `## 長時間任務與 API 生命週期` **節正文(L1246-1325)content-hash 凍結**（B0 僅修節內損壞 fence 時例外,修後重取 hash 為新基準）;ARCH `## Feature Factory 架構` 整節不得改;TGF 兩 anchor 斷言見 §V。
- **點名必留同步凍結**：Artifact Contract Table、V2/V3 兼容 why(ARCH L384-396 三條:不破壞 REST/可獨立測/可獨立部署)、DEV L4 權威 banner。
- **先修後刪**：B0 先修損壞（獨立 commit）,B1/B2 才開始。
- **抽 invariant 非整批刪**;**禁為湊行數刪資訊**;不新增內容 appendix（D4）。

## §G Golden / Baseline
- N/A（見 §N）。等效客觀基準 = §V manifest gate + anchor checker + contract assertion。

## §P Phase 與依賴
> **派工前置（v2 新增,codex 6.x）**：本 SPEC 三家閉合重驗 PASS + reconcile 戳記（`reconcile_stamps_check.sh` 格式）核可 + TODO 生成,才可派 B00。
> 拓撲（v2 寫死,消 v1 自撞）：**B00(只讀) → B0(修損壞+錯置刪除,依賴 B00 保全完成) → B1(DEV 壓縮,依賴 B0——行號/內容基準在 B0 後才穩定)**；**B2(ARCH,依賴 B00;與 B1 異檔可並行)**。DAG：`B00→B0→B1`、`B00→B2`。每 Task atomic commit+重跑 gates,checker 紅=不 merge。
> **行號漂移對策（v2;v2r10 座標統一）**：manifest 每塊**必填 content-hash**（line-span 僅輔助）;唯一比對基準=**B00 target view 檔**（實體檔 `docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`,B00 交付物,review-lock 後凍結）;真 baseline commit 只記於 manifest 供溯源,不作任何 validator 座標。

### Phase B00 — 只讀 inventory / manifest(review-lock gate)（依賴：無）
**Task B00.1 — disposition manifest（刪前凍結,委員 review-lock）**
- 檔案：新增 `docs/DOCSIMPLIFY_BATCHB_MANIFEST.md`。
- 範圍（=D1,不擴權）：DEV 八通用章+First Principle 章 逐 H3/H4/表格/碼塊；ARCH `## 解耦架構原則` 節逐子塊。數據真實性/測試規範章**不入壓縮範圍**,僅點名必留登記。
- **B0 目標視圖(v2r9,收斂 grok NB5-NB8/codex V8;取代 v2r8「virtual-repaired baseline」)**：baseline 損壞 fence(L1259 未閉;授權刪除區內另有 4 個 language-push 無 pop)在 lang_push 語意下吞掉 Python/前端/註釋/測試章,B00 無法直接盤點。定義 **B0 目標視圖(target view)**=真 baseline 依序套用:①9 個 selector 命中處 fence 修復 ②L2373-2387 結構修 ③**刪除 L1326-1405 錯置塊**(含其內 4 個無 pop 的 language fence,隨塊消滅) ④長任務節末段補閉 fence(若 ①③ 後仍 unclosed)——每步為**可重放的行級編輯步驟表**(附錄=施工圖,委員 review-lock);**target view 落為實體檔 `docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`**(B00 交付物,writable allowlist 併入;lock 後凍結;**兩 view 檔於批次 B 全部完成(B1+B2 閉合)後才可刪**——B1/B2 validator 仍以其為基準,v2r11 R5)。工單步驟明列含 ④ 長任務末段/L1259 補閉(v2r9 R2 補)。target view 必須滿足:lang_push 下 unclosed==0、nested==0、四章 heading 全部 fence 外可見(構造時機檢,不滿足=B00 FAIL 重做)。
- **座標統一(NB5)**：B00 inventory/塊 hash/line-span/validator 比對**一律以 target view 為唯一基準**(§V validator 條同步;真 baseline 只用於 B0 oracle 的 pre 集與授權刪除集交集計算)。
- **被吞 heading 重現集(NB8 更名,含 H2-H4 各級)**=機器演算:`target_view_FA_headings − raw_baseline_FA_headings`(扣除授權刪除區內者),非人工反推。
- **B0 驗收主 gate(NB7)**：B0 完成後 `diff docs/DEVELOPMENT_GUIDE.md docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`==0(整檔 byte 一致;heading 差分/fence 條件在 target view 構造時已機檢,B0 只需等值)。此 gate 同步寫入 B0.1 驗證與 §V。
- 每塊必填欄：`ID | 原 heading | content-hash(必填)+line-span(輔助,基準=target view 檔) | 分類{刪|壓縮留|原樣留} | 壓縮後承載(invariant ID 條列/pointer 目的) | 理由`。
- 分類決策表（v2=複用批次 A operational 判準,廢「常識」措辭）：
  - **可刪**：有單一 authoritative source + **可實跑完整重生命令/pointer**（CLAUDE.md 條文、protocols.py/factories.py、config、API_SPEC）,且不含 why/schema/lifecycle/failure 語意。**「通用工程常識」不是可刪理由**——無 canonical source 的教條要刪必須逐塊列「刪後資訊去哪/為何不需要」供委員否決。
  - **壓縮留**：專案特有 invariant → 3-8 條+pointer+≤1 正反例;**每條 invariant 給 ID**,manifest 承載欄列 `INV-xx→正文錨句`,驗收 `rg` 100% 可對照（grok 4）。
  - **原樣留(預設)**：跨邊界 contract、失敗語意、時間/資料可得性語意、批次 A/TGF 相關結構。
- **點名必留（v2 補 7 漏項;標「原樣留/壓縮留」,誤標刪=FAIL;驗收 needle 見 §V）**：
  1. 數據真實性 **L0/L1/L2 分層 + L1 ingest 真 kline fixture + 禁 sanitized 回歸**（DEV ~L241-267）
  2. retryable/non-retryable 錯誤分類表
  3. **hot-loop 禁 log**（DEV ~L685-705）
  4. `## 硬體自適應開發規範` 章原樣留(本批不動;v2r3:tier 偵測契約真身在 `momentum/FeatureEngineering/**/hardware_utils.py` get_memory_tier/get_tier_config,DEV 正文未承載該契約——不虛構 needle,§V 只驗章名存續;若要補 pointer 屬 scope 外另票)
  5. ARCH **R2/R3/R4 ⚠️ 誠實現況表+R8 殘留**（L156-174）與**兩支 scanner 編號語意差**（L175-176）——D1/D2 據實化成果,不得在收斂中被「順手清理」
  6. **V2/V3 兼容 why 三條**（ARCH L384-396）+ Artifact Contract Table（整表,批次 A KEEP-ARTIFACT-L65 延續）
  7. DEV L4 規範權威 banner、`## 長時間任務與 API 生命週期` 全節
  8. **ARCH 呼叫流程圖**（L349-364,Route→Service→Factory 責任鏈）——B2 收斂不得刪（composer closure 補）
  （七段命名契約真身在 ARCH FF H2=凍結保護,DEV 不強留重複——grok 修正）
- 驗證(可證偽;v2r3 validator 實體化,codex N3)：**B00 交付物含 `scripts/check_doc_manifest_b.py`**——輸入=manifest 檔+DEV view 檔(`docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`)+ARCH view 檔(`docs/DOCSIMPLIFY_BATCHB_ARCHVIEW.md`);行為=對兩 view 檔各取範圍內全部 H2/H3/H4/表格/fenced block,與 manifest 列比對;**block ID 檔名段一律用原檔名**(`DEVELOPMENT_GUIDE.md`/`ARCHITECTURE.md`),view 檔僅為取塊來源(v2r11 NB11);輸出 missing/duplicate/content-hash mismatch 明細,任一非空→exit 1;**block identity/邊界/normalization 定義寫死(v2r5,codex N3)**:block ID=`<檔名>::<heading path(H2/H3/H4 全鏈)>::<同 heading 下第 n 個 block 類型+序號>`(同名 heading 以出現序次 -1/-2 消歧);**block 邊界唯一定義(fence-aware,v2r7 grok NB2)**——heading 之認定一律用 lang_push 共用 parser(定義見 §V「fence parser 單一語意」;```lang push/裸``` pop),**fence 內 `^#{1,6} ` 行(如 `# ✅` code comment,DEV 實測 204 行)不作 heading 亦不作邊界**;heading block=該(fence 外)heading 行起**至下一個任意層級(fence 外)heading 行前**的全部行(含其直屬正文/清單,不含子 heading 段——子 heading 另列 block);table/fence block=其自身全文(由前導 heading path 定位);故「只 hash heading 行」的弱 validator 違規;content-hash=block 全文經「去行尾空白+換行統一 \n+檔尾單一換行」normalization 後 sha256——validator 與 manifest 產製方共用同一函式;附 ≥6 fixture 自測(漏列/重複 heading/hash 不符/空白差異同 hash/換行差異同 hash/**heading 下正文被改→mismatch**,可證偽)。**validator 雙模式(v2r12,codex NB11 post-state)**:①coverage 模式(B00 用)=上列三參,驗 manifest 對 view 檔全覆蓋;②**post-state 模式(B1/B2 驗收用)**=`python scripts/check_doc_manifest_b.py --post-state docs/DOCSIMPLIFY_BATCHB_MANIFEST.md docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md docs/DOCSIMPLIFY_BATCHB_ARCHVIEW.md` ——block ID 檔名段映射讀取 **live** `docs/DEVELOPMENT_GUIDE.md`/`docs/ARCHITECTURE.md`,機檢四項(v2r13 補完備性,codex):①**雙向刪除等式**——manifest 標「刪」塊在 live 必須不存在(授權刪除塊故意保留→exit 1)且 live 刪除塊⊆manifest{刪}(未授權刪除→exit 1);②「原樣留」塊 live content-hash 不變;③「壓縮留」INV 綁定驗證(v2r14)——manifest 承載欄記 `source ID → post-state ID → INV-xx 錨句` 三元組;驗證=每 INV 錨句在**其綁定的 post-state block 範圍內** rg≥1(非全域 rg;錨句移到別塊或同 ID 改寫丟錨句→exit 1);④**新增封閉+壓縮替換授權**——`live IDs − baseline IDs ⊆ manifest 預登記 post-state IDs`(登記外新增→exit 1);**壓縮 source ID 之消失=授權**(在 mapping 表內者不算未授權刪除;mapping 外舊 ID 消失仍→exit 1,消 false-red);違反任一→exit 1;fixture 增 4:篡改 live 原樣留/未授權刪除/授權刪除塊故意保留/新增未登錄 block→各 exit 1(可證偽)。≥5 代表塊委員 calibrate;點名必留全非「刪」。（writable allowlist 併入此腳本+其 fixtures。）
- 不可做：無 manifest 就刪任何塊。

**Task B00.2 — 錯置區塊欄位級驗真+保全（v2 強化）**
- 產出**欄位級 mapping 表**（併入 manifest）：錯置塊每欄位 × API_SPEC 現況(附 rg 行號) × runtime 程式碼實際欄名(附 `api/` 檔行 receipt)。
- **缺口欄位之契約語意全文復刻進 manifest 附錄**（保全存證,B0 刪正文的前置）;缺口清單=BLOCKED-scope 申請（含 `current/total` vs `current_step/total_steps` 命名裁決需求）。
- **runtime 驗真=綁定公開 endpoint 實鏈,禁泛 `rg api/`**（v2r2,codex closure #2/#10）：search-task endpoint 的 runtime truth 鏈固定為 `api/main.py`(mount,~L203-206) → `api/routes/case_search.py`(route 綁 `standalone_search_service`,~L31/L132-148) → `api/models/responses.py` `TaskInfo` progress 欄位(~L35-41);每欄位 receipt 必須出自此鏈上檔案,命中他處(如 `api/services/task_manager.py` 另一套 task system)不算數且須在表中標注「非本 endpoint」。
- 驗證：mapping 表覆蓋錯置塊全部欄位（欄位數==錯置塊實列欄位數,附計數 receipt）;每列附雙 receipt（`rg -n <欄名> docs/API_SPECIFICATION.md` + 上列 truth 鏈檔案行號）;缺口欄位保全附錄與正文 `diff`==0（逐字複刻）。

### Phase B0 — 修損壞 markdown + 錯置刪除（依賴：B00 review-lock+保全完成）
**Task B0.1**
- 依 B00 施工圖四步執行:①修 9 處損壞 fence（selector `^(typescript|python)[^ ]`）②L2373-2387 硬體節結構修 ③刪 L1326-1405 錯置塊與假 H2（缺口契約已保全於 manifest）④長任務末段/L1259 補閉 fence(若 ①③ 後仍 unclosed);DEV TOC 同步。產出必須與 TARGETVIEW byte 一致。
- 驗證（v2 廢偶數 gate;v2r9 主 gate=**與 B00 target view 整檔 byte 一致 `diff`==0**,以下條件為 target view 構造時已機檢之再確認）：`grep -cE '^(typescript|python)[^ ]' docs/DEVELOPMENT_GUIDE.md`==0;`grep -c '^## GET /api' `==0;**fence stack 平衡驗證**（python 逐行 stack:unclosed==0 **且 nested 錯誤==0**(現況 27,修後歸零) **且 heading 完整性前後差分斷言(v2r4b,codex N4;避免 raw grep 抓 python fence 內 `# comment` 之假紅)**:以 fence-aware parser(python 逐行 stack,僅 fence 外行計 `^#{1,6} ` heading)分別對修復前/修復後 DEV 抽 heading 多重集;斷言=`pre_fence_aware − post_fence_aware == authorized_raw_deletions ∩ pre_fence_aware`(v2r6 公式+v2r7 lang_push 語意事實更正:授權刪除集依 raw 列 L1326-1405 全部 4 個 heading 級行;baseline 在 lang_push 語意下該 4 行**全部被吞**(L1259 未閉 fence 波及),故 `authorized_raw ∩ pre_fence_aware` 實測=**空集**、`pre−post` 應==空集——公式對任意語意成立,數值以 lang_push 為準;位於授權刪除區且 baseline 已被吞者**不得列入重現白名單**(該 4 行隨錯置塊刪除,永不重現);**`reintroduced_heading_set`**(重現集,含 H2-H4)只含授權刪除區**外**因 fence 修復而重現的 heading;任何交集外 heading 消失→紅)且`修復後集 − 修復前集 ⊆ reintroduced_heading_set`(該集由 **B00 機器演算**=target_view_FA − raw_baseline_FA 扣授權刪除區,記入 manifest;不得由修復後結果反推;集外新增 heading→紅);另 **`expected_target_H2_set`**(=target view 之 FA H2 集,實測 22)==B0 後 DEV 之 FA H2 集——**兩集合分名分檢,不得混稱「白名單」**(v2r11 codex NB9),附 receipt;偶數計數不作 gate）;anchor checker exit 0;長任務節（修 fence 後）重取 content-hash 記入 manifest 為 B1 凍結基準。

### Phase B1 — DEV 八通用章壓縮（依賴：B0）
**Task B1.1**
- 依 manifest 逐章：「刪」刪、「壓縮留」→INV-ID 條列+pointer+≤1 正反例、「原樣留」不動;First Principle 170→~30。
- 驗證(hard gate,非行數)：**validator post-state 模式四項全跑**(v2r14 同步 B00 主定義:雙向刪除等式/原樣留 hash/INV 綁定/新增封閉,見 B00.1)——anchor checker exit 0;DEV 新增假綠裸命中==0。行數 telemetry。

### Phase B2 — ARCH 解耦節收斂（依賴：B00;與 B1 異檔並行）
**Task B2.1**
- 依 manifest：Protocol/Factory 長清單→pointer(protocols.py/factories.py 權威);保留點名 5/6 項（誠實現況表/scanner 語意差/V2V3 why/Artifact Contract）;CLAUDE.md 重複枚舉→pointer。
- 驗證：點名留項 needle 全在（§V）;**ARCH 假綠 allowlist 落實版**（v2,codex）：`rg -n '0 violation' docs/ARCHITECTURE.md` 命中=恰好 2 處且皆在 `## 解耦架構原則` 節的 scanner-pointer 表內（收斂後行號會變,以「節內+表內」判,附 receipt）,新增裸命中=0;anchor checker exit 0;TOC 僅本節條目變動（diff 斷言其他 TOC 行不變）。

## §V 驗證策略與邊界測試目錄
- **mutation**：N/A（純文件;見 §N）。
- **disposition manifest gate**：B00 manifest 委員 review-lock;validator 對 **B00 target view**(座標唯一基準,v2r9)機檢：post-state 四項(雙向刪除等式/原樣留 hash 不變/INV 綁定於 post-state block/新增封閉+mapping 授權,=B00.1 主定義,v2r14 同步);無 manifest 覆蓋的刪除=FAIL。
- **anchor checker（v2 加 TGF 斷言,codex）**：`bash scripts/check_doc_anchors.sh --files docs/DEVELOPMENT_GUIDE.md,docs/ARCHITECTURE.md,templates/TODO_GENERATION_PROMPT.md` exit 0（TGF 入列→FF/長任務 anchor 被刪即紅,不依賴 TGF 有 diff）;另斷言 `grep -c '^## Feature Factory 架構' docs/ARCHITECTURE.md`==1 且 `grep -c '^## 長時間任務與 API 生命週期' docs/DEVELOPMENT_GUIDE.md`==1。
- **fence parser 單一語意(v2r7,grok NB1)**：本 SPEC 所有 fence/heading 相關 gate、validator、B00 inventory 一律用**同一 lang_push 語意 parser**（` ```lang ` 行=push,裸 ` ``` `=pop;能偵測 unclosed/nested 損壞;禁 toggle 語意——toggle 下 nested 恆 0=死 gate）,實作為單一共用函式,B00 validator 與 B0/B1/B2 驗收共用。
- **B0 主 gate（v2r10 同步 §V,codex NB7）**：`diff docs/DEVELOPMENT_GUIDE.md docs/DOCSIMPLIFY_BATCHB_TARGETVIEW.md`==0（整檔 byte 一致）。
- **fence 完整性（v2r4 同步 B0 全條件）**：stack 平衡 unclosed==0 **且 nested==0** + 損壞 selector==0 + heading 前後差分斷言（廢偶數 gate;與 B0.1 驗證同一組命令,不得只跑弱化版）。
- **點名必留 needles（機檢錨句,B1/B2 驗收逐條 rg≥1;v2r 依 composer closure 換為正文實測字面,單一權威=本表,B00 只可增列不可改寫本表既有 needle）**：DEV——`L0|L1|L2` 分層句、`真實 kline|kline_cache`、`sanitized|消毒`禁令句、`可重試`+`不可重試`(L732/L738 實測)、`循環內大量log`(L688 實測)、`硬體自適應`(L2371 章名實測);ARCH——`R2=5|R3=12|R4=1` 或等值誠實表句、`編號語意`、`不破壞.*REST|獨立測|獨立部署`、`Artifact Contract Table`、`呼叫流程`(L349 實測)。**needle 永久有效(v2r3,codex N5)**：本表 needle 於 B1/B2 後仍必須逐條 rg≥1——壓縮改寫措辭時**錨句字面必須保留**(可移位不可消失);manifest 只可**增列 alias**,不可替換/廢止本表任何 needle。無第二權威。
- **回歸信號**：`bash scripts/check_decoupling_phase4.sh` exit 0（若環境 numba cache 紅=env 問題,清 cache 重跑,以最終 exit 為準——grok note）;`pytest tests/docs_tooling/ -q` 全綠。
- **假綠 allowlist**：ARCH=恰好 2 處 `0 violation` 於解耦節 scanner-pointer 表（B2 驗證定義）;DEV 新增裸命中=0。
- 行數 telemetry：記錄前後,不 gate。

## §R 回退
- 每 Task atomic commit 可單獨 revert;B00 只讀;B0 先行且獨立成立（fence 修復+錯置清除,缺口契約已在 manifest 保全,revert B1/B2 不影響）。
- 任一 commit anchor checker 或 manifest gate 紅 → 不 merge,不刪舊內容。

## §N N/A 登記
- **§G Golden：N/A** — 純文件治理,不碰數值/特徵/ML/回測正確性;行為不變由 §V manifest gate（content-hash 凍結+INV 對照）+anchor checker+回歸信號保證,可證偽。
- **§V mutation：N/A** — 驗收對象=文檔結構/契約保全/引用完整性,以 manifest validator+anchor checker(自帶 mutation 測試)機檢。
