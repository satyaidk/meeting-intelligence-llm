"""Storage layer: SQLAlchemy ORM tables and the Repository that queries them.

The graph (Meeting -> Action -> Person, Risk -> blocks -> Action, ...) is
stored as ordinary relational tables with foreign keys. See
docs/adr/0003-relational-storage-for-the-graph.md for why we did not start
with a graph database.
"""

from actiongraph.storage.database import create_db_engine, init_db, make_session_factory
from actiongraph.storage.repository import Repository

__all__ = ["Repository", "create_db_engine", "init_db", "make_session_factory"]
