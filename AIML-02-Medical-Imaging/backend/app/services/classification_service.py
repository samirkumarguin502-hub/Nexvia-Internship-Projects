from functools import lru_cache
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

from app.core.config import settings


LABELS = [
    "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration",
    "Mass", "Nodule", "Pneumonia", "Pneumothorax",
    "Consolidation", "Edema", "Emphysema", "Fibrosis",
    "Pleural_Thickening", "Hernia",
]

MODEL_VERSION = "NIH14-baseline-v1"
DEVICE = torch.device("cpu")


def _model_path() -> Path:
    return Path(settings.MODEL_DIR) / "nih14_densenet121_best.pt"


@lru_cache(maxsize=1)
def load_classifier():
    path = _model_path()
    if not path.is_file():
        raise FileNotFoundError(f"Model checkpoint not found: {path}")

    checkpoint = torch.load(
        path,
        map_location=DEVICE,
        weights_only=True,
    )

    if checkpoint.get("labels") != LABELS:
        raise ValueError("Checkpoint label configuration mismatch")

    model = models.densenet121(weights=None)
    model.classifier = nn.Linear(model.classifier.in_features, len(LABELS))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(DEVICE)
    model.eval()

    image_size = int(checkpoint.get("image_size", 224))
    preprocess = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])

    return model, preprocess, checkpoint


def predict_image(image: Image.Image) -> dict:
    model, preprocess, checkpoint = load_classifier()

    image = image.convert("RGB")
    tensor = preprocess(image).unsqueeze(0).to(DEVICE)

    with torch.inference_mode():
        logits = model(tensor)
        probabilities = torch.sigmoid(logits)[0].cpu().tolist()

    predictions = {
        label: round(float(probability), 6)
        for label, probability in zip(LABELS, probabilities)
    }

    ranked = sorted(
        predictions.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    return {
        "model_name": "DenseNet121",
        "model_version": MODEL_VERSION,
        "predictions": predictions,
        "predicted_label": ranked[0][0],
        "top_predictions": [
            {"label": label, "probability": probability}
            for label, probability in ranked[:5]
        ],
        "threshold": 0.5,
        "checkpoint_epoch": checkpoint.get("epoch"),
        "probability_note": (
            "Raw sigmoid model scores; not clinically calibrated "
            "and not diagnostic probabilities."
        ),
    }