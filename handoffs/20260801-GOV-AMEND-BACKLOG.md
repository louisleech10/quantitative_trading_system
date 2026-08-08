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

## 🔴 所有票的共同判準（2026-08-06 使用者定，逐字）

> 「我們現在要解的每一票，都是要讓你們 LLM Agent **如何在最低摩擦和成本下，
> 能精確且順暢的重複做同樣的事不出錯**，而你跟我的解釋或說明，
> 都是基於你跟委員精確的文件用白話解釋給我看，
> 所以第 0 批.md 內和 IC-Analysis.md 內的 `B1`,`B2`,`B1.1`,`B2-1`,`§4`,`§4-1`，
> **對我來說我是可以接受**，但**所有票都是在解你們 LLM Agent 運作上的問題**」

**這條推翻了主委在 2026-08-06 命名討論中使用的整條論證軸線。**
主委當時在論證「人能不能分辨 `第0批的B3` 與 `第2批的B3`」——**那不是判準**。
使用者讀得懂（有上下文＋主委翻譯）；票存在的理由是 **agent 做不到**。

**⇒ 每張票的取捨一律用這個公式衡量**：

```
淨摩擦 = 新增的每次成本 × 發生次數  −  省下的重工成本 × 避免的次數
價值   = 擋掉的 agent 失誤代價 ÷ 淨摩擦（淨摩擦為負時，價值為正且愈負愈高）
```

🔴 **「摩擦」算的是淨值，不是增量**（2026-08-06 使用者更正主委）：

> 「我沒說要摩擦增為 0 吧，且針對摩擦增量需為 0 就太絕對。
> **你多做一件機械檢查，是多做一件事，但後面可以省掉一直被退件重來
> 或省掉浪費好幾輪重複做，這是摩擦增加還是減少？**」

⚠️ **主委曾在 `docs/GOVB39_IDLIKE_HEADING_SPEC.md` 初版寫「摩擦增量須為 0」並掛使用者名下。
兩處皆錯**：使用者未說過；且該約束與「工具必須自帶強制機制，不准靠紀律和記憶」
直接衝突——若生效會擋掉本 epic 幾乎全部工作。已更正並具名保留於該 SPEC §C。

### 🔴 淨摩擦＝每張票與每個 Task 的**必填欄**（2026-08-06 使用者定）

> 「**將淨摩擦下降當治理 epic 的每項任務或是開票的指標**」

**⇒ 即刻適用於本 epic 的一切新增項**：

| 適用對象 | 必須寫出 |
|---|---|
| **每張新票** | 新增每次成本／發生次數／省下的重工／已避免次數 ⇒ **淨摩擦值** |
| **每個 SPEC Task** | 同上，寫在該 Task 的驗收欄旁 |
| **每個修法選項** | 若提多案，須逐案算淨摩擦後才比較 |

**判定**：
- 淨摩擦**為負**（下降）⇒ 可進執行序，愈負優先序愈高。
- 淨摩擦**為正或算不出來** ⇒ **不得進執行序**，退回重估或關閉。

🔴 **本欄同時取代「逐洞開票」的作法**（使用者 2026-08-06：「票永遠開不完，
除非你有一勞永逸的解決方式」）：
**優先找通則機制，而非為每種失誤各開一張票**；
新票若只治單一實例且無法推廣，須在淨摩擦欄說明**為何通則不可行**。

⚠️ **誠實邊界**：本欄目前為**文件約束**，尚無機檢。
機械強制**不另立票**——併入下一個動到 `template_check.sh` 的批次一起做
（正是為了不讓 backlog 因每條規則各長一張票而膨脹）。

**依此判準的直接後果（同日重排）**：

| 措施 | 治哪種失誤 | 摩擦 | 裁定 |
|---|---|---|---|
| 群集引用附摘句、比對附錄原文（延伸既有 `Oracle④`） | **歸錯群／讀錯**（本 session 9 次） | 小（同迴圈多一行比對） | ✅ 最高優先 |
| 新 ID 須帶 epic 前綴（**只約束新建**） | 找錯（`grep B3` 跨 epic 撈錯） | 小（不碰既有） | ✅ 做 |
| ~~全 repo 引用 lint（裸 `B<n>` 須帶限定詞）~~ | 看錯 | **1,414 檔／10,557 處** | ❌ **砍掉**——高摩擦低收益，且違反「既有釘死不動」 |

⚠️ **可讀性不是票的驗收標準**。若某項改動只讓人「看起來比較清楚」
而不減少 agent 的實際失誤，**不列入票的範圍**。

### 🔴 這條同時是「每張票怎麼修」的設計約束（2026-08-06 使用者補充）

> 「而且我說的那原則，是**每張票修正的原則和方向**，不然後果就是**又發散**」

**⇒ 不只用來選票，更用來約束修法本身。** 每張票的修法送審時須逐條答：

| # | 修法必答 | 不合格的樣子 |
|---|---|---|
| 1 | 擋掉哪一類 agent 失誤 | 「讓流程更完整」——沒有具名失誤 |
| 2 | **新增多少摩擦**（每次派工／每次寫檔多做什麼） | 「幾乎沒有」——沒量化 |
| 3 | **摩擦是否小於它擋掉的失誤成本** | 只講收益不講代價 |
| 4 | 是否 forward-only | 需要回頭改既有產物 ⇒ 收窄或退回 |
| 5 | 會不會**製造新的失誤面** | 見下方反例 |

🔴 **反例（同 epic 實證，2026-08-05～06）**：
`GOVB0-B3` 的第一次修補要關「超長指令未被檢查」（fail-open），
修法是**超過 8192 字元一律擋**（fail-closed）。
⇒ 漏洞補了，但**每一條超長的正常指令都被誤擋**——
本 epic 的存在理由就是「該放行的被擋」（`票 B-15`），修法卻製造同類問題。
第二次修補拿掉上限，又生出 **4MB 輸入卡死 30 秒**。

**連續兩輪「修補引入新缺口」⇒ 觸發斷路器。**
**這就是「發散」的實際長相：每修一次，範圍與摩擦都變大。**

⇒ 第 5 問（會不會製造新的失誤面）**不是形式問題**，是本 epic 已付過代價的教訓。

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
| `B-24`／`B-25`／`B-26` | KEEP／MERGE／KEEP | `B-24` **⬜ KEEP**｜`B-25` 🔴 **⬜ KEEP（2026-08-07 撤銷 MERGE）**｜`B-26` **⬜ KEEP** | 🔴 **08-06 裁「`B-25`→`GOV-XREF-SYNC` 舊票吸收新票」，08-07 撤銷**：機械查證該舊票**不在任何排期表**（白話總覽主表零命中、`ROADMAP` 僅存合併統計行）⇒ **合併＝從執行序消失**，且票數導出命令 `grep -c '^## B-'` **只數有編號者**，掉件不可見。`B-25` 改列**第 1 批 2a**。原「保留 2026-07-20 三家裁決脈絡」的理由仍成立，改以 `GOV-XREF-SYNC` 為 `B-25` 的**前身紀錄**而非承接者 |
| `B-27`／`B-28` | — | **⬜ KEEP（新開）** | 🔴 **triage 輪之後才開，未經三家裁決**。`B-27` 已機械確認無既有票涵蓋（七組語意詞零命中）；`B-28` 是主委登記缺陷的補正（漏登「把三支腳本做出來」這條路徑）。**下輪委員審時應一併裁決** |
| `B-29` | — | **⬜ KEEP（新開）** | 🔴 **triage 輪之後才開，未經三家裁決**。`GOV-BEHAVIOR-DELTA-DECLARE`——改判定類程式須先宣告預期差集、交件時機械對照。事故＝GOVFLOW `批次 B4` 8 輪中 3 輪源於此；專案端同病（21 支一次性 baseline／compare 腳本，每 epic 重造且非強制）。**使用者 2026-08-04 同意排入**。**下輪委員審時應一併裁決** |

### (c) 未編號票的裁決

| 票 | 裁決 | 依據 |
|---|---|---|
| `GOV-ID-NAMESPACE-CHECK` | **✅ DONE** | family-binding 已在 `completeness_check`／`cx_run` 交件路徑〔grok P2-02〕。🔴 **勿與 `票 B-26` 配置閘混淆** |
| `GOV-RECONCILE-LOCK-IMMUTABLE-DEADLOCK` | **✅ DONE** | 〔`CODEX-R11-P1-04`〕 |
| `GOV-XREF-SYNC` | 🔴 **🔗 MERGE→`票 B-25`（2026-08-07 反轉方向）** | 原裁「吸收 `B-25`」，但本票**無 `B-` 編號 ⇒ 不在任何排期表、不入票數計數** ⇒ 吸收即消失（08-07 實證咬人一次）。**改為由 `B-25` 承接**，本票降為前身紀錄（2026-07-20 三家裁決脈絡仍逐字保留於此）。⚠️ **通則**：無編號票不得作為 MERGE 的承接方 |
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
| **B-25** `GOV-FACT-KEY-SINGLE-SOURCE` | **同一事實在多份散文有副本**，改一處其餘不動（同日五次：授權來源／三值枚舉／`T1-I1`／D-001 狀態／驗收列數） | fact-key 註冊表：每 key 宣告唯一來源，他處**只能是指標不得是副本**；不一致或新副本 ⇒ rc=1。初始集合由**已發生的漂移導出** | ⬜ **第 1 批 2a**（`docs/GOVERNANCE_EXECUTION_ORDER.md`）。🔴 **2026-08-07 撤銷 08-06「MERGE→`GOV-XREF-SYNC`」裁定**：該舊票**不在任何排期表**（主表零命中、ROADMAP 僅存合併統計行）⇒ 併入即消失。🔴 **強制設計已改**：原「寫權威宣稱時加來源標記」被使用者推翻（①靠記憶 ②禁止詞列不完＝`B-23` 同病）⇒ 改為**資料檔＋生成＋pre-push diff**，手改或忘跑生成皆對不上而被擋 |
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

### 🔴 2026-08-07 併入兩項（`GOVB1-RECON-R1` G-9 ＋ `GOVB1-X-CONSULT-R2` R2-10）

**併入 A — 收斂工具的幽靈 ID（同一 session 內發作 2 次）**

`scripts/reconcile_cluster_attribution_check.sh:9`
`ids=$(grep -oE '[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}' "$SYNTH" | sort -u)`
—— **無行首錨點、不要求為 heading、不排除行內反引號**，掃描範圍含逐字附錄。
對照 `scripts/completeness_check.sh:116-140` 的嚴格 heading 路由（票 B-39 E2b 四層）
⇒ **兩支工具對「什麼算 finding ID」判準不一致**。

| 次 | 觸發源 | 幽靈 ID |
|---|---|---|
| 1 | 委員為 RECHECK **構造探針範例** | `GROK-R1-P3-00` |
| 2 | 委員在碼證中**引用上一輪的 ID**（**更常見的形態**） | `GROK-R1-P2-01` |

🔴 **危險性非誤報等級**：主委面對幽靈 ID 只有兩個選項——**為不存在的 finding 編處置**，
或留著警告。**與 `票 B-38` 同型的誘因結構：誠實則留紅、編造則乾淨。**

**修法**：以 `completeness_check.sh` 的 heading 路由為**單一來源**，
`reconcile_cluster_attribution_check.sh` 改為呼叫之，**禁自行重寫 regex**
（`scripts/cx_run.sh:29-38` 已記載同型教訓：「複製一份到 hook＝第二真相源，必然漂移」）。

**併入 B — `reconcile --mode` 與 `brief-kind` 枚舉不對齊（發作 2 次）**

`reconcile_build.sh --mode` 只收 `discovery|review`，但 `brief-kind` 有 `consult`；
且 `debt_clear` **只收 `review`**；`--rebuild` **只重建 lock 不重抄來源**。
⇒ 2026-08-07 連續 3 次 rc=1 才過。
**誠實邊界**：此項未解 ⇒ **第 1 批無法提供 `kind → … → debt_clear` 的端到端驗收**
（`CODEX-R2-P1-04`；已寫入 `docs/GOVB1_INPUT_QUALITY_SPEC.md` §N）。

---

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

### 🔴 2026-08-07 併入四項（GOVB1 第 1 批期間實際發作）

> **出生事故**：主委在收斂檔、`HANDOFF.md`、`白話說明/` 共 90 處寫「併入 `票 B-13`」，
> **本票內卻零命中**——寫在所有地方，就是沒寫在唯一該寫的地方。
> **這正是本票要治的病，發生在本票自己身上。**

| # | 病 | 發作 | 修法方向 |
|---|---|---|---|
| 13-a | `reconcile_cluster_attribution_check.sh` **只驗「ID 是否出現在某群集」，不驗「是否落在語意正確之群集」** | **2 次**（`x-consult-r10`／`x-stamp-r14` 兩處對帳配反，對帳機檢**未擋下**） | 比對群集主題與 finding 斷言主題；候選偵測原型＝`handoffs/20260807-govb1-attr-audit-probe.sh`（**判準過嚴會誤報，須複核**） |
| 13-b | 委員交件檔含**跨輪殘留 heading** ⇒ 收集工具依 heading 全收，主委只對本輪 ID 對帳 ⇒ **跨輪殘留必成掉項** | 1 次（`x-consult-r7` 之 `CODEX-R4-*`；**因已戳記故不改**） | 收集時以輪次號過濾，或要求交件檔只含本輪 ID |
| 13-c | `AGENTS.md` Rule 12 對 **stamp 輪本身**誤觸發——「動工前簽章不齊即停」，但**蓋章不是動工**且蓋章前簽章本就不齊 ⇒ **先蓋章者會擋掉後蓋章者**（競態） | 2 次（R14 codex／R21 codex） | Rule 12 增列例外：`brief-kind=stamp` 且 target 即本輪 stamp-target 者不適用 |
| 13-d | `plain_docs_sync_check.sh` 之監看清單與受管清單**皆為人手列舉** ⇒ 新批次／新檔**天生不受管** | 整批（第 1 批期間本守衛未觸發） | 監看路徑改前綴 `docs/GOV`；受管清單改**現讀資料夾導出**；`第N批-*.md` 由樣式取得監看定義。<br>🔴 **本列只記修法方向，不宣稱狀態**——狀態一律由 `TICKET-STATUS:` 機器標記行承擔（見本檔 §狀態標記），避免在病史表內產生與同表 FAIL 記錄撞 fingerprint 的綠 claim（2026-08-07 實測：於本表加 `VERIFY:` 會使 `verification_claim_check` 轉紅） |

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

### 狀態（2026-08-05）

TICKET-STATUS: PROVISIONAL

🔴 **timeout 值＝未定稿（`PROVISIONAL`）。**
第 0 批 SPEC Task 3.3 已定死定稿門檻：每家族累積 **≥50 筆** `committee_family_result`
（`result_state=success` 且含 duration 三欄）**且跨 ≥3 個不同 session／UTC 日期**。
現況：Task 3.1（duration 紀錄）尚未上線 ⇒ 三家族累積筆數皆為 **0** ⇒ **未達門檻**。
⇒ 機制照常以暫定值上線（codex 50m／grok 70m／composer 75m／外層 90m），
但**本票在門檻達成前一律維持「未定稿」**，`docs/GOVB0_FRICTION_TODO.md` 的 Task 3.3 同步標記未完工。

**本狀態行為機器可讀**：`TEST-3.3-PROVISIONAL` 條件③會擷取本票 bounded section
（`^## B-14 ` 至下一個 `^## B-` 前）並 `grep -c 未定稿`，須 **≥1**。
出生事故：`CODEX-TODO-P1-04` 實跑 `grep -c 未定稿` 得 **0**，證明該測試條件原本恆為 FAIL——
主委寫測試時引用了不存在的字串。本段即為修補。

## B-15 票 `GOV-GATECHECK-READONLY-PGREP-FP`

**`gate_check.sh` 把唯讀查詢誤判為派工。**

**事故（2026-08-03～04，本 session 三次）**：主委用唯讀指令診斷背景進程／讀委員產出時被擋：
- `pgrep -fl 'codex exec|cursor-agent|grok '` → `[GATE BLOCKED] 偵測到 kind=dispatch 高風險動作`
- `for f in codex composer grok; do ... done` 讀產出檔 → 同上
- `completeness_check.sh --lock <reconcile 路徑>` → 同上

