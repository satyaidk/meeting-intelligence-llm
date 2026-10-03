"""Services layer: orchestration of the building blocks.

    pipeline.py   MeetingProcessor - runs every stage for one meeting
    tracking.py   Cross-meeting logic: duplicates, applying status updates, risk links
    review.py     Human-in-the-loop actions: approve, reject, edit

Services are the only place where extraction, enrichment and storage meet.
The API and CLI are thin wrappers around these classes.
"""

from actiongraph.services.pipeline import MeetingProcessor, ProcessingReport
from actiongraph.services.review import ReviewService

__all__ = ["MeetingProcessor", "ProcessingReport", "ReviewService"]
