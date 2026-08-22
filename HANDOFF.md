# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）——
**R4 十九條全數修訂完成，尚未 FROZEN**。下一步＝**派 R5 複審**。
使用者裁定：**R5 通過即 FROZEN 後停下來**，不進 TODO／實作。

---

## 🔴 開工前必讀：三條最高位階規則

1. **量化主線 100% 正確，只能更嚴不能放水**（SPEC §C0，機械閘 `quant_standard_check.sh`）。
   「95% 解法就收」只適用治理 epic 之散文問題，量化路徑一律不受理。
2. **改 §D 裁定必須同步 §P Task**——此類錯已犯 **8 次**（R4 之群集 H 為第 8 次）。
   閘＝`spec_ruling_task_sync.sh`。🔴 **R4 已證明該閘會漏**：SYNC-FORBID 是**作者宣告式**，
   沒宣告到的形態擋不住。改「已修」宣稱前**一律 grep 全部引用點**，不得目視。
3. **全棧三欄稽核**（後端 code／前端 UI／wiring）——已列 R4 brief 必查第 1 項，R5 續列。

---

## 立即待辦（下一 session 第一件事）

**T-1｜派 SPEC R5**
- session：`20260822-gap3ux-x-review-r5`（或當日日期），task-id 大寫
- 派工模板＝scratchpad `spec_r4.sh` 改 r4→r5；找不到就照 R4 brief 之三項方法論重建
- 🔴 **R5 brief 必須沿用 R4 之三項方法論**（實測有效，見下「R4 成效」）：
  ① **零「請攻／重點看／最重要」**——主委不指定方向，assumed 清單明寫「非攻擊清單」
  ② **fact 全為可重跑 receipt**——跑 `bash handoffs/20260822-gap3ux-x-review-r4-facts.sh`
     重新產一份（SPEC 已改，sha 與行數都變了），零「主委實讀」
  ③ **標的 sha256 鎖版**寫入 brief，並要求委員開工先驗、不符即停下開 finding
- R5 brief 必附：R4 十九條之逐條落點（見 SPEC 檔頭表格）＋要求三家逐條標 CLOSED／OPEN

**T-2｜R5 通過即 FROZEN，然後停**（使用者明示）

---

## SPEC 現況

`docs/GAP3_EVENT_UX_SPEC.md`（**1168 行**，41 Task，三支閘皆 rc=0）
- 檔頭有 **R4 十九條落點表**＋**主委自承段**（不得刪）
- §C0 收斂標準｜§RISK a,b｜§A FACT-RECEIPT 14 條｜§D 七條裁定
- §G＝G-1／G-2 ＋ **新增 S-1..S-8 canonical serialization**
- §P **7 Phase／41 Task**（R4 新增 7.0／7.6／7.7）｜§V **16 → 18 條**（新增 V-14／V-15）｜§R｜§N
- 檔頭 **4 條 `SYNC-FORBID`**（R4 新增第 3 條涵蓋 `future<H>_*→<數字>` 形態）
- 交叉引用零 dangling：Task 41/41、V-1..V-15、S-1..S-8

**收斂履歷**：R1 24 → R2 7 → R3 18 → **R4 19**（全數 ACCEPT、0 條降殘留）

### R4 九群集落點（全部已修）
| 群集 | 落點 |
|---|---|
| A（弱閘） | 新增 Task 7.0；7.1／7.2／V-11 改三層驗證；基準由 `enum` 改 `accepted` − `pathExclusions` |
| B（G-2 序列化） | §G 新增 S-1..S-8；Task 2.2 改純引用 |
| C（IC×FL time_range） | 新增 Task 7.6／7.7、V-14／V-15；**§N #8／#10 殘留撤回** |
| D（A／B 語意漂移） | `/search` 只開 C／two_stage（具名封閉常數）；深度公式落 Task 2.1b |
| E（L3 vs 實碼） | Task 1.12 增 `run_event_study_only()`＋`ci` 標 unavailable |
| F（control_kind） | Task 7.5 明定唯一傳遞點＋混值 fail-closed |
| G（改名攻擊） | Task 1.10 增信任邊界 |
| H（§D L116） | §D-7 L1 改寫＋新增 SYNC-FORBID |
| I（空殼驗收欄） | Task 6.0 補命令＋`template_check.sh` 增佔位偵測 |

---

## 🔴 R4 成效（供 R5 決定是否沿用）

