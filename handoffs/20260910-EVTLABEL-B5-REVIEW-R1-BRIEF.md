# EVTLABEL B5（Phase 3 第三批：Task 3.8／3.9 倖存者輸出與前端）code review R1

brief-kind: review
task-id: 20260910-EVTLABEL-B5-REVIEW-R1
findings-round: R1
標的 diff：`git diff a98b3a84..12c334f0 -- momentum api tests frontend`
規格：`docs/EVTLABEL_SPEC.md` Task 3.8／3.9（v4，三家已 RECONCILE-STAMP APPROVED）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1（十一類）；審查對象是**碼**。
findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。實作者（Claude）不自審。

## 使用者主目標（SPEC §A 逐字）
> 「我在外面標好正反例（標的＋t₀＋0/1 標籤）匯入，平台找出 t₀ 之前哪些特徵能把正反例分開，再把這些特徵餵 ML。」

本批是「**再把這些特徵餵 ML**」那一段的交接物與畫面。倖存者檔是交接介面，
錯了不會拋例外——只會讓下游拿到一份無從追溯或不該使用的檔案。

## 這批改了什麼

1. **Task 3.8（倖存者輸出）**
   - stage3 綁定成功時寫 `event_filter.label_binary = {import_id, n_pos, n_neg,
     label_origin_values}`；缺 `import_id` ⇒ `AlignmentViolationError`。
   - 新 kwarg `event_label_binary_meta` 貫穿 analyze／三個 fallback 呼叫點／stage3；
     掃描格恆傳 None。service 由 `consumed_event_ids` 取 `label_origin_values`。
   - `build_survivor_output` 已於 B3 讀 `ef.get("label_binary")`／`statistic_kind`。
   - 負對照失敗 ⇒ `_write_survivor_output` **不落檔**，回
     `{status:"unavailable", reason:"negative_control_failed", path:None, sha256:None}`。

2. **Task 3.9（前端）**
   - `EventBatchDisclosurePanel`：`ic-param-label-mode` 三選＋批內正反數；
     選 `imported_binary` 時掃描區不渲染。
   - `ICSummaryTable`：`isBinaryMode` 由第一列有無 `rank_biserial` 判；
     binary 欄插在報酬版**之前**；表頭與 tooltip 單點自 `icLabelRule`。
   - 新 `LabelModeBanner`（`label-mode-banner`）三態 info／warn／danger。
   - `ICFeatureInfo` 加九個 optional binary 欄位。

3. **順帶修正**：後端欄名 `n_pos`／`n_neg` → `n_pos_selection`／`n_neg_selection`
   （前端 vitest 對證契約時抓到）；`n_used_binary` 補登進契約。

## 🔴 請優先攻的七點

1. **`label_origin_values` 的取法**：我用 `rec.get("label_origin", rec.get("label"))`
   ——若 records 沒有 `label_origin` 欄，就會退成 `label` 本身（0/1），
   那這個欄位等於沒有揭露任何額外資訊。請查真實 records 有沒有 `label_origin`；
   若沒有，這個欄位是不是應該直接省略而非填一份重複資料？
2. **`import_id` 之 fail-closed 會不會擋到合法路徑**：`request.event_import_id` 為空字串時
   我送 `""`，stage3 會 raise。有沒有合法的 binary run 是沒有 import_id 的？
3. **`_write_survivor_output` 之 suppressed 早退位置**：我把它放在 `case_id` 解析**之後**、
   `symbol/timeframe` 檢查**之前**。若 symbol 缺失同時負對照失敗，回的是 suppressed
   而不是 identity_missing——哪一個才是正確的優先序？
4. **與 SPEC 字面之偏離**：SPEC 寫 `status="suppressed"`，我用 `unavailable` ＋ reason
   （因為 `capability_status` 是封閉枚舉且不含 suppressed）。這個取捨可接受嗎？
   還是應該擴充枚舉？前端以 reason 判紅色 banner，是否足夠？
5. **`isBinaryMode` 由資料判**：第一列有無 `rank_biserial`。若後端某天對「不可用」的欄
   不寫該鍵，第一列剛好是不可用的特徵時整張表就會退回報酬版版面。這是真的風險嗎？
