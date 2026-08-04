import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import (
    analytics,
    auth,
    cache,
    dashboard,
    dashboard_v2,
    dataset,
    db_connection,
    export,
    performance,
    query,
    tasks,
    users,
    workers,
    llm,
    nl2sql,
    ai_cleaning,
    rag,
    agents,
    xai,
    reports,
    prompts,
    evaluation,
    models,
    workflows,
    knowledge,
    federation,
    streams,
    copilot,
    predictive,
    plugins,
    cluster,
)
from app.api.routes import health
from app.core.production import settings as prod_settings
from app.core.database import Base, engine
import app.models
from app.core.exceptions import AppException, handle_exception
from app.services.compression_service import CompressionMiddleware
from app.services.health_service import health_service
from app.services.logging_service import StructuredLoggingMiddleware, setup_logging

# Initialize JSON structured logging
setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        def add_columns_if_missing(conn):
            from sqlalchemy import inspect, text

            try:
                inspector = inspect(conn)
                columns = [c["name"] for c in inspector.get_columns("user_datasets")]
                if "profile_info" not in columns:
                    conn.execute(text("ALTER TABLE user_datasets ADD COLUMN profile_info JSON"))
                    logging.getLogger(__name__).info("Successfully added profile_info column to user_datasets table")

                if "status" not in columns:
                    conn.execute(text("ALTER TABLE user_datasets ADD COLUMN status VARCHAR(50) DEFAULT 'active'"))
                    logging.getLogger(__name__).info("Successfully added status column to user_datasets table")

                user_cols = [c["name"] for c in inspector.get_columns("users")]
                if "role" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'Viewer'"))
                    logging.getLogger(__name__).info("Successfully added role column to users table")

                if "failed_login_attempts" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0"))
                    logging.getLogger(__name__).info("Successfully added failed_login_attempts column to users table")

                if "lockout_until" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN lockout_until TIMESTAMP"))
                    logging.getLogger(__name__).info("Successfully added lockout_until column to users table")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Check or alter columns failed: {e}")

        await connection.run_sync(add_columns_if_missing)

        def seed_default_admin(conn):
            from sqlalchemy import text
            from app.core.security import get_password_hash
            import uuid
            try:
                res = conn.execute(text("SELECT id FROM users WHERE email = 'admin@example.com'"))
                row = res.fetchone()
                if not row:
                    user_id = str(uuid.uuid4())
                    hashed_pw = get_password_hash("password123")
                    # Set role to Admin to enable full features dashboard permissions
                    conn.execute(text(
                        f"INSERT INTO users (id, email, hashed_password, full_name, role, failed_login_attempts) "
                        f"VALUES ('{user_id}', 'admin@example.com', '{hashed_pw}', 'System Administrator', 'Admin', 0)"
                    ))
                    logging.getLogger(__name__).info("Successfully seeded default admin user.")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to seed default admin: {e}")

        await connection.run_sync(seed_default_admin)

        def create_database_indexes(conn):
            from sqlalchemy import text

            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_status ON user_sessions(status)",
                "CREATE INDEX IF NOT EXISTS idx_system_audit_logs_user_id ON system_audit_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_system_audit_logs_timestamp ON system_audit_logs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_dashboards_user_id ON dashboards(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_dashboards_created_at ON dashboards(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_started_at ON tasks(started_at)",
                "CREATE INDEX IF NOT EXISTS idx_user_datasets_user_id ON user_datasets(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON query_history(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at)",
            ]
            for idx in indexes:
                try:
                    conn.execute(text(idx))
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to create index '{idx}': {e}")

        await connection.run_sync(create_database_indexes)
    from app.services.plugin_manager import plugin_manager
    plugin_manager.discover_and_load_plugins()

    from app.services.workflow_scheduler import workflow_scheduler
    from app.services.distributed_scheduler import distributed_scheduler
    workflow_scheduler.start()
    await distributed_scheduler.start()
    yield
    workflow_scheduler.stop()
    await distributed_scheduler.stop()
    await engine.dispose()


from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(title="AI Data Analyst API", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_exception_handler(AppException, handle_exception)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(CompressionMiddleware)

# Mount local static folder for offline Swagger UI assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon-32x32.png",
    )


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Enforce request size limit
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > prod_settings.MAX_REQUEST_SIZE_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload too large. Enforced limit is 100MB."}
                )
        except Exception:
            pass
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    from app.core.config import settings

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
    )
    if request.url.scheme == "https" or settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(dataset.router, prefix="/api/v1")
app.include_router(db_connection.router, prefix="/api/v1")
app.include_router(dashboard_v2.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(workers.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")
app.include_router(cache.router, prefix="/api/v1")
app.include_router(llm.router, prefix="/api/v1")
app.include_router(nl2sql.router, prefix="/api/v1")
app.include_router(ai_cleaning.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(xai.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(prompts.router, prefix="/api/v1")
app.include_router(evaluation.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(federation.router, prefix="/api/v1")
app.include_router(streams.router, prefix="/api/v1")
app.include_router(copilot.router, prefix="/api/v1")
app.include_router(predictive.router, prefix="/api/v1")
app.include_router(plugins.router, prefix="/api/v1")
app.include_router(cluster.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(health.router)


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, _exc: Exception):
    logging.getLogger(__name__).exception("Unhandled application error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    return {"message": "AI Data Analyst API is running"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

