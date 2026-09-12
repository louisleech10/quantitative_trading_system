# Reconcile — 20260912-docrot-x-consult-r2

**來源** 20260912-docrot-x-consult-r2-codex.md, 20260912-docrot-x-consult-r2-composer.md, 20260912-docrot-x-consult-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：HANDOFF.md

🔴 **本輪主委不再折衷**。R1 的問題正是主委對三家互斥路線自行拍板、且折衷無人審過（使用者當面質問「你不把自己要做的修正給三家委員審？」）。本輪三家**已自行收斂到同一優先序**，主委只如實記錄，不新增任何無人提過的方案。

🔴 **本輪踩到並修掉一個歸戶閘的機械缺陷**：E2 與 E6 之逐字引文本身含管線符號（`CODEX-R2-P0-02` 第 20 字為裸 `|`、`GROK-R2-P2-02` 第 7 字為 `\|`），而 `scripts/_synth_attr.py` 原以 `split("|")` 切欄且不處理跳脫、`nfc_strip` 亦未正規化跳脫管線 ⇒ 引文含管線之 finding **結構上永遠無法歸戶**。經使用者裁定後修兩處：切欄先保護 `\|` 再還原為裸 `|`；`nfc_strip` 統一正規化。此為既有閘之首次觸發（既有 9 列含管線者皆位於處置欄，切壞不影響 `cells[3]` 判定，故未暴露）。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **E1 廣義 F3 在無 token 清單下不可實作（三家一致 P0）**——「F3「單一決定活文計數≤3」在不提供決定」「第二版裁定之F3（單一決定活文計數≤3）」「第二版裁定同時主張「F3單一決定活文計數」 | P0 | CODEX-R2-P0-01, COMPOSER-R2-P0-01, GROK-R2-P0-01 | 採納（三家各自實跑證明：閘必須先知道要數哪個 token 才能 fail-closed，而活文計數 Task 9.3 為 23、Task 9.2b 為 13 至 20、metadata.split_unify 為 11、validate_split_pair_integrity 為 8——後兩者**不是 Task 文法**，無清單則閘看不到真病灶。composer 實寫實作嘗試並證明腳本內硬編即為隱式 registry。⇒ **主委第二版之「零維護、不需 registry」與 F3 互斥，該宣稱作廢**。廣義 F3 降級為具名殘留；grok 另提之窄化版（自動抽 Task token 密度，不需 YAML）列為可選，但明載其**不覆蓋非 Task 決定**） |
| **E2 掛載點只用 PostToolUse 之強制力為假（三家一致 P0）**——「現有 `PostToolUse: Edit\|Write」「第二版裁定選擇的強制掛載點（`PostT」「第二版把「強制」掛在既有`PostToo」 | P0 | CODEX-R2-P0-02, COMPOSER-R2-P0-02, GROK-R2-P0-02 | 採納（matcher 為 Edit 與 Write，**不含 Bash**；而主委自己寫 synth 正是走 bash 腳本 ⇒ 新判定對主委最常走的路徑不跑。doc_format_precheck 檔頭已自白此事，gov_check 亦承認須靠 1b 補洞。⇒ 掛載改為**三層**：PostToolUse 早期警告＋gov_check 改動掃描補 Bash＋派工邊界硬擋；沿用既有樣板，不自創） |
| **E3 主委忽略 codex 第②條，三家一致升為首選（三家）**——「主委第二版裁定完全忽略codexR1第②」「主委第二版裁定**完全忽略**codex」「第二版沒有把 R1 已採納的 current b」 | P0 | GROK-R2-P0-03, COMPOSER-R2-P1-02, CODEX-R2-P1-04 | 採納（**審查輸入只餵當前段落＋本輪 diff、finding 之 source anchor 不得落在歷史段**。三家一致判其為成本最低且直接對應使用者原話「新一輪又看到前幾輪修完的文字」；grok 與 composer 皆將 R1 立場**修正**為以此為首選，codex 指出 R1 D2 雖寫「一併採納」卻未進入裁定操作句。⇒ 列為**第一順位**，且不需任何新腳本，只改派工契約與 completeness 之 anchor 檢查） |
| **E4 「零維護」與「掛既有鏈不算擴建」兩宣稱皆不成立（兩家）**——「第二版裁定「判定採grok零維護、強制採」「「掛進既有鏈、不新開epic」被用來主張」 | P1 | COMPOSER-R2-P1-01, GROK-R2-P1-02 | 採納（零維護之 F3 需要決定與 token 之對應表，該表即 registry；新增第九支檢查在維護與失敗面與新建腳本無本質差別，只是包裝不同。grok 明言此為「用話術繞過不再擴建之自傷規則」。⇒ 兩宣稱刪除；若加判定就承認是小幅擴建並受成效判準約束，或依 grok 建議併入既有 obligation_block_check 之歷史專區規則以達零新檔） |
| **E5 閾值三未經校準（三家）**——「≤3閾值沒有跨決定／文件類型的校準與允許」「F3門檻「≤3」為grokR1隨手範例（」「閾值「≤3」來自 R1 grok 對 Task 掛」 | P1 | CODEX-R2-P1-03, COMPOSER-R2-P2-02, GROK-R2-P2-01 | 採納（該值為 R1 grok 之示意，無 corpus、無 precision 與 recall、無 p95；現行活文七至八個 Task token 全部超標，最低亦為 8 ⇒ 一掛上即全紅、SPEC 無法再改。⇒ **遷移序寫死**：先收縮活文至基線，再以基線加裕度校準，第一期只報 warn；禁止全域常數） |
| **E6 成本實測與焦點修正（兩家）**——「將 F1–F3 掛入既有八支 PostToolUse」「既有 Edit\|Write 鏈單次中位已 ≈4」 | P2 | COMPOSER-R2-P1-03, GROK-R2-P2-02 | 採納（實測：既有八支鏈每次寫檔 4.39 至 4.97 秒，其中 obligation_block_check 獨佔 1.31 至 4.26 秒、list_active_mechanisms 2.92 秒；而新增之計數判定僅約 2.1 毫秒。⇒ **主委「未評估成本」屬實，但關注點錯**：延遲主因是鏈上既有巨石與誤擋面，不是新判定。新判定應經 narrow_check_router 窄觸發，不增第九支全域 hook） |
| **E7 裁定本身複述兩處，程序病徵即時再犯（兩家）**——「第二版裁定記錄本身重犯R1主因——同一裁」「主委把第二版裁定完整複寫進`synth.」 | P2 | COMPOSER-R2-P2-01, GROK-R2-P1-01 | 採納（同一裁定全文並列於 HANDOFF.md 與 R1 synth 兩處，非指標。⇒ 裁定正文只留 reconcile synth 之路線段，HANDOFF 改為指標。**本輪修訂即依此執行**） |
| **E8 第四條路：兩階段窄方案**——「存在第四條路——**僅codex②審查輸」 | P3 | COMPOSER-R2-P3-01 | 採納（Phase A 零新腳本：派工 brief 強制 review_scope 與 diff，completeness 拒收 anchor 落在歷史區之 finding；Phase B 最小機械：僅對單一 SPEC 建單檔決定表並掛 narrow_check_router 一列。與 grok 之第四路徑實質同向，合併為同一執行序） |

