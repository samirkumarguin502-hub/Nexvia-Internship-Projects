# Architecture
```text
React + TypeScript UI
  ├─ User/admin authentication and role-specific navigation
  └─ Authenticated REST calls
       |
       v
FastAPI API layer
  ├─ PBKDF2 password hashes, signed bearer tokens, server-side RBAC
  ├─ Content-validated uploads and owner-scoped study APIs
  ├─ Local SQLite metadata and private file storage
  ├─ PubMed E-utilities literature search (general terms only)
  ├─ Optional server-side Orthanc DICOM forwarding
  └─ Live account/study totals and configured-service probes for admins

Not configured: trained classifier, MONAI segmentation, Grad-CAM, similar-case embeddings,
dataset/version registry, MLflow experiments, and Evidently drift reports.
```
No inference result is returned until real model artifacts and a validated pipeline are supplied. Do not upload identifiable or sensitive patient data; local files are not encrypted at rest. Before real-user or clinical use, add encryption, audit/retention controls, deployment hardening, privacy/regulatory review, and validated model evaluation. Keep imaging data out of Git.
