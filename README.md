# Spam or not: web app for the Project 04 classifier

## Live notebook

**[Open the Spam Email Classifier notebook](LINK_COMING_SOON)**

<!-- TODO: replace LINK_COMING_SOON with the live notebook URL -->

The full analysis (EDA, preprocessing, baseline, vectorizer comparison, GridSearchCV tuning,
chi2 vocabulary pruning, feature importance, explainability and adversarial testing) lives in
[Spam_Email_Classifier.ipynb](Spam_Email_Classifier.ipynb).

## Table of contents

- [Live notebook](#live-notebook)
- [Overview](#overview)
- [Which preprocessing and hyperparameter choices generalized best, and why](#which-preprocessing-and-hyperparameter-choices-generalized-best-and-why)
  - [Preprocessing](#preprocessing)
  - [Hyperparameters](#hyperparameters)
  - [How we know it generalized](#how-we-know-it-generalized)
  - [What did not generalize](#what-did-not-generalize)
- [Running locally](#running-locally)
  - [Prerequisites](#prerequisites)
  - [Option 1: Docker](#option-1-docker)
  - [Option 2: Python virtual environment](#option-2-python-virtual-environment)
  - [Running the notebook](#running-the-notebook)
  - [Running the tests](#running-the-tests)
- [Model size options](#model-size-options)
- [API](#api)
- [How the highlighting works](#how-the-highlighting-works)
- [Project layout](#project-layout)
- [Caveats](#caveats)

## Overview

A FastAPI backend and a small web frontend for the Naive Bayes spam classifier from the
notebook. Paste an email and it shows the verdict, the exact log-odds arithmetic behind it,
and the email itself with every word shaded by how hard it pulled toward spam (red) or a
real email (blue).

The served model is the notebook's GridSearchCV winner, retrained with the same cleaning,
deduplication and stratified split: TF-IDF over unigrams and bigrams, `MultinomialNB(alpha=0.1)`.
On the 16,606-email test set it scores 98.49% accuracy and 99.37% spam precision.

## Which preprocessing and hyperparameter choices generalized best, and why

In spam filtering the two errors do not cost the same. Spam in the inbox is annoying, but a
real email silently moved to junk can be missed entirely. So "generalized best" here means
the choices that held up on unseen data (cross-validation folds and the untouched 16,606-email
test set) while keeping false positives, real emails flagged as spam, as low as possible.

The short answer: **TF-IDF weighting, unigrams plus bigrams, the full vocabulary and light
smoothing (`alpha=0.1`), trained on deduplicated text with dataset fingerprints removed.**
That configuration took the model from the baseline's 97.61% accuracy and 122 false positives
to 98.49% accuracy and 54 false positives.

| Model | Test accuracy | Spam precision | Spam recall | Spam F1 | False positives |
|---|---|---|---|---|---|
| Baseline: raw text, unconstrained `CountVectorizer`, `alpha=1.0` | 0.9761 | 0.9858 | 0.9686 | 0.9771 | 122 |
| Tuned: cleaned text, TF-IDF, (1,2)-grams, all features, `alpha=0.1` | **0.9849** | **0.9937** | **0.9776** | **0.9856** | **54** |

### Preprocessing

**1. Dropping exact duplicates (after whitespace normalization).** 418 emails were exact
copies once whitespace was normalized. Removing them before the train/test split stops the
model from being tested on emails it memorized during training. Near-duplicates (25.6% of
emails share their first 100 characters with another email) were kept on purpose, because
templated spam is what a real filter sees every day.

**2. TF-IDF over raw counts.** This was the most consistent win in the whole project. TF-IDF
beat `CountVectorizer` on every text variant (raw, basic clean, full clean) by 0.3 to 0.8 F1
points, and it won again in cross-validation (best CV F1 0.9639 vs 0.9589), so the choice
did not rely on the test set. It generalizes better for two reasons:

- IDF down-weights words that appear everywhere, including mid-frequency filler that no
  stopword list catches.
- L2 normalization removes the length advantage of long ham emails (median 200 words vs
  122 for spam), so the model judges what an email says rather than how long it is.

**3. Full cleaning (lowercase, strip HTML, URLs, digits and punctuation, drop stopwords and
tokens under 3 letters).** Cleaning did *not* raise headline accuracy. Raw text with TF-IDF
scored 0.9743 and fully cleaned text scored 0.9719. But cleaned text produced the fewest
false positives of the six vectorizer and preprocessing combinations (145 vs 152 for raw)
while keeping only 47% of the tokens. Stopword frequencies and punctuation density carry a
little signal inside this corpus, but that signal is a property of how the dataset was
collected, not of spam, so it is unlikely to carry over to a real inbox.

**4. Removing dataset fingerprints (`enron`, `ect`, `hou`, `escapenumber`, `escapelong`).**
This was the most important judgement call, and it is one the test score cannot reward.
`enron` appears in 6,758 emails and only one of them is spam, because the ham half of the
corpus came from the Enron archive. The word predicts *which archive an email came from*, not
whether it is spam. Keeping it would inflate the test score and fail on any inbox that is not
Enron's. Removing it slightly lowers in-corpus accuracy, which is the price of a model that
learns spam language instead of dataset labels.

### Hyperparameters

The search ran `GridSearchCV` over the whole pipeline (so the vocabulary was rebuilt inside
every fold, avoiding leakage) with 3-fold stratified CV, 50 configurations per vectorizer,
300 fits in total.

**1. `alpha=0.1` (light Laplace smoothing) mattered most.** Small values (0.01 to 0.1) won
consistently. Smoothing protects against zero probabilities when evidence is scarce, but with
tens of thousands of emails per class the evidence is plentiful. Heavy smoothing (1.0 or 2.0)
just pulls every word's spam/ham log-ratio toward zero and blunts real signal. On a much
smaller corpus the best value would move upward.

**2. `ngram_range=(1, 2)` beat unigrams.** All ten of the top ten configurations used bigrams.
Phrases such as `target price`, `retail price`, `dear customer` and `viagra cialis` are
strong spam evidence even though their individual words are ordinary. Unigrams throw that
context away.

**3. `max_features=None` (keep the full vocabulary) beat every cap.** The five worst
configurations in the grid all used `max_features=1000` (CV F1 about 0.91). Chi-squared
pruning confirmed this on the full training set: accuracy rose steadily all the way from
k=50 to the full 3.3 million features, with no plateau.

| Features kept (chi2) | Test accuracy | Spam precision | False positives |
|---|---|---|---|
| 1,000 (the knee) | 0.9485 | 0.9587 | 356 |
| 10,000 | 0.9598 | 0.9863 | 114 |
| 100,000 | 0.9737 | 0.9932 | 57 |
| 3,288,385 (all) | **0.9849** | **0.9937** | **54** |

Pruning did not help for two reasons. First, TF-IDF already acts as a soft version of feature
selection: uninformative words get small weights, so leaving them in costs Naive Bayes very
little, and a hard chi2 filter only removes useful signal on top of that. Second, 66,000
training emails is enough to estimate a usable probability even for a word seen in 20 emails.
Feature selection pays off when features outnumber the evidence, which is not the case here.

### How we know it generalized

- **The choice was made by cross-validation, not the test set.** The grid search ran on a
  3,000-email stratified subsample, yet the winner (CV F1 0.9639, standard deviation 0.0043
  across folds) went on to score 0.9856 F1 when refit on all 66,424 training emails and
  scored once on the held-out test set. A configuration that only fit noise in the subsample
  would not have improved when given more data.
- **It is better on every test metric, not just one.** Accuracy, spam precision, spam
  recall and F1 all improved over the baseline, and false positives fell by 56% (122 to 54).
- **The train/test gap grew slightly but honestly.** The tuned model's gap (0.9984 train vs
  0.9849 test) is larger than the baseline's, but the constrained models that close the gap
  do so by getting worse on *both* sides. A bigger gap with a higher test score is still the
  better model.
- **It holds up under attack.** After random character obfuscation (`free` becomes `fr33`)
  it still caught 99.4% of spam, and 98.9% when the attacker targeted the model's own
  strongest spam words. Long spam emails carry so much redundant evidence (one example cleared
  the decision boundary by +48 log-odds) that losing a slice of it rarely flips the result.

### What did not generalize

- **Mailing-list fingerprints still leak in.** The chi2 ranking puts `ethz`, `stat`,
  `posting guide`, `samba`, `perl`, `speakup` and `vince` near the top. These are names of
  mailing lists and people from the ham archives, the same kind of fingerprint as `enron`.
  They should be added to the artifact list in a production pipeline. Until then, accuracy on
  a real inbox will be lower than the test numbers.
- **Unfamiliar vocabulary hurts.** In the baseline, accuracy fell from 0.981 on emails whose
  words were almost all seen in training to 0.886 on emails where 40% or more of the words
  were new. A live filter sees more new vocabulary (new campaigns, products and senders)
  than this test set does.
- **Near-duplicate templates make the test set easier than reality.** Some test emails have
  close twins in training, so the reported scores are somewhat optimistic.
- **Character n-grams were not a free upgrade.** A `char_wb` (3,4)-gram model is the
  structural fix for obfuscation, but on a 6,000-email subsample it scored slightly lower
  than the equivalent word model both on clean mail (0.952 vs 0.960) and after attack
  (0.957 vs 0.967). It is insurance against a determined attacker, not a better default.

## Running locally

### Prerequisites

- Git, to clone this repository.
- Either **Docker Desktop** (Option 1) or **Python 3.10+** (Option 2).
- The dataset: download `combined_data.csv` from the
  [Spam Email Classification Dataset on Kaggle](https://www.kaggle.com/datasets/purusinghvi/email-spam-classification-dataset)
  and place it in the project root. It is about 140 MB and is ignored by git.

```bash
git clone <this-repo-url>
cd spam_email_classifier
# then copy combined_data.csv into this folder
```

### Option 1: Docker

Use this on Windows machines where Smart App Control blocks scipy's DLLs
("An Application Control policy has blocked this file").

```bash
docker compose --profile train run --rm train   # 1. train (a few minutes) -> models/spam_model.joblib
docker compose up -d --build web                # 2. serve at http://127.0.0.1:8000
docker compose down                             # stop
```

After changing code, run `docker compose up -d --build web` again. The model file lives in
`models/` on your disk, so it survives rebuilds; retrain only if you change `train.py`
or the cleaning code.

### Option 2: Python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Train (a few minutes)
python train.py --data combined_data.csv

# 2. Serve
fastapi dev app/main.py              # auto-reloads while you edit
```

Open http://127.0.0.1:8000 for the app, or http://127.0.0.1:8000/docs for the interactive
API documentation. Startup takes about 8 seconds while the 3.3-million-feature model loads;
after that each email is classified and explained in roughly 20 to 30 ms.

For a non-reloading server use `fastapi run app/main.py`.

### Running the notebook

The notebook needs a few extra packages that the app does not:

```bash
pip install -r requirements.txt matplotlib seaborn jupyterlab
jupyter lab Spam_Email_Classifier.ipynb
```

The notebook was written in Google Colab and reads the dataset from `/content/combined_data.csv`.
When running locally, change `DATA_PATH` in the first cell of section 1 to
`"combined_data.csv"` (or the full path to wherever you saved it). Most of the runtime is in
section 4: the two grid searches took about 10 minutes together in the recorded run, and the
refit on the full training set about 2 more.

### Running the tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests train a tiny model on eight synthetic emails, so they run in about a second and
don't need the dataset.

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
contribution, the same decomposition as section 7 of the notebook. The service asserts
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
Spam_Email_Classifier.ipynb  the full analysis and written report
train.py                     retrain and export models/spam_model.joblib
spamfilter/
  preprocessing.py           clean_email(), identical to the notebook
  explain.py                 exact per-feature decomposition of a prediction
app/main.py                  FastAPI app: lifespan model loading, /api routes, frontend
frontend/                    index.html, styles.css, app.js (no build step)
tests/test_api.py            API tests against a tiny synthetic model
```

## Caveats

- Everything the report says about corpus leakage applies here: the model partly learned
  mailing-list fingerprints from the ham archives, so real-world accuracy on your own inbox
  will be lower than the test-set numbers.
- There is no authentication or rate limiting. Keep it on localhost, or add both before
  exposing it.
- The frontend loads its fonts from Google Fonts and falls back to system fonts offline.
- A model file must be trained with the scikit-learn version you serve it with. The app
  logs a warning if they differ.
