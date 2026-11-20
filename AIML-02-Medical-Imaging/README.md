# AIML-02 — AI-Assisted Medical Imaging and Diagnosis System

An educational/research prototype with a React/TypeScript frontend and a FastAPI backend. It is **not for clinical use** and must not be used to diagnose or treat patients.

## Implemented

- Separate user/admin login portals, PBKDF2 password hashing, signed bearer tokens, server-side role checks, account deactivation, and environment-provisioned administrator accounts.
- Authenticated uploads for DICOM, PNG, JPEG, and NIfTI files, with size and content validation.
- Private on-disk study storage, owner-scoped searchable history, study details, and JSON report export.
- Optional server-side Orthanc forwarding for DICOM when explicitly enabled.
- PubMed E-utilities literature search; search terms are sent to NCBI, so do not submit patient-identifiable information.
- Admin service health and live user/study counts. The dashboard reports unavailable integrations as unavailable rather than showing sample metrics.
- Docker Compose with persistent backend data and GitHub Actions for backend tests and frontend builds.

## Important limitations

No trained or validated classification/segmentation weights or inference pipeline are included. `/api/v1/inference/analyze` validates the upload and returns HTTP 503 rather than inventing a prediction. Grad-CAM, segmentation, similar-case retrieval, model training/evaluation, dataset versioning, MLflow experiment browsing, and Evidently drift reports are not implemented/configured. These UI areas clearly indicate unavailable integrations. The Orthanc client is optional and disabled by default.

Do not upload identifiable or sensitive patient data. Local study files and account records are not encrypted at rest; this prototype is not a production or regulated medical system.

## Run on Windows

Use two PowerShell terminals. Set the working directory to the project root first.

Backend:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` and set a unique `JWT_SECRET_KEY` (at least 32 characters), plus `ADMIN_EMAIL` and a strong `ADMIN_PASSWORD` if you need an administrator account. Generate a secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`; API docs are at `http://127.0.0.1:8000/docs`. Public registration always creates a user account. An administrator account is created at backend startup only when both administrator environment values are configured.

## Docker

Configure `backend/.env` as above, then from the repository root run:

```powershell
docker compose up --build
```

The app is at `http://localhost:5173`; API docs are at `http://localhost:8000/docs`. Docker persists its database and uploaded files in the `api-data` volume. Configure `VITE_API_BASE_URL` as a frontend build argument when exposing the API at a different browser-reachable URL.

## Tests and builds

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q
Set-Location ..\frontend
npm run build
```

See [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md), [docs/API_CONTRACT.md](docs/API_CONTRACT.md), [docs/ROLE_BASED_ACCESS.md](docs/ROLE_BASED_ACCESS.md), and [docs/SAFETY_AND_DATA.md](docs/SAFETY_AND_DATA.md) for additional setup, API, and safety details.
