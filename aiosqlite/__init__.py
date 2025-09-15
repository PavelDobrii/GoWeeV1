import asyncio
import sqlite3
from typing import Any, Iterable, Optional

Row = sqlite3.Row
Error = sqlite3.Error
DatabaseError = sqlite3.DatabaseError
IntegrityError = sqlite3.IntegrityError
NotSupportedError = sqlite3.NotSupportedError
OperationalError = sqlite3.OperationalError
ProgrammingError = sqlite3.ProgrammingError
sqlite_version = sqlite3.sqlite_version
sqlite_version_info = sqlite3.sqlite_version_info

class Cursor:
    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cursor = cursor
        self.description = cursor.description
        self.lastrowid = cursor.lastrowid
        self.rowcount = cursor.rowcount

    async def execute(
        self, sql: str, parameters: Optional[Iterable[Any]] = None
    ) -> "Cursor":
        if parameters is None:
            await asyncio.to_thread(self._cursor.execute, sql)
        else:
            await asyncio.to_thread(self._cursor.execute, sql, parameters)
        self.description = self._cursor.description
        self.lastrowid = self._cursor.lastrowid
        self.rowcount = self._cursor.rowcount
        return self

    async def fetchone(self) -> Any:
        return await asyncio.to_thread(self._cursor.fetchone)

    async def fetchall(self) -> list[Any]:
        return await asyncio.to_thread(self._cursor.fetchall)

    async def close(self) -> None:
        await asyncio.to_thread(self._cursor.close)

    async def __aenter__(self) -> "Cursor":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        await self.close()

class Connection:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.row_factory = conn.row_factory

    async def cursor(self) -> Cursor:
        cur = await asyncio.to_thread(self._conn.cursor)
        return Cursor(cur)

    async def execute(
        self, sql: str, parameters: Optional[Iterable[Any]] = None
    ) -> Cursor:
        cur = await self.cursor()
        await cur.execute(sql, parameters)
        return cur

    async def commit(self) -> None:
        await asyncio.to_thread(self._conn.commit)

    async def rollback(self) -> None:
        await asyncio.to_thread(self._conn.rollback)

    async def create_function(self, *args: Any, **kwargs: Any) -> None:
        await asyncio.to_thread(self._conn.create_function, *args, **kwargs)

    async def close(self) -> None:
        await asyncio.to_thread(self._conn.close)

    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.close()

def connect(*args: Any, **kwargs: Any) -> "_ConnectAwaitable":
    return _ConnectAwaitable(args, kwargs)

class _ConnectAwaitable:
    def __init__(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.args = args
        self.kwargs = kwargs

    def __await__(self):
        async def _connect() -> Connection:
            conn = await asyncio.to_thread(sqlite3.connect, *self.args, **self.kwargs)
            return Connection(conn)
        return _connect().__await__()
