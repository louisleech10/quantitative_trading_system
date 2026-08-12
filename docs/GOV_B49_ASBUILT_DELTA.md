# B-49 as-built 差異 — 實作與 SPEC r6／TODO 的逐條落差

> 對應 SPEC：`docs/GOV_B49_PATH_GRANT_SPEC.md`（r6）｜TODO：`docs/GOV_B49_PATH_GRANT_TODO.md`
> 日期：2026-08-12｜實作端：主委自任（`implementer=claude`）
> 🔴 **本檔是延伸檔，不就地改 SPEC／TODO**（使用者 2026-08-01 定死：修訂凍結文件走延伸檔）。
> 用途：讓兩家非實作者 code review 一眼看出「哪裡沒照原文做、為什麼」。

## §0 為何會有落差

SPEC r6 定案於**使用者解除凍結授權之前**，當時 `Task 0.2` 判定為 BLOCKED。
授權（2026-08-12）改變了前提，`Task 0.2` 由「不可實作」變成「可實作且應一次做完」，
下游的授權集合大小、守衛掛載點、mutation 目標隨之改變。

**落差一律往「更嚴」或「更完整」的方向**；任一條若被 review 判為放寬，即為 `[MUST-FIX]`。

## §1 落差逐條

| # | SPEC／TODO 原文 | 實作 | 理由 | 方向 |
|---|---|---|---|---|
| D-1 | `_B49_GRANT_IDENTITY` ＝ **三條**路徑（`_B45_HARNESS` 之三） | **四條**：三 harness ＋ `docs/GOVB1_INPUT_QUALITY_TODO.md` | 解凍需就地改該檔宣告集，而它命中 B5 禁改前綴 `docs/GOVB1_` ⇒ 需同一身分綁定承接 | 擴張（受同一 byte 級綁定約束） |
| D-2 | Task 1.1 邊界「常數含 `_B45_HARNESS` 以外路徑 ⇒ 紅」 | 改為「恰四條：三條屬 `_B45_HARNESS`、一條為授權規格檔」 | D-1 之必然結果 | 中性（仍為封閉字面集合） |
| D-3 | manifest allow 新增 **四條** | 新增 **13 條**（12 幽靈路徑 ＋ 閉合證據新檔） | 使用者「不留卡點」授權；`govb1_ghostpath_check.sh` 11 條一次歸零，否則每動一檔就 G-7 紅一次 | 擴張（僅影響 G-7 宣告面，**不影響凍結**） |
| D-4 | `decl == 40`（或 41，待裁） | **49**（42 allow ＋ 6 meta ＋ 1 新檔） | D-3 之算術後果；`GROK-R1-P1-02` 已預告數字待實測 | 中性 |
| D-5 | Task 1.2 只改三道守衛之 `hit_harness` | `hit_harness` **與** 禁改前綴迴圈**兩處**都改 | `CODEX-CONSULT-R1-P0-01`：`_B5_FORBIDDEN_PREFIXES` 不含 harness，只改一處承接不到 | 完整化 |
| D-6 | TODO §0-3「`--name-only` 逐字保留」 | 逐字保留，**另加** `_rename_old_names()` 以 `--name-status -M -C` 補回舊名 | `CODEX-CONSULT-R1-P0-02`：`--name-only` 隱去 rename 舊名 ⇒ 改名即可洗出保護範圍；SPEC Task 3.1 ⑬ 本就要求擋住 | 收緊（純加法） |
| D-7 | Task 2.2「freeze active ＋ CLOSED ⇒ 紅」 | freeze active ＋ CLOSED ⇒ **呼叫 `_assert_b49_closure_evidence()` 後 return** | B-49 只解凍三檔，另兩檔設計上維持凍結 ⇒ 引信恆 active；沿用原判準則此票**永遠關不掉**（狀態機無可達終態） | 放寬（但以**實跑**證據把關） |
| D-8 | Task 2.3 之 2-① 變異＝「stamp path invalid implementer 分支」 | 改為「沙箱 `eligible` 抽成無 CLI 家族」 | 修法後**該分支已不存在**（那正是交付內容）⇒ 照原文變異會**恆綠**，成廢格 | 中性（改打真正承重處） |
| D-9 | Task 3.1 ＝ 17 格 | **19 格**（⑬ 拆成刪除／改名／偵測失敗三格） | rename 守衛為新增判定，需獨立承重證據；偵測失敗須證明 fail-closed 而非回空集合 | 擴張 |
| D-10 | Task 3.2 baseline 用 immutable pre-B49 SHA | `_PRE_B49_SHA = "835c3d35"`，並斷言該版本**不含** `_B49_GRANT_IDENTITY` | 防「基準漂成已含 grant 的版本」——自我檢查而非靠紀律 | 收緊 |

