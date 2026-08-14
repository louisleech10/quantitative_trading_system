# ROADMAP 細節 — 敘事與歷史（**不是「下一步」**）

> 🔴 **這份不是狀態，是敘事。** 要知道「現在在哪、接下來做什麼」看 `docs/ROADMAP.md` 的狀態表。
>
> **為何拆出來（2026-08-14 使用者：「ROADMAP 裡面看起來還是亂七八糟」）**：
> 拆之前 `ROADMAP.md` 227 行、其中「進行中／下一步」一節就佔 213 行——
> 要回答「我在哪」得讀 213 行混在一起的敘事。⇒ 狀態與敘事分離。
>
> 🔴 **拆檔的已知風險，本次已具名防範**：2026-08-05 的 `aae04295` 把 ROADMAP
> 由 393 → 111 行、「敘事移出 Archived」，**整條量化主線的下一步跟著被砍掉**，
> 十天內沒人發現。本次拆檔後**逐項對帳**：拆前每一個 `###` 標題，
> 必須在 `ROADMAP.md` 或本檔找得到（見 `ROADMAP.md` 狀態表之「細節」欄）。
>
> 🔴 **搬進本檔不等於作廢**。要作廢請明寫「已作廢」，不要靠「搬走」暗示。

---

### P1-6 委員未結案債狀態機 — **狀態：B5 未完工（🔴 線 C 未做）**

> **本節只寫當前狀態。**322 行敘事歷史已於 2026-08-05 移出至
> `docs/Archived/ROADMAP_P16_NARRATIVE_20260805.md`（逐字保留）。
> **移出原因**：使用者指出「ROADMAP 要更新到最新狀態，過期／被推翻的要移除」，
> 且該節已成流水帳，**實際造成誤讀**——使用者一度以為線 C 已完成而據以往後推進。

| 項目 | 狀態 |
|---|---|
| B1 registry v2 契約＋lock identity binding | ✅ `8a12c36` |
| B2 `audit_append.sh` 唯一寫入點 | ✅ `9bfcb58` |
| B3 `committee_run.sh` 開債＋`cx_run.sh` 記每家結果 | ✅ `f98862c` |
| B4 `debt_ledger.sh` 只讀帳本＋`debt_clear.sh` 唯一銷帳路徑 | ✅ |
| B5 線 A（prefilter 吞壞行）| ✅ 已修並經主委獨立變異複驗 |
| B5 線 B（凍結文件修訂程序）| ✅ `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md`，三家戳記 `a36725a55cd3` |
| **B5 線 C（債務事件分檔）** | 🔴 **未做 — 已排入「第 0.5 批」（使用者 2026-08-05 拍板：第 0 批完成後的下一個）** |
| B5 Task 3.2（mutation 探針＋回歸）| 🔴 未做 |
| `P16-GATE-D1-STRUCTURED-VERDICT`（`gate.sh:246` Verdict 正則過鬆）| 🔴 未做，B3 遺留必做項 |

🔴 **B5 完工 ＝ 線 C ＋ Task 3.2 都做完；線 C 閉合前 B5 一律 NOT-CLOSED。**

**線 C 的正當理由（勿再誤述）**：**不是效能**（效能立論已於 2026-08-02 實測推翻：
`debt_ledger --has-open` 對 30,960 行實跑 46–64ms，SPEC 要求 <100ms，早已達標）。
真問題是**資料壽命混裝**（草案 §2）：債務事件因序號連續性 fail-closed 而**永遠不可刪**（289 筆），
其餘 30,671 行本可自由輪替卻綁在同一檔。**目的＝能讀到乾淨的帳本，避免讀錯又重來。**

**2026-08-05 實證（線 C 的成本已在發生）**：`audit.log` **34,000 行**；
`debt_ledger --list` 吐 **182 個 round**（ABANDONED 146＝**80%**、CLOSED 36）。
主委當晚**實際讀錯一次**——以 session 名 grep 撈 round id 撈到已 ABANDONED 的舊筆，
得 `ERROR: round 已 ABANDONED（不可逆）` 後改 `grep OPEN` 重來；
且每次銷帳都得從 182 行裡 `sed` 撈唯一 OPEN。**帳本已無法直接讀。**

**草案**：`handoffs/20260802-LINEC-AUDIT-SPLIT-SPEC-DRAFT.md`（方案 B 為主委建議）。
**排期**：**第 0.5 批**（第 0 批完工後立即），使用者 2026-08-05 拍板。開工前須先確認第 0 批 Phase 0
已定案的 `gate_deny` schema（`scripts/audit_events.json`），線 C 的歸檔規則以它為輸入。

**已完工的獨立票（原在本節，保留為 pointer）**：
`GOV-STAMP-TASKID-INJECT` ✅（`task_id` 注入＋戳記自動 register-output）／
`GOV-DOC-CHECK-AT-WRITE` ＋ `GOV-DEXT-TEMPLATE-KIND` ✅ `901a8d9`（格式檢查移到產出端，512→563 passed）。
兩票暴露的制度缺陷已開票：`B-9 GOV-DOCS-STAMP-PROVENANCE`。

- **✅ GOVFLOW epic — 派工控制流四缺陷 A-1..A-4 全數完工（2026-08-04）**：
  B0 manifest 生成器 `0d0f3a0`／B1 heading 誤報＋四步程序 `d36d76b`／
  B2 `result_state` 三值＋emit 順序＋P16 v3.0（R 重開）`c0a7004`／
  B3 角色檢查前移＋`scripts/_role_gate.sh` `2696e77`／
  **B4 claim checker 委員逐字豁免 `6a06f0c`**。`pytest tests/governance` **617 → 701 passed**。
  - **B4 走 6 輪**（實作→NO-GO 7 條→修補一→複核→修補二→複核→收窄→複核）。
    輪 5 的修法把豁免擴到**一般原檔與 format-failed 產出**（實測同一原檔 rc 由 1 變 0），
    由 `CODEX-R15-P1-01` 抓出；輪 6 收窄為「`committee_family_result` 只供 `sources/` 回退
    ＋須 `result_state=success`」。輪 6 由**主委自實作**（使用者核准），雙家族仍為非實作者。
  - **實測回歸**：85 份真實收斂檔違規 **26→16 條、18→12 檔**。
  - 🔴 **殘留（是未完成，勿當已解）**：**A-4 全域未解**——主委摘要／群集段無 backing 的 claim
    仍不能 commit ⇒ **12 檔仍有違規**，缺口＝摘要段需 backing 或更窄豁免（另案）；
    **12 個非 M code mutation 未逐一執行**。
  - **本 epic 內 TODO §0 數字對照表漂了四次**（四格曾錯三格：`25/9/13/14` → `25/13/20/26`）
    ⇒ 佐證 `票 B-17`（機器依賴表格改資料檔＋自動生成）：只要它還是手寫的就會再漂。
  - 全部票登記於 `handoffs/20260801-GOV-AMEND-BACKLOG.md`（`B-1`～`B-36`，**唯一票登記處**）；
    白話版 `白話說明/治理待辦總覽.md`（主表一票一列；兩份已機械對帳）。
    🔴 **給使用者看的文件一律放 repo 根目錄 `白話說明/`**（使用者 2026-08-05 定，原在 `handoffs/` 已搬移）。

