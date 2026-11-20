from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from torchvision.models import DenseNet121_Weights


LABELS = [
    "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration",
    "Mass", "Nodule", "Pneumonia", "Pneumothorax",
    "Consolidation", "Edema", "Emphysema", "Fibrosis",
    "Pleural_Thickening", "Hernia",
]

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "classification" / "nih14"
SPLIT_DIR = DATA_DIR / "splits"
IMAGE_DIR = DATA_DIR / "images"
MODEL_DIR = ROOT / "artifacts" / "models"


def seed_everything(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class ChestXrayDataset(Dataset):
    def __init__(self, csv_path: Path, image_size: int = 224):
        self.data = pd.read_csv(csv_path)

        required = ["Image Index", *LABELS]
        missing = [column for column in required if column not in self.data]
        if missing:
            raise ValueError(f"Missing CSV columns: {missing}")

        self.transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        row = self.data.iloc[index]
        image_path = IMAGE_DIR / str(row["Image Index"])

        if not image_path.is_file():
            raise FileNotFoundError(image_path)

        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image = self.transform(image)

        target = torch.tensor(
            row[LABELS].to_numpy(dtype=np.float32),
            dtype=torch.float32,
        )
        return image, target


def build_model(pretrained: bool = True):
    weights = DenseNet121_Weights.DEFAULT if pretrained else None
    model = models.densenet121(weights=weights)

    # Transfer-learning baseline: freeze ImageNet feature extractor.
    for parameter in model.features.parameters():
        parameter.requires_grad = False

    model.classifier = nn.Linear(model.classifier.in_features, len(LABELS))
    return model


def calculate_metrics(targets, probabilities):
    metrics = {}
    valid_auc = []

    for index, label in enumerate(LABELS):
        y_true = targets[:, index]
        y_score = probabilities[:, index]

        if len(np.unique(y_true)) < 2:
            auc = None
        else:
            auc = float(roc_auc_score(y_true, y_score))
            valid_auc.append(auc)

        metrics[label] = {
            "positive_samples": int(y_true.sum()),
            "auroc": auc,
        }

    metrics["macro_auroc"] = (
        float(np.mean(valid_auc)) if valid_auc else None
    )
    return metrics


def run_epoch(model, loader, criterion, device, optimizer=None):
    training = optimizer is not None
    model.train(training)

    total_loss = 0.0
    all_targets = []
    all_probabilities = []

    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)

        if training:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(training):
            logits = model(images)
            loss = criterion(logits, targets)

            if training:
                loss.backward()
                optimizer.step()

        total_loss += loss.item() * images.size(0)
        all_targets.append(targets.detach().cpu().numpy())
        all_probabilities.append(
            torch.sigmoid(logits).detach().cpu().numpy()
        )

    targets_np = np.concatenate(all_targets)
    probabilities_np = np.concatenate(all_probabilities)

    return (
        total_loss / len(loader.dataset),
        calculate_metrics(targets_np, probabilities_np),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--no-pretrained",
        action="store_true",
        help="Do not download/use ImageNet pretrained weights.",
    )
    args = parser.parse_args()

    if args.epochs < 1 or args.batch_size < 1:
        raise ValueError("Epochs and batch size must be positive.")

    seed_everything(args.seed)
    device = torch.device("cpu")
    print(f"Training device: {device}")

    train_dataset = ChestXrayDataset(
        SPLIT_DIR / "train.csv", args.image_size
    )
    val_dataset = ChestXrayDataset(
        SPLIT_DIR / "validation.csv", args.image_size
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )

    train_frame = train_dataset.data
    positives = train_frame[LABELS].sum().to_numpy(dtype=np.float32)
    negatives = len(train_frame) - positives

    # Cap extreme weights for rare classes to stabilize the first run.
    pos_weight = np.clip(
        negatives / np.maximum(positives, 1.0),
        1.0,
        20.0,
    )
    pos_weight_tensor = torch.tensor(pos_weight, dtype=torch.float32)

    model = build_model(pretrained=not args.no_pretrained).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight_tensor)
    optimizer = torch.optim.AdamW(
        model.classifier.parameters(),
        lr=args.learning_rate,
        weight_decay=1e-4,
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    best_val_loss = float("inf")
    history = []

    print(f"Training images: {len(train_dataset)}")
    print(f"Validation images: {len(val_dataset)}")
    print(f"Number of labels: {len(LABELS)}")
    print("Starting training...")

    for epoch in range(1, args.epochs + 1):
        train_loss, train_metrics = run_epoch(
            model, train_loader, criterion, device, optimizer
        )
        val_loss, val_metrics = run_epoch(
            model, val_loader, criterion, device
        )

        record = {
            "epoch": epoch,
            "train_loss": train_loss,
            "validation_loss": val_loss,
            "train_macro_auroc": train_metrics["macro_auroc"],
            "validation_macro_auroc": val_metrics["macro_auroc"],
        }
        history.append(record)

        print(json.dumps(record, indent=2))

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            checkpoint_path = MODEL_DIR / "nih14_densenet121_best.pt"

            torch.save({
                "model_name": "DenseNet121",
                "labels": LABELS,
                "model_state_dict": model.state_dict(),
                "image_size": args.image_size,
                "normalization": {
                    "mean": [0.485, 0.456, 0.406],
                    "std": [0.229, 0.224, 0.225],
                },
                "best_validation_loss": best_val_loss,
                "epoch": epoch,
                "pretrained": not args.no_pretrained,
                "training_config": vars(args),
            }, checkpoint_path)

            print(f"Best checkpoint saved: {checkpoint_path}")

    history_path = MODEL_DIR / "training_history.json"
    history_path.write_text(
        json.dumps(history, indent=2),
        encoding="utf-8",
    )
    print(f"Training history saved: {history_path}")
    print("Training completed.")


if __name__ == "__main__":
    main()