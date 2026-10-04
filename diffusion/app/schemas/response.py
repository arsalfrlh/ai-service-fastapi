from fastapi.responses import JSONResponse
from typing import Any

def responseFormat(success: bool, status_code: int = 200, message: Any = "Ok", data: Any = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "success": success,
            "data": data
        }
    )