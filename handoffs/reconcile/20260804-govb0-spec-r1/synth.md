# Reconcile — 20260804-govb0-spec-r1

**來源** 20260804-govb0-spec-r1-codex.md, 20260804-govb0-spec-r1-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併 — 兩家皆判「需修補後派工，不可進 TODO」。19 條全部歸戶，**無未分群 ID**。
5 項 ACCEPT-BLOCKING（須改 SPEC 才可進 TODO）、3 項 ACCEPT（收窄／補欄）、1 項 SPLIT（Phase 4 拆出本批）、
1 項 PARTIAL（timeout 值暫定，待 Task 3.1 實測定稿）、其餘 NOTED。

**收斂基數**：19 條（codex 9／composer 10）。

| 群 | 主張 | 對應 finding | 處置 |
|---|---|---|---|
| D-1 | **Phase 2 四項疊加後 `bash -c "codex exec x"` 仍 fail-open**；與 Task 2.1 邊界③ 自相矛盾 | `CODEX-R1-P0-02`／`COMPOSER-R1-P0-01`／`COMPOSER-R1-P1-05` | **ACCEPT-BLOCKING** |
| D-2 | **Task 3.2 `.part` 與 `cx_run.sh:512` prompt 路徑未對齊**；且「`<out>` 存在」不是可靠 terminal marker | `CODEX-R1-P0-03`／`COMPOSER-R1-P0-02` | **ACCEPT-BLOCKING** |
| D-3 | **Phase 0「行為逐位元組不變」與新增 audit 欄位互相矛盾**；`match_rule` 無封閉 enum／事件契約 | `CODEX-R1-P0-05` | **ACCEPT-BLOCKING** |
| D-4 | **§V 核心驗收不可證偽**：`--single` 接受截斷檔；Task 2.5 exact-delta 無 immutable corpus／baseline | `CODEX-R1-P0-04`／`COMPOSER-R1-P1-01` | **ACCEPT-BLOCKING** |
| D-5 | **Phase 1 unknown `brief-kind` 邊界自相矛盾**（fail-closed vs 視同不需戳記＋警示） | `CODEX-R1-P1-09` | **ACCEPT-BLOCKING** |
| D-6 | **Phase 4（`B-24` checker）應獨立 pipeline**；現行 rollout scope 不足 | `CODEX-R1-P0-01` vs `COMPOSER-R1-P1-02`／`COMPOSER-R1-P1-04` | **SPLIT — 見下裁決** |
| D-7 | `OPEN-1` timeout 區間＝CLI process-group launch→return/kill；值須以 Task 3.1 真實 duration 定稿 | `CODEX-R1-P1-06`（timeout 主張部分）／composer Q1 | **PARTIAL — 暫定值見下** |
| D-8 | `OPEN-2` locale fail-open **必須開票登記**，本批不併入 | `CODEX-R1-P0-07`／`COMPOSER-R1-P1-03` | **ACCEPT** — 開 `票 B-33` |
| D-9 | `OPEN-3` FP-2 以「Phase 0 後補查」結案、**不除役**；但須定樣本門檻／期限／除役條件 | `CODEX-R1-P1-08`／`COMPOSER-R1-P2-03` | **ACCEPT** — 補條件 |
| D-10 | Task 4.1 grandfather 須具名 owner／UTC 到期日／到期後狀態 | `CODEX-R1-P0-01`（部分）／`COMPOSER-R1-P1-04` | **ACCEPT** — 隨 D-6 移出 |
| D-11 | Task 1.1 驗證測的是 harness 字串，不是委員行為 ⇒ 不可證偽委員仍寫標題 | `COMPOSER-R1-P2-02` | **ACCEPT（收窄）** — 明載本 Task 只保證 harness 端 |
| D-12 | Task 0.1 `grep -Eo` 若誤入判定前主路徑會改 rc；現行「先判後記」安全 | `COMPOSER-R1-P2-01` | **ACCEPT（明文化）** — 寫入 Task 0.1 不可做 |
| D-13 | 未宣告 forward dependency：registry enum／舊版 gate snapshot／immutable corpus／`.part` prompt identity／Phase 4 rollout manifest；Phase 1→3.2、3.1→3.3、OPEN-1→3.3 | `CODEX-R1-P1-06`／composer Q6 | **ACCEPT** — §P 補宣告 |

