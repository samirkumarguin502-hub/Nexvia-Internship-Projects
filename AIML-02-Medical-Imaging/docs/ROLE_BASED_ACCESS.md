# Authentication and role-based access

## Roles
- `user`: register, sign in, upload supported scans, search and view only their own studies, export metadata reports, and query PubMed for general research topics.
- `admin`: all user capabilities plus account management and live service/storage health; model, dataset, and drift panels explicitly report when their integrations are unavailable.

## Security controls
- Public registration always creates `user`; clients cannot submit a role.
- Admin accounts are provisioned only from backend environment variables (`ADMIN_EMAIL`, `ADMIN_PASSWORD`, optional `ADMIN_FULL_NAME`) on startup. Never add an admin signup button.
- Passwords are salted PBKDF2-HMAC-SHA256 hashes. Passwords are never returned by API responses.
- API access uses HS256 JWT bearer tokens with expiration. Set a unique secret of at least 32 characters for production; development uses a process-random secret when none is set, so sessions do not survive a backend restart.
- The frontend hides Admin navigation for users, but this is only UX. Backend authorization is the actual security boundary.
- Study APIs apply the authenticated `owner_id` to every query; attempts to access another user's study return 404.

## Setup
1. Copy `backend/.env.example` to `backend/.env`.
2. Generate a long random `JWT_SECRET_KEY` and set a unique strong `ADMIN_PASSWORD` and `ADMIN_EMAIL`.
3. Start the API from the `backend` directory. The admin account is created on first startup if it does not exist.
4. User registration is available from the User portal. Admins sign in from the Admin portal using the provisioned credentials.
5. No default administrator credentials are provided. Admins sign in from the Admin portal using the environment-provisioned account.

## Limitations
No model weights or validated inference pipeline are included. Inference therefore returns HTTP 503 rather than fabricated output. Local study files and account records are not encrypted at rest; do not upload identifiable or sensitive patient data. This prototype is not for clinical use.
