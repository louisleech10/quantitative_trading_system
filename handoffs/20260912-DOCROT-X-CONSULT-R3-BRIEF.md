# DOCROT consult R3——由三家寫出可驗收的 TODO，主委只照做

brief-kind: consult

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R3-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 是無戳記診斷／輸入檔，非 gating 檔；勿 STAMP-BLOCK。
- 本輪是 **consult**：要的是**你們寫出的 TODO 與判準**，不是對主委草案的評語。

## 使用者的目標（逐字，本輪一切以此為準）
「跟委員會討論並解決文檔問題，確切了解文檔那麼多輪的根因並解決，讓各文檔的討論是聚焦在真的程式碼和架構上，而不是文字敘述混亂和誤解，減少文檔寫作輪數，減少不必要的摩擦上讓整個流程的品質和效率提升。」

## 🔴 本輪的硬約束（使用者逐字：「很怕你們會無限窮舉去解不可能的事情，浪費超多時間但沒有結果」）
- **只解根因**（R1 之 D1／D2 ＋ review-r1 抓實的第三根因「決議→實作無可核對 TODO」）。D3／D4／D5 只准回答「做或不做、為什麼」，不准展開設計。
- **每條 TODO 必須通過三問**：①它擋的是哪一個根因？②不做會再燒幾輪（引 R1–R12 數據）？③做完怎麼機械量到？三問答不出的條目**不得列入**。
- **禁止**：新 epic、新腳本檔、任何需要「語意判斷」的閘、任何要先建全庫 registry 才能動的方案。可改既有腳本與範本。
- **上限**：TODO 總數 ≤8 條；三家對同一條目意見不同時，取**最窄**能過三問者，不取聯集。
- **停止條件**：三家對「根因是否被 TODO 涵蓋」一致答是，即收；不追求 finding 歸零。

## 已定案、本輪不重議的事實
- R1（`handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md`）：主因 D1＝一個決定手寫進多個無索引落點；次因 D2＝修訂考古寫進活義務；另 D3 三閘 rc=0 不代表無語意互斥、D4 停輪判準應機械化、D5 狀態複寫跨檔、D6 收斂檔不屬病灶。
- R2（`.../20260912-docrot-x-consult-r2/synth.md`）：主委第二版折衷被三家全 P0 否決；執行優先序五項；程序修正「凡主委產出非任一家原文之折衷，自動開一輪 consult」。
- review-r1（`.../20260912-docrot-x-review-r1/synth.md`，codex＋composer＋grok 三家齊，22 條歸十群、歸戶 22/22）：主委自實作五項**未開 consult**即 commit（兩家 P0）；以「三家共同結論」為 commit 標題背書未審實作（三家）；E3 只做一半（completeness 未拒收 HISTORY 區 anchor，grok P0）；`dupes()` 在 `HISTORY-BEGIN` break 會漏掃其後活文（三家，有構造反例）；warn-only 對主委無效，最小擋門＝`gov_check` 段 1b 對 dupes 命中 fail-closed（三家）；F1 只做 D-002 一份、成效判準不可觀測（三家）。

