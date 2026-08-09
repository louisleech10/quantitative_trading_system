# B7 — `claude` 段收窄：範圍延伸與具名偏離

> 凍結文件（`docs/GOVB0_FRICTION_TODO.md`、`docs/GOVB1_INPUT_QUALITY_TODO.md`／`_SPEC.md`）
> **不就地修改**；本檔為其延伸，記錄本次交付相對凍結宣告的每一處偏離與理由。
> 體例同 `docs/GOV_B6_SCOPE_AMENDMENT.md`。

- **標的**：`GOVB0 Task 2.2` ＝ `GOVB1 Task 3.2`（票 `B-26` 重號）
- **實作端**：主委自任　**審查**：codex ＋ composer（兩個非實作者家族）
- **日期**：2026-08-09

---

## §1 兩張票是同一件工作（票 `B-26`）

| | `GOVB0 Task 2.2` | `GOVB1 Task 3.2` |
|---|---|---|
| 目標 | `claude` 不再子字串比對；`-p`／`--print` 須為獨立引數 | `.claude/` 目錄與 scratchpad 路徑不再誤觸 |
| 宣告修改檔 | `scripts/gate_check.sh:86` 第二段 alternation | `scripts/gate_check.sh`（`claude` 段） |
| 實作要點 | ①命令位置＋路徑前綴 ②`-p`／`--print` 有詞界 ③移除 `[^|]*` | ①命令位置 ②`-p`／`--print` 獨立 token |

同一段程式碼、同一組實作要點、同一個 `票 B-15` 來源。**本次一份交付同時滿足兩張的驗收欄**
（`TEST-2.2-FP4`／`-TP`／`-PIPE`／`-REGRESS`／`-MUT` ＋ `T-3.2` 兩條 `ASSERT` ＋ 兩張的邊界欄），
`GOVB1 Task 3.2` 與 `GOVB0 Task 2.2` 一併結清，不另排一輪。

> `GOVB0 Task 2.2` 的驗收欄嚴格**涵蓋** `GOVB1 Task 3.2`（多了 `-PIPE`／`-REGRESS`／`-MUT`），
> 故以 GOVB0 版為準即可同時滿足兩者；反之不成立。

---

## §2 🔴 凍結 TODO 的一處**事實錯誤**：`TEST-2.2-PIPE` 的 from 態

`docs/GOVB0_FRICTION_TODO.md:362` 與其機械抽取產物
`tests/governance/fixtures/phase2_expected_flips.txt:26` 記載：

```
flip	TEST-2.2-PIPE	ALLOW	BLOCK	cat x | claude -p "y"
```

**實測否證 from 態**（receipt，`.claude/tmp/b7_baseline.sh` 對兩份 gate 各跑一次）：

| 受測 gate | 判定 |
|---|---|
| `tests/governance/fixtures/gate_check_pre_phase2/gate_check.sh`（TODO 撰寫時的基準） | **BLOCK** |
| `scripts/gate_check.sh` @ `0c094e5`（收窄前） | **BLOCK** |
| `scripts/gate_check.sh` @ 本次（收窄後） | **BLOCK** |

**成因**：舊式 `claude[^|]*(-p|--print)` 中的 `[^|]*` 限制的是 `claude` **右側**不得跨 `|`；
本例的 `|` 在 `claude` **左側**（`cat x | claude -p "y"`），子字串比對本來就命中。
撰寫 TODO 時把「`[^|]*` 不跨管線」誤推為「管線後的 claude 不被擋」。

**處置（r1 修訂後）**：`to` 態（BLOCK）未受影響。這條的正確 kind 是 `maintain` 而非 `flip`。

🔴 **初版處置被兩家共同否決**（`CODEX-R1-P1-04` P1 ＋ `COMPOSER-R1-P2-02`）：
初版只把更正寫進本延伸檔與測試 docstring，**機械可讀的 fixture 仍留著錯誤**
⇒ 抽取器、oracle、矩陣工具照樣拿到錯的 from 態。
「錯誤留在機器可讀層、更正只存在於人類可讀層」不算修好。

**改採機器可讀勘誤層**：新增 `tests/governance/fixtures/phase2_flips_errata.tsv`，
由 `extract_phase2_expected_flips.py` 在**抽取出口**套用，覆寫該列的 `kind`／`from`／`to`。