**三家共同結論之執行優先序（非主委折衷，逐條有三家背書）**：
1. **codex② 審查輸入隔離**（E3）——零新腳本，三家一致首選，**先做**。
2. **F1 活文版本標記歸零＋窄 F2（只數「共 N 條」形態）**（E1 之可行部分）——三家皆認可無 registry 可實作。
3. **掛載三層**（E2）——PostToolUse 警告＋gov_check 改動掃描＋派工邊界硬擋，沿用既有樣板。
4. **遷移序**（E5）——先收縮活文，再 enable fail；第一期只 warn。
5. **廣義 F3 降級為具名殘留**（E1）——若成效判準失敗再導入最小 token 表，並誠實稱之為 registry。

**程序修正（三家一致，主委接受）**：凡主委產出「非任一家原文」之折衷，**自動開一輪 consult**，不得由主委單方生效；折衷文只准寫在單一權威位置；折衷之否證觀測表每格「我跑了」非空才得標為已決。

Verdict：需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P0-01
**斷言**: F3「單一決定活文計數 ≤3」在不提供決定集合、token/anchor 與允許角色的前提下，不能成為 fail-closed 機械判定。
**碼證**: `rg -c -F 'Task 9.2b' docs/SPLITUNIFY_SPEC.D-002.md` → **20**；`rg -n 'Task 9\.2b|metadata\.split_unify|validate_split_pair_integrity' scripts/fact_keys.json scripts/govflow_lifecycle.json` → no match；後者既有 registry 只有 governance keys。RECHECK：重跑兩命令。
**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7f;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;scripts/fact_keys.json#6f24676b6c78;scripts/govflow_lifecycle.json#849ef9ca6ac
[BLOCKING] 信心度=High。硬編 `Task 9.2b` 只驗一案；泛化 regex 無法區分 normative、標題、§V、mutation 與歷史，會假綠或誤擋。修法：採決定 source/生成投影，或明確承認無 registry 時 F3 不是強制驗收。

