"""Webhook delivery creation/dispatch for LMS events."""

import hashlib
import hmac
import json
from datetime import timedelta
from urllib import request as urlrequest

from django.conf import settings
from django.utils import timezone

from learning.models import Webhook, WebhookDelivery


def _signature(secret: str, body: bytes) -> str:
    dig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={dig}"


def _send_delivery(delivery: WebhookDelivery):
    payload = delivery.payload or {}
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "MediaCMS-LMS-Webhook/1.0",
        "X-MediaCMS-Event": delivery.event_type,
        "X-MediaCMS-Delivery-ID": str(delivery.id),
    }
    if delivery.webhook.secret:
        headers["X-MediaCMS-Signature"] = _signature(delivery.webhook.secret, body)

    req = urlrequest.Request(
        delivery.webhook.url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            resp_body = resp.read(2000).decode("utf-8", errors="replace")
            code = int(resp.getcode() or 0)
    except Exception as exc:
        code = 0
        resp_body = str(exc)

    delivery.attempted_at = timezone.now()
    delivery.response_code = code if code > 0 else None
    delivery.response_body = resp_body[:2000]
    delivery.webhook.last_delivered_at = timezone.now()

    if 200 <= code < 300:
        delivery.status = "delivered"
        delivery.next_retry_at = None
        delivery.webhook.failure_count = 0
    else:
        delivery.status = "failed"
        delivery.webhook.failure_count = int(delivery.webhook.failure_count or 0) + 1
        max_retries = int(getattr(settings, "LMS_WEBHOOK_MAX_RETRIES", 3))
        if delivery.webhook.failure_count < max_retries:
            delay_minutes = min(60, 2 ** delivery.webhook.failure_count)
            delivery.next_retry_at = timezone.now() + timedelta(minutes=delay_minutes)
        else:
            delivery.next_retry_at = None

    delivery.webhook.save(update_fields=["last_delivered_at", "failure_count"])
    delivery.save(update_fields=["status", "response_code", "response_body", "attempted_at", "next_retry_at"])
    return delivery


def dispatch_pending_delivery(delivery_id: int):
    delivery = WebhookDelivery.objects.select_related("webhook").filter(pk=delivery_id).first()
    if not delivery or delivery.status == "delivered":
        return None
    return _send_delivery(delivery)


def create_webhook_deliveries(event_type: str, payload: dict, *, course=None):
    qs = Webhook.objects.filter(is_active=True)
    if course is not None:
        # Keep Phase-7 minimal: if webhook model later gets a course FK, this still works.
        try:
            qs = qs.filter(course=course)
        except Exception:
            pass
    hooks = list(qs)
    deliveries = []
    for w in hooks:
        events = w.events or []
        if events and event_type not in events and "*" not in events:
            continue
        deliveries.append(
            WebhookDelivery.objects.create(
                webhook=w,
                event_type=event_type,
                payload=payload,
                status="pending",
            )
        )
    return deliveries


def maybe_dispatch_event_webhooks(event_type: str, payload: dict, *, course=None):
    deliveries = create_webhook_deliveries(event_type, payload, course=course)
    if not deliveries:
        return []

    async_enabled = bool(getattr(settings, "LMS_WEBHOOK_ASYNC_DISPATCH", False))
    if async_enabled:
        try:
            from learning.tasks import dispatch_webhook_delivery_task

            for d in deliveries:
                dispatch_webhook_delivery_task.delay(d.id)
            return deliveries
        except Exception:
            pass

    for d in deliveries:
        dispatch_pending_delivery(d.id)
    return deliveries