**D-1 主委獨立驗證（不採信執行端報告）**

`.claude/tmp/b15probe3.sh` 兩原型對同一 9 條語料實跑：

| 原型 | `bash -c "codex exec x"` | `sh -c 'grok -m … -p x'` | 其餘 7 條 |
|---|---|---|---|
| ①單純剝引號（SPEC 原設計） | **ALLOW ← fail-open** | **ALLOW ← fail-open** | 全對 |
| ②剝引號 ＋ 對 `(bash\|sh\|zsh) -c` 引數遞迴 | BLOCK | BLOCK | 全對 |

⇒ **兩家獨立提出、主委實測確認**。修法採原型②，寫入 Task 2.1。

**D-6 裁決（兩家分歧，主委裁）**

codex：Phase 4 須**獨立 pipeline**（跨文件 enforcement，rollout scope 不足）。
composer：現行限縮（只檢新寫＋本批修改＋具名 grandfather）**足以交付**。
**裁：SPLIT。** 依據＝使用者定死「95% 解法就收」＋膨脹升級 5 訊號（本 SPEC 已達 5 票／11 Task，Phase 4 又新增 checker＋grandfather SoT＋owner 制度）。
- `B-24` 的**紀律面**（驗收欄一律寫狀態斷言）**留在本批**：本 SPEC §V 與本批 TODO 逐條照做，**零新增元件**。
- `B-24` 的**機械強制面**（`acceptance_state_check.sh`＋grandfather SoT＋owner／到期制度）**移出本批**，於 backlog 內獨立排期。
- ⇒ 本 SPEC 刪 Phase 4，改為 5 票中 `B-24` 只交付紀律面；`票 B-24` 狀態改「部分完成，機械強制待獨立批次」。
- 兩家共識點（grandfather 須具名 owner／UTC 到期／到期後狀態）**隨 D-10 一併移到該獨立批次的票面**，不遺失。

**D-7 暫定值（兩家不完全一致，取保守聯集）**

區間＝**CLI process-group launch → return/kill**（兩家一致；否決 codex R1 的 output-mtime proxy）。

| 家族 | composer 建議 | codex 建議 | **暫定採用（取大者）** |
|---|---|---|---|
| codex | 50m | 50m | **50m** |
| grok | 65m | 70m | **70m** |
| composer | 75m | 70m | **75m** |
| 外層安全閥 | 90m | — | **90m** |

主委獨立重算（`.claude/tmp/runlog_dur.sh`，n=462，birth→mtime）：
ALL p50 5.2m／p95 26.3m／p99 48.5m／max 146.7m；codex max 45.1m／composer max 146.7m／grok max 64.6m；
**上述暫定值下三家誤殺皆 0/166、0/143、0/152**。
🔴 **仍為暫定**：birth→mtime 是 proxy，非 CLI wall-clock。**Task 3.1 上線取得真實 duration 後須重算並定稿**（codex 條件，接受）。

**D-3 解法（消除矛盾）**

「行為逐位元組不變」**收窄為：判定行為不變**——同一批輸入的 `(rc, kind)` 序列逐項相等。
audit 內容**本來就會增加欄位**，不在該不變式範圍內，SPEC 原文措辭有歧義，須改寫。
`match_rule` 的**封閉 enum 與事件契約**寫入 `scripts/audit_events.json`（既有 SoT，registry_version/schema_version 已存在），
SPEC 只 pointer；`unknown_event_policy` 沿用該檔既有欄位語意。

**D-4 解法**

- Task 2.5 需 **immutable corpus**：語料檔進版控並記 sha256，差集比對綁該 sha；語料變更須另行 commit 並重跑。
- 截斷 oracle 不得只靠 `--single`：由 D-2 的 terminal marker（明確的完成標記，非「檔案存在」）承擔。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01

**斷言**: 五張票合成一份 SPEC、一次 TODO 管線的前提不成立；Phase 4 是獨立的跨文件 enforcement 任務，現有 rollout scope 不足以安全交付。

