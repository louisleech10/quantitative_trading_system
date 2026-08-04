# 凍結文件修訂程序 — 實作 backlog（**不是程序正文，不具規範效力**）

> ## 🔴 編號命名空間警告（2026-08-04 補；使用者當場指出混淆）
>
> **本檔的 `B-1`～`B-23` ＝ 治理待辦「票」**，自 2026-08-01 起累積，與任何批次無關。
>
> ⚠️ **`docs/GOV_DISPATCH_FLOW_FIX_TODO.md` §B 的 `B0`～`B4` ＝ 該 epic 的「施工批次」**
> ——**兩套編號完全無關，只差一個連字號**。
>
> 使用者原話：「不是只到 B4 嗎？為何你說 B11-B22，那 B5-B10 是什麼？」
> ⇒ **這是主委造成的命名空間撞號**，與 `M24–M27` 撞既有 M ID、自造 `V13` 撞真實 `V13`
> 屬**同一族錯誤：新增編號前未盤點既有空間**（同日第五次）。
>
> **引用紀律（即刻生效）**：本檔一律寫 **`票 B-N`**；GOVFLOW 批次一律寫 **`批次 BN`**。
> 🔴 **不得只寫 `B11` 這種無前綴形式。**

---

# 📋 全票索引（2026-08-04 建立 → **同日經三家 triage 裁決**）

> 🔴 **本索引已經 `BACKLOG-TRIAGE` 輪（codex＋composer＋grok，24 findings／4 P0）逐條裁決。**
> 主委初判**被推翻 4 處**，逐項具名於下。裁決依據皆為**實跑**，不採宣稱。

**狀態圖例**：✅ DONE｜🗑 OBSOLETE｜🔗 MERGE｜⬜ KEEP（OPEN）｜🟡 部分完成

---

## 🔴 三家 triage 的裁決總表（**先看這張**）

| 票 | 主委初判 | **三家裁決** | 依據 |
|---|---|---|---|
| `B-1`／`B-2`／`B-3` | OBSOLETE | **🗑 OBSOLETE**（三家一致） | 引用節號在 v2.0 **0 命中**；v2.0 §6 明文取代 v1.0「不新增檢查器」。🔴 **殘餘機檢需求不得掛回這三個舊票名**〔grok〕 |
| `B-4`／`B-5` | OBSOLETE | 🔴 **⬜ KEEP——主委被推翻**〔`CODEX-R11-P1-01`〕 | **舊標的被取代，但實質控制需求仍存續**。主委複驗：`gate.sh:528`／`:555` 的 `""\|waived:*\|stamped-waived:*) : ;;` **兩處直接跳過仍在** |
| `B-6` | KEEP | **⬜ KEEP** | — |
| `B-7` | DONE（低信心） | **✅ DONE**（三家一致） | composer：原始驗收（`open_ev.task_id`→prompt 注入＋`check-task-id`＋V1–V16 oracle）**已落地**；grok：`f8922dd` ＋ `test_stamp_taskid_inject.py` **67 passed** |
| `B-8` | KEEP | **⬜ KEEP** | — |
| `B-9` | ❓待判 | **⬜ KEEP（明確不 DONE）** | 🔴 **不得因 v2.0 §5「提案 C」判 DONE**——§5 C 管延伸檔 touchset／索引投影；**v2.0 §6.3 仍點名本票為階段 1 硬前置**，且 `register-output` 仍拒絕 `docs/`〔composer＋grok〕 |
| `B-10` | KEEP（繞法在用） | 🔴 **✅ DONE——主委被推翻**〔`GROK-R11-P0-02`〕 | commit `901a8d9` 已落地 dext kind＋gate 路由＋測試；主委複驗 `grep -c dext` → **13** |
| `B-11` | MERGE 候選 | **⬜ KEEP（吸收 `GOV-FAILOPEN-GUARD`）** | 同病根，**舊票吸收**〔grok P2-04〕 |
| `B-12` | KEEP | **⬜ KEEP** | — |
| `B-13` | MERGE→`B-18` | 🔴 **⬜ KEEP（改為吸收 `B-18`）——主委方向錯**〔`GROK-R11-P1-03`〕 | **`B-13` 是泛用宿主、`B-18` 是 reconcile 特例** ⇒ 應 `B-18`→`B-13`，非反向 |
| `B-14`～`B-17` | KEEP | **⬜ KEEP** | — |
| `B-18` | KEEP | **🔗 MERGE→`B-13`** | 見上 |
| `B-19`～`B-22` | KEEP | **⬜ KEEP** | `B-22` 與 `GOV-UNTRACKED-PRODUCT-GUARD`② 由**舊票吸收**〔composer P2-02〕 |
| `B-23` | MERGE 候選 | 🔴 **⬜ KEEP（不整票併）——主委被推翻**〔`GROK-R11-P2-01`〕 | 與 `GOV-FULLWIDTH-VAR-SCAN` **僅部分重疊**；allowlist 反轉 ≠ fullwidth 變數掃描，**須具名分工不得整票 MERGE** |
| `B-24`／`B-25`／`B-26` | KEEP／MERGE／KEEP | `B-24` **⬜ KEEP**｜`B-25` **🔗 MERGE→`GOV-XREF-SYNC`**｜`B-26` **⬜ KEEP** | `B-25` 三家一致：**舊票吸收新票，保留 2026-07-20 三家裁決脈絡** |
| `B-27`／`B-28` | — | **⬜ KEEP（新開）** | 🔴 **triage 輪之後才開，未經三家裁決**。`B-27` 已機械確認無既有票涵蓋（七組語意詞零命中）；`B-28` 是主委登記缺陷的補正（漏登「把三支腳本做出來」這條路徑）。**下輪委員審時應一併裁決** |

### (c) 未編號票的裁決

| 票 | 裁決 | 依據 |
|---|---|---|
| `GOV-ID-NAMESPACE-CHECK` | **✅ DONE** | family-binding 已在 `completeness_check`／`cx_run` 交件路徑〔grok P2-02〕。🔴 **勿與 `票 B-26` 配置閘混淆** |
| `GOV-RECONCILE-LOCK-IMMUTABLE-DEADLOCK` | **✅ DONE** | 〔`CODEX-R11-P1-04`〕 |
| `GOV-XREF-SYNC` | **⬜ KEEP（吸收 `B-25`）** | 保留 2026-07-20 三家裁決脈絡 |
| `GOV-FULLWIDTH-VAR-SCAN` | **⬜ KEEP** | 與 `B-23` **部分重疊，各自保留並具名分工** |
| `GOV-UNTRACKED-PRODUCT-GUARD` | **⬜ KEEP（吸收 `B-22` 呆滯判定面）** | — |
| `GOV-FAILOPEN-GUARD` | **🔗 MERGE→`票 B-11`** | 同病根 |
| `GOV-FAILOPEN-GUARD-PROBE` | **⬜ KEEP** | 保留為獨立探針票〔grok P2-04〕 |
| `GOV-NO-FINDINGS-RECEIPT` | **🔗 MERGE→`GOV-NOFINDINGS-SENTINEL`** | 同一件事兩個名字 |
| `GOV-NOFINDINGS-SENTINEL` | **⬜ KEEP（吸收上者）** | 🔴 **`completeness` 接受空殼 P3-00**，本 session 每份 brief 的 sentinel 要求**從未被機器驗證** |
| `GOV-VERIFY-RECEIPT-RUNNER` | **⬜ KEEP** | — |
| `GOV-FIXTURE-PARALLEL` | **🗑 OBSOLETE（保留風險記錄）** | 已明示接受的序列執行限制，**作為實作票作廢但風險記錄留存**〔codex P2-01〕 |
| `GOV-PREFLIGHT-SNAPSHOT-LOCATION` | **⬜ KEEP** | — |

### 🔴 主委「零掉項」宣稱**不成立**——三家同時指出

〔`CODEX-R11-P0-01` [BLOCKING]＋`COMPOSER-R11-P2-01`＋`GROK-R11-P2-03`〕

**仍無 `票 B-` 編號者**：
1. **(b) 那六張 `TODO §N` 票**——`GOV-CLAIMCHECK-VS-VERBATIM`／`GOV-COMPLETENESS-FAMILYPREFIX-FP`／
   `GOV-GATECHECK-DEBTCLEAR-DEADLOCK`／`GOV-MANIFEST-INFLATION-RESIDUAL`／
   `GOV-RECONCILE-LOCK-IMMUTABLE-DEADLOCK`（已判 DONE）／`GOV-SPEC-REV6-STALE-COUNTS`
2. **(d) `mutation_probe_static.py` 對 subprocess 型探針的 false-negative**
   ——🔴 **codex 明示「本輪不擅自分配 `票 B-27`」**，須另行正式登記

⇒ **主委的「候選 ∖ backlog = ∅」只證明「票名字串有出現在檔內」，
不證明「每張都有 `票 B-` 編號與 owner」。** 這是**量測到的東西 ≠ 想證明的東西**，
與同日「grep 命中數當完整性」同族。

### 🔴 v2.0 自身也犯了 `B-1`～`B-5` 的同一個病（本輪新發現）

主委實跑：
```
scripts/section_sig_check.sh      不存在
scripts/dext_touchset_check.sh    不存在
scripts/stamp_legacy_registry.json 不存在
```
v2.0 §6 的檢查器白名單**逐支列出**這兩支，§4 依賴 grandfather registry——**三者皆不存在**。

⚠️ **主委初版把此判為「v2.0 重演了 `票 B-1`～`B-5` 的病」，該判定過重，已於同日自行修正**：
v2.0 §7 有**遷移階段表**，且 §7 的閉包表 ④ 欄明列
`dext_touchset_check.sh`／`section_sig_check.sh`／stamp row validator 為
**「本程序新增元件」**——即**待建**，非宣稱已存在。**與 v0.5 把不存在腳本寫進可執行 oracle 表不同。**

