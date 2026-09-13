# Reconcile — 20260912-docrot-x-consult-r4

**來源** 20260912-docrot-x-consult-r4-codex.md, 20260912-docrot-x-consult-r4-composer.md, 20260912-docrot-x-consult-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：HANDOFF.md

本輪性質：依使用者 2026-09-13 裁定「不接受用紀律和記憶當解法和修正」，只問 consult-r3 定案中兩條紀律型 Task（1.6／1.8）改機械型。三家皆選機械版；Q1 三家版本不同（皆機械）⇒ 依「同為機械時取最窄能過三問者」擇 grok 版；Q2 三家皆選 codex 版 ⇒ 採 codex R4 逐字。本收斂**覆寫** consult-r3 收斂之 C7／C9 處置與定案 TODO 之 Task 1.6／1.8 列；其餘 r3 定案不變。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **R1 Task 1.6 為紀律型，須改機械（三家）**——「consult-r3 定案 Task 1.6 為」「consult-r3 定案之 Task 1.6」「codex R3 的 `CODE-ANCHOR」 | P0 | COMPOSER-R4-P0-01, GROK-R4-P0-01, CODEX-R4-P1-01 | 採納→Task 1.6 改為 **grok R4 必答 1 (b) 逐字**：P0/P1 finding 之 `**碼證**` 必含 `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>` 兩行字面；`completeness_check.sh --single` 對 P0/P1 缺任一 token → fail-closed，`CODE-ANCHOR` 落 `HISTORY-BEGIN..END`／`## 沿革` → fail（與 Task 1.4 同一判定）；P2/P3／sentinel 不套；改 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`、`scripts/completeness_check.sh`、`scripts/new_brief.sh`、`tests/governance/test_docrot_e3_brief_placeholder.py`；驗收與 mutation 逐字見 grok R4 必答 1 表。**未採**（同為機械、較寬）：codex 之 `ARCH-EDGE`／current-block manifest／heading round≥R4 邊界；composer 之 `ARCH-EDGE`＋`VERIFY:` 必填。codex 之「歷史語料 15/15 會被拒」採為 forward-only 邊界（見 R3 群） |
| **R2 Task 1.8 為紀律型，須改機械（兩家 P0；codex Q2 同向）**——「consult-r3 定案 Task 1.8 為」「consult-r3 定案之 Task 1.8」 | P0 | COMPOSER-R4-P0-02, GROK-R4-P0-02 | 採納→Task 1.8 改為 **codex R4 必答 2 逐字**：`scripts/brief_conformance_check.sh` 佔位段由全文 `grep -qF` 改 line-oriented exact-line 比對 generator 完整欄位行；成對 fence（行首可有空白之 ``` 或 ~~~）內不算，未閉合 fence fail-closed rc=2；行首 `>` blockquote 內不算；其餘 active 行照 exact-line 不做語意猜測；檔頭／ERROR 含封閉字面 `不涵蓋手寫 brief`；驗收 `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` rc=0，mutation 兩向（skeleton rc≠0；blockquote／fence 內 rc=0；未閉合 fence rc≠0；改回全檔 substring → quoted mutation 紅） |
| **R3 forward-only：機械閘只檢新交件，不溯及 r3 語料（三家）**——「brief 之 assumed「codex 機」「brief assumed「codex 機械」 | P1 | COMPOSER-R4-P1-01, GROK-R4-P1-01 | 採納（三家實跑：既有 15 個 P0/P1 若套新 token 會拒 13–15/15；`--single` 為 per-file，只對 Task 1.6 落地後之新交件生效；r3／stamp-r1 附錄 byte-faithful 不改。codex 之 heading round≥R4 機械邊界未採（較寬），具名殘留：對舊交件重跑 `--single` 會紅，屬面向未來不溯及既往之已知代價） |
| **R4 二分判準讀法＋Task 1.1／1.2／1.7 標記（兩家）**——「Grok R3 Task 1.1、1.2、1.」「assumed「主委忘了做⇒rc≠0」能」「Task 1.7（成效句寫入權威 synth」 | P1 | CODEX-R4-P1-02, GROK-R4-P1-02, COMPOSER-R4-P2-01 | 部分採納（判準採 grok「落地後持續閘」讀法。**Task 1.1／1.2**：codex 所要之 pytest 反向 mutation 已在 r3 收斂「測試落點」段採 codex 原文落入 `test_docrot_f2_total_items_count.py`，即 rc 閘 ⇒ mechanical，無新動作。**Task 1.7**：三家三讀法——codex (c) 砍為 blocked-by 殘留、composer (b) `reconcile_build.sh` 加 `grep -qF 'doc_friction_ratio'` 閘、grok mechanical（一次寫入 SSOT、無後續人審）；採 grok（零新機制、成效句已寫在 r3 收斂），composer 版會對所有 consult synth 誤擋、codex 版之唯一性閘為新機制，皆未採） |

**改後 TODO**：仍 8 條（Task 1.1–1.5、1.7 照 r3 定案；1.6／1.8 以本輪 R1／R2 逐字替換）。無新 epic、新腳本、語意閘。

**紀律型殘留**：0（8 條全為 rc 閘）。

**進實作條件**：本收斂三家戳記 APPROVED ＋ `debt_clear` rc=0 ＋ 使用者白話審閱放行 → 實作 Task 1.1–1.8 → 派三家審碼取戳記後才算完成。

Verdict：可合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P1-01

**斷言**: codex R3 的 `CODE-ANCHOR` 全量硬必填原案若不設 migration boundary，會拒收三份既有 R3 consult 的全部 15 個 P0/P1 finding；因此該原案不能直接採用。

**碼證**: `for f in ...; do grep -Ec '^## ...-P[01]-' "$f"; grep -Ec '^\\*\\*碼證\\*\\*.*CODE-ANCHOR:' "$f"; done` 實跑輸出：codex `P0/P1=7 code-field-anchor=0 reject=7`、composer `2/0/2`、grok `6/0/6`；三份 R3 stamp 均 `P0/P1=0 code-field-anchor=0 reject=0`。`nl -ba scripts/completeness_check.sh | sed -n '235,357p'` 顯示現行 parser 沒有 `CODE-ANCHOR` 狀態。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-codex.md#2588e889b572;handoffs/20260912-DOCROT-X-CONSULT-R3-composer.md#a7a0a0ca65af;handoffs/20260912-DOCROT-X-CONSULT-R3-grok.md#c7b9198ae44d;scripts/completeness_check.sh#49d4fa0f4217

[MAJOR] 信心度=High。失敗模式是既有交件被當成未填新格式，造成回放／重驗全紅，而不是只擋忘記填 anchor 的新 R4 交件。採本報告「必答 1」的 (b) migration-scoped 機械版：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`、`scripts/completeness_check.sh` 與既有 E3 測試檔同步；只在 `--single` 且 heading round 為 `R4` 或更新的 P0/P1 finding 要求 `CODE-ANCHOR: <repo-relative path>:<positive line>`、`ARCH-EDGE: producer|contract|consumer`、`MUTATION: <非空破壞描述>`，anchor path/line 存在且不落 HISTORY；R1–R3 舊交件維持既有欄位規則。可行性證據：既有 `--single` strict parser 已有欄位狀態與 history 區間可接入，且既有 E3 測試可承載 current-valid、missing-anchor、history-anchor 三向 mutation；本報告未宣稱這些未落地測試已通過。

