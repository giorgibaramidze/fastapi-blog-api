class AppException(Exception):
    status_code = 400
    detail = "Application error"
    error_code = "APPLICATION_ERROR"

    def __init__(
        self,
        detail: str | None = None,
        error_code: str | None = None,
    ):
        self.detail = detail or self.detail
        self.error_code = error_code or self.error_code

        super().__init__(self.detail)