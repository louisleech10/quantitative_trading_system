# INSTREV Phase A — SPEC/TODO 雙家族 adversarial reconcile(2026-07-05)

> 輸入:`handoffs/20260705-INSTREV-PHASEA-ADV-codex.md`(sha256:24ae8776…,gate 已 register-output)、`handoffs/20260705-INSTREV-PHASEA-ADV-composer.md`(sha256:5bd56a62…,已 register-output)。
> 作者=Claude(SPEC/TODO 作者),不自審;本 reconcile 須 codex+composer 戳記核可後才可派實作(gate 對 `--spec` 派工強制)。
> 兩腿獨立跑(不互看)。收斂點=兩家族獨立點到同一問題,列為高信號優先修。

## A. 收斂點(兩家族獨立命中,最高優先)
- **CONV-1 §B Gate 未覆蓋新制度 token**(CODEX-1 MAJOR + COMPOSER-6/7 MAJOR):A-12 補的 `register-output`/`RECONCILE-STAMP`/`VERIFY` 與 [A-4] 零刪減 14 組 grep 都**不在** TODO §B Gate 整批驗收清單 → 實作者只跑 §B Gate 即可標 DONE,漏補仍拿綠燈。**採納**:把 [A-4] 真實 baseline 檢查 + A-12 token 檢查併入 §B Gate。
- **CONV-2 「現行分工」單一來源 grep 自打/未收斂**(CODEX-2 MAJOR + COMPOSER-8 MAJOR):TODO 範例句與驗證 `grep -c "現行分工"=1` 互撞;ORCH §1 工具表「何時用」欄仍留固定分工結論 → 單一來源未真達成。**採納**:驗證改錨點式 grep;工具表「何時用」欄改 pointer;歷史 A/B 結論移 SCAR_LEDGER。
- **CONV-3 copilot「無依賴」過度宣稱**(CODEX-3 MINOR + COMPOSER-1/9 MAJOR):§A/Task 1.2 說「無 agent 依賴」,實際 `docs/ARCHITECTURE.md:485` 仍以檔名引用該檔。**採納(收窄)**:改「無現役 scripts/gate 依賴;repo 內歷史/低頻文件仍以檔名引用,因 pointer 檔不刪故不破鏈」;Task 1.2 邊界由「BLOCKED」降為「檔名級引用→收尾 SCOPE_CHANGES 註記,不擴 scope 改正文」。

## B. Composer 獨有 BLOCKING(Claude 重驗屬實,必修)
- **ADV-COMPOSER-3 [BLOCKING] 採納**:Task 2.3 零刪減 grep 列了 `繁體`/`VERIFY`/`FACT-RECEIPT`/`先問`/`白話`,但 **Claude 重跑 `grep -c` 現況 CLAUDE.md 皆 0**(繁體/白話=記憶專屬 user pref,U-10 明定留記憶不入 repo;VERIFY/register-output=A-12 才新增到合約,非既存)。→ 驗證會即刻 FAIL 或誘導 token-stuffing。**修法**:[A-4] CLAUDE.md 零刪減改用**真實 baseline 12 token**(實測存在):`data_cache`、`momentum/`(解耦表)、`Validate Assumptions`、`驗證保真度`、`三方數據`、`雙家族`、`adversarial`、`gate_check.sh`、`斷路器`、`否決`、`不跳`(不得跳步類)、`preflight`;合約家 token(A-12 新增)在 Task 4.3 post-add 驗;user-pref(繁中/白話)在 Phase 6 記憶層驗,不列 CLAUDE.md。
- **ADV-COMPOSER-4 [BLOCKING] 採納**:Task 2.2 驗證 `grep -n "Codex(GPT-5.5)實作"`(半形括號)=0,但現檔 L28 是**全形**`Codex（GPT-5.5）實作` → grep 恆 0、驗證無牙,L28 寫死分工可蒙混過關。**修法**:驗證改 `grep -nE "Codex.*實作|Composer.*實作|GPT-5.5.*實作"` 限「任務分派」節=0;「大」列與「中」列執行端欄一致改 pointer(見 CONV-2)。

