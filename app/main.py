"""FastAPI service for the Project 04 spam classifier.

    fastapi dev app/main.py        # development, auto-reload
    fastapi run app/main.py        # production

The model is loaded once at startup in the lifespan handler (the pattern FastAPI's docs
recommend for ML models), the JSON API lives under /api, and the static frontend in
./frontend is served at / with app.frontend(), which only answers paths no API route
matched.
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import sklearn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from spamfilter import explain

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "models" / "spam_model.joblib"
FRONTEND_DIR = ROOT / "frontend"

log = logging.getLogger("uvicorn.error")
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    path = Path(os.environ.get("SPAM_MODEL_PATH", DEFAULT_MODEL))
    if not path.exists():
        raise RuntimeError(
            f"No model at {path}. Train one first:\n"
            f"    python train.py --data combined_data.csv\n"
            f"or point SPAM_MODEL_PATH at an existing .joblib bundle."
        )
    bundle = joblib.load(path)
    state["pipeline"] = bundle["pipeline"]
    state["meta"] = bundle["meta"]
    # Built once: rebuilding this array per request cost ~2.5 s on the full vocabulary.
    state["feature_names"] = state["pipeline"].named_steps["vectorizer"].get_feature_names_out()
    trained_with = state["meta"].get("sklearn_version")
    if trained_with and trained_with != sklearn.__version__:
        log.warning("Model trained with scikit-learn %s but running %s — retrain if "
                    "predictions look wrong.", trained_with, sklearn.__version__)
    log.info("Loaded %s (%s features)", path.name, f"{state['meta']['n_features']:,}")
    yield
    state.clear()


app = FastAPI(
    title="Spam Classifier",
    summary="Naive Bayes spam filter with word-level explanations",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------- schemas -------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200_000,
                      description="Raw email text: subject and body.")
    top_n: int = Field(default=10, ge=1, le=50,
                       description="How many top features to return in each direction.")


class Contribution(BaseModel):
    feature: str = Field(description="Unigram or bigram, after cleaning.")
    weight: float = Field(description="TF-IDF value of the feature in this email.")
    contribution: float = Field(description="Log-odds added toward spam (negative = ham).")


class ClassifyResponse(BaseModel):
    label: Literal["spam", "ham"]
    p_spam: float = Field(ge=0, le=1)
    log_odds: float = Field(description="prior_log_odds + evidence; > 0 means spam.")
    prior_log_odds: float
    evidence: float = Field(description="Sum of every feature's contribution.")
    top_spam: list[Contribution]
    top_ham: list[Contribution]
    word_scores: dict[str, float] = Field(
        description="Per-word pull for highlighting; bigrams are split between their words.")
    words_total: int
    words_recognised: int
    features_active: int


class ModelInfo(BaseModel):
    model: str
    params: dict
    n_features: int
    n_train: int
    metrics: dict
    sklearn_version: str
    trained_at: str


# ---------- routes --------------------------------------------------------------------

@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "model_loaded": "pipeline" in state}


@app.get("/api/model", response_model=ModelInfo, tags=["meta"])
def model_info() -> dict:
    return state["meta"]


@app.post("/api/classify", response_model=ClassifyResponse, tags=["classify"])
def classify(req: ClassifyRequest) -> dict:
    # Plain `def`: vectorizing is CPU-bound, so FastAPI runs it in its threadpool
    # instead of blocking the event loop.
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Email text is empty.")
    return explain(state["pipeline"], req.text, top_n=req.top_n,
                   feature_names=state["feature_names"])


# Static UI — registered last and low-priority, so /api/* and /docs always win.
app.frontend("/", directory=FRONTEND_DIR)
