# DOCROT R2 — COMPOSER（審主委第二版裁定）

task-id: 20260912-DOCROT-X-CONSULT-R2  
family: COMPOSER  
brief: `handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md`  
findings-round: R2

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 | 否證／碼證 |
|---|---|---|
| 「掛進既有 PostToolUse 鏈」≠「擴建治理工具」 | **不成立** | 新增 F1–F3 判定仍須新腳本或改 `narrow_check_router.sh` 對照表；`list_active_mechanisms.sh` 單次 **2.92s**，整鏈 **4.39s**（見 COMPOSER-R2-P1-03）——與新建 `decision_coverage_check.sh` 維護成本同型 |
| grok F1–F3 在**無 registry** 下可實作 | **不成立** | F3 須知「哪個 token 代表哪個決定」；實跑活文 `Task 9.2b` **13** 次、`validate_split_pair_integrity` **8** 次（見 COMPOSER-R2-P0-01） |
| 主委第二版折衷可執行 | **不成立** | 採 grok「零維護」又拒 composer YAML ⇒ F3 無決定→token 映射；採 composer「寫檔當下強制」卻掛 `Edit\|Write` ⇒ Bash 生成繞過（見 COMPOSER-R2-P0-02） |
| codex 第②條（審查輸入隔離）已被裁定涵蓋 | **不成立** | `synth.md` L29 與 `HANDOFF.md` L32 全文無「當前段落＋本輪 diff」；R1 D2 處置寫「一併採納」但未進第二版裁定正文 |

fact-verified: R1 三家立場 → `handoffs/20260912-docrot-x-consult-r1-{codex,composer,grok}.md`  
fact-verified: 第二版裁定 → `handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` L29；`HANDOFF.md` L32  
fact-verified: PostToolUse 八支 doc hook → `.claude/settings.json` L188–223

---

## 必答 1 — 第二版裁定可不可行（含 F3 實作或不可行證明）

**立場：不可行。** 判定與強制掛載點互斥，F3 在無 registry 下無法定義「單一決定」。

**F3 具體實作嘗試（無 registry，照裁定字面）**：

```bash
# 假設「決定」= grok 範例 Task 9.2b（腳本內硬編碼——這已是隱式 registry）
SPEC=docs/SPLITUNIFY_SPEC.D-002.md
LIVE=$(awk '/HISTORY-BEGIN/{p=1} p&&/HISTORY-END/{p=0;next} !p' "$SPEC")
echo "$LIVE" | rg -c 'Task 9\.2b'          # → 13（門檻 ≤3 ⇒ FAIL）
echo "$LIVE" | rg -c 'validate_split_pair_integrity'  # → 8（若把此當同一決定仍 FAIL）
```

**不可行論證**：F3 要求「**單一**決定活文 ≤3」，必先回答「哪些行屬同一決定、用哪個 grep token 計數」。無 YAML／無腳本內 token 表 ⇒ 閘只能 (a) 數所有 `Task 9.x` 引用（`Task 9.3` 活文 **23** 次——含交叉引用非複述）或 (b) 漏掉 `metadata.split_unify`（**11** 次）等未冠以 Task 號的決定。兩者皆不能收斂 R12 O3 型互斥。

**照第二版做會在哪一步失敗**：實作者改 `narrow_check_router.sh` 加 F3 → 需列出決定 token 表（= composer R1 YAML 的內聯版）→ 主委以「不建 registry」拒絕 → F3 無法上線；若硬上單一 `Task 9.2b` 計數，其餘 30+ 決定表面仍 >3，或誤擋合法交叉引用。

**F1/F2 現況基線**（裁定要求與現狀差距）：活文（去 HISTORY）`vN` 類標記 **41** 處；`[0-9]+ 條` 字面 **27** 處——皆未達 F1 歸零／F2 恰一處。

---

## 必答 2 — 我 R1 主張是否修正

**部分修正，核心不變。**