- **🔵 治理 backlog — 票池**：
  **55 張**（導出命令：`grep -c '^## B-' handoffs/20260801-GOV-AMEND-BACKLOG.md`，2026-08-11 實跑；
  🔴 **不寫死**——每輪都在新開，讀本行前請自己跑一次）。
  08-11 新開：`B-54`（戳記 64 位 hex 由委員手抄，已實際掉字一次）、
  `B-55`（旗標空值處置不一致：只有 `--spec` 擋空值）、
  `B-56`／`B-57`／`B-58`（站 4 量出的詞法層殘留：`extract_inners`/`extract_cmdsubs` 逐字迴圈、
  `parse_heredoc_delim` 全尾切 500K 需 434 秒、前導空行被丟棄且是否為缺陷未判定）。
  🔴 **執行順序不看本檔**：唯一來源＝`docs/GOVERNANCE_EXECUTION_ORDER.md` 之 generated block。
  站 2.5／2.6／2.7 已收案（2026-08-10～11）。站 4 之超線性修法已進主樹待雙家戳記，
  收據＝`docs/GOV_B3R_PHASE3_RECEIPT.md`（C-5 三條實測通過；行為四組差分逐位元組全同）。
  🔴 **對外宣稱限制**見 `docs/GOV_B3R_C5_RATIONALE_AMENDMENT.md`：實作為 O(n·√n) 非 O(n)；
  C-5 秒數門檻無可驗證威脅模型，不得宣稱修掉 fail-open；`B-56`／`B-57` 已降為低優先。
  三票（`B-25`／`B-37`／`b4`）**皆不得宣稱閉合**，殘留逐條見各收斂檔與 `docs/GOV_B4_STAGE2_AMENDMENT.md`。
  （下方 40 張與 08-05／08-06 統計為**歷史紀錄**，不再更新。）
  08-05 統計：✅2（`B-7`／`B-10`）｜🗑3（`B-1`～`B-3`）｜🔗3（`B-18`→`B-13`、`B-25`→`GOV-XREF-SYNC`、`B-36`→`B-13`）。
  08-06 新開：`B-39`（id-like heading 誤判，**近程序第一站**）、`B-40`（歸屬未驗證，**當日收掉**，後由 `B-16` 擴充 C 吸收）。

  🔴 **排序權威已於 2026-08-06 更替**：v3.1（08-04 全量重排）僅餘**批次歸屬**參考價值；
  **近程執行序以三家戳記定版為準** ⇒ `handoffs/reconcile/20260806-govamend-x-consult-r1/synth.md`
  （body hash `df82cd54109b3164d3da2f90b5a022b832dd4ba5036c384c18a37153aac9be6e`）：
  `B-39` → 阻塞鏈（`B-38`／`B-15`／`B-19`／`B-31`，即第 1 批）→ 群集 ID 登記（併 `B-26`）→ `B3R` → `B4`–`B7`。
  ⚠️ 下方批次表為 08-05 規劃，與近程序衝突時**以上述定版為準**（2026-08-06 使用者稽核指出兩者對不上，已標註）。
  🔴 **`B-16` 擴充並拆批**（使用者裁「可以在這幾票解決就合併」）：
  **擴充 A**（08-05）＝文件內可執行斷言寫檔當下須實跑比對（含機器標記須行首錨定）；
  **擴充 B**（08-05）＝文件引用的函式名／檔名須存在性檢查（**誠實邊界：擋不了「呼叫方向寫反」，具名殘留**）；
  **擴充 C**（08-06）＝**宣稱的量詞範圍 > 實際驗證的覆蓋範圍**——全稱／否定量詞句須帶
  `COVERAGE: <實跑數>/<母體數> <母體定義>`，缺欄或兩數與量詞矛盾 ⇒ rc=1。
  **吸收 `票 B-40`**（主委自造規則掛使用者名下＝該病的一個實例）；
  **誠實邊界：母體數由作者宣告，擋不住謊報**（擋意外不防蓄意，同 `B-23` 紀律）。
  三者**提前至第 1 批**（原條文散文契約偵測維持第 4 批），理由＝擋的是後面每批都會再犯的錯；
  實測：A／B 至少擋掉 **9 次**（08-05 session）、C 至少擋掉 **7 次**（08-06 session，其中 4 次原靠委員推翻）。
  ```
  第0批   摩擦止血    B-24(紀律面) → B-15 → B-14 → B-30 → B-32
  第0.5批 帳本可讀    P1-6 線 C（債務事件分檔；**非 B-x 票**，屬 P1-6 的 B5）
  第1批   機制        B-19 → B-29 → B-31 → B-38 → B-16擴充A/B/C
  第4批   散文與標記  B-16原條文 → B-23
  第1.5批 守衛漂移    B-33 → B-34              第5批 fail-open   B-11 → B-6 → B-5 → B-4 → B-8
  第2批   地基        B-27                     第6批 完整性監看  B-20 → B-21 → B-12 → B-22
  第3批   殺手寫漂移  B-17 → B-13(吸收 B-18/B-36) → B-26
  另排                B-9 → B-28 → B-35 → B-24(機械強制面)
  ```
  🔴 **第 0.5 批＝P1-6 線 C（使用者 2026-08-05 拍板排此位置）**。三個理由：
  ①**順序反了要重做**——第 0 批 Phase 0（Task 0.1）正是要改 `gate_deny` 的 schema 並寫進
  `scripts/audit_events.json`，線 C 的歸檔規則必須吃它的最終版；
  ②線 C 卡著 B5，B5 卡著整個 **P1-6 epic 結案**；
  ③第 1 批會再產生大量派工輪，帳本會再長一截。
  **不插進第 0 批**的理由：該 SPEC 已跑 4 輪剛收斂（19→17→11→8），加新範圍等於重開 scope accretion。
  🔴 **本行數字曾於 2026-08-05 漂移一次**（寫 32、實 36），故加註導出命令；
  **本 session 內同型計數漂移共 8 次**（SPEC 內 3 次、本檔 1 次、其餘在 TODO/收斂檔），
  全部指向 `票 B-17`（機器依賴表格改資料檔＋自動生成）。
  🔴 **`B-34` `GOV-STAMP-ROSTER-VS-ROLEGATE`（2026-08-05 戳記輪現場撞出）**：
  角色閘把 implementer（grok）排除在 `brief-kind: review` 之外，
  但 `reconcile_stamps_check.sh` 要求 `review_families` **全員**蓋章
  ⇒ 任何 review 輪的收斂檔，結構上都不可能由實際參與者蓋滿；被迫產出語意為空的形式簽核。
  因 implementer 恆為 review_families 成員，**這是必然而非偶發**。嚴重度與修法待委員裁定。
  🔴 **`B-33` `GOV-LOCALE-GUARD-DRIFT`（2026-08-04 SPEC 審查 R1 兩家一致裁定開票，MAJOR，排第 1 批之後）**：
  `LC_ALL=C` 下 `gate.sh` 的 Verdict 守衛與 `doc_format_precheck.sh` 雙雙 **fail-open**（實測 2 例），
  `template_check.sh spec` 則誤報（1 例）。委員 CLI 與 CI runner 的 locale 不在主委控制範圍
  ⇒ 非 UTF-8 環境會**靜默失去**這兩道守衛。**本批不併入**（兩家一致，避免 scope 膨脹）。
  🔴 **`票 B-24` 拆分（SPEC 審查 R1 後主委裁 SPLIT）**：紀律面（驗收欄寫狀態斷言，零新增元件）留第 0 批；
  機械強制面（`acceptance_state_check.sh`＋grandfather SoT＋具名 owner／UTC 到期／到期後 fail-closed）移出獨立排期。
  🔴 **`B-30`／`B-31`／`B-32` 於 2026-08-04 第 0 批**偵察輪**當場撞出**（單輪 6 次摩擦、4 次無票）：
  `B-30`＝委員可覆蓋自己已寫好的產出（codex 因此多花 28 分）；
  `B-31`＝`format-failed` 後只能整份重跑，且擋住債務銷帳進而擋住所有派工；
  `B-32`＝`cx_run.sh:512` 無條件注入 RECONCILE-STAMP 指示，誘發 `completeness_check` 判違規
  ⇒ composer **連兩次** format-failed，**重跑不可能解決**。`B-32` 併入第 0 批（它正擋著第 0 批自己）。
  **批次化非一票一管線**：22 張各走完整管線 ≈66 輪；7 批＋1 另排 ≈24–30 輪。
  **2026-08-04 使用者裁決：治理優先於產品線**——「治理相關的沒做好，繼續專案開發只剩耗時間和 token
  在摩擦上」。8/1 起 `momentum/`／`api/`／`frontend/` 動 0 檔，此為已知且經同意。
  **進行中＝第 0 批**（`B-24`＋`B-15`＋`B-14` 合一批次，走完整大任務管線）。