**根因**：🔴 **2026-08-04 已讀碼＋實跑更正，勿用下方舊句。**
原記「判定僅比對指令字串是否含家族名／派工關鍵字，不區分讀寫」是**錯的**——
`gate_check.sh:86` 的家族名段只比對**命令位置**，註解明寫已避開 `cat sp_codex.txt` 這類子字串。
實際有**兩個彼此獨立**的洞（各自實跑重現，見 `handoffs/20260804-govb0-recon-{claude,codex,grok}.md`）：

**洞 A — 家族名段不理解引號**（`(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]`）
引號**內**的 `;` `&` `|` 被當成命令分隔符。實例：
`pgrep -fl 'codex exec|cursor-agent|grok '` → 命中 `|grok `；
`git commit -m "…no review file; codex closure review…"` → 命中 `; codex `（本 session 三次）。

**洞 B — `claude` 段比對子字串**（`claude[^|]*(-p|--print)`）**嚴重性更高**
觸發＝①指令含字串 `claude`（**`.claude/` 治理目錄與 `/private/tmp/claude-501/` scratchpad 皆命中**）
②之後任一處出現 `-p` 子字串（`rev-parse`／`--porcelain`／`-print`，**不必是旗標**）③兩者間無 `|`。
現場事故（2026-08-04 22:5x，主委查 push 結果）：
`head -3 "/private/tmp/claude-501/…/x.output"; git rev-parse --short origin/main` → **BLOCKED**。

🔴 **2026-08-05 00:21 第二次現場事故——觸發點是「目錄名」**：
`mkdir -p handoffs/govb0-probes; cp .claude/tmp/b15probe.sh … handoffs/govb0-probes/` → **BLOCKED**。
命中路徑＝`.claude`（scratchpad 路徑）＋ `govb0-`**`p`**`robes` 這個**目錄名裡的 `-p`**。
改成底線 `govb0_probes` 後同一條指令立即通過。
⇒ **連「取什麼檔名」都會影響指令會不會被擋**，且沒有任何提示指出真正原因。

🔴 **2026-08-06 第三次現場事故——洞 B 原樣重現，三條件全中**：
主委查背景 push 結果時執行
`cat /private/tmp/claude-501/…/tasks/<id>.output; git log --oneline -1; git rev-parse HEAD origin/main`
→ **BLOCKED**。命中＝①scratchpad 路徑含 `claude` ②後方 `rev-parse` 的 `-p` ③兩者間無 `|`。
**與 2026-08-04 22:5x 那次是同一個組合**（scratchpad 路徑 ＋ `rev-parse`），
差別只在這次多了 `cat`。⇒ **本洞的觸發是穩定可重現的，不是偶發**；
規避法（改用單一 `git rev-parse HEAD origin/main`，不帶 scratchpad 路徑）當場生效。
🔴 **2026-08-06 第四次現場事故——觸發點是 `--approver claude` 這個合法參數值**：
`bash scripts/debt_clear.sh --abandon … --approver claude; …; git rev-parse HEAD origin/main`
→ **BLOCKED**。三條件全中：①`--approver` 的值就是字串 `claude` ②後方 `rev-parse` 的 `-p`
③其間無 `|`。改 `--approver main-agent` 後同一條指令立即通過。

⇒ **本次證明影響面比先前記錄更廣**：不只 scratchpad 路徑與檔名，
**連「清債指令的合法參數值」都會觸發**——而清債正是解除 gate 阻塞的唯一路徑，
形成「被擋 → 想清債 → 清債指令也被擋」的近似死結（本次靠改參數值繞開）。

**累計現場事故：洞 A 3 次、洞 B 4 次**（08-04 ×1、08-05 ×1、08-06 ×2）。
本 session 至此 `B-15` 已咬 **7 次**（主委 6 次＋委員探針 1 次）。

🔴 **2026-08-05 00:4x 第三次現場事故——觸發點是「commit 訊息的行首」**：
`git commit -q -m "…（多行訊息，其中一行以 codex 開頭）…"` → **BLOCKED**。
機制：`gate_check.sh:86` 用 `grep -Eq` 比對，**多行字串會逐行處理，`^` 錨點在每一行都成立**
⇒ commit 訊息中任何一行以家族名開頭即命中「命令位置」。改用 `git commit -F <訊息檔>` 後通過。
🔴 **主委首寫的修法是錯的，已實測推翻**（`handoffs/govb0_probes/b15probe6.sh`）：
原擬「判定前把指令正規化為單行」——**錯**，因為**真正的多行指令，第 2 行開頭確實可能是真派工**
（`echo start\ncodex exec …`），逐行 `^` 命中在那種情況下是**正確行為**，正規化會破壞它。

**實測四象限**（2 條引號內多行 TN ＋ 2 條真多行 TP）：

| 作法 | 引號內多行（應 ALLOW） | 真多行指令（應 BLOCK） |
|---|---|---|
| 現行 gate | **誤擋** | 擋 ✓ |
| `sed 's/"[^"]*"//g'` 剝引號 | **仍誤擋**（`s///` **不跨行**） | 擋 ✓ |
| **`awk` 跨行狀態機剝引號** | **ALLOW ✓** | **BLOCK ✓** |

⇒ **正解＝剝引號必須是「跨行有狀態」的掃描**（逐字元追蹤 in-quote 狀態），
**不可用 `sed` 的行內替換**。`^` 逐行命中的語意維持不變，不需正規化。
⇒ **凡碰治理目錄的唯讀指令都在擲骰子**；「加管線就過」使它看似隨機，長期被誤判為環境問題。
🔴 **洞 B 同時是 fail-open**：`[^|]` 不跨管線 ⇒ `cat brief.md | claude -p "…"` **不會被擋**。

**票上原記的三例 FP，機制分屬兩洞**：例 1（`pgrep`）＝洞 A；
例 3（`completeness --lock`）＝**洞 B**（重建時缺 `claude` 或缺 `-p` 才會重現不出來——
三家委員與主委首輪皆誤判為「不可重現」，2026-08-04 現場事故後才定位）；
例 2（`for` 迴圈）**仍未定位**，須待 `CLAUDE-R1-P0-01` 的 deny 紀錄上線後才有辦法查。

**另兩個既有 fail-open（本輪偵察查出，票上原無）**：
① **帶路徑前綴的家族 CLI 完全不擋**：`/opt/homebrew/bin/codex exec` → ALLOW，
而 `cx_run.sh:291-292` 的 `CODEX`／`GROK` 正是絕對路徑值 ⇒ 真實派工形態不在守備範圍。
② **直接 `bash scripts/cx_run.sh …` ＝ 無 token 派工**：`cx_run.sh` 與 `_role_gate.sh`
提及 `token` 各 **0 行**，而該命令列不含命令位置的家族名 ⇒ PreToolUse 放行。

**前置阻塞（`CLAUDE-R1-P0-01`）**：被擋下的指令**全系統零紀錄**——
`gate_check.sh:28` 的 `gate_deny` 只寫 `event/ts/tool/kind/reason`（全檔 599 筆 reason 僅
`token_expired` 493／`open_debt` 106），`ts_stamp.log` 因 hook 排序在 gate 之後而不執行
（實測：已知被擋的 commit 0 筆、成功重試 2 筆）。
⇒ **誤擋率無法量測、改完無法驗證、`票 B-29` 對本票做不出差集。修法須先補紀錄。**

**修法方向（2026-08-04 偵察輪三家＋主委實測後改寫；下方「原修法選項」保留為歷史）**

四家一致：**方案②（改判準為「是否呼叫 `cx_run.sh`／`committee_run.sh`／`gate.sh dispatch`」）單獨採用＝fail-open**，
實測 TP 漏網 grok 10/13、codex 4/6、composer 7/8（手搓家族 CLI 全漏）。**明文否決單獨採用。**

採 **方案③疊加**，四個部位：
1. **引號感知**（解洞 A）：先剝除單／雙引號 span，再套命令位置判定。
2. **`claude` 段收窄**（解洞 B）：`claude` 比照家族名限定命令位置
   `(^|[;&|][[:space:]]*)(\S*/)?claude[[:space:]]`，且 `-p`／`--print` 須為**獨立引數**（詞界），禁子字串。
3. **basename 化**（解既有 fail-open ①）：命令位置改 `(\S*/)?(codex|cursor-agent|grok|agy)[[:space:]]`。
4. **呼叫點補強**（解既有 fail-open ②）：`bash scripts/cx_run.sh`／`committee_run.sh` 亦視為派工；
   `gate.sh` 自身維持排除（否則無法 bootstrap）。

🔴 **前置**：先補 `gate_deny` 紀錄（指令＋命中的 alternation），否則改完無從驗收（見上「前置阻塞」）。
🔴 **驗收須附前後行為差集**（`票 B-29` 的典型案例，但 `B-29` 尚未實作 ⇒ 本批手動附）。
🔴 **mutation 必含**：四個部位各自 revert 後，對應的 TP 須轉為漏網（可證偽）。

**原修法選項（2026-08-03 記，已被上方取代，保留供追溯）**：①白名單純讀取動詞（`pgrep`／`ps`／`grep`／`sed -n`／`ls`／`cat`）在無寫入重導向時放行
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

🔴 **2026-08-04 二次更新：`票 B-29` 插在地基之後、其餘各層之前**（使用者同意排入）。
理由＝**其餘 17 張票都是在改「判定放行／擋下」的程式**，本票是它們共用的驗收機制；
先做則後續每張各省一至數輪（GOVFLOW `批次 B4` 實證：8 輪中 3 輪源於缺此機制）。
`B-19`（brief precheck 擴充）是本票第 1 段的掛點 ⇒ **`B-19` 須先於或同批於 `B-29`**。

### 🔴🔴 排序 v3 — **SUPERSEDED（2026-08-06 起失效，勿據以行事）**

> **執行順序的唯一來源＝`docs/GOVERNANCE_EXECUTION_ORDER.md`（FACT-KEY: governance-execution-order）。**
> **本節保留僅為逐批理由的歷史脈絡，其順序內容已被取代。與唯一來源不一致時，本節即為錯誤。**
>
> 🔴 **本節原標「唯一有效」，該標記於 08-06 三家 triage 後未撤，直接造成 2026-08-07 事故**：
> 主委據本節向使用者報告過期順序，並誤報「4 張票未排入批次」（實際全部有批次）。
> 出生事故與淨摩擦見唯一來源檔的「出生事故」節。對應票＝`票 B-25`（第 1 批 2a）。
>
> ⚠️ **同一事實不得在本檔重述**——`票 B-25` 機械強制上線前，本檔對順序**只得 pointer**。

**（以下為 2026-08-04 歷史內容）重排原因**：v1／v2 的五層圖**只涵蓋 11 張票**，另 11 張 KEEP 票
（`B-4`／`B-5`／`B-6`／`B-8`／`B-9`／`B-11`／`B-12`／`B-14`／`B-15`／`B-24`／`B-26`）
**從未排入任何一層**——其中 `B-15`（2026-08-04 命中 6 次）與 `B-26`（同日撞號 8 次）
是當日發生頻率最高的兩張。使用者指示全量重排。

**排序準則（三條，依序套用）**：
1. **降低「新票出生速度」＞ 修單一 bug**——殺一整類的優先
2. **有實測事故次數的優先於無事故引用的**（29 張中 24 張有具名事故，5 張無）
3. **硬前置**不可違反

🔴 **v2→v3 的判斷變更**：v2 把 `B-27`（地基）排在 `B-19`／`B-29`（機制）之前，**現改為機制優先**。
理由：`B-27` 是 `B-21`／`B-25`／`B-26` 的前提，**不是全部票的前提**；
而 `B-19`／`B-29` 降低**包含 `B-27` 在內**的每一張票的輪次成本 ⇒ 先做機制回收更快。

```
第0批 摩擦止血   票 B-24 → 票 B-15 → 票 B-14        （便宜、當日高頻）
       ↓
第1批 機制       票 B-19 → 票 B-29                  （降低後續每張的輪次）
       ↓
第2批 地基       票 B-27                            （B-21／B-26 的前提）
       ↓
第3批 殺手寫漂移 票 B-17 → 票 B-13（吸收 B-18）→ 票 B-26
       ↓
第4批 散文與標記 票 B-16 → 票 B-23
       ↓
第5批 fail-open  票 B-11 → 票 B-6 → 票 B-5 → 票 B-4 → 票 B-8
       ↓
第6批 完整性監看 票 B-20 → 票 B-21 → 票 B-12 → 票 B-22
       ↓
另排  票 B-9 → 票 B-28                              （硬前置鏈，大任務）
```

**逐批理由**

| 批 | 為什麼是這個位置 |
|---|---|
| 0 | `B-24` 是**寫法紀律**（驗收改狀態斷言），併入各票驗收欄，近零成本且改變後面每張的驗收品質；`B-15`（當日 6 次）與 `B-14`（單次 2h20m）是**純摩擦**，修法已明確，每輪都在收益 |
| 1 | `B-19` 是 `B-29` 第 1 段的掛點，**須同批或先行**；兩者合起來讓後續每張票的「驗收條件」從「測試全綠」變成「真實標的須改變」 |
| 2 | `B-27` 讓 `B-21`／`B-26` 有前提可依；本身不直接殺錯誤，故不排在機制之前 |
| 3 | 同族＝**手寫的東西會漂**。`B-17` 先做會**縮小** `B-13` 的 scope；`B-26` 同族併此批 |
| 4 | `B-16` 界定「機器依賴不得長在散文」，`B-23` 是其符號層的具體化 |
| 5 | fail-open 群。⚠️ **本批多數防的是蓄意繞過**，依「擋意外、不在阻擋蓄意上撞牆」**刻意後排**；但 `B-11`（依賴缺席即靜默放行）與 `B-6`（token 跨 session 互相延長）**是意外失效**，故列本批最前 |
| 6 | 遞迴補完層——`B-20` 要求「票結案須指向真的檢查」，放在多數閘門已存在之後才有東西可指 |
| 另排 | `B-9`→`B-28` 是硬前置鏈且皆為大任務，與主線無互相阻塞 |

🔴 **批次化，非一票一管線**：22 張若各走一次完整管線（每張至少 3 輪）≈ **66 輪**；
按上表 **7 批＋1 另排**，每批一次 SPEC／TODO／雙家族 review ≈ **24–30 輪**。
⚠️ **`B-19` 已由「補漏洞」層上移至「機制」層**（原排在 `B-20` 之前），因 `B-29` 依賴它。

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

### 🔴 2026-08-07 併入兩項（同族＝「機器判準長在寬鬆 regex／禁令長在路徑」）

**併入 C — `template_check.sh` 空殼掃描的兩種誤判（本 session 發作 4 次）**

`scripts/template_check.sh:391` `_hollow3_re='^[[:space:]]*[-*].*驗證'`：

| 形態 | 成因 | 發作 |
|---|---|---|
| (i) **不區分欄名** | 任何 bullet 只要句中含「驗證」二字即被要求具體 token；「目標」欄也中 | 1 |
| (ii) **字元類 `[-*]` 含 `*`** | 縮排的 markdown 粗體續行 `  **粗體**…` 被當成 bullet | **3** |

**方向安全**（誤擋非漏放），但**修法須附誤擋率 receipt**（`票 B-23` 同紀律）。

**併入 D — 禁令須寫成「行為」而非「路徑」**〔`CODEX-R2-P0-02`〕

SPEC/TODO 中的禁令若寫成「不得在 `<某檔某函式>` 加 X」＝**路徑禁令**，
實作端改在另一層重寫等效邏輯即繞過。**須寫成行為禁令＋機械驗收**：
「禁止任何使 `<既有契約表>` 中 `<某集合>` 之 rc 改變的改動，**不論實作於哪一層**」
＋「該測試檔 `git diff --stat` 須為空」（禁改測試換綠）。
**出生事故**：`docs/GOVB1_INPUT_QUALITY_SPEC.md` Task 4.1 初版即為路徑禁令，
由 `CODEX-R2-P0-02` 於 SPEC 對抗審抓出。

---

### 🔴 範圍擴充（2026-08-05 使用者裁定合併，**原條文不涵蓋，此為明文擴充**）

