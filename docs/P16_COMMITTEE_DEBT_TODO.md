# P1-6 委員未結案債狀態機 — TODO

> **版本 v1.3 — Internal Frozen，B2 可派**（收 R1 27 ＋ R2 10 findings ＋ **B1 實作階段三家裁決**）　|　**基於 SPEC** `docs/P16_COMMITTEE_DEBT_SPEC.md` **v2.9**　|　日期：2026-07-29
>
> ### 📌 v1.3 收的是「SPEC 被實作階段打回後、TODO 沒跟上」（`CODEX-R4-P1-02`）
> B1 實作揭露 SPEC 的 bootstrap **P0**，SPEC 升 v2.9，但 TODO 仍宣稱基於 v2.8、§A 條數過時、Task 0.1 未落 v2.9 的 writer 契約 ⇒ **TODO 不再是 v2.9 的一致執行契約**。本版同步：
> - **Task 0.1 實作要點**加入 v2.9 的**收窄表**與「**所有 review-mode writer 路徑**都須由 audit 導出 identity、拒收 caller `--round-id`」
> - §0.4／§T 的 §A 誠實邊界條數 **13 → 14**（v2.9 新增第 11 條：`discovery` session 完全不受 identity binding 保護）
> - B1 狀態改為**已完工並 push**（`8a12c36`），批次 Gate 基準 `pytest tests/governance -q` **287 → 298 passed**
>
> **R2 結果**：27 → **10 findings、零 P0**。**composer 與 grok 皆判「B1 可派」**；codex 判需修補（7 條 P1，**全部採納並已修**）。
> **R2 codex 七條（皆為 bash 語意／契約落點的真缺陷，照 v1.1 偽碼實作必中）**：
> ①`_scan_session_locked` **把所有非零都當「沒找到」** → 掃描出錯時照樣 append（已改三態 `case`，錯誤 fail-closed）
> ②偽碼**臆造欄位名 `families`**，registry 實為 **`participants`**（已改，並加註「欄位名一律 grep registry 核對，不得自行發明」）
> ③`--rebuild` 用了**未定義的 `$session_lock`**（已補取值來源）
> ④`_cmd_has_open` 用 pipeline **吞掉 JSON parse 的 rc=2**，違反自己宣告的 fail-closed（已改為先落地再接 rc）
> ⑤`_cmd_clear` 六道 assertion **無 `|| return`**，未設 `set -e` 時失敗仍會走到 `_emit_clear`（已逐道補）
> ⑥`reason` 只寫「非空」，**漏 registry 的 `reason_min_chars`（現值 20）**（已補，且明訂讀 registry 不硬編）
> ⑦**`--kind` → `abandon_kind` 的寫入契約缺席**，只有函式名（已補契約＋ enum 驗證＋偽碼）
>
> ### ✅ SPEC sha 處置：**三家一致裁定 (a) 接受現況，不重跑戳記輪**
> 依據＝`bash scripts/verify_spec_stamp_delta.sh` rc=0，證明戳記後改動**恰為 §V M20 那一行 `VERIFY-EXEMPT` 文件註記**，零契約變更。下表為 provenance 交代。
>
> ### ⚠️ SPEC sha 的兩個值——請勿誤判為漂移（`GROK-R1-P1-05` 已抓）
> | 值 | sha256[:20] | 說明 |
> |---|---|---|
> | **三家戳記時** | `3578b4ae76590584fef7` | RECONCILE-STAMP 指向的狀態 |
> | **磁碟現況** | `0dcb9e8d96431f06a2d3` | commit `4e82a78` |
>
> **成因**：戳記完成後，為了讓 pre-commit 的 claim checker 放行，我在 §V **M20** 那一列加了一行 `VERIFY-EXEMPT:doc-example` 註記。
> **機械證明**：`bash scripts/verify_spec_stamp_delta.sh` → 把該註記還原後 **sha 精確回到 `3578b4ae76590584fef7`，差異行數 2（同一行改前/改後）** ⇒ **戳記後的改動恰為那一行，無其他未交代改動**。
> **🛑 處置未定，留給 T2 三家裁定**：該註記是文件註解、不改任何契約，但「起草者自行判定自己的改動無害」正是本 epic 反覆出事的模式。選項＝(a) 接受現況並以本表為 provenance 交代；(b) 重跑戳記輪。**起草者傾向 (a)，但不自行執行。**

---

> ## 📌 v1.1 收了什麼（R1：codex 8／composer 7／grok 12 ＝ 27 findings → 16 群，**全部採納，0 條不採納**）
>
> **27 條裡 21 條是同一個病：我寫 TODO 時沒有回讀 SPEC 對應段落。** 不是深度不足，是**根本沒對照**。最嚴重的 G1 更是我在 brief 裡親自叫三家攻的「夾帶 SPEC 未裁決的設計」，我自己踩了。
>
> | 群 | 修了什麼 |
> |---|---|
> | **G1（3/3 P0）** | Task 3.2 探針策略**整段寫反**——SPEC 改法②訂的是 `_debt_probe_helper.py` + monkeypatch **模組常數**（被 patch 的是真正決定行為的變數），我卻寫成「就地變異真腳本、**禁** monkeypatch」。已整段對齊 SPEC，並補回逃生條款 |
> | **G2/G3/G4（P0）** | Task 1.1 偽碼三個獨立 bug：**缺 `shift`**（session 名被當事件參數）／**內部函式會二次取鎖 → 自鎖**（已用 `*_locked` 命名契約在偽碼層關死）／**rc 不傳播**（`_release_lock` 回 0 吞掉失敗，恰好打穿 Task 1.2「寫入失敗不得啟動 cx_run」所依賴的前提） |
> | **G5/G6（2/3 P1）** | Task 3.2 漏 SPEC 改法③④（**14 檔 `DEBT_AUDIT_OVERRIDE` 隔離**，不做會讓整個治理測試集假紅）；Task 2.1 漏改法③ **cutoff** |
> | **G7/G8（2/3 P1）** | Task 1.2 必填欄位用 `...` 帶過（**`brief_sha256` 的寫入端就是這裡**，漏寫則 Task 1.3 的前置永遠無基準）；Task 2.2 **第六項寫錯**（SPEC ⑥是 lock sha256 稽核，我寫成 roster；且 roster 要**集合相等**非 covers） |
> | **G9–G11、G13–G15** | `--rebuild` 偽碼補取值步驟／我自行夾帶的「缺 `round_id` 容忍」限縮適用端／§B 補**批內順序**欄／B1 規模改「中」且刪去「無新控制流」誤述／`d` 移除／2.1・3.1 補偽碼／B1 增 `--rebuild` 提前 oracle |
> | **G16（P3）** | §0.1 小幅鏡射 SPEC §C — **提出方自判屬刻意代價**，不改，登記待觀察 |
>
> **修法（本輪起）**：TODO 每個 Task 落筆前，**逐個改法編號打開 SPEC 原文確認落點**。已做成 `scripts/todo_spec_crosscheck.sh`（**誠實邊界：只抓「完全沒提」，抓不到 G1 那種「寫了但寫反」**——那只有人讀或委員能抓）。
>
> ## ⚠️ 本 TODO 的反漂移設計（**請先讀，這決定了怎麼審它**）
>
> 前一版 TODO（v0.5，987 行，已封存至 `handoffs/p16-spec-archive/P16_TODO_v0.5_OBSOLETE_v122_CONTRACT.md`）**有 7 張鏡射 SPEC 各節的索引表**。實測後果：改 SPEC 一個字，機械上要動 TODO 2–4 處，**TODO 階段的 findings 有 16/19 是抄寫漂移而非設計問題**。
>
> **故本版刻意不鏡射 SPEC 內容**：
> - **改法細節與驗收條件的唯一真相源＝SPEC**。本 TODO 的「驗證」欄**只寫測試檔名與測試函式名**（SPEC 未指定的層級），通過條件一律寫「見 SPEC Task N.x 驗證段」，**不複製條文**。
> - 本 TODO 只加 SPEC 沒有的東西：**批次拓撲、函式簽名、偽碼、修改檔案到函式名、既有 caller 清單**。
> - **覆蓋追溯**見下方 §T，只列 ID 對應，不列內容。
>
> **審查者請據此判斷**：若你認為某處「該複製但沒複製」，請說明**不複製會導致實作端做錯什麼**——若只是「讀起來要跳檔」，那是本版刻意付出的代價，換掉的是七次同型漂移。

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### 0.1 憲法級（違反即退回，不接受「效果一樣」的辯解）
- **反 bypass 紅線**：任何新增 env override **一律綁 `GOVERNANCE_TEST_HARNESS=1`**，否則 fail-closed。本 epic 新增的每一個 env 都適用，無例外。
- **bash 3.2 相容**（macOS 預設）：**禁 `declare -A`**、**禁 `flock`**（`command -v flock` 在本機不存在，委員已實跑證實）。
- **家族名不得寫死**：一律讀 SoT `scripts/governance_families.json`。
- **工具優先**：合併／完整性驗**一律呼叫** `scripts/reconcile_build.sh`／`scripts/completeness_check.sh`，**不得重造等效邏輯**。
- **不得改寫既有守衛 V-A/V-B/V-C/V-M 內部**；只可旁側新增呼叫。
- **事件型別上限 4 種**。**新增第 5 種即屬範圍膨脹**，須回頭改 SPEC 並重戳，**不得在實作階段自行增加**。
- 完整清單見 SPEC §C（8 條），本節為執行端高頻項摘錄，**衝突時以 SPEC §C 為準**。

