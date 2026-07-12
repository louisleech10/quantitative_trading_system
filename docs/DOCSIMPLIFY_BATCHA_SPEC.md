# 文檔簡化 批次 A — SPEC (v2，經三家 adversarial 審修訂)

> 來源 PLAN/診斷：handoffs/DOCDRIFT-SIMPLIFY-RECONCILE.md（三家收斂+使用者定案）　|　日期：2026-07-13　|　對應 TODO：待 TODO_GENERATION_PROMPT 生成
> v1→v2：codex+composer+grok 三家 adversarial 全 BLOCK,本版修 15 項(manifest 機檢/contract inventory/mapping 驗真/依賴圖/anchor checker 規格/scope allowlist/行數降 telemetry/§A 誠實化)。審查檔 handoffs/DOCSIMPLIFY-A-SPECREVIEW-{codex,composer,grok}.md。
> 範圍：批次 A（導航面閉合）。批次 B 另立 SPEC。**核心方法論改為 inventory-first、manifest-gated、mapping-verified、先建後刪**。

## §RISK 風險分級
- **大小**：中（文件治理,動 writable allowlist 內檔+派工模板 anchor+新增 checker 腳本;不改程式邏輯）。判斷面大(853 行治理+跨檔 mapping),故拆「只讀 inventory/mapping review-gate」先行降風險(三家建議)。
- **命中高風險原則**：(b) 跨模組/共用路徑——TGF 觸發器影響所有派工按需讀範圍;anchor 改名=文檔 API 破壞面;跨檔 contract 外移。非 (a)/(d)。
- **RISK-HIT 宣告**（機檢依據）：
RISK-HIT: b
- 未命中 (a)/(d) → §G Golden N/A（§N 登記）。但因「越界刪 contract」風險高,以 §V disposition manifest 作等效客觀基準。

## §A 假設與待使用者確認
- **FACT-RECEIPT（實測,2026-07-13 Claude 實跑）**：
  - `grep -c '^### ✅' 於 ARCH §1000-1852 → 23 個已實現子節`
  - `rg -l 'Feature Factory 章|API 節' --glob '*.md' → 命中:templates/TODO_GENERATION_PROMPT.md、docs/TEMPLATE_GATE_FIX_{SPEC,MANIFEST,TODO}.md、HANDOFF.md、handoffs/2026-07-04-*、本 SPEC 自身`（→ §V grep 不可掃全 docs/,見下）
  - `grep '^## .*長時間任務' DEV → 僅 '## 長時間任務開發規範'(L1246);'## 長時間任務與 API 生命週期' 不存在`（→ 死連結風險,A0 須先建）
  - `API_SPEC body → '## 19. Feature Factory Granular'、'## 20. MultiTF+Batch';TOC 序數與 body H2 編號可能不一致`（→ pointer 用穩定標題非序數）
  - `ARCH '## 目錄'(L21-33) 逐條列各 H2`（→ 新增 H2 須同步 TOC）
  - `API_SPEC 文件日期 2026-03-15,晚於部分 ARCH 功能;路徑 ARCH '/features/' vs API_SPEC '/api/v1/features/' 有差異`（→ 外移前須驗目的地契約真存在）
- **使用者已確認(僅此二項,勿擴張)**：`2026-07-12 使用者：① 兩批都做(A+B) ② TGF 斷鏈納入批次 A`。
- **主委(Claude)設計裁決(非使用者逐字確認;reviewer 可挑戰,標明以免冒稱使用者已定)**：
  - D1：FF 穩定 H2 命名 = `## Feature Factory 架構`(slug `#feature-factory-架構`)。
  - D2：**DEV 過渡採 reconcile 原意——批次 A 直接建穩定 `## 長時間任務與 API 生命週期`**(wrap/重命名現 `## 長時間任務開發規範`,同 commit 改所有 inbound 引用),**不採 v1 的條件式暫指**(消死連結)。
  - D3：行數(≤120/320/100)一律 **telemetry 觀測值,非 pass 條件**(對齊 reconcile「看資訊類型不看硬行數」);hard gate = manifest coverage + capability ID 集 + link validity + contract assertion。
  - D4：API route→H2 用 deterministic mapping 表(A00 產出),非「對應 H2」模糊語。
