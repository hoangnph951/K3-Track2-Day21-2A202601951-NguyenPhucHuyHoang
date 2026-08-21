import json
import os
import tempfile
from pathlib import Path

import mlflow
import pandas as pd
import yaml

from src.train import train


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    phase1 = pd.read_csv(project_root / "data/train_phase1.csv")
    phase2 = pd.read_csv(project_root / "data/train_phase2.csv")
    evaluation = pd.read_csv(project_root / "data/eval.csv")
    combined = pd.concat([phase1, phase2], ignore_index=True)
    params = yaml.safe_load(
        (project_root / "params.yaml").read_text(encoding="utf-8")
    )

    original_directory = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="mlops-continuous-preview-") as temp_dir:
        temp_path = Path(temp_dir)
        train_path = temp_path / "train.csv"
        eval_path = temp_path / "eval.csv"
        combined.to_csv(train_path, index=False)
        evaluation.to_csv(eval_path, index=False)

        os.chdir(temp_path)
        try:
            mlflow.set_tracking_uri((temp_path / "mlruns").as_uri())
            accuracy = train(params, str(train_path), str(eval_path))
            metrics = json.loads(
                (temp_path / "outputs/metrics.json").read_text(encoding="utf-8")
            )
        finally:
            os.chdir(original_directory)

    preview = {
        "mode": "preview_only",
        "params": params,
        "phase1_samples": int(len(phase1)),
        "phase2_samples": int(len(phase2)),
        "combined_samples": int(len(combined)),
        "accuracy": accuracy,
        "f1_score": metrics["f1_score"],
        "passes_eval_gate": accuracy >= 0.70,
    }
    output_path = project_root / "outputs/continuous_preview.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(
        json.dumps(preview, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(preview, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