### 0.2 防假綠（本 epic 的核心風險）
- **不得放寬既有測試斷言**。本 epic 動的是治理層，`pytest tests/governance -q` 現況 **298 passed**(B1 完工後基準;287 是 B1 前)，任一 Task 完成後這個數字只可增不可減。
- **每個新守衛必須有「改壞會轉紅」的證明**：SPEC §V 列了 31 條 mutation（M1–M34，編號有跳號）。Task 3.2 負責讓它們真的存在且真的會紅。
- **驗收命令的 rc 一律直接取，禁經 pipe**（`cmd | tail; echo rc=$?` 讀到的是 `tail` 的 rc——此坑 Claude 與委員都犯過）。

### 0.3 不可違反的既有行為
- `non_debt_legacy_events`（`committee_dispatch`／`committee_output`／`gate_deny`）**保留不動**，既有腳本仍在寫，砍掉會破壞現有 provenance。
- 下游消費者 `scripts/review_quorum_check.sh` 解析 `committee_dispatch.task_id`，**新事件不得破壞其解析**。
- 三個既有測試檔探針空心（`test_verify_gate{,_b3,_b4}.py`）已在 `gov_check.sh` 具名排除，**本 epic 不處理，也不得順手改**。

### 0.4 §A manifest 引用（不整段複製）
執行端如需知道「機器擋不住什麼」，讀 SPEC §A 誠實邊界 **14 條**(v2.9 新增第 11 條)。**實作時不得寫出與該節矛盾的註解或錯誤訊息**（例：不得在錯誤訊息裡宣稱「已保證唯一」，SPEC 寫的是 fail-closed 而非無競態）。

---

## §B 批次執行策略

> **拓撲**：Phase 0 是所有 Task 的前置；Phase 1 內 Task 1.1 是 1.2／1.3 的前置；Phase 2 依賴 Phase 1；Phase 3 依賴 Phase 2。

| Batch | 含 Task | **批內順序** | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|---|
| **B1** | Task 0.1 | — | 無 | registry 契約對齊 **+ `--rebuild` 就地升級（新控制流，含三道守衛）** | **中** |
| **B2** | Task 1.1 | — | B1 | **鎖與原子 predicate+append 是整台機器的地基，單獨一批單獨審**——R8 codex 的 P0 就出在這裡（自鎖 vs TOCTOU），不與消費端混批 | **中** |
| **B3** | Task 1.2、1.3 | **1.2 → 1.3** | B2 | 兩者皆為 `audit_append.sh` 的消費端，共用同一組 fail-closed 前置，合批可一次驗「開債→交件」完整鏈。**順序不可顛倒**：1.3 的六道前置全部要比對 1.2 寫入的欄位（含 `brief_sha256`），先做 1.3 會無契約可依 | **中** |
| **B4** | Task 2.1、2.2 | **2.1 → 2.2** | B3 | 帳本（只讀）與銷帳（唯一寫入路徑）互為驗證對象，分批會造成半套狀態無法端到端測。**順序不可顛倒**：2.2 的 `--abandon` 要呼叫 2.1 的 `_round_exists_single()` | **大** |
| **B5** | Task 3.1、3.2 | **3.1 → 3.2** | B4 | 擋門與 mutation 回歸須同批，否則「閘上線但探針未驗」＝假綠窗口。**順序**：先上閘再驗探針（探針要測的正是閘的行為） | **中** |

> **⚠️ 本 epic 整體是「大任務」**（SPEC RISK-HIT **b、c**）。上表的「規模」欄僅指**單批派工的工作量**，**不是**任務分類。**每一批都走完整管線**（SPEC/TODO 已備 → 實作 → **兩個非實作者家族** code review）。

**批次間 Gate（每批完成後、派下一批前必跑，rc 直接取）**：
```
bash scripts/gov_check.sh                    # 須 rc=0
pytest tests/governance -q                   # 須 >=298 passed，且不得有既有測試轉紅
bash scripts/restore_golden_inventory.sh     # 跑完測試後還原 golden inventory 副作用
```

**B1 額外 Gate（`GROK-R1-P2-03`）**：`--rebuild` 的完整行為 oracle 掛在 SPEC Task 2.2 驗證段（B4 才跑），故 B1 的 `gov_check`＋287 **抓不住「旗標在、升級假」**。B1 收批前須**提前跑其中兩條**：
```
# happy path：discovery + OPEN + audit 恰一筆 → 升級成功且 mode 轉 review
# 反向拒  ：review → discovery 必須 rc≠0
```
> ⚠️ `pytest tests/governance -q` 要 **110 秒**，**丟背景跑**，否則看起來像當機。

**每批派工的固定合約**（照 `docs/MULTI_AGENT_ORCHESTRATION.md`）：實作端寫碼 → Claude 只讀 diff + 測試 + 摘要（**diff 既有測試斷言防假綠**）→ **兩個非實作者家族** code review → finding 由**原提出方**重跑同一反例確認關閉。

---

## Phase 0 — SoT 對齊

> **目標**：消滅「SPEC 說 4 事件、registry 檔仍是 11 事件」的矛盾。
> **完成後系統狀態**：`scripts/audit_events.json` 為 v2 形狀；`reconcile_build.sh` 支援 `--mode`／`--rebuild`；**尚無任何債務行為**（無腳本讀它）。

