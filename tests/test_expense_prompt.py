from app.prompts.templates import expense_audit_prompt


expense_details = """
Employee: Ravi
Expense Type: Hotel Accommodation
Amount: ₹4,500
Purpose: Business trip
Date: 1 September 2026
Description: One night hotel stay during an official business trip.
"""


messages = expense_audit_prompt.format_messages(
    expense_details=expense_details
)

print("Generated Prompt:")
print("-----------------")

for message in messages:
    print(f"{message.type.upper()}:")
    print(message.content)
    print()