# Reconcile — 20260805-govb0-spec-r2

**來源** 20260805-govb0-spec-r2-codex.md, 20260805-govb0-spec-r2-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併 — 17 條全部歸戶，**無未分群 ID**。
**R1 findings 已全數 CLOSED**（composer 逐條重跑確認）；本輪 17 條全為**對 R2 新文本**的新發現。

🔴 **收斂趨勢警訊（主委自陳）**：R1 = 19 條（5 P0）→ R2 = 17 條（7 P0）。**P0 未下降。**
此為 `docs/SCAR_LEDGER.md` 與 memory `epic 收斂斷路器` 記載的 P16 失敗模式重現：
**每輪修訂都新增機制，審查者在新機制上再找到缺口（scope accretion），八輪卡在 20-25 findings。**
⇒ 依使用者定死「**沒 100% 解就做 95% 那版現在收，殘留具名記錄不當阻塞**」與
「**brief 須宣告不受理範圍否則審查沒終點**」，本輪起**明確劃定不受理範圍**（見下 E-SCOPE）。

**收斂基數**：17 條（codex 10／composer 7）。

| 群 | 主張 | 對應 finding | 處置 |
|---|---|---|---|
| E-1 | **SPEC 對自身的描述不實**：11 個 Task heading vs §V 宣稱 10 個 | `CODEX-R2-P0-05` | **ACCEPT-BLOCKING**（客觀錯誤） |
| E-2 | **§V 的「每條驗證皆狀態斷言、非 rc」不實**：具名 `Task 0.1:103-104`／`1.1:127-129`／`2.5:232,235`／`3.3:294` | `CODEX-R2-P1-09`／`COMPOSER-R2-P2-01` | **ACCEPT-BLOCKING**（客觀錯誤） |
| E-3 | **詞法契約缺 `eval`／`$()`／反引號／子 shell**，且這些在**現行 gate 就已 fail-open** | `COMPOSER-R2-P0-01`／`CODEX-R2-P0-04` | **ACCEPT-BLOCKING** — 已有驗證解法 |
| E-4 | 詞法契約缺 unquoted `-c`／遞迴深度上限／escape 語義／heredoc | `CODEX-R2-P0-04`／`COMPOSER-R2-P1-02` | **ACCEPT** — 併入 E-3 契約 |
| E-5 | **terminal marker 仍非完整性 oracle**：截斷但格式完整者仍可 publish | `CODEX-R2-P0-01` | **PARTIAL — 劃入 E-SCOPE 不受理** |
| E-6 | 並發「兩個成功產出皆不得遺失」與單一 final `<out>` 資料模型不相容 | `CODEX-R2-P0-02` | **ACCEPT（改設計）** — 改為序列化 |
| E-7 | Task 0.1 schema 與「判定不變」仍互相矛盾；event object contract 不足以實作 | `CODEX-R2-P0-03` | **ACCEPT** — 分離兩個 baseline |
| E-8 | Phase 0 不變性與 Phase 2 預期改判定共用同一 baseline 會互斥 | `CODEX-R2-P1-10` | **ACCEPT** — 與 E-7 同解 |
| E-9 | publish 與 timeout/kill 無順序契約，CLI return 與 publish 間有競態 | `CODEX-R2-P1-08` | **ACCEPT** — 明文順序契約 |
| E-10 | Task 3.1「一次真實派工」不足以定稿 timeout；缺樣本門檻 | `CODEX-R2-P1-07`／`COMPOSER-R2-P1-04` | **ACCEPT** — 採 composer Q4 門檻 |
| E-11 | `票 B-34` 以權宜第三方戳記通過機檢，**非語意閉合** | `CODEX-R2-P0-06`／`COMPOSER-R2-P1-03` | **ACCEPT（明文化）** — 已開票，本批不解 |
| E-12 | `B-24` 僅交付紀律面，TODO 未強制標「部分完成」 | `COMPOSER-R2-P2-02` | **ACCEPT** — TODO §0 強制標註 |
| E-13 | **原型與契約有落差**：R2 要求契約第 3–5 項有測試，但主委原型②未實作多數項；實作者照抄原型會與 Task 2.0 驗收衝突 | `COMPOSER-R2-P1-01` | **ACCEPT** — Task 2.0 明文「禁止照抄原型即宣稱完成」，並逐項標示原型③已涵蓋／未涵蓋 |

