# GOVB1 Task 1.3 (d) 階段 2 — 交付延伸檔（`b4` 階段 2 ／ `R-11`／`R-12`）

**建立**：2026-08-10　**授權**：`handoffs/reconcile/20260810-govb1-b4-consult-r1/synth.md`（codex＋composer `RECONCILE-STAMP APPROVED`）

## 🔴 為什麼是延伸檔而不是就地改 TODO

`docs/GOVB1_INPUT_QUALITY_TODO.md` 為**凍結唯讀**（`_B45_FORBIDDEN_PREFIXES` 含 `docs/GOVB1_`，
且該前綴同時在 `_G7_OOE_HARD_PROTECTED` 內 ⇒ **out-of-epic 通道亦禁**）。
依「修訂凍結文件走延伸檔、非就地改」之既定紀律，本檔為 `TODO:821-836` 該節之**唯讀補述**。

**本檔不是機械驗收**——機械驗收在 `tests/governance/test_govb1_expected_delta.py`。

---

## A. 交付了什麼（`R-11` 關閉）

`scripts/gate.sh` 之 dispatch 主路徑，於 `_check_open_debt` 之後、completeness／stamp **之前**，新增兩層：

| 層 | 條件 | 行為 |
|---|---|---|
| ① | `[ -n "${spec}" ]` 且 `[ -z "${brief}" ]` | `miss brief`（累加，尾端統一拒發；`missing` 非空 ⇒ 不 mint token） |
| ② | `[ -n "${spec}" ]` 且 `--brief` 存在 | `brief_conformance_check.sh --only impl-kind` ⇒ kind 須**恰為 `impl`**，否則 `exit 1` |

`scripts/brief_conformance_check.sh` 新增 `--only impl-kind`（沿用**同一** kind parser，未新增第二真相源）。

### 為何②不可省（`CODEX-R1-P0-01`）

只做①不夠：`(c)` 掛點之 `--only expected-delta` 對非 impl kind **一律 rc=0**
（`_check_expected_delta:161`）。故 `--spec` ＋ 一份**合法 consult brief** 原本可讓 EXPECTED-DELTA
整段不驗而 token 照發。codex 於隔離環境實跑得 **rc=0 且 `dispatch.token` 存在**。

### 為何位置在 completeness／stamp 之前

否則一份過期或未戳記的 reconcile 會先 `exit 1`，使本閘**永遠不被執行到**——
那是「掛點空轉」的另一形態，正是 `T-1.3-N1` 的標的。主委實測撞到：
`handoffs/reconcile/20260807-govb1-x-stamp-r4/synth.md`（TODO ASSERT 原引用者）之戳記 provenance
現已失效（`task:20260807-GOVB1-X-STAMP-R5` 無 `committee_dispatch` 審計事件），
若把 (d) 排在其後，本閘在該路徑上恆不執行。

### 為何不採字面 blanket（缺 brief 即拒，不看 `--spec`）

主委於隔離 worktree 實跑全套：**57 failed／1316 passed，跨 14 個測試檔，其中僅 1 檔在 manifest allow**。
兩家一致否決。scoped 版全套 **8 failed**，扣除 worktree 無 `venv/` 造成的 2 條量測雜訊後為 **6 條**，
其中 1 條是 allow 內設計上就該翻轉的階段 1 封條，其餘 5 條分布於 3 個檔、歸因逐字相同。

---

## A′. `--spec` 值本身之 fail-closed（`CODEX-R1-P1-01`，review-r1 追加）

`gate.sh dispatch` 之 impl 判準是 `[ -n "${spec}" ]`。**顯式**傳 `--spec ""` 使其為假 ⇒
A 節①②與既有 V-C `miss reconcile` **全部不啟動**，卻仍寫出 `dispatch.token`；
parser 為 last-wins，故 `--spec <有效值> --spec ""` 亦可抹除。codex 於 review-r1 附實跑反例。

**這個判準在本輪之前就長這樣**——但本輪把它**升格為安全閘**，故不得以「既有語義」為由延後。

修法（把「旗標有沒有出現」與「值是什麼」分開）：

| 情形 | 行為 |
|---|---|
| 完全不給 `--spec` | **逐字不變**（非 impl 派工，rc=0） |
| `--spec ""` 或全空白 | `exit 1`，訊息具名 `--spec`，**不發 token** |
| `--spec` 重複給值 | `exit 1`，訊息含「重複」，**不發 token** |