## CODEX-R4-P1-02

**斷言**: Grok R3 Task 1.1、1.2、1.7 依 brief 的「主委忘了做是否有 rc≠0 擋住」判準仍是 discipline；只改 C7／C9 而不處理它們，會留下三個靠人檢查的缺口。

**碼證**: Grok R3 Task 1.1／1.2 的驗收直接呼叫 `spec_count_audit.py --dupes` 並以 stderr 內容判斷，該程式 `scripts/spec_count_audit.py:113-126` 的 `--dupes` 正常返回 `0`；Task 1.1 表格明寫「rc 見 1.3」。Task 1.7 的驗收是 `grep -n ...` 並要求「恰一權威落點」，但命令沒有 `-c`／唯一性 rc 斷言。`nl -ba scripts/gov_check.sh | sed -n '269,274p'` 另證明現行 warn-only 路徑本身不會補回 1.1／1.2 的漏掃或收窄測試。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-grok.md#c7b9198ae44d;handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#073012cd7e51;scripts/spec_count_audit.py#cbcbc959321d;scripts/gov_check.sh#4b333ce050ff

[MAJOR] 信心度=High。1.1／1.2 的 raw CLI 即使行為錯誤仍可 `rc=0`，1.7 的 grep 也不能證明單一權威；這與本輪使用者裁定的機械化要求直接衝突。處置見「必答 3」：1.1、1.2 各在既有 `tests/governance/test_docrot_f2_total_items_count.py` 補反向 mutation，讓 pytest assertion 的 rc 成為阻擋；1.7 以具名 residual 移出 TODO，因現有收斂／completeness 工具沒有 target-aware 指標唯一性閘，新增跨 synth parser 會超出本輪禁止新腳本／不擴機制的邊界。