### Task 0.1 — `scripts/audit_events.json` 砍成 v2 契約 + lock 工具鏈支援 identity binding
- **SPEC ref**：Task 0.1（改法①–⑨，含⑨③ `--rebuild`）　**目標**：把 registry 與 lock 工具鏈改成 v2 契約。
- **輸入**：現行 `scripts/audit_events.json`（v1，11 事件）／`scripts/reconcile_build.sh`／`scripts/write_sources_lock.sh`
- **輸出**：v2 形狀 registry（4 事件／3 狀態／2 結果態／新增 `abandon_kind`）＋ 兩支 lock 工具的新旗標
- **實作要點**：
  1. **registry 砍改**（改法①–⑧）：逐容器掃描，**任何以事件名為鍵或值的結構**（`required_fields_per_event`／`clear_kind_event_map`／`family_valued_fields`／`hardcode_scan_exemptions`／`event_object_allowed_keys`）殘留指向已刪事件即 fail-closed。**這是 R2 兩家共同抓到的漏點，不是可選項。**
  2. **`reconcile_build.sh` 新增 `--mode review|discovery`**（具名旗標、位置無關、**預設維持 `discovery`** 以免破壞既有呼叫）。偽碼：
     ```
     mode=discovery                       # 預設不變
     while parse_args; do
       case $1 in --mode) mode="$2"; shift 2 ;;
                 --rebuild) rebuild=1; shift ;;   # 見要點 4
       esac
     done
     [ "$mode" = review ] || [ "$mode" = discovery ] || die "unknown mode"
     ```
  3. **從 audit 反查 `round_id`**：
     ```
     _lookup_round_id() {   # $1=session_name
       hits=$(grep_committee_round_open_by_session "$1")
       n=$(count_lines "$hits")
       [ "$n" -eq 1 ] || die "session_name 命中 $n 筆(需恰 1)"   # 0 或 >=2 一律 fail-closed
       extract_round_id "$hits"
     }
     ```
     **不得做「取最新／取第一筆」等隱含選擇**——這是 R6 兩家共同要求。
     ⚠️**v2.9 收窄（B1 實作階段打回的 bootstrap P0，三家一致）——反查的觸發條件是「產生 `review` lock 時」，不是「建立 session 時」**：

     | 路徑 | audit 反查 | 額外守衛 |
     |---|---|---|
     | fresh `--mode discovery`（**預設**） | **不做**（不需 `round_id`） | 無 |
     | fresh `--mode review` | **必做**：恰一筆 | — |
     | `--rebuild`（`discovery → review`） | **必做**：恰一筆 | 該輪須 `OPEN`；只准單向 |

     ⚠️**且此不變式須涵蓋【所有】review-mode lock writer 路徑，不得只修 `reconcile_build.sh`**：`write_sources_lock.sh` 是**公開**入口，**一律拒收呼叫端傳入的 `--round-id`**，identity 由 writer 自 audit 導出（以 session basename ＝ `session_name` 為鍵）。只修一支會留下旁路，不變式不成立（**這是主委原提案的漏洞，由 codex 抓出**）。
  4. **`--rebuild` 就地升級**（改法⑨③，**R7/R8 連兩輪的 P0 出處，最容易做錯**）：
     ```
     if [ "$rebuild" = 1 ]; then
       # ── 取值步驟不可省（v1.0 直接用了未初始化的 $round_id／$existing_mode）──
       session_lock="$(_session_dir "$session")/sources.lock"   # ← 取值來源不可省
       [ -f "$session_lock" ] || die "--rebuild 需既有 session"  #   (v1.1 直接用了未定義的
       round_id=$(_lookup_round_id "$session")        # ← 內含「恰一筆」守衛，見要點 3
       existing_mode=$(read_mode_from_lock "$session_lock")     #    $session_lock)
       # ── 三道守衛全過才放行（見 SPEC Task 2.2 1b）──
       assert_round_state_is_OPEN "$round_id"
       assert_upgrade_direction_is_discovery_to_review "$existing_mode" "$mode"
       # 跳過「session 已存在即 exit 2」(reconcile_build.sh:31-34)
       # 就地改寫既有 lock 的 mode 欄 + 自 audit 重填 round_id
       # 其餘欄位(來源清單/各來源 hash/expected_roster)一律不變
     fi
     ```
     **⚠️ 絕對禁止**用 `write_sources_lock.sh --force` 或設 `GOVERNANCE_TEST_HARNESS=1` 達成升級——**正式路徑必須自給自足**（R5 已因此廢除過一整套設計）。
- **修改檔案（到函式名）**：`scripts/audit_events.json`（資料檔全檔）／`scripts/reconcile_build.sh` — 參數解析區塊、新增 `_lookup_round_id()`、新增 `_rebuild_guards()`、既有 session-exists 拒絕點（`:31-34`）／`scripts/write_sources_lock.sh` — 新增 `round_id` 欄寫入、`mode` 就地改寫路徑
- **既有 caller**：`reconcile_build.sh` 現有呼叫端（`handoffs/` 下各 reconcile 流程、`scripts/gate.sh` 的 completeness 閘）——**因 `--mode` 預設不變，既有呼叫不需修改**；此假設須由驗證中的 `gov_check` rc=0 證實
- **不可做**：不得在 SPEC 正文或本 TODO 重列 registry 的欄位表／枚舉值（會回到漂移）；不得為了通過而保留 v1 事件；不得新增第 5 種事件
- **邊界**：①砍除的事件名若仍被任何 `scripts/*.sh` 引用 → **先修引用再砍**，不得留懸空引用 ②`non_debt_legacy_events` 誤砍 → 既有 `verify_task_provenance` 消費端會壞，須實跑既有測試確認 ③既有 reconcile session（`handoffs/reconcile/*/sources.lock`）無 `round_id` 欄 → **僅 `completeness_check.sh` 等既有唯讀消費端**須容忍缺欄不崩潰；**`debt_clear.sh` 一律 fail-closed**（缺 `round_id` 即拒銷帳）。
  > ⚠️ **這條邊界是起草者自行新增、SPEC 沒有的**（`CODEX-R1-P1-06` 指出未限定適用端會與「銷帳必須 `lock.round_id == --round-id`」的 fail-closed 契約產生歧義）。已限縮如上；**若實作端發現此限縮仍與 SPEC 衝突，停手回報，不得自行放寬。**
- **風險緩解**：SPEC §RISK（b 跨模組共用路徑）
- **驗證**：測試檔 `tests/governance/test_registry_v2_shape.py`；通過條件**見 SPEC Task 0.1 驗證段**（12 項實跑清單，含逐容器清點印 0、`--help` 印出 `--mode`／`--rebuild`；**不存在／重複 session 名兩道 fail-closed 僅適用 `--mode review`**，同一組名稱在**預設 `discovery`** 下須 **rc=0**——v2.9 收窄的正向驗收，**不驗這條等於沒驗收窄，bootstrap P0 會靜默復活**）
- **存活至**：永久保留　**覆蓋風險**：無

---

## Phase 1 — 留痕

> **目標**：派工即記債、每家交件結果留痕。
> **完成後系統狀態**：audit 會長出 `committee_round_open`／`committee_family_result`，但**還沒有人讀它**（不擋任何事）。

