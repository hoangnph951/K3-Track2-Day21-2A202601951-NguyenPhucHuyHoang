import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

EVAL_THRESHOLD = 0.70
TARGET_COLUMN = "target"


def _validate_dataset(df: pd.DataFrame, path: str) -> None:
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Dataset {path!r} is missing the '{TARGET_COLUMN}' column")
    if df.empty:
        raise ValueError(f"Dataset {path!r} is empty")
    if df.isnull().any().any():
        raise ValueError(f"Dataset {path!r} contains missing values")


def train(
    params: dict,
    data_path: str = "data/train_phase1.csv",
    eval_path: str = "data/eval.csv",
) -> float:
    """Train a RandomForest model, track it with MLflow, and save artifacts."""
    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)
    _validate_dataset(df_train, data_path)
    _validate_dataset(df_eval, eval_path)

    X_train = df_train.drop(columns=[TARGET_COLUMN])
    y_train = df_train[TARGET_COLUMN]
    X_eval = df_eval.drop(columns=[TARGET_COLUMN])
    y_eval = df_eval[TARGET_COLUMN]

    if list(X_train.columns) != list(X_eval.columns):
        raise ValueError("Training and evaluation feature columns do not match")

    label_distribution = {
        str(int(label)): float(ratio)
        for label, ratio in y_train.value_counts(normalize=True).sort_index().items()
    }
    for label in sorted(set(y_train.unique())):
        ratio = label_distribution[str(int(label))]
        if ratio < 0.10:
            print(f"WARNING: class {label} represents only {ratio:.2%} of training data")

    run_name = (
        f"rf-n{params.get('n_estimators')}"
        f"-d{params.get('max_depth')}"
        f"-s{params.get('min_samples_split')}"
    )
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)

        model = RandomForestClassifier(**params, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        predictions = model.predict(X_eval)
        accuracy = float(accuracy_score(y_eval, predictions))
        f1 = float(f1_score(y_eval, predictions, average="weighted", zero_division=0))

        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("f1_score", f1)
        mlflow.sklearn.log_model(model, artifact_path="model")

        metrics = {
            "accuracy": accuracy,
            "f1_score": f1,
            "train_samples": int(len(df_train)),
            "eval_samples": int(len(df_eval)),
            "label_distribution": label_distribution,
        }

        outputs_dir = Path("outputs")
        models_dir = Path("models")
        outputs_dir.mkdir(parents=True, exist_ok=True)
        models_dir.mkdir(parents=True, exist_ok=True)

        metrics_path = outputs_dir / "metrics.json"
        metrics_path.write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        report = classification_report(y_eval, predictions, zero_division=0)
        matrix = confusion_matrix(y_eval, predictions)
        report_path = outputs_dir / "report.txt"
        report_path.write_text(
            "Classification report\n"
            "=====================\n"
            f"{report}\n"
            "Confusion matrix\n"
            "================\n"
            f"{matrix}\n",
            encoding="utf-8",
        )

        model_path = models_dir / "model.pkl"
        joblib.dump(model, model_path)
        mlflow.log_artifact(str(metrics_path), artifact_path="reports")
        mlflow.log_artifact(str(report_path), artifact_path="reports")

        print(f"Accuracy: {accuracy:.4f} | F1: {f1:.4f}")
        print(f"Training samples: {len(df_train)} | Evaluation samples: {len(df_eval)}")

    return accuracy


if __name__ == "__main__":
    os.environ.setdefault("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    with open("params.yaml", encoding="utf-8") as params_file:
        training_params = yaml.safe_load(params_file)
    train(training_params)
