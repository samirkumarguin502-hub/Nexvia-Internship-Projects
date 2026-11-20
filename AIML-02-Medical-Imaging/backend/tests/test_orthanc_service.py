from app.core.config import settings
from app.services import orthanc_service


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size: int):
        return b'{"ID":"orthanc-instance-id"}'


def test_dicom_forwarding_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, 'ORTHANC_ENABLED', False)
    assert orthanc_service.store_dicom(b'dicom bytes') is None


def test_enabled_dicom_forwarding_uses_server_credentials(monkeypatch):
    captured = {}
    monkeypatch.setattr(settings, 'ORTHANC_ENABLED', True)
    monkeypatch.setattr(settings, 'ORTHANC_URL', 'http://orthanc:8042')
    monkeypatch.setattr(settings, 'ORTHANC_USERNAME', 'service-user')
    monkeypatch.setattr(settings, 'ORTHANC_PASSWORD', 'service-password')

    def fake_urlopen(request, timeout):
        captured['request'] = request
        captured['timeout'] = timeout
        return _Response()

    monkeypatch.setattr(orthanc_service, 'urlopen', fake_urlopen)

    assert orthanc_service.store_dicom(b'dicom bytes') == 'orthanc-instance-id'
    assert captured['request'].full_url == 'http://orthanc:8042/instances'
    assert captured['request'].get_header('Authorization').startswith('Basic ')
    assert captured['timeout'] == 10