## COMPOSER-R4-P0-01

**斷言**: consult-r3 定案 Task 1.6 為紀律型（範本字面＋主委拒收），違反使用者 2026-09-13「不接受用紀律和記憶當解法和修正」；主委若忘記拒收，架構向 P0/P1 仍可 `--single` rc=0 通過。

**碼證**: `handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` C7 處置「採 grok 原文…**不採** codex 之 `CODE-ANCHOR`…＋`completeness_check --single` fail-closed」；grok Task 1.6 驗收＝`grep -F 'doc-literal-only'`、正文「執行靠主委拒收＋後續可選機檢」；`nl -ba scripts/completeness_check.sh | sed -n '350,353p'` 現僅 `seen_assert`／`seen_code`／`seen_digest`，無 `CODE-ANCHOR` token 檢查。RECHECK: 構造 P0 finding 碼證僅「章節短句」→ `completeness_check.sh --single` 現行 rc=0。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#073012cd7e51;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#58b631dccf2b;handoffs/20260912-docrot-x-consult-r3-grok.md#c7b9198ae44d

[BLOCKING] 信心度=High。**修法（Q1 三選一）**：**(a) 採 codex 機械版**——見必答 1 Task 1.6 逐字表（合併 codex R3 Task 1.1＋1.2，仍占 Task 1.6 名額）。**可行性**：既有 `--single strict=1` 欄位解析可擴三 token；`test_docrot_e3_brief_placeholder.py` 已為落點；不新腳本。

## COMPOSER-R4-P0-02

**斷言**: consult-r3 定案 Task 1.8 為紀律型（只收窄 ERROR 文案；合法引用 skeleton 仍被全文 `grep -qF` 誤拒時靠人改寫），違反同一使用者裁定；主委忘記改寫引用時無 rc≠0。

**碼證**: synth C9「**不採** codex 之改為 generator 欄位完整行比對＋允許 quoted/fenced」；`scripts/brief_conformance_check.sh:330-353` 仍 `grep -qF -- "${_ph}" "${brief}"` 掃**整份** brief；grok Task 1.8 mutation＝「宣稱改回『手寫零誤擋』⇒ 文案測試或 review 再打回」（無自動 rc）。RECHECK: brief 內 fenced 行含 `（填標題）` 字面 → 現行 rc=2。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#073012cd7e51;scripts/brief_conformance_check.sh#1ba0ef67016f;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#58b631dccf2b

[BLOCKING] 信心度=High。**修法（Q2 三選一）**：**(a) 採 codex 機械版**——見必答 2 Task 1.8 逐字表（codex R3 Task 1.3 原文）。**可行性**：既有 `test_docrot_e3_brief_placeholder.py` 可從 `new_brief.sh` 產 skeleton；加 quoted/fenced 反向 mutation 即可雙向 rc。

## COMPOSER-R4-P1-01

**斷言**: brief 之 assumed「codex 機械版對既有 brief／交件語料不會大量誤擋」若解讀為 retroactive，會拒 13/15 個歷史 P0/P1；若僅 forward-only（新交件＋改後 `--single`），誤擋可接受且與使用者「不要紀律」一致。

