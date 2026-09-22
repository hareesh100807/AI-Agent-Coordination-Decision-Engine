
from unittest.mock import patch, Mock

from langchain_core.messages import AIMessage

from app.agents.expense_audit_agent import analyze_expense


def test_policy_tool_failure_handling():

    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_expense_policy",
                "args": {"expense_type": "travel"},
                "id": "test_tool_call_1",
                "type": "tool_call",
            }
        ],
    )

    # Create a mock tool that simulates a failure
    failing_tool = Mock()
    failing_tool.invoke.side_effect = RuntimeError(
        "Simulated policy tool failure"
    )

    with patch(
        "app.agents.expense_audit_agent.llm_with_tools"
    ) as mock_llm:

        mock_llm.invoke.side_effect = [
            tool_call,
            AIMessage(
                content="Policy lookup failed. "
                        "Manual review is required."
            ),
        ]

        with patch.dict(
            "app.agents.expense_audit_agent.tools_by_name",
            {"get_expense_policy": failing_tool}
        ):
            result = analyze_expense(
                "Employee: Ravi\n"
                "Expense Type: travel\n"
                "Amount: ₹3000"
            )

    print("\nTest Result:")
    print(result)

    assert "manual review" in result.lower()
    failing_tool.invoke.assert_called_once()

    print("\nPolicy tool exception handling test passed!")


if __name__ == "__main__":
    test_policy_tool_failure_handling()