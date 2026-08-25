"""GAP-3 事件匯入 request/response 殼（Task B5.1）。

只做透傳：欄位名／枚舉／reason 字面**不**在此複列（SoT＝`momentum/Analysis/contracts/event_import_contract.json`；
驗證唯一實作＝`momentum/Analysis/event_samples/import_contract.validate_event_import`，R7）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventImportFailure(BaseModel):
    """逐列拒收理由（字面來自契約檔）。"""

    row: Optional[int] = Field(None, description="列號（批次級失敗為 null）")
    event_id: Optional[Any] = Field(None, description="事件 ID（缺則 null）")
    field: Optional[str] = Field(None, description="欄位（批次級失敗為 null）")
    reason: str = Field(..., description="契約 reason 字面")
    message: Optional[str] = Field(
        None,
        description=("補充訊息（多數 reason 為 null）。`heterogeneous_rows_in_batch` 以此列出**前 3 個**"
                     "衝突列號與欄名（Task 1.8）；字面仍以 `reason` 為準"),
    )


class EventImportJsonRequest(BaseModel):
    """JSON 記錄列表匯入。"""

    records: List[Dict[str, Any]] = Field(..., description="事件記錄（欄位依 event_import_contract.json）")
    validate_only: bool = Field(False, description="僅驗證不落檔")
    source_name: Optional[str] = Field(None, description="來源名稱（供 provenance；選填）")
    batch_defaults: Optional[Dict[str, Any]] = Field(
        None,
        description=("批次預設（GAP-3 UX Task 1.8）：{契約欄名: 值}，**只填補缺值、不覆蓋列自帶值**。"
                     "列間自帶互斥值時仍拒（heterogeneous_rows_in_batch）"),
    )
    verify_source_digest: bool = Field(
        False,
        description=("JSON 端點**不支援**（傳 true ⇒ 400）：契約 source_file_digest 指使用者原始來源檔之 sha256，"
                     "而本端點的位元組是 request body 本身，兩者必然不符（CODEX-R2-P1-03）。"
                     "需對證請改用檔案端點並上傳該來源檔。"),
    )


class EventImportResponse(BaseModel):
    """匯入結果；拒收走 4xx（本模型只在 2xx 回）。"""

    accepted: bool
    import_id: Optional[str] = Field(None, description="落檔識別（validate_only ⇒ null）")
    n_rows: int
    n_valid: int
    failures: List[EventImportFailure] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    upload_sha256: Optional[str] = Field(None, description="上傳內容 sha256（provenance；非契約 source_file_digest）")
    source_digest_verified: bool = Field(False, description="是否以上傳內容對證契約 source_file_digest（verify_source_digest）")
    contract_version: Optional[str] = None
    stored_path: Optional[str] = None
    lookahead_declaration: Optional[Dict[str, Any]] = Field(
        None,
        description=("GAP-3 UX Task 1.9／1.11／1.12 之答案窗宣告 receipt："
                     "requires_declaration／referenced_columns／default_window_bars／declared_window_bars／"
                     "lookahead_bars_declared（逐 tf map）／acknowledged_unverifiable／embargo_ms_by_symbol／split_blocked。"
                     "🔴 深度語意住 lookahead_bars_declared；label_definition.window.horizon_bars 之 1 只是 serialization floor"),
    )


class EventImportRejected(BaseModel):
    """4xx detail 形狀（顯式、逐列 reason；禁 silent coerce）。"""

    kind: str = Field(..., description="legacy_schema_detected | new_schema_on_legacy_endpoint | contract_violation | parse_error")
    message: str
    failures: List[EventImportFailure] = Field(default_factory=list)
    migration_hint: Optional[Dict[str, Any]] = None
    detail: Optional[Dict[str, Any]] = Field(
        None, description="拒收之結構化補充（如 Task 1.9 之 default_window_bars／lowered_timeframes，供 UI 預填）")


class EventImportSummary(BaseModel):
    import_id: str
    source_name: Optional[str]
    upload_sha256: str
    imported_at: str
    n_events: int
    symbols: List[str]
    timeframes: List[str]
    direction: Optional[str]
    scenario: Optional[str]


class EventImportListResponse(BaseModel):
    total: int
    imports: List[EventImportSummary]


class EventImportDetailResponse(BaseModel):
    summary: EventImportSummary
    records: List[Dict[str, Any]]


class EventAnalyzeRequest(BaseModel):
    """對一筆匯入跑 validate→align→dedupe→split＋兩張表（純透傳；統計在 momentum）。"""

    horizons: List[int] = Field(default_factory=lambda: [1, 2, 4], description="事件後報酬表 horizon（bars）")
    n_boot: int = Field(300, ge=10, le=5000)
    seed: int = Field(20260820)
    test_fraction: float = Field(0.3, gt=0.0, lt=1.0)
    embargo_ms: Optional[int] = None
    tier_min_test_events: int = Field(1, ge=0)


class EventAnalyzeResponse(BaseModel):
    import_id: str
    summary: Dict[str, Any] = Field(..., description="pipeline summary（記帳／去重／切分）")
    align_failures: List[Dict[str, Any]] = Field(default_factory=list)
    tables: Dict[str, Any] = Field(..., description="event_forward_return_table / binary_discrimination_table / all_bars_evaluation（含 capability_status／reason）")
    event_timestamps: List[int] = Field(default_factory=list, description="對齊成功事件之 t0，**epoch ms**（契約單位；非 IC 秒）")
    event_timestamps_ic_seconds: List[int] = Field(default_factory=list, description="同上換算為 bar open **秒**（IC 主線 event_timestamps 單位；GROK-R1-P2-02）")
    lookahead_declaration: Optional[Dict[str, Any]] = Field(
        None, description="GAP-3 UX Task 1.9：該批落檔之答案窗宣告 receipt（舊批為 null）")
    capability: Dict[str, Any] = Field(
        default_factory=dict,
        description=("GAP-3 UX Task 1.12：`split` 為 `ok`／`unavailable`；`unavailable` 時 `reason` 取自契約之 "
                     "capability_unavailable_reasons，該批只走 event-study-only（未執行切分與條件 IC）"))
    embargo: Dict[str, Any] = Field(
        default_factory=dict,
        description=("GAP-3 UX Task 1.9：實際送進切分的 embargo（`applied_ms`）與其來源（`source`）。"
                     "🔴 宣告深度為**下界**：`source=lookahead_declaration_lower_bound` 表示請求值低於宣告深度而被提高"))
