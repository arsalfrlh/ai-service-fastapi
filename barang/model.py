from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from barang.database import Base
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy.orm import Relationship

class Barang(Base):
    __tablename__ = "barang"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nama_barang = Column(String(255), nullable=False)
    merk = Column(String(255), nullable=False)
    stok = Column(Integer, nullable=False)
    harga = Column(Integer, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(225), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    jti = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Hotel(Base):
    __tablename__ = "hotels"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_name = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)

    facility = Relationship( #attribute facility dlm class Hotel
        "Facility", #mengisi nama class Facility
        back_populates="hotel", #mengisi nama attribute yg ada di class Facility.hotel
        cascade="all, delete-orphan")

class Facility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"))
    facility_name = Column(String(255), nullable=False)

    hotel = Relationship( #attribute hotel dlm class Facility
        "Hotel", #mengisi nama class Hotel
        back_populates="facility") #mengisi nama attribute yg ada di class Hotel.facility