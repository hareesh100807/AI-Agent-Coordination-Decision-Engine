from app.tools.expense_policy_tool import get_expense_policy


result = get_expense_policy.invoke({
    "expense_type": "travel"
})

print("Expense Policy Tool Result:")
print(result)