## ✅ 近期已完成（2026-06 / 2026-07）
- **TEMPLATE_GATE_FIX epic（2026-07-05）**:派工品質防線修補——四方委員會(Claude+Codex+Composer+Gemini)審 template/機檢,實證 2 BLOCKING 繞過(FACT-RECEIPT/§G 逃逸)+多處範本↔機檢漂移;修=§A 段級狀態機+RISK-HIT 宣告制+per-Task 分段檢+RESULT 交叉規則+gate --reconcile 閉合鏈+adversarial 實核義務+TODO prompt 憲法瘦身(省每次 ~5,100 行)。驗收=14 fixture 矩陣+4 mutation+5 gate fixture+Codex 總 review 戳記。文件=docs/TEMPLATE_GATE_FIX_{BRIEF,SPEC,TODO,MANIFEST,GRANDFATHER}.md;現役文件 grandfather(僅新文件適用)。**新寫 SPEC 須帶 RISK-HIT: 宣告與 FACT-RECEIPT**。
- **FF 一致性整併**:Q5/B1/B2/B3/B5/B6/B4/B8(觀測性 + 批次日期修復 + warmup-then-trim + 批次刪除/保留 UX)。每項走完整管線。
- **Feature Explorer 圖表修復**:Y 軸貼合線 + Shift+滾輪 Y 縮放(rolling band 不撐爆 domain)。
- **d\* 實證量化**:三方證 Option A 非二階(cross-window selection 不穩),固定參考為修法(納入 P1 epic)。見 [[project-dstar-first500-optiona]]。
- **上線須留存參數盤點**:三方三輪 CONVERGED,產出 P1 epic 的精確範圍清單。見 [[project-stateful-param-audit]]。
### P0 — 制度層總審查 epic（憲法＋流程＋任務分類三層合審；2026-07-05 立案，**使用者定 P0：完成後才回其他任務**）
- **緣起**：TGF epic 證實「prose 規則靠記性必再犯、閘門規則違反不了」（驗證保真度鐵律在 context 內仍三防全破 vs 機檢上線後連編排者派工都被連擋）。使用者 2026-07-05 明示：鐵律非其偏好、是 agent 重複犯錯逼出的補丁，他無法判斷增刪——**裁決權交委員會證據裁決**（見 memory feedback-rules-are-scar-tissue）。
- **範圍三層**：①憲法內容/架構/儲存（CLAUDE.md 每 session 全載=最大固定 token 支出；四源重疊已實證分叉一次；copilot-instructions 739 行停在 2026-04-26；ARCHITECTURE/DEV_GUIDE 疑似漂移）②派工流程管線（本次實測摩擦：戳記輪×4、claim-check 擋 commit×5、provenance 流程中途才學會、同檔並發只能序列化）③小中大分類規則（多層補丁散在 CLAUDE.md＋記憶兩處）。
- **方法**：每條規則四選一證據裁決——機械化（再犯且可寫成 gate/hook/checker）／留核心原則／合併去重／淘汰（已被機檢取代）；判準=出生事故＋violation 紀錄（audit.log/handoffs/git），不靠感覺。委員會三方裁決＋白話簡述給使用者否決權；「不可砍清單」先行＋雙家族 adversarial 防瘦身誤傷。
- **時機（2026-07-05 使用者定案）**：P0 立即執行、完成後才回 IC 等其他任務；建議新 session 起跑（本立案 session context 已滿載 TGF 歷史）。流程=委員會 read-only 審查輪（三層各出 findings＋violation 證據考掘）→ 白話決策簡述給使用者否決 → 依裁決走完整管線實作。
- **裁決（2026-07-05 使用者）**：D-1/2/3/5/6 同意預設；**D-4 否決固定制**→執行端選層動態、以使用者當下指示為準（usage 切換、未來或加 Grok），文件只留單一可變「現行分工」行。附帶：否決點以後須彈窗（AskUserQuestion）+推播；總審查頻率=事件觸發+每季保底。→ **下一步=依裁決走完整管線實作（Phase A 憲法重構起）**。
- **狀態（2026-07-05）＝Phase A（憲法重構＋合約補齊）✅ 完成待 commit**：走完整大任務管線——SPEC/TODO（`docs/INSTREV_PHASEA_{SPEC,TODO}.md`，三道機檢過）→ 雙家族 adversarial（Codex 3+Composer 12 findings，含 2 BLOCKING）→ reconcile R2 雙戳記 APPROVED（sha256:6a14a0f6…）→ Composer 2.5 實作 → Codex code review 抓 2 BLOCKING（ORCH §6/§7 殘留 Codex 主力、三方鐵律過度壓縮掉義務）→ Composer 修 → Codex 閉合重驗雙 CLOSED。**成果**：copilot 739→8 行 pointer；CLAUDE.md 216→128 行（敘事移新檔 `docs/SCAR_LEDGER.md`，規則零刪減 grep 驗）；任務分派決策表單一化；執行端選層 ORCH §1 單一「現行分工行」（動態，現行=Composer 實作+Codex review）；合約補齊 5 項制度（兩輪斷路器/register-output/VERIFY claim/STAMP-BLOCKED/產物非指令）；輪詢統一 10 分鐘、debug 統一 2 輪（含 BOOTSTRAP 第 5 分叉源）；ARCH/DEV banner。**待辦**：無（Phase C 之 U-13 已完成；U-20/21 裁決本身=先別做，屬長期觀察項）。read-only 審查輪 reconcile=`handoffs/20260705-INSTREV-RECONCILE.md`（sha256:ee8c9fab…，含 U-3 errata）。


---

# 【自 HANDOFF.md 移入】治理 epic 之交接內容（2026-08-14）

> **移入原因**（使用者 2026-08-14）：「HANDOFF.md 還是一樣亂七八糟，這是交接要做的事情，
> 有需要寫這幾百行流水帳？而且後面上百行治理 epic 相關的，為何還寫在裡面？」
> ⇒ 交接檔只留「接手要做什麼」，治理 epic 的敘事、殘留清單、操作紀律全部移入本檔。
>
> 🔴 **移入不等於作廢**（同本檔檔頭規約）。回治理時來這裡查。
> 🔴 原本 `HANDOFF.md` 內的兩張治理投影表（`governance-worklist`／`governance-sot-plan`）
> **已自 HANDOFF 拆除宿主**——它們在 `白話說明/接下來要做什麼.md` 仍有一份，資料源不變。

