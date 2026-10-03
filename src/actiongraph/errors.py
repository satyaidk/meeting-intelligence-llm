"""Exception hierarchy.

Every error we raise on purpose inherits from ``ActionGraphError``. The API
layer maps each subclass to an HTTP status code (see ``api/app.py``), and the
CLI prints the message without a scary stack trace. Unexpected errors (real
bugs) are *not* caught that way, so they stay visible.
"""


class ActionGraphError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigurationError(ActionGraphError):
    """A setting is missing or invalid (e.g. no API key)."""


class IngestionError(ActionGraphError):
    """A meeting file could not be turned into a transcript."""


class UnsupportedFileTypeError(IngestionError):
    """The uploaded file extension is not one we know how to read."""


class ExtractionError(ActionGraphError):
    """The extractor (LLM or rules) failed to produce a valid result."""


class ExtractionRefusedError(ExtractionError):
    """The model declined the request (``stop_reason == "refusal"``)."""


class NotFoundError(ActionGraphError):
    """A requested record does not exist."""


class InvalidOperationError(ActionGraphError):
    """The request is well-formed but not allowed in the current state."""
