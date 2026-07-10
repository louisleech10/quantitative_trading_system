# IC 1e+1b — B3 實作派工(Task 3.1:cross_sectional 最小面)

**執行端**:Grok 4.5(階梯續派;B1/B2 已過)
**SPEC**:`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §A D-H(v2 修 horizon 丟失)　**TODO**:`docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase 3 Task 3.1(逐條要點=唯一真相)
**基底**:main 9df75d3(B1 kernel+B2 主路徑已接)。

## Scope(單 Task)
`analyze_cross_sectional`(:958-1096 段)填掉 p_value=None:
1. **horizon 於 `_label` 改名前解析**(CODEX-3):labels_path 分支→對 `_select_label_series` 選定的**原始欄名**跑 `_resolve_label_horizon_from_column`;in-frame 分支→對命中候選欄名跑;皆不可解析→h=None。
2. h 可解析:逐期 IC 序列直接作 z 序列餵 NW(mean/se_NW,L=max(auto_bw,h-1));h=None:**p 族欄位全 NaN+metadata 記 `horizon_unresolved`**(禁產反保守 p、禁 fallback h=1 假 horizon)。
3. `t_stat` 改 HAC(取代 :1077 i.i.d.),`p_value`=HAC p,增 `p_value_adj`(apply_fdr 對該路徑全 feature)。
4. 排序仍按 ICIR,**不加門檻**;`_resolve_cross_sectional_label_horizon` fallback-1 行為由上述取代或收斂(禁留兩套)。

## 測試
T-3.1a:xsec 單元 p 非 None+與 kernel 直算一致+i.i.d. t vs HAC t 在自相關合成資料分離(mutation:換回 i.i.d.→紅,真紅 receipt);T-3.1b M-J:labels_path `return_5`→maxlags≥4(mutation:對 `_label` 解析→紅;注意:單軸 labels_path 在 xsec 會 raise(orchestrator:951-954),測試可對 `analyze_cross_sectional` 以符合契約的 MultiIndex labels_df 路徑或單元層直測 resolver,禁擅自加單軸支援);T-3.1c:horizon 不可解析→p 全 NaN+metadata 標記。mutation 類 receipt 用 `python scripts/run_with_receipt.py --claim-id <id> -- venv/bin/python <mutation probe>` 產生(參考 scripts/ic1eb_b2_mutation_probe.py 模式),RESULT 中 VERIFY:<claim-id> 引用。

## 禁止事項
- 不動 ic_mean/icir/排序;不引入淘汰門檻;不動縱向路徑(B2 已閉);不加 xsec labels_path 單軸支援(scope 外)。
- 既有斷言不放寬;`handoffs/ic1eb_baseline/` 唯讀;data_cache 唯讀;l65 inventory 被覆寫則 git restore 該單一檔(唯一允許)。

## 驗收命令(全綠才交)(VERIFY-EXEMPT:doc-example:dispatch-prompt-future-commands)
```bash
source venv/bin/activate
venv/bin/python -m pytest tests/momentum/ -q   # 預期 1015+新測試 passed, 5 skipped
grep -rn "from api\." momentum/ | wc -l         # 0
```

## 交付
`handoffs/IC1EB-B3-IMPL-RESULT.md`:改檔/T-3.1a-c receipt(VERIFY:<claim-id> 格式)/mutation 真紅。兩輪解不了→BLOCKED 停手。
