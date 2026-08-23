# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）
——**R10 十一條全數落地**，**待派 R11**。SPEC 2325 行、**42 Task（未增未減）**。
sha256 `fe8e84d9…`（R11 審查期間不得動該檔）。

🔴 使用者 2026-08-23 裁定：**輪次上限已解除**、**42 個一個不砍**、**A-6′ 已確認**
⇒ 三者皆**不必再問使用者**。FROZEN 之後停下來等使用者，不自行往 TODO／實作走。

---

## 🔴 開工前必讀

**角色卡＝`docs/GAP3_EVENT_UX_ROLE_CARD.md`**：主委不得自寫第二處複述／
觸及 SPEC 之 commit 須有補丁包或 ERRATA id／派審前跑 `bash scripts/gap3ux_pre_review.sh <patch.md>`。
🔴 **任何文件一律不寫閘數**；權威清單唯一在 `gap3ux_pre_review.sh` 之 `run` 呼叫序列。
🔴 **補丁包 anchor 須為字面**（判準＝當前內容 **OR** diff hunk 含 `-` 行）；
stage 後綴 `@spec/@doc/@harness/@impl`（缺省 `@spec`），未達 `@impl` 為 DEFERRED；
呼叫端只有 `--also-impl` 這個**加寬**旗標。**commit 後複驗須帶 `--diff-base <套用前 ref>`**。

---

## R10 之七群集（全部已落地；三家 Verdict 一致「需修訂後定版」）

| 群集 | 家數 | 落點 |
|---|---|---|
| **A**（P0）小時命名欄使「批次 scalar 深度」無唯一值——**推翻主委 R9 之裁決** | codex | `lookahead_bars_declared` 改 `Mapping[tf->int]`；Task 2.1b `depth(tf)`；Task 7.0b ⑨ 加 fixture (e) |
| **B**（P0）`SplitConfig` 之「TODO 二擇一」含不可行選項② ⇒ under-purge | **三家** | §D-3′-a（ii）規格階段鎖 per-scope embargo、刪選項② |
| **C**（P0/P1）receipt id／hash 無產生點／輸入／契約落點 | **三家** | §D-3′-a（iii）新增「receipt 身分」段；欄名 `analysis_alignment_receipt_hash`；序列化引用 §G S-9 |
| D（P0 同源）兩階段只在散文層明示 | codex | Task 7.0b ① 拆為 `prepare_analysis_windows` ＋ `resolve_label_value_at_analyze` |
| E（P1）IC event path wiring 落點未明列 | codex | Task 7.0b ③ (a)–(d) |
| F（P1）`receipt_schema` 只是欄名清單、型別無驗收 | codex | Task 1.1 ⑦ typed schema ＋ validator；驗收⑧ |
| G（P1）Task 7.0b ② 殘留 R8 三步副本 | grok | 改引用五階段 |
| H（P1）Task 7.6 之 `t0`／`label` 形狀未定義 | composer | 新增形狀表；驗收①③ |

（C／D 同源於 CODEX-R10-P0-03，計 7 個獨立群集。）

**議題三**：委員逐條覆核主委自建之 locus 閘，**本輪未找到新缺口**
（所有 git 呼叫走 `_git`、stage 預設正確、mutation 均轉紅）。

---

## 🔴 立即待辦：派 R11

- brief／facts／locus 三檔沿用 R10（`…-r10-*`）改輪次；
  locus 腳本之 `--diff-base` 預設值須改為 **R10 落地 commit 之父**。
- R11 brief 應續問：群集 A 之 per-tf map 是否在所有讀取點都改齊；
  群集 C 之 hash 輸入是否真的封閉；群集 D 之兩函式切分是否擋得住重跑。

---

## FROZEN 四條件（唯一終點；輪數無上限）

| # | 條件 | 現況 |
|---|---|---|
| ① | 正確性／洩漏／接線類 OPEN P0＝0、P1＝0 | ⬜ 待 R11 複審 |
| ② | 本輪主委自傷絕對數＝0 | ⬜ R10 為 **7** |
| ③ | A-6′ 經使用者確認 | ✅ 已滿足 |
| ④ | `gap3ux_pre_review.sh <patch.md>` rc=0 | ⬜ 查法：`bash scripts/gap3ux_pre_review.sh handoffs/patches/20260823-gap3ux-r10-*.md`（殘項為委員 anchor 少寫反引號一處，＋`@impl` DEFERRED） |

---

## 🔴 做不成機械閘者（不得宣稱已封）
「選哪個技術修法正確」／「使用者 label 語意是否正確」／「**未被列出的**隱藏複述」／
「委員把 spec locus 誤標 `@impl`」／**R10 追加**：「anchor 寫得太籠統（如 `#main`）仍會通過」