**碼證**: SPEC Phase 4 Task 4.1 同時新增 `scripts/acceptance_state_check.sh` 並掛 `template_check.sh`、`doc_format_precheck.sh`、`gate.sh`；其邊界只說「新寫與本批修改」及具名 grandfather+到期日，沒有 scope manifest、判定新/改文件的機械來源、到期後行為或 owner。R1 brief 的盤點為 docs root 629 候選行、無標註語料；`test -e docs/GOVB0_FRICTION_TODO.md` → missing。`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS`。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8; handoffs/20260804-GOVB0-SPEC-R1-BRIEF.md#6a85d350afc

[BLOCKING] 信心度=High；checker 會在沒有明確 corpus/manifest 時自行猜測，可能一次性誤擋既有文件或把 grandfather 變成永久豁免。建議把 B-24 Phase 4 拆成獨立票與獨立 pipeline，先定義具名 manifest、owner、UTC expiry、expiry 後 fail-closed 行為及新/改文件判定；B-15 的 Phase 0+2、B-14/B-30 的 Phase 3、B-32 的 Phase 1 各自保留其明確依賴。這一點修正前不應生成可派工 TODO。

## CODEX-R1-P0-02

**斷言**: Phase 2 四項修法疊加後仍會放行真派工；`bash -c "codex exec x"` 是四項各自合理但組合失效的反例。

**碼證**: Task 2.1 要先剝除引號內容，Task 2.2/2.3 只在剝除後字串上看命令位置/可選 basename，Task 2.4 只新增 `scripts/cx_run.sh`/`committee_run.sh` callpoint；因此 `bash -c "codex exec x"` 的 agent token 被 Task 2.1 移除，後三項無可命中的 token。SPEC 同時把該語料列為「仍須 BLOCK」。同型 `bash -c "claude -p x"`、`sh -c '... /opt/homebrew/bin/codex exec ...'` 也有相同漏網。`bash scripts/cx_run.sh` 的 current caller 在 `scripts/committee_run.sh:268`；current regex 在 `scripts/gate_check.sh:86`。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8; scripts/gate_check.sh#871258c9ea2e; scripts/committee_run.sh#4c6bdeff1a15

[BLOCKING] 信心度=High；這不是單一 regex 的邊界瑕疵，而是前處理語義與命令遞迴語義衝突。另有未解的 quoted path（`"/my dir/codex" exec`）及 `scripts//cx_run.sh`/`./scripts/cx_run.sh`：正文只要求「定義行為」，沒有定義。修法需先固定 lexical contract：引號內 separator 不分隔，但 `sh -c`/`bash -c` 的 command payload 必須遞迴檢查或整體 fail-closed；path normalization/quoted path 規則須列入 stacked corpus，四個 mutation 逐一與疊加後都要紅。

## CODEX-R1-P0-03

**斷言**: Task 3.2 的 `.part`→rename 不能同時保證 B-14/B-30；現有 prompt 要求委員寫 `<out>`，而「`<out>` 存在」也不是可靠 terminal marker。

**碼證**: `scripts/cx_run.sh:512` 現行 prompt 為「產出寫到 `${out}`」；Task 3.2 卻要求委員寫 `<out>.part`，並只列 `cx_run.sh` 產出處理與 `new_brief.sh`/`brief_conformance_check.sh` 骨架文字。`new_brief.sh:39-40` 只有泛化產出說明，無法強制 CLI 的 filesystem write。若只改 prompt，委員仍可能寫 `<out>`；若只由 wrapper 改傳路徑，委員可忽略 prompt，且 current `_emit_family_result` 在 `cx_run.sh:262-272` 依現有 `<out>` 判定結果。SPEC 又未要求啟動前刪除/拒絕 stale `<out>`。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8; scripts/cx_run.sh#39cfdddec350; scripts/new_brief.sh#fe34f3d74fda

