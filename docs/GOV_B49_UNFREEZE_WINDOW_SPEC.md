# B-49 授權開窗機制（`_B45_HARNESS` path-scoped unfreeze）— SPEC

> 來源診斷：`handoffs/reconcile/20260811-govb49-x-consult-r{1,2,3}/synth.md` ＋ `…-x-review-r1/synth.md`（四輪三家）　|　日期：2026-08-11　|　對應 TODO：待生成
>
> **修訂**：r2 —— 依 SPEC review r1 之 12 條（3 BLOCKING）修訂。與 r1 之差異見 §D。

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：大。
- **命中高風險原則**：(b) 跨模組/共用路徑——本機制被三道 live waiver 守衛、引信、炸彈與兩處
  source-level oracle 共同消費；(c) 多 phase／難回退——它是**解除自身約束**的機制。
- **RISK-HIT 宣告**（機檢依據）：

RISK-HIT: b,c

- 未命中 (a)(d) ⇒ §G 移 §N 標 N/A。**adversarial review 仍必跑**（三家；理由見 §C-3）。

## §A 假設與待使用者確認（事故：拿推論代替問人）

**已驗證事實**（6 條 FACT-RECEIPT，皆 2026-08-11 實跑）：

- FACT-RECEIPT: `sed -n '2427p' tests/governance/test_govb1_contract_matrix.py` → 印出
  `    return rejected >= 1 and len(_B45_HARNESS) == 5`（Claude 實跑）
- FACT-RECEIPT: `grep -n "len(_B45_HARNESS) == 5" tests/governance/test_govb1_contract_matrix.py` → 印出
  `2111`／`2213`／`2427` 三行（Claude 實跑）
- FACT-RECEIPT: `sed -n '2323p' tests/governance/test_govb1_contract_matrix.py` → 印出
  `    assert not (shell_set & set(_B45_HARNESS))`（Claude 實跑；G-7 硬保護集交叉契約）
- FACT-RECEIPT: `sed -n '2573,2574p' tests/governance/test_govb1_contract_matrix.py` → 印出
  `assert "--name-only" in body and "_B45_HARNESS" in body`（Claude 實跑；source-level oracle）
- FACT-RECEIPT: `pytest -q tests/governance/test_result_state_format_failed.py` → 印出
  `12 passed, 1 failed`（codex／composer／grok 各自獨立實跑，三份 rc 表逐格一致）
- FACT-RECEIPT: `grep -n "pytest tests/governance" scripts/gov_check.sh` → 印出 `227`／`228`
  （Claude 實跑；pre-push 委派路徑 ⇒ 紅測擋住整個 repo 的 push）

**待確認：無**（技術決策依 `CLAUDE.md` 委員會條款，不上呈使用者）。

**已確認結果**：2026-08-11 使用者指示「委員＝Codex+Grok+Composer 三家，實作＝Opus 主委」；
其結構後果見 `docs/GOV_ROLES_ORCHESTRATOR_AMENDMENT.md` §D。

## §C 約束（不重抄，引用 + 只列本任務相關）

**C-1　`_B45_HARNESS` 不得縮減。** `:2111`／`:2213` 逐字斷言 `len(...) == 5`。
⇒ 開窗**必須**是獨立授權集合，由守衛從 `hit_harness` **扣除**，不是把檔案移出 tuple。

**C-2　票文②「不得以②為藉口放寬窗凍結」是硬約束。** 授權須**單票、單期、可失效**，不得成為長期白名單。

**C-3　本機制解除的是約束自己的機制 ⇒ 不得由主委自行落地。**
完整管線（SPEC → 三家 review → 實作 → 三家 code review）不得跳步。

**C-4　守衛不得解析 commit 訊息。** `test_waiver_guards_never_parse_commit_message` 釘死。
⇒ 授權來源**不得**是 trailer。

**C-5　`_B45_HARNESS` 之完整 reader inventory**（`CODEX-R1-P1-06`；主委已逐一複驗行號）：

