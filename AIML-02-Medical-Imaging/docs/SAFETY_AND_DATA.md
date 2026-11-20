# Safety, privacy and dataset governance
- Educational/research prototype only; never use for diagnosis or treatment.
- Do not upload identifiable or sensitive patient data. Local study files and account records are not encrypted at rest.
- Authentication, owner-scoped study access, and admin API authorization are implemented, but this is not production or regulated-system security.
- PubMed search terms are sent to NCBI. Use general literature topics only; never include patient names, identifiers, or protected health information.
- Orthanc forwarding is disabled by default; when enabled, DICOM bytes are sent to the configured server over its configured URL.
- No trained or validated model is included. Inference returns unavailable rather than generating a prediction; no Grad-CAM, segmentation, or performance values are fabricated.
- Use public datasets only under their terms and access agreements. Never commit scans, DICOM metadata, credentials, private datasets, or model weights.
- Before real-user studies, add encryption at rest, audit logging, retention controls, deployment hardening, and privacy/regulatory review.
- Any future model report must document patient-level splits, class imbalance, subgroup performance, external validation, calibration, licensing, and limitations.