## CODEX-R2-P0-02
**斷言**: 現有 `PostToolUse: Edit|Write` 鏈既不能阻止寫入後才發現的錯，也完全不涵蓋 Bash／生成器產出的文件。
**碼證**: `jq '[.hooks.PostToolUse[]|select(.matcher=="Edit|Write")|.hooks[]]|length' .claude/settings.json` → **8**；`doc_format_precheck.sh:14-17,144-145` 明載「早期警告、不是硬閘」及 Bash 不觸發。八支鏈 replay 三次 → `4.56/4.56/4.79s`，`obligation_block_check.sh` → `4.10s`。RECHECK：重跑 jq；以同一 PostToolUse JSON payload 逐支 `/usr/bin/time -p`。
**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7f;.claude/settings.json#77cb54336328;scripts/doc_format_precheck.sh#e39ce0d21db0;scripts/obligation_block_check.sh#90737c0c0d7b
[BLOCKING] 信心度=High。照第二版做，Bash 重導或 generator 可落地未檢文件，且 hook 回報時文件已寫入；全域鏈還會讓非目標 Edit 承擔約 4.1s 掃描。修法：保留 PostToolUse 作提示，另在包含 Bash 的 producer/commit/dispatch 邊界 fail-closed；先以 target-aware replay 建 p95 與誤擋基線。

## CODEX-R2-P1-03
**斷言**: ≤3 閾值沒有跨決定／文件類型的校準與允許角色定義，不能從 grok 的單一 `Task 9.2b` 例外推成通用規則。
**碼證**: R1 grok 只提出「標題＋§V＋mutation，目標 ≤3」；`rg -n '≤3|目標.*3' handoffs/20260912-docrot-x-consult-r1-grok.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` 只見提案／裁定，沒有 corpus、p95 或 false-positive gate；現行 Task count 為 20。RECHECK：重跑 rg 與 count。
**來源摘要**: handoffs/20260912-docrot-x-consult-r1-grok.md#f14daa65418b;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7f
[MAJOR] 信心度=High。不同決定的必要引用數不同，固定 3 會把合法 anchor 當紅，也可能只數到無關 token 而綠。修法：先定角色語法與樣本 corpus，量測合法／非法案例的 precision、recall、p95，再由三家複審閾值；未完成前只列觀測值，不列合規 gate。

