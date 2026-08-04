# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-04 | **Branch**: **main**（全部已 push，`42f6825`）
**狀態**: 🟢 GOVFLOW epic 完工 ／ 🔵 **下一步＝治理 backlog 第 0 批**

## ▶ 下一步：第 0 批（使用者已指示 compact 後開始）

**三張合成一個批次，走完整管線**（SPEC → TODO → 雙家族 adversarial → 實作 → 雙家族 code review）。

| 票 | 病 | 根因（已查證） | 修法方向 |
|---|---|---|---|
| `B-24` `GOV-ACCEPTANCE-STATE-NOT-RC` | 驗收寫成「補救動作的 rc」而非「補救後的狀態」 | 橫向紀律，非新元件 | 併入各票驗收欄；**今日兩次踩到**：`restore_golden_inventory.sh` rc=0 被當成 golden 乾淨（正解＝`git status --short tests/golden/` 為空） |
| `B-15` `GOV-GATECHECK-READONLY-PGREP-FP` | 唯讀查詢被誤判成派工，本 session 多次 | 🔴 **已讀碼查證，勿用舊敘述**：`gate_check.sh:86` 的正則**只比對命令位置**（`(^\|[;&\|][[:space:]]*)(codex\|cursor-agent\|grok\|agy)[[:space:]]`），設計上已避開檔名子字串——**真正的洞是它不理解引號**：引號**內**的 `;` 被當成命令分隔符。實證：`--reason "…no review file; codex closure review…"` 被擋，改寫成不含家族名才過。⚠️ 其餘 FP（`pgrep`／for 迴圈讀產出／`completeness --lock`）**觸發機制可能不同，須逐一重現後才下修法** | 使正則具備**引號感知**（引號內不視為命令分隔符）；或改判準為「是否實際呼叫 `cx_run.sh`／`committee_run.sh`」。🔴 **兩案須先各自對真實指令語料實跑誤擋率**，勿憑推測選 |
| `B-14` `GOV-CURSORAGENT-POSTWRITE-HANG` | 委員工具寫完產出不退出，曾空等 **2h20m** | sandbox shell 卡在 `snap=$(command cat <&3)`（fd3 永久阻塞） | ①per-family timeout＋產出通過 `completeness_check --single` 則視為成功並終止 ②逾時且不完整 ⇒ `failed`／`format-failed` 走重派 |

🔴 **`B-15` 的修法會改變「誰被擋」⇒ 正是 `B-29`（行為差集）的典型案例，但 `B-29` 尚未實作**
⇒ **本批須手動附前後對照**（舊版 vs 新版對同一批真實指令，列出「本來擋現在放行」）。作法見 `票 B-29` §修法。

⚠️ **可併入本批考慮**（未開票，使用者未裁決）：委員家族偶發 `RetriableError: [resource_exhausted]`
（**連線中斷非配額**，重派即成功），今日吃掉一次派工。與 `B-14` 同族＝委員 CLI 異常處理。

## 治理 backlog — 排序 v3（2026-08-04 全量重排，**唯一有效**）

**唯一票登記處**＝`handoffs/20260801-GOV-AMEND-BACKLOG.md`（`B-1`～`B-29`）
**白話版**＝`handoffs/20260804-BACKLOG-白話總覽.md`（主表一票一列，兩份已機械對帳一致）

```
第0批 摩擦止血    B-24 → B-15 → B-14      第4批 散文與標記  B-16 → B-23
第1批 機制        B-19 → B-29             第5批 fail-open   B-11 → B-6 → B-5 → B-4 → B-8
第2批 地基        B-27                    第6批 完整性監看  B-20 → B-21 → B-12 → B-22
第3批 殺手寫漂移  B-17 → B-13 → B-26      另排              B-9 → B-28
```

29 張：✅2（`B-7`／`B-10`）｜🗑3（`B-1`～`B-3`）｜🔗2（`B-18`→`B-13`、`B-25`→`GOV-XREF-SYNC`）｜**待辦 22**。
🔴 **批次化非一票一管線**：22 張各走完整管線 ≈66 輪；7 批＋1 另排 ≈24–30 輪。

## GOVFLOW epic — 已完工（勿重做）

