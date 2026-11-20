from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.core import security
from app.core.config import settings
from app.main import app


# ============================================================
# TEST HELPERS
# ============================================================

def _png() -> bytes:
    """Generate a small valid PNG image for testing."""

    image = Image.new(
        "RGB",
        (4, 4),
        color="white",
    )

    output = BytesIO()
    image.save(output, format="PNG")

    return output.getvalue()


def _register(
    client: TestClient,
    email: str,
) -> dict[str, str]:
    """Register a test user and return authentication headers."""

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Test User",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


# ============================================================
# TEST 1: STUDY STORAGE, SEARCH AND USER PRIVACY
# ============================================================

def test_studies_are_persisted_searchable_and_private(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "DB_PATH",
        tmp_path / "auth.sqlite3",
    )

    monkeypatch.setattr(
        settings,
        "UPLOAD_DIR",
        str(tmp_path / "uploads"),
    )

    with TestClient(app) as client:

        owner_headers = _register(
            client,
            "owner@example.com",
        )

        other_headers = _register(
            client,
            "other@example.com",
        )

        # Upload study.
        uploaded = client.post(
            "/api/v1/studies/",
            headers=owner_headers,
            files={
                "file": (
                    "chest.png",
                    _png(),
                    "image/png",
                ),
            },
        )

        assert uploaded.status_code == 201

        study = uploaded.json()

        assert study["modality"] == "UNKNOWN"
        assert study["original_filename"] == "chest.png"

        # Verify uploaded file exists.
        stored_files = list(
            (tmp_path / "uploads").glob(
                f"{study['study_id']}.*"
            )
        )

        assert len(stored_files) == 1

        # Verify image preview.
        preview = client.get(
            f"/api/v1/studies/{study['study_id']}/image",
            headers=owner_headers,
        )

        assert preview.status_code == 200
        assert preview.headers["content-type"] == "image/png"
        assert preview.content == _png()

        # Another user must not access this image.
        unauthorized_preview = client.get(
            f"/api/v1/studies/{study['study_id']}/image",
            headers=other_headers,
        )

        assert unauthorized_preview.status_code == 404

        # Owner can search their study.
        owner_list = client.get(
            "/api/v1/studies/?q=chest",
            headers=owner_headers,
        )

        assert owner_list.status_code == 200

        assert [
            row["study_id"]
            for row in owner_list.json()
        ] == [study["study_id"]]

        # Other user cannot see owner's studies.
        other_list = client.get(
            "/api/v1/studies/",
            headers=other_headers,
        )

        assert other_list.status_code == 200
        assert other_list.json() == []

        # Other user cannot access study details.
        unauthorized_details = client.get(
            f"/api/v1/studies/{study['study_id']}",
            headers=other_headers,
        )

        assert unauthorized_details.status_code == 404

        # Verify report.
        report = client.get(
            f"/api/v1/studies/{study['study_id']}/report",
            headers=owner_headers,
        )

        assert report.status_code == 200
        assert report.json()["analysis"] is None
        assert "No model output" in report.json()["message"]


# ============================================================
# TEST 2: INVALID AND UNSUPPORTED UPLOADS
# ============================================================

def test_upload_rejects_mismatched_and_unsupported_content(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "DB_PATH",
        tmp_path / "auth.sqlite3",
    )

    monkeypatch.setattr(
        settings,
        "UPLOAD_DIR",
        str(tmp_path / "uploads"),
    )

    with TestClient(app) as client:

        headers = _register(
            client,
            "user@example.com",
        )

        # Invalid image content.
        invalid_png = client.post(
            "/api/v1/studies/",
            headers=headers,
            files={
                "file": (
                    "scan.png",
                    b"not an image",
                    "image/png",
                ),
            },
        )

        # Malformed PNG content.
        malformed_png = client.post(
            "/api/v1/studies/",
            headers=headers,
            files={
                "file": (
                    "malformed.png",
                    bytes.fromhex(
                        "89504e470d0a1a0a0000000d4948445200000001000000010804000000b5"
                        "1c0c020000000b4944415478da63fcff1f0003030200efbfad8f00000000"
                        "49454e44ae426082"
                    ),
                    "image/png",
                ),
            },
        )

        # Unsupported file extension.
        unsupported = client.post(
            "/api/v1/studies/",
            headers=headers,
            files={
                "file": (
                    "scan.txt",
                    b"content",
                    "text/plain",
                ),
            },
        )

        assert invalid_png.status_code == 415
        assert malformed_png.status_code == 415
        assert unsupported.status_code == 415