[BLOCKING] 信心度=High；若舊 `<out>` 已存在，CLI timeout 時「`<out>` 存在」會把上一輪內容誤當本輪 terminal marker；若 prompt-only 方案，委員自建檔仍可覆寫 final path。需改為每 attempt 的專用 temp namespace，啟動前確認 final marker 不存在且建立 attempt identity；只接受該 attempt 的 `.part`，格式檢查、flush/fsync、不可覆蓋的 atomic publish、audit/result_state 順序與 SIGKILL 殘留狀態須寫成可測 contract。Task 3.2 的 concurrent overwrite 情境也不能只接受「後者覆蓋前者」作為通過條件，否則成功產出可丟失。

## CODEX-R1-P0-04

**斷言**: §V 的核心驗收目前不可證偽：`--single` 可接受「最後一個 finding body 完整但檔案被截斷」的檔案，Task 2.5 的 exact-delta 也沒有 immutable corpus/baseline。

**碼證**: `scripts/completeness_check.sh:1459-1472` 的 `--single` 只驗 ID、重複 ID、finding body 與來源摘要，不驗 producer exit、EOF/terminal marker、預期 finding 集合或 attempt identity；R1 真實截斷探針 receipt 為 `COMPLETENESS PASS(single)`、`CHECK_RC=0`。SPEC Task 3.2 卻要求「截斷但格式完整的 `.part` 不得 rename」，沒有提供如何知道截斷的 expected count/hash/manifest。Task 2.5 只要求差集兩欄恰等於 SPEC 列舉項，沒有固定語料檔與舊版判定來源。

**來源摘要**: scripts/completeness_check.sh#12e981972d78; docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8; handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02

[BLOCKING] 信心度=High；改壞 rename 或 completeness gate 也可能不紅，因為 oracle 不存在；Task 2.5 若只餵 SPEC 明列的項目則是 tautology，若餵真實語料又無法判定「未預期」的合法基準。修法需提供 byte-faithful、具 sha256 的固定 corpus、舊版 snapshot/判定 receipt、預期 ID/終端 marker manifest，並讓 truncated/empty/stale-final mutation 逐一轉紅。§V 的「每個 Task mutation」不能只是一句待新增測試的承諾。

## CODEX-R1-P0-05

**斷言**: Phase 0 的新 `gate_deny.match_rule` schema 沒有封閉的 enum/事件契約，且「行為逐位元組不變」與新增 audit 欄位互相矛盾。

**碼證**: SPEC Task 0.1 說合法值由 `scripts/audit_events.json` 定義，但目前 registry 的 `non_debt_legacy_events` 只有 `gate_deny`，沒有 `gate_deny` event fields 或 `match_rule` enum；`committee_family_result` 也只有既有七欄。Task 0.1 同時要求新增 command+match_rule 欄位、`grep -Eo` 取命中片段、及「不改變任何放行/擋下判定」「行為逐位元組不變」。current `_append_gate_deny_audit` (`scripts/gate_check.sh:21-30`) 只寫五欄。

**來源摘要**: scripts/audit_events.json#91c19ab09e5e; scripts/gate_check.sh#871258c9ea2e; docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[BLOCKING] 信心度=High；實作者必須自行發明 match_rule 值、欄位型別/空值、控制字元 JSON escaping、sha256+512 bytes 的編碼與 1KB 上限，無法依 SPEC 寫出一致實作。新增 audit bytes 本身也不可能「逐位元組不變」；`(rc,kind)` 序列只證明兩個狹窄輸出，不證明 audit/stderr/副作用不變。修法需先在 registry 固化 event schema/enum/encoding，再把不變性改成決策序列+既有欄位/副作用對照，並明定 `grep -Eo` 無命中、換行、控制字元及 4MB input 的 rc/record contract。

## CODEX-R1-P1-06

**斷言**: OPEN-1 的 timeout 數據不能直接由 brief 的 `n=127`/`n=440` 重現；在目前 repo 的 462 個 runlog 以 nearest-rank 重算，排除已知 8801s composer 掛死後為 `N=461, P95=1563s, P99=2586s`。

