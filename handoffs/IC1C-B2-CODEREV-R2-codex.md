# IC1C-B2 Code Review R2 — Codex (2026-07-14)

範圍：前輪 B1–B5 反例重跑 + rework delta；唯讀審查。SPEC/TODO reconcile stamp checker 兩案皆 PASS。

## 終判
1. **B1 STILL-OPEN（BLOCKING）**：r7/r7b 以 TODO 明文改 Frozen oracle，且近零豁免只允許兩側 `|gi|<0.05`，仍保留有限/[-1,1]/feature 集合/`|diff|≤0.2` 與其餘鍵等值，修訂本身合格、非一般性開後門。但實作 `scripts/ic1c_freeze_baseline.py:1451-1455` 先要求兩值皆非 0 才做同號 gate；反例 `G-NEW=0.0, API=0.2`（max=0.2、diff=0.2）PASS，違反 r7「max(|gi|)≥0.05 強制同號」。實跑 predicate：near-zero opposite PASS、threshold opposite FAIL、zero-vs-material PASS、diff>0.2/non-finite/out-of-range FAIL。
2. **B2 CLOSED**：在 `/tmp` 同 source mirror、壞代理 `HTTPS_PROXY=HTTP_PROXY=ALL_PROXY=http://127.0.0.1:9; NO_PROXY=''` 親跑三命令：collect 20 tests exit 0；mutation 4 passed/23 deselected、PASS；new2 三段 API exit 0、`compared_features=4`、sha256 `4babd5a6...`。mirror 無 `.git`，故 artifact hash 不與 workspace receipt 作 byte claim；gate 行為可離線重現。
3. **B3 STILL-OPEN（BLOCKING）**：conditional metric 已是真 `status` discriminated union，capacity 子鍵也必填；但 profile 仍不精確。`types.ts:2495-2518` 的 GROSS_ONLY 有 spec 不存在的 `skipped?: false`，且 GROSS_ONLY/CostEnabled 是 subtype union，未以 `cost_*?: never` 等方式排除「只帶部分 cost 鍵」混合 profile；`strict:true` 不會把此 union 變成精確物件集合。
4. **B4 STILL-OPEN（BLOCKING）**：Vitest 6/6 PASS，loading 分支存在；但 `NetICChart.test.tsx:42-78` 自建 `runDeepStartCatchingError`，複製 `useICAnalysis.requestJson`/page catch，而非呼叫 production `useICAnalysis.startDeepAnalysis` 或點擊 page handler。故破壞 `useICAnalysis.ts:15-29,320-333` 或 `page.tsx:421-480` 的 422 傳導，測試仍綠；且 page `NetICChart` 掛載 `:839-846` 未傳 `loading`，isolated prop test 未證實產品路徑。
5. **B5 CLOSED**：TODO §0:19 記錄具名檔、最小改動、日期、編排端正式核可與 build-enabler 理由；diff 僅刪兩處未用 callback 參數，符合授權範圍。
6. **R2-NEW-1（BLOCKING）**：`NetICChart.tsx:92` 對缺失 `gross_ic` 使用 `?? 0`，會把壞 schema 畫成真實 0 IC，違反 Data Truth/no fake metrics；既然 TS profile 宣稱必填，runtime 缺欄應走無資料/error，不得造值。

ASSUMPTIONS_VERIFIED: r7/r7b 有界近零規則；zero-vs-material 漏洞；B2 三命令離線；B3 union/profile；B4 production wiring 未被測試；B5 授權內容與實際 diff 一致。
TESTS_RUN: `reconcile_stamps_check.sh` SPEC+TODO→2 PASS；offline collect→20 collected；offline mutation→4 passed；offline new2→exit0/4 features；`npm --prefix frontend run test -- NetICChart`→1 file/6 tests passed。
FAILURES_SEEN: 首次 `/tmp` command 因 workdir 尚未建立而未啟動；建立 mirror 後三命令皆首跑通過。predicate 證 `zero_vs_material: PASS`。
SCOPE_CHANGES: reviewer 僅新增本檔；未改 root HANDOFF、source、baseline 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: reviewer 無；待修 B1 oracle 零值邊界、B3 TS schema、B4 test wiring、R2-NEW-1 假值 fallback。
CODE-REVIEW-R2: REJECT(4 BLOCKING)
