# fracdiff max_lag 三方值守恆簽核 — Claude 腿

> 2026-07-03 | SPEC=docs/FRACDIFF_MAXLAG_SPEC.md §G | 依 R3-RECONCILE D3（雙戳記）

## 我的結論：PASS（範圍聲明見 §4）

## §1 證據鏈（全部引用實際 receipt，無合成資料）

1. **Golden 凍結**（`20260703T042407Z-fracdiff-maxlag-golden-{G1,G2}.json`，真實 kline BTC+ETH×1h、MR 同款 config 窗 2081、每 run 獨立空 d\* cache）：
   - G1 穩定性：兩次獨立跑 frame digest 檔載相同（stability_precheck.passed=true）。
   - G2 pin 生效：payload `max_lag=50`（G1=208=2081//10 len 耦合活體）、`fracdiff_hash` 與 G1 不同、`pin_method=preprocessor_instance_fracdiff_config_injection`。
2. **§G 四條件**（`20260703T085226Z-fracdiff-maxlag-postfix-compare.json` 檔載「passed=true, failures=[]」）：
   - 條件1 修後 auto（fresh cache）vs 修前 pin50：**全欄 digest 0 差異**（BTC/ETH fracdiff+非fracdiff 皆 0）→ 變更純由窗寬造成。
   - 條件2 修後 vs G1：非 fracdiff 欄 0 差異＋row/index 相等；fracdiff 欄 4546/3435 欄不同（預期）；G1 實際 max_lag=208 落檔。
   - 條件3 G2'（Task 1.2 schema 落地後真 config 路徑 pin50）vs 修後 auto：**全欄 0 差異** → 注入等價＋config 逃生口修通（D 增強）。
   - 條件4 修後 resolved max_lag==50（auto 推導正確）。
3. **條件 4'（截斷不變，§G 為必要非充分之補）**：d\* gate 兩窗（2081/2071）相等已由 slow 實跑證明（`20260703T094044Z` 輪 d\* gate 通過、失敗點皆在下游 storage 層）。
4. **可證偽護網（防回歸）**：3 個 max_lag len-coupling mutation 探針 PASSED（截斷/尾擾/parallel，monkeypatch resolver seam，`20260703T094044Z`）；full_fit 控制 PASSED；calibration 單邊擾動控制（D2 重設計+約束作者放寬 match）＝**唯一未落 receipt 項，見 §5 補記，PASS 前提條件**；P1-FF-6 cache key 7 mutant PASSED＋`mutation_probe_check.sh` exit 0（`20260703T053419Z`）。
5. **附帶修復的等價鏈**：conv FFT→direct 為 MRFAIL-RECONCILE（雙戳記）獨立段，oracle=direct 下尾擾 prefix drift 精確 0（Codex 實驗）＋d\* gate 綠；與 §G 比對（雙邊皆 FFT 基礎）不混。

## §2 反例嘗試（adversarial 腿要求）

- 換 symbol：BTC 與 ETH 獨立比對皆 0 差異（非單 symbol 巧合）。
- 換窗長：G1 208 vs pin 50 證明窗寬敏感性真實存在（若比對法無效，這裡就不會抓到 4546 欄差異——比對法的靈敏度有陽性對照）。
- 抽樣 hash 假綠風險：oracle 為 per-column 全量 value/nan-mask sha256（禁抽樣，Composer B1 finding 修訂後），identity 自檢與 G1vsG2 陽性對照皆通過。
- cache 套套邏輯：修後跑 fresh 空 cache（hit=0 起算）、receipt 載 hit/miss，非重放 G2 cache。

## §3 pre-existing 殘留聲明（R3 D3，使用者可見）

- **storage codec 截斷變異（已確認根因，另立案）**：L7 per-column parquet codec（float16/32）依全窗值域選型 → 窗長/尾值洩入儲存精度。症狀=idx508 NaN 翻面＋2^-7 ULP 值差。**與 max_lag 修復無關、非本 epic 引入**（xfail 遮蔽多時，掀開才見）。影響=兩 fracdiff MR 維持誠實 xfail（reason 已換 codec），轉綠待 storage epic。
- **更正**：MRFAIL-RECONCILE 曾預測「conv 修後尾擾 MR 轉綠」——被 094044Z 推翻（尾擾也吃 codec 翻面），已依 R3 裁決更正。
- 對 IC 定版重生成的含義：max_lag 面值正確性已證；codec 面的截斷敏感性屬存檔精度層（單 run 自洽、跨不同窗長 run 才顯現），重生成採固定窗全量跑不受其影響，但使用者應知情。

## §4 簽核範圍

- 範圍=SPEC §G run contract（BTC+ETH×1h、MR 同款 config）；全量 10 symbols×3 TF 覆蓋發生於 IC 定版重生成（使用者手動觸發）。
- 本腿判定：**max_lag 修復之值守恆 PASS**；storage codec 殘留如 §3 聲明。

## §5 補記（最終控制 receipt）

- **已補填**：檔載「1 passed in 1061.68s」（出處：handoffs/run_receipts/20260703T132059Z-fracdiff-maxlag-d2-control-final.log）——單邊校準擾動經 `columns gate failed (strict)|d_star` 合法路徑觸發（約束作者 Codex 裁定放寬，出處：20260703-FRACDIFF-MAXLAG-D2MATCH-codex.md）。前提條件成立，本腿 PASS 判定生效。