## C. 其餘 MAJOR/MINOR 裁決
- **ADV-COMPOSER-5 [MAJOR] 採納**:§V [A-4] 寫「CLAUDE.md+合約」但 Task 2.3 只 grep CLAUDE.md。→ 拆「CLAUDE 必留 12 token / 合約必留(反提示注入等既存 + A-12 新增)」兩張表,與 [A-4] 對應(併入 B 的修法)。
- **ADV-COMPOSER-2 [MAJOR] 部分採納**:U-3 納入 Phase A 屬合理(Phase A 標題=合約補齊、U-3 3/3 收斂、簡述已揭露),但 reconcile §E 原文未列。**修法**:①SPEC §A/manifest 加一句「以雙戳記 reconcile 全文 + 本 manifest [A-12] + 使用者 D-1~D-6 為準;§E 分期表為建議非窮舉」;②Claude(編排者)在舊 RECONCILE.md 戳記區**之後**append errata(不動本體雜湊,不破既有戳記),記錄 U-3 歸 Phase A。**不要求 executor 改。**
- **ADV-COMPOSER-7 [MAJOR] 採納**:Task 4.4 只跑現行 sync,新 token 未進 CONTRACT_TOKENS(U-9=Phase B)。**修法**:SPEC §V + Task 4.4 加「U-9 前以 Task 4.3 grep 為準;sync 綠 ≠ 新制度齊;殘量留 Phase B」。
- **ADV-COMPOSER-9 [MAJOR] 見 CONV-3**:另 SPEC §C 允許範圍**不**擴到改 ARCHITECTURE L485 正文(維持 U-11 不強制同步);L485 指向的是「即將變 pointer 的檔」,語意無誤導(該檔本就會變成指路檔)→ Task 1.2 收尾 SCOPE_CHANGES 註記即可。
- **ADV-COMPOSER-11 [MINOR] 採納(小幅擴 scope)**:`docs/MULTI_AGENT_BOOTSTRAP.md:35` 仍 `debug ≤3 輪`——是第 5 個分叉源,正是本 epic 要消滅的。**修法**:納入 Task 3.3 scope(同一行 3→2 改),SPEC §C 允許檔加 BOOTSTRAP.md;§B Gate 的「3 輪」grep 擴涵蓋 BOOTSTRAP.md。
- **ADV-COMPOSER-10 [MINOR] 採納**:§B Gate 關鍵詞 `stdin` 與 SCAR_LEDGER 敘事對齊——Task 1.1 事故條目須含字面 `stdin`(不只 `/dev/null`)。已在 Task 1.1 清單,§B Gate 保留 `stdin` 關鍵詞即可,補註「SCAR_LEDGER stdin 條目須含字面 stdin」。
- **ADV-COMPOSER-12 [MINOR] 採納**:行數 manifest「~130」vs SPEC/TODO「≤140」→ 統一為「**≤140 硬上限,~130 期望**」,驗收以 140 為準;避免執行端為壓 130 誤刪規則句。
- **ADV-COMPOSER-1 / CODEX-3 [MINOR] 採納(收窄措辭)**:§A「機檢依賴面=sync check 一支」→「presence 機檢=sync check;語意/派工閘=gate 族(gate.sh/gate_check/template_check/reconcile_stamps);本批不改腳本」。
- **ADV-COMPOSER Suggestions 採納**:Task 2.1 加負向 `grep -c 關鍵詞 CLAUDE.md` 上限(1970-01-21 等移出詞在 CLAUDE.md 應=0);HANDOFF 索引由 Claude 收尾對齊 manifest。

## D. 無異議通過(兩家族皆未列 Blocking)
- §RISK/§A/§C/§P/§V/§R/§N 錨點齊;§G 合理 N/A(RISK-HIT b,c);無空殼 Task;無 quant/OOM/cache/API 風險(純文件);規則零刪減**機制**修正後(B/CONV-1)即足。