- 凍結 TODO **原文一字未動**（仍唯讀）
- 手改 `phase2_expected_flips.txt` 依舊禁止；該檔由抽取器重新產生（`--check` rc=0）
- 🔴 **勘誤本身是可證偽的量測，不是宣稱**：`test_errata_rows_are_empirically_true`
  對每一列以 `receipt_gate` 指定的 gate 版本**實跑**該指令，
  判定須等於 `corrected_from`；現行 gate 的判定須等於 `corrected_to`。寫錯即紅。
- `test_errata_rows_are_not_stale`：每列須對應到 TODO 中真實存在的一列（禁死列）
- `test_mut_drop_errata_application_drifts`：拿掉抽取出口的套用 ⇒ `--check` 由 0 轉非 0
  （證明本層承重，非裝飾）

---

## §3 🔴 具名偏離：旗標採 **token 起始**比對，非 TODO 參考實作的 `grep -qx` 全等

`GOVB1 Task 3.2` 實作要點 2 給了參考實作：

```sh
_has_flag() { printf '%s\n' $1 | grep -qx -e '-p' -e '--print'; }
```

`grep -qx` ＝ **token 全等**。照抄會產生一條**新的 fail-open**：

| 指令 | 收窄前 | 全等版 | 本實作 |
|---|---|---|---|
| `claude -p"do it"` | BLOCK | **ALLOW** ⬅ 退化 | BLOCK |

shell 會把 `-p"do it"` 併為單一 token（前處理後 `-pdo␟it`），全等比對不到。
這正是本 epic 硬規矩 9 明文禁止的「**收窄型修法不得使該擋的從此不受檢**」
〔`20260808-GOVB1-B4-STAMP-R2` 三家 APPROVED〕。

**採用**：token **起始**比對 —— `(-p|--print)` 須緊接在區段內的空白之後。

**TODO 的目標仍完全成立**（「不得命中 `rev-parse`／`--porcelain`／`-print` 子字串」）：

| 樣本 | 是否 token 起始的 `-p`／`--print` | 結果 |
|---|---|---|
| `rev-parse` | 否（`-p` 前接 `v`） | 不命中 |
| `--porcelain` | 否（起始為 `--po`，`-p` 前接 `-`） | 不命中 |
| `-print` | 是（`-p` 起始） | 命中，但**到不了這關**——三例現場指令中 `claude` 皆不在命令位置，條件①先擋下 |

⇒ 偏離的是**參考實作**，不是**目標**。承重證據＝`test_22_mut_exact_token_flag_regresses_glued_form`
（把實作換成全等版 ⇒ `claude -p"do it"` 由 BLOCK 轉 ALLOW，紅）。

### §3.1 r1 修訂：長／短旗標**不對稱**（`CODEX-R1-P1-03` 之處置）

codex 判 (C)「exact ∪ 封閉列舉」，並舉具體反例：初版把 `-pfoo` 與 **`--printable`** 都擋，
「並非 closed enumeration」。composer 判 (A) 同意初版。兩家分歧 ⇒ **看碼證不數人頭**。

碼證上 codex 對一半：`--printable` 命中確實沒有正當理由。但 `-pfoo` 命中是**必要**的
（否則 `claude -p"do it"` 漏放）。差別可由 CLI 選項語法**導出**，不是任意取捨：

| | 值如何附著 | 判準 | `--printable` | `-p"do it"` |
|---|---|---|---|---|
| 短旗標 `-p` | POSIX 短選項值**可直接併寫**（`-pfoo`） | prefix-open（必要） | — | **BLOCK** ✓ |
| 長旗標 `--print` | GNU 長選項值只能 `=` 或另一 token | 後須為 `=`／空白／行尾（**封閉**） | **ALLOW** ✓ | — |

實作＝`(-p|--print([[:space:]=]|$))`。承重證據＝`test_22_r1_p1_03_mut_open_long_flag_overblocks`
（長旗標改回 prefix-open ⇒ `claude --printable x` 轉 BLOCK，紅）
＋ `test_22_r1_p1_03_long_flag_is_closed`。

### §3.2 🔴 程序瑕疵（兩家一致指出，主委接受）

`COMPOSER-R1-P1-01` ＋ `CODEX-R1-P1-03` 同時指出：本偏離在
consult-r1 **未裁決**、本檔 §8 **仍空白**時就已寫進 `_gate_lex.sh`
——實作端單方面把凍結 TODO 的「實作要點」降格為「參考實作」。