| 位置 | 性質 | 本 SPEC 之處置 |
|---|---|---|
| `:2111` B4 窗、`:2213` B5 窗 | `assert len(_B45_HARNESS) == 5` | **不得改**（C-1 之來源） |
| `:2323` | G-7 硬保護集交叉契約 `assert not (shell_set & set(_B45_HARNESS))` | **不得改**；本機制不觸及 `_G7_OOE_HARD_PROTECTED` |
| `:2517-2522` | source-level oracle：引信不得退回字面比對（`assert not hit_harness` 不得出現在引信內） | **不得改**；Task 1.4 之改動不在引信內寫該字面 |
| `:2573-2574` | source-level oracle：守衛 body 須仍含 `--name-only` 與 `_B45_HARNESS` | **不得改**；Task 1.3 兩者皆保留 |
| 三道 live waiver 守衛 | `hit_harness = names & set(_B45_HARNESS)` 後 `assert not hit_harness` | Task 1.3 更新（僅改 assert，不改 `hit_harness` 計算式） |
| `_b45_freeze_still_active()` | 引信 | Task 1.4 更新 |
| `test_b45_unfreeze_requires_roles_sot_closure` | 炸彈 | Task 1.5 更新（r2 新增） |

**C-6　誠實邊界（`CODEX-R1-P1-03`，r2 下修宣稱）**：
本機制**只防意外與遺忘，不防具寫入權者蓄意**。主委對授權常數、票庫與收斂檔皆有寫入權。
r1 曾寫「防止自己寫一張授權書」，**該宣稱過強，已刪除**。與 `票 B-49` 炸彈之既有誠實邊界一致。

> **新資料結構之處理（r2 變更）**：r1 曾規劃獨立 JSON 檔；r2 **取消**，
> 改為與守衛同檔之模組級常數（理由見 §D-2）。⇒ 本 SPEC 不再定義新的外部 schema 檔。

## §G Golden / Baseline

移 §N 標 N/A。

## §P Phase 與依賴

### Phase 1 — 授權常數、判定函式、守衛與炸彈（依賴：無）

**Task 1.1 — 授權常數（取代 r1 的 JSON 檔）**

- 目標：把「本期授權可觸及哪些 `_B45_HARNESS` 路徑」變成**與守衛同檔同 commit** 的常數。
- 檔案：`tests/governance/test_govb1_contract_matrix.py`，模組級新增
  `_B49_TICKET_ID`（字串常數，寫死 B-49 之 canonical ID）、
  `_B49_AUTHORIZED_PATHS`（frozenset，寫死具名三檔）、
  `_B49_BASIS`（收斂檔路徑）、`_B49_BASIS_SHA256`（該檔 sha256）
- 改法：四個常數並列於 `_B45_HARNESS` 之後，附註解說明退場方式（Task 2.3）。
- **驗證**：`pytest -q tests/governance/test_govb49_unfreeze_window.py -k constants` 全綠；
  且 `_B49_AUTHORIZED_PATHS <= set(_B45_HARNESS)` 與 `len(_B49_AUTHORIZED_PATHS) == 3` 皆成立
- **邊界（≥2）**：①常數不存在（退場後）⇒ 判定函式回 `frozenset()`
  ②常數存在但含 `_B45_HARNESS` 以外路徑 ⇒ **整批**回 `frozenset()`（越權即全拒，非只濾除）
- **存活至**：Task 2.3 移除；移除後行為須逐字回到現行
- **覆蓋風險**：無
- 不可做：不得用萬用字元／前綴比對／環境變數；不得放在 repo 外或未追蹤檔

**Task 1.2 — `_authorized_unfreeze_paths()` 判定函式（fail-closed）**

- 目標：把授權條件變成一個回傳集合的函式；任一條件不成立即回 `frozenset()`。
- 檔案：`tests/governance/test_govb1_contract_matrix.py`，新增模組級函式
- 改法：依序驗以下條件，任一不成立**立即**回 `frozenset()`（不得拋例外中斷收集）：
  ① 四個常數皆存在且型別正確
  ② `_B49_AUTHORIZED_PATHS` **恰等於**具名三檔集合，且為 `_B45_HARNESS` 之子集
     （`CODEX-R1-P0-01`：r1 只要求「子集」，可塞任意合法子集）
  ③ `_B49_TICKET_ID` 在 `handoffs/20260801-GOV-AMEND-BACKLOG.md` 之 `TICKET-STATUS` **非** `CLOSED`
     （`GROK-R1-P1-02`：票號由常數寫死，**不得**由授權資料自選）
  ④ `_B49_BASIS` 之現檔 sha256 **等於** `_B49_BASIS_SHA256`
     （`COMPOSER-R1-P1-01`：防指向後被改、防引用已 supersede 之收斂檔）
  ⑤ `_B49_BASIS` 經戳記檢查且**顯式**要求正式委員三家
     （`CODEX-R1-P0-02`：`reconcile_stamps_check.sh` 預設讀 `active_stampers`，
     兩家期間兩家戳記即 rc=0；本函式須傳入 `review_families` 或拒絕 `active_stampers ⊂ review_families`）