## CODEX-R2-P1-04
**斷言**: 第二版沒有把 R1 已採納的 current block＋本輪 diff 輸入邊界寫入裁定，且裁定同時複寫在 `HANDOFF.md` 與 R1 synth，會讓下一輪仍重讀歷史並複製病灶。
**碼證**: R1 synth:16 說該輸入方案「一併採納」，但 synth:29 的第二版只寫 F1–F3／PostToolUse；範本:16 仍要求「先完整讀」；`rg -n '新裁定＝|路線裁定' HANDOFF.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → 2 個活落點。RECHECK：重跑 rg，並檢查實際 dispatch payload 是否只含 current blocks＋diff。
**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#36b518be40fa;HANDOFF.md#1b24c621be54
[MAJOR] 信心度=High。照此裁定，review contract 仍是全文讀取，且主委裁定自身成為第二份／第三份可讀副本；F1–F3 通過也不會限制輸入。修法：把裁定置於單一 canonical decision source，dispatch 產出 current-block＋diff manifest；HANDOFF 只保留 pointer。由三家共同審候選折衷後再收斂。

ASSUMPTIONS_VERIFIED: R1 路線與第二版文字、既有 registry key 集合、F3 現況計數、PostToolUse matcher/八支命令與三次鏈延遲均已實跑；誤擋率與維護工時未驗證。
TESTS_RUN: `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r2-codex.md --family codex`（同一腳本／argv 以變數展開執行，輸出 `COMPLETENESS PASS(single)`，rc=0）。
FAILURES_SEEN: 逐支延遲量測第一次 sed 前綴命令格式錯；驗收字面命令被 PreToolUse 的 open-debt dispatch 分類擋下，未改任何專案檔，改以同一腳本／同一 argv 完成 rc=0；清理後初次 zsh 算術驗證報 division by zero，改用 `test` 驗證通過。
SCOPE_CHANGES: 僅新增本指定產出檔；未改碼、未改其他文檔、未動 data_cache、未改 root HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none；只記錄現況計數／延遲，未改輸出 schema。
VERDICT: blocked
BLOCKED-BY: CODEX-R2-P0-01,CODEX-R2-P0-02,CODEX-R2-P1-03,CODEX-R2-P1-04
CLOSED:
STATUS: DONE
## COMPOSER-R2-P0-01

**斷言**: 第二版裁定之 F3（單一決定活文計數 ≤3）在拒絕 composer YAML registry 後**無法實作**——閘無法得知「該數哪個 token 代表哪個決定」。

**碼證**: 活文（排除 `HISTORY-BEGIN/END`）計數：`Task 9.2b` **13**、`validate_split_pair_integrity` **8**、`metadata.split_unify` **11**；`Task 9.3` **23**。RECHECK: `awk '/HISTORY-BEGIN/{p=1} p&&/HISTORY-END/{p=0;next} !p' docs/SPLITUNIFY_SPEC.D-002.md | rg -o 'Task 9\.[0-9a-z]+|validate_split_pair_integrity|metadata\.split_unify' | sort | uniq -c | sort -rn | head -10`。隱式 registry 反例：腳本內硬編碼 `Task 9.2b` 仍 13>3。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[BLOCKING] 信心度=High。照裁定做會在「定義決定邊界」一步停滯。**修法**：F3 改為「每決定 `id` + `grep_patterns[]` + `max_hits`」機械表（composer R1 YAML 或 SPEC 內單檔表）；**可行性**：表驅動 rg 計數，R1 已論證；無表則 F3 必須降級為具名殘留。

---

## COMPOSER-R2-P0-02

**斷言**: 第二版裁定選擇的強制掛載點（`PostToolUse: Edit|Write`）**不涵蓋** Bash／生成器寫檔，與 codex R1 已證之產出端洞同型，強制力在實務路徑上為假。

**碼證**: `.claude/settings.json` L189 `matcher: Edit|Write`（doc 八支）；L180 僅 `ts_stamp` 含 `Bash`。`narrow_check_router.sh` L36：「經 Bash 重導…不觸發」。`reconcile_build.sh`／`committee_run.sh` 等產出 `synth.md` 典型走 Bash。RECHECK: `rg -n 'matcher' .claude/settings.json`；`sed -n '33,37p' scripts/narrow_check_router.sh`。

**來源摘要**: .claude/settings.json#77cb54336328;scripts/narrow_check_router.sh#61985829c6f4

[BLOCKING] 信心度=High。照裁定做：主委 `bash scripts/reconcile_build.sh` 寫 synth ⇒ F1–F3 **不跑**。**修法**：強制邊界改為 commit hook + `gate.sh register-output` + dispatch token 核發前；或 `Bash` matcher 增列 doc 檢查（成本見 P1-03）。

---

## COMPOSER-R2-P1-01

**斷言**: 第二版裁定「判定採 grok 零維護、強制採 composer」在邏輯上自相矛盾——零維護的 F3 需要決定→token 表，而該表正是 composer 所稱 registry。

**碼證**: `synth.md` L29 逐字「純計數，零維護，**不需** composer 之 YAML registry」且「強制…寫檔當下報」；同段 F3 要求「單一決定活文計數」。grok R1 F3 成效指標＝`Task 9.2b` 活文 ≤3（`synth.md` L151）——token 選擇本身即維護項。RECHECK: 對讀 L29 與 L151。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MAJOR] 信心度=High。**修法**：承認 F3 最小表為必要資料結構（可內嵌 `narrow_check_router` 路由表，不必獨立 epic）；刪「零維護」宣稱。

---

## COMPOSER-R2-P1-02

**斷言**: 主委第二版裁定**完全忽略** codex R1 第②條（審查輸入只餵當前段落＋本輪 diff），而該條可能是三家中成本最低且直接對應使用者「新一輪又看到前幾輪修完文字」的修法。

**碼證**: R1 codex P1-02 碼證：R11=12、R12=13 條全打前版修法；`synth.md` L16 D2 處置寫「codex 另主張…一併採納」但 L29 新裁定正文無輸入隔離。R12 synth：「十三條無一為新面向」。RECHECK: `rg '當前段落|本輪 diff|review command' handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md HANDOFF.md` → 裁定段 0 命中。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a;handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MAJOR] 信心度=High。會怎麼失敗：先上 F1–F3 花數週，考古再審占比不變。**修法**：必答 4 Phase A 先行；F1–F3 待 registry 就緒後再接。

---

## COMPOSER-R2-P1-03

**斷言**: 將 F1–F3 掛入既有八支 PostToolUse 鏈，每次 `Edit|Write` 增加 **~4.4s** 延遲（其中 `list_active_mechanisms.sh` 單支 **2.92s**），主委未評估對編修節奏的影響。

**碼證**: 見必答 3 量測表；`list_active_mechanisms.sh` 對任意 SPEC 路徑每次皆執行。再加 F1–F3 腳本預估 +0.5–2s（`obligation_block_check` 同型）。RECHECK: 必答 3 命令。

**來源摘要**: .claude/settings.json#77cb54336328

[MAJOR] 信心度=High。**修法**：F1–F3 只經 `narrow_check_router` 窄觸發 `docs/SPLITUNIFY_SPEC.D-002.md`；`list_active_mechanisms` 改 pre-commit 或降頻。**可行性**：路由器已存在，改表不增第九支全域 hook。

---

## COMPOSER-R2-P2-01

**斷言**: 第二版裁定記錄本身重犯 R1 主因——同一裁定複述於 `HANDOFF.md` 與 `synth.md` 兩處，無單一權威 anchor。

**碼證**: `HANDOFF.md` L32 與 `synth.md` L29 同段「新裁定＝兩家各取一半」；`rg -c '新裁定|兩家各取一半' HANDOFF.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → 各 **1**。RECHECK: 同上。

