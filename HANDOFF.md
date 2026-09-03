# HANDOFF — 當前任務狀態

**更新：2026-09-04｜狀態：`G3-D2` SPEC 延伸 D-001 與 TODO 延伸 D-006 **v2 三家戳記齊全＝FROZEN**（v1 戳記 9/3；v2＝使用者四裁定修訂，review r1→r2 收斂，戳記 9/4）。🔴 依使用者裁定**已停下**：白話說明 `白話說明/G3-D2灰色項目說明.md`（§二之二 四裁定、§三 v2 逐段範例、§四 甲乙丙），**實作未開工，等使用者放行**。**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **規格與清單 FROZEN（v2）**：D-001（五 phase：D0 取價修法→D1 預測型→D3 two_stage→D4 其餘＋k/h 掃描→D5 隨機對照組；D2 退役）；D-006（B-D0→B-D1→B-D3→B-D4→B-D5 串行）。戳記：`handoffs/reconcile/20260903-gap3d2v2-x-review-r2/synth.md`（sha `5f322471…`）＋鏡像於兩檔 `## 戳記`。實作未開工。 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN |

## 待使用者
放行實作（從 B-D0 開始）；或否決白話檔 §四 甲乙丙任一題。

## 下一步（放行後）
1. B-D0：Task D4.1（`entry_price_refs` 側載＋進 hash；open 取價；跳空 golden）→ 三家 code review → commit＋push。
2. B-D1：D1.1–D1.7 → review；B-D3；B-D4（D4.2、D4.3 含 benchmark 子步）；B-D5。每批 review CLOSED 後才進下一批。
3. 派工規約：session `<YYYYMMDD>-<epic>-<b<n>|x>-<kind>-r<N>`、task-id＝大寫；派前 `gate.sh dispatch` mint；三家齊交之 round 以 `debt_clear.sh --round-id … --session … --lock` 銷帳；外部故障（composer 模型不可用／ETIMEDOUT、codex 404、grok 500）⇒ `--abandon --kind collection-failed` → mint → `ROUND_ID=<id> cx_run.sh <family> …`。
4. commit 含 scope 外路徑須 `Governance-Scope:` trailer；`handoffs/` gitignore；白話新檔須登記 `scripts/plain_docs_sync_check.sh`；Bash 指令開頭不得出現 `codex|cursor-agent|grok|agy`（債開著時會被當 dispatch 擋）。

## 已知紅／不要誤判
- 多個 ABANDONED rounds（三家 CLI 外部故障）；產物齊全、completeness PASS。
- `reconcile_cluster_attribution_check.sh` 對前輪 ID 誤報「未被引用」＝假警。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`；9/1 之 9 批事件檔為測試檔（使用者確認），不保留。
