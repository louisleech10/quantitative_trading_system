"""
案例相關API路由

提供案例導入、批量下載等API端點
"""

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, BackgroundTasks, Query, Response
from typing import Optional

from ..models.case_models import (
    CaseImportRequest,
    CaseImportResponse,
    BatchDownloadRequest,
    DownloadProgress,
    DownloadResult,
    CaseListResponse
)
from ..services.case_import_service import (
    EventImportRejectedError,
    get_case_import_service,
    get_event_import_service,
)
from ..models.event_import_models import (
    EventAnalyzeRequest,
    EventAnalyzeResponse,
    EventImportDetailResponse,
    EventImportJsonRequest,
    EventImportListResponse,
    EventImportRejected,
    EventImportResponse,
    LookaheadDeclarationPreviewColumnsRequest,
    RandomControlCompareRequest,
    RandomControlCompareResponse,
    RandomControlGenerateRequest,
)
from ..services.ic_analysis_service import ICAnalysisService
from ..services.batch_download_service import get_batch_download_service
from ..utils.case_storage import get_case_storage_manager
from ..core.logging import get_logger

logger = get_logger("api.routes.case")

router = APIRouter(prefix="/api/v1", tags=["Case Management"])

# 獲取服務實例
case_import_service = get_case_import_service()
batch_download_service = get_batch_download_service()
case_storage = get_case_storage_manager()


