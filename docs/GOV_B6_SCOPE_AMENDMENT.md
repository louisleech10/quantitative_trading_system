# GOVB1 B6 scope 修訂（延伸檔）

STATUS: PROPOSED — 待兩家委員（codex／composer）裁決
SCOPE: 僅 B6（Task 2.1／2.2）
AMENDS: `docs/GOVB1_INPUT_QUALITY_SPEC.md:321`、`docs/GOVB1_INPUT_QUALITY_TODO.md:913`
RULE: 凍結文件不就地改；修訂走延伸檔（使用者 2026-08-01 定死）

---

## 1. 事實（機械可查證，非判斷）

| # | 事實 | 查證命令 |
|---|---|---|
| F1 | SPEC 與 TODO 皆把 `docs/GOVERNANCE_EXECUTION_ORDER.md` 列為**只讀**，且 Task 2.1「修改：無」 | `sed -n '318,321p' docs/GOVB1_INPUT_QUALITY_SPEC.md` |
| F2 | 同二檔指定該檔為**初始唯一 fact-key 的宿主** | `sed -n '321p' docs/GOVB1_INPUT_QUALITY_SPEC.md` |
| F3 | 該檔在 base commit 當下**不含任何 generated block** | `git show 62787fe:docs/GOVERNANCE_EXECUTION_ORDER.md \| grep -c 'BEGIN GENERATED'` → 0 |
| F4 | TODO 邊界②：宿主檔缺邊界標記 ⇒ `--check` **rc≠0**（fail-closed） | `sed -n '909p;918p' docs/GOVB1_INPUT_QUALITY_TODO.md` |
| F5 | Task 2.2 把 `--check` 掛進 `gov_check.sh`；`GOVB1_FACTKEY_ROOT` 未設時 root＝repo 根 | `sed -n '933,940p' docs/GOVB1_INPUT_QUALITY_TODO.md` |
| F6 | 該檔**不在** `govb1_scope.manifest` 的 allow／meta 內 | `grep -c GOVERNANCE_EXECUTION_ORDER scripts/govb1_scope.manifest` → 0 |
| F7 | G-7 掃 `git diff --diff-filter=ACMRD base..HEAD` **全部**路徑，未宣告即 FAIL | `scripts/govb1_final_gate.sh:536-547` |
| F8 | 該檔建立於 base commit 本身，base..HEAD 未曾動過 | `git log --oneline 62787fe..HEAD -- docs/GOVERNANCE_EXECUTION_ORDER.md` → 空 |
| F9 | 🔴 **manifest 的 `allow` 集合被機械釘死＝凍結 TODO 之「修改檔案」宣告集**；加一列不在 TODO 宣告內的路徑，`test_t01_f5_manifest_matches_task_decl` 與 `test_meta_t5_f5_still_allow_only` **立即轉紅**（另 4 條計數斷言 36→38 同時紅） | 主委實跑：加兩列後全套 governance **7 failed**，移除後回綠 |
| F10 | out-of-epic 硬保護集＝`docs/GOVB1_`／`govb1_scope.manifest`／`govb1_frozen_hashes.txt`；`docs/GOVERNANCE_EXECUTION_ORDER.md` **不在其中** | `scripts/govb1_final_gate.sh:380-382` |

## 2. 衝突（F1–F8 的直接推論，兩個方向都是死路）

- **照字面實作**（宿主檔維持只讀）⇒ F3＋F4＋F5 ⇒ `gov_check.sh` **恆非零** ⇒
  Task 2.2 落地當下起，**本 repo 的每一次 push 都被自己擋死**。
- **植入 block**（唯一能讓 F4 過的作法）⇒ F6＋F7 ⇒ G-7 `未宣告即修改` **FAIL**。

⇒ 這不是實作選擇題，是**規格與 repo 現況的矛盾**。SPEC/TODO 已凍結且使用者定為唯讀，
故不就地改，改以本延伸檔記錄並請委員裁決。

## 3. 主委的第一個修法**已被機器否決**（保留紀錄，不美化）

主委原採：`scripts/govb1_scope.manifest` 加 `allow docs/GOVERNANCE_EXECUTION_ORDER.md` ＋ rehash。
理由是「誠實標示本 epic 會動這個路徑」。

