"""
Enterprise Employee Expense Intelligence & Audit System
Professional Finance Dashboard - Web Application Entry Point

Phase 3: Flask + AI Agent Integration
- Connects expense submission to the existing LangChain + Gemini audit agent (analyze_expense).
- Passes structured expense & receipt details to the agent workflow.
- Captures and renders real audit findings or handles AI availability/quota errors gracefully.
- Maintains zero database persistence; files are validated in-memory only.
"""

import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Import the existing AI audit agent
from app.agents.expense_audit_agent import analyze_expense

app = Flask(__name__)

# Valid policy categories mapped to canonical names recognized by policy tools
VALID_CATEGORIES = {
    "travel": "Domestic Travel (Limit: ₹3,500)",
    "meals": "Business Meals (Limit: ₹1,500)",
    "accommodation": "Hotel Accommodation (Limit: ₹5,000)"
}

# Category names formatted for the AI agent policy tool lookup
CATEGORY_POLICY_NAMES = {
    "travel": "Domestic Travel",
    "meals": "Business Meals",
    "accommodation": "Hotel Accommodation"
}

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@app.route("/")
def dashboard():
    """
    Renders the primary finance dashboard in an empty state.
    KPI metrics initialize at zero values.
    """
    kpi_data = {
        "total_claimed": 0,
        "pending_audits": 0,
        "flagged_claims": 0,
        "compliance_rate": 0.0,
    }
    
    expenses = []
    
    return render_template(
        "dashboard.html",
        kpi_data=kpi_data,
        expenses=expenses
    )


