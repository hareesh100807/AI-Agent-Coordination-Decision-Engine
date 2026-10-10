import time
import uuid
import re
from datetime import datetime

# In-memory store for conversational context (short-term memory)
# Structure: { session_id: { 'expense_details': str, 'receipt_details': dict, 'audit_result': str, 'messages': list, 'telemetry': dict, 'workflow_status': dict } }
SESSION_STORE = {}

# Bounded in-memory audit history (max 50 records) for execution tracking & metrics
# Stores only sanitized, non-sensitive audit metadata (no raw employee names or reports)
AUDIT_HISTORY = []
MAX_AUDIT_HISTORY = 50

from app.agents.policy_agent import PolicyAgent
from app.agents.receipt_agent import ReceiptAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.decision_support_agent import DecisionSupportAgent
from app.llm.gemini import llm
from app.llm.error_handler import get_user_friendly_error
from app.tools.expense_policy_tool import load_knowledge_policies, COMPANY_POLICIES, POLICY_ALIASES


def extract_claim_parameters(expense_details: str, receipt_details: dict):
    """
    Extracts structured parameters (claimed amount, category) from
    expense details text and receipt details dictionary.
    """
    claimed_amount = 0.0
    category = ""

    if isinstance(receipt_details, dict):
        if receipt_details.get("claimed_amount") is not None:
            try:
                claimed_amount = float(receipt_details["claimed_amount"])
            except (ValueError, TypeError):
                pass

    if claimed_amount <= 0.0 and expense_details:
        amt_match = re.search(
            r'(?:Amount|Claimed Amount)[\s:]*₹?\s*([\d,]+(?:\.\d+)?)',
            str(expense_details),
            re.IGNORECASE
        )
        if amt_match:
            try:
                claimed_amount = float(amt_match.group(1).replace(',', ''))
            except (ValueError, TypeError):
                pass

    if expense_details:
        cat_match = re.search(
            r'(?:Expense Type|Category)[\s:]*([^\n\r]+)',
            str(expense_details),
            re.IGNORECASE
        )
        if cat_match:
            category = cat_match.group(1).strip()

    return claimed_amount, category


def get_policy_for_category(category: str):
    """
    Retrieves structured policy dictionary for a given category name or alias.
    """
    if not category:
        return None
    canonical_key = POLICY_ALIASES.get(category.strip().lower(), category.strip().lower())
    policies = load_knowledge_policies() or COMPANY_POLICIES
    return policies.get(canonical_key)


