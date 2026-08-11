# 票 B-49 — 修法形狀之隔離實跑收據（SPEC r4 之事實基礎）

**日期**：2026-08-11　**產出者**：主委（Claude / Opus 5，`implementer=claude`）
**性質**：實跑收據。本檔**只陳述已實跑之事實**，不含裁決；裁決在 SPEC。

🔴 **本檔存在的理由**：SPEC r1–r3 三輪都在爭論「凍結檔要怎麼修」，而那件事一直是
`assumed`。本檔把它變成 `fact-verified`，且**repo 工作區零變更**（全部在隔離副本上做）。

---

## §1 隔離環境怎麼做的（可複驗）

```
bash .claude/tmp/b49_pinshape_probe.sh <隔離目錄>
```

該腳本：把整棵 `tests/governance/` 複製到隔離目錄；`scripts/`、`templates/`、`docs/`、
`handoffs/` 以 **symlink** 指回 repo（因為測試檔用 `Path(__file__).parents[2]` 反推
`REPO_ROOT`）；`conftest.py`／`pytest.ini` 一併複製。

🔴 **邊界**：腳本只讀 repo、只寫隔離目錄。凍結檔的修改**只發生在副本**上。
若 `<隔離目錄>` 已存在則 fail-closed 拒絕覆寫。

⚠️ **已知副作用**：`scripts/` 是 symlink ⇒ 任何**就地** mutate 生產腳本的測試會動到真 repo。
本輪跑的五個檔經檢查皆 mutate 沙箱副本（`h["scripts"]`），故無此問題；
但**擴大隔離跑的範圍前必須重驗這一點**。

---

## §2 基準線（未套修法）

隔離副本上跑那四條，得 **3 failed / 1 passed**：

| 測試 | 基準線 | 拒絕它的是誰 |
|---|---|---|
| `test_result_state_format_failed.py::test_t2_c2_impl_kind_unchanged` | FAILED | `_role_gate.sh`：「實作端須為 claude,但收到 grok」 |
| `test_rolegate_predispatch.py::test_t3_u2_consult_same_set_proceeds` | FAILED | `committee_run` 角色閘 preflight |
| `test_stamp_taskid_inject.py::test_mutation_v12_force_stamp_target_all_kinds_turns_red` | FAILED | `cx_run.sh:850`：「family 須為 codex\|grok\|composer, 得到: claude」 |
| `test_cxrun_selfcheck_prompt.py::test_selfcheck_absent_for_impl` | PASSED | 已於本日先行修好（該檔**不在**凍結集合） |

---

## §3 🔴 兩種紅是**兩種不同的病**，這推翻了先前的修法方向

r1–r3 期間的隱含前提是「這些測試寫死了家族名，改成讀 SoT 就好」。**實跑證明那對三分之二是錯的。**

**形態 A — 寫死家族**（1 檔）
`test_result_state_format_failed.py:607` 逐字寫 `# impl 角色閘：implementer=grok` ＋ `fams=["grok"]`。

**形態 B — 已經在讀 SoT，仍然紅**（2 檔）
`test_rolegate_predispatch.py:343` 用 `_read_implementer(h["scripts"])`；
`test_stamp_taskid_inject.py:2099` 直接 `json.loads(...)["implementer"]`。
兩者都在做「讀 SoT」這件**對的事**，卻仍紅——因為

> `claude` **沒有 CLI 配方**。`cx_run.sh:850` 的家族白名單是 `codex|grok|composer`，
> 而那是正確的：編排端自任實作時，`impl` 根本不對外派工。

⇒ **「把測試改成讀 SoT」不是這批紅的修法。** 對形態 B 而言，讀 SoT 正是致病原因。

---

## §4 🔴 另有一條**沒人列進票文**的靜默失效

`test_stamp_taskid_inject.py:761-771`　`test_v12_non_stamp_kinds_no_stamp_target_ok`

```python
for kind in ("review", "consult", "closure", "impl"):
    ...
    if kind == "impl" and fam not in ("codex", "grok", "composer"):
        pytest.skip(f"unexpected implementer {fam}")
```

`pytest.skip` 在 **for-loop 之內**且該 loop 是**單一測試函式** ⇒ implementer 一旦不是三家 CLI 家族，
**`review`／`consult`／`closure` 三種 kind 的覆蓋一併靜默消失**，整檔仍報綠。

實測：`implementer=claude` 時本測試 **100% 空跑**，而 CI 顯示 `1 skipped`。
⇒ 這正是票文 ② 之 `skipped=0` 要擋的東西，但先前無人指出它會**連帶吃掉另外三種 kind**。

---

## §5 修法：釘定**沙箱**名冊（新增 1 個未凍結模組 ＋ 凍結檔內 6 處小改）