- **待使用者確認：無**（上列 D1-D4 為主委設計裁決,走 reconcile-stamp 由委員核可;若委員判某項需使用者,升級再問）。

## §C 約束
- 純文件治理,**不改程式邏輯**。
- **Writable allowlist(執行端只准改這些;越界→BLOCKED 申請擴 scope)**：
  `docs/ARCHITECTURE.md`、`templates/TODO_GENERATION_PROMPT.md`、`README.md`、`docs/DEVELOPMENT_GUIDE.md`(僅 A0 的長任務 H2 rename+其 inbound 引用)、`scripts/check_doc_anchors.sh`(新增)+其 `tests/`/fixtures、批次 A 的 disposition manifest 檔。
  **唯讀(不得改,只作外移目的地/查核)**：`docs/API_SPECIFICATION.md`(若查出缺契約→BLOCKED 申請,不擅自補)。
- **先建後刪**:新 anchor/H2 建好且 TGF+TOC 同步、checker 綠後,才刪舊內容。
- **抽 contract 非整批上移**;**禁為湊行數刪資訊**(行數=telemetry)。
- 特別注意共用路徑:TGF 觸發表、11+8 引用 ARCH/DEV 的 doc、API_SPEC。

## §G Golden / Baseline
- N/A（見 §N）。等效客觀基準 = §V「刪前 disposition manifest + 刪除塊 100% 有 disposition + 外移目的 anchor 存在且 contract assertion 保留」。

## §P Phase 與依賴
> 拓撲：**A00(只讀 review-gate) → A0.1 → A0.2 → A1；A2 序列化於 A1 之後(同檔 ARCH,避免 line-span/hash 漂移)**。每步 atomic commit + 重跑 checker/manifest gate,中間任一 commit checker 紅=不 merge。

### Phase A00 — 只讀 inventory / mapping(review-lock gate,先於任何刪除)（依賴：無）
**Task A00.1 — 產出 disposition manifest（刪前凍結,委員 review-lock）**
- 目標：把 ARCH §1000-1852(已實現)與 §636-999(目錄)每個 H3/H4/表格/碼塊列成可機檢 manifest。
- 檔案：新增 `docs/DOCSIMPLIFY_BATCHA_MANIFEST.md`(或 .json)。
- 內容(每塊必填欄)：`ID | 原 heading | line-span 或 content-hash | 分類{刪|外移|留} | 可重生證據命令(刪) | 目的 file#anchor(外移) | 不可重生理由(留)`。
- 分類決策表(operational,消「判斷詞」歧義):
  - **可刪**：能由單一 authoritative source + 明列命令**完整重生**,且無 why/契約(端點列、元件/測試計數、完成徽章、無 receipt 效能%、可由 repo tree/route/OpenAPI 重生者)。
  - **外移**：有唯一維護中 canonical 目的地且內容屬其責任(endpoint schema→API_SPEC 對應 H2),**且目的地契約經 A00.2 驗真存在**。
  - **預設留(除非證明 canonical destination)**：跨邊界 invariant、ownership/lifecycle、時間/資料可得性語意、schema/相容性、failure 語意。
- 驗證(可證偽)：manifest 覆蓋 §1000-1852 與 §636-999 全部子塊(無遺漏);≥5 個代表塊由委員 calibrate 分類一致;**點名必留清單(下)全部標「留」**。
- **點名必留 inventory(三家揪出,標「留」,誤標刪=FAIL)**：d_star cache key=per-column value fingerprint(§16 L1593)、native-tf 非主 TF 沿用主 TF d_star(L1592)、force_regenerate/增量生成語意(L1611)、L6.5 raw/processed 順序 why(Artifact Table)、七段式命名文法+相容理由、MultiTF/AlignmentMode 防 look-ahead 契約、IC 8 階段+3 層 config precedence(§14)、L7 tier/cache-hit lifecycle(§21-22)、CGSA 語意(§23)。
- 不可做：無 manifest 就刪任何塊。

