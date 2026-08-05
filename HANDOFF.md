# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-05 12:0x | **Branch**: main
**狀態**: 🔵 **第 0 批 TODO 已修完 R8 六條 → 待決定是否派 R9 確認輪**

## ▶ 立即接手

**唯一待決策**：R8 的 6 條已全部修畢，**是否再派一輪確認**。
主委建議 **派**——理由不是規格難，而是**連續三輪主委的修補都引入新缺口**（見下失誤模式），
在 `票 B-16` 擴充上線前，委員實跑是唯一防線。使用者尚未裁決。

R9 若派：brief 用 `handoffs/20260805-GOVB0-TODO-R8-BRIEF.md` 為樣板，
**finding heading 一律照 `scripts/completeness_check.sh:153` 的正則** `^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`。

之後：TODO 標 Internal Frozen → 實作（Grok，見 ORCH §1 現行分工行）→ **雙家族 code review**。

## 現況

- SPEC `docs/GOVB0_FRICTION_SPEC.md`：**R7 版**，七輪收斂，收斂檔三家戳記 sha `b502bac9…0f82fa4bd`。
- TODO `docs/GOVB0_FRICTION_TODO.md`：**已修 9+6 條**，`template_check todo` rc=0，SPEC 11 Task == TODO 11 Task。
- 🔴 **給使用者看的文件一律放 repo 根目錄 `白話說明/`，禁放 `handoffs/`**（使用者 2026-08-05 定）。
  現有：`README.md`（入口＋當前進度）／`第0批-在做什麼.md`／`第0批-施工清單.md`／
  `治理待辦總覽.md`／`治理進度日誌.md`。**每完成一個實作批次須更新 `README.md` 與施工清單的進度表。**
- 收斂檔 `handoffs/reconcile/20260805-govb0-todo-r8/synth.md`（I-1～I-6，**已正規銷帳**）。
- **無 OPEN 債。** 票數 **38**、待辦 **30**，三份文件同步、雙向對帳差集空。

## 🔴 主委失誤模式（本 session 最重要的發現，已入 `票 B-16`）

TODO 兩輪審查共 15 條 findings，**全部屬實、無一誤報**，且**幾乎全是主委造成，非技術難度**：

| 模式 | 案例 | 次數 |
|---|---|---|
| **沒對照就寫**（違反實測>假設） | 引用不存在的 `_bc_kv`「函式」（實為 `mktemp` 路徑變數）／caller 方向寫反／測試引用 backlog 內不存在的字串 | 4 |
| **自我引用未察** | 測試與被測內容同檔，未行首錨定 ⇒ `grep -c` 把測試定義自己算進去；**主委在修補過程中又犯 2 次** | 5 |
| **內部矛盾** | B5 依賴 B3/B4 卻要求 snapshot 在 B3 前凍結／snapshot 同時列為 B0 與 Task 2.5 產出 | 3 |
| **過度宣稱** | §T 寫「100% 覆蓋」但 `F-7`／`B-36` 無落點 | 1 |

**通解（已寫入 TODO 與 backlog）**：**禁散文關鍵字比對，改用行首錨定的機器標記**——
`^TICKET-STATUS:`／`^TASK-STATUS:`／`^RESIDUAL:`。**標記寫行首、斷言帶 `^`，兩者缺一即自我污染。**

**使用者 2026-08-05 裁定**：合併進 `票 B-16`（同一強制點 `doc_format_precheck.sh`、同一病族），
**擴充 A**＝文件內可執行斷言寫檔當下實跑比對；**擴充 B**＝引用的函式名／檔名存在性檢查。
兩者**提前至第 1 批**，`B-16` 原條文維持第 4 批。
🔴 **擴充 B 的誠實邊界**：擋不了「呼叫方向寫反」（兩個識別字都存在時無法判斷），**具名殘留**。

## ⚠️ 坑（照做省時間）

- **brief 內的機器格式一律引用檢查器正則本身，禁手寫**——本日三次 brief 誘導格式失敗，每次錯處不同。
- **`##` 只准是 canonical finding ID**；brief 不可同時要求「canonical `##`」與「逐條各一段」。
  有效作法＝**明列本輪允許的 `##` 清單＋要求用表格**。
- 委員零 findings 時要求其明寫 `FINDINGS_COUNT: 0`（`票 B-38`）。
- **brief 改了就不能同輪重派**（`brief_sha256` 不符）⇒ 只能棄輪重開。
- 正規銷帳需 `sources.lock` 為 review mode：`reconcile_build.sh <session> --mode review [--rebuild]`（`--rebuild` 不接受委員檔參數）。
- **commit 訊息零豁免**：operational claim 須 `VERIFY:<receipt-id>` ＋ 可解析 scope 或寫明 runtime 類別（`static`／`讀碼`）。
- `VERIFY-EXEMPT` 合法類別**只有 6 個**：`typo`／`doc-example`／`migration-note`／`template-drift`／`tooling-blocked`／`spec-ambiguity`。
- 委員產出交件後一律 `bash scripts/gate.sh register-output <task-id> <path>`。
- 創建 `docs/*{SPEC,TODO,PLAN}*.md` 需 `bash scripts/gate.sh artifact --file … --template-opened … --sections …`。
- **`rc` 禁經 pipe**；**禁 `python3 -c`**；`ts_stamp.log` 須 `LC_ALL=C grep -a`（**禁 export**）。

## 後續順序

第 0 批（R9? → Frozen → 實作 → 雙家族 review）→ **第 0.5 批 P1-6 線 C** → 0.9 批 `B-37`
→ 第 1 批（`B-19`／`B-29`／`B-31`／`B-38`／**`B-16` 擴充 A/B**）。
