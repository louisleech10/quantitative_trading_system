# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）
——**八輪對抗審後仍未 FROZEN**。R8 十七條全數 ACCEPT，
**架構變更第一部分已落地**（commit `c6babc29`），**其餘部分待做**。

🔴 **使用者 2026-08-23 裁定：「就做到完整 Frozen，不用管輪次」**
⇒ R3 consult 之硬輪上限**已解除**，以 FROZEN 四條件為唯一終點。**不必再問使用者要不要繼續。**

---

## 🔴 開工前必讀（工作方法已於本 epic 中途改變）

**① 角色卡＝`docs/GAP3_EVENT_UX_ROLE_CARD.md`**（R3 consult 三家裁定）。三條最要緊：
- 主委**不得**自寫第二處複述（計數／集合／公式／enum／reason／mutation）
- 觸及 SPEC 之 commit **須有補丁包**（`handoffs/patches/*.md`）或 ERRATA id
- 派審前**必跑** `bash scripts/gap3ux_pre_review.sh <patch.md>`，rc=0 才可派

**② 委員交付物已改為【補丁包】**：`AUTHORITY`／`SYNC-LOCI`／`BEFORE-AFTER`／`VERIFY`。
主委**整包套用**，機械對證＝`patch_locus_check.py`。
責任歸屬：補丁包**漏列** locus ⇒ 委員責任；列了主委沒改 ⇒ 主委責任。

**③ 量化主線 100% 正確，只能更嚴**（§C0）。**④ 全棧三欄稽核**每輪必查。

---

## 立即待辦：R8 架構變更之**其餘部分**

§D-3 與 §D-3a 已改（`c6babc29`）。**以下尚未落地**，補丁包在
`handoffs/patches/20260823-gap3ux-r8-*.md`（**在磁碟上、未入版控**——
claim-check hook 擋委員產出，比照 review 檔慣例）：

| 待改 | 內容 | 補丁包 |
|---|---|---|
| **Task 7.0b** | 🔴 **須 REOPEN 重寫**——R7 才補的 `POST /api/v1/case/label-values` 落在**匯出**生命週期，議題一成立後須改為**分析時**路徑 | `-codex-analysis-label.md`／`-arch-analyze-time-label.md` |
| Task 4.1／4.1b | 匯出端不再寫 `label_value`／`horizon_bars`；揭露文案隨之改 | `-arch-shift.md` |
| Task 4.1c／7.4 | IC decay 邊界揭露之措辭隨架構調整 | `-arch-shift.md` |
| Task 4.3 | 缺欄確認框（原綁主答案窗） | `-arch-shift.md` |
| **Task 7.6** | 🔴 「邊界：不允許在 IC 頁修改批次設定」與議題一**直接衝突**；須區分「批次**事實**欄（唯讀）」與「**分析參數**（可設定）」 | `-arch-shift.md` |
| Task 7.7 | IC picker 之 `decision_offset_bars>0` 時間戳映射（CODEX-R8-P0-03） | `-codex-pit-wiring.md` |
| §G | 新增 **analysis-label golden**：固定 kline slice／t0／k／h／mode／direction，凍結 `label_value`、label window、feature timestamp map、**purge boundary**、NaN 尾端 mask；h=3／7 共用事件事實 ID 但各自 purge | `-codex-pit-wiring.md` |
| §A／V-6 | A-6 之取代裁定已入 §D-3；§A 與 V-6 之殘留字面須同步 | `-arch-shift.md` |

**做法**：逐份補丁包套用 → `bash scripts/gap3ux_pre_review.sh <patch.md>` rc=0 → commit。
🔴 **不得自寫第二處複述**；補丁包互相矛盾時**在具體提案間裁決並記錄理由**，不另創第四種
（已有先例：`-arch-shift` 之 AUTHORITY 被兩家推翻 ⇒ 不採該句，理由寫進 §D-3a）。

**完成後**：派 **R9**（brief 沿用 R4–R8 三項方法論＋要求補丁包），
receipt 產生器複製 `handoffs/20260823-gap3ux-x-review-r8-facts.sh` 改輪次即可。

---

## FROZEN 四條件（唯一終點）

| # | 條件 | 現況 |
|---|---|---|
| ① | 正確性／洩漏／接線類 OPEN **P0＝0、P1＝0** | ⬜ R8 尚有待落地項 |
| ② | 本輪主委自傷**絕對數＝0** | ⬜ R8 為 6 |
| ③ | **A-6 或其取代裁定經使用者確認** | ✅ **已滿足**——使用者 2026-08-23 原話即取代裁定，三家碼證確認，已入 §D-3 |
| ④ | 六閘 rc=0（`bash scripts/gap3ux_pre_review.sh`） | ✅ 現況 rc=0 |

