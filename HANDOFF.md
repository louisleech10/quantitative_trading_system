# HANDOFF — 當前任務狀態

**更新：2026-09-04｜狀態：`G3-D2` 實作中——B-D0 已 DONE；B-D1 之實作與 R2 三家審碼閉合修正已 push（`5adbe126`／`7eae878f`）。下一件＝**B-D1 之 R3 閉合輪**。唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`（收據與驗收數字見 §5、地雷 §3、裁定總表 §4）。**

## 🔴 新 session 第一件事＝派 B-D1 R3 閉合輪

停輪條件⑤要求**原提出方**重跑同一反例確認 CLOSED，**不得由主委自行宣告修好**。

```
session: 20260904-gap3d2-b1-review-r3    task-id: 20260904-GAP3D2-B1-REVIEW-R3
標的: 5adbe126（閉合修正）＋7eae878f（文件）；基底 cb22f725
```

R3 brief 須逐條列「原 finding → 修法 → 對應新測試 → 請原提出方重跑同一反例」，共六條：

| 原 finding | 修法 | 複核選擇器 |
|---|---|---|
| `CODEX-R2-P1-01`＋`COMPOSER-R2-P1-01`＋`GROK-R2-P2-01`（三家全員）：`label_origin` 混值／部分宣告可落檔 | 加入 `_ALWAYS_HOMOGENEOUS_DIMENSIONS`（無條件組，非 Task 1.8 旗標組） | `test_import_contract.py -k r2_closure` |
| `CODEX-R2-P1-02`：混 `decision_offset_bars` 取首列套全批 | route 422 `mixed_decision_offset_bars` | `tests/api -k ic_event_label_defaults` |
| `CODEX-R2-P1-03`：D1.7 依深度預設不可達（hook 明送常數） | 未設定時整個鍵省略；「當根」h disabled | 同上＋`icEventBatchDisclosure.test.tsx` |
| `CODEX-R2-P2-01`：`--check` 不驗 selector drift | `--check` 逐檔對證 `resolved_cases` | `scripts/gap3_label_golden.py --check` |
| `COMPOSER-R2-P2-01`＋`GROK-R2-P2-02`：裁定 1 在旗標 False 時落空 | `_batch_scenario_mixed = enforce_batch_homogeneity and mixed` | `-k r2_closure_new_rules_apply_when_homogeneity_not_enforced` |
| `GROK-R2-P2-03`：裁定 5「UI 比矩陣嚴」無測試釘住 | 加負例＋釘住 preset 恰三個 | `icEventBatchDisclosure.test.tsx` 裁定 5 段 |

**R2 已完整收斂**（2026-09-04 補做，勿重做）：`handoffs/reconcile/20260904-gap3d2-b1-review-r2/synth.md`
六群集＋三條具名殘留（`B1-PRESET-1`／`B1-GOLDEN-2`／`B1-VERIFY-1`）；
`completeness_check --lock` rc=0（11 ID 全數）、`reconcile_cluster_attribution_check` rc=0、
`debt_clear` rc=0（round `266ba2e6` 已 CLEARED）⇒ **`gate.sh dispatch` 可正常發 token**（已實測 rc=0）。

🔴 **本 session 差點漏掉的一步**：我修完 findings 就直接 commit，**跳過 §2 步驟 6 的收斂節點**
（`reconcile_build` → attribution → completeness → `debt_clear`）。債 OPEN 會讓下一次派工被 gate 拒發，
而當時 HANDOFF 完全沒提。**判準：每輪 review 收件後，收斂節點與修 findings 是兩件事，都要做。**

委員 R2 產出（本機，gitignore）：`handoffs/20260904-gap3d2-b1-review-r2-{codex,composer,grok}.md`。
R2 brief 可作 R3 骨架：`handoffs/20260904-GAP3D2-B1-REVIEW-R2-BRIEF.md`。
R3 仍派**三家全員**（使用者裁定不可跳過）；R3 之停輪條件＝原提出方對六群集逐條回 CLOSED、且無新 P0／P1。

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | 實作中：B-D0 ✅、B-D1 待 R3 閉合；待做 B-D3→B-D4→B-D5 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN（可穿插） |

## 使用者裁定（本 session 新增）
- **三家委員不可跳過**（2026-09-04）：codex 若停滯，改用「輕量驗收版 brief」重派，**不得**拿兩家 quorum 收斂。
- **白話須有施工流程即時進度**：`白話說明/現在做到哪.md`（已建、已登記 `plain_docs_sync_check.sh`）；每完成一步即更新。

## 已知紅／不要誤判
- 🔴 **codex 於 B-D0 三度未交件之根因未定**（四假說皆已反證，見 `docs/GAP3D2_IMPL_HANDOFF.md` §3）。**但 B-D1 R2 它正常交件並抓到三條 P1**，勿當它不可用。
- 🔴 **mutation 腳本同日兩次沖掉未提交改動**。現行：`--check-clean` 開場擋、迴圈內 restore 只在套過 mutation 之後。**判準：清理動作不得早於前置檢查**；閉合輪修正**先 commit 再跑 mutation**。
- `tests/api` 其他選擇器有既有紅（`G3-R11`）；`test_ic_deep_analysis` 並行 ERROR、單跑綠；`tsc --noEmit` 8 行既有債。
- `cd frontend` 會讓 shell 停在該目錄 ⇒ 之後 `venv/bin/python` rc=127；動作前先確認 `pwd`。
- 具名殘留：`B0-REVIEW-1/2`、`B0-ATTRIB-1/2`、`B0-DOC-1`、`B0-GOLDEN-1`、`B0-MUT-1`；`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
