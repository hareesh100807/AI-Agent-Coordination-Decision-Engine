import logging
import re

# Configure standard logger
logger = logging.getLogger("expense_audit_system")

def is_quota_error(exc: Exception) -> bool:
    """
    Detects if an exception represents Gemini API quota exhaustion or HTTP 429 rate limit.
    """
    if exc is None:
        return False
    
    err_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()
    
    quota_keywords = [
        "resource_exhausted",
        "429",
        "quota",
        "ratelimit",
        "rate limit",
        "too many requests",
        "exceeded your current quota"
    ]
    
    if any(kw in err_str for kw in quota_keywords) or any(kw in exc_type for kw in quota_keywords):
        return True
        
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code in (429, "429"):
        return True
        
    return False

def get_user_friendly_error(exc: Exception, context: str = "general") -> str:
    """
    Logs technical details server-side (without logging secrets/API keys)
    and returns a user-friendly error message without exposing technical metadata,
    stack traces, or internal paths.
    """
    err_str = str(exc) if exc else "Unknown error"
    
    # Mask API keys if present in error text for logging safety
    safe_log_str = re.sub(r'key=[A-Za-z0-9_\-]+', 'key=***MASKED***', err_str, flags=re.IGNORECASE)
    logger.error(f"[{context.upper()}_ERROR] {type(exc).__name__}: {safe_log_str}")
    
    if is_quota_error(exc):
        return "The AI service has temporarily reached its usage limit. Please try again later."
        
    return "An error occurred while processing the request. Please try again later."
