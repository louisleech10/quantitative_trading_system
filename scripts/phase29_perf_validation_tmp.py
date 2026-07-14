"""QUARANTINED by IC1C-FR-STOPGAP.

原 phase29 效能驗證會直接實例化 FactorReturnAnalyzer 並呼叫 compute_batch,
在 ls_returns 時間錯位修好(1c-FR-FULL)前禁止執行。
"""

raise SystemExit("quarantined: ls_returns misaligned, see 1c-FR-FULL")
