from fastapi import FastAPI, WebSocket, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Any
from pydantic import BaseModel
import json
import uuid
import os

app = FastAPI()
FILE = "products.json"

#function validasi error
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "message": exc.errors(),
            "success": False
        }
    )

#function json helper
def read_products():
    if not os.path.exists(FILE):
        return []

    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def write_products(products):
    with open(FILE, 'w', encoding="utf-8") as w:
        json.dump(products, w, indent=4, ensure_ascii=False)

#class return response
class ApiResponse(BaseModel):
    message: Any
    success: bool
    data: Any = None

#class product request
class ProductRequest(BaseModel):
    product_name: str
    description: str
    price: int
    stock: int

@app.post("/product", response_model=ApiResponse) #response_model berarti return harus berupa class ApiResponse
def create_product(request: ProductRequest):
    products = read_products()
    product = {
        "id": str(uuid.uuid4()),
        "product_name": request.product_name,
        "description": request.description,
        "price": request.price,
        "stock": request.stock
    }
    products.append(product)
    write_products(products)
    return{
        "message": "Product berhasil ditambahkan",
        "success": True,
        "data": product
    }

@app.get("/product")
def get_product():
    products = read_products()
    return{
        "message": "Menampilkan semua product",
        "success": True,
        "data": products
    }

@app.get("/product/{id}", response_model=ApiResponse)
def detail_product(id: str):
    products = read_products()
    product = next((product for product in products if product['id'] == str(id)), None)

    if product is None:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Product tidak ditemukan"
            }
        )

    return {
        "success": True,
        "message": "Menampilkan detail product",
        "data": product
    }

@app.put("/product/{id}", response_model=ApiResponse)
def update_product(id: str, request: ProductRequest):
    products = read_products()
    for index, product in enumerate(products):
        if product['id'] == str(id):
            product_update = {
                "id": str(id),
                "product_name": request.product_name,
                "description": request.description,
                "price": request.price,
                "stock": request.stock
            }
            products[index] = product_update
            write_products(products)

            return{
                "message": "Product berhasil diupdate",
                "success": True,
                "data": product_update
            }
        
    return JSONResponse(
        status_code=404,
        content={
            "message": "Product tidak ditemukan",
            "success": False,
            "data": None
        }
    )

@app.delete("/product/{id}", response_model=ApiResponse)
def delete_product(id: str):
    products = read_products()
    product = next((product for product in products if product['id'] == str(id)), None)

    if product is None:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Product tidak ditemukan"
            }
        )

    products.remove(product)
    write_products(products)
    return {
        "success": True,
        "message": "Product telah dihapus",
        "data": product
    }