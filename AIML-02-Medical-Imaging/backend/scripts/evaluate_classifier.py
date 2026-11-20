from pathlib import Path
import json

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader

from train_classifier import (
    LABELS,
    MODEL_DIR,
    SPLIT_DIR,
    ChestXrayDataset,
    build_model,
)


def main():
    checkpoint_path = MODEL_DIR / "nih14_densenet121_best.pt"
    test_csv = SPLIT_DIR / "test.csv"

    if not checkpoint_path.exists():
        raise FileNotFoundError(checkpoint_path)

    if not test_csv.exists():
        raise FileNotFoundError(test_csv)

    device = torch.device("cpu")

    dataset = ChestXrayDataset(test_csv, image_size=224)
    loader = DataLoader(
        dataset,
        batch_size=4,
        shuffle=False,
        num_workers=0,
    )

    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=True,
    )

    if checkpoint["labels"] != LABELS:
        raise ValueError("Checkpoint label order does not match.")

    model = build_model(pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    all_targets = []
    all_probabilities = []

    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device)
            probabilities = torch.sigmoid(model(images))

            all_targets.append(targets.numpy())
            all_probabilities.append(probabilities.cpu().numpy())

    y_true = np.concatenate(all_targets)
    y_prob = np.concatenate(all_probabilities)
    y_pred = (y_prob >= 0.5).astype(np.int32)

    results = {
        "model": "DenseNet121",
        "dataset": "NIH ChestX-ray14 partial subset",
        "test_samples": len(dataset),
        "threshold": 0.5,
        "labels": {},
    }

    auc_values = []
    ap_values = []

    for index, label in enumerate(LABELS):
        truth = y_true[:, index]
        probability = y_prob[:, index]
        prediction = y_pred[:, index]

        auc = None
        ap = None

        if len(np.unique(truth)) == 2:
            auc = float(roc_auc_score(truth, probability))
            ap = float(average_precision_score(truth, probability))
            auc_values.append(auc)
            ap_values.append(ap)

        results["labels"][label] = {
            "positive_samples": int(truth.sum()),
            "auroc": auc,
            "average_precision": ap,
            "precision": float(
                precision_score(truth, prediction, zero_division=0)
            ),
            "recall": float(
                recall_score(truth, prediction, zero_division=0)
            ),
            "f1": float(
                f1_score(truth, prediction, zero_division=0)
            ),
        }

    results["macro_auroc"] = (
        float(np.mean(auc_values)) if auc_values else None
    )
    results["macro_average_precision"] = (
        float(np.mean(ap_values)) if ap_values else None
    )
    results["macro_f1"] = float(
        f1_score(y_true, y_pred, average="macro", zero_division=0)
    )

    output_path = MODEL_DIR / "test_metrics.json"
    output_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(results, indent=2))
    print(f"\nTest metrics saved: {output_path}")


if __name__ == "__main__":
    main()