# DEPRECATED（2026-09-02 使用者裁定「註解之後移除」，票 KLINE-1）：舊三欄「導入案例」→ 批量 K 線下載鏈之入口。
# 寫的是 data_cache/kline_cache.h5；Feature Factory／IC／事件分析只讀 data_cache/feature_klines/，兩者互不相干。
# 本註解不改任何行為；移除另走票。同檔之 /case/import-events*／/case/events*／lookahead-* 為事件契約，**必留**。
@router.post("/case/import", response_model=CaseImportResponse)
async def import_cases_from_csv(
    file: UploadFile = File(...),
    default_timeframe: Optional[str] = Query("1h"),
    validate_only: bool = Query(False),
    force_clear: bool = Query(False)
):
    """
    上傳CSV/Excel文件並導入案例

    Args:
        file: CSV或Excel文件
        default_timeframe: 預設時間框架（CSV缺少時使用）
        validate_only: 僅驗證不導入
        force_clear: 導入前強制清空所有舊案例（需用戶確認）

    Returns:
        CaseImportResponse: 導入結果
            - 如果有現有案例且force_clear=False，返回need_confirmation=True
            - 如果force_clear=True，清空舊案例後導入

    Raises:
        HTTPException: 導入失敗
    """
    logger.info(
        f"Receiving case import request: {file.filename} "
        f"(default_timeframe={default_timeframe}, validate_only={validate_only}, force_clear={force_clear})"
    )

    # 檢查文件格式
    filename = file.filename
    if not filename.endswith(('.csv', '.xlsx', '.xls', '.txt')):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {filename}. "
                   f"Supported formats: .csv, .xlsx, .xls, .txt"
        )

    # 讀取文件內容
    file_content = await file.read()

    # GAP-3 B5.1 legacy adapter：新 schema 檔誤投舊端點 ⇒ 顯式 400（禁 silent coerce）；放在 try 外免被泛捕成 500
    _header = _csv_header(file_content, filename)
    if _header is not None and get_event_import_service().looks_new_schema(_header):
        raise HTTPException(status_code=400, detail=EventImportRejected(
            kind="new_schema_on_legacy_endpoint",
            # 🔴 訊息是**給使用者讀的**：不寫施工票號、不寫 API 路徑
            #    （2026-09-02 使用者：「以後使用者哪知道什麼是 GAP3？」）。
            #    端點路徑改放結構化 `detail.endpoint`——除錯與前端導向仍拿得到，
            #    但不出現在畫面文字裡。
            message="這是事件契約格式的檔（含 event_id／t0／label…）；這一區只收舊三欄格式"
                    "（symbol／timestamp／Positive_case）。請改用「匯入事件」那一區上傳。",
            detail={"endpoint": "/api/v1/case/import-events", "ui_section": "匯入事件"},
        ).model_dump())

    try:
        # 導入案例（支持force_clear參數）
        result = case_import_service.import_from_file(
            file_content=file_content,
            filename=filename,
            default_timeframe=default_timeframe,
            validate_only=validate_only,
            force_clear=force_clear
        )

        logger.info(
            f"Case import completed: {result.imported_cases}/{result.total_rows} imported, "
            f"{len(result.errors)} errors"
        )

        return result

    except ValueError as e:
        logger.error(f"Validation error during case import: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error during case import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


def _csv_header(content: bytes, filename: str) -> Optional[list]:
    """只讀 CSV 首列鍵名供 schema 偵測（不做任何契約檢查）。"""
    if not filename or not filename.lower().endswith((".csv", ".txt")):
        return None
    try:
        first = content.split(b"\n", 1)[0].decode("utf-8-sig", errors="replace")
    except Exception:  # noqa: BLE001
        return None
    return [c.strip().strip('"') for c in first.split(",")]


def _rejected(exc: EventImportRejectedError, *, svc=None, content=None) -> HTTPException:
    """拒收 → HTTPException（**三條上傳路徑之唯一訊息組裝點**）。

    GAP-3 UX Task 5.1：帶了 `svc`＋`content` 時，若該內容其實是 `/search` 一併下載的
    來源對證檔（`*.source.json`），在訊息**尾端追加**正解。
    🔴 只追加訊息：`kind`（reason 字面）與狀態碼**都不變**——下游依 reason 判斷，
      且判別為來源檔**不得**自動改走 `source_file` 流程（靜默轉換＝契約禁止）。
    🔴 判準與提示字面皆非本層自寫，經 service → pipeline 出口取 momentum 之唯一實作（R3）。
    """
    detail = exc.payload.model_dump()
    hint = svc.source_file_misupload_hint(content) if (svc is not None and content is not None) else None
    if hint:
        detail["message"] = f"{detail['message']}；{hint}"
    return HTTPException(status_code=422 if exc.payload.kind == "contract_violation" else 400, detail=detail)


def _assert_source_file_usable(verify: bool, src_bytes: Optional[bytes], content: bytes) -> None:
    """`verify_source_digest` 之前置條件（JSON 與 CSV 對映**兩條路徑共用同一實作**）。

    🔴 不得為 CSV 路徑另寫一份——兩份必然漂移（V-3 之教訓）。
    """
    if verify and src_bytes is not None and src_bytes == content:
        # CODEX-R4-P1-01：事件檔內含 source_file_digest 欄，對自身取 sha256 恆不自洽 ⇒ 同檔對證在數學上不可能。
        # 直接以專屬 reason 拒（而非讓使用者收一堆 digest_mismatch），並指出正解＝另附來源檔。
        raise HTTPException(status_code=400, detail=EventImportRejected(
            kind="source_file_must_differ_from_event_file",
            message=("source_file 與事件檔位元組相同：事件檔含 source_file_digest 欄，對自身取 sha256 必不相符（自我指涉）。"
                     "請附**產生這些事件的來源檔**（/search 匯出者即同時下載的 *.source.json）；"
                     "若無來源檔可對證，請關閉 verify_source_digest"),
        ).model_dump())
    if verify and src_bytes is None:
        # 顯式引導：自我對證必然失敗，直接說清楚要傳什麼（而非讓使用者拿到一堆 digest_mismatch）
        raise HTTPException(status_code=400, detail=EventImportRejected(
            kind="source_file_required_for_verify",
            message=("verify_source_digest=true 需一併上傳 source_file（契約所指來源檔）；"
                     "事件檔本身含 source_file_digest 欄，對自己取 sha256 必然不符。"
                     "由 /search 匯出者：同時下載的 *.source.json 即為該來源檔"),
        ).model_dump())


# ---------------------------------------------------------------------------
# GAP-3 Task B5.1 — 新 schema 事件匯入（驗證唯一實作在 momentum/；本層透傳）
# ---------------------------------------------------------------------------
@router.post("/case/import-events", response_model=EventImportResponse)
async def import_events_file(
    file: UploadFile = File(..., description="事件檔（CSV／JSON，新 schema）"),
    source_file: Optional[UploadFile] = File(None, description="契約所指之『來源檔』；`verify_source_digest=true` 時以此檔位元組對證"),
    lookahead_declaration: Optional[str] = Form(
        None,
        description=('GAP-3 UX Task 1.9／1.11 之答案窗宣告：JSON 物件 '
                     '{"declared_window_bars": {timeframe: 非負整數（0 ＝未用未來資訊，須明填）}, "acknowledged_unverifiable": bool}。'
                     '🔴 逐 timeframe 各一值（單一輸入框套用全部 tf ⇒ 拒）；'
                     '低於檔內最大可用 horizon 須 acknowledged_unverifiable=true。'
                     'R 重開後每批一律須宣告（表單或列內攜帶皆無 ⇒ 拒收，落檔數 0）；引用驗不了的欄或調低須 acknowledged_unverifiable=true'),
    ),
    validate_only: bool = Query(False),
    verify_source_digest: bool = Query(
        False,
        description=("逐列對證 source_file_digest。**必須另附 `source_file`**（產生事件的來源檔）——事件檔含自己的 digest，"
                     "自我對證在數學上不可能（同檔 ⇒ 400 `source_file_must_differ_from_event_file`；未附 ⇒ 400 "
                     "`source_file_required_for_verify`）。由 /search 匯出者請上傳同時下載的 `*.source.json`（CODEX-R2-P1-03／R4-P1-01）"),
    ),
):
    """上傳 CSV/JSON（GAP-3 事件契約新 schema）。拒收 ⇒ 400（legacy／parse）或 422（契約違規，逐列 reason）。"""
    svc = get_event_import_service()
    content = await file.read()
    src_bytes = await source_file.read() if source_file is not None else None
    _assert_source_file_usable(verify_source_digest, src_bytes, content)
    try:
        records = svc.parse_upload(content, file.filename or "")
        return svc.import_records(records, source_name=file.filename, upload_bytes=content, validate_only=validate_only,
                                  verify_source_digest=verify_source_digest, source_bytes=src_bytes,
                                  lookahead_declaration=_form_json_dict("lookahead_declaration", lookahead_declaration) or None,
                                  data_columns=svc.file_columns(content, file.filename or "") or None)
    except EventImportRejectedError as exc:
        raise _rejected(exc, svc=svc, content=content)


@router.post("/case/import-events/json", response_model=EventImportResponse)
async def import_events_json(request: EventImportJsonRequest):
    """JSON 記錄列表匯入（同一 validator；`source_file_digest`＝canonical JSON sha256）。"""
    import json as _json

    svc = get_event_import_service()
    if request.verify_source_digest:
        # CODEX-R2-P1-03：JSON body ≠ 契約所指「來源檔」；開此旗標必然 digest_mismatch ⇒ 顯式拒，不做無意義比對
        raise HTTPException(status_code=400, detail=EventImportRejected(
            kind="verify_unsupported_on_json_endpoint",
            message=("JSON 端點不支援 verify_source_digest：契約 source_file_digest＝使用者原始來源檔 sha256，"
                     "本端點位元組為 request body，比對必然不符。請改用 /case/import-events 上傳該來源檔並帶 verify_source_digest=true"),
        ).model_dump())
    body = _json.dumps(request.records, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    try:
        # 🔴 R 重開（SPEC Task 1.11）：JSON 直傳**無宣告 UI**，其宣告＝列內 `lookahead_bars_declared`
        #    （Task 1.9′ 匯出時攜帶）；整批缺該欄 ⇒ **拒收**（R 前「落檔但 L3 封鎖」已刪，三家 R35 P0）。
        #    導出規則住 service（批內同值、每個出現之 tf 皆有鍵）。
        return svc.import_records(request.records, source_name=request.source_name, upload_bytes=body,
                                  validate_only=request.validate_only, verify_source_digest=request.verify_source_digest,
                                  batch_defaults=request.batch_defaults,
                                  carried_declaration_acknowledged=True)   # 殘留 R35-L2-ACK：只此路由自動視為已勾選
    except EventImportRejectedError as exc:
        raise _rejected(exc, svc=svc, content=body)


@router.post("/case/import-events/random-control", response_model=EventImportResponse)
async def import_events_random_control(request: RandomControlGenerateRequest):
    """`G3-D2` D5.3：依既有**觸發批**產一批隨機對照事件並落檔。

    🔴 **不新建 `api/routes/event_import.py`**（`D-001` D5.3；該檔不存在，新建會讓
    `/case/import-events*` 家族分裂成兩個路由檔）。落檔走**同一支** `import_records`
    ⇒ 同一 validator、同一儲存路徑、同一刪除範圍，無 profile 分裂。

    流程：讀觸發批 → 以同一支對齊實作取每事件之 `label_end_ms` → `sample_random_bars`
    → `import_records(records, random_control_spec=receipt)`。
    """
    svc = get_event_import_service()
    trigger = svc.get_import(request.event_import_id)
    if trigger is None:
        raise HTTPException(status_code=404,
                            detail=f"event import {request.event_import_id!r} not found")
    try:
        records, receipt = svc.build_random_control_batch(trigger, request.random_control_spec)
    except EventImportRejectedError as exc:
        raise _rejected(exc, svc=svc)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail={"kind": "bars_unavailable", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"kind": "pipeline_rejected", "message": str(exc)})
    try:
        return svc.import_records(
            records, source_name=f"random_control_of:{request.event_import_id}",
            upload_bytes=None, validate_only=False,
            random_control_spec=receipt,
            # 隨機批之列自帶 `lookahead_bars_declared`（深度＝答案窗長度），走列內宣告路徑。
            carried_declaration_acknowledged=True)
    except EventImportRejectedError as exc:
        raise _rejected(exc, svc=svc)


@router.post("/case/events/compare-random-control", response_model=RandomControlCompareResponse)
async def compare_random_control_batches(request: RandomControlCompareRequest):
    """`G3-D2` D5.3：觸發批 vs 隨機對照批之 prevalence 並排（規則身分閘四段）。

    🔴 **本端點是 R1 三家獨立命中之閉合**：`compare_random_control` 原本只有 service
    靜態方法、沒有任何 caller ⇒ 閘在測面綠、**產品面不可達**（與 B-D4「WS 不回填揭露欄」
    同型）。route 是唯一的取用路徑。

    🔴 **兩份 detail 由 route 撈好交進去**——`ic_analysis_service` 不得 import
    `case_import_service`（解耦 Rule 4：服務不互 import）。
    """
    svc = get_event_import_service()
    trigger = svc.get_import(request.trigger_import_id)
    if trigger is None:
        raise HTTPException(status_code=404,
                            detail=f"event import {request.trigger_import_id!r} not found")
    random_batch = svc.get_import(request.random_import_id)
    if random_batch is None:
        raise HTTPException(status_code=404,
                            detail=f"event import {request.random_import_id!r} not found")
    verdict = ICAnalysisService.compare_random_control(trigger, random_batch)
    return RandomControlCompareResponse(**verdict.to_dict())


def _form_json_dict(name: str, raw: Optional[str]) -> dict:
    """multipart 之 JSON 字串欄 → dict；非 JSON 物件即顯式 400（不猜、不接受陣列/純量）。"""
    if raw is None or str(raw).strip() == "":
        return {}
    import json as _json

    try:
        val = _json.loads(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=EventImportRejected(
            kind="parse_error", message=f"{name} 不是合法 JSON：{exc}").model_dump())
    if not isinstance(val, dict):
        raise HTTPException(status_code=400, detail=EventImportRejected(
            kind="parse_error", message=f"{name} 須為 JSON 物件（{{契約欄名: 值}}），實得 {type(val).__name__}").model_dump())
    return val


@router.post("/case/import-events/csv", response_model=EventImportResponse)
async def import_events_csv(
    file: UploadFile = File(..., description="使用者自有欄名之 CSV（不必先改成契約欄名）"),
    column_mapping: str = Form(..., description='JSON 物件 {契約欄名: CSV 欄名}；**無預設對映**（A-4′）。缺 ⇒ column_mapping_missing'),
    batch_defaults: Optional[str] = Form(None, description="JSON 物件 {契約欄名: 值}；只**填補缺值**，不覆蓋列自帶值"),
    lookahead_declaration: Optional[str] = Form(
        None,
        description=('GAP-3 UX Task 1.9／1.11 之答案窗宣告：JSON 物件 '
                     '{"declared_window_bars": {timeframe: 非負整數（0 ＝未用未來資訊，須明填）}, "acknowledged_unverifiable": bool}。'
                     '預設值請先呼叫 /case/import-events/lookahead-declaration 取得（＝檔內最大可用 horizon，逐 tf）'),
    ),
    mapping_confirmed_at: Optional[str] = Form(
        None,
        description=('GAP-3 UX Task 1.5／1.6：使用者於對映 UI **勾選確認**之時間（UTC ISO-8601）。'
                     '缺 ⇒ receipt 記伺服器落檔時間，並以 mapping_provenance.confirmed_at_source '
                     '＝server_received 揭露（伺服器時間不冒充使用者確認時間）'),
    ),
    source_file: Optional[UploadFile] = File(
        None,
        description=('契約所指之**來源檔**（如 /search 一併下載之 *.source.json）。'
                     '帶入時逐列對證 source_file_digest；未帶 ⇒ receipt 之 '
                     'mapping_provenance.source_digest_verified＝false（宣告值只證明填了同一串）'),
    ),
    derive_event_id: bool = Form(
        False,
        description=('GAP-3 UX Task 1.5（殘留 R-B2-1）：為 true 時由後端在 **t0 單位正規化之後**、'
                     '以契約 event_id_template 之唯一實作逐列產生 event_id（秒級 t0 之 CSV 免手改）。'
                     '**預設 false**——不推斷（A-4′），須使用者顯式要求'),
    ),
    validate_only: bool = Query(False),
    verify_source_digest: bool = Query(
        False,
        description=("逐列對證 source_file_digest（需一併上傳 `source_file`）。前置條件與 /import-events "
                     "共用同一實作；未開啟 ⇒ receipt 之 mapping_provenance.source_digest_verified＝false"),
    ),
):
    """CSV ＋ 欄名對映匯入（GAP-3 UX Task 1.2）。

    🔴 對映層只做欄名對應；**schema 檢核與落檔轉呼與 `/case/import-events` 相同的
    `EventImportService.import_records`（同一函式物件）**——不得為 CSV 另寫一份檢核邏輯（V-3）。
    """
    svc = get_event_import_service()
    content = await file.read()
    src_bytes = await source_file.read() if source_file is not None else None
    _assert_source_file_usable(verify_source_digest, src_bytes, content)
    mapping = _form_json_dict("column_mapping", column_mapping)
    defaults = _form_json_dict("batch_defaults", batch_defaults)
    try:
        records, warnings = svc.csv_records_from_mapping(content, mapping, defaults)
        return svc.import_records(records, source_name=file.filename, upload_bytes=content,
                                  validate_only=validate_only, batch_defaults=defaults, extra_warnings=warnings,
                                  verify_source_digest=verify_source_digest, source_bytes=src_bytes,
                                  lookahead_declaration=_form_json_dict("lookahead_declaration", lookahead_declaration) or None,
                                  data_columns=svc.file_columns(content, file.filename or "") or None,
                                  column_mapping=mapping, mapping_confirmed_at=mapping_confirmed_at,
                                  derive_event_id=derive_event_id)
    except EventImportRejectedError as exc:
        raise _rejected(exc, svc=svc, content=content)


@router.post("/case/import-events/lookahead-declaration")
async def lookahead_declaration_preview(
    file: UploadFile = File(..., description="欲上傳之事件檔（CSV／JSON）"),
    column_mapping: Optional[str] = Form(None, description="CSV 對映（同 /csv 端點）；JSON／契約欄名 CSV 免填"),
    batch_defaults: Optional[str] = Form(None, description="同 /csv 端點"),
):
    """GAP-3 UX Task 1.9 ①：答案窗宣告之**預填**資料（逐 tf 預設值＝檔內最大可用 horizon）。

    宣告 UI 於選檔後呼叫本端點取得：批內 timeframe 清單、逐 tf 預設值、以及是否**強制**宣告
    （條件引用了深度不可由 registry 驗證之欄位）。🔴 本端點只讀不落檔。
    """
    svc = get_event_import_service()
    content = await file.read()
    mapping = _form_json_dict("column_mapping", column_mapping)
    defaults = _form_json_dict("batch_defaults", batch_defaults)
    try:
        if mapping:
            records, _ = svc.csv_records_from_mapping(content, mapping, defaults)
        else:
            records = svc.parse_upload(content, file.filename or "")
        return svc.lookahead_declaration_preview(content, file.filename or "", records, defaults)
    except EventImportRejectedError as exc:
        raise _rejected(exc, svc=svc, content=content)


@router.post("/case/lookahead-declaration/preview-columns")
async def lookahead_declaration_preview_columns(request: LookaheadDeclarationPreviewColumnsRequest):
    """GAP-3 UX Task 1.9′（R 重開 D-8）：`/search` 匯出端答案窗宣告框之**預填**資料。

    輸入＝搜尋結果之欄名集合＋timeframe 集合；回 `LookaheadDeclarationPreview`（與匯入端
    `/case/import-events/lookahead-declaration` 同形、同一實作 `preview_from_columns`）。
    🔴 只讀不落檔、**不算深度**：預設值只是 registry 之揭露候選，深度＝使用者宣告。
    （Phase 2 之 `/case/lookahead-depth` 已於 R 重開退役——深度不再由篩選條件導出。）
    """
    return get_event_import_service().lookahead_declaration_preview_from_columns(
        list(request.columns), list(request.timeframes))


@router.get("/case/events", response_model=EventImportListResponse)
async def list_event_imports():
    return get_event_import_service().list_imports()


@router.get("/case/events/{import_id}", response_model=EventImportDetailResponse)
async def get_event_import(import_id: str):
    out = get_event_import_service().get_import(import_id)
    if out is None:
        raise HTTPException(status_code=404, detail=f"event import {import_id!r} not found")
    return out


@router.delete("/case/events/{import_id}", status_code=204)
async def delete_event_import(import_id: str):
    """GAP-3 UX Task 3.1：刪除該批事件與其全部落檔產物，**不留孤兒檔**。

    🔴 不存在之 `import_id` ⇒ **404（非 500）**。
    🔴 只刪該批；**不連帶刪 kline 快取或 Feature Library**，亦**不提供「刪除全部」端點**。
    """
    if not get_event_import_service().delete_import(import_id):
        raise HTTPException(status_code=404, detail=f"event import {import_id!r} not found")
    return Response(status_code=204)


@router.post("/case/events/{import_id}/analyze", response_model=EventAnalyzeResponse)
async def analyze_event_import(import_id: str, request: EventAnalyzeRequest):
    """對一筆匯入跑對齊→去重→切分＋兩張表（真實 kline；統計全在 momentum）。缺 kline／契約違規 ⇒ 4xx 顯式。"""
    svc = get_event_import_service()
    try:
        out = svc.analyze(import_id, request)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail={"kind": "bars_unavailable", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"kind": "pipeline_rejected", "message": str(exc)})
    if out is None:
        raise HTTPException(status_code=404, detail=f"event import {import_id!r} not found")
    return out


