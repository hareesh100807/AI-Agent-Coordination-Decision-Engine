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
    result = analyze_expense(expense_details)
    print("\nAUDIT RESULT")
    print("-" * 60)
    print(result)
    print("-" * 60)

except Exception as e:
    print("\nUnable to analyze the expense at this time.")
    print("The AI service may have reached its request limit.")
    print("Please try again later.")