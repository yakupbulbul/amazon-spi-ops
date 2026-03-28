from app.models import Base


def test_expected_tables_are_registered() -> None:
    expected_tables = {
        "app_settings",
        "aplus_drafts",
        "aplus_publish_jobs",
        "catalog_import_jobs",
        "event_logs",
        "inventory_alerts",
        "inventory_snapshots",
        "price_change_logs",
        "products",
        "slack_notifications",
        "stock_change_logs",
        "users",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())
