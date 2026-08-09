# Handoff

REF:handoffs/reconcile/20260809-govb1-b7-review-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b7-consult-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b3-review-r8/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。
（`20260810-govb1-b8-review-r1/synth.md` **尚未戳記**，故不得列入 REF。）

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## 🔴 接手第一件事：**B8 收尾**（stamp 輪）

B8（Task 4.1）**實作與 r1 修補都已 commit**，只差**戳記輪**：

1. 對 `handoffs/reconcile/20260810-govb1-b8-review-r1/synth.md` 補 `## 戳記` 區、算 body hash
   （`printf '\n## 戳記\n\n' >>` 後跑 `reconcile_body_hash.sh`）
2. 派 stamp 輪（codex+composer），必答＝**§B8 逐條關閉複驗** ＋ **receipt r2 的非實作者複核**
   （r1 只複核了 r2 之前的版本；r2 新增 4 個導出檔未經複核）
3. 🔴 **stamp brief 必須硬性要求 canonical `## <FAMILY>-R<n>-P<0-3>-<NN>` heading
   ＋ sentinel body 含 `**斷言**`／`**碼證**` 且非空**——本 session 連兩輪栽在這裡（`票 B-52`）

之後：**B9 → B10 → 殘留票**（使用者已定路線，不得再開順序討論）。
🔴 **B9／B10 優先序已實證上升**：本 session 三輪 stamp／review 因產出格式不合規銷帳鎖死。
🔴 **B10 必須接手 B8 的 `cx_run` 第三欄**（兩家一致移交）——
`test_cxrun_column_is_blocked_not_passing` 是逼債條款，B10 一加保留輸出的 stub 模式它就會紅。

## ✅ 本 session 已收案

| 項 | commit | 狀態 |
|---|---|---|
| **B7**（`claude` 段收窄；`票 B-26` 一併結清 `GOVB0 Task 2.2`） | `a5ddf05` OOE | 兩家 APPROVED（三輪）；已 push |
| **B8**（Task 4.1 findings-kind 判準） | `52c4a1a` `4a9de37` OOE `b6a9da2` | r1 十條全修；**待戳記** |

測試 1129 → **1196**。

## 🔴 本 session 主委被抓到的（不淡化，供接手者引以為戒）

1. **B7 初版引入真回歸**——舊式子字串比對是「偶然」擋住 `$(printf claude) -p x` 的。
   ⇒ **收窄型修法必先做三版對照**（`pre-phase2`／`HEAD`／工作區），工具 `.claude/tmp/b7_regress_probe.py`。
2. **宣稱勘誤層「可證偽」但當時是空的**——codex 用假勘誤證明全綠。
   ⇒ 修法不是加驗證，是**取消宣告**（欄位改為導出）。
3. **用程序當藉口少做一半**——B8 覆蓋率我知道能改善卻沒做，理由是「`票 B-51` 說要先取得裁決」。
   composer 判**是**。⇒ `票 B-51` 是「**先問再做**」，不是「**問了就可以不做**」。
4. **手搓測試資料造成假看守**——三格全 rc=1 看似有檢查，其實是資料結構性壞掉，與輸入無關。
5. **唯讀檔 guard 只看工作樹** ⇒「先 commit 再宣稱沒改」可矇混；改用 epic base 又會**把別票改動算到本票**。

## 🔴 未修的活缺口（不是待辦，是現在就成立的洞）

`gate_check` 對下列**真派工**放行（三版對照確認非本次引入）：
process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c`
⇒ 歸 **GOVB0 B4**（`Task 2.3`／`2.4`），與 `Task 2.2` 同檔同段須同批做。

B7 **明文不受理**（延伸檔 §7.1，兩家 APPROVED）：`$(printf clau)de -p x`、`* -p x`
——argv[0] 靜態不可判，依「擋意外不防蓄意」列為邊界。

`CODEX-R8-P1-03`：B3R 的 **O(n) scanner 未交付** ⇒ 不得宣稱 B3R 已達標。歸 GOVB0。

## 🔴 待辦與具名殘留

| 代號 | 內容 |
|---|---|
| — | **B8 戳記輪**；**B9／B10 未開工**；**GOVB0 B4/B5/B6/B7 未開工** |
| `B-52` | `govflow_lifecycle.json` 說 stamp 輪 `produces_findings:false`／銷帳 `no_findings_format_gate`，但 `debt_clear.sh` **照跑該閘** ⇒ SoT 與實作漂移。本 session **三次**因產出格式不合規只能 `--abandon --kind collection-failed`（理由屬實，**未**謊稱無 findings）。歸 B9＋B10 |
| `B-51` | OOE 偏離凍結文件**須先取得裁決才動碼**；🔴 尚無機械強制點，須另立閘 |
| `B-48` | `debt_clear --abandon --kind` 不查核事實（本 session 再用 3 次） |
| `B-49` | roles SoT 表達不了「編排端自任實作」；修它須動 `_B45_HARNESS` ⇒ 凍結期做不到 |
| `B-50` | 執行端曾把工作區留在壞狀態且無機制通知 |
| `B-29` | `REF:` 是否已戳記靠委員自覺 ⇒ 應在**發 token 前**機械驗 |
| `R-15` | `scripts/governance_families.json` 不可 commit ⇒ ambient M |
| — | `docs/ROADMAP.md` 不在 manifest ⇒ 更新須走 OOE；本 session 未更新 |
| — | `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit |

## ⚠ 踩過就別再踩

- 🔴 **stamp／review brief 必須硬性要求 canonical heading ＋ sentinel body 非空**，否則銷帳鎖死。
- 🔴 **「現跑導出」的量測必須附輸入集合指紋**——`handoffs/` 每輪都在長，
  三方會量到三個不同分母（實際發生：2960／2958／2956）。
- 🔴 **凍結 TODO 的參考程式碼不可逐字照抄**：本 session 抓到 4 處會壞的
  （`${ROOT}` 未定義、欄位名錯、`jq //` 對 `false`、`grep -qx` 全等造成漏放）。
- 🔴 `jq` 的 `//` **把 `false` 視同空值**（`jq -n 'false // "u"'` → `"u"`）。
- 🔴 `grep` 在互動 shell 是 shell-snapshot 的 function（ugrep），腳本經 `bash` 取到的是
  `/usr/bin/grep`（BSD）。驗 gate 行為別被 `grep --version` 誤導。
- 🔴 **改檔一律用 Edit/Write**；本 session 又犯一次 heredoc。
- `cmd | tail; echo rc=$?` 讀到的是 **tail 的 rc**。
- `cx_run.sh` 不可直呼；走 `committee_run.sh --session … -- <gate flags>`。
- 收斂檔**被 REJECTED 者須修訂本體並重蓋新 hash**（舊 hash 戳記自動失效）。
- `grok` 額度封鎖 ⇒ `active_stampers=["codex","composer"]`，2/2 即滿足。