class CoordinatorAgent:
    def __init__(self):
        self.policy_agent = PolicyAgent()
        self.receipt_agent = ReceiptAgent()
        self.analysis_agent = AnalysisAgent()
        self.decision_agent = DecisionSupportAgent()

    def run_audit(self, expense_details: str, receipt_details: dict, session_id: str) -> dict:
        """
        Executes the multi-agent workflow with conditional decision routing,
        per-agent latency measurement, and structured telemetry generation.
        """
        t_start = time.perf_counter()
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        agent_telemetry = []
        claimed_amount, category = extract_claim_parameters(expense_details, receipt_details)
        policy_data = get_policy_for_category(category)

        # 1. Policy Agent Execution
        t0 = time.perf_counter()
        policy_error = None
        try:
            policy_findings = self.policy_agent.analyze(expense_details)
            if "Policy Agent Error" in policy_findings:
                workflow_status['policy'] = 'Failed'
                policy_error = policy_findings
            else:
                workflow_status['policy'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_policy")
            policy_findings = f"Policy Agent Error: {friendly_err}"
            policy_error = friendly_err
            workflow_status['policy'] = 'Failed'
        dur_policy = (time.perf_counter() - t0) * 1000.0
        agent_telemetry.append({
            "agent": "PolicyAgent",
            "status": workflow_status['policy'],
            "duration_ms": round(dur_policy, 2),
            "error": policy_error
        })

        # 2. Receipt Agent Execution
        t0 = time.perf_counter()
        receipt_error = None
        try:
            receipt_findings = self.receipt_agent.analyze(receipt_details)
            if "Receipt Agent Error" in receipt_findings:
                workflow_status['receipt'] = 'Failed'
                receipt_error = receipt_findings
            else:
                workflow_status['receipt'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_receipt")
            receipt_findings = f"Receipt Agent Error: {friendly_err}"
            receipt_error = friendly_err
            workflow_status['receipt'] = 'Failed'
        dur_receipt = (time.perf_counter() - t0) * 1000.0
        agent_telemetry.append({
            "agent": "ReceiptAgent",
            "status": workflow_status['receipt'],
            "duration_ms": round(dur_receipt, 2),
            "error": receipt_error
        })

        # 3. Deterministic Decision Triage Routing
        policy_verified = (
            policy_data is not None and
            workflow_status['policy'] == 'Completed' and
            "no company policy found" not in policy_findings.lower()
        )

        policy_limit = float(policy_data.get("reimbursement_limit", float("inf"))) if policy_data else float("inf")
        is_over_limit = (claimed_amount > policy_limit) if (policy_verified and claimed_amount > 0) else False

        is_receipt_provided = (
            isinstance(receipt_details, dict) and
            bool(receipt_details.get("receipt_available", False))
        )
        is_receipt_missing = not is_receipt_provided

        amount_mismatch = False
        date_discrepancy = False
        receipt_validation_passed = False

        if is_receipt_provided and workflow_status['receipt'] == 'Completed':
            if "Amount mismatch" in receipt_findings or "amount mismatch" in receipt_findings.lower():
                amount_mismatch = True
            if "Date discrepancy" in receipt_findings or "date discrepancy" in receipt_findings.lower():
                date_discrepancy = True
            if "Receipt Validation: BASIC CHECK PASSED" in receipt_findings:
                receipt_validation_passed = True

        critical_failure = (workflow_status['policy'] == 'Failed' or workflow_status['receipt'] == 'Failed')

        # Evaluate triage priority: ELEVATED_REVIEW > DOCUMENTATION_POLICY_REVIEW > STANDARD_PROCESSING
        if critical_failure or is_over_limit or amount_mismatch:
            triage_level = "ELEVATED_REVIEW"
            if critical_failure:
                decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> ELEVATED_REVIEW (SYSTEM_FAILURE) -> SYNTHESIS -> ADVISORY_REPORT"
            elif is_over_limit:
                decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> ELEVATED_REVIEW (OVER_LIMIT) -> SYNTHESIS -> ADVISORY_REPORT"
            else:
                decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> ELEVATED_REVIEW (AMOUNT_MISMATCH) -> SYNTHESIS -> ADVISORY_REPORT"
        elif is_receipt_missing or (not policy_verified) or date_discrepancy:
            triage_level = "DOCUMENTATION_POLICY_REVIEW"
            if is_receipt_missing:
                decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> DOCUMENTATION_POLICY_REVIEW (MISSING_RECEIPT) -> SYNTHESIS -> ADVISORY_REPORT"
            elif not policy_verified:
                decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> DOCUMENTATION_POLICY_REVIEW (UNVERIFIED_POLICY) -> SYNTHESIS -> ADVISORY_REPORT"
            else:
                decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> DOCUMENTATION_POLICY_REVIEW (DATE_DISCREPANCY) -> SYNTHESIS -> ADVISORY_REPORT"
        elif policy_verified and (not is_over_limit) and receipt_validation_passed and not critical_failure:
            triage_level = "STANDARD_PROCESSING"
            decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> STANDARD_PROCESSING (COMPLIANT) -> SYNTHESIS -> ADVISORY_REPORT"
        else:
            # Safe fallback: never label unverified/edge-case conditions as standard processing
            triage_level = "DOCUMENTATION_POLICY_REVIEW"
            decision_path = "POLICY_CHECK -> RECEIPT_VERIFY -> DOCUMENTATION_POLICY_REVIEW (GENERAL) -> SYNTHESIS -> ADVISORY_REPORT"

        # 4. Analysis Agent Execution
        t0 = time.perf_counter()
        analysis_error = None
        try:
            analysis_findings = self.analysis_agent.analyze(expense_details, policy_findings, receipt_findings)
            if "Analysis Agent Error" in analysis_findings:
                workflow_status['analysis'] = 'Failed'
                analysis_error = analysis_findings
            else:
                workflow_status['analysis'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_analysis")
            analysis_findings = f"Analysis Agent Error: {friendly_err}"
            analysis_error = friendly_err
            workflow_status['analysis'] = 'Failed'
        dur_analysis = (time.perf_counter() - t0) * 1000.0
        agent_telemetry.append({
            "agent": "AnalysisAgent",
            "status": workflow_status['analysis'],
            "duration_ms": round(dur_analysis, 2),
            "error": analysis_error
        })

        # 5. Decision Support Agent Execution
        t0 = time.perf_counter()
        decision_error = None
        try:
            final_report = self.decision_agent.generate_report(analysis_findings)
            if "Decision Support Agent Error" in final_report:
                workflow_status['decision'] = 'Failed'
                decision_error = final_report
            else:
                workflow_status['decision'] = 'Completed'
        except Exception as e:
            friendly_err = get_user_friendly_error(e, context="coordinator_decision")
            final_report = f"Decision Support Agent Error: {friendly_err}"
            decision_error = friendly_err
            workflow_status['decision'] = 'Failed'
        dur_decision = (time.perf_counter() - t0) * 1000.0
        agent_telemetry.append({
            "agent": "DecisionSupportAgent",
            "status": workflow_status['decision'],
            "duration_ms": round(dur_decision, 2),
            "error": decision_error
        })

        # Final failure check adjustments
        if workflow_status['analysis'] == 'Failed' or workflow_status['decision'] == 'Failed':
            triage_level = "ELEVATED_REVIEW"

        total_duration_ms = (time.perf_counter() - t_start) * 1000.0

        decision_flags = {
            "policy_verified": policy_verified,
            "is_over_limit": is_over_limit,
            "is_receipt_missing": is_receipt_missing,
            "amount_mismatch": amount_mismatch,
            "date_discrepancy": date_discrepancy,
            "has_failures": any(item["status"] == "Failed" for item in agent_telemetry)
        }

        telemetry = {
            "trace_id": trace_id,
            "timestamp": timestamp,
            "total_duration_ms": round(total_duration_ms, 2),
            "triage_level": triage_level,
            "decision_path": decision_path,
            "decision_flags": decision_flags,
            "agent_telemetry": agent_telemetry
        }

        # Save to short-term memory
        SESSION_STORE[session_id]['audit_result'] = final_report
        SESSION_STORE[session_id]['workflow_status'] = workflow_status
        SESSION_STORE[session_id]['telemetry'] = telemetry
        SESSION_STORE[session_id]['triage_level'] = triage_level
        SESSION_STORE[session_id]['decision_path'] = decision_path

        # Record sanitized entry to bounded in-memory audit history (max 50)
        history_entry = {
            "trace_id": trace_id,
            "timestamp": timestamp,
            "category": category if category else "General",
            "claimed_amount": round(claimed_amount, 2),
            "triage_level": triage_level,
            "decision_path": decision_path,
            "duration_ms": round(total_duration_ms, 2),
            "has_failures": decision_flags["has_failures"]
        }
        AUDIT_HISTORY.append(history_entry)
        if len(AUDIT_HISTORY) > MAX_AUDIT_HISTORY:
            AUDIT_HISTORY.pop(0)

        return {
            'report': final_report,
            'status': workflow_status,
            'telemetry': telemetry,
            'triage_level': triage_level,
            'decision_path': decision_path
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


def get_dashboard_metrics() -> dict:
    """
    Aggregates metrics over in-memory AUDIT_HISTORY for dashboard presentation.
    """
    total_audits = len(AUDIT_HISTORY)
    if total_audits == 0:
        return {
            "total_claimed": 0.0,
            "pending_audits": 0,
            "flagged_claims": 0,
            "compliance_rate": 0.0,
            "total_audits": 0
        }

    total_claimed = sum(item.get("claimed_amount", 0.0) for item in AUDIT_HISTORY)
    flagged_claims = sum(
        1 for item in AUDIT_HISTORY
        if item.get("triage_level") != "STANDARD_PROCESSING" or item.get("has_failures")
    )
    compliant_claims = total_audits - flagged_claims
    compliance_rate = round((compliant_claims / total_audits) * 100, 1)

    return {
        "total_claimed": round(total_claimed, 2),
        "pending_audits": 0,
        "flagged_claims": flagged_claims,
        "compliance_rate": compliance_rate,
        "total_audits": total_audits
    }


def get_recent_audits(limit: int = 10) -> list:
    """
    Returns up to `limit` recent audit records (anonymized metadata).
    """
    return list(reversed(AUDIT_HISTORY[-limit:]))


def clear_audit_history():
    """
    Clears the in-memory audit history (utility for tests).
    """
    AUDIT_HISTORY.clear()
