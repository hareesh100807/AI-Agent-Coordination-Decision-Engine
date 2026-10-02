import uuid

# In-memory store for conversational context (short-term memory)
# Structure: { session_id: { 'expense_details': dict, 'audit_result': str, 'messages': list } }
SESSION_STORE = {}

from app.agents.policy_agent import PolicyAgent
from app.agents.receipt_agent import ReceiptAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.decision_support_agent import DecisionSupportAgent
from app.llm.gemini import llm
from app.llm.error_handler import get_user_friendly_error

class CoordinatorAgent:
    def __init__(self):
        self.policy_agent = PolicyAgent()
        self.receipt_agent = ReceiptAgent()
        self.analysis_agent = AnalysisAgent()
        self.decision_agent = DecisionSupportAgent()

    def run_audit(self, expense_details: str, receipt_details: dict, session_id: str) -> dict:
        """
        Executes the multi-agent workflow and returns a structured result.
        """
        # Initialize or update session context
        if session_id not in SESSION_STORE:
            SESSION_STORE[session_id] = {'messages': []}
        SESSION_STORE[session_id]['expense_details'] = expense_details
        SESSION_STORE[session_id]['receipt_details'] = receipt_details

        workflow_status = {
            'policy': 'Pending',
            'receipt': 'Pending',
            'analysis': 'Pending',
            'decision': 'Pending',
        }

        # 1. Policy Agent
        try:
            policy_findings = self.policy_agent.analyze(expense_details)
            if "Policy Agent Error" in policy_findings:
                workflow_status['policy'] = 'Failed'
            else:
                workflow_status['policy'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_policy")
            policy_findings = f"Policy Agent Error: {friendly_err}"
            workflow_status['policy'] = 'Failed'

        # 2. Receipt Agent
        try:
            receipt_findings = self.receipt_agent.analyze(receipt_details)
            if "Receipt Agent Error" in receipt_findings:
                workflow_status['receipt'] = 'Failed'
            else:
                workflow_status['receipt'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_receipt")
            receipt_findings = f"Receipt Agent Error: {friendly_err}"
            workflow_status['receipt'] = 'Failed'

        # 3. Analysis Agent
        try:
            analysis_findings = self.analysis_agent.analyze(expense_details, policy_findings, receipt_findings)
            if "Analysis Agent Error" in analysis_findings:
                workflow_status['analysis'] = 'Failed'
            else:
                workflow_status['analysis'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_analysis")
            analysis_findings = f"Analysis Agent Error: {friendly_err}"
            workflow_status['analysis'] = 'Failed'

        # 4. Decision Support Agent
        try:
            final_report = self.decision_agent.generate_report(analysis_findings)
            if "Decision Support Agent Error" in final_report:
                workflow_status['decision'] = 'Failed'
            else:
                workflow_status['decision'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_decision")
            final_report = f"Decision Support Agent Error: {friendly_err}"
            workflow_status['decision'] = 'Failed'

        # Save to short-term memory
        SESSION_STORE[session_id]['audit_result'] = final_report
        SESSION_STORE[session_id]['workflow_status'] = workflow_status

        return {
            'report': final_report,
            'status': workflow_status
        }

    def handle_follow_up(self, session_id: str, user_message: str) -> str:
        """
        Uses short-term memory to handle a follow-up conversation about the current expense.
        """
        context = SESSION_STORE.get(session_id)
        if not context:
            return "No active session context found. Please submit an expense first."

        # Maintain chat history
        context['messages'].append({"role": "user", "content": user_message})

        expense_info = context.get('expense_details', 'Unknown')
        audit_res = context.get('audit_result', 'No audit performed yet.')

        system_prompt = f"""
You are the Coordinator Agent for an Expense Audit System.
Use the following context to answer the user's follow-up question.
Do NOT make final approval/rejection decisions. Keep answers advisory.

Expense Details:
{expense_info}

Previous Audit Result:
{audit_res}
"""
        messages = [
            ("system", system_prompt)
        ]
        
        # Add past 5 messages using human/assistant roles
        for msg in context['messages'][-5:]:
            role = "human" if msg['role'] == "user" else "assistant"
            messages.append((role, msg['content']))

        try:
            response = llm.invoke(messages)
            ai_msg = getattr(response, "text", None) or getattr(response, "content", "")
            if not ai_msg:
                ai_msg = "No response generated by the agent."
        except Exception as e:
            ai_msg = get_user_friendly_error(e, context="follow_up_chat")

        context['messages'].append({"role": "assistant", "content": ai_msg})
        return ai_msg