**來源摘要**: HANDOFF.md#1b24c621be54;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MINOR] 信心度=High。裁定程序病徵。**修法**：HANDOFF 只留指標；裁定正文僅 `synth.md` 路線段。

---

## COMPOSER-R2-P2-02

**斷言**: F3 門檻「≤3」為 grok R1 隨手範例（標題＋驗收＋mutation），未對 v13 之 30+ 決定面做分佈驗證，套用後必然大量誤擋或大量漏擋。

**碼證**: 活文 `Task 9.1` **14** 次、`M-SU-D2-04` **5** 次——皆 >3；若僅擋 `Task 9.2b`，其他決定仍複述 5–11 次（R1 量測）。grok R1 L151 成效指標未附抽樣 n 或允許列表。RECHECK: 必答 1 的 `uniq -c` 輸出。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-grok.md;docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24

[MINOR] 信心度=Medium。**修法**：先量測每決定活文分佈再定 `max_hits`；禁止全域常數 3。

---

## COMPOSER-R2-P3-01

**斷言**: 存在第四條路——**僅 codex ② 審查輸入隔離 + 單檔決定表**——可在不新開 epic、不掛全域第九 hook 下，先降「考古再審」占比，且與第二版裁定不衝突。

**碼證**: 必答 4 Phase A 無新腳本；Phase B 一列 `narrow_check_router` 路由。R12 停輪已觸發 ⇒ 規格審查應停，不應先上未驗證 F3。**修法**：下一張票驗收 Phase A；成效不達再啟 YAML（HANDOFF L33 成效條款）。**可行性**：brief 範本改動 + 既有路由器，本輪未跑 impl。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a;scripts/narrow_check_router.sh#61985829c6f4

[MINOR] 信心度=Medium。程序建議，非阻斷第二版本身。

---

