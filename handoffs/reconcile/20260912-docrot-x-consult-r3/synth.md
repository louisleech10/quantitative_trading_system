# Reconcile — 20260912-docrot-x-consult-r3

**來源** 20260912-docrot-x-consult-r3-codex.md, 20260912-docrot-x-consult-r3-composer.md, 20260912-docrot-x-consult-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：HANDOFF.md

（本輪為 consult，無 SPEC／TODO 檔；TODO 權威＝下方「定案 TODO」指標）

本輪性質：三家依 brief 寫出可驗收 TODO，主委只擇一家原文、不寫折衷。三家對「根因是否被 TODO 涵蓋」皆答是（codex 必答 6 以 P1-01/02/04/05/06/07 為前提、composer 必答 6「可進實作」、grok「是（本家）」）。分歧點依 brief 硬約束「三家意見不同時取**最窄**能過三問者，不取聯集」裁定，逐條具名於下表。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **C1 根因：D1／D2 機械化不足以降輪數；第三根因＝決議→實作無可核對 TODO（三家）**——「D1/D2 是候選根因，但 brief 沒有能」「brief 假設「D1／D2 機械化後輪數會」「僅機械化 D1／D2 不足以降低文檔輪數——」 | P0 | CODEX-R3-P1-01, COMPOSER-R3-P1-01, GROK-R3-P0-03 | 採納（brief 之 assumed「機械化後輪數就降」三家一致判未驗證；輪數只作 stop／measurement signal 不作因果證明；HANDOFF 只寫「試點待量」。本收斂之定案 TODO 即為「決議→實作」的唯一可核對契約，主委禁表外機制） |
| **C2 `gov_check` 段 1b 對 `--dupes` 命中 fail-closed（兩家 finding；composer Task 3.2 同向）**——「目前 D1 的寫入／改動掃描仍是 warn-o」「現行 `gov_check.sh` 段 1b 對」 | P0 | CODEX-R3-P1-05, GROK-R3-P0-01 | 採納→Task 1.3（範圍限本次 diff 之 `docs/*.md`；hook 層維持 warn；不改 `.claude/settings.json`） |
| **C3 `completeness_check.sh` 拒收落在 `HISTORY-BEGIN..END` 之 anchor（grok P0；codex Task 1.2、composer Task 3.1 同向）**——「`completeness_check.」 | P0 | GROK-R3-P0-02 | 採納→Task 1.4（只解析既有 `**碼證**`／`**來源摘要**` 之 `path:line`；無 `path:line` 不觸發；不新增語意閘） |
| **C4 `dupes()` 之 `HISTORY-BEGIN` `break` 撤回，改區間 skip（三家）**——「`dupes()` 在第一個 `HISTOR」「主委五項 #3（`dupes()` `bre」「`dupes()` 在首個 `HISTORY」 | P1 | CODEX-R3-P1-04, COMPOSER-R3-P2-01, GROK-R3-P1-01 | 採納→Task 1.1（五項 #3 **撤回**；grok 構造反例＝HISTORY 後活文雙「共 7 條」現行 stderr 空；mutation「HISTORY 後活文仍報」） |
| **C5 `dupes()` 收窄至 `_RE_TOTAL_ITEMS`（三家同向，grok 獨立列 finding）**——「`--dupes` 同時掃三 regex 超出」 | P1 | GROK-R3-P1-02 | 採納→Task 1.2（五項 #2 **改寫**：只掃「共 N 條」；composer 實跑 GAP3 之「五維度」誤報為釘子） |
| **C6 `verification_claim_check.py` 對「三家共同結論」類背書語須 audit 佐證（三家）**——「`verification_claim_」（CODEX-R3-P1-06）「`verification_claim_」（COMPOSER-R3-P2-02）「`verification_claim_」（GROK-R3-P1-03） | P1 | CODEX-R3-P1-06, COMPOSER-R3-P2-02, GROK-R3-P1-03 | 部分採納→Task 1.5（**採 grok 原文**：封閉字面 `三家共同結論\|三家一致落地`、同 task-id 之 `committee_family_result` 家數 ≥ roster、允許既有 `VERIFY-EXEMPT:`。**不採** codex 之「REF／VERIFY 須與 audit `output_path`／`output_sha256` 逐項對證、commit_msg 不接受 EXEMPT」——較寬，依「取最窄」裁定，具名殘留） |
| **C7 碼證須能指向碼／架構：只改範本字面，不加 completeness 硬擋（三家）**——「current block＋diff 只是輸」「「current block＋diff」*」「只限制審查輸入為 current block」 | P1 | CODEX-R3-P1-02, COMPOSER-R3-P1-02, GROK-R3-P2-01 | 部分採納→Task 1.6（**採 grok 原文逐字句**：架構／行為／數值向主張之碼證須含 `path:符號`／`path:函式`／可重跑命令，僅文檔字面差異者最高 P3 標 `doc-literal-only`；`new_brief.sh` 必答骨架加一句。**不採** codex 之 `CODE-ANCHOR`／`ARCH-EDGE`／`MUTATION` 三必填語法＋`completeness_check --single` fail-closed（新增機械閘面、較寬）；composer 之 `COMMITTEE_FINDING_TEMPLATE.md` 規則 2 逐字改法與 grok 同目的，依「取一家原文不聯集」未採，具名殘留） |
| **C8 是否須先開 `docs/DOCROT_X_SPEC.md`＋`TODO.md`（codex 獨主張；composer／grok 明示不需）**——「把 consult 產出的 TODO 直接當成可」 | P1 | CODEX-R3-P1-07 | 駁回（2:1 且 grok 論證「另開 SPEC 會複製 D1」；改動全在既有 `scripts/`／`templates/`／`tests/governance/`；本收斂之定案 TODO 含每條檔、驗收 rc、mutation、停止條件，即最小契約。codex 所要之「allowed files／stop gate」由下方「定案 TODO」段承載，不另開 docs 檔） |
| **C9 佔位偵測：保留、宣稱收窄；不改成欄位完整行比對（兩家）**——「以封閉字面 `grep -qF` 掃整份 bri」「骨架佔位偵測可保留為 E3 輔助，但「對手寫」 | P2 | CODEX-R3-P1-03, GROK-R3-P2-02 | 部分採納→Task 1.8（五項 #1 **改寫**：文案改「只擋 `new_brief.sh` 骨架原樣派出；不涵蓋手寫 brief；合法引用骨架字面會誤拒，誤拒時改寫引用或 `VERIFY-EXEMPT`」。**不採** codex 之改為 generator 欄位完整行比對＋允許 quoted/fenced——較寬；「合法引用會誤拒」登記為具名殘留，觸發即改寫引用） |

**五項主委試點最終裁定**（三家一致處）：#1 改寫（Task 1.8）｜#2 改寫收窄（Task 1.2）｜#3 撤回（Task 1.1）｜#4 採納（hook 層 warn；硬擋只在 1b）｜#5 改寫為「D-002 單檔試點」，刪「F1 已到收斂點」。

**D3／D4／D5**：D3 不做（三家一致；需語意判斷，具名殘留）｜D4 不做（composer 主張 ROADMAP 加一句、grok 不做、codex 未提；取最窄＝不做，待 TODO 落地後下一票輪數仍不降再議）｜D5 不做（三家一致；屬使用者看板偏好，已在 HANDOFF 列待使用者）。

**定案 TODO（唯一權威＝`handoffs/20260912-docrot-x-consult-r3-grok.md` 必答 2 表 Task 1.1–1.8 逐字，本檔不複述）**。實作補充只有兩點，皆取自他家原文而非主委自創：
- 測試落點（grok 表未指定檔名）：Task 1.1／1.2／1.3 之 mutation 進既有 `tests/governance/test_docrot_f2_total_items_count.py`、Task 1.4／1.8 進既有 `tests/governance/test_docrot_e3_brief_placeholder.py`（codex Task 1.2／1.3／2.1／2.2 原文）；Task 1.5 進 `tests/governance/test_docrot_claim_committee_backing.py`（composer Task 3.5 原文；codex 指 `test_verify_gate.py`，該檔已在 CLAUDE.md 具名為探針空心假綠，故不採）。
- 允許檔（codex Task 0.1 所要之 allowed files，改由本段承載）：`scripts/spec_count_audit.py`、`scripts/gov_check.sh`、`scripts/completeness_check.sh`、`scripts/verification_claim_check.py`、`scripts/brief_conformance_check.sh`、`scripts/new_brief.sh`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、上列三個測試檔、`HANDOFF.md`。**其餘檔一律不動**；表外機制一律不做。

**成效判準（三版擇一，採 grok 必答 3 原文；理由＝較嚴且 (a) 項由 Task 1.4 機械化）**：`doc_friction_ratio`＝（該輪 synth 附錄中 (a) 碼證／來源摘要之 `path:line` 落在標的 SPEC `HISTORY-BEGIN..END`，或 (b) 斷言命中封閉字面 `多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張` 之 canonical finding 數）÷（該輪附錄 canonical finding 總數）；基線 D-002 R11＝12/12＝1.00、R12＝13/13＝1.00；及格線＝下一張中大票（SPLITUNIFY b9，標的仍 `D-002`）之 review-r1 與 review-r2 兩輪均 ≤0.30，且每輪 finding 總數 ≤20。不達 ⇒ 本 TODO 裁定失敗，只准回到「是否要最小 token 表」討論，禁同時開新 epic。codex 之「首輪 heading ≤13」與 composer 之「關鍵字占比 ≤56%」未採，具名於此供追溯。

**F1 範圍（必答 5，三家一致）**：下一張中大票＝SPLITUNIFY b9（`D-002`），F1 試點適用，不先擴到別票 SPEC；若插入其他中大票，該票 brief 須二選一：開場先做同型活文收縮，或明示本成效句不適用。

**進實作條件（必答 6）**：本收斂三家戳記 APPROVED ＋ `debt_clear` rc=0 ＋ 使用者白話審閱放行 → 只做 Task 1.1–1.8 → 派三家審碼取戳記後才算完成。commit 訊息在 Task 1.5 上線前禁用「三家共同結論」類字眼。

Verdict：可合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P1-01

**斷言**: D1/D2 是候選根因，但 brief 沒有能把「少燒輪」與「機械閘通過」連成可反駁因果的成效定義；直接把兩根因機械化後宣告會降輪數會把輪數下降、findings 改名、或 scope 變窄混為成功。

**碼證**: brief 的 `assumed: 「文檔多輪」的根因就是 R1 的 D1／D2，把 D1／D2 機械化後輪數就會降` 未附前後對照；`handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md:19` 記錄 R1–R12 findings `15/11/15/8/11/16/15/14/21/13/12/13` 且 R12 `13` 條無一新面向。VERIFY：`rg -c '^## (CODEX|COMPOSER|GROK|CLAUDE|AGY)-R[0-9]+-P[0-3]-[0-9]{2}$' handoffs/reconcile/20260911-splitunify-b9-review-r{1..12}/synth.md`（各檔輸出上述 12 個數）。RECHECK：對下一個 target synth 以同一 heading regex 計數，並按本檔成效句與前一輪比較。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#4303382a0d83;handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MAJOR] 信心度=High。修法：把「輪數」定為 stop/measurement signal，不當成因果證明；每個實作 TODO 同時記錄「命中哪個根因、mutation 轉紅、target synth canonical heading count」。可行性證據：R1–R12 的 12 份 synth 已存在且 heading 可由同一 regex 計數，基線為 `164/12=13.67`；下一張 target round 的總數嚴格低於平均值，即 `≤13`，才算輪數 signal 通過；若只改 scope 或 findings 不再帶 active anchor，則另判失敗。

## CODEX-R3-P1-02

**斷言**: current block＋diff 只是輸入邊界，不是「finding 必須指向碼／架構」的結構契約；現行 brief、synth cluster 與 completeness 都可讓純文字爭論帶著合法四欄通過。

**碼證**: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:18-22` 只規定 current block／diff 與歷史排除，`:28` 允許「章節／可搜尋原文短句」，`:75-76` 的欄位契約也未要求 symbol、path:line 或 mutation；`scripts/completeness_check.sh:226-228,350-353` 只設 `seen_assert`／`seen_code`／`seen_digest`。VERIFY：`nl -ba templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md | sed -n '18,30p;75,90p'`、`nl -ba scripts/completeness_check.sh | sed -n '226,228p;350,353p'`。

**來源摘要**: templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#854df5fbe372;scripts/completeness_check.sh#49d4fa0f4217;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167e

[MAJOR] 信心度=High。修法：在既有 prompt／finding template 增加 `CODE-ANCHOR: <repo-relative path>:<line>`、`ARCH-EDGE: <producer|contract|consumer>`、`MUTATION: <可執行破壞>` 三個必填語法，並讓 `completeness_check.sh --single` fail-closed；current block 改成逐列列出 path、symbol/line、架構角色與 diff 指令。可行性證據：現有 checker 已在 `--single` 以 `strict=1` 做欄位驗證，增加三個狀態欄不需新腳本；quoted prose 沒有 CODE-ANCHOR 即不能成為 finding。

## CODEX-R3-P1-03

**斷言**: 以封閉字面 `grep -qF` 掃整份 brief 的 placeholder 只能保護 `new_brief.sh` 原樣骨架，不能保證輸入隔離，且會把合法的 quoted/fenced placeholder 文字誤判為未填。

**碼證**: `scripts/brief_conformance_check.sh:330-353` 對 brief 全文逐字 `grep -qF`，沒有欄位、quote 或 fence scope；同檔 `:328` 自承擋不住手寫「整份檔」；`tests/governance/test_docrot_e3_brief_placeholder.py:50-132` 只有填妥、未填與 generator skeleton 三類測試，沒有合法引用字面負例。VERIFY：`nl -ba scripts/brief_conformance_check.sh | sed -n '325,353p'`、`rg -n 'quoted|fenced|合法引用' tests/governance/test_docrot_e3_brief_placeholder.py` → 無命中。

