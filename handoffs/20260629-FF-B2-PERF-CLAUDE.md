# B2 比對效能設計 — Claude 腿(委員會定案用)

## 問題
B2 全鏈截斷 MR:full+trunc 兩次 generate_features(全開,各 ~20分,本身是因果測試必要)後,**比對全部 220158 特徵**(每欄 fill_rate+NaN mask+值)>20分跑不完 → 單測 >40分不切實際。**比對規模是瓶頸,非正確性問題**(FF 因果已三方簽核 PASS)。

## Claude 提案:分層抽樣比對(generate 仍全鏈)
1. **columns gate 維持全集**(便宜:只對欄名做 set 運算,不讀值):交集 + 不對稱掉欄門檻 max(100,0.1%union)。整層消失仍抓得到。
2. **values + NaN mask gate 改分層抽樣**:
   - 把共同欄按 **(layer, operator/category)** 前綴分組(L1 by atomic category、L2 by operator、L3 by window×stat、L4 lag、L6.5 by preprocess type)。
   - 每組 **確定性抽樣 min(K, 組大小)**(K≈30-50,sorted 後固定 stride 或 seeded,可重現)→ 幾千欄,**涵蓋每個 layer/operator 型別**。
   - 對抽樣欄做收斂設計的 values(both-non-NaN rtol2e-3)+ NaN mask 分層 + 覆蓋率守衛。
3. **mutation 探針相容**:center=True(L3)/shift(-1)(L4)/全量fit(L6.5)注入的層,抽樣**必含該層欄**(保證每層至少抽到)→ mutation 仍真紅。
4. 理由:因果性(無 look-ahead)對全體均勻成立(三方讀碼確認每層算法單向),**分層抽樣每型別都驗到 = 強證據**,不需逐一比 22 萬。單測降到 generate(~20分)+ 比對(秒級)。

## 待委員(Codex/Composer)定案(純設計推理,勿跑慢全鏈)
- 分層抽樣 K 多少、分組鍵怎麼定才「每 layer/operator 型別都覆蓋」且 mutation 注入層必含?
- 抽樣會不會放走「只有某幾個特定欄洩漏」?(vs 全比)——因果是層級算法性質,單欄洩漏需該層算法錯,抽樣同層即代表;但若有風險,加「mutation 注入欄必在抽樣集」硬保證。
- columns gate 全集 + values 抽樣 的分工是否足?
- 結論:抽樣設計定案(分組鍵+K+mutation 相容保證)。
