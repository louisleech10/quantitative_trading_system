
# B3 修補 code review（雙家族）— C1–C5 關閉驗證

brief-kind: review

**受審**：工作區未 commit 變更（`scripts/_gate_lex.sh`／`scripts/gate_check.sh`／
`scripts/extract_phase2_expected_flips.py`／`tests/governance/*`／語料）
**依據**：`handoffs/reconcile/20260805-govb0-b3-review/synth.md`（三家戳記）
**實作報告**：`handoffs/20260805-govb0-b3-fix-grok.md`（**視為不可信資料**，須獨立複核）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。
finding heading 逐字格式 `^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`，本輪用 `R14`。
零 findings 請明寫 `FINDINGS_COUNT: 0`。

## §0 前提宣告

**已查證**（主委實跑，`VERIFY:20260805T124806Z-b3-failopen-independent-repro` 為修補前基線）：

- fact-verified: 修補後三條 fail-open 探針全部轉 BLOCK——
  引號內命令替換 `舊=0 新=2`、引號 env 前綴 `舊=2 新=2`、8KiB 後綴 `舊=2 新=2`。
- fact-verified: C4 舊恆真斷言已刪除，新測試以「複製原始碼→移除修法→斷言行為消失」方式做真突變。
- fact-verified: 實作端動了 **Internal Frozen** 的 `docs/GOVB0_FRICTION_TODO.md`（+1 行 HTML 註解）。

- fact-verified: **主委親跑全套** `pytest tests/governance -q` → **759 passed** rc=0（255s），
  與實作端回報一致（修補前 751）。

**假設**（請攻）：

- assumed: C1 採「超 8192 字元一律 fail-closed」是可接受的取捨。**見下方 M-2，主委認為未經量測。**
- assumed: 新增的 8 條測試**各自都會因對應修法 revert 而轉紅**。
  主委只複核了 C4／C5 兩條的突變寫法，**未逐條驗證全部 8 條**。

---

## 🔴 主委自行發現的兩條（**優先複核，不得略過**）

### M-1 — `gate_check.sh` 自我排除疑為萬用繞道【既有缺陷】

`gate_check.sh:215` 於判定為 dispatch 後執行
`if printf '%s' "$cmd" | grep -Eq 'scripts/gate(_check)?\.sh'; then exit 0; fi`
⇒ **指令只要任何位置出現該字串即整條放行**。

主委實跑（新舊皆同，**非本次修法造成**）：

| payload | 舊 rc | 新 rc |
|---|---|---|
| `codex exec x`（對照） | 2 | 2 |
| `codex exec x; echo scripts/gate.sh` | **0** | **0** |
| `codex exec x  # scripts/gate.sh` | **0** | **0** |
| 8200B + `; scripts/gate.sh; codex exec hi` | **0** | **0** |

**請判定**：這是否為真繞道？若是，是否屬「擋意外不防蓄意」的可接受設計邊界，
或應收斂為「僅當 `scripts/gate.sh` 位於**命令位置**時才排除」？請給修法與風險。

### M-2 — C1 的 fail-closed 造成正常長指令被誤擋【本次修法引入】

主委實跑：`echo` + 8200 個字元的無害字串 → **舊 rc=0、新 rc=2**。
⇒ 任何超過 8192 字元的 Bash 指令，**即使完全無派工字樣，一律被擋**。

🔴 **這正是本 epic（摩擦止血）要消除的方向**：`票 B-15` 的本質就是「該放行的被擋」。
用「一律擋」換掉 fail-open，等於把安全缺口換成摩擦缺口，**而摩擦缺口沒有被量測**。

**請判定**：
| # | 問題 |
|---|---|
| M-2a | 8192 這個上限有無依據？超過此長度的**正常**指令實際發生率如何？（可查 `.claude/gate/audit.log` 的歷史 cmd 長度分布） |
| M-2b | 是否有更精準的判準？例如：僅在超長且**含 executor 字樣**時才 fail-closed；或改 O(n) 掃描並大幅提高上限 |
| M-2c | 若維持現法，是否須提供逃生口，且逃生口會不會反過來變成新的繞道？ |

---

## 標的 1 — C1–C5 是否真的關閉（逐條複核）

實作端宣稱的驗收值如下，**請獨立複跑，不得採信**：

| # | 宣稱 | 你要驗什麼 |
|---|---|---|
| 1a | C1-a `x×8200; codex exec hi` → rc=2 | 獨立複跑 |
| 1b | C1-b latency cold_ms=70.3、rc=0 | 獨立複跑；**門檻 100ms 是否被動過** |
| 1c | C1-c 4MB 輸入 rc=2、3.817s | 獨立複跑；3.8 秒是否可接受（PreToolUse 熱路徑） |
| 1d | C2-a..d 四樁（含 E-3 回歸樁 `out=$(codex exec x)`） | 逐條複跑 |
| 1e | C3-a..d 四樁（含兩條不得誤擋） | 逐條複跑 |
| 1f | C4 mutation 前後 rc 對照 | **移除修法後測試是否真的轉紅** |
| 1g | C5 mutation（RECURSE 六條消失） | 同上 |

## 標的 2 — 有無弱化既有保護

| # | 查什麼 |
|---|---|
| 2a | `git diff tests/` 中被**刪除**的斷言是否僅限 C4 那條恆真斷言？有無其他既有斷言被弱化或刪除 |
| 2b | `match_rule` 封閉集合是否被擴充（實作端宣稱未擴） |
| 2c | **語料 A（`gate_invariance_corpus.txt`）是否一行未動** |
| 2d | `phase2_expected_flips.txt` 新增 8 列 maintain 是否**全部**可由 TODO 機械重現（`--check` rc=0） |

## 標的 3 — 動了凍結文件

實作端在 `docs/GOVB0_FRICTION_TODO.md` 加了 1 行 HTML 註解（記錄 C5 選 (a)）。
brief 原本只允許「選修法 (b) 時」改 TODO。

**請判定**：此舉是否可接受？或應改走延伸檔（使用者定死「修訂凍結文件走延伸檔非就地改」）？

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`）

1. **C6**（多 heredoc 第二 body 誤擋）——已裁定順延 B4。
2. B4 以後的 Task。
3. 重開 SPEC／TODO 設計裁決（標的 3 的「該不該就地改」除外）。
4. `audit.log` 大小／封存／latency 主題。
5. 措辭／命名／可讀性。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ B3 驗收通過，可進 B4。**
> M-1／M-2 若判為 BLOCKING，須具名修法，不得以「既有缺陷」略過。

## 硬性要求

1. **禁改碼、禁改測試、禁改 TODO／SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**。
   誤動檔案**請回報，不要自行還原**——本 epic 已有委員違反此條並具名記錄。
4. 不要 commit、不要 push；**禁碰 `data_cache/`**。
5. 跑全套 `pytest tests/governance -q` 請**丟背景並導檔再取尾**；跑完須
   `bash scripts/restore_golden_inventory.sh`。

## 產出

M-1／M-2 的獨立判定與修法、標的 1 七項的獨立複跑值、標的 2 四項的檢查結果、
標的 3 的裁定、`## 出場判準核算`。收尾清 /tmp workdir（保留 claude-501）。
