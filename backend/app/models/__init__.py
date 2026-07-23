"""ORM models package.

Re-exporting the models here means ``from app import models`` registers every
table on the declarative ``Base`` metadata.
"""

from app.models.query_log import QueryLog

__all__ = ["QueryLog"]