| R1 主張 | R2 後立場 | 理由 |
|---|---|---|
| P0：YAML + `decision_coverage_check.sh` | **仍堅持**（F3 必要條件） | 第二版裁定自證：砍 YAML 後 F3 無法定義決定邊界（P0-01） |
| 掛 PostToolUse 強制 | **改為「必要但不充分」** | 須擴到 commit/dispatch/Bash 邊界（codex ①③）；僅 Edit\|Write 不足 |
| 停輪判準寫 ROADMAP | **仍採** | 與裁定無衝突 |
| grok「不建任何工具」 | **反對仍成立** | 第二版已把 composer 強制掛進八支鏈——實質新建判定邏輯，grok 反對已被主委覆寫 |

**codex 第②條**：R1 我未單獨列 P0；R2 **升格為優先於 F1–F3**——成本最低、直接對症「新一輪又看到前幾輪修完的文字」，且不需文件結構改造。

---

## 必答 3 — PostToolUse 鏈成本（可量測）

| 腳本 | real (s) | 備註 |
|---|---|---|
| `obligation_block_check.sh` | 1.31 | SPEC 專用 |
| `list_active_mechanisms.sh --hook` | 2.92 | 每次 Edit\|Write 皆跑 |
| `doc_format_precheck.sh` | 0.07 | |
| 其餘六支合計 | ~0.18 | |
| **八支串跑總計** | **4.39** | 每次寫檔一次 |

**量測命令**：

```bash
/usr/bin/time -p bash -c 'for s in doc_format_precheck.sh plain_docs_order_check.sh obligation_block_check.sh factkey_write_guard.sh list_active_mechanisms.sh narrow_check_router.sh spec_xref_hook.sh synth_attribution_hook.sh; do bash scripts/$s docs/SPLITUNIFY_SPEC.D-002.md >/dev/null 2>&1; done'
```

**誤擋風險**：F1「活文版本標記歸零」若全域套用，`handoffs/` 與 `synth.md` 的審計敘事含 `v13`／輪次——brief 自身即含版本語境；F2「數字恰一處」對多決定 SPEC 在修復前必紅（現 **27** 處）。**未評估的路徑排除**：`narrow_check_router.sh` L36 明載 Bash 重導不觸發。

---

## 必答 4 — 第四條路（三家與主委皆未寫清）

**兩階段窄方案**（我 R1 未寫、主委未採、codex ② 單獨可成首階）：

1. **Phase A（零新腳本）**：派工 brief 強制 `review_scope: <檔>:<行範圍>` + `git diff <base>..HEAD -- <檔>`；`completeness_check` 拒收 source anchor 落在 `HISTORY-BEGIN/END` 或非 diff 區段之 finding。成本＝改 brief 範本 + 一條 grep 驗證，不碰 SPEC 結構。
2. **Phase B（最小機械）**：僅對 `docs/SPLITUNIFY_SPEC.D-002.md` 建 **單檔** `decisions` 段（非全庫 YAML epic）——每決定一行 `id|pattern|max_live_hits`；掛 `narrow_check_router` 一列，不增第九支全域 hook。

成效判準：下一輪「上一版修法再審」占比；Phase A 單獨預期降 **30–50%**（R11–R12 全打自修之直接成因）。

---

## 必答 5 — 裁定程序怎麼改

**立場：第二版折衷不得由主委單方生效。**

| 現行缺陷 | 碼證 | 程序修法 |
|---|---|---|
| 主委自產版刻意不給三家（R1 已發生） | `synth.md` L9–11 | 任何路線裁定須先入 brief 供三家 `--single` 審查一輪 |
| 第二版折衷無人審過 | 使用者當面質問；本輪 task 存在 | 裁定文字視同 SPEC 草案：`reconcile` session + `completeness_check --lock` |
| 裁定本身複述兩處 | `HANDOFF.md` L32 + `synth.md` L29 同段「新裁定＝兩家各取一半」 | 裁定只寫 `synth.md`；HANDOFF 改 `見 reconcile/.../synth.md#路線裁定` |

---

## 必答 6 — 是否不值得做

**不值得全做第二版裁定；值得做子集。**

