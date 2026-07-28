# P1-6 委員未結案債狀態機 — SPEC

> **版本 v2.9**（R1–R8 共 96 findings ＋ **B1 實作階段三家裁決** 全數收口）　|　日期：2026-07-29
>
> ## 🔴 v2.9＝**實作階段打回來的 SPEC 缺陷修正**（三家一致裁 P0，非設計爭議）
>
> **B1（Task 0.1）實作完成後，兩家非實作者 code review 各自獨立抓到同型缺陷，主委複核後實測證實：**
> ```
> $ grep -c 'committee_round_open' .claude/gate/audit.log   →  0
> $ bash scripts/reconcile_build.sh <新session> <檔...>      →  rc=1
> ERROR: session_name 命中 0 筆(需恰 1)
> ```
> **因果**：v2.8 Task 0.1 改法⑨② 要求「**建立 session 時**無條件從 audit 反查 `round_id`，命中 0 筆即 fail-closed」，但寫入 `committee_round_open` 的是 **Task 1.2（B3）**。⇒ Phase 0 完成到 Phase 1 完成之間，`reconcile_build` 對**所有**新 session 一律拒建；**而 B2／B3 自己的 code review 就需要建 session** ⇒ **本 epic 會鎖死自己的施工過程**。
> **這不是實作 bug**——實作端忠實照 SPEC 做了。**是 SPEC 的階段依賴缺陷。**
>
> **修法（三家一致）**：反查的觸發條件由「建立 session 時」**收窄為「產生 `review` mode 的 lock 時」**（詳見 Task 0.1 改法⑨的表）。
> **⚠️ 主委原提案不足，由 codex 補正**：只收窄 `reconcile_build.sh` 仍留下旁路——**公開的 `write_sources_lock.sh` 能直接建 `review` lock 並塞任意 round**，主委宣稱的不變式「任何 review lock 的 round_id 都來自 audit」**根本不成立**。故修法**必須擴及所有 lock writer 路徑**。
> **另兩條 P1**（兩家獨立同型，主委複核成立；其中一條**主委自己的獨立驗收漏掉**）：
> ①`write_sources_lock.sh --rebuild` 未設 harness 時**接受任意 `--round-id` 且完全不查 audit** → 綁定可偽造，打穿 Task 2.2④。**裁決＝(甲)**：拒收呼叫端的 round，由 writer 自 audit 導出；**(乙)「只准 `reconcile_build` 呼叫」被否決**——shell 無法可靠證明呼叫者身分，env internal marker 又違反反 bypass 紅線。
> ②B1 新增的 4 條測試**閹割守衛後仍全綠**＝非真 oracle，須改為「閹割→轉紅、復原→轉綠」逐條附 receipt。
>
> **新增誠實邊界第 11 條**（見 §A）：`discovery` session 完全不受 identity binding 保護，這是本次收窄的直接代價。
>
> **R8＝戳記輪。composer／grok 簽 APPROVED，codex 不簽並提 2 條，皆採納：**
> ①**`CODEX-R8-P0-01`（真缺口）**：v2.7 寫「唯一性掃描須與 append 共用 Task 1.1 的鎖」，但**那把鎖在 `audit_append.sh` 裡面**——呼叫端持鎖再呼叫它會**自鎖**，先放鎖再 append 則 **TOCTOU 回歸**，所以這句話**不可執行**。修法＝把判定搬進持鎖者：**Task 1.1 改法⑥ 新增 `audit_append.sh --require-absent-session <name>`**（鎖內一次完成判定＋寫入），Task 1.2 改為只能呼叫它、**明文禁止**自行 check-then-append 或自行取鎖，且**不提供 reentrant 鎖／鎖交接 API**（兩者都製造新可繞面）。§V 增 **M34**。
> ②**`CODEX-R8-P1-02`（誠實性）**：`spec_fourway_check.sh` 只是固定 `grep -c`，第④項自己都印「人工比對」，叫「四向檢查」屬**誇大**。已依 codex 給的第二選項**降級為 smoke check**（腳本檔頭與輸出都改；**刻意不做成通用 map 驅動閘門**——2026-07-27 通用版已被使用者裁定撤除，不重蓋；**不接入 `gov_check.sh`**）。
>
> **⚠️ 戳記輪自身暴露的問題（記錄，非 finding）**：`completeness_check --lock` 在整個 R8 期間是**紅的**（我 append 戳記區時多打一個 `---`，把它併進最後一條 finding 的 body → hash 不符）。**只有 codex 停下來查前置條件並拒簽；composer 與 grok 在紅燈下簽了 APPROVED**。這正是本 epic 要治的病（自報不可信）出現在戳記輪本身。結構已修，`completeness` rc=0。
>
> **R7 的 8 條 → 5 群，全部採納，0 條不採納。三家皆無「加新機制」提案。**
> ①**G1（2/3 判 P0）**：v2.6 把 `--rebuild` 寫進 Task 2.2，卻**沒動擁有 `reconcile_build.sh` 的 Task 0.1 改法段**，還留著三句「不提供事後重凍」的絕對句 → 實作者照改法段做會**漏做或自認被禁止**該旗標；即使做了，仍會撞既有兩道牆（session-exists `exit 2`、FROZEN 非 `--force` 不覆寫）。**修法**：Task 0.1 改法⑨增③寫死 `--rebuild` 落地方式與兩道牆的處理，絕對句改為「不提供 `--force` 重凍／不提供重綁 identity」。
> ②**G2（3/3 看到，1/3 判 P0）**：開債端唯一性是 check-then-append，有 TOCTOU → 併入 Task 1.1 臨界區（一句）。
> ③**G3（2/3，P2）**：Task 1.2 **驗證段**缺唯一性 oracle——**v2.6 自檢的漏網**：我學到「改法+驗證雙落點」卻只對 F1/F3 施行，沒回頭掃 F2。
> ④**G4（2/3，P2）**：`--rebuild` 只有 M33 名稱、無可執行 oracle → Task 2.2 驗證段補 happy path + 5 條負例，含「**未設 `GOVERNANCE_TEST_HARNESS` 也能完成**」（R5/R6 兩度復發的病灶）。
> ⑤**G5（2/3，P2/P3）**：檔頭收斂表補 R6/R7 兩列。
>
> **🚨 停損線觸發後的重評（條數 7→8）**：R7 的 P0 **不是設計問題，是文件傳播缺口**——與 R6-F3、R4 同型，**第 7 次同型**。所以：
> **v2.7 起自檢由「兩落點」升為「四向擁有權」**——每條要求須確認 ①落在**擁有該腳本的那個 Task** 的改法段（v2.6 的失敗處：落在了錯的 Task）②該 Task 的驗證段 ③§V 有對應 mutation ④全檔無與之矛盾的絕對句。
> **⚠️ 但 `scripts/spec_fourway_check.sh` 只是這件事的 smoke check，不是保證**（R8 codex 指正）：它只做固定字串比對，**不解析 Task 邊界、不驗語意**，擋不住同義句／錯 Task／空泛 happy path；第④項只印清單供人工比對。**PASS 不等於已收斂。**
> **下一步不再開 R8 adversarial 輪**（三家 verdict 已是「修完就簽」，同型輪只會再測我的抄寫能力），改為直接進**三家 RECONCILE-STAMP 戳記輪**——戳記輪本身即三家複驗，若我又漏傳播，機器閘門會擋下。
>
> **R6 的 7 條只打兩個點，且都是 v2.5 那次修改的直接副作用**：
> ①**「換 session 名重建」與新 provenance 鏈自相矛盾**（3/3 家族）——`session_name` 是開債當下就綁進 audit 的，換名後查無對應事件、`reconcile_build` fail-closed，**我自己的規則擋死了我自己寫的復原路徑**。改為**同名升級** `reconcile_build <同名> --mode review --rebuild`（自帶三道守衛：audit 恰一筆、輪次仍 `OPEN`、只准 `discovery→review` 單向）。
> ②**`session_name` 無唯一性契約**（3/3 家族）——兩端都補：開債端重名即拒；反查端命中 0 或 ≥2 一律拒，不做隱含選擇。
> ③Task 0.1 **驗證段**未跟上改法（R4 教訓只學一半：當時只檢查「改法」段有無落點，沒檢查「驗證」段）。
> **v2.6 起自檢擴充為：每條要求須在對應 Task 的「改法」與「驗證」兩段都有落點。**
>
> **R5 是一次「移除機制」的修訂**：三家從不同角度證明 v2.4 的 `round.id` 設計**時序上不成立**——session 目錄是 `reconcile_build.sh` 在委員**交件之後**才建立的，而開債發生在**交件之前**，`committee_run.sh` 當下無從寫入；為繞開此點所寫的「事後重凍」命令又用了綁 harness 的 `--force`，**正式路徑不可達**。
> **修法＝廢除 `round.id` 檔與整條重凍流程**，改用 **audit 紀錄本身**當 provenance：`committee_run.sh --session <name>` 把 `session_name` 記進 `committee_round_open`；`reconcile_build.sh <name> --mode review` 建立 session 時從 audit 取回 `round_id` 寫入 lock；`debt_clear.sh` 只讀驗。**少一個檔案、少一條不可達流程，且真相源改為 append-only 的 audit（`debt_clear` 無寫入權），比額外檔案更難竄改。**
>
> **R4 修的是同一個病灶：「說了要做什麼，卻沒說哪個 Task 負責做」**（9 條零設計問題）——①`round.id` 的寫入責任只寫在 Task 2.2 與檔頭，**Task 1.2（`committee_run.sh` 的唯一實作 Task）完全沒提** → 已補為 Task 1.2 改法⑦ ②「銷帳前重凍 lock 為 review mode」無 Task 歸屬且 `debt_clear` 又被禁止寫 lock → 已補 Task 2.2「銷帳前置流程」明訂由主委手動執行 ③檔頭仍寫「`--abandon` 解死鎖」與正文 2c 矛盾（**這是 R4 brief 請三家專門檢查的項目，codex 抓到**）→ 已改 ④§V 缺能證偽 provenance 鏈的 mutation → 補 M29–M31 ⑤roster 兩側欄位名未消歧 → 已明寫。
> **v2.4 起新增自檢**：每條「X 須做 Y」的要求，都要能在對應 Task 的「改法」段找到落點。
>
> **📉 收斂軌跡（本 epic 首次出現，與舊版形態明確不同）**
> | 輪 | findings | P0 | codex | composer | grok |
> |---|---|---|---|---|---|
> | 舊版 R5–R12（八輪） | 20–25 **不動** | 6–9 | — | — | — |
> | v2.0 **R1** | 34 | 9 | 有根本缺陷需重作 | 否，不可進 TODO | 需修補後派工 |
> | v2.1 **R2** | 17 | 5 | 需修補後派工 | 輕量，「修完 2 項可簽」 | 需修補後派工 |
> | v2.2 **R3** | 12 | 3 | 需修補後派工 | 輕量，「符合收斂軌跡」 | 輕量，「修完 P0-01 後可簽；P2 不應再擋一輪大修」 |
> | v2.3 **R4** | 9 | 3 | 需修補後派工 | 輕量 | **極輕量** |
> | v2.4 **R5** | **7** | **3** | 需修補後派工 | **極輕量（僅 1 條）** | 輕量 |
> | v2.5 **R6** | **7** | **2** | 需修補後派工 | 極輕量 | 輕量 |
> | v2.6 **R7** | **8** | **3**（實質共識 P0 **1**） | 需修補後派工 | **可簽 APPROVED（0 P0/0 P1）** | 修 1 條 P0 後簽 APPROVED |
>
> **條數在 R7 由 7 升至 8，觸發起草者自設的停損線**（「持平或上升即停下重評做法」）。**重評結論見下方「收斂診斷」——不是砍規模、不是重寫，而是換一個機械檢查，並改以戳記輪收尾而非再開 R8。**
> 其餘三個量在 R7 皆改善：**首次有家族簽 APPROVED**（前六輪無任何一家說過可簽）、**P0 實質共識點 2→1**、**R4 起零設計翻案**。
>
> **R3 修的三件實質事**：①**`round_id` binding 仍可自填自驗**——v2.2 只說「lock.round_id 要等於傳入值」卻沒規定誰寫入，銷帳端可自己塞值。當時改為「`committee_run.sh` 開債時寫 session 的 `round.id`」（codex+grok 各自抓到）——**⚠️ 此修法已於 R5 廢除**（時序不成立，見上方 R5 段）；現行做法是把 `session_name` 記進 audit 事件②**review-mode lock 無 production 建立路徑**——`reconcile_build.sh` 寫死 `discovery`；改為該工具須支援 `--mode`（預設仍 `discovery`）③**M26 與誠實邊界 2b 互斥**——我為一個已宣告接受的窗口加了 mutation，自相矛盾，已刪。
> **另修 7 條「改一處漏多處」**（本 session 第 5 次同型，且**本輪已成為主要類別**）：B8 的驗證句／條件④的更正註／Task 0.1① 的前綴宣稱等。
> **⚠️ 起草者紀律變更（R3 起）**：這 7 條全是「**我改了正文但沒改更正註記，導致註記與正文互相矛盾**」，且**字串層的擴充複掃抓不到**（屬語意矛盾）。**v2.3 起改為「直接改寫正文、不在正文留更正註記」**，沿革一律集中於本檔頭。
>
> **reconcile**：R1＝`handoffs/reconcile/p16-v20adv-r1/synth.md`（34→19 群集）；R2＝`handoffs/reconcile/p16-v21close-r2/synth.md`（17→9）；R3＝`handoffs/reconcile/p16-v22close-r3/synth.md`（12→7）。三輪 `completeness_check` 皆 rc=0。
> **V1 三家共識（各自主動聲明，非起草者引導）**：**砍規模的方向正確，問題全在「砍了規格沒砍設定檔」**——codex「不是把八個舊機制全部加回」／grok「不是建議加回舊版八大機制」／composer 過度工程欄「無（大砍版方向正確）」。
> **v2.1 修了什麼**：新增 **Phase 0（registry 對齊 v2 契約）**＝三家一致的頭號 BLOCKING；`flock`→`mkdir` 原子鎖（實測 `flock` 不存在）；銷帳增「lock 須 review mode」（否則委員沒附佐證也能過）＋「roster 集合相等」＋「產出 sha 比對」；`--abandon` 改單筆掃描（**使放棄在序號 gap 下仍可執行**；但**派工恢復仍需人工修復帳本**，見誠實邊界 2c——v2.1 當時誤以為此舉「解了死鎖」，R2 已更正）；Task 1.3 補「已成功家族拒重派」；探針改 Python helper 面**預先收口**；§RISK 改 `b,c`；誠實邊界增 4 條、修正 2 條過強宣稱；§V 補 M20–M25。
> **舊版封存**：`handoffs/p16-spec-archive/P16_SPEC_v1.2.2_BEFORE_SCOPE_CUT.md`（16 Task／360 行）。**舊版三家戳記不延續。**
>
> **為何重寫**（實測，非感覺）：舊版 **R5→R12 連續八輪**卡在 20–25 findings、P0 卡 6–9，**完全沒收斂就定版**，進 TODO 階段又磨五輪。讀晚期 P0 原文的根因是 **scope accretion**——每次修訂都新增機制（v0.8 加終局出口→該輪 P0 全打它；v1.0 大改寫→P0 是「v0.8 凍結的演算法整段消失」；v1.1 加守衛→P0 全打新守衛）。**規模本身就是不收斂的原因。**
>
> **本版刻意的寫法紀律（防止重蹈）**：
> 1. **不建任何鏡像索引表**——舊版 TODO 有 7 張鏡射本文件各節的表，改本文件一個字要動下游 2–4 處，是漂移主因。本版一律 pointer，不重列。
> 2. **範圍凍結**：往後輪次只准**修正**已列項目，**不准新增機制**。真有新需求 → 記入 §N「上線後再議」，不進本版。
> 3. 條數／數量一律不寫進標題（寫了就會跟內容漂）。