# 🔴🔴🔴 待辦清單（唯一來源，機器投影——**本節不得手寫**）

> 改法：編輯 `scripts/fact_keys.json` 之 `governance-worklist` → 跑
> `bash scripts/gen_fact_key_blocks.sh --write`。**完成就把該列狀態改成 `收案`。**
> 欄名見表頭（亦為機械產物）。手寫狀態字面值會被 fail-closed 擋下。

**（表格已移除——它是 `scripts/fact_keys.json` 的機械投影，現行唯一宿主為 `白話說明/接下來要做什麼.md`。）**

## 🔴🔴 `WL-04` 之前置：票 SoT 統一與產出端覆蓋（**本節亦為機器投影，不得手寫**）

> 使用者 2026-08-13 定：治理票的**新增／刪減／修改／註解／狀態變更只能有一套**，
> 且**這些確保都完成才能進 `WL-04`**。
> 改法同上：編輯 `scripts/fact_keys.json` 之 `governance-sot-plan` → 跑 `--write`。
> **由上而下第一個未完成者即當前工作**；`S0.x` 全部是後續各階段的前置。

**（表格已移除——它是 `scripts/fact_keys.json` 的機械投影，現行唯一宿主為 `白話說明/接下來要做什麼.md`。）**

# 【治理·參考】若日後回到治理：做上表由上而下第一個尚未完成的項目

**做完後只改 `scripts/fact_keys.json` 該列的狀態欄，再跑
`bash scripts/gen_fact_key_blocks.sh --write`**，兩份文件同時更新。
本節刻意**不重述任何一列的內容**——重述就是副本，副本就會過期。
🔴 **不要在本檔任何地方手寫項目編號＋狀態值**——偵測器會擋（歷次前置皆實際擋下過）。

使用者 2026-08-12 夜間指示（逐字）：治理 epic **不寫 SPEC/TODO**，由 Opus 依本表直接實作，
三家委員 review＋adversarial＋討論，分歧由主委與委員共識決、不上呈；中途只 commit 不 push。

🔴 **不要再提「等使用者回答兩個問題」**——已作廢。問題 (b)（凍結檔授權）建立在
**錯誤量測**上：可執行 ASSERT 僅 2 行、兩份凍結檔 0 行，授權問題不存在。
量法錯在何處見 `docs/GOV_ASSERT_PATHA_NOTE.md` §2。

## 【治理·已完成，留存】那 10 件（使用者 2026-08-14T18:40+08:00 定死，當日已全部定案）

使用者原話：「**全部的票和腳本，該掛哪／為何沒掛／能不能掛，可以掛的就要掛上去，
只有掛和不掛兩種結果，不掛就要有原因，耗費時間太多也是原因。
沒有什麼可能、推理、想看看——你用推理都全錯。只有掛上和不掛兩種結果。
不是表格列出，是實際上線。**」

🔴 **禁止用推理回答「能不能掛」**——本日實測：推理四次全錯、實測兩次全中。
掛載能不能成立取決於**執行時的控制流**（誰先誰後、哪裡提早 return），讀碼看不出來。
實測法：真的掛上去 → 跑反例 → 看會不會擋。擋不住就拆掉並寫原因。

### ✅ 這 10 件已全部定案（`6c48fc73`，三家 review 16 條全數採納）

**掛上四項**（各經反例驗證，非宣稱）：`check_agent_contract_sync.sh`、
`extract_phase2_expected_flips.py --check`、`b49_closure_static_check.py`（票 `B-49` 之
靜態子集，新抽出）三支經新增的 `scripts/narrow_check_router.sh` 掛 `PostToolUse`；
`check_doc_anchors.sh` 掛 `pre-commit`（3.6 秒／次，窄化省不到，成本理由寫死）。
票 `B-48` 之登記列已補（`E-021`）。

**判定不掛三項**（理由寫死於腳本檔頭與 `docs/GOV_ACTIVE_MECHANISMS.md` §七）：
票 `B-7`／`B-32`／`B-50`（實測：`PostToolUse:Bash` **確實觸發**，但派工背景執行
⇒ 觸發當下委員產出檔尚不存在）、`draft_selfcheck.sh`（委員會 R4 裁定不得作安全邊界）、
`check_decoupling_imports.py`（見下方唯一未閉之缺口）。

🔴 **`check_decoupling_imports.py` 是唯一未閉的一項，且卡在別人身上**：
canonical Rule 2/3/4 的 scanner 自 2026-07-14 起 fail-closed 在戳記關卡，**從未掃過**。
grok 本輪已獨立審查並自行戳記，但 `verify_task_provenance` 要求審計中有指向
**被戳記檔本身**的 `committee_output`，而 `register-output` **只收 `handoffs/` 內的檔**
⇒ `handoffs/` 外的受戳記資產，新戳記在現行機制下**無法通過 provenance**
（既有兩枚是走 legacy allowlist 豁免，不是真的通過）。
掛載前置已備妥（`--baseline` 模式＋`scripts/decouple_baseline.txt` 20 筆＋10 條測試）。
🔴 **不得以修改該判準來讓自己過關**。詳見 `docs/GOV_ACTIVE_MECHANISMS.md` §七.1。

### 🔴 43 張未開工票不在這 10 件內

它們**沒有產物**，「掛不掛」對它們沒有意義。真正的問題是**改法沒做**——
那是排程決策（做或不做），**需要使用者定，不是技術判斷**。

## 🔴🔴 推送與具名欠缺

**推送**：使用者 2026-08-14T14:20+08:00 指示「先停下，不要 Push」。
⇒ **一律不推，等再次明示**。筆數直接查。

✅ **前一批「未經三家 review」已補**：本輪 `20260814-govmount-x-review-r1` 三家合審
兩批（含 `gate_check.sh`／`debt_clear.sh`／`committee_run.sh` 之共用控制流變更），
16 條全數採納並修，收斂檔 `handoffs/reconcile/20260814-govmount-x-review-r1/synth.md`，
債已清（`debt_clear` OK，16/16 無掉項）。

✅ **stamp 輪已補**（`20260814-govmount-x-stamp-r2`）：三家各自複驗**自家**於 r1 提出之
findings（章程 §B8 原提出方複驗），皆以**跑反例**而非讀碼確認關閉，三家零 findings sentinel
並各自 append `RECONCILE-STAMP APPROVED`；body hash 三家各自重算且一致，
`reconcile_stamps_check.sh` rc=0，債已清。
🔴 grok 另獨立確認主委兩則「具名邊界」誠實：heredoc 那條**仍 HIT**（未修，與宣稱相符）、
`check_decoupling_imports.py` 之 provenance 限制屬真限制而非逃避。

✅ **白話說明七份已同步**（`a4d93a34`，`plain_docs_sync_check` rc=0）。

🔴 **仍未做**：
1. **未跑全套 `gov_check`**——本輪只跑受影響子集：`test_govb1_factkey_{gen,hook}` 223 條、
   `test_narrow_check_router` 13 條、`test_decouple_baseline` **9** 條、
   `test_govb1_contract_matrix`＋`test_govb49_path_grant` 124 條，皆綠。
   （🔴 主委曾把 9 寫成 10，由三家回報值比對發現——**可查的計數不得憑印象寫**。）
2. **推送等使用者明示**。筆數直接查。

### 🔴 下一手可以直接做的一件事（本輪新發現，未修）

