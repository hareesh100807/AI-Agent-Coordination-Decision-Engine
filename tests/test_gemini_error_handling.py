
from unittest.mock import patch

from app.agents.expense_audit_agent import analyze_expense


def test_gemini_failure_handling():

    with patch(
        "app.agents.expense_audit_agent.llm_with_tools",
    ) as mock_llm:

        mock_llm.invoke.side_effect = RuntimeError(
            "Simulated Gemini API failure"
        )

        result = analyze_expense(
            "Employee: Ravi\nExpense Type: travel\nAmount: ₹3000"
        )

    print("\nTest Result:")
    print(result)

    assert "AI audit unavailable" in result
    assert "could not complete" in result

    print("\nGemini exception handling test passed!")


if __name__ == "__main__":
    test_gemini_failure_handling()