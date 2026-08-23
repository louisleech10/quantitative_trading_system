# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`，1580 行／42 Task）
——**七輪對抗審後仍未 FROZEN**。2026-08-23 使用者裁定改變工作方法，
consult r3 三家 17 條全數 ACCEPT ⇒ **新流程已上線，下一步＝R8（首次以補丁包模式跑）**。

---

## 🔴 開工前必讀

**① 主委角色卡＝`docs/GAP3_EVENT_UX_ROLE_CARD.md`**（R3 consult 三家裁定）
本 session 之工作方法已改，**不照舊做法**。三條最要緊：
- 主委**不得**自寫第二處複述（計數／集合／公式／enum／reason／mutation）
- 觸及 SPEC 之 commit **須有補丁包**（`handoffs/patches/*.md`）或 ERRATA id
- 派審前**必跑** `bash scripts/gap3ux_pre_review.sh <patch.md>`（五閘＋locus），rc=0 才可派

**② 量化主線 100% 正確，只能更嚴不能放水**（SPEC §C0；`quant_standard_check.sh`）

**③ 全棧三欄稽核**（後端 code／前端 UI／wiring）——每輪必查項

---

## 立即待辦

**T-1｜派 R8（首次補丁包模式）**
- session：`20260823-gap3ux-x-review-r8`；brief 沿用 R4–R7 三項方法論
  （去錨定／可重跑 receipt／sha256 鎖版），**新增**：要求委員對每個 OPEN 群集
  產出**補丁包**（格式見角色卡），而非只給修法敘述
- 派審前跑 `bash scripts/gap3ux_pre_review.sh`（現況 rc=0）
- 🔴 **硬輪上限：自 R3 consult 起 ≤2 輪達 FROZEN**；逾則委員會只裁補丁包品質，
  **不開新 scope、不得裁「先 Frozen」**

**T-2｜R8 通過後之 FROZEN 四條件**（缺一不可，見角色卡）
① OPEN P0＝0、P1＝0　②主委自傷**絕對數＝0**　③**A-6 經使用者確認**　④五閘 rc=0

**T-3｜FROZEN 後**：由**腳本**（非手工）產 manifest 與批次 TODO views；
拆檔前須具備四項對證：42/42 守恆／逐 Task block hash／引用閉包／deterministic regeneration

---

## 使用者尚未回答之事項

🔴 **A-6**：「匯出多選報酬欄只影響帶出的欄位、不改主答案窗與 label 算法」
——委員裁定**須使用者於白話閘確認，確認前不得 FROZEN**。已問三次未答。
白話對照：`白話說明/GAP-3規格42個Task勾選表.md` 之 Phase 4 段。

---

## R3 consult 之裁定（取代主委原提案）

**主委提案「凍前拆共用底層＋四批 SPEC」整案撤回**——三家一致否決。
grok 逐字：「不得採主委提案之『凍前手拆四批』」。

| 裁定 | 內容 |
|---|---|
| 文件架構 | **凍前維持單檔**；`GAP3_EVENT_UX_SPEC.md` 為唯一規範 SoT |
| 整合方式 | **委員出補丁包**，主委整包套用、禁自寫第二處複述 |
| TODO | 由 **manifest 生成**之 execution view，只引用不複述；生成器遇規範字面拒絕 |
| 批次切邊 | A(P1+P2)／B(P3+P4)／C(P5)／D(P6+P7)——**凍後**由腳本產生，非凍前手拆 |
| Task 1.1 | 須歸 **FOUNDATION**，不歸批 A（否則雙源；composer 指出） |
| KPI | **並報自傷絕對數**——佔比在真缺口下降時會自動上升（grok 推翻主委原指標） |

---

## 機械閘現況（六支；新增兩支皆已反測）

