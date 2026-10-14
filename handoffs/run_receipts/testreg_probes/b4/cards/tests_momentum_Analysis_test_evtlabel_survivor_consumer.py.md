# 任務卡：tests/momentum/Analysis/test_evtlabel_survivor_consumer.py

- 組：G10；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r14/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r14-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_evtlabel_survivor_consumer.py::test_binary_provenance_survives_into_the_payload（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。其餘六條對 pattern_bridge._survivor_feature_names 之收件與三種 fail-loud 正常。test_binary_provenance_survives_into_the_payload 未呼叫任何生產碼，只斷言測試自建 _binary_payload 字典之鍵與值（:58-61 恆真），與 docstring「來源身分四鍵在 payload 裡完整保留」不符；修法：改由生產寫出端 survivor_contract（:532 寫 label_binary）組出 payload 後斷言四鍵與值（斷言不減）