`handoffs/` **外**的受戳記資產（如 `scripts/decouple_allowlist.md`），
新戳記在現行機制下**無法通過 provenance**——`register-output` 只收 `handoffs/` 內的檔，
既有戳記靠 `_is_legacy_allowlisted_stamp` 豁免。
後果具體且已在咬人：canonical Rule 2/3/4 的 scanner **自 2026-07-14 起從未掃過**。
掛載前置（baseline＋9 條測試）已全部就緒，**只差這個機制被修好**。
🔴 修法應指向機制本身（例如 register-output 的受管路徑集合怎麼定義），
**不得放寬 provenance 判準**。

## 【治理·參考】投影表怎麼讀（回治理時才用）

🔴 本節**刻意不重述任何一列的狀態**——重述就是副本，副本就會過期
（本檔已因此過期兩次）。狀態一律看最上方的機械投影表。

### 上一批（`S6.x`）留下的、下一手一定要知道的四件事

1. 🔴 **填「還缺什麼」前先讀該票在 backlog 的全節，不要只信抽取工具。**
   `.claude/tmp/s62_extract.sh` 初版只印命中行 ⇒ 「標題＋清單」型的修法段看起來是空的，
   主委據此把「我看不到內容」寫成「backlog 沒有內容」，committee 附行號打回。
   視窗已擴為 11 行，但**那仍是啟發式**；超長段落照樣會被截。
2. 🔴 **新加的檢查一律先寫反例測試，再看它綠不綠。** 本輪的檢查 ⑩ 初版寫起來全綠，
   實際是空心的（`map($b | contains(.))` 之 `.` 被 pipe 改寫成 `$b` 而恆真）。
   **同一個 jq 陷阱本 epic 第三次**——`.` 在 pipe 之後不是你以為的那個 `.`。
3. 🔴 **修完之後要確認反例真的會紅。** 「刪票列即繞過」那條修完後反例**沒有觸發**，
   因為沙箱樹缺 backlog 使該檢查整段被略過 ⇒ 當時並沒有能證明修法有效的測試。
   fixture 補齊後才真的紅。**「修法寫完」與「有測試證明它有效」是兩件事。**
4. 🔴 **「schema 欄位被清空即整段跳過」這個形態會反覆出現**（本 epic 已兩例：
   `S1.2` 的 settings.json、`S6.2` 的 `ticket_basis_markers`）。
   新增任何「讀 schema 決定要不要檢查」的碼時，一律問：**清空它會怎樣？**
   正解是與生成器寫死之集合**相等**，不是 `// []` 然後長度為 0 就跳過。

## 推送狀態：**本檔不寫，直接查**

`git log --oneline origin/main..HEAD | wc -l`（待推筆數）與
`bash scripts/gov_check.sh --no-probe`（丟背景）。
🔴 **筆數與 hash 刻意不寫進本檔**——歷史上一個 session 內就漂過一次。
髒檔應為 4 個且**全為規則禁止提交項**：`.claude/gate/*.log`×2、
`governance_families.json`（`R-15`）、`docs/GOVB0_FRICTION_AMENDMENTS.md`。

🔴 **`git add` 一律逐檔列出，禁目錄形式，亦禁 `$(...)` 子命令展開**：
歷次事故＝`git add docs/` 掃進 `GOVB0_FRICTION_AMENDMENTS.md`、
`git add scripts/` 掃進 `governance_families.json`（兩者皆明令不得提交），
其中一次還連帶要重寫三個本地 commit——因為 G-7 的豁免是
「該路徑在範圍內**只**被 out-of-epic commit 觸及」，補後續 commit 解不掉。
另：中文路徑經 `git status | awk` 取值會因 quotePath 轉義而**靜默取不到**，實際踩過。

## 前一批之交付與收斂檔（**狀態值一律看最上方生成區塊，此處只給指標**）

**做法**（使用者 08-12 夜間定）：不寫 SPEC/TODO，依待辦清單直接實作＋三家 review。
每項鏈路：實作 → 三家 review → 採納修補 → **原提出方複驗**（章程 §B8）→ 三家戳記 → 清債。

| 交付 | 委員輪次 | 收斂檔（含量測與逐條處置） |
|---|---|---|
| `fact_keys` schema 擴為具名欄＋表格投影 | review → closure | `handoffs/reconcile/20260813-govwl01-x-review-r1/synth.md` |
| 判準入註冊表＋三道機械檢查 | consult → review → closure | `handoffs/reconcile/20260813-govwl02-x-consult-r1/synth.md` |
| 機制證據登記（平台機制＋改法子樹掃描） | consult → review → stamp×2 | `handoffs/reconcile/20260813-govwl03-x-review-r1/synth.md`＋`…-stamp-r2/`、`…-stamp-r3/` |
| 戳記手抄消滅之設計諮詢（**未實作**） | consult | `handoffs/reconcile/20260813-govwl04-x-consult-r1/synth.md` |
| **產出端覆蓋鐵律**（票要標收案須先擋在產出端） | review | `handoffs/reconcile/20260813-govenf-x-review-r1/synth.md` |
| **全量票之產出端覆蓋盤點** | consult | `handoffs/reconcile/20260813-govenf-x-consult-r2/synth.md` |

### 🔴 接手前必讀的五條（細節與量測看上表收斂檔，本檔不重述）

1. **清單上的字面設計不等於既成事實。** 判準與機制那兩項的字面寫法都在開工前量測時被推翻
   （一項零訊號、一項誤擋率八九成）。**先量一次再動手，不要照抄開工。**
2. **「檢查只掛在其中一條路徑上」這個形態反覆出現**（已累積六個位置）。
   審查時主動問「同一種輸入有沒有第二條處理路徑」。
3. **「兩家說沒問題、一家附可重現構造」時採後者**——本 epic 已四次，四次都是那一家對。
4. 🔴 **`jq`／command substitution 的 rc 被吞掉是本 epic 最常見的空心來源**（已三個同型）。
   `$(...)`、`< <(...)`、`2>/dev/null` 都會吞。一律先落變數驗 rc。
5. 🔴 **反例只斷言 `rc≠0` 不夠，必須斷言目標錯誤訊息**——否則 DRIFT 之類的下游紅
   會讓你誤以為目標檢查生效。實際差點把一個空心的核心卡點當成通過。

### 🔴 票 SoT 已上線（本輪最大變更，接手必讀）

**61 張票收成一份**：`docs/GOV_TICKET_SOT.md`（序／票／狀態／問題描述／狀態依據）。

- 票的**任何**變動（新增／狀態／描述）→ **只改 `scripts/fact_keys.json` 之
  `governance-ticket-sot`**，再跑 `--write`。別處寫「票號＋狀態」會被 fail-closed 擋下。
- `handoffs/…-BACKLOG.md` 與 `白話說明/治理待辦總覽.md` **已標作廢**，內容一字未改
  （使用者裁定「標成舊文件就好」，不必付移除的不可逆代價）。
- 新增票**不必**寫 backlog：`scripts/ticket_universe.sh --check` 是**單向**檢查
  （backlog 有而 SoT 缺 ⇒ 擋；SoT 多出的新票 ⇒ 放行；票號格式錯 ⇒ 擋）。
  🔴 原設計要求「集合相等」，與「backlog 已作廢」自相矛盾——**使用者指出後才修正**。

### 🔴 步驟狀態只有三個值（本輪定死，不得再造詞）

