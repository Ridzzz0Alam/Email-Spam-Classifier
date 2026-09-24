# Spam or not — web app for the Project 04 classifier

A FastAPI backend and a small web frontend for the Naive Bayes spam classifier from the
notebook. Paste an email and it shows the verdict, the exact log-odds arithmetic behind it,
and the email itself with every word shaded by how hard it pulled toward spam (red) or a
real email (blue).

The served model is the notebook's GridSearchCV winner, retrained with the same cleaning,
deduplication and stratified split: TF-IDF over unigrams and bigrams, `MultinomialNB(alpha=0.1)`.
On the 16,606-email test set it scores 98.49% accuracy and 99.37% spam precision.

## Quick start with Docker

Use this on Windows machines where Smart App Control blocks scipy's DLLs
("An Application Control policy has blocked this file"). Needs Docker Desktop and
`combined_data.csv` in the project folder.

```bash
docker compose --profile train run --rm train   # 1. train (a few minutes) -> models/spam_model.joblib
docker compose up -d --build web                # 2. serve at http://127.0.0.1:8000
docker compose down                             # stop
```

After changing code, run `docker compose up -d --build web` again. The model file lives in
`models/` on your disk, so it survives rebuilds; retrain only if you change `train.py`
or the cleaning code.

## Quick start without Docker

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Train (a few minutes). Download combined_data.csv from Kaggle first.
python train.py --data path/to/combined_data.csv

# 2. Serve
fastapi dev app/main.py              # auto-reloads while you edit
```

Open http://127.0.0.1:8000 for the app, or http://127.0.0.1:8000/docs for the interactive
API documentation. Startup takes about 8 seconds while the 3.3-million-feature model loads;
after that each email is classified and explained in roughly 20–30 ms.

For a non-reloading server use `fastapi run app/main.py`.

## Model size options

| `--min-df` | features | file | load time | accuracy | false positives |
|---|---|---|---|---|---|
| `1` (default, exact notebook model) | 3,288,385 | 85 MB | ~6 s | 98.49% | 54 |
| `2` | 984,467 | 29 MB | ~3 s | 98.58% | 63 |

`--min-df 2` drops phrases seen in only one training email. It is a third of the size and
scores slightly higher on accuracy, but misfiles 9 more real emails as spam. The default
keeps the notebook's model because the report argues false positives are the error that
matters. Pick `2` if you need to deploy somewhere memory is tight.

## API

`POST /api/classify`

```bash
curl -X POST http://127.0.0.1:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Limited time offer! Order cheap pills now", "top_n": 5}'
```

Returns the label, `p_spam`, and the decomposition:

```json
{
  "label": "spam",
  "p_spam": 0.9991,
  "log_odds": 6.9962,
  "prior_log_odds": 0.1109,
  "evidence": 6.8853,
  "top_spam": [
    {
      "feature": "order cheap",
      "weight": 0.425,
      "contribution": 1.314
    },
    {
      "feature": "cheap pills",
      "weight": 0.45,
      "contribution": 1.227
    }
  ],
  "top_ham": [],
  "word_scores": {
    "cheap": 1.987,
    "pills": 1.724,
    "time": 0.952
  },
  "words_total": 6,
  "words_recognised": 6,
  "features_active": 11
}
```

(Lists trimmed for display; the real response returns up to `top_n` features each way and a score for every recognised word.)

`log_odds = prior_log_odds + evidence`, and `evidence` is exactly the sum of every feature's
contribution — the same decomposition as section 7 of the notebook. The service asserts
this identity against scikit-learn's own `predict_log_proba` on every request.

Other endpoints: `GET /api/model` (training metadata and test metrics), `GET /api/health`.
Emails up to 200,000 characters are accepted.

## How the highlighting works

Multinomial Naive Bayes is additive in log space, so each feature's contribution is
`tfidf_weight × (log P(feature|spam) − log P(feature|ham))`. For shading, a bigram's
contribution is split evenly between its two words, and a word's score is its total across
the email. Words removed by cleaning (stopwords, numbers, anything under 3 letters) and
words the model never saw carry no evidence and stay unshaded.

Try the "Disguised spam" sample: `V1agra` becomes `agra` after cleaning strips the digit,
and `agra`, `alis` and `rmacy` are themselves learned spam features, because the training
spam was already obfuscated. The model learned the debris of disguise.

## Project layout

```
train.py                 retrain and export models/spam_model.joblib
spamfilter/
  preprocessing.py       clean_email(), identical to the notebook
  explain.py             exact per-feature decomposition of a prediction
app/main.py              FastAPI app: lifespan model loading, /api routes, frontend
frontend/                index.html, styles.css, app.js (no build step)
tests/test_api.py        API tests against a tiny synthetic model
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests train a tiny model on eight synthetic emails, so they run in about a second and
don't need the dataset.

## Caveats

- Everything the notebook's report says about corpus leakage applies here: the model
  partly learned mailing-list fingerprints from the ham archives, so real-world accuracy on
  your own inbox will be lower than the test-set numbers.
- There is no authentication or rate limiting. Keep it on localhost, or add both before
  exposing it.
- The frontend loads its fonts from Google Fonts and falls back to system fonts offline.
- A model file must be trained with the scikit-learn version you serve it with. The app
  logs a warning if they differ.
