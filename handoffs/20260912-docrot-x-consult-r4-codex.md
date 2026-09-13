# DOCROT consult R4 — Codex

task-id: `20260912-DOCROT-X-CONSULT-R4`
family: `codex`
findings-round: `R4`
scope: 只審 C7／C9 與 Grok R3 Task 1.1–1.8；不重議 C1–C6、C8、D3–D5；禁改碼。

## §0 假設挑戰與驗證邊界

- fact-verified：`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` → PASS；body hash `ddb910b2b323a228c1c1bfdba753db7f3babdf1e2b32cb17948f5031df8e7307`，三家均 `APPROVED`。
- fact-verified：對三份 R3 consult 與三份 R3 stamp 以 canonical heading 及 `**碼證**` 欄計數；R3 consult 為 codex `7/7`、composer `2/2`、grok `6/6` 缺 `CODE-ANCHOR:`，合計 **15/15** 會被「所有 P0/P1 一律必填」拒收；三份 stamp 無 P0/P1，為 **0/0**。
- fact-verified：目前 `completeness_check.sh` 的 strict body parser 只追蹤 `seen_assert`／`seen_code`／`seen_digest`；`brief_conformance_check.sh` 的 placeholder 段仍以 `grep -qF` 掃原始 brief，雖然其他 kind/fact 路徑已有獨立 fence stripping。
- assumption rejected：不能把 codex R3 的 anchor 原案直接套到既有 R1–R3 交件而宣稱「不會大量誤擋」；15/15 是已實跑的反例。機械化仍可做，但必須有明示的 R4 migration boundary。

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

## 必答 1 — Q1（C7）

**選擇：(b) 提出另一個機械版。** Codex R3 原案的機械方向正確，但「所有歷史 P0/P1 立即必填」被 15/15 corpus replay 否證；採下列窄化版，不靠主委記憶，也不改歷史交件。

逐字規格：

> 在 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 的 canonical 四欄「碼證」條、`templates/COMMITTEE_FINDING_TEMPLATE.md` 規則 2、`scripts/new_brief.sh` review/consult current-block 骨架中，加入：`R4+ 的 P0/P1 finding 必須在 **碼證** 欄含 CODE-ANCHOR: <repo-relative path>:<positive line>、ARCH-EDGE: <producer|contract|consumer>、MUTATION: <非空可執行破壞描述>；CODE-ANCHOR 的 path 必須存在、line 必須在檔案範圍內，且不得落在 HISTORY-BEGIN..HISTORY-END 或沿革節。R1–R3 交件不回溯要求新 token。`
>
> 在 `scripts/completeness_check.sh` 的 `--single` strict parser 中，以 heading 的 round 數字作封閉判定：`R4` 以上且 severity `P0`／`P1` 時，缺任一 token、格式不符、path 不存在、line 越界或 history 命中即 `rc=1`；R1–R3 僅沿用既有 `seen_assert`／`seen_code`／`seen_digest` 規則。`--lock`／synth 入口不因此翻轉。

驗收與預期 rc：

- `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` → `rc=0`；測試須含 R4 current-valid `rc=0`、missing `CODE-ANCHOR` `rc=1`、missing `MUTATION` `rc=1`、history anchor `rc=1`、R3 legacy replay 不因新 token 轉紅。
- `bash scripts/completeness_check.sh --single <R4-valid> --family codex` → `rc=0`；同一 fixture 刪一個 token／移入 history → `rc=1`。
- corpus replay：三份 R3 consult 的既有 P0/P1 維持 legacy path；三份 R3 stamp 沒有 P0/P1，不新增拒收面。

mutation：把 R4 fixture 的 `CODE-ANCHOR`、`MUTATION` 或 current/history 判定任一移除，對應 `--single` 應由 `rc=0` 變 `rc=1`；把 round gate 改成所有 round 都要求 token，R3 corpus 的 `15/15` legacy replay 應轉紅，證明 migration boundary 真有作用。

三問：擋根因＝未指向可核對碼／架構的 P0/P1；不做＝下一輪仍可用散文欄位合法通過，重演 C7 字面戰；機械量＝R4+ P0/P1 的 token、path/line、history 區間與 mutation rc，且舊 corpus replay 不被回溯誤擋。

## 必答 2 — Q2（C9）

**選擇：(a) 採 codex 機械版，並把 quote/fence 範圍寫成封閉語法。** 這能把現行 `grep -qF` 的誤擋改成 generator placeholder 的完整行比對；它不替代 C7 anchor gate。

逐字規格：

