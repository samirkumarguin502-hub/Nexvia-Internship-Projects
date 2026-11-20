from pathlib import Path

p = Path("backend/app/main.py")
s = p.read_text(encoding="utf-8")

# Imports
s = s.replace("import logging\n", "import logging\nimport os\n")
s = s.replace(
    "from backend.app.db import Repository\n",
    "from backend.app.db import Repository\nfrom backend.app.auth import create_access_token, decode_access_token, hash_password, verify_password\n"
)
s = s.replace(
    "    FeedbackIn,\n",
    "    FeedbackIn,\n    LoginIn,\n    UserCreateIn,\n"
)

# Bootstrap admin from environment
needle = "    repo.init_schema()\n"
insert = '''    repo.init_schema()

    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if admin_username and admin_password and not repo.get_user_by_username(admin_username):
        repo.create_user(admin_username, hash_password(admin_password), "admin")

    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if settings.is_production and len(jwt_secret) < 32:
        raise RuntimeError("Production requires JWT_SECRET_KEY with at least 32 characters.")
'''
if needle not in s:
    raise SystemExit("Could not find database initialization. No main.py changes made.")
s = s.replace(needle, insert, 1)

# Add principal middleware authentication
start = s.index("        # Health and readiness endpoints remain public.")
end = s.index("        # Enforce declared body size for non-batch requests.", start)

auth_block = '''        # Public endpoints: health, readiness and login.
        is_public = path in PUBLIC_PATHS or path == f"{API}/auth/login"
        request.state.principal = {
            "user_id": None,
            "username": "anonymous",
            "role": "analyst",
            "auth_type": "development",
        }

        if not is_public and (settings.api_key or jwt_secret):
            authorization = request.headers.get("authorization", "")
            bearer = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
            api_key = request.headers.get("x-api-key", "")
            principal = None

            if bearer and jwt_secret:
                try:
                    claims = decode_access_token(bearer, jwt_secret)
                    user = repo.get_user(int(claims["sub"]))
                    if user and user["is_active"] and user["role"] == claims["role"]:
                        principal = {
                            "user_id": user["id"],
                            "username": user["username"],
                            "role": user["role"],
                            "auth_type": "jwt",
                        }
                except (ValueError, TypeError):
                    principal = None

            # Legacy API key remains supported for analyst-level operations.
            if principal is None and settings.api_key:
                candidate = bearer or api_key
                if candidate and hmac.compare_digest(candidate, settings.api_key):
                    principal = {
                        "user_id": None,
                        "username": "api-key-client",
                        "role": "analyst",
                        "auth_type": "api_key",
                    }

            if principal is None:
                response = JSONResponse(
                    AppError(401, "unauthorized", "Valid authentication is required.").body(rid),
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                response.headers["X-Request-ID"] = rid
                response.headers["Cache-Control"] = "no-store"
                return response

            request.state.principal = principal

            admin_only = (
                path == f"{API}/users"
                or path.startswith(f"{API}/users/")
                or (
                    path.startswith(f"{API}/monitoring/retraining")
                    and request.method == "POST"
                )
            )
            if admin_only and principal["role"] != "admin":
                response = JSONResponse(
                    AppError(403, "forbidden", "Administrator role required.").body(rid),
                    status_code=403,
                )
                response.headers["X-Request-ID"] = rid
                response.headers["Cache-Control"] = "no-store"
                return response

        # Record authenticated activity without storing secrets or transaction data.
        principal = request.state.principal

'''
s = s[:start] + auth_block + s[end:]

# Fix invalid route decorators
s = s.replace('f"{API}/transactions/{transaction_id}"', 'f"{API}/transactions/{{transaction_id}}"')
s = s.replace('f"{API}/transactions/{transaction_id}/case"', 'f"{API}/transactions/{{transaction_id}}/case"')
s = s.replace('f"{API}/transactions/{transaction_id}/feedback"', 'f"{API}/transactions/{{transaction_id}}/feedback"')
s = s.replace('f"{API}/monitoring/retraining/{request_id}/transition"', 'f"{API}/monitoring/retraining/{{request_id}}/transition"')

# Add auth endpoints before health endpoints
marker = "    # ---------------------------------------------------------\n    # Health endpoints\n"
auth_routes = '''    # ---------------------------------------------------------
    # Authentication and user administration
    # ---------------------------------------------------------

    @app.post(f"{API}/auth/login", tags=["authentication"])
    def login(body: LoginIn, request: Request):
        if len(jwt_secret) < 32:
            raise AppError(503, "auth_not_configured", "JWT authentication is not configured.")

        user = repo.get_user_by_username(body.username)
        if not user or not user["is_active"] or not verify_password(body.password, user["password_hash"]):
            raise AppError(401, "invalid_credentials", "Username or password is incorrect.")

        token = create_access_token(
            user["id"], user["username"], user["role"],
            secret_key=jwt_secret, expires_minutes=60,
        )
        repo.record_audit(user["id"], user["username"], user["role"], "login", f"{API}/auth/login", request_id(request))
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
        }

    @app.post(f"{API}/users", tags=["administration"])
    def create_user(body: UserCreateIn, request: Request):
        try:
            user = repo.create_user(body.username, hash_password(body.password), body.role)
        except Exception as exc:
            import sqlite3
            if isinstance(exc, sqlite3.IntegrityError):
                raise AppError(409, "username_exists", "Username already exists.") from None
            raise
        principal = request.state.principal
        repo.record_audit(principal.get("user_id"), principal["username"], principal["role"], "user_created", f"{API}/users", request_id(request))
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "is_active": bool(user["is_active"]),
            "created_utc": user["created_utc"],
        }

    @app.get(f"{API}/users", tags=["administration"])
    def list_users():
        return [
            {**user, "is_active": bool(user["is_active"])}
            for user in repo.list_users()
        ]

'''
if marker not in s:
    raise SystemExit("Could not find health endpoint insertion point. No main.py changes made.")
s = s.replace(marker, auth_routes + marker, 1)

p.write_text(s, encoding="utf-8")
print("MAIN.PY AUTHENTICATION AND RBAC PATCH APPLIED")
