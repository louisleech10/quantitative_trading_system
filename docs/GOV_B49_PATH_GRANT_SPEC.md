# B-49 永久 path grant（**git 物件綁定**）＋ 炸彈狀態機 R-A ＋ 行為式閉合證據 — SPEC

> 來源：`handoffs/reconcile/20260811-govb49-x-consult-r4/synth.md`（三家 consult，C 案）　|　日期：2026-08-11　|　對應 TODO：待生成
>
> 🔴 **設計來源＝委員 C 案，非主委原案。** 主委前一版（`docs/GOV_B49_UNFREEZE_WINDOW_SPEC.md`）
> 已於 SPEC review r2 因斷路器命中而**放棄**，該檔保留供對照，**不是**本 SPEC 的基礎。
>
> **修訂脈絡**：r4 把授權上界由「commit 區間」改為「內容 digest」，三家判定 r3 之七條 range 系列
> **全部消解、無一原樣重現**。r5 承接 r4 之 14 條 review findings
> （`handoffs/reconcile/20260811-govb49-x-review-r4/synth.md`），**方向不變**：
> 三家一致「方向問題 BLOCKING ＝ 0」。r5 的實質＝**把 digest 由概念變成可驗收的契約**。

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：大。
- **命中高風險原則**：(b) 跨模組/共用路徑——被三道 live waiver 守衛、引信、炸彈與兩處
  source-level oracle 共同消費；(c) 多 phase／難回退——永久改寫凍結面，授權事後不可撤銷（見 §C-2、§R）。
- **RISK-HIT 宣告**（機檢依據）：

RISK-HIT: b,c

- 未命中 (a)(d) ⇒ §G 移 §N 標 N/A。**adversarial review 必跑**（三家）。

## §A 假設與待使用者確認

**已驗證事實**（皆 2026-08-11 實跑；派工前／派工後分列）：

- FACT-RECEIPT: 修法形狀之完整隔離實跑收據 → `docs/GOV_B49_PINSHAPE_RECEIPT.md`
  （主委實跑：基準線 3 failed → 套修法後五個 `_B45_HARNESS` 檔 **141 passed / 0 skipped**；
  r4 findings 修畢後**同值複跑**，證明行為未變）
- FACT-RECEIPT: `.claude/tmp/rolepin_probe.py` → **7 格全 PASS**，含 codex 之四空白 `evil)` 反例
  （主委實跑；G5 一格即票文條件 2-② 之「三個合法家族逐一可釘」證據）
- FACT-RECEIPT: `git rev-parse HEAD:tests/governance/test_stamp_taskid_inject.py` → 印出 40-hex blob id；
  `git ls-tree HEAD -- <同路徑>` → 印出 `100644 blob <同一 id>`；
  `git diff --quiet HEAD -- <同路徑>` → rc=0（乾淨）、對已改檔 → rc=1（主委實跑；**§C-9 之三個原語**）
- FACT-RECEIPT: `python3 -c` 讀 `scripts/governance_families.json` → `review_families`
  ＝`['codex','composer','grok']`；`executor_clis`＝`['codex','cursor-agent','grok','agy']`
  （後者是 **CLI 執行檔名不是家族名**，不可用作家族來源）
- FACT-RECEIPT: `sed -n '2189,2192p' tests/governance/test_govb1_contract_matrix.py` → 印出
  `_B5_MANIFEST_AUTHORIZED_ADDITIONS = frozenset(`（**本 SPEC 照抄之先例**）
- FACT-RECEIPT: `grep -n "len(_B45_HARNESS) == 5" tests/governance/test_govb1_contract_matrix.py` → 印出
  `2111`／`2213`／`2427`
- FACT-RECEIPT: `bash scripts/debt_ledger.sh --has-open` → **派工前 rc=0**；派工後預期值: rc=1

**待確認：無**（技術決策依 `CLAUDE.md` 委員會條款）。

**已確認結果**：2026-08-11 使用者指示三家委員＋主委自任實作，並授權「照你跟委員的共識決做完」。

## §C 約束

**C-1　照抄既有先例，不發明新機制。**
`_B5_MANIFEST_UNLOCKED` ＋ `_B5_MANIFEST_AUTHORIZED_ADDITIONS` ＋
`test_b5_manifest_extension_is_exactly_authorized` 已是「永久、字面、被測試釘死的授權」之範本。
🔴 該處註解逐字警告：oracle 須為**字面期望集合**；若寫成由同一常數導出之式子會
**同義反覆恆真**。本 SPEC 之所有 oracle 同此要求。