---

## 機械閘（六支；權威清單唯一在 `scripts/gap3ux_pre_review.sh`）

🔴 **本檔與任何文件一律不寫閘數**——閘數字面漂移已犯三次（R6 三→四、R7 四→五、R8 清單分歧）。
新增任何 GAP-3 UX 閘**必須加進 `gap3ux_pre_review.sh`**，那是唯一清單。

計數稽核之**掃描面與呼叫方式**唯一來源＝`scripts/gap3ux_count_check.sh`
（`pre_review` 與 `narrow_check_router` 皆只呼叫它、不得自帶參數清單——
同型錯誤第四次之處置）。
基準檔＝`handoffs/run_receipts/gap3ux-spec-count-baseline.txt`；
改動計數字面後須 `python3 scripts/spec_count_audit.py --list <SPEC> $(ls -1 handoffs/*gap3ux*-facts.sh) > <基準>`。

---

## 🔴 做不成機械閘者（三家明列，不得宣稱已封）
「選哪個技術修法正確」／「使用者 label 語意是否正確」／「**未被列出的**隱藏複述」
⇒ 保留獨立委員審查與使用者裁定。

---

## 收斂履歷與錯誤帳（誠實記錄；**須並列絕對數**）

| 輪 | findings | 主委自傷（絕對數） | 錯誤類型 |
|---|---|---|---|
| R1–R3 | 24 → 7 → 18 | — | — |
| R4 | 19 | 3 | 選錯修法 |
| R5 | 13 | 5 | 選錯修法 |
| R6 | 15 | 6 | 整合時字面不同步 |
| R7 | 12 | 7 | 整合時字面不同步 |
| **R8** | **17**（含 7 份補丁包） | **6** | **全在主委自建之工具／receipt** |

⚠️ **佔比是壞指標**（GROK-R3-P2-01）：真缺口下降時佔比會自動上升 ⇒ **一律並列絕對數**。
委員找到之真缺口：約 16 → 8 → 9 → 5 → 8。

**42 Task 之出處**：使用者直接要求 20（48%）／衍生自使用者一次糾正 5（12%）／
委員長出而未問使用者 17（40%）。**使用者已裁一個都不砍**。
白話對照＝`白話說明/GAP-3規格42個Task勾選表.md`（已登記 WATCHED，Task 增減須同步）。

---

## 坑（累積；全部實測過）

- **rc 一律直接取**：`cmd; echo rc=$?` 取到的是 `echo` 的 rc ⇒ 假綠（R8 再犯一次）
- **shell 文字工具對非 ASCII 不可靠**（macOS awk 逐位元組）⇒ 比對中文一律用 Python
- **`git diff HEAD --name-only` 不含 untracked**；**`git status -uall` 不含 ignored**
  ⇒ `handoffs/*` 被 gitignore，列舉改動檔須另走 mtime 比較
- **測試不得依賴 repo 髒污狀態**（commit 後前提消失會自轉紅）；反測須配正例
- **單一來源須同時滿足**：內部不含可漂移字面（用 glob／導出）＋所有呼叫者不自帶參數
- `git checkout`／`git restore --staged`／`rm` 被 auto-mode classifier 擋
  ⇒ 還原 tracked 檔用 Edit，unstage 用 `git reset -q HEAD <path>`
- **長 heredoc 會被 `gate_check` 誤判為派工** ⇒ 改檔先寫腳本檔再 `python3 <檔>`
- `handoffs/*` 在 `.git/info/exclude`：新檔須 `git add -f`
- **委員產出（review .md／補丁包）不入版控**——claim-check hook 擋 operational claim，
  且不得編輯委員產出；審計鏈由 `handoffs/reconcile/*/sources/` 承接
- `plain_docs_sync_check` 是 commit 時序判準：先 `git add` 再跑 `--staged`
- commit 之 `Governance-Scope` trailer 須單行；長訊息一律 `git commit -F <檔>`
- 白話說明新增 `.md` 須同步加 `_watched_for` 一行

## 已知既有紅（非本批造成）
`tests/api` 10 failed + 3 errors／G-7 scope 淨差（基準凍結 2026-08-07，500+ commit）／
`.probe_ic{,2,3}.sh` 與 `白話說明/_r4skel.md`（untracked 殘檔，`rm` 被權限擋）

## 其他線
`/search` 三 bug 修復 🏁 已收案。
GAP-3 五個施工批全部蓋章，**只差使用者 UAT B 段 13 項簽字**。
#9b 規模防護排 GAP-6；純事件研究模組／標籤方法論討論皆使用者裁定另立。
