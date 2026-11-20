from pathlib import Path
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "classification" / "nih14"
CSV_PATH = DATA_DIR / "Data_Entry_2017_v2020.csv"
IMAGE_DIR = DATA_DIR / "images"
OUTPUT_DIR = DATA_DIR / "splits"

LABELS = [
    "Atelectasis",
    "Cardiomegaly",
    "Effusion",
    "Infiltration",
    "Mass",
    "Nodule",
    "Pneumonia",
    "Pneumothorax",
    "Consolidation",
    "Edema",
    "Emphysema",
    "Fibrosis",
    "Pleural_Thickening",
    "Hernia",
]

def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(IMAGE_DIR)

    df = pd.read_csv(CSV_PATH)
    df["Image Index"] = df["Image Index"].astype(str)
    df["Patient ID"] = df["Patient ID"].astype(str)

    available = {p.name for p in IMAGE_DIR.glob("*.png")}
    df = df[df["Image Index"].isin(available)].copy()

    if df.empty:
        raise RuntimeError("No matching images found.")

    for label in LABELS:
        df[label] = df["Finding Labels"].apply(
            lambda value: int(label in str(value).split("|"))
        )

    # First split: 80% train, 20% temporary.
    first = GroupShuffleSplit(
        n_splits=1, test_size=0.20, random_state=42
    )
    train_idx, temp_idx = next(
        first.split(df, groups=df["Patient ID"])
    )

    train = df.iloc[train_idx].copy()
    temp = df.iloc[temp_idx].copy()

    # Second split: 10% validation, 10% test overall.
    second = GroupShuffleSplit(
        n_splits=1, test_size=0.50, random_state=42
    )
    val_idx, test_idx = next(
        second.split(temp, groups=temp["Patient ID"])
    )

    val = temp.iloc[val_idx].copy()
    test = temp.iloc[test_idx].copy()

    # Verify no patient leakage.
    train_ids = set(train["Patient ID"])
    val_ids = set(val["Patient ID"])
    test_ids = set(test["Patient ID"])

    assert not (train_ids & val_ids)
    assert not (train_ids & test_ids)
    assert not (val_ids & test_ids)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    train.to_csv(OUTPUT_DIR / "train.csv", index=False)
    val.to_csv(OUTPUT_DIR / "validation.csv", index=False)
    test.to_csv(OUTPUT_DIR / "test.csv", index=False)

    print("Dataset split completed")
    print("Total images:", len(df))
    print("Train:", len(train))
    print("Validation:", len(val))
    print("Test:", len(test))
    print("Unique patients:", df["Patient ID"].nunique())
    print("Patient leakage: NONE")
    print("Labels:", len(LABELS))
    print("Output:", OUTPUT_DIR)

if __name__ == "__main__":
    main()