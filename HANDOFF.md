# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）
——**R9 十四條全數落地**，**待派 R10**。SPEC 2158 行、**42 Task（未增未減）**。
sha256 `a376ecfe…`（R10 審查期間不得動該檔）。

🔴 使用者 2026-08-23 裁定：**輪次上限已解除**、**42 個一個不砍**、**A-6′ 已確認**
⇒ 三者皆**不必再問使用者**。FROZEN 之後停下來等使用者，不自行往 TODO／實作走。

---

## 🔴 開工前必讀

**角色卡＝`docs/GAP3_EVENT_UX_ROLE_CARD.md`**：主委不得自寫第二處複述／
觸及 SPEC 之 commit 須有補丁包或 ERRATA id／派審前跑 `bash scripts/gap3ux_pre_review.sh <patch.md>`。
🔴 **任何文件一律不寫閘數**；權威清單唯一在 `gap3ux_pre_review.sh` 之 `run` 呼叫序列。
🔴 **補丁包之 anchor 須為該檔當前內容之字面**；stage 後綴 `@spec/@doc/@harness/@impl`
（缺省 `@spec`），未達之 `@impl` 為 DEFERRED；呼叫端只有 `--also-impl` 這個**加寬**旗標。

---

## R9 之八群集（全部已落地；三家 Verdict 一致「需修訂後定版」）

| 群集 | 家數 | 落點 |
|---|---|---|
| **A**（P0）purge 混用單位、無逐列 ms 換算 ⇒ 洩漏 | **三家** | §D-3′-a（ii）權威式；Task 7.0b ⑨ 四組 fixture；§G G-3 ④ |
| **B**（P0）分析時 receipt 未定義 ⇒ h=7 在 h=1 舊 window 建 split | codex | **§D-3′-a（iii）五階段**；§D-3a 改純引用；Task 7.0b ④⑩；Task 7.7 ③；G-3 ⑥ |
| C（P1）§F-2′ reason 登記處自相矛盾 | **三家** | 刪 R6 殘段，只引用 Task 1.1 |
| D（P1）Task 7.6 事實欄與 detail 鍵集互斥、`direction` 歸屬 | 兩家 | Task 7.6 **三分權威表**；formatter 改**欄位級 registry**；Task 7.3 同步 |
| E（P1）depth=0 之 floor 與真實深度混淆 | codex | 新增 derived 欄 `lookahead_bars_declared`；Task 1.1 ⑤⑦／2.1b／1.9／4.1／4.1b |
| F（P1）`pre_gap3.json` fixture 無建立步驟 | codex | Task 1.1 寫死 `cp`→`cmp`→`shasum` 順序＋immutable＋驗收⑥ |
| G（P1）`h` 以匯出深度欄種子化 | grok | Task 7.0b ③／Task 7.6 表：初始值＝常數 `1`；驗收⑦ |
| H（P1）locus 閘缺 stage＋CJK 假紅 | **三家**裁定＋grok | `patch_locus_check.py`（quotepath／stage／anchor 字面閘）；角色卡；測試檔擴充 |

**三個主委裁決點經三家覆核＝全部裁對**；兩處主委補充中（i）被推翻（改群集 E）、（ii）方向對但換算未閉合（改群集 A）。

---

## 🔴 立即待辦：派 R10

- brief 沿用 R9（`handoffs/20260823-gap3ux-x-review-r9-brief.md`），改輪次；
  facts 產生器複製 `…-r9-facts.sh` 改輪次；`…-r9-locus.sh` 同理。
- 🔴 **R10 brief 須新增要求**：補丁包之 SYNC-LOCI **必須標 stage 後綴**，
  且 anchor 須為可 grep 之字面（R9 已落地機械閘，未標＝預設 `@spec`）。
- **locus 現況之查法**（不在此複述結果，跑一次即知）：
  `bash scripts/gap3ux_pre_review.sh handoffs/patches/20260823-gap3ux-r9-*.md`。
  已知殘項為兩個 `@impl` 性質之 locus（`event_import_contract.json#receipt_schema`、
  `pre_gap3.json#version`——皆 Task 1.1 實作時才會動）；委員撰寫時 stage 機制尚未存在
  故未標，預設 `@spec` ⇒ **屬委員責任、非主委漏套**，R10 起補標即消。

---

## FROZEN 四條件（唯一終點；輪數無上限）