## §2 主委實作時被自己的機制擋下的三次（皆為正確行為，逐條列供覆核）

1. **授權後改一個位元組即被拒**：改 `test_stamp_taskid_inject.py` 後，B5 守衛立刻報
   「觸及未授權之 B-45 harness」——因 `ls-tree HEAD` 身分未同批更新。**grant 生效之證據。**
2. **`mut01` 抓到注入錨點不唯一**：`brief_rel = "handoffs/brief.md"` 在該檔多處出現，
   `replace(count=1)` 把死碼塞進**別的函式** ⇒ 1-a 沒抓到。修為「先取 V12 片段再注入」。
3. **`mut06` 用字串掃全檔會誤判**：`_role_pin` 的 docstring 逐字寫著「不得出現
   `("codex", "grok", "composer")` 這種字面三元組」——用散文測散文。改走 AST，只看程式碼常數。

## §3 具名殘留（**不在本批處理**，須 review 確認可接受）

1. `_G7_OOE_HARD_PROTECTED` 仍字面含 `docs/GOVB1_`，而該檔現在在 manifest allow 內。
   讀碼確認不矛盾（`_g7_covered` 先命中 ⇒ OOE 通道不被詢問），`COMPOSER-R1-P2-02` 覆核同意。
   **不同批處理**；若日後把該檔移出 allow，OOE 硬保護仍在，無保護真空。
2. **同批 rebind 機械上不可區分**（SPEC §C-11）：主委改授權檔並同批更新常數，
   與正常施工無法區分。本機制**只防意外與遺忘，不防具寫入權者蓄意**。
3. `_B45_HARNESS` 另兩檔（`test_cxrun_stamp_prompt.py`／`test_completeness_idlike_fp.py`）
   **維持凍結**，本批未授權、未修改。引信仍以它們為偵測對象。

4. **掏空偵測之靜態近似**（review r5 三家裁定，取較嚴之 (B) 版）：
   `_b49_selector_is_substantive` 的抽象域為 `{False, True, None}`——僅 `ast.Constant`
   之 `bool(value)` 與空 `List`／`Tuple`／`Set`／`Dict` 判 False，其餘一律 `None`（保守計入）。
   - **擋得住**：`if False:`／`if 0:`／`if []:`／`while False:`／`for _ in []:`、
     巢狀函式／類別／lambda 內之死碼、同名重複定義、selector 清單重複與契約失配。
   - **擋不住**：需常數折疊才能判定者（`if not True:`、`if 1 == 0:`、`range(0)`、布林短路），
     以及 `assert True` 這類語法可達但語意空洞者。**兩者皆已實跑確認**。
   - **為何停在這裡**：要覆蓋上述形式必走常數折疊擴張 ⇒ 列不完。依使用者 2026-08-07
     定死之規則（遇此類 judgment 改封閉機械閘，**禁再耗回合列舉**，只能降級具名殘留）
     與「95% 解法就收」，**停止列舉**並記入本節，**不作為 push 阻塞**。
   - **威脅模型**：只防**意外掏空與重構失手**，不防蓄意——與整套 B-49 機制同一邊界。
   - 保守方向已實測不誤殺：`if x: assert x` 判為有實質。

## §5 收斂軌跡（供日後判斷同型問題是否在收斂）

| 輪次 | finding 數 | 性質 |
|---|---|---|
| consult r1 | 2 P0 | 形狀裁定（`ALLOW-WITH-CONSTRAINT`）＋ rename 守衛缺口 |
| review r2 | 6 | 假格、判定缺口、關票路徑不可達 |
| review r3 | 1 | 掏空規則不封閉（兩條探針） |
| review r4 | 2 | 靜態死碼分支、清單↔契約漂移 |
| review r5 | **0** | 三家 APPROVED，終止 |

🔴 **主委自跑反向驗證額外抓到三個委員未提出的殘留**（`mut11b` 假格／隔離副本缺
`git init` 致關票仍不可達／掏空偵測缺席）。**三個都不是靠測試綠發現的**——
測試綠只證明「現在通過」，反向驗證才證明「拿掉判定會不會紅」。

## §4 驗收命令（review 可逐條複跑）

```
python3 -m pytest tests/governance/test_govb49_path_grant.py -q      # 33 passed
python3 -m pytest tests/governance/test_govb1_contract_matrix.py -q  # 84 passed
bash scripts/govb1_final_gate.sh --only g7                           # rc=0
bash scripts/govb1_ghostpath_check.sh                                # 0 條
git diff --numstat 835c3d35 -- docs/GOVB1_INPUT_QUALITY_TODO.md      # 只增不刪
```
