"""API tests against a tiny synthetic model, so they run in about a second without the
dataset. The model is trained on eight emails and saved to a temp bundle that the app
loads through SPAM_MODEL_PATH, exactly as it would load the real one."""
import joblib
import pytest
import sklearn
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from spamfilter import clean_email

SPAM = [
    "Buy cheap viagra online now, limited offer, click here",
    "Win a free prize! Claim your cash reward today",
    "Cheap pharmacy pills, no prescription needed, order now",
    "Exclusive offer: make money fast, click here to claim",
]
HAM = [
    "Can we move the project meeting to Thursday afternoon?",
    "Attached are the notes from yesterday's code review",
    "Thanks for the patch, the parser tests look good",
    "Let's schedule a call next week to discuss the report",
]


@pytest.fixture(scope="module")
def client(tmp_path_factory, monkeypatch_module):
    pipe = Pipeline([
        ("vectorizer", TfidfVectorizer(ngram_range=(1, 2))),
        ("classifier", MultinomialNB(alpha=0.1)),
    ])
    pipe.fit([clean_email(t) for t in SPAM + HAM], [1] * len(SPAM) + [0] * len(HAM))
    meta = {
        "model": "test model",
        "params": {"ngram_range": [1, 2], "alpha": 0.1},
        "n_features": len(pipe.named_steps["vectorizer"].vocabulary_),
        "n_train": len(SPAM) + len(HAM),
        "metrics": {"accuracy": 1.0},
        "sklearn_version": sklearn.__version__,
        "trained_at": "2026-01-01T00:00:00+00:00",
    }
    path = tmp_path_factory.mktemp("model") / "model.joblib"
    joblib.dump({"pipeline": pipe, "meta": meta}, path)
    monkeypatch_module.setenv("SPAM_MODEL_PATH", str(path))

    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "model_loaded": True}


def test_model_info(client):
    body = client.get("/api/model").json()
    assert body["n_train"] == 8
    assert body["sklearn_version"] == sklearn.__version__


def test_classifies_spam(client):
    body = client.post("/api/classify",
                       json={"text": "Click here for cheap pills, order now"}).json()
    assert body["label"] == "spam"
    assert body["p_spam"] > 0.5
    assert body["top_spam"]


def test_classifies_ham(client):
    body = client.post("/api/classify",
                       json={"text": "Notes from the code review meeting on Thursday"}).json()
    assert body["label"] == "ham"
    assert body["p_spam"] < 0.5
    assert body["top_ham"]


def test_decomposition_adds_up(client):
    body = client.post("/api/classify",
                       json={"text": "Free prize! Can we discuss the report?", "top_n": 50}).json()
    feats = body["top_spam"] + body["top_ham"]
    assert body["log_odds"] == pytest.approx(body["prior_log_odds"] + body["evidence"])
    assert body["evidence"] == pytest.approx(sum(f["contribution"] for f in feats))
    assert len(feats) == body["features_active"]


def test_top_n_limits_lists(client):
    body = client.post("/api/classify",
                       json={"text": " ".join(SPAM + HAM), "top_n": 1}).json()
    assert len(body["top_spam"]) <= 1
    assert len(body["top_ham"]) <= 1


@pytest.mark.parametrize("payload", [
    {"text": ""},
    {"text": "   \n  "},
    {"text": "x" * 200_001},
    {"text": "hello", "top_n": 0},
    {"text": "hello", "top_n": 51},
])
def test_rejects_bad_input(client, payload):
    assert client.post("/api/classify", json=payload).status_code == 422


def test_unknown_words_are_unscored(client):
    body = client.post("/api/classify", json={"text": "zyxwv qwertyuiop"}).json()
    assert body["features_active"] == 0
    assert body["words_recognised"] == 0
    assert body["evidence"] == 0


def test_serves_frontend(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Spam or not" in r.text