6. **前端 banner 之優先序**：negative_control_failed > insufficient_blocks > imported_binary >
   auto-degraded。若同時 degraded 又 suppressed，使用者只看得到紅色那條——夠嗎？
7. **既有紅**：`tests/momentum/Analysis` 之 20 條既有紅已具名於 `HANDOFF.md`。
   請確認本批未讓其中任何一條變嚴重。

## ⚠️ 前置說明
- **禁改碼、禁改文件**。不得跑 `pytest tests/governance`（小時級）。
- 既有紅基準見 `HANDOFF.md`「既有紅盤點」節。

## 本 brief 之前提（逐條標）

fact-verified: 前端 `npm run build` rc=0；`npx tsc --noEmit` 無新錯；vitest **707 passed（91 檔）**。
fact-verified: 後端六檔 **131 passed**；`--phase 3b` 8/8 RED、UNCOVERED=0；`gate 3b` rc=0。
fact-verified: G-6 survivor golden 未漂移；decoupling 對 baseline rc=0。
fact-verified: 欄名錯誤是**前端 vitest 對證契約時抓到的**（我原寫 `n_pos`／`n_neg`）。
fact-verified: `oosDowngradeDocs.test.ts` 之假紅來自其正規式掃到我的**註解**，已改寫措辭。

assumed: records 帶有 `label_origin` 欄
← 否證觀測：真實批次之 records 無該欄 ⇒ `label_origin_values` 退成 0/1 之重複。
／我跑了：**沒查**。只讀了 `event_import_contract.json` 之欄位清單印象。請正面打（必答 1）。

assumed: 合法 binary run 必有非空 `import_id`
← 否證觀測：某條路徑以 `event_timestamps` 走 binary（無 import_id）⇒ 被我的 raise 擋掉。
／我跑了：讀碼確認 Task 3.2 之不變式要求非 auto 必帶 import_id，但**沒查** auto 解析成
  binary 時是否也保證有 import_id。請正面打（必答 2）。

assumed: 第一列必定帶 `rank_biserial`（`isBinaryMode` 之判準）
← 否證觀測：`binary_status != ok` 之欄不寫該鍵，且它排在第一列。
／我跑了：讀碼確認 `_merge_binary_statistics` 對每一列都寫（不分 status），
  但**沒有**寫一條測試釘住「不可用的欄也要有該鍵」。

## 🔴 我沒查的
| claim | observable_if_false | reason_code |
|---|---|---|
| stage6b 之 `role="diagnostic"` 標記 | 使用者把報酬版邊際 IC 當成 binary 結論 | blocked-by（B4 review 已具名殘留，本批仍未做） |
| 端到端（真實 kline）跑一次 binary 全流程 | 某處接不上而單元測試皆過 | needs-research（Task 3.10 之範圍，下一批） |
| 倖存者檔真的餵得進 ML consumer | 檔案產出但下游讀不了 | needs-research（Task 3.11 之範圍，下一批） |
| 前端 e2e（真的點下去跑一次） | 元件各自綠但頁面沒接上 | cost（本專案無 e2e 基礎設施） |

## 必答（成對）
1a. records 有沒有 `label_origin` 欄？ 1b. 若沒有，該欄位該省略還是改取別的來源。
2a. 合法 binary run 是否必有非空 import_id？ 2b. 若否，fail-closed 該放在哪一層。
3a. suppressed 早退與 identity_missing 之優先序何者正確？ 3b. 你的建議。
4a. `unavailable` ＋ reason 取代 `suppressed` 可接受嗎？ 4b. 若否，最小修法。
5a. `isBinaryMode` 由第一列判是否為真風險？ 5b. 更穩的判準。
6a. banner 只顯示最嚴重那條是否足夠？ 6b. 若否，建議的呈現方式。
7. 有無 ≥10× 不必要複雜？本批可否進最後一批（Task 3.10／3.11）？

## 停輪條件
① 必答 1a–7 皆有 verdict；② 必答 1a／2a 有實跑或讀真實資料之證據；
③ P0／P1 皆指出修訂位置與最小修法。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
