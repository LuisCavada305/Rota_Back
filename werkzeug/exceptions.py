from __future__ import annotations


class HTTPException(Exception):
    code = 500
    description = "Internal Server Error"

    def __init__(self, description: str | None = None, code: int | None = None) -> None:
        if description is not None:
            self.description = description
        if code is not None:
            self.code = code
        super().__init__(self.description)


class Unauthorized(HTTPException):
    code = 401
    description = "Unauthorized"


class Forbidden(HTTPException):
    code = 403
    description = "Forbidden"
