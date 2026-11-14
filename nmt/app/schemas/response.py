from typing import Any
from fastapi.responses import JSONResponse

def responseFormat(success: bool, status_code: int = 200, message: str = "Ok", data: Any = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "success": success,
            "data": data
        }
    )