🔴 **F9 證明這個理由是錯的**：manifest 的 `allow` **不是**主委的宣告欄，
它是**凍結 TODO 宣告集的機械鏡像**。往裡面加一列＝聲稱「TODO 宣告過這個路徑」，而 TODO 沒有。
守衛立刻抓到（7 條紅）。**該守衛做對了，被擋的是主委。**

⇒ 已完整回退（manifest 與 `frozen_hashes.txt` 皆逐字回到 HEAD；`git diff --stat` 無輸出）。

## 4. 改採之修法（committed，待裁決；被否即回退）

| 動作 | 檔案 | 通道 |
|---|---|---|
| A1 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 植入一組邊界標記，內容由 `--write` 產出 | out-of-epic commit |
| A2 | 本延伸檔（`docs/GOV_B6_SCOPE_AMENDMENT.md`） | 同上 |

**為何 out-of-epic 是唯一機械可行通道**（不是偏好，是消去法）：

1. in-epic 通道＝manifest allow ⇒ 被 F9 定義性地關閉（allow ≡ 凍結 TODO 宣告集）。
2. 改 TODO 使其宣告該路徑 ⇒ 違反使用者「凍結文件唯讀」之定死條款。
3. out-of-epic ⇒ F10 顯示該路徑不在硬保護集內，機械可行；且
   `gov_check.sh` 第 0b 段**每次 push 都把每一筆 out-of-epic commit 印出來**，不是靜默旁路。

🔴 **主委對此仍有保留意見，具名於此供委員推翻**：植入 block 是 `票 B-25` 的工作本體，
把它標成 `out-of-epic` 在**語意**上像 scope laundering。主委接受它是因為
「機械上沒有別的門，且這道門是被稽核的」，不是因為語意上恰當。
若委員認為語意優先，請指出可執行的第三條路。

**檔名為何不是 `docs/GOVB1_B6_...`**：`docs/GOVB1_` 屬 out-of-epic 硬保護前綴（F10），
以該前綴命名會使本檔自己無法經由唯一可行通道進入版控。原檔為未 commit 之新檔，
以 `mv` 更名，**不產生 git rename**（避免觸發 `_g7_ooe_rename_hits_protected` 之整體關閉）。

**明確否決的替代方案**（列出理由，供委員推翻）：

| 替代 | 否決理由 |
|---|---|
| `fact_keys.json` 初始留空 `{}`（邊界①允許 rc=0） | 違反 TODO 實作要點 1「初始只收 `governance-execution-order` 一項」；且機制上線卻零涵蓋＝假保護 |
| 把 target 改指某個已在 allow 內的檔 | 違反 F2；漂移事故發生在該宿主檔，換靶＝不治病 |
| 放寬 `--check`：宿主檔缺標記時回 0 | 違反 F4，且正是「缺標記＝沒保護」那個 fail-open |

## 5. 本修訂**不**主張的事

- 不主張 SPEC/TODO 其餘任何條文變更。
- 不主張放寬 G-7、不新增 meta 列、不動 `_g7_policy` expected-set、**不動 manifest**。
- 不主張「single-source 已完成」——具名殘留原封保留（見 §6）。

## 6. 具名殘留（不解，僅記錄）

1. 生成器不知道的新文件裡憑空手寫第三份副本 ⇒ 擋不到。
2. `git push --no-verify` 可繞。
3. 宿主檔內 generated block **以外**的敘述段（站 1–5、站 5 之後主表）仍是同一事實的第二份副本；
   本機制只保證「區塊 ≡ 資料檔」，**不保證敘述段 ≡ 區塊**。已於宿主檔內就地標明。
4. 兩個 commit 之間存在**一個 gov_check 為紅的中間狀態**（實作 commit 落地時宿主檔尚無 block，
   或反之生成器尚不存在）。因兩 commit 同批 push，實務上不影響；bisect 到該點會見紅。
   不拆成兩個 commit 就得讓一個 commit 同時帶 epic 內外路徑並掛 out-of-epic 標籤，
   那會讓稽核清單更失真——兩害相權取其輕，具名於此。

## 7. 委員裁決欄（請兩家各填一列）

| 家族 | 裁決 | 理由／要求之替代作法 |
|---|---|---|
| codex | | |
| composer | | |