## 一句話

我每次問完委員，機器自動記一筆債；**沒證明把意見完整收好，就不准問下一輪**。

## §RISK 風險分級
- **大小**：**大**。改 `committee_run.sh` / `cx_run.sh` / `gate.sh` 三支共用控制流；既有 governance 測試依賴 `gate.sh`。
- **命中高風險原則**：**(b) 跨模組／共用路徑** ＋ **(c) 難回退**。**不命中 (a)/(d)**（不碰數值／ML／回測）。
  **(c) 的來源是 audit schema append-only 不可回退**（見 §R），**不是** phase 數量——V1 codex/grok 指出 v2.0 原標「不命中 (c)」與 §R 自承「audit schema 不可回退」自相矛盾，已更正。
- RISK-HIT: b,c
- **adversarial review 仍必跑**（大任務鐵律）。

## §A 假設與待使用者確認

### FACT-RECEIPT（逐條附實跑命令與輸出）
- FACT-RECEIPT: `python -m pytest tests/governance -q` → `287 passed`（Claude 實跑 2026-07-27）
- FACT-RECEIPT: `grep -n "audit\|AUDIT" scripts/cx_run.sh` → 0 命中（`cx_run.sh` 現況 85 行完全無 audit 寫入）
- FACT-RECEIPT: `rg -n 'gate|token|GATE' scripts/reconcile_build.sh` → **0 命中** → **清帳路徑不經 dispatch 閘，故「有債萬事停」不是死鎖**
- FACT-RECEIPT: `nl -ba scripts/gate_check.sh | sed -n '67,76p'` → fresh token 直接 `exit 0`，**不重讀 audit**（＝§A 誠實邊界第 1 條的成因）
- FACT-RECEIPT: `grep -rln GATE_DIR_OVERRIDE tests/governance` → `14 檔`；`grep -rn "pop.*GOVERNANCE_TEST_HARNESS" tests/governance` → `6 檔 10 處`（Claude 2026-07-27 機械清點）
- FACT-RECEIPT: `git config --get core.hooksPath` → `scripts/git_hooks`；`scripts/git_hooks/pre-push` 呼叫 `gov_check.sh --no-probe`
- FACT-RECEIPT: 以**實作型派工的實際產出**（`handoffs/20260727-p16-srcfix2-codex.md`，canonical ID 數 = 0）跑 `reconcile_build.sh` → **rc=1**、`COMPLETENESS FAIL: 無任何來源抽出 heading ID(vacuous)`（Claude 實跑 2026-07-27）→ **證實「不產意見清單的派工結構上無法走正常銷帳路徑」**，此即裁決 5 分兩種理由碼的成因