# ============================================================
# TEST 3: UPLOAD SIZE LIMIT
# ============================================================

def test_upload_enforces_configured_size_limit(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "DB_PATH",
        tmp_path / "auth.sqlite3",
    )

    monkeypatch.setattr(
        settings,
        "UPLOAD_DIR",
        str(tmp_path / "uploads"),
    )

    monkeypatch.setattr(
        settings,
        "MAX_UPLOAD_MB",
        1,
    )

    with TestClient(app) as client:

        headers = _register(
            client,
            "user@example.com",
        )

        response = client.post(
            "/api/v1/studies/",
            headers=headers,
            files={
                "file": (
                    "scan.png",
                    b"x" * (1024 * 1024 + 1),
                    "image/png",
                ),
            },
        )

        assert response.status_code == 413


# ============================================================
# TEST 4: INFERENCE MUST NOT CLAIM SUCCESS WITHOUT A MODEL
# ============================================================

def test_inference_does_not_claim_success_without_models(
    tmp_path,
    monkeypatch,
):
    """
    Simulate a missing classification checkpoint.

    The API must return HTTP 503 and must not report
    a successful prediction.
    """

    from app.api.v1.endpoints import inference as inference_endpoint

    monkeypatch.setattr(
        security,
        "DB_PATH",
        tmp_path / "auth.sqlite3",
    )

    def missing_model(_image):
        raise FileNotFoundError(
            "Model checkpoint unavailable"
        )

    # Replace only the classifier used by this test.
    monkeypatch.setattr(
        inference_endpoint,
        "predict_image",
        missing_model,
    )

    with TestClient(app) as client:

        headers = _register(
            client,
            "user@example.com",
        )

        response = client.post(
            "/api/v1/inference/analyze",
            headers=headers,
            files={
                "file": (
                    "scan.png",
                    _png(),
                    "image/png",
                ),
            },
        )

        assert response.status_code == 503

        assert (
            "No inference was performed"
            in response.json()["detail"]
        )


# ============================================================
# TEST 5: INFERENCE REJECTS NON-X-RAY FORMATS
# ============================================================

def test_inference_rejects_nifti_and_dicom(
    tmp_path,
    monkeypatch,
):
    """
    The NIH DenseNet121 endpoint must not accept
    CT/MRI/DICOM/NIfTI as chest X-ray input.
    """

    monkeypatch.setattr(
        security,
        "DB_PATH",
        tmp_path / "auth.sqlite3",
    )

    monkeypatch.setattr(
        settings,
        "UPLOAD_DIR",
        str(tmp_path / "uploads"),
    )

    with TestClient(app) as client:

        headers = _register(
            client,
            "format-test@example.com",
        )

        # Minimal invalid NIfTI-like file.
        nifti_response = client.post(
            "/api/v1/inference/analyze",
            headers=headers,
            files={
                "file": (
                    "scan.nii",
                    b"invalid nifti data",
                    "application/octet-stream",
                ),
            },
        )

        # Invalid DICOM file.
        dicom_response = client.post(
            "/api/v1/inference/analyze",
            headers=headers,
            files={
                "file": (
                    "scan.dcm",
                    b"invalid dicom data",
                    "application/dicom",
                ),
            },
        )

        assert nifti_response.status_code == 415
        assert dicom_response.status_code == 415