**來源摘要**: scripts/brief_conformance_check.sh#1ba0ef67016f;tests/governance/test_docrot_e3_brief_placeholder.py#61e8f637cc53;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167e

[MAJOR] 信心度=High。修法：保留這個檢查但改成 generator 欄位的完整行／欄位範圍比對；允許 fenced/quoted example，並明示「不涵蓋手寫 brief 的整份檔語意」。可行性證據：既有測試已能從 `new_brief.sh` 產生真實 skeleton 並轉紅；只需加入 quoted/fenced mutation，便可同時驗「未填仍紅、合法引用為綠」。

## CODEX-R3-P1-04

**斷言**: `dupes()` 在第一個 `HISTORY-BEGIN` 或 `## 沿革` 直接 `break`，不是 BEGIN～END 的區間 skip；若歷史 marker 前移或現行段落出現在 marker 後，後半段的真相源會靜默漏掃。

**碼證**: `scripts/spec_count_audit.py:112-118` 在 marker 行直接 `break`，從未讀 `HISTORY-END`；既有 F2 測試 `test_dupes_ignores_history_section` 只驗沿革在文件尾端。VERIFY：`nl -ba scripts/spec_count_audit.py | sed -n '102,126p'`。

**來源摘要**: scripts/spec_count_audit.py#cbcbc959321d;tests/governance/test_docrot_f2_total_items_count.py#48cbaeb20fe1;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167

[MAJOR] 信心度=High。修法：同一函式改成 `in_history` state machine：遇 BEGIN 設 1、遇 END 設 0、只在 state=1 skip，禁止 `break`；`dupes()` 同時收窄為 `_RE_TOTAL_ITEMS`，不把 R2 窄 F2 擴回三種 regex。可行性證據：這是既有逐行 scanner 的兩個局部狀態／regex 修改；`current→HISTORY→current` mutation 可在現有 F2 測試中證明後段仍報。

## CODEX-R3-P1-05