## 主委自創五項 vs 三家原文（review-r1 G1；請逐項裁定：採納／改寫／撤回）
| # | 主委做了什麼 | 三家原文是什麼 |
|---|---|---|
| 1 | `brief_conformance_check.sh`：拒派含 `new_brief.sh` 骨架佔位字面之 brief | E3＝「審查輸入只餵當前段落＋本輪 diff」；E8 Phase A（composer）＝「brief 強制 `review_scope` 與 diff；`completeness_check` 拒收 anchor 落在 `HISTORY-BEGIN/END` 之 finding」——後半**未做** |
| 2 | `spec_count_audit.py --dupes`：同一計數字面出現在多行即警告（三種 regex） | 窄 F2＝「只數『共 N 條』形態」 |
| 3 | `dupes()` 在第一個 `HISTORY-BEGIN` 處 `break` | 無任何一家提過；grok 已證 break 會漏掃其後活文 |
| 4 | 產出端警告層併入既有 `spec_xref_hook.sh`，不新增 `settings.json` 條目 | E2＝「掛載三層，沿用既有樣板」；併入哪一支是主委成本拍板 |
| 5 | F1 活文收縮只做 `docs/SPLITUNIFY_SPEC.D-002.md` 即宣告收斂點 | 三家未限定範圍 |

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`handoffs/reconcile/20260912-docrot-x-review-r1/synth.md:1-30`（十群處置表）；上列五項對應之碼段——`scripts/brief_conformance_check.sh`（PLACEHOLDERS 段）、`scripts/spec_count_audit.py`（`_RE_TOTAL_ITEMS`／`dupes()`）、`scripts/spec_xref_hook.sh`（③ 段）、`scripts/gov_check.sh`（段 1b 內 `--dupes` 呼叫）
- **本輪 diff**：`git diff 44bbd8d3..HEAD -- scripts/brief_conformance_check.sh scripts/spec_count_audit.py scripts/spec_xref_hook.sh scripts/gov_check.sh scripts/new_brief.sh templates/ tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_f2_total_items_count.py`
- 🔴 **不在範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 之 `HISTORY-BEGIN`～`HISTORY-END`；finding anchor 落在歷史段者不受理。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: review-r1 十群全為 codex＋composer＋grok 原文之處置，主委未加入任何新機制 → 歸戶檢查 22/22、completeness PASS、`debt_clear` rc=0（`handoffs/reconcile/20260912-docrot-x-review-r1/`）。
fact-verified: 目前 D1 之寫入時硬擋覆蓋率為 0%——兩處 `--dupes` 皆 `|| true` 不改 rc → `scripts/gov_check.sh` 段 1b、`scripts/spec_xref_hook.sh` ③ 段實讀。
fact-verified: `docs/` 200 個 `.md` 中 132 個命中 `spec_xref_hook` 觸發集合，68 個不命中 → `ls docs/ | grep -cE 'SPEC|TODO|PLAN|RECON'`。
fact-verified: `docs/` 下**不存在**任何 DOCROT 的 SPEC 或 TODO；主委從決議直接進碼，未宣告任務大小 → `ls docs/ | grep -i docrot` 為空。
assumed: 「文檔多輪」的根因就是 R1 的 D1／D2，把 D1／D2 機械化後輪數就會降——主委沒有任何一張票的前後對照數據。請直接攻這條。
assumed: 「討論聚焦在碼與架構」可以靠限制審查輸入（只餵 current block＋diff）達成——但委員仍可能在 diff 內爭字面。請直接攻這條：什麼形態的 brief／synth 結構才能讓 finding 必須指向碼或架構？
assumed: 三家 consult 產出的 TODO 可以不經 SPEC 直接實作（因為改動全在 `scripts/`／`templates/`，屬治理工具）。若你們認為仍須 SPEC，請明說並給最小形態。

## 必答（逐條 verdict；答案要能直接變成 TODO 條目）
1. 五項逐項裁定：採納／改寫（給改寫後的逐字規格）／撤回。撤回者主委即 revert。
2. **寫出 TODO**：以 `Task N.N` 形態列出「要做的全部」，每條含：改哪個既有檔、驗收指令與預期 rc、mutation（改壞什麼會紅）。限制：不新增腳本檔、不開新 epic；可改既有腳本與範本。至少涵蓋：E8 Phase A 之 completeness HISTORY-anchor 拒收；`gov_check` 段 1b 對 dupes fail-closed；`dupes()` 區間 skip；`verification_claim_check` 對「三家共同結論」類背書語之 audit 佐證。
3. **成效判準寫成可機械計算的一句**：分子、分母、資料來源（哪個檔、哪個欄位）、基線值（用 D-002 R1–R12 的十二份 synth 算出）、及格線。
4. 直接回答使用者的問題：現行 brief／synth／SPEC 的哪些**結構**讓委員的 finding 落在字面而非碼與架構？要改哪一個範本的哪一段？給逐字改法。
5. F1 範圍：下一張中大票是 SPLITUNIFY b9 實作（`D-002`）還是別的？若不是 D-002，F1 要不要先擴到該票的 SPEC？
6. 可以進實作嗎，還是有 BLOCKING 必須先修？

## 產出
canonical 四欄 findings ＋ **必答 2 的 TODO 表** ＋ **Verdict**。**禁改碼**（只產 consult 檔）。收尾清 /tmp workdir（保留 claude-501）。