**碼證**: 實跑命令：`find handoffs -type f -name '*.runlog' -exec stat -f '%B %m %N' {} + | awk 'NF>=3 {d=$2-$1; if(d>=0) print d "\\t" $3}' | sort -n`；輸出 `N=462`，最高為 `handoffs/20260803-govflow-todo-r2-composer.runlog=8801s`。排除此一已知掛死後：`codex N=166 P50=697s P95=1791s P99=2506s MAX=2704s`、`grok N=143 P50=290s P95=1254s P99=2503s MAX=3874s`、`composer N=152 P50=169s P95=698s P99=2315s MAX=4090s`；20m 以上為 49/461=10.63%，60m 以上為 2/461=0.43%，70m 以上為 0/461。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02; scripts/cx_run.sh#39cfdddec350

[MAJOR] 信心度=High（量測 proxy）；timeout 應涵蓋「家族 CLI process group launch 前一刻 → CLI 正常返回或被 timeout 終止」；runlog birth→mtime 還包含前置/後處理，output mtime→runlog close 也漏掉 CLI 等待，兩者都不是控制區間。以目前 proxy，20m 誤殺正常完成 10.63%；60m 誤殺 0.43%（grok 1、composer 1）；保守 per-family 建議為 codex 50m、grok 70m、composer 70m，70m 在清理後 corpus 無正常誤殺，但這只是暫定基線。Task 3.1 必須先落真實 CLI start/end/monotonic duration 及固定 sample manifest，再把值寫入 TODO；不可把目前 n=440/127 當不可重放事實。

## CODEX-R1-P0-07

**斷言**: OPEN-2 是治理控制面的 locale fail-open，必須開新票；「不納入本批」只有在正式登記、排序與環境護欄存在時才成立。

**碼證**: brief 的實測 receipt：`LC_ALL=C` 下 `gate.sh` 對 `## Verdict：` 發 token、`doc_format_precheck.sh` 對 `**Verdict: （待填…）**` rc=0 放行、`template_check.sh spec` 對合格 SPEC 誤判缺 §A。源碼顯示 Verdict 的 `awk` 字元類別在 `scripts/verdict_filled_check.sh:42-46`，SPEC anchor 以 `grep -qF "## §A"` 在 `scripts/template_check.sh:89-90`。

**來源摘要**: handoffs/20260804-GOVB0-SPEC-R1-BRIEF.md#6a85d350afc; scripts/verdict_filled_check.sh#dc0e6fae6e82; scripts/template_check.sh#7b2e6a018236

[BLOCKING] 信心度=High；兩個 fail-open 會在非 UTF-8/`C` locale 靜默放行，屬硬防線失效；template 誤報則會阻塞合規文件。建議新票範圍含 `gate.sh`、`doc_format_precheck.sh`、`verdict_filled_check.sh`、`template_check.sh` 的 locale matrix 與 CI 執行環境；不把它偷偷併進 B0，因為那會擴大 Phase 2 shared-path scope。若新票尚未正式入 backlog，B0 不可宣稱已處置此風險。

## CODEX-R1-P1-08

**斷言**: OPEN-3 應以「Phase 0 上線後補查」結案，不應除役；但 SPEC 沒有補查的樣本門檻、期限或除役條件。

**碼證**: 目前以 `gate_check.sh:86` 等價命令位置 regex 重建 `for f in codex composer grok; do ... done` 與 `completeness_check.sh --lock ...` 均無 family-position match；R1 synth 也將 FP-2 標為尚未定位。相同 synth 的內部覆寫已把另一例定位到 `claude[^|]*(-p|--print)`，不能反推 FP-2 已不存在。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02; scripts/gate_check.sh#871258c9ea2e

[MAJOR] 信心度=High；選項①是保守正確裁定，因現有無 command/match_rule 紀錄。TODO 應定義 telemetry 上線後的最小樣本數/觀測期間、`match_rule` 缺席時的結論、以及誰可將事故改標為記載錯誤；在此之前 Task 2.5 不得把 FP-2 靜默算成「預期差集」或「除役」。

## CODEX-R1-P1-09

**斷言**: Phase 1 的 unknown `brief-kind` 邊界與既有 parser 行為互斥，會讓實作者無法同時滿足 fail-closed 與「unknown 視同不需戳記並 audit 警示」。

