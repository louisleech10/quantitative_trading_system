# 派工:修 B0 code review P0(Composer,§B8 原實作者修)

Codex code review(`handoffs/20260627-FF-DEEPAUDIT-B0-CODEREVIEW-codex.md`)抓出 2 P0:

## P0-1(必修):DATA_MANIFEST 測試讀真 kline 卻漏 requires_kline marker
- `tests/fixtures/test_data_manifest.py` 的 4 個讀真 kline 的測試(validate/3 mutation)未掛 `@pytest.mark.requires_kline` → `pytest --collect-only -m "not requires_kline"` 仍收集它們,PR smoke job 缺 kline 會 fail。
- 修:對讀真 kline 的測試掛 `@pytest.mark.requires_kline`;`test_manifest_file_is_versioned` 若不讀 kline 可留 smoke(確認它真的不讀)。
- 驗:`pytest --collect-only -q tests/fixtures/test_data_manifest.py -m "not requires_kline"` 只收集不讀 kline 的測試;`-m requires_kline` 收集讀 kline 的。

## P0-2(已由 Claude 還原,勿再動):golden/parquet 副作用已 git checkout 還原,不要重新生成或提交 tests/golden/l65/ 下任何檔。

## 次要(一併修):conftest KeyError 收斂
- `tests/conftest.py:75` 只捕 `ManifestValidationError`;manifest 有 entry 但實際 dataset 缺時 `compute_dataset_fingerprint()` 可能丟 `KeyError` → 變 pytest ERROR 非明確 fail。收斂成 `pytest.fail` 明確訊息。

收尾:更新 `handoffs/20260627-FF-DEEPAUDIT-B0-RESULT.md` 附修正驗證。完成 STATUS: DONE。不要動 golden/parquet/B1/B2。
