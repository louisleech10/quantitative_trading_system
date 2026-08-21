"""
案例導入服務

提供CSV/Excel案例上傳、解析、驗證和存儲功能
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dateutil import parser as date_parser
import io
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.logging import get_logger
from api.models.case_models import CaseRecord, CaseImportResponse
from api.utils.case_storage import CaseStorageManager, get_case_storage_manager

logger = get_logger("api.case_import_service")


class CaseImportService:
    """
    案例導入服務

    提供CSV/Excel解析、驗證、標準化和存儲功能
    """

    # 必要欄位定義
    REQUIRED_COLUMNS = ['symbol', 'timestamp', 'Positive_case']
    OPTIONAL_COLUMNS = ['timeframe']

    # 支援的文件大小限制（10MB）
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, storage_manager: Optional[CaseStorageManager] = None):
        """
        初始化案例導入服務

        Args:
            storage_manager: 案例存儲管理器（若為None則自動創建）
        """
        self.storage = storage_manager or CaseStorageManager()
        logger.info("CaseImportService initialized")


    def import_from_file(
        self,
        file_content: bytes,
        filename: str,
        default_timeframe: str = "1h",
        validate_only: bool = False,
        force_clear: bool = False
    ) -> CaseImportResponse:
        """
        從文件導入案例

        Args:
            file_content: 文件內容（bytes）
            filename: 文件名
            default_timeframe: 預設時間框架（CSV缺少時使用）
            validate_only: 僅驗證不導入
            force_clear: 導入前強制清空所有舊案例（預設False）

        Returns:
            CaseImportResponse: 導入結果
            如果需要確認清空：success=False, need_confirmation=True

        Raises:
            ValueError: 文件格式錯誤或驗證失敗
        """
        logger.info(
            f"Importing cases from file: {filename} "
            f"(size: {len(file_content)} bytes, validate_only={validate_only}, force_clear={force_clear})"
        )

        # 檢查文件大小
        if len(file_content) > self.MAX_FILE_SIZE:
            error_msg = (
                f"File size ({len(file_content)} bytes) exceeds limit "
                f"({self.MAX_FILE_SIZE} bytes)"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Step 1: 解析CSV/Excel
        try:
            df = self._parse_file(file_content, filename)
            logger.info(f"Parsed {len(df)} rows from file")
        except Exception as e:
            logger.error(f"Failed to parse file: {e}", exc_info=True)
            raise ValueError(f"Failed to parse file: {str(e)}")

        # Step 2: 標準化列名（大小寫不敏感匹配）
        df = self._normalize_column_names(df)
        logger.debug("Normalized column names")

        # Step 3: CSV注入防護
        df = self._sanitize_dataframe(df)
        logger.debug("Applied CSV injection protection")

        # Step 4: 驗證欄位
        validation_errors, validation_warnings = self._validate_columns(df)

        # Step 5: 清理和標準化數據
        df_cleaned, cleaning_errors = self._clean_and_normalize(df, default_timeframe)

        # 合併錯誤
        all_errors = validation_errors + cleaning_errors

        # Step 6: 計算統計信息
        total_rows = len(df)
        valid_cases = len(df_cleaned)
        invalid_cases = total_rows - valid_cases

        # Step 6.5: 檢查現有案例（如果不是僅驗證模式）
        existing_count = 0
        if not validate_only:
            existing_cases = self.storage.get_cases()
            existing_count = len(existing_cases)

            # 如果已有案例且未強制清空，返回需要確認
            if existing_count > 0 and not force_clear:
                logger.warning(
                    f"System has {existing_count} existing cases. "
                    f"Import cancelled - need user confirmation to clear."
                )
                return CaseImportResponse(
                    success=False,
                    need_confirmation=True,
                    existing_count=existing_count,
                    total_rows=total_rows,
                    valid_cases=valid_cases,
                    invalid_cases=invalid_cases,
                    imported_cases=0,
                    errors=[],
                    warnings=[
                        f"系統已有 {existing_count} 個案例。上傳新CSV將清空所有舊案例，請確認是否繼續。"
                    ],
                    case_ids=[]
                )

            # 如果強制清空，執行清空
            if force_clear and existing_count > 0:
                cleared_count = self.storage.clear_all()
                logger.info(f"Cleared {cleared_count} existing cases before import (force_clear=True)")
                validation_warnings.append(f"已清空 {cleared_count} 個舊案例")

        # Step 7: 如果不是僅驗證，則存儲案例
        imported_case_ids = []
        if not validate_only and valid_cases > 0:
            try:
                cases = self._create_case_records(df_cleaned, filename)
                imported_case_ids = self.storage.save_cases(cases)
                
                # 檢查是否有案例存儲失敗
                failed_count = len(cases) - len(imported_case_ids)
                if failed_count > 0:
                    all_errors.append(
                        f"Storage: {failed_count} cases failed to save (check logs for details)"
                    )
                
                logger.info(f"Saved {len(imported_case_ids)}/{len(cases)} cases to storage")
            except Exception as e:
                logger.error(f"Failed to save cases: {e}", exc_info=True)
                all_errors.append(f"Storage error: {str(e)}")

        # Step 8: 構建響應
        response = CaseImportResponse(
            success=(len(all_errors) == 0) if not validate_only else (len(validation_errors) == 0),
            total_rows=total_rows,
            valid_cases=valid_cases,
            invalid_cases=invalid_cases,
            imported_cases=len(imported_case_ids),
            errors=all_errors,
            warnings=validation_warnings,
            case_ids=imported_case_ids
        )

        logger.info(
            f"Import completed: {response.valid_cases}/{response.total_rows} valid, "
            f"{response.imported_cases} imported, {len(response.errors)} errors"
        )

        return response


    def _parse_file(self, file_content: bytes, filename: str) -> pd.DataFrame:
        """
        解析CSV或Excel文件

        Args:
            file_content: 文件內容
            filename: 文件名

        Returns:
            pd.DataFrame: 解析的數據

        Raises:
            ValueError: 解析失敗
        """
        file_ext = Path(filename).suffix.lower()

        try:
            if file_ext in ['.csv', '.txt']:
                # 嘗試多種編碼
                for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'big5']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                        logger.debug(f"Successfully parsed CSV with encoding: {encoding}")
                        return df
                    except UnicodeDecodeError:
                        continue
                raise ValueError("Failed to parse CSV with any encoding")

            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(io.BytesIO(file_content))
                logger.debug("Successfully parsed Excel file")
                return df

            else:
                raise ValueError(f"Unsupported file format: {file_ext}")

        except Exception as e:
            logger.error(f"File parsing error: {e}", exc_info=True)
            raise


    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        標準化列名（大小寫不敏感匹配）

        將CSV文件中各種可能的列名格式轉換為標準格式：
        - Symbol/SYMBOL → symbol
        - Timestamp/TIMESTAMP → timestamp
        - Positive_Case/POSITIVE_CASE/Positive_case → Positive_case
        - Timeframe/TIMEFRAME → timeframe

        Args:
            df: 原始DataFrame

        Returns:
            pd.DataFrame: 列名標準化後的DataFrame
        """
        # 創建列名映射字典（大小寫不敏感）
        column_mapping = {}

        # 定義標準列名和可能的變體
        standard_columns = {
            'symbol': ['symbol', 'Symbol', 'SYMBOL'],
            'timestamp': ['timestamp', 'Timestamp', 'TIMESTAMP'],
            'Positive_case': ['Positive_case', 'Positive_Case', 'POSITIVE_CASE', 'positive_case'],
            'timeframe': ['timeframe', 'Timeframe', 'TIMEFRAME']
        }

        # 遍歷DataFrame的列，找到匹配的標準列名
        for col in df.columns:
            # 去除首尾空白
            col_stripped = col.strip()

            # 查找匹配的標準列名
            for standard_col, variants in standard_columns.items():
                if col_stripped in variants:
                    column_mapping[col] = standard_col
                    logger.debug(f"Mapped column '{col}' → '{standard_col}'")
                    break

        # 應用映射
        if column_mapping:
            df = df.rename(columns=column_mapping)
            logger.info(f"Normalized {len(column_mapping)} column names")

        return df


    def _validate_columns(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """
        驗證必要欄位

        Args:
            df: DataFrame

        Returns:
            Tuple[List[str], List[str]]: (errors, warnings)
        """
        errors = []
        warnings = []

        # 檢查必要欄位
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
            logger.error(f"Missing columns: {missing_cols}")

        # 檢查可選欄位
        for col in self.OPTIONAL_COLUMNS:
            if col not in df.columns:
                warnings.append(f"Optional column '{col}' not found, will use default")
                logger.warning(f"Optional column '{col}' not found")

        # 檢查空值
        if not errors:
            for col in self.REQUIRED_COLUMNS:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    warnings.append(
                        f"Column '{col}' has {null_count} null values, rows will be skipped"
                    )
                    logger.warning(f"Column '{col}' has {null_count} null values")

        return errors, warnings


    def _sanitize_csv_injection(self, value: str) -> str:
        """
        防止CSV注入攻擊

        檢測並清理可能包含危險公式的字符串，防止在Excel/LibreOffice中執行

        Args:
            value: 字符串值

        Returns:
            str: 清理後的值
        """
        if not isinstance(value, str):
            return value

        # 去除首尾空白
        value = value.strip()

        # 檢查是否以危險字符開頭
        dangerous_prefixes = ['=', '+', '-', '@', '\t', '\r']

        for prefix in dangerous_prefixes:
            if value.startswith(prefix):
                # 在開頭添加單引號，防止公式執行
                cleaned_value = f"'{value}"
                logger.warning(
                    f"Detected potential CSV injection: {value[:50]}... "
                    f"Sanitized to: {cleaned_value[:50]}..."
                )
                return cleaned_value

        return value


    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        對DataFrame所有字符串列進行CSV注入防護

        Args:
            df: 原始DataFrame

        Returns:
            pd.DataFrame: 清理後的DataFrame
        """
        df_sanitized = df.copy()

        # 對所有object類型的列進行清理
        for col in df_sanitized.columns:
            if df_sanitized[col].dtype == 'object':
                df_sanitized[col] = df_sanitized[col].apply(
                    lambda x: self._sanitize_csv_injection(x) if isinstance(x, str) else x
                )

        return df_sanitized


    def _clean_and_normalize(
        self,
        df: pd.DataFrame,
        default_timeframe: str
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        清理和標準化數據

        Args:
            df: 原始DataFrame
            default_timeframe: 預設時間框架

        Returns:
            Tuple[pd.DataFrame, List[str]]: (cleaned_df, errors)
        """
        errors = []
        df_clean = df.copy()

        # 移除必要欄位為空的行
        for col in self.REQUIRED_COLUMNS:
            if col in df_clean.columns:
                before_count = len(df_clean)
                df_clean = df_clean.dropna(subset=[col])
                after_count = len(df_clean)
                if before_count > after_count:
                    logger.info(
                        f"Removed {before_count - after_count} rows with null {col}"
                    )

        # 添加預設timeframe（如果缺少）
        if 'timeframe' not in df_clean.columns:
            df_clean['timeframe'] = default_timeframe
            logger.info(f"Added default timeframe: {default_timeframe}")

        # 標準化symbol（轉大寫）
        if 'symbol' in df_clean.columns:
            df_clean['symbol'] = df_clean['symbol'].str.upper()
            logger.debug("Normalized symbols to uppercase")

        # 標準化timestamp
        if 'timestamp' in df_clean.columns:
            df_clean['timestamp_normalized'], ts_errors = self._normalize_timestamps(
                df_clean['timestamp']
            )
            errors.extend(ts_errors)

            # 移除timestamp轉換失敗的行
            before_count = len(df_clean)
            df_clean = df_clean.dropna(subset=['timestamp_normalized'])
            after_count = len(df_clean)
            if before_count > after_count:
                logger.warning(
                    f"Removed {before_count - after_count} rows with invalid timestamps"
                )

            # 替換原timestamp欄位
            df_clean['timestamp'] = df_clean['timestamp_normalized'].astype(int)
            df_clean = df_clean.drop('timestamp_normalized', axis=1)

        # 驗證Positive_case值（只能是0或1）
        if 'Positive_case' in df_clean.columns:
            invalid_labels = ~df_clean['Positive_case'].isin([0, 1, '0', '1'])
            if invalid_labels.any():
                invalid_count = invalid_labels.sum()
                errors.append(
                    f"{invalid_count} rows have invalid Positive_case values (must be 0 or 1)"
                )
                logger.warning(
                    f"Found {invalid_count} invalid Positive_case values"
                )
                df_clean = df_clean[~invalid_labels]

            # 轉換為整數
            df_clean['Positive_case'] = df_clean['Positive_case'].astype(int)

        return df_clean, errors


    def _normalize_timestamps(self, timestamps: pd.Series) -> Tuple[pd.Series, List[str]]:
        """
        標準化時間戳格式

        支援多種格式：
        - Unix timestamp (整數)
        - ISO格式字串 ("2025-01-15 12:00:00")
        - Excel datetime

        Args:
            timestamps: 時間戳Series

        Returns:
            Tuple[pd.Series, List[str]]: (normalized_timestamps, errors)
        """
        errors = []
        normalized = pd.Series(index=timestamps.index, dtype='float64')

        for idx, ts in timestamps.items():
            try:
                # 情況1：已經是Unix timestamp（整數）
                if isinstance(ts, (int, np.integer)):
                    normalized[idx] = int(ts)
                    continue

                # 情況2：浮點數（可能是Excel datetime或Unix timestamp）
                if isinstance(ts, (float, np.floating)):
                    if ts > 1e9:  # 大於10億，視為Unix timestamp
                        normalized[idx] = int(ts)
                    else:  # 否則視為Excel datetime
                        # Excel起始日期：1900-01-01
                        excel_epoch = datetime(1900, 1, 1)
                        dt = excel_epoch + pd.Timedelta(days=ts - 2)  # Excel誤差修正
                        normalized[idx] = int(dt.timestamp())
                    continue

                # 情況3：字串格式
                if isinstance(ts, str):
                    # 嘗試解析為datetime（視為UTC時間）
                    dt = date_parser.parse(ts)
                    # 如果沒有時區信息，視為UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    normalized[idx] = int(dt.timestamp())
                    continue

                # 情況4：pandas Timestamp
                if isinstance(ts, pd.Timestamp):
                    normalized[idx] = int(ts.timestamp())
                    continue

                # 無法識別的格式
                errors.append(f"Row {idx}: Unrecognized timestamp format: {ts}")
                logger.warning(f"Row {idx}: Unrecognized timestamp format: {ts}")

            except Exception as e:
                errors.append(f"Row {idx}: Failed to parse timestamp '{ts}': {str(e)}")
                logger.warning(f"Row {idx}: Timestamp parsing error: {e}")

        return normalized, errors


    def _create_case_records(
        self,
        df: pd.DataFrame,
        source_file: str
    ) -> List[CaseRecord]:
        """
        從DataFrame創建CaseRecord列表

        Args:
            df: 清理後的DataFrame
            source_file: 來源文件名

        Returns:
            List[CaseRecord]: 案例記錄列表
        """
        cases = []
        current_time = datetime.utcnow()

        for idx, row in df.iterrows():
            try:
                # 生成case_id
                case_id = (
                    f"{row['symbol']}_{row['timestamp']}_{row['Positive_case']}"
                )

                case = CaseRecord(
                    case_id=case_id,
                    symbol=row['symbol'],
                    timeframe=row['timeframe'],
                    timestamp=int(row['timestamp']),
                    positive_case=int(row['Positive_case']),
                    source_file=source_file,
                    import_time=current_time
                )
                cases.append(case)

            except Exception as e:
                logger.warning(
                    f"Row {idx}: Failed to create CaseRecord: {e}"
                )
                continue

        logger.info(f"Created {len(cases)} CaseRecords from DataFrame")
        return cases


# 創建全局實例
_case_import_service = None


def get_case_import_service() -> CaseImportService:
    """
    獲取CaseImportService單例

    Returns:
        CaseImportService: 服務實例
    """
    global _case_import_service

    if _case_import_service is None:
        # 使用全局單例的storage manager
        storage_manager = get_case_storage_manager()
        _case_import_service = CaseImportService(storage_manager=storage_manager)
        logger.info("Created global CaseImportService instance with shared storage")

    return _case_import_service


# ===========================================================================
# GAP-3 Task B5.1 — 新 schema 事件匯入（驗證唯一實作在 momentum/ 純函式；本層只解析檔案、透傳、落檔）
# ===========================================================================
import hashlib as _hashlib
import json as _json
import uuid as _uuid

from api.models.event_import_models import (
    EventImportDetailResponse, EventImportFailure, EventImportListResponse, EventImportRejected,
    EventImportResponse, EventImportSummary,
)

LEGACY_COLUMNS = frozenset({"symbol", "timestamp", "positive_case"})
_NESTED_FIELDS = ("label_definition", "meta", "source_model", "event_interval", "reference_symbols")


class EventImportRejectedError(ValueError):
    """匯入拒收（顯式、逐列 reason；路由轉 4xx）。"""

    def __init__(self, payload: EventImportRejected):
        self.payload = payload
        super().__init__(payload.message)


class EventImportService:
    """新 schema 事件匯入：解析（CSV/JSON）→ `create_event_sample_pipeline().validate()` → 落檔。

    - 契約檢查**不**在此重複（R7）：只呼叫 momentum 純函式並透傳 failures。
    - legacy 三欄（symbol/timestamp/Positive_case）⇒ 顯式 migration 提示拒收（禁 silent coerce）。
    - 落檔：`<storage_dir>/<import_id>.json`（預設 `data_cache/events/`；舊 `cases.json` 不遷移）。
    """

    MAX_FILE_SIZE = 50 * 1024 * 1024

    def __init__(self, storage_dir: Optional[Path] = None):
        from momentum.factories import create_event_sample_pipeline  # 唯一出口（TODO §0-6-⑦）

        self._pipeline = create_event_sample_pipeline()
        self._contract = self._pipeline.import_contract()
        project_root = Path(__file__).resolve().parents[2]
        self.storage_dir = Path(storage_dir) if storage_dir else project_root / "data_cache" / "events"

    # ---- 偵測（只看鍵名，不做檢查） ----
    def required_fields(self) -> List[str]:
        return list(self._contract["required_fields"].keys())

    @staticmethod
    def _canon_cols(columns: List[str]) -> set:
        """偵測用欄名正規化：去 BOM／引號／空白、casefold（CODEX-R1-P2-06：`Event_ID,T0,Label` 亦須命中 marker）。"""
        return {str(c).replace("﻿", "").strip().strip('"').strip("'").strip().casefold() for c in columns}

    def looks_legacy(self, columns: List[str]) -> bool:
        cols = self._canon_cols(columns)
        return LEGACY_COLUMNS <= cols and not ({"event_id", "t0", "label"} <= cols)

    def looks_new_schema(self, columns: List[str]) -> bool:
        return {"event_id", "t0", "label"} <= self._canon_cols(columns)

    def migration_hint(self, columns: List[str]) -> Dict[str, object]:
        cols = {str(c).strip() for c in columns}
        return {
            "endpoint": "/api/v1/case/import-events",
            "required_fields_absent": [f for f in self.required_fields() if f not in cols],
            "field_mapping": {"timestamp(秒)": "t0(epoch ms UTC；錨定 TF bar open)", "Positive_case": "label(0/1)",
                              "symbol": "symbol", "timeframe": "timeframe(錨定 TF，必填)"},
            "contract": "momentum/Analysis/contracts/event_import_contract.json",
            "note": "舊 cases.json 不遷移；新 schema 須逐列附 label_definition/control_kind/digest 等欄位",
        }

    # ---- 解析 ----
    def parse_upload(self, content: bytes, filename: str) -> List[Dict[str, object]]:
        if len(content) > self.MAX_FILE_SIZE:
            raise EventImportRejectedError(EventImportRejected(kind="parse_error", message=f"檔案超過 {self.MAX_FILE_SIZE} bytes"))
        name = (filename or "").lower()
        try:
            if name.endswith(".json"):
                data = _json.loads(content.decode("utf-8"))
                records = data.get("records") if isinstance(data, dict) else data
                if not isinstance(records, list):
                    raise ValueError("JSON 須為記錄列表或 {records: [...]}")
                return [dict(r) for r in records]
            # 分塊解析（TODO B5.1 邊界②：不一次 materialize 整個 DataFrame；上限由 MAX_FILE_SIZE 界定）
            records: List[Dict[str, object]] = []
            for chunk in pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False, chunksize=self.CSV_CHUNK_ROWS):
                records.extend(self._csv_rows_to_records(chunk))
            return records
        except EventImportRejectedError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EventImportRejectedError(EventImportRejected(kind="parse_error", message=f"解析失敗：{exc}")) from exc

    CSV_CHUNK_ROWS = 5000

    def _csv_rows_to_records(self, df: pd.DataFrame) -> List[Dict[str, object]]:
        """CSV → 記錄：巢狀欄接受 JSON 字串儲存格或 dotted 欄（`label_definition.rule_id`）；數值欄以 JSON 解碼。"""
        records: List[Dict[str, object]] = []
        cols = list(df.columns)
        for row_t in df.itertuples(index=False, name=None):
            row = dict(zip(cols, row_t))
            rec: Dict[str, object] = {}
            for c in cols:
                raw = row[c]
                if raw == "" or raw is None:
                    continue
                key = str(c).strip()
                val: object = raw
                try:
                    val = _json.loads(raw)
                except (ValueError, TypeError):
                    val = raw
                if "." in key and key.split(".", 1)[0] in _NESTED_FIELDS:
                    top, sub = key.split(".", 1)
                    target = rec.setdefault(top, {})
                    if isinstance(target, dict):
                        if "." in sub:
                            s1, s2 = sub.split(".", 1)
                            target.setdefault(s1, {})[s2] = val
                        else:
                            target[sub] = val
                    continue
                rec[key] = val
            records.append(rec)
        return records

    # ---- 匯入 ----
    def import_records(
        self, records: List[Dict[str, object]], *, source_name: Optional[str], upload_bytes: Optional[bytes],
        validate_only: bool, verify_source_digest: bool = False, source_bytes: Optional[bytes] = None,
    ) -> EventImportResponse:
        """upload_bytes：事件檔內容（記 `upload_sha256` 供 provenance）。
        source_bytes：契約所指之**來源檔**位元組（CODEX-R2-P1-03）；`verify_source_digest=True` 時以此逐列對證
        `source_file_digest`（未提供則退回 upload_bytes——僅在事件檔本身即來源檔時才有意義）。"""
        columns = sorted({k for r in records for k in r.keys()}) if records else []
        if self.looks_legacy(columns):
            raise EventImportRejectedError(EventImportRejected(
                kind="legacy_schema_detected",
                message="偵測到舊三欄格式（symbol/timestamp/Positive_case）；新端點只收 event_import_contract 新 schema，不做靜默轉換",
                migration_hint=self.migration_hint(columns),
            ))
        verify_bytes = (source_bytes if source_bytes is not None else upload_bytes) if verify_source_digest else None
        df, failures = self._pipeline.validate(records, source_bytes=verify_bytes)
        digest = _hashlib.sha256(upload_bytes).hexdigest() if upload_bytes is not None else None
        if df is None:
            raise EventImportRejectedError(EventImportRejected(
                kind="contract_violation",
                message=f"{len(failures)} 筆契約違規（逐列 reason 見 failures；字面＝event_import_contract.json）",
                failures=[EventImportFailure(**{k: f.get(k) for k in ("row", "event_id", "field", "reason")}) for f in failures],
                migration_hint=self.migration_hint(columns) if self.migration_hint(columns)["required_fields_absent"] else None,
            ))
        warnings: List[str] = []
        import_id = None
        stored_path = None
        if not validate_only:
            import_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + _uuid.uuid4().hex[:8]
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "import_id": import_id, "source_name": source_name, "upload_sha256": digest,
                "source_digest_verified": bool(verify_source_digest),
                "source_file_sha256": _hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None,
                "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "contract_version": str(self._contract.get("version")),
                "records": df.to_dict("records"),
            }
            p = self.storage_dir / f"{import_id}.json"
            p.write_text(_json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str), encoding="utf-8")
            stored_path = str(p)
        return EventImportResponse(
            accepted=True, import_id=import_id, n_rows=len(records), n_valid=int(len(df)), failures=[],
            warnings=warnings, upload_sha256=digest, source_digest_verified=bool(verify_source_digest),
            contract_version=str(self._contract.get("version")), stored_path=stored_path,
        )

    # ---- 查詢 ----
    def _load(self, path: Path) -> Dict[str, object]:
        return _json.loads(path.read_text(encoding="utf-8"))

    def _summary(self, payload: Dict[str, object]) -> EventImportSummary:
        recs = payload.get("records") or []
        return EventImportSummary(
            import_id=str(payload["import_id"]), source_name=payload.get("source_name"),
            upload_sha256=str(payload.get("upload_sha256") or ""), imported_at=str(payload["imported_at"]),
            n_events=len(recs), symbols=sorted({str(r.get("symbol")) for r in recs}),
            timeframes=sorted({str(r.get("timeframe")) for r in recs}),
            direction=str(recs[0].get("direction")) if recs else None, scenario=str(recs[0].get("scenario")) if recs else None,
        )

    def list_imports(self) -> EventImportListResponse:
        items: List[EventImportSummary] = []
        if self.storage_dir.is_dir():
            for p in sorted(self.storage_dir.glob("*.json")):
                try:
                    items.append(self._summary(self._load(p)))
                except Exception:  # noqa: BLE001 —— 壞檔列為不可讀、不吞；以 warning log 揭露
                    logger.warning("event import 檔無法讀取：%s", p)
        return EventImportListResponse(total=len(items), imports=items)

    def get_import(self, import_id: str) -> Optional[EventImportDetailResponse]:
        if not import_id or "/" in import_id or ".." in import_id:
            return None
        p = self.storage_dir / f"{import_id}.json"
        if not p.is_file():
            return None
        payload = self._load(p)
        return EventImportDetailResponse(summary=self._summary(payload), records=list(payload.get("records") or []))


    # ---- 分析（B5.2 兩表資料源；統計全在 momentum，本層只組 request/response） ----
    def analyze(self, import_id: str, req) -> Optional[Dict[str, object]]:
        from api.utils.json_serializer import sanitize_for_json

        detail = self.get_import(import_id)
        if detail is None:
            return None
        records = detail.records
        symbols = sorted({str(r["symbol"]) for r in records})
        tfs = sorted({str(r["timeframe"]) for r in records})
        bars = self._pipeline.bars_from_kline_cache(symbols, tfs)
        res = self._pipeline.run_with_params(
            records, bars, test_fraction=float(req.test_fraction), embargo_ms=req.embargo_ms,
            tier_min_test_events=int(req.tier_min_test_events),
        )
        tables = self._pipeline.analyze_tables(res, bars, horizons=tuple(int(h) for h in req.horizons),
                                               seed=int(req.seed), n_boot=int(req.n_boot))
        payload = {
            "import_id": import_id,
            "summary": res.summary,
            "align_failures": res.align_failures.to_dict("records") if not res.align_failures.empty else [],
            "tables": tables,
            "event_timestamps": [int(t) for t in res.events["t0"].tolist()],                     # epoch ms（契約 t0）
            "event_timestamps_ic_seconds": [int(t) // 1000 for t in res.events["t0"].tolist()],  # IC 主線 row_index＝bar open 秒
        }
        return sanitize_for_json(payload)


_event_import_service: Optional[EventImportService] = None


def get_event_import_service() -> EventImportService:
    global _event_import_service
    if _event_import_service is None:
        _event_import_service = EventImportService()
    return _event_import_service
