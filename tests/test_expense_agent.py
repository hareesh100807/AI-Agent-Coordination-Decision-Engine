from app.agents.expense_audit_agent import analyze_expense

expense_details = """
Employee: Ravi
Expense Type: Hotel Accommodation
Amount: ₹4,500
Purpose: Business trip
Date: 1 September 2026
Description: One night hotel stay during an official business trip.
"""
result = analyze_expense(expense_details)
print("Expense Audit Result:")
print(result)