### Task 1.1 — `audit_append.sh`：唯一寫入點 + 原子 predicate+append
- **SPEC ref**：Task 1.1（改法①–⑥）　**目標**：所有債務紀錄只能經此腳本寫，序號連續、可稽核。
- **輸入**：`scripts/audit_events.json`（Task 0.1 對齊後的 v2 形狀）　**輸出**：新增 `scripts/audit_append.sh`
- **實作要點**：
  1. **`mkdir` 原子鎖**保護「讀尾端序號 → +1 → append」為單一臨界區。**禁 `flock`**。取不到鎖時**有上限的重試 + 逾時 fail-closed**（不得無限等待）。
     ```
     _acquire_lock() {          # 回傳 0=取得 1=逾時
       i=0
       until mkdir "$LOCKDIR" 2>/dev/null; do
         i=$((i+1)); [ "$i" -ge "$MAX_RETRY" ] && return 1
         sleep "$RETRY_INTERVAL"
       done
       return 0
     }
     _release_lock() { rmdir "$LOCKDIR" 2>/dev/null; }
     ```
  2. **`producer` 由本腳本強制填入**，呼叫端指定即忽略覆寫（防偽造來源）。
  3. **事件名／必填欄位讀 registry**，缺欄 fail-closed；陣列欄位以 `--field k=@<json>` 傳入，**非法 JSON 拒寫**。
  4. **legacy 事件不受序號規則管**，不參與連續性掃描。
  5. **原子 predicate+append `--require-absent-session <name>`（改法⑥；R8 codex P0 的收口）**：
     ```
     # ── 內部 API 命名契約（不可省，否則實作端會寫出自鎖）────────────────
     #   *_locked()  = 「假設鎖已被呼叫端持有」，**函式內一律不得再 _acquire_lock**
     #   無後綴者     = 自行取鎖的對外入口，**不得被 *_locked() 內部呼叫**
     #   本檔僅有兩個對外入口：main 的一般 append、與 _append_with_absent_guard
     # ────────────────────────────────────────────────────────────────
     _next_seq_locked()   { ... }   # 讀尾端序號，假設持鎖
     _scan_session_locked() { ... } # 掃 session_name，假設持鎖
     _append_event_locked() { ... } # 寫入一筆，假設持鎖

     _append_with_absent_guard() {   # $1=session_name, 其餘=事件欄位
       session="$1"; shift                          # ← 必須 shift，否則 session 名
                                                    #   會被當成事件參數傳下去
       _acquire_lock || return 2                    # ← 鎖只在這裡取一次
       _scan_session_locked "$session"              # 三態，不可只用 if/then
       case $? in                                   # 0=找到 1=沒找到 其餘=掃描出錯
         0) _release_lock; return 1 ;;              #   已存在 → 不 append、rc≠0
         1) : ;;                                    #   確認不存在 → 往下 append
         *) _release_lock; return 2 ;;              #   ← 掃描錯誤必須 fail-closed
       esac                                         #     (v1.1 把所有非 0 當「沒找到」
                                                    #      → 掃描壞掉時照樣 append)
       _append_event_locked "$@"                    # ← 寫入也在同一把鎖內
       rc=$?                                        # ← 必須先接住 rc
       _release_lock                                #   (_release_lock 回 0，
       return "$rc"                                 #    不接 rc 會讓失敗被吞掉)
     }
     ```
     **三個各自獨立的坑（R1 三家各抓到一個，照舊版偽碼實作必中）**：
     ①**缺 `shift`** → `session_name` 被當事件參數（`CODEX-R1-P0-02`）
     ②**內部函式若自行 `_acquire_lock` → 自鎖**（`GROK-R1-P0-02`／`COMPOSER-R1-P1-03`）→ 故用 `*_locked` 命名契約在偽碼層關死
     ③**rc 不傳播** → `_release_lock` 回 0 使函式回 0，`committee_run` 以為開債成功而啟動 `cx_run`，但 audit 無 `committee_round_open`（`GROK-R1-P0-03`）——**恰好打穿 Task 1.2 改法③所依賴的前提**
     **⚠️ 為何判定必須長在本腳本**：鎖由本腳本持有。呼叫端先取鎖再呼叫本腳本 → **本腳本再取同一把鎖 → 自鎖**；呼叫端先放鎖再 append → **TOCTOU 回歸**。兩條路都是死的，**唯一可執行形態是把判定搬進持鎖者**。
     **不得**新增任何繞過本腳本的旁路；**不得**提供 reentrant 鎖或鎖交接 API（**兩者都會製造新的可繞面**）。
- **修改檔案（到函式名）**：新增 `scripts/audit_append.sh` — **取鎖入口**：`_acquire_lock()`／`_release_lock()`；**lock-held 內部 API（一律不得自行取鎖）**：`_next_seq_locked()`／`_scan_session_locked()`／`_append_event_locked()`；**對外入口（自行取鎖）**：`_append_with_absent_guard()`／`main()` 一般 append 路徑
- **既有 caller**：新建，無
- **不可做**：不得讓任何 Task 繞過本腳本；不得硬編事件名；**不得把耗時操作放進臨界區**（鎖內只做讀序號／掃描／append）；**`*_locked()` 內一律不得 `_acquire_lock`**；**不得提供 reentrant 鎖或鎖交接 API**（SPEC 明禁，兩者都製造新可繞面）
- **邊界**：①audit 檔不存在 → **建立而非崩潰** ②取鎖逾時 → fail-closed ③registry 缺檔／JSON 壞 → fail-closed
- **風險緩解**：SPEC §RISK（b 跨模組共用路徑、c 難回退）
- **驗證**：測試檔 `tests/governance/test_debt_emit.py`；關鍵測試函式 `test_session_uniqueness_is_atomic_with_append`（對應 §V **M34**）；通過條件**見 SPEC Task 1.1 驗證段**（含兩程序併發各寫 100 筆序號 == `range(1,201)`、`--require-absent-session` 三態驗收、**呼叫端自行持鎖後呼叫須不得成功**）
- **存活至**：永久保留　**覆蓋風險**：無