# DEPRECATED（KLINE-1）：舊案例清單。🔴 移除前須先處理仍在呼叫的前端：hooks/useAvailableSymbols（FF BatchGenerationPanel、strategy-test）、chart、charts。
@router.get("/case/list", response_model=CaseListResponse)
async def get_case_list():
    """
    獲取所有已導入案例列表

    Returns:
        CaseListResponse: 案例列表和統計信息
    """
    logger.info("Retrieving case list")

    try:
        result = case_storage.get_statistics()

        logger.info(f"Retrieved {result.total} cases")

        return result

    except Exception as e:
        logger.error(f"Failed to retrieve case list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cases: {str(e)}")


# DEPRECATED（KLINE-1）：舊案例計數，只供 /data-preparation 舊區塊。
@router.get("/case/count")
async def get_case_count():
    """
    獲取當前案例數量

    Returns:
        dict: {"count": int} - 當前案例總數
    """
    logger.info("Retrieving case count")

    try:
        cases = case_storage.get_cases()
        count = len(cases)

        logger.info(f"Current case count: {count}")

        return {"count": count}

    except Exception as e:
        logger.error(f"Failed to retrieve case count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve case count: {str(e)}")


# DEPRECATED（KLINE-1）：以舊案例為中心的批量 K 線下載（batch_download_service）。給特徵計算用的 K 線下載入口＝/api/v1/feature-data/kline/download（Feature Factory 頁）。
@router.post("/kline/batch-download")
async def start_batch_download(
    request: BatchDownloadRequest,
    background_tasks: BackgroundTasks
):
    """
    開始批量K線下載任務

    Args:
        request: 批量下載請求
        background_tasks: FastAPI背景任務

    Returns:
        dict: {"task_id": str, "message": str}
    """
    logger.info(
        f"Starting batch download: case_ids={request.case_ids}, "
        f"lookback={request.lookback_bars}, forward={request.forward_bars}"
    )

    try:
        # 創建下載任務
        task_id = batch_download_service.create_download_task(request)

        # 添加到背景任務
        background_tasks.add_task(
            batch_download_service.execute_batch_download,
            task_id,
            request
        )

        logger.info(f"Batch download task {task_id} created and queued")

        return {
            "task_id": task_id,
            "message": f"Batch download task created successfully"
        }

    except Exception as e:
        logger.error(f"Failed to start batch download: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start download: {str(e)}"
        )