**斷言**: 目前 D1 的寫入／改動掃描仍是 warn-only：`--dupes` 的命中既不改 hook rc，也不進 `gov_check` 的 `_docbad`，所以寫入時硬擋覆蓋率仍為零。

**碼證**: `scripts/gov_check.sh:269-274` 明載不進 `_docbad` 且 `|| true`；`scripts/spec_xref_hook.sh:57-66` 同樣維持 warn-only；review-r1 current block G5 已將最小擋門定為 gov_check 段 1b。VERIFY：`nl -ba scripts/gov_check.sh | sed -n '269,274p'`、`nl -ba scripts/spec_xref_hook.sh | sed -n '57,66p'`、`rg -n 'G5|fail-closed|_docbad' handoffs/reconcile/20260912-docrot-x-review-r1/synth.md | head`。

**來源摘要**: scripts/gov_check.sh#a42330392eb5;scripts/spec_xref_hook.sh#aa3cf7fce02a;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167e

[MAJOR] 信心度=High。修法：只在既有 `gov_check.sh` 段 1b 的本次 `docs/*.md` diff 迴圈把 `--dupes` 命中計入 `_docbad`；hook 保持提示層，不改 `.claude/settings.json`，並用既有 F2 測試加一個 duplicate-doc mutation 期待 gov_check rc≠0。可行性證據：段 1b 已有 `_docbad`、`_docn` 與 fail path；不需新腳本，也不需掃全庫。

## CODEX-R3-P1-06

**斷言**: `verification_claim_check.py` 目前知道 `commit_msg` 是 operational context，也有 committee audit registry，但沒有把「三家共同結論／三家一致／consensus」背書語與特定 audit event 綁定；因此未審機制仍可借用共識 provenance。

**碼證**: `scripts/verification_claim_check.py:46-58` 的 polarity regex 沒有 consensus token；`:598-611` 的 registry 只回傳 output path/hash；`:795-807` 只將 commit message 分類為 `commit_msg`；`:2047-2061` 的 commit-msg 路徑只呼叫 `check_unit`，沒有要求 `task_id`／`round_id`／`committee_output` 對證。VERIFY：`rg -n -C 3 'STRONG_POLARITY_RE|commit_msg|committee_output|task_id|round_id' scripts/verification_claim_check.py`。

**來源摘要**: scripts/verification_claim_check.py#1eff89b0566d;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167

[MAJOR] 信心度=High。修法：在既有 commit-msg 路徑加入封閉 consensus token 集；命中時必須同時有可解析的 `REF`／`VERIFY` 指向 committee output，且 audit JSON 的 `task_id`、`round_id`、output path/hash 與該證據一致，否則 rc=1；commit_msg 不接受一般 `VERIFY-EXEMPT`。可行性證據：既有 audit log 已有 `committee_output`、`task_id`、`round_id`、`output_path`、`output_sha256` 欄位，既有 `_committee_registered_files` 可作對證資料源。

## CODEX-R3-P1-07

**斷言**: 把 consult 產出的 TODO 直接當成可派工實作規格，會再次重演「決議→實作無可核對 TODO」；目前 `docs/` 沒有 DOCROT SPEC/TODO 的 current contract、allowed files、mutation map 或 stop gate。

**碼證**: brief 已把「`docs/` 下不存在任何 DOCROT 的 SPEC 或 TODO；主委從決議直接進碼」列為 fact-verified；`HANDOFF.md:14` 又記錄五項先實作後被 review-r1 全 blocked。RECHECK：`ls docs | grep -i docrot` 應為空（brief supplied fact），`rg -n 'allowed files|mutation|預期 rc|stop' handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md`。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#4303382a0d83;HANDOFF.md#a1160a93cee9;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167

[MAJOR] 信心度=High。修法：先建立最小 `docs/DOCROT_X_SPEC.md`＋`docs/DOCROT_X_TODO.md`，只承載本輪核可的七項 Task、current input boundary、允許既有檔、每條 mutation/rc、停止條件與 `§N` 殘留；這不是新 epic 或新腳本。可行性證據：兩份文件可用既有 `doc_format_precheck.sh` 檢查，TODO 欄位可由 `rg`/既有測試機械驗收，且不需先建全庫 registry。

### 五項主委試點逐項裁定

| # | Verdict | 本輪核可的逐字規格 |
|---|---|---|
| 1 | 改寫 | 保留 placeholder guard，但只拒收 `new_brief.sh` 產生的 generator 欄位完整行；quoted/fenced example 通過；不得宣稱涵蓋手寫 brief 的「整份檔」語意。E8 Phase A 的真正硬契約由 `completeness_check.sh` 的 HISTORY-anchor 與 code-anchor 檢查承擔。 |
| 2 | 改寫 | `spec_count_audit.py --dupes` 只掃 `_RE_TOTAL_ITEMS` 的 `共 N 條`；不採三 regex 聯集。其結果先由 hook 提示、由 `gov_check` 段 1b 對本次 diff fail-closed；誤報基線留在既有 F2 mutation。 |
| 3 | 撤回 | `HISTORY-BEGIN` 的 `break` 撤回；沿革只可排除 BEGIN～END 區間，marker 後的現行內容必須繼續掃描。 |
| 4 | 改寫 | `spec_xref_hook.sh` 的 `--dupes` 保留 warn-only 觀測層；不得以 PostToolUse 宣稱硬擋。硬擋只放既有 `gov_check` 段 1b 的 diff 範圍，沿用現有 hook/settings，不新增掛載或腳本。 |
| 5 | 改寫 | F1 標為 `D-002 trial`，不宣稱 DOCROT 全庫收斂；成效只對下一張實際 target SPEC 的 current block／active anchor／round count 計算。若下一張票不是 D-002，先重新指定 target，不自動擴大範圍。 |

