"""Provider seams. OTP uses delivery immediately; commerce uses a durable outbox."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger("kabisa.notifications")


class NotificationProvider(Protocol):
    async def send(self, *, recipient: str, channel: str, message: str, reference: str) -> None: ...


class ConsoleNotificationProvider:
    async def send(self, *, recipient: str, channel: str, message: str, reference: str) -> None:
        if not settings.is_development:
            raise AppError(
                status_code=503,
                detail="Message delivery is not configured.",
                code="notification_not_configured",
            )
        # No phone, email, or customer identity is logged. Development only.
        logger.info(
            "development_notification reference=%s channel=%s message=%s",
            reference,
            channel,
            message,
        )


class GatewayNotificationProvider:
    """Vendor-neutral HTTPS bridge. A deployment adapter can map this to any gateway."""

    async def send(self, *, recipient: str, channel: str, message: str, reference: str) -> None:
        if (
            not settings.notification_gateway_url.startswith("https://")
            or not settings.notification_gateway_token
        ):
            raise AppError(
                status_code=503,
                detail="Message delivery is not configured.",
                code="notification_not_configured",
            )

        def deliver():
            body = json.dumps(
                {
                    "to": recipient,
                    "channel": channel,
                    "message": message,
                    "reference": reference,
                    "sender": settings.notification_sender,
                }
            ).encode()
            req = Request(
                settings.notification_gateway_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.notification_gateway_token}",
                },
                method="POST",
            )
            with urlopen(req, timeout=10) as response:
                response.read(1024)

        try:
            await asyncio.to_thread(deliver)
        except (OSError, ValueError) as exc:
            raise AppError(
                status_code=503,
                detail="Message delivery is temporarily unavailable.",
                code="notification_unavailable",
            ) from exc


def notification_provider() -> NotificationProvider:
    if settings.notification_provider == "console":
        return ConsoleNotificationProvider()
    if settings.notification_provider == "gateway":
        return GatewayNotificationProvider()
    raise AppError(
        status_code=503,
        detail="Message delivery is not configured.",
        code="notification_not_configured",
    )


@dataclass(frozen=True)
class PaymentIntent:
    status: str
    reference: str
    redirect_url: str | None = None


class PaymentProvider(Protocol):
    async def initiate(
        self, *, order_id: str, amount: str, currency: str, method: str
    ) -> PaymentIntent: ...
    async def reconcile(self, *, payload: bytes, signature: str) -> dict: ...


class ManualProvider:
    async def initiate(
        self, *, order_id: str, amount: str, currency: str, method: str
    ) -> PaymentIntent:
        return PaymentIntent(status="AWAITING_PAYMENT", reference=order_id)

    async def reconcile(self, *, payload: bytes, signature: str) -> dict:
        raise AppError(
            status_code=409, detail="Payments are recorded by Kabisa staff.", code="manual_payments"
        )


class AggregatorProvider:
    """Inactive slot for a reviewed ClickPesa/Selcom adapter; never acknowledges money."""

    async def initiate(
        self, *, order_id: str, amount: str, currency: str, method: str
    ) -> PaymentIntent:
        raise AppError(
            status_code=503,
            detail="Online payments are not enabled.",
            code="payment_provider_disabled",
        )

    async def reconcile(self, *, payload: bytes, signature: str) -> dict:
        raise AppError(
            status_code=503,
            detail="Online payments are not enabled.",
            code="payment_provider_disabled",
        )


def payment_provider() -> PaymentProvider:
    return ManualProvider() if settings.payment_provider == "manual" else AggregatorProvider()
