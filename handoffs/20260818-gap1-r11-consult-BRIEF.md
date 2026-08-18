# GAP-1 殘留 G1-R11 諮詢：Sharpe 對「常數／近常數序列」之退化判定——業界／文獻怎麼算？（三家 consult，唯讀研究）

VERIFY-EXEMPT:doc-example:gap1-r11-consult-questions

> 本檔為提問清單；結論在你們的產出與收斂檔。使用者 2026-08-18 指示：「G1-R11 你跟委員參考現實量化或金融投資是怎麼計算的」。

brief-kind: consult

## 問題
`momentum/Analysis/strategy_validation/sharpe.py::compute_sharpe`（Task 1.2，已蓋章）以 `std == 0.0` **精確比對**判「常數序列 ⇒ 退化 ⇒ NaN＋status 非 ok」。
B4 review 兩家實跑：80 個 `0.01` 之序列（**數學上完全相同之值**）因浮點求和捨入，`values.std(ddof=1) ≈ 1.75e-18 ≠ 0` ⇒ 不視為退化，回 SR ≈ 5.7e15。
PBO（Task 4.2）之 path 級退化判定沿用同語意（`pbo._sharpe_pp_1d` 逐位等價）。登記為殘留 **G1-R11**（needs-research：容差判準）。

## 主委自產版（請攻）
1. **這不是「容差」問題，是「常數判定用錯量」**：序列是否常數應直接判 **`values.max() == values.min()`**（`np.ptp(values) == 0`）或 `np.all(values == values[0])`——
   對「所有輸入值精確相等」之序列**恆真且不受求和捨入影響**；對「近常數但確有微擾」（如 `0.01 + 1e-9·k`）之序列，其變異數是**真實的**、SR 巨大是**數學上正確**的結果，不該用人為容差抹掉。
   ⇒ 建議修法：退化條件由 `std == 0.0` 改為 `std == 0.0 or np.ptp(values) == 0.0`（**無**新常數、無容差選擇問題）；G1-R11 由 needs-research 降為可直接修之小缺陷。
2. 若仍要「相對容差」（例：`std <= 1e-12 * max(1, |mean|)`）——我**反對**：任何 ε 都是自創常數，且會把真實低波動策略誤殺；本專案「禁自創常數／禁調常數參數」精神一致。

## 請你們各自查證（唯讀；可讀 venv 內套件源碼；自建探針一律加 timeout、檔尾 `STATUS: DONE`）
A. **業界實作怎麼處理 std=0／近 0**（各至少讀 3 個真實源碼並貼行號）：`empyrical`／`quantstats`／`pyfolio`／`vectorbt`／`ffn`／`pandas`／`scipy` 中與 Sharpe 或 SR-like 統計相關者——
   是回 NaN、inf、直接除（得巨大值）、還是有 ε？有沒有任何一家用「相對容差」？有沒有用 `ptp`／`all equal`？
B. **文獻**：Bailey & López de Prado（DSR／PSR）、Lo (2002) *The Statistics of Sharpe Ratios*、Sharpe (1994) 對「零波動」有無定義（無風險資產／退化）？
C. **主委方案之反例**：`ptp == 0` 判常數是否有漏（例：`[0.01, 0.01, 0.010000000000000002]` 這種**同一數學值不同 double 表示**之序列會被視為非常數——這在真實資料管線中可能發生嗎？如 CSV 解析／float32→float64 轉換）。
D. **對 PBO 的影響**：CSCV 之 IS／OOS 切片若為常數欄（例：策略某段全零報酬＝已正確 NaN；某段全 `0.001`？），你的建議會改變 golden 三案例嗎（應不會，請實跑確認 `test_pbo.py` 之三案例 excl 仍 0）。
E. **修法歸類**：若採 `ptp==0`——它是「實作 bug 修補（SPEC 字面『常數序列 ⇒ NaN』本就如此）」還是「語意變更」？前者可走小任務＋三家 review；後者須延伸檔＋三家 adversarial。請給判定與理由。

## 本 brief 前提（逐條標）
fact-verified: `compute_sharpe` 退化條件為 `std == 0.0`（`sharpe.py:89`）→ 主委讀碼
fact-verified: 80 個 `0.01` 之序列 `values.std(ddof=1) ≈ 1.75e-18`、`compute_sharpe(...).value_per_period ≈ 5.7e15`（非 NaN）→ composer R18 P2-02 實跑；主委 `test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe` 之 `0.01` 欄斷言 `abs(got)>1e6` 通過
fact-verified: `np.ptp(np.full(80, 0.01)) == 0.0`（所有元素為同一 double）→ 主委實跑
assumed: 業界主流套件（empyrical／quantstats／vectorbt）對 std=0 多數**不**特判或回 inf／NaN，且**無**採相對容差者 ← 請查證（段 A）
assumed: 真實資料管線不會產生「同一數學值、不同 double 表示」之常數序列 ← 請攻（段 C）
assumed: `ptp==0` 修法不改 golden 三案例 ← 請實跑（段 D）

## 範本
`templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md` 全文照做（§0 挑戰前提／canonical 四欄／Verdict）；finding 格式依 `templates/COMMITTEE_FINDING_TEMPLATE.md`。
ID＝`## <FAMILY>-R20-P<0-3>-<NN>`，**本輪輪次=R20**（task-id `20260818-GAP1-X-CONSULT-R20`）；零 findings 用 sentinel `## <FAMILY>-R20-P3-00`。

## 產出
Verdict（採主委方案／改為相對容差／維持現狀不修）＋ A–E 之查證證據（源碼行號／文獻條目）＋canonical findings。
禁改碼／禁 commit／禁 push。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