**未開工**＝產物一個都不存在；**進行中**＝產物部分存在但驗收未全達成；
**收案**＝驗收條件全部達成且有可重跑的驗證指令。
🔴 主委曾臨時造「基本完成」「可標收案」兩個詞——**沒全達成就是進行中**，
「驗收過了但還沒改表」不是狀態，是該立刻去改表。
`governance-sot-plan` 已加「驗收條件」欄，20 步全填且皆為可重跑指令或可構造反例。

### 🔴 「產出端」的定義（本輪釐清，勿再誤讀）

使用者原話是「產出**完成前**」「連留到**下一節點派工**都已經是摩擦」⇒
**產出端＝我還在做這件事的那個工作階段內就知道**；**消費端＝要等後面某個關卡才發現**。
`PostToolUse` **屬產出端**（寫完當下回灌），不是「寫入前」。
🔴 主委曾把它誤讀成「寫入前」並據此排錯優先序；`PreToolUse` 對**一致性型**檢查
會直接死鎖（改註冊表必然先不一致 ⇒ 永遠通不過）。分類見 `governance-sot-plan` 之 `S3.2`。

## 已完成並 push（`origin/main`）

- `票 B-49`：凍結出口補上、幽靈路徑 11→0、關票條件機械可驗（**狀態值見生成區塊**）
- **ASSERT 自鎖 T0 止血**（`53966e90`）：寫檔路徑零執行 ＋ 逐行 timeout ＋ `proc_guard.sh`
- 檢查鏈段序改「便宜先」＋早退＋失敗摘要（`2c34027a`）

## 📜 前一 session（2026-08-12）之批次——**歷史紀錄，非現況**

**PUSH 11 分鐘 ＋ ASSERT 自鎖，兩題皆已改碼**（前版交接記為「一行程式碼都沒改」）：

| 改動 | 檔 |
|---|---|
| 段序改便宜先＋便宜段早退＋失敗摘要末尾化＋backlog 移至最末 | `scripts/gov_check.sh` |
| 路 A：呼叫端不執行文件內 ASSERT（**三處**） | `gate.sh`×2、`spec_fourway_check.sh`×1 |
| NO_EXEC 下印出「ASSERT 未驗證」（不得靜默） | `scripts/template_check.sh` |
| 新增守衛測試 13 格（含 5 條 mutation 反面） | `tests/governance/test_gov_check_cheap_first.py` |
| 處置與具名殘留 | `docs/GOV_ASSERT_PATHA_NOTE.md` |

**三家 review**（`handoffs/20260812-govcheap-x-review-r1/`）：Composer／Grok 判可派工；
**Codex 判需修補**（2 條 P1，附行號碼證）。依「不數人頭以碼證定」採 Codex，兩條均已修：
① G-7 缺檔原寫成「略過」＝fail-open ⇒ 改以 `scripts/govb1_scope.manifest` 判適用性、
　 缺腳本判紅，並補 `test_mutation_removing_g7_script_turns_red`
② NO_EXEC 靜默放行「文法對但結果會錯」之 ASSERT ⇒ 改為大聲印出，
　 並把可執行 ASSERT 之**檔案集合凍成具名清單**（新增即轉紅）
另 Grok＋Codex 抓到主委自造回歸：以 `awk` 批次改註解時**掉了 `gov_check.sh` 的可執行位**，已還原。

### 續作（同日第二輪，session `20260812-govassert-x-review-r1`）

`CODEX-R1-P2-04` 指出「掃呼叫端」判準**不封閉**（`scripts/test_template_check.sh:64`
以 `bash "${TEMPLATE_CHECK}"` 呼叫，正則看不見）⇒ **反轉預設**：
`template_check.sh` 改為預設不執行、須明示 `TEMPLATE_CHECK_EXEC=1`；
四處呼叫端的死旗標移除；列舉式掃描測試刪除，改為形態面＋行為面兩條判準。

三家再審 6 條**全數採納並修**。其中 `GROK-R1-P1-01` 為 BLOCKING：
反轉後 `test_t15_a1_path_hijack_blocked`（唯一不走 `_run_fn` 的承重測）變成空心格，
已修並經反面實證（拆掉 PATH 固定 ⇒ marker 出現）。

🔴 **本輪品質觀察（重要）**：必答「是否出現空心格」一題，**Codex 與 Composer 皆答錯**
（兩家都聲稱 PATH 劫持測經由 `_run_fn`，實為自建 probe），只有 grok 實跑隔離。
⇒ 該兩家之「可 commit」verdict 建立在錯誤事實上。
**review 品質的分水嶺是「有沒有真的跑」，不是家數**——派工時應要求附實跑隔離結果。

### 第三批（`eddd78e3`；使用者指示「寫在一定會看到、不會漏也不會讀錯的地方」）

- **待辦清單改為機械投影**：新 fact-key `governance-worklist`，宿主＝本檔＋
  `白話說明/接下來要做什麼.md`。**狀態只改 `scripts/fact_keys.json` 一處**，手寫即 fail-closed。
- **`CLAUDE.md` 去除會漂的值**：① code review 家數改為指向 `ORCH §1`
  （原寫「2 個」而 ORCH 為三家，當日害主委做錯一次）② pytest 秒數／測試數改為
  「十分鐘級、前景必 timeout」之不變判準（該數字已過期四次）。
- 延伸檔 `docs/GOV_B25_SCOPE_AMENDMENT.md` 補列 `FACTKEY-ADDED: governance-worklist`，
  並把該檔寫死的「兩個狀態 key」改為指標。
- 🔴 **本批未經三家 review**（改動為資料註冊與文件去漂，無行為邏輯）。
  若下個 session 認為需要，補派一輪即可；**不得宣稱已審**。

## 實測數字：本檔不重述，看唯一來源

| 量到什麼 | 唯一來源 |
|---|---|
| `--fast`／全套 push 路徑之前後對照、backlog 75 秒之根因 | `白話說明/接下來要做什麼.md` 之「8/12 深夜」節 |
| 可稽核收據（含 exit_code／sha256／git_head） | `handoffs/run_receipts/20260812T121019Z-govcheap-fast-1s.*`<br>`handoffs/run_receipts/20260812T122358Z-govcheap-fullgate-703s.*` |
| ASSERT 執行面之正確量法與數字 | `docs/GOV_ASSERT_PATHA_NOTE.md` §2 |

🔴 **舊記「89 行／9 檔／凍結檔 45 行」係量法錯誤（未錨定行首），已作廢——勿再引用。**

## 平台事實（勿重測，直接用）

- `ulimit -H -u` 本機**不能降**（`Invalid argument`）；只降 soft 必被子程序抬回
- **無 `setsid` 指令**；`set -m` 可使背景 job 自成 pgid，`kill -TERM -<pgid>` 實測連孫程序一併終止
- per-user process 上限 `ulimit -u`＝**1333**

## 🔴 未修的活缺口

> 🔴 **本節是機器輸入**：`governance-ticket-closure` 之導出集合＝本節 ∪
> backlog「2026-08-10 scope 缺口」節所提及之票號。增刪票號提及須同步 `scripts/fact_keys.json`。

- 🔴 `票 B-25`：判準資料化**三段皆已交付**（待辦清單前三列）。
  🔴 **能力邊界（三家一致，永遠不會由本機制關閉）**：語意互斥——兩段話用**不同條件字串**
  描述同一物理事件時鍵不相等，機械上偵測不到；出生事故那型即屬此類。
  另：既有散文判準不溯及既往；機制證據那段在現樹訊號近零，且其子樹旁路
  **四度被委員實構**（發現曲線未收斂，改 parser 須重跑候選組）。
  完整殘留見 `docs/GOV_CRITERIA_REGISTRY.md` 與 `docs/GOV_MECHANISM_REGISTRY.md`（11 條）。
  該票於票狀態表之列為 ord `005`（**狀態值見生成區塊，本檔不重述**）；
  票本身另有具名殘留，見 backlog `B-25` 節。
- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；OOE 通道救不了
- `R-13` Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`
- 🔴 `票 B-49`：**狀態已下修**（值見生成區塊）——產出端覆蓋鐵律之第一個溯及既往實例。
  主委所寫之豁免理由經三家一致否決——閉合證據的靜態可判定部分無需 commit 亦可於產出端驗。
  重新收案之前置＝把靜態子集前移至產出端，見 `docs/GOV_ENFORCEMENT_REGISTRY.md` 之 `E-007`。
  另四條具名殘留見 `docs/GOV_B49_ASBUILT_DELTA.md` §3
- 🔴 **產出端覆蓋機制本身之缺口**（9 條，見 `docs/GOV_ENFORCEMENT_REGISTRY.md` 殘留節）：
  掛載點對證擋不掉「腳本被掏空」；自我保護有本質極限（守衛執行的正是可能已被竄改的生成器）
  ⇒ **只擋意外不擋蓄意**；票表刪列可繞過；批次不受覆蓋要求；`settings.json` 缺席時略過對證
  （主委為修測試而引入之 fail-open）。**當下票表已無收案票 ⇒ 該閘無實際攔截對象**
- `票 B-54`：戳記 64 位 hex 仍由委員手抄，曾掉字一次。**已部分緩解但未機械化**——
  現行做法是在 stamp brief 內要求委員**自行以 `reconcile_body_hash.sh` 重算核對、不得抄**，
  並聲明「算出不同就以你算的為準並開 finding」。屬紀律非強制；根治＝待辦清單之 `WL-04`
- `B3R` 已進主樹但三家 review 未戳記 ⇒ 只能說「已交付、待戳記」
- `票 B-56`／`票 B-57`（優先序低）／`票 B-58`（前導空行是否為缺陷未判定）
- `票 B-59`（優先序高）：dispatch gate 判定式為黑名單列舉，**不得宣稱閘已完備**
- `票 B-60`：`review_quorum_check.sh:35` 家族清單硬編未讀 SoT
- `票 B-61`：`_role_gate.sh` 之 `known_only` 對未知家族靜默放行
- `票 B-15` 誤擋仍在（含 `for f in codex composer grok` 這類唯讀迴圈被家族名偵測誤擋）
- `票 B-50` 流程面永久標記為跳步；`票 B-31` 只能說「產出端已有檢查點」（`票 B-53` 落地前）
- 站 5 未修殘留：`CODEX-R3-P0-03`／`CODEX-R3-P1-04`／`gate_check.sh` audit 分類器未同步
- 另有兩條空心探針不在 `LEGACY_PROBE_DEBT` 內（`test_mutation_g5_g6_empty_extract_fails`／
  `test_mutation_removing_selfcheck_case_turns_red`）⇒ `gov_check` 全跑必紅（pre-push 用
  `--no-probe` 跳過故不擋推送）。**既有債**，pre-B49 基準實測同樣紅。刻意不加進具名排除清單。
- `R-15`：`scripts/governance_families.json` 不可 commit
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**`（`run_receipts/` 除外）不得 commit
- 卡頓偵測器錯誤歸因：`settings.json` 之 `ts_stamp.sh OUT`（`:184`）早於
  `doc_format_precheck`（`:197`）⇒ hook 執行時間被記成「Claude 生成慢」。屬使用者設定檔，需其同意

## ⚠ 操作紀律（踩過的坑，一律照做）

- ✅ **「推送前必跑 8 秒快閘」已不再是紀律**——白話同步／fact-key／G-7 已是 `gov_check.sh`
  的第 2–4 段，且**便宜段一紅即早退**（實測 10 秒內給答案，不再跑滿 12 分鐘）。
  自檢直接跑 `bash scripts/gov_check.sh --no-probe`（丟背景）即可。
- 🔴 **失敗先看最末的 `GOV-CHECK-FAILED:` 摘要**（已具名段號與修法），**禁直接重跑套件**。
  曾兩次只 `tail -3` 就重跑，白花 22 分鐘——摘要末尾化就是為此而做。
- 🔴 **G-7／F5 用 endpoint 淨差**：commit **前**是綠的（檔還沒進範圍），一 commit 才現形
  ⇒ **commit 之後必須重驗**。歷次 session 皆踩過。
- 🔴 **G-7 的 out-of-epic 豁免是「該路徑在範圍內*只*被帶 trailer 的 commit 觸及」**
  ⇒ 同一檔若被任一無 trailer 的 commit 碰過，**補後續 commit 解不掉**，只能重寫歷史。
  凡動到 scope 外的檔（如新建 `docs/GOV*`），**該檔涉及的每一筆 commit 都要帶 trailer**。
- 🔴 **反向驗證才算數**（移除判定 ⇒ 對應斷言須轉紅）；**前必先 commit**——
  `git clone --local` 只取已提交內容（曾因此白驗一輪）。
- 🔴 **實測 > 假設**（本專案最貴的一條，已連續多輪咬人）：
  ・寫進文件的機制**必須先實跑**（`setsid`／`ulimit` 那次燒掉三輪審查）
  ・**量測時 pattern 須一致**，且**引用命中數必須同時給比對式**——
  　同一件事三家量出三個不同數字，只是寬嚴不同，不附 pattern 的數字等於沒有數字
  ・**斷言「這條規則抓得到那個已知案例」時，要拿那個案例去跑**——
  　曾斷言新規則會攔到 `setsid`，實測發現 `setsid` 不在 PATH ⇒ 規則反而漏掉它本身
- 🔴 **待辦清單上的字面設計不等於既成事實**：連續兩項（判準偵測、機制證據）
  的字面寫法都在開工前量測時被推翻（一項零訊號、一項誤擋率八九成）。
  **每項開工前先量一次「這條規則在現有語料抓得到東西嗎」**，這已兩次擋下無效施工。
- 🔴 **注意「檢查只掛在其中一條路徑上」這個形態**：一天內出現四個位置
  （表頭 vs 儲存格／schema 單欄刪除／狀態靠列舉位置／驗證只掛 `--check`）。
  審查時主動問「同一種輸入有沒有第二條處理路徑」。
- 🔴 **不以家數表決，以碼證定**（本 epic 三次「兩家一種說法、一家附碼證」，皆採後者）。
- 🔴 **同一支腳本不得並行跑多份**——曾三份 `template_check` 併發導致 fork 耗盡（上限 1333）。
- ✅ **fact-key 註記「不得含日期」已作廢**（使用者 2026-08-14 指出該判準選錯）。
  舊判準掃 `20XX-XX-XX` 樣式，是 proxy 且兩頭不準：**誤擋**資料裡的固定歷史日期
  （寫死字串，重生成一模一樣，不會讓 diff 恆紅），**又漏掉**隨機數／PID／路徑等
  同樣會讓 diff 恆紅的動態內容。現判準＝**生成器連跑兩次須逐位元組相同**，
  直接對應「輸出不穩定」這個要防的問題，且嚴格涵蓋舊判準的有效部分。
  ⇒ **歷史日期現在可以（也應該）寫進註記**——沒有時序就分不出兩條矛盾規則哪條較新。
