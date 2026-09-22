from langchain.tools import tool


# Simulated company expense policies
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

    policy = COMPANY_POLICIES.get(policy_key)

    if policy is None:
        return (
            f"No company policy found for expense type: "
            f"{expense_type}. Compliance cannot be confirmed."
        )

    return str(policy)