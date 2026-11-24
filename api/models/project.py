"""
Minimal Project ORM model.

Refs #129: `projects` has never had an ORM model anywhere in this
codebase -- every router/service that touches it does so via raw SQL or
SQLAlchemy Core, never a mapped class. That's fine on its own, but
several *other* models (SyncHistory, SyncPlan, SyncState,
SchemaComparison) declare `ForeignKey('projects.id', ...)` columns, and
each of those model files registers its own isolated
`declarative_base()` with its own independent `MetaData` -- so none of
them has ever had a `projects` table registered anywhere in their own
metadata for that string reference to resolve against.

This surfaces as `sqlalchemy.exc.NoReferencedTableError` the moment the
ORM needs to sort tables for a flush (`session.add(SomeRelatedModel(...));
session.commit()` -- exactly what sync_history_service.py,
conflict_resolver.py, and sync_plan_service.py actually do in real
request handling), confirmed live inside the real running zerodb-api
container, not just in tests.

The fix: give this file -- and every file with a `ForeignKey('projects.id')`
-- a single shared `Base` (api/database.py's, previously declared but
never actually used by any model) instead of each calling
`declarative_base()` itself. `Project` here is deliberately minimal (just
`id`, the only column any FK ever needs to resolve against) rather than a
full mirror of the real `projects` table/schema.sql -- it exists solely to
make FK string resolution work, not to be used for querying or writing
project rows (that stays raw SQL / SQLAlchemy Core, as before, everywhere
it already was).
"""
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
