## Quick guide for AI coding agents (GitHub Copilot / coding agents)

Follow these concise rules to be immediately useful in this repository (quantitative_trading_system).

1. Big picture (one-liner): this is an ML-first strategy research platform — FastAPI backend (api/) provides services (case search, indicator calc, ML training); Next.js frontend (frontend/) visualizes search results and charts; heavy numeric data lives in HDF5 under `data_cache/`.

2. Important directories to inspect before changes:
   - `api/` — FastAPI app entry in `api/main.py`; services in `api/services/`, routes in `api/routes/`, models in `api/models/`.
   - `momentum/` — core research engines (case_search_engine.py, signal_analyzer.py, indicator modules).
   - `data_cache/` — HDF5 K-line caches (many files like `BTCUSDT_12h.h5`). Treat contents as authoritative; do not replace with synthetic data.
   - `frontend/` — Next.js app (app/, components/, store/). Use when adding UI or API consumers.
   - top-level scripts: `run_api.py` starts the backend locally; `requirements.txt` lists Python deps.

3. Local dev & quick commands (macOS/Linux):
   - Backend: create venv, pip install -r requirements.txt, run `python run_api.py` (FastAPI serves at http://localhost:8000). API docs at `/docs`.
   - Frontend: `cd frontend && npm install && npm run dev` (Next at http://localhost:3000).

4. Project-specific conventions and gotchas:
   - Data truth: HDF5 files in `data_cache/` are treated as real market data. Avoid committing or generating fake data; confirm any new data sources are documented in docs/.
   - Performance-first: strive for vectorized pandas/polars operations; prefer Optuna for hyperparameter tuning where applicable. See `momentum/` for example patterns.
   - Logging: use INFO for normal events and ERROR with exc_info=True for exceptions. Avoid noisy logs inside tight loops.
   - Error handling: external API calls (e.g., Binance/ccxt) must be wrapped with try/except and classified (retryable vs fatal).

5. Common code patterns and examples (search locations):
   - Case search engine: `momentum/DataExtraction/case_search_engine.py` — follow its function signatures when adding search filters or new parameters.
   - Indicator computation: `momentum/Indicator/` — add new indicators as pure functions that accept and return DataFrame-like objects.
   - API entry: `api/main.py` mounts routers from `api/routes/` and relies on `api/services/` for heavy work. Keep route handlers thin.

6. Tests and where they live:
   - Unit tests: top-level `test_*.py` files (e.g., `test_kline_downloader.py`, `test_kline_storage.py`). Run tests with your preferred test runner (pytest is expected). Run quick smoke tests after edits.

7. What to avoid or flag in PRs:
   - Large binary data commits (HDF5/CSV). Data should go to `data_cache/` and be excluded by .gitignore.
   - Replacing numeric algorithms with un-vectorized Python loops without benchmarking.
   - Breaking the API shape — keep changes in `api/models/` backward compatible where possible.

8. When you modify behavior, update these files:
   - `README.md` or appropriate `docs/` file (ARCHITECTURE.md, DEVELOPMENT_GUIDE.md, API_SPECIFICATION.md).
   - Add or update tests covering the changed behavior (see existing test_*.py files).

9. Pull request checklist for AI-generated changes:
   - No fake or synthetic market data committed.
   - All new code has at least one unit test or a concrete smoke test.
   - Update docs for architecture or API changes.
   - Preserve performance patterns (vectorized ops) and add a short benchmark if replacing core numeric logic.

If anything above is unclear or you want more examples from specific files (router, service, or indicator implementations), tell me which file and I'll extract examples and expand this guide.
