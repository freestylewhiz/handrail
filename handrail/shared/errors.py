"""Errors retain the failing boundary without leaking provider output."""
class HandrailError(Exception):
    def __init__(self, code, message, *, details=None, retryable=False, uncertain=False):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.retryable = retryable
        self.uncertain = uncertain

    def as_dict(self):
        return {"error": self.code, "message": str(self), "details": self.details,
                "retryable": self.retryable, "uncertain": self.uncertain}
