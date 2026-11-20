from io import BytesIO
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from app.services.classification_service import (
    LABELS,
    load_classifier,
)


def generate_gradcam(image: Image.Image, target_label: str) -> bytes:
    if target_label not in LABELS:
        raise ValueError("Unsupported Grad-CAM target label")

    model, preprocess, _checkpoint = load_classifier()
    model.eval()

    activations = {}
    gradients = {}

    target_layer = model.features.denseblock4

    def forward_hook(_module, _inputs, output):
        activations["value"] = output
        output.register_hook(
            lambda gradient: gradients.__setitem__("value", gradient)
        )

    handle = target_layer.register_forward_hook(forward_hook)

    try:
        image = image.convert("RGB")
        original_size = image.size
        tensor = preprocess(image).unsqueeze(0)

        model.zero_grad(set_to_none=True)
        logits = model(tensor)
        class_index = LABELS.index(target_label)
        logits[0, class_index].backward()

        feature_map = activations["value"]
        gradient_map = gradients["value"]

        weights = gradient_map.mean(dim=(2, 3), keepdim=True)
        cam = (weights * feature_map).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)

        cam = F.interpolate(
            cam,
            size=(original_size[1], original_size[0]),
            mode="bilinear",
            align_corners=False,
        )[0, 0]

        cam = cam.detach().cpu().numpy()
        minimum = float(cam.min())
        maximum = float(cam.max())

        if maximum > minimum:
            cam = (cam - minimum) / (maximum - minimum)
        else:
            cam = np.zeros_like(cam)

        # Simple red-yellow heatmap, independent of plotting libraries.
        red = np.clip(1.5 - np.abs(4.0 * cam - 3.0), 0, 1)
        green = np.clip(1.5 - np.abs(4.0 * cam - 2.0), 0, 1)
        blue = np.clip(1.5 - np.abs(4.0 * cam - 1.0), 0, 1)

        heatmap = np.stack([red, green, blue], axis=-1)
        heatmap_image = Image.fromarray(
            (heatmap * 255).astype(np.uint8)
        ).convert("RGB")

        base = image.convert("RGB")
        overlay = Image.blend(base, heatmap_image, alpha=0.40)

        output = BytesIO()
        overlay.save(output, format="PNG")
        return output.getvalue()

    finally:
        handle.remove()
        model.zero_grad(set_to_none=True)