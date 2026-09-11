# SPLITUNIFY 補裁決輪（三家把 B7-REVIEW-R1 之結論改寫成機械裁決塊）

brief-kind: closure
task-id: 20260911-SPLITUNIFY-B7-REVIEW-R2
findings-round: R2

🔴 **這是補裁決（closure），不是重新審查、不是實作。禁改碼、禁動 tracked 檔；禁跑 `tests/governance` 全套；禁在本 repo commit／push。**
照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 全文照做；末段三行機械塊只准值集（`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`）；`CLOSED:` 只列本家 ID；**`STATUS: DONE` 逐字**。

## 為什麼有這一輪
VERDICTGATE（治理票 B-62）上線後，開任何新批前閘會讀前批三家的**機械裁決**（audit `committee_output.verdict`）。SPLITUNIFY 之 `20260911-SPLITUNIFY-B7-REVIEW-R1`（實為 B4 閉合確認輪）三家皆以散文寫結論（「已全數閉合」／`## Verdict`），**audit 無機械裁決** ⇒ `verdictgate_check 20260911-SPLITUNIFY 8` 擋、指名補裁決輪（TODO §E E-4；使用者 2026-08-05「不溯及既往」⇒ 只補這一輪，不回溯 B1–B6）。

## 你要做的事
1. 讀你自己的 `handoffs/20260911-splitunify-b7-review-r1-<你的家族>.md`，把當時的結論改寫成機械裁決塊：閉合輪結論「已全數閉合」⇒ `VERDICT: proceed`＋`CLOSED:` 列你在 SPLITUNIFY 各輪提出且你已確認閉合之 ID（只列本家）；若當時仍有你認為未閉合之 P0/P1 ⇒ `VERDICT: blocked`＋`BLOCKED-BY:` 列之。
2. **不重審碼**；只把已有結論機械化。若你要改結論，須附碼證並說明與 R1 差異。
3. composer 之 `COMPOSER-R1-P2-02`（P2「獨立檢查 residual」）：P2 不進 BLOCKED-BY（契約只列 P0/P1）；請在內文重述其處置建議即可。

## 交件形態
至少一個 canonical heading（零新 findings 用 sentinel `## <FAMILY>-R2-P3-00`）；末段三行機械塊；`STATUS: DONE`。

## 前提
fact-verified: `bash scripts/verdictgate_check.sh 20260911-SPLITUNIFY 8 20260911-SPLITUNIFY-B7-REVIEW` → rc=1，三家皆「無機械裁決」（主委 2026-09-12）。
fact-verified: `debt_ledger --has-open` rc=0（派工後預期值: rc=1——本輪 OPEN，非 2）。
assumed: 三家 R1 結論皆為「已全數閉合」（主委讀檔：composer／grok 明寫；codex 檔內文亦為閉合）⇒ 否證觀測：任一家 `VERDICT: blocked`。／我跑了：**讀了三檔**。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
