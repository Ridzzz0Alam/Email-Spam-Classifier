"""Spam classifier package: shared preprocessing and prediction explanations."""
from .preprocessing import clean_email
from .explain import explain

__all__ = ["clean_email", "explain"]