- **驗證（可證偽）**：Task 2.1 之 mutation 矩陣 8 格逐格轉紅；
  且無授權常數時 `_authorized_unfreeze_paths() == frozenset()`
- **邊界（≥2）**：①票號在 backlog 中不存在 ⇒ `frozenset()`（不得當成「沒限制」）
  ②`_B49_BASIS` 檔不存在 ⇒ `frozenset()`
- **存活至**：Task 2.3 移除常數後，本函式保留（永久回 `frozenset()` ＝ 永久全凍結）
- **覆蓋風險**：無
- 不可做：不得讀 commit 訊息（C-4）；不得讀環境變數；不得有任何「測試模式」旁路

**Task 1.3 — 三道 live 守衛改為扣除授權集合**

- 目標：讓守衛在授權範圍內放行、範圍外仍 fail-closed。
- 檔案：`tests/governance/test_govb1_contract_matrix.py` 之
  `test_waiver_b3_range_does_not_touch_forbidden`／`_b4_`／`_b5_`
- 改法：`assert not hit_harness` → `assert not (hit_harness - _authorized_unfreeze_paths())`
  🔴 **`hit_harness` 之計算式與 `--name-only` 逐字不動**（C-5 之 `:2573-2574` oracle 釘死兩者）。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k waiver` 全綠；
  且無授權常數時 OLD vs NEW 之 reject 布林逐格相等（Task 2.2，判準 `old_reject == new_reject`）
- **邊界（≥2）**：①diff 同時含授權路徑與非授權 harness 路徑 ⇒ **拒**（差集非空）
  ②diff 只含非 harness 檔 ⇒ 放行（現行行為不變）
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得放寬 `_B45_FORBIDDEN_PREFIXES` 等其他禁改集合

**Task 1.4 — 引信：餵入路徑取自差集 ＋ live guard 數 fail-closed**

- 目標：授權開窗**不得**使引信提前判 inactive；守衛全 dormant **不得**被當成安全退場。
- 檔案：`tests/governance/test_govb1_contract_matrix.py` 之 `_b45_freeze_still_active()`
- 改法：
  1. 餵入之假 diff 路徑改由 `sorted(set(_B45_HARNESS) - _authorized_unfreeze_paths())` 取首項
     （`COMPOSER-R1-P1-02`／`GROK-R1-P2-01`：r1 未寫死取法，實作若仍固定 `[0]` 會在
     `[0]` 落入授權集合時誤判 inactive）；該差集為空 ⇒ 直接判 inactive（＝五檔全授權＝真解凍）
  2. 新增 fail-closed 條件：**live guard 數 ≥ 1**；三道 guard 全 dormant／缺失 ⇒
     **不得**回報 inactive（`CODEX-R1-P1-04`）
  3. `len(_B45_HARNESS) == 5` 之判準**保留**（C-1）
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k b45` 全綠且
  `test_b45_bomb_cannot_be_defused_by_skip` 通過（該測讀引信原文，確認 `_fake_run` 與斷言皆在）
- **邊界（≥2）**：①授權＝`_B45_HARNESS[0]` 單一項 ⇒ 引信仍 active
  ②授權＝五檔全部 ⇒ 引信 inactive（此為**非法輸入**，由 Task 1.5 之炸彈轉紅攔下）
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得刪引信任一判準；不得以 `pytest.skip` 拆引信；不得在引信內寫入
  `assert not hit_harness` 字面（C-5 之 `:2517-2522` oracle）

**Task 1.5 — 炸彈終態分支（r2 新增；`GROK-R1-P0-01`）**

- 目標：修正「退場後必紅」之狀態機死結。
- 檔案：`tests/governance/test_govb1_contract_matrix.py` 之
  `test_b45_unfreeze_requires_roles_sot_closure`
- 改法：`freeze active` 分支內，先判票是否 `CLOSED`；若是，則要求**完成證據在場**再放行：

