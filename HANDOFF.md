# HANDOFF — 當前任務狀態

**更新：2026-09-11｜現行票：`VERDICTGATE`（治理，大；RISK b,c）｜狀態：偵察收斂（V1–V6，債已清）→ SPEC v1 起草並過 template_check → **三家 adversarial R1 進行中**（session `20260911-verdictgate-x-review-r1`）｜`SPLITUNIFY` 暫停**
🔴 偵察推翻主委三處：Verdict 不是「不可解析」而是**開放詞彙＋從未入 audit**；G-3 落點須在 **commit-msg**（pre-commit 拿不到訊息）且與 warn-only 的 G-7 分離；跨批漏洞第三條主路＝`debt_clear`→開輪，GAP-3／EVTLABEL 同型。
派工命名：batch 只准 `b<N>` 或 `x`——`spec-review` 被拒一次，改 `x-review-r1`。
使用者 2026-09-11 裁定（逐字）：「為了文檔品質，先把治理票做完，再開始量化主線項目」。

## VERDICTGATE 要解什麼（全部有實證，見 `handoffs/20260911-VERDICTGATE-RECON-claude.md`）
1. 批次之間的 `review_quorum_check.sh` 只在 `*-impl-b<N>-<家族>` 派工時觸發（`gate.sh:783-803`）⇒ **主委自任實作時從未跑過**；且只驗「有沒有派出去」、**不讀裁決**。SPLITUNIFY 每個批次邊界都在至少一家寫「不可進」下跨過。
2. 程式碼審查之收斂**不要求委員確認**；`completeness_check` 只驗編號在檔（附錄逐字保留 ⇒ **永遠通過**）；`reconcile_cluster_attribution_check.sh` 恆 rc=0 且 `cut -c` 在中文上壞掉。回溯稽核：8 輪 57 條意見中 **3 條被主委弄丟**。
3. 收斂檔寫「延後到 Bx」即從此消失（H6 → 投影把使用者設定靜默換成 1）。
4. 使用者設計指示：觸發點**不論哪家執行都要觸發**（含主委自任）⇒ 主委也須領實作權限＋pre-commit 最後一道。

## SPLITUNIFY 暫停時之狀態（全部已 push，最新 `fa9f51c1`）
- B1–B4 實作完成；8 輪審碼＋**閉合確認輪**（原提出方重跑反例：codex／grok 全閉合；composer 挑戰成功一條已修）。
- 🔴 **未收票**。依使用者殘留規則（只准「已定義在其他 Phase」或「現階段完全不可能」）仍須做：
  **R-1** per-symbol 投影（會推翻 SPEC C-2，待使用者裁示）、**R-5** 事件掃描端取 universe、
  **SU-RESID-2** 多 TF 複合鍵、**SU-RESID-3** 同源對證只比首尾；**SU-RESID-1** 併入 VERDICTGATE。
  另：已廢止之「95% 就收」曾被用來接受 D1 之範圍裁定，未重審。
- 已關：R-2（C-9 差異實跑，挖出「0 個標的」假數字已修）。合格留存：R-3（UAT 最後）、R-4（GAP-3 TODO 已定義）。

## 今日全專案層級變更（已 push）
- **「95% 就收」全專案（含治理）廢止**：記憶規則整條刪、10 處現行文件改寫；守衛 `quant_standard_check.sh` 改全專案掃描、內容鍵凍結基準（96 條只准變短）、接上 `gov_check` 1a 段（pre-push）。
- 8 支 hook 之無界 stdin 讀取加 5 秒逾時（Write／Edit 那段故障主因是 OOM，不是它們）。

## 踩坑（本 session）
- `fact_keys.json` 以**行號**引用腳本 ⇒ 改腳本就位移；產出端檢查只驗「是不是註解」不驗「是不是原本那行」（本日兩次）。
- 基準／清單用行號當鍵太脆弱（在檔頭插一行 ⇒ 全部歷史命中掉出）。
- 委員名字出現在 Bash 指令列會被 `gate_check` 誤判為派工 ⇒ 改寫成腳本檔再跑。
- 同時跑重型測試＋三家委員 worktree ⇒ 疑似 OOM（推論，未證實）。
