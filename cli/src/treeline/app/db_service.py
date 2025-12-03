"""Service for database operations."""

from treeline.abstractions import Repository
from treeline.domain import Result


class DbService:
    """Service for database operations."""

    def __init__(self, repository: Repository):
        self.repository = repository

    async def initialize_db(self) -> Result:
        """Initialize database directory and schema."""
        db_result = await self.repository.ensure_db_exists()
        if not db_result.success:
            return db_result

        return await self.repository.ensure_schema_upgraded()

    async def execute_query(self, sql: str) -> Result:
        cleaned_sql = self._clean_and_validate_sql(sql)
        return await self.repository.execute_query(cleaned_sql)

    def _clean_and_validate_sql(self, sql: str) -> str:
        # TODO: Implement SQL cleaning and validation
        return sql
