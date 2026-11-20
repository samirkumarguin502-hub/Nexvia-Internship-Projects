from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.api.v1.endpoints.auth import get_current_user
from app.schemas.literature import LiteratureSearchResponse
from app.schemas.study import StudySummary
from app.services.retrieval_service import search_pubmed
from app.services.image_service import render_preview
from app.services.study_service import create_study, get_study, get_study_asset, get_study_report, list_studies
from app.services.upload_service import validate_upload

router = APIRouter()


@router.get('/literature', response_model=LiteratureSearchResponse)
def search_literature(
    q: str = Query(min_length=3, max_length=200),
    limit: int = Query(default=10, ge=1, le=20),
    _current_user=Depends(get_current_user),
):
    return search_pubmed(q, limit)


@router.post('/', response_model=StudySummary, status_code=201)
async def upload_study(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    validated = await validate_upload(file)
    filename = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
    return create_study(current_user['id'], filename, validated)


@router.get('/', response_model=list[StudySummary])
def search_studies(
    q: str = Query(default='', max_length=100),
    modality: str | None = Query(default=None, pattern='^(XRAY|CT|MRI|UNKNOWN)$'),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
):
    return list_studies(current_user['id'], q, modality, limit, offset)


@router.get('/{study_id}/report')
def export_study_report(study_id: str, current_user=Depends(get_current_user)):
    report = get_study_report(current_user['id'], study_id)
    if not report:
        raise HTTPException(status_code=404, detail='Study not found')
    return JSONResponse(
        content=report,
        headers={'Content-Disposition': f'attachment; filename="study-{study_id}.json"'},
    )


@router.get('/{study_id}/image')
def get_study_image(study_id: str, current_user=Depends(get_current_user)):
    asset = get_study_asset(current_user['id'], study_id)
    if not asset:
        raise HTTPException(status_code=404, detail='Study not found')
    content, media_type = render_preview(*asset)
    return Response(content=content, media_type=media_type, headers={'Cache-Control': 'private, no-store'})


@router.get('/{study_id}', response_model=StudySummary)
def get_study_details(study_id: str, current_user=Depends(get_current_user)):
    study = get_study(current_user['id'], study_id)
    if not study:
        raise HTTPException(status_code=404, detail='Study not found')
    return study