**C-2　永久授予不可撤銷（r6 依三家實測更正措辭）。**
🔴 **守衛吃的不是「歷史路徑 union」，是 endpoint net-diff。**
r5 之 `CODEX-R5-P0-01`／`COMPOSER-R5-P1-01`／`GROK-R5-P1-01` 三家各自實跑推翻前版措辭：
`:2037` B3 窗＝`b3..b4_start`、`:2135` B4 窗＝`b4_start..b5_start`（**兩端皆非 HEAD**）、
`:2256` B5 窗＝`b5..HEAD`。且 `git diff a..b` 只比兩端點，
**改了又還原的路徑根本不會出現在其中**。

⇒ 本 SPEC **明確採 endpoint net-diff 語義**，不改實作
（改逐 commit union 會把 r3 那整類 range／clamp／rename 問題全部請回來）。
⇒ **正確表述**：三檔一旦出現在**任一受檢窗之 endpoint net-diff**，該窗之授權即不可撤除。
⇒ **具名接受之邊界**：若某窗內「改了又還原」，該窗不觸發——這是 endpoint 語義的固有性質，
**已知且接受**，不得宣稱為 history 覆蓋。
⇒ 本設計**無退場 Task**。

**C-3　永久授權不得變成長期白名單。**
授權綁定於**被授權物件之 git 身分**（blob id ＋ mode），而非 commit 區間。
⇒ 授權**之後**再改這三檔 ⇒ 身分不符 ⇒ **轉紅**。
⇒ 「授權區間」不是時間概念而是**狀態**概念，故不存在可滑動的上界。

**C-4　守衛不得解析 commit 訊息**（`test_waiver_guards_never_parse_commit_message` 釘死）。

**C-5　`_B45_HARNESS` 之 reader inventory**（沿用，已逐一複驗）：
`:2111`／`:2213` 兩處 `len == 5` **不得改**；`:2323` G-7 硬保護集交叉契約**不得改**；
`:2517-2522`／`:2573-2574` 兩處 source-level oracle **不得改**（後者釘死守衛 body 須仍含
`--name-only` 與 `_B45_HARNESS`）；三道 live guard、引信、炸彈為本 SPEC 之標的。

**C-6　誠實邊界。** 本機制**只防意外與遺忘，不防具寫入權者蓄意**。與 `票 B-49` 炸彈之既有邊界一致。

**C-7　主控端跑驗收時不得動檔**；行為探針一律走隔離副本。

**C-8　票文條件 3 之字面與現實已分岔，本 SPEC 明列處置。**
票文寫「`eligible` 與測試內家族集合須機械連動」。該句寫於 `eligible` 恰為三家之時；
使用者加入 `claude` 後，`eligible`（四項，含無 CLI 配方之編排端）**已不是**
「可被 CLI 派工的家族」之正確切片。
⇒ 本 SPEC 以 `review_families` 為該切片，並要求**兩條**不變式同時成立：
`dispatch 集合 == review_families`（**相等**，非 subset）與 `review_families ⊆ eligible`。
🔴 `CODEX-R4-P0-02` 明示：**subset 單獨不得冒充票文之機械連動**。

**C-9　digest 契約（`CODEX-R4-P0-01`／`COMPOSER-R4-P1-01`／`GROK-R4-P1-02`，三家同時命中）。**
r4 只寫了函式名 `_sha256_of_worktree`，未定義被雜湊的是什麼 ⇒ 三種來源會得出三種值。
本節逐條寫死，**不留實作者裁量**：

1. **被授權的身分 ＝ git 物件身分**，取自 `git ls-tree HEAD -- <path>` 的
   **`<mode> <type> <object-id>`** 三元組（實跑樣例：`100644 blob 32a8b417…`）。
   🔴 **r6 更正**：前版寫「與 `hit_harness` **同源**」，該宣稱**過強且已被三家實跑推翻**
   （見 C-2）。誠實版＝**兩者本來就不同源**：`hit_harness` 是各窗之 endpoint net-diff，
   身分固定取自 HEAD。本 SPEC **不主張**同源，而是讓兩者各司其職——
   前者決定「**哪些路徑要受檢**」，後者決定「**受檢的路徑現在是不是被授權的那個東西**」。
   r4 之核心洞（「digest 讀 worktree／命中集合讀 HEAD」之錯配）由**第 4 條**關閉，不靠同源。
2. **不做任何正規化**。git 物件身分不涉及 CRLF／編碼／文字模式的再詮釋 ⇒
   r4 遺留的換行正規化爭議**不再存在**（不是「決定不處理」，是**沒有那個決策點**）。
3. **mode 納入身分**。symlink 之 mode 為 `120000`、可執行為 `100755`、gitlink 為 `160000`
   ⇒ 檔案型別／權限被替換一律不符 ⇒ 紅。**不需另寫 symlink 條款**。
