# B8（`GOVB1 Task 4.1` / `票 B-38`）— 範圍延伸與具名偏離

> 凍結文件（`docs/GOVB1_INPUT_QUALITY_SPEC.md`／`_TODO.md`）**不就地修改**；
> 本檔為其延伸，記錄本次交付相對凍結宣告的每一處偏離與理由。
> 體例同 `docs/GOV_B6_SCOPE_AMENDMENT.md`、`docs/GOV_B7_SCOPE_AMENDMENT.md`。

- **標的**：`GOVB1 Task 4.1` — findings-kind 產出的機械分類判準
- **實作端**：主委自任　**審查**：codex ＋ composer（兩個非實作者家族）　**日期**：2026-08-10

---

## §1 交付

| 檔 | 動作 |
|---|---|
| `scripts/findings_kind_classify.sh` | 新建（`--single`／`--audit`／`--sample`／`--wilson` 四模式） |
| `tests/governance/test_govb1_findings_kind.py` | 新建（26 tests） |
| `tests/governance/test_govb1_zeroid_no_regression.py` | 新建（9 tests） |
| `handoffs/20260810-govb1-b8-fp-receipt.md` | 新建（§V-FP 誤擋率 receipt） |

三個 code 路徑**都在 `govb1_scope.manifest` allow 內** ⇒ 一般 commit，不走 out-of-epic。

---

## §2 🔴 凍結 TODO 偽碼的**兩個靜默 bug**（照抄會壞，且不報錯）

`docs/GOVB1_INPUT_QUALITY_TODO.md:1065-1071` 給了參考實作：

```sh
v="$(LC_ALL=C jq -r --arg k "${bk}" '.kinds[$k].is_findings_kind // "unknown"' …)"
```

**兩處與實況不符，且都是靜默失敗**（不報錯、只是全部判成 `unknown`）：

| # | 偽碼 | 實況 | 後果 |
|---|---|---|---|
| 1 | 欄位名 `is_findings_kind` | SoT 的欄位是 **`produces_findings`**（`jq 'keys'` 實測，`is_findings_kind` 不存在） | 全語料判 `unknown` |
| 2 | `… // "unknown"` | jq 的 `//` **把 `false` 視同空值**（`jq -n 'false // "u"'` → `"u"`） | `produces_findings=false` 的 kind（`impl`／`stamp`）被誤判成 `unknown` |

**採用**：`has("produces_findings")` ＋ 型別為 `boolean` 才取值，否則 `unknown`。

承重證據（各一條定向 mutation，實跑轉紅）：
- `test_mut_wrong_sot_field_name_makes_everything_unknown`
- `test_mut_jq_slash_slash_regresses_false_kinds`

🔴 第 2 點若沒被抓到，會是**最惡性的一種錯**：`--audit` 照樣 rc=0、照樣印出漂亮的矩陣，
只是每一格都錯。發現途徑是 smoke test（`--single` 對一份 `brief-kind: stamp` 的 brief 回 `unknown`），
不是讀碼讀出來的。

---

## §3 🔴 覆蓋率：分類器只回答 **16.8%** 的語料，其餘按 SPEC 判 `unknown`

SPEC 目標寫的是「哪些**產出**應該有 findings」，但 TODO 的判準是讀檔內的 `brief-kind:` 宣告。
委員**產出檔**多數不帶該行 ⇒ 一律 `unknown`。

實測（`--audit --corpus handoffs`，分母 2956）：

| 分類 | 檔數 | 佔比 |
|---|---|---|
| `findings` | 290 | 9.8% |
| `non-findings` | 198 | 6.7% |
| `unknown` | 2468 | **83.5%** |

⇒ 判準對 **83.5% 的語料不表態**。這**符合** SPEC 邊界 ③「未知 kind ⇒ `unknown`，不得猜」，
但**未達成** SPEC 目標句所指的「產出」範圍。

**主委提案（🔴 尚未實作，等裁決）**：委員產出檔名遵守
`handoffs/<session>-<family>.md` ↔ `handoffs/<session>-brief.md` 的對應
（由 `committee_run.sh` 機械產生，非慣例）。
據此把產出檔連回**該輪 brief 的 kind**，是**導出**不是猜測。

🔴 **本次刻意不先動手**——`票 B-51`（B7 的教訓）：
OOE／偏離凍結文件須**先取得裁決才動碼**。故此處只提案，實作等 review 輪裁定。

**請committee 裁定**：(A) 現況（只認自帶 `brief-kind:` 者）即滿足 Task 4.1
(B) 應補上 brief 連結導出，本票內做　(C) 應補，但另立票。

---

## §4 🔴 三入口交叉 oracle：**只閉合一欄，另兩欄具名阻塞**

SPEC 要求「三入口 × 三輸入，逐格 rc 改前 == 改後」。實況：

| 欄 | 狀態 | 說明 |
|---|---|---|
| `completeness --single` | ✅ **已閉合** | 三格基準**量測**取得（主委初版用猜的，其中一格就錯）；另附鑑別力對照，證明「三格全 0」不是因為該欄不看內容 |
| `completeness --lock` | 🔴 **阻塞** | 手搓 `sources.lock` 三格全 rc=1，是 lock **結構性失敗**而非輸入差異 ⇒ 假看守。正解＝用 `reconcile_build.sh` 產真實 lock，需要不汙染真實 session 空間的隔離方案 |
| `cx_run` 交件路徑 | 🔴 **阻塞（不可達）** | `CX_STUB_MODE=success` 會呼叫 `_write_stub_success_output` **覆寫 `${out}`** ⇒ 三種輸入傳不進去；而 `cx_run.sh` 在 Task 4.1 的檔案欄是**只讀（本 Task 不改）** ⇒ 無法新增「保留既有輸出」的 stub 模式 |