**碼證**: SPEC Task 1.1 邊界同時要求「解析失敗/缺欄 fail-closed」與「未知值視同不需戳記但寫 audit」。既有 `scripts/brief_conformance_check.sh:64-89` 對缺欄與未知值皆 `exit 2`；`cx_run.sh:45-47` 只會消費成功 parser 的 `_bk`。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8; scripts/brief_conformance_check.sh#f178e28a45d2

[MAJOR] 信心度=High；若維持既有 parser，unknown 分支永遠不可達；若放行 unknown，便改變 fail-closed contract 且新增 audit event 未定義。修法需二選一並寫明：unknown 與 parse failure 都拒派，或新增明確 unknown schema/event、角色規則、審計欄位與測試；不可留給 TODO 實作者自行判斷。

## COMPOSER-R1-P0-01

**斷言**: Phase 2 四 Task 疊加後，`bash -c "codex exec x"` 在引號感知實作下仍可能 **fail-open**，與 Task 2.1 邊界③「引號內含真派工須 BLOCK」衝突。

**碼證**: 隔離原型 `bash /private/tmp/composer-govb0-r1/phase2_fullstack_probe.sh` → 8/9 通過，**唯一失敗**＝`bash -c "codex exec x"` got=ALLOW want=BLOCK。機制：雙引號內容被剝除後，外層字串不再命中家族段。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[BLOCKING] 信心度=High。SPEC 已列邊界案例但 **驗收未要求四 Task 疊加後重跑 TP 全集**；實作者若用 naive quote-strip 會開洞。修法：Task 2.5 語料＋整合測試必含此條；引號感知須 **保留 `bash -c`/`eval` 外殼內容** 或對 `-c` 後引號段單獨再判。

---

## COMPOSER-R1-P0-02

**斷言**: Task 3.2 要求委員寫 `<out>.part`，但 `cx_run.sh:512` prompt 仍為「產出寫到 ${out}」，且 Task 3.2「不可做」易被誤讀為不改 prompt——**路徑未對齊必致 B-30 重現或 format-failed**。

**碼證**: `grep -n '產出寫到' scripts/cx_run.sh` → `:512` 僅 `${out}`；Task 3.2 改法①寫 `.part`、不可做段寫「不改委員 prompt 要求它自己做 atomic write」——**未列 harness prompt 改為 `${out}.part` 或內部 remap**。

**來源摘要**: scripts/cx_run.sh#39cfdddec350

[BLOCKING] 信心度=High。失敗模式：委員寫入 `<out>` 直接上架（無 atomic）或寫錯路徑只剩 `.part`。修法：Task 3.2 增子步「`prompt` 產出路徑與 `new_brief.sh` 骨架同步為 `.part`」；驗證增「prompt 含 `.part` 後綴」斷言。

---

## COMPOSER-R1-P1-01

**斷言**: Task 2.5「『本來擋現在放行』與『本來放行現在擋』兩欄的**每一項**都須在 SPEC 中被預期」在 Phase 0 上線後 **不可執行**——真實 `gate_deny` 語料會產生 SPEC 未列舉項，導致永遠 FAIL 或實作者悄悄放寬。

**碼證**: §V「行為差集」＋Task 2.5 驗證②③；Phase 0 Task 0.1「存活至永久」且「後續 Phase 只讀」⇒ Phase 2 完工後 deny 紀錄持續累積。`CLAUDE-R1-P0-01`（synth C-8）已證目前零 deny 指令欄。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MAJOR] 信心度=High。修法：差集驗收改為 **必要子集＝Task 2.1–2.4 列舉 12 條**；Phase 0 真實語料為 **附加堆**，出現未預期附加項時須 **人工標註＋回寫 SPEC 或 backlog**，而非機械 FAIL。

---

## COMPOSER-R1-P1-02

**斷言**: 五票合一 SPEC **可接受**，但「一次管線」假設把 **Phase 4（新 checker + grandfather 機制）** 與 **Phase 2（高風險正則）** 綁在同一 adversarial／TODO 臨界路徑，放大單輪 BLOCKING 面。

**碼證**: §P 5 Phase／11 Task；`CODEX-R1-P0-03`（synth C-5）629 docs 候選；Phase 4 已限縮 scope 仍含新腳本＋hook 接入。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02

