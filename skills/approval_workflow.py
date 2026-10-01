"""
approval_workflow.py — a sequential-step approval state machine.

A request moves through an ordered list of steps (e.g. ["manager",
"finance"]); each step must be approved before the next step's owner is
notified. A single rejection at any step ends the workflow as "rejected".

Public functions:
  - create_request(title, requester, steps) -> ApprovalRequest
  - decide(request_id, decision, actor) -> ApprovalRequest
  - get_status(request_id) -> ApprovalRequest
  - list_pending() -> list[ApprovalRequest]
"""

import uuid
from datetime import datetime

import memory
from adapters import email_adapter
from config import settings
from models import ApprovalRequest


def _to_model(d: dict) -> ApprovalRequest:
    return ApprovalRequest(
        request_id=d["request_id"], title=d["title"], requester=d["requester"],
        steps=d["steps"], current_step_index=d["current_step_index"],
        status=d["status"], history=d["history"],
        created_at=d["created_at"], updated_at=d["updated_at"],
    )


def _notify_step_owner(approval: ApprovalRequest) -> None:
    if approval.status != "pending" or approval.current_step_index >= len(approval.steps):
        return
    owner = approval.steps[approval.current_step_index]
    routing = settings.routing_table()
    to_addr = routing.get(owner.lower(), owner if "@" in owner else "")
    if not to_addr:
        print(f"[approval_workflow] No email configured for step owner '{owner}' — skipping notification.")
        return
    email_adapter.send_email(
        to_addr=to_addr,
        subject=f"Approvazione richiesta: {approval.title}",
        body=(
            f"Richiesta '{approval.title}' di {approval.requester} è in attesa "
            f"della tua approvazione (step: {owner}).\nID richiesta: {approval.request_id}"
        ),
    )


def create_request(title: str, requester: str, steps: list) -> ApprovalRequest:
    """
    Open a new approval request and notify the first step's owner.

    Args:
        title:     Short description of what's being approved.
        requester: Who is asking for approval.
        steps:     Ordered list of step owners (role names or email addresses).

    Returns:
        The created ApprovalRequest.
    """
    approval = ApprovalRequest(
        request_id=str(uuid.uuid4())[:8],
        title=title,
        requester=requester,
        steps=steps,
    )
    memory.save_approval(approval)
    _notify_step_owner(approval)
    print(f"[approval_workflow] Created request '{approval.request_id}' — {title}.")
    return approval


def decide(request_id: str, decision: str, actor: str) -> ApprovalRequest:
    """
    Record a decision ("approve" or "reject") for the current step of a
    request. Approving the last step marks the whole request "approved";
    rejecting at any step marks it "rejected" immediately.

    Args:
        request_id: The ID returned by create_request().
        decision:   "approve" or "reject".
        actor:      Who made the decision.

    Returns:
        The updated ApprovalRequest.

    Raises:
        ValueError: if the request doesn't exist, is already finished, or
            decision isn't "approve"/"reject".
    """
    if decision not in ("approve", "reject"):
        raise ValueError(f"[approval_workflow] decision must be 'approve' or 'reject', got {decision!r}")

    data = memory.load_approval(request_id)
    if data is None:
        raise ValueError(f"[approval_workflow] No request found with ID '{request_id}'")
    approval = _to_model(data)

    if approval.status != "pending":
        raise ValueError(f"[approval_workflow] Request '{request_id}' is already {approval.status}")

    step = approval.steps[approval.current_step_index]
    approval.history.append({
        "step": step, "decision": decision, "actor": actor,
        "at": datetime.now().isoformat(timespec="seconds"),
    })

    if decision == "reject":
        approval.status = "rejected"
    else:
        approval.current_step_index += 1
        if approval.current_step_index >= len(approval.steps):
            approval.status = "approved"

    approval.updated_at = datetime.now().isoformat(timespec="seconds")
    memory.save_approval(approval)

    if approval.status == "pending":
        _notify_step_owner(approval)

    print(f"[approval_workflow] Request '{request_id}' — {step} {decision}d by {actor}. "
          f"Status: {approval.status}.")
    return approval


def get_status(request_id: str) -> ApprovalRequest:
    """Return the current state of a request, or raise if it doesn't exist."""
    data = memory.load_approval(request_id)
    if data is None:
        raise ValueError(f"[approval_workflow] No request found with ID '{request_id}'")
    return _to_model(data)


def list_pending() -> list:
    """Return all requests currently awaiting a decision."""
    return [_to_model(d) for d in memory.list_approvals(status="pending")]