🔴 **真正的問題是內部不一致**：
- §7 把三者當**階段 1 待建元件**
- 但 §3 `:151` 寫「`section_sig_check.sh` 與所有 stamp brief **必印** TSV」、
  §5 `:338` 寫「**掛點**：`scripts/dext_touchset_check.sh`，由**產出端**呼叫」
  ——**皆為 operative 語氣**，讀者會以為已在運行

⇒ **待開票**：①三者標註須全檔一致（`待實作` vs operative）②階段 1 未完成前，
引用 v2.0 §3／§4／§5 的機制時**不得宣稱已有機械保護**。
⚠️ **主委 2026-08-04 即以 v2.0 §6 為判準宣告 `票 B-1`～`B-3` OBSOLETE**
——該判準本身的階段 1 尚未落地，**判定仍成立**（依據是節號 0 命中與 §6 明文取代），
但**引用時須知其強制力尚未存在**。

---

## 第一群：凍結程序 v0.5 的「正文引用了不存在的腳本」（`票 B-1`～`B-5`）

> **共同背景**：程序 v0.5 §9 的 oracle 表有多列指向 `spec_binding_check.sh`／`manifest_parse.py`
> ——**兩支腳本都不存在**。依正文「列不出四欄的機制一律不寫進程序」，那些列是不可執行空殼，
> 故移入本檔。**腳本合併並通過三態驗證後，該列才可加回正文。**
>
> ❓ **五張共同的前提疑慮（2026-08-04 提出，未確認）**：
> 程序已於 2026-08-03 升 **v2.0**，其 §6 把 v1.0 的「**不新增任何檢查器**」改為
> **具名有界檢查器白名單**。⇒ 這五張的立票前提（「不得新增檢查器故移出正文」）**可能已失效**。
> 🔴 **主委未確認**，不得逕行結案或逕行實作——**須先讀 v2.0 §6 判定。**

| 票 | 發生什麼 | 要修什麼 | 現況 |
|---|---|---|---|
| **B-1** `spec_binding_check.sh` | 正文 §3.3-A 的 A0–A11 判定無實作 | 建該腳本。**實作陷阱兩條（committee 實跑，不得遺漏）**：①A0 與 A1 **不是獨立 oracle**——unset env 後 `git ls-tree HEAD` 仍為 `120000`，**須同時移除兩者才轉紅** ⇒ A1 須改用不受 env 影響的取樣，否則應合併成一列 ②`patch_path` 的「未 commit」分支缺 tracked-path 檢查——未追蹤的 `valid.patch` 其 `git ls-files --error-unmatch` rc=128 但 `git apply --check` rc=0，**只驗後者的 mutant 不成立** | ⬜ ❓ |
| **B-2** `manifest_parse.py` | 正文 §4.2 的 manifest 解析與三項判定（`supersedes` 子集／extension 衝突／`state` 值域）無實作 | 建該腳本。**約束：單一實作，禁止各檢查器自行以 awk/sed 解析 yaml**〔`COMPOSER-R4-P2-01`：不同 tokenizer 對巢狀結構與引號會得出**不同子集結果**〕 | ⬜ ❓ |
| **B-3** `rejections.yaml` validator | v0.5 **誤把** §7 的四欄完整性驗證指給 `manifest_parse.py`〔`GROK-R5-P2-01`＋`COMPOSER-R5-P1-02`：**機制域名不符**，實作者會把拒絕登錄檢核塞進 manifest 解析器或漏做〕 | 改為**獨立 validator** 或 `reconcile_stamps_check` 的子命令 | ⬜ ❓ |
| **B-4** 戳記區白名單 | 正文 §4.4 未實作 | 實作 §4.4；**遷移影響已實測**（見程序正文 §4.4） | ⬜ ❓ |
| **B-5** `gate.sh` 落地缺口 | `CODEX-R5-P0-01` 實跑：現碼與正文 §3.4／§7b 有兩處差距——①`gate.sh:488-528` 的 `""\|waived:*\|stamped-waived:*) : ;;` **直接跳過** ②`reconcile_stamps_check` 呼叫**只在 `if [ -n "${spec}" ]` 分支內** | 補齊兩處。**正文須以「待實作」標示，不得寫成現在式** | ⬜ ❓ |

## 第二群：治理工具票（`票 B-6`～`B-12`）

| 票 | 發生什麼 | 要修什麼 | 現況 |
|---|---|---|---|
| **B-6** `GOV-TOKEN-WORKTREE-BIND` | `gate.sh` token 未綁 worktree（既有 `GATE-TOKEN-BINDING` 債的延伸）。⚠️ 現行 token **只驗 mtime 新鮮度、不比對內容**：900 秒內授權任意 task-id／任意 intent，且固定檔名無 session 區隔 ⇒ **跨 session 互相延長有效期（fail-open）** | token 綁 worktree | ⬜ |
| **B-7** `GOV-STAMP-TASKID-INJECT` | **要求委員手抄 task-id，抄錯是必然而非偶然**——R4 有**兩家**抄了 brief 的格式範例字串，provenance 機檢擋下，**多花兩輪補正** | `cx_run.sh` 已注入 `ROUND_ID`，應同樣注入 `TASK_ID`，brief 改為「用注入值」 | ✅ **已完成**——內容經 D-001 落地，D-001 於 2026-08-04 因 P16 走 R 而 `SUPERSEDED-BY-R`，**條文已併回 P16 v3.0 Task 1.3 改法⑧⑨**（`c0a7004`） |
| **B-8** `GOV-REJECTED-LIST-ACK` | `handoffs/gov_rejected_mechanisms.tsv` 的 append **無任何他方確認** | append 須**至少一家非主委 ACK** 或寫入 audit。現行緩解僅「`--rejected` 覆寫限測試 harness」＋「每次執行印清單 sha256」 | ⬜ |
| **B-9** `GOV-DOCS-STAMP-PROVENANCE` | **`docs/` 內的 D 延伸檔無法取得可過機檢的戳記**：①`reconcile_stamps_check.sh:67` 對每枚戳記跑 provenance ②provenance 需 `output_path` 指向該檔的事件 ③唯一入口 `gate.sh register-output:166-169` **明文只收 `handoffs/` 內檔案** ⇒ 程序 §3.2 的機檢**不可執行**。且 §3.2 與 §3.1／§2 **互相矛盾**。**事故**：2026-08-02 codex 依 `AGENTS.md` 第 12 條對 `docs/…D-001.md` 直接跑機檢得 rc=1 而正確停工，**燒掉一輪派工** | 唯一可執行讀法＝**戳記放收斂檔**（v1.0 自身即以此定案）。**修法須走程序 §5 的 R**（完整三家審＋使用者裁定） | ⬜ ❓ 須確認 v2.0 是否已處理 |
| **B-10** `GOV-DEXT-TEMPLATE-KIND` | **`template_check.sh` 沒有 D 延伸檔的 kind**：`gate.sh:588` 對 `--spec` 跑 `template_check.sh spec`，要求完整 SPEC 錨點，但 D 延伸用的是另一套模板 ⇒ **`gate.sh dispatch --spec <D延伸檔>` 永遠拒發 token**。**事故**：2026-08-02 實作派工 `TEMPLATE FAIL (spec)`，**燒掉一輪派工** | ①`template_check.sh` 新增 `dext` kind ②`gate.sh` 對 `*.D-NNN.md` 路由到該 kind | ✅ **DONE**〔`GROK-R11-P0-02` 指正〕——commit **`901a8d9`** 已落地：`template_check.sh` 新增 `dext` kind（10 個必填錨點）＋ `gate.sh` 對 `*.D-NNN.md` 路由 ＋ 測試（含 `R1-P2-04` glob 跨 `/` 的巢狀路徑誤判修正）。主委實跑複驗：`grep -c dext scripts/template_check.sh` → **13**。<br>⚠️ **主委兩次錯**：①索引原標 🟡「根治未做」②2026-08-04 triage 派工時 gate 拒發 `--spec docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md`，主委宣稱「**正是 B-10 的病當場發作**」——**錯誤歸因**：該檔是**程序文件**當 `--spec` 傳，`dext` 路由只認 `*.D-NNN.md`，與本票無關 |
| **B-11** `GOV-FAILCLOSED-DEP-GUARD` | 病根一句話（composer）＝「**治理檢查器把『依賴缺席』當成『檢查不適用』而非『檢查失敗』**」 | ⚠️ **主委原案（靜態探針當硬 gate ＋ `# OPTIONAL-DEP:` 註記豁免）已被實跑否決**——誤判率 100% 且會漏抓真陽性；單純註記三家一致判為**橡皮圖章**。**採委員改寫版**：靜態探針**降級為 tripwire 警告**／**隔離 runtime mutation 當硬 gate** | ⬜ 不阻塞 T1。🔴 **與 `GOV-FAILOPEN-GUARD` 同病根，待併** |
| **B-12** `GOV-TESTHARNESS-SCRIPTLIST-SSOT` | 測試 harness 的腳本複製清單**無單一來源** | 建立 SSOT | ⬜ |

## 第三群：2026-08-04 治理根因整治批（`票 B-13`～`B-26`）

> **使用者定死三方針**：①不得再以新增規則／記憶／紀律解決 ②一律往機器可驗／機械閘走
> ③**不得再在散文／文字／字體層面撞牆**，解法要避開該模式。

