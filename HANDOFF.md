# Handoff

REF:handoffs/reconcile/20260810-govb1-b10-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b9-review-r1/synth.md
REF:handoffs/reconcile/20260810-govb1-b8-review-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b7-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## 🔴 接手第一件事：**殘留票 `B-48`／`B-49`／`B-50`／`B-51`／`B-52`／`B-53`**

第 1 批（B7／B8／B9／B10）**四票全數收案並 push**。GOVB0 的 B4/B5/B6/B7 未開工。

| 票 | 內容 |
|---|---|
| `B-53` | **新立**。主委自產 findings 的 **fail-closed** 強制路徑；現況只有產出端早期警告（PostToolUse，寫入後才跑、Bash 重導不觸發）。🔴 在它落地前，`票 B-31` 對外**不得說「強制」**，只能說「產出端已有檢查點」。兩家在 B10 stamp-r1 逐一否決了四個替代方案（見該收斂檔 C4） |
| `B-52` | `govflow_lifecycle.json` 說 stamp 輪 `no_findings_format_gate`，`debt_clear.sh` 卻照跑 ⇒ SoT 與實作漂移。**本 session 三次銷帳皆 rc=0 未觸發**——症狀只在產出**完全沒有** canonical sentinel 時才出現 |
| `B-51` | OOE 偏離凍結文件須先取得裁決才動碼；🔴 尚無機械強制點 |
| `B-48` | `debt_clear --abandon --kind` 不查核事實 |
| `B-49` | roles SoT 表達不了「編排端自任實作」；修它須動 `_B45_HARNESS` ⇒ 凍結期做不到 |
| `B-50` | 執行端曾把工作區留在壞狀態且無機制通知 |
| `B-29` | `REF:` 是否已戳記靠委員自覺 ⇒ 應在**發 token 前**機械驗 |
| `R-15` | `scripts/governance_families.json` 不可 commit ⇒ ambient M |
| — | `docs/ROADMAP.md` 不在 manifest ⇒ 更新須走 OOE；本 session 未更新 |
| — | `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit |

## ✅ 本 session 已收案（測試 1129 → **1261**）

| 票 | commit | 狀態 |
|---|---|---|
| **B7** claude 段收窄 | `a5ddf05` OOE | 兩家 APPROVED |
| **B8** findings-kind 判準 | `52c4a1a` `4a9de37` OOE `b6a9da2` | 兩家 APPROVED |
| **B9** 零 findings 單一契約 | `39037f5` `be9fda0` | 兩家 APPROVED |
| **B10** `票 B-31` 補救層＋三件移交 | `f674cb73` `53d83dbf` OOE `9e35f159` | 兩家 APPROVED、**裁 (A) 可收案** |

## 🔴 未修的活缺口（不是待辦，是現在就成立的洞）

`gate_check` 對下列**真派工**放行（三版對照確認非本次引入）：
process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c`
⇒ 歸 **GOVB0 B4**（`Task 2.3`／`2.4`），與 `Task 2.2` 同檔同段須同批做。
`CODEX-R8-P1-03`：B3R 的 **O(n) scanner 未交付** ⇒ 不得宣稱 B3R 已達標。歸 GOVB0。

## ⚠ 踩過就別再踩

- 🔴 **修一條 finding ≠ 修一個類別**。r1 判我「源碼斷言冒充端到端」，我修好那一格，
  同一批新增裡又放兩條同型的（兩家都沒抓到，我自己發現）。收窄型修補**必回頭掃同型**。
- 🔴 **「委員當場驗過」≠「以後改壞會被抓」**：臨時探針必須落成常駐測試，否則保護期只有那一輪。
- 🔴 **`cx_run.sh` 被 `_B45_HARNESS` 逐字錨定**（函式本體、`bash "${_cc}" --single …`、
  呼叫點 `_fmt_rc="$(...)"`）。新增一律加**錨點外側**；要傳值走 bash **動態作用域**。
  `--selfcheck` 因此把 `_emit_fixup_list` **定義**上移檔頭（本體與呼叫點字面不變，g6 rc=0）。
- 🔴 **同一檔第二次 OOE 改動極易漏 `Governance-Scope:` trailer**。收尾必跑
  `bash scripts/govb1_final_gate.sh --only g7`；未推前 `git commit --amend` 補即可。
- 🔴 **`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc**——本 session 又犯一次（`plain_docs_sync_check`）。
- 🔴 **stamp／review brief 必須硬性要求 canonical heading ＋ sentinel body 非空**，否則銷帳鎖死。
- 🔴 **「現跑導出」的量測必須附輸入集合指紋**（`handoffs/` 每輪都在長，三方會量到三個分母）。
- 🔴 **改檔一律用 Edit/Write**；`jq` 的 `//` 把 `false` 當空值；`grep` 互動 shell 是 ugrep、腳本是 BSD。
- 銷帳前先確認 `sources.lock` 是 **review 模式**（`--mode review --rebuild` 就地升級，
  該路徑在 `reconcile_build.sh:238` 即 exit，**不動 synth**——我讀過並先備份才跑）。
- 收斂檔**被 REJECTED 者須修訂本體並重蓋新 hash**；`grok` 額度封鎖 ⇒ `active_stampers=["codex","composer"]`。
