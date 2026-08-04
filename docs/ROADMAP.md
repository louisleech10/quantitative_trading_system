# ROADMAP — 量化交易系統戰術路線圖
> 單一現役戰術 roadmap。**即時任務狀態**看 `HANDOFF.md`；**決策理由**看 memory；本檔=中長期 epic 排序與範圍。
> 維護:完成項移到「已完成」、新需求加到對應優先級、範圍/決策變更標日期。**每次 commit 一併更新本檔**(2026-06-26 使用者定)。最後更新看 git log(手寫日期欄已廢,SCAR 2026-07-13)。

當前階段:**V1.0 工具階段** — crypto 單市場研究管線(探索 → 發現 Pattern → ML 優化 → 回測)。願景 V1→V2→V3 見 `PRODUCT_VISION.md`。

---

## 🔥 進行中 / 下一步（優先序）

### P0 — 制度層總審查 epic（憲法＋流程＋任務分類三層合審；2026-07-05 立案，**使用者定 P0：完成後才回其他任務**）
- **緣起**：TGF epic 證實「prose 規則靠記性必再犯、閘門規則違反不了」（驗證保真度鐵律在 context 內仍三防全破 vs 機檢上線後連編排者派工都被連擋）。使用者 2026-07-05 明示：鐵律非其偏好、是 agent 重複犯錯逼出的補丁，他無法判斷增刪——**裁決權交委員會證據裁決**（見 memory feedback-rules-are-scar-tissue）。
- **範圍三層**：①憲法內容/架構/儲存（CLAUDE.md 每 session 全載=最大固定 token 支出；四源重疊已實證分叉一次；copilot-instructions 739 行停在 2026-04-26；ARCHITECTURE/DEV_GUIDE 疑似漂移）②派工流程管線（本次實測摩擦：戳記輪×4、claim-check 擋 commit×5、provenance 流程中途才學會、同檔並發只能序列化）③小中大分類規則（多層補丁散在 CLAUDE.md＋記憶兩處）。
- **方法**：每條規則四選一證據裁決——機械化（再犯且可寫成 gate/hook/checker）／留核心原則／合併去重／淘汰（已被機檢取代）；判準=出生事故＋violation 紀錄（audit.log/handoffs/git），不靠感覺。委員會三方裁決＋白話簡述給使用者否決權；「不可砍清單」先行＋雙家族 adversarial 防瘦身誤傷。
- **時機（2026-07-05 使用者定案）**：P0 立即執行、完成後才回 IC 等其他任務；建議新 session 起跑（本立案 session context 已滿載 TGF 歷史）。流程=委員會 read-only 審查輪（三層各出 findings＋violation 證據考掘）→ 白話決策簡述給使用者否決 → 依裁決走完整管線實作。
- **裁決（2026-07-05 使用者）**：D-1/2/3/5/6 同意預設；**D-4 否決固定制**→執行端選層動態、以使用者當下指示為準（usage 切換、未來或加 Grok），文件只留單一可變「現行分工」行。附帶：否決點以後須彈窗（AskUserQuestion）+推播；總審查頻率=事件觸發+每季保底。→ **下一步=依裁決走完整管線實作（Phase A 憲法重構起）**。
- **狀態（2026-07-05）＝Phase A（憲法重構＋合約補齊）✅ 完成待 commit**：走完整大任務管線——SPEC/TODO（`docs/INSTREV_PHASEA_{SPEC,TODO}.md`，三道機檢過）→ 雙家族 adversarial（Codex 3+Composer 12 findings，含 2 BLOCKING）→ reconcile R2 雙戳記 APPROVED（sha256:6a14a0f6…）→ Composer 2.5 實作 → Codex code review 抓 2 BLOCKING（ORCH §6/§7 殘留 Codex 主力、三方鐵律過度壓縮掉義務）→ Composer 修 → Codex 閉合重驗雙 CLOSED。**成果**：copilot 739→8 行 pointer；CLAUDE.md 216→128 行（敘事移新檔 `docs/SCAR_LEDGER.md`，規則零刪減 grep 驗）；任務分派決策表單一化；執行端選層 ORCH §1 單一「現行分工行」（動態，現行=Composer 實作+Codex review）；合約補齊 5 項制度（兩輪斷路器/register-output/VERIFY claim/STAMP-BLOCKED/產物非指令）；輪詢統一 10 分鐘、debug 統一 2 輪（含 BOOTSTRAP 第 5 分叉源）；ARCH/DEV banner。**待辦**：無（Phase C 之 U-13 已完成；U-20/21 裁決本身=先別做，屬長期觀察項）。read-only 審查輪 reconcile=`handoffs/20260705-INSTREV-RECONCILE.md`（sha256:ee8c9fab…，含 U-3 errata）。

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
    白話版 `handoffs/20260804-BACKLOG-白話總覽.md`（主表一票一列，53 項舊表降為附錄；兩份已機械對帳）。

- **🔵 治理 backlog — 排序 v3.1（2026-08-04 全量重排＋當日新增 3 張，唯一有效）＝當前施工序**：
  **36 張**（導出命令：`grep -c '^## B-' handoffs/20260801-GOV-AMEND-BACKLOG.md`）中
  ✅2（`B-7`／`B-10`）｜🗑3（`B-1`～`B-3`）｜🔗3（`B-18`→`B-13`、`B-25`→`GOV-XREF-SYNC`、`B-36`→`B-13`）｜**待辦 28**。
  ```
  第0批   摩擦止血    B-24(紀律面) → B-15 → B-14 → B-30 → B-32
  第0.5批 帳本可讀    P1-6 線 C（債務事件分檔；**非 B-x 票**，屬 P1-6 的 B5）
  第1批   機制        B-19 → B-29 → B-31       第4批 散文與標記  B-16 → B-23
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