| 票 | 發生什麼 | 要修什麼 | 現況 |
|---|---|---|---|
| **B-13** `GOV-MERGE-COMPLETENESS-CHECKER` | 文件搬遷無機械完整性檢查。**事故**：P16 走 R 需併回 D-001（238 行），**首版漏 §D3 執行契約／§D5／§D6，補併又漏 §D4／§D7／V13–V15**，兩輪三家對抗審（R8 28 findings／R9 17 findings）**本不必發生** | `merge_completeness_check.sh`：來源原子單位 ∖ 已宣告落點 ≠ ∅ ⇒ rc=1；反向亦驗（防捏造）；目標檔 ID 撞號 ⇒ rc=1 | ⬜ 🔴 **與 `B-18` 應合併為單一檢查器**（同機制不同輸入） |
| **B-14** `GOV-CURSORAGENT-POSTWRITE-HANG` | `cursor-agent` 寫完產出後**不退出**。**實測**：三家 18 分鐘內全部交件，`committee_run` 卻**空等 2 小時 20 分**；根因＝sandbox shell 卡在 `snap=$(command cat <&3)`（fd 3 讀取永久阻塞，CPU time `0:00.00`） | `cx_run.sh` 加 per-family timeout：逾時且**產出已完整**視為成功並終止；產出不完整則記 `failed`／`format-failed`。🔴 **不得只加 timeout 就殺** | ⬜ **繞法**：派工後每 10 分鐘輪詢進程樹＋產出檔 |
| **B-15** `GOV-GATECHECK-READONLY-PGREP-FP` | `gate_check.sh` 把**唯讀查詢**誤判為派工（本 session 三次：`pgrep`／讀產出檔的 for 迴圈／`completeness_check --lock`） | ①白名單純讀取動詞在無寫入重導向時放行，或②改以「是否呼叫 `cx_run.sh`／`committee_run.sh`／`gate.sh dispatch`」為判準。**須附 mutation：真派工在新判準下仍須被擋** | ⬜ **繞法**：拆成不含家族名的多條簡單指令 |
| **B-16** `GOV-PROSE-CONTRACT-DETECTOR` | **機器依賴的契約長在散文裡**，導致「用 regex 解析 markdown」成為必經之路。**事故**：`grep -cE '^\| *V[0-9]'` 數 D-001 得 12，實際 **15**——匹配不到 `\| **V13** \|` 粗體列；漏掉的 **V14 是「禁止兩次 grep 交集」契約的唯一 oracle** | ID 樣式**同時出現在 `.md` 與 `scripts\|tests`** ⇒ 必須帶 generated-source 標記，否則 rc=1 ⇒ **新散文契約無法出生** | ⬜ 🔴 排序第一 |
| **B-17** `GOV-CONTRACT-TABLES-TO-DATA` | 四張機器依賴的表（`V1–V16`／`M1–M38`／`PHASE_MAP`／逐節落點表）全為**手寫 markdown** | 改結構化資料＋生成視圖。**本票是刪除非新增**。先例：`audit_events.json`／`governance_roles.json` **同日零事故** | ⬜ |
| **B-18** `GOV-RECONCILE-SKELETON-PREFILL` | 收斂步驟是**自由書寫**，漏一項不會被擋。本 session 的漏處置／捏造 ID／漏搬章節**全部集中於此** | `reconcile_build.sh` 已抽出所有 ID ⇒ 順便產**預填骨架**（每 ID 一個 `<待填>`），殘留即擋 | ⬜ 🔴 **與 `B-13` 應合併** |
| **B-19** `GOV-BRIEF-PRECHECK-EXPAND` | brief 是最高槓桿產物卻檢查最少，**本 session 燒 3 輪**：`B0R` 前綴違反 `CANONICAL_ID_RE`／漏寫授權 reconcile 使 codex 撞上無法戳記的 R6 檔／SPEC 對抗審誤標 `review` 使角色閘排除 grok | `doc_format_precheck.sh` 對 brief 增驗三項：kind 與標的型態相符／授權 reconcile 已給且 `stamps_check` rc=0／ID 樣板符合 `CANONICAL_ID_RE`。**併原票 `GOV-BRIEF-IDPATTERN-UNVALIDATED`** | ⬜ |
| **B-20** `GOV-TICKET-CLOSURE-REQUIRES-GATE` | 「有沒有建閘」**完全靠主委自覺**——遞迴少一層。使用者原話：「靠你想到才做就是一直漏」 | 票要結案**必須**二擇一：①指向實際存在的檢查（可 `grep` 驗證掛在 `gov_check`／hook）②具名說明為何無法機械強制。**形狀與既有「具名不併」相同** | ⬜ |
| **B-21** `GOV-ARTIFACT-CHECKER-REGISTRY` | 無「artifact → 驗證檢查器」對照 | 凡被 `scripts/*` 當資料源讀取的檔須在註冊表有一列，缺列 fail-closed。**與 `B-20` 互補**（B-20 管結案、B-21 管覆蓋面） | ⬜ |
| **B-22** `GOV-DISPATCH-WATCHER` | 派工無監看（見 `B-14` 的 2h20m 事故） | Haiku 級每 2 分鐘查進程樹＋產出檔。🔴 **不走委員通道**（不產 findings、不開債）。🔴 **明文不做：不派 agent 做「驗證」判斷**——LLM 驗「有沒有漏」自己就是會漏的那種東西 | ⬜ **唯一新增元件**。🔴 **與 `GOV-UNTRACKED-PRODUCT-GUARD`② 重疊待裁** |
| **B-23** `GOV-MARKUP-WHITELIST` | 現行是**列舉禁止形式**（無界）。P16 §A #12 已登記 **20 種** punctuation 逃脫變體，且自陳「**散文形式空間無界，必然還有未列舉的寫法**」⇒ **打地鼠已被自己的文件證明打不完** | fail-closed 反轉：枚舉**允許**的有限集合，其餘拒收。**須先全量掃描定初始集合並附誤擋率 receipt，不得憑想像** | ⬜ 🔴 **與 `GOV-FULLWIDTH-VAR-SCAN` 重疊待裁** |
| **B-24** `GOV-ACCEPTANCE-STATE-NOT-RC` | 驗收寫成「**補救動作的 rc**」而非「**補救之後的狀態**」。三次：「已開票」沒看檔案／「已完整併回」只看 grep 命中數／「golden 已還原」只看 `restore` 的 rc=0 | 凡「跑某腳本」的驗收欄**必須**同時要求狀態斷言。**橫向紀律，併入各票驗收欄，不另建檢查器** | ⬜ |
| **B-25** `GOV-FACT-KEY-SINGLE-SOURCE` | **同一事實在多份散文有副本**，改一處其餘不動（同日五次：授權來源／三值枚舉／`T1-I1`／D-001 狀態／驗收列數） | fact-key 註冊表：每 key 宣告唯一來源，他處**只能是指標不得是副本**；不一致或新副本 ⇒ rc=1。初始集合由**已發生的漂移導出** | ⬜ 🔴 **與 `GOV-XREF-SYNC`（2026-07-20 三家裁決）重疊待裁** |
| **B-26** `GOV-IDSPACE-ALLOC-GATE` | ID 空間**跨檔配置無登記無檢查**——同日 **8 次**撞號，含 `票 B-11`／`B-12` 被跨檔重複配置 | 新增 ID 前驗：①樣式已在 `docs/GOVERNANCE_ID_NAMESPACES.md` §1 登記 ②不與既有值重複（含粗體變體）③配置紀錄寫在該空間的**唯一擁有文件**內。⚠️ 初版名 `GOV-ID-NAMESPACE-REGISTRY` 與既有 `GOV-ID-NAMESPACE-CHECK` 近似已改名 | ⬜ 登記表本體已建 |
| **B-27** `GOV-DOC-TAXONOMY` | **專案無任何文件分類規定**：票散在**四處**（本檔／`GOV_DISPATCH_FLOW_FIX_TODO §N`／`ROADMAP`／各 handoffs）；13 種 ID 樣式零登記；**新文件放哪沒規則**（主委 2026-08-04 建 `GOVERNANCE_ID_NAMESPACES.md` 放 `docs/` 純屬自行決定）；handoffs 檔名無慣例。<br>🔴 **這是同日多起事故的直接根因**：`票 B-11`／`B-12` 跨檔重複配置（因為票可開在 ROADMAP 也可開在本檔）／事實多副本改一漏多（因為沒規定哪份是來源）／主委重新發明 `GOV-XREF-SYNC`（因為它在 ROADMAP 而主委只看本檔）。<br>**委員產出亦然**：散在三種目錄，檢查器認不得其中一種 ⇒ **69 份收斂檔 0 份進版控** | 訂文件分類規定：**哪類文件放哪目錄／檔名慣例／票只能開在哪一份／哪份是某事實的唯一來源**，並用機器檢查。<br>🔴 **兩段交付**：①規則本體（便宜）②機械強制（**中任務，須完整管線**） | ⬜ 🔴 **2026-08-04 已機械確認無既有票涵蓋**——換 `文件分類／檔案分類／目錄規範／文件放哪／檔名慣例／文件型別／票只能開在` 七組語意詞掃全 `docs/`＋`handoffs/`，**零命中**。**本 backlog 唯一一張完全無前人碰過的票** |
| **B-28** `GOV-V2-STAGE1-TOOLING` | **凍結程序 v2.0 §6 白名單逐支列出的檢查器、§4 依賴的 registry，三者皆不存在**：`scripts/section_sig_check.sh`／`scripts/dext_touchset_check.sh`／`scripts/stamp_legacy_registry.json`（主委實跑 `test -e` 三項皆 rc=1）。<br>⚠️ **與 `票 B-27`／講法統一是兩件事**：講法統一只是把 §3／§5 的 operative 語氣改成「待實作」（**便宜**）；**本票是真的把三者做出來**（**貴**）。<br>🔴 **主委 2026-08-04 的登記缺陷**：白話總覽第 50 項只登記了「講法不一致」這條**便宜路徑**，**把「真的做出來」漏掉**——等於「把一件事的兩條處理路徑中的一條當成整件事登記」，與同日「把 D-001 的一半當成全部併回」同族 | 實作三者並掛上 v2.0 §3／§4／§5 所述掛點；完成後 §7 遷移階段 1 才算 DoD 達成 | ⬜ **大任務，須完整管線**。🔴 **硬前置＝`票 B-9` `GOV-DOCS-STAMP-PROVENANCE`**（v2.0 §6.3 明列）。⚠️ 本票在此之前**只存在於主委 session 內的工作清單**，**跨 session 即消失** |