### 已確認結果（使用者裁決，憲法級）
1. **一律開債**：委員派工一律開債，不看有無下游、不看結論採不採用（2026-07-25 定）。
2. **一扇門**：所有委員派工走 `committee_run.sh`；無分類、無豁免、無執行通道（2026-07-25 定）。
3. **擋門範圍**：債未清 → 擋所有新派工，**含實作**（2026-07-25 定）。
4. **降低可繞過機率優先於完全阻擋**（2026-07-27 定，使用者原話：「要完全擋下的成本太高，那就盡可能降低可繞過的機率就好」）。→ 本版據此把舊版最貴的 token 時序機制簡化為單次帳本重查。
5. **逃生口在帳本可解析的前提下隨時可用、但須留痕，且須分兩種理由碼**（2026-07-27 定，取代舊版「軟 TTL 7 日逾期才可放棄」）。理由：等 7 日等於 7 日內什麼都不能派，實務上不可行。
   **逃生口須帶兩種理由碼之一**（枚舉值與判定條件定義於 §P Task 2.2，本節不重列）：一種代表「該輪產出本來就不是意見清單」，一種代表「真的收不齊」。**兩者都須留痕、都須非空理由與簽核者，沒有一種是免費的**；差別只在**分開計數**，讓後者不被前者淹沒。
   > **為何不用分類器自動判別**：憲法級裁決禁止用主委可自報訊號當分類器，而「這輪是不是實作」正是自報訊號。本設計**不假裝機器能分辨我的意圖**，改為讓**紀錄**可分辨，由使用者看兩個數字判斷。
6. **不支援中途補派**（2026-07-27 定）：要加家族 → 開新一輪。以摩擦換掉一整塊機制。
7. **先上線再迭代**（2026-07-27 定）：以能擋掉大部分情況的版本先上線，**上線後持續記錄實際發生的逃脫點，逐步修正**。→ 落地見 §V「逃脫點回報」。

### 待使用者確認
**待確認：無**

### 誠實邊界（**不得宣稱機器覆蓋**；上線後只准增列，不准刪減）
1. **`gate_check` 的重查只是次要補強，主擋門是 `gate.sh`**（**V1 更正，v2.0 此條寫反了**）：`gate_check.sh:50` 的 executor 正則**不命中** `bash scripts/cx_run.sh`／`bash scripts/committee_run.sh`（grok R1-P1-04 實測），故「fresh token 重查帳本」**幾乎不覆蓋官方入口**；真正的擋門是 `gate.sh` 的 `_check_open_debt`。此外 `gate_check.sh` 在 **jq 缺失或 JSON parse 失敗時直接 fail-open**、且**完全不比對 token 內容／task／intent**（codex R1-P1-01）——**皆為既有洞，本版不修**。
2. **`cx_run` 直呼**：拿到合法輪次編號後仍可直呼 `cx_run` 追加派工，不經 `committee_run`。本版以 membership 檢查限制危害（不能換 brief、**不能重派最新已 `success` 的家族**——見 Task 1.3 前置③），**但擋不住**。
2b. **dispatch → 開債之間的窗口**（composer R1-P1-02／P2-01）：`gate.sh` 發出 token 到 `committee_round_open` 實際寫入之間有一段空窗，該窗口內第二次 dispatch 仍會看到「無債」；若開債寫入失敗，token 仍 fresh 而帳本無債。**本版依裁決 4「降低機率優先於完全阻擋」不做原子交接**，明列為邊界。
2c. **帳本序號 gap／JSON 損毀＝需人工介入的故障狀態，機器不可自癒**（**R2 grok P1-01 更正了起草者對「死鎖」的認定**）：
   Task 2.1 改法⑦讓 `--abandon` 在序號 gap 下仍可執行，**但放棄之後 `--has-open` 仍會 rc=2，派工照樣被擋**。
   **起草者原以為「讓逃生口能用」就解了死鎖，這個認定是錯的。**
   深究後的正解：**序號 gap 代表帳本本身不可信，此時本來就不該放行派工**——這不是設計缺陷，是 fail-closed 的正確行為。故本版**不再宣稱「逃生口解決了所有死鎖」**，改為明列**復原程序**：
   ①先以 `--abandon` 結清受影響輪次（留痕）→ ②人工修復 `audit.log`（補回缺號或移除損毀行）或以綁 `GOVERNANCE_TEST_HARNESS=1` 的 `DEBT_AUDIT_OVERRIDE` 切換到乾淨路徑 → ③確認 `--has-open` 恢復 rc=0/1 後才能繼續派工。
   **步驟②出 §A 第 4 條信任模型之外**（需要人直接改檔），機器不保證、也不阻擋。
2d. **誤銷帳不可機械更正**（codex R1-P1-03／composer R1-P2-02）：本版砍除 `supersede` 事件，一筆誤寫的 `committee_debt_clear` 永久有效。補救＝手動在 audit 追加更正紀錄（出信任模型）或重開一輪。**登記於 §N，若實際發生一次即補**。
3. **純對話綜合**：讀完 N 份直接講結論、不派任何工 → **永遠**攔不到。
4. **檔案系統信任模型**：有 `.claude/gate/audit.log` 寫權者可直接偽造紀錄（無簽章／HMAC）。序號連續性擋的是「偷偷刪一筆」，不是「有權限的人偽造」。
5. **逃生口可被濫用**：主委隨時可放棄任一筆債。機器只保證留痕 ＋ 非空理由 ＋ 非空簽核者，**不保證不濫用**。降低濫用靠「每 session 開頭稽核報放棄筆數」＝社會性摩擦，非機械強制。
6. **`gate.sh artifact` / `register-output` 不在債務閘範圍**：主委仍可在有債時創建治理文件。
7. **銷帳只驗「機械合併回報 0 掉項」，不驗「綜合得對不對」**：委員意見有沒有被正確理解、分箱有沒有分錯，機器不判斷。
8. **不驗 brief 品質**：主委可蓄意寫爛 brief 讓委員交不出東西，然後走逃生口。**機器擋不住 brief 品質。**
9. **`abandon_kind` 是主委自報，機器不辨真假**：我可以把一次「真的收不齊」填成 `no-findings-expected` 混進實作那堆數字裡。**機器只保證兩種都留痕**；分辨真偽靠使用者看兩個數字的趨勢，是社會性摩擦，非機械強制。
10. **重派無次數上限，可用來無限拖延**：某家族一直失敗時，我可以一直重派而不清帳也不放棄，機器不擋。**v2.0 原稱「拖延期間新派工被擋＝自我懲罰」，此宣稱過強已刪**（codex R1-P1-02）：本 SPEC 同時保留 `cx_run` 可直呼（第 2 條），故拖延者**未必**被有效懲罰。真正的約束只有「不能開**新一輪**」。
11. **`discovery` session 完全不受 identity binding 保護**（v2.9 收窄的直接代價，三家裁決接受）：任何人可自由建立 `discovery` session，機器不查 audit、不綁 round。**擋得住的只有「拿它去銷帳」**（Task 2.2③ 要求 `mode=review`，而升到 review 必經 audit 反查）。
    **出生事故（實測，非推測）**：v2.8 原文要求「**建立 session 時**無條件反查 audit」，但寫入 `committee_round_open` 的是 Task 1.2（B3）。B1 合併後實測 `reconcile_build <新session>` → `rc=1 session_name 命中 0 筆`，**而 B2/B3 自己的 code review 就需要建 session** ⇒ **這台機器會鎖死自己的施工過程**。三家一致判 **P0**。修法即本條收窄。
    **誠實邊界**：本條讓「未經開債就開一輪討論並產出 discovery session」變成完全不留痕的動作——**這本來就在第 3 條（純對話綜合永遠攔不到）的射程內**，非新增漏洞，但**射程確實變大了**（現在連跑了收集工具也不必然留痕）。