4. **工作樹內容須與授權 blob 逐位元組相同**（r6 改法，`GROK-R5-P1-03`）：
   比對 `git cat-file blob <授權 oid>` 之輸出與 `Path(p).read_bytes()`。
   🔴 **前版用 `git diff --quiet HEAD -- <path>`，已被 grok 實測打敗**：
   `skip-worktree`／`assume-unchanged` 之 index 旗標可讓它在**工作樹已改**時仍回 rc=0。
   改為直接位元組比對後**完全不經 index**，該類旗標失效。
   ⇒ 順帶關閉 `CODEX-R5-P1-02` 之 filter／`core.autocrlf` 爭議：若環境設了 filter 使兩者不等，
   結果是**紅**——方向正確，不需另立條款。
   另須斷言該路徑為 **regular file**（非 symlink／目錄／不存在），否則紅。
5. **填常數與 guard 驗證必須呼叫同一個函式**（`_b49_object_identity(path)`），
   且該函式**不得**有任何參數可切換來源。
6. **讀不到即 fail-closed**：路徑不在 HEAD、`git` 非零退出、輸出不合
   `^[0-7]{6} [a-z]+ [0-9a-f]{40}$` ⇒ 一律視為不符（紅），**不得**回退到工作樹讀取。
7. 🔴 **威脅模型排除項（`CODEX-R5-P1-07`，誠實列出而非假裝擋得住）**：
   `git` 執行檔本身、object database、`replace` refs、`GIT_*` 環境變數
   **均在 C-6 之「不防具寫入權者蓄意」範圍內**，本機制**不宣稱**能防。
   ⇒ 不得把 C-9 描述為一般性 fail-closed；它是**針對意外與遺忘**的 fail-closed。

**C-11　🔴 同批 rebind 不可防，具名排除（r6 定案；`CODEX-R6-P0-01`）。**
「改標的檔 ＋ 同批更新 grant 身分常數」與「合法的向前修」**是同一個操作**。
兩者的差別只在**意圖**，而意圖不可被測試觀察。

r6 曾試圖以「兩段提交」（先獨立 commit 建立授權、再分離提交內容）區分兩者。
🔴 **該方案是假解，已撤回**：第一段要寫入的身分等於**第二段之後**的 blob oid，
那個物件此刻不存在；若預先寫入未來 oid，第一段自身的字面 oracle 就不等於當時 HEAD
⇒ 違反 Task 1.1 與 C-9-1。**這與 r3 的 bootstrap 死結是同一個東西換了位置。**

⇒ 依 **C-6**，本機制**不防同批 rebind**，由 **code review（兩個非實作者家族）**承接。
⇒ **不得宣稱**「授權無法自我更新」。可宣稱的是：任何 rebind 都會**改動字面常數**，
因而**必然出現在 diff 裡**——這是可見性，不是不可能性。

🔴 **教訓（已入紀律）**：消解條文矛盾的正確手段是**刪掉錯的那一端**，不是再發明一層機制。
r6 的兩段提交正是「為了修矛盾而新增機制」，然後撞回舊死結。

**C-10　隔離須為實體隔離（`CODEX-R4-P1-05`）。**
現行探針把 `scripts/` **symlink** 回生產 ⇒ 任何直接寫 `REPO_ROOT/scripts/...` 的變異會**穿透副本**。
⇒ 閉合證據之 runner 必須**實體 copy** `scripts/`（禁 symlink），並於 subprocess 前後對 repo 做
snapshot diff；setup／symlink 檢查／snapshot 任一不符即紅。
🔴 `_role_pin` 已有的「拒絕傳入生產 `scripts/`」**只擋參數誤傳，不擋 symlink 穿透**，
兩者**不得互相冒充**。

> **新資料結構**：本 SPEC 只新增模組級常數（與守衛同檔同 commit），**不建外部 schema 檔**，
> **不需要** `scripts/govb1_frozen_hashes.txt` 新增任何鍵。

## §G Golden / Baseline

移 §N 標 N/A。

## §P Phase 與依賴

### Phase 0 — 未凍結區先落地（依賴：無；**已完成並經三家 review**）

**Task 0.1 — `tests/governance/_role_pin.py` ＋ `test_cxrun_selfcheck_prompt.py`**

- 目標：把「凍結檔要怎麼修」從 assumed 變成 fact-verified，且不動凍結面。
- 檔案：`tests/governance/_role_pin.py`（新建）、`tests/governance/test_cxrun_selfcheck_prompt.py`
- 改法：見 `docs/GOV_B49_PINSHAPE_RECEIPT.md` §5、§7、§7b。
  r4 三家對此段開了三條，全部成立、全部已修：`reviewers` 公式改
  `eligible ∩ review_families − {impl}`；SoT 來源改讀傳入之 `scripts_dir`；
  `case` 分支縮排放寬且**結尾錨點**改 `\n[ \t]*esac`。
- **驗證**：`pytest -q tests/governance/test_cxrun_selfcheck_prompt.py` → **7 passed**；
  `python3 .claude/tmp/rolepin_probe.py` → **7 格全 PASS**（皆已實跑）