```
if _b45_freeze_still_active():
    if status == "CLOSED":
        _assert_b49_closure_evidence()
        return
    assert status == "OPEN"
    return
assert status == "CLOSED"
```

  `_assert_b49_closure_evidence()` 逐一斷言三檔內之具名 fail-closed 標記在場
  （即 B-49 條件①②③之落地痕跡），缺一即紅。
  ⇒ 「可以關票」之條件由**狀態字串**升級為**證據在場**。
  🔴 `test_b45_bomb_cannot_be_defused_by_skip` 要求之三項（無 `pytest.skip`、
  `_b45_freeze_still_active()` 在、`status == "CLOSED"` 在）**全部保留**。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k "b45 or bomb"` 全綠；
  且 Task 2.1 之第 ⑦⑧ 格（偽造關票、證據缺失）各自轉紅
- **邊界（≥2）**：①票 `CLOSED` 但三檔證據缺失 ⇒ **紅**
  ②票 `OPEN` 且授權為三檔 ⇒ 綠（施工期正常態）
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得把 `_assert_b49_closure_evidence()` 寫成字面比對即可通過的空殼

### Phase 2 — 可證偽性與退場（依賴：Phase 1 全部 Task）

**Task 2.1 — mutation 矩陣（8 格）**

- 目標：證明每一條授權條件與炸彈改動都承重。
- 檔案：`tests/governance/test_govb49_unfreeze_window.py`（新建）
- 改法：以隔離副本（真 SoT 全程唯讀）逐格變異：
  ① 無授權常數 ⇒ 觸及三檔之 diff 須被拒
  ② 授權三檔、diff 含第四個 harness 檔 ⇒ 須被拒
  ③ commit 訊息含 `Governance-Scope` ⇒ **不影響**判定（守衛不讀訊息，C-4）
  ④ 授權僅三檔、diff 含五檔 ⇒ 須被拒
  ⑤ `_B49_BASIS` 僅二家 APPROVED ⇒ 授權集合須為空
  ⑥ 授權集合＝`{_B45_HARNESS[0]}` ⇒ 引信仍 active（`GROK-R1-P2-01`）
  ⑦ 票標 `CLOSED` 但三檔證據缺失 ⇒ 炸彈須紅（`GROK-R1-P0-01`）
  ⑧ `_B49_TICKET_ID` 改為另一張 OPEN 票 ⇒ 授權集合須為空（`GROK-R1-P1-02`）
- **驗證（可證偽）**：`pytest -q tests/governance/test_govb49_unfreeze_window.py` → 8 格全綠；
  且逐格「移除該判定後重跑 ⇒ 對應斷言 rc 由 1 轉 0」，證明該判定承重（非只是存在）
- **邊界（≥2）**：①`_B49_AUTHORIZED_PATHS` 為空 frozenset ②含 `_B45_HARNESS` 外路徑
  —— 兩者皆須回 `frozenset()` 而非「全授權」
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得以「測試通過」作為驗收（`docs/TEST_DESIGN_CHARTER.md`：廉價綠燈不算保證）

**Task 2.2 — 行為不變對照（無授權常數時）**

- 目標：證明本機制在未授權時對既有行為**逐字無影響**。
- 檔案：`tests/governance/test_govb49_unfreeze_window.py`
- 改法：以 `git show HEAD:tests/governance/test_govb1_contract_matrix.py` 為對照，
  於「無授權常數」情境對同一組假 diff 比對 OLD vs NEW 之 reject 布林。
- **驗證**：矩陣逐格 `old_reject == new_reject`（比照 grok 在 `_role_gate.sh` 那次 15/15 對照）
- **邊界（≥2）**：①diff 含 harness ②diff 不含 harness
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得只做靜態推理充當對照

**Task 2.3 — 退場條件**

- 目標：授權窗**必須**能關，且關閉後回到全凍結、炸彈不紅。
- 檔案：`tests/governance/test_govb1_contract_matrix.py`（刪四常數）＋
  `handoffs/20260801-GOV-AMEND-BACKLOG.md`（`TICKET-STATUS` 改 `CLOSED`）
- 改法：B-49 之 ①②③ 完成並經三家 code review 後，先確認
  `_assert_b49_closure_evidence()` 綠，再改票狀態，最後刪四常數。
- **驗證**：刪常數後 `pytest -q tests/governance` exit 0；三道守衛對 harness diff 恢復全拒
- **邊界（≥2）**：①先關票未刪常數 ⇒ 條件③使授權失效，炸彈走 `CLOSED` ＋ 證據分支
  ②刪常數未關票 ⇒ 條件①使授權失效，炸彈要求 `OPEN`（仍綠，因票確實 OPEN）
- **存活至**：本 Task 為終點
- **覆蓋風險**：無
- 不可做：不得把授權常數留在樹上「以備下次」

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 為 `b,c`；本機制**宣稱驗正確性**（它是閘門），
  依 `docs/TEST_DESIGN_CHARTER.md` 仍必附 mutation ⇒ Task 2.1 之 8 格矩陣。
- 測試層級：單元（判定函式）／整合（三道守衛 + 引信 + 炸彈）／對照（OLD vs NEW）／邊界。
  可獨立 `pytest tests/governance/test_govb49_unfreeze_window.py` 跑，不需 `run_api.py`。
- **防假綠**：本批不得修改既有斷言之期望值；`hit_harness` 計算式與 `--name-only` 逐字不動；
  `test_b45_bomb_cannot_be_defused_by_skip`、`test_waiver_guards_never_parse_commit_message`、
  `:2323` G-7 交叉契約三者**須全程綠**。
- **驗收之可證偽反例**（任一成立 ⇒ 未完成）：
  - 無授權常數時，觸及 harness 之 diff 竟被放行
  - `_B49_BASIS` 僅二家 APPROVED 時授權集合非空
  - `_B49_TICKET_ID` 換成另一張 OPEN 票仍能開窗
  - `_B49_BASIS` 內容被改而 sha256 未同步時仍能開窗
  - `_B45_HARNESS` 長度不再為 5，或 `hit_harness` 計算式被改寫
  - 三道守衛全 dormant 時引信回報 inactive
  - 票標 `CLOSED` 而三檔證據缺失時炸彈仍綠
  - 授權集合含 `_B45_HARNESS` 以外路徑而未整批拒絕
- **非法輸入（不是 boundary）**：授權集合＝五檔全部——票 `OPEN` 時引信 inactive 使炸彈要求
  `CLOSED`、票 `CLOSED` 時條件③使授權為空。⇒ 標為**預期拒絕**，不得列為可用狀態（`CODEX-R1-P1-05`）。
- **邊界目錄**（本任務適用）：空輸入（授權集合為空）、越權輸入（非子集／非恰等）、
  全量輸入（五檔＝非法）、守衛全 dormant。
  不適用：全NaN／Inf／std=0／OOM／並發寫／大尺度浮點 reduction。

## §R 回退

- Phase 1／Phase 2 各自獨立 commit，可單獨 revert。
- 「預設關閉」＝**四個授權常數不存在**：刪常數一鍵回退至全凍結，不需改判定函式。
- 任一 mutation 未轉紅 ⇒ 不 merge。

## §D 與 r1 之差異（供 review 對照）

- **D-1**：新增 Task 1.5 修炸彈終態死結（`GROK-R1-P0-01`；r1 之退場序列**必紅**）。
- **D-2**：**移除獨立 JSON 授權檔**，改為與守衛同檔之模組常數（`CODEX-R1-P1-03`）。
  ⇒ untracked／symlink／本地與遠端不一致三種向量**結構上消失**，且改動必現於 diff。
- **D-3**：授權由「某票未關 ＋ 某收斂檔有戳記」收緊為「票號寫死 ＋ 路徑恰等於三檔 ＋
  basis digest 相符 ＋ 顯式三家」（`CODEX-R1-P0-01`／`P0-02`、`GROK-R1-P1-02`、`COMPOSER-R1-P1-01`）。
- **D-4**：引信餵入路徑改取自差集，並新增 live guard 數 fail-closed（`COMPOSER-R1-P1-02`、
  `GROK-R1-P2-01`、`CODEX-R1-P1-04`）。
- **D-5**：§C-5 補完整 reader inventory（`CODEX-R1-P1-06`）；§C-6 下修宣稱為「只防意外不防蓄意」。
- **D-6**：mutation 由 5 格擴為 8 格；五檔格由 boundary 改標非法輸入（`CODEX-R1-P1-05`）。

## §N N/A 登記

- **§G Golden / Baseline：N/A** —— 本任務不碰數值／ML／feature 生成或 merge 路徑，
  亦不動 `data_cache/`；產出為治理閘門之判定邏輯，無 baseline 可凍結。
  行為不變之證明由 Task 2.2 之 OLD vs NEW 對照矩陣承擔（等價於 Golden 的角色）。