回歸護欄 `test_p1_01_no_spec_flag_unchanged` 存在的理由：沒有它，上述三條可以被
「一律拒 `--spec`」這種過寬修法騙過去。

## A″. kind 解析排除 code fence（`CODEX-R1-P2-02`，review-r1 追加）

`_resolve_kind_into_bk` 原以 `grep -E '^brief-kind:'` 全檔擷取，會採信 **fence 內**的示例宣告。
修法＝在**同一** parser 內排除 fence，判準與 `_check_expected_delta` 之 awk 同源（不另立第二套規則）。
影響面大於 `--only impl-kind`——`--emit`／full path／`_role_gate` 都吃同一個解析結果。

---

## B. `TODO:822` 第 1 條 ASSERT 仍**字面不成立**（`R-12`，具名殘留）

```
ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_impl_delta_absent.md THEN rc!=0
```

**現況 rc=0。** full path 仍不驗 EXPECTED-DELTA。

### 為什麼不做

掛上 full path 會打紅 `_B45_HARNESS` 五檔中的四檔共 **10 條**（主委實測；根因單一＝
那些檔的 `_write_brief()` 對 `kind=impl` 產生的 stub brief 不含 `EXPECTED-DELTA:` 區塊）。
而修那五檔 ⇒ 觸發 `_WAIVER_GUARD_FNS` 三道窗守衛 ⇒ 需解凍 ⇒
`test_b45_unfreeze_requires_roles_sot_closure` 要求 `票 B-49` 轉 `CLOSED`，
而 B-49 之閉合條件第 4 項為「**由使用者更新 `scripts/governance_roles.json`**」，該檔**只有使用者可改**。

🔴 **out-of-epic 通道救不了**：`_MSG_PARSE_MARKERS` 含字串 `"Governance-Scope"`，
窗守衛**結構上被禁止解析 commit 訊息**（C1 裁決，由 `test_waiver_guards_never_parse_commit_message` 強制）。
OOE 只鬆綁 `G-7`。兩家獨立覆核此結論成立。

### 安全語義是否有缺口

**限定範圍下沒有**——條件是 `--spec` **經顯式驗證為非空、非全空白、且未重複給值**（見下 §A′）。

生產面能 mint token 的路徑經兩家窮舉**僅** `gate.sh dispatch`
（`dispatch.sh:84`／`committee_run.sh:413` 皆 `exec`／轉呼；`cx_run.sh` 只 `register-output`）。
A 節之①②在該唯一入口收口。`R-12` 的剩餘價值＝縱深防禦 ＋ 讓 `:822` 字面成立。

🔴 **初版此段寫的是無條件的「沒有」，那是過度宣稱**（`CODEX-R1-P2-03`）：
當時 `--spec ""` 可使①②整組不啟動而仍發 token。宣稱與修法同輪落地，本節已改為有條件敘述。

### 機械綁定

`test_full_path_does_not_yet_enforce_expected_delta`（在 manifest allow 內）**凍結為具名行為**——
full path 一旦改為強制，該測即紅，逼下一手回來處理本檔與 `票 B-49`。

---

## C. 對外宣稱限制

| 可以說 | **不得**說 |
|---|---|
| `T-1.3-N1`（缺 `--brief` 即拒）已閉合，並附 kind binding | 「`TODO:822` 已全數達成」 |
| impl 派工之 EXPECTED-DELTA 已在唯一 mint 入口強制 | 「full path 已強制」「R-12 已閉合」 |
| `b4` 階段 2 之 `R-11` 已交付 | 「`b4` 已整批完成」「`票 B-49` 已閉合」 |

---

## D. 本次未動、且不得誤以為可動的東西

- `_B45_HARNESS` 五檔 —— 一字未改。
- `scripts/brief_conformance_check.sh` 之 full path 尾段 —— 一字未改（僅新增 `--only impl-kind` 分支）。
- `scripts/dispatch.sh` —— 不在 allow，**不必改**：`:84` 為 `exec` 轉呼 `gate.sh dispatch`，在 gate 收口即傳遞覆蓋。
- `scripts/governance_roles.json` —— 只有使用者可改。
- `scripts/gate.sh:598-601` 之註解 —— composer 覆核確認**未過期**（該處講的是
  `reconcile_stamps_check.sh` 呼叫之逐字凍結，與 manifest allow 無關），主委原判「已過期」**錯誤，已撤回**。
