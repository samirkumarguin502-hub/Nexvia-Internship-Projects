from dataclasses import dataclass
from gzip import GzipFile
from io import BytesIO
from pathlib import PurePath
import math
import struct

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
import pydicom

from app.core.config import settings


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    suffix: str
    content_type: str
    modality: str


def _nifti_header(data: bytes, compressed: bool) -> bool:
    try:
        stream = GzipFile(fileobj=BytesIO(data)) if compressed else BytesIO(data)
        header = stream.read(540)
        if len(header) < 4:
            return False
        endian = '<' if int.from_bytes(header[:4], 'little') in (348, 540) else '>'
        header_size = struct.unpack(f'{endian}i', header[:4])[0]
        if header_size == 348:
            if len(header) < 352 or header[344:348] != b'n+1\x00':
                return False
            dims = struct.unpack(f'{endian}8h', header[40:56])
            datatype = struct.unpack(f'{endian}h', header[70:72])[0]
            offset = struct.unpack(f'{endian}f', header[108:112])[0]
        elif header_size == 540:
            if len(header) < 540 or header[4:8] != b'n+2\x00':
                return False
            dims = struct.unpack(f'{endian}8q', header[16:80])
            datatype = struct.unpack(f'{endian}h', header[12:14])[0]
            offset = struct.unpack(f'{endian}q', header[168:176])[0]
        else:
            return False
        bytes_per_voxel = {1: 1, 2: 1, 4: 2, 8: 4, 16: 4, 32: 8, 64: 8, 128: 3, 256: 1, 512: 2, 768: 4, 1024: 8, 1280: 16, 1536: 8, 1792: 16}.get(datatype)
        if not bytes_per_voxel or not 1 <= dims[0] <= 7 or any(dim <= 0 for dim in dims[1:dims[0] + 1]):
            return False
        minimum_offset = 352 if header_size == 348 else 544
        if not math.isfinite(offset) or offset < minimum_offset:
            return False
        voxel_count = math.prod(dims[1:dims[0] + 1])
        if not compressed and len(data) < math.ceil(offset) + voxel_count * bytes_per_voxel:
            return False
        return True
    except (OSError, EOFError):
        return False


def _validate_content(name: str, data: bytes) -> tuple[str, str, str]:
    suffix = ''.join(PurePath(name).suffixes).lower()
    if suffix in ('.png', '.jpg', '.jpeg'):
        try:
            with Image.open(BytesIO(data)) as image:
                image.verify()
                if suffix == '.png' and image.format != 'PNG':
                    raise ValueError('File extension does not match image content')
                if suffix in ('.jpg', '.jpeg') and image.format != 'JPEG':
                    raise ValueError('File extension does not match image content')
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
            raise HTTPException(status_code=415, detail='Invalid or mismatched image file') from exc
        return suffix, 'image/png' if suffix == '.png' else 'image/jpeg', 'UNKNOWN'

    if suffix in ('.nii', '.nii.gz'):
        if not _nifti_header(data, suffix.endswith('.gz')):
            raise HTTPException(status_code=415, detail='Invalid NIfTI header')
        content_type = 'application/gzip' if suffix.endswith('.gz') else 'application/octet-stream'
        return suffix, content_type, 'UNKNOWN'

    if suffix in ('.dcm', '.dicom'):
        try:
            dataset = pydicom.dcmread(BytesIO(data), stop_before_pixels=True, force=False)
        except Exception as exc:
            raise HTTPException(status_code=415, detail='Invalid DICOM file') from exc
        modality = str(getattr(dataset, 'Modality', '')).upper()
        modality = {'CR': 'XRAY', 'DX': 'XRAY', 'DR': 'XRAY', 'CT': 'CT', 'MR': 'MRI'}.get(modality, 'UNKNOWN')
        return suffix, 'application/dicom', modality

    raise HTTPException(status_code=415, detail='Unsupported file type')


async def validate_upload(file: UploadFile) -> ValidatedUpload:
    name = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
    if not name or name in ('.', '..'):
        raise HTTPException(status_code=400, detail='A valid filename is required')

    data = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    await file.seek(0)
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail='File too large')
    if not data:
        raise HTTPException(status_code=400, detail='Empty upload')

    suffix, content_type, modality = _validate_content(name, data)
    return ValidatedUpload(data=data, suffix=suffix, content_type=content_type, modality=modality)