- **邊界（≥2）**：①傳入生產 `scripts/` ⇒ 拒絕　②釘定無 CLI 配方之家族 ⇒ 拒絕
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得寫 repo 的 `scripts/governance_roles.json`；不得硬編家族三元組

### Phase 1 — 永久 path grant，git 物件綁定（依賴：Phase 0）

**Task 1.1 — `_B49_GRANT_IDENTITY` 常數（照抄 `_B5_MANIFEST` 形狀）**

- 目標：以字面常數表達「B-49 被授權之 harness 路徑**及其被授權之 git 物件身分**」。
- 檔案：`tests/governance/test_govb1_contract_matrix.py`，模組級新增
- 改法：三條路徑與其 `<mode> <type> <oid>` **逐字寫死**：

```
_B49_GRANT_IDENTITY = {
    "tests/governance/test_stamp_taskid_inject.py": "100644 blob <40-hex 字面>",
    "tests/governance/test_rolegate_predispatch.py": "100644 blob <40-hex 字面>",
    "tests/governance/test_result_state_format_failed.py": "100644 blob <40-hex 字面>",
}
_B49_HARNESS_GRANT = frozenset(_B49_GRANT_IDENTITY)
```

  值於實作時由 `_b49_object_identity(path)`（C-9 之單一函式）對**施工 commit 後**的 HEAD 取得。
- **驗證**：`pytest -q tests/governance/test_govb49_path_grant.py -k grant_is_exact` 綠；
  oracle 為**字面期望集合**（路徑集合與三個身分字串皆逐字比對），
  **禁**寫成由同一常數導出之式子（C-1 之同義反覆警告）
- **邊界（≥2）**：①常數含 `_B45_HARNESS` 以外路徑 ⇒ 專測轉紅
  ②少於或多於三條 ⇒ 專測轉紅
- **存活至**：永久（C-2）
- **覆蓋風險**：無
- 不可做：不得用萬用字元／前綴；不得由 `_B45_HARNESS` 導出；不得存不合 C-9-6 格式之值

**Task 1.2 — 三道 live 守衛：以 git 物件身分判定是否豁免**

- 目標：讓 B-49 之施工合法，同時**不**把三檔變成長期白名單（C-3）。
- 檔案：三道 `test_waiver_b{3,4,5}_range_does_not_touch_forbidden`
- 改法：斷言由 `assert not hit_harness` 改為

```
unexcused = {p for p in hit_harness
             if _b49_object_identity(p) != _B49_GRANT_IDENTITY.get(p)
             or not _b49_worktree_matches_head(p)}
assert not unexcused
```

  🔴 `hit_harness` 之既有計算式與 `--name-only` **逐字保留**（C-5 之 `:2573-2574` oracle）；
  本 Task **不動 range**，故三道守衛各自的 `b3..upper`／`b4..upper`／`b5..HEAD` 語義**逐字不變**
  ——r3 之 per-window range 與 clamp 問題整類不適用。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k waiver` 全綠；
  且 Task 3.2 之 OLD vs NEW 對照在「grant 常數不存在」情境下逐格 `old_reject == new_reject`
- **邊界（≥2）**：①三檔在授權後**再被改動一個位元組** ⇒ 身分不符 ⇒ **拒**（C-3 之核心）
  ②diff 含第四個 harness 檔 ⇒ 拒（不在 `_B49_GRANT_IDENTITY` 鍵集內）
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得無條件扣除；不得放寬 `_B45_FORBIDDEN_PREFIXES`；不得改 diff range 取法；
  不得在身分取不到時回退讀工作樹（C-9-6）

### Phase 2 — 炸彈狀態機 R-A ＋ 行為式閉合證據（依賴：Phase 1）

**Task 2.1 — 引信：餵入路徑取自「未授權」差集**

- 目標：授權三檔後，引信仍須反映「另兩檔仍凍結」。
- 檔案：`_b45_freeze_still_active()`
- 改法：餵入路徑改為 `sorted(set(_B45_HARNESS) - _B49_HARNESS_GRANT)[0]`；
  差集為空 ⇒ 判 inactive。新增 fail-closed：**live guard 數 ≥ 1**，全 dormant ⇒ 不得回 inactive。
  `len(_B45_HARNESS) == 5` 判準保留（C-5）。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k b45` 全綠；
  `test_b45_bomb_cannot_be_defused_by_skip` 通過
- **邊界（≥2）**：①grant＝三檔 ⇒ 引信仍 active ②三道 guard 全 dormant ⇒ **不得**回 inactive
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得在引信內寫 `assert not hit_harness` 字面（C-5 之 `:2517-2522`）

**Task 2.2 — 炸彈 R-A：`CLOSED` 須附行為式證據**