---

## 收斂履歷與錯誤帳（**須並列絕對數**；佔比是壞指標 GROK-R3-P2-01）

| 輪 | findings | 主委自傷（絕對數） | 錯誤類型 |
|---|---|---|---|
| R1–R3 | 24 → 7 → 18 | — | — |
| R4 → R7 | 19 → 13 → 15 → 12 | 3 → 5 → 6 → 7 | 選錯修法 → 整合字面不同步 |
| R8 | 17 | 6 | 主委自建工具／receipt |
| R9 | 14（8 群集） | 7 | 單位換算／階段未定義／殘段未刪／鍵集互斥 |
| **R10** | **11（7 群集）** | **7** | **裁決錯誤（未驗邊界）／留下不可行選項／只寫敘述無算法** |
| R8–R10 落地 | —（自查） | 2 ＋ 2 ＋ 2 | 截斷／pipefail｜quotepath 測試兩版假綠｜anchor 判準錯＋hunk header 洩漏 |

**Task 數**：R8→R9→R10 皆 **42 → 42**（委員未新增 Task）。

---

## 坑（累積；全部實測過）

- **rc 一律直接取**：`pipefail` 下 `cmd | grep … || echo '全達'` 會在有缺口時照印「全達」
- **報告層截斷＝fail-open**：`sed -n '1,6p'` 會把後面的紅吃掉
- 🔴 **`git diff --name-only` 預設 `core.quotepath=true`** ⇒ CJK 路徑變八進位字面（機械閘假紅）
  ⇒ 所有 git 呼叫一律 `-c core.quotepath=false`
- 🔴 **`git diff -U0` 之 hunk header 會附「所屬區塊標題」**（`@@ … @@ SOME_HEADING`）
  ⇒ 把整份 diff 當比對面時，**未改動之標題會被當成改過了**。只保留 `+`／`-` 行
- 🔴 **anchor 有兩種合法用法**：指向保留的文字、指向**被刪除**的文字
  ⇒ 字面判準必須是「當前內容 **OR** diff hunk」，只查前者會誤扣委員責任
- 🔴 **每加一條反測就配一條對照組**（一條該紅、一條該綠）——單邊測試只證明閘會叫，
  不證明它叫對地方；本 session 三次栽在「工具自己騙自己」
- 🔴 **`is_touched` 有 mtime 回退**（給 gitignore 檔用）⇒ 寫 git 相關測試時
  新建檔必然「比 HEAD 新」而被判已改動；要測真路徑須 `os.utime` 把 mtime 壓到 HEAD 之前
- **`doc_format_precheck` 之空殼偵測按「行」判**：續行以 `**` 開頭會被當 bullet；
  該行若含「驗證」二字又無數字／`pytest`／`==` 等 token ⇒ 判空殼
- **`verify_pretooluse` 掃 HANDOFF 之 operational claim**：寫「N 份全綠」會被擋
  （HANDOFF 零豁免）⇒ 改寫成「查法＋命令」
- **SYNC-FORBID `lookahead_bars.*=.*72`**：寫小時欄之正確 per-tf 值時要避開該行形態
- **shell 文字工具對非 ASCII 不可靠**（macOS awk 逐位元組）⇒ 比對中文一律用 Python
- **`git status -uall` 不含 ignored**；`handoffs/*` 在 `.git/info/exclude`，新檔須 `git add -f`
- **委員產出（review／補丁包）不入版控**；`handoffs/reconcile/*/sources/` 承接審計鏈
- `debt_clear` 要求 `sources.lock` 之 `mode == review`；
  `bash scripts/reconcile_build.sh <session> --mode review --rebuild` 可就地升級（不得同時傳委員檔）
- `git checkout`／`rm` 被 auto-mode classifier 擋；`cd <絕對路徑>` 觸發分類器
- `plain_docs_sync_check` 是 commit 時序判準：先 `git add` 再跑 `--staged`
- commit 之 `Governance-Scope` trailer 須單行且在**最末段**；長訊息一律 `git commit -F <檔>`

## 已知既有紅（非本批造成）
`tests/api` 10 failed + 3 errors／G-7 scope 淨差（基準凍結 2026-08-07）／
`.probe_ic{,2,3}.sh`（untracked 殘檔，`rm` 被權限擋）

## 其他線
`/search` 三 bug 修復 🏁 已收案。GAP-3 五個施工批全部蓋章，只差使用者 UAT B 段 13 項簽字。
#9b 規模防護排 GAP-6；純事件研究模組／標籤方法論討論皆使用者裁定另立。