# DEPRECATED（KLINE-1）：與 /kline/batch-download 成對。
@router.get("/kline/download-status/{task_id}", response_model=DownloadProgress)
async def get_download_status(task_id: str):
    """
    查詢批量下載任務進度

    Args:
        task_id: 任務ID

    Returns:
        DownloadProgress: 下載進度

    Raises:
        HTTPException: 任務不存在
    """
    logger.debug(f"Querying download status for task: {task_id}")

    progress = batch_download_service.get_progress(task_id)

    if not progress:
        logger.warning(f"Download task not found: {task_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Download task not found: {task_id}"
        )

    return progress


# DEPRECATED（KLINE-1）：清空舊案例；只供 /data-preparation 舊區塊。
@router.delete("/case/clear-all")
async def clear_all_cases():
    """
    清空所有案例（謹慎使用）

    Returns:
        dict: {"success": bool, "cleared_count": int, "message": str}
    """
    logger.warning("Clearing all cases from storage")

    try:
        cleared_count = case_storage.clear_all()

        logger.info(f"All cases cleared successfully: {cleared_count} cases")

        return {
            "success": True,
            "cleared_count": cleared_count,
            "message": f"Successfully cleared {cleared_count} cases"
        }

    except Exception as e:
        logger.error(f"Failed to clear cases: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cases: {str(e)}"
        )