ASSUMPTIONS_VERIFIED: brief §0 四條 assumed 均已用 shell 量測否證；PostToolUse 八支延遲、活文 token 計數、裁定複述、settings matcher 均已實跑  
TESTS_RUN: `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r2-composer.md --family composer`（交件前自檢）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R2-P0-01,COMPOSER-R2-P0-02,COMPOSER-R2-P1-01,COMPOSER-R2-P1-02  
CLOSED:  
STATUS: DONE
## GROK-R2-P0-01

**斷言**: 第二版裁定同時主張「F3 單一決定活文計數 ≤3」與「不需任何 registry／token 清單」——二者互斥；照原文實作會在「閘要數哪個字串」這一步失敗或淪為腳本內沉默名單。

**碼證**: 裁定原文「單一決定活文計數降至三以下…**不需** composer 之 YAML registry」（`handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md:29`）。實跑活文：`Task 9.2b`×19 可自動抽，但 R12 病灶 token `metadata.split_unify`×11、`validate_split_pair_integrity`×8 **不是** Task 文法，無名單則閘不知數它們。RECHECK：必答 1 之 Python 區塊。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7

[BLOCKING] 信心度=High。會怎麼失敗：實作者卡死／只數 Task 而漏真病灶／把 pattern 寫進腳本卻仍宣稱零 registry。**修法**：把 F3 正式窄化為「自動 Task-token 密度」；非 Task 決定列為具名殘留或接受最小名單（誠實承認那是 registry）。可行性＝本輪已跑出 Task Counter 與非 Task 計數對照。

---

## GROK-R2-P0-02

**斷言**: 第二版把「強制」掛在既有 `PostToolUse: Edit|Write`，等於選用已被文件化、且 R1 codex 已揭的洞當唯一強制點——Bash／生成器寫檔不觸發該 matcher。

**碼證**: `.claude/settings.json:189` matcher=`Edit|Write`（八支文件檢查）；`scripts/doc_format_precheck.sh` 檔頭 L17–18 自白「經 Bash 重導寫出的檔…都不會觸發 hook」；`scripts/gov_check.sh` L226–229 亦承認須靠 1b 補洞。第二版原文只寫掛 PostToolUse，**未**要求同步掛 1b／派工邊界。RECHECK：`python3 -c` 印 settings PostToolUse matchers；`sed -n '14,22p;226,229p' scripts/doc_format_precheck.sh scripts/gov_check.sh`。

**來源摘要**: .claude/settings.json#77cb54336328;scripts/doc_format_precheck.sh#e39ce0d21db0;handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a

[BLOCKING] 信心度=High。會怎麼失敗：主委用 Bash／`cx_run`／生成器改 SPEC → 新密度閘沉默放行，與「違反即寫檔當下報」文案不符。**修法**：沿用既有三層（PostToolUse 警告＋`gov_check` 1b 改動掃描＋派工硬擋），新判定三處同掛；或具名登記「Bash 洞殘留」且不得宣稱已強制。可行性＝doc_format 已是該樣板，複製掛載點即可。

---

## GROK-R2-P0-03

**斷言**: 主委第二版裁定完全忽略 codex R1 第②條（審查輸入只餵當前段落＋本輪 diff），而該條可能是三家中對「重審已修文字」最直接、且零新工具的一等修法。

**碼證**: brief 必攻點 6 與 R1 codex `CODEX-R1-P1-02` 修法段；synth 路線裁定段（L22–31）只字未提「輸入範圍／diff-only／anchor 不得落歷史」。RECHECK：`grep -n 'diff\|當前段落\|輸入範圍\|HISTORY\|審查輸入' handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → 路線段無採納句（D2 群曾寫「一併採納」卻未進入「新裁定」操作句）。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7

[BLOCKING] 信心度=High。會怎麼失敗：即使 F1 之後活文較乾淨，派工仍餵全文 → 委員繼續打沿革／前輪敘事；工具閘無法替代輸入隔離。**修法**：新裁定操作句必須顯式採納 codex②（brief 範本＋拒收歷史 anchor）；可與密度閘並行，且應**先**做。可行性＝只改派工契約，不需新腳本。

---

## GROK-R2-P1-01

**斷言**: 主委把第二版裁定完整複寫進 `synth.md` 與 `HANDOFF.md` 兩處，正是 R1 判定的主因（一決定多落點）在治理敘事上的即時再犯。

**碼證**: `grep -n '判定採 grok\|新裁定' HANDOFF.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → HANDOFF:32 與 synth:29 兩段並列全文（非指標）。RECHECK：重跑該 grep；對讀兩段是否需同步改一字。

