from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from barang.database import Base, get_db, SessionLocal, engine
from barang.model import Hotel, Facility
from sqlalchemy.orm import Session, selectinload
from barang.schema import HotelRequest

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.exception_handler(RequestValidationError)
def request_validation(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": exc.errors(),
            "success": False
        }
    )

@app.get("/hotel")
def get_hotel(db: Session = Depends(get_db)):
    hotels = db.query(Hotel).options(selectinload(Hotel.facility)).all()
    data = []
    for hotel in hotels:
        facilities = []
        for facility in hotel.facility:
            facilities.append({
                "id": facility.id,
                "facility_name": facility.facility_name
            })

        data.append({
            "id": hotel.id,
            "hotel_name": hotel.hotel_name,
            "rating": hotel.rating,
            "facilites": facilities
        })

    return JSONResponse(
        status_code=200,
        content={
            "message": "Menampilkan semua data hotel",
            "success": True,
            "data": data
        }
    )

@app.post("/hotel")
def create_hotel(request: HotelRequest, db: Session = Depends(get_db)):
    hotel = Hotel(
        hotel_name = request.nama_hotel,
        rating = request.rating
    )
    db.add(hotel)
    db.flush()
    for facility in request.facilities:
        db.add(Facility(
            hotel_id = hotel.id,
            facility_name = facility.facility_name
        ))
    db.commit()

    return JSONResponse(
        status_code=201,
        content={
            "message": "Hotel berhasil ditambahkan",
            "success": True
        }
    )

@app.put("/hotel/{hotel_id}")
def update_hotel(hotel_id: int, request: HotelRequest, db: Session = Depends(get_db)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Hotel tidak ditemukan",
                "success": False
            }
        )

    hotel.hotel_name = request.nama_hotel
    hotel.rating = request.rating

    for fc in request.facilities:
        facility = db.query(Facility).filter(Facility.id == fc.facility_id).first()
        if not facility:
            return JSONResponse(
                status_code=404,
                content={
                    "message": "Fasilitas tidak ditemukan",
                    "success": False
                }
            )
        facility.facility_name = fc.facility_name
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "message": "Hotel berhasil diupdate",
            "success": True
        }
    )

@app.delete("/hotel/{hotel_id}")
def delete_hotel(hotel_id: int, db: Session = Depends(get_db)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Hotel tidak ditemukan",
                "success": False
            }
        )
    db.delete(hotel)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "message": "Hotel telah dihapus",
            "success": True
        }
    )