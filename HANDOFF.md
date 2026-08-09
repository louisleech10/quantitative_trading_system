# Handoff

REF:handoffs/reconcile/20260809-govb1-b7-review-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b7-consult-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b3-review-r8/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## 🔴 接手第一件事：**B8 實作**（Task 4.1 / `票 B-38`）

**使用者已定路線，不得再開順序討論**（2026-08-09 原話：「順序排了就排了…不如趕快照現在的路線做完」）：
**B8 → B9 → B10 → 殘留票**。B8 是 B9 的前置（4.2 消費 4.1 的判準），順序本就正確。

- **B8**＝Task 4.1，新建 `scripts/findings_kind_classify.sh` ＋
  `tests/governance/test_govb1_findings_kind.py` ＋ `test_govb1_zeroid_no_regression.py`。
  三檔**都在 manifest allow 內 ⇒ 一般 commit，不必 OOE**。
  🔴 `G-1 全域禁令`：不得使 `C-2` 表中期望 `rc==0` 之列變非 0；**改判不在本批**。
  🔴 誤擋率 receipt 必附（分母 >100 ⇒ 抽 ≥100 ＋ Wilson CI）；mutation 必附。
- **B9**＝Task 4.2（`govflow_lifecycle.json` 加 `zero_findings_contract` 節，append-only）
- **B10**＝Task 4.3（`cx_run.sh` `format-failed` 補救層）

🔴 **B9／B10 的優先序已實證上升**：本 session 兩輪 stamp 都因產出格式不合規而**銷帳鎖死**
（詳見 `票 B-52`）。它們不是補強，是本 epic 自己正在踩的坑。

## ✅ 本 session 已收案

| 項 | commit | 狀態 |
|---|---|---|
| **B7**（`claude` 段收窄；`票 B-26` 重號一併結清 `GOVB0 Task 2.2`） | `a5ddf05`（OOE） | 兩家 APPROVED；`g7` PASS；測試 1143→**1151** |

三輪收斂：review-r1（7 findings）→ stamp-r1（8 findings，codex REJECTED）→ stamp-r2（兩家 APPROVED）。
逐條處置見收斂檔 C1–C8。**主委被抓到兩件，已具名不淡化**：
① 初版引入真回歸（`$(printf claude) -p x`／`claude${IFS}-p x`，舊式子字串是「偶然」擋住的）
② 宣稱勘誤層「可證偽」但當時是空的——codex 用假勘誤證明全綠；修法＝`kind` 由 `from/to` 導出。

## 🔴 未修的活缺口（**不是待辦清單，是現在就成立的洞**）

`gate_check` 對下列**真派工**一律**放行**（三版對照確認皆非本次引入）：

```
bash scripts/gate.sh <(<家族> exec hi)  /  >(…)     ← process substitution
echo x | xargs -n 1 <家族> exec hi  /  -I{}          ← wrapper
env FOO=bar <家族> exec hi   /   FOO="$HOME" <家族> exec hi
/bin/bash -c '<家族> exec hi'                        ← 絕對路徑
```

歸屬＝**GOVB0 B4**（`Task 2.3`／`2.4`），與 `Task 2.2` 同檔同段、TODO §B 明載**須同批做**。
複驗腳本：`.claude/tmp/r8_p0_probe.sh`（🔴 只餵字串給閘判定，**不執行派工**）。

另 **B7 明文不受理**（`docs/GOV_B7_SCOPE_AMENDMENT.md` §7.1，兩家 APPROVED）：
`$(printf clau)de -p x`（替換輸出串接）與 `* -p x`（glob 求值）——argv[0] 靜態不可判，
依「擋意外不防蓄意」列為**邊界**。要擋只能執行前解析 argv[0]，是另一種機制。

另：`CODEX-R8-P1-03` — B3R 的 **O(n) scanner 未交付**（quoted 500K `timeout 20 → rc=124`）
⇒ **不得宣稱 B3R 已達標**。歸 GOVB0。

