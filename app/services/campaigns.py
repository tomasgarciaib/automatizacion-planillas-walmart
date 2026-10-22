import sqlite3
from dataclasses import dataclass


VALID_STATUSES = ("Borrador", "En preparación", "Lista para Drive", "Archivada")


@dataclass(frozen=True)
class Campaign:
    id: int
    name: str
    brand: str
    discount: str
    status: str
    created_at: str


def create_campaign(
    connection: sqlite3.Connection, *, name: str, brand: str, discount: str
) -> Campaign:
    cursor = connection.execute(
        "INSERT INTO campaigns (name, brand, discount) VALUES (?, ?, ?)",
        (name.strip(), brand.strip(), discount.strip()),
    )
    connection.commit()
    return get_campaign(connection, cursor.lastrowid)


def get_campaign(connection: sqlite3.Connection, campaign_id: int) -> Campaign:
    row = connection.execute(
        "SELECT id, name, brand, discount, status, created_at FROM campaigns WHERE id = ?",
        (campaign_id,),
    ).fetchone()
    if row is None:
        raise LookupError("Campaña no encontrada")
    return Campaign(**dict(row))


def list_campaigns(connection: sqlite3.Connection) -> list[Campaign]:
    rows = connection.execute(
        "SELECT id, name, brand, discount, status, created_at "
        "FROM campaigns ORDER BY id DESC"
    ).fetchall()
    return [Campaign(**dict(row)) for row in rows]


def update_status(
    connection: sqlite3.Connection, *, campaign_id: int, status: str
) -> Campaign:
    if status not in VALID_STATUSES:
        raise ValueError("Estado no válido")
    connection.execute(
        "UPDATE campaigns SET status = ? WHERE id = ?", (status, campaign_id)
    )
    connection.commit()
    return get_campaign(connection, campaign_id)
