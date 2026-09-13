# SPLITUNIFY b9 — review-r13 三條閉合再驗證 ＋ D-002 v14 重簽（＝DOCROT 成效量測第二輪）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 🔴 **本輪不重審 SPEC 既有內容**。R12 停輪判準已觸發並經三家確認；R13 三家亦一致判「不為三條 ASSERT 重開 §V」。本輪標的**只有** v13→v14 的 diff 與 `docs/SPLITUNIFY_TODO.md` 的 T2／T3 修補。

## 本輪要做兩件事

### (A) 逐條重跑你自己在 review-r13 提出的反例
| finding | 提出方 | 修補摘要 |
|---|---|---|
| `CODEX-R13-P1-01` | codex | 新增 `M-SU-D2-35`（`assignments` 不寫 `feature_timeframe` 欄），`C5-20` 改指之 |
| `CODEX-R13-P1-02` | codex | `Task 9.3` receipt 閘改為 exact ID set ＋ TASK／COMMIT 標頭綁定，明文禁 `wc -l` |
| `CODEX-R13-P2-03` | codex | `B9D` 改為逐列具名（七個下游消費模組 ＋ 兩個支撐面 ＝ 九列） |
| **主委自產（請一併審）** | — | `C5-21` 有與 `C5-20` 完全相同的錯配（原指 `M-SU-D2-24`）⇒ 新增 `M-SU-D2-36` 並改指之；條數 34 → 36 |

### (B) 對 `docs/SPLITUNIFY_SPEC.D-002.md` **重簽**
- v13 之三家戳記因 (A) 之 body 變更而**失效**。新 body sha256（實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` 取得）：
  `7455b305c6f3c013de84d1941c4d69bc731fb5fa90f6e91d447e14382f0b10e2`
- 審完 append 到該檔 `## 戳記` 區，逐字格式：
  `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:7455b305c6f3c013de84d1941c4d69bc731fb5fa90f6e91d447e14382f0b10e2 task:20260911-SPLITUNIFY-B9-REVIEW-R14`
  （判 REJECTED 者把 `APPROVED` 換成 `REJECTED` 並在同行尾以 `—` 接原因。）
- 🔴 **舊的 v13 戳記行請保留**（追溯用），不要刪。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：
  - `docs/SPLITUNIFY_SPEC.D-002.md`：只讀 `C5-20`／`C5-21` 兩列（`grep -n '`C5-20`\|`C5-21`'`）、mutation 目錄標題行與 `M-SU-D2-35`／`M-SU-D2-36` 兩列（`grep -n 'M-SU-D2-3[56]\|mutation 目錄'`）
  - `docs/SPLITUNIFY_TODO.md`：`§B` 之 `B9D` 那一列、`§C-9` 之 `Task 9.2a` 與 `Task 9.3`
- **本輪 diff**：`git show 9ec33871 -- docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md`
- 🔴 **不在審查範圍**：`HISTORY-BEGIN`～`HISTORY-END` 與「## 沿革與追溯索引」節，以及逐字標記「作廢／前版／舊敘述／原寫」之字面。**finding 之 source anchor 落在歷史段者不受理**（`completeness --single` fail-closed 拒收整份交件）。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: mutation 表為 36 列、ID 01–36 連續無缺 → `grep -cE '^\| .M-SU-D2-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` ＝ 36；逐號檢查無缺。派工後預期值: 不變（本輪為唯讀審查）。
fact-verified: §C-9 對 36 條全數認領 → `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l` ＝ 36。
fact-verified: register 仍為 29 列 → `grep -cE '^\| .C5-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` ＝ 29（本輪未動 register 列數，只改兩列的 mutation 欄）。
fact-verified: 兩檔之產出端格式閘皆過 → `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` 與同一命令對 `docs/SPLITUNIFY_TODO.md` 皆 rc=0。
fact-verified: 條數字面只存在一處 → `grep -n '共 \*\*36\*\* 條' docs/SPLITUNIFY_SPEC.D-002.md` 恰一行（mutation 目錄標題）；本延伸自定之「條數只存在於 register／mutation 表標題一處」未被違反。

assumed: `M-SU-D2-35`／`M-SU-D2-36` 的「應紅之測試」欄成立——即刪掉 `feature_timeframe` 欄後，`test_assignments_composite_key_unique`／`test_purged_composite_key_unique` 會因 `duplicated(subset=[...])` 之 `KeyError` 而轉紅。**我的否證觀測（已先跑）**：這兩個測試**尚未存在**（`Task 9.2a` 未開工），所以我**無法**實跑驗證；我的依據只是 pandas 對缺欄 subset 會 raise `KeyError` 的一般行為。**我沒查**：若實作者把 guard 寫成先 `if "feature_timeframe" in df.columns` 再判，欄缺就**不會** raise 而是靜默跳過 ⇒ 該 mutation 變成無處可紅。← **請直接攻這條**，並判 `M-SU-D2-35`／`36` 的「應紅之測試」欄是否該寫得更具體（例如明寫「不得以 `in df.columns` 條件包住 guard」）。

