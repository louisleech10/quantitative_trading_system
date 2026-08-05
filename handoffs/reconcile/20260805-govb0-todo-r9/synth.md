# Reconcile — 20260805-govb0-todo-r9

**來源** 20260805-govb0-todo-r9-codex.md, 20260805-govb0-todo-r9-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 可合併 — 5 條全部歸戶、**無未分群 ID**。
**兩家一致判 TODO 可標 Internal Frozen**，`blocks-implementation = 0`，5 條全為 `named-residual`。
🔴 **主委仍選擇全部就地修完**（依「第一性原理・現在修」：五條皆為分鐘級修補，
且其中 `J-1` 會直接卡住實作者，留給下一輪不合理）。

**TODO 收斂軌跡**：R8 前輪 9 條 → 修 → R8 **6 條**（全為修補引入的新缺口）→ 修 → R9 **5 條（0 blocks-implementation）**。
🔴 **R9 是 TODO 的最後一輪**（brief 明文終止條件，依使用者定死「95% 解法就收・殘留先記錄」）。
**首次未出現「修補引入 blocking 缺口」** —— 前兩輪皆有，本輪為 0。

**收斂基數**：5 條（codex 3／composer 2）。ID→斷言對照由 `awk` 自附錄機械抽出後才填表。

**驗證 receipt**（主委實跑 2026-08-05，**含 R9 要求的擷取命令實跑**）：
VERIFY: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0
VERIFY: `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-todo-r9/sources.lock` → rc=0，5/5 ID 全在綜合檔
VERIFY: bounded 擷取命令實跑 → `票 B-24` 內 `^TICKET-STATUS:` **1**、`票 B-14` 內 **1**（非假設，實跑）

| 群 | 主張 | 對應 finding | 處置 |
|---|---|---|---|
| J-1 | **`.sha256` sidecar 無 producer**：`TEST-2.5-CORPUS-SHA`（R8 新增）要求 `gate_decision_corpus.txt.sha256` 已 commit，但**沒有任何 Task 負責產出它** ⇒ 實作者照 TODO 做會卡住 | `CODEX-R9-P1-02`／`COMPOSER-R9-P1-01` | **ACCEPT → 已修**（🔴 **兩家獨立指出同一條，最強訊號**）：Task 2.0 的「輸入／輸出」與「修改檔案」明列該 sidecar，**producer ＝ Task 2.0，且須與語料同一次 commit**；內容為 `sha256sum` 單行；語料變更須同 commit 更新 |
| J-2 | **`TEST-3.3-B24-PARTIAL` 只給自然語言＋`grep -c`，未給可執行的 bounded 擷取命令** ⇒ 實作者需自行猜測邊界 | `CODEX-R9-P1-01` | **ACCEPT → 已修**：寫入逐字 `awk` 擷取命令（`/^## B-24 /{p=1} p && /^## B-/ && !/^## B-24 /{exit} p`），並註明 `票 B-14` 同法。**主委已實跑該命令驗證兩票各得 1**，非紙上宣稱 |
| J-3 | **`D-4`／`D-6`／`F-1`／`F-3` 等具名 ID 在 §T 無 literal 落點**（內容已分散落實）⇒ 下游以 §T 為索引會誤判為漏 | `CODEX-R9-P2-03` | **ACCEPT → 已修**：§T 補列 13 個具名 ID 的對應位置（`D-1`～`D-13`／`E-2`／`E-3`／`E-7`～`E-9`／`F-1`／`F-3`／`F-6`） |
| J-4 | **Gate 正文引用過期**：`B6→B7` 與 Phase 3 Gate 仍寫 `TEST-3.2-LOCK-⑨`～`⑫`「四條」，但 R8 已新增 `⑬` 與 `TEST-3.2-E9-ORDER` | `COMPOSER-R9-P2-01` | **ACCEPT → 已修**：兩處改為 `⑨`～`⑬`「**五條**並發／錯誤路徑斷言（含 `TEST-3.2-E9-ORDER`）」。**同 `票 B-17` 病型**——手寫的計數引用必漂，本 session 第 10 次 |

**本輪與前兩輪的關鍵差異（收斂訊號）**

| 輪次 | findings | 其中「修補引入的新 blocking 缺口」 |
|---|---|---|
| R8 前輪 | 9 | 2（BLOCKING） |
| R8 | 6 | 1（BLOCKING） |
| **R9** | **5** | **0** |

⇒ 前兩輪主委的修補**各自引入 blocking 缺口**；本輪 5 條全為 `named-residual`，**首次歸零**。
主委對「修補彼此不衝突」的信心在前兩輪被推翻兩次，本輪兩家獨立確認未再發生。

**主委自記**：`J-1` 是**兩家獨立指出的同一條**，且是唯一會實質卡住實作者的。
它的成因是 R8 修 `I-4`（corpus mutation 不可證偽）時**新增了一個依賴檔卻沒指定 producer**——
即「修 A 引入 B」的同型模式第三次。⇒ 已納入 `票 B-16` 擴充的佐證
（文件宣稱某檔「已 commit」時，應機械檢查是否有 Task 負責產出它）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R9-P1-01

**斷言**: `TEST-3.3-B24-PARTIAL` 宣稱檢查 B-24 bounded section，但 TODO:665–667 只給 `grep -c` 與自然語言，沒有給 `^## B-24 ` 起點及下一個 `^## B-` 終點；實作者若對整個 backlog grep，仍可得到綠燈而未驗 marker 屬於 B-24。