主委**接受此指摘，不辯解**。consult-r1 只裁決了實作**位置** (A)，沒有裁決旗標語意。
正確程序＝動碼**之前**先取得裁決。
⇒ 立 `票 B-51`：**OOE 偏離凍結文件者，須先 consult／review 取得裁決才動碼**；
且此規則本身要有機械強制點，否則只是又一條靠紀律的規矩（見 §7）。

---

## §4 具名偏離：實作位置為 `scripts/_gate_lex.sh`，非 TODO 所寫的 `gate_check.sh:86`

兩份 TODO 都寫「修改 `scripts/gate_check.sh`（`:86` alternation）」。
B3R 已把詞法判定整段移出至 `scripts/_gate_lex.sh`（`gate_check.sh:116` 自承），
`gate_check.sh` 內僅保留 `GATE_LEGACY_DECISION=1` 的舊路徑。
⇒ 若照字面改 `gate_check.sh`，等於再分岔出第二套詞法，正是 B3R 剛消除的問題。

**裁定出處**：`handoffs/reconcile/20260809-govb1-b7-consult-r1/synth.md`，codex ＋ composer
兩家 APPROVED 選項 (A)「改 `_gate_lex.sh`」。

**副作用（已確認無害）**：`tests/governance/test_gate_deny_fields.py:728-731` 以源碼字面
`claude\[\^\|\]\*\(-p\|--print\)` 錨定 `deny_bash_claude_agent` 分支。該字面仍存在於
`gate_check.sh:215`（legacy 分支）與 `:54,56`（deny 路徑 `match_rule` 鏡像，非判定），
故錨點未漂移。`match_rule=claude_agent` 的歸戶對本次所有新增 BLOCK 樣本仍正確
（新規則命中集合 ⊆ 舊字面命中集合），`test_01_enum_claude_agent` 綠。

---

## §5 交付通道＝out-of-epic

`scripts/_gate_lex.sh`、`tests/governance/test_gate_claude_narrow.py`、
`tests/governance/test_gate_lexical_contract.py` **均不在** `scripts/govb1_scope.manifest` allow 內。

in-epic 通道**定義性關閉**：manifest 的 `allow` ≡ 凍結 TODO 宣告集的機械鏡像
（`test_t01_f5_manifest_matches_task_decl`），加列＝聲稱凍結 TODO 宣告過該路徑 ⇒ 7 條測試立刻紅。
而 `GOVB1 Task 3.2` 的「新建」欄為**無**，本次卻需新建測試檔。

⇒ 走 `Governance-Scope: out-of-epic` trailer，與 B3R 落地（`a1a95cc`／`e7be91f`）同一通道。
硬保護前綴（`docs/GOVB1_`／`govb1_scope.manifest`／`govb1_frozen_hashes.txt`）本次**未觸及**。

---

## §6 收窄後的判定式與受測矩陣

