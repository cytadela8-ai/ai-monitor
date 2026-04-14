import sqlite3
from typing import Any
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_monitor.auth import generate_api_key, hash_api_key
from ai_monitor.db.schema import ensure_database


@dataclass(frozen=True)
class MachineRecord:
    id: int
    label: str
    is_local: bool
    is_active: bool
    created_at: str
    last_seen_at: str | None
    last_refresh_at: str | None
    last_refresh_source: str | None


@dataclass(frozen=True)
class MachineAuthResult:
    machine: MachineRecord | None
    status: str


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _machine_from_row(row: tuple[Any, ...] | None) -> MachineRecord | None:
    if row is None:
        return None
    return MachineRecord(
        id=int(row[0]),
        label=str(row[1]),
        is_local=bool(row[2]),
        is_active=bool(row[3]),
        created_at=str(row[4]),
        last_seen_at=None if row[5] is None else str(row[5]),
        last_refresh_at=None if row[6] is None else str(row[6]),
        last_refresh_source=None if row[7] is None else str(row[7]),
    )


def _fetch_machine(
    connection: sqlite3.Connection,
    where_sql: str,
    params: tuple[object, ...],
) -> MachineRecord | None:
    row = connection.execute(
        f"""
        SELECT
            id,
            label,
            is_local,
            is_active,
            created_at,
            last_seen_at,
            last_refresh_at,
            last_refresh_source
        FROM machines
        {where_sql}
        """,
        params,
    ).fetchone()
    return _machine_from_row(row)


def ensure_local_machine(database_path: Path, label: str) -> MachineRecord:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        with connection:
            machine = _fetch_machine(connection, "WHERE is_local = 1", ())
            if machine is not None:
                if machine.label != label:
                    connection.execute(
                        "UPDATE machines SET label = ? WHERE id = ?",
                        (label, machine.id),
                    )
                    updated_machine = get_machine_by_id(database_path, machine.id)
                    if updated_machine is None:
                        raise ValueError("Updated local machine could not be reloaded")
                    return updated_machine
                return machine

            by_id = _fetch_machine(connection, "WHERE id = 1", ())
            created_at = _now_iso()
            if by_id is not None:
                connection.execute(
                    """
                    UPDATE machines
                    SET label = ?, api_key_hash = NULL, is_local = 1, is_active = 1
                    WHERE id = 1
                    """,
                    (label,),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO machines (
                        id,
                        label,
                        api_key_hash,
                        is_local,
                        is_active,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (1, label, None, 1, 1, created_at),
                )
    finally:
        connection.close()
    machine = get_machine_by_id(database_path, 1)
    if machine is None:
        raise ValueError("Local machine was not created")
    return machine


def create_machine(database_path: Path, label: str) -> tuple[MachineRecord, str]:
    ensure_database(database_path)
    api_key = generate_api_key()
    created_at = _now_iso()
    connection = sqlite3.connect(database_path)
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO machines (
                    label,
                    api_key_hash,
                    is_local,
                    is_active,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (label, hash_api_key(api_key), 0, 1, created_at),
            )
            if cursor.lastrowid is None:
                raise ValueError("Machine creation did not return an id")
            machine_id = cursor.lastrowid
    finally:
        connection.close()
    machine = get_machine_by_id(database_path, machine_id)
    if machine is None:
        raise ValueError("Machine creation failed")
    return machine, api_key


def get_machine_by_id(database_path: Path, machine_id: int) -> MachineRecord | None:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        return _fetch_machine(connection, "WHERE id = ?", (machine_id,))
    finally:
        connection.close()


def list_machines(database_path: Path) -> list[MachineRecord]:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT
                id,
                label,
                is_local,
                is_active,
                created_at,
                last_seen_at,
                last_refresh_at,
                last_refresh_source
            FROM machines
            ORDER BY is_local DESC, label
            """
        ).fetchall()
    finally:
        connection.close()
    machines: list[MachineRecord] = []
    for row in rows:
        machine = _machine_from_row(row)
        if machine is not None:
            machines.append(machine)
    return machines


def revoke_machine(database_path: Path, machine_id: int) -> MachineRecord | None:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        with connection:
            connection.execute(
                "UPDATE machines SET is_active = 0 WHERE id = ? AND is_local = 0",
                (machine_id,),
            )
    finally:
        connection.close()
    return get_machine_by_id(database_path, machine_id)


def authenticate_machine_key(database_path: Path, api_key: str) -> MachineAuthResult:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        machine = _fetch_machine(
            connection,
            "WHERE api_key_hash = ?",
            (hash_api_key(api_key),),
        )
    finally:
        connection.close()
    if machine is None:
        return MachineAuthResult(machine=None, status="missing")
    if not machine.is_active:
        return MachineAuthResult(machine=machine, status="inactive")
    return MachineAuthResult(machine=machine, status="ok")