### 必答 2 — 可驗收 TODO（7 條；不新增腳本、不開新 epic）

| Task | 改哪個檔／做什麼 | 驗收指令與預期 rc | mutation；擋根因／不做再燒幾輪／機械量 |
|---|---|---|---|
| Task 0.1 | 新增最小 `docs/DOCROT_X_SPEC.md` 與 `docs/DOCROT_X_TODO.md`；SPEC 只含 `§RISK/§A/§C/§G/§V/§R/§N` 的本輪 contract，TODO 只含本表、allowed files、禁做、mutation、rc、stop。 | `bash scripts/doc_format_precheck.sh docs/DOCROT_X_SPEC.md`；同命令替換 TODO；兩者 rc=0；`rg -q 'CODE-ANCHOR|MUTATION|預期 rc|停止' docs/DOCROT_X_TODO.md` rc=0。 | 刪掉任一 Task 的檔案、rc 或 mutation → `rg`/SPEC-TODO coverage 檢查紅；根因 D3；不做至少再開一輪 consult（本輪 R3 即由五項未審折衷觸發）；機械量=Task 行數、每行必有 path/command/rc/mutation。 |
| Task 1.1 | 改 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 的輸入邊界／§0／canonical 四欄與 `templates/COMMITTEE_FINDING_TEMPLATE.md` 四欄；current block 逐列要求 `CODE-ANCHOR`＋`ARCH-EDGE`，finding `碼證` 要求 `CODE-ANCHOR`＋`MUTATION`。 | `rg -n 'CODE-ANCHOR:|ARCH-EDGE:|MUTATION:' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md templates/COMMITTEE_FINDING_TEMPLATE.md` rc=0；既有 E3/F2 scoped pytest rc=0。 | 去掉任一 token 或把 code anchor 改回「章節短句」→ template probe 紅；根因 D1/D2/D3；不做下一輪仍可在 diff prose 爭字面，至少重燒一輪；機械量=每個 current-block row 與每個 finding heading 的 token presence。 |
| Task 1.2 | 改 `scripts/completeness_check.sh` 的 `--single` strict body parser 與既有 `tests/governance/test_docrot_e3_brief_placeholder.py`；解析 `CODE-ANCHOR: path:line`，命中 `HISTORY-BEGIN..END` 行區間即 fail，缺 anchor/mutation 也 fail。 | `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` rc=0；正例 current anchor rc=0、history anchor mutation rc=1。 | 將 anchor 移入 D-002 HISTORY 區而測試仍綠 → mutation 紅；根因 D2；不做下一輪可再次審已作廢段，R11/R12 已示範連續兩輪；機械量=history range 判定 rc。 |
| Task 1.3 | 改 `scripts/brief_conformance_check.sh` 的 placeholder 判定與既有 E3 測試；由 substring grep 改為 generator 欄位完整行／scope 比對，保留 skeleton fail、允許 quoted/fenced literal。 | `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` rc=0；新增 skeleton rc≠0、quoted/fenced rc=0 mutation。 | 把 `grep -qF` 改回全檔 substring → quoted mutation 紅；根因 D2／輸入隔離；不做會再燒至少一輪 false-positive 修補；機械量=兩個反向 mutation 的 rc。 |
| Task 2.1 | 改 `scripts/spec_count_audit.py:dupes` 與既有 `tests/governance/test_docrot_f2_total_items_count.py`；只保留 `_RE_TOTAL_ITEMS`，BEGIN/END state machine 禁 `break`。 | `pytest tests/governance/test_docrot_f2_total_items_count.py -q` rc=0；`current→HISTORY→current` 期待後段 duplicate stderr 非空、rc=0（scanner 本身仍 warn-only）。 | 把 `for rx` 恢復三 regex 或 marker 後不掃 → narrow/after-history mutation 紅；根因 D1/D2；不做下一輪仍可能漏真相源或因擴張誤報；機械量=regex 集合與 after-END 命中。 |
| Task 2.2 | 改 `scripts/gov_check.sh` 段 1b 與既有 F2 governance test；本次 `docs/*.md` diff 的 `--dupes` stderr 命中計入 `_docbad`，checker 缺失／執行錯誤也 fail-closed；`spec_xref_hook.sh` 保持提示層。 | `pytest tests/governance/test_docrot_f2_total_items_count.py -q` rc=0；duplicate doc mutation 走 1b 期待 `gov_check` rc≠0。 | 不增 `_docbad` 或保留 `|| true` → duplicate-doc gate mutation 紅；根因 D1；不做下張票主委仍能看到 warning 卻繼續，R1 review 已證至少再開一輪；機械量=本次 diff duplicate hit → 1b rc。 |
| Task 3.1 | 改 `scripts/verification_claim_check.py` commit-msg 路徑與既有 `tests/governance/test_verify_gate.py`；封閉 consensus token 命中時，`REF/VERIFY` 必須與 audit JSON 的 `task_id/round_id/output_path/output_sha256` 對上，否則 rc=1。 | `pytest tests/governance/test_verify_gate.py -q` rc=0；無 audit 的「三家共同結論」rc=1；匹配 `committee_output` audit rc=0。 | 移除 audit 對證仍讓無 backing 通過 → provenance mutation 紅；根因 D3；不做未審實作仍可借 commit subject 封口，review-r1 G1/G2 已造成一次 consult 回補；機械量=token × audit event exact-scope 對證。 |

