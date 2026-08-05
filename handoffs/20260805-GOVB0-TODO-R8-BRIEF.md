# 第 0 批 TODO 確認輪（R8）

brief-kind: review

target: `docs/GOVB0_FRICTION_TODO.md`（692 行，`template_check todo` rc=0）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。本 brief 只收斂範圍。

## 🔴 finding heading 格式（**直接引用檢查器的正則，勿依賴散文描述**）

`scripts/completeness_check.sh:153` 的 canonical 正則**逐字**為：

```
^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$
```

⇒ **本輪合法範例**：`CODEX-R8-P1-01`／`COMPOSER-R8-P0-02`
⇒ **注意**：`P` 後只能是 `0`–`3`；序號**至少兩位數**；**必須有 `R<數字>` 段**。

🔴 **出生事故（本 brief 前一版）**：主委手寫成 `<家族>-TODO-P<嚴重度>-<序號>`，**漏了 `R<數字>` 段**
⇒ 兩家產出**全部** `invalid finding ID`、整輪 format-failed。
此為本日第三次 brief 誘導格式失敗（前兩次是要求逐條 `##` 分段），
共同根因＝**主委手寫機器依賴格式進 brief，而非自檢查器正則導出**（`票 B-16`／`B-17` 病型）。

**本輪唯一允許的 `##` 標題**：`## Verdict`／`## §0 前提宣告`／`## 逐項核對表`／`## 出場判準核算`
＋ 上述 canonical finding heading。**其餘分段一律用 `###`。**
若結論為零 findings，請明寫一行 `FINDINGS_COUNT: 0`（`票 B-38`）。

## §0 前提宣告

**已查證**（可自行復跑）：

- fact-verified: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0。
- fact-verified: SPEC Task 數 **11**（`grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md`）
  == TODO Task 數 **11**（`grep -c '^### Task ' docs/GOVB0_FRICTION_TODO.md`）。
- fact-verified: `_bc_kv` 為 `mktemp` 暫存檔路徑變數非函式 → `grep -n '_bc_kv' scripts/cx_run.sh` 命中 `:39/:44/:45/:46/:47`。
- fact-verified: `_prepare_and_run`(`:501`) 呼叫 `_run_cli_and_emit`(`:513`)，非反向 → `grep -n` 實測。
- fact-verified: `票 B-14` 票面已含「未定稿」→ `LC_ALL=C grep -c 未定稿 handoffs/20260801-GOV-AMEND-BACKLOG.md` → **4**（修補前為 0）。

**假設**（請優先攻）：

- assumed: **9 條修補彼此不衝突**。主委逐條修但**未做交叉一致性複查**，
  特別是 B0 的加入是否使既有 Gate 敘述前後矛盾。
- assumed: **本輪追溯已完整**。上一輪 composer 抓到兩處漏列（`OPEN-2`／`E-9`）⇒
  主委對「§T 追溯表已 100% 覆蓋」的信心**已被實證推翻一次**，本輪仍可能有漏。
- assumed: **新增的 5 個 Test ID 在實作端可構造**（尤其 `TEST-3.2-LOCK-⑬` 的 ③→④ crash probe
  與 `TEST-3.1-MANIFEST` 的 49／50 筆構造資料）。**未實作、未實跑。**
- assumed: `票 B-14` 的 bounded section 擷取法（`^## B-14 ` 至下一 `^## B-`）
  在 backlog 後續改動下仍穩定。未驗證 backlog 標題格式是否會變。

## 本輪定位：**確認輪**——你們上一輪的 9 條已全部修畢

**不重開已裁決事項。** 逐條確認關閉即可。

### codex 的 5 條（含 2 BLOCKING）與主委修法