- 目標：使「三檔修好 ＋ 未授權 harness 仍全拒 ＋ 票可 `CLOSED`」可達。
- 檔案：`test_b45_unfreeze_requires_roles_sot_closure`
- 改法：

```
if _b45_freeze_still_active():
    if status == "CLOSED":
        _assert_b49_closure_evidence()
        return
    assert status == "OPEN"
    return
assert status == "CLOSED"
```

  `test_b45_bomb_cannot_be_defused_by_skip` 要求之三項**全部保留**。
  炸彈 docstring `:2463-2467` 逐字列票文①②③④，須與 Task 2.3 之對照表**逐條同步改寫**。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k "b45 or bomb"` 全綠
- **邊界（≥2）**：①票 `CLOSED` 且證據齊 ⇒ 綠　②票 `CLOSED` 而證據缺 ⇒ **紅**
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得把 `_assert_b49_closure_evidence()` 寫成字面比對

**Task 2.3 — 閉合證據：每格獨立 selector ＋ 獨立 receipt**

- 目標：讓「B-49 行為已落地」成為**行為判準**，且**每格可由自己的 rc／pass／skip 獨立判定**。
  🔴 r4 版之六格表被三家判定不可獨立判定，本 Task 為 r5 之重寫核心。
- 檔案：`tests/governance/test_govb1_contract_matrix.py` 新增私有函式；
  新測試置於 `tests/governance/test_govb49_path_grant.py`
- **selector → 票文對照表**（每格獨立 selector、獨立 receipt）：

| 票文條件 | selector | 判準 |
|---|---|---|
| 1-a　`:769` 靜默 skip **已移除** | `test_govb49_path_grant.py::test_v12_body_has_no_skip_escape` | **原始碼片段（含 decorator 行）不得出現不分大小寫子字串 `skip`**（見下） |
| 1-b　四種 kind 皆實際跑到 | `test_stamp_taskid_inject.py::test_v12_non_stamp_kinds_no_stamp_target_ok` | `passed == 4` 且 `skipped == 0` |
| 2-①　invalid mutation 轉紅 | `test_govb49_path_grant.py::test_stamp_path_invalid_implementer_turns_red` | **四個 rc 皆須固定**（見下）；標的＝**stamp 路徑之 invalid implementer 分支**，非 pin API |
| 2-②　三個合法值逐一通過 | `test_govb49_path_grant.py::test_impl_path_works_for_every_cli_family` | **實體隔離 subprocess 內跑真正 impl route**；逐一釘定後 `returncode == 0` 且 `skipped == 0`；集合取自**外部字面** |
| 3-a　dispatch 集合 **等於** `review_families` | `test_govb49_path_grant.py::test_dispatch_set_equals_review_families` | `passed == 1`（相等，非 subset） |
| 3-b　`review_families ⊆ eligible` | `test_govb49_path_grant.py::test_review_families_subset_of_eligible` | `passed == 1` |

- 🔴 **1-a 必須是原始碼層判準**（`GROK-R4-P1-01`）：
  釘定之後 `pytest.skip` 成為**死碼** ⇒「保留 skip」與「移除 skip」在
  `passed==4 ∧ skipped==0` 之下**無法區分** ⇒ 純行為判準會讓票文條件 1 在**未移除**時判綠。
  故 1-a 與 1-b **拆成兩格**，前者查原始碼、後者查行為，缺一不可。
- 🔴 **1-a 之抗混淆下界（r6 補；`COMPOSER-R5-P1-02`／`GROK-R5-P1-02`／`CODEX-R5-P1-03`）**：
  **禁止字面子字串掃描**——`getattr(pytest,"skip")`／`from pytest import skip as _s`／
  字串拼接皆不含 `pytest.skip` 這個子字串，naive 實作會假綠。
  依使用者定死之「文字問題用白名單機械卡」，**不列黑名單**，改**封閉可導出集合**。

  🔴 **r6 定案（`CODEX-R6-P1-03` ＋ `GROK-R6-P1-01`，兩家獨立命中）**：
  前版寫「AST 內不存在名為 `skip` 的識別字」，**那個規則不封閉**。codex 附四條實測反例：
  `pytest.importorskip(...)`（outcome=`Skipped`）、
  `from _pytest.outcomes import Skipped as Halt; raise Halt(...)`（outcome=`Skipped`）、
  `raise unittest.SkipTest(...)`、以及 `@pytest.mark.skipif(True)`
  **加在 decorator 上**（根本不在 body AST 內）；composer 另指出 `getattr(pytest,"skip")` 之字串常數。

  ⇒ **改用真正封閉的判準**：

  > 取該函式之**原始碼片段（`ast.get_source_segment`，且須包含其 decorator 行）**，
  > 斷言其中**不出現不分大小寫的子字串 `skip`**。

  一次涵蓋 `pytest.skip`／`skipif`／`importorskip`／`SkipTest`／`Skipped`／
  `getattr(...,"skip")`，且**不隨繞法擴充**——這才是封閉集合。

  🔴 **具名接受之過嚴**：函式內若有任何識別字或字串含 `skip`（含變數命名）也會紅。
  該情形在本函式不存在，且**過嚴的方向是安全的**。

  🔴 **具名殘留（此規則覆蓋不到，且判定為可接受）**：
  於**模組層**把 skip 例外 import 成不含 `skip` 之別名，再於 body 內 `raise <別名>`。
  ⇒ 該形態若**真的會 skip**，1-b 的 `skipped == 0` 必抓；
  唯一漏網情形是**死碼**（永不執行的 skip），而死碼不影響覆蓋率。
  ⇒ **1-a ＋ 1-b 聯合覆蓋**，殘留僅限「模組層別名之死碼」。
- 🔴 **2-① 之四個 rc 須全部固定（r6 補；`CODEX-R5-P1-04`）**：
  ①未突變 base `rc == 0`　②invalid mutation 後 `rc != 0`　③突變後 `skipped == 0`
  ④外層 receipt `rc == 0`。mutation **必須落在 stamp path 的 invalid implementer 分支**，
  不得以 pin API 或單純 wrapper assertion 代替。
- 🔴 **2-② 不得以 pin API 單元測試充當（r6 補；`CODEX-R5-P1-06`）**：
  `rolepin_probe.py` 之 G5 只證明「三個家族都釘得起來」，**沒有跑 impl route**
  ⇒ 它是 pin API 的單元測試，**降級**，不再充當票文 2-② 之 receipt。
  2-② 須在**實體隔離 subprocess** 內對外部字面三家集合逐一釘 implementer、
  執行**真正的 impl route**，並確認 `returncode == 0`、`skipped == 0`、產出路徑正確。
- 🔴 **1-b 之 selector 須先參數化**（`CODEX-R3-P1-05`）：現行
  `for kind in ("review","consult","closure","impl")` 是**單一測試節點**，
  刪掉 `impl` 這一 case 仍表面綠。改為 `@pytest.mark.parametrize("kind", ...)`
  ⇒ 四種 kind 各成一節點 ⇒ `passed == 4` 即為 per-kind visit receipt。
- 🔴 **2-② 禁自我參照**（`CODEX-R4-P0-02`）：判準寫 `passed == 3` 之**字面**，
  並另以外部字面集合 `frozenset({"codex","composer","grok"})` 對照 `review_families`
  ——**不得**寫成 `passed == len(review_families)`（來源縮短即綠，證明不了三個現行值逐一被跑）。
- 🔴 **條件 4**（「之後才由使用者更新 roles」）**已被使用者於 2026-08-11 先行執行** ⇒ 順序是倒的。
  本 SPEC **不主張**補救該順序，只**具名記錄**；`_assert_b49_closure_evidence()`
  **不得**把條件 4 列為可判定項（它是人的行為，不是行為判準）。
- **執行環境**（`CODEX-R3-P2-06`／`CODEX-R4-P1-05`／C-10）：於**實體隔離副本**以子程序跑：
  `scripts/` **實體 copy，禁 symlink**；`env` 最小集（`PATH`／`HOME`／`LANG=C.UTF-8`，其餘清空）；
  `-p no:cacheprovider`；明確 `cwd`；逾時上限；子程序前後對 repo 做 snapshot diff。
  runner setup、symlink 檢查、snapshot 任一步失敗 ⇒ 紅，不得吞成綠。
- **驗證**：Task 3.1 之 mutation 逐格轉紅
- **邊界（≥2）**：①selector 不存在（測試被改名／刪除）⇒ **紅**，不得當成「通過」
  ②子程序逾時 ⇒ 紅
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得以整檔 `exit 0` 取代具名 selector；不得在主工作樹跑；
  不得以任一格之 receipt 兼充另一格

### Phase 3 — 可證偽性（依賴：Phase 1、2）

**Task 3.1 — mutation 矩陣（編號至 ⑯＋⑩b／⑩c 共 18 個編號，其中 ⑫ 已刪 ⇒ **實跑 17 格**）**

- 目標：證明每一條判定都承重。
- 檔案：`tests/governance/test_govb49_path_grant.py`（新建）
- 改法：實體隔離副本逐格變異：
  ① v12 之 `pytest.skip` 改回（**且釘定仍在**，使其成死碼）⇒ 1-a 須紅（1-b 不會紅，這正是要證明的）
  ② 移除參數化之 `impl` case ⇒ 1-b 須紅
  ③ 2-② 之三合法值測試改成只跑一個 ⇒ 須紅
  ④ 3-a 之 dispatch 集合改成 `review_families` 之真子集 ⇒ 須紅（subset 不得放行）
  ⑤ `review_families` 與 `cx_run.sh` 分支人為漂移 ⇒ `cli_dispatchable_families()` 須紅
  ⑥ 家族三元組改回硬編 ⇒ 須紅
  ⑦ 無 `_B49_GRANT_IDENTITY` ⇒ 三檔 diff 須被拒
  ⑧ grant 含第四個 harness 檔 ⇒ 專測須紅（非「只濾除」）
  ⑨ 🔴 三檔內容改動一個位元組 ⇒ blob id 不符 ⇒ 須被拒（C-3 之核心）
  ⑩ 🔴 **工作樹改壞、HEAD 未動** ⇒ C-9-4 之逐位元組比對須擋下（codex 之同 commit 假綠）
  ⑩b 🔴 **對該路徑設 `skip-worktree` 或 `assume-unchanged` 後再改工作樹** ⇒ 仍須紅
      （grok 實測前版 `git diff --quiet` 會被此打敗）
  ⑩c 🔴 **設 `core.autocrlf=true` 或 `.gitattributes` filter** ⇒ 逐位元組比對不等 ⇒ 須紅（非放行）
  ⑪ 🔴 **mode 由 `100644` 改為 `100755`／`120000`（symlink）／`160000`（gitlink）** ⇒ 須紅
  ⑫ 🔴 **已刪除**（r6 定案；`CODEX-R6-P0-01`）。原格為「同批 rebind 須紅」。
      刪除理由見 §C-11——同批 rebind 與合法維護在機械上**不可區分**，
      該格在任何實作下都會與正規維護路徑衝突。**不得復原此格。**
  ⑬ 被授權檔遭刪除或改名 ⇒ 身分取不到 ⇒ 須被拒
  ⑭ 🔴 隔離 runner 之 `scripts/` 改回 symlink ⇒ setup 檢查須紅（C-10）
  ⑮ 票標 `CLOSED` 而任一格證據缺 ⇒ 炸彈須紅
  ⑯ 任一 reader oracle 被刪／改名 ⇒ 須紅
- **驗證**：`pytest -q tests/governance/test_govb49_path_grant.py` → 17 格全綠；
  且逐格「移除該判定後重跑 ⇒ 對應斷言 rc 由 1 轉 0」，證明承重
- **邊界（≥2）**：①grant 為空 dict ②grant 含非 harness 路徑 —— 皆須拒，非「全授權」
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得以「測試通過」作為驗收（`docs/TEST_DESIGN_CHARTER.md`）

**Task 3.2 — 行為不變對照**

- 目標：證明在「grant 常數不存在」時對既有行為逐字無影響。
- 檔案：`tests/governance/test_govb49_path_grant.py`
- 改法：以 `git show HEAD:tests/governance/test_govb1_contract_matrix.py` 為對照，
  對同一組假 diff 比對 OLD vs NEW 之 reject 布林。
- **驗證**：矩陣逐格 `old_reject == new_reject`（比照 grok 於 `_role_gate.sh` 之 15/15 對照）
- **邊界（≥2）**：①diff 含 harness ②diff 不含 harness
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得只做靜態推理充當對照

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT `b,c`；本機制為閘門且宣稱驗正確性 ⇒ 必附 mutation（Task 3.1 之 17 格）。
- 測試層級：單元（grant 常數 oracle、家族導出）／整合（守衛＋引信＋炸彈）／
  行為（closure evidence 之六格 selector）／原始碼（1-a、reader oracle）／對照（OLD vs NEW）／邊界。
  可獨立 `pytest tests/governance/test_govb49_path_grant.py` 跑。
- **防假綠**：不得修改既有斷言之期望值；`hit_harness` 計算式與 `--name-only` 逐字不動；
  三道守衛之 diff range 取法逐字不動；
  `test_b45_bomb_cannot_be_defused_by_skip`、`test_waiver_guards_never_parse_commit_message`、
  `:2323` G-7 交叉契約三者須全程綠；所有 oracle 用**字面期望集合**（C-1）。
- **驗收之可證偽反例**（任一成立 ⇒ 未完成）：
  - 無 grant 常數時三檔 diff 竟被放行
  - grant 含非 harness 路徑而未整批拒絕
  - 三檔於授權後被改動（HEAD 或工作樹任一）仍被放行
  - mode 由 `100644` 變 `100755`／`120000` 而未轉紅
  - grant 常數與標的檔同批改寫而字面 oracle 未紅
  - 被授權檔被刪除／改名而守衛仍綠
  - v12 保留 `pytest.skip`（死碼）而條件 1 仍判綠
  - 1-b 之 selector 未參數化，移除 `impl` case 仍綠
  - 2-② 寫成 `passed == len(review_families)` 之自我參照
  - 條件 3 僅以 subset 通過而未驗相等
  - 隔離 runner 以 symlink 指回生產 `scripts/`
  - 三道 guard 全 dormant 時引信回報 inactive
  - `_B45_HARNESS` 長度不再為 5，或 `hit_harness` 計算式被改寫
  - 任一 reader oracle 被刪／改名而驗收未轉紅
- **邊界目錄**：空輸入（grant 為空）、越權輸入（含非 harness 路徑）、狀態（身分不符／工作樹髒）、
  型別與權限（symlink／exec bit）、檔案缺失／改名、守衛全 dormant、selector 缺失、
  子程序逾時、SoT 漂移、隔離穿透。
  不適用：全NaN／Inf／std=0／OOM／並發寫／大尺度浮點 reduction。

## §R 回退

🔴 **r5 更正（`CODEX-R4-P1-06`／`COMPOSER-R4-P2-01`／`GROK-R4-P2-01`）**：
r4 把**兩件不同的事**混為一談。codex 之表述較準，逐字採用：

> 正確表述是「**已 push 後不能撤銷 path grant**」，不是「任何程式碼不能 operational rollback」。

### 授權面（不可撤銷）

三道守衛吃的是**歷史 diff 區間之路徑集合**。三檔一旦出現在受檢區間，該事實**不因 revert 而消失**。
⇒ **path grant 一旦 push 即永久**。唯一能真正移除的是 history rewrite，不在本 SPEC 授權範圍。

### 程式碼面（可回退，狀態矩陣）

🔴 **本矩陣逐列一律採 endpoint net-diff 語義**（r6 定案；`CODEX-R6-P0-02`）。
前版各列混用 endpoint 與 history 語義，會讓施工者對「同窗 revert」寫出兩種相反的 oracle。
**同窗 revert 之例外只在本表下方寫一次**，各列不重複、不改寫。

| 回退動作 | 授權常數 | 三檔內容 | closure 證據 | 守衛結果（endpoint 語義） |
|---|---|---|---|---|
| 只拿掉 grant 常數 | 移除 | 保留 | 保留 | **紅**（三檔變回未授權） |
| `git revert` 整批（跨窗） | 移除 | 還原 | 還原 | **紅**（路徑仍在該窗 net-diff，且已無授權） |
| revert 其他程式碼；grant／三檔／**closure 證據皆未動** | 保留 | 保留 | **保留** | **綠** ← 唯一可用的 operational rollback |
| revert 其他程式碼，但**closure 證據被一併回退** | 保留 | 保留 | **移除** | 🔴 **紅** ← 見下 |
| 只 revert 部分 Phase | 視情況 | 視情況 | 視情況 | **未定義**，不得宣稱綠 |
| 向前修：改三檔＋更新身分常數（同批） | 更新 | 更新 | 保留 | **綠** ← 正規維護路徑（機械上不可與蓄意 rebind 區分，見 §C-11） |

🔴 **第四列是 r6 新增（`CODEX-R6-P1-04`）**，它直接命中「可導致票 B-49 假 CLOSED」：
若被 revert 掉的正是 closure evidence 那些測試，前版 row 3 會判綠，而票仍可 `CLOSED`
——**證據已被移除卻仍宣稱閉合**。
⇒ row 3 之綠色前提**必須明列**「closure evidence path 未被回退」，
並由 Task 3.1⑯（reader oracle 被刪／改名須紅）承重。

⇒ **operational rollback 是可能的**，條件是**不動 grant 常數、三檔內容、與 closure 證據**。

🔴 **endpoint 語義的固有例外，只在此處具名一次**：若 revert 與原變更
**落在同一個受檢窗內**，該窗之 endpoint net-diff **看不到**這些路徑（C-2）⇒ 守衛不觸發。
這不是漏洞，是 endpoint 語義的性質。**但不得因此宣稱「revert 可撤銷授權」**——
跨窗時仍紅，且落在哪個窗不由操作者決定，故**實務上一律視為不可回退**。

### push 原子性（誠實降級）

🔴 **「Phase 1／2／3 不得分次 push」是流程要求，不是 git 強制。**
`pre-push` 只跑當前工作樹測試，**不知道** branch 上是否已有僅含 Phase 1 的 push 紀錄
⇒ repo **無機械閘**可阻止分次 push。**不得宣稱硬 enforcement。**
中間態（僅 Phase 1 已 push）視同缺陷，補救方式是 **forward-fix**，不是 revert。
- 任一 mutation 未轉紅 ⇒ 不 merge、不 push。

## §N N/A 登記

- **§G Golden / Baseline：N/A** —— 不碰數值／ML／feature 路徑，不動 `data_cache/`；
  行為不變之證明由 Task 3.2 之 OLD vs NEW 對照矩陣承擔（等價於 Golden 的角色）。
