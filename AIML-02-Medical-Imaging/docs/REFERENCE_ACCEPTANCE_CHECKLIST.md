# Reference image acceptance checklist

## Home / product showcase
- [x] Dark navy medical-tech hero with AIML-02 title and product description
- [x] Classification, segmentation, explainable AI and study retrieval feature tags
- [x] Industry-level feature list
- [x] Platform module cards
- [x] Overall architecture diagram (React, FastAPI, AI models, Orthanc, MLflow, Feast, Evidently)
- [x] Technology stack categories (Frontend, Backend, AI/ML, Data & Infrastructure, Monitoring, Deployment)
- [x] Submission deliverables and evaluation checklist

## Navigation / pages
- [x] Home
- [x] Diagnose / Upload & Analyze
- [x] Diagnosis results clearly show original-image preview when supported and no inference when unavailable
- [x] Similar Cases
- [x] Research Articles
- [x] History / Study Records with search and modality filter
- [x] Admin / Model Monitoring
- [x] About

## Required project feature coverage
- [x] UI integration point for classification (DenseNet / EfficientNet)
- [x] UI integration point for segmentation (MONAI 3D U-Net)
- [x] UI integration point for Grad-CAM
- [x] DICOM / Orthanc integration point
- [x] Dataset and preprocessing / DVC documentation
- [x] Medical research retrieval integration point
- [x] MLflow experiment tracking integration point
- [x] Evidently AI drift monitoring integration point
- [x] Docker and CI/CD technology documentation
- [x] Backend API scaffold and service adapter structure

## Not represented as completed
- [ ] Trained model weights and verified model metrics
- [ ] Actual clinical inference or clinical validation
- [ ] Production Orthanc integration
- [ ] Persistent database, authentication and audit trail
- [ ] Real literature / similar-case retrieval index
- [ ] Real MLflow and Evidently reports
- [ ] Production-grade medical image viewer and PDF report generation

These are backend/ML integration and validation tasks. Do not mark them complete until implemented and tested.

## Admin dashboard visual correction (reference screenshot)
- [x] Dedicated dark navy left administration sidebar
- [x] Sidebar navigation: Dashboard, Model Experiments, Data & Datasets, Model Monitoring, System Health
- [x] Actual registered-user and study totals from the API
- [x] Model, drift, MLflow, Evidently, and service status clearly report when unavailable
- [x] No synthetic accuracy, F1, drift, or experiment values