原 `B-16` 管的是「**契約不該長在散文裡**」。本次擴充加入**兩個相鄰但不同**的缺口——
兩者共用同一強制點（`doc_format_precheck.sh`，寫檔當下）且屬同一病族
（**文件對機器產物做出宣稱，卻沒有任何機制確認該宣稱為真**），故合併而非另開票。

#### 擴充 A — 文件內的**可執行斷言**，寫檔當下未被實跑

**問題**：文件裡寫 `` `grep -c '^X' <檔>` == 1 `` 這種**已經是可執行形式**的斷言時，
**沒有任何機制在寫下的當下去跑它**。⇒ 可以寫出「從落筆起就恆為 FAIL」的驗收條件而無人察覺。

🔴 **與原條文的差別**：原 `B-16` 擋的是「契約還停在散文、需要用 regex 去解析」；
**擴充 A 的契約已經是可執行形式了，問題是沒人執行**。兩者互補，不重疊。

**事故（2026-08-05，第 0 批 TODO，主委實測）**：
| # | 主委寫下的斷言 | 實測 | 後果 |
|---|---|---|---|
| 1 | `票 B-14` bounded section 含「未定稿」 | `grep -c` → **0** | 該測試自落筆起恆為 FAIL |
| 2 | `票 B-24` bounded section 含「部分完成」 | `grep -c` → **0** | 同上（`CODEX-R8-P0-01` BLOCKING） |
| 3 | 條件② `grep -c '…未完工…'` **== 1** | 實測 **2** | **測試定義自身含該字串 ⇒ 自我引用污染** |
| 4 | 補救時在否定敘述提到被禁關鍵字 | `grep -c` 由 0 → **4** | **主委補救動作本身弄壞自己的測試** |
| 5 | `RESIDUAL:` 標記未行首錨定 | `grep -c` → **2** | 同 #3，同一陷阱**當日第五次** |

**修法（判準可機械算）**：文件內凡符合「可執行斷言」樣式者——
`` `<cmd>` == <值> ``／`` `<cmd>` ≥ <值> ``／`` `<cmd>` → <值> ``（`<cmd>` 限白名單：`grep -c`／`wc -l`／`jq -r`／`sha256sum` 等唯讀命令）——
**寫檔當下實跑並比對宣稱值**；不符 ⇒ rc=1 並印出「宣稱 X、實測 Y」。
🔴 **同時強制「標記行首錨定」**：斷言若比對機器標記（`TICKET-STATUS:`／`TASK-STATUS:`／`RESIDUAL:` 等），
**標記必須寫在行首、斷言必須帶 `^`**，兩者缺一即自我污染（事故 #3／#5 的通解）。

#### 擴充 B — 文件引用的**函式名／檔名**無存在性檢查

**問題**：文件寫「檔案：`scripts/x.sh` 的 `_foo()`；既有 caller：`_bar()`」時，
**沒有任何機制確認 `_foo`／`_bar` 真的存在、或呼叫方向是否正確**。

**事故（2026-08-05，第 0 批 TODO，`CODEX-TODO-P0-02` BLOCKING）**：
- 主委寫「輸入＝`brief_conformance_check.sh` 經 `_bc_kv` 回傳」——
  實測 `grep -n '_bc_kv' scripts/cx_run.sh` 顯示它是 `mktemp` 的**暫存檔路徑變數**（`:39`），**不是函式**。
- 主委寫「既有 caller ＝ `_run_cli_and_emit`」——
  實測 `_prepare_and_run`(`:501`) **呼叫** `_run_cli_and_emit`(`:513`)，**方向相反**。
⇒ 執行端照文件做會**改錯函式、找不存在的 helper**。

**修法**：文件內 `` `<path>` `` 與 `` `_<ident>()` `` 樣式 ⇒
①路徑須存在於 repo；②識別字須能在該路徑內 `grep` 到定義；③找不到 ⇒ rc=1。
**誠實邊界**：③**擋不了「方向寫反」**（`_a` 與 `_b` 都存在時無法判斷誰呼叫誰）⇒
此為**具名殘留**，須靠 code review 或另立票，**不得宣稱本擴充已全解**。

#### 擴充 C — **宣稱的量詞範圍 > 實際驗證的覆蓋範圍**（2026-08-06 使用者裁定合併）

**問題**：實跑了**子集**，結論卻寫成**全集**。與擴充 A 的差別：
擴充 A 管「斷言**沒被執行**」；**擴充 C 管「斷言執行了，但涵蓋範圍配不上結論的範圍」**。
⇒ 產出帶 receipt、看起來已驗證，`verification_claim_check.py` 仍放行。
VERIFY:probe-coverage-outward-20260806 — `python3 scripts/verification_claim_check.py --files <探針>` → **rc=0**（2026-08-06 實跑）。
SUPERSEDED: 本行實測**取代**主委原先「依該工具檔頭自陳推論其行為」的說法——
該推論未經實跑，本身即是本擴充要治的病（讀了 A 就宣稱 B）。

**上述 VERIFY 的細節**（實跑，非引用檔頭推論）：探針含兩案例——
A＝樣本 1 個 ＋ 結論寫「全部 20 個消費者皆不受影響、保護未減弱」＋ 附 receipt；B＝範圍相符。
`python3 scripts/verification_claim_check.py --files <探針>` → **rc=0（兩案例皆放行）**。
🔴 **COVERAGE: 1/N 外推形式**——本探針只證「**至少一種**帶 receipt 的範圍外推會被放行」，
未列舉全部形式 ⇒ **不得宣稱「該工具對所有外推皆無感」**。
（該工具檔頭亦自陳：「分類器只路由語境與 provenance，**不判斷『人對結果的詮釋是否正確』**」，
但檔頭是**設計意圖**，不等於實際行為——上述 rc=0 才是行為證據。）

**事故（2026-08-06，主委同型 11 次，6 次由委員抓到；下列為可定位者，依 `VALUE_RULE`）**：

| # | 主委宣稱 | 實跑涵蓋 | 推翻者 |
|---|---|---|---|
| 1 | 「封存後消費者不受影響」 | 只驗 **1/20** 消費者 | codex |
| 2 | 「10K→0.09s 故非即時風險」 | 只量**小輸入**，母體含 500K | codex（主委撤回） |
| 3 | 「兩家一致主張關閉，交集 9 張」 | 只取 **codex 清單**，未逐張比對 grok（真交集 **7** 張） | 主委自查 |
| 4 | 「保護未減弱」 | 只驗「沒變差」，未驗「有無新洞」（同行混用 `APPROVED`+`REJECTED` 可繞過） | codex |
| 5 | 「31/38 張帶事故證據」 | 關鍵字 `grep` 命中數當證據 | codex（立 `VALUE_RULE`） |
| 6 | 「`###` 一律作廢」 | 由**單一失敗案例**外推全體 | grok（三探針證偽） |
| 7 | 「HANDOFF 未 commit 清單 9 個」 | 憑印象，實際 **10** 個 | 主委自查 |

**修法（判準可機械算）**：文件／報告中，凡句子同時滿足
①含**全稱或否定量詞**（`全部`／`皆`／`一律`／`都`／`沒有`／`未`／`無`／`整體`／`任一`／`所有`／`N 個`）
②所在段落引用 receipt 或實跑輸出
⇒ **必須同段宣告 `COVERAGE: <實跑樣本數>/<母體數> <母體定義>`**；
```
缺 COVERAGE 欄                          ⇒ rc=1
實跑樣本數 < 母體數 但量詞為全稱        ⇒ rc=1（印「宣稱涵蓋全集、實跑 X/Y」）
母體定義為空或寫「全部」等自我指涉      ⇒ rc=1
```

**誠實邊界（四條，不得宣稱本擴充已全解）**：
- 母體數多數情況**無法自動求得** ⇒ 由作者宣告，工具只驗「**有沒有宣告**」與「**兩數是否與量詞矛盾**」；
- **擋不住作者謊報母體**——屬「擋意外不防蓄意」，與 `票 B-23` 同紀律；
- 中文全稱量詞形式**無界** ⇒ 初始集合須由**已發生事故**導出（上表七項即初始集合），
  並依 `票 B-23` 紀律**先全量掃描定集合並附誤擋率 receipt，不得憑想像列舉**；
- 🔴 **掃描範圍缺口（2026-08-06 實測發現，本票開票時未知）**：
  `verification_claim_check.py:1918 _is_scannable_path()` 只認
  `HANDOFF.md`／`handoffs/**.md`／`docs/**.md`
  ⇒ **`白話說明/` 全數不在掃描範圍**。
  **VERIFY**：`grep -n 'def _is_scannable_path' -A 16 scripts/verification_claim_check.py`
  → 白名單僅 `("handoffs/", "docs/")` 兩個 marker ＋ `HANDOFF.md` 特例，2026-08-06 實跑。
  **後果**：主委寫給使用者看的文件**從未被 claim checker 檢查過**——
  而那正是使用者唯一的稽核面（使用者原話：「我也是看你寫出來在這裡的句子」）。
  ⇒ 修法須決定是否將 `白話說明/` 納入掃描；**納入前不得宣稱本擴充覆蓋使用者可見面**。

**吸收 `票 B-40`**：`B-40`（`GOV-USER-ATTRIBUTION-UNVERIFIED`，主委把自創約束掛使用者名下）
是本擴充的**一個實例**——宣稱「使用者定」而實際涵蓋範圍為零。
使用者原話：「票永遠開不完，除非你有一勞永逸的解決方式」⇒ **不為該子型單獨立票，由本擴充通則涵蓋。**

**淨摩擦（依使用者 2026-08-06 判準）**：
新增每次成本 ≈ 0（寫全稱句須附覆蓋範圍，**本為應盡義務**，僅由自律改為機器強制）；
避免次數 ＝ 上表 7 次／單 session，每次成本 ＝ 1 輪委員往返或使用者等待。**淨值為負。**

#### 為何合併而非另開票

三項判準（使用者 2026-08-05 裁「可以在這幾票解決就合併」）：
①**強制點相同**——皆掛 `doc_format_precheck.sh` 寫檔當下；
②**病族相同**——文件對機器產物的宣稱無人驗證；
③**分開做會重複實作**——四者都需要「解析 md 取出機器依賴片段」這一層。

**與其他票的邊界（勿重複開票）**：
- `票 B-13`（merge completeness）＝管「**有沒有漏**」；本擴充＝管「**寫進去的是不是真的**」。互補。
- `票 B-17`（表格改資料檔）＝管「手寫表格必漂」；本擴充＝管「非表格的散落宣稱」。互補。
- `票 B-29`（行為差集）＝管「改程式時的副作用」，強制點在**改碼**；
  **擴充 C** ＝管「宣稱範圍 > 驗證範圍」，強制點在**寫檔**。二者為同一病族的**兩個域**：
  B-29 的失效輸出（「只驗我要的效果」）常以擴充 C 的形式（「保護未減弱」）寫進文件 ⇒ **互補，不重疊**。
- `票 B-25`（fact-key 單一來源）＝管「同一事實**多份副本**漂移」；
  擴充 C 管「**單一陳述**的範圍超出證據」。無重疊。

**槓桿估算（實測，非估計）**：
- 擴充 A／B：本 session 主委引入的缺口中**至少 9 次**會被寫檔當下擋掉（上表 5 次 ＋ `_bc_kv` 類 2 次 ＋ 計數漂移 2 次）。
- 擴充 C：2026-08-06 單一 session **7 次可定位**（擴充 C 事故表），其中 **4 次靠委員推翻**、
  **1 次（10K→0.09s）已進入使用者可見結論後才撤回**。

**排期**：隨 `B-16` 進**第 4 批**過於落後 ⇒ 🔴 **本擴充部分（A／B／C）提前至第 1 批**
（與 `B-19`／`B-29`／`B-31`／`B-38` 同批），理由＝它擋的正是**後面每一批都會再犯**的錯。
`B-16` 的原條文（散文契約偵測）維持第 4 批。

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

### 狀態（2026-08-05）

TICKET-STATUS: PARTIAL

- **紀律面**（驗收欄一律寫執行後狀態斷言，零新增元件）＝**隨第 0 批交付**，
  已落實於 `docs/GOVB0_FRICTION_SPEC.md` §V 與 `docs/GOVB0_FRICTION_TODO.md` §0.5。
- **機械強制面**（`acceptance_state_check.sh` ＋ grandfather SoT ＋ 具名 owner／UTC 到期日／到期後 fail-closed）
  ＝**已裁定 SPLIT 移出，獨立排期**，本批**不做**。
⇒ **code review 與完工回報一律不得宣稱本票已完成。**

🔴 **為何用 `TICKET-STATUS:` 標記而非散文關鍵字**（出生事故，同型錯誤本日第四次）：
主委原本把測試寫成「bounded section 內 `grep -c 部分完成` ≥1 且 `grep -c 全綠` == 0」。
`CODEX-R8-P0-01` 實跑得 `B24_PARTIAL_COUNT=0`——目標區段內**根本沒有該字串**。
主委補寫狀態段後，**又因為在否定敘述中提到後者而使 `grep -c` 由 0 變 4，把自己的測試弄壞**。
⇒ **散文關鍵字比對本質脆弱**：任何討論該詞的句子都會污染計數，且無法區分「宣稱」與「否定宣稱」。
**改為單一機器標記行 `TICKET-STATUS: <PARTIAL|PROVISIONAL|DONE|OPEN>`**，
語意明確、不受行文影響。此作法應推廣至所有票（列入 `票 B-17` 的修法）。

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

### 🔴 2026-08-07 併入：判準資料化（GOVB1 第 1 批之未竟項）

> **不另開票**——使用者當日指正「你又開始隨意開票，無止盡延伸嗎」。
> 本項與本票**同一機制**（單一資料源＋生成器＋diff 強制），故併入而非新開。

**病**：判準寫在 markdown 散文 ⇒ 同一判準必然多處產生副本。
GOVB1 第 1 批「原則修了、實例沒修」**發作 15 次**；四種對策（四面比對／先刪後補／
單條通讀／單一來源表）**全部失效**，因四種皆為紀律。
決定性：**第 13 次犯在「專為修此病而設的修法」內**、**第 15 次犯在「修第 13 次」的更正說明內**
（解釋舊判準時逐字複述其原文）⇒ **只要判準是散文，任何解釋它的動作都會再生副本。**

**本批已做到的極限**（三家確認，**不得宣稱已閉合**）：
`§0.1b` 判準單一來源表 ＋ `scripts/govb1_single_source_check.sh`（**正向斷言**：
只問「有沒有指回唯一來源」，不判斷該處寫什麼；差分自證 PASS→FAIL 已驗）。

**三項具名殘留**：①正向斷言擋不住「有 pointer 但旁邊另寫互斥判準」
②「引用已廢判準只寫階號」為寫作紀律，無機械偵測 ③完整解未做（即本項）。

🔴 **前置（`x-consult-r12` J-1，主委原假設已證偽）**：現行 `fact_keys` 之 `.rows[]|@tsv`
**只有平面列，不適用「現行／已廢」兩欄之表格型判準** ⇒ **須擴充 schema 或新增第二 fact-key**。

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
- **B-17**（四表結構化）＝**表格**類事實的單一來源 ⇒ 本票補的是**散文**類，二者互補不重疊
- **B-16**（散文契約偵測器）＝阻止**機器依賴的契約**進散文 ⇒ 本票管的是**人類讀的事實**，
  它們合法地留在散文裡，問題只在**有多份副本**
- **B-13**（搬遷完整性）＝單次 doc→doc 搬遷 ⇒ 本票管**長期存在的多份副本漂移**

**修法（機械可驗）**：建立 **fact-key 註冊表**，每個 key 宣告
①唯一來源檔＋錨點 ②允許出現的其他位置**只能是指標（pointer）不得是副本（literal restatement）**。
檢查器掃描全 `docs/`＋`handoffs/`，對每個 key：
```
若某處出現該 key 的字面陳述且與來源不一致  ⇒ rc=1
若某處出現字面陳述但未登記為 pointer      ⇒ rc=1（防新副本出生）
```

**風險**：fact-key 集合須**具名有界**，不得無限擴張；初始集合應由**已發生的漂移事故**導出
（上表五項即為初始集合），**不得憑想像列舉**。
🔴 **與 B-23（標記白名單）同紀律**：先全量掃描定初始集合並附誤擋率 receipt。

