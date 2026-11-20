# API contract

Base URL: `/api/v1`. Protected routes require `Authorization: Bearer <JWT>`.

| Method | Endpoint | Access | Behavior |
|---|---|---|---|
| GET | `/health` | Public | API health and environment |
| POST | `/auth/register` | Public | Create a user account; never accepts a role |
| POST | `/auth/login` | Public | Authenticate on the user or admin portal |
| GET | `/auth/me` | Authenticated | Return the current active account |
| GET | `/studies/` | User | Search only the caller's studies (`q`, `modality`, `limit`, `offset`) |
| POST | `/studies/` | User | Validate and store a DICOM, PNG, JPEG, or NIfTI upload |
| GET | `/studies/literature?q=...` | User | Search PubMed E-utilities (`limit` 1–20); use general terms only |
| GET | `/studies/{study_id}` | Owner | Return study metadata; another owner's record returns 404 |
| GET | `/studies/{study_id}/image` | Owner | Return PNG/JPEG or a rendered monochrome DICOM preview; NIfTI preview is unavailable |
| GET | `/studies/{study_id}/report` | Owner | Download JSON metadata and an explicit no-analysis notice |
| POST | `/inference/analyze` | User | Validate a scan; returns 503 when no real model pipeline is configured |
| GET | `/admin/users` | Admin | List public account fields |
| PATCH | `/admin/users/{user_id}/status` | Admin | Enable/disable an account; administrators cannot disable themselves |
| GET | `/monitoring/summary` | Admin | Actual user/study counts and configured-service reachability |

Study metadata responses contain `study_id`, `original_filename`, `content_type`, `size_bytes`, `modality`, `created_at`, and `status`. Upload failures use 400 (empty/invalid filename), 413 (too large), or 415 (unsupported/mismatched content). Unauthenticated requests receive 401; role violations receive 403; missing or non-owned studies receive 404.

Inference intentionally does not return a success-shaped placeholder, label, confidence, heatmap, or segmentation. A configured trained and validated model pipeline is required before those response fields can be populated.
