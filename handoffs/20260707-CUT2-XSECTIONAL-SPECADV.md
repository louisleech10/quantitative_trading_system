# 20260707-CUT2-XSECTIONAL-SPECADV handoff

正在做: 已完成 CUT2 cross_sectional SPEC/TODO adversarial review。
待辦: Claude/委員會需 reconcile findings，尤其 test-only output、labels_path HDF5 schema、min_label_coverage。
阻塞: 無執行阻塞；review 產出含 3 個 BLOCKING findings。
本次決策: 僅唯讀審查；未改 SPEC/TODO/程式碼；finding 寫入 handoffs/CUT2-XSECTIONAL-SPECADV-codex.md。
踩坑提醒: `_load_labels_hdf5` 目前無 symbol schema；F3 purge=0 mutation 不保證觸發 `validate_split_pair_integrity` raise。
驗證: 未跑 pytest；使用 `sed`/`rg` 讀取指定文件與程式碼。
STATUS: DONE