---

## B-29 票 `GOV-BEHAVIOR-DELTA-DECLARE`

**改「判定類程式」時，只驗證「我要的那個效果有了」，不驗證「還有什麼跟著變了」。**

### 發生什麼（本 epic 實證，非推測）

GOVFLOW `批次 B4` 走 6 輪，**其中 3 輪源於本缺口**：

| 輪 | 事故 | 當時的驗收給了什麼 | 缺的是什麼 |
|---|---|---|---|
| 6 | Task 4.1 **在真實流程上是死碼**（原檔只被記為 `committee_family_result`，checker 只認 `committee_output`） | 26 條測試全綠、mutation probe 綠、雙家族 review 過 | **沒有任何一份真實檔案的判定改變** |
| 7 | 修補二把豁免擴到**一般原檔**（實測同一原檔 rc 由 1 → 0） | 「三份真實副本現在 rc=0」 | **還有誰跟著被放行** |
| 8 | 收窄 ＋ 複核 | — | 輪 7 的後果 |

**輪 6 與輪 7 是同一個病的兩面**：驗收只問「我瞄準的目標達成沒」，不問「實際動到了哪些」。

**主委事後補跑的對照（真實語料 299 份 `sources/*.md` ＋ `synth.md`）**：
被擋檔數 **60 → 27**；本來擋現在放行 **42 份**（`sources/` 副本 27＋`synth` 15）、
本來放行現在擋 **9 份**、判定未變 **248 份**。
⇒ 若此表在**輪 1** 產出，「放行」欄會只有 15 份 synth、**27 份副本一份都不會出現**，輪 6 當場結案。

### 專案端同病（**這不是治理專屬**）

`scripts/` 現有 **21 支**一次性 baseline／compare 腳本、`tests/golden/` **7 個** baseline 目錄：
`build_l65_golden{,_baseline}.py`／`capture_{full_golden,ic1eb}_baseline.py`／
`compare_{fracdiff_maxlag_postfix,output_size,with_full_golden_baseline,wq_numba_vs_pandas}.py`／
`freeze_{batch1,batch2d,failopen}_baseline.py`／`freeze_fracdiff_maxlag_golden.py`／
`generate_golden_output.py`／`golden_multi_symbol_c3.py`／`ic1c_{freeze,validate}_baseline.py`／
`ic1d_{baseline_freeze,compare}.py`／`ic1eb_g2_golden_diff.py`／`register_v8_golden_lite.py`／
`restore_golden_inventory.sh`。

**每個 epic 重造一支，且無一支是強制的。** `CLAUDE.md` 已規定行為不變型重構須
「改前 vs 改後 byte 級一致」——**缺的是「行為本來就該變」時的對應規矩**。

### 覆蓋面

backlog 既有 28 張票中（**不含本票**），**17 張**是在改「判定放行／擋下」的程式
（`B-1`／`B-2`／`B-3`／`B-4`／`B-5`／`B-6`／`B-9`／`B-10`／`B-11`／`B-13`／`B-15`／
`B-16`／`B-19`／`B-20`／`B-21`／`B-23`／`B-26`）。
其中 **`B-23`（禁止清單反轉為允許清單）** 與 **`B-15`（放寬唯讀指令誤判）**
在定義上就是大規模改變「誰被擋」，**無前後對照即無法驗收**。

### 修法（三段強制，**由早到晚**）

🔴 **強制點必須放在最早能攔的位置**——commit 在整條線最尾端，委員已跑完，**不得作為主力**。

1. **派工當下（`gate.sh dispatch`）**——brief 須含 `EXPECTED-DELTA:` 區塊，
   宣告改動後**應該改變判定的真實標的**（治理端＝哪些檔由擋轉放行；
   專案端＝哪些數值／形狀／輸出大小應變、容差多少）。**缺區塊或格式不合 ⇒ 不發 token。**
   掛點＝`B-19`（brief precheck 擴充）。
   🔴 **此步不是檢查，是換掉驗收條件**：由「測試全綠」換成「這 N 份真實標的須改變」，
   使執行端**從第一分鐘就知道目標**，不會交出「全綠但功能是死的」產物。
2. **交件當下（`cx_run` 產出端）**——自動跑前後對照並與宣告比對，
   不符 ⇒ `result_state=format-failed`（**機制已存在**，`批次 B2` 建立），同輪立即重派。
   **忘記的代價＝同輪重跑（分鐘級），非一輪委員作廢。**
3. **commit（保險）**——`scripts/git_hooks/pre-commit` 僅作最後攔截。

### 兩份清單一律**現算**，不得手寫

- **「判定類程式」集合**＝由 `scripts/git_hooks/*` 與 `gate.sh` 的呼叫圖導出。
  🔴 手寫清單必漂（本 epic 內 TODO §0 數字表漂 4 次為證）。
- **語料範圍**＝由該程式實際會處理的檔案集導出，**不得由人填**。

### 誠實邊界

- **不防蓄意**：可寫假的 `DELTA-ACK` 混過。依「擋意外、不在阻擋蓄意上撞牆」，不解。
- **全新功能無舊行為可比**時，本機制退化為只能證明「既有行為未壞」，證不了新功能是活的。
- **治理端與專案端不共用實作**：治理端判定為布林（放行／擋下）且舊版可由 git 現取；
  專案端為數值，需容差與 baseline 儲存。**同一套規矩、兩個實作。**
- 主委首次實跑此對照即因 **zsh 不對未加引號變數斷詞**而失效，
  報表印出「前 0 後 0、無差異」——**壞掉的量測與「一切正常」外觀相同**。
  ⇒ 工具**自身**須帶有效性自檢（輸出含 `Traceback` 即停；前後皆 0 即停）。

### 與既有票的關係（依 `B-19` 紀律，開票前盤點）

- **`B-24`（驗收改狀態斷言，非 rc）**：同向且互補——本票規定「斷言什麼」，`B-24` 規定「怎麼斷言」
- **`B-19`（brief precheck 擴充）**：本票第 1 段的掛點，**須先於本票或同批**
- **`B-13`（搬遷完整性）／`B-17`（四表結構化）**：管文件，本票管**程式行為**，不重疊

### 建議順序

排在 **0 層地基（`B-27` 文件分類）之後、其餘 17 張改判定票之前**——
每一張都會用到它，先做則後續每張票各省一至數輪。

### 狀態

**2026-08-04 開票，未實作。** 使用者已同意排入。

---

# 🔴 2026-08-04 第 0 批偵察輪當場撞出的新票（`B-30`～`B-31`）

**背景**：`GOVB0-RECON-R1`（第 0 批開工偵察，三家＋主委）**單一輪**內撞了 6 次摩擦，
其中 **4 次無既有票涵蓋**。四次分屬兩個病，開兩張票。
**開票前已依 `B-19` 紀律盤點既有 29 張票，確認無涵蓋**（掃 `覆蓋`／`覆寫`／`overwrite`／
`format-failed`／`銷帳`／`角色閘`／`brief_sha` 七組語意詞）。

## B-30 票 `GOV-COMMITTEE-OUTPUT-SELF-OVERWRITE`

**委員可以把自己已經寫好的產出檔覆蓋掉，系統無任何保護，且主委只會看到「這家跑很久」。**

### 事故（2026-08-04，`GOVB0-RECON-R1`，實測）

codex 耗時 **43 分 26 秒**，超出它自己的歷史 max（43.1m）。
主委讀 runlog 尾端才查出原因——codex 自述：

> 我發現報告路徑與合約要求的 handoff 路徑同名，剛才建立 handoff 時**覆蓋了報告**；
> 這是我這邊的檔案路徑失誤。現在恢復完整報告到使用者指定路徑…

同輪對照：grok ~5 分、composer ~15 分。⇒ **約 28 分鐘（65%）花在重寫被自己蓋掉的檔**。

### 為什麼是系統缺陷而非委員個人失誤

1. `cx_run.sh` 把產出路徑當**純參數**傳給委員，**不保護該路徑**——委員可任意重寫、清空、改名。
2. 委員自行建立其他檔案時**沒有機制檢查是否撞到自己的產出路徑**。
3. 主委端**看不到**：`committee_run.sh` 緩衝輸出，中途只有檔案大小可觀察，而
   「大小歸零後重新長回來」與「持續寫入中」外觀相同（**壞掉的量測與正常外觀相同**，同
   `CLAUDE.md` Gotchas 的 zsh 斷詞／locale 兩例）。
4. 若覆蓋發生在**接近逾時**時，`B-14` 的「產出完整即成功」判準會拿到一份**被截斷的新檔**。
   ⇒ **本票與 `B-14` 直接耦合，須同批考慮。**

### 修法方向（未定案，SPEC 前須先實測）

- ① `cx_run.sh` 於 CLI 返回後比對產出檔的 **inode／大小／sha 變化軌跡**，偵測「曾非空後歸零」；
- ② brief 骨架（`new_brief.sh`）明文標示產出路徑**專用、禁挪作他用**，並列出委員自建檔的命名空間；
- ③ 產出路徑加 `.part` → 完成才 rename（atomic close），順帶給 `B-14` 一個真正的 terminal marker。
  🔴 ③ 與 `B-14` 的「terminal marker」需求是**同一個機制**，勿各做一份。

### 與既有票的關係

- **`B-14`（委員寫完不退出）**：同為委員生命週期，且 ③ 的 atomic close 同時解兩票 ⇒ **強烈建議同批**
- **`B-24`（驗收看狀態非 rc）**：本票是「狀態悄悄變壞而無人察覺」的具體案例
- **`B-20`／`B-22`（完整性監看）**：可能是掛點，實作前須確認不重複造輪子

### 狀態

**2026-08-04 開票，未實作。**

## B-31 票 `GOV-FORMATFAIL-NO-CHEAP-FIX`

**委員交件格式不合規（`result_state=format-failed`）之後，唯一可行路徑是「整份重跑」；
且該輪債務無法銷帳，因而擋住所有後續派工。**

### 🟡 2026-08-06 部分完成：**預防層**已落地（三家戳記核可）

新增第四個修法方向（原票只列 ①fixup ②附掛 brief ③`debt_clear` 降級，皆為**事後補救**）：
**④ 預防——交件前自檢進 `cx_run.sh` prompt 模板**（`review|consult|closure`）。

- 產出：prompt 追加 `bash scripts/completeness_check.sh --single ${out} --family ${fam}`，
  並**明示 0-findings 落差**（`--single` 回 PASS 但收斂仍 FAIL，屬 `票 B-38`）
  ＋警告「勿為湊數捏造 finding」。
- 測試：`tests/governance/test_cxrun_selfcheck_prompt.py`（**7 tests**），含
  期望集合斷言、`closure` runtime case、真實 format-failed 形態 fixture（正反對照）、反向 mutation。
- 收斂：`handoffs/reconcile/20260806-govb31-b1-review-r1/synth.md`
  （9 findings → 4 群集，三家 APPROVED，sha256 `837188bc`）。
- 實跑：`pytest tests/governance -q` → **789 passed**（改動前 782）。

🔴 **證據強度具名（兩家 P1 一致）**：效果證據為 **n=1**（2026-08-06 一輪兩家）。
**不宣稱 format-failed 發生率下降**，只宣稱「消除一個已知可重現的失敗模式」。
可終結的後續量測（落地後 30 天從 audit 抽 `result_state=format-failed` 計數比對）
⇒ **併入 `票 B-37`**，本票不做。

🔴 **①②③ 三個事後補救方向仍保留**（三家一致）：預防層不涵蓋「已經 format-failed 之後怎麼便宜修」。
codex 裁定優先序＝①fixup／②附掛 brief 優先，③`debt_clear` 降級最後且須雙家族 adversarial。

### 事故（2026-08-04，`GOVB0-RECON-R1`，實測）

composer 的 R1 產出**內容完整、6 條 findings 齊全**，只有兩處格式瑕疵：
① 多了一個 `## RECONCILE-STAMP` 標題（本輪 `brief-kind=consult` 根本不需戳記）
② `COMPOSER-R1-P1-01` 的 `**來源摘要**` 寫成 `scripts/completeness_check.sh#（:1459-1472 行為）`，
`#` 後不是 hex digest。

修這兩處**是分鐘級的工作**。主委嘗試派一份「只修格式」的小 brief，**連撞三道牆**：

| # | 阻擋 | 出處 | 為什麼擋 |
|---|---|---|---|
| 1 | `brief-kind: impl` → 角色閘拒派 composer | `scripts/governance_roles.json` `_rules.impl` | `impl` 只准 implementer（grok）。**沒有「產出方修正自己交付物」這個 kind** |
| 2 | 改用 `brief-kind: closure` 後 → `ERROR: brief_sha256 與開債記錄不符（換 brief 掛既有 round 已拒）` | 同輪重派的 round 綁定 | 同輪重派**只接受原 brief**，送不了小 brief |
| 3 | 正規銷帳 `debt_clear.sh --round-id --session` 會跑 `completeness_check`，一家不合規即失敗 | `scripts/debt_clear.sh` | ⇒ 債務維持 OPEN ⇒ **擋住所有後續派工**（`gate_deny reason=open_debt`，audit 內已 106 筆） |

**結果**：為了修兩行格式，只能讓 composer **重跑整份 15 分鐘的分析**。
逃生口 `--abandon` 存在，但其兩個 kind（`no-findings-expected`／`collection-failed`）
都不誠實描述「三家合格、一家格式瑕疵」，且用它等於繞過閘門。

### 為什麼不是「照設計運作」

`cx_run.sh` 自己的訊息寫著「**可同輪重派**」，暗示存在低成本修正路徑；
實測**不存在**——同輪重派＝用原 brief 重跑全部，成本與首次相同。
`format-failed` 這個狀態值因此**沒有兌現它的設計意圖**（三值契約中它與 `failed` 分離，
本意就是「產出有救，別當失敗」）。

### 修法方向（未定案）

- ① 新增 `brief-kind: fixup`（或等價），角色規則＝**只准原產出方**，且只准改自己那一個檔；
- ② 同輪重派允許「附掛 brief」：round 綁定改為「原 brief sha ＋ 附掛 brief sha 的有序對」，
  審計記兩者，**不破壞 provenance**；
- ③ 或反向：`debt_clear` 允許在**其餘家族全合格**時，以具名理由對單一 format-failed 家族降級，
  但須寫入 audit 且 reconcile 的 union 分母顯示「該家族缺席」。
  🔴 ③ 觸及 fail-closed 邊界，**須雙家族 adversarial 專審**，勿主委自裁。

### 與既有票的關係

- **`B-19`（brief precheck 擴充）**：①的掛點
- **`B-24`（驗收看狀態非 rc）**：本票暴露「`format-failed` 這個狀態值沒有對應的處理路徑」
- **`B-30`**：兩票都源自「委員產出的生命週期沒有被完整建模」，但可各自獨立實作

### 🔴 第二次事故（2026-08-05，`GOVB0-SPEC-R5`／`R5B`，實測）— **新增兩項關鍵事實**

**經過**：composer 的 R5 產出把「逐條確認結果」寫成 `## G-1（\`CODEX-R4-P0-01\`…）— **CLOSED**`。
`completeness_check.sh` 把**每個 `##` heading 都當 finding ID 候選**解析，6 個皆不符 schema ⇒ **整份 format-failed**。

**新事實 ①：根因是 brief 自相矛盾，不是委員失誤。**
該 brief 同時要求「findings 一律用 `## <家族>-R5-P<n>-<nn>`」與「逐條確認結果 G-1～G-6 各一段」。
委員照後者寫就必然產生非 canonical 的 `##` heading。⇒ 與 `票 B-32` 同病：**我們自己的指示誘導格式違規**。

**新事實 ②（🔴 最重要）：純 prompt 層警告已實測無效。**
主委修 brief 加入明文警告——「`##` 只准用於 canonical finding ID heading，逐條確認**一律用 `###` 或表格**，
否則整份 format-failed（附本票票號與原因）」——**composer 補派輪仍寫成 `## G-1（…）— NOT-CLOSED`，同型失敗第二次**。
⇒ **證實修法不能靠 prompt／紀律，必須在產出端或檢查器端機械化**（呼應使用者定死的「工具必須自帶強制機制」）。

