# Handoff
**Agent**: Claude(Fable 5) | **Time**: 2026-07-14 下午 | **Branch**: main

## 🔄 進行中:1c Net IC 量綱正確化(大,RISK-HIT a,b,d,完整管線)
1. **SPEC v1.0 Frozen**(docs/IC1C_NETIC_SPEC.md):五輪三家 adversarial(r1 17B→r5 0B)全閉合;RECONCILE 戳記機檢 PASS(codex/composer/grok,body sha256:ab910286)。裁決=**B-strict**:禁相關係數減報酬率;`net_ic` 鍵全樹禁止;canonical 因子報酬序列拆票 **1c-FR**(codex 實證 `ls_returns` reset_index 位置相減錯位),1c 內 net_factor_return/breakeven/profitable 一律 unavailable+reason;成本公式**去 ×2**(quantile_turnover 已含雙腿);§U 三 profile 鍵集合+discriminated union;cost_bps 域 (0,1000] 三層 fail-closed(0 非法);審計鏈 handoffs/20260714-IC1C-SPECREV-*。
2. **TODO r6 Frozen(2026-07-14)**:六輪三家 adversarial(15B→0;grok r3/composer r5/codex r6 APPROVE);RECONCILE-STAMP 機檢 PASS(body 936daabc);SPEC 同步補 v1.1(負 turnover→SKIPPED 禁 clamp,三家核可)。receipt=handoffs/IC1C-GOVERNANCE-RECEIPT.md。
3. **下一步:B0 派工 Grok**(baseline 凍結,workspace 沙箱)→B1(核心+momentum 消費點)→B2(全棧接線)→B3(UI 註記);每批 Codex+Composer 審查,Gate 命令在 TODO §B;派工進度 10 分鐘回報。

## 📌 慣例/本 session 新裁定
- **Grok 審查輪改用 `--sandbox workspace` 直接寫產出檔**(2026-07-14 使用者質疑唯讀限制後改制,記憶已更新);read-only 只留純諮詢。
- RECONCILE 戳記須 v2 格式:`## 戳記` 區段+`RECONCILE-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<id>`,委員自算 hash;grok 家族用 check 腳本第二參數納入。
- pytest collect 副作用檔 `tests/golden/l65/test_inventory.txt` 每次 revert;全套件既有紅 ~50 failed/171 errors(非本 session 引入)。
- commit 訊息 operational claim 需 VERIFY:<receipt>(hook 強制)。

## ⚠️ 未 commit
docs/IC1C_NETIC_{SPEC,TODO}.md+handoffs/ 審計鏈全未 commit(待 TODO Frozen 後與 ROADMAP/HANDOFF 一併 commit+push)。