B0 `0d0f3a0`／B1 `d36d76b`／B2 `c0a7004`／B3 `2696e77`／**B4 `6a06f0c`**。
`pytest tests/governance` **617 → 701 passed**。B4 走 6 輪，雙家族最終皆 GO。

🔴 **具名接受的殘留（是未完成，勿當已解）**：
- **A-4 全域未解**：主委摘要／群集段無 backing 的 claim 仍不能 commit ⇒ 85 份真實收斂檔中 **12 份**仍有違規
- **12 個非 M code mutation 未逐一執行**（`T4-U1/N1/N2/C1/U2/N3/N4/N5/B1/B2/N6/B3`）
- TODO §0 數字對照表**本 epic 內漂 4 次**（四格曾錯三格）⇒ `票 B-17` 未做前還會再漂

## 🔴 使用者定死（最高優先）

1. **不能 100% 擋下 → 解決 95%，出問題再記錄**；**擋意外，不在「阻擋蓄意」上撞牆**
2. **工具必須自帶強制機制——不准靠紀律和記憶**；**檢查點放產出端，不放消費端**
3. **狀態回報**：寫【進行中】必須 (a) 同回覆有工具呼叫 或 (b) 附背景任務 ID；否則【停住】
   （機械強制：`scripts/status_marker_check.sh`）
4. **治理投資看所有 epic 完成後的合計貢獻**，不以單輪 findings 數評斷
5. 🔴 **2026-08-04 新裁決**：**治理優先於產品線**——「治理相關的沒做好，繼續專案開發只剩耗時間和
   token 在摩擦上」。8/1 起四天 `momentum/`／`api/`／`frontend/` 動到 **0 個檔案**，此為已知且經同意。
6. 🔴 **強制點須放在最早能攔的位置**：派工當下（gate 拒發 token）＞ 交件當下（`format-failed` 同輪重派）
   ＞ commit（保險）。**commit 在整條線最尾端，委員已跑完，不得作為主力。**

## 📌 開工前必做

1. 稽核本檔／ROADMAP vs repo 實況　2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`；收集用 `reconcile_build.sh`；**實作單派 Grok，review＝codex＋composer**
4. **`git push` 會跑整套 governance（約 180s）→ 一律丟背景**
5. **禁用專案外絕對路徑**（觸發 600 秒 A 類卡頓）；**改檔用 Edit 工具**
6. **`handoffs/*` 被 `.git/info/exclude` 排除**——須 `git add -f` 才進版控
7. brief 內假設標籤**不得用 `X-N` 形態**（`E-1` 會撞 `completeness_check` ID 誤報）

## ⚠️ 本 session 新增的坑（都親自踩過）

- **`core.hooksPath = scripts/git_hooks`**——查 `.git/hooks/` 會誤判「hook 沒裝」。**主委據此對使用者
  說了錯話**。正解＝用**有效探針**實測 rc，且探針須先確認「本來會被擋」。
- **zsh 不對未加引號的變數斷詞**：`--files ${LIST}` 把 2559 個路徑當成一個超長檔名，python 直接死掉，
  報表印「前 0 後 0、無差異」——**壞掉的量測與「一切正常」外觀相同**。批量傳檔一律走 `xargs`。
- **`echo "(以上無輸出=乾淨)"` 這類無條件標籤**會在有輸出時仍印出，**製造假紀錄**。改用 `if` 判斷。
- 委員探針會在 `handoffs/reconcile/` 留 `probe-*` 目錄，**污染統計基準**（89 vs 85）。
- `gate_check.sh` 的派工偵測**不理解引號**：`--reason "…; codex …"` 這種引號內的 `;` 被當成命令分隔符
  ⇒ 唯讀清帳被擋（＝`票 B-15`）。**權宜作法：清帳／commit 訊息裡不要出現「`;` 後接家族名」。**
- 🔴 **主委在 HANDOFF 寫根因前沒讀碼**，把 `B-15` 寫成「有家族名就擋」——讀 `gate_check.sh:78-86`
  後發現註解明寫已避開檔名子字串，真因是引號。**寫進交接文件的根因＝下一輪 SPEC 的輸入，必須先讀碼。**