assumed: 我補 `C5-21`／`M-SU-D2-36` 是「同型自查」而非過度延伸。**我的否證觀測（已先跑）**：`C5-21` 原指 `M-SU-D2-24`，而 `M-SU-D2-24` 的內容逐字是「答案窗 purge 仍用**逐列** `in_train`（未改按事件側）」——與「`purged` 表少了 `feature_timeframe` 欄」確為兩件事。**我沒查**：register 其餘 27 列的 mutation 欄是否也有同型錯配（我只查了 codex 點名的那一列與其鄰列）。← **請直接攻這條**：**逐列**核對 `C5-01`..`C5-29` 的 mutation 欄是否真的對應到會破壞該列所述改法的那條。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| mutation 條數與表列一致 | 36 列、01–36 連續、§C-9 認領 36/36（上列 fact-verified） | — |
| register 逐列 mutation 對應 | 只查了 `C5-20`／`C5-21` 兩列 | 🔴 **其餘 27 列**（見上 assumed 第 2 條）——請逐列核對並列出所有錯配 |
| `Task 9.3` receipt 閘之新判準 | exact ID set ＋ TASK／COMMIT 標頭；明文禁 `wc -l` | 新判準本身是否仍可被繞過（例：receipt 寫對 ID 集合但分類欄全填同一值；或 `COMMIT:` 填任意 sha 而無人對證） |
| `B9D` 之列數敘述 | 已改為七模組＋兩支撐面＝九列，與 `Task 9.3` 表列一致 | `§B` 其餘五列（`B9A`／`B9B`／`B9C`／`B9E`／`B9F`）之描述是否也與各自 Task 的實際內容相符 |
| v13 舊戳記 | 保留在 `## 戳記` 區供追溯；`reconcile_stamps_check` 對新 body 會 FAIL（預期，本輪重簽解決） | 保留舊戳記行是否會讓 `reconcile_stamps_check` 誤判（例如取到舊行而非最新行） |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 逐條重跑你在 review-r13 提出的反例，對每條給 `CLOSED` 或 `STILL-OPEN`。
   **(1b)** 判 `CLOSED` 者，寫出**你重跑的那一條命令與觀測到的輸出特徵**；不接受無標的說法。
2. **(2a)** 逐列核對 `C5-01`..`C5-29` 的 mutation 欄：還有幾列錯配？逐列列出（ID、現指、應指或「需新增」）。
   **(2b)** 若你答「零錯配」，請貼出你用來逐列核對的**可執行命令或逐列對照表**——「逐項核對後無問題」不受理。
3. **(3a)** `M-SU-D2-35`／`M-SU-D2-36` 之「應紅之測試」欄是否足夠？（見上 assumed 第 1 條之繞過形態）
   **(3b)** 若不足，給出**可直接貼進該欄**的加強字面；若足夠，說明為何 `in df.columns` 那類繞過不成立。
4. **(4a)** `Task 9.3` 之新 receipt 閘還能被繞過嗎？給出你試過的繞過構造與結果。
   **(4b)** 若能繞過，給**最小**修補；若不能，說明你試了哪幾種構造。
5. **(5a)** 對 `docs/SPLITUNIFY_SPEC.D-002.md` 新 body sha256 `7455b305…`：`APPROVED` 還是 `REJECTED`？
   **(5b)** 若 `APPROVED`，指出 v14 裡最可能在 `Task 9.1` 實作當下變紅的條文（具名）；若 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉。
6. **(6a)** 現在可以領 impl token 進 `Task 9.1` 了嗎？
   **(6b)** 若可以，說明你檢查了什麼才敢說可以；若不可以，列**最小**閉合集合。

## 🔴 本輪格式硬約束（違反會被機械閘退件）
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）；`**碼證**:` 後接換行再條列＝空殼，會被退件。
4. **零 findings 時**須用 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的零 findings sentinel 形態，且 sentinel 內同樣要有**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**——🔴 **不得填日期**（stamp-r1 曾因 `CLOSED: 2026-09-13` 被 `verdict_parse` 拒收，整輪卡住）。

## 🔴 本輪是 DOCROT 的成效量測第二輪
`doc_friction_ratio`（唯一權威＝`handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md`）之及格線＝**本輪與上一輪皆 ≤0.30，且每輪 finding 總數 ≤20**。第一輪（review-r13）實測 **0/5 = 0.00**。
⇒ 請照實寫 finding，**不要**為了讓數字好看而少提；但請先確認落點**不是歷史段**。
🔴 **另請順帶判一件事**：r13 之 `CODEX-R13-P2-03`（`B9D` 數字與表列不符）語意上明顯是「同一件事寫兩處而不一致」的文檔病，卻**未命中**該判準的封閉字面集合（`多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張`）。請判：該集合是否過窄？若是，給**可直接替換**的新字面集合（仍須封閉、可 grep、不得靠語意判斷）。

## 產出
canonical 四欄 findings + **Verdict** ＋ 戳記（append 到 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `## 戳記` 區）。
**禁改碼、禁改 SPEC 正文、禁改 TODO**（戳記 append 除外）。收尾清 /tmp workdir（保留 claude-501）。