### Task 1.2 — `committee_run.sh` 開債
- **SPEC ref**：Task 1.2（改法①–⑦）　**目標**：派工即記一筆債，輪次編號主委不可指定。
- **輸入**：`audit_append.sh`（Task 1.1）　**輸出**：`scripts/committee_run.sh` 改造（現 60–75 行區塊）
- **實作要點**：
  1. **`round_id` 由本腳本 mint（UUID v4），主委不得指定**——否則可偽造編號假裝已開債。
  2. **寫入時機卡死**：`gate.sh dispatch` 成功之後、啟動 `cx_run.sh` 之前；**寫入失敗 → `exit!=0` 且不得啟動 `cx_run`**。
  3. `task_id` 從**透傳 argv** 解析 gate 的 `--task-id`，**不另發明同名旗標**；缺則 rc≠0。
  4. 以 env `ROUND_ID` 傳給 `cx_run.sh`。
  5. **（改法⑥）`committee_round_open` 必記欄位——不得用 `...` 帶過**（`COMPOSER-R1-P1-01`／`CODEX-R1-P1-03`）：
     `round_id`／`task_id`／**該輪家族名單**／**每家族的 expected 產出路徑**／`brief_path`／**`brief_sha256`**。
     > **`brief_sha256` 特別點名**：Task 1.3 把「本次 brief 的 sha256 == 開債時記錄的值」列為不可缺的 fail-closed 前置，**但寫入端就是這裡**。漏寫 → 該前置永遠無基準可比 → **R2 codex 的 P0（換 brief 掛既有輪次）復活**。
     **具體欄位名以 registry 為準**（Task 0.1 對齊後的 v2 形狀），**本 TODO 不重列值**。
  6. **`--session <name>` 必填**；唯一容許的寫入形態：
     ```
     bash scripts/audit_append.sh --require-absent-session "$session" \
          --event committee_round_open \
          --field round_id="$round_id"      --field task_id="$task_id" \
          --field brief_path="$brief"       --field brief_sha256="$brief_sha" \
          --field session_name="$session" \
          --field participants=@"$participants_json" \
          --field expected_outputs=@"$outputs_json" \
       || die "session_name 重複或寫入失敗"    # ← rc 必須傳播（見 Task 1.1 坑③）
     ```
     > ⚠️ **欄位名一律以 registry 為準，不得自行發明**（`CODEX-R2-P1-02`）：家族名單欄在現行 SoT 是 **`participants`**，v1.1 偽碼寫成 `families` 是起草者臆造，**SPEC 未授權改名**。
     > 上列 `--field` 名稱**僅為形態示範**；**實作前必須 `grep` `scripts/audit_events.json` 逐一核對**（Task 0.1 對齊後的 v2 形狀），**不符即以 registry 為準**。
     **本腳本不得自行掃描後再 append，也不得自行取鎖後呼叫 `audit_append.sh`。**
  7. **不得在開債時建立 session 目錄或寫入其中任何檔案**——session 目錄是 `reconcile_build.sh` 在**委員交件之後**才建立的，**開債當下不存在**（v2.4 曾因誤解此時序而設計出整套不可達流程，R5 廢除）。
- **修改檔案（到函式名）**：`scripts/committee_run.sh` — 參數解析新增 `--session`、新增 `_mint_round_id()`、新增 `_open_debt()`（呼叫 `audit_append.sh`）、既有 dispatch→cx_run 之間的控制流
- **既有 caller**：Claude 的派工流程（本 session 已用過多次）；`--session` 為新必填參數，**所有現有呼叫都要加**，須在批次 Gate 實測一次真派工
- **不可做**：不得讓主委指定新 `round_id`；不得對 N=1 略過開債；**不得實作「中途補派」**（使用者裁決 6：要加人就重開一輪）
- **邊界**：①N=1 仍開債 ②只含 advisory 家族仍開債 ③寫入失敗不啟動 `cx_run`
- **風險緩解**：SPEC §RISK（b、c）
- **驗證**：測試檔 `tests/governance/test_debt_emit.py`；通過條件**見 SPEC Task 1.2 驗證段**（含派 3 家後恰 1 筆、派 1 家也必須寫、缺 `--session` rc≠0、**開債後 session 目錄仍不存在**、第二次同名 rc≠0 且 audit 不增長、**兩程序並行同名恰一筆成功**）
- **存活至**：永久保留　**覆蓋風險**：無

### Task 1.3 — `cx_run.sh` 記每家結果
- **SPEC ref**：Task 1.3（改法①–⑦）　**目標**：每家交件與否留痕；並限制直呼危害。
- **輸入**：`ROUND_ID`（Task 1.2 傳入）　**輸出**：`scripts/cx_run.sh` 改造
- **實作要點**：
  1. **家族名由 `$1` 直取**，**不得從路徑或 review_role 推導**（推導錯會記成 `unknown`，整本帳報廢）。
  2. 🔴 **`result_state` 三值**（**R 修訂／P16 v3.0，2026-08-04**；本條原為二值，已作廢）
     〔`COMPOSER-R8-P1-01`＋`GROK-R8-P1-03`＋`CODEX-R8-P1-04` 三家獨立命中：
     本 TODO 仍鎖二值，與 v3.0 凍結契約及已上線 runtime 矛盾，**若仍被當派工 SoT 會重現 R4 orphan-success 語意**〕：
     - `success`＝產出存在且非空且 `cli_rc==0`，**且**（brief-kind ∈ {review,consult,closure} 時）格式合規
     - `format-failed`＝`cli_rc==0` 且產出非空但格式檢查失敗（含 checker 缺席的 fail-closed）；**非空** `output_sha256`；process **exit 3**
     - `failed`＝`cli_rc!=0` 或產出空；`output_sha256` 空字串
     🔴 **格式檢查必須在 audit append 之前**。**CLI 失敗仍要寫一筆並帶 `cli_rc`，不得靜默。**
     **權威定義見** `docs/P16_COMMITTEE_DEBT_SPEC.md` v3.0 Task 1.3 改法②。
  3. **六道 fail-closed 前置**（缺一不可）：`ROUND_ID` 已設／audit 有對應 `committee_round_open`／該家族在該輪名單內／產出路徑與登記一致／**本次 brief 的 sha256 == 開債時記錄的 brief sha256**／**該 `(round,family)` 最新 `result_state` 不是 `success`**。
     > 第 5 道是 R2 codex 的 P0：沒有它可以**換一份 brief 掛在既有輪次上**。
     > 第 6 道防「一直重跑到拿到想要的答案」。
  4. **產出指紋 `output_sha256`**（🔴 **三態，R 修訂／P16 v3.0**〔`COMPOSER-R9-P2-02`：本欄原只寫兩態，
     與同檔已更新的三值正文殘留漂移——**主委改了正文卻漏改驗證欄**〕）：
     `success` 填實際 sha256／**`format-failed` 亦填非空 sha256**（產出存在，只是格式不合規）／
     **`failed` 填空字串**（R2 codex P1-04：v2.1 曾同時要求「失敗仍寫」與「每筆須有非空 sha」，兩者互斥）。
     **空 sha 例外僅 `failed`**，三態分別驗，不得混為一條。
  5. **同輪重派明確允許（限尚未成功者）**，不需開新輪、不需補派機制；每次重派**各寫一筆，append-only 不覆蓋**。**不設重派次數上限。**
- **修改檔案（到函式名）**：`scripts/cx_run.sh` — 新增 `_assert_round_preconditions()`（六道）、`_compute_output_sha()`、`_emit_family_result()`；既有 CLI 呼叫收尾處
- **既有 caller**：`scripts/committee_run.sh`（Task 1.2）；**可被直呼**（SPEC §A 誠實邊界 2 已列，本版以 membership 檢查限制危害但擋不住）
- **不可做**：不得從產出路徑推導家族；**不得把 CLI 執行放進鎖的臨界區**（CLI 動輒數分鐘，會鎖死整台機器）
- **邊界**：①`ROUND_ID` 未設 → 拒派 ②並發 3 家 → 3 筆完整不交錯 ③audit 檔不存在 → 建立而非崩潰
- **風險緩解**：SPEC §RISK（b）
- **驗證**：測試檔 `tests/governance/test_debt_emit.py`；通過條件**見 SPEC Task 1.3 驗證段**（含 family 非 `unknown`、對最新已 `success` 家族重派 rc≠0 且 audit 零新增、**`success`/`failed` 兩態的 `output_sha256` 分別驗不得混為一條**）
- **存活至**：永久保留　**覆蓋風險**：無

---

## Phase 2 — 帳本與銷帳

> **目標**：由客觀紀錄算出欠帳，並提供唯一銷帳路徑 + 逃生口。
> **完成後系統狀態**：帳本可查、債可銷、可放棄，**但還沒擋任何門**。

