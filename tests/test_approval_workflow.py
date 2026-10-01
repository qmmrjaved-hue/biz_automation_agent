"""
Pure-logic tests for the approval_workflow state machine. DRY_RUN defaults
to true, so the notification step just logs — no email credentials needed.
Each test points memory at an isolated SQLite file so runs don't interfere.
"""

import pytest

import memory
from config import settings
from skills import approval_workflow


@pytest.fixture(autouse=True)
def isolated_memory_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "memory_db_path", str(tmp_path / "test_agent.db"))
    yield


def test_create_request_starts_pending():
    approval = approval_workflow.create_request("Nuovo laptop", "Mario Rossi", ["manager", "finance"])
    assert approval.status == "pending"
    assert approval.current_step_index == 0


def test_approving_all_steps_marks_approved():
    approval = approval_workflow.create_request("Nuovo laptop", "Mario Rossi", ["manager", "finance"])
    approval = approval_workflow.decide(approval.request_id, "approve", "Manager")
    assert approval.status == "pending"
    assert approval.current_step_index == 1

    approval = approval_workflow.decide(approval.request_id, "approve", "Finance")
    assert approval.status == "approved"
    assert len(approval.history) == 2


def test_rejecting_stops_the_workflow():
    approval = approval_workflow.create_request("Nuovo laptop", "Mario Rossi", ["manager", "finance"])
    approval = approval_workflow.decide(approval.request_id, "reject", "Manager")
    assert approval.status == "rejected"


def test_deciding_a_finished_request_raises():
    approval = approval_workflow.create_request("Nuovo laptop", "Mario Rossi", ["manager"])
    approval_workflow.decide(approval.request_id, "approve", "Manager")
    with pytest.raises(ValueError):
        approval_workflow.decide(approval.request_id, "approve", "Manager")


def test_list_pending_only_returns_open_requests():
    a = approval_workflow.create_request("A", "Mario", ["manager"])
    approval_workflow.create_request("B", "Mario", ["manager"])
    approval_workflow.decide(a.request_id, "approve", "Manager")

    pending = approval_workflow.list_pending()
    assert all(p.status == "pending" for p in pending)
    assert a.request_id not in [p.request_id for p in pending]