### 成效判準（單句）

以 `handoffs/reconcile/20260911-splitunify-b9-review-r{1..12}/synth.md` 中 canonical `## <FAMILY>-R<n>-P<0-3>-<NN>` heading 為資料來源，分子是下一張 target SPEC 首輪 synth 的 heading 總數、分母是 R1–R12 之 12 份 synth 的 heading 總數 `164`（基線 `164/12=13.67/輪`、中位數 `13`，實際序列 `15/11/15/8/11/16/15/14/21/13/12/13`），及格線為 target 首輪 `≤13` 且所有 P0/P1 finding 均帶 active `CODE-ANCHOR`、history-anchor 命中數為 `0`；此句是可機械計算的 stop signal，不宣稱單靠總量證明因果。

### 必答 4 — 為何現行結構會落到字面，以及逐字改法

現行 brief 只要求 current block／diff，沒有逐列的 code symbol／架構邊界；synth 的群集表只有斷言前綴、來源 ID、處置，沒有 implementation anchor／mutation；SPEC/TODO review prompt 的 `碼證` 又接受章節或原文短句，而 completeness 只驗欄位存在。因此委員能在 diff 內爭字面，仍通過 canonical 四欄。

建議改 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 的輸入邊界、§0 及 canonical 四欄，並同步 `templates/COMMITTEE_FINDING_TEMPLATE.md`，逐字加入：

> `current block` 必須是逐列 manifest：`CODE-ANCHOR: <repo-relative path>:<line>`、`ARCH-EDGE: <producer|contract|consumer>`、`role: <一句>`；不得以「整份檔」、單一章節名或只有自然語言段落代替。  
> 每個 finding 的 `**碼證**` 必須含 `CODE-ANCHOR: <repo-relative path>:<line>`、`MUTATION: <可執行破壞>`、`VERIFY: <命令> -> rc=<整數>`；沒有 active code/architecture anchor 的內容只能放 Suggestions，不得列 P0/P1 finding。  
> `HISTORY-BEGIN..HISTORY-END` 內的 anchor 一律不是 active evidence；`completeness_check.sh --single` 命中即 fail。

### 必答 5/6 — F1 scope 與是否可進實作

`HANDOFF.md:3,6,13-14` 的現行狀態是 D-002 v13 停輪，待補 `docs/SPLITUNIFY_TODO.md` Task 9.1–9.5；所以按目前看板，下一張中大票是 SPLITUNIFY b9 的 D-002 實作，F1 不必先擴到別的 SPEC，只能標為 D-002 trial。若看板改成別票，必須在該票開場另指定 target SPEC，不得把 D-002 成效外推。

目前不能進實作。Blocking 是 CODEX-R3-P1-01、02、04、05、06、07；先完成 consult reconcile/批准、最小 DOCROT SPEC＋TODO、active code-anchor/history gate、dupes narrow＋interval skip、gov_check fail-closed、consensus audit 對證，再依 TODO 執行。placeholder guard 的改寫是同一批核可工作，不是繼續擴建的理由。

