from app.tools.expense_policy_tool import get_expense_policy
from app.llm.gemini import llm
from app.llm.error_handler import get_user_friendly_error
from langchain_core.messages import ToolMessage

class PolicyAgent:
    def analyze(self, expense_details: str) -> str:
        """
        Uses the expense policy tool to retrieve policies and checks for compliance.
        """
        llm_with_tools = llm.bind_tools([get_expense_policy])
        messages = [
            ("system", "You are the Policy Agent. Your job is to extract the expense type from the details, use the get_expense_policy tool to find the applicable rules, and summarize any potential policy limits or requirements. Do NOT accuse the user of fraud."),
            ("human", f"Expense Details:\n{expense_details}")
        ]
        
        # Simple loop for tool calls
        for _ in range(3):
            try:
                response = llm_with_tools.invoke(messages)
            except Exception as e:
                friendly_err = get_user_friendly_error(e, context="policy_agent")
                return f"Policy Agent Error: {friendly_err}"

            messages.append(response)
            
            if not getattr(response, "tool_calls", None):
                res_text = getattr(response, "text", None) or getattr(response, "content", "")
                return str(res_text) if res_text else "Policy analysis completed."
                
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                tool_args = tool_call.get("args", {}) if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                tool_id = tool_call.get("id", "") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
                
                if tool_name == "get_expense_policy":
                    try:
                        tool_result = get_expense_policy.invoke(tool_args)
                    except Exception as e:
                        tool_result = f"Error calling tool: {e}"
                else:
                    tool_result = f"Unknown tool: {tool_name}"
                    
                messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))
        
        return "Policy analysis could not be completed within the allowed steps."