**Task A00.2 — route→API H2 mapping + 目的地契約驗真**
- 目標：消 API 觸發器歧義 + 防外移到缺契約的目的地。
- 檔案：mapping 併入 A00.1 manifest。
- 內容：`route basename(如 feature_factory/case_search/optimization) → API_SPEC 穩定 H2 標題(非序數)`;未知 basename→「讀 API_SPEC Router 表+人工確認」。每個標記「端點已在 API_SPEC」的能力,附命令查核 endpoint/schema 真在目的地(route decorator 或 API_SPEC 內文);缺→標 BLOCKED-scope 不外移。
- 驗證：至少 feature_factory、case_search、optimization、未知新 route 四 fixture 得唯一 H2 或明確 fallback;path 差異(`/features/` vs `/api/v1/features/`)在 mapping 註明以何為準。

### Phase A0 — 建穩定導航錨點 + 修 TGF（依賴：A00 review-lock 通過）
**Task A0.1 — ARCH 新建 `## Feature Factory 架構` H2（依賴：A00）**
- 檔案：docs/ARCHITECTURE.md 新增 `## Feature Factory 架構`(插入點：`## 解耦架構原則` 後、`## 整體架構` 前),同步更新 `## 目錄` TOC。
- 內容：只放 A00 標「留」且屬 FF 的跨邊界 contract(抽出精煉,非搬 §16/§20 原段);Optuna λ 只 pointer optuna_optimizer.py 不複製公式。
- 驗證：`grep -c '^## Feature Factory 架構' ARCH`==1;`## 目錄` 含新條目;`rg 'λ|=1.0' 新節`==0;checker 綠。
- 不可做：整段複製 §16/§20。

**Task A0.2 — 建 DEV `## 長時間任務與 API 生命週期` + 修 TGF（依賴：A0.1）**
- 檔案：DEV rename `## 長時間任務開發規範`→`## 長時間任務與 API 生命週期`(同 commit 改所有 inbound 引用);templates/TODO_GENERATION_PROMPT.md 觸發表 L26-29。
- 改法(三列全給穩定 anchor 字面量)：
  - `momentum/FeatureEngineering` → `docs/ARCHITECTURE.md#feature-factory-架構`
  - `api/routes`/`api/services` → `docs/API_SPECIFICATION.md`(依 A00.2 route→H2 mapping 選節,附「未知→讀 Router 表」規則)+ `docs/DEVELOPMENT_GUIDE.md#長時間任務與-api-生命週期`(lifecycle)
  - `跨域 / factories.py` → `docs/ARCHITECTURE.md#feature-factory-架構` + `#解耦架構原則`(不再留「上兩檔對應節」模糊語)
- 驗證：見 §V anchor checker;`rg 'Feature Factory 章|API 節' templates/TODO_GENERATION_PROMPT.md`==0;所有新 target anchor 存在。
- 不可做：指向不存在的 anchor(依賴 A0.1 完成);指行號。

### Phase A1 — 能力索引化 + 假綠修正（依賴：A0.2；同檔序列化於 A0 後）
**Task A1.1 — 已實現功能 §1000-1852 → 能力索引表**
- 檔案：docs/ARCHITECTURE.md `## 已實現功能`。
- 改法：依 A00.1 manifest 執行——標「刪」者刪、「外移」者移至驗真目的地+留 pointer、「留」者進 FF H2(A0.1)或索引表 contract 欄;表頭 `能力 | 狀態(pointer→HANDOFF/ROADMAP) | 主要 module | API(→API_SPEC 穩定 H2) | 前端(→code)`。狀態欄一律 pointer,不寫「✅ 完成」硬編。
- 驗證(hard gate,非行數)：**所有刪除塊 ∈ manifest「刪|外移」集(diff 比對,未列塊消失=FAIL)**;外移目的 anchor 存在+關鍵 contract assertion 保留;假綠 `rg '175 tests|159 tests|100% coverage|Rule 1-7 完全遵守'` 於本節+changelog==0;capability ID 集與 manifest 一致(合併/拆分須顯式 mapping,不硬守 23)。行數 = telemetry(記錄,不 gate)。
- 不可做：壓成一行卻留假綠;無 manifest disposition 的刪除。