```
(^|[;&|(`]|\$\()[[:space:]]*((eval|xargs)[[:space:]]+)?((\S*/)?)claude([[:space:]][^;&|]*)?[[:space:]](-p|--print)
```

🔴 上式為 r1 前的初版。**r1 修訂後**尾段改為 `(-p|--print([[:space:]=]|$))`（§3.1），
另加兩層（皆為 r1 findings 之修法）：

- **fail-closed 網**（`CODEX-R1-P0-01`）：掃描字串含展開標記（`$` 或反引號）
  ⇒ 退回舊式 `claude[^|]*(-p|--print)`。理由＝命令名可由展開產生時，靜態詞法決定不了 `argv[0]`。
- **前處理**（`CODEX-R1-P0-02` ＋ `COMPOSER-R1-P2-01`）：引號內換行比照空白中性化為 `US`；
  引號外 `\`+LF 依 bash 語意移除。成因＝`grep` 逐行比對，而 claude 段是**名稱＋旗標**
  的兩 token 規則，換行會把兩者拆到不同行；家族 CLI 是**單 token** 規則故不受影響
  （實測 codex／grok 同型三條皆 BLOCK）⇒ 本病專屬 claude 段。

十個承重要素，各有定向 mutation（全部實跑轉紅）：

| 要素 | 若拿掉會怎樣 | mutation 測試 |
|---|---|---|
| 命令位置（取代子字串比對） | `FP4` 四條轉回 BLOCK | `test_22_mut_restore_substring_reblocks_fp4` |
| `$(`／`(` 屬命令位置 ＋ cmdsub 抽取 ＋ 網 | `v=$(claude -p "hi")` 轉 ALLOW（**須三層全剝**） | `test_22_mut_drop_cmdsub_position_allows_regress` |
| 路徑前綴 `(\S*/)?` | `/usr/local/bin/claude --print x` 轉 ALLOW | `test_22_mut_drop_path_prefix_allows_abspath` |
| 區段界 `[^;&|]*`（旗標不跨 `;&\|`） | `claude foo; grep -p bar` 開始誤擋 | `test_22_mut_drop_segment_bound_overblocks` |
| 短旗標 token **起始**（非全等） | `claude -p"do it"` 轉 ALLOW（§3） | `test_22_mut_exact_token_flag_regresses_glued_form` |
| 長旗標**封閉**（`=`／空白／行尾） | `claude --printable x` 轉 BLOCK（§3.1） | `test_22_r1_p1_03_mut_open_long_flag_overblocks` |
| 展開標記 fail-closed 網 | `$(printf claude) -p x`／`claude${IFS}-p x` 轉 ALLOW | `test_22_r1_p0_01_mut_drop_expansion_net_regresses` |
| 引號內換行中性化 | `claude "a<LF>b" -p x` 轉 ALLOW | `test_22_r1_p0_02_mut_drop_quoted_newline_regresses` |
| `\`+LF 續行處理 | `claude \`+LF+`-p "x"` 轉 ALLOW | `test_22_r1_p0_02_mut_drop_line_continuation_regresses` |
| 勘誤層套用（§2） | `extract --check` 由 0 轉非 0 | `test_mut_drop_errata_application_drifts` |

**狀態轉移實測**（22 條探針，`.claude/tmp/b7_baseline.sh`，收窄前／後各跑一次）：
6 條 `BLOCK → ALLOW`（`FP4` 四條 ＋ 引號內 `--print` ＋ `.claude` 路徑 ＋ `--porcelain`），
其餘 16 條**判定不變**，其中 8 條真派工形態全程維持 BLOCK。**零條 `BLOCK → ALLOW` 屬真派工**。

**三版對照**（`pre-phase2` ／ `HEAD` ／ 本版，`.claude/tmp/b7_regress_probe.py`，9 條）：
r1 提出的 5 條旁路 payload **全部收斂為 BLOCK**。其中——

| payload | pre2 | HEAD | 本版 | 性質 |
|---|---|---|---|---|
| `$(printf claude) -p x` | BLOCK | BLOCK | BLOCK | 🔴 初版曾**回歸**，已修 |
| `claude${IFS}-p x` | BLOCK | BLOCK | BLOCK | 🔴 初版曾**回歸**，已修 |
| `claude "a<LF>b" -p x` | ALLOW | ALLOW | BLOCK | 既有缺口，本票順修 |
| `v=$(claude "a<LF>b" -p x)` | ALLOW | ALLOW | BLOCK | 既有缺口，本票順修 |
| `claude \`+LF+`-p "x"` | ALLOW | ALLOW | BLOCK | 既有缺口，本票順修 |

**跨 grep 實作**（`.claude/tmp/b7_grep_portability.sh`，24 條）：
`/usr/bin/grep`（BSD grep 2.6.0-FreeBSD，即腳本經 `bash` 實際取到的 grep）**24/24 符合期望**。
🔴 互動 shell 的 `grep` 是 Claude Code shell-snapshot 的 shell function（包 ugrep 7.5.0），
**不是** gate 的執行環境，勿被此誤導。GNU grep（CI linux）本機無法取得
⇒ 以 `governance.yml` 跑 pytest 為可證偽 backstop；CI 紅則本結論作廢。

---

## §7 未涵蓋（具名殘留，不在本票）

- 5 種 wrapper 形態（process substitution／`xargs -n1`／`env`／動態賦值／絕對路徑 `bash -c`）
  仍 fail-open ⇒ 歸 `GOVB0 B4`（`Task 2.3`／`2.4`），與本票同檔不同段。
- B3R 的 O(n) scanner 未交付（quoted 500K `timeout 20 → rc=124`，`CODEX-R8-P1-03`）⇒ 歸 GOVB0。
- 無旗標的 `claude <prompt>`（互動式）維持 ALLOW —— 收窄前後語意一致，非本次引入。
- ~~fail-closed 網的具名代價（誤擋唯讀指令）~~ —— **stamp-r1 已收斂**：
  網的觸發由「整條含 `$`／反引號」收窄為「**命令位置 token** 含 metachar」，
  `echo "$(cat .claude/tmp/x)"; git rev-parse HEAD` 這類唯讀指令不再誤擋
  （`test_22_s1_net_trigger_is_command_position_scoped`）。

### 🔴 §7.1 明確**不受理範圍**（刻意宣告，避免對抗審無終點）

本專案對 `gate_check` 的既定定位是「**擋意外，不防蓄意**」（`GATE-TOKEN-BINDING` 一節、
`票 B-15` 之設計理由）。下列向量需要**刻意構造**才會發生，且**pre-phase2／HEAD／本版三個
版本一致放行**（非本次引入），因此**列為邊界而非缺陷**，本票不受理：

| 向量 | 為何靜態詞法解不了 |
|---|---|
| `$(printf clau)de -p x` | argv[0] 由**替換輸出與字面串接**而成；literal `claude` 根本不存在於指令文字中 |
| `* -p x`／`./* -p x`／`~/* -p x` | argv[0] 由 **glob 對檔案系統求值**決定；同一字串在不同 cwd 有不同 argv[0] |

要擋這兩類，唯一可靠解是「**執行前解析 argv[0]**」（例如改用 shell 的 `DEBUG` trap 或
在 wrapper 層取真實 argv），那是**另一種機制**，不是詞法層能補的，且不在本 epic scope。
🔴 提出這兩類的複驗**不構成 B7 的阻擋項**；若要推翻此邊界，請先推翻
「擋意外不防蓄意」這條專案定位（那是使用者層級的決定，不是本票能改的）。
- 🔴 `票 B-52`（stamp-r1 現場發現，**活證據**）：`govflow_lifecycle.json` 的 `stamp` 項
  明載 `produces_findings: false` 與 `debt_clear.preconditions = [all_families_terminal,
  no_findings_format_gate]`，但 `scripts/debt_clear.sh` **實際仍跑 findings-format 閘**
  ⇒ SoT 與實作漂移。本輪具體後果：codex 的 stamp 產出含 4 條實質 findings ＋ 1 條勘誤層漏洞，
  卻因為用 `FINDING <ID>:` 散文列而非 canonical `## <ID>` heading，
  收集器抽不到任何 ID（vacuous）⇒ `completeness` 拒銷 ⇒ **銷帳被鎖死**，
  最終只能走 `--abandon --kind collection-failed`（理由欄逐字記錄實情，未謊稱無 findings）。
  🔴 這同時證明 `produces_findings: false` 對 stamp 輪**是錯的**——stamp 輪會產生 findings，
  而 SoT 說它不會 ⇒ 那些 findings 沒有 canonical 落點。
  歸屬＝`GOVB1 Task 4.2`（B9，`findings 的落點`）＋`Task 4.3`（B10，`format-failed` 補救層）。
  ⇒ **B9／B10 的優先序因此上升**：它們不是「補強」，是本 epic 自己正在踩的坑。
- 🔴 `票 B-51`（§3.2）：**OOE 偏離凍結文件須先取得裁決才動碼**。本輪主委違反此序。
  該規則自身**尚無機械強制點** ⇒ 依「工具必須自帶強制機制」，它現在只是靠紀律，
  必須另立票做成閘（候選檢查點：`gate.sh` 於發 OOE 相關 token 前，
  驗延伸檔 §裁決區非空且有兩家戳記）。**不得只寫進文件就當完成。**

---

## §8 委員裁決

### r1（`20260809-GOVB1-B7-REVIEW-R1`，codex ＋ composer 兩家，皆 Verdict=需修補後派工）

| 必答 | codex | composer | 主委處置 |
|---|---|---|---|
| §1 旗標偏離 | (C) exact ∪ 封閉列舉 | (A) 同意偏離 | **看碼證取兩者交集**：短旗標 prefix-open（(A) 之必要性）＋長旗標封閉（(C) 之具體反例 `--printable`）⇒ §3.1 |
| §2 勘誤處置 | 需機器可讀 errata | 人類延伸檔**不足** | **全盤接受**：新增 `phase2_flips_errata.tsv` ＋ 4 條強制測試 ⇒ §2 |
| §3 獵漏 | P0-01 回歸 ×2、P0-02 跨行 ×2 | P2-01 續行 ×1 | **全數修掉**，各附承重 mutation ⇒ §6 |
| §4 誤放率 | 自訂語料 3/8 誤放 | 0/7 誤放 | codex 的 3 條即 P0-01／P0-02，修後重跑歸零 |
| §5 `票 B-26` 雙票結清 | 大致涵蓋，待 §1 裁決 | **可一併結清** | 採「可結清」；`T-3.2-R1` 第三例字面探針已由 FP4 等價形態覆蓋 |
| 程序 | P1-03 先動手後補文件 | P1-01 同左 | **接受，不辯解** ⇒ §3.2 立 `票 B-51` |

**兩家分歧僅一處（§1）**，處置＝看碼證不數人頭：codex 的反例 `--printable` 成立且已修；
composer 對 `-p"do it"` 必須 prefix-open 的判斷亦成立且已保留。

### stamp-r1（`20260810-GOVB1-B7-STAMP-R1`）：composer APPROVED、**codex REJECTED**

codex 以「heredoc 與動態命令名仍 fail-open」駁回，提 4 條新 findings ＋ 1 條勘誤層漏洞。
兩家分歧 ⇒ **看碼證不數人頭**：codex 每條都附 payload 與 rc，composer 未覆蓋這些形態。
⇒ 採 codex，逐條處置如下（主委三版對照複驗，`.claude/tmp/b7_stamp_findings.py`）：

| finding | codex 定性 | 主委三版複驗 | 處置 |
|---|---|---|---|
| `NEW-P0-01` heredoc 內跨行 `$()` | P0 | pre2／HEAD／初版**皆 ALLOW**＝既有缺口 | **修**：`_gate_lex_extract_cmdsubs` 改整份單一 record（`RS='\001'`），emit 時換行轉 `;` |
| `NEW-P0-02b` `clau\de -p x` | P0 | 同上，既有缺口 | **修**：前處理觸發條件納入反斜線；引號外 `\X` 依 bash 語意去斜線 |
| `NEW-P2-04c` `!claude -p x` | **P2**（低估） | 🔴 pre2／HEAD **BLOCK**、初版 ALLOW ＝ **回歸** | **上修為回歸並修掉**：網的觸發改判「命令位置 token 含 metachar」，`!` 納入封閉集合 |
| `NEW-P0-02a` `$(printf clau)de` | P0 | 三版皆 ALLOW | **不受理**（§7.1 邊界：蓄意構造 ＋ 靜態不可判） |
| `NEW-P2-04a/b` glob | P2 | 三版皆 ALLOW | **不受理**（§7.1 同上） |
| `NEW-P0-03` `\`+CRLF 續行 | P0 | 三版皆 ALLOW | 🔴 **誤判，已實跑否證**（見下） |
| `ERRATA_RECHECK` kind 未驗 | — | 主委複現 | **修**：kind 改為由 from/to **導出**，宣告不符即 `ValueError` |

**`NEW-P0-03` 之否證**（`.claude/tmp/crlf_semantics.sh`，以 `echo` 代打，未執行任何派工）：

```
$ printf 'echo A \\\r\n-p x\n' | bash
A ^M
line 2: -p: command not found
```

bash **不把 `\`+CRLF 當續行**——`\` 跳脫的是 CR（成為字面 CR 引數），LF 才結束指令。
故 `claude \`+CRLF+`-p x` 執行起來是「`claude <CR>`（無 print 旗標 ⇒ 非 headless 派工）」
加「一條不存在的指令」，**本來就不是派工**⇒ 判 ALLOW 正確。
對照組 LF 續行確實是同一條指令，故必須 BLOCK（`test_22_s1_crlf_continuation_is_correctly_allowed`
同時釘死兩者）。

🔴 **codex 抓到的勘誤層漏洞是本輪最有價值的一條**：主委在 r1 宣稱勘誤層「是可證偽的量測，
不是宣稱」，codex 用一列「from/to 皆與實跑相符、但 `kind` 寫成 `maintain`」的假勘誤
證明**全部測試仍綠** —— 因為當時沒有任何斷言把 `kind` 綁回 from/to。
修法不是加驗證而是**取消宣告**：`kind` 由 from/to 導出（`from==to → maintain`，否則 `flip`），
宣告值不符即在讀檔當下 `ValueError`。回歸＝`test_errata_kind_is_derived_not_declared`。

### stamp-r2（待派）

修補後須由 codex 再複核（composer 已 APPROVED r1 收斂檔，但本輪增量亦需其複驗）。
🔴 該輪 brief 須逐字帶上 §7.1 的**不受理範圍**，否則對抗審沒有終點。