## 🔴 索引的誠實邊界

1. **`票 B-1`～`B-5` 的 ❓** ：立票前提（v1.0「不新增檢查器」）**可能已被 v2.0 §6 推翻**，
   **主委未讀 v2.0 §6 確認**。不得逕行結案或實作。
2. **`票 B-7` 標 ✅ 是推論**：D-001 已 `SUPERSEDED-BY-R` 且條文併回 P16 v3.0，
   但**未回頭確認該票的原始驗收條件是否全數滿足**。
3. 第三群（`B-13`～`B-26`）的「發生什麼」全部出自 2026-08-04 本 session 實測，
   **第一、二群的事故敘述則轉引自原票**，主委未重跑複驗。

> **本檔的存在理由**〔R5 群集 γ，採 composer 修法②〕：
> v0.5 §9 的 oracle 表有多列「命令」欄指向 `scripts/spec_binding_check.sh` 與
> `scripts/manifest_parse.py`——**兩支腳本都不存在**。
> 依程序正文 §9 末句「列不出四欄的機制，一律不寫進本程序」，那些列是不可執行空殼，
> 與 v0.4 被否決的「四欄可執行版」同一個病，只是從缺欄變成缺腳本。
>
> ⇒ **正文只保留已可跑的 oracle；依賴未存在腳本的機制移入本檔。**
> **腳本合併並通過三態驗證後，該列才可加回正文。**

## B-1 `scripts/spec_binding_check.sh`（不存在）

實作 §3.3-A 的 A0–A11 與 §3.3-B 的支路定序。

**已知的實作陷阱（committee 實跑，不得遺漏）**：
- A0 與 A1 **不是獨立 oracle**〔`CODEX-R5-P1-03` 實跑〕：unset 環境變數後 `git ls-tree HEAD`
  仍為 `120000`，必須同時移除 A0 與 A1 才轉紅。
  ⇒ 實作時 A1 須改用**不受 env 影響**的取樣（`git ls-tree`），A0 才有獨立可測的效果；
  或明白承認兩者是同一道防線的兩半，合併成一列 oracle。
- `patch_path` 的「未 commit」分支缺 tracked-path 檢查〔`CODEX-R5-P1-03` 實跑〕：
  未追蹤的 `valid.patch` 其 `git ls-files --error-unmatch` rc=128，
  但 `git apply --check` rc=0 ⇒ 只驗後者的 mutant 不成立。

## B-2 `scripts/manifest_parse.py`（不存在）

實作 §4.2 的 manifest 解析與三項判定：`supersedes` 子集、extension 衝突、`state` 值域。

**約束**：單一實作，禁止各檢查器自行以 awk 或 sed 解析 yaml
〔`COMPOSER-R4-P2-01`：不同 tokenizer 對巢狀結構與引號會得出不同子集結果〕。

## B-3 `rejections.yaml` 的專用 validator（不存在）

v0.5 誤把 §7 `rejections.yaml` 的四欄完整性驗證指給 `manifest_parse.py`
〔`GROK-R5-P2-01`、`COMPOSER-R5-P1-02`：機制域名不符，實作者會把拒絕登錄檢核塞進 manifest 解析器或漏做〕。
應為獨立 validator 或 `reconcile_stamps_check` 的子命令。

## B-4 `reconcile_stamps_check.sh` 的戳記區白名單

實作 §4.4。**遷移影響已實測**，見程序正文 §4.4。

## B-5 `gate.sh` 的落地缺口

`CODEX-R5-P0-01` 實跑指出，現碼與程序正文 §3.4／§7b 的目標態有兩處差距：
- `gate.sh:488-528`：`""|waived:*|stamped-waived:*) : ;;` 直接跳過
- `reconcile_stamps_check` 呼叫只在 `if [ -n "${spec}" ]` 分支內

**這兩處在正文以「待實作」標示**，不得寫成現在式。

## B-6 票 `GOV-TOKEN-WORKTREE-BIND`

token 綁 worktree（既有 `GATE-TOKEN-BINDING` 債的延伸）。不在本程序範圍。

## B-7 票 `GOV-STAMP-TASKID-INJECT`

`cx_run.sh` 已注入 `ROUND_ID`，應同樣注入 `TASK_ID`，brief 改為「用注入值」。
**根因**：要求委員手抄 task-id，抄錯是必然而非偶然——R4 有兩家抄了 brief 的格式範例字串，
provenance 機檢擋下，多花兩輪補正。

## B-8 票 `GOV-REJECTED-LIST-ACK`

`handoffs/gov_rejected_mechanisms.tsv` 的 append 須至少一家非主委 ACK 或寫入 audit。
現行緩解僅為「`--rejected` 覆寫限測試 harness」與「每次執行印出清單 sha256」。

---

# 2026-08-02 新增：D 延伸檔實戰暴露的兩條制度缺陷

> 出處＝票 `GOV-STAMP-TASKID-INJECT` 的實作過程，**皆為 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` v1.0
> 首次實戰才現形的問題：該程序創造了「D 延伸檔」這個新文件型別，但既有機器閘不認識它。**
> 兩條都由機器閘 fail-closed 擋下（未造成錯誤放行），代價是各燒一輪派工。

## B-9 票 `GOV-DOCS-STAMP-PROVENANCE`

**`docs/` 內的 D 延伸檔無法取得可過機檢的戳記。**

1. `reconcile_stamps_check.sh:67` 對每枚戳記跑 `verify_task_provenance.py check-stamp`
2. provenance 需要一筆 `output_path` 指向該檔且 `output_sha256` 非 `pending` 的事件
3. 產生該事件的唯一入口 `gate.sh register-output` 在 `:166-169` **明文只收 `handoffs/` 內檔案**
4. ⇒ 程序 §3.2「機檢 `reconcile_stamps_check.sh <延伸檔>` rc=0」**不可執行**

且 §3.2 與 §3.1（來源放 `handoffs/reconcile/<session>/`）、§2（`## 戳記` 放延伸檔內）**互相矛盾**。
唯一可執行的讀法＝戳記放收斂檔，**該程序 v1.0 自身即以此方式定案**。

**事故**：2026-08-02 TODO 戳記輪，codex 依 `AGENTS.md` 第 12 條 STAMP-BLOCKED
對 `docs/…D-001.md` 直接跑機檢得 rc=1 而正確停工。**燒掉一輪派工。**
**修法須走程序 §5 的 R**（完整三家審＋使用者裁定）。

## B-10 票 `GOV-DEXT-TEMPLATE-KIND`

**`template_check.sh` 沒有 D 延伸檔的 kind。**

`gate.sh:588` 對 `--todo` 跑 `template_check.sh todo`，對 `--spec` 跑 `template_check.sh spec`；
後者要求完整 SPEC 錨點（`§RISK`／`§C`／`§P`／`§R`／`§N`＋至少一個 Task）。
但 D 延伸檔用的是 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` §2 的模板（`BASE`／`PREDECESSOR`／
`觸及面宣告`／`內容`／`戳記`），結構完全不同 ⇒ **`gate.sh dispatch --spec <D延伸檔>` 永遠拒發 token。**

**事故**：2026-08-02 實作派工，`--spec docs/P16_COMMITTEE_DEBT_SPEC.D-001.md` →
`TEMPLATE FAIL (spec)` → gate 拒發 → 不開債不派工（fail-closed 正確）。**燒掉一輪派工。**

**現行繞法（本票未解前照此做）**：`--spec` 傳**底本** SPEC（`docs/P16_COMMITTEE_DEBT_SPEC.md`，
機檢 rc=0），延伸檔在 brief 內具名為實際權威。
**修法選項**：①`template_check.sh` 新增 `dext` kind ②`gate.sh` 對符合 `*.D-NNN.md` 命名者改用該 kind。
兩者皆會動 `gate.sh`／`template_check.sh`，屬機檢腳本變更，**須先盤攻擊面**（見記憶
`feedback_gate_script_full_attack_surface`）。

## B-13 票 `GOV-MERGE-COMPLETENESS-CHECKER`

**文件搬遷沒有機械完整性檢查；「已完整併回」是散文宣稱。**

`completeness_check.sh` 已解過同構問題（委員 findings → 收斂檔，逐 ID 驗，漏一個 rc=1），
但**只量委員產出，不量文件搬遷**。⇒ D 延伸併回本體、SPEC 重構、章節搬移一律靠人眼＋散文宣稱。

**事故（2026-08-04，同一件事連犯兩次）**：P16 走 R 重開，須把 D-001（238 行，§D1–§D7）併回本體。
- **首版**：只併 §D2／§D3 前半，漏 §D3 執行契約整塊／§D5 驗證表／§D6 誠實邊界
  ⇒ **三家獨立同時判 P0**（`CODEX-R8-P0-01`／`COMPOSER-R8-P0-01`／`GROK-R8-P0-01`）
- **R8 補併**：又漏 §D4／§D7／V13–V15，並**發明撞號的 V13** 與 **M24–M27**（§V 早有 M1–M34）
  ⇒ **R9 再判 2 個 P0**（`GROK-R9-P0-01`／`CODEX-R9-P0-02`）

🔴 **根因不是粗心，是量測工具寫錯**：主委用 `grep -cE '^\| *V[0-9]'` 數 D-001 驗證表得 **12**，
據以宣稱「V1–V12 逐列併回」。實際 **15 列**——該 regex **匹配不到 `| **V13** |` 這種粗體列**。
⚠️ **寫錯的機械檢查比沒有檢查更危險**：它給出一個具體數字，宣稱因此更理直氣壯。
漏掉的 **V14 恰是「禁止兩次 grep 交集」那條契約的唯一 oracle** ⇒ 只搬禁令、留下無法證偽的約束。

**修法**：
```
merge_completeness_check.sh <來源檔> <目標檔> <落點表>
  來源原子單位（heading／編號項／表格列，含粗體變體）∖ 落點表已宣告項 != ∅  ⇒ rc=1
  落點表項目 ∖ 來源實際單位 != ∅                                        ⇒ rc=1（防捏造）
  目標檔 ID 空間撞號（同一表內重複 ID）                                  ⇒ rc=1
  每項須標 merged-at:<錨點> 或 dropped:<理由>