🔴 **E-13 是主委在第一版群集表**漏掉**的（`COMPOSER-R2-P1-01` 未列入任何 E 群）**，由 codex 與 composer
在戳記輪**各自獨立**指出而拒章（`MISMATCH_1`）。
⚠️ **這暴露 `completeness_check` 的一個盲點**：它驗「ID 是否出現在綜合檔」，附錄逐字保留使該 ID 必然存在
⇒ **「ID 在檔案裡」rc=0，但「ID 進了群集表」沒有任何機器檢查**。
本次是**委員抓到檢查器抓不到的東西**。已記為候選新票（見 `E-SCOPE` 下方「本輪新發現的檢查器盲點」）。

**E-3 主委獨立驗證與解法（不採信執行端報告）**

`handoffs/govb0_probes/b15probe4.sh` 實跑，**證實比 composer 所述更嚴重**——四個向量在**現行 gate 亦 fail-open**：

| 向量 | 現行 gate | R2 原型② |
|---|---|---|
| `eval "codex exec x"` | **ALLOW** | ALLOW |
| `out=$(codex exec x)` | **ALLOW** | ALLOW |
| `` out=`codex exec x` `` | **ALLOW** | ALLOW |
| `(codex exec x)` | **ALLOW** | ALLOW |
| `v=$(claude -p "hi")` | BLOCK（子字串偶然命中） | **ALLOW ← R2 收窄造成的回歸** |

