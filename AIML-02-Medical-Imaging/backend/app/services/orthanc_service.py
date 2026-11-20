import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.core.config import settings


def store_dicom(data: bytes) -> str | None:
    if not settings.ORTHANC_ENABLED:
        return None

    request = Request(
        f'{settings.ORTHANC_URL.rstrip("/")}/instances',
        data=data,
        headers={'Content-Type': 'application/dicom'},
        method='POST',
    )
    if settings.ORTHANC_USERNAME:
        credentials = base64.b64encode(
            f'{settings.ORTHANC_USERNAME}:{settings.ORTHANC_PASSWORD}'.encode()
        ).decode()
        request.add_header('Authorization', f'Basic {credentials}')

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read(64_001))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail='Orthanc could not store the DICOM instance') from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=502, detail='Orthanc returned an invalid response') from exc

    instance_id = result.get('ID')
    if not isinstance(instance_id, str) or not instance_id:
        raise HTTPException(status_code=502, detail='Orthanc response did not contain an instance ID')
    return instance_id
