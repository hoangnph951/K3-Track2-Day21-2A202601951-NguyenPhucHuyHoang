import json
from pathlib import Path

import mlflow
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FEATURES = [
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


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> None:
    expected_rows = {
        "train_phase1.csv": 2998,
        "eval.csv": 500,
        "train_phase2.csv": 2998,
    }
    for filename, row_count in expected_rows.items():
        csv_path = PROJECT_ROOT / "data" / filename
        pointer_path = PROJECT_ROOT / "data" / f"{filename}.dvc"
        check(csv_path.exists(), f"{filename} is available in the DVC workspace")
        check(pointer_path.exists(), f"{filename}.dvc exists")
        dataframe = pd.read_csv(csv_path)
        check(len(dataframe) == row_count, f"{filename} has {row_count} rows")
        check(
            list(dataframe.columns) == EXPECTED_FEATURES + ["target"],
            f"{filename} uses the serving schema",
        )
        check(not dataframe.isnull().any().any(), f"{filename} has no missing values")

    metrics = json.loads(
        (PROJECT_ROOT / "outputs/metrics.json").read_text(encoding="utf-8")
    )
    check("accuracy" in metrics and "f1_score" in metrics, "metrics contain accuracy and F1")
    check((PROJECT_ROOT / "outputs/report.txt").exists(), "performance report exists")
    check((PROJECT_ROOT / "models/model.pkl").exists(), "serialized model exists")

    params = yaml.safe_load((PROJECT_ROOT / "params.yaml").read_text(encoding="utf-8"))
    check(params["n_estimators"] > 0, "selected parameters are valid")

    mlflow.set_tracking_uri(f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}")
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("wine-quality-random-forest")
    check(experiment is not None, "MLflow experiment exists")
    runs = client.search_runs([experiment.experiment_id])
    check(len(runs) >= 3, "MLflow contains at least three experiment runs")
    check(
        all("accuracy" in run.data.metrics and "f1_score" in run.data.metrics for run in runs),
        "every MLflow experiment run contains accuracy and F1",
    )

    workflow = (PROJECT_ROOT / ".github/workflows/mlops.yml").read_text(
        encoding="utf-8"
    )
    for job_name in ["test:", "train:", "eval:", "deploy:"]:
        check(job_name in workflow, f"workflow contains {job_name[:-1]} job")
    check("TODO" not in workflow, "workflow contains no unfinished TODOs")

    print("\nLocal lab validation completed successfully.")


if __name__ == "__main__":
    main()