**解法＝原型③**（`handoffs/govb0_probes/b15probe5.sh`）：把「命令位置」擴大為**所有 shell 命令起始語境**
（行首／`;`／`&`／`|`／`(`／`` ` ``／`$(`／`&&`／`||`／`eval` 後／`xargs` 後），
並對 `(bash|sh|zsh) -c` **與 `eval`** 的引號引數遞迴。
**實跑 26/26 全對**：16 條真派工全 BLOCK（含上表五條與 `bash -c`、管線後、`&&`／`||` 後、`xargs` 後、絕對路徑 `claude`）、
10 條唯讀全 ALLOW（含 `pgrep` 引號、commit 訊息、`.claude` ＋ `--porcelain`、`find -print`、檔名子字串、目錄名 `grok`）。
⇒ **R3 的 Task 2.0／2.1 直接採原型③**，並把 26 條語料作為 Task 2.5 immutable corpus 的初始集合。

**E-6 改設計（回應 `CODEX-R2-P0-02`）**

R2 要求「並發時兩個成功產出皆不得遺失」，但資料模型只有單一 final `<out>` ⇒ 無可執行的取勝規則。
**改為序列化**：同一 `<out>` 同時只允許一個 attempt（以檔案鎖或 attempt registry 實現），
第二個 attempt **直接拒絕啟動**並記 audit，**不進入並發保存問題**。
理由：委員派工本來就不應對同一產出路徑並發；拒絕比仲裁簡單且不丟資料。

**E-7／E-8 解法（兩個 baseline 分離）**

- **Phase 0 baseline**＝「Phase 0 改動前後」的 `(rc, kind)` 序列比對，**語料 A**（現行語料，判定應完全相同）。
- **Phase 2 baseline**＝「Phase 2 改動前後」的判定差集，**語料 B**（immutable corpus，判定**應該**改變）。
- 兩者**使用不同的 snapshot 與不同的語料檔**，互不重疊 ⇒ 不互斥。R2 未區分，R3 明文分離。
- event object contract：`gate_deny` 的 `required_fields_per_event` 與 `match_rule` enum **完整寫入 `scripts/audit_events.json`**，
  R3 明列該檔須新增哪些 key（但**不在 SPEC 散文中列舉值**，符合範本規定）。

**E-10 定稿門檻（🔴 主委首版弱化了 codex 主張，經戳記輪 `MISMATCH_2` 指出後改採較嚴者）**

兩家原始主張：composer Q4 ＝每家族 ≥20 筆、<10 筆時可用暫定值；
`CODEX-R2-P1-07` ＝每家族 **≥50 筆**、**≥3 個不同 session／UTC 日期**、**未達門檻不得用暫定值**。
主委首版只寫 composer 的 ≥20／<10 ⇒ **實質弱化 codex 主張**，且未標示分歧。**已改為：**

①**定稿門檻（採 codex 較嚴者）**：每家族累積 **≥50 筆** `result_state=success` 且含 duration 三欄，
  **且跨 ≥3 個不同 session／UTC 日期**（避免單日單批的取樣偏差）；composer 的 ≥20 僅作**中途 sanity check**。
②取各家族 `max(duration)` 與 `P99(duration)`（**單調時鐘欄位，非 runlog proxy**）。
③`timeout_family = ceil(max(max, P99 × 1.25))`；外層 `= max(family_timeouts) + 15m`。
④**未達定稿門檻時的處置（主委裁決，兩家主張不同，此處明示取捨）**：
  timeout **機制照常上線並以暫定值運作**，但 Task 3.3 **不得宣稱完工**，值須逐行標 `PROVISIONAL`，
  且 `票 B-14` 保持「未定稿」狀態直到門檻達成。
  🔴 **與 codex「未達門檻不得用暫定值」的差異與理由**：若嚴格照 codex，未達 50 筆前 timeout 不能上線，
  但**無 timeout 正是 `B-14` 事故的成因**（空等 2h20m）。「有暫定 timeout」嚴格優於「無 timeout」，
  故取「上線但不宣稱完工」。**若委員不同意此取捨，請於本輪拒章並寫明。**
⑤歷史 runlog proxy（n=462）僅作 sanity check，**不可替代** Task 3.1 欄位。

**E-SCOPE — 本批明確不受理範圍（依使用者定死「95% 解法就收」；R3 brief 須逐字宣告）**

| 不受理項 | 來源 finding | 理由 | 殘留處置 |
|---|---|---|---|
| **產出完整性 oracle**（expected manifest／record count／byte-faithful digest 以偵測截斷） | `CODEX-R2-P0-01` | 需要委員端配合產生 manifest，**跨越本批的元件邊界**；且 `B-14` 的原始病是「不退出」，attempt-scoped publish 已解 stale/覆蓋/未完成三種，截斷是第四種且未曾實際致害 | **開新票**，`B-14` 票面標「截斷偵測未解」 |
| **`B-34` 語意閉合**（roster vs 角色閘） | `CODEX-R2-P0-06`／`COMPOSER-R2-P1-03` | 觸及角色語意與 kind 分類，**須獨立管線** | 已開 `票 B-34`，本批只用權宜作法並明文標註 |
| **`B-24` 機械強制面** | `COMPOSER-R2-P2-02` | 已於 R1 `D-6` 裁 SPLIT | 已記於 backlog 拆分節；TODO §0 強制標「B-24 部分完成」 |
| **`B-15` FP-2 定位** | R1 `OPEN-3` | 需 Phase 0 紀錄累積 | 已定補查條件（≥200 筆或 ≥30 日） |

🔴 **R3 brief 須逐字宣告**：上述四項**不受理**，委員若再提同一議題，請標為 `OUT-OF-SCOPE` 並附「若不做會怎樣」的
具體失效場景即可，**不作為 BLOCKING**。
🔴 **若委員認為某項不受理會導致本批交付物本身失效**（而非只是不夠完美），**該條仍可 BLOCKING**，但須寫明失效路徑。

**E-SCOPE 的委員表態（第一次戳記輪，三家皆已回覆）**：
codex 逐項確認四項**皆不使本批交付物本身失效**（`E-SCOPE_1`～`E-SCOPE_4`）；
composer 與 grok 未就 `E-SCOPE` 提出反對。⇒ **不受理範圍已獲委員接受**，非主委單方宣告。

**本輪新發現的檢查器盲點（候選新票，待 R3 輪裁定嚴重度）**

`scripts/completeness_check.sh --lock` 只驗「來源 finding ID 是否出現在綜合檔」。
由於綜合檔的**附錄逐字保留全部來源 findings**，任一 ID **必然存在** ⇒
**「該 ID 有沒有被寫進群集／處置表」完全沒有機器檢查**。
本輪實證：`COMPOSER-R2-P1-01` 未進群集表，`completeness --lock` 仍 **rc=0**；
由 codex 與 composer 在戳記輪各自獨立指出才被發現。
⇒ 收斂工具的「零掉項」保證，**只涵蓋檔案層，不涵蓋判斷層**。
候選修法：`completeness_check` 增加「群集段須逐一引用每個來源 ID」的檢查（群集段＝`## 戳記` 之前、附錄之前的區段）。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R2-P0-01

**斷言**: Task 2.0 詞法契約 5 項未涵蓋 `eval`／命令替換／反引號／子 shell，且這些向量在參考原型②上 **全部 fail-open**。

**碼證**: 隔離探針 `/tmp/govb0-r2-composer/lexical_gap_probe.sh` → `eval "codex exec x"`、`$(codex exec x)`、`` `codex exec x` ``、`(codex exec x)` 皆 `ALLOW want=BLOCK`；契約 5 項未列上述機制。SPEC Task 2.0 `:146-151` 僅列引號／`-c`／路徑／未閉合引號。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[BLOCKING] 信心度=High。攻擊路徑：`eval "codex exec …"` 繞過引號感知與 `-c` 遞迴。修法：契約增「命令替換／eval／子 shell 內容遞迴判定」或對未知包裝 **fail-closed**；每項至少 1 TP 進 corpus。

---

## COMPOSER-R2-P1-01

**斷言**: R2 要求契約第 3–5 項（引號路徑、路徑正規化、未閉合引號）有測試，但主委原型② **未實作多數項**，實作者若照抄原型會與 Task 2.0 驗收衝突。

**碼證**: 同一探針 → `bash scripts/../scripts/cx_run.sh`、`"./my dir/codex" exec`、`bash -c "codex exec x'`（未閉合）、`bash -c codex exec x`、巢狀 `bash -c` 皆 `ALLOW`（契約要求 BLOCK 或 fail-closed）。b15probe3 僅 9 條，未覆蓋上述。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=High。修法：Task 2.0 驗證列出具名語料（與 Task 2.3／2.4 列舉對齊）；Task 2.1 改法不得寫「參考原型②」而不列缺口。

---

## COMPOSER-R2-P1-02

**斷言**: 詞法契約未處理 heredoc／分號在引號外組合，原型②對 `cat <<EOF; codex exec x` **誤擋（假陽性）**。

**碼證**: 探針 → `heredoc 假陽性` = `BLOCK want=ALLOW`；契約與 Task 2.4 邊界③「腳本名在字串引數中→ALLOW」未覆蓋 heredoc 形態。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=Medium。修法：契約增 heredoc 或「僅引號內家族名不判定」的 TN；納入 corpus 防回歸。

---

## COMPOSER-R2-P1-03

**斷言**: `票 B-34` 結構衝突未在 R2 處理——`brief-kind:review` 禁止 grok 參與，但 `reconcile_stamps_check.sh` 仍要求三家蓋章，非參與者戳記語意為空。

**碼證**: `bash scripts/_role_gate.sh check-families … codex,composer,grok` → rc=2；`governance_roles.json` implementer=grok；`reconcile_stamps_check.sh:33-38` 預設 `review_families`。權宜 `brief-kind:stamp` 補派可過機檢但不治本。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#fa6a9a90835c

[MAJOR] 信心度=High。修法見 Q6①；本批不併入，TODO §0 須登記。

---

## COMPOSER-R2-P1-04

**斷言**: Task 3.1 未規定「多少真實派工才足以定稿 Task 3.3 timeout」，使「與 duration manifest 一致」在 TODO 生成時 **不可執行**。

**碼證**: Task 3.1 驗證僅「一次真實派工」自洽（`:250`）；Task 3.3 要求 TODO 值與 manifest 一致（`:298`）但未給 manifest 最小 n。§A 暫定值標 proxy 非 wall-clock（`:49`）。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=High。修法：採 Q4 五條寫入 Task 3.1／TODO §0。

---

## COMPOSER-R2-P2-01

**斷言**: §V `:310` 宣稱「每 Task 驗證皆非腳本 rc」**過度**——Task 0.1／1.1／3.3 仍用 `ASSERT … rc` 作 harness outcome（雖並列狀態斷言）。

**碼證**: grep SPEC → Task 0.1 `:103-104`、Task 1.1 `:127-129`、Task 3.3 `:294` 含 `rc` token；§V `:316` 對 golden restore 的狀態要求正確。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MINOR] 信心度=High。修法：§V 改為「補救腳本不得以 rc 代替狀態；harness outcome 的 rc 須與狀態斷言並列」。

---

## COMPOSER-R2-P2-02

**斷言**: D-6 SPLIT 後 B-24 僅交付紀律面，**機械強制仍缺**——與使用者「工具必須自帶強制」有已知差距；R2 未在 TODO 生成條件中強制標「B-24 部分完成」。

**碼證**: §V `:309-311` 紀律面；Phase 4／`acceptance_state_check.sh` 已移出（`:10-13`、`§N :334`）；backlog `票 B-24` 狀態仍 ⬜ 全票面。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#fa6a9a90835c

[MINOR] 信心度=High（SPLIT 已裁）。TODO §0 須寫明部分完成，避免假綠。

---

ASSUMPTIONS_VERIFIED: R2 template_check rc=0；b15probe3 proto2 9/9；role_gate grok+review rc=2；lexical_gap 12 條探針；SPEC sha256=cbd44a5a71ae942d72705e418c03b6216777f1b940eb44999ff0c2da2ee6a170
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` PASS；`bash .claude/tmp/b15probe3.sh` PASS；`bash /tmp/govb0-r2-composer/lexical_gap_probe.sh` 12 cases；`bash scripts/_role_gate.sh check-families …` rc=2
FAILURES_SEEN: none（探針預期失敗為證據）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE

## 戳記