| # | 條件 | 現況 |
|---|---|---|
| ① | 正確性／洩漏／接線類 OPEN P0＝0、P1＝0 | ⬜ 待 R10 複審（R9 兩條 P0 已落地，須反例重跑確認閉合） |
| ② | 本輪主委自傷絕對數＝0 | ⬜ R9 為 **7** |
| ③ | A-6′ 經使用者確認 | ✅ 已滿足 |
| ④ | `gap3ux_pre_review.sh <patch.md>` rc=0 | ⬜ 見上「locus 現況之查法」 |

---

## 🔴 做不成機械閘者（三家明列，不得宣稱已封）
「選哪個技術修法正確」／「使用者 label 語意是否正確」／「**未被列出的**隱藏複述」
／**R9 追加**：「委員把 spec locus 誤標 `@impl`」（與 anchor 精確度同類，屬委員責任）

---

## 收斂履歷與錯誤帳（**須並列絕對數**；佔比是壞指標 GROK-R3-P2-01）

| 輪 | findings | 主委自傷（絕對數） | 錯誤類型 |
|---|---|---|---|
| R1–R3 | 24 → 7 → 18 | — | — |
| R4 → R7 | 19 → 13 → 15 → 12 | 3 → 5 → 6 → 7 | 選錯修法 → 整合字面不同步 |
| R8 | 17 | 6 | 全在主委自建工具／receipt |
| R8 落地 | —（自查） | 2 | 報告層截斷；pipefail 假綠 |
| **R9** | **14（8 群集）** | **7**（計入 quotepath 則 8；兩種算法皆列，不擇有利者） | 單位換算／階段未定義／殘段未刪／鍵集互斥 |
| R9 落地 | —（自查） | 2 | locus 列表 pipefail 假綠；**quotepath 回歸測試連兩版假綠** |

**Task 數**：R8→R9→R9 落地皆 **42 → 42**（本輪委員未新增 Task）。

---

## 坑（累積；全部實測過）

- **rc 一律直接取**：`set -o pipefail` 下 `cmd | grep … || echo '全達'` 會在有缺口時照印「全達」
- **報告層截斷＝fail-open**：`sed -n '1,6p'` 會把後面的紅吃掉
- 🔴 **`git diff --name-only` 預設 `core.quotepath=true`** ⇒ CJK 路徑輸出成八進位字面，
  與 UTF-8 路徑永不相等（機械閘假紅）。**所有 git 呼叫一律 `-c core.quotepath=false`**
- 🔴 **寫「假紅／假綠」之回歸測試時，先確認 fixture 真的會走到那條路徑**：
  quotepath 之測試連兩版假綠——①未追蹤檔走 `git status -z`（本就不 quote）
  ②tmp repo 但未壓 mtime（`is_touched` 之 mtime 回退把它救綠）。第三版壓 mtime 才真紅
- **`doc_format_precheck` 之空殼偵測按「行」判**：續行以 `**` 開頭會被當 bullet；
  該行若含「驗證」二字又無數字／`pytest`／`==` 等 token ⇒ 判空殼
- **`verify_pretooluse` 掃 HANDOFF 之 operational claim**：寫「N 份全綠」這類結果宣稱會被擋
  （HANDOFF 零豁免）⇒ 改寫成「查法＋命令」而非結果
- **shell 文字工具對非 ASCII 不可靠**（macOS awk 逐位元組）⇒ 比對中文一律用 Python
- **`git status -uall` 不含 ignored**；`handoffs/*` 在 `.git/info/exclude`，新檔須 `git add -f`
- **委員產出（review／補丁包）不入版控**；`handoffs/reconcile/*/sources/` 承接審計鏈
- `debt_clear` 要求 `sources.lock` 之 `mode == review`；
  `bash scripts/reconcile_build.sh <session> --mode review --rebuild` 可就地升級
  （**不得**同時傳委員檔）
- `git checkout`／`rm` 被 auto-mode classifier 擋；`cd <絕對路徑>` 觸發分類器
- `plain_docs_sync_check` 是 commit 時序判準：先 `git add` 再跑 `--staged`
- commit 之 `Governance-Scope` trailer 須單行且在**最末段**；長訊息一律 `git commit -F <檔>`

## 已知既有紅（非本批造成）
`tests/api` 10 failed + 3 errors／G-7 scope 淨差（基準凍結 2026-08-07）／
`.probe_ic{,2,3}.sh`（untracked 殘檔，`rm` 被權限擋）

## 其他線
`/search` 三 bug 修復 🏁 已收案。GAP-3 五個施工批全部蓋章，只差使用者 UAT B 段 13 項簽字。
#9b 規模防護排 GAP-6；純事件研究模組／標籤方法論討論皆使用者裁定另立。
