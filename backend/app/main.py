"""FastAPI service exposing the Part 1 planning graph.

Endpoints:
- ``GET  /health``          liveness + whether a real LLM is active
- ``POST /api/plan``        run the graph, return the costed option (one shot)
- ``POST /api/plan/stream`` same, streamed as Server-Sent Events (one event per
                            agent stage) so the UI can show the supervisor
                            delegating live
"""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents.graph import get_session_state, run_plan
from app.db.seed import seed
from app.llm.client import llm
from app.logging_config import configure_logging
from app.schemas import ApproveRequest, PlanRequest, VendorDecisionRequest
from app.services import vendor as vendor_svc
from app.services.orders import (
    AlreadyApprovedError,
    NotFoundError,
    approve_option,
    get_order,
)
from app.services.persistence import get_event, save_event

configure_logging()

app = FastAPI(title="Caterer — Planning & Quoting", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local-only tool
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    # Create tables and seed the catalog if the DB is empty.
    seed(reset=False)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm": "ollama" if llm.is_available() else "fallback"}


def _persist_result(requirements: dict, result: dict) -> dict:
    """Store the option set produced by a run and attach the event id.

    Only persists successful runs (at least one option produced). Persistence
    never breaks planning: on error we log and return the unpersisted result.
    """
    options = result.get("options") if result else None
    if not options:
        return result or {"type": "result", "options": [], "errors": ["no result produced"]}
    try:
        result["event_id"] = save_event(requirements, options)
    except Exception:  # noqa: BLE001
        logging.getLogger("caterer.api").exception("Failed to persist option set")
    return result


@app.post("/api/plan")
def plan_once(req: PlanRequest) -> dict:
    requirements = req.to_requirements()
    result = None
    for event in run_plan(requirements, session_id=req.session_id):
        if event["type"] == "result":
            result = event
    return _persist_result(requirements, result)


@app.post("/api/plan/stream")
def plan_stream(req: PlanRequest) -> StreamingResponse:
    requirements = req.to_requirements()

    def event_source():
        for event in run_plan(requirements, session_id=req.session_id):
            if event["type"] == "result":
                event = _persist_result(requirements, event)
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sessions/{session_id}/state")
def read_session_state(session_id: str) -> dict:
    """Return the checkpointed state for a planning session (resume/inspect)."""
    state = get_session_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session not found")
    return state


@app.get("/api/options/{event_id}")
def get_options(event_id: str) -> dict:
    """Retrieve a persisted event with its option set."""
    event = get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return event


@app.post("/api/orders/approve", status_code=201)
def approve_order(req: ApproveRequest) -> dict:
    """Freeze the chosen option into an immutable approved order (Part 1 → Part 2 hinge)."""
    try:
        return approve_option(req.event_id, req.option_id)
    except AlreadyApprovedError as exc:
        raise HTTPException(status_code=409,
                            detail={"message": str(exc), "order_id": exc.order_id})
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/orders/{order_id}")
def read_order(order_id: str) -> dict:
    """Retrieve a frozen approved order by id."""
    order = get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


@app.post("/api/orders/{order_id}/vendor-draft", status_code=201)
def vendor_draft(order_id: str) -> dict:
    """Draft a supplier order from the approved order; pauses at the approval gate."""
    try:
        return vendor_svc.draft_vendor_order(order_id)
    except vendor_svc.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/orders/{order_id}/vendor-decision")
def vendor_decision(order_id: str, req: VendorDecisionRequest) -> dict:
    """Approve (place) or reject the drafted vendor order at the human gate."""
    try:
        return vendor_svc.decide_vendor_order(order_id, req.decision)
    except vendor_svc.NoDraftError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except vendor_svc.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/orders/{order_id}/vendor")
def read_vendor_order(order_id: str) -> dict:
    """Retrieve the vendor order (draft/placed/rejected) for an approved order."""
    vo = vendor_svc.get_vendor_order(order_id)
    if vo is None:
        raise HTTPException(status_code=404, detail="no vendor order for this approved order")
    return vo
