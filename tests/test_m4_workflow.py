import pytest
from unittest.mock import patch, MagicMock
from app.agents.coordinator_agent import (
    CoordinatorAgent,
    SESSION_STORE,
    AUDIT_HISTORY,
    get_dashboard_metrics,
    get_recent_audits,
    clear_audit_history
)


@pytest.fixture(autouse=True)
def clean_state():
    """Clears in-memory audit history and session store between tests."""
    clear_audit_history()
    SESSION_STORE.clear()
    yield
    clear_audit_history()
    SESSION_STORE.clear()


@pytest.fixture
def mock_llm():
    """Mocks all Gemini LLM invocations across agents for fast, offline testing."""
    mock_response = MagicMock()
    mock_response.text = "Mocked LLM Advisory Audit Report"
    mock_response.content = "Mocked LLM Advisory Audit Report"
    mock_response.tool_calls = []

    mock_bound = MagicMock()
    mock_bound.invoke.return_value = mock_response

    mock_llm_obj = MagicMock()
    mock_llm_obj.invoke.return_value = mock_response
    mock_llm_obj.bind_tools.return_value = mock_bound

    with patch("app.agents.policy_agent.llm", mock_llm_obj), \
         patch("app.agents.analysis_agent.llm", mock_llm_obj), \
         patch("app.agents.decision_support_agent.llm", mock_llm_obj), \
         patch("app.agents.coordinator_agent.llm", mock_llm_obj):
        yield mock_llm_obj


def test_standard_processing_workflow(mock_llm):
    """
    Verifies that a compliant expense with a matching receipt within policy limits
    routes to STANDARD_PROCESSING and records accurate telemetry.
    """
    coordinator = CoordinatorAgent()
    expense_details = """
Employee: Priya Sharma
Expense Type: Domestic Travel
Amount: ₹2500
Purpose: Regional client visit
Date: 2026-10-01
"""
    receipt_details = {
        "receipt_available": True,
        "merchant": "Express Travels",
        "receipt_date": "2026-10-01",
        "receipt_amount": 2500.0,
        "claimed_amount": 2500.0,
        "expense_date": "2026-10-01"
    }

    result = coordinator.run_audit(expense_details, receipt_details, "session_std_1")

    # M3 backwards compatibility assertions
    assert "report" in result
    assert "status" in result
    assert result["status"]["policy"] == "Completed"
    assert result["status"]["receipt"] == "Completed"
    assert result["status"]["analysis"] == "Completed"
    assert result["status"]["decision"] == "Completed"

    # M4 Triage & Decision Routing assertions
    assert result["triage_level"] == "STANDARD_PROCESSING"
    assert "STANDARD_PROCESSING (COMPLIANT)" in result["decision_path"]

    # M4 Telemetry assertions
    telemetry = result["telemetry"]
    assert telemetry["trace_id"].startswith("trace_")
    assert telemetry["total_duration_ms"] >= 0.0
    assert telemetry["decision_flags"]["policy_verified"] is True
    assert telemetry["decision_flags"]["is_over_limit"] is False
    assert telemetry["decision_flags"]["is_receipt_missing"] is False
    assert telemetry["decision_flags"]["amount_mismatch"] is False
    assert telemetry["decision_flags"]["has_failures"] is False

    # Per-agent telemetry checks
    assert len(telemetry["agent_telemetry"]) == 4
    for agent_data in telemetry["agent_telemetry"]:
        assert agent_data["status"] == "Completed"
        assert agent_data["duration_ms"] >= 0.0
        assert agent_data["error"] is None


def test_over_limit_claim_routing(mock_llm):
    """
    Verifies that an expense exceeding the category reimbursement threshold
    (e.g., Business Meals limit is ₹1,500, claimed ₹3,200) routes to ELEVATED_REVIEW.
    """
    coordinator = CoordinatorAgent()
    expense_details = """
Employee: Rohan Das
Expense Type: Business Meals
Amount: ₹3200
Purpose: Client dinner meeting
Date: 2026-10-02
"""
    receipt_details = {
        "receipt_available": True,
        "merchant": "City Bistro",
        "receipt_date": "2026-10-02",
        "receipt_amount": 3200.0,
        "claimed_amount": 3200.0,
        "expense_date": "2026-10-02"
    }

    result = coordinator.run_audit(expense_details, receipt_details, "session_over_limit")

    assert result["triage_level"] == "ELEVATED_REVIEW"
    assert "ELEVATED_REVIEW (OVER_LIMIT)" in result["decision_path"]
    assert result["telemetry"]["decision_flags"]["is_over_limit"] is True
    assert result["telemetry"]["decision_flags"]["policy_verified"] is True


def test_missing_receipt_routing(mock_llm):
    """
    Verifies that a claim without a receipt routes to DOCUMENTATION_POLICY_REVIEW
    and is never marked as STANDARD_PROCESSING.
    """
    coordinator = CoordinatorAgent()
    expense_details = """
Employee: Anita Roy
Expense Type: Hotel Accommodation
Amount: ₹4000
Purpose: Conference stay
Date: 2026-10-03
"""
    receipt_details = {
        "receipt_available": False
    }

    result = coordinator.run_audit(expense_details, receipt_details, "session_no_receipt")

    assert result["triage_level"] == "DOCUMENTATION_POLICY_REVIEW"
    assert "DOCUMENTATION_POLICY_REVIEW (MISSING_RECEIPT)" in result["decision_path"]
    assert result["telemetry"]["decision_flags"]["is_receipt_missing"] is True