**碼證**: `python3` 掃描 `handoffs/20260912-docrot-x-consult-r3-{codex,composer,grok}.md` ＋ `handoffs/20260912-docrot-x-stamp-r1-{codex,composer,grok}.md`：P0/P1 計 **15**，缺 `CODE-ANCHOR` 或 `MUTATION` 計 **13**（stamp 三份 0 finding）；其中 grok/consult-r3 碼證多含 `path:line` 但無 `CODE-ANCHOR:` token，機械閘須認 token 不認隱式 path。RECHECK: 同上 python 探針。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#073012cd7e51;handoffs/20260912-docrot-x-consult-r3-grok.md#c7b9198ae44d

[MAJOR] 信心度=High。**修法**：Task 1.6 實作時 `--single` **只檢新交件**，不 retroactive 掃 r3 附錄；收斂 synth 附錄 byte-faithful 保留。可行性：現行 `--single` 本就 per-file；無需改歷史 lock。

## COMPOSER-R4-P2-01

**斷言**: Task 1.7（成效句寫入權威 synth）仍為 discipline——收斂後 `grep` 驗收，主委忘了寫成效句時派工／commit 前無 rc≠0。

**碼證**: grok Task 1.7 驗收＝`grep -n 'doc.friction.ratio|活文多落點占比' handoffs/reconcile/*/synth.md`；無腳本在 `reconcile_build`／`debt_clear` 前 fail-closed。RECHECK: 構造缺 `doc_friction_ratio` 之 synth → 現行流程仍可 `debt_clear`（若他檔合規）。

**來源摘要**: handoffs/20260912-docrot-x-consult-r3-grok.md#c7b9198ae44d

[MINOR] 信心度=Medium。**修法（附帶三選一）**：**(b) 另一機械版**——Task 1.7 增一句：`scripts/reconcile_build.sh` 寫 consult synth 前 `grep -qF 'doc_friction_ratio' "${draft}"` 否則 exit 1（封閉字面，改既有腳本）。**可行性**：`reconcile_build.sh` 已有 brief-kind 分支；不新腳本、不語意判斷。

---

## GROK-R4-P0-01

**斷言**: consult-r3 定案之 Task 1.6（範本字面＋主委／人審拒收、不改 `completeness_check --single`）是紀律型，違反使用者 2026-09-13「不接受用紀律和記憶當解法」；主委忘了拒收時，純散文 P0 仍可 `--single` rc=0。

**碼證**: r3 synth C7「採 grok 原文…**不採** codex 之 `CODE-ANCHOR`…＋`completeness_check --single` fail-closed」；本家 r3 Task 1.6 正文「執行靠主委拒收＋後續可選機檢」、驗收＝`grep -F 'doc-literal-only'`；`scripts/completeness_check.sh:350-353` 現僅 `seen_assert`／`seen_code`／`seen_digest`。VERIFY: 構造 P0 碼證僅「見某某章節用詞差異」→ `bash scripts/completeness_check.sh --single /tmp/grok-r4-probe/prose_p0.md --family grok` → **rc=0**（本輪實跑）。RECHECK: 同上構造。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#b668b6c7ade7;handoffs/20260912-docrot-x-consult-r3-grok.md#96accd24398d;scripts/completeness_check.sh#c76692e041da

[BLOCKING] 信心度=High。**修法（Q1＝(b)）**：見必答 1——機械閘＝P0/P1 必含 `CODE-ANCHOR:`＋`MUTATION:`，缺則 `--single` fail-closed；HISTORY 區間同 Task 1.4；**不**把 `ARCH-EDGE`／`VERIFY:` 列為 completeness 必填（較 codex 全套窄，仍過三問）。**可行性**：`--single` 已有 strict 欄位狀態機（L226-228、L350-353）；只加兩個 token 旗標；測試落點既有 `tests/governance/test_docrot_e3_brief_placeholder.py`；不新腳本。

## GROK-R4-P0-02

**斷言**: consult-r3 定案之 Task 1.8（只收窄 ERROR／誠實邊界文案；合法引用骨架字面仍靠人改寫或 `VERIFY-EXEMPT`）是紀律型，違反同一裁定；全文 `grep -qF` 誤拒時主委忘記改寫 ⇒ 無機械放行路徑。

