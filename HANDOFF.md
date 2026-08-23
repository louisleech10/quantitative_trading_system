# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）
——**R11 二十條全數落地**，**待派 R12**。SPEC 2541 行、**42 Task（未增未減）**。
sha256 `94cdf05b…`（R12 審查期間不得動該檔）。

🔴 **findings 反轉上升：17 → 14 → 11 → 20。診斷＝規格階段之 scope accretion**
（每輪為修洞而新增機制、下輪發現該機制未定死；同 `feedback_epic_convergence_breaker` 所載
P16 之形態）。**20 條中無一為新洩漏或架構錯誤**（composer：P0=0）。
已採對策：①新增機制時同一次編輯把完整形狀寫死；②新增 `<!-- SYNC-FORBID: 二擇一 -->`
（沿用既有閘、不新增工具），上線即抓到第三處未定案分叉（Task 1.3，委員三輪未抓到）。

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

## R11 之九群集（全部已落地；三家 Verdict 一致「需修訂後定版」）

| 群集 | 家數 | 落點 |
|---|---|---|
| A（P0）深度 map 之鍵集凍結時點未定、左項仍 scalar | codex | §D-3′-a（ii）鍵集凍結於匯入驗證後／prepare 前；Task 2.1b 左項改 `declared_window_bars[tf]` |
| B（P0）receipt hash 之輸入 dict 形狀未定 | **三家** | §D-3′-a（iii）寫死唯一 dict（`batch`／`event_level`／`per_tf`，鍵序與 row keyset 封閉） |
| C（P0）決定性 hash 擋不住 prepare 重入 | 兩家 | `PreparedAnalysisWindows` frozen 物件＋非決定性 `prepared_token`＋spy `call_count == 1` |
| D（P0）coverage 插入點與過濾對象未鎖 | codex | 唯一位置＝prepare 後／manifest 前；只吃 `allowed_event_ids` 過濾後之 (events, receipts) 配對 |
| E（P1）per-scope embargo 仍兩條路徑 | 兩家 | 寫死 `EventSplitConfig.embargo_ms_by_symbol`，與 scalar 互斥即 fail-closed |
| F（P1）`receipt_schema` migration 與 `pre_names` 未定 | 兩家 | namespace-aware typed schema ＋ `flatten()` traversal ＋ root scalar 反例 |
| G（P1）G-3 舊三段鏈；條 5 缺小時命名鏡像 | **三家** | 改引用五階段；條 5 拆 (a)(b)(c)；mutation 五→七 |
| H（P1）Task 7.6 `t0`／`label` wire shape 互斥 | 兩家 | 改兩個各自 typed array，元素鍵集互不含對方 |
| I（P1）locus 閘三個新自欺點 | 三家各一 | 非法行 fail-closed／弱證據須意圖佐證／意圖來源排除 SYNC-LOCI 本身；測試 13→17 |

🔴 **主委不再自行第四次改 `patch_locus_check` 之 anchor 判準**——R9／R10／R11 三次改判準
**每次都引入新洞（3/3）**；剩餘之結構性摩擦列為 R12 議題一交委員裁定。

---

## 🔴 立即待辦：派 R11

- brief／facts／locus 三檔沿用 R11（`…-r11-*`）改輪次；
  locus 腳本之 `--diff-base` 預設值須改為 **R11 落地 commit 之父**。
- 🔴 **R12 議題一＝anchor 判準之結構性摩擦**（主委已三次改判準、3/3 引入新洞 ⇒ 不自行改第四次）：
  委員 anchor 常是**段落指標**，而正確套用往往是「在該段旁邊加字」而非改動 anchor 那一行
  ⇒ 現行「anchor 須出現在 diff hunk」使大量**已正確套用**之 locus 仍紅。
  請委員裁定判準（候選：diff 落在 anchor 所在行前後 N 行內即算；或 anchor 改為行號範圍）。
- R12 應續問：九群集之落地有無新的內部矛盾；scope accretion 是否已止（看 findings 是否
  仍集中在「上一輪新增的名詞」）。

---

## FROZEN 四條件（唯一終點；輪數無上限）

| # | 條件 | 現況 |
|---|---|---|
| ① | 正確性／洩漏／接線類 OPEN P0＝0、P1＝0 | ⬜ 待 R12 複審 |
| ② | 本輪主委自傷絕對數＝0 | ⬜ R11 為 **9** |
| ③ | A-6′ 經使用者確認 | ✅ 已滿足 |
| ④ | `gap3ux_pre_review.sh <patch.md>` rc=0 | ⬜ 查法：`bash scripts/gap3ux_pre_review.sh handoffs/patches/20260823-gap3ux-r11-*.md`；殘項為 anchor 機制之結構性摩擦（見 R12 議題一），**非內容未套** |

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
| R10 | 11（7 群集） | 7 | 裁決錯誤（未驗邊界）／留下不可行選項／只寫敘述無算法 |
| **R11** | **20（9 群集）🔴 反轉上升** | **9** | **scope accretion：新增機制未定死其形狀** |
| R8–R11 落地 | —（自查） | 2 ＋ 2 ＋ 2 ＋ 1 | 截斷／pipefail｜quotepath 測試兩版假綠｜anchor 判準錯＋hunk header 洩漏｜意圖來源含 SYNC-LOCI 本身（恆真） |

**Task 數**：R8→R9→R10→R11 皆 **42 → 42**（委員未新增 Task）。

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
- 🔴 **`git diff -U0` 之 `-` 行是弱證據**：同檔刪掉**無關**內容若恰含 anchor 字面即會通過
  ⇒ 弱證據須另有補丁包正文之意圖佐證；且**意圖來源必須排除 SYNC-LOCI 區段本身**
  （該區段就寫著 anchor ⇒ 拿它當佐證等於恆真）
- 🔴 **SPEC 內禁「二擇一」**：以 `<!-- SYNC-FORBID: 二擇一 -->` 機械強制；
  歷史／撤回敘事需帶既有豁免詞（撤回／已改／原寫／不得…）才不觸發
- 🔴 **`doc_format_precheck` 之樣板殘留偵測會吃掉整行 `...`**：程式碼區塊裡的省略號要改成註解
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