def test_receipt_amount_mismatch_routing(mock_llm):
    """
    Verifies that an amount discrepancy between claimed amount and receipt amount
    routes to ELEVATED_REVIEW.
    """
    coordinator = CoordinatorAgent()
    expense_details = """
Employee: Vikram Singh
Expense Type: Domestic Travel
Amount: ₹3000
Purpose: Intercity commute
Date: 2026-10-04
"""
    receipt_details = {
        "receipt_available": True,
        "merchant": "Express Rail",
        "receipt_date": "2026-10-04",
        "receipt_amount": 2000.0,  # ₹2,000 receipt vs ₹3,000 claimed
        "claimed_amount": 3000.0,
        "expense_date": "2026-10-04"
    }

    result = coordinator.run_audit(expense_details, receipt_details, "session_mismatch")

    assert result["triage_level"] == "ELEVATED_REVIEW"
    assert "ELEVATED_REVIEW (AMOUNT_MISMATCH)" in result["decision_path"]
    assert result["telemetry"]["decision_flags"]["amount_mismatch"] is True


def test_unknown_policy_category_routing(mock_llm):
    """
    Verifies that an unverified/unknown policy category routes to DOCUMENTATION_POLICY_REVIEW.
    """
    coordinator = CoordinatorAgent()
    expense_details = """
Employee: Sameer Khan
Expense Type: Wellness Subscription
Amount: ₹1500
Purpose: Gym membership reimbursement
Date: 2026-10-05
"""
    receipt_details = {
        "receipt_available": True,
        "merchant": "FitLife Gym",
        "receipt_date": "2026-10-05",
        "receipt_amount": 1500.0,
        "claimed_amount": 1500.0,
        "expense_date": "2026-10-05"
    }

    result = coordinator.run_audit(expense_details, receipt_details, "session_unknown_cat")

    assert result["triage_level"] == "DOCUMENTATION_POLICY_REVIEW"
    assert "DOCUMENTATION_POLICY_REVIEW" in result["decision_path"]
    assert result["telemetry"]["decision_flags"]["policy_verified"] is False


def test_agent_failure_isolation_and_telemetry(mock_llm):
    """
    Verifies that when an individual agent fails, the coordinator isolates the error,
    accurately records failure telemetry, flags ELEVATED_REVIEW, and continues safely.
    """
    coordinator = CoordinatorAgent()
    expense_details = "Employee: Test\nExpense Type: Travel\nAmount: ₹1000"
    receipt_details = {"receipt_available": False}

    with patch.object(coordinator.policy_agent, 'analyze', side_effect=RuntimeError("Quota Limit Reached")):
        result = coordinator.run_audit(expense_details, receipt_details, "session_failure")

    assert result["status"]["policy"] == "Failed"
    assert result["status"]["receipt"] == "Completed"
    assert result["triage_level"] == "ELEVATED_REVIEW"
    assert "SYSTEM_FAILURE" in result["decision_path"]

    # Telemetry should record the failure accurately
    telemetry = result["telemetry"]
    assert telemetry["decision_flags"]["has_failures"] is True
    policy_telemetry = next(item for item in telemetry["agent_telemetry"] if item["agent"] == "PolicyAgent")
    assert policy_telemetry["status"] == "Failed"
    assert policy_telemetry["error"] is not None


def test_dashboard_metrics_aggregation_and_bounding(mock_llm):
    """
    Verifies that get_dashboard_metrics() correctly computes aggregate metrics
    and bounded history caps at MAX_AUDIT_HISTORY (50 entries).
    """
    coordinator = CoordinatorAgent()

    # Initial state: 0 audits
    metrics_empty = get_dashboard_metrics()
    assert metrics_empty["total_audits"] == 0
    assert metrics_empty["total_claimed"] == 0.0
    assert metrics_empty["compliance_rate"] == 0.0

    # Execute 1 compliant claim (₹1,000)
    coordinator.run_audit(
        "Employee: A\nExpense Type: Domestic Travel\nAmount: ₹1000",
        {"receipt_available": True, "merchant": "Cab", "receipt_date": "2026-10-01", "receipt_amount": 1000.0, "claimed_amount": 1000.0, "expense_date": "2026-10-01"},
        "s1"
    )

    # Execute 1 over-limit claim (₹10,000)
    coordinator.run_audit(
        "Employee: B\nExpense Type: Business Meals\nAmount: ₹10000",
        {"receipt_available": True, "merchant": "Dining", "receipt_date": "2026-10-01", "receipt_amount": 10000.0, "claimed_amount": 10000.0, "expense_date": "2026-10-01"},
        "s2"
    )

    metrics = get_dashboard_metrics()
    assert metrics["total_audits"] == 2
    assert metrics["total_claimed"] == 11000.0
    assert metrics["flagged_claims"] == 1
    assert metrics["compliance_rate"] == 50.0

    # Test recent audits query
    recent = get_recent_audits(limit=5)
    assert len(recent) == 2
    # Verify privacy: employee names and raw reports are not in global history
    for entry in recent:
        assert "employee_name" not in entry
        assert "report" not in entry
        assert "trace_id" in entry
        assert "triage_level" in entry

    # Test bounding to 50 entries
    for i in range(55):
        coordinator.run_audit(
            f"Employee: User_{i}\nExpense Type: Travel\nAmount: ₹500",
            {"receipt_available": False},
            f"s_bulk_{i}"
        )

    assert len(AUDIT_HISTORY) == 50
    metrics_bounded = get_dashboard_metrics()
    assert metrics_bounded["total_audits"] == 50
