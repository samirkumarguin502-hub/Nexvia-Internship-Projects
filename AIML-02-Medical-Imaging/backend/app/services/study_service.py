import json
import os
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.security import _db
from app.services.orthanc_service import store_dicom
from app.services.upload_service import ValidatedUpload


def _public_study(row: Any) -> dict[str, Any]:
    return {
        "study_id": row["study_id"],
        "original_filename": row["original_filename"],
        "content_type": row["content_type"],
        "size_bytes": row["size_bytes"],
        "modality": row["modality"],
        "created_at": row["created_at"],
        "status": row["status"],
    }


def _ensure_analysis_table(conn) -> None:
    """Create the inference-result table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS study_analyses (
            study_id TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL REFERENCES users(id),
            analysis_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (study_id)
                REFERENCES studies(study_id)
                ON DELETE CASCADE
        )
        """
    )


def create_study(
    owner_id: int,
    filename: str,
    upload: ValidatedUpload,
) -> dict[str, Any]:
    study_id = str(uuid.uuid4())

    safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    stored_name = f"{study_id}{upload.suffix}"

    storage_dir = Path(settings.UPLOAD_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)

    destination = storage_dir / stored_name
    temporary = storage_dir / f"{study_id}.tmp"

    try:
        with temporary.open("xb") as stored_file:
            stored_file.write(upload.data)
            stored_file.flush()
            os.fsync(stored_file.fileno())

        temporary.replace(destination)

        orthanc_instance_id = None

        if upload.suffix in (".dcm", ".dicom"):
            orthanc_instance_id = store_dicom(upload.data)

        with _db() as conn:
            conn.execute(
                """
                INSERT INTO studies (
                    study_id,
                    owner_id,
                    stored_name,
                    original_filename,
                    content_type,
                    modality,
                    size_bytes,
                    orthanc_instance_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    study_id,
                    owner_id,
                    stored_name,
                    safe_name,
                    upload.content_type,
                    upload.modality,
                    len(upload.data),
                    orthanc_instance_id,
                ),
            )

            row = conn.execute(
                "SELECT * FROM studies WHERE study_id = ?",
                (study_id,),
            ).fetchone()

        return _public_study(row)

    except Exception:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise


def mark_study_analyzed(
    owner_id: int,
    study_id: str,
) -> bool:
    """Update study status and modality for an owned study."""

    with _db() as conn:
        cursor = conn.execute(
            """
            UPDATE studies
            SET status = ?, modality = ?
            WHERE study_id = ? AND owner_id = ?
            """,
            ("analyzed", "XRAY", study_id, owner_id),
        )

        return cursor.rowcount == 1


def save_study_analysis(
    owner_id: int,
    study_id: str,
    analysis: dict[str, Any],
) -> bool:
    """
    Persist actual inference output for a study.

    The study status and analysis result are saved in one
    database transaction and scoped to the authenticated owner.
    """

    serialized = json.dumps(
        analysis,
        ensure_ascii=False,
        allow_nan=False,
    )

    with _db() as conn:
        _ensure_analysis_table(conn)

        cursor = conn.execute(
            """
            UPDATE studies
            SET status = ?, modality = ?
            WHERE study_id = ? AND owner_id = ?
            """,
            ("analyzed", "XRAY", study_id, owner_id),
        )

        if cursor.rowcount != 1:
            return False

        conn.execute(
            """
            INSERT INTO study_analyses (
                study_id,
                owner_id,
                analysis_json
            )
            VALUES (?, ?, ?)
            ON CONFLICT(study_id)
            DO UPDATE SET
                owner_id = excluded.owner_id,
                analysis_json = excluded.analysis_json,
                created_at = CURRENT_TIMESTAMP
            """,
            (study_id, owner_id, serialized),
        )

    return True


def list_studies(
    owner_id: int,
    query: str = "",
    modality: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:

    conditions = ["owner_id = ?"]
    values: list[Any] = [owner_id]

    if query.strip():
        conditions.append(
            "(study_id LIKE ? OR original_filename LIKE ?)"
        )
        values.extend(
            (
                f"%{query.strip()}%",
                f"%{query.strip()}%",
            )
        )

    if modality:
        conditions.append("modality = ?")
        values.append(modality)

    values.extend((limit, offset))

    with _db() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM studies
            WHERE {" AND ".join(conditions)}
            ORDER BY created_at DESC, study_id DESC
            LIMIT ? OFFSET ?
            """,
            values,
        ).fetchall()

    return [_public_study(row) for row in rows]


def get_study(
    owner_id: int,
    study_id: str,
) -> dict[str, Any] | None:

    with _db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM studies
            WHERE study_id = ? AND owner_id = ?
            """,
            (study_id, owner_id),
        ).fetchone()

    return _public_study(row) if row else None


def get_study_asset(
    owner_id: int,
    study_id: str,
) -> tuple[Path, str] | None:

    with _db() as conn:
        row = conn.execute(
            """
            SELECT stored_name, content_type
            FROM studies
            WHERE study_id = ? AND owner_id = ?
            """,
            (study_id, owner_id),
        ).fetchone()

    if not row:
        return None

    storage_dir = Path(settings.UPLOAD_DIR).resolve()
    asset_path = (storage_dir / row["stored_name"]).resolve()

    if asset_path.parent != storage_dir or not asset_path.is_file():
        return None

    return asset_path, row["content_type"]


def get_study_report(
    owner_id: int,
    study_id: str,
) -> dict[str, Any] | None:

    study = get_study(owner_id, study_id)

    if not study:
        return None

    with _db() as conn:
        _ensure_analysis_table(conn)

        row = conn.execute(
            """
            SELECT analysis_json, created_at
            FROM study_analyses
            WHERE study_id = ? AND owner_id = ?
            """,
            (study_id, owner_id),
        ).fetchone()

    if not row:
        return {
            **study,
            "analysis": None,
            "analysis_created_at": None,
            "message": (
                "No model output is available for this study. "
                "It may have been uploaded without inference."
            ),
            "disclaimer": (
                "Educational/research use only; not for clinical use."
            ),
        }

    analysis = json.loads(row["analysis_json"])

    return {
        **study,
        "analysis": analysis,
        "analysis_created_at": row["created_at"],
        "message": "Inference results retrieved successfully.",
        "disclaimer": (
            "Educational/research output only; "
            "not for clinical use."
        ),
    }


def count_studies() -> int:
    with _db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM studies"
        ).fetchone()[0]