ASSUMPTIONS_VERIFIED: R1–R12 heading counts 實跑為 15/11/15/8/11/16/15/14/21/13/12/13；指定 diff stat 實跑為 9 個檔；completeness 無 HISTORY marker、gov_check/xref 的 `--dupes` 仍不改 rc、D-002 `--dupes` 實跑 rc=0；D-002 下一票狀態以 HANDOFF 現行文字核對。
TESTS_RUN: `nl -ba`/`rg`/`git diff --stat`/`git hash-object` read-only probes；本輪未跑 pytest；交件後另跑指定 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r3-codex.md --family codex`。
FAILURES_SEEN: 一次以 shell 變數展開的基線 awk probe 被 PreToolUse 以 open-debt dispatch gate 拒絕，未改檔；一次把 `git show` pipe 到 `/dev/stdin` 的 claim-check probe 回 rc=2（checker 回報 no input files），未改檔；兩者均未用作通過證據。
SCOPE_CHANGES: 只新增本指定 consult 產出檔；未改 scripts、templates、tests、data_cache 或根 `HANDOFF.md`。
NUMERIC_OR_SCHEMA_IMPACT: none；只新增 consult findings/TODO/基線敘述，未改生產輸出或 schema。

VERDICT: blocked
BLOCKED-BY: CODEX-R3-P1-01,CODEX-R3-P1-02,CODEX-R3-P1-04,CODEX-R3-P1-05,CODEX-R3-P1-06,CODEX-R3-P1-07
CLOSED:
STATUS: DONE
## COMPOSER-R3-P1-01

**斷言**: brief 假設「D1／D2 機械化後輪數會降」**無前後對照數據**，在 `--dupes` 仍 warn-only（硬擋 0%）時不得當作已驗事實。

**碼證**: `for r in $(seq 1 12); do rg -c '## (CODEX|COMPOSER|GROK)-R'"$r"'-P' handoffs/reconcile/20260911-splitunify-b9-review-r"$r"/synth.md; done` → 15,11,15,8,11,16,15,14,21,13,12,13；`scripts/gov_check.sh:271-274` `|| true`；`scripts/spec_xref_hook.sh:65` `|| true`。RECHECK: 重跑迴圈；`rg '\|\| true' scripts/gov_check.sh scripts/spec_xref_hook.sh`。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#70660a69b76f;scripts/gov_check.sh#4b333ce050ff

[MAJOR] 信心度=High。宣稱已解會在 b9 再燒 3+ 輪 doc-sync。**修法**：必答 3 成效公式＋Task 3.2 fail-closed；無數據前 HANDOFF 只寫「試點待量」。

---

## COMPOSER-R3-P1-02

**斷言**: 「current block＋diff」**單獨**不能保證 finding 指向碼與架構——範本仍允許 **碼證** 僅引 SPEC 散文。

**碼證**: `templates/COMMITTEE_FINDING_TEMPLATE.md:17` 仍寫「檔案路徑 / 行號 / 命令 / 觀測輸出摘要」無 diff 邊界；R8–R12 群集關鍵字 grep 17/73 低估因表頭非機械碼證。RECHECK: `sed -n '15,20p' templates/COMMITTEE_FINDING_TEMPLATE.md`。

**來源摘要**: templates/COMMITTEE_FINDING_TEMPLATE.md#0c1fbb8d3f0b;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：必答 4 逐字改法＋Task 3.7；與 Task 3.1 同鏈拒收越界 anchor。

---

## COMPOSER-R3-P2-01

**斷言**: 主委五項 #3（`dupes()` `break`）必須**撤回**；#2 必須**收窄**至 `_RE_TOTAL_ITEMS`，否則 G4/G6 在 b9 首輪即復發。

**碼證**: `scripts/spec_count_audit.py:117-118` `break`；`python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md` → 「五維度」誤報；D-002 `--dupes` 活文區 rc=0（無雙「共 N 條」時）。RECHECK: 重跑 GAP3 `--dupes`；讀 `dupes()` L117。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 3.3–3.4；#3 主委 revert `break` 引入 commit 之邏輯，改 interval skip。

---

## COMPOSER-R3-P2-02

**斷言**: `verification_claim_check.py` 未擋「三家共同結論」類 commit 背書，第三根因「決議→實作無可核對」仍開。

**碼證**: `git show 3e009126 --format='%s'` → 含「三家共同結論」；`venv/bin/python scripts/verification_claim_check.py --commit-msg` 同上 subject → **rc=0**；`STRONG_POLARITY_RE`（L46-52）無「三家」模式。RECHECK: 重跑 verification_claim_check。

**來源摘要**: scripts/verification_claim_check.py#2fc6b3a0e20c;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 3.5 加 regex＋`audit.log` `committee_family_result` 同 task-id 佐證。

---

ASSUMPTIONS_VERIFIED: D-002 R1–R12 計數、GAP3 `--dupes` 誤報、`verification_claim_check` rc=0、`gov_check`/`hook` `|| true` 均已實跑  
TESTS_RUN: （交件前）`bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r3-composer.md --family composer`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（consult 禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none

VERDICT: proceed  
BLOCKED-BY:  
CLOSED: COMPOSER-R2-P3-01  
STATUS: DONE
## GROK-R3-P0-01

**斷言**: 現行 `gov_check.sh` 段 1b 對 `--dupes` 命中不進 `_docbad` 且 `|| true`，使 D1 在改動掃描路徑上的硬擋覆蓋率仍為 0%。

**碼證**: `scripts/gov_check.sh:271-273` 逐字「刻意**不進 _docbad**」＋`python3 scripts/spec_count_audit.py --dupes "${f}" >/dev/null || true`；`scripts/spec_xref_hook.sh` ③ 段同型不改 rc。RECHECK: `sed -n '268,275p' scripts/gov_check.sh`。

**來源摘要**: scripts/gov_check.sh#4b333ce050ff;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[BLOCKING] 信心度=High。review-r1 G5 三家已採納「最小擋門＝1b fail-closed」；主委試點仍停在 warn。**修法**：Task 1.3——命中計入 `_docbad`；hook 維持 warn。**可行性**：段 1b 迴圈與 `_docbad`／`_gc_fail` 已存在；只改分支。pytest：雙「共 N 條」→ 1b rc≠0。

## GROK-R3-P0-02

**斷言**: `completeness_check.sh` 仍不拒收落在 `HISTORY-BEGIN`‥`HISTORY-END` 的 finding anchor，E8 Phase A 後半未做，E3 輸入隔離無機械牙。

**碼證**: `grep -n 'HISTORY-BEGIN' scripts/completeness_check.sh` → **0 命中**（本輪實跑）；對照 `scripts/new_brief.sh:66` 與範本已寫「落在歷史段者不受理」但無執行端。RECHECK: 同上 grep；構造 `--single` 交件含 HISTORY 行號。

**來源摘要**: scripts/completeness_check.sh#c76692e041da;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[BLOCKING] 信心度=High。R2 E3／E8A 與 review-r1 G3（本家 P0）已定案。**修法**：Task 1.4——解析碼證／來源摘要之 `path:line`，落 HISTORY 區間即 FAIL。**可行性**：只讀既有欄位與檔內標記；`obligation_block_check` 已有區間 skip 可鏡像；不新腳本。

## GROK-R3-P0-03

**斷言**: 僅機械化 D1／D2 不足以降低文檔輪數——第三根因是「委員會決議 → 主委實作」之間沒有可核對 TODO，本輪主委 R2→碼即再犯。

**碼證**: review-r1 G1：五項非原文折衷且未開 consult 即 commit（`git log --oneline 44bbd8d3..HEAD` 含 `3e009126`／`ab3508c0`／`68a70342` 等）；`ls docs/ \| grep -i docrot` → 空。R2 程序修正「折衷須 consult」已被繞過。RECHECK: 對讀 review-r1 synth L13；`ls docs/ \| grep -i docrot`。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#70660a69b76f

[BLOCKING] 信心度=High。挑戰 brief assumed「D1／D2 機械化後輪數就降」：**不充分**。**修法**：本 consult 產出之 Task 1.1–1.5 為唯一實作清單；主委禁表外機制；實作後須審碼輪對表驗收。**可行性**：不新 epic；TODO 即契約。

## GROK-R3-P1-01

**斷言**: `dupes()` 在首個 `HISTORY-BEGIN` 使用 `break` 會漏掃其後活文，屬主委自創且有構造反例。

**碼證**: `scripts/spec_count_audit.py:117-118`；構造檔活前 L1「共 7 條」＋HISTORY＋活後 L7「共 7 條」→現行 `--dupes` stderr 空、rc=0；interval-skip 原型回傳 `('共 7 條',[1,7])`。RECHECK: 重跑同構造。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 1.1 區間 skip、禁 break。**可行性**：`obligation_block_check.sh` 已實作同型；加 mutation「HISTORY 後活文仍報」。

## GROK-R3-P1-02

**斷言**: `--dupes` 同時掃三 regex 超出 R2 窄 F2「只數共 N 條」；升 fail-closed 前必須收窄，否則誤報面會逼回 warn。

**碼證**: R2 synth L26「窄 F2（只數『共 N 條』形態）」；`dupes()` L120 `for rx in (_RE_NUM_UNIT, _RE_COUNT_ASSERT, _RE_TOTAL_ITEMS)`；composer 實跑 GAP3 報「五維度」等多行非「共 N 條」。RECHECK: `python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md`。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7

[MAJOR] 信心度=High。硬約束「取最窄能過三問者」。**修法**：Task 1.2 只留 `_RE_TOTAL_ITEMS`。**可行性**：改 for 迴圈一行；測試釘「五維度不報／共 N 條雙落點報」。

## GROK-R3-P1-03

**斷言**: `verification_claim_check.py` 對 commit 主旨「三家共同結論」類背書語現行不擋（rc=0），無法強制 audit 佐證。

**碼證**: `STRONG_POLARITY_RE`（L46–53）無「三家共同結論」；本輪 `printf 'fix(docrot): 落地三家共同結論前兩項…' > /tmp/msg` + `venv/bin/python scripts/verification_claim_check.py --commit-msg /tmp/msg` → **rc=0**。RECHECK: 重跑同命令。

**來源摘要**: scripts/verification_claim_check.py#2fc6b3a0e20c;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 1.5——封閉字面＋audit 家數檢查；允許 EXEMPT。**可行性**：既有 commit_msg 路徑與 committee audit 白名單（L30–41）可复用。

## GROK-R3-P2-01

**斷言**: 只限制審查輸入為 current block＋diff，不足以迫使 finding 指向碼／架構；diff 內字面差異仍可成篇。

**碼證**: 範本已有輸入邊界（`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`），但碼證欄未要求 `path:函式`；D-002 晚輪 findings 多數打修法字面（R1 D4／R12）。RECHECK: 讀範本輸出格式段；對照 R12 synth 附錄。

**來源摘要**: templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#976f11c084b2;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MINOR] 信心度=Medium。**修法**：Task 1.6 範本＋`new_brief.sh` 逐字句；doc-literal-only ≤P3。**可行性**：只改範本字面，無新腳本；執行靠主委拒收＋後續可選機檢。

## GROK-R3-P2-02

**斷言**: 骨架佔位偵測可保留為 E3 輔助，但「對手寫 brief 零誤擋／E3 已完成」宣稱過寬，且不能替代 completeness HISTORY 拒收。

**碼證**: `brief_conformance_check.sh` PLACEHOLDERS 段自承「擋不住手寫 brief 把審查標的寫成整份檔」；review-r1 G8。RECHECK: `sed -n '314,350p' scripts/brief_conformance_check.sh`。

**來源摘要**: scripts/brief_conformance_check.sh#55d4b8162804;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MINOR] 信心度=High。**修法**：必答 1＃1 改寫宣稱＋Task 1.8 文案；主牙仍是 Task 1.4。

---

## 戳記

（委員審完後各自 append 一行：`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<task-id>` 或 `RECONCILE-STAMP: <family> REJECTED <YYYY-MM-DD> — <理由>`）

RECONCILE-STAMP: composer APPROVED 2026-09-13 sha256:ddb910b2b323a228c1c1bfdba753db7f3babdf1e2b32cb17948f5031df8e7307 task:20260912-DOCROT-X-STAMP-R1

RECONCILE-STAMP: grok APPROVED 2026-09-13 sha256:ddb910b2b323a228c1c1bfdba753db7f3babdf1e2b32cb17948f5031df8e7307 task:20260912-DOCROT-X-STAMP-R1

RECONCILE-STAMP: codex APPROVED 2026-09-13 sha256:ddb910b2b323a228c1c1bfdba753db7f3babdf1e2b32cb17948f5031df8e7307 task:20260912-DOCROT-X-STAMP-R1
