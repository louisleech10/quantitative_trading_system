# Reconcile — 20260805-govb0-todo-r8

**來源** 20260805-govb0-todo-r8-codex.md, 20260805-govb0-todo-r8-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併 — 6 條全部歸戶、**無未分群 ID**。**全部 6 條已修畢**（逐條見下）。

**收斂基數**：6 條（codex 4／composer 2）。ID→斷言對照由 `awk` 自附錄機械抽出後才填表（防歷來 7 次錯位）。

🔴 **本輪 6 條全部是主委上一輪「修補」自己引入的新缺口**，非 SPEC 或原始 TODO 的問題。

**驗證 receipt**（主委實跑 2026-08-05）：
VERIFY: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0
VERIFY: `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-todo-r8/sources.lock` → rc=0，6/6 ID 全在綜合檔

| 群 | 主張 | 對應 finding | 處置 |
|---|---|---|---|
| I-1 | **狀態斷言引用了目標區段內不存在的字串** ⇒ 測試自落筆起恆為 FAIL | `CODEX-R8-P0-01`／`COMPOSER-R8-P1-02` | **ACCEPT-BLOCKING → 已修**：`票 B-24` 補 `TICKET-STATUS: PARTIAL` 機器標記行（實測 bounded section 內 `grep -c '^TICKET-STATUS: PARTIAL'` == 1） |
| I-2 | **斷言自我引用**：`grep -c` 宣稱 == 1，實測 2，因**測試定義本身含該字串** | `COMPOSER-R8-P1-01` | **ACCEPT → 已修**：改用 `TASK-STATUS: INCOMPLETE` 行首錨定標記。🔴 **主委在修補過程中又踩同一陷阱兩次**（補 `票 B-24` 時於否定敘述提及被禁關鍵字使計數 0→4；補 `RESIDUAL` 時未錨定使計數 == 2）⇒ **改用通解：機器標記寫行首、斷言帶 `^`，兩者缺一即自我污染**。同型陷阱本日共 **5 次** |
| I-3 | **snapshot 所有權矛盾**：B0 已是 producer，Task 2.5 卻仍把它列在「修改檔案」 ⇒ 實作者可在 B5 重產，差集 oracle 會含 Phase 2 改動 | `CODEX-R8-P1-02` | **ACCEPT → 已修**：Task 2.5「修改檔案」只列 `gate_decision_delta.sh`；snapshot 與 corpus 及其 `.sha256` sidecar 改列**唯讀輸入**，明載 sha ownership 屬 B0 |
| I-4 | **corpus immutability mutation 不可證偽**：報表標頭與當前語料實算值比對，改語料後兩邊一起變 ⇒ 假綠 | `CODEX-R8-P1-03` | **ACCEPT → 已修**：`TEST-2.5-CORPUS-SHA` 改為**同時**比對①當前實算值②**已 commit 的 `.sha256` sidecar**（獨立 SoT）；mutation 明訂**必須針對 sidecar 那一半**，只移除①不算數 |
| I-5 | **§T 宣稱 100% 覆蓋為不實**：`F-7`／`票 B-36` 無任何 TODO 落點 | `CODEX-R8-P1-04` | **ACCEPT → 已修**：§T 標題改為「本批 in-scope Task 覆蓋 ＋ 明列排除清單」，新增**具名排除表**（`F-7`／`B-36`、`E-SCOPE` 四項、`H-1`／`H-2`、`OPEN-2`／`D-8`）各列後續落點 |
| I-6 | **provenance 漂移**：SPEC:5 停在「版本 R4」，實際 R7 | `CODEX-R8-P1-04`（同條附帶） | **ACCEPT → 已修**：SPEC:5 更正為 R7 並列全部輪次；標記為 `票 B-17` 同型漂移**本 session 第 9 次** |

**主委的失誤模式（自記，供 `票 B-16` 擴充佐證）**

本輪 6 條可歸為三類，**全部是主委造成，非技術難度**：
①**沒對照就寫**（I-1）——`grep -c` 跑一次就知道是 0，主委沒跑；
②**自我引用未察**（I-2）——測試與被測內容同檔，未行首錨定即自我污染，主委在**修補過程中又犯兩次**；
③**編輯殘留與過度宣稱**（I-3／I-5）——改了一處未同步另一處；宣稱 100% 未實際核對。

⇒ 使用者 2026-08-05 裁定**合併進 `票 B-16` 並提前至第 1 批**（擴充 A：可執行斷言寫檔當下實跑；
擴充 B：引用的函式名／檔名存在性檢查）。實測本 session 主委引入的缺口**至少 9 次**會被其在寫檔當下擋掉。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R8-P0-01

**斷言**: `TEST-3.3-B24-PARTIAL` 指定 B-24 bounded section 必須含「部分完成」，但 canonical `^## B-24 ` 至下一 `^## B-` 區間目前沒有該字串，因此驗收必然 FAIL。

**碼證**: `awk` bounded predicate → `B24_PARTIAL_COUNT=0`、`B24_GREEN_COUNT=0`、rc=1；`grep -n '部分完成\|全綠' handoffs/20260801-GOV-AMEND-BACKLOG.md` 顯示 B-24 狀態文字只在 line 1522、位於 bounded section 外；TODO:646–647 要求該 predicate。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f；handoffs/20260801-GOV-AMEND-BACKLOG.md#e864a30429d5

