import json
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pytest

from src.train import train

FEATURE_NAMES = [
    "fixed_acidity",
    "volatile_acidity",
    "citric_acid",
    "residual_sugar",
    "chlorides",
    "free_sulfur_dioxide",
    "total_sulfur_dioxide",
    "density",
    "pH",
    "sulphates",
    "alcohol",
    "wine_type",
]


@pytest.fixture(autouse=True)
def isolated_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mlflow.end_run()
    mlflow.set_tracking_uri((tmp_path / "mlruns").as_uri())


def _make_temp_data(tmp_path):
    rng = np.random.default_rng(0)
    n = 200
    features = rng.random((n, len(FEATURE_NAMES)))
    target = rng.integers(0, 3, size=n)
    dataframe = pd.DataFrame(features, columns=FEATURE_NAMES)
    dataframe["target"] = target

    train_path = tmp_path / "train.csv"
    eval_path = tmp_path / "eval.csv"
    dataframe.iloc[:160].to_csv(train_path, index=False)
    dataframe.iloc[160:].to_csv(eval_path, index=False)
    return str(train_path), str(eval_path)


def test_train_returns_float(tmp_path):
    train_path, eval_path = _make_temp_data(tmp_path)
    accuracy = train(
        {"n_estimators": 10, "max_depth": 3, "min_samples_split": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert isinstance(accuracy, float)
    assert 0.0 <= accuracy <= 1.0


def test_metrics_and_report_files_created(tmp_path):
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3, "min_samples_split": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    metrics_path = Path("outputs/metrics.json")
    report_path = Path("outputs/report.txt")
    assert metrics_path.exists()
    assert report_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert "accuracy" in metrics
    assert "f1_score" in metrics
    assert metrics["train_samples"] == 160
    assert metrics["eval_samples"] == 40
    assert set(metrics["label_distribution"]) == {"0", "1", "2"}


def test_model_file_created(tmp_path):
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3, "min_samples_split": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert Path("models/model.pkl").exists()