新增 **`tests/governance/_role_pin.py`**（新檔，**不在**凍結集合，**已落地 repo**），單一定義處。
兩個公開函式：

**`cli_dispatchable_families() -> tuple[str, ...]`**
🔴 **這是票文閉合條件 3（「禁再硬編三元組」）的正面答案。** 家族清單**不得寫死**，
由**兩個獨立來源導出並交叉比對**：

| 來源 | 取法 | 現值 |
|---|---|---|
| ① `scripts/governance_families.json` 之 `review_families` | SoT 中「會被派工的委員家族」 | `codex, composer, grok` |
| ② `scripts/cx_run.sh` 含 `_prepare_and_run` 的 `case "${fam}" in` 分支 | 執行期真相 | `codex, grok, composer` |

兩者不一致 ⇒ `AssertionError`（fail-closed）。
⇒ 這不是「挑一個來源信」，而是把本 repo 反覆出事的**「同一概念兩處定義不一致」做成偵測器**。

🔴 **錨點選擇的理由**：錨 `_prepare_and_run` 這個 **dispatch 動作**，不錨錯誤訊息字串
（`"family 須為 codex|grok|composer"`）。訊息會被改寫，分支不會。
找到的區塊數 ≠ 1 ⇒ 拒絕猜測，直接紅。

⚠️ **已排除的錯誤選項**：`governance_families.json` 有 `executor_clis`
＝`['codex','cursor-agent','grok','agy']`，看似正解但**是 CLI 執行檔名不是家族名**
（`cursor-agent` 之家族為 `composer`；`agy` 為 `advisory_only`）。**主委第一版差點用錯它。**

**`pin_implementer(scripts_dir, fam=None) -> str`**
把沙箱名冊釘成 `fam`（預設 `allowed[0]`），同步改寫 `reviewers`＝`eligible` 扣掉 implementer。

🔴 **邊界（寫進 docstring，不靠紀律）**：只准改 `scripts_dir` 指向的**沙箱副本**。
repo 的 `scripts/governance_roles.json` 是使用者專屬 SoT，任何測試都不得寫它。
五個 fail-closed 分支（SoT 缺檔／`review_families` 型別錯／錨點失配／清單漂移／
`fam ∉ eligible`）使「釘不成功」不可能靜默通過。

**為什麼這是對的**：這些測試要驗的是 **`cx_run.sh`／`committee_run.sh` 在 impl 路徑上的行為**，
與「現實世界誰是 implementer」無關。舊寫法（兩種形態都是）把**測試標的**耦合到**生產設定**，
那是缺陷本身。釘沙箱後，**未來換誰實作都不會再讓這批測試回紅**——這一點是純 A 案／純 B 案都給不出的。

### 凍結檔內的改動（共 6 處 ＋ 3 行 import）

| 檔 | 處 | 改動 |
|---|---|---|
| `test_result_state_format_failed.py` | import ＋ `:607` | 釘定；並把 `fams=["grok"]`／`family="grok"`／輸出檔名／`stub-ok family=` 斷言**全部改用 `fam` 變數** |
| `test_rolegate_predispatch.py` | import ＋ `:343` | 釘定；`fams_csv` 由條件式改為 `",".join(cli_dispatchable_families(...))`（語意仍是「含 implementer」） |
| `test_stamp_taskid_inject.py` | import ＋ `:765`、`:2072`、`:2098` | 釘定；**移除 `pytest.skip` 出口**（§4） |

🔴 `test_result_state_format_failed.py` 那處**第一版我自己寫錯**：`fam` 指派後函式體仍寫死 `"grok"`
⇒ 解耦只是裝飾。已改為全程用 `fam`。**列此以供 review 對照**。

---

## §6 實跑結果（隔離副本，套修法後）

```
python3 -m pytest <ISO>/tests/governance/{test_result_state_format_failed,
  test_rolegate_predispatch,test_stamp_taskid_inject,
  test_cxrun_stamp_prompt,test_completeness_idlike_fp}.py -q -rs
```

| 階段 | 結果 |
|---|---|
| 基準線（四條） | **3 failed / 1 passed** |
| 套修法後（四條） | **3 passed** |
| 套修法後（五個 `_B45_HARNESS` 檔全跑，含移除 skip 前） | **140 passed / 1 skipped**（73.79s） |
| 套修法後（五檔全跑，**移除 skip 後**） | 🔴 **141 passed / 0 skipped**（76.93s） |

⇒ **`skipped=0` 已達成**，且 `test_cxrun_stamp_prompt.py`／`test_completeness_idlike_fp.py`
（rc 本來就 0 的兩檔）**未被波及**——零附帶損害。

---

## §7 已在 repo 落地的部分（不需 `票 B-49`）

兩件，皆**不在** `_B45_HARNESS`，故未動凍結面：

