from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "india_steel_twin.db"


class IndiaSteelTwinStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS twins (
                    thing_id TEXT PRIMARY KEY,
                    definition TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    correlation_id TEXT,
                    thing_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS twin_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thing_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    correlation_id TEXT,
                    event_id TEXT,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transition_events (
                    event_id TEXT PRIMARY KEY,
                    thing_id TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ledger_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT NOT NULL,
                    chain_id TEXT NOT NULL,
                    block_index INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    thing_id TEXT NOT NULL,
                    emission REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    current_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scenario_runs (
                    correlation_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    supplier_thing_id TEXT NOT NULL,
                    batch_tonnes REAL NOT NULL,
                    status TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def upsert_twin(
        self,
        thing: Dict[str, Any],
        entity_type: str,
        updated_at: str,
        correlation_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = self.get_twin(thing["thingId"])
        revision = 1 if not existing else int(existing["revision"]) + 1
        thing["revision"] = revision
        thing["metadata"]["updatedAt"] = updated_at
        payload = json.dumps(thing)

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO twins (
                    thing_id, definition, policy_id, entity_type, revision,
                    correlation_id, thing_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thing_id) DO UPDATE SET
                    definition = excluded.definition,
                    policy_id = excluded.policy_id,
                    entity_type = excluded.entity_type,
                    revision = excluded.revision,
                    correlation_id = excluded.correlation_id,
                    thing_json = excluded.thing_json,
                    updated_at = excluded.updated_at
                """,
                (
                    thing["thingId"],
                    thing["definition"],
                    thing["policyId"],
                    entity_type,
                    revision,
                    correlation_id,
                    payload,
                    updated_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO twin_history (
                    thing_id, revision, correlation_id, event_id, snapshot_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    thing["thingId"],
                    revision,
                    correlation_id,
                    event_id,
                    payload,
                    updated_at,
                ),
            )
        return thing

    def get_twin(self, thing_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM twins WHERE thing_id = ?", (thing_id,)
            ).fetchone()
        return None if row is None else dict(row)

    def list_twins(self) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM twins ORDER BY entity_type, thing_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_twins_for_correlation(self, correlation_id: str) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT thing_id, revision, snapshot_json, created_at
                FROM twin_history
                WHERE correlation_id = ?
                ORDER BY thing_id ASC, revision ASC, created_at ASC
                """,
                (correlation_id,),
            ).fetchall()

        latest_by_thing: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            record = dict(row)
            latest_by_thing[record["thing_id"]] = {
                "thing_id": record["thing_id"],
                "revision": record["revision"],
                "thing_json": record["snapshot_json"],
                "updated_at": record["created_at"],
            }

        ordered = list(latest_by_thing.values())
        ordered.sort(key=lambda item: item["thing_id"])
        return ordered

    def record_event(self, event: Dict[str, Any]) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO transition_events (
                    event_id, thing_id, correlation_id, event_type, stage,
                    from_state, to_state, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["eventId"],
                    event["thingId"],
                    event["correlationId"],
                    event["eventType"],
                    event["stage"],
                    event.get("fromState"),
                    event.get("toState"),
                    json.dumps(event["payload"]),
                    event["timestamp"],
                ),
            )

    def list_events(
        self,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            if correlation_id:
                rows = connection.execute(
                    """
                    SELECT * FROM transition_events
                    WHERE correlation_id = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (correlation_id, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM transition_events
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        events: List[Dict[str, Any]] = []
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event.pop("payload_json"))
            events.append(event)
        return events

    def record_block(self, block: Dict[str, Any]) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO ledger_blocks (
                    correlation_id, chain_id, block_index, stage, thing_id, emission,
                    created_at, previous_hash, current_hash, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    block["correlationId"],
                    block["chainId"],
                    block["index"],
                    block["stage"],
                    block["thingId"],
                    block["emission"],
                    block["timestamp"],
                    block["previous_hash"],
                    block["current_hash"],
                    json.dumps(block["payload"]),
                ),
            )

    def list_blocks(self, correlation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            if correlation_id:
                rows = connection.execute(
                    """
                    SELECT * FROM ledger_blocks
                    WHERE correlation_id = ?
                    ORDER BY block_index ASC
                    """,
                    (correlation_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM ledger_blocks ORDER BY id ASC"
                ).fetchall()
        blocks: List[Dict[str, Any]] = []
        for row in rows:
            block = dict(row)
            block["payload"] = json.loads(block.pop("payload_json"))
            blocks.append(block)
        return blocks

    def upsert_scenario_run(
        self,
        correlation_id: str,
        scenario_id: str,
        supplier_thing_id: str,
        batch_tonnes: float,
        status: str,
        result: Dict[str, Any],
        timestamp: str,
        is_active: bool = True,
    ) -> None:
        with self._connection() as connection:
            if is_active:
                connection.execute("UPDATE scenario_runs SET is_active = 0")
            connection.execute(
                """
                INSERT INTO scenario_runs (
                    correlation_id, scenario_id, supplier_thing_id, batch_tonnes,
                    status, is_active, result_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(correlation_id) DO UPDATE SET
                    scenario_id = excluded.scenario_id,
                    supplier_thing_id = excluded.supplier_thing_id,
                    batch_tonnes = excluded.batch_tonnes,
                    status = excluded.status,
                    is_active = excluded.is_active,
                    result_json = excluded.result_json,
                    updated_at = excluded.updated_at
                """,
                (
                    correlation_id,
                    scenario_id,
                    supplier_thing_id,
                    batch_tonnes,
                    status,
                    1 if is_active else 0,
                    json.dumps(result),
                    timestamp,
                    timestamp,
                ),
            )

    def get_active_run(self) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM scenario_runs
                WHERE is_active = 1
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        run = dict(row)
        run["result"] = json.loads(run.pop("result_json"))
        return run

    def get_run(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM scenario_runs WHERE correlation_id = ?",
                (correlation_id,),
            ).fetchone()
        if row is None:
            return None
        run = dict(row)
        run["result"] = json.loads(run.pop("result_json"))
        return run

    def clear_runtime(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                DELETE FROM twins;
                DELETE FROM twin_history;
                DELETE FROM transition_events;
                DELETE FROM ledger_blocks;
                DELETE FROM scenario_runs;
                """
            )