## §C 約束
- 只動 `scripts/` 治理層與 `tests/governance/`；解耦 7 條不受影響。
- bash 3.2 相容（macOS 預設），**禁 `declare -A`**。
- **反 bypass 紅線**：任何新增 env override 一律綁 `GOVERNANCE_TEST_HARNESS=1`，否則 fail-closed。
- **家族不得寫死**：一律讀 SoT `scripts/governance_families.json`。
- **工具優先**：不得重造已存在工具的等效邏輯（合併／完整性驗一律呼叫 `scripts/reconcile_build.sh`／`scripts/completeness_check.sh`）。
- **不得改寫既有守衛 V-A/V-B/V-C/V-M 內部**；只可旁側新增呼叫。
- 下游消費者 `scripts/review_quorum_check.sh` 解析 `committee_dispatch.task_id`；新事件不得破壞其解析。
- **事件型別上限 4 種**（見 §P）。**新增第 5 種即屬範圍膨脹，須回頭改本 SPEC 並重戳**，不得在實作階段自行增加。

## §G Golden / Baseline
移 §N 標 N/A（RISK-HIT 無 a/d）。

## §P Phase 與依賴

> **四種事件（全部，不再有第五種）**：`committee_round_open`（開債）／`committee_family_result`（某家交件結果）／`committee_debt_clear`（銷帳）／`debt_abandon`（放棄）。
> **⚠️ 名稱以 registry 實際字串為準**（V1 三家指出 v2.0 用短名 `round_open` 而 registry 是 `committee_round_open`，實作端無所適從）。本文件與 `scripts/audit_events.json` **必須同一字串**。
> **三種狀態**：`OPEN`（欠著）／`CLOSED`（已銷）／`ABANDONED`（已放棄，終結）。
> 欄位定義集中於 `scripts/audit_events.json`；**本文件不重列欄位**。

### Phase 0 — SoT 對齊（依賴：無；**其餘所有 Task 依賴本 Task**）

**Task 0.1 — `scripts/audit_events.json` 砍成 v2 契約**
- 目標：消滅「SPEC 說 4 事件、SoT 檔仍是 11 事件」的矛盾。**這是 V1 三家一致的頭號 BLOCKING**（codex/composer/grok 各自實跑證實）。　檔案：`scripts/audit_events.json`
- **不做會怎樣（V1 實證的失敗鏈）**：實作端忠實讀 SoT → `enums.abandon_kind` 不存在 → `--abandon --kind …` 永遠 rc≠0 → 而實作型派工結構上又只能走逃生口（見 §A FACT-RECEIPT）→ **整台機器一啟用即死鎖**。
- 改法：
  ①**事件砍至四種**：`committee_round_open`／`committee_family_result`／`committee_debt_clear`／`debt_abandon`。**事件名一律採 registry 現有字串，不新造、不強加前綴**——三個 `committee_*` ＋ 一個 `debt_abandon`（它本來就沒有前綴，保留原名）。SPEC 正文與 registry 必須同一字串。刪除 `committee_round_amendment`／`committee_family_dispatch`／`committee_family_degrade`／`committee_debt_clear_format_failure`／`committee_debt_clear_all_degraded`／`committee_debt_supersede`／`round_open_failed`。
  ②`enums.round_state` 砍為 `OPEN|CLOSED|ABANDONED`；`enums.result_state` 砍為 `success|failed`。
  ③**新增 `enums.abandon_kind` ＝ `no-findings-expected|collection-failed`**；`debt_abandon.fields` 增 `abandon_kind`。
  ④`committee_family_result.fields` 須含 `output_sha256`（Task 2.2 銷帳要比對）。
  ⑤刪除已無消費者的 v1 幽靈常數（`attempt_cap`／`ttl_days`／`renew_once_per_round_family`／`clear_kind` 與其映射／`pending_deadline*` 等）與對應 `docs` 說明。
  ⑥`non_debt_legacy_events`（`committee_dispatch`／`committee_output`／`gate_deny`）**保留不動**——既有腳本仍在寫，砍掉會破壞現有 provenance。
  ⑦**所有平行容器須與砍後的 4 事件同步**（R2 codex P0-03／grok P1-02）：`required_fields_per_event`／`clear_kind_event_map`／`family_valued_fields`／`hardcode_scan_exemptions`／`event_object_allowed_keys` 等任何以事件名為鍵或值的結構，**殘留指向已刪事件的項目即 fail-closed**。`debt_abandon` 的既有必填欄須與 v2 契約對齊（移除 `remediation_owner` 等 v1 專屬欄，加入 `abandon_kind`）。
  ⑧**`committee_round_open.fields` 增 `session_name`**（Task 1.2⑦ 寫入、Task 2.2④ 讀取的 identity binding 真相源）。
  ⑨**lock 工具鏈支援 identity binding**：`reconcile_build.sh` 須①接受 **`--mode review|discovery`**（具名旗標、位置無關；**預設維持 `discovery`** 以免破壞既有呼叫）②建立 session 時**從 audit 查 `session_name` 對應的 `committee_round_open`，將其 `round_id` 寫入 `sources.lock`**，查不到即 fail-closed 拒建。`write_sources_lock.sh` 對應支援寫入 `round_id` 欄。
     ⚠️**反查的觸發條件＝「產生 `review` mode 的 lock 時」，不是「建立 session 時」**（v2.9 依 B1 三家裁決收窄；v2.8 原文寫「建立 session 時」無條件反查，**實測會鎖死本 epic 自己的施工過程**——見下方 §A 誠實邊界 11）：

     | 路徑 | audit 反查 | 額外守衛 |
     |---|---|---|
     | fresh `--mode discovery`（**預設**） | **不做**（不需 `round_id`） | 無 |
     | fresh `--mode review` | **必做**：`session_name` 對應的 `committee_round_open` **恰一筆** | — |
     | `--rebuild`（`discovery → review`） | **必做**：**恰一筆** | 該輪須 `OPEN`；只准 `discovery → review` 單向 |

     **為何這樣收窄仍然安全**：綁定的目的（Task 2.2④）是防「**銷帳端**自己產生綁定值」，而綁定**只在銷帳時有意義**；Task 2.2③ 已規定 `mode` 必須是 `review` 才能銷帳。故 `discovery` session 不需 `round_id`，而**任何 `review` lock 的 `round_id` 必來自 audit 反查**。
     ⚠️**此不變式須涵蓋所有 lock writer 路徑，不得只修 `reconcile_build.sh`**（B1 codex 指出主委原提案的漏洞）：`write_sources_lock.sh` 是**公開**入口，若它仍能直接建立 `review` lock 並塞入呼叫端給的 round，不變式即不成立。**所有 review-mode 的建立／升級一律由 writer 以 session 對應的 audit 自行導出 identity，不接受呼叫端傳入的 round**（或移除 public writer 的 review 建立路徑，改由單一受驗證 owner 寫入）。
     ③**接受 `--rebuild`，實作 Task 2.2 1b 的同名 `discovery → review` 就地升級**。此旗標**必須在本 Task 落地**（`reconcile_build.sh` 由本 Task 擁有），且須明確處理既有兩道拒絕牆：
        - **`reconcile_build.sh` 現行「session 已存在即 `exit 2`」**（`scripts/reconcile_build.sh:31-34`）：`--rebuild` 且 1b 三道守衛全過時**跳過此拒絕**；未帶 `--rebuild` 時行為不變（仍 `exit 2`）。
        - **`write_sources_lock.sh` 現行「`closure_state=FROZEN` 非 `--force` 不得覆寫」**：`--rebuild` 路徑下允許**就地改寫既有 lock 的 `mode` 欄（僅 `discovery → review`）並自 audit 重填 `round_id`**，其餘欄位（來源清單／各來源 hash／`expected_roster`）**一律保持不變**。
        - **明文禁止**以 `write_sources_lock.sh --force` 或設 `GOVERNANCE_TEST_HARNESS=1` 達成此升級——正式路徑必須自給自足。
     **本 SPEC 不提供 `--force` 重凍，也不提供任何「重綁 identity」的路徑**；`mode` 誤用的唯一補救是具名 `--rebuild` 的**單向**升級（見 Task 2.2 1b）。
- **驗證（可證偽）**：`python3 -m json.tool scripts/audit_events.json` rc=0；實跑印出 `debt_events` 長度 **== 4**；`enums.abandon_kind` **== 兩值**；`enums.round_state` **== 三值**；`enums.result_state` **== 二值**；`debt_abandon.fields` 含 `abandon_kind`；`committee_family_result.fields` 含 `output_sha256`；`grep -c attempt_cap scripts/audit_events.json` **== 0**；**任何以事件名為鍵或值的容器（`required_fields_per_event`／`clear_kind_event_map`／`family_valued_fields`／`hardcode_scan_exemptions`／`event_object_allowed_keys` 等）中，不得殘留指向已刪事件的項目——逐容器實跑清點並印出 0**（改法⑦的驗收，v2.2 漏列）；**`committee_round_open.fields` 含 `session_name`**（改法⑧）；**`bash scripts/reconcile_build.sh --help`（或無參數）印出 `--mode` 與 `--rebuild`**（改法⑨）；**以 audit 中不存在的 session 名跑 `reconcile_build` → rc≠0**、**以重複的 session 名跑 → rc≠0**（改法⑨的兩道 fail-closed）；`bash scripts/gov_check.sh` rc=0（既有 287 測試不得因本改動轉紅）
- **邊界（≥2）**：①砍除的事件名若仍被任何 `scripts/*.sh` 引用 → 先修引用再砍，不得留懸空引用 ②`non_debt_legacy_events` 誤砍 → 既有 `verify_task_provenance` 等消費端會壞，須實跑既有測試確認
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得在 SPEC 正文重列 registry 的欄位表／枚舉值（會回到漂移）；不得為了通過而保留 v1 事件

