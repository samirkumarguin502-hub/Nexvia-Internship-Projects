# Implementation status

## Implemented and locally verified
- [x] Separate user/admin login, PBKDF2 password hashing, HS256 JWTs, account deactivation, and server-side role checks
- [x] Owner-scoped, searchable SQLite study metadata and local file persistence
- [x] Upload validation for DICOM, PNG, JPEG, and structurally checked NIfTI; upload-size enforcement
- [x] Authenticated original PNG/JPEG and monochrome DICOM previews; image previews honor study ownership
- [x] JSON metadata report export with an explicit no-inference result
- [x] Live PubMed E-utilities literature search (do not enter patient information)
- [x] Optional Orthanc server-side DICOM forwarding; disabled by default
- [x] Admin account management, actual user/study counts, and service reachability/configuration status
- [x] Docker Compose persistence/health checks and GitHub Actions backend/frontend CI
- [x] Tests for RBAC, owner isolation, content validation, report/preview, JWT format, and service adapters

## Remaining integrations and validation
- [ ] Trained classification and segmentation models, CPU inference, model versioning and evaluation
- [ ] Grad-CAM generation and clinically meaningful segmentation overlays
- [ ] Similar-case embedding/index and validated retrieval
- [ ] MLflow experiment tracking and Evidently drift reports
- [ ] Dataset registry/versioning and licensed datasets
- [ ] Encryption at rest, audit logging, rate limiting, production deployment hardening and regulatory/privacy review
- [ ] Clinical validation, calibration, bias/subgroup evaluation, and external validation

No model weights or datasets are included. Inference returns HTTP 503 rather than fabricated predictions or metrics. NIfTI upload/storage is supported, but NIfTI image preview and inference are not. This prototype is not for clinical use and must not receive identifiable or sensitive patient data.