| 做法 | 值得？ | 判準 |
|---|---|---|
| F1–F3 無 registry 硬上 PostToolUse | **不值得** | 實作卡在 P0-01；投入後 F3 仍假綠 |
| 僅 codex ② 審查輸入隔離 | **值得** | 下一輪同型「考古再審」finding 占比 |
| 完整 composer YAML + 產出端 equality | **值得但延後** | 若下一票「改一處漏一處」占比未降（HANDOFF L33 成效條款） |
| 接受矛盾、只靠審查抓 | **不建議** | R12 已證三閘同綠仍互斥；無機械背書等於重複 R1–R12 |

---

## COMPOSER-R2-P0-01

**斷言**: 第二版裁定之 F3（單一決定活文計數 ≤3）在拒絕 composer YAML registry 後**無法實作**——閘無法得知「該數哪個 token 代表哪個決定」。

**碼證**: 活文（排除 `HISTORY-BEGIN/END`）計數：`Task 9.2b` **13**、`validate_split_pair_integrity` **8**、`metadata.split_unify` **11**；`Task 9.3` **23**。RECHECK: `awk '/HISTORY-BEGIN/{p=1} p&&/HISTORY-END/{p=0;next} !p' docs/SPLITUNIFY_SPEC.D-002.md | rg -o 'Task 9\.[0-9a-z]+|validate_split_pair_integrity|metadata\.split_unify' | sort | uniq -c | sort -rn | head -10`。隱式 registry 反例：腳本內硬編碼 `Task 9.2b` 仍 13>3。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[BLOCKING] 信心度=High。照裁定做會在「定義決定邊界」一步停滯。**修法**：F3 改為「每決定 `id` + `grep_patterns[]` + `max_hits`」機械表（composer R1 YAML 或 SPEC 內單檔表）；**可行性**：表驅動 rg 計數，R1 已論證；無表則 F3 必須降級為具名殘留。

---

## COMPOSER-R2-P0-02

**斷言**: 第二版裁定選擇的強制掛載點（`PostToolUse: Edit|Write`）**不涵蓋** Bash／生成器寫檔，與 codex R1 已證之產出端洞同型，強制力在實務路徑上為假。

**碼證**: `.claude/settings.json` L189 `matcher: Edit|Write`（doc 八支）；L180 僅 `ts_stamp` 含 `Bash`。`narrow_check_router.sh` L36：「經 Bash 重導…不觸發」。`reconcile_build.sh`／`committee_run.sh` 等產出 `synth.md` 典型走 Bash。RECHECK: `rg -n 'matcher' .claude/settings.json`；`sed -n '33,37p' scripts/narrow_check_router.sh`。

**來源摘要**: .claude/settings.json#77cb54336328;scripts/narrow_check_router.sh#61985829c6f4

[BLOCKING] 信心度=High。照裁定做：主委 `bash scripts/reconcile_build.sh` 寫 synth ⇒ F1–F3 **不跑**。**修法**：強制邊界改為 commit hook + `gate.sh register-output` + dispatch token 核發前；或 `Bash` matcher 增列 doc 檢查（成本見 P1-03）。

---

## COMPOSER-R2-P1-01

**斷言**: 第二版裁定「判定採 grok 零維護、強制採 composer」在邏輯上自相矛盾——零維護的 F3 需要決定→token 表，而該表正是 composer 所稱 registry。

**碼證**: `synth.md` L29 逐字「純計數，零維護，**不需** composer 之 YAML registry」且「強制…寫檔當下報」；同段 F3 要求「單一決定活文計數」。grok R1 F3 成效指標＝`Task 9.2b` 活文 ≤3（`synth.md` L151）——token 選擇本身即維護項。RECHECK: 對讀 L29 與 L151。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MAJOR] 信心度=High。**修法**：承認 F3 最小表為必要資料結構（可內嵌 `narrow_check_router` 路由表，不必獨立 epic）；刪「零維護」宣稱。

---

## COMPOSER-R2-P1-02

**斷言**: 主委第二版裁定**完全忽略** codex R1 第②條（審查輸入只餵當前段落＋本輪 diff），而該條可能是三家中成本最低且直接對應使用者「新一輪又看到前幾輪修完文字」的修法。