- 🔴 改 `fact_keys.json` 後**直接跑
  `bash scripts/regen_factkey_fixtures.sh`**（會重生成兩份 fixture 並自動補回 drifted 的竄改列）。
  🔴 不要再手動 `GOVB1_FACTKEY_ROOT=… --write` 兩次——上一個 session 手動做了六次、
  其中兩次忘記補竄改，被產出端守衛以「FIXTURE 鑑別力已失」攔下。
- 🔴 **`awk -v` 不接受含換行之值**（"newline in string"）。多行內容一律寫檔後用 `getline` 讀。
  同一個坑本 epic 已踩兩次（`S0.6` 指標替換、機制一覽 `--write`）。
- 🔴 **寫入型腳本一律先驗產出再落地**：`[ -s "$tmp" ]` ＋ 關鍵標記存在才 `cp`。
  違反實例＝機制一覽 `--write` 初版，awk 失敗產出空檔、`cp` 照樣覆蓋，**把文件清成 0 行**。
- 🔴 **grep 腳本掛載點要用 basename，不要用相對路徑**：呼叫端多寫 `"${SCRIPT_DIR}/x.sh"`。
  用 `scripts/x.sh` 比對會**偽陰性**——實際把三支已掛的檢查判成「未掛」，
  差點據此對外宣稱「文件說機器強制但實際沒掛」。
- 🔴 **在 `HANDOFF.md` 寫「某步收案前不得 X」這種句子會被自己的偵測器擋**
  （同一行有識別碼＋狀態值）。改寫成「那兩步未完成前」即可，狀態一律指向投影表。
- 🔴 **新增一個 fact-key 有四項固定連帶工作，缺一即紅**（上輪四項全中，14 分鐘 gate 抓了三輪）：
  ① 延伸檔補 `FACTKEY-ADDED:`（集合相等契約）② 兩份 fixture 各補宿主檔
  ③ 內容不得含 `年-月-日` ④ 動到 `status_scope_grandfathered` 須同步
  `test_govb1_factkey_gen.py` 之集合相等表。
  **改完先跑窄測試**（`pytest tests/governance/test_govb1_factkey_{gen,hook}.py -q`，約 2 分鐘），
  **不要讓 14 分鐘的全套去發現 2 分鐘能發現的事**。
- 🔴 **說明檔同步是工作項目的最後一個 commit**：同一 commit 既動 `scripts/` 又動
  `白話說明/` 必判過期（判準＝說明檔不早於其 WATCHED）。一輪內踩三次，一律拆兩個 commit。
- 🔴 **commit 訊息檔寫在專案內**（如 `.claude/tmp/`），勿放 scratchpad——
  `/private/tmp` 在專案外，每次 `git commit -F` 都命中權限分類器（實測 12–17 秒／次）。

### 下個 session 開頭優先處理：把測試選擇機械化（未開工）

**問題**：`gov_check` 含全套 pytest（1674 條、約 14 分鐘），而典型改動只牽動一小撮測試
（本輪改 fact-key 只需 `test_govb1_factkey_*` 共 212 條、112 秒）。問題留到 push 才現形，
一輪紅就是 14 分鐘，本輪連紅三輪。**這正是「檢查放在後面關卡＝純摩擦」的實例。**

**提案**：`factkey_write_guard.sh`（已掛 `PostToolUse`）順帶跑相關測試子集。
🔴 **必須 fail-closed**——改到的檔不在對應表內就跑全套；漏登記的代價是慢，不是放行。

**另一條路（傾向否決）**：`pytest-xdist` 平行化。治理測試有一批會就地 mutate 檔案再還原，
專案明令不得並行；標漏一個即隨機假綠。**風險高於收益。**

⇒ 屬技術取捨，**交委員會裁定**，不佔用使用者判斷。
- 🔴 `handoffs/run_receipts/` 進 commit 須帶 `Governance-Scope: out-of-epic` trailer，
  且 **trailer 必須在最後一段**（git 只解析最末段）。
- 🔴 閘會把含家族名的**讀取指令與 commit 訊息**當成派工 ⇒ 訊息一律用 Write 工具寫檔再 `-F`。
- 🔴 禁 `cd <專案路徑>` 前綴、禁 `sed -i`、禁 `rm`（用 `mv` 到 `.claude/tmp/`）、
  禁 `python3 - <<'PY'` heredoc；改檔一律用 Edit／Write。
  **`printf ... >> 檔` 也算違反**——內容裡的 `%` 會被當格式指令，
  曾一次把三份說明檔截斷在句子中間。Edit 找不到目標會失敗，shell 拼字串會**靜默產出半截**。
- 🔴 **`git add` 一律逐檔列出，禁目錄形式**——`git add docs/`／`git add scripts/`
  曾各掃進一個明令不得提交的檔（`GOVB0_FRICTION_AMENDMENTS.md`、`governance_families.json`），
  其中一次還連帶要重寫三個本地 commit。
- 🔴 **說明檔同步是「每個工作項目的最後一個 commit」**，不是每次存檔都補——
  時序判準比的是「說明檔最後改動不早於程式最後改動」，只要又動程式全部說明檔就再度過期。
  曾照「每次存檔都補」做而連撞三次。
- 🔴 **委員戳記的 body hash 一律要求委員自算**（brief 內明寫「不得抄、算出不同以你的為準」）——
  `票 B-54` 是委員手抄掉字造成的。
- 🔴 **生成區塊的內容不得含 `年-月-日`**——既有測試 `test_output_has_no_bom_no_crlf_no_timestamp`
  會攔。要標時間點就寫「使用者定」「本輪」，日期留給 git。**本輪犯兩次。**
- 🔴 **派工前先開 gate token**：`committee_run.sh` 本身就會被 `gate_check.sh` 擋
  （它是 dispatch 動作），要先跑 `gate.sh dispatch`。另：session 名須符命名規約，
  `kind ∈ {impl,review,stamp,consult,fix}`——**沒有 `closure`**，閉合輪走 `stamp-r<N>`；
  task-id 須為 session 的**大寫**形式。三者本輪各擋一次。
- 🔴 **委員 brief 要求「每條 finding 附修法」**（使用者本輪指示）：具體到檔＋行＋可貼片段，
  無需修者寫 `不需修：<理由>`。實證可省掉整整一輪往返。
- 🔴 **唯讀指令裡不要出現家族名**（如 `for f in codex composer grok`）——
  會被 dispatch 閘誤判為派工（`票 B-15`，本輪又擋一次）。改用萬用字元或不列舉。
- 🔴 **`scripts/fact_keys.json` 一律用 Edit 改，`jq` 只准拿來讀**——
  `jq` 會把整檔重新格式化，實測 diff 從 2 個字變成 **1322 行整檔重排**，review 完全看不出真正改了什麼。
  **本輪犯兩次**（第二次是在剛寫下這條規則之後）。改資料列用 `awk` 逐行重寫亦可。
- 🔴 **反例只看 rc 會被騙**：本輪兩次「rc 如期轉紅」，一查訊息才發現紅的是別的原因
  （一次是 JSON 語法錯、一次是 DRIFT），**目標檢查根本沒被執行到**。
  一律 `grep` 目標錯誤訊息，不要只斷言 rc。
- 🔴 **作廢一份文件後，要把後果推到底**：本輪把 backlog 標作廢，卻仍寫了「SoT 必須等於
  backlog」的檢查 ⇒ 新增票會被逼去寫作廢檔。**舊模型的假設會殘留在新設計裡**，
  作廢／取代之後要回頭檢查所有依賴它的規則。
