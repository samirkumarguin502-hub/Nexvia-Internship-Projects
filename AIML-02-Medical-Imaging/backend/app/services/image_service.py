from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
import numpy as np
import pydicom
from pydicom.pixels import apply_modality_lut, apply_voi_lut


def render_preview(path: Path, content_type: str) -> tuple[bytes, str]:
    if content_type in ('image/png', 'image/jpeg'):
        return path.read_bytes(), content_type

    try:
        dataset = pydicom.dcmread(path)
        if not hasattr(dataset, 'PixelData') or int(dataset.Rows) * int(dataset.Columns) > 25_000_000:
            raise HTTPException(status_code=415, detail='DICOM image dimensions or pixel data are not supported')
        if int(getattr(dataset, 'SamplesPerPixel', 1)) != 1:
            raise HTTPException(status_code=415, detail='Color DICOM previews are not supported')
        pixels = np.asarray(dataset.pixel_array)
        if pixels.ndim == 3:
            pixels = pixels[0]
        pixels = np.asarray(apply_modality_lut(pixels, dataset), dtype=np.float32)
        try:
            pixels = np.asarray(apply_voi_lut(pixels, dataset), dtype=np.float32)
        except (AttributeError, ValueError):
            pass
        finite = pixels[np.isfinite(pixels)]
        if finite.size == 0:
            raise HTTPException(status_code=415, detail='DICOM image has no displayable pixel values')
        low, high = np.percentile(finite, [1, 99])
        if high <= low:
            high = low + 1
        normalized = np.clip((pixels - low) * (255.0 / (high - low)), 0, 255).astype(np.uint8)
        if getattr(dataset, 'PhotometricInterpretation', '') == 'MONOCHROME1':
            normalized = 255 - normalized
        output = BytesIO()
        Image.fromarray(normalized).save(output, format='PNG')
        return output.getvalue(), 'image/png'
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=415, detail='Unable to render a preview for this scan') from exc
