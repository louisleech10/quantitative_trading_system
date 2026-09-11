# SPLITUNIFY D-001 閉合確認 R7（原提出方重驗 R6 之五條）

brief-kind: closure
task-id: 20260911-SPLITUNIFY-X-REVIEW-R7
findings-round: R7

🔴 **這是閉合確認（closure），不是實作、不是重新全審。禁改碼、禁動 tracked 檔；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（`gate_check` 會誤判為派工）。

🔴 **交件格式（本票已四度因此回頭正規化，請逐字遵守）**：
- findings 一律 `## <FAMILY>-R7-P<0-3>-<NN>` **二級**標題
- 末段三行機械塊：`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`。**無內容就留空**，不得寫 `none`
- 完成訊號**逐字** `STATUS: DONE`

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；零新 findings 用 sentinel `## <FAMILY>-R7-P3-00`。

## 你要重驗的（只看自己 R6 提的）
主委修法已落 `docs/SPLITUNIFY_SPEC.D-001.md`（R6 後修訂版）：

| R6 ID | 修法落點 |
|---|---|
| `CODEX-R6-P1-01`（producer 寫全框位置 vs C2 要求 symbol-local 序號） | **D-001-C2 第 4 點**：不改 `row_index` 既有語意（它被 IC 主線全框驗證與既有 golden 依賴），改為明定**唯一、可驗證的無損轉換層**——只在指紋計算與比對兩處、由同一支具名 helper 實作；映不到即 fail-closed；附往返測試與交錯多標的 fixture。另新登記殘留 `SU-RESID-4`（是否該把 `row_index` 本身改為 symbol-local）。Task 8.2 驗證段加三條轉換層 ASSERT |
| `CODEX-R6-P1-02`（凍結腳本與接線測試未入 scope） | **Task 8.1／8.2 檔案清單**補 `scripts/freeze_splitunify_golden.py`、`tests/momentum/event_samples/test_splitunify_wiring.py`、`tests/momentum/Analysis/test_splitunify_golden.py`；驗證命令加入三者；**C2 第 7 點**改為獨立 oracle 須與 **producer 實際寫入 plan 的指紋欄**逐值相等 |
| `GROK-R6-P1-01`（指紋列容器形狀未釘死） | **D-001-C2 第 1 點**：釘死 `list[list]`、元素順序固定、與凍結腳本逐字同形；欄位名稱僅文件稱呼不進 JSON；禁 `list[dict]`；同步要求改凍結腳本註解之舊欄名 |
| `GROK-R6-P2-01`（C1.2 殘留「指紋不足以分辨」與 payload 含 symbol 互斥） | **D-001-C1 第 2 點末段**改寫為「指紋已含 symbol、可區分列所屬標的；三角相等仍為獨立必查，兩者目的不同」 |
| `GROK-R6-P2-02`（C-4 整節標覆寫但只換簽名） | **觸及面**改標「覆寫其**簽名段**」＋新增限定句：BASE C-4 其餘段落（keyed 輸入契約、禁 positional zip、兩段式判定、`build_event_keys` 具名）**原文仍有效，未重述 ≠ 已廢止** |

## 🔴 必答
1. **你 R6 的每一條**：逐條回「已閉合／未閉合」＋重驗碼證（對讀修訂後之 D-001）。
2. **新引入面之反查**：本輪修法新增了「無損轉換層」與「新殘留 `SU-RESID-4`」。①轉換層是否可能成為第二份 row 語意的來源（即實作在轉換層外另寫一份）？②把 `row_index` 語意之遷移登記為殘留而非本批做掉，是否會讓 b8 上線後留下「兩套 row 語意並存」的長期債？給立場與碼證。
3. **可否進入實作**（`VERDICT: proceed`）？

## 停輪條件
①必答 1–3 皆有立場；②必答 1 逐條附重驗碼證；③**禁以「三家零 finding」當停輪**；④若仍 blocked，須說明「不改會在 b8 實作或收案時具體怎麼失敗」。

## 前提
fact-verified: R6 六條全數採納並已落 D-001 → 讀 `handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md` 群集表（主委 2026-09-12）
fact-verified: 主委對三條 P1 之關鍵碼證逐條抽驗屬實（producer 以全框位置寫入 `row_index`、凍結腳本四處舊式呼叫、接線測試建無指紋欄之 plan、清單形與字典形 sha256 不同） → 各自 grep／實跑
fact-verified: 修訂後 D-001 之歸戶閘與交叉引用皆通過 → `reconcile_cluster_attribution_check.sh` rc=0、`spec_xref_check.sh --synth` 對 R5／R6 兩份皆 rc=0、`doc_format_precheck.sh` rc=0
fact-verified: R6 輪債已清 → `bash scripts/debt_ledger.sh --has-open` rc=0（派工後預期值: rc=1——本輪 OPEN，非 2）
assumed: 無損轉換層足以橋接兩套 row 語意而不引入第二份判定 ⇒ 否證觀測：必答 2① 指出實作必須在轉換層外另寫一份 row 對應才能成立之情形。／我跑了：**沒跑**（尚未實作）
assumed: `SU-RESID-4` 登記為殘留不影響 b8 自洽 ⇒ 否證觀測：必答 2② 指出 b8 上線後兩套語意並存會造成的具體錯分路徑。／我跑了：**沒跑**

## ⚠️ 前置
禁改碼；只讀；收尾清 /tmp workdir（保留 `claude-501`）。
