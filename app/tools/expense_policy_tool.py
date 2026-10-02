import os
import json
from langchain.tools import tool

# Default fallback simulated company expense policies
COMPANY_POLICIES = {
    "travel": {
        "category": "Domestic Travel",
        "reimbursement_limit": 3500,
        "receipt_required": True,
        "approval_required_above_limit": True
    },
    "meals": {
        "category": "Business Meals",
        "reimbursement_limit": 1500,
        "receipt_required": True,
        "approval_required_above_limit": True
    },
    "accommodation": {
        "category": "Hotel Accommodation",
        "reimbursement_limit": 5000,
        "receipt_required": True,
        "approval_required_above_limit": True
    }
}

# Map common expense names to policy keys
POLICY_ALIASES = {
    "domestic travel": "travel",
    "hotel": "accommodation",
    "hotel accommodation": "accommodation",
    "lodging": "accommodation",
    "business meals": "meals"
}

def load_knowledge_policies():
    """Attempt to load policies from the local JSON knowledge base."""
    # Compute path relative to this file to be safe: 
    # file is in app/tools/ -> we want ../../knowledge/expense_policies.json
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    json_path = os.path.join(base_dir, "knowledge", "expense_policies.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load local knowledge policies: {e}")
    return None

@tool
def get_expense_policy(expense_type: str) -> str:
    """
    Retrieve the simulated company expense policy
    for a given expense type.

    Use this tool when company policy information
    is required to analyze an employee expense.
    """

    expense_type = expense_type.strip().lower()

    # Resolve aliases to their canonical policy keys
    policy_key = POLICY_ALIASES.get(
        expense_type, expense_type
    )

    # Try JSON knowledge first, fallback to in-memory dictionary
    policies = load_knowledge_policies() or COMPANY_POLICIES
    policy = policies.get(policy_key)

    if policy is None:
        return (
            f"No company policy found for expense type: "
            f"{expense_type}. Compliance cannot be confirmed."
        )

    return str(policy)