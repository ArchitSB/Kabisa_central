import io
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.errors import AppError
from app.models import AdminUser, OrderStatus
from app.schemas import ReportOptions
from app.services import export_service, reporting_service

router = APIRouter()
ExportFormat = Literal["xlsx", "csv"]


@router.get("/options", response_model=ReportOptions)
async def report_options(
    _: Annotated[AdminUser, Depends(require_permission("reports.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReportOptions:
    return await reporting_service.report_options(session)


def _check_export(current_user: AdminUser, export: ExportFormat | None) -> None:
    if export and "reports.export" not in {
        permission.code for permission in current_user.role.permissions
    }:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export reports.",
            code="permission_denied",
        )


def _download(
    *,
    export: ExportFormat,
    title: str,
    filename: str,
    meta,
    headers: list[str],
    rows: list[list],
) -> StreamingResponse:
    content = (
        export_service.build_xlsx(meta=meta, title=title, headers=headers, rows=rows)
        if export == "xlsx"
        else export_service.build_csv(meta=meta, title=title, headers=headers, rows=rows)
    )
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if export == "xlsx"
        else "text/csv; charset=utf-8"
    )
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{export}"'},
    )


@router.get("/sales", response_model=None)
async def sales_report(
    current_user: Annotated[AdminUser, Depends(require_permission("reports.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    date_from: date | None = None,
    date_to: date | None = None,
    customer_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    order_status: OrderStatus | None = None,
    export: ExportFormat | None = None,
):
    _check_export(current_user, export)
    report = await reporting_service.sales_report(
        session,
        page=1 if export else page,
        page_size=50_000 if export else page_size,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        order_status=order_status,
    )
    if not export:
        return report
    return _download(
        export=export,
        title="Sales report",
        filename="kabisa-sales-report",
        meta=report.meta,
        headers=[
            "Order",
            "Date",
            "Customer",
            "Warehouse",
            "Status",
            "Payment",
            "Total",
            "Collected",
            "Balance",
        ],
        rows=[
            [
                row.order_number,
                row.order_date,
                row.customer_name,
                row.warehouse_name,
                row.status,
                row.payment_status,
                row.total_amount,
                row.collected_amount,
                row.balance_due,
            ]
            for row in report.items
        ],
    )


@router.get("/products", response_model=None)
async def products_report(
    current_user: Annotated[AdminUser, Depends(require_permission("reports.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: UUID | None = None,
    brand_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    export: ExportFormat | None = None,
):
    _check_export(current_user, export)
    report = await reporting_service.product_report(
        session,
        page=1 if export else page,
        page_size=50_000 if export else page_size,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        brand_id=brand_id,
        warehouse_id=warehouse_id,
    )
    if not export:
        return report
    return _download(
        export=export,
        title="Products report",
        filename="kabisa-products-report",
        meta=report.meta,
        headers=["SKU", "Product", "Brand", "Category", "HSN", "Qty", "Revenue", "Tax", "Discount"],
        rows=[
            [
                row.sku,
                row.name,
                row.brand,
                row.category,
                row.hsn_code,
                row.quantity_sold,
                row.revenue,
                row.tax,
                row.discount,
            ]
            for row in report.items
        ],
    )


@router.get("/receivables", response_model=None)
async def receivables_report(
    current_user: Annotated[AdminUser, Depends(require_permission("reports.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    date_from: date | None = None,
    date_to: date | None = None,
    customer_id: UUID | None = None,
    export: ExportFormat | None = None,
):
    _check_export(current_user, export)
    report = await reporting_service.receivables_report(
        session,
        page=1 if export else page,
        page_size=50_000 if export else page_size,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
    )
    if not export:
        return report
    return _download(
        export=export,
        title="Receivables report",
        filename="kabisa-receivables-report",
        meta=report.meta,
        headers=[
            "Order",
            "Date",
            "Customer",
            "Payment",
            "Total",
            "Collected",
            "Balance",
            "Age days",
            "Aging",
        ],
        rows=[
            [
                row.order_number,
                row.order_date,
                row.customer_name,
                row.payment_status,
                row.total_amount,
                row.collected_amount,
                row.balance_due,
                row.age_days,
                row.aging_bucket,
            ]
            for row in report.items
        ],
    )


@router.get("/inventory", response_model=None)
async def inventory_report(
    current_user: Annotated[AdminUser, Depends(require_permission("reports.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    warehouse_id: UUID | None = None,
    category_id: UUID | None = None,
    brand_id: UUID | None = None,
    export: ExportFormat | None = None,
):
    _check_export(current_user, export)
    report = await reporting_service.inventory_report(
        session,
        page=1 if export else page,
        page_size=50_000 if export else page_size,
        warehouse_id=warehouse_id,
        category_id=category_id,
        brand_id=brand_id,
    )
    if not export:
        return report
    return _download(
        export=export,
        title="Inventory report",
        filename="kabisa-inventory-report",
        meta=report.meta,
        headers=[
            "SKU",
            "Product",
            "Brand",
            "Category",
            "Warehouse",
            "Batch",
            "Expiry",
            "On hand",
            "Cost",
            "Stock value",
            "Low stock",
            "Expiring",
            "Dead stock",
            "Last outbound",
        ],
        rows=[
            [
                row.sku,
                row.product_name,
                row.brand,
                row.category,
                row.warehouse_name,
                row.batch_number,
                row.expiry_date,
                row.on_hand,
                row.cost_price,
                row.stock_value,
                row.low_stock,
                row.expiring_soon,
                row.dead_stock,
                row.last_outbound_at,
            ]
            for row in report.items
        ],
    )
