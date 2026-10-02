from app.llm.gemini import llm
from app.llm.error_handler import get_user_friendly_error

class AnalysisAgent:
    def analyze(self, expense_details: str, policy_findings: str, receipt_findings: str) -> str:
        """
        Combines and analyzes findings from Policy and Receipt agents.
        Identifies potential risks and inconsistencies.
        """
        messages = [
            ("system", "You are the Analysis Agent. Combine the findings to identify potential risks, inconsistencies, missing information, or policy concerns. Be objective and state what is missing or doesn't align."),
            ("human", f"Expense Details:\n{expense_details}\n\nPolicy Findings:\n{policy_findings}\n\nReceipt Findings:\n{receipt_findings}")
        ]
        try:
            response = llm.invoke(messages)
            res_text = getattr(response, "text", None) or getattr(response, "content", "")
            if not res_text:
                return "Analysis completed with no additional findings."
            return str(res_text)
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="analysis_agent")
            raise RuntimeError(f"Analysis Agent Error: {friendly_err}") from e