**額外阻擋**：修好 brief 後**無法同輪重派**（`ERROR: brief_sha256 與開債記錄不符`）。
⇒ 形成死結：**「brief 有缺陷」這個最該修的情況，恰好是同輪重派擋死的情況**。只能棄輪重開。
本日因此連續 `--abandon` 兩輪（`a50b7e6c`／`8fedcd8b`，皆 `collection-failed`）。

**代價**：兩輪派工（各約 10 分鐘）＋ 兩次棄輪。**實質產出未損失**——兩家內容皆完整收到且結論一致。

### 追加修法方向（源自第二次事故，**優先於原 ①②③**）

- ④ **`completeness_check.sh` 的 finding heading 解析改為「pattern-matched 才視為 finding」**：
  只有符合 `^## [A-Z]+-R\d+-P\d+-\d+$` 的 `##` 才當 finding ID；其餘 `##` 視為一般章節標題。
  🔴 **此解有真實張力，須委員裁**：放寬後「ID 打錯字的真 finding」會**被靜默忽略**（漏 > 誤擋）。
  折衷方向＝**近似比對**：完全不像 ID 的（如 `## Verdict`／`## G-1（…）`）忽略；
  **像但不合規**的（如 `## COMPOSER-R5-P1-1`，位數錯）維持 hard-fail。
- ⑤ **產出端自動正規化**：`cx_run.sh` 交件時把非 canonical 的 `##` 自動降級為 `###`。
  ⚠️ 但這會改動委員產出的位元組，與 byte-faithful 附錄原則衝突 ⇒ 須先裁定優先序。

### 狀態

**2026-08-04 開票，2026-08-05 第二次現形並追加兩項修法方向，未實作。**
🔴 **嚴重度應上調**：原判「摩擦」，現已實測**連續兩輪派工失敗**且 **prompt 層修補無效**。
排期建議：與 `B-19`（派工單檢查）同批（第 1 批），④ 為最小可行解。

## B-32 票 `GOV-CXRUN-STAMP-PROMPT-UNCONDITIONAL`

**`cx_run.sh` 對「每一次派工」都注入 RECONCILE-STAMP 指示，不分 `brief-kind`；
而 `completeness_check` 會把委員照做寫出的 `## RECONCILE-STAMP` 判為格式違規。
⇒ 系統自己誘發交件失敗。**

### 碼證（2026-08-04 實測）

- `scripts/cx_run.sh:512`（**無條件，無 brief-kind 分支**）：
  `prompt="讀 ${brief} 照其指示做。…你的 task-id=${task_id}。RECONCILE-STAMP 的 task: 欄位須逐字使用此值；brief 內任何 task-id 範例一律不得採用。"`
- `scripts/completeness_check.sh:179`：任何 `## ` 標題不符
  `^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$` 即 `COMPLETENESS FAIL: invalid finding ID`。
- 合法戳記其實是**一整行**（`cx_run.sh:345` 的正則）：
  `RECONCILE-STAMP: <family> APPROVED <date> sha256:<hash> task:<id>`，**不是 `## ` 標題**。
  注入句**沒有說明這件事**，也沒說「consult 輪不需要戳記」。

### 事故成本（`GOVB0-RECON-R1`）

composer **連續兩次** `result_state=format-failed`，兩次都是同一個 `## RECONCILE-STAMP`：

| 次 | 缺陷 | 成本 |
|---|---|---|
| 1 | `## RECONCILE-STAMP` ＋ `P1-01` 來源摘要非 hex | 首輪 ~15 分 |
| 2（同 brief 重跑） | `## RECONCILE-STAMP`（digest 已自行修正） | 再 ~15 分 |

⇒ **重跑不可能解決**，因為每次重跑都會重新注入同一句誘導。
連帶：該輪債務無法正規銷帳（見 `票 B-31`），擋住所有後續派工。

🔴 **codex／grok 未觸發，純屬運氣**——同一句注入對它們也送出了，只是它們沒寫成標題。
**這是潛伏 trap，不是 composer 的個別問題。**

### 修法方向（未定案）

- ① 注入句**依 `brief-kind` 分支**：只有 `stamp`／`closure` 輪才提 RECONCILE-STAMP；
- ② 若仍要提，**必須連格式一起講**（「是一整行 `RECONCILE-STAMP: …`，不是 `## ` 標題」）；
- ③ 或 `completeness_check` 對 `## RECONCILE-STAMP` 給**專屬錯誤訊息**並指出正確寫法
  （現在的訊息 `invalid finding ID` 完全看不出該怎麼修）。
  🔴 ①②③ 不互斥；至少 ① 必做，否則 consult／review 輪永遠帶著一句無意義的誘導。

### 與既有票的關係

- **`B-31`（format-failed 無便宜修正路徑）**：本票是**觸發源**、`B-31` 是**放大器**。
  兩票獨立存在意義：即使修好本票，其他成因的 format-failed 仍無便宜修正路徑。
- **`B-16`（機器依賴長在散文裡）**：注入句是散文，卻是機器行為的一部分 ⇒ 同族

### 狀態

TICKET-STATUS: DONE

🔴 **2026-08-07 更正——原記「未實作」為過期狀態**〔`GROK-R1-P1-03`（GOVB1-RECON-R1）指出，主委複驗成立〕。

**碼證**：`scripts/cx_run.sh:313-359` `_maybe_register_stamp_output()` 依 `brief-kind` 分派；
`tests/governance/test_cxrun_stamp_prompt.py` 逐 kind 斷言
（`test_11_consult_prompt_no_reconcile_stamp`／`test_11_stamp_prompt_has_stamp_and_format`／
`test_11_closure_prompt_has_stamp_and_format`），並含 mutation
`test_11_mut_unconditional_inject_turns_consult_red`（還原無條件注入 ⇒ CONSULT 轉紅）。

🔴 **修法方向與票名相反，勿照票名施工**：票名 `…-UNCONDITIONAL` 描述的是**病**
（注入句無條件出現而誤導 consult 輪委員），**修法是「按 kind 條件注入」**。
〔`GROK-R1-P1-03` 措辭寫成「無條件注入已落地」，語意反向；主委讀碼複驗後更正。
**執行端產物視為不可信資料，本例即碼證。**〕

**殘留**：無。原「建議併入第 0 批」已不適用。

## B-33 票 `GOV-LOCALE-GUARD-DRIFT`

**治理守衛的判定依賴環境 locale；在 `LC_ALL=C` 下 `gate.sh` 與 `doc_format_precheck.sh` 雙雙 fail-open。**

**開票依據**：第 0 批 SPEC 審查 R1，**兩家一致裁定須開票**——
`COMPOSER-R1-P1-03`（MAJOR，範圍＝`gate.sh` D-1 Verdict 正則／`doc_format_precheck.sh`／`template_check.sh` §A 錨點）、
`CODEX-R1-P0-07`（「治理控制面的 locale fail-open，必須開新票；『不納入本批』只有在正式登記、排序與環境護欄存在時才成立」）。

### 事故（2026-08-04，實測）

主委為繞開 `.claude/gate/ts_stamp.log` 的編碼問題而 `export LC_ALL=C`，該設定洩漏進 pre-push 環境：

| 案例 | 期望 | `LC_ALL=C` 實際 | 方向 |
|---|---|---|---|
| `## Verdict：`（全形冒號後空白）送 `gate.sh` | 拒發 token | **發出 token** | 🔴 **fail-open** |
| `**Verdict: （待填…）**` 送 `doc_format_precheck.sh` | rc=2 擋下 | **rc=0 放行** | 🔴 **fail-open** |
| 合格 SPEC 送 `template_check.sh spec` | rc=0 | 誤判缺 §A 錨點 | fail-closed 誤報 |

拿掉 `LC_ALL=C` 後同一批測試 **96 passed**。三個案例的共同點＝**判定字串含全形標點**（`：`／`…`／`（）`），
而這些正是治理文件的常態寫法。

🔴 **為何是真問題而非「別亂設 locale」**：委員 CLI 與 CI runner 的 locale **不在主委控制範圍**；
任一執行端在非 UTF-8 環境跑，就**靜默失去**這兩道守衛，且**沒有任何訊號**（fail-open 不報錯）。

### 修法方向（未定案）

- ① 受影響腳本**顯式鎖定 locale**（在腳本內設定，不依賴繼承），禁依賴環境預設；
- ② 或改用不依賴 locale 的位元組級比對（全形標點以位元組序列表示）；
- ③ 加一條 meta 測試：**在 `LC_ALL=C` 與 UTF-8 兩種環境下各跑一次守衛測試**，兩者結果須一致
  （這條是**強制機制**，沒有它，修完仍會再漂）。

### 與既有票的關係

- **`B-15`（gate 判定）**：無耦合——兩家一致，**不納入第 0 批**（避免 scope 膨脹）。
- **`B-16`（機器依賴長在散文裡）**：同族（判定依賴不穩定的外部條件）。
- **`B-29`（行為差集宣告）**：本票是「環境改變導致行為差集」的案例，`B-29` 只涵蓋「程式改變」。

### 狀態

**2026-08-04 開票，未實作。排第 1 批之後**（兩家一致：本批不併入，但不可無票放置）。

## B-36 票 `GOV-COMPLETENESS-CLUSTER-BLINDSPOT`

**收斂工具宣稱的「零掉項」只涵蓋檔案層，不涵蓋判斷層——
一條 finding 可以完全沒被寫進群集／處置表，`completeness_check --lock` 仍然 rc=0。**

### 碼證（2026-08-05 實證，`GOVB0-SPEC-R2` 戳記輪）

- `scripts/completeness_check.sh --lock` 驗的是「來源檔的每個 heading ID 是否出現在綜合檔」。
- 綜合檔的**附錄逐字保留全部來源 findings**（byte-faithful，設計如此）⇒ **任一 ID 必然出現在綜合檔**。
- ⇒ **「該 ID 有沒有被寫進群集／處置表」完全沒有機器檢查。**
- 實證：主委在 `handoffs/reconcile/20260805-govb0-spec-r2/synth.md` 的群集表**漏掉 `COMPOSER-R2-P1-01`**，
  `bash scripts/completeness_check.sh --lock …` 仍 **rc=0**；
  由 **codex（`MISMATCH_1`）與 composer（不蓋章理由）在戳記輪各自獨立指出**才被發現。

🔴 **這正是收斂工具存在的理由被架空**：memory `收斂方法工具上線` 記載該工具的目的是
「機械擋 Claude 手抄合併委員產物掉項」，但**掉項發生在群集表時它抓不到**。
本次靠人（委員）補上，而使用者定死「**不准靠紀律和記憶**」。

### 修法方向（未定案，嚴重度待委員裁定）

- ① `completeness_check --lock` 增加一層：**群集段**（`## 附錄` 之前、`## 戳記` 之前的區段）
  須逐一引用每個來源 ID，缺一即 FAIL。
  🔴 難點＝「群集段」的界定須機械可判；現行 synth 由 `reconcile_build.sh` 生成，段落結構固定，可行。
- ② 或由 `reconcile_build.sh` 生成群集表骨架時**預先列出全部 ID**（一行一條，處置欄待填），
  主委只能填處置不能刪列 ⇒ 從**產出端**杜絕（符合使用者定死「檢查點放產出端」）。
- 🔴 **②優於①**：①是事後檢查，②是結構上不可能漏。建議兩者併用。

### 與既有票的關係

- **`B-13`（搬遷／收斂填表漏東西不會被擋）**：**高度重疊，可能應合併**——`B-13` 吸收了 `B-18`，
  範圍是「收斂填表漏填不會被擋」。本票是其**具體實例＋已定位的機制**。
  ⚠️ **開票前已比對**：`B-13` 票面未載明本盲點的機制（附錄使 ID 必然存在），故本票有獨立資訊；
  但**實作時應與 `B-13` 合併為一，避免 `票 B-11`／`B-12` 那種跨檔重複配置**。
- **`B-29`（行為差集宣告）**：同族——「宣稱驗過的東西，實際驗的範圍比宣稱窄」。

### 狀態

🔴 **2026-08-05 委員裁定（SPEC R3 輪，兩家一致）**：
- **嚴重度＝MAJOR／P1**（`CODEX-R3-P1-05`：判斷層完整性漏洞；`COMPOSER-R3-P2-02`：MAJOR 治理債）
- **應併入 `票 B-13`**（`CODEX-R3-P1-05` 明示）⇒ **本票不獨立實作**，內容併入 `B-13` 的範圍
- **修法在產出端**（兩家一致）：`reconcile_build.sh` 生成群集表骨架時**預列全部來源 ID**（一行一條，處置欄待填），
  主委只能填處置**不能刪列** ⇒ 結構上不可能漏。事後檢查為輔。
- **`CODEX-R3-P1-05` 另註**：本項為「TODO 生成前的收斂工具前置」——因為第 0 批自己的每一輪收斂都在用它。

🔴 **裁定後又現形一次（2026-08-05，R3 收斂）**：主委在 R3 群集表**引錯三個 ID**
（`COMPOSER-R3-P1-02`／`P2-01`／`P2-02` 被誤寫成 `P0-02`／`P1-04`／`P2-01`，其中 `P2-02` 完全未被引用），
`completeness_check --lock` **全程 rc=0**，由主委自建的逐 ID 自檢抓到。**同型錯誤本 session 第 4 次。**

🔴 **具名殘留：產出端修法只能擋「漏」，擋不了「錯位」**（2026-08-05 R3 戳記輪實證）
主委修好「漏引 ID」後，緊接著把 `COMPOSER-R3-P1-01`（E-10 門檻）與 `COMPOSER-R3-P1-02`（1b 語料）
**在兩個群集列之間對調**。此時：
- `completeness_check --lock` **rc=0**（兩個 ID 都在檔案裡）
- 主委自建的逐 ID 自檢 **也通過**（兩個 ID 都在群集段裡，只是掛錯列）
- **`B-36` 提議的產出端修法（骨架預列 ID）同樣無感**——ID 是預列的，錯的是「哪一列配哪個主張」
⇒ **「ID 錯位」目前沒有任何機械防線**，只有委員的語意複核抓得到
（本次 codex／composer／grok **三家各自獨立**指出同一處而全數拒章）。
**此殘留須隨本票併入 `B-13` 時一併記載，勿因「產出端已修」而視為全解。**

**2026-08-05 開票，未實作。已裁定併入 `票 B-13`、修法在產出端（僅擋「漏」，「錯位」為具名殘留）。**
本批權宜作法：主委在收斂後加一道**人工自檢**（逐 ID grep 群集段），本輪已跑 17/17 全在。
🔴 **人工自檢不算解決**——正是使用者定死「不准靠紀律和記憶」所指的那種作法。

---

## B-35 票 `GOV-OUTPUT-TRUNCATION-ORACLE`

**沒有任何機制能判斷委員產出是否「寫完整了」——只能判斷「格式合不合規」。
一份中途被截斷、但恰好最後一條 finding 格式完整的檔案，會通過所有現有檢查。**

**開票依據**：第 0 批 SPEC 審查 `CODEX-R2-P0-01`（BLOCKING）＋ R1 `CODEX-R1-P0-04`／`GROK-R1-P1-01`。
**本批明文不受理**（見 `handoffs/reconcile/20260805-govb0-spec-r2/synth.md` 的 `E-SCOPE`），理由與殘留如下。

### 碼證

`scripts/completeness_check.sh:1459-1472` 的 `--single` 只驗 canonical ID、同檔重複 ID、finding body、
P0/P1 digest；**不驗** producer 是否正常結束、EOF／terminal marker、預期 finding 數、attempt identity。
codex R1 實跑：把真實 handoff 截成 6 行、保留一個完整 finding body ⇒ `COMPLETENESS PASS(single)`、`CHECK_RC=0`。

### 為何本批不受理（不是不重要，是邊界問題）

1. 可靠的截斷偵測需要**委員端在寫檔時產生 expected manifest**（預期 finding 數／record count／byte digest），
   **跨越第 0 批的元件邊界**（第 0 批只改 harness 端）。
2. `票 B-14` 的原始病是「**寫完了但不退出**」。第 0 批的 attempt-scoped publish 已解掉
   stale `<out>` 誤判、委員覆蓋自產（`B-30`）、未完成即上架三種失效模式；**截斷是第四種，且至今未曾實際致害**。
