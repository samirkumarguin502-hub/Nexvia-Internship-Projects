from io import BytesIO
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.schemas.inference import InferenceResponse
from app.services.classification_service import predict_image
from app.services.explainability_service import generate_gradcam
from app.services.study_service import (
    create_study,
    get_study,
    save_study_analysis,
)
from app.services.upload_service import validate_upload


router = APIRouter()


def _gradcam_path(study_id: str) -> Path:
    """Return the server-side storage path for a study's Grad-CAM."""

    directory = Path(settings.UPLOAD_DIR).resolve() / "derived"
    directory.mkdir(parents=True, exist_ok=True)

    return directory / f"{study_id}_gradcam.png"


@router.post(
    "/analyze",
    response_model=InferenceResponse,
)
async def analyze_scan(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Analyze a chest X-ray using the NIH ChestX-ray14 DenseNet121 model.

    Supported inference formats: PNG, JPG and JPEG.
    """

    upload = await validate_upload(file)

    if upload.suffix not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(
            status_code=415,
            detail=(
                "The NIH DenseNet121 model currently supports "
                "PNG/JPEG images only. CT, MRI, DICOM and NIfTI "
                "require separate modality-specific inference pipelines."
            ),
        )

    # Decode the uploaded image.
    try:
        with Image.open(BytesIO(upload.data)) as source:
            source.verify()

        with Image.open(BytesIO(upload.data)) as source:
            image = source.convert("RGB")

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=415,
            detail="Unable to decode uploaded image",
        ) from exc

    # Run DenseNet121 classification.
    try:
        result = predict_image(image)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Classification checkpoint is not installed. "
                "No inference was performed."
            ),
        ) from exc

    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Image classification failed",
        ) from exc

    # Generate Grad-CAM.
    try:
        heatmap_bytes = generate_gradcam(
            image,
            result["predicted_label"],
        )

    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Grad-CAM generation failed",
        ) from exc

    # Save the original uploaded study.
    try:
        study = create_study(
            owner_id=int(current_user["id"]),
            filename=file.filename or "uploaded-image.png",
            upload=upload,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to save analyzed study",
        ) from exc

    study_id = study["study_id"]
    heatmap_path = _gradcam_path(study_id)
    temporary_path = heatmap_path.with_suffix(".tmp")

    # Save Grad-CAM artifact.
    try:
        with temporary_path.open("xb") as output:
            output.write(heatmap_bytes)
            output.flush()

        temporary_path.replace(heatmap_path)

    except OSError as exc:
        temporary_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Unable to save Grad-CAM visualization",
        ) from exc

    # Construct the complete inference response.
    response = InferenceResponse(
        study_id=study_id,
        status="analyzed",
        model_name=result["model_name"],
        model_version=result["model_version"],
        predicted_label=result["predicted_label"],
        calibrated_probability=None,
        predictions=result["predictions"],
        top_predictions=result["top_predictions"],
        probability_note=result["probability_note"],
        gradcam_url=(
            f"/api/v1/inference/studies/{study_id}/gradcam"
        ),
        segmentation_url=None,
        disclaimer=(
            "Educational/research output only; "
            "not for clinical use."
        ),
    )

    # Persist the actual inference result.
    try:
        saved = save_study_analysis(
            owner_id=int(current_user["id"]),
            study_id=study_id,
            analysis=response.model_dump(mode="json"),
        )

        if not saved:
            raise RuntimeError(
                "Analysis result was not associated with an owned study"
            )

    except Exception as exc:
        heatmap_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Unable to persist inference results",
        ) from exc

    return response


@router.get("/studies/{study_id}/gradcam")
def get_gradcam(
    study_id: str,
    current_user=Depends(get_current_user),
):
    """Retrieve the Grad-CAM image belonging to the authenticated user."""

    study = get_study(
        int(current_user["id"]),
        study_id,
    )

    if not study:
        raise HTTPException(
            status_code=404,
            detail="Study not found",
        )

    path = _gradcam_path(study_id)

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Grad-CAM not found",
        )

    return Response(
        content=path.read_bytes(),
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )