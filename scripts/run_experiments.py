import json
import os
from pathlib import Path

import mlflow
import yaml

from src.train import train

EXPERIMENTS = [
    {"n_estimators": 50, "max_depth": 3, "min_samples_split": 2},
    {"n_estimators": 100, "max_depth": 5, "min_samples_split": 2},
    {"n_estimators": 200, "max_depth": 10, "min_samples_split": 5},
    {"n_estimators": 200, "max_depth": None, "min_samples_split": 2},
]


def main() -> None:
    os.environ.setdefault("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("wine-quality-random-forest")

    results = []
    for index, params in enumerate(EXPERIMENTS, start=1):
        print(f"\nRunning experiment {index}/{len(EXPERIMENTS)}: {params}")
        accuracy = train(params)
        metrics = json.loads(
            Path("outputs/metrics.json").read_text(encoding="utf-8")
        )
        results.append(
            {
                "run": index,
                "params": params,
                "accuracy": accuracy,
                "f1_score": metrics["f1_score"],
            }
        )

    best = max(
        results,
        key=lambda result: (
            result["accuracy"],
            result["f1_score"],
            -result["params"]["n_estimators"],
        ),
    )

    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/experiment_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    rows = [
        "# Kết quả thí nghiệm MLflow",
        "",
        "| Run | n_estimators | max_depth | min_samples_split | Accuracy | F1 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        params = result["params"]
        rows.append(
            f"| {result['run']} | {params['n_estimators']} | "
            f"{params['max_depth']} | {params['min_samples_split']} | "
            f"{result['accuracy']:.4f} | {result['f1_score']:.4f} |"
        )
    rows.extend(
        [
            "",
            "## Cấu hình được chọn",
            "",
            f"`{best['params']}` với accuracy `{best['accuracy']:.4f}` "
            f"và F1 `{best['f1_score']:.4f}`.",
        ]
    )
    Path("outputs/experiment_results.md").write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )

    Path("params.yaml").write_text(
        "# Best RandomForestClassifier parameters selected by MLflow experiments\n"
        + yaml.safe_dump(best["params"], sort_keys=False),
        encoding="utf-8",
    )

    print("\nExperiment summary")
    for result in results:
        print(
            f"Run {result['run']}: accuracy={result['accuracy']:.4f}, "
            f"f1={result['f1_score']:.4f}, params={result['params']}"
        )
    print(f"Selected best parameters: {best['params']}")


if __name__ == "__main__":
    main()