3. 依使用者定死「沒 100% 解就做 95% 那版現在收，殘留具名記錄」。

### 修法方向（未定案）

- ① 委員端在 prompt 中被要求先宣告預期 finding 數，harness 交件時比對；
- ② producer 寫完後產生 sidecar（byte count ＋ sha256），publish 前比對；
- ③ 以 `STATUS: DONE` 之類的終止標記為必要條件（**現行部分委員已自發輸出，但無強制**）。
  🔴 ③最便宜但可被截斷後偽造（若 `STATUS: DONE` 恰好在保留段內），須與 ①②併用。

### 與既有票的關係

- **`B-14`**：本票是其未解殘留；`B-14` 票面須標「**截斷偵測未解，見 B-35**」。
- **`B-31`**（format-failed 無便宜修正路徑）：同族——交件品質判定的粒度不足。

### 狀態

**2026-08-05 開票，未實作。第 0 批明文不受理，排 `B-14` 完工後。**

---

## B-34 票 `GOV-STAMP-ROSTER-VS-ROLEGATE`

**角色閘把 implementer 排除在 review 之外，戳記檢查卻要求「全部 review_families」蓋章
⇒ 任何 review 輪的收斂檔，結構上都不可能由「實際參與者」蓋滿。**

### 碼證（2026-08-05 實測，`GOVB0-SPEC-R1` 現場）

- `scripts/governance_families.json`：`review_families = ["codex","composer","grok"]`
- `scripts/governance_roles.json`：`implementer = "grok"`；`_rules.review` ＝「目標家族**不得**是 implementer」
- ⇒ `bash scripts/committee_run.sh … codex,composer,grok -- …`（`brief-kind: review`）**被角色閘整批拒派**：
  `ERROR: grok 是現行 implementer,不得擔任 code review(實作者不自審)`
- 改派 `codex,composer` 成功，收斂檔 `handoffs/reconcile/20260804-govb0-spec-r1/synth.md` 完成（19/19，rc=0）
- 但 `bash scripts/reconcile_stamps_check.sh <該檔>` 要求**三家**：
  `· codex: 缺 APPROVED 戳記` `· grok: 缺 APPROVED 戳記`
- ⇒ **grok 必須為一份它從未參與審查的收斂檔蓋章。**

### 🔴 第二次現場發作（2026-08-06，`GOVB39-B2-REVIEW-R1`）

與上述形態**逐點相同**，證實「必然而非偶發」：

- 依 ORCH §1 現行分工派 `codex,composer` 做 code review（`brief-kind: review`）⇒ 角色閘放行、兩家完成
- 收斂檔 `handoffs/reconcile/20260806-govb39-b2-review-r1/synth.md` 完成
  （6 findings 歸 3 群集，`reconcile_cluster_attribution_check.sh` rc=0）
- 兩家 append `APPROVED` 後 `bash scripts/reconcile_stamps_check.sh <該檔>` → **rc=1**：
  `· grok: 缺 APPROVED 戳記`
- ⇒ 主委被迫補派 `20260806-GOVB39-B2-STAMP-R2` 單獨向 grok 求一個**它未參與該輪審查**的戳記。

**累計現場發作：2 次**（2026-08-05 `GOVB0-SPEC-R1`／2026-08-06 `GOVB39-B2-REVIEW-R1`）。
**每次成本＝額外一輪派工**（開債／派工／戳記／銷帳），且該輪產出的戳記**語意為空**。

⇒ 依使用者 2026-08-06 淨摩擦判準：新增每次成本＝1 輪派工 × 每個 review 輪；
省下的重工＝0（它不防任何錯誤）⇒ **淨摩擦為正**，屬應優先修掉的那類。

### 為何是制度缺陷而非操作失誤

1. `implementer` 恆為 `review_families` 的成員（現行 SoT 即如此），所以**這不是偶發組合，是必然**。
2. 戳記的語意是「**我確認我的 findings 被忠實歸戶**」（見 `templates/` 與既有 stamp brief 慣例）。
   非參與者沒有 findings 可確認 ⇒ 它的戳記**語意為空**，只是形式蓋章。
   這與「機器強制」的初衷相反：閘門仍在，但被迫產出無意義的簽核。
3. 替代解讀（「第三方獨立複核」）也說不通：若真要第三方複核，
   brief 內容應為「複核歸戶正確性」而非「確認你自己的 findings」，兩者驗收條件不同。

### 修法方向（未定案，**嚴重度待委員裁定**）

- ① `reconcile_stamps_check.sh` 的必要 roster 改為**該輪的實際參與者**（從 audit 的
  `committee_round_open.participants` 取，而非 `review_families` 全集）；
- ② 或角色閘對 `brief-kind: review` 放寬為「implementer 不得審**自己實作的產出**」，
  而 SPEC 審查階段尚無實作 ⇒ 不構成自審（**此解需要區分 SPEC review 與 code review，現行 kind 不分**）；
- ③ 或新增 `brief-kind: spec-review`，與 `code-review` 分離。
  🔴 ①最小；②③觸及角色語意，須雙家族專審。

### 與既有票的關係

- **`B-31`（format-failed 無便宜修正路徑）**：同族——角色/kind 分類過粗導致無路可走。
- **`B-21`（哪份檔案由哪支檢查器把關）**：本票是「兩支檢查器對同一件事有不同 roster 定義」的實例。

### 狀態

**2026-08-05 開票，未實作。嚴重度與修法待委員裁定**（已列入第 0 批 SPEC R2 審查輪的必答題）。
權宜作法：`brief-kind: stamp` 不受角色限制，故補派 grok 單獨蓋章可通過機檢，但語意問題仍在。

---

## B-37 票 `GOV-FRICTION-TALLY-BY-TICKET`

**票的優先順序目前**沒有任何量化依據**——「哪張票最常咬人」只能靠主委人工計數，
而人工計數本身違反使用者定死的「工具必須自帶強制機制，不准靠紀律和記憶」。**

### 使用者原話（2026-08-05）

> 「是不是弄一欄統計，當你撞到問題，就直接看是哪一票，然看你怎麼做去統計發生的次數，
> 累積起來，這樣我們可以改變優先度的先後順序」

### 碼證（2026-08-05 實測，主委實跑）

- `LC_ALL=C grep -ao '"event": *"[^"]*"' .claude/gate/audit.log | sort | uniq -c`
  → `committee_dispatch 1340`／`committee_output 677`／`gate_deny 649`／`committee_family_result 337`／
  `committee_round_open 184`／`debt_abandon 147`／`committee_debt_clear 36`
- `LC_ALL=C grep -ao '"reason": *"[^"]*"' .claude/gate/audit.log | sort | uniq -c | sort -rn`
  → `gate_deny` 的 reason **只有兩種機器值**：`token_expired 514`／`open_debt 135`。
  其餘長文 reason 皆屬 `debt_abandon`，非 gate_deny。
- ⇒ **`gate_deny` 無指令欄位、無票號欄位**（與 `docs/GOVB0_FRICTION_SPEC.md` §A 的 FACT-RECEIPT 一致）。

### 為何現在做不了：資料源不存在

本 session 主委宣稱「`票 B-15` 咬 9 次」——該數字**無法從 `audit.log` 導出**，是人工目視計數。
⇒ 若以此排序，**排序依據本身建立在不可稽核的人工計數上**，等同無依據。

### 硬前置

**第 0 批 Phase 0（可觀測性）** —— 該 Phase 正是要為 `gate_deny` 補判定來源與指令欄位。
本票**必須排在 Phase 0 定案之後**，否則統計無資料源。**不需插隊，天然接續。**

### 修法方向（未定案）

- ① **票 ↔ 事件簽章對照表**（機器可讀 SoT），將 Phase 0 新增的 `gate_deny` 欄位映射到票號；
- ② `scripts/friction_tally.sh` 由 `.claude/gate/audit.log` ＋ `.claude/gate/ts_stamp.log.slow`
  導出「每票撞擊次數 ／ 時間窗」；
- ③ **強制機制**（回答「怎麼被強制執行」）：撞擊次數**不手寫進**白話總覽／backlog——
  本 session 計數已漂 8 次。二選一：(i) 文件只放導出命令，數字隨時導出；
  (ii) 數字寫入文件但 pre-commit 校驗「文件內數字 == 腳本輸出」，手改即擋。

### 🔴 已知副作用（排序設計時必須處理）

純以撞擊次數排序會**系統性偏袒高頻低痛的票**，壓掉**低頻高痛**的（如資料正確性類：
一年咬一次，但那一次是災難）。
⇒ 撞擊次數應為排序的**一個輸入**，非唯一依據。可行解：撞擊次數 × 單次代價，
或限制高頻票**只能在同風險級距內**往前插。**此設計選擇須委員裁定。**

### 與既有票的關係

- **`B-17`（四張機器依賴的表全是手寫）**：同族——手寫數字必漂，本票的③即該病的具體修法。
- **`B-22`（派工後沒人監看）**：同一資料源（audit 事件流），可共用導出層。
- **P1-6 線 C（債務事件分檔）**：本票要掃全份 `audit.log`；線 C 完成後帳本更乾淨，掃描更可信。

### 狀態

**2026-08-05 開票，未實作。** 硬前置＝第 0 批 Phase 0。
排期：**Phase 0 定案後**（即第 0 批完工前後），優先於第 1 批。

---

## B-38 票 `GOV-ZERO-FINDINGS-BLOCKS-CLOSURE`

**委員合法回報「0 findings」時，`completeness_check` 抽不到 heading ID ⇒ 判 WARN 並使整體 FAIL
⇒ 該輪正規銷帳結構上不可達，只能走 `--abandon` 逃生口。**

### 碼證（2026-08-05 實測，`GOVB0-SPEC-R6`）

```
[reconcile_build] synth.md 已建；每檔抽到 findings：
    20260805-govb0-spec-r6-codex.md: 3
    20260805-govb0-spec-r6-composer.md: 0
COMPLETENESS PASS: …-codex.md — 3/3 個 ID 全在綜合檔。
COMPLETENESS WARN: …-composer.md 抽不到任何 heading ID(來源未用 ## <ID>?) → 本腳本無法保護,須人工/覆議
COMPLETENESS FAIL: 完整性檢查未過(…)。補齊後重跑。
[reconcile_build] completeness rc=1
```

composer 的報告**格式完全合規**，判定為「兩項皆 CLOSED、可進 TODO 生成」——
**「沒有 finding」正是它的結論**，不是缺漏。

### 🔴 第二次現場發作（2026-08-07 `GOVB19-X-CONSULT-R1`）——**優先序決定性證據**

**這次是被 `票 B-31` 的修法直接誘發出來的，形態比第一次更明確**：

1. 2026-08-06 `票 B-31` 落地，在 `cx_run.sh` prompt 加入
   「若結論確為 0 finding，請明確寫出並保留完整推理，**勿為湊數捏造 finding**」。
2. 本輪 composer 的產出第 171 行即為 `## 本輪 0 findings — 推理保留`
   ⇒ **委員完全照做，誠實回報而非捏造**。
3. `bash scripts/completeness_check.sh --single <該檔> --family composer` → **rc=0（PASS）**
4. `bash scripts/reconcile_build.sh …` → `COMPLETENESS WARN: 抽不到任何 heading ID` ＋
   `COMPLETENESS FAIL` ⇒ **rc=1，收斂無法建立，該輪只能 abandon**。

⇒ **制度在同一輪內自相矛盾**：一支檢查說「0 findings 合法」，另一支說「0 findings 即失敗」。
⇒ **誠實回報反而受罰**：若 composer 當時捏造一條 finding，本輪就能正規收斂。
   `票 B-31` 的警告擋住了捏造，但**沒有給誠實者出路**。

**這在 B-31 的 code review 中已被預言**〔`CODEX-R1-P1-01`，2026-08-06〕：
「自檢假綠，收斂時才失敗」——**24 小時內原樣重現**。

**累計現場發作：2 次**（08-05 `GOVB0-SPEC-R6`／08-07 `GOVB19-X-CONSULT-R1`），
且第二次**擋住了另一張票（`B-19`）的裁定收斂**。

⇒ 🔴 **優先序：本票應排在第 1 批之首。** 依淨摩擦判準：
它每次發作都強制一輪 abandon（該輪產出無法正規銷帳），且**與 `B-31` 的誠實性要求直接衝突**
——不修它，`B-31` 的警告等於把委員推進「誠實則卡住、捏造則通過」的兩難。

### 🟡 2026-08-07 部分完成：sentinel 出路已通，**核心殘留未解，本票維持 OPEN**

**修法（檢查器零改動）**：`cx_run.sh` prompt 改為要求 0 findings 時寫
`## <家族>-R<輪次>-P3-00` sentinel（body 照常填三欄），取代原散文版。
`P3-00` 是合法 canonical ID ⇒ 抽得到 ⇒ 不觸發 vacuous；空殼仍被 body validator 擋。

**實跑**：實質 sentinel 收斂 rc=0 ／ 空殼 rc=1 ／ 散文版反向對照 rc=1 ／
`pytest tests/governance -q` → **795 passed**（改動前 789）。
測試：`tests/governance/test_zero_findings_sentinel.py`（6 tests）。
收斂：`handoffs/reconcile/20260807-govb38-b1-review-r1/synth.md`（6 findings → 3 群集）。

🔴 **本票不得宣稱關閉——核心殘留**〔`CODEX-R1-P1-02`〕：
修法只在**委員照做時**有效。未讀 prompt／prompt 截斷／模型未遵循 ⇒
`cx_run` 交件層仍接受 prose-only（`--single` 對 0 canonical ID 直接 PASS）
⇒ 病只是從「主委忘記寫」變成「委員沒有遵循」。
**修補需先解「如何機械識別應有 findings 的產出」**——主委初測「對 0-ID 產出改判 FAIL」
影響 **1073/1418** 檔（76%），但樣本含 `impl`／`stamp`／runlog（本無 canonical ID）
⇒ **誤擋率未證，不得逕行改判**。

🔴 **主委測試假綠（codex mutation 證明，已修）**：原 `test_hollow_sentinel_rejected`
的 hollow source 與 synth body 不同，**實際由 body-hash 不一致擋下**；
把 source validator 改成 `if false` 後該測試**仍 passed**。
已修為 body 逐字相同＋新增 `test_hollow_rejection_is_not_body_hash_artifact`
斷言 stderr 須含 `empty-shell`。

**其他具名殘留**：語意空洞 sentinel 可過（四入口全 rc=0，屬舊病換型非本修法引入）；
sentinel 計入 union 分母（`票 B-37` 統計須扣除）；契約未進 `templates/`。

### 🔴🔴 2026-08-07 SCOPE 降級（`GOVB1-RECON-R1` 收斂 G-3，三家 APPROVED）

TICKET-STATUS: PARTIAL

**核心殘留的既定修法方向「0-canonical-ID ⇒ FAIL」被行為表契約否決，本批不做改判。**

**碼證（主委獨立發現，三家複驗成立；codex 實跑 `pytest tests/governance/test_completeness_idlike_fp.py -q` → `30 passed`）**：
- `tests/governance/test_completeness_idlike_fp.py:102-105` 的 probe 檔**只寫一行 heading**；
- `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md:141,154,155,159,160,161,162,163` 共 **8 列期望 `rc==0`**；
- ⇒ 該 8 列的 probe **canonical ID 數必為 0** ⇒ 「0-ID ⇒ FAIL」會使 8 個參數化用例**同時轉紅**。
- 這也解釋主委先前初測「影響 1073/1418 檔」為何樣本不純：`--single` 的呼叫方含測試探針。

**第 1 批交付物（降級後）**：只產出「**findings-kind 產出的機械分類判準**」＋誤擋率 receipt
（見 `docs/GOVB1_INPUT_QUALITY_SPEC.md` Task 4.1）。**改判本身另立後續票。**

🔴 **禁令形態（`CODEX-R2-P0-02` 修正）**：SPEC 中的禁令**必須寫成行為禁令而非路徑禁令**——
「不得在 `--single` 加 0-ID⇒FAIL」擋不住實作端改在 `--lock`／`cx_run` 重寫等效邏輯。
現行條文＝「禁止任何使該 8 列 rc 由 0 變非 0 的改動，不論實作於哪一層」＋
`git diff --stat tests/governance/test_completeness_idlike_fp.py` 須為空。

