# Git workflow
Verify each milestone before committing:
```powershell
git status
cd frontend
npm run build
cd ..
git add frontend docs
git commit -m "feat: complete reference-aligned AIML-02 frontend"
```
Backend changes must be tested separately. Keep commits small and coherent. Check `.env`, patient data, DICOM files, private datasets and model weights are not tracked.
