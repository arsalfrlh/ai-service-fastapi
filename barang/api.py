from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from barang.schema import BarangRequest, BarangResponse, LoginRequest, RegisterRequest, UserResponse, TokenResponse
from barang.model import Barang, User, Token
from sqlalchemy.orm import Session
from barang.database import engine, get_db, Base
import json
from datetime import datetime, timezone

from barang.auth import hash_password, verify_password, create_access_token, get_current_user, logout_access_token

app = FastAPI()
# Membuat tabel otomatis
Base.metadata.create_all(bind=engine)

@app.exception_handler(RequestValidationError)
def validation_request(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": exc.errors(),
            "success": False
        }
    )

@app.get("/barang", response_model=list[BarangResponse])
def get_barang(db: Session = Depends(get_db)):
    data = db.query(Barang).all()
    # return JSONResponse(
    #     status_code=200,
    #     content={
    #         "message": "Menampilkan data barang",
    #         "success": True,
    #         "data": {
    #             "id": data.id,
    #             "nama_barang": data.nama_barang,
    #             "merk": data.merk,
    #             "stok": data.stok,
    #             "harga": data.harga
    #         }
    #     }
    # )
    return data

@app.get("/barang/{barang_id}", response_model=BarangResponse) #barang_id itu adalah data id yg diterima dari url, response_mode=BarangResponse itu adalah return response yg akan mengkonversi class jadi data dict
def show_barang(barang_id: int, db: Session = Depends(get_db)):
    data = db.query(Barang).filter(Barang.id == barang_id).first()
    if not data:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Barang tidak ditemukan",
                "success": False
            }
        )

    # return JSONResponse(
    #     status_code=200,
    #     content={
    #         "message": "Menampilkan detail barang",
    #         "success": True,
    #         "data": {
    #             "id": data.id,
    #             "nama_barang": data.nama_barang,
    #             "merk": data.merk,
    #             "stok": data.stok,
    #             "harga": data.harga
    #         }
    #     }
    # )
    return data

@app.post("/barang", response_model=BarangResponse)
def create_barang(request: BarangRequest, db: Session = Depends(get_db)):
    barang = Barang(
        nama_barang = request.nama_barang,
        merk = request.merk,
        stok = request.stok,
        harga = request.harga
    )
    db.add(barang)
    db.commit()
    db.refresh(barang) #fungsi refresh untuk menandapatkan data barang dari sql yg sudah ada id nya, dll
    # return JSONResponse(
    #     status_code=201,
    #     content={
    #         "message": "Barang berhasil ditambahkan",
    #         "success": True,
    #         "data": {
    #             "id": barang.id,
    #             "nama_barang": barang.nama_barang,
    #             "merk": barang.merk,
    #             "stok": barang.stok,
    #             "harga": barang.harga
    #         }
    #     }
    # )
    return barang

@app.put("/barang/{barang_id}", response_model=BarangResponse)
def update_barang(barang_id: int, request: BarangRequest, db: Session = Depends(get_db)):
    barang = db.query(Barang).filter(Barang.id == barang_id).first()
    if not barang:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Barang tidak ditemukan",
                "success": False
            }
        )

    barang.nama_barang = request.nama_barang
    barang.merk = request.merk
    barang.stok = request.stok
    barang.harga = request.harga
    db.commit()
    db.refresh(barang)
    return barang

@app.delete("/barang/{barang_id}")
def delete_barang(barang_id: int, db: Session = Depends(get_db)):
    barang = db.query(Barang).filter(Barang.id == barang_id).first()
    if not barang:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Barang tidak ditemukan",
                "success": False
            }
        )

    db.delete(barang)
    db.commit()
    return JSONResponse(
        status_code=200,
        content={
            "message": "Barang telah dihapus",
            "success": True
        }
    )

@app.post("/register", response_model=UserResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Email sudah terdaftar",
                "success": False
            }
        )

    hashed_password = hash_password(request.password)
    user = User(
        name=request.name,
        email=request.email,
        password=hashed_password
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Email tidak terdaftar di sistem",
                "success": False
            }
        )

    valid_password = verify_password(request.password, user.password)
    if not valid_password:
        return JSONResponse(
            status_code=401,
            content={
                "message": "Password anda salah",
                "success": False
            }
        )

    access_token, jti, expires_at = create_access_token(user.id)
    token = Token(
        user_id=user.id,
        jti=jti,
        expires_at=expires_at
    )
    db.add(token)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "token_type": "Bearer"
        }
    )

@app.get("/user", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/logout")
def logout(response: JSONResponse = Depends(logout_access_token)):
    return response