### Task 2.1 — `debt_ledger.sh`：只讀紀錄算未結案債
- **SPEC ref**：Task 2.1（改法①–⑦）　**目標**：由客觀紀錄算出哪些輪還欠著。
- **輸入**：audit 流水帳　**輸出**：新增 `scripts/debt_ledger.sh`（**不另存狀態檔**）
- **實作要點**：
  1. **只認 `startswith("{")` 的 JSON 行**；**以 `{` 開頭但 JSON 解析失敗 → fail-closed rc=2**（V1 codex：半截寫入不得被靜默忽略）。
  2. 狀態推導：每筆 `committee_round_open` 即一筆債 → 有合法 `committee_debt_clear` → `CLOSED`；有 `debt_abandon` → `ABANDONED`；其餘 `OPEN`。
  3. **（改法③）cutoff 之前的紀錄一律不計**：值**讀 registry**，**僅 `GOVERNANCE_TEST_HARNESS=1` 可覆寫**。
     > 漏做的後果：SPEC 驗證項「cutoff 前紀錄 → 0 筆」直接不過；且開發機的歷史 audit 會被算成一堆 OPEN 債。
  4. **白名單事件序號缺號／重號 → fail-closed**。
  5. **`--abandon` 的讀取路徑例外（防死鎖，V1 三家一致的 P0）**：判定「該輪是否存在」時**只做該 `round_id` 的單筆存在性掃描，不跑全域序號連續性檢查**。**正常銷帳與擋門路徑仍維持 fail-closed 不放寬。**
     > **責任落點（`CODEX-R1-P1-04`）**：本 Task 負責**提供**這條不做連續性檢查的查詢介面（如 `_round_exists_single()`）；**呼叫端是 `debt_clear.sh --abandon`（Task 2.2）**。兩邊都要有落點，否則 escape path 的 owner 會漂移。
     > ⚠️ **不得宣稱這解決了所有死鎖**（R2 grok 更正了起草者的錯誤認定）：放棄之後 `--has-open` 仍會 rc=2、派工照樣被擋。**帳本壞掉本來就不該放行**，復原須人工修帳（SPEC §A 2c 已明列，在信任模型之外）。
  6. **同一 `(round_id, family)` 多筆結果時取序號最大那筆**——重派成功後不得再被舊的 `failed` 拖住。
  7. 子命令：`--list`／`--has-open`（**rc 0=無債、1=有債、2=fail-closed**）／`--abandoned-count`（**依 `abandon_kind` 分開輸出兩個數字**，支撐使用者裁決 5 與 7 的逐步修正）。偽碼骨架（`GROK-R1-P2-01`：本 Task 原缺偽碼）：
     ```
     _cmd_has_open() {
       _assert_seq_continuity || return 2          # 缺號/重號 → fail-closed
       # ⚠️ 不可用 pipeline：`a | b | wc -l` 只回最後一段的 rc，
       #    _iter_json_lines 的 JSON parse 失敗(rc=2)會被整條吞掉
       #    → 違反本 Task 自己宣告的 malformed JSON fail-closed (CODEX-R2-P1-04)
       tmp=$(mktemp)
       _iter_json_lines > "$tmp"; rc=$?             # ← 先落地並接住 rc
       [ "$rc" -ne 0 ] && { rm -f "$tmp"; return 2; }
       n=0
       while read -r r; do
         [ "$(_round_state "$r")" = OPEN ] && n=$((n+1))
       done < <(_filter_round_open_after_cutoff < "$tmp")
       rm -f "$tmp"
       [ "$n" -eq 0 ] && return 0 || return 1      # 0=無債 1=有債 2=fail-closed
     }
     ```
- **修改檔案（到函式名）**：新增 `scripts/debt_ledger.sh` — `_iter_json_lines()`／`_assert_seq_continuity()`／`_latest_result_per_family()`／`_round_state()`／`_cmd_list()`／`_cmd_has_open()`／`_cmd_abandoned_count()`
- **既有 caller**：新建；Task 2.2 與 Task 3.1 將呼叫
- **不可做**：**不得另存狀態檔**（多一份就多一個可竄改、可不同步的地方）；不得靜默自動過期
- **邊界**：①audit 缺失 → fail-closed ②audit 空 → 無債放行 ③同一 `round_id` 兩筆 `committee_round_open` → fail-closed
- **風險緩解**：SPEC §RISK（b、c）
- **驗證**：測試檔 `tests/governance/test_debt_ledger.py`；通過條件**見 SPEC Task 2.1 驗證段**（含 **audit 存在但零 JSON 行 → 無債 rc=0**，14 檔隔離測試依賴此）
- **存活至**：永久保留　**覆蓋風險**：無

### Task 2.2 — `debt_clear.sh`：唯一銷帳路徑 + 逃生口
- **SPEC ref**：Task 2.2（改法 1／1b／2／2c 等）　**目標**：跑機械合併且 0 掉項才算還債；並提供防死鎖的人工放棄。
- **輸入**：`debt_ledger.sh`（2.1）＋`completeness_check.sh`（既有）　**輸出**：新增 `scripts/debt_clear.sh`
- **實作要點**：
  1. **銷帳六項全成立才寫 `committee_debt_clear`**（逐項見 SPEC Task 2.2 改法 1 ①–⑥）。偽碼：
     ```
     _cmd_clear() {
       # ⚠️ 每一道都必須 `|| return`——本檔不假設 `set -e`（CODEX-R2-P1-05）
       #    v1.1 偽碼六道並排無 rc 分支 → 任一道失敗仍會走到 _emit_clear
       _assert_round_is_OPEN       "$round_id"        || return 1  # ① 該輪處於 OPEN
       _run_completeness --lock    "$lock"            || return 1  # ② rc 直接取不經 pipe
       _assert_lock_mode_is_review "$lock"            || return 1  # ③ discovery 不強制附佐證
       _assert_identity_binding    "$lock" "$round_id"|| return 1  # ④ lock.round_id==--round-id
       _assert_roster_equals       "$lock" "$round_id"|| return 1  #   ④的**附加**檢查(見下)
       _assert_all_families_success_and_sha_match     || return 1  # ⑤ 防交件後替換內容
       lock_sha=$(shasum -a 256 "$lock" | cut -d' ' -f1) || return 1   # ⑥ 只做記錄
       _emit_clear --field lock_sha256="$lock_sha"
     }
     ```
     **⚠️ 編號務必對齊 SPEC，v1.0 曾把 ⑥ 寫成 roster 而漏掉 lock sha256**（`GROK-R1-P1-01`）：
     - **SPEC ⑥＝「寫入的 `committee_debt_clear` 記下當次 lock 檔 sha256 供事後稽核」**，且 SPEC 明註**只做記錄、不作綁定判準**（lock 在時間上晚於開債，開債當下無從預存可比對的值）。**漏寫＝少一個稽核欄。**
     - **roster 檢查是 ④ 底下的附加項，不是第六道門檻**。且它要的是**集合相等**（`CODEX-R1-P1-05`：v1.0 命名 `_assert_roster_covers` 暗示 subset，實作端可能做成包含關係）→ **更名 `_assert_roster_equals()` 並明確傳入兩側集合**（lock 側 `expected_roster` vs `committee_round_open` 側家族名單欄位，**欄位名以 registry 為準**）。SPEC 已老實註明此檢查**零鑑別力**（本專案每輪都派同樣三家），**不可單獨作為綁定**。
  2. **對 `sources.lock` 一律只讀**，不得建立或修改任何欄位（綁定值不得由銷帳端產生，否則自填自驗）。
  3. **`mode != review` 時拒絕**，並在錯誤訊息印出建立與升級命令（`reconcile_build … --mode review` 與 `… --rebuild`）。
  4. **逃生口 `--abandon`**：`reason`／`approver`／`kind` **三者皆必填非空**；`kind` 屬於 `no-findings-expected|collection-failed`（**兩種分開計數**，使用者裁定「路二」）。**不得自動放棄**，一律人工且留痕。
     - **`reason` 另有長度下限**（`CODEX-R2-P1-06`）：registry 的 `constants.reason_min_chars`（**現值 20**）；**值一律讀 registry，不得硬編**。低於下限 → rc≠0。v1.1 只寫「非空」＝漏落地。
     - **CLI `--kind` → 事件欄位的寫入契約**（`CODEX-R2-P1-07`）：`_emit_abandon()` 須把 CLI 的 `--kind` 值寫入 `debt_abandon` 的 **`abandon_kind`** 欄（欄名以 registry 為準，Task 0.1 改法③新增），並先驗其 ∈ `enums.abandon_kind`；**不在 enum 內 → rc≠0**。v1.1 只有函式名、沒有欄位契約。
     ```
     _cmd_abandon() {
       [ -n "$reason" ]   || return 1
       [ -n "$approver" ] || return 1
       min=$(_registry_get constants.reason_min_chars)      # 不硬編 20
       [ "${#reason}" -ge "$min" ]        || return 1
       _assert_kind_in_enum "$kind"       || return 1        # ∈ enums.abandon_kind
       _round_exists_single "$round_id"   || return 1        # ← Task 2.1 提供，
                                                             #   不跑序號連續性檢查
       _emit_abandon --field abandon_kind="$kind" \
                     --field reason="$reason" --field approver="$approver"
     }
     ```
  5. **重複銷帳 → 冪等 no-op**；`ABANDONED` 後再銷 → rc≠0。
