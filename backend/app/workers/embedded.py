from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from datetime import datetime

from sqlalchemy import select

from app.db import RecoveryAction, SessionLocal, WebhookEvent, utcnow
from app.workers.tasks import process_webhook, reconcile_action_job

_state: dict[str, object] = {
    "running": False,
    "last_heartbeat": None,
    "last_error": None,
    "processed_webhooks": 0,
    "reconciled_actions": 0,
}


def embedded_worker_enabled() -> bool:
    return os.getenv("EMBEDDED_WORKER_ENABLED", "false").lower() == "true"


def embedded_worker_status() -> dict[str, object]:
    heartbeat = _state["last_heartbeat"]
    return {
        "enabled": embedded_worker_enabled(),
        "status": "healthy" if _state["running"] and heartbeat else ("starting" if _state["running"] else "not_running"),
        "count": 1 if _state["running"] else 0,
        "last_heartbeat": heartbeat.isoformat() if isinstance(heartbeat, datetime) else None,
        "last_error": _state["last_error"],
        "processed_webhooks": _state["processed_webhooks"],
        "reconciled_actions": _state["reconciled_actions"],
        "mode": "embedded_database_worker",
    }


def run_embedded_cycle(batch_size: int = 20) -> dict[str, int]:
    now = utcnow()
    with SessionLocal() as db:
        webhook_ids = list(db.scalars(
            select(WebhookEvent.id)
            .where(WebhookEvent.status == "received", WebhookEvent.signature_valid.is_(True))
            .order_by(WebhookEvent.received_at)
            .limit(batch_size)
        ))
        action_ids = list(db.scalars(
            select(RecoveryAction.id)
            .where(
                RecoveryAction.provider_reference.is_not(None),
                RecoveryAction.verification_status != "verified",
                RecoveryAction.status.in_(["executed", "verification_pending"]),
                RecoveryAction.next_reconcile_at.is_not(None),
                RecoveryAction.next_reconcile_at <= now,
                RecoveryAction.reconciliation_attempts < 12,
            )
            .order_by(RecoveryAction.next_reconcile_at)
            .limit(batch_size)
        ))

    processed = 0
    reconciled = 0
    errors: list[str] = []
    for event_id in webhook_ids:
        try:
            if process_webhook(event_id):
                processed += 1
        except Exception as exc:
            errors.append(f"webhook {event_id}: {exc}")
    for action_id in action_ids:
        try:
            reconcile_action_job(action_id)
            reconciled += 1
        except Exception as exc:
            errors.append(f"action {action_id}: {exc}")

    _state["last_heartbeat"] = utcnow()
    _state["last_error"] = "; ".join(errors)[:500] if errors else None
    _state["processed_webhooks"] = int(_state["processed_webhooks"]) + processed
    _state["reconciled_actions"] = int(_state["reconciled_actions"]) + reconciled
    return {"processed_webhooks": processed, "reconciled_actions": reconciled, "errors": len(errors)}


async def run_embedded_worker() -> None:
    interval = max(1.0, float(os.getenv("EMBEDDED_WORKER_INTERVAL_SECONDS", "2")))
    _state["running"] = True
    try:
        while True:
            try:
                await asyncio.to_thread(run_embedded_cycle)
            except Exception as exc:
                _state["last_heartbeat"] = utcnow()
                _state["last_error"] = str(exc)[:500]
            await asyncio.sleep(interval)
    finally:
        _state["running"] = False


async def stop_embedded_worker(task: asyncio.Task[None] | None) -> None:
    if not task:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