> 在 `scripts/brief_conformance_check.sh` placeholder 段，把對每個 placeholder 的 `grep -qF -- "${_ph}" "${brief}"` 改為 line-oriented scanner：placeholder 集合只含 `new_brief.sh` 實際輸出的**完整欄位行**（含其固定前綴／尾綴），只在 active top-level 行做 exact-line match，不做 substring match。fence 定義沿用本檔既有判準：行首可有空白的成對 ````` `` 或 `~~~`；fence 未閉合即 fail-closed `rc=2`。quoted 定義為行首第一個非空白字元為 `>` 的 Markdown blockquote；該行及其內容不算 generator placeholder。其他含有引號或 inline code 的 active 行仍照 exact-line 規則，不以語意猜測。

驗收與預期 rc：

- `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` → `rc=0`；保留 generator skeleton `rc!=0`，新增 active exact placeholder `rc!=0`、blockquote 內 placeholder `rc=0`、成對 fence 內 placeholder `rc=0`、未閉合 fence `rc!=0`。
- `bash scripts/brief_conformance_check.sh <generated-skeleton>` → `rc=2`；同一 placeholder 只放在 blockquote／成對 fence → `rc=0`（其餘必填欄位已填）。

mutation：將 exact-line scanner 恢復為全檔 substring `grep -qF`，blockquote／fence 兩個合法引用 mutation 應由 pytest 轉紅；移除 active-line 檢查，generator skeleton 應錯誤變成 `rc=0`，同一測試轉紅。這兩個方向分別驗「不誤擋」與「仍擋骨架」。

三問：擋根因＝generator 骨架原樣派出與合法引用被同一 substring 規則混淆；不做＝下一輪仍因引用字面誤擋或放出空骨架，再燒至少一輪 E3 修補；機械量＝完整行 exact match、fence state、blockquote prefix 與兩向 mutation rc。

## 必答 3 — Grok Task 1.1–1.8 的 mechanical／discipline 標記

判準固定為「主委忘了做，現有驗收是否會以 rc≠0 擋住」，以下先標 R3 原始 Grok 表，再列 R4 處置：

| Task | R3 原始標記 | 證據／理由 | R4 處置 |
|---|---|---|---|
| 1.1 `dupes()` 區間 skip | `discipline` | raw `--dupes` 命中仍 rc=0；表格把 rc 交給 1.3 | (b) 在既有 F2 pytest 加 current→HISTORY→current mutation；錯誤 `break` 時 pytest rc=1 |
| 1.2 `dupes()` 收窄 `_RE_TOTAL_ITEMS` | `discipline` | raw `--dupes` 仍 rc=0，stderr 內容需人讀；無反誤報 rc gate | (b) 在既有 F2 pytest 加「五維度不報／共 N 條雙落點報」mutation；恢復三 regex 時 pytest rc=1 |
| 1.3 `gov_check` 1b fail-closed | `mechanical` | 本次 docs diff 命中 dupes 應使既有 1b `rc≠0` | 保留；hook 仍 warn-only，1b 是阻擋點 |
| 1.4 completeness 拒 HISTORY anchor | `mechanical` | `--single` 的 history-anchor mutation 預期 `rc≠0` | 保留；與 Q1 的 R4+ anchor gate 分開記錄 |
| 1.5 consensus audit backing | `mechanical` | 無 audit 的封閉 consensus token 預期 claim checker `rc=1` | 保留；不擴 codex 的 output/hash 加嚴版 |
| 1.6 碼證指向碼／架構 | `discipline` | R3 原案明寫「執行靠主委拒收＋後續可選機檢」 | Q1 (b)；改成 R4+ `--single` fail-closed |
| 1.7 F1 指標單一權威 | `discipline` | `grep -n` 沒有唯一性／target-aware rc gate；`reconcile_stamps_check.sh` 只驗 stamp/hash | (c) `blocked-by: 既有工具沒有 target-aware 指標唯一性閘；新增跨 synth parser 會超出本輪禁止新腳本／不擴機制，純 grep 不能作 blocking gate` |
| 1.8 佔位宣稱收窄 | `discipline` | R3 只有文案／grep，未對 quoted/fenced 與 active skeleton 做反向 rc mutation | Q2 (a)；改成完整行＋scope＋雙向 mutation rc |

R4 後 1.1、1.2、1.3、1.4、1.5、1.6、1.8 均有 rc-based gate；1.7 保留具名 residual，不再假稱已機械化。

## 必答 4 — 改後 TODO 數量

改後為 **7 條，仍 ≤8**：保留 1.1–1.6、1.8 八個編號中的七項；1.1／1.2 只補既有 F2 測試的阻擋性 mutation，1.6 以 Q1(b) 取代，1.8 以 Q2(a) 取代。**砍掉 Task 1.7**，原因是它在現有工具集合下只能由跨 synth 的新 target-aware gate 才能證明「恰一權威」，而本輪硬約束禁止新腳本／擴建機制；殘留具名為上表的 `blocked-by:`，不以散文或「之後再說」帶過。沒有新增 epic、腳本或語意閘。

本輪不授權 SPLITUNIFY 生產碼；本文件只把 r4 consult 規格送入收斂。下一步若通過 r4 reconcile，仍須依 r3 已定案的實作條件、白話審閱與三家審碼戳記流程辦理。

ASSUMPTIONS_VERIFIED: r3 synth `reconcile_stamps_check.sh` 實跑 PASS；R3 consult P0/P1 與 `**碼證**` 之 corpus replay 實跑為 15/15 缺 exact `CODE-ANCHOR:`、R3 stamp 為 0/0；現行 parser／placeholder／Task 表以 `nl -ba`、`rg`、`grep -Ec` 讀取核對；R4 提案本身未宣稱已落地。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` → PASS；corpus count command → codex 7/7、composer 2/2、grok 6/6 reject，三份 stamp 0/0；`bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r4-codex.md --family codex` → PASS rc=0；本輪未跑 pytest，因禁改碼且尚未有 R4 implementation mutation。
FAILURES_SEEN: 一次只讀檔案清單命令被 PreToolUse 以 open-debt dispatch gate 拒絕，未改檔；其餘讀取與計數探查完成。
SCOPE_CHANGES: 只新增本指定 consult 交件檔；未改 scripts、templates、tests、data_cache 或根 `HANDOFF.md`；既有 dirty worktree 保留。
NUMERIC_OR_SCHEMA_IMPACT: none；15/15、0/0 僅為交件格式 replay 計數，未改生產輸出、數值或 schema。
OUTPUT_PATH: `handoffs/20260912-docrot-x-consult-r4-codex.md`
TMP_CLEANUP: `/private/tmp/govb1-r6-wt-vg29wmts`、`/private/tmp/govb1-r7-wt-i8sa38b8` 已移入 `/private/tmp/.Trash/docrot-r4-cleanup/`；`/private/tmp/claude-501` 已確認保留。

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
