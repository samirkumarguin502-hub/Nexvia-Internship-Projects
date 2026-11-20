import gzip
import struct

from app.services.upload_service import _nifti_header


def _nifti1() -> bytes:
    data = bytearray(368)
    struct.pack_into('<i', data, 0, 348)
    struct.pack_into('<8h', data, 40, 2, 2, 2, 1, 1, 1, 1, 1)
    struct.pack_into('<h', data, 70, 16)
    struct.pack_into('<f', data, 108, 352)
    data[344:348] = b'n+1\x00'
    return bytes(data)


def test_nifti_header_checks_dimensions_type_and_payload():
    nifti = _nifti1()
    assert _nifti_header(nifti, compressed=False)
    assert _nifti_header(gzip.compress(nifti), compressed=True)
    assert not _nifti_header(b'\x5c\x01\x00\x00', compressed=False)