---

### 🔴 開工前偵察發現：本票與 `GOV-NOFINDINGS-SENTINEL` 是同一件事的兩面（2026-08-07）

**不得各自實作**——否則會造出第四種「0 findings」表達方式。

| 票 | 管什麼 | 狀態 |
|---|---|---|
| **B-38**（本票） | 0 findings **無法正規銷帳**（收斂端） | OPEN |
| `GOV-NOFINDINGS-SENTINEL` | sentinel 機制**存在但未被機器驗證**（`completeness` 接受空殼 `P3-00`，codex 四行 probe 實證 `DIRECT_RC=0`） | OPEN（見本檔 `:155`、`:612`） |

**實測現況**：`grep -rn 'P3-00' templates/ scripts/` → **命中 0**
⇒ sentinel 慣例**只寫在個別 brief 裡靠主委每次手寫**，未進模板、無機器強制。

🔴 **主委已製造第三種格式（2026-08-06，`票 B-31`）**：
`cx_run.sh` 的 prompt 現在教委員寫「本輪 0 findings」，**與既有 `P3-00` sentinel 慣例不一致**。
今日 composer 照著寫了 `## 本輪 0 findings — 推理保留` ⇒ 收斂端不認得。

**現存三種「0 findings」表達**：
1. `P3-00` sentinel（舊慣例，手寫在 brief，未機器強制）
2. 「本輪 0 findings」散文（主委 2026-08-06 寫進 prompt 模板）
3. 什麼都不寫（多數情況）⇒ 直接 vacuous FAIL

⇒ **本票的修法須先統一表達方式，再談收斂端如何接受**。
建議 scope：**B-38 ＋ `GOV-NOFINDINGS-SENTINEL` 合併為單一票**，一併定契約（欄位／位置／驗證方式），
並同步修 `cx_run.sh` prompt 與 `templates/`。
🔴 **同時檢查是否連帶解 `票 B-35`**（報告截斷偵測）——若契約含「宣告 findings 數」，
宣告值與實際抽出數不符即可偵測截斷，兩票可能一併關閉。

⚠️ **既有測試契約**：`tests/governance/test_completeness_oracles.py:603`
`assert cov["union_size"] > 0, "union 空 → vacuous 守衛，不算 PASS"`
⇒ 修法**必然撞到這條**，須在設計階段決定如何處置（不得逕行改斷言）。

### 為何是制度缺陷

1. 檢查器把「抽不到 ID」一律當**可疑**（原意是防「委員沒用 canonical 格式」），
   但**無法區分**「格式錯誤導致抽不到」與「真的沒有 findings」。
2. 後果不對稱：**愈是乾淨的審查輪（全部通過、零 finding）愈無法正規銷帳**，
   反而必須用逃生口 ⇒ 直接推高 `--abandon` 比率（現況 182 輪中 146 輪 ABANDONED）。
3. 與 `票 B-24`「驗收＝狀態不是 rc」同族：狀態「0 findings」是**合法終局狀態**，卻無對應處理路徑。

### 修法方向（未定案）

- ① 委員報告增一個**明示欄位**（如 `FINDINGS_COUNT: 0`）；
  `completeness_check` 見此欄即視為**合法零 findings**，PASS；缺此欄才維持 WARN/FAIL。
  🔴 此解最小且**可證偽**：委員必須主動宣告，無法靠「剛好抽不到」矇混。
- ② 或由 `reconcile_build` 在 roster 內某家 0 findings 時要求主委具名確認，寫入 audit。
- ③ 反對「直接把 WARN 降級為 PASS」——那會讓真正的格式錯誤靜默通過（與 `票 B-31` ④ 同型張力）。

### 與既有票的關係

- **`B-31`**（format-failed 無便宜修正路徑）：同族，皆為「委員產出生命週期未完整建模」。
- **`B-35`**（截斷 oracle）：①的 `FINDINGS_COUNT` 宣告**同時也是截斷偵測的材料**（宣告數 vs 實際數）。
  🔴 **兩票應合併評估**——同一個欄位可同時解兩題。
- **P1-6 線 C**：本票直接推高 ABANDONED 比率，是帳本髒污的來源之一。

### 狀態

**2026-08-05 開票，未實作。** 排期建議：與 `B-31`／`B-35` 同批（第 1 批）。
🔴 本日已因此走一次 `--abandon`（round `002839f3`），理由已具名載入 audit。

---

## 📌 `票 B-24` 的拆分裁決（2026-08-04，SPEC 審查 R1 後）

`B-24` 原修法欄寫「併入各票驗收欄，不另建檢查器」。R1 偵察三家一致判定**不滿足使用者定死
「工具必須自帶強制機制」**（`CODEX-R1-P0-03`／`GROK-R1-P1-02`）。
但 SPEC 審查 R1 兩家對「機械強制要多大」分歧：
codex 判**須獨立 pipeline**（`CODEX-R1-P0-01`：跨文件 enforcement，缺 scope manifest／owner／到期行為）；
composer 判**現行限縮足以交付**（`COMPOSER-R1-P1-02`／`P1-04`）。

**主委裁：SPLIT**（依據＝使用者定死「95% 解法就收」＋膨脹升級 5 訊號）。

| 面向 | 歸屬 | 內容 |
|---|---|---|
| **紀律面** | **留第 0 批** | 本批 SPEC／TODO 的每個驗收欄一律寫狀態斷言，**零新增元件**。已落實於 `docs/GOVB0_FRICTION_SPEC.md` §V。 |
| **機械強制面** | **移出，獨立排期** | `scripts/acceptance_state_check.sh`＋grandfather SoT＋**具名 owner／UTC 到期日／到期後 fail-closed 行為**＋新/改文件的機械判定來源。 |

⇒ `B-24` 狀態＝**部分完成**（紀律面隨第 0 批交付；機械強制面待獨立批次）。
兩家共識的 grandfather 三要件（owner／UTC expiry／到期後狀態）**已記於此，不隨拆分遺失**。

---

## 📌 同輪另兩次摩擦（已有票，此處只記為新證據，不重複開票）

| 摩擦 | 歸屬 |
|---|---|
| 主委 commit 訊息含 `; codex closure review` 被 gate 擋（本 session 第 3 次） | `B-15` |
| **composer 執行自己的探針時被 `gate_check` 反覆卡住**（委員自述於 runlog） | `B-15` — **首次證實此洞會咬委員，不只咬主委**，代價是該家族兩個背景探針失敗 |

---

## B-39 票 `GOV-IDLIKE-HEADING-FALSE-POSITIVE`

**`completeness_check.sh` 的 finding-ID 通道把「長得像 ID 的合法子標題」判為非法，
使**格式正確**的委員報告整份作廢；本日已因此作廢 3 輪。**

### 開票依據（2026-08-06 全票重裁，兩家獨立列為「無票但高頻」）

- `CODEX-R21-P0-01` [BLOCKING]：現行委員輪的硬阻塞，**且不是委員措辭錯**。
- `GROK-R21-P0-01` [BLOCKING]：**修正主委的過寬診斷**——不是「凡 `###` 必 fail」。

### 🔴 根因（grok 三探針實測，主委原診斷過寬）

| 探針 | rc | 說明 |
|---|---|---|
| `### G-1 extra` | **1** | id-like（大寫＋連字號＋數字）⇒ 進 finding 通道 ⇒ 非 canonical ⇒ hard-fail |
| `### 另外要回答的` | **0** | 中文子標題 ⇒ 正常通過 |

⇒ **根因＝id-like 判定過寬**，非「`###` 一律拒收」。
🔴 **本票不得寫成「禁 `###`」**——那是把摩擦轉嫁給每位委員與每份 brief 卻不修根因
（主委已犯此錯，見 `20260806-govamend-x-consult-r1/synth.md` 具名記錄）。

### 實證（可重跑）

| # | 事件 | 查法 |
|---|---|---|
| 1 | `GOVB35-SPEC-REVIEW` composer `## OUT-OF-SCOPE` | `grep -c 'invalid finding ID' <該輪 runlog>` |
| 2 | `GOVB35-SPEC-REVIEW2` composer `### OUT-OF-SCOPE`（**照主委 brief 指示寫的**） | `grep -n '927b9f79' .claude/gate/audit.log` |
| 3 | `GATELEX-REDESIGN` 三家皆用 brief 小節代號作 `##` | 該輪 runlog |

⇒ **3 輪作廢**。事件 2 尤其重要：委員**照指示做**仍被判違規。

### 依使用者判準的取捨（2026-08-06）

| 問 | 答 |
|---|---|
| 擋哪類 agent 失誤 | **合法報告被判違規 → 整輪作廢**（重跑成本＝一輪三家） |
| 實證次數 | **3**（本日；皆可由 audit／runlog 定位） |
| 新增摩擦 | **零** —— 修的是檢查器自身的判定，委員與 brief 都不必多做事 |
| 摩擦 < 收益？ | ✅ 顯著 |
| forward-only？ | ✅ 只改判定，不動任何既有產出 |
| 會否製造新失誤面 | ⚠️ **會**——放寬後可能漏收真正畸形的 canonical-like heading ⇒ 見驗收 |

### 修法方向（兩家一致）

1. **結構標題 allowlist**：`Verdict`／`§0 前提宣告`／`逐項核對表`／`出場判準核算`／表名等
   一律不進 finding 通道。
2. **只有 canonical 或「近似 canonical 的畸形」**才進 finding 通道並受 schema 檢驗。
3. **`###` 及以下預設為結構標題**，除非本身即 canonical 形式。

### 🔴 驗收（缺一不可）

| # | 待驗項目 | 期望 |
|---|---|---|
| 1 | `### 另外要回答的`（中文子標題） | rc=**0** |
| 2 | `### 逐項核對表`（結構標題） | rc=**0** |
| 3 | `## CODEX-R99-P1-01`（合法 canonical） | rc=**0** |
| 4 | `## CODEX-R99-P9-01`（**畸形 canonical-like**） | rc≠0 —— **放寬不得漏收這類** |
| 5 | `## OUT-OF-SCOPE` 作 h2 | 由委員裁定：仍拒或改列結構標題 |
| 6 | **mutation** | 移除修法後，項目 1／2 須轉紅（證明修法真的起作用） |

### 狀態

⬜ **OPEN**。2026-08-06 開票，依全票重裁裁定為**當前阻塞鏈之首**。
與 `B-38`（零 findings 無法銷帳）同屬「合法產出被判失敗」族，可一併評估但**不合併**
（根因不同：本票是 heading 判定，`B-38` 是 vacuous 判定）。

---

## B-40 票 `GOV-USER-ATTRIBUTION-UNVERIFIED`

**治理文件中「使用者定／使用者原話／依使用者裁定」的宣稱，
目前沒有任何機制驗證它是否真有對應的使用者發言。
⇒ 主委自行加碼的規則可掛使用者名下，成為不可動搖的偽憲法。**

### 開票依據（2026-08-06 實證）

主委在 `docs/GOVB39_IDLIKE_HEADING_SPEC.md` 初版 §C 寫：

```
| C-5 | 摩擦增量須為 **0**——委員與 brief 都不得因本修法多做任何事 | 使用者 2026-08-06 判準 |
```

- **使用者從未說過此話。**
- 該約束**與使用者已定死的「工具必須自帶強制機制，不准靠紀律和記憶」直接衝突**
  ——若生效會擋掉本 epic 幾乎全部工作（任何新增機械檢查都會使摩擦增量 > 0）。
- **被發現純屬偶然**：主委在對話中恰好把該條逐字唸出，使用者才抓到。

使用者原話：

> 「**但我也是看你寫出來在這裡的句子，其他你沒寫的我也不知道**」

⇒ 使用者的稽核面**僅限主委主動寫出的內容**；未寫出者結構上不可見。

### 依判準的取捨

| 問 | 答 |
|---|---|
| 擋哪類 agent 失誤 | **主委自造規則冒充使用者裁定** → 進入凍結文件後被當憲法引用 |
| 實證次數 | **1**（2026-08-06，且該次為偶然發現） |
| 新增每次成本 | 一次正則掃描（與既有 `doc_format_precheck` 同一趟） |
| 省下的 | **偽憲法一旦生效，後續每一張票都受其約束**——本例會擋掉整個 epic |
| 淨摩擦 | **負**（合法引用本來就會附逐字原話，不必多做事） |
| forward-only | ✅ 只掃新寫／改到的文件 |
| 會否製造新失誤面 | ⚠️ 會——若規則太嚴，正當的「使用者曾口頭確認但未逐字記錄」會被擋 ⇒ 須設逃生口並記錄 |

### 修法方向（未定案）

治理文件中出現歸屬關鍵字（`使用者定`／`使用者原話`／`使用者要求`／`依使用者裁定` 等）時，
**同一段落內須有 `>` 開頭的逐字引用區塊**；無引用者 → 檢查器拒收。

### 🔴 誠實邊界（開票時即載明）

1. **只擋「沒附引用」，不擋「引用是假的」**——主委仍可貼一段捏造的引文。
   屬「擋意外不防蓄意」，與本 repo 既有檢查器同一等級。
2. **只在主委「寫出來」時生效**。若主委未寫入文件而**直接依錯誤信念行動**，
   本檢查完全無感——這是使用者原話所指的結構性盲區，**本票不聲稱解決它**。

### 狀態

🗑 **不做（2026-08-06 使用者當日裁定，開票後隨即收掉）**。

使用者原話：

> 「**B-40 先算了，感覺這樣票永遠開不完，除非你有一勞永逸的解決方式。**」

**裁定理由**：本票是「為單一漏洞開一張票」的典型——而它擋不到的那個結構性盲區
（主委未寫出即行動）本票自己也承認無解。**逐洞開票會讓 backlog 無限成長，
本身即違反淨摩擦判準。**

**保留本票內文的理由**：2026-08-06 的事故（主委自造規則掛使用者名下）是實證，
供後續若有「一勞永逸」方案時引用。**但不列入任何執行序。**

⇒ **通則取代**：見本檔「所有票的共同判準」節新增的**淨摩擦必填欄**——
與其為每種偽造開一張票，不如讓**每張票與每個 Task 都必須算出淨摩擦**，
算不出來或為正者不得進執行序。

### 🔗 2026-08-06 後續：已由 `票 B-16` 擴充 C 吸收

使用者追問「『驗了 A 就當作 B 也成立』有辦法根治嗎？有在哪一票裡嗎？」
主委逐張對回 40 票後確認：該病族被切成三塊，`B-29`（程式行為域）與 `B-16` 擴充 A（文件斷言域）已有票，
**「驗了子集就宣稱全集」無票**——而本票（B-40）正是該子型的一個實例
（宣稱「使用者定」，實際涵蓋範圍為零）。

⇒ 使用者裁定合併：**`票 B-16` 新增擴充 C「宣稱的量詞範圍 > 實際驗證的覆蓋範圍」**，
本票不復活、不列入執行序；**其事故內文（§開票依據）作為擴充 C 事故表第 7 列的來源保留**。

**本票狀態維持 🗑 不做**，但 `B-16` 擴充 C 落地後，本票所描述的偽憲法場景將被
`COVERAGE:` 欄要求間接涵蓋（宣稱「使用者定」須宣告來源涵蓋範圍）。
🔴 **不得因此宣稱「B-40 已解決」**——擴充 C 擋的是**範圍宣稱**，
不擋「附了一段捏造引文」（見上方誠實邊界第 1 條，該邊界原封有效）。

---

## B-41 票 `GOV-ROLE-ASSIGNMENT-NO-ENFORCEMENT`

**分工規則（誰起草、誰審查、審幾家）零機械強制，且同一事實在同一份文件有三處副本。**

TICKET-STATUS: OPEN

### 事故（2026-08-07，實測，由**使用者**發現）

主委將 `docs/GOVB1_INPUT_QUALITY_TODO.md` 的生成**派給 grok**，違反兩條明文規則：

