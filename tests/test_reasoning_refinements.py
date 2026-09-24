"""
Unit tests verifying the refined classification, category-purpose consistency,
optional field handling, and policy reasoning rules for the expense audit agent.
"""

from unittest.mock import patch, Mock
from langchain_core.messages import AIMessage, ToolMessage
from app.agents.expense_audit_agent import analyze_expense
from app.prompts.templates import expense_audit_prompt
from app.tools.expense_policy_tool import get_expense_policy


def test_prompt_formatting_and_instructions():
    """Verify that the refined system prompt correctly formats messages and contains new rules."""
    expense_details = """
Employee: Priya Sharma
Expense Type: Domestic Travel
Amount: ₹3,200
Purpose: Regional client visit
Date: 2026-09-24
Description: N/A
"""
    messages = expense_audit_prompt.format_messages(expense_details=expense_details)
    assert len(messages) == 2
    system_text = messages[0].content
    human_text = messages[1].content

    # Assert new reasoning rules are embedded
    assert "Primary Expense Category" in system_text
    assert "Do NOT infer a second expense category" in system_text
    assert "Category-Purpose Consistency" in system_text
    assert "category-purpose mismatch" in system_text
    assert "Applicable Policy Limits" in system_text
    assert "Field Distinction (Required vs. Optional)" in system_text
    assert "Do NOT flag a missing or blank optional Description" in system_text
    assert "Priya Sharma" in human_text
    print("test_prompt_formatting_and_instructions: PASSED")


def test_primary_category_single_policy_lookup():
    """Verify that the agent only queries the primary selected category tool without inferring secondary categories."""
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_expense_policy",
                "args": {"expense_type": "travel"},
                "id": "call_policy_1",
                "type": "tool_call",
            }
        ],
    )

    final_response = AIMessage(
        content="""
1. Expense Classification: Domestic Travel (primary category).
2. Key Observations: Purpose is travel to client site.
3. Potential Policy Concerns: Claimed ₹3,200 is within the ₹3,500 limit.
4. Risk Assessment: Low risk.
5. Recommended Next Step: Proceed with standard manager review.
"""
    )

    mock_policy_tool = Mock()
    mock_policy_tool.invoke.return_value = "{'category': 'Domestic Travel', 'reimbursement_limit': 3500, 'receipt_required': True, 'approval_required_above_limit': True}"

    with patch("app.agents.expense_audit_agent.llm_with_tools") as mock_llm:
        mock_llm.invoke.side_effect = [tool_call, final_response]

        with patch.dict("app.agents.expense_audit_agent.tools_by_name", {"get_expense_policy": mock_policy_tool}):
            result = analyze_expense(
                """
Employee: Aarav Patel
Expense Type: Domestic Travel
Amount: ₹3,200
Purpose: Travel to regional hub including lunch with team
Date: 2026-09-24
Description: 
""",
                receipt_details={
                    "receipt_available": True,
                    "merchant": "Express Travels",
                    "receipt_date": "2026-09-24",
                    "receipt_amount": 3200.0,
                    "claimed_amount": 3200.0,
                    "expense_date": "2026-09-24"
                }
            )

    assert "Domestic Travel" in result
    assert "₹3,500 limit" in result or "within" in result.lower()
    mock_policy_tool.invoke.assert_called_once_with({"expense_type": "travel"})
    print("test_primary_category_single_policy_lookup: PASSED")


def test_category_purpose_mismatch_reasoning():
    """Verify agent handling when category and purpose are mismatched."""
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_expense_policy",
                "args": {"expense_type": "travel"},
                "id": "call_policy_mismatch",
                "type": "tool_call",
            }
        ],
    )

    final_response = AIMessage(
        content="""
1. Expense Classification: Submitted under Domestic Travel.
2. Key Observations: Potential category-purpose mismatch detected. Purpose is for software license purchase rather than travel.
3. Potential Policy Concerns: Travel policy retrieved (limit ₹3,500), but expense nature does not align with travel.
4. Risk Assessment: Requires review due to category-purpose inconsistency.
5. Recommended Next Step: Request clarification from employee and recommend reclassifying expense.
"""
    )

    mock_policy_tool = Mock()
    mock_policy_tool.invoke.return_value = "{'category': 'Domestic Travel', 'reimbursement_limit': 3500, 'receipt_required': True}"

    with patch("app.agents.expense_audit_agent.llm_with_tools") as mock_llm:
        mock_llm.invoke.side_effect = [tool_call, final_response]

        with patch.dict("app.agents.expense_audit_agent.tools_by_name", {"get_expense_policy": mock_policy_tool}):
            result = analyze_expense(
                """
Employee: Meera Nair
Expense Type: Domestic Travel
Amount: ₹2,500
Purpose: Annual software IDE subscription renewal
Date: 2026-09-24
Description: N/A
"""
            )

    assert "category-purpose mismatch" in result.lower() or "inconsistency" in result.lower()
    assert "reclassifying" in result.lower() or "clarification" in result.lower()
    print("test_category_purpose_mismatch_reasoning: PASSED")


def test_optional_description_not_flagged_as_violation():
    """Verify that blank optional description is not flagged as a policy breach."""
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_expense_policy",
                "args": {"expense_type": "meals"},
                "id": "call_policy_meals",
                "type": "tool_call",
            }
        ],
    )

    final_response = AIMessage(
        content="""
1. Expense Classification: Business Meals.
2. Key Observations: Purpose is client lunch discussion. Description is omitted (optional field).
3. Potential Policy Concerns: No policy violation. Claimed ₹1,200 is within the ₹1,500 limit.
4. Risk Assessment: Low risk.
5. Recommended Next Step: Standard approval workflow.
"""
    )

    mock_policy_tool = Mock()
    mock_policy_tool.invoke.return_value = "{'category': 'Business Meals', 'reimbursement_limit': 1500, 'receipt_required': True}"

    with patch("app.agents.expense_audit_agent.llm_with_tools") as mock_llm:
        mock_llm.invoke.side_effect = [tool_call, final_response]

        with patch.dict("app.agents.expense_audit_agent.tools_by_name", {"get_expense_policy": mock_policy_tool}):
            result = analyze_expense(
                """
Employee: Rohan Das
Expense Type: Business Meals
Amount: ₹1,200
Purpose: Client lunch meeting
Date: 2026-09-24
Description: 
"""
            )

    assert "no policy violation" in result.lower()
    assert "Business Meals" in result
    print("test_optional_description_not_flagged_as_violation: PASSED")


if __name__ == "__main__":
    test_prompt_formatting_and_instructions()
    test_primary_category_single_policy_lookup()
    test_category_purpose_mismatch_reasoning()
    test_optional_description_not_flagged_as_violation()
    print("\nAll refined classification & policy reasoning tests PASSED successfully!")
