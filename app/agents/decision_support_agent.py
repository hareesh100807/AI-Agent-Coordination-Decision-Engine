from app.llm.gemini import llm
from app.llm.error_handler import get_user_friendly_error

class DecisionSupportAgent:
    def generate_report(self, analysis_findings: str) -> str:
        """
        Produces the final advisory audit result based on the combined analysis.
        Uses cautious language (never makes final financial decisions).
        """
        messages = [
            ("system", "You are the Decision Support Agent. Based on the analysis, produce a final advisory audit result. Summarize findings and provide recommendations.\nCRITICAL RULES:\n1. Never make a final financial approval/rejection decision.\n2. Never accuse an employee of fraud.\n3. Use cautious language like 'potential risk', 'possible policy issue', 'requires review', 'recommendation: human review'."),
            ("human", f"Analysis Findings:\n{analysis_findings}")
        ]
        try:
            response = llm.invoke(messages)
            res_text = getattr(response, "text", None) or getattr(response, "content", "")
            if not res_text:
                return "Decision support analysis completed with no summary available."
            return str(res_text)
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="decision_support_agent")
            raise RuntimeError(f"Decision Support Agent Error: {friendly_err}") from e
