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
