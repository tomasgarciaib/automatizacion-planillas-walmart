import sqlite3
from pathlib import Path

from app.database import get_connection, initialize_database
from app.services.campaigns import create_campaign, list_campaigns, update_status


def test_campaign_lifecycle(tmp_path: Path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        campaign = create_campaign(
            connection,
            name="Ripholia 15%",
            brand="Ripholia",
            discount="15%",
        )
        assert campaign.status == "Borrador"

        updated = update_status(
            connection, campaign_id=campaign.id, status="En preparación"
        )
        assert updated.status == "En preparación"
        assert [item.name for item in list_campaigns(connection)] == ["Ripholia 15%"]


def test_schema_requires_campaign_name(tmp_path: Path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        try:
            connection.execute(
                "INSERT INTO campaigns (name, brand, discount) VALUES (NULL, 'X', '15%')"
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("La base debe exigir un nombre de campaña")
