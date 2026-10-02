from app.tools.receipt_validation_tool import validate_receipt

class ReceiptAgent:
    def analyze(self, receipt_details: dict) -> str:
        """
        Uses the receipt validation tool to perform basic checks on the receipt.
        Does not claim authenticity verification.
        """
        if not isinstance(receipt_details, dict):
            return "Receipt Agent Error: Invalid receipt details format (expected dictionary)."

        # Ensure all required parameters for validate_receipt tool are present with safe defaults
        safe_details = {
            "receipt_available": bool(receipt_details.get("receipt_available", False)),
            "merchant": str(receipt_details.get("merchant", "") or ""),
            "receipt_date": str(receipt_details.get("receipt_date", "") or ""),
            "receipt_amount": float(receipt_details.get("receipt_amount", 0.0) or 0.0),
            "claimed_amount": float(receipt_details.get("claimed_amount", 0.0) or 0.0),
            "expense_date": str(receipt_details.get("expense_date", "") or "")
        }
            
        try:
            result = validate_receipt.invoke(safe_details)
            return f"Receipt Findings: {result}"
        except Exception as e:
            return f"Receipt Agent Error: {e}"