- **修改檔案（到函式名）**：新增 `scripts/debt_clear.sh` — `_cmd_clear()`／`_cmd_abandon()`／`_assert_round_is_OPEN()`／`_run_completeness()`／`_assert_lock_mode_is_review()`／`_assert_identity_binding()`／**`_assert_roster_equals()`**（集合相等，非 covers）／`_assert_all_families_success_and_sha_match()`／`_emit_clear()`（含 `lock_sha256` 欄）／`_emit_abandon()`。
  **`--abandon` 須呼叫 Task 2.1 的 `_round_exists_single()`**（不做序號連續性檢查的查詢介面），**不得自行實作等效掃描**
- **既有 caller**：新建；由主委手動執行（**不經 dispatch 閘**，見 SPEC §A FACT-RECEIPT 9）
- **不可做**：不得接受 `waived:` 字串當銷帳；**不得讓任何旗標繞過銷帳的六項綁定或放棄的四項必填**；不得自動放棄
- **邊界**：①`committee_round_open` 不存在 → 拒 ②lock 的 `round_id` 與 `--round-id` 不符 → 拒 ③`completeness` 回 DEGRADED（rc=3）→ **不得銷帳**
- **風險緩解**：SPEC §RISK（b、c）
- **驗證**：測試檔 `tests/governance/test_debt_clear.py`；通過條件**見 SPEC Task 2.2 驗證段**（含拿 A 輪 lock 銷 B 輪 rc≠0、`mode=discovery` rc≠0、產出檔交件後被改動 rc≠0、**`--abandon` 在 OPEN 未逾期時 rc=0**、**序號缺號時 `--has-open` rc=2 但 `--abandon` 仍 rc=0**，以及 **1b `--rebuild` 行為驗收**的 happy path + 5 條負例，含「**未設 `GOVERNANCE_TEST_HARNESS` 也能完成**」）
- **存活至**：永久保留　**覆蓋風險**：無

---

## Phase 3 — 擋門與回歸

> **目標**：有未清債 → 拒發新派工 token；並證明所有守衛「改壞會轉紅」。
> **完成後系統狀態**：**機器上線**。

### Task 3.1 — `gate.sh` 債務閘 + `gate_check.sh` 重查
- **SPEC ref**：Task 3.1（改法①–⑤）　**目標**：有未清債 → 拒發新派工 token（含實作）。
- **輸入**：`debt_ledger.sh`（2.1）　**輸出**：`scripts/gate.sh`／`scripts/gate_check.sh` 改造
- **實作要點**：
  1. **`_check_open_debt()` 的唯一呼叫點**＝dispatch 分支**必填欄位檢查之後、既有 completeness 閘之前**（位置寫死，不得散佈多處）。偽碼骨架（`GROK-R1-P2-01`：本 Task 原缺偽碼）：
     ```
     # gate.sh dispatch 分支內
     _assert_required_flags "$@"          # 既有：--intent/--risk/--facts-asked/...
     _check_open_debt || exit 1           # ← 新增，唯一呼叫點
     _run_completeness_gate "$@"          # 既有
     ...發 token...

     _check_open_debt() {
       audit=$(_resolve_audit_path)       # registry 登記路徑；DEBT_AUDIT_OVERRIDE 須綁 harness
       command -v bash >/dev/null && [ -x scripts/debt_ledger.sh ] \
         || { echo "debt_ledger 缺失"; return 1; }   # fail-closed
       bash scripts/debt_ledger.sh --has-open --audit "$audit"
       case $? in
         0) return 0 ;;                   # 無債 → 放行
         1) bash scripts/debt_ledger.sh --list; return 1 ;;   # 有債 → 全部列出後拒
         *) echo "帳本不可信(fail-closed)"; return 1 ;;
       esac
     }
     ```
  2. **判定極簡**：`debt_ledger.sh --has-open` 回報有債 → 拒發，**不分討論／實作**（使用者裁決 3）。
  3. audit 來源固定為 registry 登記路徑；測試隔離走**綁 `GOVERNANCE_TEST_HARNESS=1`** 的 `DEBT_AUDIT_OVERRIDE`，**不得讀未綁 harness 的 `GATE_DIR_OVERRIDE`**。
  4. `gate_check.sh` 對 fresh token **不再直接放行**，改為重查一次帳本（使用者裁決 4 的落地；**不做 token 指紋／時序機制**）。
     > ⚠️ SPEC §A 誠實邊界 1 已明列：`gate_check.sh:50` 的 executor 正則**不命中** `committee_run.sh`／`cx_run.sh`，故這條重查**幾乎不覆蓋官方入口**，**真正的擋門是 `gate.sh`**。**實作端不得在註解或訊息中宣稱 `gate_check` 是主擋門。**
  5. `debt_ledger.sh` 缺失或崩潰 → fail-closed。
  6. **效能驗收**：`gate_check` 單次 **< 100ms**（audit 是 append-only 只會變長，熱路徑每次重掃是 O(N)）。**超過即須改為只掃尾端 N 行或建索引。**
