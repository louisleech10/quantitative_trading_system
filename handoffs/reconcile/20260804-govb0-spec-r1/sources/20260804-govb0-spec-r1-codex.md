# GOVB0 SPEC R1 adversarial review

family: codex
task-id: GOVB0-SPEC-R1
scope: docs/GOVB0_FRICTION_SPEC.md only; no code/test changes

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

## Verdict

需修補後派工；目前不能進 TODO 生成。逐題裁定：Q1 使用 CLI process-group launch→return/kill 區間；暫定 codex 50m、grok 70m、composer 70m，需 Task 3.1 真實 duration manifest 定稿。Q2 為 BLOCKING locale 新票，票號由 backlog owner 配置；本批不併入但不可無票放置。Q3 選 Phase 0 後補查，不除役。Q4 現有限縮不足，B-24 Phase 4 應獨立 pipeline，grandfather 必須具名、owner、UTC expiry、到期後狀態。Q5 §V 目前有不可證偽與 tautological acceptance，須補 manifest/baseline/oracle。Q6 未宣告 forward dependencies 包括 registry enum、舊版 gate snapshot、immutable corpus、`.part` prompt/attempt identity 與 Phase 4 rollout manifest；Phase 4 是 downstream audit，不是本身的循環，但現有依賴圖不完整。Q7 P0 findings 修正前不可生成可派工 TODO。

被當成事實的未驗證假設（§0）：`n=440`/`n=127` 的樣本集合與排除規則未固定；「逐位元組不變」未定義可觀測範圍；`.part` 截斷可由 `--single` 識別；`<out>` 存在足以代表本次 terminal；Phase 4 grandfather scope 可由散文落實；四個 gate regex 修改可在疊加後保留 `sh -c` 真派工攔截。

STATUS: DONE
