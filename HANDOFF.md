# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）
——**R12 十五條全數落地**，**待派 R13**。SPEC 2618 行、**42 Task（未增未減）**。
sha256 見 `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`（R13 審查期間不得動該檔）。

🔴 **findings 走勢 17 → 14 → 11 → 20 → 15**。R12 三家**自行歸因**之絕對數：
**(N) 新缺口 2／(A) accretion 13／(R) 回歸 0** ⇒ **(A) 仍占 13/15**，
主委 R11 之對策①②**經三家判定不足**。
⇒ R12 給出 **scope accretion 入口閘**（已寫入角色卡新節）：
① 一個 Task 只能有一個可執行 owner，新增要求只能擴充其 schema／測試，
   **不得**再增第二個 producer／transport／receipt／encoder／parallel fixture；
② 機制入 SPEC 之前置＝同一份補丁包內須同時提供
   **owner／shape／consumer／negative mutation／SYNC-LOCI** 五者；
③ 🔴 這是**入口閘，不是刪 Task 之授權**。

🔴 **anchor 判準：三家裁定「維持現行」，並背書主委不改第四次**
（候選 (a) 前後 N 行、(b) 行號區間皆被否決）。改的是**委員寫法責任**：
anchor 須指向會被改動／已寫入的**那一行字面**；指到未改動之段落標題**歸委員責任**。

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

## R12 之七群集（全部已落地；三家 Verdict 一致「需修訂後定版」）

| 群集 | 家數 | 落點 |
|---|---|---|
| **A**（P0）`PreparedAnalysisWindows` frozen ／寫回 ／`is` 同一物件**三者不可同時成立** | **三家** | `allowed_event_ids` 初值＝全集；新增 `apply_event_coverage()` 以 `dataclasses.replace` 回傳新物件；驗收⑩之 `is` 對象改為 coverage 後之 `prepared1` |
| B（P1）Task 1.3 digest 定案未接線、驗收④⑤仍要前端各算一次 | 兩家 | 刪互斥條；補端點 `POST /api/v1/case/source-digest` 之承載；**時序定案＝匯出當下算、匯入只比對** |
| C（P1）coverage 剔除整 TF 後鍵集保留**無 fixture／mutation** | **三家** | Task 7.0b ⑭(f)＋mutation |
| D（P1）prepared 無 per-TF surface | codex | 增 `.per_tf` typed tuple；驗收⑩(v) 三處讀同一份 |
| E（P1）spec 未綁定 ⇒ h=7 prepare ＋ h=3 resolve 仍同 hash | codex | 增 `.normalized_spec`；不相等即 fail-closed；驗收⑩(iv) |
| F（P1）`allowed_event_ids` 初值未定 | composer | 併入 A；驗收⑭(e) |
| G（P2×2）derived 欄名不一致／hour-named fixture 只寫「鏡像」 | codex | 正名；改共用具名 fixture `fixtures/hour_named_mixed_tf.json` |

---

## 🔴 立即待辦：派 R11

- brief／facts／locus 三檔沿用 R12（`…-r12-*`）改輪次；
  locus 腳本之 `--diff-base` 預設值須改為 **R12 落地 commit 之父**。
- 🔴 **R13 brief 須把角色卡新增之「scope accretion 入口閘」與「anchor 寫法」列為硬性要求**，
  並續要求三家做 (N)/(A)/(R) 三類歸因之絕對數（看 (A) 是否下降）。

---

## FROZEN 四條件（唯一終點；輪數無上限）

| # | 條件 | 現況 |
|---|---|---|
| ① | 正確性／洩漏／接線類 OPEN P0＝0、P1＝0 | ⬜ 待 R13 複審 |
| ② | 本輪主委自傷絕對數＝0 | ⬜ R12 為 **7** |
| ③ | A-6′ 經使用者確認 | ✅ 已滿足 |
| ④ | `gap3ux_pre_review.sh <patch.md>` rc=0 | ⬜ 查法：`bash scripts/gap3ux_pre_review.sh handoffs/patches/20260823-gap3ux-r12-*.md`；R12 補丁包寫於本輪 anchor 裁定**之前**，anchor 多為段落指標 ⇒ 依裁定歸**委員責任**，R13 起補丁包須照新寫法 |

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
| R11 | 20（9 群集）🔴 反轉上升 | 9 | scope accretion：新增機制未定死其形狀 |
| **R12** | **15（7 群集）** | **7** | **同上；三家歸因 (N)2／(A)13／(R)0** |
| R8–R11 落地 | —（自查） | 2 ＋ 2 ＋ 2 ＋ 1 | 截斷／pipefail｜quotepath 測試兩版假綠｜anchor 判準錯＋hunk header 洩漏｜意圖來源含 SYNC-LOCI 本身（恆真） |

**Task 數**：R8→R12 皆 **42 → 42**（委員未新增 Task）。

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
- 🔴 **多條約束加在同一物件上，最後要問「能同時成立嗎」**：R11 之
  frozen ＋ 寫回 ＋ `is` 同一物件，三個好理由加起來是 Python 做不到的事
- 🔴 **「我定案了」≠「規格有可執行路徑」**：定案時同一次要①刪互斥舊條②指定 Task 承載
  ③把時序／觸發點寫死；少一件下輪必被歸為 (A) accretion
- 🔴 **「鏡像／對應／保持一致」不是機制**：兩處要一致就得**讀同一個具名物件**
  （這次副本長在測試 fixture 上）
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