**碼證**: `nl -ba docs/GOVB0_FRICTION_TODO.md | sed -n '652,667p'` 顯示 B-14 在 TODO:656 有完整 anchor，B-24 在 TODO:665–667 沒有；`rg -n '^## .*B-24|^TICKET-STATUS:' handoffs/20260801-GOV-AMEND-BACKLOG.md` → status section line 880/899、另一 B-24 heading line 1594；整檔 `grep -c '^TICKET-STATUS: PARTIAL'`=1，而正確 bounded extraction 也為 1。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421；handoffs/20260801-GOV-AMEND-BACKLOG.md#a65ede08244a

[MAJOR] 信心度=High；分類=`named-residual`，不阻塞實作者（目前 canonical `^## B-24 ` heading 存在且可由 B-14 形狀推知）。修法：在 `TEST-3.3-B24-PARTIAL` 逐字寫明由 `^## B-24 ` 起至下一 `^## B-` 前擷取，再在該 bounded output 上斷言 `^TICKET-STATUS: PARTIAL`==1、`^TICKET-STATUS: DONE`==0；補一個把 marker 移出 bounded section 的 mutation，必須轉紅。

## CODEX-R9-P1-02

**斷言**: R8 新增的 `TEST-2.5-CORPUS-SHA` 要求已 commit 的 `gate_decision_corpus.txt.sha256`，但 Task 2.0 的輸出/修改檔案只列 corpus 與 test，Task 2.5 又明定不產生任何 fixture；corpus sidecar 沒有明確 producer、格式或入版控 gate。

**碼證**: TODO:258–259、284–285 只列 `gate_decision_corpus.txt`；TODO:410–423 要求 sidecar 並把 snapshot producer 明確歸 B0，卻只說 corpus「由 Task 2.0 產出」。目前 `tests/governance/fixtures/` 尚不存在，故該 sidecar 尚無可檢查的實體落點（implementation 尚未開始，非 runtime failure）。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MAJOR] 信心度=High；分類=`named-residual`，不阻塞實作者（sidecar 可自然作為 Task 2.0 的 corpus derivative）。修法：Task 2.0 的輸出/修改檔案明列 `gate_decision_corpus.txt.sha256`、producer=Task 2.0、canonical 64-hex 格式與 commit ownership；B3/B5 gate 同時檢查 corpus 與 sidecar 已追蹤且 hash 相等。Task 2.5 維持只讀消費。

## CODEX-R9-P2-03

**斷言**: 全量 SPEC 實質引用的 `D-4`、`D-6`、`F-1`、`F-3` 在 TODO 沒有 literal ID 落點；內容雖已分別寫入 Task 2.5、B-24 split、Task 0.1、Task 3.2，但 §T 無法以 ID 機械追溯這四個非排除裁決。

**碼證**: `rg -o '\b(?:D|E|F|G|H)-[0-9]+\b|\bE-SCOPE\b|\bOPEN-[0-9]+\b' docs/GOVB0_FRICTION_SPEC.md | sort -u` 清單含上述四項；`rg -n -w 'D-4|D-6|F-1|F-3' docs/GOVB0_FRICTION_TODO.md` → rc=1、無輸出。反查 Task 內容：TODO:407–450（D-4）、TODO:12–20/694–698（D-6）、TODO:149–175（F-1 語意）、TODO:524–606（F-3 語意）。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#283298bb1e8a；docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MINOR] 信心度=High；分類=`named-residual`，不阻塞實作者，且不把版本摘要中的 E-1/E-13/G-1/G-6 虛列為缺口。修法：§T in-scope 表補四列 `D-4→Task 2.5`、`D-6→§0.1/§T`、`F-1→Task 0.1`、`F-3→Task 3.2`；保留現有語意，不需新增機制。

## COMPOSER-R9-P1-01

**斷言**: Task 2.0 的「輸入／輸出」與「修改檔案」未列 `gate_decision_corpus.txt` 的 `.sha256` sidecar，但 Task 2.5 將其列為 Task 2.0 產出且 `TEST-2.5-CORPUS-SHA` 依賴已 commit sidecar。

**碼證**: Task 2.0 L258-259 輸出僅語料 + 測試；L284 修改檔案同。Task 2.5 L423 唯讀輸入含「語料 B … + 其 `.sha256` sidecar」；L439-443 `TEST-2.5-CORPUS-SHA` 雙比對。RECHECK: `rg -n 'gate_decision_corpus' docs/GOVB0_FRICTION_TODO.md` 比對 Task 2.0 輸出欄 vs Task 2.5 唯讀輸入欄。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MAJOR] 信心度=High；分類=**named-residual**。實作者僅讀 Task 2.0 時不知須產 sidecar；讀到 Task 2.5 可反推，不構成開工阻斷。修法：Task 2.0「輸出」補「`tests/governance/fixtures/gate_decision_corpus.txt.sha256`（語料 sha256 sidecar，與 B0 snapshot 同模式）」；「修改檔案」同步補列。

## COMPOSER-R9-P2-01

**斷言**: §B「B6→B7」Gate（L102）與「Phase 3 Gate」（L681-682）正文仍寫 `TEST-3.2-LOCK-⑨`～`⑫`「四條」，未提及已存在的 `TEST-3.2-LOCK-⑬`（reclaim 孤兒探針，L598-604）。

**碼證**: L102、L681-682 vs Task 3.2 驗證段 L598 `TEST-3.2-LOCK-⑬`。RECHECK: `rg -n 'LOCK-⑬\|LOCK-⑨' docs/GOVB0_FRICTION_TODO.md`。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MINOR] 信心度=High；分類=**named-residual**。全檔 `pytest tests/governance/test_atomic_publish.py` 仍會跑到 ⑬，Gate 文案漏列不致漏測。修法：§B B6→B7 與 Phase 3 Gate 改為「⑨～⑬」或明列 ⑬ 為 reclaim 孤兒釘扎測試。