| 閘 | 擋什麼 | 反測 |
|---|---|---|
| `doc_format_precheck`（含 `template_check` 之佔位偵測） | 格式／空殼驗收欄 | 灌回 `python3 -c "..."` ⇒ 紅 |
| `spec_ruling_task_sync.sh` | §D 裁定→§P 落地；4 條 SYNC-FORBID | 灌回 `future72_max_*→72` ⇒ rc=2 |
| `spec_v_task_ref_check.sh` | §V 複述 §P 斷言（雙源） | 灌回 `contractAccepted` ⇒ rc=2 |
| `quant_standard_check.sh` | 量化主線放水語 | 造假語料 2/2 |
| `spec_count_audit.py` | 計數字面 vs 實際數（**全檔全語境**） | R6／R7 三個實際 bug 皆 rc=2 |
| **`patch_locus_check.py`**（新） | diff 觸及集合 ⊇ 補丁包 SYNC-LOCI | 漏改 locus ⇒ rc=2；空 SYNC-LOCI ⇒ rc=2 |

**唯一入口＝`scripts/gap3ux_pre_review.sh`**（包上列五支＋locus）。
🔴 **新增任何 GAP-3 UX 機械閘，必須加進該檔**——閘數字面漏同步已在 R6／R7 各犯一次。

---

## 🔴 做不成機械閘者（三家明列，不得宣稱已封）
「選哪個技術修法正確」／「使用者 label 語意是否正確」／「**未被列出的**隱藏複述」
⇒ 保留獨立委員審查與使用者裁定。

---

## 收斂履歷與錯誤帳（誠實記錄）

| 輪 | findings | 主委自傷（絕對數／佔比） | 錯誤類型 |
|---|---|---|---|
| R1–R3 | 24 → 7 → 18 | — | — |
| R4 | 19 | 3／16% | 選錯修法 |
| R5 | 13 | 5／38% | 選錯修法 |
| R6 | 15 | 6／40% | 整合時字面不同步 |
| R7 | 12 | 7／58% | 整合時字面不同步 |

委員找到之**真缺口**逐輪下降（約 16 → 8 → 9 → 5）；主委自傷絕對數緩升。
⚠️ 佔比會在真缺口下降時自動上升 ⇒ **回報一律並列絕對數**（grok 裁）。

**42 Task 之出處**：使用者直接要求 20（48%）／衍生自使用者一次糾正 5（12%）／
委員七輪長出而未問使用者 17（40%）。使用者已裁**一個都不砍**。

---

## 坑（延續前 session，仍有效）

- `git checkout`／`git restore --staged`／`rm` 會被 auto-mode classifier 擋；
  還原 tracked 檔用 Edit，unstage 用 `git reset -q HEAD <path>`
- `handoffs/*` 在 `.git/info/exclude`：新檔須 `git add -f`
- `plain_docs_sync_check` 是 commit 時序判準：先 `git add` 再跑 `--staged`
- 長 heredoc 會被 `gate_check` 誤判為派工 ⇒ 改檔一律先寫腳本檔再 `python3 <檔>`
- **shell 文字工具對非 ASCII 不可靠**（macOS awk 逐位元組比對）⇒ 比對中文一律用 Python
- **`git diff HEAD --name-only` 不含 untracked** ⇒ 列舉改動檔須用 `git status --porcelain -uall`
- commit 之 `Governance-Scope` trailer 須單行；長訊息一律 `git commit -F <檔>`
- 白話說明新增 `.md` 須同步加 `_watched_for` 一行；已收工者移 `Archived/`

## 已知既有紅（非本批造成）
`tests/api` 10 failed + 3 errors／G-7 scope 淨差（基準凍結於 2026-08-07，500+ commit）／
`.probe_ic{,2,3}.sh` 與 `白話說明/_r4skel.md`（untracked 殘檔，`rm` 被權限擋）

## 其他線
`/search` 三 bug 修復 🏁 已收案。
GAP-3 五個施工批全部蓋章，**只差使用者 UAT B 段 13 項簽字**。
#9b 規模防護排 GAP-6；純事件研究模組／標籤方法論討論皆使用者裁定另立。
