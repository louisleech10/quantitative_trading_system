# GOVB0 SPEC R2 adversarial review

family: codex
task-id: GOVB0-SPEC-R2
scope: docs/GOVB0_FRICTION_SPEC.md only; no code/test changes

### §0 前提挑戰與實跑 receipt

- fact-verified: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS`，rc=0。
- fact-verified: `bash .claude/tmp/b15probe3.sh` → 原型② TP/TN 9/9，rc=0；這只驗原型，不等於 R2 已實作。
- fact-verified: `rg -n '^\*\*Task [0-9]' docs/GOVB0_FRICTION_SPEC.md` → 11 個 Task heading；4 個 Phase heading。
- fact-verified: `scripts/audit_events.json` 現有 `gate_deny` 僅列於 `non_debt_legacy_events`，`committee_family_result` 仍只有既有欄位；R2 將新增契約列為 Task 0.1 工作，不是現況事實。
- assumed（被推翻一部分）: R2 已把 D-1～D-13 全部落成可執行、無新矛盾的契約。以下 findings 證明仍有未定義的狀態與互斥驗收。

### Q1 — R1 Codex findings 逐條重跑

| R1 finding | verdict | 重跑反例與結果 |
|---|---|---|
| `CODEX-R1-P0-01` | CLOSED（僅就原 scope finding） | `rg -n '^### Phase 4|原 Phase 4' docs/GOVB0_FRICTION_SPEC.md` 無 Phase 4；§A/§N 與 backlog 明寫 B-24 機械面移出、紀律面留批。這不代表 B-24 整票完成，見 Q3。 |
| `CODEX-R1-P0-02` | CLOSED（原反例已被納入契約/語料要求） | `bash .claude/tmp/b15probe3.sh` 的原型②對 9 條語料全對；R2 Task 2.0 明列 quote、`-c` recursion、path、未閉合 quote，Task 2.1 要求 mutation。仍有新 lexical 漏項，見 `CODEX-R2-P0-04`。 |
| `CODEX-R1-P0-03` | NOT-CLOSED | R2 已補 attempt id、prompt 同步、stale 檢查、fsync/rename；但 Task 3.2 並發測試只寫「兩者成功產出不得遺失」而未定義兩份 payload 的保存位置，且正常路徑又要求清除 attempt 檔。見 `CODEX-R2-P0-02`。 |
| `CODEX-R1-P0-04` | NOT-CLOSED | R2 仍以格式檢查後 publish 為條件；現行 `completeness_check.sh --single` 只檢 ID、重複 ID、finding body、來源摘要，未檢 EOF/expected manifest。最後一個 finding 完整但檔案截斷的原反例仍可能 publish。見 `CODEX-R2-P0-01`。 |
| `CODEX-R1-P0-05` | NOT-CLOSED | R2 把不變式收窄為 `(rc, kind)`，但 Task 0.1 驗收仍寫「比對輸出兩份 JSON 並 diff 為空」；新增 audit 欄位後完整 JSON 必然不同。事件欄位型別/編碼也未完整釘死。見 `CODEX-R2-P0-03`。 |
| `CODEX-R1-P1-06` | NOT-CLOSED | R2 Task 3.1 驗證仍是「一次真實派工」；沒有每家族樣本數、session 分布或 timeout 選值方法。見 `CODEX-R2-P1-07`。 |
| `CODEX-R1-P0-07` | CLOSED（B-33 已正式登記且明列不併入） | `docs/GOVB0_FRICTION_SPEC.md` §A OPEN-2 明列 B-33、MAJOR、排第 1 批後；backlog B-33 節存在。R2 未宣稱本批修復 locale。 |
| `CODEX-R1-P1-08` | CLOSED（補查門檻已寫入） | §A OPEN-3 現為 Phase 0 後 `≥200` 筆 `gate_deny` 或 `≥30` 日，先到者為準，並規定零命中才可記錄除役。 |
| `CODEX-R1-P1-09` | CLOSED（互斥行為已收斂） | Task 1.1 改為 unknown `brief-kind` 單一路徑 fail-closed；邊界同時寫缺欄與未知值皆拒派，不再保留 audit-only 放行分支。 |

## CODEX-R2-P0-01

**斷言**: Task 3.2 的 publish/format contract 仍不能辨識「最後一個 finding body 完整但檔案被截斷」的產出，故 terminal marker 不是可驗證的完整性 oracle。

**碼證**: R2 Task 3.2 改法 ④只要求 rc=0、flush/fsync、格式檢查後 rename，改法 ⑤把 publish 定義成 terminal marker；驗收 3.2 只寫 attempt 檔存在/清除與 `format-failed`。現行 `scripts/completeness_check.sh:1459-1473` 的 `--single` 只跑 ID、duplicate、body、digest 檢查，沒有 producer EOF、expected count、完整檔案 sha 或 terminal record。`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS`、rc=0，只證模板欄位存在。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae; scripts/completeness_check.sh#12e981972d78; handoffs/20260804-govb0-spec-r1-codex.md#18283d8b33ad

[BLOCKING] 信心度=High；R2 只把「publish 完成」改名為 marker，沒有提供如何證明被 publish 的內容是本 attempt 的完整內容。截斷 mutation 若恰好保留最後一個完整 finding，仍可通過既有格式檢查並被 rename。修法：在 attempt 啟動前建立綁定 attempt id 的 expected manifest/terminal contract；publish 前要求 producer 完成標記、bytes/record count 或 byte-faithful digest 與 manifest 一致；保留 truncated/empty/stale mutation，並對 publish 後的 audit 與檔案狀態做雙向斷言。

## CODEX-R2-P0-02

**斷言**: Task 3.2 的並發要求「兩個成功產出皆不得遺失」與單一 final `<out>`、正常清除 attempt 檔的資料模型不相容，沒有可執行的保存/取勝規則。

**碼證**: R2 Task 3.2 ①要求每次使用 `<out>.<attempt-id>.part`，④通過後 atomic publish，驗收 271 要求正常結束後 attempt 檔清除；驗收 276 又要求同一 `<out>` 的兩次派工「成功產出不得遺失、audit 兩筆皆在」。現行 `scripts/cx_run.sh:262-288` 的事件模型只有一個 `output_path` 與一個 `output_sha256`，沒有第二份 payload/archive 欄位。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae; scripts/cx_run.sh#39cfdddec350

[BLOCKING] 信心度=High；兩次 rename 到同一 final path 至少會使一份內容不可由 final path 取回；兩個 audit hash 只能證明曾有兩筆，不等於成功產出沒有遺失。修法二選一但須在 SPEC/TODO 固定：每 attempt 使用唯一 final artifact 並由 manifest 指定 canonical winner，或將兩份已 publish payload 保留在 immutable attempt archive 並在 final path 建立明確 winner；驗收須逐 byte 比對兩份內容、兩個 audit link 與清理後狀態。stale `<out>` 的「拒絕啟動或標記 stale」也須固定一種 result_state/exit contract，不可留 OR 分支。

## CODEX-R2-P0-03

**斷言**: Task 0.1 的新 audit schema 與「判定不變」驗收仍互相矛盾，且實作者仍無法只依 SPEC 寫出完整的 event object contract。

**碼證**: R2 Task 0.1 §改法 ②要求把 `match_rule` enum/`required_fields` 寫入 `scripts/audit_events.json`，§改法 ④把不變式收窄為 `(rc, kind)`；但同一 Task 的驗證 105 仍要求「逐項比對輸出兩份 JSON 並 diff 為空」，驗證 106 另要求新 audit 欄位存在。實跑 `LC_ALL=C grep -aEn 'gate_deny|committee_family_result|match_rule|required_fields|result_state' scripts/audit_events.json` 顯示 `gate_deny` 目前只是 legacy event，沒有 field schema/enum；`committee_family_result` 目前只有既有七欄。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae; scripts/audit_events.json#91c19ab09e5e

[BLOCKING] 信心度=High；若 JSON 是完整 audit record，新增 command/match_rule 後 diff 不可能為空；若 JSON 只含 decision trace，SPEC 沒有明說它與 audit record 是兩個不同輸出。另缺 exact key/type/encoding contract（sha256 欄、前 512 bytes、控制字元、缺 command 的空值與 1KB 上限如何共同序列化）。修法：分離 immutable decision trace（只含 `(rc,kind)`）與 audit event；在 `audit_events.json` 固定欄位名、型別、空值、escaping/truncation 與 closed enum；測試分別 diff decision trace 與驗證 audit schema，不再以完整 JSON 空 diff 代表判定不變。

## CODEX-R2-P0-04

**斷言**: Task 2.0 的五項 lexical contract 沒有覆蓋它自己要求實作者處理的 unquoted `-c`、遞迴深度上限與 escape/wrapper 語義，仍可能留下 gate fail-open。

**碼證**: Task 2.0 item 2 只定義 `(bash|sh|zsh) -c <引號引數>`；Task 2.1 邊界③卻要求 `bash -c codex`「依契約定義並測試」，契約沒有該輸入的結果。Task 2.0 邊界①要求巢狀 `-c` 有上限且逾限 fail-closed，但沒有數值或超限的具體 oracle；邊界②只說 escaped quote 不得因剝除錯誤而放行，沒有定義 escaped separator、backslash-newline、`eval`/`env`/`command` 外層的處理。`bash .claude/tmp/b15probe3.sh` 的原型② → 9/9，只覆蓋既有 9 條，不能證明上述未列語料。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae; handoffs/20260804-GOVB0-SPEC-R2-BRIEF.md#6a85d350afc

[BLOCKING] 信心度=High；「依契約定義」在契約缺項時把安全邊界交給實作者自行發明；不同 shell/quote parser 可能對同一字串得出不同命中，造成蓄意或偶發放行。修法：先固定有限 lexical grammar（含 unquoted `-c` payload、escape、newline/comment、明確 wrapper allow/deny），給出精確 recursion cap 與 over-cap fail-closed 結果；超出 grammar 一律 fail-closed。每項須進 immutable corpus，並以 TP/TN、over-depth、escaped/unclosed mutation 驗證。

## CODEX-R2-P0-05

**斷言**: R2 對 Phase/Task 數量的自我描述已漂移：SPEC 內有 11 個 Task heading，但 §V 宣稱全部 10 個 Task，且 Task 2.0 沒有自己的 mutation acceptance。

**碼證**: 實跑 `rg -n '^\*\*Task [0-9]' docs/GOVB0_FRICTION_SPEC.md` → Task 0.1、1.1、2.0–2.5、3.1–3.3，共 11 個；`rg -n '^### Phase ' ...` → 4 個 Phase。§V:307 寫「全部 10 個 Task 皆宣稱…mutation」，但 Task 2.0:152-154 只有 10 條 TP/TN 與邊界，沒有 mutation bullet。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae; handoffs/20260804-GOVB0-SPEC-R2-BRIEF.md#6a85d350afc

[BLOCKING] 信心度=High；TODO 生成器若依 brief 的「4 Phase／10 Task」計數，可能漏掉新加入的 Task 2.0；若依 §V 交付 mutation，Task 2.0 又沒有對應 mutation。修法：建立唯一 Task manifest，明確決定 Task 2.0 是正式 Task 還是 Phase 2 contract substep；同步修正 brief/SPEC/§V/依賴圖/驗收計數，若保留 Task 2.0 則補其 mutation（刪除/繞過 shared contract 後應轉紅）。

## CODEX-R2-P0-06

**斷言**: B-34 是第 0 批目前 review/convergence path 的結構性 roster mismatch；以權宜第三方戳記通過機檢，不能視為語意閉合。

**碼證**: 實跑 `bash scripts/_role_gate.sh check-families handoffs/20260804-GOVB0-SPEC-R2-BRIEF.md codex,composer,grok` → rc=2，輸出 `grok 是現行 implementer,不得擔任 code review`。`scripts/governance_roles.json` 的 implementer 是 grok、reviewers 是 codex/composer；`scripts/reconcile_stamps_check.sh:33-39` 預設 required roster 取 `review_families`，而 `scripts/governance_families.json` 的 review_families 含三家。backlog B-34:1176-1218 也記錄同一結構。

**來源摘要**: scripts/governance_roles.json#73103784a286; scripts/reconcile_stamps_check.sh#c524f06ca1c6; handoffs/20260801-GOV-AMEND-BACKLOG.md#9600c0cdc556

[BLOCKING] 信心度=High；正確的 SPEC review 派 codex+composer 時，review role gate 拒絕 grok，但 stamp checker 仍要求 grok；現行通路只能補派 grok 以「stamp」名義確認未參與的 findings，空戳記破壞簽核語意。嚴重度：P0/阻塞 review convergence。建議納入第 0 批的最小修法是讓 stamps checker 從該 round 的 `committee_round_open.participants`/expected outputs 取實際 roster，並保留 provenance、hash、task 綁定；若要第三方複核，另用明確 `spec-review` kind，不借用「自己的 findings」語意。主委以 B-33 scope 避免膨脹的理由不適用：B-34 正在阻擋本輪正確收斂。

## CODEX-R2-P1-07

**斷言**: Task 3.1 的「一次真實派工」不足以產出可負責任的 per-family timeout manifest，Task 3.3 的值定稿條件仍不可執行。

**碼證**: Task 3.1:249-253 只要求一次真實派工後有起訖與時長；Task 3.3:292/298 要求 TODO timeout 與 duration manifest 一致，但沒有樣本數、每家族最低數、session 分布、異常/重試納入規則或選值公式。R2 §A 仍把 50m/70m/75m 標為暫定，且已承認既有 birth→mtime 是 proxy。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae; handoffs/20260804-govb0-spec-r1-codex.md#18283d8b33ad

[MAJOR] 信心度=High；一次觀測可能是短 prompt、cache hit 或未代表性的正常路徑，不能支撐 3 家族尾端 timeout。可執行的最低門檻建議寫入 TODO：每家族至少 50 筆真正 instrumented CLI duration，分布於至少 3 個獨立 session/UTC 日期；每筆皆有 monotonic start/end、CLI rc、result_state、attempt id，缺欄不得納入；另固定 timeout 選值公式、grace/outer safety 關係與 manifest sha。50 是本 review 的保守執行門檻建議，不是現況事實；未達門檻不得把暫定值寫入 TODO。

## CODEX-R2-P1-08

**斷言**: Task 3.2 的 publish critical section 與 Task 3.3 的 timeout/kill interval 沒有順序契約，CLI return 與 publish 之間的競態可產生錯誤 `failed` 或重複 `result_state`。

**碼證**: Task 3.2:267 要求「CLI 返回 rc=0 後」才 flush/fsync、格式檢查、rename；Task 3.3:289 把 timeout 區間定為 CLI launch→return/kill，291 又要求「逾時後已 publish」依格式結果、未 publish 才 `failed`。沒有說 timeout watcher 在 CLI return 後何時停止、publish 是否在 timer/kill 的同一 process group、或哪個事件對 race 取優先。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae; scripts/cx_run.sh#39cfdddec350; scripts/committee_run.sh#4c6bdeff1a15

[MAJOR] 信心度=High；若 timeout 在 rc=0 後、publish 前觸發，3.2 的 publish 前提與 3.3 的未 publish→failed 同時成立；若 kill 連 publish worker，則又可能留下已完成 attempt 而沒有 terminal audit。修法：明定 timer stop 的線性化點、publish 的不可中斷/可恢復 critical section、SIGTERM/SIGKILL 後 state precedence，以及 outer safety valve 不得追加第二筆 family result；加一個 return-at-deadline、publish-at-deadline、kill-during-fsync 的整合 mutation。

## CODEX-R2-P1-09

**斷言**: §V 對 B-24 的「每個 Task 驗證皆為狀態斷言、而非腳本 rc」宣稱不實；仍有直接 rc acceptance，且部分沒有對應的後狀態斷言。

**碼證**: `rg -n 'ASSERT|rc[!=]=|rc≠' docs/GOVB0_FRICTION_SPEC.md` 列出 Task 0.1:103-104 的 blocked/allowed rc、Task 1.1:127-129 的 consult/stamp/unknown rc、Task 2.5:232/235 的 rc fail 條件、Task 3.3:294 的 hang rc。§V:309-311 卻宣稱驗收不是某腳本 rc=0。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=High；有些 rc 是與狀態斷言並列的必要 process guard，但它們仍違反「一律狀態」的字面契約；尤其 Task 1.1 unknown 只有 rc≠0，沒有明確 no-token/no-audit/no-open-debt 狀態。修法：把 rc 降為輔助護欄，所有 normative acceptance 改成執行後狀態；至少補 unknown 無 token、audit 零新增、debt 未開，並把 §V 文案改成「不可只看 rc」。

## CODEX-R2-P1-10

**斷言**: Phase 0 的不變性與 Phase 2 的預期改判定沒有分開 baseline；同一份「改前」語料快照可使兩個驗收互斥。

**碼證**: Task 0.1:100-105 要求同一批輸入改前/改後 `(rc,kind)` 逐項相等並把兩份 JSON diff 為空；Task 2.5:227 又要求舊版 snapshot 是 Phase 2 動工前的 `gate_check.sh`。Phase 2 明文要求 Task 2.1-2.4 的多條由 ALLOW↔BLOCK 改變。SPEC 沒有命名 Phase 0 前、Phase 0 後/Phase 2 前、Phase 2 後三個 snapshot。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=High；若 Task 0.1 使用 Phase 2 前 snapshot，會把預期改變判成失敗；若使用 Phase 2 後 snapshot，會掩蓋 Phase 0 觀測改動是否改變判定。修法固定三個狀態：S0→S1 只驗 Phase 0 `(rc,kind)` 相等；S1→S2 由 Task 2.5 報告預期差集；每個 snapshot 綁 commit/file sha 與 corpus sha，並在 dependency graph/驗收中明寫。

### Q2 — 新矛盾/漏洞裁定

以上 `CODEX-R2-P0-01`～`P0-05` 直接回答 Task 2.0 與 2.1–2.5 的詞法/語料矛盾、Task 0.1 invariant 與 Task 2.x 預期改判定的互斥，以及 Task 3.2/3.3 的 timeout-publish race。結論是：有新矛盾，不能只信任「D-1～D-13 全數落實」宣稱。

### Q3 — D-6 SPLIT

SPLIT 作為「部分完成」的排程裁決可接受；backlog 已明寫 B-24 狀態為部分完成，沒有把紀律欄冒充機械 enforcement。但它不滿足「工具必須自帶強制機制」的最終目標，也不能在 TODO/收尾中寫成 B-24 完成。生成 TODO 前須保留一個可追蹤的獨立 mechanical lane，具名 owner、UTC 到期日、到期後 fail-closed 行為與新/改文件來源；否則該 split 會退化成 R1 原點。因本輪另有 P0 blockers，這項條件列入 blocking list；不建議把 acceptance checker 偷塞回本批以擴大 Phase 2 scope。

### Q4 — Task 3.3 timeout 值定稿條件

R2 目前不可執行，因 Task 3.1 只要求一次真實派工。可執行門檻採 `每家族 ≥50 筆 instrumented CLI duration + 至少 3 個獨立 session/UTC 日期 + 每筆 start/end/rc/result_state/attempt id 完整`；所有缺欄、proxy 或未能區分 CLI 與 wrapper 時間的樣本排除並記錄。TODO 另須固定 deterministic timeout selection/grace 公式，最後以 duration manifest sha 與 TODO 值相等驗收。這是建議門檻，不是已驗證數據。

### Q5 — §V 的 B-24 紀律面

未完全落實。仍是直接 rc 斷言者：Task 0.1:103-104、Task 1.1:127-129、Task 2.5:232/235、Task 3.3:294。Task 0.1、2.5、3.3 多數另有狀態斷言，因此不是每一條都「只看 rc」；但 §V:310 的絕對描述仍不成立，Task 1.1 unknown 明顯缺 no-side-effect state。應修正為「rc 只能作輔助，狀態是 normative acceptance」，並補齊後狀態。

### Q6 — B-34 `GOV-STAMP-ROSTER-VS-ROLEGATE`

嚴重度：P0/Blocking。這是結構性 review convergence dead-end，不是一次操作失誤；實跑 role gate 已以 rc=2 證明三家 review roster 被拒，checker 的 default roster 又是三家。最小修法選方向①：從 audit 綁定的該輪實際 participants/expected outputs 取 required stamp roster；`review_families` 僅作合法家族 universe，不作每輪必簽全集。若日後需要第三方複核，新增明確語意的 review kind。應納入第 0 批，因它正阻擋本輪正確收斂；B-33 的「避免 scope 膨脹」理由不足以排除這個同輪結構缺陷。

### Q7 — 是否可進 TODO 生成

不可。BLOCKING 清單：

1. `CODEX-R2-P0-01`：補 attempt-bound complete-content/terminal oracle 與 truncated mutation。
2. `CODEX-R2-P0-02`：定義並發兩份成功 payload 的 durable 保存、canonical winner、audit link。
3. `CODEX-R2-P0-03`：分離 decision trace 與 audit record，固化 `audit_events.json` schema/encoding，移除完整 JSON 空 diff 矛盾。
4. `CODEX-R2-P0-04`：補 unquoted `-c`、escape、wrapper、recursion cap 的有限 lexical contract 與 fail-closed corpus。
5. `CODEX-R2-P0-05`：修正 11 Task/10 Task 漂移，補 Task 2.0 mutation 或明確改為 substep。
6. `CODEX-R2-P0-06`：修 B-34 roster source，讓實際參與者與必要戳記一致。
7. `CODEX-R2-P1-07`：補每家族真實 duration 樣本門檻與 deterministic timeout selection。
8. `CODEX-R2-P1-08`：固定 timeout 與 publish 的線性化順序、kill race、outer safety valve。
9. `CODEX-R2-P1-09`：修 §V B-24 wording/acceptance，使 rc 僅為輔助並補 post-state。
10. `CODEX-R2-P1-10`：固定 S0/S1/S2 baseline，避免 Phase 0 invariant 與 Phase 2 delta 共用歧義 snapshot。
11. 保留 B-24 mechanical lane 為具名、可到期、到期 fail-closed 的獨立 backlog work；目前只能標「部分完成」。

## Verdict

需修補後派工。R1 原有 P0-01、P0-02、P0-07、P1-08、P1-09 已由 R2 文本實質閉合；其餘原 P0/P1 加上本輪新發現仍足以阻塞 TODO。B-34 應併入第 0 批的最小 roster 修法；B-24 SPLIT 可保留，但不得宣稱機械面已完成。

STATUS: DONE
