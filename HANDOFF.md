# Handoff

REF:handoffs/reconcile/20260809-govb1-b3-review-r8/synth.md
REF:handoffs/reconcile/20260809-govb1-b7-consult-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b3-review-r7/synth.md
REF:handoffs/reconcile/20260809-govb1-b6-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。
（本 session 因違反此條而**整輪作廢**一次：r7 的 REF 列了未戳記檔，codex 正確 BLOCKED。）

**Agent**: Claude(Opus 5) | **Time**: 2026-08-09 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## 🔴 接手第一件事：**B7 實作**（Task 3.2 / `票 B-15`）

**使用者已定路線，不得再開順序討論**（2026-08-09 原話：「順序排了就排了，改順序如果又要
消耗一堆時間和 token 跟流程，不如趕快照現在的路線做完」）：
**B7 → B8 → B9 → B10 → `票 B-48`／`B-49`／`B-50`**。

- **B7**＝Task 3.2「`claude` 段收窄」。🔴 **改 `scripts/_gate_lex.sh`**（非 TODO 寫的
  `gate_check.sh`——該檔 `:116` 自承詞法已移出；consult-r1 兩家裁定 (A)）。
  現況：`_gate_lex_match_scan()` 用 `grep -Eq 'claude[^|]*(-p|--print)'` **子字串比對**。
  修法＝`claude` 須在命令位置 ＋ `-p`／`--print` 須為獨立 token。
  🔴 **同一件工作在 `GOVB0 Task 2.2` 也有編號**（重號，與 `票 B-26` 同型）——做之前先看該處。
- **B8**＝Task 4.1（新建 `scripts/findings_kind_classify.sh`）
- **B9**＝Task 4.2（改 `scripts/govflow_lifecycle.json`）
- **B10**＝Task 4.3（改 `scripts/cx_run.sh`）
  三者皆**不碰詞法檔**、皆在 manifest allow 內 ⇒ 一般 commit。

## ✅ 本 session 已收案

| 項 | commit | 狀態 |
|---|---|---|
| **B6**（`票 B-25` 事實單一來源） | `11ea47a` `030c9cf` `266e6b8` `87aeb8c` | 兩家戳記 APPROVED；測試 50→56；已 push |
| **B3R 詞法層落地**（151 行生產碼進版控） | `a1a95cc`（OOE） | r8 兩家 APPROVED；解除「本機/CI 兩套詞法」 |
| **self-gate 換行旁路 P0** | `e7be91f`（OOE） | 9 條回歸（含承重 mutation） |

## 🔴 未修的活缺口（**不是待辦清單，是現在就成立的洞**）

`gate_check` 對下列**真派工**一律**放行**（主委實測，HEAD 與工作區判定相同 ⇒ 既有缺口非回歸）：

```
bash scripts/gate.sh <(<家族> exec hi)      >(…)          ← process substitution
echo x | xargs -n 1 <家族> exec hi          -I{}          ← wrapper
env FOO=bar <家族> exec hi
FOO="$HOME" <家族> exec hi                                ← 動態賦值（靜態 FOO="bar" 會擋）
/bin/bash -c '<家族> exec hi'                             ← 絕對路徑（相對 bash -c 會擋）
```

歸屬＝**GOVB0 B4**（`Task 2.3` 家族名 basename 化／`Task 2.4` 官方外層腳本呼叫點），
與 `Task 2.2` 同檔同段、TODO §B 明載**須同批做**。複驗腳本：`.claude/tmp/r8_p0_probe.sh`
（🔴 只餵字串給閘判定，**不執行派工**）。

另：`CODEX-R8-P1-03` — B3R 的 **O(n) scanner 未交付**，quoted 500K `timeout 20 → rc=124`
（SPEC C-5 要求 <5s）⇒ **不得宣稱 B3R 已達標**。歸 GOVB0。

## 🔴 待辦與具名殘留

| 代號 | 內容 |
|---|---|
| — | **B7–B10 未開工**；**B4 階段 2** scope 錯配須另立票 |
| — | **GOVB0 B4／B5／B6／B7 未開工**（第 0 批剩餘；B4 依賴已落地的 B3R） |
| `B-48` | `debt_clear --abandon --kind` **不查核事實**。🔴 **本 session 主委用了 3 次**（戳記輪產出無 canonical ID，正規路 vacuous）⇒ 發生率正在升 |
| `B-49` | roles SoT 表達不了「編排端自任實作」＋ `test_stamp_taskid_inject.py:769` 靜默 skip。**修它須動 `_B45_HARNESS` ⇒ 凍結期間做不到**；🔴 解凍即紅（定時炸彈） |
| `B-50` | 執行端曾兩次把工作區留在壞狀態且無機制通知（本 session 兩家皆正確還原） |
| `B-29` | 🔴 **新**：`REF:` 是否已戳記**靠委員自覺去驗**（codex 驗了、composer 沒驗）⇒ 應在**發 token 前**機械驗完。歸屬經 codex 更正為 `B-29`（非 `B-38`） |
| `B-26` | 🔴 **新**：`GOVB0 Task 2.2` 與 `GOVB1 Task 3.2` 是同一件工作的兩個編號 |
| `R-15` | `scripts/governance_families.json` **不可 commit** ⇒ 走 ambient M |
| — | `docs/ROADMAP.md` 不在 manifest ⇒ epic 期間更新須走 OOE；本 session 未更新 |
| — | `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` **不得 commit** |

## ⚠ 踩過就別再踩（本 session 新增）

- 🔴 **排序原則＝淨摩擦公式**（`handoffs/20260801-GOV-AMEND-BACKLOG.md:34`），**不是批號**。
  主委本 session 一路照批號走，被使用者當場指出。使用者已定：**現階段照現行路線做完，不再改序**。
- `manifest` 的 `allow` ≡ **凍結 TODO 宣告集的機械鏡像**；加列＝聲稱 TODO 宣告過 ⇒ 7 條測試立刻紅。
  凍結 TODO 沒宣告的路徑，唯一通道是 `Governance-Scope: out-of-epic`。
- `cmd | tail; echo rc=$?` 讀到的是 **tail 的 rc**——本 session 又犯一次。
- `cx_run.sh` **不可直呼**（缺 `ROUND_ID`）；一律走 `committee_run.sh --session … -- <gate flags>`。
- session 名須 `<日期>-<epic>-<batch>-<kind>-r<N>`，`batch`＝`b<數字>`或`x`，
  `kind` ∈ {impl,review,stamp,consult,fix}。寫 `b3r-close` 會被 fail-closed 擋下。
- `reconcile_build` 的 `sources.lock` 預設 `mode=discovery`；`debt_clear` 要 `review`
  ⇒ 先 `reconcile_build <session> --mode review --rebuild`（**不得再帶委員檔**）。
- 收斂檔須先 `printf '\n## 戳記\n\n' >>` 才算得出 body hash；戳記後須
  `gate.sh register-output <task> <reconcile檔>` 否則 provenance 永遠 pending。
- 🔴 **改檔一律用 Edit/Write**；本 session 用 `cat >> …<<'EOF'` heredoc 被派工閘擋下一次。
- `grok` 403 ⇒ `active_stampers=["codex","composer"]`，2/2 即滿足。