- **修改檔案（到函式名）**：`scripts/gate.sh` — 新增 `_check_open_debt()`、dispatch 分支插入點／`scripts/gate_check.sh` — fresh-token 放行點改為重查
- **既有 caller**：`gate_check.sh` 是 PreToolUse hook（**每次工具呼叫都跑**，故有 100ms 驗收）；`gate.sh dispatch` 是所有派工入口
- **不可做**：不得改寫既有守衛 V-A/V-B/V-C/V-M 內部；不得為了讓本 epic 自己的派工過關而開特例（**本 epic 自身派工同樣受管**）
- **邊界**：①空 audit ＝無債放行 ②多筆 open 債 → 全部列出，任一未清即拒 ③**本 epic 自身派工同樣受管**
- **風險緩解**：SPEC §RISK（b、c）
- **驗證**：測試檔 `tests/governance/test_debt_gate.py`；通過條件**見 SPEC Task 3.1 驗證段**（含**有 `OPEN` 債時實作派工帶 `--spec` 也 rc≠0**、`GATE_DIR_OVERRIDE` 指向空目錄但真 audit 有債仍 rc≠0、`DEBT_AUDIT_OVERRIDE` 未帶 harness rc≠0、**單次 `gate_check` < 100ms 附 receipt**）
- **存活至**：永久保留　**覆蓋風險**：無

### Task 3.2 — mutation 探針 + 既有測試回歸
- **SPEC ref**：Task 3.2 ＋ §V（M1–M34，共 31 條）　**目標**：證明每個守衛「改壞會轉紅」，且沒弄壞既有 287 測試。
- **輸入**：Phase 0–3 全部產出　**輸出**：mutation 探針測試 + 回歸 receipt
- **實作要點**：
  1. **（改法①）逐條對照 §V 的 31 條 mutation**，每類各**一常駐探針**，且實跑證明「閹割守衛後同輸入從綠轉紅、復原轉綠」。**不得只寫測試名交差**——R7 codex 的 P2-03 就是抓「只有測試名、沒有可執行 oracle」。
  2. **（改法②）探針以 Python 受測面書寫——這是 SPEC 預先選定的收口路徑，不是「遇到再說」**：
     - 新增 `tests/governance/_debt_probe_helper.py` 作為**薄封裝層**，把各 shell 腳本的判定入口包成 Python 函式（**內部 `subprocess` 呼叫真腳本**）。
     - 探針 **`monkeypatch` 該 helper 的模組常數**（腳本路徑、registry 路徑等）來注入變異。
     - **為何這樣就不是「假 monkeypatch」**：被 patch 的是**真正決定行為的變數**——換掉腳本路徑，跑的就真的是被變異過的腳本。這使探針天然滿足 `mutation_probe_static.py` 的判準。
     ```
     # _debt_probe_helper.py（骨架）
     AUDIT_APPEND = "scripts/audit_append.sh"      # <- 探針 monkeypatch 這個
     REGISTRY     = "scripts/audit_events.json"    # <- 或這個
     def append_event(*args, env=None):
         return subprocess.run(["bash", AUDIT_APPEND, *args], env=env, capture_output=True)
     ```
     > ⚠️ **不得**改成「就地變異真腳本」——2026-07-27 已實證：**直接為 shell 腳本寫探針會被判偽自證並使 `gov_check` 轉紅**。
  3. **（改法③）既有 287 測試逐檔跑**，轉紅者逐檔判定「真回歸」vs「fixture 契約更新」，**禁 skip／xfail／waiver**。跑完須 `bash scripts/restore_golden_inventory.sh` 還原副作用。
  4. **（改法④）14 個用 `GATE_DIR_OVERRIDE` 隔離的測試須補 `DEBT_AUDIT_OVERRIDE` + harness**（或於 `conftest.py` 層預設隔離空 audit）。
     > **不做的後果**：現有測試只隔離 token、**不隔離債務 audit**，開發機留有一筆 OPEN 債就會使**整個治理測試集假紅**，B5 永遠收斂不了。
     > 另：6 檔 10 處 `pop GOVERNANCE_TEST_HARNESS` 須**逐處確認不觸發 fail-closed**。
- **修改檔案（到函式名）**：新增 `tests/governance/_debt_probe_helper.py` — 模組常數 + 各腳本入口封裝函式；新增 `tests/governance/test_debt_mutations.py`（31 條 mutation 對應）；`tests/governance/conftest.py` — `DEBT_AUDIT_OVERRIDE` 隔離；既有 14 檔測試補隔離
- **既有 caller**：`scripts/gov_check.sh` 的探針健檢步驟；`scripts/mutation_probe_check.sh`
- **不可做**：**不得為通過靜態閘而塞入「與行為無關」的假 `monkeypatch`**（注意：patch helper 的模組常數**不屬於此類**，那正是 SPEC 指定的做法）；不得為求通過而放寬既有斷言
- **⚠️ 逃生條款（僅在改法②被證明不可行時啟用）**：若實測發現 helper 封裝法**仍**過不了靜態閘，**停手回報**，**不得自行塞假 `monkeypatch`、不得自行加豁免、不得自行改走別的路徑**（本 TODO v1.0 就是因為起草者自行改路徑而被三家判 P0）。
- **邊界**：①探針自身失效 → 由 `scripts/mutation_probe_check.sh` 抓 ②既有測試轉紅 → 逐檔判定，**禁 skip** ③**helper 封裝層本身出錯 → 該層須有自己的單元測試**
- **風險緩解**：SPEC §RISK（b、c）
- **驗證**：測試檔 `tests/governance/test_debt_mutations.py` + `_debt_probe_helper` 自身單元測試；通過條件**見 SPEC Task 3.2 驗證段**（含每類 mutation 改壞轉紅／復原轉綠**逐條 receipt**、`pytest tests/governance -q` 全綠且 ≥287、`bash scripts/mutation_probe_check.sh tests/governance/test_debt_*.py` **rc=0**＝改法②真的解決靜態閘的具名 oracle、**人工預置一筆 OPEN 債後 `pytest tests/governance -q` 仍全綠**＝改法④的具名 oracle）
- **存活至**：永久保留　**覆蓋風險**：無

---

## §T 覆蓋追溯（只列 ID 對應，不列內容——反漂移）

| SPEC 項 | 合計 | TODO 落點 |
|---|---|---|
| Task ID | **8** | Task 0.1／1.1／1.2／1.3／2.1／2.2／3.1／3.2 — **8/8 一一對應，無合併無拆分** |
| Phase | **4** | Phase 0／1／2／3 — 4/4 |
| §V mutation | **31**（M1–M34，編號跳號） | Task 3.2 統一負責；M32/M33/M34 另分別由 Task 1.2／2.2／1.1 的驗證段直接覆蓋 |
 | §A 誠實邊界 | **14** | §0.4 指向 SPEC，**不複製**；實作端只需遵守「不得寫出與該節矛盾的訊息」 |
| §C 約束 | **8** | §0.1 摘錄高頻項，**衝突以 SPEC §C 為準** |
| §RISK 命中 | **b、c**（SPEC RISK-HIT 原文，**無 d**） | 各 Task「風險緩解」欄 |
| 環境變數 | `ROUND_ID`／`DEBT_AUDIT_OVERRIDE`／`GOVERNANCE_TEST_HARNESS` | Task 1.2⑤／3.1③／§0.1 反 bypass 紅線 |

**合計數自檢**：Task 8＝8 ✅／Phase 4＝4 ✅／mutation 31 條全歸 Task 3.2 ✅。

---

## §Handoff

```
SPEC=docs/P16_COMMITTEE_DEBT_SPEC.md TODO=docs/P16_COMMITTEE_DEBT_TODO.md FOCUS=完整審查
```
用 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 獨立審查；BLOCKING 修補後才 Frozen。
**未過外部 review 前狀態＝`Internal Frozen`，不得派實作。**
