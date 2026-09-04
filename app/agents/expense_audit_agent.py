from app.prompts.templates import expense_audit_prompt
from app.llm.gemini import llm


def analyze_expense(expense_details):
    messages = expense_audit_prompt.format_messages(
        expense_details=expense_details
    )

    response = llm.invoke(messages)

    return response.text