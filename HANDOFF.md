# HANDOFF — 當前任務狀態

**更新：2026-09-05｜狀態：`G3-D2` 實作中，但**目前插隊在 G-7FIX**（使用者指示：四步一起做完，不掛到 B-D4 之後）。**

## 🔴 現在進行中＝G-7FIX（四步）

使用者裁定（2026-09-05）：G-7 的四步處置**現在**跟委員討論每一步怎麼做，然後四步做完；
**不得**延到 B-D4 之後（原本我把第 4 步掛在 B-D4 是我自己加的相依，已撤銷）。

**已完成**：
- consult R1 三家全員（`handoffs/reconcile/20260905-g7fix-x-consult-r1/synth.md`）
- 收斂節點四步全過：歸戶 rc=0（18 條零掉項）／completeness `--lock` PASS／`debt_clear` rc=0
- 補清上輪殘留：R2 reconcile（`20260905-g7perf-x-consult-r2`）三家 RECONCILE-STAMP 已補齊並 PASS

- **consult R2**（使用者選的確認輪）三家全員，14 條，收斂節點四步全過，債清
  （`handoffs/reconcile/20260905-g7fix-x-consult-r2/synth.md`，群集 α–ι）

**R1 四個 P0（方向錯）**：`epic_state` 塞不進凍結檔／dormant 照字面恆紅（grok 獨家）／轉態豁免被穿透三條／洞 C 命中即擋會死鎖。

**R2 三個 P0（規格不夠精確到能施工）**：
- **α**：我只擴了**測試端**常數，沒指定 production parser（三支腳本須共用一支）＋需 `_FROZEN_ENUM_KEYS`
- **β**：🔴 **我的修補案自己新開的洞**——只封 `dormant→active`，沒封 `active→dormant`；frozen 檔在 manifest 是 allow ⇒ 一般 commit 就能關掉整個閘
- **γ**：old state 讀法（兩家實構補上：`old=git show HEAD:<p>`／`new=git show :<p>`／無 HEAD fail-closed）

**新查到的事實**：昂貴 G-7 自 2026-08-14 起**沒在 push 上跑過**（`gov_check.sh:266-267` `--fast` 早退，G-7 在 `:343-350`）。日常摩擦全來自 commit-msg 那支假閘。

- **SPEC review R1**（`docs/G7FIX_SPEC.md`）三家全員，18 條含 3 P0，三家一致**不可 freeze**；收斂節點四步全過，債清
  （`handoffs/reconcile/20260905-g7fix-x-review-r1/synth.md`，群集 1–11）

**SPEC review R1 之三個 P0**（我 brief 標的「我沒查」5 格中有 4 格開出真 finding）：
- **1**：`active→dormant` 無授權來源，我還把未授權路徑釘成 `rc=0` ⇒ 改為須帶 `ruling:<ID>` 且該 ID 須在 `docs/GOV_ENFORCEMENT_REGISTRY.md` 字面存在
- **2**：`GOVB1_FROZEN_HASHES` env 鉤子＝重蹈 `GOVB1_FACTKEY_ROOT` 傷疤（三家全員）⇒ 刪除，強制點 `env -u`
- **3**：dormant × 交付形態守衛我寫「須明確定義」＝定義本體留白（三家全員）⇒ 寫死決策表

SPEC 已依 11 群集改完，`template_check` PASS，具名 mutation 由 6 種補到 **16 種**（前版 §V 稱「≥8」是我的空頭宣稱，被 composer／grok 抓到）。

## 🔴 下一步＝SPEC review R2 閉合輪

閉合輪判定權屬**原提出方**，第三方不得代簽。R2 零 finding 才可 freeze SPEC 並進 TODO。

## G3-D2 主線（G-7FIX 完成後回來）

`B-D0／B-D1／B-D3` 皆 ✅ DONE（B-D3 於 R4 停輪，三家零 finding）。
下一件＝**B-D4（D4.2 全矩陣 13 對＋D4.3 k 參數化與掃描網格）**；
唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`（收據 §5、流程 §2、地雷 §3、裁定總表 §4），§2 七步不得跳步。
🔴 D4.3 之 benchmark 子步須**先於**凍結 cap。
