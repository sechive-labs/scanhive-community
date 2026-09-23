from fastapi import FastAPI
from sqlalchemy import inspect, text as sql_text

from app.db.base import Base
from app.db.session import engine, SessionLocal

from app.models import *
from app.services.role_templates import seed_default_roles
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as project_router
from app.api.v1.scans import router as scan_router
from app.api.v1.findings import router as finding_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.iam import router as iam_router
from app.api.v1.api_keys import router as api_key_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware



Base.metadata.create_all(bind=engine)

# create_all only creates missing tables, it never alters existing ones --
# there's no migration framework in this project, so newly added nullable
# columns are added by hand here, guarded to be safe to run on every startup.
# Both blocks below use Postgres-only syntax and only matter for upgrading
# an existing install, so they're skipped for the SQLite engine used by the
# test suite (backend/tests/conftest.py), where create_all already produces
# the full, current schema.
is_sqlite = engine.url.get_backend_name() == "sqlite"

if not is_sqlite:
    with engine.begin() as connection:
        for column, ddl_type in [
            ("end_line", "INTEGER"),
            ("start_column", "INTEGER"),
            ("end_column", "INTEGER"),
            ("snippet", "TEXT"),
            ("cwe", "VARCHAR(255)"),
            ("owasp", "VARCHAR(255)"),
            ("help_uri", "VARCHAR(1000)"),
        ]:
            connection.execute(sql_text(
                f"ALTER TABLE findings ADD COLUMN IF NOT EXISTS {column} {ddl_type}"
            ))
        connection.execute(sql_text(
            "ALTER TABLE roles ADD COLUMN IF NOT EXISTS locked BOOLEAN NOT NULL DEFAULT false"
        ))
        connection.execute(sql_text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP"
        ))
        # Email verification arrived after accounts already existed. Those
        # accounts are grandfathered as verified exactly once -- when the
        # column is first added -- so later unverified sign-ups stay unverified.
        if "email_verified_at" not in {c["name"] for c in inspect(connection).get_columns("users")}:
            connection.execute(sql_text("ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP"))
            connection.execute(sql_text("UPDATE users SET email_verified_at = NOW()"))

# Same as above: enforce case-insensitive unique API key names per user at
# the DB level as a backstop (the API already rejects duplicates itself).
# Wrapped separately and tolerantly -- if an existing install already has
# duplicate names, this index creation fails and is skipped rather than
# blocking startup; it'll succeed once those duplicates are renamed.
if not is_sqlite:
    try:
        with engine.begin() as connection:
            connection.execute(sql_text(
                "CREATE UNIQUE INDEX IF NOT EXISTS api_keys_user_id_name_lower_key "
                "ON api_keys (user_id, lower(name))"
            ))
    except Exception as exc:
        print(
            "Warning: could not create unique index on api_keys(user_id, lower(name)) "
            f"-- likely pre-existing duplicate names: {exc}"
        )

# Backfill the composable role catalog (iam-admin / project-admin / auditor
# / security-analyst / platform-admin, see app/services/role_templates.py)
# onto organizations created before it existed, and rename any still-old-
# named role (from a prior pass of this same catalog) onto the current name
# in place -- same row id, so existing user/group assignments carry over
# automatically without any special-cased reassignment. Fully idempotent,
# runs every startup.
try:
    with SessionLocal() as backfill_db:
        for organization in backfill_db.query(Organization).all():
            seed_default_roles(backfill_db, organization.id)
        backfill_db.commit()
except Exception as exc:
    print(f"Warning: could not backfill the composable role catalog: {exc}")

app = FastAPI(
    title="ScanHive",
    version="0.1.0"
)

extra_cors_origins = [
    origin.strip()
    for origin in settings.EXTRA_CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *extra_cors_origins,
    ],
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1|"
        r"10(?:\.\d{1,3}){3}|"
        r"192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})"
        r"(?::\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    # Set here (not per-endpoint) so error responses -- which drop headers
    # set on the injected Response -- are covered too.
    if request.url.path.startswith("/api/v1/auth/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(auth_router)
app.include_router(project_router)
app.include_router(scan_router)
app.include_router(finding_router)
app.include_router(dashboard_router)
app.include_router(iam_router)
app.include_router(api_key_router)

@app.get("/")
def root():
    return {
        "application": "ScanHive",
        "status": "Running"
    }


@app.get("/health")
def health():
    return {
        "database": "Connected",
        "status": "Healthy"
    }