**來源摘要**: HANDOFF.md#1b24c621be54;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MAJOR] 信心度=High。會怎麼失敗：R2 若修裁定，必漏一處 → 下輪又打「裁定文檔互斥」。**修法**：權威只留 synth 路線段；HANDOFF 改 `見 handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#路線裁定`。可行性＝刪複述、留指標。

---

## GROK-R2-P1-02

**斷言**: 「掛進既有鏈、不新開 epic」被用來主張「不算擴建治理工具」，但新增第 9 支 PostToolUse 檢查腳本在維護／失敗面與「新建腳本」無本質差別，只是包裝不同。

**碼證**: 現鏈已 8 支（settings L193–222）；brief assumed「掛進既有檢查鏈在制度上不算擴建」標 **沒跑**。composer R1 要的也是「一個 checker 腳本」——差異在有無 YAML，不在「有沒有新腳本」。RECHECK：數 settings 內 Edit\|Write hooks；對讀 composer P0 修法與第二版「強制採 composer」實際只採掛載、不採 YAML。

**來源摘要**: .claude/settings.json#77cb54336328;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7;handoffs/20260912-docrot-x-consult-r1-composer.md#4b16eee31672

[MAJOR] 信心度=Medium。會怎麼失敗：用話術繞過「不再擴建」自傷規則，日後第 10、11 支同理擠入。**修法**：若加腳本，就承認「小擴建」並受成效判準約束；或把 F1／窄 F2 併入既有 `obligation_block_check`／HISTORY 規則，**零新檔**。可行性＝obligation 已管歷史專區，F1 與之同向。

---

## GROK-R2-P2-01

**斷言**: 閾值「≤3」來自 R1 grok 對 Task 掛名的示意（標題＋§V＋mutation），未經驗證，且對現行 D-002 活文立刻全滅（7／8 個 Task token >3），不宜未經校準就寫進強制閘。

**碼證**: R1 grok F3 原文「目標 ≤3：標題+§V 掛名+mutation 掛名」；本輪 Counter 最低超標亦為 8。RECHECK：必答 1 Python。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-grok.md#f14daa65418b;docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24

[MINOR] 信心度=High。會怎麼失敗：閘一掛上 SPEC 無法改、或被迫把閾值偷偷改大假綠。**修法**：先收縮活文；閾值改由「收縮後基線＋裕度」校準，或第一期只報 warn。可行性＝先量基線再設限。

---

## GROK-R2-P2-02

**斷言**: 既有 Edit\|Write 鏈單次中位已 ≈4.97s（obligation 獨佔 ≈4.26s）；主委「成本未評估」屬實，但**新增** F 類計數不是延遲主因——未評估的是鏈上已有巨石與誤擋面，而非毫秒級新判定。

**碼證**: 本輪計時表（必答 3）；F 類計數 ≈2.1ms。RECHECK：對 `obligation_block_check.sh` 餵 SPEC 的 Edit JSON 單次 `perf_counter`。

**來源摘要**: .claude/settings.json#77cb54336328;scripts/obligation_block_check.sh

[MINOR] 信心度=High。會怎麼失敗：討論焦點誤放在「再加一支會不會慢」，忽略寫每次 SPEC 已付 ~5s 與 Bash 洞。**修法**：成本評估改問「掛載是否含 1b／誤擋 path filter／遷移序」；延遲優化另打 obligation，不擋 F1。可行性＝本輪已分拆測量。

---

ASSUMPTIONS_VERIFIED: R1 三家原文與 synth 兩版裁定已對讀；PostToolUse 八支已數；F1／F2／Task-auto F3／非 Task token 已對 D-002 實跑；Edit\|Write 鏈八支中位耗時已測；裁定在 synth＋HANDOFF 雙寫已 grep  
TESTS_RUN: 上列 python 計數與 hook 計時（本機實跑；obligation median≈4.259s；鏈 SUM≈4.965s；F-check≈2.1ms）；交件前 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r2-grok.md --family grok`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀；僅新增本產出與交接檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: blocked
BLOCKED-BY: GROK-R2-P0-01,GROK-R2-P0-02,GROK-R2-P0-03
CLOSED:
STATUS: DONE