---

### Phase 1 — 留痕（依賴：Phase 0）

**Task 1.1 — `audit_append.sh`：唯一寫入點**
- 目標：所有債務紀錄只能經此腳本寫，序號連續、可稽核。　檔案：新增 `scripts/audit_append.sh`
- 改法：①**以 `mkdir` 原子鎖**保護「讀尾端序號 → +1 → append」為單一臨界區——**不得用 `flock`**（V1 codex 實測 `command -v flock` → 不存在；本 SPEC 宣告 bash 3.2／macOS 相容，`flock(1)` 非 macOS 內建）。`mkdir` 在 POSIX 上保證原子性，取不到鎖時以有上限的重試 + 逾時 fail-closed ②`producer` 由本腳本強制填入，呼叫端指定即忽略覆寫 ③事件名／必填欄位讀 `scripts/audit_events.json`（**Task 0.1 對齊後的 v2 形狀**），缺欄 fail-closed ④陣列欄位以 `--field k=@<json>` 傳入，非法 JSON 拒寫 ⑤既有 legacy 事件（`committee_dispatch`／`committee_output`／`gate_deny`）**不受序號規則管**，不參與連續性掃描
  ⑥**原子 predicate+append（`--require-absent-session <name>`）**：本腳本提供此旗標，語意＝「**在本腳本自己那把鎖之內**先掃 audit：若已存在 `session_name == <name>` 的 `committee_round_open` 則**不 append 並 rc≠0**；否則 append」。
     **為何必須長在本 Task**：鎖由本腳本持有。若讓呼叫端（Task 1.2）先取鎖再呼叫本腳本，本腳本會再取同一把鎖 → **自鎖**；若呼叫端先放鎖再 append → **TOCTOU 回歸**。故唯一可執行的形態是**把判定搬進持鎖者**，由本腳本一次完成判定與寫入。
     **不得**因此新增任何繞過本腳本的旁路，**不得**提供 reentrant 鎖或鎖交接 API（兩者都會製造新的可繞面）。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_emit.py -q` 全綠；兩程序併發各寫 100 筆 → 序號 `sorted(seqs) == range(1,201)`；呼叫端傳 `producer=fake` → 落地值為 `audit_append.sh`；缺必填欄 → rc≠0；混入現存 legacy 紀錄 → 不誤報缺號；**`--require-absent-session S` 在 audit 已有同名 `committee_round_open` 時 → rc≠0 且 audit 行數不變**（改法⑥）；**兩程序同時以 `--require-absent-session S` 競爭 → 恰一筆成功、另一筆 rc≠0，audit 中 `session_name == S` 恆為一筆**（改法⑥的原子性驗收，證偽 check-then-append）；**呼叫端自行持鎖後再呼叫本腳本 → 不得成功**（證偽「鎖交接」形態）
- **邊界（≥2）**：①audit 檔不存在 → 建立而非崩潰 ②取鎖逾時 → fail-closed ③registry 缺檔／JSON 壞 → fail-closed
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得讓任何 Task 繞過本腳本；不得硬編事件名

**Task 1.2 — `committee_run.sh` 開債**
- 目標：派工即記一筆債，輪次編號主委不可指定。　檔案：`scripts/committee_run.sh`（現 60-75 行區塊）
- 改法：①`round_id` 由本腳本 mint（UUID v4），**主委不得指定** ②寫入時機＝`gate.sh dispatch` 成功之後、啟動 `cx_run.sh` 之前 ③寫入失敗 → `exit≠0` 且**不得啟動 `cx_run`** ④`task_id` 從透傳 argv 解析 gate 的 `--task-id`，**不另發明同名旗標**；缺則 rc≠0 ⑤以 env `ROUND_ID` 傳給 `cx_run.sh`
  ⑥**`committee_round_open` 必記的欄位**（V1 grok 指出未寫明，而 Task 1.3 與帳本都要比對它們）：`round_id`／`task_id`／**該輪家族名單**／**每家族的 expected 產出路徑**／`brief_path`。**具體欄位名以 registry 為準，本文件不重列值**。
  ⑦**新增 `--session <name>` 參數，並把 `session_name` 記進 `committee_round_open`（Task 2.2④ identity binding 的產生端）**：
     `--session` 為**必填**，值＝之後 `reconcile_build.sh <name>` 將使用的 session 名稱；缺則 rc≠0。
     **全域唯一性（fail-closed，且須為原子操作）**：開債前先掃 audit，**若該 `session_name` 已出現在任一 `committee_round_open` → 拒開債 rc≠0**。理由：`session_name` 是 Task 2.2④ 反查 `round_id` 的鍵，重名會造成綁定歧義。
     ⚠️**唯一容許的實作形態＝呼叫 `audit_append.sh --require-absent-session <name>`（Task 1.1 改法⑥），由該腳本在自己的鎖內一次完成判定與寫入**。
     **`committee_run.sh` 本身不得自行掃描後再 append**（check-then-append），**也不得自行取鎖後呼叫 `audit_append.sh`**（會自鎖）。否則兩程序可同時掃到「不存在」後各寫一筆同名事件 → Task 2.2④ 反查命中 ≥2 → 兩輪債都無法正常銷帳，只剩 `--abandon`。
     **綁定的真相源是 audit 紀錄本身**（由 `audit_append.sh` 寫入、`debt_clear.sh` 無寫入權），**不另建任何檔案**。
     **不得**在開債時建立 session 目錄或寫入其中的任何檔案——**session 目錄是 `reconcile_build.sh` 在委員交件之後才建立的，開債當下不存在**。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_emit.py -q` 全綠；派 3 家後恰 1 筆 `committee_round_open` 且家族清單長度 3；**派 1 家也必須寫**；同一 `round_id` 第二筆 → rc≠0；gate 拒發 token → audit 零新增；**缺 `--session` → rc≠0**；**寫入的 `committee_round_open` 含非空 `session_name`**；**開債後 `handoffs/reconcile/<name>/` 仍不存在**（證偽「開債時建目錄」的錯誤設計）；**第二次以同一 `--session` 名開債 → rc≠0 且 audit 事件數不增長**（改法⑦全域唯一性的驗收，v2.6 漏列）；**兩程序並行以同一 `--session` 名開債 → 恰一筆成功、另一筆 rc≠0，audit 中該 `session_name` 恆為一筆**（改法⑦原子性的驗收）
- **邊界（≥2）**：①N=1 仍開債 ②只含 advisory 家族仍開債 ③寫入失敗不啟動 `cx_run`
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得讓主委指定新 `round_id`；不得對 N=1 略過開債；**不得實作「中途補派」**（使用者裁決 6）

