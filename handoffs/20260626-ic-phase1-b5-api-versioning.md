# IC Phase 1 B5 API Versioning Handoff

## Status
BLOCKED: debug two validation rounds did not pass under user limit.

## Changed
- `api/core/config.py`: added `Settings.ic_response_v2=False`.
- `api/routes/ic_analysis.py`: `/result/{task_id}` accepts `schema_version` Query and forwards to service.
- `api/models/ic_models.py`: added `ICResultV2Response`, `ICArtifactFilter`, `ICArtifactQueryParams`.
- `api/services/ic_analysis_service.py`: added v1 fallback and v2 artifact-backed response branch.
- `tests/api/test_ic_response_v2.py`: expanded TestClient coverage for v1 baseline, negotiation, artifact SSOT, subroutes, no artifact.

## Validation Rounds
1. `pytest tests/api/test_ic_response_v2.py -q`: collection failed because importing `api.main` initialized all routes and Binance ping attempted network.
2. `pytest tests/api/test_ic_response_v2.py -q`: 4 tests passed, then hung in `test_flag_off_subroutes_unchanged` after `/export/{task_id}/json`; interrupted at 71s.

## Passing Evidence
- `grep -rE 'from api\.' momentum/`: no output, exit 1 (expected zero matches).
- In round 2, route tests passed through v1 baseline, v2 negotiation, and v2 top-N SSOT before export hang.

## Suspected Next Step
- Avoid StreamingResponse hang in export subroute test by hashing `ic_analysis_service.export_analysis(..., "json")` bytes directly, or use `CLIENT.stream()` with bounded read.

## Scope Notes
- No frontend or momentum files were edited.
- No numeric/schema payload changes beyond new v2 API envelope and query models.
