import pytest
from unittest.mock import patch, MagicMock
from app.agents.coordinator_agent import CoordinatorAgent, SESSION_STORE

@pytest.fixture
def mock_llm():
    mock_response = MagicMock()
    mock_response.text = "Mocked LLM Response"
    mock_response.content = "Mocked LLM Response"
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

def test_normal_expense_workflow(mock_llm):
    coordinator = CoordinatorAgent()
    expense_details = "Employee: John Doe\nAmount: ₹1000\nCategory: Domestic Travel"
    receipt_details = {
        "receipt_available": True,
        "receipt_amount": 1000,
        "claimed_amount": 1000,
        "merchant": "Uber",
        "expense_date": "2023-01-01",
        "receipt_date": "2023-01-01"
    }
    
    result = coordinator.run_audit(expense_details, receipt_details, "session_1")
    
    assert result['status']['policy'] == 'Completed'
    assert result['status']['receipt'] == 'Completed'
    assert result['status']['analysis'] == 'Completed'
    assert result['status']['decision'] == 'Completed'
    assert "Mocked LLM Response" in result['report']

def test_successful_policy_retrieval(mock_llm):
    coordinator = CoordinatorAgent()
    
    tool_call_response = MagicMock()
    tool_call_response.text = ""
    tool_call_response.content = ""
    tool_call_response.tool_calls = [{
        "name": "get_expense_policy",
        "args": {"expense_type": "travel"},
        "id": "call_123"
    }]
    
    final_response = MagicMock()
    final_response.text = "Policy limit for domestic travel is ₹3,500."
    final_response.content = "Policy limit for domestic travel is ₹3,500."
    final_response.tool_calls = []

    mock_bound = MagicMock()
    mock_bound.invoke.side_effect = [tool_call_response, final_response]

    with patch("app.agents.policy_agent.llm.bind_tools", return_value=mock_bound):
        policy_findings = coordinator.policy_agent.analyze("Category: Domestic Travel")
        assert "Policy limit for domestic travel is ₹3,500." in policy_findings

def test_over_limit_expense(mock_llm):
    coordinator = CoordinatorAgent()
    expense_details = "Employee: John Doe\nAmount: ₹10000\nCategory: Business Meals"
    receipt_details = {
        "receipt_available": True,
        "receipt_amount": 10000,
        "claimed_amount": 10000,
        "merchant": "Steakhouse",
        "expense_date": "2023-01-01",
        "receipt_date": "2023-01-01"
    }
    
    result = coordinator.run_audit(expense_details, receipt_details, "session_2")
    
    assert result['status']['policy'] == 'Completed'
    assert result['status']['receipt'] == 'Completed'
    assert result['status']['analysis'] == 'Completed'

def test_missing_receipt(mock_llm):
    coordinator = CoordinatorAgent()
    expense_details = "Employee: John Doe\nAmount: ₹1000\nCategory: Domestic Travel"
    receipt_details = {"receipt_available": False}
    
    result = coordinator.run_audit(expense_details, receipt_details, "session_3")
    
    assert result['status']['policy'] == 'Completed'
    assert result['status']['receipt'] == 'Completed'
    assert result['status']['analysis'] == 'Completed'

def test_genuine_receipt_tool_failure(mock_llm):
    coordinator = CoordinatorAgent()
    
    mock_tool = MagicMock()
    mock_tool.invoke.side_effect = Exception("Database connection timeout")
    
    with patch("app.agents.receipt_agent.validate_receipt", mock_tool):
        result = coordinator.run_audit("Expense details", {"receipt_available": True}, "session_failure_test")
        assert result['status']['receipt'] == 'Failed'

def test_receipt_amount_mismatch(mock_llm):
    coordinator = CoordinatorAgent()
    expense_details = "Employee: John Doe\nAmount: ₹2000\nCategory: Domestic Travel"
    receipt_details = {
        "receipt_available": True,
        "receipt_amount": 1000,
        "claimed_amount": 2000,
        "merchant": "Uber",
        "expense_date": "2023-01-01",
        "receipt_date": "2023-01-01"
    }
    
    result = coordinator.run_audit(expense_details, receipt_details, "session_4")
    
    assert result['status']['policy'] == 'Completed'
    assert result['status']['receipt'] == 'Completed'
    assert result['status']['analysis'] == 'Completed'

def test_empty_model_responses(mock_llm):
    coordinator = CoordinatorAgent()
    
    empty_response = MagicMock()
    empty_response.text = ""
    empty_response.content = ""
    empty_response.tool_calls = []

    with patch("app.agents.analysis_agent.llm.invoke", return_value=empty_response), \
         patch("app.agents.decision_support_agent.llm.invoke", return_value=empty_response):
        
        analysis_res = coordinator.analysis_agent.analyze("details", "policy", "receipt")
        assert "no additional findings" in analysis_res.lower()
        
        decision_res = coordinator.decision_agent.generate_report("analysis")
        assert "no summary available" in decision_res.lower()

def test_short_term_memory(mock_llm):
    coordinator = CoordinatorAgent()
    expense_details = "Amount: ₹500"
    coordinator.run_audit(expense_details, {"receipt_available": False}, "session_5")
    
    response = coordinator.handle_follow_up("session_5", "What was the amount again?")
    assert "Mocked LLM Response" in response

def test_gemini_429_quota_exhaustion_in_chat(mock_llm):
    coordinator = CoordinatorAgent()
    session_id = "session_quota_test"
    expense_details = "Amount: ₹1500"
    
    # 1. Complete initial audit successfully
    coordinator.run_audit(expense_details, {"receipt_available": False}, session_id)
    
    # 2. Simulate 429 RESOURCE_EXHAUSTED error on follow-up request
    quota_error = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for metric Generate Content API requests")
    
    with patch("app.agents.coordinator_agent.llm.invoke", side_effect=quota_error):
        response = coordinator.handle_follow_up(session_id, "Is hotel covered?")
        
        # Friendly response expected
        assert response == "The AI service has temporarily reached its usage limit. Please try again later."
        assert "RESOURCE_EXHAUSTED" not in response
        assert "429" not in response
        
        # Existing session context remains preserved
        assert session_id in SESSION_STORE
        assert SESSION_STORE[session_id]['expense_details'] == expense_details
        assert SESSION_STORE[session_id]['workflow_status']['policy'] == 'Completed'

def test_unrelated_model_errors(mock_llm):
    coordinator = CoordinatorAgent()
    session_id = "session_unrelated_error_test"
    coordinator.run_audit("Amount: ₹500", {"receipt_available": False}, session_id)
    
    with patch("app.agents.coordinator_agent.llm.invoke", side_effect=Exception("Connection timed out")):
        response = coordinator.handle_follow_up(session_id, "Check again")
        assert response == "An error occurred while processing the request. Please try again later."
        assert "Connection timed out" not in response

def test_agent_failure(mock_llm):
    coordinator = CoordinatorAgent()
    
    with patch.object(coordinator.policy_agent, 'analyze', side_effect=Exception("API Error")):
        result = coordinator.run_audit("Expense", {"receipt_available": False}, "session_6")
        
    assert result['status']['policy'] == 'Failed'
    assert result['status']['analysis'] == 'Completed'
    assert result['status']['decision'] == 'Completed'

def test_missing_context():
    coordinator = CoordinatorAgent()
    response = coordinator.handle_follow_up("invalid_session", "Hello")
    assert "No active session context found" in response