| 原 finding | 主委實測結果 | 修法 |
|---|---|---|
| `P0-02` TODO 引用不存在的 `_bc_kv` helper、caller 方向寫反 | **屬實**。`grep -n '_bc_kv' scripts/cx_run.sh` 顯示它是 `mktemp` 暫存檔路徑變數（`:39`），非函式；`_prepare_and_run`(`:501`) **呼叫** `_run_cli_and_emit`(`:513`)，方向與主委原文相反 | Task 1.1 輸入改為既有 `${_bk}`（`cx_run.sh:46`）並貼出 `:39/:45/:46/:47` 實際機制；修改檔案改為 `_prepare_and_run`（`:501-513`）；既有 caller 改為 `:518`／`:521`／`:524` |
| `P0-03` B5 排序悖論（依賴 B3/B4 卻要求 snapshot 在 B3 前凍結） | **屬實**，且後果嚴重：B3 改完才複製 snapshot ⇒ 差集 oracle 失效 | 新增 **B0 前置批**（純步驟，無 Task），產出 snapshot＋`.sha256`；B3 依賴改為 `B1, B0`；新增 **B0 → B3 硬 Gate**（`git ls-files --error-unmatch` rc=0 且 sha256 相符）；Task 2.5 改為只**消費**該 snapshot，缺失或 sha 不符即 fail-closed |
| `P1-04` §0 三項宣告不能全部機械讀取 | **屬實**。`grep -c 未定稿 handoffs/20260801-GOV-AMEND-BACKLOG.md` → **0** ⇒ `TEST-3.3-PROVISIONAL` 條件③**恆為 FAIL** | ①`票 B-14` 補「狀態（2026-08-05）」段，明載未定稿與門檻（現 count=4）②條件③改為 **bounded section** 擷取（`^## B-14 ` 至下一 `^## B-`）③Task 3.1 新增 `handoffs/duration_manifest.json` 的路徑／schema／producer／`status` 純函式導出 ④新增 `TEST-3.1-MANIFEST`＋其 mutation、`TEST-3.3-B24-PARTIAL`、`TEST-3.3-H2-RESIDUAL`、`TEST-3.2-LOCK-⑬`（③→④ crash 孤兒） |
| `P1-01`／`P1-05` | 併入上述修補 | 同上 |

### composer 的 4 條與主委修法

| 原 finding | 主委實測結果 | 修法 |
|---|---|---|
| `P1-01` SPEC §N 要求 `OPEN-2`／`D-8`（locale 守衛，`票 B-33`）寫入 TODO §0，主委漏列 | **屬實** | §0.2 新增該條，並加一句實作指引：本批新增守衛**若依賴中文字串比對，非 UTF-8 環境同樣會失效**，請優先用 ASCII 錨點 |
| `P1-02` SPEC Task 3.2 的 `E-9` publish／timeout 順序契約無對應 Test ID | **屬實** | 新增 `TEST-3.2-E9-ORDER`：①先 CLI wait 再 format check／publish ②該 attempt 的 `committee_family_result` **計數 == 1** ③競態時仍維持②；附兩個反向 mutation |
| `P1-03` `TEST-3.3-PROVISIONAL` 條件③無機械錨點 | **屬實**（與 codex `P1-04` 同一條） | 同上 |
| `P2-01` SPEC §V 要求全 11 Task 皆有 mutation，Task 2.5 無 | **屬實** | 新增 `TEST-2.5-MUT` 三個 mutation（sha 守衛／附加項標註守衛／空語料 fail-closed），各須貼實跑 rc |

## 你要確認的

| # | 查什麼 | 通過條件 |
|---|---|---|
| 1 | 上表 9 條是否**真的關閉** | 逐條標 CLOSED／NOT-CLOSED，附你自己的實跑命令與結果 |
| 2 | **修補是否引入新矛盾** | 特別查 B0 的加入是否使既有批次依賴或 Gate 敘述前後不一致 |
| 3 | **追溯完整性複查** | 上一輪 composer 抓到 `OPEN-2`／`E-9` 兩處漏列 ⇒ **請重跑一次全量 SPEC 具名 ID 對照**，列出你 grep 到的清單與落點 |
| 4 | 新增的 5 個 Test ID 是否**可證偽** | `TEST-3.1-MANIFEST`／`TEST-3.2-E9-ORDER`／`TEST-3.2-LOCK-⑬`／`TEST-2.5-MUT`／`TEST-3.3-B24-PARTIAL`：mutation 是否真的會轉紅？ |

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`，不計入 findings）

1. 重開 SPEC 的設計裁決（已七輪收斂＋三家戳記）。**例外**：該決策使 TODO 無法被實作。
2. `E-SCOPE` 四項、R7 兩條殘留（`H-1`／`H-2`）。
3. **防蓄意繞過**類——本批目標是擋意外。
4. 措辭／可讀性／命名一致性。
5. 「委員債務無 OPEN」不必查（派工本身會開債）。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ TODO 標 Internal Frozen，進實作。**

## 硬性要求

1. **禁改碼、禁改 TODO／SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
4. 每條 finding 附**可執行修法**（具體到「哪個 Task 的哪一欄補什麼」）。

## 產出

上表四項逐項判定、findings（若有，用 canonical heading）、`## 出場判準核算`。
收尾清 /tmp workdir（保留 claude-501）。