## E. 修補清單(Claude 動手,改 SPEC/TODO/manifest;executor 不需管)
1. SPEC §A:收窄 copilot 依賴 + 機檢措辭 + U-3 errata 引用句 + 執行端現行分工=Composer 實作/Codex review(使用者 07-05 額度切換)。
2. SPEC §C:允許檔加 `docs/MULTI_AGENT_BOOTSTRAP.md`;明列不改 ARCHITECTURE L485 正文。
3. SPEC §V:[A-4] 改真實 baseline 12 token + 拆 CLAUDE/合約兩表 + A-12 token 併入整批驗收 + sync 殘量註記 + 行數 140 硬上限。
4. TODO §B Gate:加 [A-4] 12 token + A-12 三 token + BOOTSTRAP 3輪 grep + 現行分工錨點式。
5. TODO Task 1.2 邊界、Task 2.2 驗證、Task 2.3 token 列、Task 3.1 工具表、Task 3.3 scope、Task 4.4 殘量:逐項照 B/C 修。
6. 舊 RECONCILE.md 戳記後 append U-3 errata(Claude,不破雜湊)。
7. 修補後重跑 template_check + coverage_check;取 codex+composer 對**本 reconcile** 戳記;gate dispatch --spec 派 Composer 實作。

## 戳記
(待 codex/composer append RECONCILE-STAMP;family ∈ {codex, composer};body-hash = 本行「## 戳記」之前全文)

### R1 戳記(REJECTED,已由 SPEC 修補處理,supersede 記錄如下)
- 2026-07-05 R1:codex(task:instrev-phasea-recstamp-codex,harness b4f7rwm48)與 composer(task:instrev-phasea-recstamp-composer,harness bfvbkeomv)**皆 REJECTED**,收斂點=SPEC 未忠實套用 reconcile 的選層對調:`docs/INSTREV_PHASEA_SPEC.md` L22/L62(半形無牙 grep)/L69(Task3.1 仍寫 Codex 實作+Composer review)與 §A L20/TODO 的「Composer 實作+Codex review」矛盾;composer 另指 SPEC Task1.2 邊界仍 BLOCKED 未同 TODO 收窄。
- **處置(Claude,reconcile body 未動、hash 仍 6a14a0f6)**:SPEC L22/L62/L69 選層全改為 Composer 實作+Codex review 並改錨點式 grep;SPEC Task1.2 邊界收窄為 SCOPE_CHANGES,與 TODO 一致。R1 REJECTED 由本節記錄保存(harness log 為獨立佐證),下方 R2 戳記針對修補後版本。

### R2 戳記(針對修補後 SPEC/TODO)
RECONCILE-STAMP: codex APPROVED 2026-07-05 sha256:6a14a0f69f38203e38530f3d0d2489b8f535d21b6f6d72e45e2893b2ce8452c5 task:instrev-phasea-recstamp-codex-r2
RECONCILE-STAMP: composer APPROVED 2026-07-05 sha256:6a14a0f69f38203e38530f3d0d2489b8f535d21b6f6d72e45e2893b2ce8452c5 task:instrev-phasea-recstamp-composer-r2

## Finding 處置對照(codex 腿 ID 補全,戳記後區,不影響 body-hash)
> CODEX 腿 finding 已於 §A CONV-1/2/3 裁決,此處補全 gate 要求的 `ADV-CODEX-n → 處置` 明列。
- ADV-CODEX-1 [MAJOR] → 採納(=CONV-1):A-12 token + [A-4] 真實 baseline 併入 TODO §B Gate 整批驗收(已改)。
- ADV-CODEX-2 [MAJOR] → 採納(=CONV-2):「現行分工」驗證改錨點式 grep;ORCH 工具表「何時用」欄改 pointer 措辭;範例句不含精確四字(已改)。
- ADV-CODEX-3 [MINOR] → 採納收窄(=CONV-3):§A/Task 1.2 copilot 依賴改「無現役 scripts/gate 依賴;檔名級引用因 pointer 檔不刪不破鏈」(已改)。

Verdict：可派工(雙家族 adversarial findings 已全數 reconcile,R2 雙戳記 APPROVED;此行於戳記後區,供 gate quality-check,不影響 body-hash)
- ADV-COMPOSER-2 [MAJOR] → 部分採納(§C):U-3 歸 Phase A,權威=雙戳記 reconcile+manifest[A-12]+D-1~D-6;Claude 補舊 reconcile errata。
- ADV-COMPOSER-7 [MAJOR] → 採納(§C):Task 4.4 加 sync 殘量註記,新 token 以 Task 4.3 grep 為權威,U-9 留 Phase B。
- ADV-COMPOSER-10 [MINOR] → 採納(§C):§B Gate 保留 stdin 關鍵詞,SCAR_LEDGER stdin 條目須含字面 stdin。
