class YbsError(Exception):
    """An expected user-facing failure with a stable process exit code."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
