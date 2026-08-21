import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from google.cloud import storage
from pydantic import BaseModel

GCS_MODEL_KEY = "models/latest/model.pkl"
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
LABELS = {0: "thap", 1: "trung_binh", 2: "cao"}


def get_model_path() -> Path:
    return Path(os.getenv("MODEL_PATH", "~/models/model.pkl")).expanduser()


def download_model(
    bucket_name: str,
    model_key: str = GCS_MODEL_KEY,
    destination: Path | None = None,
) -> Path:
    """Download the promoted model from Google Cloud Storage."""
    destination = destination or get_model_path()
    destination.parent.mkdir(parents=True, exist_ok=True)

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(model_key)
    blob.download_to_filename(str(destination))
    print(f"Downloaded gs://{bucket_name}/{model_key} to {destination}")
    return destination


def load_model():
    """Load a local model, downloading the latest GCS model when configured."""
    model_path = get_model_path()
    bucket_name = os.getenv("GCS_BUCKET")
    if bucket_name:
        download_model(bucket_name=bucket_name, destination=model_path)

    if not model_path.exists():
        raise RuntimeError(
            f"Model not found at {model_path}. Set GCS_BUCKET or MODEL_PATH correctly."
        )
    return joblib.load(model_path)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    if getattr(fastapi_app.state, "model", None) is None:
        fastapi_app.state.model = load_model()
    yield


app = FastAPI(title="Wine Quality Classifier", version="1.0.0", lifespan=lifespan)
app.state.model = None


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    if len(req.features) != len(FEATURE_NAMES):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(FEATURE_NAMES)} features (wine quality)",
        )

    model = getattr(app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    feature_frame = pd.DataFrame([req.features], columns=FEATURE_NAMES)
    prediction = int(model.predict(feature_frame)[0])
    if prediction not in LABELS:
        raise HTTPException(status_code=500, detail="Model returned an unknown class")
    return {"prediction": prediction, "label": LABELS[prediction]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
