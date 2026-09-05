import uuid
import jwt
from datetime import datetime, timedelta, timezone
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from sqlalchemy.orm import Session
from barang.database import get_db
from barang.model import Token, User
from fastapi.responses import JSONResponse

SECRET_KEY = "kwanzzx-arsalfrlh"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login"
)

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def credential_exception(message: str):
    return JSONResponse(
        status_code=401,
        headers={
            "WWW-Authenticate": "Bearer"
        },
        content={
            "message": message,
            "success": False
        }
    )

def create_access_token(user_id: int, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    jti = str(uuid.uuid4())

    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": now,
        "exp": expire
    }

    token = jwt.encode(
        payload=payload,
        key=SECRET_KEY,
        algorithm=ALGORITHM
    )
    return token, jti, expire

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(jwt=token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        jti = payload['jti']

        if user_id is None or jti is None:
            return credential_exception("Invalid Token")

        user_id = int(user_id)
    except (InvalidTokenError, ValueError, TypeError):
        return credential_exception("Interval Server Error")

    db_token = db.query(Token).filter(Token.jti == jti).first()
    if not db_token:
        return credential_exception("User Not Found")

    if db_token.revoked_at is not None:
        return credential_exception("Token Sudah logout")

    now = datetime.now(timezone.utc)
    expires_at = db_token.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= now:
        return credential_exception("Token Expired")

    user = db.query(User).filter(User.id == user_id).first()
    if not User:
        return credential_exception("User Not Found")

    return user

def logout_access_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(jwt=token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        jti = payload['jti']

        if user_id is None or jti is None:
            return credential_exception("Invalid Token")

        user_id = int(user_id)
    except (InvalidTokenError, ValueError, TypeError) as e:
        print(e)
        return credential_exception("Interval Server Error")

    db_token = db.query(Token).filter(Token.jti == jti).first()
    if not db_token:
            return credential_exception("User Not Found")

    db_token.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return JSONResponse(
        status_code=200,
        content={
            "message": "Anda telah logout",
            "success": True
        }
    )