## 🔴 待辦與具名殘留

| 代號 | 內容 |
|---|---|
| — | **B8–B10 未開工**；**GOVB0 B4／B5／B6／B7 未開工**（第 0 批剩餘） |
| `B-52` | 🔴 **新**：`govflow_lifecycle.json` 說 stamp 輪 `produces_findings:false`／銷帳 `no_findings_format_gate`，但 `debt_clear.sh` **照跑該閘** ⇒ SoT 與實作漂移。本 session **連兩輪**因此銷帳鎖死，只能 `--abandon --kind collection-failed`（理由欄逐字記實情，**未**謊稱無 findings）。且「stamp 不產生 findings」本身是錯的。歸 B9＋B10 |
| `B-51` | 🔴 **新**：OOE 偏離凍結文件**須先取得裁決才動碼**；本輪主委違反此序（兩家指出，已接受）。🔴 該規則**尚無機械強制點**，依「工具必須自帶強制機制」須另立閘，不得只寫文件 |
| `B-48` | `debt_clear --abandon --kind` **不查核事實**（本 session 再用 2 次，皆 `collection-failed` 且理由屬實） |
| `B-49` | roles SoT 表達不了「編排端自任實作」；修它須動 `_B45_HARNESS` ⇒ 凍結期間做不到，解凍即紅 |
| `B-50` | 執行端曾把工作區留在壞狀態且無機制通知 |
| `B-29` | `REF:` 是否已戳記**靠委員自覺去驗** ⇒ 應在**發 token 前**機械驗完 |
| `R-15` | `scripts/governance_families.json` **不可 commit** ⇒ 走 ambient M |
| — | `docs/ROADMAP.md` 不在 manifest ⇒ epic 期間更新須走 OOE；本 session 未更新 |
| — | `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` **不得 commit** |

## ⚠ 踩過就別再踩（本 session 新增）

- 🔴 **stamp 輪派工單必須硬性要求 canonical `## <FAMILY>-R<n>-P<0-3>-<NN>` heading
  ＋ sentinel body 須含 `**斷言**`／`**碼證**`**。少任一項 ⇒ completeness 判 vacuous／empty-shell
  ⇒ 銷帳鎖死。本 session 連兩輪栽在這裡（第二輪是我以為修好之後又栽的）。
- 🔴 **收窄型修法必先做三版對照**（`pre-phase2` ／ `HEAD` ／工作區）。
  「舊規則偶然擋住某形態」是真實現象——只看新規則對不對，會漏掉自己造成的回歸。
  工具：`.claude/tmp/b7_regress_probe.py`（現在會以非零 rc 表達失敗）。
- 🔴 **`grep` 在互動 shell 是 Claude Code shell-snapshot 的 function（ugrep）**，
  但腳本經 `bash` 取到的是 `/usr/bin/grep`（BSD）。驗 gate 行為時別被 `grep --version` 誤導。
- 🔴 **自己寫的 fail-closed 網會擋到自己**：含 `.claude/` 路徑 ＋ `$` ＋ `-p` 的指令會被判 dispatch。
  已於 stamp-r1 收窄為「命令位置 token 含 metachar」才觸發，但仍可能撞到。
- 🔴 **改檔一律用 Edit/Write**；本 session 又用了一次 `cat >> <<'EOF'` heredoc（違反 CLAUDE.md）。
- `cmd | tail; echo rc=$?` 讀到的是 **tail 的 rc**。
- `cx_run.sh` **不可直呼**；一律走 `committee_run.sh --session … -- <gate flags>`。
- session 名須 `<日期>-<epic>-<batch>-<kind>-r<N>`，`kind` ∈ {impl,review,stamp,consult,fix}。
- 收斂檔須先 `printf '\n## 戳記\n\n' >>` 才算得出 body hash；**被 REJECTED 者須修訂本體並重蓋新 hash**。
- `grok` 額度封鎖 ⇒ `active_stampers=["codex","composer"]`，2/2 即滿足。