**碼證**: R1 codex P1-02 碼證：R11=12、R12=13 條全打前版修法；`synth.md` L16 D2 處置寫「codex 另主張…一併採納」但 L29 新裁定正文無輸入隔離。R12 synth：「十三條無一為新面向」。RECHECK: `rg '當前段落|本輪 diff|review command' handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md HANDOFF.md` → 裁定段 0 命中。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a;handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MAJOR] 信心度=High。會怎麼失敗：先上 F1–F3 花數週，考古再審占比不變。**修法**：必答 4 Phase A 先行；F1–F3 待 registry 就緒後再接。

---

## COMPOSER-R2-P1-03

**斷言**: 將 F1–F3 掛入既有八支 PostToolUse 鏈，每次 `Edit|Write` 增加 **~4.4s** 延遲（其中 `list_active_mechanisms.sh` 單支 **2.92s**），主委未評估對編修節奏的影響。

**碼證**: 見必答 3 量測表；`list_active_mechanisms.sh` 對任意 SPEC 路徑每次皆執行。再加 F1–F3 腳本預估 +0.5–2s（`obligation_block_check` 同型）。RECHECK: 必答 3 命令。

**來源摘要**: .claude/settings.json#77cb54336328

[MAJOR] 信心度=High。**修法**：F1–F3 只經 `narrow_check_router` 窄觸發 `docs/SPLITUNIFY_SPEC.D-002.md`；`list_active_mechanisms` 改 pre-commit 或降頻。**可行性**：路由器已存在，改表不增第九支全域 hook。

---

## COMPOSER-R2-P2-01

**斷言**: 第二版裁定記錄本身重犯 R1 主因——同一裁定複述於 `HANDOFF.md` 與 `synth.md` 兩處，無單一權威 anchor。

**碼證**: `HANDOFF.md` L32 與 `synth.md` L29 同段「新裁定＝兩家各取一半」；`rg -c '新裁定|兩家各取一半' HANDOFF.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → 各 **1**。RECHECK: 同上。

**來源摘要**: HANDOFF.md#1b24c621be54;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MINOR] 信心度=High。裁定程序病徵。**修法**：HANDOFF 只留指標；裁定正文僅 `synth.md` 路線段。

---

## COMPOSER-R2-P2-02

**斷言**: F3 門檻「≤3」為 grok R1 隨手範例（標題＋驗收＋mutation），未對 v13 之 30+ 決定面做分佈驗證，套用後必然大量誤擋或大量漏擋。

**碼證**: 活文 `Task 9.1` **14** 次、`M-SU-D2-04` **5** 次——皆 >3；若僅擋 `Task 9.2b`，其他決定仍複述 5–11 次（R1 量測）。grok R1 L151 成效指標未附抽樣 n 或允許列表。RECHECK: 必答 1 的 `uniq -c` 輸出。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-grok.md;docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24

[MINOR] 信心度=Medium。**修法**：先量測每決定活文分佈再定 `max_hits`；禁止全域常數 3。

---

## COMPOSER-R2-P3-01

**斷言**: 存在第四條路——**僅 codex ② 審查輸入隔離 + 單檔決定表**——可在不新開 epic、不掛全域第九 hook 下，先降「考古再審」占比，且與第二版裁定不衝突。

**碼證**: 必答 4 Phase A 無新腳本；Phase B 一列 `narrow_check_router` 路由。R12 停輪已觸發 ⇒ 規格審查應停，不應先上未驗證 F3。**修法**：下一張票驗收 Phase A；成效不達再啟 YAML（HANDOFF L33 成效條款）。**可行性**：brief 範本改動 + 既有路由器，本輪未跑 impl。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a;scripts/narrow_check_router.sh#61985829c6f4

[MINOR] 信心度=Medium。程序建議，非阻斷第二版本身。

---

ASSUMPTIONS_VERIFIED: brief §0 四條 assumed 均已用 shell 量測否證；PostToolUse 八支延遲、活文 token 計數、裁定複述、settings matcher 均已實跑  
TESTS_RUN: `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r2-composer.md --family composer`（交件前自檢）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R2-P0-01,COMPOSER-R2-P0-02,COMPOSER-R2-P1-01,COMPOSER-R2-P1-02  
CLOSED:  
STATUS: DONE
