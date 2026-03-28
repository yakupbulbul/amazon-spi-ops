from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import InventoryAlert, InventorySnapshot, Product, User
from app.models.enums import AlertSeverity, InventoryAlertStatus, UserRole

logger = logging.getLogger(__name__)


def bootstrap_admin_user() -> None:
    with SessionLocal() as session:
        existing_user = session.scalar(select(User).where(User.email == settings.admin_email))
        if existing_user is not None:
            return

        session.add(
            User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                full_name="Local Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
        )
        session.commit()
        logger.info("Bootstrapped local admin user for %s", settings.admin_email)


def bootstrap_sample_catalog() -> None:
    with SessionLocal() as session:
        existing_product = session.scalar(select(Product.id).limit(1))
        if existing_product is not None:
            return

        seeded_products = [
            Product(
                sku="TRAVEL-MUG-20OZ",
                asin="B0AMZNSKU01",
                title="Insulated Travel Mug 20oz",
                brand="Northstar Goods",
                marketplace_id="ATVPDKIKX0DER",
                price_amount=Decimal("24.99"),
                price_currency="USD",
                low_stock_threshold=18,
                is_active=True,
            ),
            Product(
                sku="STANDING-DESK-MAT",
                asin="B0AMZNSKU02",
                title="Ergonomic Standing Desk Mat",
                brand="Northstar Goods",
                marketplace_id="ATVPDKIKX0DER",
                price_amount=Decimal("49.00"),
                price_currency="USD",
                low_stock_threshold=12,
                is_active=True,
            ),
            Product(
                sku="LED-DESK-LAMP",
                asin="B0AMZNSKU03",
                title="Adjustable LED Desk Lamp",
                brand="Northstar Goods",
                marketplace_id="ATVPDKIKX0DER",
                price_amount=Decimal("39.50"),
                price_currency="USD",
                low_stock_threshold=10,
                is_active=True,
            ),
        ]
        session.add_all(seeded_products)
        session.flush()

        captured_at = datetime.now(UTC)
        healthy_snapshot = InventorySnapshot(
            product_id=seeded_products[0].id,
            available_quantity=42,
            reserved_quantity=3,
            inbound_quantity=24,
            alert_status=InventoryAlertStatus.HEALTHY.value,
            captured_at=captured_at,
        )
        low_snapshot = InventorySnapshot(
            product_id=seeded_products[1].id,
            available_quantity=9,
            reserved_quantity=2,
            inbound_quantity=8,
            alert_status=InventoryAlertStatus.LOW.value,
            captured_at=captured_at,
        )
        out_of_stock_snapshot = InventorySnapshot(
            product_id=seeded_products[2].id,
            available_quantity=0,
            reserved_quantity=1,
            inbound_quantity=20,
            alert_status=InventoryAlertStatus.OUT_OF_STOCK.value,
            captured_at=captured_at,
        )
        session.add_all([healthy_snapshot, low_snapshot, out_of_stock_snapshot])
        session.flush()
        session.add_all(
            [
                InventoryAlert(
                    product_id=seeded_products[1].id,
                    snapshot_id=low_snapshot.id,
                    severity=AlertSeverity.WARNING.value,
                    message="STANDING-DESK-MAT is at or below the low-stock threshold.",
                    is_resolved=False,
                    created_at=captured_at,
                ),
                InventoryAlert(
                    product_id=seeded_products[2].id,
                    snapshot_id=out_of_stock_snapshot.id,
                    severity=AlertSeverity.CRITICAL.value,
                    message="LED-DESK-LAMP is out of stock.",
                    is_resolved=False,
                    created_at=captured_at,
                ),
            ]
        )
        session.commit()
        logger.info("Bootstrapped sample catalog data for local development")
