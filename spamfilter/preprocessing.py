"""Email cleaning — identical to the notebook, so the served model sees the same
text distribution it was trained and evaluated on."""
import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

URL_RE = re.compile(r"(?:https?://|www\.)\S+|\S+@\S+\.\S+")
HTML_TAG_RE = re.compile(r"<[^>]{0,200}>")
HTML_ENT_RE = re.compile(r"&[a-z]{2,8};|&#\d{1,5};")
NON_ALPHA = re.compile(r"[^a-z\s]")
TOKEN_RE = re.compile(r"\b[a-z]{3,}\b")

# Dataset fingerprints found in the notebook's artifact audit. `enron`, `ect` and `hou`
# identify the source archive rather than spamminess, so they are removed on purpose.
CORPUS_ARTIFACTS = {
    "escapenumber", "escapelong", "escapetoken",
    "enron", "ect", "hou",
    "nbsp", "href", "http", "https", "www",
}
STOPWORDS = frozenset(ENGLISH_STOP_WORDS)


def clean_email(text: str) -> str:
    """Normalise one raw email into a whitespace-joined string of clean tokens."""
    t = text.lower()
    t = HTML_TAG_RE.sub(" ", t)
    t = HTML_ENT_RE.sub(" ", t)
    t = URL_RE.sub(" ", t)
    t = NON_ALPHA.sub(" ", t)
    return " ".join(
        w for w in TOKEN_RE.findall(t)
        if w not in STOPWORDS and w not in CORPUS_ARTIFACTS
    )