1. **`tests/governance/_role_pin.py`**（新檔）——§5 之模組本體。
   先落地的理由：它是未凍結區，且讓 review r4 的委員**可以直接實跑**，而非只讀 SPEC 上的引文。
2. **`tests/governance/test_cxrun_selfcheck_prompt.py`**——改用 `_role_pin`，**7 passed**。
   除釘定外另補兩條**防偽綠**斷言：原斷言是「prompt **不含** X」，空字串同樣不含 X
   ⇒ 先斷言 prompt 真的組出來（含家族名與產出路徑），否則捕捉檔沒寫成也會綠。

🔴 **主委在此犯了同一個錯兩次，兩次都自己抓到，列此供 review 對照**：
兩處都是「`fam = pin_implementer(...)` 指派後，函式體仍寫死 `"grok"`」
⇒ 解耦只是裝飾，測試照樣綁死家族名。已改為全程用 `fam` 變數。
**這條值得 review 特別針對——它是「看起來修好了但沒有」的典型形態。**

---

## §7b 🔴 review r4 打掉的三個自傷（本收據之更正）

三家 review r4 對**已落地的 Phase 0 程式碼**開了三條，全部成立，全部已修並複驗：

| finding | 病 | 修法 | 複驗 |
|---|---|---|---|
| `CODEX-R4-P1-03` | `reviewers` 寫成 `eligible − {impl}` ⇒ **把無 CLI 配方的 `claude` 算進 review pool** | 改用 `set_roles.sh` 的公式 `eligible ∩ review_families − {impl}`，並加 pool<2 fail-closed | 探針 G4／G5 |
| `CODEX-R4-P1-04`① | SoT 來源固定讀 `REPO_ROOT/scripts/*`，**不是**傳入的 `scripts_dir` ⇒ 沙箱變異看不見，mutation 會假綠 | 兩個來源皆改讀 `scripts_dir`；另加「傳入生產 `scripts/` 一律拒絕」 | 探針 G3／G6 |
| `CODEX-R4-P1-04`② | dispatch 分支 regex 要求**恰好兩空白**縮排 ⇒ 四空白的 `evil)` 分支被漏掉（codex 附探針） | 縮排改為任意；並修 `case` 區塊**結尾錨點**（見下） | 探針 G2 |
| `GROK-R4-P1-03` | 本收據 §5 表格仍寫字面 `fams_csv="codex,composer,grok"`，與「禁硬編三元組」自相矛盾 | 已改為 `",".join(cli_dispatchable_families(...))` | 本節 |

🔴 **修 `CODEX-R4-P1-04`② 時揭出一個更深的問題**：`case` 區塊的結尾錨點原寫 `\nesac`（頂格），
但 `cx_run.sh:727` 的 `esac` 有四個空白縮排 ⇒ 區塊比對**一路吞掉兩個 case 區塊**
（`:699` `_prepare_and_run` 內層 ＋ `:840` 外層 dispatch），家族名各出現兩次。
舊版之所以「看起來對」，**純粹是因為兩塊縮排剛好不同**（內層 6 空白、外層 2 空白），
而舊 regex 恰好只收 2 空白。⇒ **它一直是靠巧合正確的。**
放寬縮排後立刻顯形（重複家族名 ⇒ 漂移偵測器轉紅），修法＝結尾錨點改 `\n[ \t]*esac`。

**承重探針**：`.claude/tmp/rolepin_probe.py`，**7 格全 PASS**——
G1 基準線／G2 四空白 `evil` 分支／G3 沙箱 SoT 變異可見／G4 reviewers 不含 `claude`／
G5 三個合法家族逐一可釘（此格即票文條件 2-② 之證據）／G6 拒絕操作生產 `scripts`／
G7 `claude` 不得被釘。

**修法後隔離複跑**：五個 `_B45_HARNESS` 檔 **141 passed / 0 skipped**（70.67s）——與修法前同值，
證明這三個修正**未改變**測試行為，只改變其正確性邊界。

## §8 這份收據**不**主張的事（誠實邊界）

1. **不**主張 `票 B-49` 可以閉合——閉合條件 ①②③ 之 selector 設計仍是 SPEC 的事。
2. **不**主張凍結面可以被繞過：三個檔仍在 `_B45_HARNESS`，任何 diff 仍會觸窗守衛
   ⇒ **path grant 依舊必要**。本收據只把「grant 之後要放什麼 diff 進去」變成已知。
3. **不**主張隔離副本等於真環境：`scripts/` 是 symlink，且未跑全套
   （全套 ≈615s，且與主控端動檔互斥）。**併入 repo 後必須全套實跑複驗。**
4. **不**主張 `DEFAULT_PIN = "grok"` 有特殊地位——任一 CLI 家族皆可，選 grok 只為讓 diff 最小。
