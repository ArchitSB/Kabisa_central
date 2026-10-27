from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.models import AdminUser, ProductBatch, ProductImage, ProductPrice
from app.schemas.catalog import ProductUpdate
from app.services import catalog_service

from tests.test_catalog_inventory import _catalog_records


@pytest.mark.parametrize("operation", ["view", "save"])
async def test_populated_product_detail_in_a_fresh_session(test_session_factory, operation):
    async with test_session_factory() as session:
        user, warehouse, product, tiers = await _catalog_records(session)
        product_id, user_id = product.id, user.id
        session.add_all(
            [
                ProductImage(
                    product_id=product_id,
                    file_path="/uploads/products/test.png",
                    is_primary=True,
                    sort_order=0,
                ),
                ProductPrice(product_id=product_id, price_tier_id=tiers[0].id, price=100),
                ProductBatch(
                    product_id=product_id,
                    warehouse_id=warehouse.id,
                    batch_number="DETAIL-REGRESSION",
                    expiry_date=date.today() + timedelta(days=90),
                    received_date=date.today(),
                    quantity_available=12,
                    quantity_reserved=2,
                ),
            ]
        )
        await session.commit()

    # A new request must not depend on relationships left in a seed session's identity map.
    async with test_session_factory() as session:
        if operation == "save":
            user = await session.get(AdminUser, user_id)
            detail = await catalog_service.update_product(
                session, product_id, ProductUpdate(name="Updated catalog product"), user
            )
            assert detail.name == "Updated catalog product"
        else:
            detail = await catalog_service.product_detail(session, product_id)
        assert detail.on_hand == 10
        assert detail.primary_image == "/uploads/products/test.png"
        assert len(detail.images) == len(detail.prices) == len(detail.batches) == 1
        assert detail.prices[0].price == Decimal("100")
        assert detail.batches[0].warehouse_name == "Test Warehouse"

    async with test_session_factory() as session:
        repeated = await catalog_service.product_detail(session, product_id)
        assert repeated.name == detail.name
        assert repeated.on_hand == 10