```
**強制點**：掛寫檔當下（與 `doc_format_precheck.sh` 同一 hook）——**送審前就擋**，
本次 R8／R9 兩輪三家對抗審**本來就不必發生**。

**已落地的替代品（本票未解前照此做）**：P16 v3.0 檔頭已建**逐節落點表**（§D1–§D7 每節須有落點
或具名不併理由），並寫死「完整性宣稱一律以本表為準，**不得以 grep 命中數代替**」。
⇒ 人工版有效但**不具強制性**，仍靠紀律——本票即為把它機械化。

**風險**：動 `doc_format_precheck.sh` 屬機檢腳本變更，**須先盤攻擊面**。
「原子單位」的抽取對散文段落不可靠（表格列／編號項可靠），**須具名宣告涵蓋範圍**，
不得宣稱能檢查任意文件搬遷。

## B-14 票 `GOV-CURSORAGENT-POSTWRITE-HANG`

**`cursor-agent`（composer）寫完產出後不退出，整輪掛住。**

**事故（2026-08-03，實測）**：TODO R2 審查輪，三家產出檔寫入時間為
grok 17:29／composer 17:31／codex 17:44——**審查 18 分鐘內全部完成**；
但 `committee_run.sh` 到 19:50 仍未返回，**空等 2 小時 20 分**。

**根因**：composer 的 sandbox shell 卡在 `snap=$(command cat <&3)`——**從 fd 3 讀取永久阻塞**，
`ps` 顯示 CPU time `0:00.00`（完全沒在跑）。殺掉該 shell 後 `cursor-agent` 仍不退出
（無子進程、狀態 S、CPU 0:18），再 TERM 掉它，`committee_run` 立刻補齊完成記錄並正常收尾。

**修法選項**：①`cx_run.sh` 加 per-family timeout，逾時且**產出檔已完整**（通過 `completeness_check --single`）
則視為成功並終止進程 ②逾時但產出不完整 ⇒ 記 `failed`／`format-failed`（依三值契約）走重派。
🔴 **不得只加 timeout 就殺**——會把已完成的審查誤判為失敗，製造無謂重派。

**繞法（本票未解前）**：派工後**每 10 分鐘輪詢進程樹＋產出檔**，
不要只等 harness 通知（`committee_run` 是緩衝輸出，中途看不到進度）。

## B-15 票 `GOV-GATECHECK-READONLY-PGREP-FP`

**`gate_check.sh` 把唯讀查詢誤判為派工。**

**事故（2026-08-03～04，本 session 三次）**：主委用唯讀指令診斷背景進程／讀委員產出時被擋：
- `pgrep -fl 'codex exec|cursor-agent|grok '` → `[GATE BLOCKED] 偵測到 kind=dispatch 高風險動作`
- `for f in codex composer grok; do ... done` 讀產出檔 → 同上
- `completeness_check.sh --lock <reconcile 路徑>` → 同上

**根因**：判定僅比對指令字串是否含家族名／派工關鍵字，**不區分讀寫**。

**修法選項**：①白名單純讀取動詞（`pgrep`／`ps`／`grep`／`sed -n`／`ls`／`cat`）在無寫入重導向時放行
②改以「是否呼叫 `cx_run.sh`／`committee_run.sh`／`gate.sh dispatch`」為判準，而非家族名出現。
🔴 **屬機檢腳本變更，須先盤攻擊面**——放寬判定有讓真派工漏網的風險，
**必須附 mutation**：真派工指令在新判準下**仍須被擋**。

**繞法（本票未解前）**：拆成不含家族名的多條簡單指令。

---

# 🔴 2026-08-04 全 repo 票務對帳（本檔升為**唯一票登記處**）

**起因**：使用者要求「先把 backlog 整理清楚，別掉項」。
**方法**：機械掃 `docs/*.md` ＋ `handoffs/*.md` 的 `GOV-[A-Z-]+`，濾掉 task-id／brief 名後
得 **38 個票候選**，與本檔已有的 19 個做差集 ⇒ **24 個缺口**。逐一查出處與狀態後歸類如下。

🔴 **對帳當場抓到 `票 B-11`／`票 B-12` 被配置兩次**：
2026-08-02 三家裁定已把 `B-11`＝`GOV-FAILCLOSED-DEP-GUARD`、`B-12`＝`GOV-TESTHARNESS-SCRIPTLIST-SSOT`
**記在 `docs/ROADMAP.md` 而非本檔**；主委 2026-08-04 只看本檔（當時最大號 B-10）就從 B-11 起編
⇒ **覆蓋掉兩張既有票**。**處置**：主委今日開立的 13 張整體平移為 `B-13`～`B-25`，
`B-11`／`B-12` 歸還原主（見下）。
⇒ **這是同日第 8 次 ID 撞號**，且是**跨檔案配置**造成——正是 `票 B-21` 與
`docs/GOVERNANCE_ID_NAMESPACES.md` 要解的東西。

## B-11 票 `GOV-FAILCLOSED-DEP-GUARD`（2026-08-02 三家裁定，**原記於 ROADMAP:66**）

病根一句話（composer）＝「**治理檢查器把『依賴缺席』當成『檢查不適用』而非『檢查失敗』**」。
⚠️ 主委原案（靜態探針當硬 gate ＋ `# OPTIONAL-DEP:` 註記豁免）**已被實跑否決**
——誤判率 100% 且會漏抓真陽性；單純註記三家一致判為橡皮圖章。
**採委員改寫版**：靜態探針**降級為可解釋 tripwire 警告**／**隔離 runtime mutation 當硬 gate**。
**不阻塞 T1。** 全文見 `docs/ROADMAP.md`。

## B-12 票 `GOV-TESTHARNESS-SCRIPTLIST-SSOT`（2026-08-02 三家裁定，**原記於 ROADMAP**）

測試 harness 的腳本複製清單無單一來源。全文見 `docs/ROADMAP.md`。

## 🔴 票務對帳表（24 個缺口的歸類）

### (a) 已完成，**不再列為待辦**（4）

| 票 | 狀態 |
|---|---|
| `GOV-DOC-CHECK-AT-WRITE` | ✅ commit `901a8d9`（格式檢查移到產出端） |
| `GOV-FORMAT-SSOT` | ✅ commit `8193582`（委員產出交件當下檢查）；第二段 `result_state` 收窄已由**批次 B2** 完成（P16 v3.0 三值，commit `c0a7004`） |
| `GOV-COMPLETENESS-IDLIKE-FP` | ✅ **批次 B1** commit `d36d76b`（`extract_heading_ids` 四步程序） |
| `GOV-ROLEGATE-PREDISPATCH` | ✅ **批次 B3** 實作完成（675 passed），**閉合複核待跑** |

### (b) 只在 `GOV_DISPATCH_FLOW_FIX_TODO.md §N`，**從未進本檔**（6）

`GOV-CLAIMCHECK-VS-VERBATIM`／`GOV-COMPLETENESS-FAMILYPREFIX-FP`／
`GOV-GATECHECK-DEBTCLEAR-DEADLOCK`／`GOV-MANIFEST-INFLATION-RESIDUAL`／
`GOV-RECONCILE-LOCK-IMMUTABLE-DEADLOCK`／`GOV-SPEC-REV6-STALE-COUNTS`

🔴 **成因**：`TODO §N` 是**第二個票登記處**，兩處從未對帳。
**處置**：語意與現況以 §N 原文為準（不重抄，避免多副本＝`票 B-25` 要治的病）；
本表僅登記其存在與所在。**`TODO §N` 自即日起降為指標，新票一律開在本檔。**

### (c) 只在 `ROADMAP` 或 `handoffs`，**從未進本檔**（12）

| 票 | 所在 |
|---|---|
| `GOV-ID-NAMESPACE-CHECK` | ROADMAP——⚠️ **語意＝委員產出 `## ` 標題的家族前綴須等於產出家族**，**不是** ID 空間登記；與主委 2026-08-04 自創的名稱高度近似但意義不同 |
| `GOV-XREF-SYNC` | ROADMAP——**跨文件交叉引用同步機械化**（2026-07-20 三家裁決分案；理由＝A/B 靠人審、C 靠 grep，混寫會讓 agent 用價值題敷衍 xref）。**OPEN** |
| `GOV-VERIFY-RECEIPT-RUNNER` | ROADMAP——驗收 receipt 執行器（A′′），立票理由含**使用者論證原文**。**OPEN** |
| `GOV-NOFINDINGS-SENTINEL` | ROADMAP——🔴 **現行 `completeness` 仍接受「空殼」P3-00**（codex 四行 probe 實證 `DIRECT_RC=0`）。**OPEN** |
| `GOV-NO-FINDINGS-RECEIPT` | handoffs——「無 findings」收斂契約正式化；原提案「或併入 `GOV-FORMAT-SSOT` 子項」。**OPEN** |
| `GOV-FAILOPEN-GUARD` | handoffs——格式檢查**依賴缺席時 fail-open**（deps 失敗即 skip 掃描且不報）。修法＝skip 時須印「格式檢查未執行（依賴缺）」或反轉為 `_require_file`。**OPEN** |
| `GOV-FAILOPEN-GUARD-PROBE` | handoffs——上者的**探針實作**分票（T1 已三輪＋563 tests，不再合併以免拖長已收斂 diff）。**OPEN** |
| `GOV-FIXTURE-PARALLEL` | handoffs——並行 fixture 競態；**已 ACCEPT 為已知限制**，登記「驗收一律序列跑」 |
| `GOV-FULLWIDTH-VAR-SCAN` | ROADMAP／handoffs——全形變數坑的定義驅動掃描；兩家皆主張不塞進批次 B4；主委已修 3 處但**不宣稱該類坑已清除**。**OPEN** |
| `GOV-PREFLIGHT-SNAPSHOT-LOCATION` | handoffs——preflight 快照位置（由「拿未戳記收斂檔派工被 gate 擋下」連帶立票）。**OPEN** |
| `GOV-UNTRACKED-PRODUCT-GUARD` | handoffs——①並行就地探針**踩踏 untracked 產品檔**（主委備份屬運氣非制度）②呆滯門檻**按任務類型**、判定前先查是否仍在寫檔。**OPEN** |
| `GOV-TESTHARNESS-SCRIPTLIST-SSOT` | 已升為 `票 B-12`（見上） |

### 🔴 逐張讀完後的結論：**主委 2026-08-04 新開的票中，3 張與既有票重疊**

| 新票（今日） | 既有票（更早） | 重疊點 |
|---|---|---|
| `票 B-25 GOV-FACT-KEY-SINGLE-SOURCE` | `GOV-XREF-SYNC`（2026-07-20 **三家裁決**） | 同治「跨文件事實不同步」 |
| `票 B-23 GOV-MARKUP-WHITELIST` | `GOV-FULLWIDTH-VAR-SCAN` | 同治「標記／全形變體」 |
| `票 B-22 GOV-DISPATCH-WATCHER` | `GOV-UNTRACKED-PRODUCT-GUARD` ② | 同治「呆滯判定」 |

**另有兩對既有票本身即重複**（非本日造成，一併提出）：
`GOV-FAILOPEN-GUARD` ↔ `票 B-11 GOV-FAILCLOSED-DEP-GUARD`（同病根：依賴缺席當成檢查不適用）；
`GOV-NOFINDINGS-SENTINEL` ↔ `GOV-NO-FINDINGS-RECEIPT`（同一件事的兩個名字）。

⚠️ **主委開票時完全沒有讀既有票**——與「開 9 張新票未對照 `票 B-13`」「`票 B-11`／`B-12`
跨檔重複配置」是**同一動作的第 9、10 次：新增前不盤點既有空間**。
🔴 本節即 `票 B-26 GOV-IDSPACE-ALLOC-GATE` 第 ① 條的實證需求來源。

🔴 **待使用者裁決的併票**（主委**不自行合併**，因涉及既有三家裁決過的票）：
①`B-25` × `GOV-XREF-SYNC`　②`B-23` × `GOV-FULLWIDTH-VAR-SCAN`
③`B-22` × `GOV-UNTRACKED-PRODUCT-GUARD`②　④`GOV-FAILOPEN-GUARD` × `票 B-11`
⑤`GOV-NOFINDINGS-SENTINEL` × `GOV-NO-FINDINGS-RECEIPT`

### 🔴 本輪最該立即處理的一項（與本 session 直接相關）

`GOV-NOFINDINGS-SENTINEL`：**`completeness` 接受空殼 P3-00**（codex probe 實證 `DIRECT_RC=0`）。

本 session 主委在**每一份 brief** 都寫「零 finding 時須產恰一條 `P3-00` sentinel，不得空手」
——**該要求目前可被一個空殼 heading 形式滿足，機器不會擋**。
⇒ 本 session 所有「委員回報零 finding」的輪次，
**其 sentinel 是否有實質內容，從未被機器驗證過**。

### (d) 本 session 發生但**兩處皆無票**（3，須新開）

| 問題 | 新票號 |
|---|---|
| ID 空間跨檔配置無登記無檢查（同日 8 次撞號） | **`票 B-26`** 已涵蓋機械強制面；登記表本體＝`docs/GOVERNANCE_ID_NAMESPACES.md` |
| claim checker 擋本 epic 產物進版控 | 疑與 `GOV-UNTRACKED-PRODUCT-GUARD` 同源，**待併票確認**（見 (c)） |
| `mutation_probe_static.py` 對 **subprocess 型探針**誤判「未碰到待測系統」 | **待開**——本 session 以 `test_debt_gate.py` 既有配方繞過（helper module-level 常數 ＋ `monkeypatch`），**限制本身未記錄** |
| **專案無文件分類規定** | 🔴 **已開 `票 B-27` `GOV-DOC-TAXONOMY`**（2026-08-04 使用者追問後機械確認無既有票，七組語意詞零命中） |
| **v2.0 §6 白名單的三支元件不存在**（`section_sig_check.sh`／`dext_touchset_check.sh`／`stamp_legacy_registry.json`） | 🔴 **已開 `票 B-28` `GOV-V2-STAGE1-TOOLING`**。⚠️ 原僅在「講法不一致」項下被提及，**「真的做出來」這條路徑漏登**，使用者追問後補正 |

🔴 **本表的誠實邊界**：(c) 的 12 張**僅登記存在，未逐張讀內文**；
語意摘要只對已在對帳過程中讀到的四張（`GOV-ID-NAMESPACE-CHECK`／`GOV-FIXTURE-PARALLEL`／
`GOV-FULLWIDTH-VAR-SCAN`／`GOV-FAILCLOSED-DEP-GUARD`）成立。
**其餘八張的優先級與現況待逐張確認**——**不得據本表宣稱已完整盤點**。

---

# 🔴 2026-08-04 使用者裁定：治理根因整治批（B-13～B-25）

**使用者定死的三條方針**（本批所有票的驗收前提）：
1. **不得再以新增規則／記憶／紀律解決**——「這根本防不住」。
   實證：主委把「工具必須自帶強制機制、不准靠紀律和記憶」寫進自己的文件，**同一份文件內違反四次**。
2. **一律往機器可驗／機械閘／自動化的方向解根因。**
3. 🔴 **不得再在散文／文字／字體層面撞牆**——解法要**避開該模式**，改用第 2 點。

**排序原則**：先阻止新病灶出生（B-14／B-21），再清存量（B-15），再補流程缺口（B-16～B-19），
最後是不影響正確性的工具坑（B-20）。**B-22 為橫向紀律，併入各票驗收欄。**

## 🔴 與 `票 B-13`（原編 B-11）的關係（**本節為事後補建，成因見下**）

〔**使用者 2026-08-04 當場抓到**：「但這些 backlog 中要做的其中一項，
不就是要擋搬文檔時會漏東西嗎？」——**指控成立**。〕

> 🔴 **本節票號已於 2026-08-04 全面更新**〔`CODEX-R11-P0-01` [BLOCKING]：
> 主委改號時**只改 `## B-N` 標題、內文引用一個都沒改**，導致「同一票號指向兩個不同的票」
> ——**正是改號要修的病本身**。這是「改一項漏多項」在改號動作上的復發。〕

**`票 B-13` `GOV-MERGE-COMPLETENESS-CHECKER`（同日稍早開立）就是擋文件搬遷漏項的票**，
而 **`票 B-16`／`B-17`／`B-18` 三張都壓在它的地盤上**，主委開票時**完全沒有對照**
——`grep` 實證：該區塊對既有票的引用只有一處，**對 `GOV-MERGE-COMPLETENESS-CHECKER` 零命中**。

⚠️ **「新增前不盤點既有空間」同日發作清單**：
| # | 事件 |
|---|---|
| 1 | `M24–M27` 撞既有 `M24/M25/M26/M27`（§V 早有 M1–M34） |
| 2 | 自造 `V13` 撞 D-001 真實 `V13` |
| 3 | 只改 `P16_D001_IMPL_TODO` 檔頭、漏改正文三處 |
| 4 | 開 9 張新票未對照 1 小時前自己開的 `GOV-MERGE-COMPLETENESS-CHECKER` |
| 5 | 票 `B-` 與批次 `B` 撞名 |
| 6 | `GOVERNANCE_ID_NAMESPACES.md` 自身宣稱 `F<n>` 未使用（實際 `F1` 688 次） |
| 7 | `票 B-11`／`B-12` 被跨檔重複配置（ROADMAP vs backlog） |
| 8 | **本節**——改號時只改標題不改內文引用〔`CODEX-R11-P0-01`〕 |

🔴 **這正是 `票 B-21`（契約→檢查器註冊表）與 `票 B-20`（票結案須指向具名檢查）要解的東西
——而它在這兩張票被寫下來的當下就再犯，改號時又再犯一次。** 具名記錄，不美化。

### 四票的正確分工（收斂後）

| 票 | 管什麼 | 與 `票 B-13` 的關係 |
|---|---|---|
| **`票 B-16`** 散文契約偵測器 | **阻止**機器依賴的契約長進散文 | **上游**——契約不是散文，搬遷問題就縮小 |
| **`票 B-17`** 四表結構化 | **清掉**存量（V／M／PHASE_MAP／落點表） | **上游**——移走最難搬的部分 |
| **`票 B-13`** 搬遷完整性檢查 | 檢查 doc→doc 搬遷：來源原子單位 ∖ 已宣告落點 = ∅ | **本體**；`B-17` 後 scope 縮至**真正的散文段落** |
| **`票 B-18`** 收斂骨架預生成 | findings → 處置：每個 ID 一個空欄，空欄即擋 | **同一機制、不同輸入** |

🔴 **`票 B-13` 與 `票 B-18` 是同一個機制套在兩組輸入上**
（「列舉來源原子單位 → 每項要求具名落點 → 缺項 fail-closed」）
⇒ **實作時應合併為單一檢查器**，二者只是 `<source, target>` 參數不同。
**合併是刪除（一支檢查器而非兩支），符合刪除原則。**

### 排序修正

🔴 **2026-08-04 更新：`票 B-27` 插到最前面（地基層）**，理由見該票——
`B-21`（檔案→檢查器對照）、`B-25`（事實單一來源）、`B-26`（編號配置閘）
**三張都預設「知道東西該放哪」，而該前提現在不存在**。

```
地基   票 B-27（文件分類，先做規則本體）
       ↓
止血   票 B-16（散文契約偵測）→ 票 B-23（標記白名單）
       ↓
清存量 票 B-17（四表結構化）→ 票 B-13＋B-18 合併實作
       ↓
補漏洞 票 B-19 → 票 B-20 → 票 B-21 → 票 B-22
       ↓
另排   票 B-28（v2.0 階段 1 工具，硬前置＝票 B-9）
```

理由：`B-17` 先做會**縮小** `B-13` 的 scope，避免為已要遷走的表寫檢查器。
`B-28` **不排在主線**——它是大任務且硬前置未解，與上述五層無互相阻塞。

⚠️ **本批不得插進 B0–B4 批次**——實測：這些改動觸及 `gen_govflow_manifest.sh`（Phase 0）、
`reconcile_build.sh`、`doc_format_precheck.sh`，**不在 Phase 3／4 允許集合**，
G-MANIFEST scope gate 會直接判外洩。**該機制擋住主委插隊，即為它有效的證據。**

## B-16 票 `GOV-PROSE-CONTRACT-DETECTOR`

**機器實際依賴的契約長在散文裡，導致「用 regex 解析 markdown」成為必經之路。**

**事故（2026-08-04）**：主委用 `grep -cE '^\| *V[0-9]'` 數 D-001 §D5 驗證表得 **12**，
據以宣稱「V1–V12 逐列併回」。實際 **15 列**——該 regex **匹配不到 `| **V13** |` 這種粗體列**。
漏掉的 **V14 恰是「禁止兩次 grep 交集」predicate 契約的唯一 oracle** ⇒ 只搬禁令、留下無法證偽的約束。
**兩輪三家對抗審（R8 28 findings／R9 17 findings）本來就不必發生。**

**修法（判準可機械算）**：若某 ID 樣式（`V\d+`／`M\d+`／`T\d+-\w+` 等）
**同時出現在 `.md` 與 `scripts|tests`** ⇒ 該 ID 空間是**機器依賴的契約** ⇒
**必須**帶 generated-source 標記（指向資料檔），否則 rc=1。
⇒ **新的散文契約無法出生。**

**強制點**：`doc_format_precheck.sh`（寫檔當下）＋ `gov_check.sh`。
**風險**：動機檢腳本，**須先盤攻擊面**；ID 樣式清單須具名且可擴充，**不得無界**。

## B-17 票 `GOV-CONTRACT-TABLES-TO-DATA`

**四張機器依賴的表改為結構化資料 ＋ 生成視圖（本票是刪除，非新增）。**

現況全為手寫 markdown：`V1–V16` 驗收契約／`M1–M38` mutation 登記／
`PHASE_MAP`（path→phases）／逐節落點表。

**結構化後，2026-08-04 的整類失敗在物理上不可能發生**：

| 原本的錯 | 結構化之後 |
|---|---|
| 粗體讓 regex 漏列（V13–V15） | 讀 JSON key，**沒有格式可漏** |
| ID 撞號（M24–M27 與既有重複） | **重複 key** ⇒ 解析當場失敗 |
| 搬遷漏節（§D4／§D7） | 兩個 dict 的 **key 差集** |
| 一處改了另一處沒改（檔頭 vs 正文） | **只有一份**，視圖是生成的 |
| 表列數 vs collected 不一致 | `len(dict)` vs collect 數 |

🔴 **符合刪除原則**：刪掉手寫 markdown 表，留唯一資料源；markdown 降為生成視圖。
**先例**：`scripts/audit_events.json`／`governance_roles.json` 已是此形態，
**2026-08-04 全天在那兩處零事故**。

**驗收**：抽出的 key 集合與原表**逐項相等**（`comm` 可驗）；生成視圖與資料檔 round-trip 一致。

## B-18 票 `GOV-RECONCILE-SKELETON-PREFILL`

**收斂步驟是自由書寫，漏一項不會被擋。**

**事故**：2026-08-04 主委在收斂步驟的失敗——漏處置、捏造 ID、漏搬章節、ID 撞號——**全部集中於此**。
文獻（Multi-Review／CodeRabbit）在此步有 **aggregator LLM ＋ verification agent**，我們沒有。

**修法（比加 agent 便宜）**：`reconcile_build.sh` **已會抽出所有 finding ID** 做完整性檢查
⇒ 讓它順便產出**預填骨架**，每個 ID 一個空處置欄：
```
### <FAMILY>-Rn-Pn-NN
**處置**: <待填>
```
「不得有 `<待填>` 殘留」為機器可驗。⇒ **無法忘記一個已經存在的空格。**

🔴 **為何不能用刪除達成**：收斂本身不可省；被取代的是「主委手寫完整性宣稱」這個動作，
該動作**沒有刪除路徑**。

## B-19 票 `GOV-BRIEF-PRECHECK-EXPAND`

**brief 是最高槓桿產物，卻檢查最少。2026-08-04 因此燒掉 3 輪。**

| 事故 | 損失 |
|---|---|
| brief 指定 `B0R` 前綴，違反 `CANONICAL_ID_RE` | codex 產出被判不合規，整輪 abandon |
| brief 漏寫授權 reconcile ⇒ codex 撞上永久無法戳記的 R6 檔 | 整輪自我 BLOCKED |
| SPEC 對抗審誤標 `review`（應 `consult`）⇒ 角色閘正確排除 grok | 整輪失敗 |

**三次都是機制做對、主委指令下錯。**

**修法**：`doc_format_precheck.sh` 對 brief 增驗三項——
①`brief-kind` 與標的型態相符（SPEC/TODO 對抗審＝`consult`；實作 code review＝`review`）
②授權 reconcile 已給且該檔 `reconcile_stamps_check` rc=0
③brief 內指定的 finding ID 樣板符合 `CANONICAL_ID_RE`
**三項皆機器可驗。** 併原票 `GOV-BRIEF-IDPATTERN-UNVALIDATED`（TODO §N）。

## B-20 票 `GOV-TICKET-CLOSURE-REQUIRES-GATE`

**「有沒有建閘」目前完全靠主委自覺——這一層沒有閘（遞迴少一層）。**

**使用者原話**：「不然靠你想到才做就是一直漏，根本沒解決問題。」

現況綁定是**事故 → 規則**（`SCAR_LEDGER`），應為**事故 → 具名的強制檢查**。

**修法**：ledger／backlog 任一票要結案，**必須**二擇一：
①指向一個實際存在的檢查（可 `grep` 驗證它真的掛在 `gov_check` 或 hook 裡）
②帶一行**具名說明為何無法機械強制**
二者皆無 ⇒ **不得結案**。
🔴 **形狀與既有的「具名不併」相同**——該模式 2026-08-04 已實證有效。

**誠實邊界**：本票擋的是「已知形狀的契約缺閘」，**擋不住全新型態的失敗**
——後者仍由三家獨立審偵測（實證：D-001 漏搬三家同時命中，當時無任何閘會抓）。
**機械閘＝已知型態防再犯；冗餘獨立審＝新型態偵測。兩者不可互相取代。**

## B-21 票 `GOV-ARTIFACT-CHECKER-REGISTRY`

**凡被 `scripts/*` 當資料源讀取的檔，須在「artifact → 驗證檢查器」註冊表有一列；缺列 fail-closed。**

把「我們有沒有記得建閘」轉成「**註冊表完不完整**」——後者是集合差集，可機械驗。
**與 B-18 互補**：B-18 管票的結案，B-19 管覆蓋面稽核。

## B-22 票 `GOV-DISPATCH-WATCHER`（唯一新增元件）

**派工監看，不走委員通道。**

**事故**：`cursor-agent` 寫完產出後掛住，**空等 2 小時 20 分**（詳見 B-12）。

**修法**：便宜模型（Haiku 級）每 2 分鐘檢查進程樹＋產出檔，異常即通報。
🔴 **不走委員通道**（不產 findings、不開債）——否則依「一扇門」每批次會多好幾輪。
🔴 **明文不做**：**不派 agent 做「驗證」判斷**——一個 LLM 去驗「有沒有漏」，
**它自己就是會漏的那種東西**。2026-08-04 有效的檢查一次都不是「多看一遍」，全是集合運算。
Multi-Review 那類做法給的是 recall 提升（+118.83%），**不是保證**。

## B-23 票 `GOV-MARKUP-WHITELIST`

**標記／符號／字體用法改為白名單；白名單外一律拒收，要加須經討論。**

〔**使用者 2026-08-04 提出**〕**理由是實證的**：現行做法是**列舉禁止形式**（無界空間），
`docs/P16_COMMITTEE_DEBT_SPEC.md` §A 誠實邊界 #12 的「逃脫點追蹤」已登記
**20 種** punctuation 變體（全形冒號／全形驚嘆號／全形逗號／半形分隔 `|`／前綴否定／
整行判定被同行 token 掩護／斷言跨行……），且該節自陳
**「散文形式空間無界，必然還有未列舉的寫法」**。

⇒ **打地鼠已被自己的文件證明打不完。** 白名單是**同一個判準的 fail-closed 反轉**：
枚舉**允許**的有限集合，其餘一律拒。

**與 B-14／B-15 的分工**：B-14 阻止機器契約長進散文、B-15 清掉存量；
但 brief／收斂群集／SPEC 敘事**仍會是散文** ⇒ **B-21 覆蓋剩下的散文面**。

**修法**：定義允許的標記集合（強調符號、標點、清單／表格形式），
`doc_format_precheck.sh` 對治理文件檢查；白名單外的字元／形式 ⇒ rc=1。
**新增項須經委員會討論後入白名單**，不得由任一 agent 自行擴充。

**風險**：白名單過窄會誤擋正常書寫 ⇒ **須先以現有治理文件全量掃描定出初始集合**，
並附「誤擋率」receipt；**不得憑想像定集合**。

## B-24 票 `GOV-ACCEPTANCE-STATE-NOT-RC`（橫向紀律，併入各票驗收欄）

**驗收條件寫成「補救動作的 rc」而非「補救之後的狀態」。**

**2026-08-04 同一形態三次**：
| 宣稱 | 實際查的 | 該查的 |
|---|---|---|
| 「已開票」 | 無（只在對話裡宣告） | 檔案裡有沒有那張票 |
| 「D-001 已完整併回」 | grep 關鍵字命中數 | 每一節有沒有落點 |
| 「golden 已還原」 | `restore_golden_inventory.sh` rc=0 | `git status --short tests/golden/` |

🔴 **rc=0 只證明腳本跑過**，不保證此刻狀態正確（後續任何測試都可能再弄髒）。

**修法**：所有 brief／TODO 的驗收欄，凡「跑某腳本」者**必須**同時要求**狀態斷言**
（`git status` 輸出、集合差集為空、key 集合相等…）。
**併入 B-14～B-21 各票的驗收欄，不另建檢查器。**

## B-27 票 `GOV-DOC-TAXONOMY`

**專案無任何文件分類規定。**

**實況**：票散在**四處**（本檔／`GOV_DISPATCH_FLOW_FIX_TODO.md §N`／`ROADMAP.md`／各 handoffs）；
13 種 ID 樣式零登記；**新文件放哪沒規則**——主委 2026-08-04 建
`docs/GOVERNANCE_ID_NAMESPACES.md` 放 `docs/` **純屬自行決定**；handoffs 檔名無慣例。

🔴 **是同日多起事故的直接根因**：
- `票 B-11`／`B-12` 跨檔重複配置 ⇒ 因為票可開在 ROADMAP 也可開在本檔
- 事實多副本、改一處漏其他 ⇒ 因為沒規定哪份是來源
- 主委重新發明 `GOV-XREF-SYNC` ⇒ 因為它在 ROADMAP，而主委只看本檔
- **委員產出散在三種目錄，檢查器認不得其中一種 ⇒ 69 份收斂檔 0 份進版控**

**修法（兩段交付）**：①**規則本體**——哪類文件放哪目錄／檔名慣例／票只能開在哪一份／
哪份是某事實的唯一來源（**便宜**）②**機械強制**（**中任務，須完整管線**）。

🔴 **2026-08-04 已機械確認無既有票涵蓋**：換
`文件分類`／`檔案分類`／`目錄規範`／`文件放哪`／`檔名慣例`／`文件型別`／`票只能開在`
七組語意詞掃全 `docs/` ＋ `handoffs/`，**零命中**。
⇒ **本 backlog 唯一一張完全無前人碰過的票。**

## B-28 票 `GOV-V2-STAGE1-TOOLING`

**凍結程序 v2.0 §6 白名單逐支列出的檢查器、§4 依賴的 registry，三者皆不存在。**

主委實跑 `test -e` 三項皆 rc=1：
`scripts/section_sig_check.sh`／`scripts/dext_touchset_check.sh`／`scripts/stamp_legacy_registry.json`。

⚠️ **與「講法統一」是兩件事，不是一件事的兩種做法**：
- **講法統一**＝把 §3 `:151`／§5 `:338` 的 operative 語氣改成「待實作」（**便宜**，
  但依 v2.0 §10 **仍須走 R**）
- **本票**＝**真的把三者做出來**（**貴**）

🔴 **主委的登記缺陷**：白話總覽初版第 50 項**只登記了「講法不一致」這條便宜路徑**，
把「真的做出來」漏掉——等於**把一件事的兩條處理路徑中的一條當成整件事登記**，
與同日「把 D-001 的一半當成全部併回」同族。**使用者追問後才發現。**

**修法**：實作三者並掛上 v2.0 §3／§4／§5 所述掛點；完成後 §7 遷移階段 1 才算 DoD 達成。

**狀態**：⬜ **大任務，須完整管線**。
🔴 **硬前置＝`票 B-9` `GOV-DOCS-STAMP-PROVENANCE`**（v2.0 §6.3 明列）。
⚠️ 本票開立前**只存在於主委 session 內的工作清單**，**跨 session 即消失**。

## B-26 票 `GOV-IDSPACE-ALLOC-GATE`

**ID 空間跨檔配置無登記、無檢查——2026-08-04 單日撞號 8 次。**

⚠️ **命名說明**：主委今日初版取名 `GOV-ID-NAMESPACE-REGISTRY`，
**與既有 `GOV-ID-NAMESPACE-CHECK`（ROADMAP）語意近似但意義不同**
（後者＝委員產出標題的**家族前綴**須等於產出家族）⇒ **已改名為 `GOV-IDSPACE-ALLOC-GATE`**，
避免兩張近名票並存。**舊名不得再使用。**

**登記表本體已建**：`docs/GOVERNANCE_ID_NAMESPACES.md`（13 個 ID 空間、407+ 相異值）。
🔴 **該檔是登記表，不是檢查器；本票即為它的機械強制。**

**同日 8 次事故**（見該檔 §5）：`M24–M27` 撞號／自造 `V13` 撞真實 `V13`／
只改檔頭漏改正文／開票未對照 `票 B-13`／票 `B-` 與批次 `B` 撞名／
該檔自身宣稱 `F<n>` 未使用（實際 `F1` 688 次）／**`票 B-11`＋`B-12` 被跨檔重複配置**。

**修法**：
```
新增任何 ID 前，檢查器須驗：
  ① 該樣式已在 docs/GOVERNANCE_ID_NAMESPACES.md §1 登記      否則 rc=1
  ② 新號不與該空間既有值重複（含粗體變體的抽取）             否則 rc=1
  ③ 配置紀錄寫在該空間的「唯一擁有文件」內，不得散在他處     否則 rc=1
```
🔴 **③ 是 `票 B-11`／`B-12` 事故的直接對策**——那兩張配置在 `ROADMAP` 而非 backlog。

**風險**：動 `doc_format_precheck.sh`／`gov_check.sh`，**須先盤攻擊面**；
ID 樣式清單須具名有界，**不得無界**。**驗收依 `票 B-24`：須貼狀態斷言非動作 rc。**

## B-25 票 `GOV-FACT-KEY-SINGLE-SOURCE`

🔴 **「改一項漏多項」的直接解——本票為 2026-08-04 使用者追問時才發現的缺口，前 22 張票皆未涵蓋。**

〔使用者原話：「那改一項漏多項的解決方案是哪一個？」
主委盤點後確認：**B-15 只覆蓋四張表，散文中的事實副本無票可管。**〕

**病根**：**同一個事實在多份散文有多個副本**，改一處其餘不動，且無機制偵測。

**2026-08-04 同日五次實證**（皆非表格，故 B-15 管不到）：
| 事實 | 改了哪 | 漏了哪 |
|---|---|---|
| 「誰是授權來源」 | `P16_D001_IMPL_TODO` 檔頭 | 同檔 L66／L87／L172／L196／L201 |
| `result_state` 二值→三值 | `P16_COMMITTEE_DEBT_TODO` 正文 | 同檔**驗證欄** |
| Phase 1 節點含 `T1-I1` | TODO 測試表 | **B1 派工 prompt** |
| D-001 是否仍為活授權 | P16 本體 | `ROADMAP.md`（主委自己寫的行） |
| 驗收契約列數 | 補了 V13–V16 | 同段開頭仍寫「V1–V12」 |

**與既有票的關係（依 B-19 紀律，開票前盤點）**：
- **B-15**（四表結構化）＝**表格**類事實的單一來源 ⇒ 本票補的是**散文**類，二者互補不重疊
- **B-14**（散文契約偵測器）＝阻止**機器依賴的契約**進散文 ⇒ 本票管的是**人類讀的事實**，
  它們合法地留在散文裡，問題只在**有多份副本**
- **B-11**（搬遷完整性）＝單次 doc→doc 搬遷 ⇒ 本票管**長期存在的多份副本漂移**

**修法（機械可驗）**：建立 **fact-key 註冊表**，每個 key 宣告
①唯一來源檔＋錨點 ②允許出現的其他位置**只能是指標（pointer）不得是副本（literal restatement）**。
檢查器掃描全 `docs/`＋`handoffs/`，對每個 key：
```
若某處出現該 key 的字面陳述且與來源不一致  ⇒ rc=1
若某處出現字面陳述但未登記為 pointer      ⇒ rc=1（防新副本出生）
```

**風險**：fact-key 集合須**具名有界**，不得無限擴張；初始集合應由**已發生的漂移事故**導出
（上表五項即為初始集合），**不得憑想像列舉**。
🔴 **與 B-21（標記白名單）同紀律**：先全量掃描定初始集合並附誤擋率 receipt。
