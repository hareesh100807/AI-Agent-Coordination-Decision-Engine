
from datetime import datetime
from langchain.tools import tool


@tool
def validate_receipt(
    receipt_available: bool,
    merchant: str,
    receipt_date: str,
    receipt_amount: float,
    claimed_amount: float,
    expense_date: str
) -> str:
    """
    Check receipt completeness and compare receipt
    details with the submitted expense.

    This is a basic consistency check. It does not
    verify receipt authenticity or policy compliance.
    """

    if not receipt_available:
        return (
            "Receipt is not available. "
            "Manual review required."
        )

    issues = []
    findings = []

    # 1. Check merchant
    if not merchant or not merchant.strip():
        issues.append("Merchant name is missing")
    else:
        findings.append(f"Merchant: {merchant.strip()}")

    # 2. Validate receipt date
    parsed_receipt_date = None

    try:
        parsed_receipt_date = datetime.strptime(
            receipt_date, "%Y-%m-%d"
        ).date()
        findings.append(f"Receipt date: {receipt_date}")
    except (ValueError, TypeError):
        issues.append(
            "Receipt date is missing or invalid "
            "(expected YYYY-MM-DD)"
        )

    # 3. Validate receipt amount
    if receipt_amount <= 0:
        issues.append("Receipt amount must be greater than zero")
    else:
        findings.append(f"Receipt amount: ₹{receipt_amount:.2f}")

    # 4. Validate claimed expense amount
    if claimed_amount <= 0:
        issues.append(
            "Claimed expense amount must be greater than zero"
        )
    elif receipt_amount > 0 and receipt_amount != claimed_amount:
        issues.append(
            f"Amount mismatch: claimed ₹{claimed_amount:.2f}, "
            f"receipt ₹{receipt_amount:.2f}"
        )
    elif claimed_amount > 0 and receipt_amount > 0:
        findings.append("Receipt amount matches claimed amount")

    # 5. Compare expense date and receipt date
    parsed_expense_date = None

    try:
        parsed_expense_date = datetime.strptime(
            expense_date, "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError):
        issues.append(
            "Expense date is missing or invalid "
            "(expected YYYY-MM-DD)"
        )

    if parsed_receipt_date and parsed_expense_date:
        if parsed_receipt_date != parsed_expense_date:
            issues.append(
                f"Date discrepancy: expense date "
                f"{expense_date}, receipt date {receipt_date}"
            )
        else:
            findings.append("Receipt date matches expense date")

    # 6. Return combined validation result
    if issues:
        return (
            "Receipt Validation: REQUIRES REVIEW\n"
            + "\n".join(f"- {item}" for item in findings)
            + "\nIssues detected:\n"
            + "\n".join(f"- {item}" for item in issues)
            + "\nAuthenticity and policy compliance are not verified."
        )

    return (
        "Receipt Validation: BASIC CHECK PASSED\n"
        + "\n".join(f"- {item}" for item in findings)
        + "\nNo basic completeness or amount/date "
        "mismatch detected. Authenticity and policy "
        "compliance are not verified."
    )