"""Evaluation: measure extraction quality against hand-labelled meetings.

"It looks right on the demo" is not evidence. This package scores any
extractor on a small "golden" dataset (``evals/datasets/``) with the same
metrics used for information-extraction research: precision, recall and F1,
plus owner and deadline accuracy on the items that matched.
"""
