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
- **★ 狀態（2026-07-28 更新）＝P1-6 委員未結案債狀態機：SPEC v2.8 定版、待實作**。目標＝派委員即自動開債、債未清擋所有新派工、跑機械合併驗 0 掉項才銷帳（根因＝主委手動合併委員意見**必掉項**，歷史事故漏 grok T1-01 害整份 SPEC 作廢）。
  **⚠️ 2026-07-27 使用者裁定大砍規模**：只留「開債 ＋ 一條銷帳路徑 ＋ 擋門」＋一條逃生口；**「要完全擋下的成本太高，就盡可能降低可繞過的機率就好」**（使用者原話）。舊 **v1.2.2**（16 Task／11 事件／6 狀態／360 行）已封存至 `handoffs/p16-spec-archive/`，重寫為 **v2.8**（**8 Task／4 事件／3 狀態／355 行**／M1–M34 mutation／13 條誠實邊界）。
  **審查歷程**：舊版 R1–R12 十二輪 + 新版 **R1–R9 九輪**，findings `34→17→12→9→7→7→8→2→0`；**R4 起零設計問題、零設計翻案**。三家 **RECONCILE-STAMP 全 APPROVED**（`reconcile_stamps_check.sh` rc=0，body sha `908abb3c…`；`completeness_check --lock` rc=0；`template_check` rc=0）。**🛑 白話閘已由使用者放行（2026-07-28）**。
  **實作進度 6/8（2026-07-30 更新）**：**B1**（Task 0.1 registry v2 契約＋lock 工具鏈 identity binding，`8a12c36`）／**B2**（Task 1.1 `audit_append.sh` 唯一寫入點＋原子 predicate+append，`9bfcb58`）／**B3**（Task 1.2 `committee_run.sh` 開債＋Task 1.3 `cx_run.sh` 記每家結果，`f98862c`）／**B4**（Task 2.1 `debt_ledger.sh` 只讀帳本＋Task 2.2 `debt_clear.sh` 唯一銷帳路徑）皆已 push。`pytest tests/governance -q` **287→431 passed**。**B5 進行中（2026-08-01）**：Task 3.1 `gate.sh` 債務閘已上線並**實際擋下主委派工**（首次生效）；雙家族序列審查抓出 10 條 findings／5 群集／3 個 BLOCKING，其中**兩個 fail-open 由 codex 隔離重現**（快取鍵缺語意輸入→stale allow；sidecar 可預置毒化）。修補採「整個移除快取」一刀解三洞。閉合複驗再抓 3 條，故 B5 拆三線：**線 A**（壞行被 prefilter 吞掉、違反 B4 已簽核 fail-closed ＋ `verify_b2` §7 語意面盲）已修並經主委獨立變異複驗；**線 B** 凍結文件修訂程序 **✅ 已定案入 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md`（2026-08-01，三家戳記 `a36725a55cd3`）**；**線 C** 債務事件分檔。**B5 完工判定綁在線 C（composer 裁定），線 C 閉合前一律 NOT-CLOSED。** 之後才是 Task 3.2 與 B3 遺留必做項 `P16-GATE-D1-STRUCTURED-VERDICT`（`gate.sh:246` Verdict 正則過鬆，骨架佔位行即可命中，曾據此實際做出 fail-open）。
  **B5 關鍵發現（實查，前人未提）**：`.claude/gate/audit.log` 30,232 行中**債務紀錄僅 176 行（0.58%）**，92.6% 是與債無關的舊式散文 gate 派工紀錄 ⇒ 效能問題根因是**債務事件與其他紀錄共用同一個檔**，非掃描演算法；分檔後掃描量降至 176 行，prefilter 不再需要，連帶消滅其副作用。
  **🔴 上述效能立論已於 2026-08-02 被實測推翻**：`debt_ledger --has-open` 對 30,960 行實跑 **46–64ms**
  （SPEC 本就要求 <100ms，早已達標）；30,960 行中真正被解析的 JSON 僅 2,448 行，其餘非 `{` 開頭只做一次字首判斷即跳過。
  且 92% 散文**仍在持續產生**（`gate.sh:616-625` 每次發 token 寫 15 行）、**且不可刪**——內含 `intent`／`risk`／
  `facts_asked`／`review_role`／`adversarial`／`spec`／`todo` 等欄，而 `committee_dispatch` JSON 只有 6 欄。
  `gate_deny` 僅 366 行（1.2%），單搬它收益趨近於零。
  ⇒ **線 C 不得以效能立論**；唯一站得住的版本＝把 15 行散文壓成 1 行 JSON（欄位一字不減）＋歸檔既有散文，
  **只買到衛生與成長率，不買效能也不買正確性**，屬 cleanup 非 fix。草案見
  `handoffs/20260802-LINEC-AUDIT-SPLIT-SPEC-DRAFT.md`，**開工前須使用者裁定是否值得花這個工**。
  **線 B 定案記錄（2026-08-01）**：v1.0 極簡版 147 行，**範圍＝只擋意外不防蓄意、零新增檢查器**；
  v0.1–v0.6 六版草案全部作廢。**最大產出是失控機制的定性**：主委把「修訂約定」做成「防蓄意繞過系統」，
  致對抗審成無限迴圈（寫防護→找洞→補洞→找新洞）——**委員每輪都對，問題在題目沒邊界**。
  使用者定「沒 100% 解就先解 95%、殘留具名記錄、再犯再說」後，R2–R6 全判「不可實作」的同一批委員，
  **R7 一致給出「文字修補即可定案」**。成本：7 輪、33 次派工、約 50% 為純程序開銷（戳記／provenance 補正／格式補件）。
  新增 `scripts/draft_selfcheck.sh`（起草缺陷五條檢查，**ADVISORY 不得掛 gate**，R4 收斂裁定）。
  **✅ 票 `GOV-STAMP-TASKID-INJECT` 完工（2026-08-02）**：原病＝`cx_run.sh` 已注入 `ROUND_ID` 卻未注入 `TASK_ID`，
  致委員手抄 task-id 與 provenance pending。**修法走 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` 的 D 延伸**
  （`docs/P16_COMMITTEE_DEBT_SPEC.D-001.md`，該程序**首個實戰案例**）：`task_id` 由 audit 的 `committee_round_open`
  導出並注入 prompt（**明文否決 env 通道**，避免與 audit SSOT 分叉）；`brief-kind=stamp` 於戳記落地後自動
  `register-output`；`stamp-target` 驗證上移至 `committee_run.sh` **`gate.sh dispatch` 之前**（audit 逐位元組零新增）。
  `pytest tests/governance -q` **469→512 passed**、`gov_check.sh` rc=0、新檔 65 tests＋21 mutation probes。
  流程＝D-001（R1 對抗審 9 findings→R2 codex REJECTED→R3 三家 APPROVED）＋TODO（5 findings→三家 APPROVED）
  ＋實作 7 輪＋code review 3 輪（CR1 7 條含 regex fail-open／CR2 1 條 P1／CR3 零活缺陷）＋閉合輪三家判可 commit；
  **五份收斂檔 `reconcile_stamps_check.sh` 全數 rc=0**。
  **本票暴露的兩條制度缺陷（新票，見 backlog B-9/B-10）**：`GOV-DOCS-STAMP-PROVENANCE`（`docs/` 內延伸檔
  拿不到可過機檢的戳記，因 `register-output` 只收 `handoffs/`；程序 §3.2 與 §3.1／§2 自相矛盾，修法須走 §5 的 R）、
  `GOV-DEXT-TEMPLATE-KIND`（`template_check.sh` 無 D 延伸檔 kind ⇒ `--spec <D延伸檔>` 永遠拒發 token）。
  兩者皆 fail-closed 未誤放行，各燒一輪派工。

  **✅ 票 `GOV-DOC-CHECK-AT-WRITE` ＋ `GOV-DEXT-TEMPLATE-KIND` 完工（2026-08-02，`901a8d9`）**：
  病根＝**治理文件的格式檢查點在消費端（派工/freeze）不在產出端（寫檔當下）**，
  代價是「寫完→派工被擋→重寫→重派」，每次燒一整輪委員（本 session 4 輪、B4 批次 5 輪＝該批 38%）。
  改法五處：`template_check.sh` 新增 **`dext` kind**（錨點取自 `FROZEN_DOC_AMENDMENT_PROCEDURE` §2）／
  **`brief_conformance_check.sh`（新）**＝brief 合規閘唯一實作，`cx_run.sh` 與 `committee_run.sh` 皆改呼叫／
  **`doc_format_precheck.sh`（新）**掛 PostToolUse `Edit|Write`，寫檔當下即檢查、exit 2 回灌 context／
  `gate.sh` 對 `--spec <*.D-NNN.md>` 路由 dext／`gov_check.sh` 新增 1b 段對本次改動的 `docs/*.md` 全掃。
  **測試 512 → 563 passed（+51）**，新增兩檔各附 mutation 探針證明可證偽。
  3 輪 code review ＋ 1 輪 consult，findings 全數由**原提出方**確認真關閉：
  `R1-P1-01`（`committee_run.sh` 另有第二份 parser 且開債早於完整檢查 ＝ audit `sequence 367` 孤兒債的真成因）／
  `R1-P2-04`（`docs/*.D-NNN.md` 的 glob **跨 `/`**，巢狀路徑誤判 dext）／
  `R2-P1-01`＋`R3-P1-01`（**兩次同型 fail-open**：`[ -f dep ] && …` 缺檔即靜默跳過並回報通過）。
  **主委原提的結構性修法被 codex 實跑否決**（60 支 shell／命中 5／**真陽性 0**／且漏抓 `gate_check.sh:66`）→
  改採委員版本，另立票見下 B-11／B-12。

  **新票 B-11 `GOV-FAILCLOSED-DEP-GUARD`**（2026-08-02 三家裁定，**不阻塞 T1**）：
  病根一句話（composer）＝「**治理檢查器把『依賴缺席』當成『檢查不適用』而非『檢查失敗』**」。
  ⚠️ **主委原案（靜態探針當硬 gate ＋ `# OPTIONAL-DEP:` 註記豁免）已被實跑否決**——
  誤判率 100% 且會漏抓真陽性；單純註記三家一致判為橡皮圖章。
  **採委員改寫版**：靜態探針**降級為可解釋 tripwire 警告**／**隔離 runtime mutation 當硬 gate**／
  豁免改為**可過期 registry**（`task-id`＋`owner`＋`expiry`＋理由＋對應 mutation test，每檔上限 2 條、
  `gov_check` 印出清單、定期審計）／提供 `require` helper（僅在裸條件式被機械禁止時才有價值）。
  範圍收窄為 `gov_check`／`gate`／`verify_hooks_health` 閉包，**非全 `scripts/*.sh`**。
  優先序（composer）：**探針（強制）> helper（好寫）> 紀律（禁止）**。
  已知未修的真陽性：`gate_check.sh:66` 的 `jq` fail-open。

  **新票 B-12 `GOV-TESTHARNESS-SCRIPTLIST-SSOT`**：「隔離 repo 需要哪些腳本」的清單**散在至少 4 份 fixture**
  （`test_stamp_taskid_inject._SCRIPT_NAMES`／`test_debt_emit` inline tuple／
  `test_verify_gate_b3._setup_temp_git_repo` symlink 清單／`test_debt_clear`、`test_debt_gate` 各自的），
  新增一支腳本要人肉改四處且**無任何機制提醒漏了哪份**——本 session 因此紅了 4 次（39／23／7／2 條）。
  與 `GOV-FORMAT-SSOT` 同型（第 N 真相源），標的不同。

  **使用者 2026-08-01 定死三條**：①測試可質疑規則但**不准用統計手法或量測技巧充當達標**（中位數／去離群／取最小／放寬倍率皆不接受），認為規則錯就走委員會改 SPEC ②做不到就提案改 SPEC/TODO，不得硬幹繞路 ③**修訂凍結文件走延伸檔**（引用＋註明來龍去脈），避免同一份 SPEC 翻來覆去（就地改需重審 936 行 vs 延伸檔約 70 行）。
  **新發現治理債**：`verify_spec_stamp_delta.sh` 常數停在 v2.8（SPEC 已合法升 v2.9）→ 實跑 rc=1，而 TODO 檔頭仍以現在式宣稱該腳本證明「無其他未交代改動」＝**文件宣稱的護欄已腐爛**（票 `P16-SPEC-STAMP-DELTA-STALE`）；`todo_spec_crosscheck.sh`／`spec_fourway_check.sh` 自述僅為煙測，PASS 不等於已收斂。
  **B4 實作教訓**：①**新造的驗收工具必須與產品碼同輪受審**——B4 的 `verify_b4_independent.sh` 自己假綠（只驗存在性、綁錯測試），是主委在 brief 點名才抓到，**制度原無此條** ②**委員探針一律用隔離副本**，禁直接變異 repo 內 `scripts/*.sh`／`tests/**`（本批 `debt_clear.sh` 曾被並行探針清成 0 bytes，untracked git 救不回）③**凡變異產品檔或跑同一套驗證工具的輪次一律序列派工**（並行時委員會讀到他家探針中間態而拒絕背書）④**零 finding 的審查輪須補 `P3-00` sentinel**，禁 `debt_abandon`、禁手寫 `committee_debt_clear`（三家裁決 A′；殘留風險＝機檢仍接受空殼 P3-00，由 `GOV-NOFINDINGS-SENTINEL`／`GOV-VERIFY-RECEIPT-RUNNER` 承接）。
  **收斂教訓**（本 epic 最大產出，非機制）：①舊版連八輪卡 20–25 findings 未收斂即定版，根因是 **scope accretion**（每次修訂新增機制）；TODO 階段則是**抄寫漂移** —— 兩病要分開診斷 ②`handoffs/` 底下 **82 份舊 RECONCILE 檔 canonical ID 全為 0**，以前 findings 從未被機械清點，「以前沒漂移」有一半是**量測假象** ③新版第七輪條數不降反升觸發停損線，重評結論＝卡住的**不是設計，是改文件時的傳播缺口**（同型犯 7 次）→ 自檢演進為「**四向擁有權**」（改法落在**擁有該腳本的 Task**／該 Task 驗證段／§V mutation／全檔無矛盾絕對句）④**戳記輪自身被打臉**：`completeness` 紅燈期間 composer/grok 仍簽 APPROVED，只有 codex 查前置條件並拒簽 → 重簽輪硬性要求「簽前自跑前置條件貼 rc，紅燈不准簽」。憲法級裁決：一扇門（所有委員派工走 `committee_run.sh` 一律開債）／不得用任何主委可自報的信號當分類器（5 種全被三家打穿）／債未清擋所有新派工含實作／TTL 7 日禁自動 clear。**制度傷疤（本輪新增）**：①SPEC 定義新資料結構一律建 JSON/schema 當 SoT（markdown 無型別系統，P1-6 連三輪漏同步）②SPEC 階段禁止寫實作（委員以「腳本不存在」作碼證時應寫成驗收條件）——兩條已入 `templates/SPEC_TEMPLATE.md`。**新發現債 `GATE-TOKEN-BINDING`**：`gate_check.sh` 只驗 token mtime 不比對內容 → 一 token 900s 內授權任意 task-id；固定檔名跨 session 互相延長（fail-open），應併入 Task 4.2。
- **狀態（2026-07-06）＝Phase C（U-13 批次戳記慣例）✅ 完成**：批次戳記（一次派工審多檔逐檔 append）+同檔並發序列化+不可自我認證原則不動，寫進 `docs/MULTI_AGENT_ORCHESTRATION.md` §戳記後（第二階段「包單一命令」暫緩）。**U-20**（共用路徑 hook 警示）/**U-21**（Codex vs Composer 長期主力）裁決＝先別做、累積證據 → 長期觀察項。**∴ 制度層 epic 可實作項全完成（A 憲法＋B 腳本＋U-13）；實質下一站＝IC Analysis（P0，FF 測試資料已就緒，見下）。**
- **🔧 委員文件收斂方法 epic（2026-07-22 立案；IC reconcile 手抄事故衍生）**：病灶＝Claude 主委手動 merge 委員產物**必掉項**（IC reconcile 漏 ~15 項）。目標＝機械可證的文件收斂，**擋意外 90-95% 不防蓄意**（使用者定死），不碰 gate 活洞 H1-H7。**地基 ✅ 完成（commit 574efba）**：governance suite 151/0 綠 + `completeness_check.sh` 紅隊加固版入 repo。**SPEC ✅ 三家審+閉合全 APPROVED（2026-07-22，v3，commit 08eb7fe）**：`docs/CONVERGENCE_METHOD_SPEC.md`（7 Phase/9 Task；R1-R6+C1-C17 全落地）；SPEC reconcile 戳記 PASS（body sha256:03cf9083）。**TODO ✅ 三家審+閉合全 APPROVED（2026-07-23，v3）**：`docs/CONVERGENCE_METHOD_TODO.md`（§0/§B 6 批次+9 Task+內嵌 polarity 矩陣+偽碼+真實函式名）；審查鏈=v1 三家（codex REJECT 4P0/grok+composer CONDITIONAL）→reconcile 48 findings→26 群集 0 掉項→v2→§B8 閉合（各抓 v2 改字新洞）→v3 精修 7 殘留→最終確認輪三家 APPROVED；TODO reconcile 戳記 PASS（body sha256:8dd8df24）。**✅ 實作 6 批次 B1-B6 全完工（2026-07-23，commits 9dac863→27b499d）**：B1 變異先紅→B2 canonical ID+digest+空殼機檢→B3 目錄鎖+gate 掛載+反bypass硬化（5 env override 全綁 GOVERNANCE_TEST_HARNESS）→B4 self-check+DEGRADED_PENDING 狀態機→B5 5 oracle+非循環 90%水位（dogfood 機器驗證「32 findings 0 掉項」）→B6 語意 charter+收編 mutation_red 入主 suite。`pytest tests/governance -q → 215 passed/xfail=0`。每批 Grok 實作/Codex+Composer 雙家 review/Claude 獨立驗+finding closure；codex 逐批深度對抗（並發競態/env bypass/循環 coverage/裸 ID 冒充）全修閉合。**工具上線**：`scripts/completeness_check.sh`（--lock 正式入口）+`replay_convergence_coverage.sh`+`write_committee_accepted.sh`+`templates/COMMITTEE_{FINDING,SEMANTIC_REVIEW}_TEMPLATE.md`。**殘留 backlog（非阻擋）**：composer B6-P1-01/P2 producer hardening、B1 receipt 位置（P2/P3 carry-forward）。審計 handoffs/20260722-convergence-*。
- **狀態（2026-07-06）＝Phase B（治理腳本補強 U-9/12/14/15）✅ 完成待 commit**：走完整中任務管線——SPEC/TODO（`docs/INSTREV_PHASEB_{SPEC,TODO}.md`，template_check PASS）→ Codex adversarial（8 findings，2 BLOCKING，REJECT）→ 全數 ACCEPTED+修訂 → Codex 閉合重驗 8 全 CLOSED → reconcile 雙戳記（sha256:1e919edd）→ Composer 實作 → Codex code review（3 findings）→ Composer 修 → 閉合重驗全 CLOSED。**成果**：U-9 sync 兩層 token（CONTRACT_REQUIRED/PLANNER_REQUIRED）+選層單一來源反向檢查+A-12 新 token；U-12 gate DENY（no_fresh_token/token_expired）落 audit.log；U-14 pre-commit index-only 尾空白 auto-fix（binary-safe，排除 fenced/hard-break/表格）+checker 缺 backing 提示；U-15 gate.sh 用法模板+新 `scripts/dispatch.sh`（碰撞 fail-closed+透傳）。governance 140 passed/9 pre-existing（非本批，舊 spec/fixture 不符演進規則，技術債另記）。

### P0 — 驗收防偽閘 verify-gate（2026-07-01 FF 驗收捏造事故後立,擋「宣稱已驗≠真驗」）
- **範圍**:`docs/VERIFY_GATE_SPEC.md` v2.1(P0-FF-3「align mutation真紅」不實事故 → run receipt + claim checker + enforcement 三層)。
- **狀態(2026-07-02)= epic B1-B5 全落地**:B1 receipt(`d3870c4`)、B2 claim checker(`a1d3638`,V7誤報=0)、B4+B5 provenance/RESULT硬欄位(`6c0a6b0`,Codex 6 BLOCKING 閉合)、B3 enforcement 三層+health(本次 commit;Codex 4 BLOCKING 閉合檔載「FINAL VERDICT: APPROVED」;governance 75 tests VERIFY:20260701T235954Z-governance-b3-final)。PreToolUse hook 已生效;git hooks 用 `bash scripts/install_verify_hooks.sh` 安裝。殘餘=誠實邊界(careless-proof+tamper-evident,非防惡意)。
- **全系統紅隊 ✅(本次 commit)**:三方(Claude+Codex+Composer)紅隊抓 7 洞(env-prefix繞閘/docs走私/模糊洗白/假歸屬自我認證/路徑正規化/無逃生程序/provenance未接線),全修+Codex閉合R1-R7 CLOSED;淨判斷「仍有洞需緊>過嚴」。88 governance tests。
- **接續**:FF P0-FF-3 收尾完成(mutation 全探針輪 receipt log 檔載「5 passed」,出處:handoffs/run_receipts/20260702T125150Z-mutation-test_ff_multitf_truncation_mr.log;⚠️舊 receipt 020806Z 那輪的 align 為假綠 shape 已作廢;B2 回歸出處:20260702T042627Z-ff-b2-regression.log;Codex final review 檔載「APPROVED」出處:20260702-FF-P0FF3-FINAL-REVIEW-CODEX.md)。**P1-FF-5/7 ✅ 完成(2026-07-03,本次 commit)**:跨 symbol 值隔離+wrapper 路徑正確性兩測試檔落地(Codex 實作+Composer adversarial 7 BLOCKING→4 輪修復閉合→CLOSURE/INCREMENTAL 皆檔載「APPROVED」,出處:20260702-FF-P1-57-REVIEW-composer.md);slow 全鏈實跑 receipt 檔載「1 passed in 992.47s」(出處:run_receipts/20260702T203429Z-p1ff57-slow-fullchain-v3.log)。殘餘待辦:B-5 兩污染面 defer(batch checkpoint/RunLease、L7 path-map deep)。**GOV-O3EXT-R7 ✅ 完成(2026-07-03)**:R7-emitter 全 task-id 留痕+register-output+委員會過程檔 sha256 綁定豁免(Composer adversarial F1-F7 全 CLOSED+code review 檔載「FINAL VERDICT: APPROVED」出處:20260703-GOV-O3EXT-R7-REVIEW-composer.md;11 份委員會過程檔已註冊過 checker 補 commit);跟進=review B1-B5 NON-BLOCKING。**次站=fracdiff max_lag 大 epic(P1-FF-6 併入,見下方 P1 節;新 session 起手)**。

### P0 — IC Gatekeeper 開發 + 真實端到端測試
- **為何**:FF 已收尾,pipeline 下一站。現況 79 IC 單元測試**全合成資料**,從未真實 kline 端到端驗證。
- **範圍**:限 crypto(三方 2026-06-17 定,見 [[project-datasource-ff-ic-assessment]]);真實 kline 跑 IC Gatekeeper(12+10 模組) 端到端 + 驗證。
- **★施工藍圖(2026-06-24 四家委員會地圖)**:`handoffs/20260624-ic-map-WHOLEMAP.md`(5 階段 28 種分析全棧盤點 + 系統性發現 A-H)。盤出主流程**幾乎無防偽護網**:
  - **🎯 絕對優先(正確性紅線/生死)**:事件 case-control 套件(主戰場全缺)、train/test 切分(主路徑無)、FDR 接線(幽靈,43萬≈21,500假陽性)、Net IC 量綱錯誤、factor_attribution NaN 繞過。
  - **🚨 P0 止血**:grouped/decay 崩潰、幽靈開關群(feature_filter/turnover/slippage)、靜默空圖、大尺度 cap。
  - **大尺度(430K)架構**:見 `handoffs/20260624-ic-optimization-CONVERGED.md`(串流分塊不物化全矩陣)。每優先項走完整 SPEC 管線。
- **分階段執行計畫(四家收斂)**:`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`(七 Phase,contract-first+雙軌)。
- **★★ IC Gatekeeper 七 Phase 全景(骨架;狀態即時;細節見上述 CONVERGED 檔+各 Phase SPEC)** — *本表=canonical 全景,勿再壓成一行;新增/完成 Phase 直接更新此表*:
  | Phase | 內容 | 狀態 |
  |---|---|---|
  | **0 止血+正確性硬閘** | crash/時間軸/feature-guard/空圖/大尺度 cap | ✅ 完成(`11507f5`) |
  | **1 正確性 kernel + contract(能信)** | 1-contract/1a 切分+接線/1-align 前瞻閘/1e HAC+1b FDR/1c Net IC+1c-FR/1d attribution/1f 空圖;**+前瞻整治 LA-0(P0)✅/LA-1(P1)✅/LA-2(P2)✅** | 🔵 **進行中**(尾巴=**IC 全棧健檢 epic**〔吸收原 1f 空圖;見下方專節〕;**1d attribution 六批 B0-B5 全完工 2026-07-22**:清債落地=intercept 正名/NaN·inf·輸出溢位·index fail-closed(unavailable 三鍵)/幽靈 factor_attribution 顯式 unavailable+completed_partial 外顯;每批 Grok 實作+Codex+Composer 雙審+agy 實習+閉合+quorum+Gate;三方 DATA-CORRECT 經 scope reconcile 一致 IN-SCOPE-PASS。**未 commit(待使用者)**。follow-up 另票:exposure 家族 fillna fail-closed 化(§N 他票)、cache close all-NaN carrier index 對齊(production-hardening)) |
  | **2A 事件 case-control 語義 kernel(主戰場,小尺度先驗)** | 事件清單 ingestion+事件前窗對齊+AUC/t-stat+正反 matching(同波動/regime)+事件 OOS(purged CV)+FDR+波動調整 | ❌ 未啟動(大,需設計;依賴 P0 前置+P1 子集) |
  | **3 串流承載(430K×百 symbol)** | direct L7+chunk iterator+row mask+metric sink+candidate set+**staged screening(=粗/精篩 funnel)+redundancy cap**+cross-sectional 串流;**IC-PERF/feature 上限保護在此** | ❌ 未啟動(大,基礎軌;依賴 P1 contract) |
  | **2B 事件 case-control 大尺度整合** | event mask×streaming chunks+artifact+全 430K universe 篩選 | ❌ 未啟動(依賴 2A+3) |
  | **4 整合+進階** | **IC→ML 橋(複用 ML 孤島非重寫)**+多因子組合+**邊際/residual IC**+HRP/Grinold+DSR/PBO/MinBTL+Pooled IC+**容量**+centrality auto-run;**regime-conditional IC 驗證(HMM/GMM 選型+小樣本+多重檢定)歸此,獨立票、條件觸發** | ❌ 未啟動 |
  | **5 Agent 顧問層(V2)** | 結構化可機讀輸出+嚴謹度指標+Agent 委員會式解讀 | ❌ 未啟動(依賴 P1+P4) |
  - **funnel/IC-PERF 定位**:非獨立 deferred 項,=Phase 3(staged screening/redundancy cap)+Phase 4(多因子);「等整張 map 完成才做」≡「等 P1 收完進 P3/4」(memory `project_ic_feature_selection_funnel`)。
  - **regime IC 驗證定位**:Phase 4 進階層,**獨立票、條件觸發**(只有要讓 regime-conditional IC 當決策級才做;現只進報告非 gate,不做也不出錯)。2026-07-17 使用者提出。
  - **★IC 全棧健檢 epic(2026-07-22 使用者定;Phase 1 收尾,吸收原 1f 空圖)**:2026-06-24 WHOLEMAP 已隔月過時(1a/1e/1b/1c/1c-FR/1c-FR-FULL/LA 整治/1d 全落地),需 refresh 全棧盤點 + 以量化業界觀點檢視功能有無遺漏。**設計原則(使用者洞察)**:①任何 audit 先天不完整、增減必然 → time-box 不追求完美;②手動快照會腐爛 → **把發現做成機器閘門**(審一次、以後自守);③**分層防禦**(無單層完整,靠疊):架構逼 typed 契約(工具看得到大宗)+wiring 閘門(查對應/空態/不崩,**不查值正確/不查好看**)+adversarial review(抓繞過契約者)+里程碑複審(兜底)。**執行順序(定案)**:(1)盤點現況 discovery sweep=起點(Claude+三委員平行,產「後端產出/前端消費/wiring/空態」四欄表,浮現既有幽靈/斷線/靜默空圖)→(2)quant gap analysis(現況 vs 業界;複審 4 個 deferred〔funnel/capacity/regime IC/walk-forward+CPCV〕該否提前)→(3)建 typed 契約 SoT + wiring 閘門(形式化+自動化,編碼無孤兒/無斷線/空態誠實不變式;順手修 #1 幽靈=原 1f)→(4)跑閘門確認閉合+之後自動守。底稿=`handoffs/20260624-ic-map-WHOLEMAP.md`(舊,須複核)。
  - **1d 收尾 follow-up 兩票(2026-07-22 三方 DATA-CORRECT scope reconcile 一致 IN-SCOPE-PASS 後登記;證據=`handoffs/1d-DATACORRECT-SCOPE-RECONCILE.md`)**:Codex adversarial 揪出、經三家證實非 1d 引入之 pre-existing 資料債,**明列防丟**:
    - **FU-1 exposure 家族 fillna fail-closed 化**:`factor_exposure_analyzer.py` 的 `neutralize_factor_matrix`/`calculate_portfolio_exposure`/`monitor_exposure_concentration`(:111-307)壞值靜默 `fillna(0.0)`。**嚴重度=中**(FactorExposureConfig `enabled=False` 預設關;portfolio_exposure 只餵 Radar 診斷、非交易決策)。修法=比照 1d B2 把 attribution fail-closed 的模式套到 exposure 家族。**階段=1f 之後的 fail-closed sweep 或獨立票**;§N「exposure 家族 NaN 靜默=他票」已凍結。
    - **FU-2 cache close all-NaN carrier index 對齊**:kline `RangeIndex` vs features `DatetimeIndex` 對不齊 → carrier 全 NaN(`cache_close_finite=0/512`)。**硬前置=票A/票B(接真 attribution)**:接真歸因**必須**先修此(全 NaN carrier 上無法接真),故自然被票A/票B 閘門擋;**保證機制**=1d golden 已外顯 `cache_close_finite`,comparator 會偵測未來變化,藏不住。SPEC §P B0 errata「production-hardening 另票」。
  - **attribution 後續兩票定位(2026-07-20 四方可行性挑戰收斂裁決;綜合=`handoffs/1d-FEASIBILITY-SYNTHESIS.md`)**:1d 本票只清債(正名+NaN fail-closed+幽靈顯式 unavailable),**接真 attribution 拆兩張條件票,皆不插隊 Phase 1**(委員 2:1;composer 主張 P1 尾票之前提「依賴已存在」已被 cumsum 事實推翻)。**勿再合稱「1d-WIRE」**——兩票前置條件完全不同:
    - **票 A — 策略 timing-overlap / clone score 診斷**:回答「ML 是否只是在做簡單因子規則」。**階段=Phase 4 或移出 IC 的 ML/回測評估新 epic**(canonical owner 應在 ML/Strategy evaluation,IC 只接 typed adapter;codex)。**開票前置=先修 equity curve 契約**:`prediction_analyzer.py:163` 欄位 `strategy_returns` 實裝 `np.cumsum`(非逐期報酬)、`:152` 只有 long/flat 無做空、`api/routes/pattern_analysis.py:1050` 缺值 `fillna(0)`。**IC→ML 橋非本票普遍前置**(僅 equity 版需要;position-only 版不需)。
    - **票 B — 真·多標的橫截面 attribution**:**階段=Phase 4**(貼 Phase 3 多 symbol 承載之後)。**條件觸發:只有宇宙變多標的才成立**。前置=CS factor-return 管線(現`factor_return_analyzer.py:272-287` 只收單一 `future_returns: pd.Series`,無 symbol/holdings/權重)+持倉權重 canonical 定義+xsec 與 deep 棧整合(`analyze_cross_sectional` 現完全繞過 deep)。
    - **根因備忘(防未來重撞)**:單標的下 `ls_returnᵢ=positionᵢ⊙r`、組合報酬=`position_p⊙r`,兩邊共用同一 `r` → OLS 只識別 **position 重疊度**,非風險曝險(codex toy:`q=p1`→β=[≈0,1,≈0],R²=1,殘差1.1e-16)。β 可誠實命名 timing-overlap,**禁冒充 Barra attribution**。與 1c-FR P1 canonical 同源限制(memory `project_1cfr_full_p1_canonical`)。
    - **優先序**:1d 清債 > 1f > Phase 2A/3 主線 >> 票 A >> 票 B。
  - **⚠️ 本檔既存不一致(2026-07-20 grok 抓,待另票修)**:上方 Phase 表(L43)將 **residual/邊際 IC 列 Phase 4**,但下方 L55 敘事寫「真 residual IC 歸 **Phase 2B**」。以 **Phase 表為準**(canonical);且 residual IC 與上述 attribution 兩票**是不同議題,勿混**。
  - **✅ 資源分配已決(2026-07-17 使用者)=全力收 Phase 1**(不與 Phase 2A 並進;P1 尾巴 LA-2→1c-FR-FULL→1d→1f 收完才啟 2A)。walk-forward/CPCV 已決=複用 ML 孤島(下方)。
- **決策**:walk-forward/CPCV **复用 ML 孤島**非重寫;contract-first 不硬接舊全 DataFrame 路徑。
- **狀態(2026-06-26)**:
  - **Phase 0 止血+正確性硬閘 ✅ 完成**(commit `11507f5`):CRASH/TIMEAXIS/BYVOL/FEATURE-GUARD/DECAY-LOG/UX-ERR 六 epic + 實機 45k smoke。
  - **Phase 1 正確性 kernel + contract 🔵 進行中**:
    - **1-contract ✅ 完成**(commit `e857834`):契約 DTO + 洩漏紅線(三方簽核,8 LEAK 全閉)+ Parquet artifact + API 版本化。
    - **1a 第一刀(單幣縱向接線)✅ 完成**:契約紅線接進 IC 主流程 `analyze()`——holdout 切分 + train-only fit(winsor/std/coverage/constant)+ OOS 報告 + purge≥horizon 防前瞻 + allowed_symbols/expected_freq 落實。**兩輪雙家族 adversarial(9 BLOCKING)+ 三方數據簽核 PASS(R1 抓 2 LEAK→修→R2)+ G-NEW 真實全 run 抓 2 整合 bug→修。default ON,OOS 不可行時分因回退(資料不足→full-sample 標記;時間軸壞→fail-closed)**。docs/IC_PHASE1_1a_CUT1_{SPEC,TODO}。
    - **1a 第二刀主體(cross_sectional 防洩漏)✅ 完成(2026-07-07,三方數據正確性簽核全 PASS)**:**F1** `_append_cross_sectional_labels` kline int64-ts→datetime 對齊(修第一刀 row_index 回歸暴露的橫截面標籤全 NaN,實測 0/5088→5085/5088 真 3sym×12h);**F4** per-symbol 覆蓋守衛 fail-closed(all-NaN/短序列無條件擋,推導下界非 magic floor);**F2** 單軸 labels_path fail-closed(symbol-aware/事件驅動 labels→Phase2 epic);**F3** 全域同步時間邊界 OOS holdout+purge+embargo(非 per-symbol 比例切,test-only 覆蓋全部 report 輸出)。**雙家族 adversarial SPEC review→reconcile D-1~D-4→雙 RECONCILE-STAMP APPROVED→freeze;Composer 實作→Codex code review 抓 F4 邊界 BLOCKING→fix-round→原提出方複驗閉合→三方 DATA-CORRECT PASS**;Claude 自跑 18 passed。docs/IC_PHASE1_1a_CUT2_XSECTIONAL_{SPEC,TODO}。
    - **剩餘刀順序已裁定(2026-07-08 三方委員會一致+使用者裁定,出處 handoffs/IC1A-CUTS-ORDER-{claude,codex,composer}.md)**:① 1-align 前瞻硬閘 ✅ 完成(2026-07-09,三方 DATA-CORRECT 簽核全 PASS;B1-B3+fixture 遷移 4 commit;重大破案=cut1 golden 舊 baseline 凍到 rolling IC join 0 列壞行為,已重凍;殘留見 HANDOFF)→ ② 1e HAC+1b FDR 合刀「顯著性正確化」✅ **完成(2026-07-11,B1-B5 入版 cfcf08e+e433500;假陽率 0.43→0.06;三方簽核全 PASS 閉合〔R4 codex DATA-CORRECT PASS〕;審計鏈 handoffs/IC1EB-*;殘留=1a cut1 golden 4 檔 provenance 閉合拆入 P2 債票 5,見 HANDOFF)**(大;**SPEC v2.2+TODO v2.2 已凍結 2026-07-09**:三方偵察→R1 雙家族 adversarial 雙 REJECT(4 BLOCKING 含 xsec `_label` horizon 丟失)→R2/R3 全 CLOSED→**使用者質疑觸發嚴謹度委員會**三腿 FREEZE-OK(HAC+BH=本層標準工具;M-B 增相關 null 實測把 PRDS 從假設變被測性質)→雙 RECONCILE-STAMP sha256:b77932d8;docs/IC_PHASE1_1E1B_SIGNIF_{SPEC,TODO}.md;baseline 快照 ✅(2026-07-10 v4:14 腿+xsec/full/event×2/labels-raise receipt;三家四輪 adversarial 複驗全 PASS;handoffs/ic1eb_baseline/+IC1EB-BASELINE-RECONCILE.md)→**B1 起 Grok 4.5 實作**(批次階梯,同批兩輪斷路器換 Codex)+Codex/Composer 雙審→三方簽核——2026-07-10 分工二調見 ORCH §1)→ 【使用者 2026-07-11 裁定:③ 之前先插一個獨立 P2 債 session(governance 9 紅 fixture 遷移 ✅ **完成(2026-07-11,151 passed 0 failed,完整中型管線+斷路器換手一次,docs/P2DEBT_T1_GOVFIX_{SPEC,TODO}.md)**/legacy 測試 data_cache tmp redirect ✅ **完成(2026-07-12,e6825d9;process-global patch+S1-S11 seam manifest+逐檔 digest oracle;final7 五 set 全綠 exit0;finding 鏈 C-1~C-5+雙家族審 CE8 全閉合;C-5 digest 抓到真洩漏證守衛可證偽;label horizon 既有紅拆票6)**/tsc 全部既存 errors ✅ **完成(2026-07-11,492c4cc;實測 11→0,vitest 31 綠,grok+composer 雙審)**/codex 沙箱卡死 ✅ **完成(669c6fa/59c691e;繞法固化 ORCH+根因=macOS workspace-write 族 #18243 非 #7852,Grok X 搜尋修正,A′ 避管線首選;持續蒐集 log)**/1a cut1 golden provenance ✅ **完成(2026-07-12,27fdb00;票5:誠實補史三事由+移 float64+append-only events+content-addressed reuse guard fail-closed〔6 mutation raise〕;replay Gate A 語意〔pytest golden〕/Gate B 因 gitignored 降手動限制;完整管線 SPEC→codex+grok 雙 BLOCK〔6+4 洞〕→R2 雙戳→實作→Gate B concur→三方 GOLDEN DATA-CORRECT PASS〔Claude+grok+composer〕)。**P2 債五票全清**);細目=HANDOFF Session 排程節)】→ **【IC-API-TEST-MODERNIZATION epic(票6 升級,使用者 2026-07-12「現在就做」)**:23 個 API IC 測試用 rng.normal 合成 fixture 違反真-kline 鐵律+多層 stale;三方共識=真 kline 衍生共用 session fixture(ETHUSDT/12h/~512,return_5+尾NaN)+分層 L0/L1/L2+去重 3;test_ic_e2e.py 同病 Phase2;RISK-HIT a/d 大完整管線;審計 handoffs/P2DEBT-T6-TESTSTRATEGY-*】→ **Phase 1 ✅ 完成(2026-07-12,56a9566;tests/fixtures/ic_api_real_kline.py 真 ETHUSDT/12h 衍生共用 fixture,31 passed,PIT 三方 DATA-CORRECT PASS〔Claude+grok+composer〕;完整管線 SPEC→雙BLOCK→R2 reconcile 雙戳+composer CONCUR→實作〔主委探診 warmup off-by-2〕;去重3+分層 L0/L1/L2;票6 23 nodeid 消化)** → **Phase 2/3 ✅ 完成(2026-07-12,a39dc6c;三方 scope 分類=遷移空集,5 momentum IC 合成測試全 LEGIT〔護欄/FDR/OOS/mutation 探針+管線煙測〕;Phase3=docs/IC_API_TEST_LAYERING.md 分層判準)。epic 三 Phase 全閉合。follow-up=票2 v6_baseline 可縮〔23 API 紅已由 epic 修綠+去重3〕** → ③ 1c Net IC 量綱(大;net_ic_analyzer.py:34 相關係數減報酬率;獨立 session 開)——**使用者參數已訪談(2026-07-14)**:①交易成本**不得寫死**(crypto/台股期/美股期各異)→ 前端使用者輸入+「是否啟用成本」勾選,全棧接線(後端+API+前端+wiring,防幽靈開關);②持倉頻率不定(1h~1w 皆可能)→ 成本分析一律情境掃描、不綁單一 timeframe 假設;③capacity 分析(participation_rate 1%)使用者不用→維持現狀標未校準、低優先。量綱修法已裁=**B-strict**(2026-07-14 三家 RULING 收斂:拆報告+報酬空間成本;禁 IC 減報酬率;`net_ic` 鍵全樹禁止;canonical 因子報酬序列拆票 **1c-FR**〔codex 實證 ls_returns reset_index 位置錯位〕,1c 內 breakeven/profitable fail-closed unavailable;成本公式去 ×2〔turnover 已含雙腿〕)。**SPEC v1.1+TODO r6 已凍結(2026-07-14)**:SPEC 五輪(17B→0)+TODO 六輪(15B→0)三家 adversarial 全閉合,雙 RECONCILE-STAMP 機檢 PASS;docs/IC1C_NETIC_{SPEC,TODO}.md;審計 handoffs/20260714-IC1C-*。**✅ 1c 完成(2026-07-14,B0-B3 四批 4 commits f1d85c5/2133c77/04ac6fb/+B3;每批 Claude 獨立實跑 Gate+雙審 APPROVE;B1/B2 經 codex 多輪退修+一次斷路器換手 composer;殘留=票 1c-FR canonical 因子報酬序列〔breakeven/profitable 實值〕另立)**;**1c-FR 四方委員會(2026-07-14)揭「無消費者」前提不成立**(錯位 ls_returns 預設 enabled 且活在 reporter/UI)→拆兩票:**①IC1C-FR-STOPGAP ✅ 完成(2026-07-14/15,B0-B2 三批 8be3056/41c26e0/81724c7;default-off 三態契約+統一收斂 sanitizer〔codex 三輪實證揪出 save_report/cache-hit/cache force-merge 三條洩漏路徑〕+AST consumer guard+前端兩圖三態下架;SPEC 四輪+TODO 三輪三家 adversarial,雙 RECONCILE-STAMP 機檢 PASS;docs/IC1CFR_STOPGAP_{SPEC,TODO}.md)** ②**IC1C-FR-FULL=1d 之後近期排入**(使用者 2026-07-14 定;canonical timestamp-aligned factor-portfolio return series 重建)。分工=Grok 實作/Codex+Composer 審查(2026-07-14 三調)→ ④ 1d attribution 正名+NaN fail-closed(中/大開工定;真 residual IC 歸 Phase 2B)→ ⑤ 1f 空圖 schema flatten+grouped schema 殘留併入(小-中,最後收尾)。**grouped_ic 崩潰止血已於 Phase 0 11507f5 完成,自清單移除**。1e+1b 若拆必 1e 先(反對先 FDR 接高估 p 值)。治理修補(SCAR):SPEC consumer-map 須含所有 reindex/merge 下游 + 真路徑 red-on-break 測試。
    - **🔴 IC-ANALYSIS-LOOKAHEAD-REMEDIATION epic 開立(2026-07-15,四方全面盤點+使用者裁定深修)**:1c-FR-FULL 稽核揪出上游洩漏→使用者要求盤點全 IC Analysis→四方(Claude+codex+composer+grok)實跑證 look-ahead **結構性瀰漫**。**核心洞察=之前只建「OOS切分+stage1 train-fit」防線,從未審分析模組『內部計算』,切分給假安心感**。master=`handoffs/ICLOOKAHEAD-MASTER.md`。**P0(預設路徑必踩)**:①`ic_engine.py:290` rolling IC spearman **全序列 pre-rank**(污染 rolling IC/ICIR/門檻/trend/centrality;現成 `_rolling_spearman` 窗內版未用)②stage5 `monotonicity_tester`/`turnover_analyzer` 全窗 qcut→因子淘汰門檻(0.6)③`data_preprocessor` 特徵 winsorize/zscore full-sample fallback。**P1**:regime rule 全期 vol 分位/long_short/fallback silent/FR。**使用者裁定=先 P0 統一整治,FR 併入統一 PIT helper**。每 Phase 完整管線+三家 DATA-CORRECT(a,d)。**1c-FR-FULL SPEC v0.6 ✅ FROZEN(2026-07-18)**(`docs/IC1CFR_FULL_SPEC.md`;canonical=P1 單標的擇時多空;PIT 分位)→併入本 epic。**演進**:R1-R4 adversarial→R4 分裂(Codex/Composer FREEZE-OK,Grok OPEN-R4-1 winsorize 契約自撞)→R5 三家確認閉合→**使用者質疑觸發 winsorize 存廢前提辯論→四方一致 REMOVE**(FR 是診斷非交易 PnL,裁尾藏尾部;砍掉整包 min_samples/M-winsorize/OPEN-R4-1 複雜度;`ls_return_full=position×future_return` raw identity)→三家戳記輪 RECONCILE-STAMP APPROVED,`reconcile_stamps_check.sh` PASS(body sha256:dd357efd)。審計=`handoffs/1cFRFULL-{WINSOR-PREMISE-*,SPEC-R5-*,SPEC-STAMP-*}`。**✅ 1c-FR-FULL 完工(2026-07-19)**:TODO R1→R3.1 四輪 adversarial 凍結→7 批 B0-F5(Grok 實作/Codex+Composer 雙審,每批 Claude 獨立驗;雙審攔下假綠護網×2/cache一致性/data_cache污染/假wiring/check-nodeids假receipt 等真洞)→**三方 DATA-CORRECT 全 PASS**(Claude+Codex adversarial+Composer;真kline PIT無前瞻+跨symbol隔離+hash+正名)。功能 enabled=True 上線。branch feat/ic-1cfr-full-impl(commit 5bafd45..daf78d7);審計 handoffs/1cFRFULL-*+ic1cfr_full_baseline/DATACORRECT-*。相關 memory `project_1cfr_winsorize_removed`+`project_1cfr_full_p1_canonical`。**下一站候選=1d attribution park**(偵察完成 handoffs/1d-RECON-*;含幽靈接線)/1f 空圖。
      - **✅ LA-0(P0)/LA-1(P1)/LA-2(P2) 全部完工並合併 main**。**LA-2(P2)完工(2026-07-18,branch `feat/ic-la2-p2-impl` 6 commits 463bfb5→7b4be86,已 merge main)**:治理=SPEC `docs/IC_LA2_SPEC.md` v0.5(R1-R5)+TODO `docs/IC_LA2_TODO.md` v0.4(R1-R4)三家凍結。實作 B0(baseline+骨架)→B1(winsorized label 禁用三層 fail-closed,DEC-1)→B2(model OOT-only 契約:綁 canonical SplitPlan+嚴格`<` off-by-one 閘+receipts field-wise sha256 不可繞+欄位級 eval_scope 28 path 表+calibrator 禁自簽+cal/PR/Brier/ECE=cv_oof)→B3(pattern 晉升 server 權威+factor typed loud proxy 因果化`shift(1)`+regime `_fit_global` 硬移除=收官 LA-1 §N)→B4.1(mutation 全套+golden 重基準)→**B4.2 三方 DATA-CORRECT PASS**(Claude+Composer 兩腿獨立收斂 DOUBT-1〔verify_oot_receipt 等號邊界無測〕→Grok 補 test〔nodeid 12→13〕→三方親跑 mutate `<`→`<=` 必 FAIL 證關閉;Grok=實作者不簽)。每批 Codex+Composer 雙家 review+finding-closure;final gate 31 passed 0 skip/xfail 真 kline。taxonomy 三分(C-1 causal-PIT/C-2 promotion-train-mask/C-3 diagnostic-loud)+軌2 model in-sample 樂觀。審計 `handoffs/LA2-*`。
      - **✅ LA-0(P0)完成(2026-07-16,branch `feat/ic-la0-p0-impl` 9 commits,未 push)**:三 P0 洩漏修復(B2 rolling IC 窗內 rank/B3 stage5 分位 PIT/B4 stage1 fit_mode 四出口;pit_stats 七原語;B0 改前 golden+B6 改後歸因表)。每批雙家 review(codex 每批抓真 finding 含 B4 `_is_type_feature` 讀未來真洩漏)+**三方 DATA-CORRECT PASS**(Claude+Codex+Composer)。SPEC v0.5.3/TODO v2.3 凍結;FR descope 移 1c-FR-FULL。**流程 scar**:中/大 review=Codex+Composer 雙家(ORCH §1),曾憑印象只派單家→做成機器閘門 `review_quorum_check.sh` 接 gate.sh。P1(regime/long_short)=LA-1 後續。
      - **✅ LA-1(P1)完工(2026-07-17,branch `feat/ic-la1-p1-impl` 7 commits,未合併 main)**:五洩漏全修(P1-1 rule 分位/P1-1b fallback/P1-1c kmeans Segment-causal/P1-2 long_short qcut/P1-3 fallback loud);每批 Grok 實作+Codex(Luna)+Composer 雙家 review+finding-closure;**三方 DATA-CORRECT PASS**(Claude/Codex/Composer,各自 adversarial 證可證偽)。收官抓 golden 帳本 bug(reverse-check symbol 盲)→BTC+ETH 對稱修。**regime-conditional IC 若要當決策級須另立驗證 epic**(kmeans 非最佳實務+小樣本雜訊;現只進報告非 gate)。
      - **(歷史)LA-1 治理(2026-07-16)**:SPEC v0.4.3+TODO v2.3 **雙凍結**(SPEC 4 輪 adversarial+5 輪 freeze-stamp 機器 hash gate PASS;TODO 2 輪 adversarial+codex closure 鏈 R3-R5 FROZEN-OK)。scope=P1-1 regime rule 全期分位+**P1-1b** kmeans fallback 同病+**P1-1c** kmeans `_align_labels` 全期命名(adversarial 抓,使用者裁併入完整修=Segment-causal,影響 XGBoost Market_Phase fallback〔已裁可接受〕,LightGBM 0 hits)+P1-2 long_short qcut(含 codex 抓的第三層=future-label availability 污染)+P1-3 fallback loud(root `analysis_status`+G-A2+禁內層 persist+5 oracle carrier)。批次 B0→{B1,B2,B3}→B4;Grok 實作+Codex/Composer 雙家 review+B4 三方 DATA-CORRECT。
      - **📌 deferred(2026-07-16 使用者定,見 memory `project_ic_feature_selection_funnel`)**:IC Analysis **全功能完善後**才定義**粗篩/精篩 funnel** 選特徵(選特徵邏輯要用 IC 各指標,先備工具再設計)。現況缺口=IC 無自動特徵上限,全量 43 萬丟預設 config 會 OOM(LA-0 窗內 rank 加重);與 **IC-PERF epic 合併**(Numba/chunk+特徵上限保護)。過渡=跑 IC 傳 feature_filter 先降維。
    - **✅ IC SPEC conformance pass 完成(2026-07-06)**：4 份 `IC_*_SPEC` 過 `template_check`（補 RISK-HIT+FACT-RECEIPT，不改設計/數值；受查發現 4 份皆對應已落地工作）。
    - **✅ IC 測試定向重驗完成(2026-07-06,含 Codex adversarial review)**：SPEC conformance 後重跑 51 個 Phase0/1 測試曾 45/6；6 紅根因＝goldens/run_selector 釘死舊 config_hash 未註冊 + run-selector 硬化(643c5c2)把「明確給 features_path 卻要求 config_hash 註冊」的 golden replay 路徑弄斷。**修法**：`ic_analysis_service` fail-closed 收斂到 registry 解析路徑（features_path 缺席才 raise；明確給 path 不擋），run-selector 靜默錯 run 保證不變（golden byte-equal + 2 hermetic 契約測試 + mutation 證偽 pin 住）；run_selector 4 測試改 is_materialized skip-guard（12h 資料 gitignored，誠實 skip 非造綠）。終態 **49 passed/4 skipped/0 failed**（VERIFY:20260706T052454Z-ic-reverify-final）。Codex [P1]（skip 掩蓋契約）已補 hermetic 測試閉合；殘留 [P2]：features_path 與 config_hash 不一致未校驗（pre-existing，另立）。FF 測試資料已就緒（3 sym×1h+12h 對齊、max_lag 後、`data_cache/features/`）。
    - **✅ run_selector 重凍完成(2026-07-06,含 Codex review)**：使用者補生兩套競爭 12h run（e53e2290+f754aad4，同 tf 不同 config、row 同 feature 異），重凍 generator/baseline/mini_registry/測試常數+防漂移不變式+3 sibling 測試改 hash；targeted 19 passed/1 xfailed（VERIFY:20260706T135518Z-ic-runselector-final）。
    - **✅ 第二刀首項 bug 修復完成（2026-07-07，全三方數據正確性簽核 PASS）**：`feature_library._attach_row_index`（鏡像 `_attach_cgsa_row_index`）在 V2 load 路徑貼回 `load_row_index_v2` 真時間軸；無 sidecar→no-op，長度不符→ValueError；只改 index，值/欄/列/檔大小不變（G-1 值守恆 + G-2 時間軸 byte-equal，真 12h run e53e2290/f754aad4 皆驗）。追蹤測試由 full-analyze xfail retarget 至失敗邊界斷言（218k 特徵 full analyze>17min 屬正交效能問題，歸「79 測試換真資料」epic）。清 bug 期中毒 ingest cache。**三方 PASS 零 BLOCKING**：Claude 自產 + Codex adversarial（語義時間 oracle 交叉驗列序 0 mismatch）+ Composer 資料正確性；RECONCILE-STAMP codex+composer APPROVED。docs/IC_PHASE1_1a_CUT2_ROWINDEX_{SPEC,TODO}。follow-up：ingest cache 版本化、1d 頻率地圖、conftest scoped-collect clobber golden。
  - Phase 2A/3/2B/4/5 未啟動——**全景+內容見上方「★★ IC Gatekeeper 七 Phase 全景」canonical 表**(勿再各處分列不同步)。

### P0.5 — IC 效能 + grouped_ic 崩潰止血(已盤點,可立即動)
- **為何**:使用者實測選 run 跑 analyze 卡死+崩潰;三方 reconcile 完成。
- **Epic**:`handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`(IC-CRASH/IC-FEATURE-GUARD/IC-UX-ERR=P0;IC-PERF=P1)。**狀態**:grouped_ic 崩潰止血已完成(Phase 0 11507f5);其餘(IC-PERF 等)未啟動(2026-07-11 校正,原「實作未啟動」與 L42 矛盾)。

### ✅ 制度改進案落地（2026-07-20/21；三家 GOV-NECESSITY-REVIEW 裁決 + GOV-IMPL-STAMP 四輪把關）
- **源起**：使用者一句「`unexplained` 需不需要存在」揭露 1d SPEC 六輪 adversarial 未抓的白工 → 三家判定「必要性盲點」系統性問題。
- **落地五處**：①SPEC/TODO 範本每 Task 加 `存活至`/`覆蓋風險` 欄（`template_check.sh` 機檢，legacy manifest 豁免既有檔）②adversarial §1 10→11 類（必要性/短命工）③ORCH 加 code review 效率題（≥10× 門檻 + hot path 觸發式）④症狀 C 分案=下方 GOV-XREF-SYNC ⑤`GOV-IMPL-STAMP` codex 四輪抓 7 個繞過洞全堵（啟發式規避/basename 碰撞/heading 變體/零 Task/fixture 矩陣等）。
- **審計**：`handoffs/GOV-NECESSITY-REVIEW-*`、`handoffs/GOV-IMPL-STAMP-*`。

### 🔵 進行中 — Gate/派工逃脫點 epic（2026-07-23；收斂工具首場實戰；`handoffs/reconcile/pipeline-gate-audit-r1/`）
- **源起**：舊 UNION 手抄盤點過時+會漏 → 用收斂工具正確重做。四家 canonical 獨立稽核 178 findings。
- **✅ reconcile 全鏈落地 (a)-(e)**：178 raw → **8 主題/51 仍開真洞 + ledger**；`completeness_check.sh --lock` exit 0（0 掉項/body-hash/lock）；三家語意複查 REQUEST-CHANGES 全納 v2；**RECONCILE-STAMP codex+composer+grok APPROVED**（body sha256:5501dc49）；🛑白話閘1 使用者拍板方向對。定案=`synth.md`。
- **工具流程真洞（待併 SPEC）**：過早凍結捕獲不合規源檔；重凍 FROZEN lock 只能靠 harness 旗標（正式路徑 fail-closed）。
- **★下一步**：(f) SPEC 修 51 洞（碼債優先 grok-gate/token-kind/waiver-bypass/jq-failopen/gatedir-override/completeness-scope；family-registry 為 root cause）→🛑白話閘2→(g) 分批修。

### P1 — GOV-FORMAT-SSOT：格式契約單一真相源（2026-07-30 立案，使用者定「**P1-6 B5 完工後**才做，不塞進 B5」）

- **共同根因**：**格式的定義在檢查器裡，但產出格式的人靠記憶**。契約有兩個真相源必漂移。
- **症狀 A（主委端）＝機器解析字串手寫**。本 session 實證 3 次，代價各不同：
  ① `RECONCILE-STAMP` 格式手寫錯（缺日期、前綴寫成 `body-sha256:`）→ 兩家白簽一輪、重派
  ② synth 的 `Verdict（綜合）：` 與 `gate.sh` 正則 `Verdict[[:space:]]*[:：]` 不符 → 拒發 token；
     **修該行必須動 body → 三家戳記 sha 全失效 → 整輪重簽**
  ③ 為修 ② 而在 `reconcile_build.sh` 骨架加佔位行，**該佔位行命中正則** → **fail-open**（沒填結論也能拿 token，
     codex 端到端實跑 `GATE PASS rc=0`）→ 又一輪裁定
- **症狀 B（委員端）＝格式檢查點在消費端而非產出端**。P1-6 B4 實證**吃掉 5 輪**（該批共 13 輪，佔 38%）：
  ```
  委員交件 → cx_run 只看「檔案存在且非空且 CLI rc=0」→ 記 success
           → 主委合併時才跑 completeness → 才發現缺「來源摘要」/ID 重複 → 判紅
           → 想叫同一家重寫 → Task 1.3 守衛⑥ 擋（最新已 success，拒重派）→ 只能開新輪
  ```
  守衛⑥ 本意防「一直重跑到拿到想要的答案」，但它把**「產出根本不合格」**與**「產出合格但主委不滿意」**當同一件事。
  實際犯例：composer 缺來源摘要 ×1／codex 缺來源摘要 ×1／codex `## ` 標題誤用 `COMPOSER-` 前綴致跨檔重複 ID ×1。
- **建議落地**（未啟動，待走完整管線）：
  1. **症狀 B 主修**：把 `completeness_check` 的**單檔格式檢查**前移到 `cx_run.sh` 判定 `result_state` 的那一刻
     ——不合格即 `failed`（同輪重派本來就允許）⇒ **B4 那 5 輪有 4 輪可省**。
  2. **症狀 A 主修**：凡需人寫的機器格式，一律由工具**從檢查器導出**（如 `reconcile_add_stamp_section.sh` 的作法）；
     骨架佔位**不得命中該格式的正則**（症狀 A③ 的教訓）。
  3. **併入 `GOV-ID-NAMESPACE-CHECK`**（B4 新增）：`## ` 標題的家族前綴須等於該檔產出家族。
     現況錯誤訊息指向**被冒用的家族**而非冒用者，主委因此誤判過一次。
- **免費止血（已即刻採用，不待本票）**：要寫機器格式前**先跑一次檢查器，抄它錯誤訊息印出的格式**
  （檢查器本來就會印必填形狀，症狀 A① 純粹是憑印象寫）。
- **⚠️ 為何不塞進 B5**：ROADMAP 已載舊版 SPEC 連八輪不收斂的根因＝**scope accretion（每次修訂新增機制）**；
  B5 已背一個 B3 遺留的必做項。**⚠️ 為何不插隊在 B5 前**：本票動 `cx_run.sh`（共用控制流）屬大任務，
  自身要走 4–8 輪完整管線，**高於它在 B5 內能省的 3–6 輪**；真正回報在後續每個 epic。

### P2 — GOV-XREF-SYNC：跨文件交叉引用同步機械化（2026-07-20 三家裁決分案，`handoffs/GOV-NECESSITY-REVIEW-*`）
- **本 session 累計實證 11 次**（原 6 次 + 戳記輪 5 次）；且戳記卡多輪的另一根因=brief 列死 task_id 未更新 + reconcile 舊 task_id 成抄錯源 → 落地應含「凍結前殘留掃描 + reconcile 脫敏 + brief task_id 機械生成」。
- **出生事故**：1d SPEC 過程「改了裁決卻未同步其交叉引用」**同類錯 6 次**（composer-v3B1／grok-v3B2／grok-v4B1＋composer-v4B1／composer-v5B1／codex v0.5 戳記輪 REJECTED），每次都由委員擋下並多耗一輪三家複審。
- **已試過但不足**：v0.4.2 新增 §D-MAP 裁決↔落地對照表，**只覆蓋 SPEC 內部**，不含 reconcile／ROADMAP／HANDOFF → 第 6 次仍漏。
- **三家一致：與必要性/效率案（症狀 A/B）分案**，理由=A/B 是「價值判斷缺席」靠人審，C 是「機械同步缺席」靠 grep；**混寫會讓 agent 用價值題敷衍 xref**（composer 語）。
- **建議落地**（未啟動）：① 凍結前 `grep` 已作廢措辭清單殘留數=0（舊 Phase 名、已刪 allow-add 鍵、舊版本號）② 擴 §D-MAP 為「SPEC 內 + 固定外部檔清單（reconcile／HANDOFF／ROADMAP 錨點段）」③ 可考慮併入既有 docdrift 機制。
- **優先序**：不擋 1d/1f；建議於 Phase 1 收尾後、或下次遇到同類錯時啟動。

### P2 — FF preset 移除盤點（2026-07-03 使用者排入,IC 正確性紅線之後做）
- **為何**:使用者從未用過/測過 professional_full 等 preset（2026-06-29 明示想移除）;現行測試/生成一律 base/full 全特徵不綁 preset,preset 定義成死碼+誤用風險。
- **範圍**:盤點所有 preset 定義與引用點（config/前端/文件）→ 確認零真實使用者 → 移除或明確 deprecate;涉 config schema 下游,走「中」型管線。
- **狀態**:已排程未啟動;不擋 IC。

### P2 — 文檔簡化 epic(2026-07-12 三家研究收斂+使用者定案兩批次,出處 handoffs/DOCDRIFT-SIMPLIFY-{STUDY-*,RECONCILE}.md)
- **為何**:ARCH(2044)+DEV_GUIDE(2434)=4478 行,漂移面大、假綠濃縮;真 ROI=抗漂移+消假綠(非省 token)。
- **範圍(兩批)**:A=修 TGF 斷鏈+建 ARCH `## Feature Factory 架構` 穩定 H2+刀1 已實現 853→能力索引(修假綠狀態欄)+刀3 目錄→~80+README 假行數;B=刀2 DEV 8 通用章→300-450+解耦枚舉→pointer(留 Artifact Contract/V2V3 why)+修 §1277+ 損壞 markdown。預期全檔→~2200-2500(−44〜−51%)。
- **鐵律**:驗收看資訊類型非硬行數;抽 contract 非整批上移;單檔 A/B/C 不拆 appendix;先建後刪 anchor。
- **狀態**:**批次 A 完成(2026-07-13)**——A00 manifest LOCKED→A0.1 FF H2→A0.2 DEV rename+TGF 斷鏈修復→A1 能力索引(853→表,native-tf drift+CAP-14 stage 舊錯一併正名)→A2 目錄+README;anchor checker(`scripts/check_doc_anchors.sh`+11 tests)入庫;§V 全套 gate PASS;ARCH 2044→935 行。每步 Codex 實作+composer/grok 對抗審+閉合重驗(4 輪 BLOCK 全閉)。**批次 B 完成(2026-07-13)**——B00 manifest LOCKED→B0 修損壞(byte==target view,被吞三章重見)→B1 八章壓縮(2382→823)→B2 解耦節收斂(935→643);post-state validator 全量 PASS。**epic 收官:全檔 4478→1466 行(-67%)**,契約全留可機檢、假綠清零、TGF 斷鏈修復。

### P2 — 解耦 Rule 4 既存違規修復(2026-07-12 doc 漂移施工揪出,使用者裁定立票、code 暫不動)
- **問題(不只 Rule 4,doc review 揭更廣)**:`check_decoupling.sh` 2026-07-12 實跑報 **R2=5、R3=12、R4=1** 全紅:
  - R4:`api/services/feature_factory_batch_adapters.py:9` service→service import(1 筆)。
  - R2:`momentum/Analysis/*` 直接 import `momentum/FeatureEngineering`(warmup_lookup/consumer_gate/feature_reader,5 筆)。
  - R3:api/services、api/routes 直接 import `momentum/FeatureEngineering` 具體工具未走 factory(run_locks/run_paths/hardware_utils…,12 筆)。
  - **phase4 scanner 只窄查特定檔**(R2 僅 strategy_backtest、R3 僅 2 factory、且不查 R4),故長期被誤報全綠。
- **待判定**:上述 R2/R3 是**真違規**還是 `momentum/FeatureEngineering` 應**豁免為共用基礎設施**(如 momentum.core)?屬架構判斷,須三方 triage(不是 doc 能定)。
- **Claude 初判(2026-07-13,待三方 triage 確認,勿當定案)**:被 import 的多為**共用基礎設施/唯讀介面**——`run_paths`(路徑 helper)、`run_locks`(per-run lease)、`hardware_utils`(tier 偵測)、`feature_reader`/`feature_library`(唯讀消費介面)、`consumer_gate`(fail-open 契約 helper)、`warmup_lookup`(warmup 查表)。性質接近已被 scanner 白名單的 `momentum.core`,**多半是良性共用底層**,非跨域伸手進別域內部業務邏輯。**風險低**(不碰數值/回測正確性 a/d、系統運作正常、無實際壞行為);**難度多為輕**:預期 triage 結論=把這批 shared-util/interface **納入 scanner 白名單或移入 momentum.core**(scanner 設定+doc 決策,非重寫);唯 R4 的 1 筆 service→service 需一個小 protocol/factory 間接(contained 改動)。它之所以「看起來嚇人」只是被半套 phase4 蓋住而靜默累積,非真的壞掉。
- **範圍**:triage 後,真違規者改走 protocol/factory 或明確把共用工具納入 scanner 白名單;動 api/services + momentum/Analysis 共用路徑(RISK-HIT b),走完整管線+驗證。
- **Triage 完成(2026-07-13,四家委員會,reconcile 雙 v2 戳記 PASS,見 handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md)**:最終裁決=**白名單豁免 13、修 code 後豁免 1(R2-4 去 private)、真違規改碼 3(R3-9/R3-10/R4-1)**;白名單機制 3:1 採用(Codex 少數意見存檔,吸收 symbol 級註記+scanner `import momentum.*` 盲區+R4-1 composition-root 必填注入)。**Claude 初判「17 豁免」被實證修正**:R3-10 實為現行 bug(`ic_analysis_service:1002` `FeatureLibrary()` 必炸 TypeError 被吞,永遠 fallback);consumer_gate docstring「fail-open」誤標(實為混合契約);hardware_utils=FF 運維政策表非純硬體。落地=三段:①即修小票(R3-10/R4-1/R3-9/R2-4)②白名單+scanner 機制票(單一機讀來源+精準匹配+戳記機檢)③P3(route 下沉/hardware 收斂/`_registry` 穿透)。
- **附帶**:scanner 覆蓋自身也要校準——`check_decoupling.sh` 的「Rule 6」只查 api/services 的 lambda monkeypatch(非所有 callback bypass),也不查 canonical R6/Rule 8;納 CI 前須先確立各檢查真實覆蓋範圍,勿再宣稱「查全」。ARCHITECTURE/PRODUCT_VISION 已據實標。
- **落地(2026-07-14,兩票完成)**:①DECOUPLE-FIX4——R3-10(ic_analysis 死碼 bug)/R3-9/R4-1/R2-4 四筆修復,4 commits,G1 等值+G2 run 選擇+M1-M4 mutation receipt,Composer+Grok 雙 PASS;②DECOUPLE-ALLOWLIST——R2/R3 改 **AST import 掃描器**(`scripts/check_decoupling_imports.py`,全 import 形式/縮排/同行覆蓋)+白名單 manifest(`scripts/decouple_allowlist.md`,module+symbol+owner+contract,**戳記機檢 fail-closed 內建 scanner**,CLI 無 bypass)+永久 regression 矩陣 31 tests+ARCH 單源 pointer。
- **P2 — DECOUPLE-TRIAGE-2(follow-up,2026-07-14 立票;07-14 使用者裁定拆兩段)**:①**pending 5 筆退場=綁 Optuna 重啟 epic**(2026-07-14 使用者定:Optuna 功能休眠至 IC/ML 完成後才開發測試,屆時整條鏈重驗,triage 順路做、驗證成本共享;manifest pending 表持續亮著防遺忘);②掃描死角修復=**DECOUPLE-SCAN2 完成(2026-07-14)**:R4 由 AST 接管(routes 面/相對 import resolve/nested package 通用化,grok code review 抓出 nested 假綠退修後閉合)+api/models 入 R3 掃描根(triage:DataSourceEnum 死 import 刪除、SUPPORTED_TIMEFRAMES 白名單 2:1 多數決,codex relocate-to-core-constants 少數意見存 manifest contract P3 註記+timeframe 重複副本債);manifest 10 條重戳 PASS;scanner ALL RULES PASS;矩陣 55 tests;另 `api/models/` 不在 R3 掃描根=已知缺口,擴根前須 triage 新紅字;**R4 grep 亦有 import 形式盲區**(`import api.services.x`/`from api import services` 不被 `check_decoupling.sh:60-65` 抓,codex 2026-07-14 實證,DECOUPLE-P3 以 T1d AST allow-set 對新檔手動 gate,系統性修法歸本票)。未啟動;不擋 IC。
- **P3 整理完成(2026-07-14,DECOUPLE-P3 票)**:①route hardware 組裝全量下沉 `api/services/hardware_info_service.py`(route 變薄,golden JSON 修前後逐欄相等);②hardware_utils docstring 正名 FF tier 政策表(AST dump 等值=零邏輯變更);③FeatureLibrary 唯讀轉發 façade(`get_entry`/`find_latest_materialized`),api 零 `_registry` 穿透。3 commits,Composer+Grok 雙 PASS。
- **狀態**:主票+P3 全部完成;殘餘=**DECOUPLE-TRIAGE-2**(pending 3 筆 triage/api-models 掃描根/R4 grep import 形式盲區)。

### P2 — 統計嚴謹度後續登記(2026-07-09 嚴謹度委員會三腿一致,出處 handoffs/IC1EB-RIGOR-{claude,codex,composer}.md)
- **策略層 data-snooping epic**:White RC/Hansen SPA/Deflated Sharpe/PBO=回測/策略選擇層,與特徵級 FDR 互補不互代;未啟動。
- **FDR 方法升級選項**:`fdr_by`(任意相依保證)/`romano_wolf`(resampling stepdown);M-B 相關 null 實測帶外時 BY 為既定升級路徑。
- **monotonicity long-short `ttest_ind`(i.i.d.)**:現未入閘故風險受限;若未來接 p 閘須先 HAC/block 化(P2)。
- **描述性指標正名**:ic_mean/icir/hit_rate/monotonicity/ic_decay/grouped=描述性門檻非檢定,文件標明即可(P3-P4);grouped 子樣本加 n 顯示歸 1f 刀順手。

### P2 — IC 輸出 Agent-readable + 顧問層(V2 願景地基)
- **為何**:使用者要 AI Agent 直接讀 IC 輸出、像委員會討論、回饋「哪些特徵/參數真的較好」+ 點破盲點。**前提=先修上面正確性**(否則 Agent 讀到污染數字會自信推薦過擬合假因子)。
- **範圍**:① IC 輸出結構化可機讀(穩定 schema);② 輸出含 FDR/OOS/DSR 嚴謹度指標(讓 Agent 分辨真好 vs 過擬合);③ Agent 解讀/委員會式討論層。**依賴**:P0 正確性紅線。**狀態**:概念,未規劃。

### P1 — fracdiff max_lag 截斷不變修復（2026-07-02 三方委員會立案,使用者定序）
- **根因**:`max_lag = min(max(2, len(df)//10), 252)` 以整段長度推導,把總長度洩進 d* 計算(600→60,590→59)→ 截斷不變性破壞。**非 look-ahead**(d* 校準只吃 first-500 prefix),量化因果安全,但屬真實作缺陷。三腿檔 `handoffs/20260702-FF-DSTAR-GATE-{CLAUDE,CODEX,COMPOSER}.md`;B2 回歸 receipt 20260702T042627Z(8 passed/2 fracdiff failed 揭露)。
- **順序(使用者 2026-07-02 定)**:FF 深稽全完成(護網完工)→ 本 epic 修 max_lag(改由 calibration/固定推導;**會改全部 fracdiff 特徵值**,命中 (a)(d) 走完整管線+三方值守恆)→ 修完 2 個 strict-xfail 截斷測試應轉綠 → **重新生成 FF 定版給 IC**。併 P1-FF-6(d*/fracdiff probe)避免重工。
- **現況（2026-07-03 epic 主體完成,詳見 handoffs/20260703-FRACDIFF-MAXLAG-*）**:
  ①max_lag 缺陷已修（`_resolve_fracdiff_max_lag` calibration-derived=50+config 顯式欄位）並經 golden 等價鏈證明（receipt 085226Z:修後 auto ≡ 修前 pin50 全欄 digest 0 差異、非 fracdiff 欄 0 差異、G2' config 路徑 ≡ R）;
  ②附帶修復:fracdiff FFT 卷積尾擾捨入洩前綴（`_hurst_prior._convolve_1d`+孿生 `_frac_diff_convolve` 改 direct）;發現並修復 pydantic 靜默丟棄 config max_lag（逃生口本是幽靈）;
  ③**兩 MR 維持誠實 xfail（reason 已換）**:卡在 pre-existing storage codec bug（見下一節）,轉綠時點=storage epic 完成後;max_lag 面護網=d\* gate+3 mutation 探針+full_fit/calibration(單邊重設計)控制;
  ④P1-FF-6 cache key mutation 探針落地（7 mutant 對準 v3 guard）。

### P1 — FF storage codec 截斷變異（2026-07-03 R3 委員會確認根因立案）
- **根因（已確認,非假說）**:L7 raw per-column parquet codec（float16/32）依**全窗值域**選型（feature_storage.py:2554-2588）→ 窗長/尾值變化使同欄跨 run 選型翻面 → 儲存精度不可比。症狀:①近零分母大值 float16 溢出→inf→sanitize NaN（截斷 MR idx508 artifact）;②ULP 級 2^-7 值差（尾擾 MR dtype dump）。證據鏈:`handoffs/20260703-FRACDIFF-MAXLAG-{MRFAIL,R3}-*.md`+receipts 054245Z/094044Z 差分。
- **修向**:codec 選型決定論化（不依全窗 stats,如固定 dtype 或依 calibration 段選型）;修完兩 fracdiff MR xfail 應轉綠。命中 (a)(b),走完整管線。

### P1 — Productionization Epic（全棧參數持久化）★上線前置
- **為何**:任一特徵/模型要上線推論前必做,否則 train/serve 分布偏移、模型靜默失效。三方三輪盤點 CONVERGED。
- **權威範圍清單**:`docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md`(全棧三層)。
- **子項(優先序)**:
  1. **fracdiff d\* 持久化 / 固定參考**(最高;同時解 cross-window 可重現 + train/serve;見 [[project-dstar-first500-optiona]])。大任務,命中 (d),走完整管線。
  2. A-schema:訓練特徵清單 pin(上線同欄位)。
  3. A4 safe_denominator 改 causal;A5 labels winsor 改 train-split 或棄用。
  4. B 累積(OBV/AD/ADOSC/SAR)一致 reset + state;C L5 reference 可得性。
  5. IC/ML 層:模型權重 + scaler 統計 + 選中特徵集 + 校準映射 隨模型留存。
  6. Optimization 層:Optuna best params 隨部署留存。
- **狀態**:盤點完成(inventory),修法未啟動。V1 未上線故非急,**上線觸發即啟動**。守則已加 serving-parity 判斷樹(`FEATURE_DEVELOPER_CHECKLIST.md`)防新組件再引入未留存參數。

---

## 🅿️ 已決定擱置（非急,有觸發再啟）
- **B7 L6.5 並行**(P2):MTF 細→粗罕見,ThreadPool 需 nogil 才 4.3x。見 [[project-mtf-direction-b7-parked]]。
- **T-A per-layer 串流釋放**(P1,磁碟):scaffold 已存,砍 RSS 峰值根本解。磁碟再緊則啟。
- **T-B float16 暫存 / T-D 28GB 取證 / gstack 清理**:低優先。
- 既有壞測試:`frontend/src/__tests__/strategy-components.test.tsx` 缺 SignalTooltip(可另開小修)。

---

## 🔭 未來 Epic（更遠,待 V1 穩固）
- **FF preset 盤點/移除**（2026-06-29 使用者提,B2 後啟）：未用/未測 preset(professional_full / ml_optimized / trend_focused / intermediate_research / fibonacci_full / basic_essential…)= 死碼/可能 config bug 的未測路徑。使用者從沒用過 professional_full、想移除但未討論。**範圍**:盤點每 preset 有無真 caller、前端真送哪些、哪些從沒被測 → 給清單再決定移除。命中跨模組共用路徑(config_manager/前端 toggle)→ 走完整管線。B2 因果測試已改 base/full 全特徵(不綁 preset)。
- **多資產擴充**:台指期 / 美指期 + 基本面/總經/月季報/籌碼/三大法人。核心=**PIT 對齊**(公告時戳 + vintage),幾乎全「粗→細」(見 [[project-mtf-direction-b7-parked]])。新數據源另立 epic。
- **V2.0 對話式研究** / **V3.0 自主研究員**(見 PRODUCT_VISION)。

---

## ✅ 近期已完成（2026-06 / 2026-07）
- **TEMPLATE_GATE_FIX epic（2026-07-05）**:派工品質防線修補——四方委員會(Claude+Codex+Composer+Gemini)審 template/機檢,實證 2 BLOCKING 繞過(FACT-RECEIPT/§G 逃逸)+多處範本↔機檢漂移;修=§A 段級狀態機+RISK-HIT 宣告制+per-Task 分段檢+RESULT 交叉規則+gate --reconcile 閉合鏈+adversarial 實核義務+TODO prompt 憲法瘦身(省每次 ~5,100 行)。驗收=14 fixture 矩陣+4 mutation+5 gate fixture+Codex 總 review 戳記。文件=docs/TEMPLATE_GATE_FIX_{BRIEF,SPEC,TODO,MANIFEST,GRANDFATHER}.md;現役文件 grandfather(僅新文件適用)。**新寫 SPEC 須帶 RISK-HIT: 宣告與 FACT-RECEIPT**。
- **FF 一致性整併**:Q5/B1/B2/B3/B5/B6/B4/B8(觀測性 + 批次日期修復 + warmup-then-trim + 批次刪除/保留 UX)。每項走完整管線。
- **Feature Explorer 圖表修復**:Y 軸貼合線 + Shift+滾輪 Y 縮放(rolling band 不撐爆 domain)。
- **d\* 實證量化**:三方證 Option A 非二階(cross-window selection 不穩),固定參考為修法(納入 P1 epic)。見 [[project-dstar-first500-optiona]]。
- **上線須留存參數盤點**:三方三輪 CONVERGED,產出 P1 epic 的精確範圍清單。見 [[project-stateful-param-audit]]。
