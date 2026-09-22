
from app.prompts.templates import expense_audit_prompt
from app.llm.gemini import llm

from app.tools.expense_policy_tool import get_expense_policy
from app.tools.receipt_validation_tool import validate_receipt
from langchain_core.messages import ToolMessage


# Register the tools available to the agent
tools = [get_expense_policy]

# Create a lookup for tools by name
tools_by_name = {
    tool.name: tool for tool in tools
}

# Allow Gemini to request tool calls
llm_with_tools = llm.bind_tools(tools)



def analyze_expense(expense_details, receipt_details=None):

    messages = expense_audit_prompt.format_messages(
        expense_details=expense_details
    )

    # Validate receipt details directly
    if receipt_details is not None:
        try:
            receipt_result = validate_receipt.invoke(
                receipt_details
            )

            print("\n[Tool Executed]: validate_receipt")
            print(f"[Tool Input]: {receipt_details}")
            print(f"[Tool Result]: {receipt_result}\n")

        except Exception as error:
            receipt_result = (
                f"Receipt validation failed: "
                f"{type(error).__name__}"
            )

        # Add validation result to Gemini's context
        messages.append(
            (
                "human",
                f"Receipt Validation Result: {receipt_result}"
            )
        )

    # Continue with Gemini's policy tool workflow
    for _ in range(5):
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            print(
                f"\n[Gemini Error]: "
                f"{type(e).__name__}: {e}"
            )

            return (
                "AI audit unavailable. Gemini could not "
                "complete the expense analysis. "
                "Please try again later. "
                "The receipt validation result, if available, "
                "is a separate preliminary check."
            )
        messages.append(response)

        if not response.tool_calls:
            return response.text

        for tool_call in response.tool_calls:

            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            selected_tool = tools_by_name.get(tool_name)

            try:
                if selected_tool is None:
                    tool_result = f"Unknown tool: {tool_name}"
                else:
                    tool_result = selected_tool.invoke(tool_args)

                    print(f"\n[Tool Executed]: {tool_name}")
                    print(f"[Tool Input]: {tool_args}")
                    print(f"[Tool Result]: {tool_result}\n")

            except Exception as error:
                tool_result = (
                    f"Tool execution failed: "
                    f"{type(error).__name__}. "
                    "The requested information could not be retrieved."
                )

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id
                )
            )

    return (
        "The agent could not complete the analysis "
        "within the allowed tool-call steps."
    )