### Phase A2 — 目錄結構收斂 + README（依賴：A1 完成,同檔序列化）
**Task A2.1 — ARCH 目錄結構 §636-999 收斂**
- 改法：依 manifest;保留頂層 domain+關鍵入口(factories.py/protocols.py/main.py/run_api.py)+「完整樹以 repo 為準」。
- 驗證：`bash scripts/check_doc_anchors.sh` exit 0;刪除塊 ⊆ manifest{刪,外移}(diff 比對);`grep -cE 'factories.py|protocols.py|main.py|run_api.py' 於 ARCH 目錄結構節`≥1(domain 入口 pointer 保留)。行數 telemetry 不 gate。
**Task A2.2 — README 假行數**
- 改法：刪易漂行數欄(~1800/~3500),改「見檔案本身」。
- 驗證：`rg '1800|3500' README.md 該區`==0。

## §V 驗證策略與邊界測試目錄
- **mutation**：N/A（純文件;見 §N）。以結構機檢替代。
- **disposition manifest gate(擋越界刪的核心)**：實作前 A00.1 manifest 委員 review-lock;每個被刪/改動的原塊須在 manifest 有 disposition;驗收 diff：`刪除塊 ⊆ manifest{刪,外移}`,`外移塊目的 anchor 存在且 contract assertion 保留`,`manifest 標「留」塊不得消失`。無 manifest 覆蓋的刪除=FAIL。
- **anchor checker(`scripts/check_doc_anchors.sh`,本 SPEC 交付物,含 tests/fixtures)**：
  - slug 規則 = GitHub-compatible(小寫、空白→`-`、去標點、CJK 保留、重複 heading `-1/-2`);附 fixtures 各一例:中文、`+`、括號、重複 H2、相對路徑、reference-style link、缺 anchor。
  - 掃描策略：本次**改動檔的所有本地 `file#fragment` 連結**目的 anchor 必存在(新增 dead link=0);另報 repo baseline/delta(既存 dead link 不歸本任務,但不得新增)。
  - 排除 root：`docs/Archived/`、`handoffs/`(歷史,非導航驗收面)。
- **舊觸發字串清除(scope 收斂,消自撞)**：`rg 'Feature Factory 章|API 節' templates/TODO_GENERATION_PROMPT.md`==0;**不掃全 docs/**(TEMPLATE_GATE_FIX/HANDOFF/本 SPEC/handoffs 為歷史或引述,明列豁免;其正名另立票不在批次 A)。
- **防假綠 allowlist**：`rg 'Rule 1-7 完全遵守|✅ 已修復|0 violation' docs/ARCHITECTURE.md` 僅允許出現在 D1/D2 已據實化的 scanner-pointer 表列(明列 file+heading+expected 位置);新增裸命中=FAIL。
- **回歸信號**：`bash scripts/check_decoupling_phase4.sh` **exit 0**(記錄實際 collected/passed,不硬釘 ==135;phase4 僅 Strategy 子集,env 可能因 numba cache 波動,以 exit code 為準)。
- **每段刪/外移/留分類**：見 disposition manifest gate（取代 v1 的「TODO 附分類」軟要求）。

## §R 回退
- 每 Task atomic commit 可單獨 revert;A00 只讀不改 repo(產 manifest);A0(建 anchor/H2+修 TGF)先行,即使 A1/A2 revert,TGF 仍指有效 anchor。
- 任一 commit anchor checker 或 manifest gate 紅 → 不 merge,不刪舊內容。

## §N N/A 登記
- **§G Golden：N/A** — 純文件治理,不碰數值/特徵/ML/回測正確性;行為不變改由 §V disposition manifest（刪除塊皆有 disposition + 外移 contract assertion 保留）+ anchor checker（引用不斷鏈）+ decoupling exit 0 保證,可證偽。
- **§V mutation：N/A** — 無「驗數值正確性」測試;驗收對象=文檔結構/契約保全/引用完整性,以 manifest gate + anchor checker fixtures 機檢(缺 disposition/新 dead link/缺 fixture 通過 → FAIL)。
