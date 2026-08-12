from collections import Counter
import re


class FakePostgreSQLDatabase:
    def __init__(self) -> None:
        self.tables: dict[str, dict[str, dict[str, object]]] = {}
        self.meta: dict[str, str] = {}
        self.executed: list[str] = []

    def connect(self, _database_url: str):
        return FakePostgreSQLConnection(self)


class FakePostgreSQLConnection:
    def __init__(self, database: FakePostgreSQLDatabase) -> None:
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def cursor(self):
        return FakePostgreSQLCursor(self.database)


class FakePostgreSQLCursor:
    def __init__(self, database: FakePostgreSQLDatabase) -> None:
        self.database = database
        self.rows: list[dict[str, object]] = []

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def execute(self, query: str, params: tuple[object, ...] | None = None):
        self.database.executed.append(query)
        normalized = " ".join(query.lower().split())
        params = params or ()
        self.rows = []
        if normalized.startswith("create table if not exists"):
            match = re.search(r"create table if not exists (\w+)", normalized)
            if match:
                self.database.tables.setdefault(match.group(1), {})
            return self
        if normalized.startswith("create index if not exists"):
            return self
        if normalized.startswith("insert into backend_core_meta"):
            self.database.meta[str(params[0])] = str(params[1])
            return self
        if normalized.startswith("insert into"):
            self._handle_insert(query, params)
            return self
        if normalized.startswith("select raw_json from"):
            self._handle_raw_json_select(normalized, params)
            return self
        if normalized.startswith("select count(*) as total from"):
            table = normalized.split(" from ", 1)[1].split(" ", 1)[0]
            self.rows = [{"total": len(self.database.tables.get(table, {}))}]
            return self
        if normalized.startswith("select value from backend_core_meta"):
            value = self.database.meta.get(str(params[0]))
            self.rows = [{"value": value}] if value is not None else []
            return self
        count_match = re.match(r"select (\w+) as value, count\(\*\) as total from (\w+) group by \w+", normalized)
        if count_match:
            column, table = count_match.groups()
            counts = Counter(row.get(column) for row in self.database.tables.get(table, {}).values())
            self.rows = [{"value": value, "total": total} for value, total in counts.items()]
            return self
        raise AssertionError(f"unexpected SQL: {query}")

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)

    def _handle_insert(self, query: str, params: tuple[object, ...]) -> None:
        match = re.search(r"insert\s+into\s+(\w+)\s*\((.*?)\)\s+values", query, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise AssertionError(f"cannot parse INSERT: {query}")
        table = match.group(1).lower()
        columns = [column.strip() for column in match.group(2).replace("\n", " ").split(",")]
        row = dict(zip(columns, params))
        self.database.tables.setdefault(table, {})[str(row["id"])] = row

    def _handle_raw_json_select(self, normalized: str, params: tuple[object, ...]) -> None:
        table = re.search(r"select raw_json from (\w+)", normalized).group(1)
        rows = list(self.database.tables.get(table, {}).values())
        filter_columns = re.findall(r"(\w+) = %s", normalized)
        for column, value in zip(filter_columns, params):
            rows = [row for row in rows if row.get(column) == value]
        order_match = re.search(r"order by (\w+) desc", normalized)
        if order_match:
            order_column = order_match.group(1)
            rows.sort(key=lambda row: str(row.get(order_column) or ""), reverse=True)
        self.rows = [{"raw_json": row["raw_json"]} for row in rows]
