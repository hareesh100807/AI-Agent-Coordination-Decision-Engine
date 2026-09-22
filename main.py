from app.agents.expense_audit_agent import analyze_expense


print("=" * 60)
print(" Enterprise Employee Expense Intelligence & Audit System")
print("=" * 60)

print("\nEnter the expense details below.\n")

employee_name = input("Employee Name: ")
expense_type = input("Expense Type: ")
amount = input("Amount (₹): ")
purpose = input("Purpose: ")
date = input("Date: ")
description = input("Description: ")

# Collect receipt details
print("\nEnter receipt details below.\n")

receipt_available = input("Receipt Available? (yes/no): ").strip().lower()

merchant = ""
receipt_date = ""
receipt_amount = ""

if receipt_available == "yes":
    merchant = input("Merchant Name: ")
    receipt_date = input("Receipt Date (YYYY-MM-DD): ")
    receipt_amount = input("Receipt Amount (₹): ")

# Prepare expense information for the AI agent
expense_details = f"""
Employee: {employee_name}
Expense Type: {expense_type}
Amount: ₹{amount}
Purpose: {purpose}
Date: {date}
Description: {description}
"""

print("\nAnalyzing expense...")
print("Please wait while the AI agent analyzes the expense...")
print("-" * 60)

try:
    result = analyze_expense(expense_details, receipt_details={
        "receipt_available": receipt_available == "yes",
        "merchant": merchant,
        "receipt_date": receipt_date,
        "receipt_amount": float(receipt_amount) if receipt_amount else 0,
        "claimed_amount": float(amount),
        "expense_date": date
    })
    print("\nAUDIT RESULT")
    print("-" * 60)
    print(result)
    print("-" * 60)

except Exception as e:
    print("\nUnable to analyze the expense at this time.")
    print("The AI service may have reached its request limit.")
    print("Please try again later.")