from sqlalchemy import func, select

from app.models import BatchStatus, Product, ProductBatch


def product_on_hand(today, warehouse_id=None):
    filters = [
        ProductBatch.product_id == Product.id,
        ProductBatch.deleted_at.is_(None),
        ProductBatch.status == BatchStatus.ACTIVE,
        ProductBatch.expiry_date >= today,
    ]
    if warehouse_id is not None:
        filters.append(ProductBatch.warehouse_id == warehouse_id)
    return (
        select(
            func.coalesce(
                func.sum(
                    func.greatest(
                        ProductBatch.quantity_available - ProductBatch.quantity_reserved, 0
                    )
                ),
                0,
            )
        )
        .where(*filters)
        .correlate(Product)
        .scalar_subquery()
    )


def stock_filter(on_hand, threshold, stock):
    if stock == "out":
        return on_hand == 0
    if stock == "low":
        return (on_hand > 0) & (on_hand <= threshold)
    if stock == "in":
        return (on_hand > 0) & (on_hand > threshold)
    return True


async def counted_page(session, statement, *, page, page_size):
    """Count and page in one statement; preserve totals for an empty later page."""
    query = statement.add_columns(func.count().over().label("_page_total"))
    if page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(query)).unique().all()
    if rows:
        return [row[:-1] for row in rows], rows[0][-1]
    total = 0
    if page > 1:
        total = await session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
    return [], total or 0