**碼證**: r3 synth C9「**不採** codex 之 generator 欄位完整行比對＋允許 quoted/fenced」；`scripts/brief_conformance_check.sh:330-353` 對 brief **全文** `grep -qF`；同檔 L326-328 自承「對手寫 brief 零誤擋／只擋骨架原樣」且無 fence scope。RECHECK: `nl -ba scripts/brief_conformance_check.sh | sed -n '325,353p'`；brief 內 fenced 含 `（填標題）` → 現行預期 rc=2。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982;scripts/brief_conformance_check.sh#55d4b8162804;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#b668b6c7ade7

[BLOCKING] 信心度=High。**修法（Q2＝(a)）**：見必答 2——改為 generator 欄位完整行比對；fenced／quoted 內骨架字面不算佔位；mutation 兩向（skeleton rc≠0、fenced/quoted rc=0）。**可行性**：既有 E3 測試已能從 `new_brief.sh` 產 skeleton；只需加反向 mutation；不新腳本。

## GROK-R4-P1-01

**斷言**: brief assumed「codex 機械版對既有 brief／交件語料不會大量誤擋」若解讀為對已交付 P0/P1 做同一 token 契約，會拒光 consult-r3 語料；不得拿「歷史會紅」否定 forward-only 機械閘。

**碼證**: 本輪探針掃 `handoffs/20260912-docrot-x-consult-r3-{codex,composer,grok}.md` ＋ `handoffs/20260912-docrot-x-stamp-r1-{codex,composer,grok}.md`：P0/P1 合計 **15**（stamp 三份皆 0）；字面 `CODE-ANCHOR` 作**證據格式**（修法段 meta 提及計 miss）→ 拒 **15/15**；缺 `MUTATION:` → 拒 **13/15**；僅要求 `path:line` → 拒 **3/15**。CODEX-R3-P1-02／P1-07 之 `CODE-ANCHOR` 命中僅在「修法：增加 CODE-ANCHOR…」meta 句。RECHECK: 重跑 `/tmp/docrot_ca_probe.py`（或同邏輯掃描）。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982;handoffs/20260912-docrot-x-consult-r3-codex.md#fdd556f07f63;handoffs/20260912-docrot-x-consult-r3-grok.md#96accd24398d

[MAJOR] 信心度=High。**修法**：Task 1.6 之 `--single` 只檢**新交件**（現行 per-file 行為），不 retroactive 改寫 r3 附錄；實作後第一輪交件須改用新 token。可行性：無需改 lock／歷史 synth。

## GROK-R4-P1-02

**斷言**: assumed「主委忘了做 ⇒ rc≠0」能乾淨二分 8 條 Task——若把「Task 驗收命令」也算 rc 閘，則現行 1.6／1.8 的 `grep -F` 驗收會把兩者標成 mechanical，二分失敗；合法讀法只能是「落地後、主委忘了執行該 Task 所依賴的人審步驟時，管線是否仍有 rc≠0」。

**碼證**: grok r3 Task 1.6 驗收＝`grep -F 'doc-literal-only' …`（有 rc）；Task 1.8 驗收＝`grep -F '不涵蓋手寫' …`（有 rc）；但兩條正文皆把**持續阻擋**交給主委拒收／改寫引用。對照 Task 1.3／1.4／1.5：落地後忘了人審，`gov_check`／`completeness`／`verification_claim_check` 仍可 rc≠0。RECHECK: 對照 `handoffs/20260912-docrot-x-consult-r3-grok.md` 必答 2 表 L51-55。

**來源摘要**: handoffs/20260912-docrot-x-consult-r3-grok.md#96accd24398d;handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982

[MAJOR] 信心度=High。**修法**：附帶表一律用「落地後持續閘」讀法（見必答 3）；1.7 寫入一次成效句 SSOT、無後續人審步驟 ⇒ **mechanical**（勿與 D4 停輪自動化混淆；D4 本輪仍不做）。

---

## 戳記

RECONCILE-STAMP: grok APPROVED 2026-09-13 sha256:1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23 task:20260912-DOCROT-X-STAMP-R2

RECONCILE-STAMP: composer APPROVED 2026-09-13 sha256:1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23 task:20260912-DOCROT-X-STAMP-R2

RECONCILE-STAMP: codex APPROVED 2026-09-13 sha256:1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23 task:20260912-DOCROT-X-STAMP-R2
