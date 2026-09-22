from app.tools.receipt_validation_tool import validate_receipt


result = validate_receipt.invoke({
    "receipt_available": True,
    "merchant": "ABC Travels",
    "receipt_date": "2026-08-13",
    "receipt_amount": 3000.0,
    "claimed_amount": 3000.0,
    "expense_date": "2026-09-13"
})

print("Receipt Validation Tool Result:")
print(result)