@app.route("/submit-expense", methods=["GET", "POST"])
def submit_expense():
    """
    Handles rendering, server-side validation, and dispatching validated
    claims to the existing Gemini AI audit agent.
    """
    errors = {}
    form_data = {
        "employee_name": "",
        "expense_category": "",
        "claimed_amount": "",
        "expense_date": "",
        "purpose": "",
        "description": "",
        "receipt_available": "no",
        "merchant": "",
        "receipt_date": "",
        "receipt_amount": ""
    }

    if request.method == "POST":
        # Extract text inputs
        employee_name = request.form.get("employee_name", "").strip()
        expense_category = request.form.get("expense_category", "").strip().lower()
        claimed_amount_raw = request.form.get("claimed_amount", "").strip()
        expense_date_raw = request.form.get("expense_date", "").strip()
        purpose = request.form.get("purpose", "").strip()
        description = request.form.get("description", "").strip()
        receipt_available = request.form.get("receipt_available", "no").strip().lower()
        merchant = request.form.get("merchant", "").strip()
        receipt_date_raw = request.form.get("receipt_date", "").strip()
        receipt_amount_raw = request.form.get("receipt_amount", "").strip()

        # Extract file upload
        receipt_file = request.files.get("receipt_file")

        # Repopulation state
        form_data = {
            "employee_name": employee_name,
            "expense_category": expense_category,
            "claimed_amount": claimed_amount_raw,
            "expense_date": expense_date_raw,
            "purpose": purpose,
            "description": description,
            "receipt_available": receipt_available,
            "merchant": merchant,
            "receipt_date": receipt_date_raw,
            "receipt_amount": receipt_amount_raw
        }

        # 1. Employee Name Validation
        if not employee_name:
            errors["employee_name"] = "Employee name is required."
        elif len(employee_name) < 2:
            errors["employee_name"] = "Employee name must be at least 2 characters."

        # 2. Category Validation
        if not expense_category:
            errors["expense_category"] = "Please select an expense category."
        elif expense_category not in VALID_CATEGORIES:
            errors["expense_category"] = "Invalid expense category selected."

        # 3. Claimed Amount Validation
        claimed_amount = 0.0
        if not claimed_amount_raw:
            errors["claimed_amount"] = "Claimed amount is required."
        else:
            try:
                claimed_amount = float(claimed_amount_raw)
                if claimed_amount <= 0:
                    errors["claimed_amount"] = "Claimed amount must be greater than ₹0."
            except ValueError:
                errors["claimed_amount"] = "Please enter a valid numeric amount."

        # 4. Expense Date Validation
        if not expense_date_raw:
            errors["expense_date"] = "Expense date is required."
        else:
            try:
                datetime.strptime(expense_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors["expense_date"] = "Please enter a valid date (YYYY-MM-DD)."

        # 5. Purpose Validation
        if not purpose:
            errors["purpose"] = "Purpose is required."

        # 6. Receipt Details & File Validation
        receipt_amount = 0.0
        uploaded_file_info = None

        if receipt_available == "yes":
            if not merchant:
                errors["merchant"] = "Merchant name is required when receipt is available."

            if not receipt_date_raw:
                errors["receipt_date"] = "Receipt date is required when receipt is available."
            else:
                try:
                    datetime.strptime(receipt_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    errors["receipt_date"] = "Please enter a valid receipt date (YYYY-MM-DD)."

            if not receipt_amount_raw:
                errors["receipt_amount"] = "Receipt amount is required when receipt is available."
            else:
                try:
                    receipt_amount = float(receipt_amount_raw)
                    if receipt_amount <= 0:
                        errors["receipt_amount"] = "Receipt amount must be greater than ₹0."
                except ValueError:
                    errors["receipt_amount"] = "Please enter a valid numeric receipt amount."

            # File Validation (In-memory inspection)
            if receipt_file and receipt_file.filename:
                filename = receipt_file.filename.strip()
                if not allowed_file(filename):
                    errors["receipt_file"] = "Invalid file type. Only PDF, JPG, JPEG, and PNG files are supported."
                else:
                    receipt_file.seek(0, os.SEEK_END)
                    file_size = receipt_file.tell()
                    receipt_file.seek(0)

                    if file_size > MAX_FILE_SIZE_BYTES:
                        errors["receipt_file"] = f"File size exceeds the 5 MB limit ({format_file_size(file_size)})."
                    elif file_size == 0:
                        errors["receipt_file"] = "Uploaded file is empty (0 bytes)."
                    else:
                        ext = filename.rsplit(".", 1)[1].lower()
                        uploaded_file_info = {
                            "filename": filename,
                            "size_bytes": file_size,
                            "formatted_size": format_file_size(file_size),
                            "extension": ext,
                            "is_image": ext in {"jpg", "jpeg", "png"},
                            "is_pdf": ext == "pdf"
                        }

        # If validation succeeds, invoke the existing AI agent
        if not errors:
            policy_category_name = CATEGORY_POLICY_NAMES.get(expense_category, expense_category.title())
            display_category = VALID_CATEGORIES.get(expense_category, policy_category_name)

            # 1. Format expense_details string for analyze_expense()
            expense_details = f"""
Employee: {employee_name}
Expense Type: {policy_category_name}
Amount: ₹{claimed_amount}
Purpose: {purpose}
Date: {expense_date_raw}
Description: {description if description else 'N/A'}
"""

            # 2. Format receipt_details dict for analyze_expense()
            receipt_details = {
                "receipt_available": (receipt_available == "yes"),
                "merchant": merchant if receipt_available == "yes" else "",
                "receipt_date": receipt_date_raw if receipt_available == "yes" else "",
                "receipt_amount": receipt_amount if receipt_available == "yes" else 0.0,
                "claimed_amount": claimed_amount,
                "expense_date": expense_date_raw
            }

            claim_summary = {
                "employee_name": employee_name,
                "expense_category": display_category,
                "policy_category_name": policy_category_name,
                "claimed_amount": claimed_amount,
                "expense_date": expense_date_raw,
                "purpose": purpose,
                "description": description if description else "—",
                "receipt_available": (receipt_available == "yes"),
                "merchant": merchant if receipt_available == "yes" else "—",
                "receipt_date": receipt_date_raw if receipt_available == "yes" else "—",
                "receipt_amount": receipt_amount if receipt_available == "yes" else 0.0,
                "uploaded_file": uploaded_file_info,
                "audited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 3. Invoke existing AI Agent
            audit_result_text = None
            audit_status = "success"
            audit_error_message = None

            try:
                raw_result = analyze_expense(expense_details, receipt_details=receipt_details)
                
                # Check if agent returned the fallback unavailable response
                if isinstance(raw_result, str) and ("AI audit unavailable" in raw_result or "could not complete the analysis" in raw_result):
                    audit_status = "unavailable"
                    audit_result_text = raw_result
                else:
                    audit_result_text = raw_result

            except Exception as exc:
                audit_status = "error"
                audit_error_message = str(exc)
                audit_result_text = (
                    "AI audit could not be performed due to an unexpected service or network error. "
                    "Please check your API configuration or try again later."
                )

            return render_template(
                "audit_result.html",
                claim=claim_summary,
                audit_result=audit_result_text,
                audit_status=audit_status,
                audit_error_message=audit_error_message
            )

    return render_template(
        "submit_expense.html",
        errors=errors,
        form_data=form_data,
        categories=VALID_CATEGORIES
    )


@app.route("/api/health")
def health_check():
    """
    Basic application health check.
    """
    return jsonify({
        "status": "healthy",
        "service": "Enterprise Expense Intelligence UI",
        "database_connected": False,
        "mode": "Phase 3: Flask + AI Agent Integration Active"
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