🔴 **兩欄都做成「逼債條款」而非靜靜缺席**：
- `test_lock_column_requires_real_reconcile_not_handcrafted`
- `test_cxrun_column_is_blocked_not_passing` —— 一旦 `cx_run.sh` 出現保留輸出的 stub 模式
  （B10 的 `format-failed` 補救層很可能會加），該測試**立刻紅**，逼下一手補上第三欄。

**請committee 裁定**：第三欄的不可達是否為 Task 4.1 的**允許偏離**（因為它與檔案唯讀欄直接衝突），
或應把該欄移到 B10（屆時 `cx_run.sh` 本來就可改）。

---

## §5 誤擋率 receipt

`handoffs/20260810-govb1-b8-fp-receipt.md`：分母 2956、抽 n=100（決定性、可重現）、
FP=0、**95% CI [0.00%, 3.70%]** ≤ 5% 門檻。

- 抽樣用 djb2 雜湊排序，**不用** `shuf`／`$RANDOM`（不可重現）、
  **不用**檔名排序（帶日期會系統性偏向早期輪次）。無偏性佐證見該檔。
- Wilson 實作以 **SPEC 自己的兩個數字**當 oracle（n=50→7.14%、n=100→3.70%），
  測試 `test_wilson_reproduces_spec_numbers`。
- 🔴 §V-FP 要求「主委標註 → 至少一非實作者家族複核」⇒ **本 receipt 在 review 輪複核前不算完成**。

---

## §6 觀察到的殘留（不在本票 scope）

- 語料中 **8 個舊 brief** 的 `brief-kind:` 值格式不合規（值後黏 `；`／`;`），判 `unknown`。
  fail-closed 正確；依「面向未來不溯及既往」不回頭修，具名記錄。
- `stamp` 的 `produces_findings: false` **與實況不符**——B7 的兩輪 stamp 各產生了實質 findings
  （`票 B-52`）。本票**不改判**（Task 4.1 只產判準），但分類器會忠實地把 stamp 判為
  `non-findings`，因此那些 findings 依舊沒有 canonical 落點。歸 B9（Task 4.2）。

---

## §7 委員裁決（`20260810-GOVB1-B8-REVIEW-R1`）

兩家皆 **Verdict＝需修補後派工**。codex 5 條、composer 5 條，**全數接受**。

| finding | 兩家立場 | 主委處置 |
|---|---|---|
| receipt 過期（`CODEX-P0-01`／`COMPOSER-P1-03`） | 一致 | **修**：重跑 r2 版，並新增**語料清單指紋**——`handoffs/` 每輪都在長，沒有指紋就無法複驗到同一分母 |
| CRLF 兩路徑分歧 ＋ 缺檔／空 `.kinds` 未 fail-closed（`CODEX-P1-02`） | — | **修**：兩路徑統一剝 CR；缺檔與空 `.kinds` 改 rc≠0 |
| 覆蓋率（`CODEX-P1-04` (C) 另立票 ／ `COMPOSER-P1-01` (B) 本票補） | **分歧** | **採 composer (B)，本票內補**——composer 給了可行性論證，codex 只是 scope 紀律考量而非認為方案錯。實測 unknown 2468→**2362**、findings 290→**330** |
| `--lock` 欄逼債不算完成（`CODEX-P1-03`／`COMPOSER-P1-02`） | 一致「做得到」 | **修**：改用 schema 完整的 review-mode lock，三格基準 **1/1/0**（有鑑別力），並加反空轉斷言 |
| `cx_run` 欄移交 B10（`CODEX-P1-03`／`COMPOSER-P2-02`） | 一致 | **接受**：保留逼債條款，正式移交 B10 |
| `--audit`/`--single` 一致性只比總數（`COMPOSER-P2-01`） | — | **修**：改為**逐檔配對**比對（原版兩檔互換分類而總數不變會假綠） |
| guard 只看工作樹、caller glob 漏 `scripts/git_hooks/`（`CODEX-P1-05`） | — | **修**：範圍由「第一個觸及交付物的 commit」導出（不用 epic base——那會把別票改動算到 B8 頭上，實測會誤報）；掃描改遞迴 |

🔴 **主委在「覆蓋率」一項被兩家從不同角度指出同一件事**：
主委說「依 `票 B-51` 先取得裁決才動碼」，brief 中自請攻擊「這會不會是用程序當藉口少做一半」。
composer 判**是**（Task 4.1 未完成，應本票補）。主委接受並補上。
⇒ `票 B-51` 的正確用法是「**先問再做**」，不是「**問了就可以不做**」。

### 仍未關閉（移交）

- `cx_run` 第三欄 → **B10**（屆時 `cx_run.sh` 本來就可改）。
  逼債條款 `test_cxrun_column_is_blocked_not_passing` 保留：一旦出現保留輸出的 stub 模式即紅。
- 覆蓋率仍有 **79.8% unknown**——多為採用 `<session>-brief.md` 慣例**之前**的舊檔，
  依「面向未來不溯及既往」不回頭處理，具名記錄。
- 誤擋率 receipt 的**非實作者複核**：r1 兩家已各自複驗 18/22 個分類檔並確認符合 SoT，
  但 r2 版 receipt（含 4 個新導出檔）**尚未複核** ⇒ 待下一輪。
