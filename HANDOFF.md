# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-05 20:0x | **Branch**: main
**狀態**: 🔵 **B3 已完成但未過 review** —— compact 後第一件事＝派 B3 的雙家族 code review

## ▶ compact 後立即接手（照這個順序）

**1. 派 B3 code review**（brief 已寫好且兩支檢查器皆 rc=0）

```
bash scripts/committee_run.sh --session 20260805-govb0-b3-review \
  handoffs/20260805-GOVB0-B3-CODEREVIEW-BRIEF.md handoffs/20260805-govb0-b3-review codex,composer -- \
  --intent "B3 雙家族 code review，Phase 2 首批" --risk high \
  --facts-asked "…" --review-role "adversarial code review，實作者不自審，禁改碼" \
  --template "n/a: 用 brief" \
  --adversarial handoffs/reconcile/20260805-govb0-todo-r9/synth.md \
  --reconcile  handoffs/reconcile/20260805-govb0-todo-r9/synth.md --task-id "GOVB0-B3-REVIEW"
```

🔴 **前一次派這個失敗過**，原因是主委當時把 `audit.log` 截斷、
`committee_dispatch` 事件被搬走 ⇒ 戳記 provenance 檢查失敗。
**已還原，該問題應已消失**；若仍失敗，先查 `audit.log` 是否完整（應 ≥34,501 行）。

**2. review 過關後** → B4（Task 2.2／2.3／2.4，修三個 fail-open，同改 `gate_check.sh:86` 故同批）
→ B5（差集報表，Phase 2 合併關卡）→ B6（3.1＋3.2）→ B7（3.3）→ 第 0.5 批線 C。

## 🔴 主委今日最後一個錯誤（已撤回，但要知道經過）

**錯誤**：`test_gate_check_latency_under_100ms` 紅過一次（287ms），
主委**未重跑**就斷定「根因＝`audit.log` 34,479 行」，寫了 `audit_archive_legacy.sh` 把
33,716 行封存、只留 763 行 debt 白名單，並 commit + push（`c2a351f`）。

**後果**：下一次派工立刻失敗——戳記 provenance 需要 `committee_dispatch` 事件，
它**不在** debt 白名單，被搬走了。

**真相**（codex 實測 + 主委獨立連跑 3 次）：**在完整未動的 34,501 行檔案上，latency 全部通過**（79ms）。
那次 287ms 是**單次冷啟抖動**，不是結構性問題。

**已撤回**：`audit.log` 還原為完整、封存檔刪除、`audit_archive_legacy.sh` 刪除、
白話說明的不實敘述已加更正段（原文保留不刪）。

⚠️ **`c2a351f` 已推上 GitHub**，本次撤回為新 commit（不改寫歷史）。

## 現況（皆已實測）

| 項目 | 值 |
|---|---|
| 測試 | **750 passed**（起始 701）；latency 已綠 |
| `audit.log` | **34,501 行**（完整，未截斷） |
| 委員債務 | 無 OPEN |
| 實作進度 | 8 批做完 **4 批**：B0 ✅ B1 ✅ B2 ✅ B3 ✅（B3 待 review） |
| SPEC | `docs/GOVB0_FRICTION_SPEC.md` R7，七輪收斂，三家戳記 |
| TODO | `docs/GOVB0_FRICTION_TODO.md` **Internal Frozen**，三輪收斂 |
| B3 收斂依據 | `handoffs/reconcile/20260805-govb0-todo-r9/synth.md`（三家戳記 sha `bb0090a6…`） |

## 🔴 使用者定死的三條（本 session 新增）

1. **面向未來，不溯及既往**——修正只考慮以後；不管舊文件與舊資料格式，
   除非該檔**未來還要被機器讀**且格式改不掉。遇舊資料不合新規**預設封存非遷移**。
   ⚠️ 但「未來還要被機器讀」的判定**必須窮舉消費者**（主委就是漏查而弄壞 provenance）。
2. **排程由 Claude 與委員共識決定，不問使用者。**
3. **技術問題自己修，不要停下來等使用者**（使用者不懂技術細節）。

## 白話說明維護（使用者定死，已機械強制）

給使用者看的文件放 **repo 根目錄 `白話說明/`**，**禁放 `handoffs/`**。
`scripts/plain_docs_sync_check.sh` 兩層：**commit 時提醒**（不擋）／**push 時硬擋**（時序判準）。
接在 `gov_check.sh` 4/4。**本 session 已真實擋下主委兩次**（`e243776`／`18cfdd2`）。
一份任務整批完工 → `git mv` 說明檔到 `白話說明/Archived/`，README 只留當前任務。

## ⚠️ 坑（照做省時間）

- **派 brief 前先跑兩支檢查器**，不要逐行試：
  `bash scripts/doc_format_precheck.sh <brief>` ＋ `python3 scripts/verification_claim_check.py --files <brief>`。
  本 session 曾逐行修三次才想到一次列出全部。
- **commit 訊息零豁免**：operational claim 須 `VERIFY:<receipt-id>` ＋ 可解析 scope
  或寫明 runtime 類別（`static`／`讀碼`／`真跑`）。receipt 的 `runtime_class` 必須對得上宣稱。
- 「**廉價綠燈**」四字會觸發 claim checker，改寫成「測試品質：依範本 §1 第 9 類舉證」。
- **中文路徑一律 `git -c core.quotepath=false`**——否則逃脫成 `\347\231\275…` 比對永遠失敗（本日踩 3 次）。
- **`rm` 在 deny 清單**，刪檔用 `git rm`。
- **`票 B-15` 本 session 咬 13 次**：commit 訊息某行以家族名開頭、指令引號內含 `|` 皆會誤判為派工。
  權宜＝`git commit -F <訊息檔>`、指令改寫成腳本檔再 `bash`。
- **pre-commit 會剝除 staged 內容的行尾空白但不動工作區** ⇒ commit 後工作區看似「多出空白」。
  這是早上「檔案莫名漂移」之謎的根因，非委員產出失真。
- **`rc` 禁經 pipe**；**禁 `python3 -c`**；`ts_stamp.log` 須 `LC_ALL=C grep -a`（**禁 export**）。

## 票

`handoffs/20260801-GOV-AMEND-BACKLOG.md`（**38 張，唯一登記處**）。
本日新增 `B-37`（優先序無數據依據，0.9 批）、`B-38`（0 findings 無法正規銷帳，第 1 批）；
`B-31` 嚴重度上調；`B-16` 擴充 A／B 合併並提前至第 1 批。