**Task 1.3 — `cx_run.sh` 記每家結果**
- 目標：每家交件與否留痕；並限制直呼危害。　檔案：`scripts/cx_run.sh`
- 改法：①CLI 結束後寫 `committee_family_result`（家族名由 `$1` 直取，**不得從路徑或 review_role 推導**）②`result_state` 二值：`success`＝產出存在且非空且 `cli_rc==0`；其餘 `failed` ③**fail-closed 前置**：`ROUND_ID` 已設、audit 有對應 `committee_round_open`、該家族在該輪名單內、產出路徑與 `committee_round_open` 登記一致、**本次 brief 的 sha256 == `committee_round_open` 記錄的 brief sha256**(R2 codex P0-02:v2.1 前置漏此條,可換 brief 掛既有 round,與 §A#2 宣稱矛盾)、**該 `(round,family)` 最新 `result_state` 不是 `success`** ④CLI 失敗仍寫 result 帶 `cli_rc`，不得靜默
  ⑤**同輪重派明確允許（限尚未成功者）**：家族本來就在該輪名單內且最新結果非 `success`，以同一 `ROUND_ID` 再跑一次即可，**不需開新輪、不需任何補派機制**（與裁決 6「不支援中途補派」不衝突——補派是加**新**家族，重派是同一家族再試）。每次重派各寫一筆，**append-only 不覆蓋**。
  ⑥**產出指紋**：`committee_family_result` 須記 `output_sha256`;**`result_state=failed`(CLI 失敗或無產出檔)時填空字串**,銷帳條件⑤只對 `success` 家族比對(R2 codex P1-04:v2.1 同時要求「失敗仍寫 result」與「每筆須有非空 sha」,互斥)（Task 2.2 銷帳時比對，防「交件後替換內容再銷帳」——V1 codex R1-P1-04）。
  ⑦**不設重派次數上限**（舊版 attempt_cap 一併砍除）。誠實邊界見 §A（**v2.0 原寫「拖延＝自我懲罰」過強，已修正**）。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_emit.py -q` 全綠；合法呼叫後 `family` 欄位為實際家族名（**非 `unknown`**）；`ROUND_ID=不存在的值` → rc≠0 且 audit 零新增；家族不在該輪名單 → rc≠0；CLI 回非 0 → 仍寫一筆 result；**對最新已 `success` 的家族重派 → rc≠0 且 audit 零新增**；**`success` 的 result 含非空 `output_sha256` 且等於當時產出檔的 sha256；`failed` 的 result `output_sha256` 為空字串**（兩態分別驗，不得混為一條）
- **邊界（≥2）**：①`ROUND_ID` 未設 → 拒派 ②並發 3 家 → 3 筆完整不交錯 ③audit 檔不存在 → 建立而非崩潰
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得從產出路徑推導家族；不得把 CLI 執行放進鎖的臨界區

### Phase 2 — 帳本與銷帳（依賴：Phase 1）

**Task 2.1 — `debt_ledger.sh`：只讀紀錄算未結案債**
- 目標：由客觀紀錄算出哪些輪還欠著。　檔案：新增 `scripts/debt_ledger.sh`（**不另存狀態檔**）
- 改法：①只認 `startswith("{")` 的 JSON 行；**以 `{` 開頭但 JSON 解析失敗 → fail-closed rc=2**（V1 codex R1-P1-07：v2.0 只說「認 `{` 開頭的行」，沒說解析失敗怎麼辦，半截寫入可被靜默忽略）②每筆 `committee_round_open` 即一筆債；有合法 `committee_debt_clear` → `CLOSED`；有 `debt_abandon` → `ABANDONED`；其餘 `OPEN` ③cutoff 之前的紀錄一律不計（值讀 registry，僅 `GOVERNANCE_TEST_HARNESS=1` 可覆寫）④白名單事件序號缺號／重號 → fail-closed
  ⑦**`--abandon` 的讀取路徑例外（防死鎖，V1 三家一致的 P0）**：`debt_clear.sh --abandon` 判定「該輪是否存在」時，**只做該 `round_id` 的單筆 `committee_round_open` 存在性掃描，不跑全域序號連續性檢查**。理由：④的 fail-closed 若同時擋住逃生口，會形成「不能派、不能銷、也不能放棄」的三路全斷。正常銷帳與擋門路徑**仍維持 ④ 的 fail-closed 不放寬**。
  ⑤**同一 `(round_id, family)` 有多筆 `committee_family_result` 時，一律取序號最大（最新）那筆**——重派成功後不得再被舊的 `failed` 紀錄拖住（Task 1.3 改法⑤的必要配套）。
  ⑥子命令：`--list`（列出）／`--has-open`（rc 0=無債、1=有債、2=fail-closed）／`--abandoned-count`（**依 `abandon_kind` 分開輸出兩個數字**，支撐使用者裁決 5 與 7 的逐步修正）
- **驗證（可證偽）**：`pytest tests/governance/test_debt_ledger.py -q` 全綠；派 3 家 → `--list` 1 筆 `OPEN`；**派 1 家 → 也 1 筆 `OPEN`**；銷帳後 → 0 筆；cutoff 前紀錄 → 0 筆；**audit 存在但零 JSON 行 → 無債 rc=0**（14 檔隔離測試依賴此）；audit 檔缺失 → rc=2
- **邊界（≥2）**：①audit 缺失 → fail-closed ②audit 空 → 無債放行 ③同一 `round_id` 兩筆 `committee_round_open` → fail-closed
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得另存狀態檔；不得靜默自動過期

**Task 2.2 — `debt_clear.sh`：唯一銷帳路徑 + 逃生口**
- 目標：跑機械合併且 0 掉項才算還債；並提供防死鎖的人工放棄。　檔案：新增 `scripts/debt_clear.sh`
- 改法：
  1. **銷帳（`--round-id … --session …`）六項全成立才寫 `committee_debt_clear`**：
     ① 該輪處於 `OPEN`
     ② `completeness_check.sh --lock` 實跑 **rc=0**
     ③ **lock 的 `mode` 必須是 `review`**：`completeness_check.sh` 在 `discovery` 模式下不強制 P0/P1 附來源摘要，故「0 掉項」可在委員完全沒附佐證時通過＝**本機器的核心價值失效**。**建立 session 當下即以 `--mode review` 產生**（見 1b）；誤用 `discovery` 時**不提供 `--force` 重凍，僅允許具名 `--rebuild` 的單向就地升級**（見 1b 與 Task 0.1 改法⑨③）。
     ④ **identity binding，且綁定值不得由銷帳端產生**：
        - `committee_run.sh` 開債時把 **`session_name`** 記入 `committee_round_open` 事件（Task 1.2⑦）。**綁定的真相源是 append-only 的 audit 紀錄，不是任何額外檔案。**
        - `reconcile_build.sh <name>` 建立 session 時，**從 audit 查出 `session_name == <name>` 的 `committee_round_open`，取其 `round_id` 寫入 `sources.lock` 的 `round_id` 欄**。**命中 0 筆或 ≥2 筆一律 fail-closed 拒建**——不得做「取最新」「取第一筆」等隱含選擇（唯一性由 Task 1.2⑦ 在開債端保證，此處為第二道防線）。
        - `debt_clear.sh` 銷帳時驗 **`lock.round_id` == `--round-id` 傳入值**，且 **對 `sources.lock` 一律只讀，不得建立或修改任何欄位**。
        - 附加檢查：**`sources.lock` 的 `expected_roster` 集合 == `committee_round_open` 的家族名單欄位集合**（兩側欄位名不同，實作端勿比錯欄位；`committee_round_open` 側的實際欄位名以 registry 為準）。**僅為附加，不可單獨作為綁定**——本專案每輪都派同樣三家，roster 集合永遠相同，零鑑別力。
  1b. **session 建立即定 mode（不提供 `--force` 重凍；僅具名 `--rebuild` 單向升級）**：
     收齊委員產出後，主委以 **`bash scripts/reconcile_build.sh <session-name> --mode review <委員檔...>`** 建立 session；`--mode` 為**具名旗標，位置無關**。
     **誤用 `discovery` 建立時的復原＝同名升級，不得換名**：`bash scripts/reconcile_build.sh <同一 session-name> --mode review --rebuild`。
     `--rebuild` 為**具名旗標且自帶守衛**（**不使用 `--force`**——該旗標綁 `GOVERNANCE_TEST_HARNESS=1`，正式路徑不可達）。三項全成立才放行：
     ①audit 中該 `session_name` 的 `committee_round_open` **存在且恰為一筆** ②該輪狀態仍為 `OPEN` ③**只允許 `discovery → review` 單向升級，反向一律拒**。
     三道全過時，`--rebuild` **就地**升級既有 session：跳過「session 已存在即拒」、改寫既有 lock 的 `mode`、自 audit 重填 `round_id`，**來源清單／各來源 hash／`expected_roster` 一律不變**（落地細節見 Task 0.1 改法⑨③）。
     **不得以「換一個 session 名」作為復原手段**——`session_name` 在開債當下即綁進 `committee_round_open`，換名後 audit 查無對應事件，`reconcile_build` 會 fail-closed 拒建，**復原路徑等於不存在**。
     `debt_clear.sh` 遇 `mode != review` 一律拒絕，並在錯誤訊息中印出上述建立與升級命令。
     ⑤ **每個家族的最新 `committee_family_result` 皆為 `success`，且其 `output_sha256` == 該產出檔當前的 sha256**（防交件後替換內容再銷帳）
     ⑥ 寫入的 `committee_debt_clear` 事件**記下當次 lock 檔的 sha256** 供事後稽核（**只做記錄，不作為綁定判準**——lock 在時間上晚於開債，開債當下無從預存可比對的值）
  2. **完整性一律呼叫既有工具**（`scripts/completeness_check.sh`），**禁自寫等效比對邏輯**（§C 工具優先）。
  3. **逃生口（`--abandon --round-id … --kind <abandon_kind> --reason … --approver …`）**：**在帳本可解析的前提下隨時可用**（不受任何期限限制；帳本損毀時的復原程序見 §A 誠實邊界 2c）（使用者裁決 5），但四項缺一即拒——`kind` ∈ registry `enums.abandon_kind`、`reason` 須達 registry 下限字數、`approver` 非空、該輪須存在且非 `ABANDONED`。寫 `debt_abandon`（含 `abandon_kind` 欄），該輪轉 `ABANDONED`（**不可逆**）。
     **`abandon_kind` 兩個枚舉值與適用情境**：

     | 值 | 什麼情況 | 為何需要 |
     |---|---|---|
     | `no-findings-expected` | 該輪產出**本來就不是意見清單**（派實作／修檔／蓋章類） | 見 §A FACT-RECEIPT：零 canonical ID 的來源跑合併工具會被判 vacuous 拒收，**結構上走不通正常銷帳路徑** |
     | `collection-failed` | 真的收不齊（委員交不出合格產出、格式損毀等） | **這才是該警覺的訊號**，須與上者分開計數 |
     **⚠️ 放棄的是「證明收齊」這項義務，不是委員產出**：已交件家族的產出檔一律保留，仍可使用；`debt_abandon` 不刪除任何 `committee_family_result` 或產出。
     **⚠️ 逃生口的讀取路徑必須抗帳本故障（V1 三家一致的死鎖修法）**：「該輪須存在」的判定**只做該 `round_id` 的單筆掃描，不跑全域序號連續性檢查**（見 Task 2.1 改法⑦）。否則序號缺號時 `--abandon` 會與擋門一起 fail-closed → **不能派、不能銷、也不能放棄**。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_clear.py -q` 全綠；拿 A 輪 lock 銷 B 輪 → rc≠0；lock roster 與該輪家族集合不相等 → rc≠0；**lock `mode=discovery` → rc≠0**（A5 的具名 oracle）；`completeness` rc≠0 → 拒銷；**某家產出檔在交件後被改動（sha 不符）→ rc≠0**；重複銷帳 → 冪等 no-op；`--abandon` 缺 `reason`／`approver`／`kind` → rc≠0；**`--abandon` 在 `OPEN` 未逾任何期限時 → rc=0**（證偽「必須逾期才能放棄」的舊設計）；**audit 存在序號缺號時：`--has-open` rc=2 但 `--abandon` 仍 rc=0**（死鎖修法的具名 oracle）；`ABANDONED` 後再銷 → rc≠0
  **1b `--rebuild` 的行為驗收（v2.6 只有 M33 名稱、無可執行 oracle，v2.7 補）**：**discovery 建成的 session ＋ 該輪 `OPEN` ＋ audit 恰一筆 → `reconcile_build <同名> --mode review --rebuild` rc=0 且 `sources.lock` 的 `mode` 轉為 `review`、`round_id` 非空、來源清單與各來源 hash 與升級前逐欄相同**（happy path，證偽「旗標存在但沒真的升級」）；**同一情境不帶 `--rebuild` → 仍 rc≠0**（證偽「`--rebuild` 把既有拒絕牆整個拆掉」）；**`review → discovery` 反向 → rc≠0**；**該輪已非 `OPEN` → rc≠0**；**audit 命中 0 筆或 ≥2 筆 → rc≠0**；**整條升級路徑在 `GOVERNANCE_TEST_HARNESS` 未設時可完成**（證偽「正式路徑不可達」——此為 R5/R6 兩度復發的病灶）
- **邊界（≥2）**：①`committee_round_open` 不存在 → 拒 ②lock 的 `round_id` 與 `--round-id` 不符 → 拒（**R2 更正**:v2.1 原寫「lock 被竄改 sha 不符→拒」,與「⑥只事後記錄不預存」自相矛盾,無可比對基準） ③`completeness` 回 DEGRADED（rc=3）→ 不得銷帳
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得接受 `waived:` 字串當銷帳；不得讓任何旗標繞過銷帳的六項綁定或放棄的四項必填；**不得自動放棄**（放棄一律人工且留痕）

### Phase 3 — 擋門與回歸（依賴：Phase 2）

**Task 3.1 — `gate.sh` 債務閘 + `gate_check.sh` 重查**
- 目標：有未清債 → 拒發新派工 token（含實作）。　檔案：`scripts/gate.sh`（dispatch 分支）、`scripts/gate_check.sh`
- 改法：①`gate.sh` 新增 `_check_open_debt()`，**唯一呼叫點**＝dispatch 分支必填欄位檢查之後、既有 completeness 閘之前 ②判定極簡：`debt_ledger.sh --has-open` 回報有債 → 拒發，**不分討論／實作**（使用者裁決 3）③audit 來源固定為 registry 登記路徑；測試隔離走**綁 `GOVERNANCE_TEST_HARNESS=1`** 的 `DEBT_AUDIT_OVERRIDE`，**不得讀未綁 harness 的 `GATE_DIR_OVERRIDE`** ④`gate_check.sh` 對 fresh token **不再直接放行**，改為重查一次帳本（使用者裁決 4 的落地；**不做 token 指紋／時序機制**）⑤`debt_ledger.sh` 缺失或崩潰 → fail-closed
- **驗證（可證偽）**：`pytest tests/governance/test_debt_gate.py -q` 全綠；有 `OPEN` 債時開新輪 → rc≠0 且 token 檔 mtime 未變；**有 `OPEN` 債時實作派工（帶 `--spec`）→ 也 rc≠0**（使用者裁決 3 的具名 oracle）；債清後 → rc=0；`GATE_DIR_OVERRIDE` 指向空目錄但真 audit 有債 → **仍 rc≠0**；`DEBT_AUDIT_OVERRIDE` 未帶 harness → rc≠0；`debt_ledger.sh` 改名 → rc≠0；**單次 `gate_check` 耗時 < 100ms**（以當前 audit 行數實測附 receipt——V1 codex/composer 指出 audit 是 append-only 只會變長，熱路徑每次重掃是 O(N) 且 v2.0 未設驗收；**超過即須改為只掃尾端 N 行或建索引**）
- **邊界（≥2）**：①空 audit ＝無債放行 ②多筆 open 債 → 全部列出，任一未清即拒 ③本 epic 自身派工同樣受管
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得新增任何 `--debt-waived` 逃生旗標；不得改寫 V-A/V-B/V-C/V-M 內部

**Task 3.2 — mutation 探針 + 既有測試回歸**
- 目標：證明閘門非假綠，且不弄壞既有測試。　檔案：`tests/governance/test_debt_*.py`
- 改法：
  ①§V 每類 mutation 各一常駐探針。
  ②**探針以 Python 受測面書寫（本版預先選定的收口路徑，非「遇到再說」）**：新增 `tests/governance/_debt_probe_helper.py` 作為薄封裝層，把各 shell 腳本的判定入口包成 Python 函式（內部 `subprocess` 呼叫真腳本）；探針 `monkeypatch` 該 helper 的模組常數（如腳本路徑、registry 路徑）來注入變異。**這使探針天然滿足 `mutation_probe_static.py` 的判準，且不是塞假 `monkeypatch`——被 patch 的是真正決定行為的變數。**
  ③既有 287 測試逐檔跑，轉紅者逐檔判「真回歸」vs「fixture 契約更新」，**禁 skip／xfail／waiver**。
  ④**14 個用 `GATE_DIR_OVERRIDE` 隔離的測試須補 `DEBT_AUDIT_OVERRIDE` + harness**（或於 `conftest.py` 層預設隔離空 audit）——**V1 composer/grok 指出**：現有測試只隔離 token 不隔離債務 audit，開發機留有 OPEN 債會使整個治理測試集**假紅**。6 檔 10 處 `pop GOVERNANCE_TEST_HARNESS` 亦須逐處確認不觸發 fail-closed。
- **驗證（可證偽）**：每類 mutation 改壞 → 對應具名測試轉紅、復原轉綠（逐條 receipt）；`pytest tests/governance -q` 全綠且總數 ≥ 287；`bash scripts/gov_check.sh` rc=0；**`bash scripts/mutation_probe_check.sh tests/governance/test_debt_*.py` rc=0**（＝改法②真的解決了靜態閘問題的具名 oracle）；**在 `.claude/gate/audit.log` 人工預置一筆 OPEN 債後，`pytest tests/governance -q` 仍全綠**（＝改法④的具名 oracle）
- **邊界（≥2）**：①探針自身失效 → 由 `scripts/mutation_probe_check.sh` 抓 ②既有測試轉紅 → 逐檔判定，禁 skip ③helper 封裝層本身出錯 → 該層須有自己的單元測試
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得為求通過而放寬既有斷言；**不得為通過靜態閘而塞入與行為無關的假 `monkeypatch`**
- **⚠️ 逃生條款（僅在改法②被證明不可行時啟用）**：若實作端實測發現 helper 封裝法仍過不了靜態閘，**停手回報，不得自行塞假 `monkeypatch`、不得自行加豁免**。2026-07-27 已實證：直接為 shell 腳本寫探針會被判偽自證並使 `gov_check` 轉紅。

## §V 驗證策略與邊界測試目錄

- **mutation 類別**（每類一常駐探針；**類別清單以本節為唯一來源，不在他處重列**）：
  | ID | 改壞哪裡 | 必轉紅的測試 |
  |---|---|---|
  | M1 | 債檢查函式永遠回報無債 | `test_open_debt_blocks_new_round` |
  | M2 | `cx_run` 不寫 `committee_family_result` | `test_each_family_result_recorded` |
  | M3 | 銷帳不校驗 `round_id` | `test_reject_foreign_round_clear` |
  | M4 | 銷帳允許 lock 家族少於該輪名單 | `test_clear_requires_full_roster` |
  | M5 | `waived:` 被誤當銷帳 | `test_waive_does_not_clear_debt` |
  | M6 | `ROUND_ID` 只驗非空、不驗 `committee_round_open` 存在 | `test_cx_run_rejects_forged_round_id` |
  | M7 | N=1 被略過開債 | `test_single_family_still_opens_debt` |
  | M8 | 只掛 `gate_check` 不掛 `gate.sh` 本體 | `test_gate_sh_enforces_debt_without_hook` |
  | M9 | 有債時實作派工未被擋 | `test_open_debt_blocks_impl_dispatch` |
  | M10 | `producer` 由呼叫端指定而非強制覆寫 | `test_producer_forced_by_pipeline` |
  | M11 | 序號非原子（併發產生重號/缺號） | `test_concurrent_append_sequence_unique` |
  | M12 | 放棄不需 `reason`／`approver` | `test_abandon_requires_reason_and_approver` |
  | M12b | 放棄不需 `abandon_kind`，或接受列舉外的值 | `test_abandon_requires_valid_kind` |
  | M12c | `--abandoned-count` 把兩種理由碼合併成一個數字 | `test_abandoned_count_split_by_kind` |
  | M16 | 帳本取**最舊**而非最新的 `committee_family_result`（重派成功仍被舊 `failed` 拖住） | `test_ledger_takes_latest_family_result` |
  | M17 | 銷帳只驗 lock 涵蓋全家族，不驗每家最新結果為 `success` | `test_clear_requires_all_families_success` |
  | M20 | registry 被改回 v1 形狀仍全綠——含事件數 ≠ 4／缺 `abandon_kind`／**任一平行容器殘留指向已刪事件的鍵或值**（改法⑦的機械面）〔VERIFY-EXEMPT:doc-example:m20-mutation　本欄描述「改壞後應轉紅」的假設情境，非宣稱已實跑〕 | `test_registry_is_v2_shape` |
  | M21 | 銷帳接受 `mode=discovery` 的 lock（P0/P1 缺來源摘要仍可銷帳） | `test_clear_requires_review_mode_lock` |
  | M22 | 帳本序號缺號時 `--abandon` 也被 fail-closed（死鎖復現） | `test_abandon_survives_sequence_gap` |
  | M23 | 以 `{` 開頭但 JSON 解析失敗的行被靜默忽略 | `test_corrupt_json_line_fail_closed` |
  | M24 | 銷帳不比對 `output_sha256`（交件後替換內容仍可銷帳） | `test_clear_detects_stale_output` |
  | M25 | 對最新已 `success` 的家族允許重派（可自咬卡住銷帳） | `test_reject_redispatch_of_success_family` |
  > **刻意不設 mutation 的項目**：`dispatch → committee_round_open` 之間的窗口（§A 誠實邊界 2b）**已依裁決 4 明文接受為誠實邊界**，故**不為它設 mutation**。設了等於要求測試擋住一件 SPEC 自己宣告不擋的事，屬自相矛盾。
  | M27 | 銷帳只比對 lock roster 集合、不比對 `lock.round_id`（同 roster 的錯輪 lock 可銷帳） | `test_clear_requires_round_id_binding` |
  | M28 | `cx_run` 不驗 brief sha（可換 brief 掛既有 round） | `test_cx_run_rejects_brief_swap` |
  | M29 | **`debt_clear.sh` 自行改寫 `sources.lock` 的 `round_id` 後仍能銷帳**（provenance 鏈被繞過，＝自簽自驗） | `test_clear_cannot_author_its_own_binding` |
  | M30 | **lock 以 `discovery` mode 建立卻仍能銷帳** | `test_clear_requires_review_mode_lock_at_build` |
  | M31 | `committee_run.sh` 未記 `session_name`，或 `reconcile_build.sh` 未從 audit 取 `round_id` 寫入 lock，銷帳仍能通過 | `test_session_name_provenance_required` |
  | M32 | **`session_name` 可重複**（開債端不擋重名，或 reconcile 反查多筆時做隱含選擇） | `test_session_name_must_be_unique` |
  | M34 | **唯一性判定被搬出 `audit_append.sh` 的鎖**（改回 check-then-append，或改用鎖交接／reentrant 鎖）→ 兩程序同名競爭仍能各寫一筆 | `test_session_uniqueness_is_atomic_with_append` |
  | M33 | **`--rebuild` 允許 `review → discovery` 反向降級，或對非 `OPEN` 輪次生效** | `test_rebuild_upgrade_only_and_open_only` |
  | M13 | 債務閘讀未綁 harness 的 `GATE_DIR_OVERRIDE` | `test_gate_dir_override_cannot_hide_debt` |
  | M14 | `gate_check` 對 fresh token 直接放行 | `test_fresh_token_rechecks_ledger` |
  | M15 | 新增 env override 未綁 `GOVERNANCE_TEST_HARNESS` | 沿用既有反 bypass 測試 |
- **測試層級**：單元（帳本／schema）／整合（真跑一輪派工看紀錄）／邊界／併發／mutation。可獨立 `pytest tests/governance/ -q`。
- **防假綠**：diff 既有測試斷言，不得放寬或刪除換綠。
- **⛔ 禁止的驗收寫法**：不得用不可測百分比；一律列舉具體反例逐條跑。
- **既有測試回歸**：14 檔用 `GATE_DIR_OVERRIDE` 隔離、6 檔 10 處 `pop GOVERNANCE_TEST_HARNESS`（值見 §A FACT-RECEIPT），**逐檔實跑確認不被誤擋**；矩陣由 Task 3.2 產出，**不在本文件重列**（重列必漂）。
- **逃脫點回報（使用者裁決 5 與 7 的落地）**：上線後每次 session 開頭稽核須執行 `bash scripts/debt_ledger.sh --abandoned-count`，並**把兩個數字都報給使用者**，格式例：`累積放棄：no-findings-expected 12 筆／collection-failed 1 筆`。
  **判讀方式**：第一個數字隨派實作次數自然成長屬正常；**第二個數字成長＝真的有輪次收不齊，須追根因**。
  另將**實際發生**的繞過／逃脫情形增列到 §A 誠實邊界。**該節只准增列，不准刪減**——刪一條等於宣稱已覆蓋。

## §R 回退
- **Phase 3（擋門）**：`revert` 該 commit，或註解 `gate.sh` 內 `_check_open_debt` 的**單一呼叫點**即可移除擋門。
- **明確不回退**：已寫入 audit 的紀錄（append-only）。回退後系統**留痕但不擋**（向後相容）。
- 每 Phase 獨立 commit，可單獨 revert。任一 Phase 導致既有測試轉紅且非 §V 所列 → 不 merge。
- audit 事件 schema 不可回退 → 故 Phase 1 的 schema 必須先過 adversarial 審才實作；此為本 SPEC 走完整管線的主要理由。

## §N N/A 登記
- **§G Golden / Baseline：N/A** — RISK-HIT 為 `b,c`，未命中 (a)/(d)。僅動 `scripts/` 治理層與 `tests/governance/`，無數值輸出可對照。**替代保證**＝§V 的 mutation 類別 + 既有測試逐檔回歸 + 各 Task 具體反例。
- **以下為 v1.2.2 砍除項，登記為「上線後再議，真的踩到才做」**（去向明列，非遺失）：
  | 砍除項 | 原用途 | 為何砍 | 何時再議 |
  |---|---|---|---|
  | 中途補派（amendment） | 沿用同一筆債追加家族 | 使用者裁決 6 | 真的頻繁需要追加時 |
  | 格式失敗出口／全體降級出口／單家退出+續期／清錯帳更正 | 四種特殊清帳路徑 | 全部併入單一逃生口 | 逃生口被證明摩擦不足時 |
  | brief 範本閘（V-E） | 標 `impl` 跳過範本檢查 | 本就是獨立的洞 | **另立票**，不屬本 epic |
  | 事件真相源 + 12 項守衛 | 管 11 種事件的同步 | 事件僅剩 4 種 | 事件型別需超過 4 種時（同時須回頭改本 SPEC） |
  | token 時序機制（指紋／預發號／不可變期限／自污豁免） | 完全阻擋 token 時序競態 | 使用者裁決 4 | §A 誠實邊界第 1 條的競態**實際發生**時 |
  | `governance_tools.json` 強制力機械化 | 「凡有可用腳本一律套用」 | 與本 epic 無共用程式碼 | **另立票**（另需委員先裁定哪些工具真的 mandatory） |
- **誤開輪次的撤銷路徑：N/A（以逃生口取代）** — 誤開者走 `--abandon`，留痕。
- **誤銷帳的更正路徑（V1 新增登記）**：本版砍除 `supersede`，一筆誤寫的 `committee_debt_clear` 永久有效（誠實邊界 2d）。**觸發條件＝實際發生一次誤銷帳**，屆時補回 append-only 的收緊向更正事件。在那之前不做，符合範圍凍結。

## RESULT（實作完成後由執行端填寫）
- STATIC_CHECK=
- RUNTIME_CHECK=
- MUTATION_CHECK=
- RECEIPTS=
- OPEN_PENDING=
