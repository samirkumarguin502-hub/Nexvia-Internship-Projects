import base64
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends

from app.api.v1.endpoints.auth import require_admin
from app.core.config import settings
from app.core.security import count_users
from app.services.study_service import count_studies

router = APIRouter(dependencies=[Depends(require_admin)])


def _service_status(url: str, username: str = '', password: str = '') -> dict[str, str]:
    if not url:
        return {'status': 'not_configured'}
    request = Request(url, method='GET')
    if username:
        credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        request.add_header('Authorization', f'Basic {credentials}')
    try:
        with urlopen(request, timeout=1) as response:
            return {'status': 'available' if 200 <= response.status < 300 else 'unavailable'}
    except HTTPError as error:
        return {'status': 'unavailable', 'http_status': str(error.code)}
    except (URLError, TimeoutError, OSError):
        return {'status': 'unavailable'}


@router.get('/summary')
def summary():
    orthanc_url = f'{settings.ORTHANC_URL.rstrip("/")}/system' if settings.ORTHANC_ENABLED else ''
    mlflow_url = f'{settings.MLFLOW_TRACKING_URI.rstrip("/")}/health' if settings.MLFLOW_TRACKING_URI else ''
    return {
        'metrics': {
            'registered_users': count_users(),
            'stored_studies': count_studies(),
        },
        'services': {
            'api': {'status': 'available'},
            'orthanc': _service_status(orthanc_url, settings.ORTHANC_USERNAME, settings.ORTHANC_PASSWORD) if settings.ORTHANC_ENABLED else {'status': 'disabled'},
            'mlflow': _service_status(mlflow_url),
            'evidently': {'status': 'not_configured'},
        },
        'model': {
            'status': 'unavailable',
            'reason': 'No trained model and validated inference pipeline are configured.',
        },
        'drift': {
            'status': 'unavailable',
            'reason': 'Evidently AI and reference data are not configured.',
        },
    }
