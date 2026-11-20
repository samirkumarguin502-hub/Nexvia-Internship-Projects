# AIML-02 setup on Windows

## Backend

From the repository root, in PowerShell:

```powershell
Set-Location backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env`. Set a unique secret and provision an administrator only if needed:

```dotenv
JWT_SECRET_KEY=<at least 32 random characters>
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<strong unique password>
```

Generate a secret using `python -c "import secrets; print(secrets.token_urlsafe(48))"`. There are no default admin credentials. Public registration only creates user accounts. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

Start the API in this terminal:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs`  
Health: `http://127.0.0.1:8000/health`

## Frontend

In another PowerShell terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The browser API base defaults to `http://127.0.0.1:8000/api/v1`; override it with `VITE_API_BASE_URL` when the API is served elsewhere.

## Docker

After configuring `backend/.env`, run from the project root:

```powershell
docker compose up --build
```

Docker serves the frontend on port 5173 and the API on port 8000. Database and upload files are kept in the named `api-data` volume.

## Implementation and safety status

Authenticated upload validation, user-owned study storage/history, JSON report export, PubMed search, and admin health/account/study metrics are implemented. Orthanc forwarding is disabled unless `ORTHANC_ENABLED=true` and server credentials/URL are configured. No trained inference model is included; inference returns HTTP 503 and does not fabricate a result. Grad-CAM, segmentation, similar-case retrieval, MLflow, Evidently, and dataset/model workflows still require real model artifacts or services. Local files are not encrypted at rest. This prototype is not for clinical use; do not upload identifiable or sensitive patient data.