[BLOCKING] 信心度=High；任何 implementation 都不能使既有 bounded predicate 通過而不改 backlog/TODO。修法：在 `## B-24` 至下一 `## B-` 內加入明確「部分完成」狀態行，並保證同區間無「全綠」；保留 `TEST-3.3-B24-PARTIAL` 不降門檻。

## CODEX-R8-P1-02

**斷言**: B0 已成為 snapshot producer，但 Task 2.5 的「修改檔案」仍把同一 snapshot 列為 Task 2.5 新增輸出，和其「只消費」及 B0→B3 hard Gate 互相矛盾。

**碼證**: TODO:79–92 將 snapshot producer 放在 B0 且 B3 依賴 B0；TODO:410–416 明說 Task 2.5 只消費，但 `修改檔案` 仍列 `gate_check_pre_phase2.sh.snapshot`。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High；實作者可在 B5 重產 snapshot，讓差集 oracle 含 Phase 2 改動。修法：Task 2.5 `修改檔案` 移除 snapshot（及其 sidecar），改列為唯讀輸入；B0 明確列出兩個 producer path 與 sha ownership。

## CODEX-R8-P1-03

**斷言**: `TEST-2.5-MUT` 的 corpus immutability mutation 不具可證偽性：只要求報表 header hash 等於當前 corpus，改 corpus 後重跑仍可重新計算並相等。

**碼證**: TODO:407–414 只規定 sha 寫入報表 header、未定固定 expected sha／sidecar；TODO:431 與 433–436 卻聲稱改 corpus 應使 `TEST-2.5-CORPUS-SHA` 轉紅。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High；測試可能假綠，無法證明「同一次驗收不得修改語料」。修法：B0 或 immutable fixture 同時提交 corpus `.sha256` SoT，報表與測試比對該固定值；mutation 改 corpus 後必須 rc≠0，再另行更新 fixture commit。

## CODEX-R8-P1-04

**斷言**: TODO §T 宣稱 SPEC ID 100% 覆蓋，但 SPEC 的具名殘留 `F-7`／`B-36` 沒有任何 TODO 落點。

**碼證**: `rg -n 'F-7|B-36|D-4|F-3' docs/GOVB0_FRICTION_SPEC.md` 命中 SPEC:587–593；同命令對 TODO rc=1；TODO §T:663–678 只列 11 Task、E-SCOPE、H-1/H-2、B-24、E-10。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#15ce4f6e6a11；docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High；下游以 §T 為完整追溯索引會漏掉「B-36 併入 B-13」的錯位殘留。修法：TODO §0/§T 增列 `F-7/B-36` 的已知 residual 與明確 OUT-OF-SCOPE/後續票落點，或把 §T 標題改成「本批 in-scope Task coverage」並列出排除清單；另同步處理 SPEC:5 的 R4 與 TODO:4 的 R7 provenance 漂移。

## COMPOSER-R8-P1-01

**斷言**: `TEST-3.3-PROVISIONAL` 條件②要求 `grep -c '本 Task 於本 TODO 產出時標記為「未完工」' docs/GOVB0_FRICTION_TODO.md` **== 1**，但該字串同時出現在條件②自身的規格行（L639），實測 **count=2**，條件恆 FAIL。

**碼證**: `grep -c '本 Task 於本 TODO 產出時標記為「未完工」' docs/GOVB0_FRICTION_TODO.md` → **2**；落點 L600（宣告）、L639（測試規格自引用）。RECHECK: 同上命令；或改為錨定 `^\- \*\*🔴 本 Task 於` 唯一標記行。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High。實作者按字面實作 `TEST-3.3-PROVISIONAL` 會在條件②永久轉紅，與 codex P1-04「三項可機械驗證」修法目標相悖。

**修法**: Task 3.3 驗證欄 `TEST-3.3-PROVISIONAL` 條件②改為唯一錨點（例 `grep -c '^\- \*\*🔴 本 Task 於本 TODO 產出時標記為「未完工」'` **== 1**），或將測試規格移至不污染 grep 目標的附錄；同步避免在 `docs/GOVB0_FRICTION_TODO.md` 內嵌可被 `grep -c` 誤數的原文。

---

## COMPOSER-R8-P1-02

**斷言**: `TEST-3.3-B24-PARTIAL` 要求 `票 B-24` bounded section 含「部分完成」，但未像 `TEST-3.3-PROVISIONAL` ③那樣定義 `^## …` 錨點；若實作者沿用 `^## B-14 ` 同型式取 `^## B-24 `，該區間 **不含**「部分完成」（實測 count=0），測試恆 FAIL。

**碼證**: `awk '/^## B-24 /{f=1;n=0} f{print} /^## B-/{if(f&&n++)exit}' handoffs/20260801-GOV-AMEND-BACKLOG.md | LC_ALL=C grep -c '部分完成'` → **0**。「部分完成」在 `## 📌 票 B-24 的拆分裁決`（backlog L1507-1522）。RECHECK: 同上 awk+grep；對照 `TEST-3.3-PROVISIONAL` ③的 bounded section 寫法（TODO L640-642）。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High。B-24 紀律面邊界無法機械驗收，與 §0.1 第 1 條及 codex P1-04 五測試補強目標不一致。

**修法**: Task 3.3 驗證欄 `TEST-3.3-B24-PARTIAL` 補齊 bounded section 錨點（建議 `^## 📌 \`票 B-24\` 的拆分裁決` 至下一 `^## `），並明寫 `grep -c '部分完成'` **≥1** 且 `grep -c '全綠'` **==0**（於該區間內）。

---

