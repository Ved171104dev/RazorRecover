from __future__ import annotations

from uuid import uuid4

import pytest

from app.db import RecoveryAction, SessionLocal, WebhookEvent, utcnow
from app.workers.embedded import run_embedded_cycle
from app.workers.tasks import process_webhook, reconcile_action_job


def test_embedded_cycle_processes_persisted_webhook_exactly_once():
    event_id=f"evt_embedded_{uuid4()}"
    with SessionLocal() as db:
        event=WebhookEvent(
            event_id=event_id,
            event_type="payment.captured",
            payload_sha256="a"*64,
            signature_valid=True,
            status="received",
            payload={"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_unmatched","amount":100,"status":"captured","notes":{}}}}},
        )
        db.add(event);db.commit();database_id=event.id

    assert run_embedded_cycle()["processed_webhooks"]>=1
    assert process_webhook(database_id) is False
    with SessionLocal() as db:
        stored=db.get(WebhookEvent,database_id)
        assert stored.status=="processed" and stored.processed_at is not None


def test_reconciliation_failure_uses_backoff(authed,monkeypatch):
    opportunity=authed.get("/api/risk/opportunities").json()["items"][0]
    prepared=authed.post("/api/actions/prepare",json={"opportunity_ids":[opportunity["id"]]}).json()["items"][0]
    with SessionLocal() as db:
        action=db.get(RecoveryAction,prepared["id"])
        action.status="executed";action.provider_reference=f"plink_{uuid4()}";action.next_reconcile_at=utcnow();action.reconciliation_attempts=0;db.commit();action_id=action.id

    def fail(*_args,**_kwargs):raise RuntimeError("provider temporarily unavailable")
    monkeypatch.setattr("app.workers.tasks.reconcile_action",fail)
    before=utcnow()
    with pytest.raises(RuntimeError,match="temporarily unavailable"):
        reconcile_action_job(action_id)
    with SessionLocal() as db:
        action=db.get(RecoveryAction,action_id)
        assert action.reconciliation_attempts==1
        assert (action.next_reconcile_at-before).total_seconds()>=299
        assert "temporarily unavailable" in action.execution_result["reconciliation_error"]
