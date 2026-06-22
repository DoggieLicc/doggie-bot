import os
from dataclasses import dataclass
import asqlite


__all__ = [
    'BaseColumn',
    'BaseTable',
    'DatabaseHelper'
]


@dataclass(slots=True)
class BaseColumn:
    name: str
    datatype: str
    addit_schema: str | None = None


@dataclass(slots=True)
class BaseTable:
    name: str
    columns: list[BaseColumn]


class DatabaseHelper:
    def __init__(self, base_tables: list[BaseTable], user_version: int, *args, **kwargs):
        self.base_tables = base_tables
        self.user_version = user_version
        self.args, self.kwargs = args, kwargs
        self.add_version = False

    async def startup(self):
        if not os.path.exists(self.args[0]):
            self.add_version = True

        if self.add_version:
            await self.set_version()

        await self.create_table()

    def conn(self):
        return asqlite.connect(*self.args, **self.kwargs)

    async def execute(self, command: str, *args, **kwargs):
        async with self.conn() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(command, *args, **kwargs)
            await conn.commit()

    async def set_version(self):
        async with self.conn() as conn:
            await conn.execute(f'PRAGMA user_version = {self.user_version}')

    async def create_table(self):
        async with self.conn() as conn:
            async with conn.cursor() as cursor:
                for table in self.base_tables:
                    column_schema = ', '.join(
                        f'{col.name} {col.datatype}{" " + col.addit_schema if col.addit_schema else ""}'
                        for col in table.columns
                    )
                    command = f"CREATE TABLE IF NOT EXISTS {table.name} ({column_schema})"
                    await cursor.execute(command)

            await conn.commit()
