from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
class BarangRequest(BaseModel):
    nama_barang: str
    merk: str
    stok: int
    harga: int

class BarangResponse(BaseModel):
    id: int
    nama_barang: str
    merk: str
    stok: int
    harga: int

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime
    model_config = ConfigDict(
        from_attributes=True
    )

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class FacilityRequest(BaseModel):
    facility_id: int | None = None
    facility_name: str

class HotelRequest(BaseModel):
    nama_hotel: str
    rating: int
    facilities: list[FacilityRequest]