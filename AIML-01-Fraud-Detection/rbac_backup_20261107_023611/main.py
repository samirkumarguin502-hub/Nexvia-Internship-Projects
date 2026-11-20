"""FastAPI binding for AIML-01 Fraud Detection Platform.

Run:
    python -m uvicorn backend.app.main:create_app --factory

Business logic remains in service.py, validation.py and db.py.
Authentication is optional for local development and enabled through API_KEY.
"""

from __future__ import annotations

import hmac
import logging
import time
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config import Settings
from backend.app.db import Repository
from backend.app.errors import AppError
from backend.app.logging_setup import log_event, setup_logging
from backend.app.model_service import ModelService
from backend.app.ratelimit import RateLimiter
from backend.app.schemas import (
    BatchOut,
    CaseUpdateIn,
    FeedbackIn,
    PredictionOut,
    RetrainCreateIn,
    RetrainTransitionIn,
    TransactionIn,
)
from backend.app.service import FraudService


API = "/api/v1"

CSV_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.ms-excel",
}

PUBLIC_PATHS = {
    f"{API}/health",
    f"{API}/ready",
}


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = settings or Settings.from_env()

    logger = setup_logging(settings.log_level)

    # Initialize persistence and model services.
    repo = Repository(settings.database_path)
    repo.init_schema()

    model = ModelService(settings.model_dir)
    model.load()

    service = FraudService(settings, repo, model)

    limiters = {
        "predict": RateLimiter(settings.rate_predict_per_min),
        "batch": RateLimiter(settings.rate_batch_per_min),
        "read": RateLimiter(settings.rate_read_per_min),
    }

    docs_url = None if settings.is_production else "/docs"
    openapi_url = (
        None if settings.is_production else "/openapi.json"
    )

    app = FastAPI(
        title="AIML-01 Fraud Detection API",
        version="0.3.0",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
    )

    app.state.service = service
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    # ---------------------------------------------------------
    # Request identity and rate limiting
    # ---------------------------------------------------------

    def request_id(request: Request) -> str:
        return getattr(request.state, "request_id", "")

    def client_key(request: Request) -> str:
        """Resolve client IP.

        TRUST_PROXY must only be enabled when the application is
        behind a trusted proxy that strips client-supplied forwarding
        headers and writes its own X-Forwarded-For header.
        """

        if settings.trust_proxy:
            forwarded = request.headers.get(
                "x-forwarded-for", ""
            )

            if forwarded:
                return forwarded.split(",")[0].strip()[:64]

        if request.client:
            return request.client.host

        return "unknown"

    def limit(bucket: str):
        def dependency(request: Request) -> None:
            limiter = limiters[bucket]

            allowed, retry_after = limiter.check(
                client_key(request)
            )

            if not allowed:
                raise AppError(
                    429,
                    "rate_limited",
                    "Too many requests; slow down.",
                    headers={
                        "Retry-After": str(
                            max(1, int(retry_after) + 1)
                        )
                    },
                )

        return dependency

    # ---------------------------------------------------------
    # Middleware
    # ---------------------------------------------------------

    @app.middleware("http")
    async def base_middleware(request: Request, call_next):
        rid = uuid.uuid4().hex[:12]
        request.state.request_id = rid

        started = time.perf_counter()
        path = request.url.path

        # Health and readiness endpoints remain public.
        is_public = path in PUBLIC_PATHS

        # API key authentication.
        if settings.api_key and not is_public:
            authorization = request.headers.get(
                "authorization", ""
            )

            bearer = ""

            if authorization.lower().startswith("bearer "):
                bearer = authorization[7:].strip()

            candidate = (
                bearer
                or request.headers.get("x-api-key", "")
            )

            if not hmac.compare_digest(
                candidate,
                settings.api_key,
            ):
                response = JSONResponse(
                    AppError(
                        401,
                        "unauthorized",
                        "Valid API authentication is required.",
                    ).body(rid),
                    status_code=401,
                    headers={
                        "WWW-Authenticate": "Bearer",
                    },
                )

                response.headers["X-Request-ID"] = rid
                response.headers[
                    "X-Content-Type-Options"
                ] = "nosniff"
                response.headers["Cache-Control"] = "no-store"

                log_event(
                    logger,
                    "request",
                    request_id=rid,
                    method=request.method,
                    route="protected",
                    status=401,
                    latency_ms=round(
                        (time.perf_counter() - started) * 1000,
                        1,
                    ),
                )

                return response

        # Enforce declared body size for non-batch requests.
        # Batch requests have their own streaming size enforcement.
        content_length = request.headers.get(
            "content-length", ""
        )

        is_batch = path == f"{API}/predict/batch"

        if (
            request.method in {"POST", "PUT", "PATCH"}
            and not is_batch
            and content_length.isdigit()
            and int(content_length) > settings.max_json_bytes
        ):
            response = JSONResponse(
                AppError(
                    413,
                    "payload_too_large",
                    "Request body too large.",
                ).body(rid),
                status_code=413,
            )

        else:
            response = await call_next(request)

        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"

        route = request.scope.get("route")

        log_event(
            logger,
            "request",
            request_id=rid,
            method=request.method,
            route=route.path if route else "unmatched",
            status=response.status_code,
            latency_ms=round(
                (time.perf_counter() - started) * 1000,
                1,
            ),
        )

        return response

    # ---------------------------------------------------------
    # Exception handlers
    # ---------------------------------------------------------

    @app.exception_handler(AppError)
    async def handle_app_error(
        request: Request,
        exc: AppError,
    ):
        return JSONResponse(
            exc.body(request_id(request)),
            status_code=exc.status,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ):
        # Do not include submitted values in the response.
        details = [
            {
                "loc": [
                    str(item)
                    for item in error.get("loc", [])
                ],
                "reason": error.get("msg", "invalid"),
                "type": error.get("type", ""),
            }
            for error in exc.errors()
        ]

        error = AppError(
            422,
            "validation_error",
            "Request validation failed.",
            details=details,
        )

        return JSONResponse(
            error.body(request_id(request)),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        exc: StarletteHTTPException,
    ):
        code = {
            404: "not_found",
            405: "method_not_allowed",
        }.get(exc.status_code, "http_error")

        message = {
            404: "Resource not found.",
            405: "Method not allowed.",
        }.get(exc.status_code, "Request failed.")

        error = AppError(
            exc.status_code,
            code,
            message,
        )

        return JSONResponse(
            error.body(request_id(request)),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ):
        log_event(
            logger,
            "unhandled_error",
            logging.ERROR,
            request_id=request_id(request),
            exc_type=type(exc).__name__,
        )

        error = AppError(
            500,
            "internal_error",
            "Internal server error.",
        )

        return JSONResponse(
            error.body(request_id(request)),
            status_code=500,
        )

    # ---------------------------------------------------------
    # Health endpoints
    # ---------------------------------------------------------

    @app.get(
        f"{API}/health",
        tags=["health"],
    )
    def health():
        return service.health()

    @app.get(
        f"{API}/ready",
        tags=["health"],
    )
    def ready():
        status, body = service.readiness()

        return JSONResponse(
            body,
            status_code=status,
        )

    # ---------------------------------------------------------
    # Model endpoints
    # ---------------------------------------------------------

    @app.get(
        f"{API}/model",
        tags=["model"],
        dependencies=[Depends(limit("read"))],
    )
    def model_info():
        return service.model_info()

    # ---------------------------------------------------------
    # Single transaction prediction
    # ---------------------------------------------------------

    @app.post(
        f"{API}/predict",
        tags=["prediction"],
        response_model=PredictionOut,
        dependencies=[Depends(limit("predict"))],
    )
    def predict(tx: TransactionIn):
        payload = tx.model_dump(exclude_none=True)

        return service.predict_one(payload)

    # ---------------------------------------------------------
    # Batch CSV prediction
    # ---------------------------------------------------------

    @app.post(
        f"{API}/predict/batch",
        tags=["prediction"],
        response_model=BatchOut,
        dependencies=[Depends(limit("batch"))],
    )
    async def predict_batch(request: Request):
        """Accept raw CSV data without writing uploaded data to disk."""

        content_type = (
            request.headers.get("content-type", "")
            .split(";")[0]
            .strip()
            .lower()
        )

        if content_type not in CSV_TYPES:
            raise AppError(
                415,
                "unsupported_media_type",
                "Send the CSV as the raw body with Content-Type: text/csv.",
            )

        content_length = request.headers.get(
            "content-length", ""
        )

        if (
            content_length.isdigit()
            and int(content_length) > settings.max_upload_bytes
        ):
            raise AppError(
                413,
                "file_too_large",
                f"File exceeds the {settings.max_upload_bytes} byte limit.",
            )

        chunks = []
        total_bytes = 0

        async for chunk in request.stream():
            total_bytes += len(chunk)

            if total_bytes > settings.max_upload_bytes:
                raise AppError(
                    413,
                    "file_too_large",
                    f"File exceeds the {settings.max_upload_bytes} byte limit.",
                )

            chunks.append(chunk)

        csv_content = b"".join(chunks)

        return await run_in_threadpool(
            service.predict_batch,
            csv_content,
        )

    # ---------------------------------------------------------
    # Transaction listing and details
    # ---------------------------------------------------------

    @app.get(
        f"{API}/transactions",
        tags=["transactions"],
        dependencies=[Depends(limit("read"))],
    )
    def transactions(
        page: int = Query(1, ge=1),
        page_size: int = Query(
            25,
            ge=1,
            le=settings.max_page_size,
        ),
        sort: str = "id",
        order: str = "desc",
        flagged: Optional[bool] = None,
        type: Optional[str] = Query(
            None,
            max_length=32,
        ),
        min_score: Optional[float] = Query(
            None,
            ge=0,
            le=1,
        ),
        max_score: Optional[float] = Query(
            None,
            ge=0,
            le=1,
        ),
        source: Optional[str] = None,
        case_status: Optional[str] = None,
        batch_id: Optional[str] = Query(
            None,
            max_length=64,
        ),
    ):
        return service.list_transactions(
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            flagged=flagged,
            type_=type,
            min_score=min_score,
            max_score=max_score,
            source=source,
            case_status=case_status,
            batch_id=batch_id,
        )

    @app.get(
        f"{API}/transactions/{transaction_id}",
        tags=["transactions"],
        dependencies=[Depends(limit("read"))],
    )
    def transaction(transaction_id: int):
        return service.get_transaction(transaction_id)

    # ---------------------------------------------------------
    # Case management and analyst feedback
    # ---------------------------------------------------------

    @app.patch(
        f"{API}/transactions/{transaction_id}/case",
        tags=["cases"],
        dependencies=[Depends(limit("read"))],
    )
    def update_case(
        transaction_id: int,
        body: CaseUpdateIn,
    ):
        return service.update_case(
            transaction_id,
            body.model_dump(),
        )

    @app.put(
        f"{API}/transactions/{transaction_id}/feedback",
        tags=["cases"],
        dependencies=[Depends(limit("read"))],
    )
    def feedback(
        transaction_id: int,
        body: FeedbackIn,
    ):
        return service.set_feedback(
            transaction_id,
            body.model_dump(),
        )

    # ---------------------------------------------------------
    # Alerts
    # ---------------------------------------------------------

    @app.get(
        f"{API}/alerts",
        tags=["alerts"],
        dependencies=[Depends(limit("read"))],
    )
    def alerts(
        page: int = Query(1, ge=1),
        page_size: int = Query(
            25,
            ge=1,
            le=settings.max_page_size,
        ),
        case_status: Optional[str] = None,
    ):
        return service.alerts(
            page=page,
            page_size=page_size,
            case_status=case_status,
        )

    # ---------------------------------------------------------
    # Dashboard
    # ---------------------------------------------------------

    @app.get(
        f"{API}/dashboard/summary",
        tags=["dashboard"],
        dependencies=[Depends(limit("read"))],
    )
    def dashboard():
        return service.dashboard_summary()

    # ---------------------------------------------------------
    # Monitoring and pipeline status
    # ---------------------------------------------------------

    @app.get(
        f"{API}/monitoring/status",
        tags=["monitoring"],
        dependencies=[Depends(limit("read"))],
    )
    def monitoring_status():
        return service.monitoring_status()

    @app.get(
        f"{API}/pipeline/status",
        tags=["monitoring"],
        dependencies=[Depends(limit("read"))],
    )
    def pipeline_status():
        return service.pipeline_status()

    # ---------------------------------------------------------
    # Retraining workflow
    # ---------------------------------------------------------

    @app.get(
        f"{API}/monitoring/retraining",
        tags=["monitoring"],
        dependencies=[Depends(limit("read"))],
    )
    def retrain_list():
        return service.retrain_list()

    @app.post(
        f"{API}/monitoring/retraining",
        tags=["monitoring"],
        dependencies=[Depends(limit("read"))],
    )
    def retrain_create(body: RetrainCreateIn):
        return service.retrain_create(
            body.model_dump()
        )

    @app.post(
        f"{API}/monitoring/retraining/{request_id}/transition",
        tags=["monitoring"],
        dependencies=[Depends(limit("read"))],
    )
    def retrain_transition(
        request_id: int,
        body: RetrainTransitionIn,
    ):
        return service.retrain_transition(
            request_id,
            body.model_dump(exclude_none=True),
        )

    return app