from __future__ import annotations


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("neo4j driver is not installed") from exc

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()