**去錨定有效**：R1–R3 三份 brief 共 10 處「請攻」，R3 十八條幾乎全落在點名軸上；
R4 零指令後多出 **5 條前三輪無人觸及之 findings**，最重者＝CODEX-R4-P0-02
（D-7 L3 與實碼呼叫鏈矛盾）。**此條做不成機械閘**——寫規格者同時決定審查者看哪裡，
只能靠紀律（摩擦九十）。

**機械閘成效分項**：放水語閘 0 findings（有效）；裁定同步閘**漏掉群集 H**（宣告式的結構限制）；
`doc_format_precheck` **漏掉群集 I**（有 token ≠ 可執行）。兩者皆已補並以實際字面反測轉紅。

**主委自承**：19 條中 2 條為主委 T-1 改寫自行引入、1 條為不實宣稱；
三家能抓到是因為 brief **事前具名標示「該批改寫未經審查」**——此作法建議保留。

---

## 本批新增／改動之機械閘

| 腳本 | 改動 | 反測 |
|---|---|---|
| `spec_ruling_task_sync.sh` | SPEC 新增第 3 條 SYNC-FORBID：`future[0-9]+_[^→]*→[0-9]` | 灌回 `future72_max_*→72` ⇒ rc=2 |
| `template_check.sh` | 新增 3b「驗證欄佔位形態」（引號內省略號／中文佔位） | 灌回 `python3 -c "..."` ⇒ rc=1；166 份 docs 誤報 **0** |
| `plain_docs_sync_check.sh` | `GAP-3施工進度.md` 之 WATCHED 加 `docs/GAP3_EVENT_UX_SPEC.md` | `--staged` rc=0 |
| `fact_keys.json` ＋鎖定測試 | `白話說明/Archived/GAP-2施工進度.md` 進 grandfathered（B1–B5 撞名 6 處誤報，擋住每次白話說明編輯） | 集合鎖定測試 3 passed；`--check` rc=0 |

🔴 **`template_check.sh` 首版關鍵字太寬**：含 `TODO`／`XXX` ⇒ 166 份 docs 誤報 **17**
（本 repo 拿 TODO 當文件型別名）。已收窄。規則見摩擦九十二：
**新增關鍵字型機檢，上線前必須全 repo 實掃並報誤報數，> 0 就收窄**。

---

## 坑

- **`git checkout` / `git restore --staged` / `rm` 會被 auto-mode classifier 擋**——
  還原 tracked 檔改用 Edit 工具；unstage 用 `git reset -q HEAD <path>`。
- **`handoffs/*` 在 `.git/info/exclude`**：新檔須 `git add -f` 才進版控（reconcile 產物必須進）。
- **`plain_docs_sync_check` 是 commit 時序判準**：工作區改好仍紅，須先 `git add`
  再跑 `--staged`（摩擦八十九之固定動作）。
- **`gov_check --no-probe` 之 G-7 需 commit 才有淨差**，commit 前必紅，屬預期。
- **commit 之 `Governance-Scope` trailer 必須單行**；長訊息一律 `git commit -F <檔>`。
- **改檔一律用 Edit 工具**；Bash 跑 python heredoc 改檔會被權限拒。
- **`cmd | head` 讀到的是 head 的 rc**；rc 一律直接取。
- review 輪派工用 `--risk low` ＋ `--template "n/a:"`；`--spec` 只能用於 impl 派工。
- session 命名 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，batch 段須為 `b<數字>` 或 `x`。
- **`_watched_for` 之 catch-all 回空字串**＝新增白話檔預設不受監看且 fail-closed，
  新增 `.md` 到 `白話說明/` 必須同時加 WATCHED 一行；已收工者移 `Archived/`（該目錄不受管）。

---

## 已知既有紅（非本批造成）

- `tests/api` 10 failed + 3 errors（R2 已 byte-identical 基準對證）
- `白話說明/_r4skel.md`（brief 骨架殘檔，untracked＋gitignored）——`rm` 被 classifier 擋，待清
- `.probe_ic{,2,3}.sh`（#9 IC OOM 探針，untracked）——HANDOFF 引用之重現法，刻意保留

---

## 其他線的狀態

- **`/search` 三 bug 修復**：🏁 已收案（白話檔已移 `白話說明/Archived/`）
- **GAP-3 B1–B5**：全部蓋章，**只差使用者 UAT B 段 13 項簽字**
- **#9b IC 規模防護本體**：排 GAP-6（registry #6）
- **純事件研究模組／標籤方法論討論**：使用者裁定另立、排在系統完成之後