| 違反 | 出處（逐字） |
|---|---|
| TODO 須主委起草 | `docs/MULTI_AGENT_ORCHESTRATION.md:61`「**SPEC/TODO 初稿＝Claude 主委一律起草**」 |
| 交執行端僅限額度 fallback | 同檔 `:190`「**TODO 預設 Opus 寫**（深度只能 Opus）；**交執行端生成僅 Opus 額度吃緊時 fallback，且須配 Opus adversarial 抓淺**」——主委無額度問題 |
| 對抗審須三家 | `:61`「SPEC/TODO 對抗審維持**三家** codex+composer+grok——起草後審查**不得漏 grok** 鐵律不變」 |

**連帶後果**：grok 起草即成實作者 ⇒ 依「實作者不自審」，對抗審**由三家降為兩家**
⇒ **主委的違規動作自己砍掉了一個審查家族**。

### 🔴 根因（非「忘記」，是文件結構）

主委**派工前確實查了** ORCH §1，指令為
`grep -n "現行分工\|中/大實作\|code review" docs/MULTI_AGENT_ORCHESTRATION.md`，
命中 `:32-34` 的**表格三列**——該表只寫「執行端（實作）＝`cursor-agent`/`codex exec` 等」，
**未含「SPEC/TODO 初稿一律主委起草」這句**。

⇒ **同一事實在同一份文件有三處表述，強弱不一**：

| 位置 | 內容 | 強度 |
|---|---|---|
| `:32-34` 表格 | 「執行端（實作）＝…」＋「依本節 §1 現行分工行」 | **弱**（指向他處，自身不含規則） |
| `:61` 現行分工行 | 完整規則（起草者／實作者／審查家數） | **強** |
| `:190` TODO 專條 | TODO 專屬規則＋fallback 條件 | **強** |

主委讀到最弱的那處並據以行動。**這是 `票 B-25`（同一事實多份副本）在單一檔案內的形態。**

### 🔴 為何嚴重度高於一般 B-25 實例

**本次無任何機制攔截**：`gate.sh dispatch` 放行、`doc_format_precheck` rc=0、
`verification_claim_check` rc=0、`session_name_check` rc=0。**由使用者發現。**
⇒ 分工規則**目前完全靠主委記得看對地方**，違反使用者 2026-08-02 定死的治理三原則第 3 條
「寫出來的工具就是要有強制使用機制，不准靠紀律和記憶」。

### 修法（兩段，皆機械可驗）

**① 機械強制（便宜，可立即做）**
`scripts/gate.sh dispatch`：若 `brief-kind=impl` 且 brief 或 `--intent` 指向產出
`docs/*SPEC*.md`／`docs/*TODO*.md` ⇒ **拒發 token**，訊息指向 `ORCH:61`／`:190`。
逃生口＝顯式旗標 `--drafting-fallback "<額度理由>"`，且該旗標**寫入 audit**。

**② 單一來源（治本，併 `票 B-25`）**
ORCH 的分工規則抽成資料檔（家族 × 角色 × 任務型別 → 誰起草／誰實作／審幾家），
`:32-34` 表格與 `:61`／`:190` 皆由該檔**生成**，禁手寫。
⇒ 主委無論 grep 到哪一處，讀到的都是同一份事實。

### 與既有票的關係（依 `B-19` 紀律，開票前盤點）

- **`票 B-25`（事實單一來源）**：本票的 ② 段即 `B-25` 的一個 fact-key（`role-assignment`）
  ⇒ **② 併入 `B-25`（第 1 批 2a）**；① 獨立且更便宜，可先做。
- **`票 B-29`（改判定程式須宣告差集）**：本票管**派工前的角色檢查**，不重疊。
- **`票 B-20`（票結案須指向真檢查）**：同族紀律，不重疊。

### 誠實邊界

- ①**擋不了**主委在 brief 內不寫產出路徑而規避偵測；屬「擋意外不防蓄意」。
- ②在 `票 B-25` 的生成器上線前無法實施。
- **本票不進第 1 批**（不在既定 8 項 scope 內）；① 建議排 `票 B-25` 同批交付，② 併入 `B-25`。

### 狀態

**2026-08-07 開票，未實作。** 排期：① 隨 `票 B-25`（第 1 批 2a）交付；② 併入 `B-25` 的 fact-key 集合。

---

## B-42 票 `GOV-TODO-GATE-GENERALIZE`

**把 GOVB1 的 TODO 專屬閘（複數）泛化為通用閘，但既有語料誤擋率使其不得直接上線。**

TICKET-STATUS: OPEN

🔴 **2026-08-07 範圍擴大（具名，非默默追加）**：本票原名 `GOV-TODO-DEPTH-CHECK-GENERALIZE`，
範圍只含 `govb1_selfcheck.sh` 之**五類 per-Task 深度檢查**。
當日新增第六類閘（**票↔Task 歸屬**，`govb1_single_source_check.sh --task`），
其泛化**受同一個誤擋障礙阻擋**（37/38 既有 TODO 無對應表）。

**主委原本直接把它追加在票尾而未動標題與範圍聲明**，使用者當場指出
「**你這只是不開新票，硬塞進有但不相關的 B-42？**」——**質疑成立**：
同類工作 ≠ 同一範圍，**默默擴大既有票 ＝ 用「沒開新票」掩蓋「悄悄擴權」**。
⇒ 改為**明文擴大範圍並改名**（`DEPTH-CHECK` → `GATE`），使票名與實際涵蓋一致。
**往後凡把新內容併入既有票，須同步檢查標題與範圍聲明是否仍成立。**

### 來源（2026-08-07，三家裁定 `U-7`）

收斂檔 `handoffs/reconcile/20260807-govb1-x-consult-r5/synth.md`。

`scripts/govb1_selfcheck.sh` 的五類 per-Task 檢查（偽碼 fence／修改欄函式名／檔案欄涵蓋／
placeholder／凍結分母）**在語意上是 TODO 通用的**，非 GOVB1 專屬。
主委原構想＝泛化後掛進 `scripts/doc_format_precheck.sh` 的 `kind=todo` 分支。

### 🔴 否決依據（grok 實測，本輪唯一的決定性量化數據）

> 五類 per-Task 檢查若**無條件**泛化進 `doc_format_precheck kind=todo`，
> 對既有語料**誤擋率 97.1%（33/34）**。

⇒ 違反 `票 B-23` 紀律（放寬/收緊類改動須附誤擋率 receipt）
⇒ **候選 A（掛 `doc_format_precheck`）三家一致否決**。

### 本批已做的（不在本票範圍）

`gate.sh:578-591` 新增 GOVB1 深度自檢閘，**以檔名精確匹配**
（`docs/GOVB1_INPUT_QUALITY_TODO.md`），誤擋率 0。
測試 `tests/governance/test_govb1_gate_selfcheck.py`（10 tests）釘死：
掛載存在、**非 glob**、mutation 自證（selfcheck 紅 ⇒ gate 拒發 token）。

### 本票要做的（**2026-08-07 由一項擴為兩項**）

1. **五類 per-Task 深度檢查** → 通用 `scripts/todo_depth_check.sh`（原範圍）
2. 🔴 **票↔Task 歸屬檢查** → 併入同一通用閘（**新增範圍，見票頭之範圍擴大聲明**）

### 硬前置（缺一不得動工）

1. **逐類判定通用化後的判準**——現行五類中，哪些對所有 TODO 都成立、哪些須放寬或改寫。
   誤擋 97.1% 表示**多數類別的現行判準對既有語料過嚴**。
2. **對全部既有 `docs/*TODO*.md` 產出誤擋率 receipt**，依 `票 B-23` 紀律：
   分母＝實際掃描檔數（現跑）；分子＝人工標註 false-positive；
   **n≥100 抽樣 ＋ Wilson 95% CI；報區間不報點估計；上界 ≤5% 方得上線**。
3. **先全量掃描定初始集合**（同 `票 B-23`／`票 B-25` 紀律），禁憑想像列舉判準。

### 誠實邊界

- 現行五類判準**是為單一份 TODO（GOVB1）調校的**，其通過率不可外推。
- 若逐類放寬後誤擋率仍不達標，**正解可能是「只泛化其中一到兩類」**而非全部。
  依「95% 解法就收・殘留具名記錄」，部分泛化亦為合格交付。

### 與既有票的關係（依 `B-19` 紀律，開票前盤點）

- **`票 B-16` 原條文**（機器依賴的契約不得長在散文）：本票是其**執行層工具**，同族不重疊。
- **`票 B-23`**（禁止清單反轉為允許清單）：本票**沿用其誤擋率 receipt 紀律**，非重疊。
- **`票 B-41`**（分工規則零機械強制）：同為「工具寫了但沒掛載」之族，但標的不同。
- **`票 B-13`**（同一語意兩個實作）：若泛化後與 `doc_format_precheck` 既有檢查重疊，須併入考量。

### 狀態

**2026-08-07 開票，未實作。** 排期：**不進第 1 批**（三家明文）；建議排 `票 B-16` 原條文（第 4 批）同批，
因兩者共用「TODO/SPEC 的機器判準」語意層。


### 🔴 2026-08-07 併入：票↔Task 歸屬閘之泛化（同樣受 97.1% 問題阻擋）

> 使用者當日質問：「**這次這樣解，之後換另一套任務時候又犯同樣問題？**」
> **答：會。** 本條記錄證據與已採之前向修法，**不另開票**。

**本批已做**：`scripts/govb1_single_source_check.sh --task N.M` ＋ `gate.sh` GOVB1 段掛載
⇒ 歸屬票為「未標註／待確認」之 Task **拒發 impl token**（雙向自證：`Task 2.1` 擋、`Task 0.1` 放）。

**為何不現在泛化**（與本票主體同因，**實查證據**）：
`ls docs/*TODO*.md | wc -l` → **38 份**，其中**具 `§0.1a` 對應表者：僅 GOVB1 一份**。
⇒ 改為 glob 掛載（`docs/GOV*_TODO.md` 或全部）**會立即擋掉其餘 37 份**，
與本票主體之 97.1% 誤擋同一形態。**故掛點維持檔名精確匹配。**

🔴 **已採之前向修法（不溯及既往，使用者 2026-08-05 定）**：
`templates/TODO_GENERATION_PROMPT.md` 之 Task 結構已改為
**標題必含 `票 B-NN`；不對應單一票者寫 `票 —` 並說明；禁留空、禁「未標註」**。
⇒ **往後新生成的 TODO 天生具備歸屬宣告**，舊 38 份不回頭改。
待新 TODO 累積到一定數量後，glob 泛化之誤擋率才可能降到可上線水準——
**該重測為本票之前置，不得在無 receipt 下泛化。**

---

## B-43 票 `GOV-TODO-PSEUDOCODE-UNEXECUTABLE`

**凍結施工清單的偽碼不可執行，且與實作分叉——後批照抄即得假綠。**

TICKET-STATUS: OPEN

🔴 **開票依據（非主委自行擴張）**：2026-08-07 批 1 code review，**codex 與 composer 兩家獨立**
判定此三處為真缺陷且**各自明文指示「走延伸檔／另票，本輪不改 TODO」**
（`CODEX-R1-P1-05`、`COMPOSER-R1-P2-01`；收斂檔 `handoffs/reconcile/20260807-govb1-b1-review-r1/synth.md` 群集 E）。

### 病

`docs/GOVB1_INPUT_QUALITY_TODO.md` §B／Task 0.1 之三處偽碼**對真實輸入零命中或取到空**：

| # | 位置 | 錯 | 後果 |
|---|---|---|---|
| 1 | §B `_frozen_hits` | `grep -nE "…"` 無檔案參數 | 讀 stdin 恆空 ⇒ **G-2 假綠** |
| 2 | Task 0.1 要點 4 `_fixture_names` | `sed -n '/fixture 清單/,/^```$/p'` 於 opening fence 即截斷 | 抽出 **0 名** ⇒ `T-0.1-F1` 空對空恆綠 |
| 3 | §B 執行段 | `awk … '{print $4}'` 對**三欄**表 | 取到空 ⇒ 永遠找不到檢查函式 |

**實作端（`b92aff6`）已自行修正三處**，故批 1 交付正確；**但 TODO 仍留錯版本**。
偽碼是給後批照抄的——**分叉即假綠來源**。

### 🔴 為何本 epic 內無法修（主委實查，非推測）

```
awk '$1=="allow"{print $2}' scripts/govb1_scope.manifest | grep -c '^docs/'   → 0
```

凍結 scope manifest **不含任何 `docs/` 路徑**，且 TODO 於各 Task 皆列**只讀**欄。
⇒ 把 TODO 改進 `base..HEAD` 即 `G-7`「未宣告即修改」違規。
把 `docs/` 加進 `allow` 亦不可——那正是 `G-7` 所禁之「以只讀／allow 標註規避 scope」，
且會使 `T-0.1-F5`（allow 集合 == 各 Task 修改∪新建欄）轉紅。
**要改 TODO 就得先改 TODO 自己的「修改檔案」欄 ⇒ 循環。**

### 出生事故（主委錯誤，具名）

主委於 r3 判定「TODO 檔頭為 `v1 DRAFT` 故非凍結文件，可就地改」，**覆蓋了兩家委員的「另票」裁定**。
該判讀**對一半**（TODO 確非凍結文件），但**漏查 scope manifest** ——
兩者是**獨立**的兩道限制。結果：`d56b07e` 使 `--only g7` rc=1、全套 `2 failed, 826 passed`，
於 `fd7f0f1`（r4）撤回。**教訓：委員說「不在本輪」時，主委要推翻須先窮舉所有相關閘，不能只查一道。**

### 修法方向（不在本 epic）

1. GOVB1 epic 全部批次完工、manifest 解凍後，一次修正三處偽碼；或
2. 若中途必須修，須以**新 base commit ＋ 新 manifest**（含 `docs/` 宣告）重開 scope，
   並同步更新各 Task 之「修改檔案」欄——成本高於價值，**預設採 1**。

### 誠實邊界

**本票無機械綁定**——不像 `票 B-13` 之 R-1 有到期閘。
若後批有人照抄 TODO 偽碼，**沒有任何檢查會擋**。這是已知且具名接受的暴露面。

---

## B-44 票 `GOV-GUARD-SELF-AUTHORIZABLE`

**治理守衛可在同一 commit 內自我授權——repo 內無解，須外部信任錨。**

TICKET-STATUS: OPEN

🔴 **開票依據**：2026-08-08 批 2 前置，**codex 與 composer 兩家獨立判 BLOCKING**
（`CODEX-R2-P0-01`／`COMPOSER-R2-P0-01`），經一輪範圍裁定後兩家**一致改判 (b) 具名殘留**
（`handoffs/reconcile/20260808-govb1-b2-review-r3/synth.md`）。**不開票即為漏項。**

### 病

`scripts/govb1_final_gate.sh` 之 `_meta_want`（expected-set）、`scripts/govb1_scope.manifest` 之
`meta` 列、`scripts/govb1_frozen_hashes.txt` 之 `scope_manifest` hash——**三者同屬同一可改邊界**。
同一交付單元同時改這三處，即可讓**未經委員裁定之路徑**通過 `G-7`。

**兩家實測**：隔離副本中同步三處後 `_g7_policy` rc=0、`PASS g7`。

### 🔴 非純蓄意（codex 修正主委原判）

主委原判「此屬防蓄意層」，**被 codex 修正**：
> 「也可能由**非蓄意的合法同步變更**觸發」——合法新增簿記或讀取端時順手同步三處，
> 即可**無意間**擴大授權。

composer 補充：須同批改三處且經雙家族 review，屬**可見、可稽核**之協調行為，**非單鍵誤觸**
⇒ 風險存在但不足以升級為阻斷。

### 為何 repo 內無解

> 任何 verifier、搬移位置或額外 hash，**若仍在 repo 內，都能被同一 commit 一併修改**。

兩家皆**無法具名任何 repo 內、不需外部信任錨之閉合動作**。
⇒ 若堅持 BLOCKING，等於「本 epic 永遠無法開工」，兩家皆不接受該後果。

### 閉合條件（需 repo 外）

**交付物不可修改之 trust anchor**：簽章／外部凍結基準／受保護之 CI verifier。

### 閉合前已有之風險降低（**皆不提供不可自證性，不得宣稱已閉合**）

`git log`／immutable commit-range 可稽核｜雙家族 review｜固定六項 expected-set｜
hash-lock｜single-source check。

### 誠實邊界

本票**無機械綁定**。與 `票 B-43` 同屬「已知且具名接受之暴露面」。
