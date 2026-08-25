"""
案例導入服務

提供CSV/Excel案例上傳、解析、驗證和存儲功能
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
import io
import logging
import warnings

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
import csv as _csv
import hashlib as _hashlib
import json as _json
import re as _re
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
        # 對映層 reason 字面之具名出口（R7：api 層不複列契約字面；字面漂移即 raise）
        self._mapping_reasons = self._pipeline.mapping_failure_reasons(self._contract)
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
            for chunk in self._read_csv_chunks(content):
                records.extend(self._csv_rows_to_records(chunk))
            return records
        except EventImportRejectedError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EventImportRejectedError(EventImportRejected(kind="parse_error", message=f"解析失敗：{exc}")) from exc

    CSV_CHUNK_ROWS = 5000

    @staticmethod
    def _has_unquoted_lone_cr(text: str) -> bool:
        """引號**外**之 `\\r` 且其後不是 `\\n`（舊式 Mac 換行，或 LF 檔中混入的裸 CR）。

        🔴 與前端 `csvPreview.splitRecords()` 之判準**逐字同一條**
        （R5 `CODEX-R5-P1-01`：R4 只讓前端擋，於是同一類分歧翻面成「前端擋／後端收」
        ——`label,symbol\\n1,ETHUSDT\\r` 後端讀得出來、前端整個不給用）。
        引號**內**之 `\\r` 是資料，兩端皆原樣保留。
        """
        quoted = False
        for i, ch in enumerate(text):
            if quoted:
                if ch == '"':
                    quoted = False          # `""` 之第二個引號會在下一圈把 quoted 轉回 True
                continue
            if ch == '"':
                quoted = True
            elif ch == "\r" and text[i + 1:i + 2] != "\n":
                return True
        return False

    def _assert_uniform_row_widths(self, content: bytes) -> None:
        """每一資料列之欄數須等於標頭欄數；不等即 `parse_error`（**本層為主要守衛**）。

        🔴 為何不靠 pandas（R2 `CODEX-R2-P1-02` 實測）：pandas 對欄數異常之反應**不一致**——
        每列多一格非空 ⇒ 靜默左移（加 `index_col=False` 後改為 ParserWarning）；
        每列多一格**空的** ⇒ 完全靜默吞掉；只有某一列多 ⇒ `ParserError`。
        三種同源異常三種行為，且依 pandas 版本而異 ⇒ 不能當作規則來源。
        本檔以 `csv` 標準庫獨立 tokenize 一次，得到**單一條、與 pandas 版本無關**的規則：
        「每列欄數 == 標頭欄數」——前端 `csvPreview.parseCsvText()` 之 `raggedRows` 用的是同一條，
        兩端因此不會出現「畫面擋了後端收」或反過來的落差。
        """
        text = content.decode("utf-8-sig", errors="replace")
        if self._has_unquoted_lone_cr(text):
            raise EventImportRejectedError(EventImportRejected(
                kind="parse_error",
                message=("CSV 含**不成對的 CR 換行**（舊式 Mac 換行，或 LF 檔中混入的裸 CR）。"
                         "支援的行尾只有 LF 與 CRLF；引號內的 CR 視為資料、不受此限。"
                         "請另存為一般換行後再上傳"),
            ))
        reader = _csv.reader(io.StringIO(text))
        header_width: Optional[int] = None
        bad: List[Tuple[int, int]] = []
        try:
            rows = list(reader)
        except _csv.Error as exc:
            # 舊式 Mac 換行（每行只有 CR）會走到這裡。訊息要**說出真正的原因**——
            # 原生訊息是 "new-line character seen in unquoted field"，使用者看不懂要改什麼。
            # 🔴 前端對同一個檔亦回空模型並顯示同一件事（R4 `CODEX-R4-P1-01`：
            #    舊版前端會把整檔黏成一行、產出看似合理的欄名讓使用者照著對映）。
            raise EventImportRejectedError(EventImportRejected(
                kind="parse_error",
                message=("CSV 解析失敗：常見原因是檔案用了**舊式 Mac 換行**（每行只有 CR）"
                         "或引號沒有成對。請另存為一般換行（LF／CRLF）後再上傳。"
                         f"（原始訊息：{exc}）"),
            )) from exc
        for i, row in enumerate(rows):
            # 整行空白＝跳過（與 pandas `skip_blank_lines` 及前端 `splitRecords` 三端一致）。
            # 🔴 `csv.reader` 對**真正的空行**回 `[]`、對「只有空白字元的行」回 `[' ']`
            #    ——兩種都要跳（實測 pandas 兩種都跳）。R3 三家獨立命中：漏了 `[]` 這半
            #    ⇒ 檔尾或中間留一個空行的合法 CSV 會被誤擋（且與前端相反，變成「前端收、後端擋」）。
            # 🔴 但 `,`（兩個空欄）**不是**空行：`csv.reader` 回 `['', '']`（2 欄），
            #    pandas 亦保留為一列空值 ⇒ 不得跳過，否則會把真實的資料列吃掉。
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if header_width is None:
                header_width = len(row)
                continue
            if len(row) != header_width:
                bad.append((i, len(row)))                   # i＝含標頭之列序（1-based 資料列＝i）
                if len(bad) >= 3:
                    break
        if bad:
            detail = "、".join(f"第 {r} 列（{w} 欄）" for r, w in bad)
            raise EventImportRejectedError(EventImportRejected(
                kind="parse_error",
                message=(f"CSV 欄數不齊：標頭 {header_width} 欄，但 {detail} 不同。"
                         "欄數不齊會讓解析結果與你看到的不一致（多出的欄可能被靜默丟棄或整列錯位），"
                         "故一律拒收；請先修正檔案"),
            ))

    def _read_csv_chunks(self, content: bytes):
        """CSV 分塊讀取之**唯一**入口（`parse_upload` 與對映層共用同一 reader 參數）。

        🔴 **欄數比標頭多的列一律 fail-closed**（R1 三家共提；grok 實跑）：
        pandas 預設會把第一欄當 index、**整列左移且零 warning** ——標頭五欄、資料六欄時
        `label` 讀到的是隔壁欄的值（實測 0 翻成 1），使用者在確認畫面看到的筆數與後端 ingest 不同。
        `index_col=False` 可修正對位，但 pandas 改為**丟棄多出的欄並只發 ParserWarning**
        ——那仍是靜默資料遺失，故一併升為例外，由呼叫端轉 `parse_error` 拒收。
        `on_bad_lines="error"` **無效**（實測仍左移），不要改用它。

        分層：**主要守衛＝上面的 `_assert_uniform_row_widths()`**（規則單一、與 pandas 版本無關，
        長列短列同一條）；
        本層之 `index_col=False` ＋ ParserWarning 升例外為**後備**——萬一 `csv` 標準庫與 pandas
        對某個引號形態 tokenize 不同，仍不會退回靜默左移。
        🔴 後備層**刻意沒有專屬 mutation**：主要守衛會先攔下同一批輸入，任何只拆後備層的變異
        都錄不到紅（空紅集合）。要證明後備層仍有作用，見 mutation `1.2-M6`（兩層一起拆）。
        """
        self._assert_uniform_row_widths(content)
        with warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.ParserWarning)
            for chunk in pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False,
                                     chunksize=self.CSV_CHUNK_ROWS, index_col=False):
                yield chunk

    # ---- 欄位對映層（GAP-3 UX Task 1.2） ----
    @staticmethod
    def _binary_label(raw: object) -> Optional[int]:
        """label 儲存格 → 0/1；**不猜**（True/yes/Y 等一律不接受，回 None ⇒ 對映層之 `label_not_binary` reason）。"""
        s = str(raw).strip()
        return int(s) if s in ("0", "1") else None

    def csv_records_from_mapping(
        self,
        content: bytes,
        column_mapping: Dict[str, str],
        batch_defaults: Optional[Dict[str, object]] = None,
    ) -> Tuple[List[Dict[str, object]], List[str]]:
        """CSV ＋ 使用者欄名對映 → 契約記錄（Task 1.2）。

        🔴 **只做欄位對映**：schema 檢核與落檔一律由呼叫端轉呼 `import_records`（與 JSON 路徑同一函式物件），
        本方法**不得**內含任何契約檢核。此處只擋三件對映層自身的事——
        `mapping_missing`／`column_not_found`／`label_not_binary`
        （字面由 `EventSamplePipeline.mapping_failure_reasons()` 自契約封閉集合取得，本層不複列）。

        Returns:
            (records, warnings)：warnings 列出**未對映而被忽略**之 CSV 欄（不靜默丟棄）。
        """
        if len(content) > self.MAX_FILE_SIZE:
            raise EventImportRejectedError(EventImportRejected(kind="parse_error", message=f"檔案超過 {self.MAX_FILE_SIZE} bytes"))

        mapping = {str(k).strip(): str(v).strip() for k, v in (column_mapping or {}).items() if str(v).strip()}
        defaults = dict(batch_defaults or {})
        if not mapping:
            raise EventImportRejectedError(EventImportRejected(
                kind="contract_violation",
                message="未提供 column_mapping：CSV 欄名與契約欄名之對應須由使用者顯式指定，不做任何預設對映（A-4′）",
                failures=[EventImportFailure(row=None, event_id=None, field=None, reason=self._mapping_reasons["mapping_missing"],
                                             message="column_mapping 為空；請逐項指定 {契約欄名: CSV 欄名}")],
            ))
        if "label" not in mapping and defaults.get("label") is None:
            raise EventImportRejectedError(EventImportRejected(
                kind="contract_violation",
                message="column_mapping 未指定 label 欄：正反例答案欄是本次匯入之核心宣告，不得由平台猜測",
                failures=[EventImportFailure(row=None, event_id=None, field="label", reason=self._mapping_reasons["mapping_missing"],
                                             message="column_mapping 缺 'label'；請指定哪一個 CSV 欄是你標好的正反例")],
            ))

        label_src = mapping.get("label")
        records: List[Dict[str, object]] = []
        bad_label_rows: List[Tuple[int, str]] = []
        header: Optional[List[str]] = None
        row_base = 0
        try:
            # 分塊：一次只持有一個 chunk（與 parse_upload 同一 reader、同一記憶體特性）
            for chunk in self._read_csv_chunks(content):
                if header is None:
                    header = [str(c) for c in chunk.columns]
                    missing = [(field, src) for field, src in mapping.items() if src not in header]
                    if missing:
                        raise EventImportRejectedError(EventImportRejected(
                            kind="contract_violation",
                            message=f"{len(missing)} 個對映指向 CSV 不存在之欄（檔案標頭＝{header}）",
                            failures=[EventImportFailure(row=None, event_id=None, field=field,
                                                         reason=self._mapping_reasons["column_not_found"],
                                                         message=f"契約欄 {field!r} 對映到 CSV 欄 {src!r}，但檔案標頭沒有這個欄名")
                                      for field, src in missing],
                        ))
                if label_src is not None:
                    for offset, raw in enumerate(chunk[label_src].tolist()):
                        if str(raw).strip() != "" and self._binary_label(raw) is None:
                            bad_label_rows.append((row_base + offset, str(raw)))
                sub = pd.DataFrame({field: chunk[src] for field, src in mapping.items()})
                records.extend(self._csv_rows_to_records(sub))
                row_base += len(chunk)
        except EventImportRejectedError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EventImportRejectedError(EventImportRejected(kind="parse_error", message=f"解析失敗：{exc}")) from exc

        if header is None:
            raise EventImportRejectedError(EventImportRejected(kind="parse_error", message="CSV 無資料列"))

        if bad_label_rows:
            shown = bad_label_rows[:3]
            raise EventImportRejectedError(EventImportRejected(
                kind="contract_violation",
                message=(f"label 欄 {label_src!r} 非二元 0/1：{len(bad_label_rows)} 列不是 '0' 或 '1'（不猜、不轉換）"),
                failures=[EventImportFailure(row=r, event_id=None, field="label", reason=self._mapping_reasons["label_not_binary"],
                                             message=f"列 {r} 之 label 值 {v!r} 不是 '0' 或 '1'")
                          for r, v in shown],
            ))

        ignored = [c for c in header if c not in set(mapping.values())]
        warnings = ([f"未對映而忽略之 CSV 欄（{len(ignored)}）：{ignored}"] if ignored else [])
        return records, warnings

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
    # ---- 答案窗宣告（GAP-3 UX Task 1.9／1.11；判定與投影唯一實作在 momentum，本層只轉呼與轉 4xx） ----
    ON_MISSING_REJECT = "reject"
    ON_MISSING_BLOCK = "block"

    @staticmethod
    def file_columns(content: bytes, filename: str) -> List[str]:
        """CSV 首列欄名（含未對映欄）；非 CSV 回 `[]`。

        🔴 只供①預設宣告值②引用欄之候選集合——**不**做任何契約檢核（V-3：檢核唯一實作在 momentum）。
        """
        if not filename or not str(filename).lower().endswith((".csv", ".txt")):
            return []
        head = content.split(b"\n", 1)[0].decode("utf-8-sig", errors="replace")
        return [c.strip().strip('"').strip("'").strip() for c in head.split(",") if c.strip()]

    # ---- 對映 provenance（GAP-3 UX Task 1.6；只記錄，不參與任何計算） ----
    #: `mapping_provenance.confirmed_at_source` 之兩值——伺服器時間**不得**冒充使用者確認時間。
    CONFIRMED_AT_CLIENT = "client_declared"
    CONFIRMED_AT_SERVER = "server_received"
    #: `mapping_provenance.event_id_source` 之兩值（R-B2-1：秒級 t0 之 ID 由後端依契約模板產生）。
    EVENT_ID_FROM_COLUMN = "csv_column"
    EVENT_ID_DERIVED = "derived_from_template"
    @staticmethod
    def _parse_iso_utc(text: str) -> Optional[datetime]:
        """UTC ISO-8601 字面 → aware datetime；不是合法 UTC 時刻回 `None`。

        🔴 **不得用 regex 代替日期解析**（R2 `CODEX-R2-P2-03` 實測）：形狀對但**不存在**的時刻
        （`2026-02-30T25:61:61Z`）會通過 regex，而合法之 `+00:00` 反而被擋。
        `Z` 與 `+00:00` 視為同義（皆為 UTC）；非零位移一律拒——本欄語意即「UTC 時刻」。
        """
        raw = str(text).strip()
        try:
            parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            return None
        return parsed

    @staticmethod
    def _batch_source_file_digest(
        records: List[Dict[str, object]], batch_defaults: Optional[Dict[str, object]],
    ) -> Optional[str]:
        """本批之 `source_file_digest` 單一值；**批內不一致或缺值 ⇒ `None`**（＝無法對證來源）。

        🔴 回 `None` 不在本函式報錯：由 `mapping_provenance` 之契約驗證以契約之「缺必填欄」
        reason fail-closed（reason 字面住契約，本層不複列）。
        列自帶值優先、`batch_defaults` 補缺——與 `validate` 之語意一致。
        """
        default = (batch_defaults or {}).get("source_file_digest")
        seen: set = set()
        for r in records:
            raw = r.get("source_file_digest")
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                raw = default
            if raw is None:
                return None
            text = str(raw).strip()
            if not text:
                return None
            seen.add(text)
        return seen.pop() if len(seen) == 1 else None

    def _derive_event_ids(
        self, records: List[Dict[str, object]], batch_defaults: Optional[Dict[str, object]],
    ) -> int:
        """依契約 `event_id_template` 之**唯一實作**逐列產生 `event_id`（解除殘留 `R-B2-1`）。

        🔴 呼叫時機必須在 `normalize_t0_units()` **之後**——秒級 t0 的摩擦正是「t0 被換算成毫秒，
        使用者手寫的 ID 還是秒版」。三欄任一缺值之列**原樣保留**（不猜），由契約層逐列拒。
        🔴 公式不在本層：轉呼 `EventSamplePipeline.canonical_event_id()`（R3 出口），禁手寫第二份。
        """
        defaults = batch_defaults or {}
        derived = 0
        for r in records:
            symbol = r.get("symbol") if r.get("symbol") not in (None, "") else defaults.get("symbol")
            timeframe = r.get("timeframe") if r.get("timeframe") not in (None, "") else defaults.get("timeframe")
            t0 = r.get("t0") if r.get("t0") not in (None, "") else defaults.get("t0")
            if symbol in (None, "") or timeframe in (None, "") or not isinstance(t0, int):
                continue
            r["event_id"] = self._pipeline.canonical_event_id(
                symbol, timeframe, t0, contract=self._contract)
            derived += 1
        return derived

    def _mapping_provenance(
        self, records: List[Dict[str, object]], batch_defaults: Optional[Dict[str, object]], *,
        column_mapping: Dict[str, object], source_file_name: Optional[str],
        confirmed_at: Optional[str], imported_at: str,
        source_digest_verified: bool, event_id_source: str,
    ) -> Dict[str, object]:
        """Task 1.6：組出對映 provenance 並經契約驗證；不合規 ⇒ 拒收（落檔數 0）。

        四項＝`column_mapping`／來源檔名／`source_file_digest`／確認時間，外加三個**誠實揭露**欄：
        `source_digest_verified`（digest 是否真的以位元組對證過）、`event_id_source`
        （ID 是使用者欄位還是後端依契約模板產生）、`confirmed_at_source`（確認時間是誰給的）。
        少了它們，receipt 讀起來會像「已對證／使用者確認過」而其實不是（R1 codex BLOCKING）。
        """
        declared_at = str(confirmed_at).strip() if confirmed_at else ""
        if declared_at and self._parse_iso_utc(declared_at) is None:
            raise EventImportRejectedError(EventImportRejected(
                kind="contract_violation",
                message=("mapping_confirmed_at 須為**存在的** UTC 時刻（`…Z` 或 `+00:00` 皆可，"
                         f"如 2026-08-25T09:30:00Z）；收到 {declared_at!r}。"
                         "本欄是使用者聲明之時刻、非可信時鐘，但仍須是可解析的真實時刻"),
                detail={"field": "mapping_provenance.confirmed_at", "received": declared_at},
            ))
        provenance: Dict[str, object] = {
            "column_mapping": {str(k): str(v) for k, v in (column_mapping or {}).items()},
            "source_file_name": str(source_file_name or ""),
            "source_digest_verified": bool(source_digest_verified),
            "event_id_source": str(event_id_source),
            "confirmed_at": declared_at or imported_at,
            "confirmed_at_source": self.CONFIRMED_AT_CLIENT if declared_at else self.CONFIRMED_AT_SERVER,
        }
        digest = self._batch_source_file_digest(records, batch_defaults)
        if digest is not None:
            provenance["source_file_digest"] = digest
        outcome = self._pipeline.validate_receipt_values(
            "mapping_provenance", provenance, contract=self._contract)
        if not outcome["ok"]:
            raise EventImportRejectedError(EventImportRejected(
                kind="contract_violation",
                message=("對映 provenance 不合契約（Task 1.6：無法對證『這批是依哪一欄、哪個檔宣告的』）；"
                         "逐欄 reason 見 failures"),
                failures=[EventImportFailure(row=None, event_id=None, field=str(f.get("field")),
                                             reason=str(f.get("reason")),
                                             message="mapping_provenance 之欄位缺值或型別不符")
                          for f in outcome["failures"]],
            ))
        return provenance

    def _resolve_lookahead(
        self, records: List[Dict[str, object]], *, data_columns: List[str],
        declaration: Optional[Dict[str, object]], on_missing: str,
    ) -> Dict[str, object]:
        """轉呼 pipeline 出口；不合規 ⇒ `EventImportRejectedError`（落檔數 0）。"""
        out = self._pipeline.resolve_lookahead_declaration(
            records, data_columns=data_columns, declaration=declaration, on_missing=on_missing)
        if not out["ok"]:
            raise EventImportRejectedError(EventImportRejected(
                kind=str(out["kind"]), message=str(out["message"]), detail=dict(out.get("detail") or {})))
        return dict(out["receipt"])

    def lookahead_declaration_preview(
        self, content: bytes, filename: str, records: List[Dict[str, object]],
        batch_defaults: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        """宣告 UI 之預填資料（Task 1.9 ①：預設值＝檔內最大可用 horizon，逐 tf）。"""
        cols = self.file_columns(content, filename)
        view = [{**dict(batch_defaults or {}), **r} for r in records]
        tfs = sorted({str(r["timeframe"]) for r in view if r.get("timeframe") is not None})
        receipt = self._resolve_lookahead(
            view, data_columns=cols, declaration=None, on_missing=self.ON_MISSING_BLOCK)
        return {
            "timeframes": tfs,
            "data_columns": cols,
            "default_window_bars": receipt["default_window_bars"],
            "requires_declaration": receipt["requires_declaration"],
            "referenced_columns": receipt["referenced_columns"],
        }

    def import_records(
        self, records: List[Dict[str, object]], *, source_name: Optional[str], upload_bytes: Optional[bytes],
        validate_only: bool, verify_source_digest: bool = False, source_bytes: Optional[bytes] = None,
        batch_defaults: Optional[Dict[str, object]] = None, extra_warnings: Optional[List[str]] = None,
        lookahead_declaration: Optional[Dict[str, object]] = None, data_columns: Optional[List[str]] = None,
        on_missing_declaration: Optional[str] = None,
        column_mapping: Optional[Dict[str, object]] = None, mapping_confirmed_at: Optional[str] = None,
        derive_event_id: bool = False,
    ) -> EventImportResponse:
        """upload_bytes：事件檔內容（記 `upload_sha256` 供 provenance）。
        source_bytes：契約所指之**來源檔**位元組（CODEX-R2-P1-03）；`verify_source_digest=True` 時以此逐列對證
        `source_file_digest`。**必須是與事件檔相異之檔**——事件檔含自身 digest 欄，自我對證恆不自洽
        （路由層以 `source_file_must_differ_from_event_file`／`source_file_required_for_verify` 擋在前面；CODEX-R4-P1-01）。"""
        # GAP-3 UX Task 1.4：t0 單位偵測（CSV／JSON **共用**同一函式物件，經 pipeline 出口；R3）。
        # 判不出者原樣保留 ⇒ 下方 validate 以契約既有之單位 reason 逐列拒，不猜預設值。
        self._pipeline.normalize_t0_units(records, contract=self._contract)
        # 殘留 `R-B2-1`：秒級 t0 之 `event_id` 摩擦。使用者顯式要求時（opt-in，預設關 ⇒ A-4′ 不推斷），
        # 於**單位正規化之後**由契約之唯一實作逐列產生 ms 版 ID——不改 upload bytes，
        # 故 `upload_sha256` 與 Task 1.6 之來源 provenance 仍指向使用者實際上傳的那個檔。
        if derive_event_id:
            self._derive_event_ids(records, batch_defaults)
        columns = sorted({k for r in records for k in r.keys()}) if records else []
        if self.looks_legacy(columns):
            raise EventImportRejectedError(EventImportRejected(
                kind="legacy_schema_detected",
                message="偵測到舊三欄格式（symbol/timestamp/Positive_case）；新端點只收 event_import_contract 新 schema，不做靜默轉換",
                migration_hint=self.migration_hint(columns),
            ))
        # GAP-3 UX Task 1.9／1.11：答案窗宣告須在 validate **之前**解析——它會就地投影
        # `label_definition.window.horizon_bars`，而 label_start/end_ms 由該值導出。
        # 🔴 以 batch_defaults **填補缺值**後之視圖判定（與 validate 之語意一致：列自帶值優先）——
        #    否則對映路徑之 `label_definition`（含 filters）只住 defaults，引用欄會整批看不見。
        declaration_view = [{**dict(batch_defaults or {}), **r} for r in records]
        declaration_receipt = self._resolve_lookahead(
            declaration_view, data_columns=list(data_columns) if data_columns is not None else columns,
            declaration=lookahead_declaration,
            on_missing=on_missing_declaration or self.ON_MISSING_REJECT)
        verify_bytes = (source_bytes if source_bytes is not None else upload_bytes) if verify_source_digest else None
        df, failures = self._pipeline.validate(records, source_bytes=verify_bytes, batch_defaults=batch_defaults)
        digest = _hashlib.sha256(upload_bytes).hexdigest() if upload_bytes is not None else None
        if df is None:
            raise EventImportRejectedError(EventImportRejected(
                kind="contract_violation",
                message=f"{len(failures)} 筆契約違規（逐列 reason 見 failures；字面＝event_import_contract.json）",
                failures=[EventImportFailure(**{k: f.get(k) for k in ("row", "event_id", "field", "reason", "message")}) for f in failures],
                migration_hint=self.migration_hint(columns) if self.migration_hint(columns)["required_fields_absent"] else None,
            ))
        warnings: List[str] = list(extra_warnings or [])
        # Task 1.9 ③：宣告深度之投影**在同質檢查之後**才寫入（見 pipeline 出口 docstring）
        stored_records = df.to_dict("records")
        if declaration_receipt.get("lookahead_bars_declared"):
            self._pipeline.apply_lookahead_horizon_projection(
                stored_records, declaration_receipt["lookahead_bars_declared"])
        imported_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Task 1.6：對映路徑之 provenance——**在落檔之前**驗證（不合規 ⇒ 拒收，落檔數 0）。
        # JSON 直傳路徑無對映可追，不寫本 namespace。
        mapping_provenance = None
        if column_mapping:
            mapping_provenance = self._mapping_provenance(
                stored_records, batch_defaults, column_mapping=column_mapping,
                source_file_name=source_name, confirmed_at=mapping_confirmed_at, imported_at=imported_at,
                source_digest_verified=bool(verify_source_digest and source_bytes is not None),
                event_id_source=self.EVENT_ID_DERIVED if derive_event_id else self.EVENT_ID_FROM_COLUMN)
        import_id = None
        stored_path = None
        if not validate_only:
            import_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + _uuid.uuid4().hex[:8]
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "import_id": import_id, "source_name": source_name, "upload_sha256": digest,
                "source_digest_verified": bool(verify_source_digest),
                "source_file_sha256": _hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None,
                "imported_at": imported_at,
                "contract_version": str(self._contract.get("version")),
                "lookahead_declaration": declaration_receipt,
                "records": stored_records,
            }
            # 邊界②：只**補**本 namespace，不覆寫 payload 之任何既有欄。
            if mapping_provenance is not None:
                payload.setdefault("mapping_provenance", mapping_provenance)
            p = self.storage_dir / f"{import_id}.json"
            p.write_text(_json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str), encoding="utf-8")
            stored_path = str(p)
        return EventImportResponse(
            accepted=True, import_id=import_id, n_rows=len(records), n_valid=int(len(df)), failures=[],
            warnings=warnings, upload_sha256=digest, source_digest_verified=bool(verify_source_digest),
            contract_version=str(self._contract.get("version")), stored_path=stored_path,
            lookahead_declaration=declaration_receipt,
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

    def _stored_declaration(self, import_id: str) -> Optional[Dict[str, object]]:
        """落檔之答案窗宣告 receipt（Task 1.9／1.12）。

        🔴 舊批（Task 1.9 上線前落檔）無此鍵 ⇒ 回 `None`，由 momentum 側判定為**不封鎖**
        （使用者 2026-08-05「面向未來不溯及既往」；不把舊資料補回新規則）。
        """
        if not import_id or "/" in import_id or ".." in import_id:
            return None
        p = self.storage_dir / f"{import_id}.json"
        if not p.is_file():
            return None
        val = self._load(p).get("lookahead_declaration")
        return dict(val) if isinstance(val, dict) else None

    def get_import(self, import_id: str) -> Optional[EventImportDetailResponse]:
        if not import_id or "/" in import_id or ".." in import_id:
            return None
        p = self.storage_dir / f"{import_id}.json"
        if not p.is_file():
            return None
        payload = self._load(p)
        return EventImportDetailResponse(summary=self._summary(payload), records=list(payload.get("records") or []))


    @staticmethod
    def _assert_scope_embargo_expressible(declaration: Optional[Dict[str, object]]) -> None:
        """per-symbol 下界不一致時 fail-closed（SPEC §D-3′-a(ii) 明令禁止之作法的守門）。

        現行 `split_events` 只吃 scalar `embargo_ms`；當各 symbol 的宣告下界**相同**（含單一 symbol）
        時，scalar 與 per-scope 等價、可安全套用。一旦不同就**無法表達**——
        取 max 即過度 purge、取 min 即洩漏 ⇒ 兩者皆錯，故拒絕分析而非二選一。
        """
        bounds = (declaration or {}).get("embargo_ms_by_symbol") or {}
        distinct = {int(v) for v in bounds.values()}
        if len(distinct) <= 1:
            return
        raise ValueError(
            "本批各標的之答案窗宣告導出**不同**的 purge 下界"
            f"（{ {k: int(v) for k, v in bounds.items()} }），"
            "而現行切分只接受單一 embargo：取最大會對窗較小的標的過度 purge、取最小會洩漏，"
            "兩者皆為錯誤，故拒絕分析（fail-closed）。"
            "逐 symbol 的隔離寬度（EventSplitConfig.embargo_ms_by_symbol）之唯一實作與驗收"
            "由 SPEC 鎖在 Task 7.0b；在那之前請將此批依 timeframe 拆成各自同質的批次再分析"
        )

    # ---- 分析（B5.2 兩表資料源；統計全在 momentum，本層只組 request/response） ----
    def analyze(self, import_id: str, req) -> Optional[Dict[str, object]]:
        from api.utils.json_serializer import sanitize_for_json

        detail = self.get_import(import_id)
        if detail is None:
            return None
        records = detail.records
        declaration = self._stored_declaration(import_id)
        symbols = sorted({str(r["symbol"]) for r in records})
        tfs = sorted({str(r["timeframe"]) for r in records})
        # 🔴 R2（`CODEX-R2-P1-01`）：SPEC §D-3′-a(ii)「明令禁止」逐字寫著
        #    「以單一 batch scalar `embargo_ms` 冒充 per-scope 下界」——切分本就逐 symbol，
        #    取全批 max 會對窗較小之 symbol **過度 purge**（§C0：過度 purge 亦是錯誤）。
        #    per-symbol API（`EventSplitConfig.embargo_ms_by_symbol`）之唯一實作與驗收
        #    由 SPEC 鎖在 **Task 7.0b ⑨**，本批不提前做半套（雙源正是本 epic 反覆受傷處）。
        #    ⇒ B3 之立場：**能表達就套用，不能表達就拒絕**，絕不靜默折疊。
        #    檢查刻意排在載 bars **之前**：不可表達的下界不該先做任何工作。
        self._assert_scope_embargo_expressible(declaration)
        bars = self._pipeline.bars_from_kline_cache(symbols, tfs)
        # 🔴 Task 1.12（L3）：深度不可證之批**不進切分**，改走 event-study-only executor。
        #    分派在此發生 ⇒ `split_events` 對該批**根本不會被呼叫**（非「呼叫後再擋」）。
        split_blocked = self._pipeline.lookahead_split_blocked(declaration)
        if split_blocked:
            res = self._pipeline.run_event_study_only_with_params(records, bars)
            embargo_applied: Optional[int] = None
            embargo_source = "not_applicable_event_study_only"
        else:
            # 🔴 R1（`CODEX-R1-P1-03`）：宣告值必須**真的接到 split**，否則 `embargo_ms_by_symbol`
            #    只是沒人用的數字。原版把 `req.embargo_ms`（預設 None）直傳 ⇒ `split_events` 退回
            #    `label 窗最大值`；而 `label_return_mode="open_to_close"` 之 label 窗**不隨 horizon 變**
            #    ⇒ 宣告 20 根、實際只隔 1 根＝洩漏。此處把宣告投影當**下界**套上去。
            #    保守方向（往上調）永遠允許，故取 max 而非拒收。
            # 🔴 R2：此處之 `max` 只在**各 symbol 下界皆相同**時才會執行到——
            #    不同值已由 `_assert_scope_embargo_expressible` 在上方擋掉，故不是「全批 max 冒充 per-scope」。
            declared_lb = max((int(v) for v in (declaration or {}).get("embargo_ms_by_symbol", {}).values()), default=0)
            requested = int(req.embargo_ms) if req.embargo_ms is not None else 0
            embargo_applied = max(requested, declared_lb) or None
            embargo_source = ("lookahead_declaration_lower_bound"
                              if declared_lb and declared_lb > requested else
                              "request" if requested else "label_window_max")
            res = self._pipeline.run_with_params(
                records, bars, test_fraction=float(req.test_fraction), embargo_ms=embargo_applied,
                tier_min_test_events=int(req.tier_min_test_events),
            )
        tables = self._pipeline.analyze_tables(res, bars, horizons=tuple(int(h) for h in req.horizons),
                                               seed=int(req.seed), n_boot=int(req.n_boot))
        payload = {
            "import_id": import_id,
            "lookahead_declaration": declaration,
            "capability": ({"split": "unavailable", "reason": self._pipeline.split_blocked_capability_reason()}
                           if split_blocked else {"split": "ok"}),
            "embargo": {"applied_ms": embargo_applied, "source": embargo_source},
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