[MAJOR] 信心度=Medium。若本輪修補後 Phase 2／3 穩定，Phase 4 可跟進；**不建議拆票**除非 Phase 4 grandfather 機制再膨脹。判準：新腳本 >200 行或需改 `template_check` 以外第三個 caller 時再拆。

---

## COMPOSER-R1-P1-03

**斷言**: OPEN-2（locale 守衛漂移）應 **開 B-33、不納入本批**，但嚴重度應標 **MAJOR** 並寫入 TODO §0 已知債——非「可忽略」。

**碼證**: 本機 `bash /private/tmp/composer-govb0-r1/open2_locale_probe.sh` → `doc_format_precheck` 在 `LC_ALL=C` 下對 `**Verdict: （待填…）**` rc=0；synth C-12 表三例方向不一致。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02

[MAJOR] 信心度=High（gate.sh 項採 synth 主委實測）。同意主委不納入本批；**攻「不納入」≠「不嚴重」**。

---

## COMPOSER-R1-P1-04

**斷言**: Task 4.1 grandfather 清單「須具名且有到期日」**未指定誰維護、依何事件續期**，實作後易成永久豁免垃圾場。

**碼證**: Task 4.1 邊界②僅寫清單格式；無 owner／review cadence。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MAJOR] 信心度=High。修法：指定 Claude 維護 `docs/governance_grandfather.yaml`；到期預設 90 天；續期須附機械掃描 receipt。

---

## COMPOSER-R1-P1-05

**斷言**: brief 假設「Phase 2 四 Task 疊加不開新洞」**僅在含 `bash -c` 修補後才成立**；其餘 8 條 TN/TP 原型全通。

**碼證**: `phase2_fullstack_probe.sh` 輸出 8/9 ok；`b15probe.sh`／`b15probe2.sh` 重現 FP-1（洞 A）、洞 B 誤擋與 fail-open `| claude -p`。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02

[MAJOR] 信心度=High。疊加本身不互斥，**實作技巧**（quote-strip 範圍）才是風險；見 P0-01。

---

## COMPOSER-R1-P2-01

**斷言**: Task 0.1 在 deny 路徑加 `grep -Eo` **若誤入判定前主路徑**，可能因 grep 失敗或性能改變 rc；目前設計「先判後記」則安全。

**碼證**: `gate_check.sh:86` 判定 → `:88` 排除 → 僅 deny 時 `_append_gate_deny_audit`；SPEC Task 0.1 改法①取命中片段在判定**之後**。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MINOR] 信心度=Medium。修法：Task 0.1 明寫「`grep -Eo` 只在 `kind` 已設為 dispatch 之後執行；grep 失敗不得改 rc」。

---

## COMPOSER-R1-P2-02

**斷言**: Task 1.1 驗證「prompt 不含 RECONCILE-STAMP」**無法證偽 agent 仍寫 `## RECONCILE-STAMP` 標題**——測的是 harness 字串，不是委員行為。

**碼證**: Task 1.1 驗證③明訂「不得以委員這次沒寫為斷言」；僅測 prompt 文字。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MINOR] 信心度=High。可接受為必要非充分條件；B-32 根因是 **誘導句**，移除誘導已覆蓋主要風險。可選增強：`completeness_check` 錯誤訊息專屬提示（票 B-32 ③，本批不做）。

---

## COMPOSER-R1-P2-03

**斷言**: OPEN-3 應 **Phase 0 後補查**，不應將 B-15 FP-2 從 backlog **除役**——現行不可重現不等於從未發生。

**碼證**: `b15probe.sh` FP-2a/b ALLOW；backlog `B-15` 仍列 `for` 迴圈事故。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#fa6a9a90835c

[MINOR] 信心度=High。SPEC §A OPEN-3 結案文案建議用「未定位／待紀錄」而非「記載錯誤」。

---

STATUS: DONE

## 戳記

RECONCILE-STAMP: composer APPROVED 2026-08-04 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2
RECONCILE-STAMP: codex APPROVED 2026-08-04 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2

RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2
