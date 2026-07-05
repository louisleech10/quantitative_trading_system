<!--
SPEC 範本 V13 — Compliance-First / Gate-Anchored（取代 V12 重型版）
為何這版能被真的 follow：
1. 緊湊：強制核心一螢幕內；rigor 靠「分層」展開，不靠「全篇鉅細靡遺」（長度是 follow 的敵人，V12 過長導致被改寫）。
2. 錨點綁 gate：下列 `## §X` 是 greppable 必填錨點。派工/freeze 前 `scripts/template_check.sh spec <file>`
   grep 它們，缺一個 → gate FAIL 擋死。「有沒有照範本」是機器驗的，不靠 Claude 誠實或記性。
3. 照失敗模式設計：每個必填欄對應一個真實事故（沒問使用者/漏 Golden/驗收不可證偽/Phase 依賴矛盾/沒跑 adversarial）。
用法：複製本檔，填 {{...}}；不適用的必填段「不可刪」，移到 §N 標 N/A+理由。
必填錨點（gate 檢查 spec）：§RISK §A §C §P §V §R §N；§G 在高風險(a/d)時必填，否則於 §N 標 N/A。
舊 V12 的重型機制（per-Task 偽碼/函式名、Golden、邊界測試、人工確認）全保留，只是重構成緊湊+分層+機檢。
複製為 SPEC 後刪除本 HTML 註解。
-->

# {{專案/任務名稱}} — SPEC

> 來源 PLAN/診斷：{{路徑 / N/A}}　|　日期：{{YYYY-MM-DD}}　|　對應 TODO：{{由 TODO_GENERATION_PROMPT 生成的路徑}}

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：{{小 / 中 / 大}}（接 CLAUDE.md 任務分派規則）。
- **命中高風險原則**：{{勾並說明 (a)數值/資料品質 (b)跨模組共用路徑 (c)多phase/難回退 (d)ML/回測正確性}}。
- **RISK-HIT 宣告**（機檢依據，缺行 FAIL）：`RISK-HIT: <a,b,c,d 子集|none>`（例：`RISK-HIT: b,c` 或 `RISK-HIT: none`）。
- 命中 (a) 或 (d) → **§G Golden 必填、adversarial review 必跑**（gate `--adversarial`）。

## §A 假設與待使用者確認（事故：拿推論代替問人）
> 寫程式/開委員會前，列出「code/log 推不出、只有使用者或執行期知道」的事實，**先問再做**。
- **FACT-RECEIPT 格式**（資料結構/型別/單位斷言必填）：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`
- **已驗證事實**（附 receipt；缺 receipt 機檢 FAIL）：{{例：FACT-RECEIPT: `echo probe` → 印出 `probe`（作者 實跑 YYYY-MM-DD）}}
- **待使用者確認**（未確認前不得實作）：{{例：UI 模式}}；無待決寫 **`待確認：無`**（精確字樣，勿寫「待回覆」）。
- **已確認結果**：`YYYY-MM-DD 使用者<來源/摘要>`（須含日期+使用者；禁止混入待回覆/未確認）。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條（`grep "from api\." momentum/`→0、服務不互 import 等）、不可違反原則（跨tier/多symbol/資料品質/不弱化 NaN·inf gate/不擅改輸出大小）。
- 本任務特別注意：{{會踩的共用路徑 / 下游消費者 / 既有 caller}}。

## §G Golden / Baseline（高風險(a/d)必填；否則移 §N 標 N/A+理由）
> 凡改「數值正確性/特徵計算/ML 路徑」，必須有客觀 baseline 證明行為不變，否則驗收=口說。
- **feature/kline 條件**：涉 feature/kline 生成/計算/merge/split/洩漏 → 須真實 `data_cache/feature_klines/kline_cache.h5`+三方簽核計畫；禁合成 fixture；**不適用即略過**。
- **凍結時機 / reference 設定**：{{動工前用什麼 symbol+config 跑 baseline，存哪（路徑寫死）}}
- **baseline 內容**（須能抓「值重排/局部錯位/同矩漂移」，非只 aggregate）：
  名稱集合 sha256 + 數量/schema + 每 feature mean/std/nan_ratio + **抽樣 value hash + NaN mask hash**。
- **通過條件（可證偽，容差分尺度）**：nan_ratio exact；mean/std/value `abs≤atol 或 rel≤rtol`（float32 放寬）；
  超出即列出該 feature + 實際 diff = FAIL。**改前==改後 / 單==多 對照一致**。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）
> 每 Phase 一句目標 + 依賴前置。**自檢：每個 Task 的輸入來源 Task，確認無「依賴尚未完成的後續 Phase」。**

### Phase N — {{標題}}（依賴：{{前置 Phase/Task 或「無」}}）
**Task N.x — {{名稱}}**
- 目標：{{一句}}　檔案：{{精確到函式名}}　既有 caller/影響面：{{列出或「新建無 caller」}}
- 改法：{{關鍵步驟/偽碼/函式簽名；改既有 caller 須列同步點}}
- **驗證（可證偽，禁「更穩定/確認正確」）**：{{具體數值 / 檔案存在 / log 字串 / id 格式 + 測試指令}}
- **邊界（≥2 具體場景）**：{{空輸入 / 全NaN / 單值 / 重啟 / 並發… 各自預期行為}}
- 不可做：{{防過度工程的明確禁止}}

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：RISK-HIT 含 a/d 或測試宣稱驗正確性 → 附可證偽/mutation 設計（引 `docs/TEST_DESIGN_CHARTER.md`）；否則 §N 標 mutation N/A+理由。
- 測試層級：單元 / 整合 / Golden 對照 / 邊界。可獨立 `pytest tests/...` 跑，不需 run_api.py。
- **防假綠**：diff 既有測試斷言，不得放寬/刪除換綠燈；新斷言對應新行為。
- **邊界目錄**（本任務適用者打勾並對應 Task）：空DF / 全NaN列 / Inf / std=0 / 重複·亂序 timestamp / API重啟 / 並發寫 / OOM降載 / 大尺度浮點 reduction。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert；高風險改動包 feature flag（預設 off）一鍵回退；Golden FAIL → 不 merge。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- {{例：§G：N/A — 本任務不碰數值/ML（理由）。其餘省略段同格式}}
