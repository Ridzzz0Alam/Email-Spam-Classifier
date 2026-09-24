"""Train the tuned spam classifier from the notebook and export it for the API.

Reproduces the notebook exactly: same deduplication, same cleaning, same stratified
80/20 split (seed 42), same GridSearchCV winner — TF-IDF, unigrams + bigrams,
MultinomialNB(alpha=0.1).

    python train.py --data combined_data.csv              # exact notebook model (~85 MB)
    python train.py --data combined_data.csv --min-df 2   # ~29 MB, 9 more false positives
"""
import argparse
import datetime as dt
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from spamfilter import clean_email

RANDOM_STATE = 42


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="combined_data.csv", help="path to the Kaggle CSV")
    ap.add_argument("--out", default="models/spam_model.joblib")
    ap.add_argument("--min-df", type=int, default=1,
                    help="drop features seen in fewer emails (1 = notebook's exact model)")
    ap.add_argument("--alpha", type=float, default=0.1)
    args = ap.parse_args()

    t0 = time.time()
    df = pd.read_csv(args.data)
    df["text"] = df["text"].astype(str)
    norm = df["text"].str.replace(r"\s+", " ", regex=True).str.strip()
    df = df.loc[~norm.duplicated()].reset_index(drop=True)
    print(f"Loaded {len(df):,} emails after dedup ({time.time() - t0:.0f}s)")

    t0 = time.time()
    df["clean_text"] = df["text"].map(clean_email)
    print(f"Cleaned in {time.time() - t0:.0f}s")

    X_tr, X_te, y_tr, y_te = train_test_split(
        df["clean_text"].values, df["label"].values,
        test_size=0.20, random_state=RANDOM_STATE, stratify=df["label"].values)

    pipe = Pipeline([
        ("vectorizer", TfidfVectorizer(ngram_range=(1, 2), max_features=None,
                                       min_df=args.min_df)),
        ("classifier", MultinomialNB(alpha=args.alpha)),
    ])
    t0 = time.time()
    pipe.fit(X_tr, y_tr)
    n_feat = len(pipe.named_steps["vectorizer"].vocabulary_)
    print(f"Fitted on {len(y_tr):,} emails, {n_feat:,} features ({time.time() - t0:.0f}s)")

    # Drop the (large, unused) stop_words_ attribute that TfidfVectorizer keeps for
    # min_df pruning — it holds every discarded term and bloats the file.
    vec = pipe.named_steps["vectorizer"]
    if hasattr(vec, "stop_words_"):
        vec.stop_words_ = None

    p = pipe.predict(X_te)
    metrics = {
        "accuracy": accuracy_score(y_te, p),
        "precision_spam": precision_score(y_te, p),
        "recall_spam": recall_score(y_te, p),
        "f1_spam": f1_score(y_te, p),
        "false_positives": int(((p == 1) & (y_te == 0)).sum()),
        "false_negatives": int(((p == 0) & (y_te == 1)).sum()),
        "n_test": int(len(y_te)),
    }
    print(json.dumps({k: round(v, 4) if isinstance(v, float) else v
                      for k, v in metrics.items()}, indent=2))

    meta = {
        "model": "TF-IDF (1,2)-grams + MultinomialNB",
        "params": {"ngram_range": [1, 2], "max_features": None,
                   "min_df": args.min_df, "alpha": args.alpha},
        "n_features": n_feat,
        "n_train": int(len(y_tr)),
        "metrics": metrics,
        "sklearn_version": sklearn.__version__,
        "trained_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    joblib.dump({"pipeline": pipe, "meta": meta}, out, compress=3)
    print(f"Saved {out} ({out.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
